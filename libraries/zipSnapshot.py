#  Copyright (c) 2022 Caterpillar

import datetime
import os
import re
import stat
import sys
import time
import traceback
import zipfile

import ServerTools
import adminPrefixIfOld
import minestar
import mstarpaths

logger = minestar.initApp()

DIR_MAPPINGS = {
    '_system':          "{MSTAR_SYSTEM_HOME}",
    'config':          "{MSTAR_CONFIG}",
    'shortcuts':       "{MSTAR_SYSTEM_HOME}/shortcuts",
    'logs':            "{MSTAR_LOGS}",
    'additional_logs': "{MSTAR_ADD_LOGS}",
    'messages':        "{MSTAR_MESSAGES}",
    'trace':           "{MSTAR_TRACE}",
    'onboard':         "{MSTAR_ONBOARD}",
    'updates':         "{MSTAR_UPDATES}",
    'tmp':             "{MSTAR_TEMP}",
    'dxf':             "{MSTAR_CONFIG}/explorer/dxf",
    }

DXF_DIR = {
    'dxf': "{MSTAR_CONFIG}/explorer/dxf",
}

EXCLUDE_DIRS = {
    'data':      "{MSTAR_DATA}",
    'onboardflash': "{MSTAR_ONBOARD}/flash",
    'builds': "{MSTAR_UPDATES}/.*",
    'fusiondipper': "{MSTAR_DATA}/ext-data/fusion-dipper",
    }

FLAT_DIRS = [
    'tmp',
    '_system',
    ]

RECURSE_STD = [
    'config',
    'shortcuts',
    'logs',
    'additional_logs',
    'messages',
    'trace',
    ]

RECURSE_LIMITED = [
    'config',
    'shortcuts',
    ]

# Directories to only include recent files from
LIMITED_LOOKBACK = ['tmp', 'logs', 'additional_logs', 'messages', 'trace']

DEFAULT_FILE_READ_CHUNKS_KB = 100 * 1024

# Process the data for log entry time stamp looking for the format Jul 01 10:18:55
timeRegex = re.compile(r'\d{2}:\d{2}:\d{2}')     # HH:mm:ss
pathRegex = re.compile(r'_\d{8}.log')            # YYYYMMMDDD

logDateRegex = re.compile(r'[A-Z]\w{2}\s+\d{2}\s+')    # e.g. Jul 08
logDateFormat = "%b %d %Y %H:%M:%S"                    # e.g. Jul 08 2016 14:25:54

geoServerDateRegex = re.compile(r'\d{2}\s+[A-Z]\w{2}\s+') # e.g. 08 Jul
geoServerDateFormat = "%d %b %Y %H:%M:%S"                 # e.g. 08 Jul 14:25:54

perfLogDateRegex = re.compile(r'\d{4}-\d{2}-\d{2}\s+') # e.g. 2023-01-10
perfLogDateFormat = "%Y-%m-%d %H:%M:%S"              # e.g. 2023-01-10 14:25:54

def getDateFromFilename(filename):
    # Get required date information from the file name.
    dateStartIndex = filename.rfind('_') + 1
    dateEndIndex = filename.rfind('.')
    fileDate = datetime.datetime.strptime(filename[dateStartIndex:dateEndIndex], "%Y%m%d")
    if fileDate is None:
        fileDate = datetime.datetime.now()

    return fileDate


def findLastLogEntry(filename):
    # example log file "C:\\mstarFiles\\systems\\main\\logs\\MineTracking_Service_MN26C001172349_20160701.log"
    fileDate = getDateFromFilename(filename)

    dateRegex = logDateRegex
    dateFormat = logDateFormat

    if "GeoServer" in filename:
        # timestamp format is different in the GeoServer logs.
        dateRegex = geoServerDateRegex
        dateFormat = geoServerDateFormat
    elif "_perf_" in filename:
        # timestamp format is different in the perf logs.
        dateRegex = perfLogDateRegex
        dateFormat = perfLogDateFormat

    # Read the last line in the log file:
    with open(filename, 'rb') as f:
        try:  # catch OSError in case of a one line file
            fileSize = len(f.readlines())
            if(fileSize <= 1):
                return None
            else:
                f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
        except OSError:
            f.seek(0)
        last_line = f.readline().decode().strip()

        try:
            timestamp = findTimeStamp(filename, last_line, dateRegex, dateFormat, fileDate)
            logger.info("File %s has last line log timestamp: %s ..." % (filename, datetime.datetime.fromtimestamp(timestamp)))
            return timestamp
        except Exception:
            logger.info("File %s has no timestamp on the last line" % filename)
            return None

def findTimeStamp(filename, line, dateRegex, dateFormat, fileDate):
    d = dateRegex.search(line)
    t = timeRegex.search(line)

    # we need both date and time so process the next line if not found yet
    if d is None or t is None:
        return None

    date = d.group() + " " + str(fileDate.year) + " " + t.group()
    if "_perf_" in filename:
        date = d.group() + t.group()

    processedDate = datetime.datetime.strptime(date.strip(), dateFormat)

    # Check the year hasn't rolled over and if so update the date accordingly
    if "_perf_" not in filename and processedDate.month == 1 and fileDate.month == 12:
        date = d.group() + " " + str(fileDate.year + 1) + " " + t.group()
        processedDate = datetime.datetime.strptime(date.strip(), dateFormat)

    modifiedTime = time.mktime(processedDate.timetuple())
    if modifiedTime:
        return modifiedTime
    return None


def fileInHorizon(path, horizonTime):
    """returns true if path has been modified since horizonTime"""
    try:
        if horizonTime == 0:
            return 1

        modifiedTime = os.stat(path)[stat.ST_MTIME]
        inHorizon = modifiedTime >= horizonTime
        if not inHorizon and pathRegex.search(path) is not None:
            # Tanuki keeps the file open and the modified timestamp sometimes doesn't update until the file is closed
            # causing files to be skipped during a snapshot. Process only service log files in chunks of 100Kb in
            # reverse until a timestamp is found
            lastLogTime = findLastLogEntry(path)
            if lastLogTime is not None:
                modifiedTime = lastLogTime

        # modifiedTimeStr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modifiedTime))

        inHorizon = modifiedTime >= horizonTime
        # if inHorizon:
        #     logger.info("Including file %s as last modified time %s is after horizon" % (path, modifiedTimeStr))
        # else:
        #     logger.info("Skipping file %s as last modified time %s is before horizon" % (path, modifiedTimeStr))
        return inHorizon
    except Exception as e:
        logger.error("Skipping %s due to %s" % (path, str(e)))
        return False


def isForbiddenInSnapshots(name):
    return (name.startswith("Snap_") and name.endswith(".zip")) \
           or (name.startswith("assignmentContext-")) \
           or (name.startswith("small") and name.endswith(".log"))


def recursiveFileList(base, directory, horizonTime=0, includeDXF=0):
    """
    Get the list of filenames in a directory, including subdirectories.
    If horizonTime is non-zero, only files modified after that time are returned.
    """
    result = []
    excludedareas = EXCLUDE_DIRS
    if includeDXF == 0:
        excludedareas.update(DXF_DIR)
    for exclarea in excludedareas.keys():
        excldir = mstarpaths.interpretPath(excludedareas[exclarea])
        if excldir == directory or len(base) <= len(excldir) and (re.compile(excldir).match(directory.rstrip(os.sep)) is not None):
            logger.info("Excluding directory %s ..." % directory)
            return result

    try:
        files = os.listdir(directory)
    except:
        logger.warn("Failed to list directory %s: %s" % (directory, traceback.format_exc(sys.exc_info()[0])))
        return result
    for file in files:
        if file.startswith(adminPrefixIfOld.MARKED_FOR_DELETION):
            continue
        if isForbiddenInSnapshots(file):
            logger.info("%s does not go in snapshots" % file)
            continue
        path = directory + os.sep + file
        if os.path.isdir(path):
            result = result + recursiveFileList(base, path, horizonTime, includeDXF)
        else:
            if fileInHorizon(path, horizonTime):
                relPath = path[len(base) + 1:]
                result.append(relPath)
    return result


def flatFileList(directory, horizonTime=0):
    """
    Get the list of filenames in a directory, excluding subdirectories.
    If horizonTime is non-zero, only files modified after that time are returned.
    """
    result = []
    try:
        files = os.listdir(directory)
    except:
        logger.warn("Failed to list directory %s: %s" % (directory, traceback.format_exc(sys.exc_info()[0])))
        return result
    for file in files:
        if file.startswith(adminPrefixIfOld.MARKED_FOR_DELETION):
            continue
        path = directory + os.sep + file
        if not os.path.isdir(path) and fileInHorizon(path, horizonTime):
            result.append(file)
    return result


def getManifest(horizon=0, doExportEssentialEntities=None, includeTrace=0, includeUpdates=0, specifiedAreas=None, includeOnboard=0, includeDXF=0, includeExtData=0):
    """
    returns a dictionary mapping filenames to archive names.
    If horizon is 0, all files are returned. If horizon is -1, only the core files are returned.
    Otherwise, the horizon is the timestamp to lookback for files.
    """
    manifest = {}
    for area in FLAT_DIRS:
        dir = mstarpaths.interpretPath(DIR_MAPPINGS[area])
        if area in LIMITED_LOOKBACK:
            if horizon == -1:
                continue
            horizonTimeToUse = horizon
        else:
            horizonTimeToUse = 0
        (drive, tail) = os.path.splitdrive(os.getcwd())
        logger.info("zipSnapshot.getManifest: Searching %s current drive %s ..." % (dir, drive))
        for name in flatFileList(dir, horizonTimeToUse):
            pathname = dir + os.sep + name
            if isForbiddenInSnapshots(name):
                logger.info("Skipping %s as it does not get included in snapshots" % pathname)
                continue
            nameInArchive = area + os.sep + name
            manifest[pathname] = nameInArchive

    # add Essential Entities export directories:
    if doExportEssentialEntities:
        area = 'data/failover'
        dir = mstarpaths.interpretPath("{MSTAR_DATA}/failover")
        (drive, tail) = os.path.splitdrive(os.getcwd())
        logger.info("zipSnapshot.getManifest: Searching %s current drive %s ..." % (dir, drive))
        for name in recursiveFileList(dir, dir, 0, includeDXF):
            pathname = dir + os.sep + name
            nameInArchive = area + os.sep + name
            manifest[pathname] = nameInArchive
        areas = RECURSE_LIMITED
    else:
        if specifiedAreas is not None:
            specifiedAreas = specifiedAreas.replace(" ", "")
            areas = specifiedAreas.split(",")
        else:
            areas = RECURSE_STD

    if includeUpdates and areas.count('updates') == 0:
        areas.append("updates")
    else:
        logger.info("Skipping updates files")

    if includeOnboard == 1:
        areas.append("onboard")
    else:
        logger.info("Skipping onboard files")

    if includeExtData == 1:
        areas.append("extData")
    else:
        logger.info("Skipping extension data files")

    # If the logs directory and additional logs directories are the same, no need to include the logs twice
    skipAddLogs = mstarpaths.interpretPath("{MSTAR_LOGS}") == mstarpaths.interpretPath("{MSTAR_ADD_LOGS}")

    # Collect the files
    areas.sort()
    for area in areas:
        if not includeTrace and area == 'trace':
            logger.info("Skipping Inspector trace files")
            continue
        if skipAddLogs and area == 'additional_logs':
            logger.info("Skipping additional logs as same as standard logs")
            continue
        if area not in DIR_MAPPINGS:
            continue
        dir = mstarpaths.interpretPath(DIR_MAPPINGS[area])
        if area in LIMITED_LOOKBACK:
            if horizon == -1:
                continue
            horizonTimeToUse = horizon
        else:
            horizonTimeToUse = 0
        logger.info("Searching %s recursively for files to include" % dir)
        for name in recursiveFileList(dir, dir, horizonTimeToUse, includeDXF):
            # Include all files but exclude any dxf files if includeDXF is false 
            if not includeDXF and (name.endswith(".dxf") or name.endswith(".DXF")) and (not name.endswith("Surface0.dxf")):
                logger.info("Skipping DXF file %s" % name)
            elif name.endswith(".p12") or name.endswith(".P12") or name.endswith(".jks") or name.endswith(".JKS"):
                logger.info("Skipping certificate file %s" % name)
            else:
                pathname = dir + os.sep + name
                nameInArchive = area + os.sep + name
                manifest[pathname] = nameInArchive

    # Include releaseInfo.txt file so that the scripts that check snapshots can tell what build they are running on site.
    relFile = mstarpaths.getReleaseInfoFile()
    if relFile is not None:
        pathname = relFile
        nameInArchive = os.path.basename(relFile)
        manifest[pathname] = nameInArchive

    # add MSTAR_DATA Cycle Cache recovery files if running on the App Server:
    if specifiedAreas is None or areas.count('data') > 0:
        thisComputer = ServerTools.getCurrentServer()
        appServer = mstarpaths.interpretVar("_HOME")
        if thisComputer.lower() == appServer.lower():
            area = 'data'
            dir = mstarpaths.interpretPath("{MSTAR_DATA}")
            logger.info("Searching %s for dat files to include" % dir)
            for name in flatFileList(dir, 0):
                if name.endswith(".dat"):
                    pathname = dir + os.sep + name
                    nameInArchive = area + os.sep + name
                    manifest[pathname] = nameInArchive

    # add MSTAR_DATA/ext-data files if running on the App Server:
    if areas.count('extData') > 0:
        thisComputer = ServerTools.getCurrentServer()
        appServer = mstarpaths.interpretVar("_HOME")
        if thisComputer.lower() == appServer.lower():
            area = 'data/ext-data'
            dir = mstarpaths.interpretPath("{MSTAR_DATA}/ext-data")
            logger.info("Searching %s for all files to include" % dir)
            for name in recursiveFileList(dir, dir, 0, 0):
                pathname = dir + os.sep + name
                nameInArchive = area + os.sep + name
                manifest[pathname] = nameInArchive

    # add underground draw card CSV files if the license contains underground and if running on the App Server:
    if specifiedAreas is None or areas.count('data') > 0:
        subSystems = mstarpaths.interpretVar("_SUBSYSTEMS")
        if 'Underground' in subSystems:
            thisComputer = ServerTools.getCurrentServer()
            appServer = mstarpaths.interpretVar("_HOME")
            if thisComputer.lower() == appServer.lower():
                area = 'data'
                dir = mstarpaths.interpretPath("{MSTAR_DATA}/drawcards")
                logger.info("Searching %s for csv files to include" % dir)
                for name in recursiveFileList(dir, dir, 0, includeDXF):
                    if name.endswith(".csv"):
                        pathname = dir + os.sep + name
                        nameInArchive = area + os.sep + "drawcards" + os.sep + name
                        manifest[pathname] = nameInArchive

    return manifest


def dumpManifest(names, filename):
    """dumps a list of filenames to a file"""
    mfFile = open(filename, 'w')
    for n in names:
        mfFile.write(n + "\n")
    mfFile.close()


def deleteManifest(file):
    try:
        os.remove(file)
    except:
        # ignore
        pass


def zipSnapshot(zipFileName, modelDBFile=None, PitmodelDBFile=None,
                lookbackHours=0, doExportEssentialEntities=None, includeTrace=0, includeOnboard=0, includeDXF=0, includeExtData=0, allowZip64=None):
    if lookbackHours > 0:
        horizon = time.time() - lookbackHours * 3600
    else:
        horizon = lookbackHours
    manifest = getManifest(horizon, doExportEssentialEntities, includeTrace, 0, None, includeOnboard, includeDXF, includeExtData)
    if modelDBFile is not None:
        if os.path.isfile(modelDBFile):
            exportFileParts = os.path.split(modelDBFile)
            manifest[modelDBFile] = "tmp" + os.sep + exportFileParts[1]
    if PitmodelDBFile is not None:
        if os.path.isfile(PitmodelDBFile):
            exportFileParts = os.path.split(PitmodelDBFile)
            manifest[PitmodelDBFile] = "tmp" + os.sep + exportFileParts[1]
    files = manifest.keys()
    files.sort()
    zf = zipfile.ZipFile(file=zipFileName, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=True)
    manifestFilename = zipFileName + ".MANIFEST"
    dumpManifest(files, manifestFilename)
    manifest[manifestFilename] = 'MANIFEST'
    files.insert(0, manifestFilename)
    for path in files:
        logger.info("Adding %s ..." % path)
        nameInArchive = manifest[path]
        try:
            st = os.stat(path)
            mtime = time.localtime(st.st_mtime)
            date_time = mtime[0:6]
            if date_time[0] < 1980 or None:
                os.utime(path, None)
            zf.write(path, str(nameInArchive))
        except:
            logger.warn("Cannot add %s: %s" % (path, traceback.format_exc(sys.exc_info()[0])))
            pass
    zf.close()
    deleteManifest(manifestFilename)
    zipSize = os.stat(zipFileName)[stat.ST_SIZE] * 1.0 / 1024 / 1024
    logger.info("zipSnapshot completed: %d files zipped into %s (%.1fM) using a lookback of %d hours" % \
      (len(files), zipFileName, zipSize, lookbackHours))


if __name__ == "__main__":
    # Check usage
    if len(sys.argv) != 2:
        print "Usage: zipSnapshot.py ZIP_FILE_NAME"
        print sys.argv
        sys.exit(12)
    mstarpaths.loadMineStarConfig()
    zipSnapshot(sys.argv[1])
