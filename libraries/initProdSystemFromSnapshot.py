__version__ = "$Revision: 1.6 $"

import minestar
logger = minestar.initApp()
import sys, os,fnmatch
import mstarpaths, mstarrun, datastore, ServerTools, exportData, snapshotSystem, unzip
import time
def restoreDatabases(snapshotPath):
    """
    Restore a production model database from a snapshot file.
    """
    # Establish the target directory for the system we're restoring and ensure it exists
    # Unpack the zip file
    logger.info("Unpacking snapshot file ...")
    absSnapshotPath = os.path.abspath(snapshotPath)
    WORKING_DIR = mstarpaths.interpretPath("{MSTAR_SYSTEMS}") + os.sep + mstarpaths.interpretPath("{MSTAR_SYSTEM}" + os.sep + "tmp" + os.sep + "standby")
    # if the "tmp/standby" directory exists delete it:
    if minestar.isDirectory(WORKING_DIR):
        try:
            minestar.rmdir(WORKING_DIR)
        except OSError, err:
            logger.warning("Directory %s cannot be removed - will be overwritten!", WORKING_DIR)
    try:
        os.mkdir(WORKING_DIR)
    except OSError, err:
        logger.error("Failed to create standby snapshot directory %s: %s", WORKING_DIR, err)
        # return None

    logger.info("Unzipping the snapShot file %s at location %s", absSnapshotPath, WORKING_DIR)
    try:
        unzip.unzip(absSnapshotPath, WORKING_DIR)
    except IOError:
        logger.error('Could not decompress the file: %s\n' % absSnapshotPath)

    (mode, customerCode, computerName, restoreSystem, timestamp) = snapshotSystem.unpackSnapshotFilename(absSnapshotPath)
    dbFileDir = os.path.sep.join([WORKING_DIR, "tmp"])
    modelDbFile = os.path.sep.join([dbFileDir, exportData.buildExportFilename("_MODELDB",customerCode,timestamp)])
    pitModelDbFile = os.path.sep.join([dbFileDir, exportData.buildExportFilename("_PITMODELDB",customerCode,timestamp)])

    if not os.access(modelDbFile, os.F_OK):
        logger.error("Cannot restore databases because the snapshot does not contain the model database file %s", modelDbFile)
        return
    if not os.access(pitModelDbFile, os.F_OK):
        logger.error("Cannot restore databases because the snapshot does not contain the pit model database file %s", pitModelDbFile)
        return

    modelDb = datastore.getDataStore("_MODELDB")
    pitModelDb = datastore.getDataStore("_PITMODELDB")
    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject()
    if(dbobject.getDBString()=="sqlserver" and not ServerTools.onDbServer()):
        #Copy files to db system temp directory to import
        modelDbFile = copyDbFilesToTempDir(dbFileDir,modelDbFile)
        modelDb.purgeRecycleBin()
        modelDb.reimport(modelDbFile,modelDb)
        if os.access(modelDbFile, os.F_OK):
            os.remove(modelDbFile)
        pitModelDbFile = copyDbFilesToTempDir(dbFileDir,pitModelDbFile)
        pitModelDb.purgeRecycleBin()
        pitModelDb.reimport(pitModelDbFile,pitModelDb)
        if os.access(pitModelDbFile, os.F_OK):
            os.remove(pitModelDbFile)
    else:
        modelDb.purgeRecycleBin()
        modelDb.reimport(modelDbFile,modelDb)
        pitModelDb.purgeRecycleBin()
        pitModelDb.reimport(pitModelDbFile,pitModelDb)

def copyDbFilesToTempDir(dbFileDir,dbFile):
    # When importing to remote db server it is required to have bak files to be placed in shared path.
    tmpExportDir =  mstarpaths.interpretFormat("{TempDBDirectory}")
    tmpExportDir = mstarpaths.getUncPathOfMapDrive(tmpExportDir)
    if tmpExportDir is None or tmpExportDir == mstarpaths.interpretPath("{MSTAR_DATA}"):
        logger.error("Please specify shared path in Database system temp directory.")
        minestar.exit(1)
    minestar.copy(dbFile,tmpExportDir,True)
    dbFile = dbFile.replace(dbFileDir,tmpExportDir)
    return dbFile

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    if not ServerTools.onAppServer():
        minestar.abort("This script can only be run from the application server")

    # Process options and check usage
    optionDefns = [
      make_option("-a", "--application", action="store_true", \
        help="Only restore the application server settings."),
      make_option("-d", "--database", action="store_true", \
        help="Only restore the database."),
      make_option("-e", "--essential", action="store_true", \
        help="Only migrate essential records - cycles, delays etc."),
      ]
    argumentsStr = "snapshotFile"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    mstarpaths.loadMineStarConfig()

    # Check that the file exists and is readable
    snapshotFile = args[0]
    if not os.access(snapshotFile, os.F_OK):
        minestar.abort("Snapshot file %s does not exist" % snapshotFile)
    elif not os.access(snapshotFile, os.R_OK):
        minestar.abort("Snapshot file %s is not readable" % snapshotFile)

    restoreApp = 1
    restoreDb = 1
    operation = "restore MineStar Application Server settings and migrate data from standby to production."
    if options.application and not options.database:
        restoreDb = 0
        operation = "restore MineStar Application Server settings from standby."
    elif not options.application and options.database:
        restoreApp = 0
        operation = "migrate data from standby to production."

    msg = "About to: " + operation
    mstarrun.run(["confirmYesNoPanel",msg,"initProdSystemFromSnapshot : Confirmation Alert!!!","initProdSysConfirmation.txt"])
    time.sleep( 3 )
    response = minestar.readFile(mstarpaths.interpretPath("{MSTAR_TEMP}/initProdSysConfirmation.txt"))
    if response != '0':
        minestar.exit()

    currDir = os.getcwd()
    if restoreApp:
        #first restore the configuration
        logger.info("Initialising production system from standby snapshot")
        mstarrun.run(["initSystemFromSnapshot", snapshotFile])

    os.chdir(currDir)
    if restoreDb:
        # now restore the data from the standby snapshot
        mstarrun.run(["switchActiveDatabase", "-r", "PRODUCTION"])
        mstarpaths.loadMineStarConfig(forceReload=1)
        restoreDatabases(snapshotFile)

        # now restore the remaining historical data
        migrateArgs = ["migrateStandbyDataToProduction"]
        if options.essential:
            migrateArgs.append("-e")
        mstarrun.run(migrateArgs)
    os.chdir(currDir)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()

