import os

from packageChanges import PackageChange
from packageRepositories import PathRepository, CompressedPackage, createRepositoryFrom
from packages import ComponentPackage
import mstarPackages


def mstarrunDebug(msg):
    if 'MSTARRUN_DEBUG' in os.environ:
        print "debug: %s"


class MStarInstallError(RuntimeError):
    """ Raised when there is a problem with the MineStar install."""
    pass


class MStarInstall(object):

    _instanceMap = {}

    """ Class for common MineStar install operations. """

    def __init__(self, installDir):
        if installDir is None:
            raise ValueError("Must specify an install directory.")
        if not os.path.exists(installDir):
            raise ValueError("Install location '%s' does not exist." % installDir)
        if not os.access(installDir, os.F_OK):
            raise ValueError("Install location '%s' cannot be accessed." % installDir)
        if not os.path.isdir(installDir):
            raise ValueError("Install location '%s' is not a directory." % installDir)
        self._installDir = installDir
        self._mstarConfigFile = None
        self._licenseKey = None
        self._supportedTargets = None
        self._packageDefinitions = None
        self._mstarStatusChecker = None
        self._backups = None
        self._config = None
        self._packagesDir = None
        
    @property
    def installDir(self):
        return self._installDir

    @property
    def mstarHomeDir(self):
        """ Get the MSTAR_HOME directory, e.g. /mstar/mstarHome or /mstar/mstar5.1 """
        import mstarpaths
        return mstarpaths.interpretPath('{MSTAR_HOME}')

    @property
    def mstarrunFile(self):
        """ Get the location of the mstarrun script for executing, e.g. ${MSTAR_HOME}/bus/bin/mstarrun.bat on Windows. """
        import sys
        if sys.platform.startswith('win'):
            mstarrunFile = os.path.join(self.mstarHomeDir, 'bus', 'bin', 'mstarrun.bat')
        else:
            mstarrunFile = os.path.join(self.mstarHomeDir, 'bus', 'bin', 'mstarrun')
        return mstarrunFile

    @property
    def configDir(self):
        return os.path.join(self.installDir, 'conf')

    @property
    def buildsDir(self):
        return os.path.join(self.installDir, 'builds')

    @property
    def packagesDir(self):
        """ Get the location of the packages directory, e.g. {MSTAR_INSTALL}/packages """
        if self._packagesDir is None:
            self._packagesDir = self._loadPackagesDir()
        return self._packagesDir
        
    def _loadPackagesDir(self):
        # Use '${project}/runtime/target/packages' directory if running from source.
        from sourceRepository import SourceRepository
        source = SourceRepository.getInstance(self.mstarHomeDir)
        if source.running:
            return os.path.join(source.runtimeDir, 'packages')
        # Otherwise use '{MSTAR_INSTALL}/packages' directory.
        return os.path.join(self.installDir, 'packages')

    @property
    def updatesDir(self):
        """ Get the path to the updates directory, e.g. '${mstarInstall}/updates'. Creates the directory if
            it does not already exist. """
        directory = os.path.join(self.installDir, 'updates')
        if not os.path.exists(directory):
            os.makedirs(directory)
        return directory

    @property
    def packageUpdatesDir(self):
        """ Get the path to the directory containing package updates, e.g. '${mstarInstall}/updates/packages'.
            Creates the directory if it does not already exist. """
        directory = os.path.join(self.updatesDir, 'packages')
        if not os.path.exists(directory):
            os.makedirs(directory)
        return directory

    @property
    def repositoryUpdatesDir(self):
        """ Get the path to the directory containing repository updates, e.g. '${mstarInstall}/updates/repositories'.
            Creates the directory if it does not already exist. """
        directory = os.path.join(self.updatesDir, 'repositories')
        if not os.path.exists(directory):
            os.makedirs(directory)
        return directory

    @property
    def systemsDir(self):
        """ Get the path to the mstar systems directory, as defined in the LICENSE.key file, e.g. 
           '/mstarFiles/systems'. """
        return self.licenseKey.mstarSystems

    @property
    def backups(self):
        if self._backups is None:
            from backups import Backups
            self._backups = Backups(self.installDir)
        return self._backups

    def getMStarBuildNames(self):
        """ Get the list of M* build names in the M* install, e.g. ['Home', '4.4.1', '5.1-SNAPSHOT'],
            etc. Each build name can be passed to getMStarBuildDir() to obtain the build directory,
            or to getMStarBuild() to obtain the build object. """ 
        from mstarBuild import MStarBuild
        return MStarBuild.findMStarBuildNames(self.installDir)
    
    def getMStarBuilds(self):
        """ Get the list of M* builds in the M* install. """
        from mstarBuild import MStarBuild
        return MStarBuild.findMStarBuilds(self.installDir)
    
    def getMStarBuildDir(self, buildName):
        """ Get the M* build directory for the build name. """
        from mstarBuild import MStarBuild
        return MStarBuild.getMStarBuildDir(buildName)
    
    def getMStarBuildForBuildName(self, buildName='Home'):
        """ Get the M* build matching the build name, e.g. 'Home', '1.2.3', etc. """
        for build in self.getMStarBuilds():
            if build.name == buildName:
                return build
        return None
    
    def getMStarBuildForSystemName(self, systemName='main'):
        """ Get the M* build for a system name, e.g. 'main', 'test', etc. """
        mstarBuildName = self.config.getBuild(systemName)
        if mstarBuildName is None:
            return None
        # Get the build directory for the build name,
        from mstarBuild import MStarBuild
        mstarBuildDir = MStarBuild.getMStarBuildDir(self.installDir, mstarBuildName)
        if not MStarBuild.isValidMStarBuildDir(mstarBuildDir):
            return None
        # Create a build from the build directory.
        return MStarBuild(mstarBuildDir)
    
    @property
    def installedPackagesRepository(self):
        """ Get the installed packages repository. This will include all packages in the
            ${mstarInstall}/packages directory. """
        # Always create the repository dynamically, as packages may have been installed since previous call.
        return self._createInstalledPackagesRepository()

    def _createInstalledPackagesRepository(self):
        # Create the '/packages' directory, if required.
        if not os.path.exists(self.packagesDir):
            os.makedirs(self.packagesDir)
        return PathRepository(self.packagesDir)

    @property
    def availablePackagesRepository(self):
        """ Get the available packages repository. This will include all packages in the 
            ${mstarInstall}/updates/packages directory and all repositories in the 
            ${mstarInstall}/updates/repositories directory. """
        # Always create the repository dynamically, as packages may have been installed since previous call.
        return self._createAvailablePackagesRepository()

    def _createAvailablePackagesRepository(self):
        repositories = []
        
        # Finds the archives in a directory.
        def findArchivesIn(directory):
            archives = []
            if os.path.exists(directory):
                from zipfile import is_zipfile
                for fname in os.listdir(directory):
                    resource = os.path.join(directory, fname)
                    if is_zipfile(resource):
                        archives.append(resource)
            return archives
        
        # Add a repository for updates/packages directory.
        packages = [CompressedPackage(x) for x in findArchivesIn(self.packageUpdatesDir)]
        if len(packages) > 0:
            repositories.append(createRepositoryFrom(packages))
            
        # Add repositories in updates/repositories directory.
        repositories.extend([createRepositoryFrom(x) for x in findArchivesIn(self.repositoryUpdatesDir)])
        return createRepositoryFrom(repositories)

    @property
    def runStatus(self):
        """ Get the run status of the M* system (assumes single installed system). """
        if self._mstarStatusChecker is None:
            from mstarStatus import MStarStatusChecker
            self._mstarStatusChecker = MStarStatusChecker()
        return self._mstarStatusChecker.status

    def running(self):
        """ Return True if M* service or process is running, False otherwise. """
        status = self.runStatus
        from mstarStatus import MStarStatus
        return status == MStarStatus.PROCESSES_RUNNING or status == MStarStatus.SERVICES_RUNNING

    def createPackageManager(self, available=None, supportedTargets=None, policy=None):
        """
        Create a new package manager. The installed packages of the package manager defaults
        to the ${installDir}/packages directory. 
        
        :param available: The available packages repository. Defaults to the available packages repository.
        
        :param supportedTargets: The supported targets, as a list of strings (e.g.['client','server']).
        Defaults to the settings in the license key file.
        
        :param policy: The install policy. Defaults to PackageChange.POLICY_INSTALL.
        """

        # Use the default available packages repository, if required.
        if available is None:
            available = self.availablePackagesRepository

        # Get the default supported targets, if required.
        if supportedTargets is None:
            supportedTargets = self.supportedTargets

        # Create default install policy.
        policy = policy or PackageChange.POLICY_INSTALL

        from packageManager import PackageManager
        return PackageManager(available=available, installed=self.installedPackagesRepository,
                              supportedTargets=supportedTargets, policy=policy)

    @property
    def mstarConfigFile(self):
        """ Get the path to the M* config file (e.g. '/mstar/MineStar.ini') """
        if self._mstarConfigFile is None:
            from minestarIni import MineStarIni
            self._mstarConfigFile = os.path.join(self.installDir, MineStarIni.filename())
        return self._mstarConfigFile

    @property
    def config(self):
        """ Get the M* configuration (from e.g. /mstar/MineStar.ini file) """
        if self._config is None:
            self._config = self._loadMineStarConfig()
        return self._config

    def _loadMineStarConfig(self):
        from minestarIni import MineStarIni
        if not os.access(self.mstarConfigFile, os.F_OK):
            raise MStarInstallError("Cannot find M* config file '%s'" % self.mstarConfigFile)
        return MineStarIni.load(self.mstarConfigFile)
        
    @property
    def licenseKey(self):
        if self._licenseKey is None:
            self._licenseKey = self._loadLicenseKey()
        return self._licenseKey

    def _loadLicenseKey(self):
        from licenseKey import LicenseKey
        licenseKeyFile = os.path.join(self.installDir, LicenseKey.filename())
        if not os.access(licenseKeyFile, os.F_OK):
            raise MStarInstallError("Cannot find license key file '%s'" % licenseKeyFile)
        return LicenseKey.load(licenseKeyFile)

    @property
    def supportedTargets(self):
        if self._supportedTargets is None:
            self._supportedTargets = self._loadSupportedTargets()
        return self._supportedTargets

    def _loadSupportedTargets(self):
        supportedTargets = []
        deploymentType = self.licenseKey.deploymentType
        if deploymentType == 'Server':
            supportedTargets.append('server')
        elif deploymentType == 'Client':
            supportedTargets.append('client')
        return supportedTargets

    def packageConfigurations(self, version):
        """ Get the package configurations for the mstar version. """
        if self._packageDefinitions is None:
            self._packageDefinitions = self._loadPackageDefinitions()
        return self._packageDefinitions.getPackageConfigs(version)

    def _loadPackageDefinitions(self):
        from packageDefinitions import PackageDefinitions
        return PackageDefinitions()

    # getInstalledPackage("geoserver")
    # getInstalledPackage("geoserver:2.10.3")
    # getInstalledPackage(package)
    def getInstalledPackage(self, packageID):
        """ Get the installed package (if any) represented by the package ID. Returns None
            if the installed package cannot be found """
        return self.installedPackagesRepository.findPackage(packageID)
        
    def getPackagePath(self, packageID):
        """ Get the path to package, e.g. 'geoserver' -> '/mstar/packages/geoserver/2.10.3'. This
            does not guarantee that the package exists. Always use a repository or package manager
            for such operations, or check if the path exists. """
        # Verify that a package is specified.
        if packageID is None:
            raise ValueError("No package ID specified")
        # Resolve the package ID if required.
        from packages import PackageIdentifier
        packageID = PackageIdentifier.createFrom(packageID)
        # The resolved package path is ${MSTAR_INSTALL}/packages/${package.name}/${package.version}    
        return os.path.join(self.packagesDir, packageID.name, str(packageID.version))

    def _getBootstrapPackages(self, mstarBuild):
        """ Get the bootstrap packages (if any) for a M* build. """
        packages = []
        
        # Check for old layouts (e.g. installing mstar:4.4.1 or earlier)
        from installerLayoutVersions import InstallerLayoutVersions
        if mstarBuild.layout == InstallerLayoutVersions.VERSION_1:
            mappings = self.packageConfigurations(mstarBuild.version)
            for (name, config) in mappings.items():
                # Get the path to the original directory (e.g. '/mstar/geoserver' or '/mstar/system').
                path = os.path.join(self.installDir, config.name)
                if os.path.exists(path) and os.path.isdir(path):
                    from packages import ComponentPackage
                    packages.append(ComponentPackage(path, config))
                else:
                    from packages import BootstrapPackage
                    packages.append(BootstrapPackage(config))

        # The packages for later layouts (e.g. mstar-5.0.1) should have been installed
        # separately by the package manager, or when the installables are extracted (by
        # makeSystem or refreshBuild).
        
        return packages

    def update(self, mstarBuild):
        """ Update the install by installing the packages for an M* release. """
        if mstarBuild is None:
            raise ValueError("No M* build specified.")

        # Get the bootstrap packages (if any).
        packages = self._getBootstrapPackages(mstarBuild)

        # Create a repository containing the bootstrap packages.
        repository = createRepositoryFrom(packages)

        # Add package for the 'mstar' build itself, if required.
        p = repository.findPackage('mstar')
        if p is None:
            packages.append(ComponentPackage(mstarBuild.path, mstarBuild.packageConfig))
            repository = createRepositoryFrom(packages)

        # Add the available packages. This may include repositories for other builds.
        repository = createRepositoryFrom([repository, self.availablePackagesRepository])

        # Find the 'system' package. The 'available' repository takes precedence over the
        # 'installed' repository, so that snapshots are handled properly. It is assumed
        # that 'available' will later contain later snapshots than 'installed'. If the
        # 'installed' system package is a later snapshot than the 'available' system 
        # package, then the 'available' system package's dependencies are installed, but
        # will not be referenced until the later 'installed' snapshot is removed.
        repository = createRepositoryFrom([repository, self.installedPackagesRepository])
        systemPackageId = 'system:%s' % mstarBuild.version
        systemPackage = repository.findPackage(systemPackageId)
        if systemPackage is None:
            errorMsg = "Cannot update M* build %s - package '%s' not found." % (mstarBuild.version, systemPackageId)
            mstarrunDebug(errorMsg)
            from packages import UnresolvedPackageError
            raise UnresolvedPackageError(errorMsg)

        # Get the dependencies of the M* system.
        dependencies = mstarPackages.getPackageDependencies(package=systemPackage)

        # Install the 'system' package and its dependencies.
        packageManager = self.createPackageManager(available=repository)
        packageManager.install(systemPackage, options={'installDependencies': True, 'dependencies': dependencies})

    def run(self, command):
        """ Run an M* command (via ${MSTAR_HOME}/bus/bin/mstarrun). Returns the exit code of the command. """
        mstarrun = self.mstarrunFile
        # Check that the mstarrun script is executable.
        if not os.path.exists(mstarrun):
            raise RuntimeError("Cannot find '%s'" % mstarrun)
        if not os.access(mstarrun, os.X_OK):
            raise RuntimeError("Cannot execute '%s'" % mstarrun)
        # Execute the mstarrun command.
        return os.system("%s %s" % (mstarrun, command))

    @staticmethod
    def defaultMStarInstallDir():
        """ Get the default mstar install directory. This will be ${user.home}/mstar for all platforms. """
        userHomeDir = os.path.expanduser('~')
        return os.path.join(userHomeDir, 'mstar')

    @staticmethod
    def defaultMStarFilesDir():
        """ Get the default mstar files directory. This will be ${user.home}/mstarFiles for all platforms. """
        userHomeDir = os.path.expanduser('~')
        return os.path.join(userHomeDir, 'mstarFiles')

    @staticmethod
    def defaultMStarSystemsDir():
        """ Get the default mstar systems directory. This will be ${user.home}/mstarFiles/systems for all platforms. """
        return os.path.join(MStarInstall.defaultMStarFilesDir(), 'systems')

    @staticmethod
    def defaultMStarDataDir():
        """ Get the default mstar data directory. This will be ${user.home}/mstarData for all platforms. """
        userHomeDir = os.path.expanduser('~')
        return os.path.join(userHomeDir, 'mstarData')

    @staticmethod
    def getInstance(installDir=None):
        """ Get the singleton instance of the MStarInstall for the install directory. """
        # Get the default install directory; assume that M* config has been loaded.
        if installDir is None:
            import mstarpaths
            installDir = mstarpaths.interpretPath("{MSTAR_INSTALL}")
        key = os.path.abspath(installDir)
        if key in MStarInstall._instanceMap:
            return MStarInstall._instanceMap[key]
        instance = MStarInstall(installDir)
        MStarInstall._instanceMap[key] = instance
        return instance
