#  Copyright (c) 2020 Caterpillar

import ServerTools
import adminPrefixIfOld
import i18n
import mstarpaths
import os
import stat
import sys
import time

import minestar

logger = minestar.initApp()

DEFAULT_PATTERNS = ['*.log', '*.tmp', '*.csv', '*.txt', '*.xml', '*.ser', '*.dmp', '*.zip', '*.bat', '*.properties', '*.json', 'tmp*exp', '*-GC-*.log*', '*.sqlite']

def __remove(filename):
    try:
        if minestar.isDirectory(filename):
            logger.info("Removing directory %s" % filename)
            os.rmdir(filename)
        else:
            logger.info("Removing file %s" % filename)
            os.remove(filename)
        return 1
    except OSError:
        logger.warn("Failed to remove %s" % filename)
        return 0


def _deleteDirIfEmpty(dir):
    """If the directory is empty, remove it"""
    filesInDir = os.listdir(dir)
    if len(filesInDir) == 0:
        return __remove(dir)
    else:
        return 0


def _deleteMarkedForDeletion(dirName, daysToDelete, recursive=0, prefix=adminPrefixIfOld.MARKED_FOR_DELETION):
    """
    Delete files and directories which are marked for deletion as long as they are more than
    daysToDelete days old
    """
    count = 0
    if not os.access(dirName, os.W_OK):
        logger.warn("Can't access directory %s - skipping deleteMarkedForDeletion()" % dirName)
        return 0
    files = os.listdir(dirName)
    limitInSeconds = daysToDelete * 24 * 3600
    for f in files:
        filename = dirName + os.sep + f
        if recursive and minestar.isDirectory(filename):
            _deleteMarkedForDeletion(filename, daysToDelete, recursive)
            count += _deleteDirIfEmpty(filename)
        elif f.startswith(prefix):
            statInfo = os.stat(filename)
            ageInSeconds = time.time() - statInfo[stat.ST_MTIME]
            if ageInSeconds > limitInSeconds and not minestar.isDirectory(filename):
                count += __remove(filename)
    return count


def _tidyDir(dirName, daysDelete, daysRetain, patterns=DEFAULT_PATTERNS, daysRetain2=9999, patterns2=None, recursive=0, retainRecent=0):
    """Clean the expired files matching patterns in a directory"""
    if not os.access(dirName, os.F_OK):
        logger.warn(i18n.translate(" Can't tidy %s  - directory not found") % (dirName))
        return 0, 0
    logger.info("Tidying %s ..." % dirName)
    deleted = _deleteMarkedForDeletion(dirName, daysDelete, recursive)
    marked = 0
    for pat in patterns:
        if not retainRecent:
            marked += adminPrefixIfOld.addPrefix(pat, dirName, daysRetain, recursive=recursive)
        else:
            minNumFiles = int(mstarpaths.interpretVar("_MIN_FILES"))
            marked += adminPrefixIfOld.retainRecentAddPrefix(pat, dirName, minNumFiles, daysRetain, recursive=recursive)

    # If a special set of patterns is defined, retain them for the matching period
    if patterns2 is not None:
        for pat in patterns2:
            marked += adminPrefixIfOld.addPrefix(pat, dirName, daysRetain2, recursive=recursive)
    return deleted, marked


def _tidy(mstarDir, daysDelete, daysRetain, patterns=DEFAULT_PATTERNS, daysRetain2=9999, patterns2=None, recursive=0, retainRecent=0):
    "clean the expired files matching patterns in a minestar named directory"
    dirName = mstarpaths.interpretPath(mstarDir)
    return _tidyDir(dirName, daysDelete, daysRetain, patterns, daysRetain2, patterns2, recursive, retainRecent)


def _recursiveFileList(base, directory):
    result = []
    try:
        files = os.listdir(directory)
    except:
        logger.warn("Failed to list directory %s" % directory)
        return result
    for file in files:
        path = directory + os.sep + file
        if os.path.isdir(path):
            result = result + _recursiveFileList(base, path)
        else:
            relPath = path[len(base) + 1:]
            result.append(relPath)
    return result


def cleanExpiredFiles():
    totalDeleted = 0
    totalMarked = 0

    onServer = ServerTools.onServer()

    if onServer:
        # Clean up the FieldCommsServer files
        fcsRetain = int(mstarpaths.interpretVar("_FCSRETAIN"))
        zipRetain = int(mstarpaths.interpretVar("_FCSRETAINZIPS"))
        fcsDelete = int(mstarpaths.interpretVar("_FCSDELETE"))
        (deleted, marked) = _tidy("{MSTAR_MESSAGES}", fcsDelete, fcsRetain, ["*.gwm"], zipRetain, ["*.zip"])
        totalDeleted += deleted
        totalMarked += marked

    if onServer:
        # Clean up the database exports and SENT FTP files directory:
        dbRetain = int(mstarpaths.interpretVar("MSTAR_DBEXPORT_RETAIN"))
        dbDelete = int(mstarpaths.interpretVar("MSTAR_DBEXPORT_DELETE"))
        (deleted, marked) = _tidy("{MSTAR_DATA}", dbDelete, dbRetain)
        totalDeleted += deleted
        totalMarked += marked
        (deleted, marked) = _tidy("{MSTAR_DATA_BACKUPS}", dbDelete, dbRetain)
        totalDeleted += deleted
        totalMarked += marked
        # Clean up any standby snapshots on the standby server
        currentSystem = mstarpaths.interpretVar("MSTAR_SYSTEM")
        standbyDir = "{MSTAR_STANDBY}/%s/data/standby" % currentSystem
        (deleted, marked) = _tidy(standbyDir, dbDelete, dbRetain)
        totalDeleted += deleted
        totalMarked += marked
        (deleted, marked) = _tidy("{MSTAR_SENT}", dbDelete, dbRetain)
        totalDeleted += deleted
        totalMarked += marked

    if onServer:
        # Clean up out of date onboard files
        onboardRetain = int(mstarpaths.interpretVar("_ONBOARD_RETAIN"))
        onboardDelete = int(mstarpaths.interpretVar("_ONBOARD_DELETE"))
        (deleted, marked) = _tidy("{MSTAR_ONBOARD}/Minestar", onboardDelete, onboardRetain, patterns=["*.mwf"], recursive=1, retainRecent=1)
        totalDeleted += deleted
        totalMarked += marked

    if onServer:
        # Clean up out of date draw cards files
        drawCardRetain = int(mstarpaths.interpretVar("_DRAWCARD_RETAIN"))
        drawCardDelete = int(mstarpaths.interpretVar("_DRAWCARD_DELETE"))
        (deleted, marked) = _tidy("{MSTAR_DATA}/drawcards", drawCardDelete, drawCardRetain, patterns=["*.csv"], recursive=1)
        totalDeleted += deleted
        totalMarked += marked

    # Clean up the trace files
    traceDelete = int(mstarpaths.interpretVar("_TRACE_DELETE"))
    traceRetain = int(mstarpaths.interpretVar("_TRACE_RETAIN"))
    (deleted, marked) = _tidy("{MSTAR_TRACE}", traceDelete, traceRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Clean up the admin, logs, temp, data and other areas
    daysRetain = int(mstarpaths.interpretVar("_ADMINTIDY_RETAIN"))
    daysDelete = int(mstarpaths.interpretVar("_ADMINTIDY_DELETE"))
    for name in ["{MSTAR_ADMIN}", "{MSTAR_LOGS}", "{MSTAR_LOGS}/AssignmentRecorder", "{MSTAR_TEMP}","{MSTAR_DATA}"]:
        (deleted, marked) = _tidy(name, daysDelete, daysRetain)
        totalDeleted += deleted
        totalMarked += marked

    (deleted, marked) = _tidy("{MSTAR_LOGS}/audit", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    (deleted, marked) = _tidy("{MSTAR_LOGS}/audit-csv", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    (deleted, marked) = _tidy("{MSTAR_LOGS}/iAssignment", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    (deleted, marked) = _tidy("{MSTAR_LOGS}/UIFacade", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    (deleted, marked) = _tidy("{MSTAR_LOGS}/config", daysDelete, daysRetain, daysRetain2=daysRetain, patterns2=['*.2004*', '*.2005*'], recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Clean up the onboard snapshot files
    (deleted, marked) = _tidy("{MSTAR_LOGS}/onboardsnapshot", daysDelete, daysRetain, patterns=["*.*"], recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Clean up the mcui snapshot files
    (deleted, marked) = _tidy("{MSTAR_LOGS}/mcui_snapshots", daysDelete, daysRetain, patterns=["*.*"], recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Cleaning up the metrics log files
    (deleted, marked) = _tidy("{MSTAR_LOGS}/metrics", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Cleaning up the generated performance log files
    (deleted, marked) = _tidy("{MSTAR_LOGS}/performance", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Clean up the planner state files
    (deleted, marked) = _tidy("{MSTAR_LOGS}/planner", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Clean up the v2x incident data zip files
    (deleted, marked) = _tidy("{MSTAR_DATA}/incidentData", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Clean up the extension data files
    (deleted, marked) = _tidy("{MSTAR_DATA}/ext-data", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Cleaning up the generated postgrace log files
    (deleted, marked) = _tidy("{MSTAR_DATA}/postgis/pg_log", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Clean up the cycle activity archive files
    (deleted, marked) = _tidy("{MSTAR_DATA}/cycle-activities", daysDelete, daysRetain, recursive=1)
    totalDeleted += deleted
    totalMarked += marked

    # Removing of filess from outgoing folder as defined in MSTAR-8716
    ftpMachine = mstarpaths.interpretVar("_FTPSERVER")
    if ftpMachine is None or ftpMachine == "" or ftpMachine == 'mstar1':
        (deleted, marked) = _tidy("{MSTAR_OUTGOING}", daysDelete, daysRetain)
        totalDeleted += deleted
        totalMarked += marked

    # Dump some statistics
    mesg = "cleanExpiredFiles completed: %d files/dirs deleted, %s files marked for deletion" % (totalDeleted, totalMarked)
    logger.info(mesg)
    minestar.logit(mesg)


## Main Program ##

if __name__ == '__main__':
    import mstarrun

    mstarrun.loadSystem(sys.argv[1:])
    cleanExpiredFiles()
