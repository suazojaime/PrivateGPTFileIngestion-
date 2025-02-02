__version__ = "$Revision: 1.13 $"

import minestar
logger = minestar.initApp()
import os, sys, csv
import mstarpaths, mstarrun, ServerTools, i18n, zipSnapshot, makeShortcuts, shutil, FailoverTools, datastore
import filemutex, time


MIGRATE_SPEC = "CLASS=%s OPERATION=Migrate WHERE=%s TARGET=%s;\n"

def syncStandbyHistoricalDatabase():
    """Copy active cycles and delays for production to standby database"""
    mutex = filemutex.Mutex("syncStandbyHistoricalDatabase", 30)
    try:
        try:
            mutex.lock()
            logger.info("Updating standby database with historical production data")
            #create link in historical database to point to standby
            hist = datastore.getDataStore("_HISTORICALDB")
            standbyHist = datastore.getDataStore("_HISTORICALDB", "STANDBY")
            import databaseDifferentiator
            dbobject = databaseDifferentiator.returndbObject()
            if(dbobject.getDBString()=="Oracle"):
                hist.dropDBLink(standbyHist.linkName)
                hist.createDBLink(standbyHist)
                logger.info("Link to standby historical database created")
            else:
                dbobject.createLinkServer(hist,"production")
                dbobject.createLinkServer(standbyHist,"standby")
                logger.info("Link to standby historical database created")
            # set the dbdataman script name:
            migrateSpecFileName = mstarpaths.interpretPath("{MSTAR_TEMP}/dbdataman_standbymigrate.txt")
            migrateSpecFile = open(migrateSpecFileName, "w")
            filter = FailoverTools.getStandbyDelayFilter()
            migrateSpecFile.write(MIGRATE_SPEC % ("Delay", filter, standbyHist.linkName))
            filter = FailoverTools.getStandbyCycleFilter()
            migrateSpecFile.write(MIGRATE_SPEC % ("Cycle", filter, standbyHist.linkName))
            migrateSpecFile.close()

            logger.info("Copying historical standby data")
            FailoverTools.deleteHistoricalStandbyData()
            hist.dbdataman("-ca", migrateSpecFileName)

            #update next oid
            standbyModel = datastore.getDataStore("_MODELDB", "STANDBY")
            FailoverTools.updateNextOid(standbyModel, standbyHist)

        except filemutex.MutexError:
            logger.warn("syncStandbyHistoricalDatabase could not aquire lock - no sync possible this invocation")
            logger.warn("try checking if the snapshot folder exists in the following directory and remove")
            logger.warn("directory is: %s" % mutex.getFilename())
    finally:
        mutex.release()

def syncStandbyPitModelDatabase():
    """Copy machine_in_pit and machine_in_pit_gb_list to standby database"""
    mutex = filemutex.Mutex("syncStandbyPitModelDatabase", 30)
    try:
        try:
            mutex.lock()
            logger.info("Updating standby database with pit model data")
            #create link in pit model database to point to standby
            pitModel = datastore.getDataStore("_PITMODELDB")
            standbyPitModel = datastore.getDataStore("_PITMODELDB", "STANDBY")
            import databaseDifferentiator
            dbobject = databaseDifferentiator.returndbObject()
            if(dbobject.getDBString()=="Oracle"):
                pitModel.dropDBLink(standbyPitModel.linkName)
                pitModel.createDBLink(standbyPitModel)
                logger.info("Link to standby pit model database created: " + standbyPitModel.linkName)
                pitModel.javaUpdate("delete from machine_in_pit_gb_list@%s" % standbyPitModel.linkName)
                pitModel.javaUpdate("delete from machine_in_pit@%s" % standbyPitModel.linkName)
                logger.info("Deleted standby records from pit model standby")
                pitModel.javaUpdate("insert into machine_in_pit@%s select * from machine_in_pit" % standbyPitModel.linkName)
                pitModel.javaUpdate("insert into machine_in_pit_gb_list@%s select * from machine_in_pit_gb_list" % standbyPitModel.linkName)
                logger.info("Copied pit model standby data")
            else:
                dbobject.createLinkServer(pitModel,"production")
                dbobject.createLinkServer(standbyPitModel,"standby")
                logger.info("Link to standby pit model database created")
                instanceName = standbyPitModel.instance
                standbydb=ServerTools.getStandbyDatabaseServer()
                sysUser =standbyPitModel.user
                pitModel.javaUpdate("delete from [%s\%s].%s.dbo.machine_in_pit" % (standbydb,instanceName,sysUser))
                pitModel.javaUpdate("delete from [%s\%s].%s.dbo.machine_in_pit_gb_list" % (standbydb,instanceName,sysUser))
                logger.info("Deleted standby records from pit model standby")
                pitModel.javaUpdate("insert into [%s\%s].%s.dbo.machine_in_pit select * from machine_in_pit" % (standbydb,instanceName,sysUser))
                pitModel.javaUpdate("insert into [%s\%s].%s.dbo.machine_in_pit_gb_list select * from machine_in_pit_gb_list" % (standbydb,instanceName,sysUser))
                logger.info("Copied pit model standby data")
        except filemutex.MutexError:
            logger.warn("syncStandbyPitModelDatabase could not aquire lock - no sync possible this invocation")
            logger.warn("try checking if the snapshot folder exists in the following directory and remove")
            logger.warn("directory is: %s" % mutex.getFilename())
    finally:
        mutex.release()

def syncStandbyDirectory(standbyDir, area=None):
    #copy across necessary config and data files - similar to performing a standby snapshot
    #copy stuff which would go into a standby snapshot
    standbyDir = standbyDir.rstrip(os.path.sep)
    currentSystem = mstarpaths.interpretVar("MSTAR_SYSTEM")
    standbyFileDest = os.path.sep.join([standbyDir, currentSystem])
    logger.info("Syncing standby directory %s for system %s" % (standbyDir, currentSystem))
    includeUpdates = 0
    if area is None:
        includeUpdates = 1
    manifest = zipSnapshot.getManifest(-1, includeUpdates=includeUpdates, specifiedAreas=area,includeOnboard=1,includeDXF=1)
    files = manifest.keys()
    files.sort()
    systemPath = mstarpaths.interpretPath("{MSTAR_BASE_CENTRAL}")
    updatesPath = mstarpaths.interpretPath("{MSTAR_UPDATES}")
    for sourceFile in files:
        relPaths =sourceFile.split(systemPath)
        if len(relPaths)<2:
            #print "Ignoring non site config file %s" % sourceFile
            continue
        destFile = os.path.sep.join([standbyFileDest, relPaths[1]])
        if len(sourceFile.split(updatesPath)) > 1:
            #do not copy patch or service pack if file already exists
            if os.path.exists(destFile):
                print "Ignoring update %s which already exists" % os.path.basename(destFile)
                continue
        minestar.makeDirsFor(destFile)
        shutil.copy(sourceFile, destFile)

    logger.info("Standby directory synchronised, now recreating shortcuts")
    # As links on the original system may not work, rename the existing standby shortcuts directory
    # out of the way and create new ones suitable for the standby computer
    logger.info("Moving existing shortcuts out of the way ...")
    existingShortcuts = standbyFileDest + os.sep + "shortcuts"
    copiedShortcuts = standbyFileDest + os.sep + "shortcuts.original"
    if minestar.isDirectory(copiedShortcuts):
        minestar.rmdir(copiedShortcuts)
    try:
        os.rename(existingShortcuts, copiedShortcuts)
    except:
        logger.warn("Failed to move existing shortcuts out of the way - old shortcuts will be lost")
    logger.info("Recreating shortcuts ...")
    makeShortcuts.makeShortcuts(makeShortcuts.ALL_GROUPS, currentSystem, baseDir=standbyFileDest)

    logger.info("Finished synchronising standby directory")

# Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [\
      #choices=['onboard', 'config', 'updates', 'data']
      make_option("-i", "--info", \
        help="the information type to synchronise"),
      make_option("-a", "--application", action="store_true", \
        help="Only sync the application server settings."),
      make_option("-s", "--sync", action="store_true", \
        help="Sync the cycle state cache."),
      make_option("-d", "--database", action="store_true", \
        help="Only sync the database."),
        ]
    argumentsStr = "..."
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    syncApp = 1
    syncDb = 1
    if options.application and not options.database:
        syncDb = 0
    elif not options.application and options.database:
        syncApp = 0

    mstarpaths.loadMineStarConfig()
    if not ServerTools.onAppServer() or ServerTools.isStandbyDbRole():
        #logger.warn("syncStandbyInformation can only be run on the production application server")
        return

    minestar.logit("Running syncStandbyInformation with area: %s" % options.info)
    mutex = filemutex.Mutex("syncStandbyInformation", 60)
    try:
        try:
            mutex.lock()

            if syncApp:
                dir = mstarpaths.interpretPath("{MSTAR_STANDBY}")
                if dir is None or dir == "" or dir == "{MSTAR_STANDBY}":
                    logger.warning("MineStar standby directory is not defined - no configuration will be synchronised")
                elif not os.path.exists(dir):
                    logger.warning("MineStar standby directory %s is not valid - no configuration will be synchronised" % dir)
                    minestar.logit("MineStar standby directory %s is not valid - no configuration will be synchronised" % dir)
                else:
                    try:
                        syncStandbyDirectory(dir, options.info)
                    except:
                        import traceback
                        msg = "STANDBY ERROR: Cannot sync standby directory\n%s" % traceback.format_exc(sys.exc_info()[0])
                        logger.error(msg)
                        minestar.logit(msg)

            if syncDb:
                if ServerTools.getStandbyDatabaseServer() is None or ServerTools.getStandbyDatabaseServer() == "":
                    logger.warning("Current Configuration does not support the process. Please configured applicable standby server.")
                else:
                    try:
                        syncStandbyHistoricalDatabase()
                    except:
                        import traceback
                        msg = "STANDBY ERROR: Cannot sync standby historical database\n%s" % traceback.format_exc(sys.exc_info()[0])
                        logger.error(msg)
                        minestar.logit(msg)
                    try:
                        syncStandbyPitModelDatabase()
                    except:
                        import traceback
                        msg = "STANDBY ERROR: Cannot sync standby pit model database\n%s" % traceback.format_exc(sys.exc_info()[0])
                        logger.error(msg)
                        minestar.logit(msg)

        except filemutex.MutexError:
            logger.warn("syncStandbyInformation could not aquire lock - no sync possible this invocation")
            logger.warn("try checking if the snapshot folder exists in the following directory and remove")
            logger.warn("directory is: %s" % mutex.getFilename())            

    except SystemExit:
        mutex.release()
    finally:
        mutex.release()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
