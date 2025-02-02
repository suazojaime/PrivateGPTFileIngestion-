"""refreshBuild.py unpacks build packages if not done already"""

__version__ = "$Revision: 1.12 $"

import os
import mstarpaths, minestar, mstarrun
import symlink

from install.mstarBuild import MStarBuildListener

def getOriginalBuild():
    """ Get the original build name, e.g. the version specified in the ${MSTAR_INSTALL}/mstarHome/releaseInfo.txt file. """
    mstarHome = mstarpaths.interpretPath("{MSTAR_INSTALL}/mstarHome")
    from install.releaseInfo import ReleaseInfo
    if not ReleaseInfo.containsConfig(mstarHome):
        return "Home"
    return ReleaseInfo.load(mstarHome).version

def updateBuildNameForSystem(buildName, systemName):
    from install.minestarIni import MineStarIni
    mstarIniFile = mstarpaths.interpretPath("{MSTAR_INSTALL}/%s" % MineStarIni.filename())
    if not os.path.exists(mstarIniFile):
        print "WARNING: Assuming old layout as %s file doesn't exist." % mstarIniFile
        return
    try:
        mstarrun.setLocalBuild(mstarIniFile, buildName, systemName)
        print "Updated %s with build number %s for system %s" % (mstarIniFile,buildName,systemName)
    except OSError as error:
        print "ERROR: Failed to update %s with build number %s for system %s: %s" % (mstarIniFile,buildName,systemName,error)
        minestar.exit(1)
    except IOError as error:
        print "ERROR: Failed to update %s with build number %s for system %s: %s" % (mstarIniFile,buildName,systemName,error)
        minestar.exit(1)

def getMStarInstall():
    from install.mstarInstall import MStarInstall
    return MStarInstall.getInstance()

class CleanTempFilesMStarBuildListener(MStarBuildListener):

    """ An M* build listener that will mark the temporary directory for cleaning after a M* build is refreshed. """

    # @Override
    def onEnd(self, operation, buildName, systemName):
        import cleanTempDir
        cleanTempDir.cleanTempDir(later=1)


class ScheduledTasksMStarBuildListener(MStarBuildListener):

    """ An  M* build listener that will schedule task updates after a M* build is refreshed. """

    # @Override
    def onEnd(self, operation, buildName, systemName):
        print "\nMaking scheduled task updates ..."
        getMStarInstall().run("makeScheduledTasks update")


class UpdateMineStarOverridesBuildListener(MStarBuildListener):

    """ An  M* build listener that will update the MineStar.overrides file after an M* build is refreshed. """

    # @Override
    def onEnd(self, operation, buildName, systemName):
        # Remove /Version.properties._PACKAGES
        # Update /Version.properties._CURRENT_BUILD
        from mstaroverrides import loadOverridesForSystem, saveOverridesToFile, overridesDictToPairs

        # Get the overrides.
        (overrides, overridesFile) = loadOverridesForSystem(system=systemName, config=mstarpaths.getConfig())

        changed = False

        # Check if current build in overrides needs updating.
        versions = overrides.get('/Versions.properties', {})

        def getNextBuildName():
            """ Get the next build name. This is the version derived from the {MSTAR_HOME}/releaseInfo.txt
                file, which may be different to the version derived from the {MSTAR_HOME}/package.ini
                file (e.g. '5.2-SNAPSHOT' vs '5.2.0-r10000', etc). """
            build = getMStarInstall().getMStarBuildForBuildName(buildName)
            # Try getting version from {MSTAR_HOME}/releaseInfo.txt file.
            from install.releaseInfo import ReleaseInfo
            if ReleaseInfo.containsConfig(build.path):
                return ReleaseInfo.load(build.path).version
            # Can't find version.
            return None

        nextBuild = getNextBuildName()
        currentBuild = versions.get('CURRENT_BUILD', None)

        if nextBuild and nextBuild != currentBuild:
            print "Updating /Versions.properties.CURRENT_BUILD from %s to %s ..." % (currentBuild, nextBuild)
            versions['CURRENT_BUILD'] = nextBuild
            changed = True
            # Remove /Versions.properties._PACKAGES for new build.
            if '_PACKAGES' in versions:
                print "Removing /Versions.properties._PACKAGES..."
                del versions['_PACKAGES']
            # TODO remove patches?

        # Save if the overrides back
        if changed:
            saveOverridesToFile(overridesFile, overridesDictToPairs(overrides))


def getDefaultBuildListeners():
    """ The default listeners when refreshing a build. """
    return [ScheduledTasksMStarBuildListener(), UpdateMineStarOverridesBuildListener(), CleanTempFilesMStarBuildListener()]


def refreshBuild(buildName=None, force=False, listeners=None):
    """
     Check that the nominated build has been installed.

     :param buildName: the name of the build to be installed. A value of None will check the current build.

     :param force: force the build to be installed, overwriting any existing build.

     :param listeners: the collection of M* build listeners to receive install / activation events. If no
     listeners are specified then the default listeners (for cleaning the temp directory and scheduling task
     updates) are assumed.
    """

    # If the directory does yet yet exist, create it
    mstarpaths.loadMineStarConfig()

    # Do nothing if running from a repository (build never changes).
    if mstarpaths.runningFromRepository:
        return

    # Resolve the build name, if required.
    buildName = _resolveBuildName(buildName)
    if buildName is None:
        print "Cannot refresh build: cannot resolve build name"
        return

    # Get the system name.
    systemName = mstarpaths.interpretVar('MSTAR_SYSTEM')

    # Create default listeners, if required.
    if listeners is None:
        listeners = getDefaultBuildListeners()

    # Notify listeners of pre-refresh.
    for listener in listeners:
        listener.onStart("refreshBuild", buildName, systemName)

    # Install the build (e.g. unpack the zip file).
    if buildName != "Home":
        _installBuild(buildName, force)

    # Bind the build to the current M* system (e.g. set current build in config file, etc).
    _bindBuild(buildName, force)

    # Notify listeners of post-refresh.
    for listener in listeners:
        listener.onEnd("refreshBuild", buildName, systemName)


def _resolveBuildName(buildName):
    # Get the build name, if not specified.
    if buildName is None:
        # Get the current build name (e.g. '4.0.8-16', etc).
        buildName = mstarpaths.interpretVar("CURRENT_BUILD")

        # If no current build name: can't do anything.
        if not buildName or buildName.isspace():
            print "Current build not set - no refresh attempted."
            return None

        # If build name matches original build then set build name to 'Home'.
        if buildName == getOriginalBuild():
            print "Current build is the original build."
            buildName = 'Home'

    return buildName


def _bindBuild(buildName, force):
    """ Binds the specified build to the current M* system. """
    systemName = mstarpaths.interpretVar('MSTAR_SYSTEM')
    updateBuildNameForSystem(buildName, systemName)


def _extractInstallables(buildName, buildDir):
    """ Installs any packages contained in the build. """
    # Create MStarInstall object.
    from install.mstarInstall import MStarInstall
    mstarInstall = MStarInstall.getInstance(mstarpaths.interpretPath("{MSTAR_INSTALL}"))

    # Create MStarBuild object.
    from install.mstarBuild import MStarBuild
    mstarBuild = MStarBuild(buildDir)

    # Extract the installables (packages, repositories, patches, etc) from the build.
    mstarBuild.extractInstallables(mstarInstall)

def _getReleaseInfoFromZipFile(buildZipFile):
    from install.releaseInfo import ReleaseInfo
    return ReleaseInfo.load(buildZipFile)

def _createMStarPackageConfigFromZipFile(zipfile):
    """ Creates an M* package config from a zip file. The zip file must contain a releaseInfo.txt file. """
    from install.packages import PackageConfig
    config = PackageConfig()
    config.name = 'mstar'
    config.version = _getReleaseInfoFromZipFile(zipfile).version
    config.description = "Mine Star Build %s" % config.version
    config.symlink = '%s%s' % (config.name, config.version)
    return config

def _zipFileContainsPackageConfig(buildZipFile):
    """ Determines if a zipfile contains a package config. """
    from zipfile import ZipFile
    zip = ZipFile(buildZipFile, 'r')
    try:
        from install.packageConfig import PackageConfig
        with zip.open(PackageConfig.filename(), 'r'):
            return True
    except Exception:
        return False
    finally:
        zip.close()

def _unpackZipFile(buildZipFile, directory):
    from zipfile import ZipFile
    zip = ZipFile(buildZipFile, 'r')
    try:
        zip.extractall(directory)
    finally:
        zip.close()


def _createBuildFromVersionOneArchive(mstar, buildZipFile, force=False):
    # Get the release version from the zip file.
    config = _createMStarPackageConfigFromZipFile(buildZipFile)

    # Unpack the archive to ${MSTAR_INSTALL}/packages/mstar/${config.version}
    buildDir = os.path.join(mstar.installDir, 'packages', 'mstar', config.version)
    if not os.path.exists(buildDir) or force:
        _unpackZipFile(buildZipFile, buildDir)

    # Create M* build from the installed package.
    from install.mstarBuild import MStarBuild
    return MStarBuild(buildDir)


def _createBuildFromVersionTwoArchive(mstar, buildZipFile, force=False):
    # Create the M* package.
    from install.packages import CompressedPackage
    package = CompressedPackage(buildZipFile)

    # Install the M* package (but not any dependencies until installables are extracted).
    from install.packageChanges import PackageChange
    policy = PackageChange.POLICY_FORCE if force else PackageChange.POLICY_INSTALL
    packageManager = mstar.createPackageManager(policy=policy)
    packageManager.install(package, options={'installDependencies': False})

    # Create M* build from the installed package.
    from install.mstarBuild import MStarBuild
    return MStarBuild(mstar.getPackagePath(package))

def _unpackBuild(mstar, buildName, force=False):

    # Create a package from the build zip file (constructing a package config
    # if one is not already present, e.g. in an old style mstar.zip file).
    buildZipFile = _getBuildZipFileOrDie(buildName)
    if _zipFileContainsPackageConfig(buildZipFile):
        build = _createBuildFromVersionTwoArchive(mstar, buildZipFile, force)
    else:
        build = _createBuildFromVersionOneArchive(mstar, buildZipFile, force)

    return build


def _installBuild(buildName, force=False):
    from install.mstarInstall import MStarInstall
    mstar = MStarInstall.getInstance()

    # Install the build, if possible.
    build = _unpackBuild(mstar, buildName, force)
    if build is None:
        return

    # Extract any installables from the M* build.
    build.extractInstallables(mstar)

    # Update the build. This will install the packages of the build, if required.
    mstar.update(build)

    # Get the path to the unpacked mstar package.
    packageId = 'mstar:%s' % build.version
    packageDir = mstar.getPackagePath(packageId)
    if not os.path.isdir(packageDir):
        raise RuntimeError("Cannot find path to package %s" % packageId)

    # Get the M* build directory (e.g. '/mstar/mstarHome', '/mstar/mstar5.1', etc).
    buildDir = os.path.join(mstar.installDir, 'mstar%s' % buildName)

    # Remove existing build directory if it is a symbolic link and does not resolve to same version.
    if os.path.exists(buildDir) and symlink.isSymbolicLink(buildDir):
        # Version changes when upgrading a snapshot, e.g. from:
        #   /mstar/mstar5.1-SNAPSHOT -> /mstar/mstar/5.1.0.1000
        # to:
        #   /mstar/mstar5.1-SNAPSHOT -> /mstar/mstar/5.1.0.1001
        from install.mstarBuild import MStarBuild
        from install.versions import Version
        existingBuild = MStarBuild(path=buildDir)
        if not Version.equalTo(existingBuild.version, build.version):
            print "Removing existing symbolic link: %s -> %s" % (buildDir, symlink.resolveSymbolicLink(buildDir))
            symlink.removeSymbolicLink(buildDir)

    # Create a symlink to the package, if necessary (e.g. '/mstar/mstar5.1' -> '/mstar/packages/mstar/5.1')
    if not os.path.exists(buildDir):
        # Create the symlink to the package.
        print "Creating symbolic link: %s -> %s" % (buildDir, packageDir)
        symlink.createSymbolicLink(buildDir, packageDir)
        # Sanity check.
        if not os.path.exists(buildDir):
            raise RuntimeError("Failed to create symbolic link from %s to %s" % (buildDir, packageDir))

    # Removing Windows services. They should be recreated by makeSystem.
    import windowsServices
    if windowsServices.isWindowsServicesEnabled():
        print "Removing Windows services"
        windowsServices.removeAllServices()

def _getBuildZipFileOrDie(buildName):
    """ Get the build package file for the build name, e.g. maps '1.2.3' to
        '${mstarSystems}/main/updates/builds/mstar1.2.3.zip'. Exits if the
        build package file cannot be found. """
    packageDir = mstarpaths.interpretPath("{MSTAR_UPDATES}/builds")
    packageFile = "mstar%s.zip" % buildName
    buildPackageFile = os.path.join(packageDir, packageFile)
    if not os.path.exists(buildPackageFile):
        minestar.logit("ERROR: unable to find build package %s in %s" % (packageFile,packageDir))
        minestar.exit(2)
    return buildPackageFile

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = "[current|buildName]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Install the build
    build = None if (len(args) == 0 or args[0] == "current") else args[0]
    refreshBuild(build)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
