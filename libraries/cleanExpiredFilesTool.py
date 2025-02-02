import minestar, mstarpaths, os, i18n, adminPrefixIfOld, sys, time, stat

logger = minestar.initApp()

DEFAULT_PATTERNS = ['*.log', '*.tmp', '*.txt', '*.xml', '*.ser', '*.dmp', '*.zip', '*.bat', '*.properties', 'tmp*exp']

standardDirs = {}

def __remove(filename):
    try:
        if minestar.isDirectory(filename):
            logger.info("Removing directory %s" % filename)
            os.rmdir(filename)
        else:
            logger.info("Removing file %s" % filename)
            os.remove(filename)
        return 1
    except OSError, ex:
        logger.warn("Failed to remove %s" % filename)
        return 0

def _deleteDirIfEmpty(dir):
    "If the directory is empty, remove it"
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
    for file in files:
        filename = dirName + os.sep + file
        if recursive and minestar.isDirectory(filename):
            _deleteMarkedForDeletion(filename, daysToDelete, recursive)
            count += _deleteDirIfEmpty(filename)
        elif file.startswith(prefix):
            statInfo = os.stat(filename)
            ageInSeconds = time.time() - statInfo[stat.ST_MTIME]
            if ageInSeconds > limitInSeconds:
                if not minestar.isDirectory(filename):
                    count += __remove(filename)
    return count

def _tidyDir(dirName, daysDelete, daysRetain, patterns=DEFAULT_PATTERNS, daysRetain2=9999, patterns2=None, recursive=0):
    "clean the expired files matching patterns in a directory"
    if not os.access(dirName, os.F_OK):
        logger.warn(i18n.translate(" Can't tidy %s  - directory not found") % (dirName))
        return (0,0)
    print "Tidying %s ..." % dirName    
    logger.info("Tidying %s ..." % dirName)
    deleted = _deleteMarkedForDeletion(dirName, daysDelete, recursive)
    marked = 0
    for pat in patterns:
        marked += adminPrefixIfOld.addPrefix(pat, dirName, daysRetain, recursive=recursive)

    # If a special set of patterns is defined, retain them for the matching period
    if patterns2 is not None:
        for pat in patterns2:
            marked += adminPrefixIfOld.addPrefix(pat, dirName, daysRetain2, recursive=recursive)
    return (deleted,marked)

def _tidy(mstarDir, daysDelete, daysRetain, patterns=DEFAULT_PATTERNS, daysRetain2=9999, patterns2=None, recursive=0):
    "clean the expired files matching patterns in a minestar named directory"
    dirName = standardDirs.get(mstarDir)
    return _tidyDir(dirName, daysDelete, daysRetain, patterns, daysRetain2, patterns2, recursive)

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
    _FCSRETAIN = "7"
    _FCSRETAINZIPS = "15"
    _FCSDELETE = "14"
    _OC_RETAIN = "2"
    _OC_DELETE = "2"
    _ADMINTIDY_RETAIN = "5"
    _ADMINTIDY_DELETE = "7"
    _CATPREVIEWFILE_RETAIN = "7"
    _CATPREVIEWFILE_DELETE = "14"

    totalDeleted = 0
    totalMarked = 0

    # Clean up the FieldCommsServer files
    fcsRetain = int(_FCSRETAIN)
    zipRetain = int(_FCSRETAINZIPS)
    fcsDelete = int(_FCSDELETE)
    (deleted,marked) = _tidy("{MSTAR_MESSAGES}", fcsDelete, fcsRetain, ['*.gwm'], zipRetain, ['*.zip'])
    totalDeleted += deleted
    totalMarked += marked

    # Clean up the admin, logs, temp and other areas
    daysRetain = int(_ADMINTIDY_RETAIN)
    daysDelete = int(_ADMINTIDY_DELETE)
    (deleted,marked) = _tidy("{MSTAR_TERRAIN_LOGS}", daysDelete, daysRetain)
    totalDeleted += deleted
    totalMarked += marked
    
    #clean up hprof files created in the oc folder
    ocRetain = int(_OC_RETAIN)
    ocDelete = int(_OC_DELETE)
    (deleted,marked) = _tidy("{MSTAR_TERRAIN_LOGS_OC}", ocRetain, ocDelete, ['*.hprof','*.txt'])
    totalDeleted += deleted
    totalMarked += marked
    
	#clean up .CAT files created in the "cat_minestar_file_repository\design\_TEMP_MINESTAR" folder
    ocRetain = int(_CATPREVIEWFILE_RETAIN)
    ocDelete = int(_CATPREVIEWFILE_DELETE)
    (deleted,marked) = _tidy("{MSTAR_TERRAIN_DESIGN_TEMP}", ocRetain, ocDelete, ['*.cat'])
    totalDeleted += deleted
    totalMarked += marked
    
    # Dump some statistics
    mesg = "cleanExpiredFiles completed: %d files/dirs deleted, %s files marked for deletion" % (totalDeleted,totalMarked)
    logger.info(mesg)

## Main Program ##

if __name__ == '__main__':
    MSTAR_SYSTEMS="c:/mstarFiles/systems"
    if len(sys.argv) > 0:
        MSTAR_SYSTEMS=sys.argv[1]
    MSTAR_SYSTEMS=MSTAR_SYSTEMS.replace("/", os.path.sep)
    SYSTEM_NAME="main"
    PROFILE_DIR=os.path.join(MSTAR_SYSTEMS, SYSTEM_NAME)
    DESIGN_TEMP_DIR = "cat_minestar_file_repository\design\_TEMP_MINESTAR"
    DESIGN_TEMP_DIR = DESIGN_TEMP_DIR.replace("/",os.path.sep);
	
    standardDirs["{MSTAR_MESSAGES}"] = os.path.join(PROFILE_DIR, "messages")
    standardDirs["{MSTAR_TERRAIN_LOGS}"] = os.path.join(PROFILE_DIR, "logs")
    standardDirs["{MSTAR_TERRAIN_LOGS_OC}"] = os.path.join(standardDirs.get("{MSTAR_TERRAIN_LOGS}"), "oc")
    standardDirs["{MSTAR_TERRAIN_DESIGN_TEMP}"] = os.path.join(PROFILE_DIR, DESIGN_TEMP_DIR)

    mstarpaths.config = { "MSTAR_LOGS" : standardDirs.get("{MSTAR_TERRAIN_LOGS_OC}") }
    cleanExpiredFiles()
