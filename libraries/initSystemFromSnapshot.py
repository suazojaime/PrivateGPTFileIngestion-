__version__ = "$Revision: 1.15 $"

import sys, os, zipfile, string, fnmatch
import minestar, mstarpaths, mstaroverrides, mstarrun, makeShortcuts, snapshotSystem, exportData, filemutex, unzip

logger = minestar.initApp()
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

def removeRecoveryFiles():
    """
    Removes any *-RecoveryFile.dat from \mstarFiles\systems\<system>\data
    """
    mstarData = mstarpaths.interpretPath("{MSTAR_DATA}")
    recoveryFiles = fnmatch.filter(os.listdir(mstarData), "*-RecoveryFile.dat")
    for file in recoveryFiles:
        path = os.path.sep.join([mstarData, file])
        os.remove(path)

def restoreSystem(snapshotPath, options, targetSystem=None):
    """
    Restore a system from a snapshot file. If targetSystem is specified, that name will be used as the
    new system name, otherwise the system name is extracted from the zip file.
    """
    # Get the target system and display info about what we're doing
    snapshotBasename = os.path.split(snapshotPath)[1]
    (mode, customerCode, computerName, restoreSystem, timestamp) = snapshotSystem.unpackSnapshotFilename(snapshotBasename)
    if targetSystem is None:
        targetSystem = restoreSystem
    logger.info("Restoring system %s from snapshot file %s", targetSystem, snapshotPath)

    # Establish the target directory for the system we're restoring and ensure it exists
    logger.info("Creating directory for system ...")
    restoreDir = _createDirForSystem(targetSystem)
    if restoreDir is None:
        minestar.abort("Unable to proceed as system directory creation failed")

    # Unpack the zip file
    logger.info("Unpacking snapshot file ...")
    absSnapshotPath = os.path.abspath(snapshotPath)
    WORKING_DIR = mstarpaths.interpretPath("{MSTAR_SYSTEMS}") + os.sep + mstarpaths.interpretPath("{MSTAR_SYSTEM}")
    logger.info("Unzipping the snapShot file %s at location %s", absSnapshotPath, WORKING_DIR)
    try:
        unzip.unzip(absSnapshotPath, WORKING_DIR)
    except IOError:
        logger.error('Could not decompress the file: %s\n' % absSnapshotPath)

    #remove the _system dir form the snapshot as it is not needed on the new system
    minestar.rmdir(WORKING_DIR + os.sep + "_system")

    # As links on the original system may not work here, rename the existing shortcuts directory
    # out of the way and create new ones suitable for this computer.
    logger.info("Moving restored shortcuts out of the way ...")
    orgShortcuts = restoreDir + os.sep + "shortcuts"
    restoredShortcuts = restoreDir + os.sep + "shortcuts.original"
    if minestar.isDirectory(restoredShortcuts):
        minestar.rmdir(restoredShortcuts)
    try:
        os.rename(orgShortcuts, restoredShortcuts)
    except:
        logger.warn("Failed to move restored shortcuts out of the way - shortcuts from snapshot will be lost")
    logger.info("Recreating shortcuts ...")
    makeShortcuts.makeShortcuts(makeShortcuts.ALL_GROUPS, targetSystem)

    # Remove any Cycle Recovery Files from MSTAR_DATA, if the '-remove' option is specified:
    if options.remove:
        logger.info("Removing cycle recovery files ...")
        removeRecoveryFiles()

    # Output a summary of how things went
    logger.info("System configuration %s successfully restored", targetSystem)

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [
      make_option("-r", "--remove", action="store_true", \
        help="Remove (and do not use) Cycle Cache Recovery Files."),
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

    mutex = filemutex.Mutex("syncStandbyInformation", 60)
    try:
        try:
            mutex.lock()
            # Load the MineStar configs and restore the system
            restoreSystem(snapshotFile, options)

        except filemutex.MutexError:
            logger.warn("initSystemFromSnapshot could not aquire lock")
            logger.warn("try checking if the snapshot folder exists in the following directory and remove")
            logger.warn("directory is: %s" % mutex.getFilename())            
            minestar.exit(1)

    except SystemExit:
        mutex.release()
    finally:
        mutex.release()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
