__version__ = "$Revision: 1.16 $"

import shutil, os, zipfile
import minestar, wikiUtils

logger = minestar.initApp()

def getCurrentInstalledBuild():
    # Check MineStar.ini for current installed build number
    currentBuild = ''
    f0 = open('C:/mstar/MineStar.ini', 'r')
    while True:
        line = f0.readline()
        if line == "": break
        if line.startswith('build = '):
            line1 = line.lstrip('build = ')
            currentBuild = line1.rstrip('\n')
    f0.close()
    logger.info('Installed Build: '+currentBuild)
    return currentBuild

def getCurrentAvailableBuild():
    # find the latest current available build from \\Diamond\Releases\2.1dev
    a = os.listdir('//diamond/releases/2.1dev/')
    b = []
    for build in a:
        try:
            b.append(int(build))
        except:
            logger.warn("'"+build+"' is not a valid directory, it is being ignored")
    b.sort()
    b.reverse()
    for item in b:
        directoryName = str(item)
        c = os.listdir('//diamond/releases/2.1dev/'+directoryName)
        fileName = 'mstar2.1dev-' + directoryName + '.zip'
        if fileName in c:
            fileName0 =  '//diamond/releases/2.1dev/'+directoryName+'/'+fileName
            #Check to see if valid Zip File
            if zipfile.is_zipfile(fileName0) == True: break

    buildName = fileName.replace('mstar', '')
    buildName = buildName.replace('.zip', '')                
    logger.info('Available Build: '+buildName)   
    return buildName

def updateMineStar(buildName):
    prefix = '2.1dev-'
    #Copy the zip file to local drive
    fileName = 'mstar' + buildName + '.zip'
    updatesDir = 'C:/mstarFiles/systems/main/updates/'
    buildsDir = updatesDir + 'builds/'
    if not os.path.exists(updatesDir):
        os.mkdir(updatesDir)
    if not os.path.exists(buildsDir):
        os.mkdir(buildsDir)
    fileNameServer = '//diamond/releases/2.1dev/' + buildName[len(prefix):] + '/' + fileName
    fileNameLocal = buildsDir + fileName
    shutil.copyfile(fileNameServer, fileNameLocal)

    # update overrides file
    overridesFile = 'C:/mstarFiles/systems/main/config/MineStar.overrides'
    newOverridesFile = 'C:/mstarFiles/systems/main/config/MineStar.overrides.'+buildName

    f0 = open(overridesFile, 'r')
    f1 = open(newOverridesFile, 'w')

    while True:
        line = f0.readline()
        if line == "": break
        if line.startswith('/Versions.properties.CURRENT_BUILD'):
            f1.write('/Versions.properties.CURRENT_BUILD='+buildName+'\n')
        else:
            f1.write(line)
    f1.close()
    f0.close()
    # remove the existing overrides file
    os.remove(overridesFile)
    # rename the new overrides file to be the old overrides file
    os.rename(newOverridesFile, overridesFile)

    #Call mstarrun commands to refresh, remake and restart the system
    logger.info('calling mstarrun refreshBuild')
    os.system("mstarrun refreshBuild")
    logger.info('calling mstarrun makeSystem main')
    os.system("mstarrun makeSystem main")
    logger.info('calling mstarrun makeDataStores all')
    os.system("mstarrun makeDataStores -dropConstraints all")
    logger.info('calling mstarrun makeDataStores Health')
    os.system("mstarrun makeDataStores Health")

    # Delete the temporary zip file
    os.remove(fileNameLocal)


def removeOldMineStarFiles(installed):
    logger.info('Checking for old MineStar files to remove')
    loc = 'C:/mstar/'
    prefix = 'mstar2.1dev-'
    prefixShort = '2.1dev-'
    installedNum = int(installed[len(prefixShort):]) 
    files = os.listdir(loc)
    for f in files:
        if f.startswith(prefix):
            if ((int(f[len(prefix):] != -1)) and (int(f[len(prefix):]) < (installedNum - 5))): #if directory is at least six build old
                try:
                    logger.info('Removing old MineStar directory: '+loc+f)
                    shutil.rmtree(loc+f)
                except:
                    logger.warn("Error removing directory '"+loc+f+"'")               
    logger.info('Finished removing old MineStar files')
                
## Main Program ##

from optparse import make_option

def main(appConfig=None):
    prefix = '2.1dev-'
    installed = getCurrentInstalledBuild()
    available = getCurrentAvailableBuild()
    try:
        installedBuildNum = int(installed[len(prefix):])
    except: #if installed build is 'home', we will upgrade straight away
        installedBuildNum = 0
    availableBuildNum = int(available[len(prefix):])

    if installedBuildNum < availableBuildNum:
        logger.info('Stopping System')
        os.system('mstarrun stopSystem')
        #Kill TAE (stopSystem won't kill)
        os.system('taskkill /F /IM TAE.EXE')
        logger.info('Updating MineStar to Build: ' + available)
        updateMineStar(available)
        installed = getCurrentInstalledBuild()
        removeOldMineStarFiles(installed)
        logger.info('Removing old temporary files')
        os.system("mstarrun cleanExpiredFiles")
        logger.info('Starting MineStar')
        os.system("mstarrun startSystem")

    minestar.exit()
    
if __name__ == '__main__':
    """entry point when called from python"""
    main()
