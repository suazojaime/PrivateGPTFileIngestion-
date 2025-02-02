
import sys, os, string, types, cgi, zipfile, shutil, mstarpaths, ufs, minestar, locale

locale.setlocale(locale.LC_ALL, "")

CONFIG_FILES = ['topeconfig.txt','topeconfigcommon.txt','topewincfg.txt','topeconfig.overrides.xml','topeconfigcommon.overrides.xml','topewincfg.overrides.xml']

logger = minestar.initApp()


def isConfigFile(filename):
    """ returns true if file is a config file that should be ignored """
    if filename.lower() in CONFIG_FILES:
        return True
    return False


def moveOldFilesToBackupFolder(targetFolderPath,backupFolderPath):
    fileList = os.listdir(targetFolderPath)
    for tgtFile in fileList:
        if not isConfigFile(tgtFile):
            targetFile = "%s/%s" % (targetFolderPath,tgtFile)
            backupFile = "%s/%s" % (backupFolderPath,tgtFile)
            if os.path.isfile(targetFile):
                if os.path.exists(backupFile):
                    os.remove(backupFile)
                os.rename(targetFile,backupFile)
    return


def updateFolder(srcUfsFolder,targetFolderPath,backupFolderPath,indent):
    """ recursively update folders"""
    if not os.path.exists(targetFolderPath):
        os.makedirs(targetFolderPath)
    if not os.path.exists(backupFolderPath):
        os.makedirs(backupFolderPath)
    moveOldFilesToBackupFolder(targetFolderPath,backupFolderPath)
    fileList = srcUfsFolder.listFileNames()
    fileList.sort(cmp=locale.strcoll)
    for srcFileName in fileList:
        targetFilePath = "%s/%s" % (targetFolderPath,srcFileName)
        if isConfigFile(srcFileName) and os.path.exists(targetFilePath):
            print "%s%s skipped as it exists and is a configuration file" % (indent,srcFileName)
        else:
            srcFileUfs = srcUfsFolder.get(srcFileName)
            targetFilePath = "%s/%s" % (targetFolderPath,srcFileName)
            srcFilePath = srcFileUfs.getPhysicalFileName()
            print "%s%s <- %s" % (indent,srcFileName,srcFilePath[:len(srcFilePath)- len(srcFileUfs.getPath())])
            shutil.copy2(srcFilePath, targetFilePath)
    subFolders = srcUfsFolder.listSubdirNames()
    subFolders.sort(cmp=locale.strcoll)
    if len(subFolders) > 0:
        for subFolder in subFolders:
            subFolderSrcUfs = srcUfsFolder.getSubdir(subFolder)
            subFolderTgtPath = "%s/%s" % (targetFolderPath,subFolder)
            subFolderBkpPath = "%s/%s" % (backupFolderPath,subFolder)
            print "%s%s:" % (indent, subFolder)
            updateFolder(subFolderSrcUfs,subFolderTgtPath,subFolderBkpPath,indent+"  ")
    return


def updatePlatform(srcPlatformUfs,targetPlatformFolderPath,backupPlatformFolderPath):
    """update specified platform"""
    print "Updating %s ..." % (targetPlatformFolderPath)
    updateFolder(srcPlatformUfs,targetPlatformFolderPath,backupPlatformFolderPath,"  ")
    print ""
    return


def updateOnboards():
    """loop through each onboard software type """
    last_error = 0
    targetFolder = mstarpaths.interpretPath("{MSTAR_ONBOARD}")
    backupFolder = targetFolder + ".backup"
    if not os.path.exists(backupFolder):
        os.makedirs(backupFolder)
    sourcePath = mstarpaths.interpretVar("UFS_PATH")
    root = ufs.getRoot(sourcePath)
    busFolder = root.getSubdir("bus")
    templateFolder = busFolder.getSubdir("system_template")
    onboardFolder = templateFolder.getSubdir("onboard")
    platformList = onboardFolder.listSubdirNames()
    for platformName in platformList:
        try:
            platformUfs = onboardFolder.getSubdir(platformName)
            targetPlatform = "%s/%s" % (targetFolder, platformName)
            backupPlatform = "%s/%s" % (backupFolder, platformName)
            updatePlatform(platformUfs,targetPlatform,backupPlatform)
        except Exception, e:
            print "ERROR: failed to update platform '%s' due to: %s" % (platformName, str(e))
            last_error = 1
    return last_error

def main(appConfig=None):
    """entry point when called from mstarrun"""
    mstarpaths.loadMineStarConfig()
    last_error = updateOnboards()
    minestar.exit(last_error)

if __name__ == "__main__":
    """entry point when called from python"""
    main()
