__version__ = "$Revision: 1.59 $"

#  Copyright (c) 2020 Caterpillar

import os
import string
import shutil
import re
import mstarpaths
import mstarrun
import minestar
import ConfigurationFileIO
import makeShortcuts
import makeCatalogs
import filecmp

import mstaroverrides
import systemOverrides
import StringTools

logger = minestar.initApp()

# Default settings which do not need to be overridden
LICENCING_PROPERTIES = "{MSTAR_INSTALL}/LICENSE.key"
DEFAULT_LANGUAGE = systemOverrides.DEFAULT_LANGUAGE
DEFAULT_COUNTRY = systemOverrides.DEFAULT_COUNTRY
DEFAULT_TIME_ZONE = systemOverrides.DEFAULT_TIME_ZONE
DEFAULT_DEFAULT_DAY_START = systemOverrides.DEFAULT_DEFAULT_DAY_START

# Directory lists used during an upgrade
DIRS_EXPECTED_LOCAL = ["MSTAR_ADMIN", "MSTAR_LOGS", "MSTAR_TEMP", "MSTAR_CACHE", "MSTAR_TRACE", "MSTAR_BO_JARS", "MSTAR_CREDS"]
DIRS_EXPECTED_CENTRAL = ["MSTAR_ADD_LOGS", "MSTAR_CONFIG", "MSTAR_DATA","TempDBDirectory", "MSTAR_HELP", "MSTAR_MESSAGES",
  "MSTAR_ONBOARD", "MSTAR_OUTGOING", "MSTAR_REPORTS", "MSTAR_SENT", "MSTAR_UPDATES",
  "MSTAR_REPORT_TEMPLATES", "MSTAR_REPORT_PROPERTIES", "MSTAR_REPORT_OUTPUT"]
DIRS_OTHER = ["TempDBDirectory", "MSTAR_VIMS", "MSTAR_FLUID_IMPORT"]
DEFAULT_DIRECTORIES = DIRS_EXPECTED_LOCAL + DIRS_EXPECTED_CENTRAL + DIRS_OTHER

# Mappings between the directories in the system template and their destination directory.
# There must be an entry for each directory in the templates file.
MINESTAR_DIR_MAPPINGS = {
    'admin':      '{MSTAR_ADMIN}',
    'data':       '{MSTAR_DATA}',
    'logs':       '{MSTAR_LOGS}',
    'onboard':    '{MSTAR_ONBOARD}',
    'shortcuts':  '{MSTAR_BASE_LOCAL}/shortcuts',
    'simulator':  '{MSTAR_BASE_CENTRAL}/simulator',
    'trace':      '{MSTAR_TRACE}'
}

# Directories to skip
MINESTAR_DIR_IGNORE = {
    '.svn',
}

class MakeSystemOptions(object):

    """ Class representing the options for makeSystem. """

    def __init__(self, cmdLineOpts=None, args=None):
        # Derive the options.
        if cmdLineOpts is not None:
            self._upgrade = cmdLineOpts.upgrade or False
            self._keepJetty = cmdLineOpts.keep_jetty or False
            self._forceJetty = cmdLineOpts.force_jetty or False
            self._geoserverRefresh = cmdLineOpts.geoserver_refresh or False
            self._verbose = cmdLineOpts.verbose or False
        else:
            self._upgrade = False
            self._keepJetty = False
            self._forceJetty = False
            self._geoserverRefresh = False
            self._verbose = False

        # Derive system name and central directory from the args.
        self._systemName = 'main'
        self._oldCentral = None
        self._overrideCentral = None

        if args and len(args) >= 1:
            self._systemName = args[0]

        if args and len(args) >= 2:
            self._overrideCentral = args[1]

    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, verbose):
        self._verbose = verbose

    @property
    def keepJetty(self):
        """ Indicates if skip cleaning jetty web application directories. """
        return self._keepJetty

    @keepJetty.setter
    def keepJetty(self, keepJetty):
        self._keepJetty = keepJetty

    @property
    def forceJetty(self):
        """ Indicates if force generating jetty web application directories. """
        return self._forceJetty

    @forceJetty.setter
    def forceJetty(self, forceJetty):
        self._forceJetty = forceJetty

    @property
    def upgrade(self):
        """ Indicates if upgrade build to use mstarHome install. """
        return self._upgrade

    @upgrade.setter
    def upgrade(self, upgrade):
        self._upgrade = upgrade

    @property
    def geoserverRefresh(self):
        """ Indicates if refreshes GeoServer data directory. """
        return self._geoserverRefresh

    @geoserverRefresh.setter
    def geoserverRefresh(self, geoserverRefresh):
        self._geoserverRefresh = geoserverRefresh

    @property
    def systemName(self):
        return self._systemName

    @property
    def centralDir(self):
        return self._centralDir

    @property
    def oldCentral(self):
        """ The old value of the 'MSTAR_BASE_CENTRAL' variable. """
        return self._oldCentral

    @oldCentral.setter
    def oldCentral(self, oldCentral):
        """ Thw new value (if any) of the 'MSTAR_BASE_CENTRAL' variable. """
        self._oldCentral = oldCentral

    @property
    def overrideCentral(self):
        return self._overrideCentral

    @overrideCentral.setter
    def overrideCentral(self, overrideCentral):
        self._overrideCentral = overrideCentral

def getCurrentBuild():
    relFile = mstarpaths.getReleaseInfoFile()
    if relFile is not None:
        (rs, rc) = mstarpaths.loadConfig(relFile)
        return "%s-%s" % (rc["MAJOR"], rc["MINOR"])
    else:
        # Fall back to the best we can
        return "Home"

def runningFromRepository():
    mstarHome = mstarpaths.interpretPath("{MSTAR_HOME}/../mstarHome")
    result = not os.access(mstarHome, os.F_OK)
    #print "makeSystem.runningFromRepository called: returning %s" % result
    return result

def _guessSystemOverrides(computer, suite):
    return systemOverrides.guessSystemOverrides(computer,suite)

def _deriveExtensions(productListStr, allExtensions):
    """
    build the list of actual extensions from a comma-separated list of product names, e.g.
    if productListStr is "Fleet_Commander\Health,Fleet_Commander\Machine_Tracking"
    then a list is returned containing all the actual extensions found under these product areas
    """
    if productListStr is None:
        return []
    result = []
    products = productListStr.split(",")
    import mstarext
    for p in products:
        # The install program may put in empty strings so skip them
        p = p.strip()
        if len(p) == 0:
            continue
        extsForProduct = mstarext.getExtensionsForProduct(p)
        if len(extsForProduct) > 0:
            result.extend(extsForProduct)
    return result

def _getDeploymentType():
    licenseFile = mstarpaths.interpretPath(LICENCING_PROPERTIES)
    if licenseFile is not None:
        (sources,depVal) = mstarpaths.loadConfig(licenseFile)
        depType = depVal.get("deploymentType")
        if depType is None:
            depType = "Client"
        return depType
    return "Client"

def _copySystemTemplateDirectories(directories):
    """Copy all directories and files from the bus/system_template directory to the new system's directory, """
    "preserving those that already exist. "
    print "Copying system_template directory ..."
    # Get the name of the template directory.
    templateDir = mstarpaths.interpretPathOverride("{MSTAR_HOME}/bus/system_template", directories)
    dirs = os.listdir(templateDir)

    # Get the installation type from the license.key file
    onboardDir = mstarpaths.interpretPathOverride("{MSTAR_ONBOARD}", directories)
    if os.path.exists(onboardDir):
        print "NOTE: Sub-directories, software and config in %s will NOT be overwritten. To obtain the latest bundled onboard software delete the onboard directory and run makeSystem main." % onboardDir
        if 'onboard' in dirs:
            dirs.remove('onboard')

    for dir in dirs:
        sourceDir = "%s/%s" % (templateDir, dir)
        if not dir in MINESTAR_DIR_MAPPINGS:
            if not dir in MINESTAR_DIR_IGNORE:
                print "WARNING: Directory " + dir + " is not defined in makeSystem. Skipping"
            continue
        targetDir = mstarpaths.interpretPathOverride(MINESTAR_DIR_MAPPINGS[dir], directories)
        print "%s -> %s..." % (dir, targetDir)

        # Copy the system_template for the given directory to the target.  Already existing files will not be overwritten.
        # Also pass the deplyoment type so that onboard need not be copied for profiles other than server.
        _copyTreeAndPrintErrors(dir, sourceDir, targetDir)

def _copyTreeAndPrintErrors(dir, sourceDir, targetDir):
    errors = _copyTree(sourceDir, targetDir)
    if errors:
        print "%d errors while installing %s. See log for details" % (errors, dir)


def _copyTree(src, dest):
        """Recursively copy a directory tree."""
        errors = 0
        minestar.makeDir(dest)
        if os.access(src, os.F_OK):
            for f in os.listdir(src):
                srcPath = "%s%s%s" % (src, os.sep, f)
                if minestar.isDirectory(srcPath) and not f.startswith("."):
                    destPath = mstarpaths.interpretPath(dest)
                    (newPath, lastBit) = os.path.split(srcPath)
                    destPath1 = os.path.join(destPath, lastBit)
                    errors += _copyTree(srcPath, destPath1)
                elif not minestar.isDirectory(srcPath):
                    destPath = "%s%s%s" % (dest, os.sep, f)
                    # Don't overwrite files that already exist.
                    if not os.path.exists(destPath):
                       # And a nasty hack for Ian Booth - don't overwrite any file having the form "Tope*.exe" or "CAES*.exe". Yuk.
                       flower = f.lower()
                       if flower == "tope.exe" or flower == "caes.exe":
                           topeExists, CAESExists = checkTopeCAES(dest, flower)
                           if flower == "tope.exe" and topeExists:
                              print "NOT copying Tope.exe into the new system"
                              continue
                           elif flower == "CAES.exe" and CAESExists:
                              print "NOT copying CAES.exe into the new system"
                              continue
                       else:
                           try:
                               shutil.copy(srcPath, dest)
                           except (IOError, error) as why:
                               minestar.logit('Error copying %s -> %s: %s' % (srcPath, dest, why))
                               errors += 1
                    elif not minestar.isDirectory(srcPath) and not filecmp.cmp(srcPath, destPath, False):
                       print "WARNING: Destination file differs to source %s. File has not been replaced." % srcPath
        return errors

def _copy_overwrite_tree(src, dest, do_not_overwrite = None):
    """Copy an entire directory tree, overwriting any file which already exist"""
    if os.path.isdir(src):
        if not os.path.exists(dest):
            os.makedirs(dest)
        files = os.listdir(src)
        for f in files:
            srcfile = os.path.join(src, f)
            destfile = os.path.join(dest, f)
            if do_not_overwrite is not None and f in do_not_overwrite and os.path.isfile(srcfile) and os.path.exists(destfile):
                print "  (not replacing file %s)" % f
                continue
            _copy_overwrite_tree(srcfile, destfile, do_not_overwrite)
    else:
        shutil.copyfile(src, dest)

def checkTopeCAES(path, origFileName):
    # Check the directory for a file called "Tope*.exe" and one called "CAES*.exe".
    topeExists = False
    CAESExists = False
    for f in os.listdir(path):
        nameInLowercase = f.lower()
        if origFileName == "tope.exe":
           if re.compile("tope").search(nameInLowercase) is not None:
              if nameInLowercase.endswith(".exe"):
                 topeExists = True
        if origFileName == "caes.exe":
           if re.compile("caes").search(nameInLowercase) is not None:
              if nameInLowercase.endswith(".exe"):
                 CAESExists = True
    return topeExists, CAESExists

def upgradeDirectories(dirFile, options, directories):
    # Upgrade the directories ensuring directory entries required for this build are present.
    # If centralDir is being overridden then update this entry in MineStar.directories.

    overrideCentralDir = options.overrideCentral

    newDirs = ConfigurationFileIO.loadDictionaryFromFile(dirFile)

    # If central dir was overridden on the command line then write it out to the MineStar.directories file
    if overrideCentralDir:
        print "Upgrading MSTAR_BASE_CENTRAL %s -> %s in %s " % (options.oldCentral, overrideCentralDir, dirFile)
        newDirs['MSTAR_BASE_CENTRAL'] = overrideCentralDir

    for k in directories.keys():
        # Add any values in directories that are not currently in MineStar.directories
        if k not in newDirs or StringTools.isEmpty(newDirs[k]):
            newDirs[k] = directories[k]

    ConfigurationFileIO.saveDictionaryToFile(newDirs, dirFile)
    return newDirs

def saveDefaultOverrides(overridesFile, systemName):
    computer = mstarpaths.interpretVar("COMPUTERNAME")
    suite = mstarpaths.getSuiteForSystem(systemName)
    overrides = _guessSystemOverrides(computer, suite)
    overridePairs = [("/MineStar.properties", overrides)]

    # Add calendar defaults, if any.
    calendarDefaults = __guessCalendarDefaults()
    if calendarDefaults is not None:
        overridePairs.append(("com.mincom.util.calendar.Config", calendarDefaults))

    # Add the default extensions, if any.
    defaultExtensions = __guessDefaultExtensions()
    if len(defaultExtensions) > 0:
        versionOverrides = {"_SUBSYSTEMS": string.join(defaultExtensions, ","),
                            "CURRENT_BUILD": getCurrentBuild()}
        overridePairs.append(("/Versions.properties", versionOverrides))

    mstaroverrides.saveOverridesToFile(overridesFile, overridePairs)
    return overrides

def __guessDefaultExtensions():
    # Set the default set of extensions
    de = mstarpaths.interpretVar("defaultExtensions")
    products = []
    if de is not None and de != "":
        products = [ s.strip() for s in de.split(",") ]
    defaultExtensions = []
    import mstarext
    for p in products:
        defaultExtensions = defaultExtensions + mstarext.getExtensionsForProduct(mstarpaths.config, p)
    return defaultExtensions

def __guessCalendarDefaults():
    dayStart = mstarpaths.interpretVar("defaultDayStart")
    if dayStart is None or dayStart == DEFAULT_DEFAULT_DAY_START:
        return None

    calendarDefaults = {"Default_Days.at": dayStart}

    try:
        shiftsPerDayStr = mstarpaths.interpretVar("defaultShiftsPerDay")
        if shiftsPerDayStr.find("3") >= 0:
            shiftsPerDay = 3
        else:
            shiftsPerDay = 2
    except:
        shiftsPerDay = 2
    if shiftsPerDay == 3:
        calendarDefaults["Default_Shifts.calendars"] = "8HR_Shifts,8HR_Shifts,8HR_Shifts,8HR_Shifts,8HR_Shifts,8HR_Shifts,8HR_Shifts"
    return calendarDefaults

def upgradeOverridesForNewBuild():
    print "Updating build number and disabling existing patches"
    (overridePairs, ovFile) = mstaroverrides.loadOverrides()
    versionOverrides = overridePairs.get("/Versions.properties", {})
    buildId = getCurrentBuild()
    print "Updating MineStar.overrides - clearing patches and setting new build to %s" % buildId
    versionOverrides["CURRENT_BUILD"] = buildId
    for k in versionOverrides.keys():
        if k.startswith("patch_"):
            del versionOverrides[k]
            print "Disabling patch %s" % k[len("patch_"):]
    overridePairs.update({"/Versions.properties": versionOverrides})
    mstaroverrides.saveOverrides(overridePairs)

def removeCycleDefinitions():
    # Remove existing standard definition files as a part of upgrade process
    (overridePairs, ovFile) = mstaroverrides.loadOverrides()
    cycleKPIOverrides = overridePairs.get("minestar.production.service.kpisummaries.Config", {})
    for k in cycleKPIOverrides.keys():
        if k.startswith("cycles.load."):
            del cycleKPIOverrides[k]
    overridePairs.update({"minestar.production.service.kpisummaries.Config": cycleKPIOverrides})
    mstaroverrides.saveOverrides(overridePairs)

def _overrideIfNotSet(config, key, overrideValue):
    if not StringTools.isEmpty(config.get(key)):
        return
    config[key] = overrideValue


def _installDefaultHelp():
    # Install default help for the language, if required.
    languageCode = mstarpaths.interpretVar("_LANGUAGE")
    if StringTools.isEmpty(languageCode) or languageCode == "_LANGUAGE":
        import systemOverrides
        languageCode = systemOverrides.DEFAULT_LANGUAGE

    from helpDoc import HelpDoc
    helpDoc = HelpDoc(languageCode)
    if helpDoc.installed():
        print "Help files already installed for language '%s'." % languageCode
    else:
        print "Installing help files for language '%s'..." % languageCode
        helpDoc.install()


def makeSystem(options):
    """create a system or finish creating a partially made system"""

    systemName = options.systemName
    upgradeSystem = options.upgrade
    overrideCentralDir = options.overrideCentral

    # Create system directories
    systemDir = mstarpaths.interpretPath("{MSTAR_SYSTEMS}/%s" % systemName)
    if os.path.exists(systemDir):
        print "directory for system %s already exists" % systemName
    else:
        print "creating directory %s ..." % systemDir
        os.makedirs(systemDir)
    localDir = mstarpaths.interpretVar("MSTAR_BASE_LOCAL") or systemDir
    if not os.path.exists(localDir):
        print "creating directory %s ..." % localDir
        os.makedirs(localDir)
    centralDir = overrideCentralDir or mstarpaths.interpretVar("MSTAR_BASE_CENTRAL") or systemDir
    if not os.path.exists(centralDir):
        print "creating directory %s ..." % centralDir
        os.makedirs(centralDir)

    directories = __loadDefaultDirectories()

    # If a directories file does not yet exist, create one. Either way, get the set of directories.
    directoriesFile = mstarpaths.interpretPath("{MSTAR_SYSTEMS}/%s/MineStar.directories" % systemName)
    if os.path.exists(directoriesFile):
        print "MineStar.directories already exists - upgrading"
        directories = upgradeDirectories(directoriesFile, options, directories)
    else:
        print "creating MineStar.directories ..."
        # Set some sensible system-specific directories
        try:
            ConfigurationFileIO.saveDictionaryToFile(directories, directoriesFile)
        except:
            print "WARNING: Failed to create file %s" % directoriesFile

    # If using the defaults, set these in "directories"
    _overrideIfNotSet(directories, 'MSTAR_BASE_LOCAL', localDir)
    _overrideIfNotSet(directories, 'MSTAR_BASE_CENTRAL', centralDir)

    # Copy files from system template area to the new system's area.
    _copySystemTemplateDirectories(directories)

    # If an overrides file does not yet exist, create one.
    # If a central directory was specified, assume this has already been done.
    serverList = None
    deploymentType = mstarpaths.getDeploymentType()
    if deploymentType != "Server":
        print "%s install - skipping MineStar.overrides and config/reports generation" % deploymentType
    else:
        mstarConfig = mstarpaths.interpretPathOverride(directories['MSTAR_CONFIG'], directories)
        overridesName = mstaroverrides.OVERRIDES_NAME
        overridesFile = os.path.join(mstarConfig, overridesName)
        if os.path.exists(overridesFile):
            secureOverridesAction = "migrating"
            computer = mstarpaths.interpretVar("COMPUTERNAME")
            appServer = mstarpaths.interpretVar("_HOME")
            if upgradeSystem and computer.lower() == appServer.lower():
                print "%s already exists - on Application Server so upgrading ..." % overridesName
                upgradeOverridesForNewBuild()
            else:
                print "%s already exists" % overridesName
        else:
            print "creating %s ..." % overridesName
            secureOverridesAction = "creating"
            overrides = saveDefaultOverrides(overridesFile, systemName)
            mstarpaths.saveOverridesToConfig(overrides, "(default overrides)")
            serverList = overrides.get("_START")


        print "%s Secure Overrides" % secureOverridesAction
        mstaroverrides.migrateOverridesForSystem(systemName)

        # Create a config/reports directory as the default location for saving report designs
        reportsDir = mstarConfig + os.sep + "reports"
        if os.path.exists(reportsDir):
            print "config/reports directory for system %s already exists" % systemName
        else:
            print "creating directory %s ..." % reportsDir
            os.makedirs(reportsDir)

    # Delete contents of cache directory
    mstarCache = mstarpaths.interpretPathOverride(directories['MSTAR_CACHE'], directories)
    if os.path.exists(mstarCache):
        print "Deleting contents of cache directory %s ..." % mstarCache
        import shutil
        for root, dirs, files in os.walk(mstarCache):
            try:
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    shutil.rmtree(os.path.join(root, d))
            except Exception, e:
                print "Could not delete %s" % mstarCache

    # Before making the catalogs lets check for Autonomy extn.
    import mstarext
    mstarext.verifyCommandLicense()
    # Reload the application configuration.
    mstarpaths.loadMineStarConfig(systemName, forceReload=1)

    # Make the shortcuts. If a central directory was specified, skip the Server ones.
    # Otherwise we need to explicitly do the server ones as the overrides are generated
    # (above) after the config is loaded.
    if centralDir is not None:
        makeShortcuts.makeShortcuts(['Client', 'Admin'], systemName)
    else:
        makeShortcuts.makeShortcuts(makeShortcuts.ALL_GROUPS, systemName, serverListAsStr=serverList)

    # Make the catalogs.
    # If a central directory was specified, assume this has already been done.
    if deploymentType != "Server":
        print "%s install - skipping catalog generation" % deploymentType
    else:
        allCatalogs = makeCatalogs.DEFAULT_TAGS.keys()
        allCatalogs.sort()
        catalogs = allCatalogs
        targetArea = mstarpaths.interpretPath("{MSTAR_CONFIG}")
        searchPath = mstarpaths.interpretVar("UFS_PATH")
        try:
            makeCatalogs.buildCatalogs(catalogs, allCatalogs, searchPath, targetArea)
        except:
            print "ERROR: makeCatalogs aborted unexpectedly - please contact MineStar support"

    # Upgrade the configs.
    configuredApps = mstarpaths.interpretVar("_START") or ""
    print "Configured apps pre-upgrade: %s" % configuredApps

    mstarrun.run("minestar.platform.presentation.upgrade.UpgradePageConfigs")

    # Reload the application configuration.
    mstarpaths.loadMineStarConfig(systemName, forceReload=1)
    configuredApps = mstarpaths.interpretVar("_START") or ""
    print "Configured apps post-upgrade: %s" % configuredApps

    # Initialise Jython scripting
    print "Initializing Jython scripting ..."
    script = mstarpaths.interpretPath("{MSTAR_HOME}/bus/jythonlib/scripting.py")
    mstarrun.run(["org.python.util.jython", script])

    # Regenerate windows services, if required
    import windowsServices
    if windowsServices.isWindowsServicesEnabled():
        print "Regenerating Windows Services Configuration and Property files"
        windowsServices.regenerateServices()
        print "Updating Windows Services as needed"
        windowsServices.updateServices(True)

    # Ensure that the build is correct for the system
    print "\nUpdating MineStar.ini with an initial build name ..."
    import refreshBuild
    buildName = mstarpaths.interpretVar("CURRENT_BUILD")
    if upgradeSystem or buildName is None or len(buildName.strip()) == 0:
        buildName = 'Home'
    elif not runningFromRepository() and buildName == refreshBuild.getOriginalBuild():
        print "Current build is the original build."
        buildName = 'Home'
    refreshBuild.updateBuildNameForSystem(buildName, systemName)

    subSystems = mstarpaths.interpretVar("_SUBSYSTEMS")
    if 'Underground' not in subSystems:
        # removing Cycle definitions from Overrides ensures that the upgrade will always have standard kpi files selected.
        removeCycleDefinitions()

    _installDefaultHelp()


def __loadDefaultDirectories():
    bootstrapConfig = mstarpaths.loadBootstrapConfig()
    directories = {key: bootstrapConfig[key] for (key) in DEFAULT_DIRECTORIES}
    return directories


def _maintainJetty(options):
    """Setup Jetty patching"""
    if not options.keepJetty:
        print "Cleaning web directories, see help (-h) to prevent this."
        mstarweb.cleanWebDirectories()

        # Check Jetty is a selected server
        servers = mstarpaths.interpretVar("_START").split(",")

        # Either force generation or we have detected we should do this
        if options.forceJetty or "Jetty" in servers:
            # Get the web directories
            print "Generating web directories because of Jetty or -f."
            mstarweb.unpackWebDirectories()

def _updateBuildPathForScheduledTask():
    import makeScheduledTasks
    print "\nMaking scheduled task updates ..."
    makeScheduledTasks.run("update")

def _setupGeoServer(options):
    """Setup GeoServer"""
    print "\nSetting up GeoServer ..."

    # Create GeoServer Data directory if it doesn't already exist
    geoServerDataDir = mstarpaths.interpretPath("{_GEOSERVER_DATA_DIR}")
    if not os.path.exists(geoServerDataDir):
        print "Creating GeoServer data directory %s ..." % geoServerDataDir
        os.makedirs(geoServerDataDir)
    else:
        print "GeoServer data directory already exists: %s" % geoServerDataDir

    if options.geoserverRefresh:
        # Delete all folders and files in GeoServer data directory (except for user_projections)
        print "Refreshing GeoServer data directory %s ..." % geoServerDataDir
        names = os.listdir(geoServerDataDir)
        for name in names:
            fullname = os.path.join(geoServerDataDir, name)
            if os.path.isdir(fullname):
                # Delete all folders except for user_projections and security
                if name not in ["user_projections", "security"]:
                    shutil.rmtree(fullname)
            else:
                # Delete all files in the root folder
                os.unlink(fullname)

    # Copy GeoServer config into data directory, but don't overwrite existing files
    geoServerConfig = mstarpaths.interpretPath("{MSTAR_HOME}/geoserver")
    print "Copying %s to GeoServer Data directory ..." % geoServerConfig
    _copyTreeAndPrintErrors('GeoServer data', geoServerConfig, geoServerDataDir)

    # Remove content folder from GeoServer data directory as this is not needed here
    geoServerContent = mstarpaths.interpretPath("{_GEOSERVER_DATA_DIR}/content")
    if os.path.exists(geoServerContent):
        shutil.rmtree(geoServerContent)

    # Copy required M* libraries to geoserver libraries.

    mstarHome = _getMStarHomeDir()

    geoserverLibDir = mstarpaths.interpretPath("{_GEOSERVER_HOME}/webapps/geoserver/WEB-INF/lib")
    if not os.access(geoserverLibDir, os.F_OK):
        raise RuntimeError("Cannot find geoserver lib directory: %s" % geoserverLibDir)

    requiredLibs = mstarpaths.interpretVar("_GEOSERVER_REQUIRED_LIBS")
    if requiredLibs is not None:
        from install.mstarBuild import MStarBuild
        mstarBuild = MStarBuild(mstarHome)
        mstarLibsDir = os.path.join(mstarHome, 'lib')
        for lib in [x.strip() for x in requiredLibs.split(',') if x.strip() is not '']:
            def findJar():
                # Try exact version first ${lib}-${version} (e.g. 'base-5.1.1.jar').
                src = os.path.join(mstarLibsDir, '%s-%s.jar' % (lib, mstarBuild.version))
                if os.access(src, os.F_OK):
                    return src
                # Try equivalent versions (e.g. '5.1' is equivalent to '5.1.0', etc).
                for version in mstarBuild.equivalentVersions():
                    src = os.path.join(mstarLibsDir, '%s-%s.jar' % (lib, version))
                    if os.access(src, os.F_OK):
                        return src
                # If the version is a build ID (e.g. '5.1.0-r10000') then it is possibly a snapshot
                # release (e.g. '5.1-SNAPSHOT' or '5.1.0-SNAPSHOT'). This is a bit of a hack since
                # there is no way to identify if a build represents a snapshot.
                for version in mstarBuild.equivalentSnapshotVersions():
                    src = os.path.join(mstarLibsDir, '%s-%s.jar' % (lib, version))
                    if os.access(src, os.F_OK):
                        return src
                # Can't find exact version, or equivalent version, or possible snapshot, so look for
                # first file with name '${lib}-*.jar'. This should allow a sensible fallback in case
                # versioning changes in future releases.
                # TODO change this to most recent match?
                for f in os.listdir(mstarLibsDir):
                    import fnmatch
                    if fnmatch.fnmatch(f, '%s-*.jar' % lib):
                        return os.path.join(mstarLibsDir, f)
                # Can't find any ${lib}-*.jar file.
                raise RuntimeError("Cannot find geoserver dependency '%s'" % lib)
            def removeConflictingJars(jar):
                # Remove any ${lib}-*.jar files in geoserver lib dir that don't match the target jar file, e.g.
                # when upgrading from M* 5.1 to M* 5.2 it is necessary to remove "base-5.1.jar" before installing
                # "base-5.2.jar" so that multiple versions of the same jar file are not present).
                for f in os.listdir(geoserverLibDir):
                    jarName= os.path.basename(jar)
                    import fnmatch
                    if fnmatch.fnmatch(f, '%s-*.jar' % lib):
                        installedJar = os.path.join(geoserverLibDir, f)
                        # Check for different versions (e.g. "base-5.3.0.jar" vs "base-5.4.0.jar")
                        if f != jarName:
                            print "Removing geoserver dependency %s (replaced by %s)..." % (f, jarName)
                            os.remove(installedJar)
                        # Check for different content (e.g. "base-5.3.0-SNAPSHOT.jar" may be updated)
                        elif not filecmp.cmp(installedJar, jar):
                            print "Removing geoserver dependency %s (out of date) ..." % f
                            os.remove(installedJar)
            def installJar(jar):
                # Copy the jar file to the geoserver lib dir (if it does not already exist).
                targetJar = os.path.join(geoserverLibDir, os.path.basename(jar))
                if not os.path.exists(targetJar):
                    print "Installing geoserver dependency %s to %s ..." % (os.path.basename(jar), geoserverLibDir)
                    shutil.copy(jar, geoserverLibDir)
            # Remove existing library jars (if any) then install required library jar.
            jar = findJar()
            removeConflictingJars(jar)
            installJar(jar)


def _setupPostGISDataDir(options):
    """Setup PostGIS data directory"""

    # Check that postgis home directory exists.
    postGISHomeDir = mstarpaths.interpretPath("{_POSTGIS_HOME}")
    if not postGISHomeDir:
        print "POSTGIS_HOME not defined; skipping POSTGIS setup."
        return

    # Check if PostGIS has been initialised by checking if the PostGIS base directory exists
    postGISDataDir = mstarpaths.interpretPath("{_POSTGIS_DATA_DIR}")
    postGISBaseDir = os.path.join(postGISDataDir, "base")

    from postgisControl import PostgisControl, PostgisError
    postgis = PostgisControl(postgisHomeDir=postGISHomeDir, postgisDataDir=postGISDataDir)

    # If postgis is installed...
    if os.path.exists(postGISDataDir):
        # Ensure that PostgreSQL is stopped
        if postgis.installed:
            print "postgis database is installed"

            if postgis.running:
                print "postgis database is (probably) running; stopping postgis"
                postgis.stop()
            else:
                print "postgis database is not running"

        if options.geoserverRefresh:
            # Delete all folders and files in GeoServer data directory (except for user_projections)
            print "postgis database refresh; deleting data directory %s" % postGISDataDir
            shutil.rmtree(postGISDataDir)

    if not os.path.exists(postGISBaseDir):
        # No base directory, so initialise PostGIS
        if os.path.exists(postGISDataDir):
            # Delete the PostGIS data directory, so PostGIS can be initialised
            shutil.rmtree(postGISDataDir)

        try:
            # Verify that postgis database is installed.
            if not postgis.installed:
                print "WARNING: postgis database is not installed; skipping configuration."
                return
            # Install necessary extensions.
            print "postgis database setup"
            postgis.initDB()
            postgis.start()
            postgis.installExtension("postgis")
            postgis.installExtension("postgis_topology")
            postgis.installExtension("pg_stat_statements")
            postgis.stop()
        except PostgisError as e:
            print "ERROR: %s" % e
            return

    # Rename existing config files (if postgis config dir exists - may not be case for 4.0.8 build for example).
    postGISConfigDir = mstarpaths.interpretPath("{MSTAR_HOME}/postgis")
    if os.path.exists(postGISConfigDir) and os.path.exists(postGISDataDir):
        # Create a backup of files in data dir that will be overwritten by files in config dir.
        print "postgis database config backup; backing up existing postgis config files in data directory %s" % postGISDataDir
        _backupTree(postGISConfigDir, postGISDataDir)
        # Copy PostGIS config files into data directory
        print "postgis database config installation; copying %s to postgis data directory" % postGISConfigDir
        _copyTreeAndPrintErrors('PostGIS data', postGISConfigDir, postGISDataDir)


def _backupTree(srcDir, destDir):
    """ Copy files/directories from srcDir to destDir, making backups of existing files/directories in destDir. """
    for fileName in os.listdir(srcDir):
        existingFileName = os.path.join(destDir, fileName)
        if os.path.exists(existingFileName):
            backupFileName = os.path.join(destDir, fileName + ".bak")
            # Remove the existing backup file / directory.
            if os.path.exists(backupFileName):
                if os.path.isdir(backupFileName):
                    shutil.rmtree(backupFileName)
                else:
                    os.unlink(backupFileName)
            # Rename the existing file to the backup file.
            os.rename(existingFileName, backupFileName)


def changeTask(mstarTask):
    import mstarpaths
    mstarHome = mstarpaths.interpretPath("{MSTAR_HOME}")
    mstarRun = "%s%s%s%s%s\\mstarrun.bat" % (mstarHome, os.sep, "bus", os.sep, "bin")
    if checkTaskExist(mstarTask):
        changeCmd = 'schtasks /Change /TN %s /TR %s' % (mstarTask,mstarRun)
        #print changeCmd
        subprocess.call(changeCmd)

def _getMStarHomeDir():
    from mstarpaths import interpretPath
    if runningFromRepository():
        mstarHome = interpretPath("{REPOSITORY_MSTAR_HOME}")
    else:
        mstarHome = interpretPath("{MSTAR_HOME}")
    return mstarHome

def _getMStarInstallDir():
    from mstarpaths import interpretPath
    return interpretPath("{MSTAR_INSTALL}")

def _getMStar():
    from install.mstarInstall import MStarInstall
    return MStarInstall.getInstance(_getMStarInstallDir())

def _extractInstallables(options):
    # Move any installables embedded in M* builds to the updates directory.
    mstar = _getMStar()
    for mstarBuild in mstar.getMStarBuilds():
        mstarBuild.extractInstallables(mstar)

def _installPackages(options):
    """ Installs any packages required by the build. """
    # No package updates if running from a source repository.
    if runningFromRepository():
        if options.verbose:
            print "No install packages check: not an installed system."
        return

    # Get the M* build for the specified system name.
    systemName = options.systemName
    mstar = _getMStar()
    mstarBuild = mstar.getMStarBuildForSystemName(systemName)

    # If there's no build for the system name, and no entry for the system name in the
    # MineStar.ini file, then this is a new system that will use the same build as the
    # 'main' system.
    if mstarBuild is None and systemName is not 'main' and systemName not in mstar.config.builds:
        mstarBuild = mstar.getMStarBuildForSystemName('main')

    # Check that a build was found for the system name.
    if mstarBuild is None:
        raise RuntimeError("Cannot find M* build for system name %s" % systemName)

    # Check packages are installed for the current M* build.
    print "Checking for packages to install for M* release %s ..." % mstarBuild.version
    mstar.update(mstarBuild)

    # Reload the config in case there have been changed to the installed packages.
    mstarpaths.loadMineStarConfig(forceReload=True)

def _writePythonMappingsConfiguration(options):
    """ Write the package mappings configuration file for bootstrapping. It is
        expected that these mappings would be used by other scripts for bootstrapping
        (e.g. finding a suitable python installation). """
    mstar = _getMStar()

    # Get the python packages.
    from install.packages import findPackageWithMinimumVersion
    pythonPackages = mstar.installedPackagesRepository.findPackages('python')
    pythonPackage = findPackageWithMinimumVersion(pythonPackages)
    pythonPackagePath = mstar.getPackagePath(pythonPackage)

    configDir = mstar.configDir
    if not os.path.exists(configDir):
        os.makedirs(configDir)

    configFile = os.path.join(configDir, "python-mappings.properties")
    print "Writing configuration file %s ..." % configFile
    with open(configFile, "wt") as f:
        f.write("# Python directory mappings for M*\n")
        f.write("python=%s\n" % pythonPackagePath)

def _writeConfiguration(options):
    # Do not write configuration files if running from repository.
    if runningFromRepository():
        return
    _writePythonMappingsConfiguration(options)

def _windowsServicesEnabled():
    """ Determines if M* windows services are enabled. """
    import sys
    result = False
    if sys.platform.startswith("win"):
        from windowsServices import WindowsServicesController
        result = WindowsServicesController.isEnabled()
    return result

# def _uninstallServices(options):
#     """ Uninstall M* windows services if upgrading the system. """
#     if options.upgrade and _windowsServicesEnabled():
#         # Uninstall all possible M* windows services, not just the configured services.
#         print "Uninstalling M* windows services ..."
#         from windowsServices import WindowsServicesController
#         failedServices = WindowsServicesController.forConfiguredServices().uninstall()
#         if len(failedServices) == 0:
#             if options.verbose:
#                 print "Uninstalled all M* windows services successfully."
#         else:
#             serviceNames = [s.serviceName for s in failedServices]
#             print "ERROR: failed to uninstall %d M* windows service(s): %s" % (len(failedServices), serviceNames)
#
# def _installServices(options):
#     """ Install M* windows services if upgrading the system. """
#     if options.upgrade and _windowsServicesEnabled():
#         # Reinstall just the configured M* windows services.
#         print "Installing M* windows services ..."
#         from windowsServices import WindowsServicesController
#         failedServices = WindowsServicesController.forConfiguredServices().install()
#         if len(failedServices) == 0:
#             if options.verbose:
#                 print "Uninstalled all M* windows services successfully."
#         else:
#             serviceNames = [s.serviceName for s in failedServices]
#             print "ERROR: failed to install %d M* windows service(s): %s" % (len(failedServices), serviceNames)

def _preMakeSystemActions(options):
    """ Actions to perform before making the system. """
    # _uninstallServices(options)
    _extractInstallables(options)
    _installPackages(options)
    _writeConfiguration(options)

def _postMakeSystemActions(options):
    """ Actions to perform after making the system. """
    _maintainJetty(options)
    _setupPostGISDataDir(options)
    _setupGeoServer(options)
    _updateBuildPathForScheduledTask()
    # _installServices(options)

## Main program ##

import mstarweb

from optparse import make_option

def _getMakeSystemOptions(appConfig=None):
    # Process options and check usage
    optionDefns = [
        make_option("-u", "--upgrade", action="store_true", help="upgrade build to use mstarHome install & delete all patches"),
        make_option("-k", "--keep_jetty", action="store_true", help="skip cleaning jetty web application directories", default=False),
        make_option("-f", "--force_jetty", action="store_true", help="force generating jetty web application directories which is useful for running jetty as a service", default=False),
        make_option("-g", "--geoserver_refresh", action="store_true", help="refreshes GeoServer data directory by restoring the initial configuration", default=False),
    ]
    argumentsStr = "name [centralDir]"
    (cmdLineOpts, args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)
    options = MakeSystemOptions(cmdLineOpts, args)

    # Load the configuration for the system name.
    mstarpaths.loadMineStarConfig(system=options.systemName, systemSource='(makeSystem)')

    # Update the configuration if overriding the central directory.
    if options.overrideCentral is not None:
        options.oldCentral = mstarpaths.interpretVar('MSTAR_BASE_CENTRAL')
        mstarpaths.config['MSTAR_BASE_CENTRAL'] = options.overrideCentral
        mstarpaths.sources['MSTAR_BASE_CENTRAL'] = '(makeSystem)'

    # Dump the options.
    if options.verbose:
        print "MakeSystem Settings"
        print "==================="
        print "  systemName      : %s" % options.systemName
        print "  keepJetty       : %s" % options.keepJetty
        print "  forceJetty      : %s" % options.forceJetty
        print "  upgrade         : %s" % options.upgrade
        print "  geoserverRefresh: %s" % options.geoserverRefresh
        print "  oldCentral      : %s" % _quotedStr(options.oldCentral)
        print "  overrideCentral : %s" % _quotedStr(options.overrideCentral)

    return options

def main(appConfig=None):
    """Entry point when called from mstarrun"""

    # Get the makeSystem options.
    options = _getMakeSystemOptions(appConfig)

    # Show information about the current M* installed builds.
    mstar = _getMStar()
    print "M* builds: %s" % mstar.getMStarBuildNames()
    for mstarBuild in mstar.getMStarBuilds():
        print "M* build : name=%s, version=%s, layout=%s" % (mstarBuild.name, mstarBuild.version, mstarBuild.layout)

    _preMakeSystemActions(options)
    makeSystem(options)
    _postMakeSystemActions(options)

    minestar.exit()

def _quotedStr(str):
    if str is None:
        return "None"
    return "'%s'" % str

if __name__ == "__main__":
    """entry point when called from python"""
    main()

