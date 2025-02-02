__version__ = "$Revision: 1.21 $"

import minestar
logger = minestar.initApp()
import sys, os, zipfile, string, fnmatch, logging
import mstarpaths, mstaroverrides, mstarrun, makeShortcuts, snapshotSystem, exportData, datastore
import ServerTools, FailoverTools, filemutex, unzip


overrides = []

def _createDirForSystem(system):
    """
    Create a directory for a system and return the directory name.
    If the directory already exists, a warning is output.
    If the directory cannot be created, it prints an error and returns None
    """
    dir = mstarpaths.interpretPath("{MSTAR_SYSTEMS}") + os.sep + system
    if minestar.isDirectory(dir):
        logger.warning("Directory %s already exists - system will be overwritten!", dir)
    else:
        try:
            os.mkdir(dir)
        except OSError, err:
            logger.error("Failed to create system directory %s: %s", dir, err)
            return None
    return dir


def _formatProbeResult(dbName, errorCode):
    #import checkDataStores
    message = errorCode
    #if checkDataStores.RESPONSE_MEANINGS.has_key(errorCode):
    #    message = "%s" % checkDataStores.RESPONSE_MEANINGS[errorCode]
    return "%s database probe result: %s" % (dbName, message)


def _restoreDatabases(restoreDir, targetSystem, customerCode, timestamp, options):
    """restore the databases in the targetSystem using files unpacked from a snapshot"""
    # Check that we're running in the system being imported
    thisSystem = mstarpaths.interpretVar("MSTAR_SYSTEM")

    success = 1
    currDir = os.getcwd()
    logger.info("Restoring the model database ...")
    modelDbFile = os.path.sep.join(
        [restoreDir, "tmp", exportData.buildExportFilename("_MODELDB", customerCode, timestamp)])
    #logger.info("_restoreDatabases: modelDbFile='%s'" % modelDbFile)
    pitModelDbFile = os.path.sep.join(
        [restoreDir, "tmp", exportData.buildExportFilename("_PITMODELDB", customerCode, timestamp)])

    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject()
    dbname = dbobject.getDBString();
    if(dbname=="sqlserver"):
        mstarrun.run("checkDataStores STANDBY._MODELDB refreshUser")
        mstarrun.run("checkDataStores STANDBY._PITMODELDB refreshUser")

    modelDb = datastore.getDataStore("_MODELDB", "STANDBY")
    histDb = datastore.getDataStore("_HISTORICALDB", "STANDBY")
    summDb = datastore.getDataStore("_SUMMARYDB", "STANDBY")
    pitModelDb = datastore.getDataStore("_PITMODELDB", "STANDBY")

    modelProbeResult = modelDb.probe()
    histProbeResult = histDb.probe()
    summProbeResult = summDb.probe()
    pitModelProbeResult = pitModelDb.probe()

    if (modelDb.probe() != "OK" or histDb.probe() != "OK" or summDb.probe() != "OK" or pitModelDb.probe() != "OK"):
        msg = "Cannot restore databases because the standby database instances are not ready"
        logger.error(msg)
        minestar.logit(msg)
        if( modelProbeResult != "OK" ):
            msg = _formatProbeResult("Model", modelProbeResult)
            logger.error(msg)
            minestar.logit(msg)
        if( histProbeResult != "OK" ):
            msg = _formatProbeResult("Historical", histProbeResult)
            logger.error(msg)
            minestar.logit(msg)
        if( summProbeResult != "OK" ):
            msg = _formatProbeResult("Summary", summProbeResult)
            logger.error(msg)
            minestar.logit(msg)
        if( pitModelProbeResult != "OK" ):
            msg = _formatProbeResult("PitModel", pitModelProbeResult)
            logger.error(msg)
            minestar.logit(msg)
        success = 0
    elif not os.access(modelDbFile, os.F_OK):
        logger.error("Cannot restore databases because the snapshot does not contain the model database file %s",
            modelDbFile)
        success = 0
    elif not os.access(pitModelDbFile, os.F_OK):
        logger.error("Cannot restore databases because the snapshot does not contain the pitmodel database file %s",
            pitModelDbFile)
        success = 0
    else:
        modelDb.purgeRecycleBin()
        pitModelDb.purgeRecycleBin()
        #Restore the model db
        if options.auto:
            modelDb.reimport(modelDbFile,modelDb,'true')
            pitModelDb.reimport(pitModelDbFile,pitModelDb,'true')
            #delete exisiting historical standby data (ie delays and cycles)
            FailoverTools.deleteHistoricalStandbyData()
        else:
            # Note: we execute this in a subprocess so that the latest configuration is used
            mstarrun.run(['replaceDataStoresWithModel', "-s", "-r", modelDbFile, pitModelDbFile])

        #Only import historical data if we expect there will be no incompatibiliities
        if not options.remove:
            # Import failover data into the HISTDB schema
            histUser = histDb.user
            histPass = histDb.password
            histService = histDb.instanceName
            logger.info("Remove the Delay and Cycle Data from Standby Server")
            # call dbdataman with the appropriate script:
            exportSpecFileName = mstarpaths.interpretPath("{MSTAR_TEMP}/dbdataman_delete_essential_entities.txt")
            print 'Executing dbdataman to deleting CYCLES and DELAYS'
            histDb.dbdataman("-c", exportSpecFileName)
            os.chdir(currDir)

            logger.info("Restoring the essential historical data to %s@%s ...", histUser, histService)
            importDir = os.path.sep.join([restoreDir, "data", "failover", "dbdataman_export"])
            #cmd = ["importExportedData", "-d", "_HISTORICALDB", "-r", "STANDBY", "-i", importDir]
            #logger.info("  command is %s" %cmd)
            mstarrun.run(["importExportedData", "-d", "_HISTORICALDB", "-r", "STANDBY", "-i", importDir])
            #logger.info("Finished restoring the essential historical data")
            FailoverTools.updateNextOid(modelDb, histDb)

        #Ensure we have no bad data
        logger.info("Running consistency checker ...")
        mstarrun.run(['consistencychecker', "-c"])
        logger.info("Finished running consistency checker")

        # Reinitialise the summaries database
        logger.info("Reinitializing the summaries database ...")
        # get the "summary" datastore URL:
        import databaseDifferentiator

        dbobject = databaseDifferentiator.returndbObject()
        summDbFile1 = os.path.sep.join(
            [restoreDir, "data", "failover", "_SUMMARYDB_DIMENSIONS" + dbobject.getdumpfileExt()])
        summDbFile2 = os.path.sep.join(
            [restoreDir, "data", "failover", "_SUMMARYDB_EMPTY_FACT" + dbobject.getdumpfileExt()])
        #
        dbname = dbobject.getDBString();
        if(dbname=="sqlserver"):
            summDbFilesqlserver= os.path.sep.join([restoreDir, "data", "failover"]);
            if os.path.exists(summDbFilesqlserver):
                mstarrun.run(["importExportedData", "-d", "_SUMMARYDB", "-r", "STANDBY", "-i", summDbFilesqlserver])
                dbobject.refreshUser(summDb,'true')
                dbobject.refreshUser(modelDb,'true')
                dbobject.refreshUser(histDb,'true')
                dbobject.refreshUser(pitModelDb,'true')
        else:
            if os.path.exists(summDbFile1) and os.path.exists(summDbFile2):
                # first, drop any schema objects:
                summDb.dropAll()
                summDb.imp(summDbFile1)
                summDb.imp(summDbFile2)
        mstarrun.run(['makeDataStores', "-standby", "-db=summary", "all"])
        os.chdir(currDir)
    return success

    # call dbdataman with the appropriate script:
    histDb.dbdataman("-c", exportSpecFileName)
    os.chdir(currDir)


def removeRecoveryFiles():
    """
    Removes any *-RecoveryFile.dat from \mstarFiles\systems\<system>\data
    """
    mstarData = mstarpaths.interpretPath("{MSTAR_DATA}")
    recoveryFiles = fnmatch.filter(os.listdir(mstarData), "*-RecoveryFile.dat")
    for file in recoveryFiles:
        path = os.path.sep.join([mstarData, file])
        os.remove(path)


def restoreStandbyDb(snapshotPath, options, targetSystem=None):
    """
    Restore a system from a snapshot file. If targetSystem is specified, that name will be used as the
    new system name, otherwise the system name is extracted from the zip file.
    """
    # Get the target system and display info about what we're doing
    snapshotBasename = os.path.split(snapshotPath)[1]
    (mode, customerCode, computerName, restoreSystem, timestamp) = snapshotSystem.unpackSnapshotFilename(
        snapshotBasename)
    if targetSystem is None:
        targetSystem = restoreSystem
    msg = "Restoring Standby Databases %s from snapshot file %s" % (targetSystem, snapshotPath)
    logger.info(msg)
    minestar.logit(msg)

    # Establish the target directory for the system we're restoring and ensure it exists
    # Unpack the zip file
    logger.info("Unpacking snapshot file ...")
    absSnapshotPath = os.path.abspath(snapshotPath)
    WORKING_DIR = mstarpaths.interpretPath("{MSTAR_SYSTEMS}") + os.sep + mstarpaths.interpretPath("{MSTAR_SYSTEM}" + os.sep + "tmp" + os.sep + "standby")
    #logger.info("working dir is '%s'" % WORKING_DIR)
    # if the "tmp/standby" directory exists delete it:
    if minestar.isDirectory(WORKING_DIR):
        logger.warning("Directory %s already exists - will be re-created!", WORKING_DIR)
        try:
            minestar.rmdir(WORKING_DIR)
        except OSError, err:
            logger.warning("Directory %s cannot be removed - will be overwritten!", WORKING_DIR)
    try:
        os.mkdir(WORKING_DIR)
    except OSError, err:
        logger.error("Failed to create standby snapshot directory %s: %s", WORKING_DIR, err)
        # return None

    # Remove any Cycle Recovery Files from MSTAR_DATA, if the '-remove' option is specified:
    if options.remove:
        logger.info("Removing cycle recovery files ...")
        removeRecoveryFiles()

    os.chdir(WORKING_DIR)
    logger.info("Unzipping the snapShot file %s at location %s", absSnapshotPath, WORKING_DIR)
    try:
        unzip.unzip(absSnapshotPath, WORKING_DIR)
    except IOError:
        logger.error('Could not decompress the file: %s\n' % absSnapshotPath)


# Configure the Standby databases
    dbRestorationSucceeded = _restoreDatabases(WORKING_DIR, targetSystem, customerCode, timestamp, options)

    # Output a summary of how things went
    status = "SUCCESS"
    if not dbRestorationSucceeded:
        status = "FAILED"

    msg = "Standby databases %s restore finished with status: %s" % (targetSystem, status)
    logger.info(msg)
    minestar.logit(msg)

def findMostRecentSnapshotFile(dir):
    if not os.path.isdir(dir):
        return None
    snapshotFile = None
    snapshotFiles = fnmatch.filter(os.listdir(dir), "Snap_STANDBY*.zip")
    mostRecent = "00000000"
    for file in snapshotFiles:
        (mode, customerCode, computerName, restoreSystem, timestamp) = snapshotSystem.unpackSnapshotFilename(file)
        thisComputer = ServerTools.getCurrentServer().upper()
        computerName = computerName.upper()
        if timestamp > mostRecent: # and not ServerTools.isAppServer(computerName) and not computerName==thisComputer:
            snapshotFile = os.path.sep.join([dir, file])
            mostRecent = timestamp
    return snapshotFile

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [
        make_option("-r", "--remove", action="store_true",\
            help="Remove (and do not use) Cycle Cache Recovery Files."),
        make_option("-a", "--auto", action="store_true",\
            help="Use when invoked from scheduled task. Does not drop historical database."),
        ]
    argumentsStr = "..."
    (options, args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Unless force mode is enabled, check this is the standby server
    mstarpaths.loadMineStarConfig()

    minestar.logit("Running initStandbyDbFromSnapshot. Auto option is %s" % options.auto)
    # Check that the file exists and is readable
    snapshotFile = None
    if len(args) > 0:
        snapshotFile = args[0]
    if snapshotFile is None:
        if not options.auto:
            minestar.abort("Snapshot file was not specified")
        else:
            if ServerTools.getCurrentDatabaseServer() == ServerTools.getStandbyDatabaseServer():
                minestar.abort(
                    "Auto initStandbyDbFromSnapshot can only be run if standby server is not being used for production")
            if not ServerTools.onServer() and not ServerTools.getCurrentServer() in ServerTools.getAllowedDatabaseHosts():
                minestar.abort(
                    "Auto initStandbyDbFromSnapshot can only be run on a server %s" % ServerTools.getAllowedDatabaseHosts())
                #we need to get the snapshot file from the backups dir
            dataDir = mstarpaths.interpretPath("{MSTAR_DATA}/standby")
            snapshotFile = findMostRecentSnapshotFile(dataDir)
            if snapshotFile is None:
                backupsDir = mstarpaths.interpretPath("{MSTAR_DATA_BACKUPS}")
                snapshotFile = findMostRecentSnapshotFile(backupsDir)
            if snapshotFile is not None:
                logger.info("No snapshot file specified - using most recent copy %s" % snapshotFile)
            else:
                minestar.logit("No valid snapshot files found to unpack")
                minestar.abort("No valid snapshot files found to unpack")
        #if not os.access(snapshotFile, os.F_OK):
    #    minestar.abort("Snapshot file %s does not exist" % snapshotFile)
    #elif not os.access(snapshotFile, os.R_OK):
    #    minestar.abort("Snapshot file %s is not readable" % snapshotFile)

    mutex = filemutex.Mutex("syncStandbyDatabase", 60)
    try:
        try:
            mutex.lock()
            # Load the MineStar configs and restore the system
            #logger.info("Restoring using snapshotFile %s and options %s" % (snapshotFile,options))
            if not ServerTools.isStandbyDbRole():
                restoreStandbyDb(snapshotFile, options)
            else:
                minestar.logit("Current DataBase role is STANDDBY. Hence, skipping the STANDBY DataBase update.")

        except filemutex.MutexError:
            logger.warn("syncStandbyInformation could not aquire lock - no sync possible this invocation")
            logger.warn("Try checking if the following directory already exists and if so, remove it.")
            logger.warn("Directory is: %s" % mutex.getFilename())
            minestar.exit(1)

    except SystemExit:
        try:
            mutex.release()
        except filemutex.MutexError:
            logger.info("Ignoring mutex release exception")
    finally:
        try:
            mutex.release()
        except filemutex.MutexError:
            logger.info("Ignoring mutex release exception")

    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()

