import os
import re

from releaseInfo import ReleaseInfo
from packageConfig import PackageConfig
from installerLayoutVersions import InstallerLayoutVersions
from fileOps import FileOps


majorMinorRegex = re.compile('^(\d\.\d)(-\w+)?$')
majorMinorZeroRegex = re.compile('^(\d\.\d)\.0(-\w+)?$')
buildIdRegex = re.compile('^(\d(\.\d)*)(-r\d+)$')

class MStarBuildError(RuntimeError):
    """ Error raised when there is a general error to do with an mstar build. """
    pass


class MStarBuildListener(object):

    """ Listens for various M* build events. """

    def onStart(self, operation, buildName, systemName):
        """ Called at the start of an M* build operation, e.g
            operation='refreshBuild', buildName='Home', systemName='main'. """
        pass

    def onEnd(self, operation, buildName, systemName):
        """ Called at the end of an M* build operation, e.g.
            operation='refreshBuild', buildName='Home', systemName='main'. """
        pass

    # TODO consider adding onPreInstall, onPostInstall, onPreUninstall, etc


class MStarBuild(object):
    
    """ Class representing the content of an mstar directory, e.g. /mstar/mstarHome, /mstar/mstar4.4, etc. """
    
    def __init__(self, path):
        # Check that the path is a valid M* build.
        if path is None:
            raise ValueError("No path specified for M* build")
        if not MStarBuild.isValidMStarBuildDir(path):
            raise ValueError("Invalid path '%s' for M* build" % path)
        self._path = path
        self._name = None
        self._version = None
        self._layout = None
        self._packageConfig = None
        self._packages = None
        self._repository = None
        self._installDir = None
        
    # @Override
    def __repr__(self):
        return "{path:'%s', version:%s, layout:%s}" % (self.path, self.version, self.layout)
    
    @property
    def path(self):
        return self._path
    
    @property
    def name(self):
        """ Get the name of the build. The name is derived from the path, so '/mstar/mstarHome'
            will have the name 'Home' and '/mstar/mstar4.4.1' will have the name '4.4.1'. This
            matches the build name in the MineStar.ini file. """
        if self._name is None:
            p = os.path.basename(self.path)
            if p.startswith('mstar'):
                p = p[5:]
            self._name = p    
        return self._name
    
    @property
    def version(self):
        """ Get the version of the mstar build, derived from the configuration files in the build. The
            version may be different to the build name (e.g. in the case of '/mstar/mstarHome'). """
        if self._version is None:
            self._version = self._resolveVersion(self._lookupVersion())
        return self._version

    def _resolveVersion(self, version):
        # Hack to get around issues when running from source. Should not be running from source!

        def isRunningFromSource():
            from sourceRepository import SourceRepository
            source = SourceRepository.getInstance(self.path)
            return source.running

        def getVersionWhenRunningFromSource():
            # MSTAR_HOME should be: ${project}/fleetcommander/src/main/config
            # Get the version from: ${project}/fleetcommander/target/unpack/release-properties/releaseInfo.properties
            fleetcommanderModuleDir = os.path.abspath(os.path.join(self.path, os.pardir, os.pardir, os.pardir))
            releasePropertiesDir = os.path.join(fleetcommanderModuleDir, 'target', 'unpack', 'release-properties')
            releaseInfoPropertiesFile = os.path.join(releasePropertiesDir, 'releaseInfo.properties')
            if not os.access(releaseInfoPropertiesFile, os.F_OK):
                raise MStarBuildError("Cannot find release information file %s" % releaseInfoPropertiesFile)
            from propertiesConfig import PropertiesConfig
            config = PropertiesConfig.load(releaseInfoPropertiesFile)
            return config['release.info.version.resolved']

        def containsPlaceHolders(s):
            return '${' in s and '}' in s

        if containsPlaceHolders(version):
            resolved = None
            if isRunningFromSource():
                resolved = getVersionWhenRunningFromSource()
            if resolved is None:
                raise MStarBuildError("Cannot resolve M* build version: '%s'" % version)
            if containsPlaceHolders(resolved):
                raise MStarBuildError("Cannot resolve M* build version: '%s'" % resolved)
            version = resolved
        return version

    def _lookupVersion(self):
        # Check for package config (layout model 2.0).
        if PackageConfig.containsConfig(self.path):
            return PackageConfig.load(self.path).version

        # Check for release info (layout model 1.0)
        if ReleaseInfo.containsConfig(self.path):
            return ReleaseInfo.load(self.path).version

        # Check for 'rel-X_X_X' file (layout model 1.0)
        for fileName in os.listdir(self._path):
            if fileName.startswith("rel_"):
                return fileName[4:].replace("_", "-")

        # Cannot determine version, assume undefined.
        raise MStarBuildError("Cannot determine MineStar version in path '%s'." % self.path)

    def equivalentVersions(self):
        """ Find the equivalent versions for an M* build. So if the version is e.g. '5.1-SNAPSHOT' or 
            '5.1.0-SNAPSHOT' then equivalent versions would be ['5.1-SNAPSHOT', '5.1.0-SNAPSHOT']. This 
            gets around M* sometimes using a different version in the release to the version used by 
            maven when generating an artifact. """
        return equivalentVersions(self.version)

    def equivalentSnapshotVersions(self):
        versions = []
        # If the version is of form 'x.y.z-buildNum' then it may be a snapshot, e.g. '5.1-r10000' -> '5.1-SNAPSHOT'.
        match = buildIdRegex.match(self.version)
        if match:
            versions = equivalentVersions(match.group(1) + '-SNAPSHOT')
        return versions

    @property
    def layout(self):
        """ Get the layout of the mstar build. """
        if self._layout is None:
            self._layout = self._lookupLayout()
        return self._layout
    
    def _lookupLayout(self):
        # Check for 'package.ini' file.
        if PackageConfig.containsConfig(self.path):
            return InstallerLayoutVersions.VERSION_2
        
        # Check for 'releaseInfo.txt' file.
        if ReleaseInfo.containsConfig(self.path):
            return InstallerLayoutVersions.VERSION_1
        
        # Check for 'rel_X_X_X' file.
        if any([f.startswith('rel_') for f in os.listdir(self.path)]):
            return InstallerLayoutVersions.VERSION_1
        
        raise MStarBuildError("Cannot determine MineStar layout model in path '%s'." % self.path)

    @property
    def packageConfig(self):
        if self._packageConfig is None:
            self._packageConfig = self._loadPackageConfig()
        return self._packageConfig
    
    def _loadPackageConfig(self):
        # Load the package config if it already exists.
        if PackageConfig.containsConfig(self.path):
            return PackageConfig.load(self.path)
        # Otherwise create a default package config.
        return self._createPackageConfig()
    
    def _createPackageConfig(self):
        """ Create the default package config for an M* build. Typically used when creating 
            a new M* package for migrating."""
        config = PackageConfig()
        config.name = 'mstar'
        config.version = self.version
        config.description = "CAT Mine Star Build %s" % self.version
        config.symlink = '%s%s' % ('mstar', self.version)
        
        # TODO set the timestamp to the modification date of the releaseInfo.txt file.
        # releaseInfoTxtFile = os.path.join(self.path, ReleaseInfo.FILE_NAME)
        # if os.path.exists(releaseInfoTxtFile):
        #     from timestamps import Timestamp
        #     from datetime import datetime
        #     modtime = os.stat(releaseInfoTxtFile).st_mtime
        #     config.timestamp = Timestamp.fromDateTime(datetime.fromtimestamp(modtime))
            
        return config

    @property
    def installDir(self):
        if self._installDir is None:
            # XXX Assumes a directory layout: /mstar/mstar1.2.3 or /mstar/packages/mstar/1.2.3
            installDir = os.path.abspath(os.path.join(self.path, os.pardir))
            while 'packages' in installDir:
                installDir = os.path.abspath(os.path.join(self.path, os.pardir))
            self._installDir = installDir
        return self._installDir
    
    @property
    def resourcesDir(self):
        """ The location of the 'resources' directory in the build, e.g.
            '/mstar/mstarHome/resources', '/mstar/packages/mstar/4.5/resources'. """
        return os.path.join(self.path, 'resources')

    @property
    def installerResourcesDir(self):
        """ The location of the installer resources directory in the build, e.g.
            '/mstar/mstarHome/resources/installer', '/mstar/packages/mstar/4.5/resources/installer'. """
        return os.path.join(self.resourcesDir, 'installer')

    @property
    def packages(self):
        """ Get the packages (if any) contained in the mstar build. """
        if self._packages is None:
            self._packages = self.repository.packages
        return self._packages

    @property
    def repository(self):
        """ Get the repository for the packages (if any) contained in the mstar build. """
        if self._repository is None:
            self._repository = self._loadRepository()
        return self._repository

    # XXX This is probably deprecated now that installables are extracted ...

    def _loadRepository(self):
        # Check for embedded packages in ${mstarHome}/packages
        packagesDir = os.path.join(self.path, 'packages')
        if os.path.exists(packagesDir):
            from packageRepositories import PathRepository
            return PathRepository(packagesDir)
        # Check for embedded packages in ${mstarHome}/resources/installer
        zippedPackages = os.path.join(self.installerResourcesDir, 'mstar-packages-%s.zip' % self.version)
        if os.path.exists(zippedPackages):
            from packageRepositories import CompressedRepository
            return CompressedRepository(zippedPackages)
        packages = []
        # Check for old layouts.
        from installerLayoutVersions import InstallerLayoutVersions
        if self.layout == InstallerLayoutVersions.VERSION_1:
            from mstarInstall import MStarInstall
            mstarInstall = MStarInstall.getInstance(self.installDir)
            mappings = mstarInstall.packageConfigurations(self.version)
            for name in mappings:
                config = mappings[name]
                path = os.path.join(self.installDir, config.name)
                if os.path.exists(path) and os.path.isdir(path):
                    from packages import ComponentPackage
                    packages.append(ComponentPackage(path, config))
                else:
                    from packages import BootstrapPackage
                    packages.append(BootstrapPackage(config))
        # Create a repository containing the (possibly empty) packages.
        from packageRepositories import PackagesRepository
        return PackagesRepository(packages)

    def extractInstallables(self, mstarInstall):
        """ Extract any installable resources embedded in the build. """

        # Move any archives found in source directory to the target directory.
        def installArchivesFrom(sourceDirectory, targetDirectory):
            if os.path.exists(sourceDirectory):
                options = {'overwrite': True}
                for fname in os.listdir(sourceDirectory):
                    resource = os.path.join(sourceDirectory, fname)
                    if os.path.isfile(resource) and resource.endswith('zip'):
                        print "Extracting %s to %s ..." % (resource, targetDirectory)
                        # Create the target directory if it does not exist.
                        if not os.path.exists(targetDirectory):
                            os.makedirs(targetDirectory)
                        # Move the archive to the target directory.
                        FileOps.getFileOps().moveFile(resource, targetDirectory, options)

        # Check for embedded packages.
        installArchivesFrom(os.path.join(self.path, 'updates', 'packages'), mstarInstall.packageUpdatesDir)

        # Check for embedded repositories ('resources/installer' for backwards compatibility)
        installArchivesFrom(os.path.join(self.path, 'updates', 'repositories'), mstarInstall.repositoryUpdatesDir)
        installArchivesFrom(os.path.join(self.path, 'resources', 'installer'), mstarInstall.repositoryUpdatesDir)

        # TODO check for embedded patches, etc.

    @classmethod
    def getMStarBuildDir(cls, installDir, buildName):
        """ Get the M* build directory for the build name in an M* install. For example, if 
            the install dir is '/mstar' and the build name is 'Home' then the M* build 
            directory is '/mstar/mstarHome'. """
        if isEmptyString(installDir):
            raise ValueError("Cannot get M* build: invalid install directory %s" % installDir)
        if isEmptyString(buildName):
            raise ValueError("Cannot get M* build: invalid build name %s" % buildName)
        return os.path.join(installDir, 'mstar%s' % buildName)
    
    @classmethod
    def isValidMStarBuildDir(cls, dir):
        """ Determines if a directory represents a valid M* build. The directory must exist and
            must contain a package.ini file, releaseInfo.txt, or rel_<xyz> file. """
        # The directory must exist.
        if dir is None or not os.path.isdir(dir):
            return False
        
        # Check if directory contains a package.ini file. 
        if PackageConfig.containsConfig(dir):
            return True
            
        # Check if directory contains a releaseInfo.txt file.
        if ReleaseInfo.containsConfig(dir):
            return True

        # Check if directory contains rel_X_X_X file.
        return any([f.startswith("rel_") for f in os.listdir(dir)])
    
    @classmethod
    def findMStarBuildNames(cls, installDir):
        """ Return a list of mstar build names contained in the given install directory. For example,
            if the install directory is '/mstar' with '/mstar/mstarHome' and '/mstar/mstar4.4.1' 
            directories then the list returned will be ['Home', '4.4.1']. Note that only the names of
            valid builds are returned. """
        if isEmptyString(installDir):
            raise ValueError("Cannot find M* build names: invalid install directory: %s" % installDir)
        buildNames = []
        for f in os.listdir(installDir):
            # Only consider directories starting with 'mstar', e.g. 'mstarHome', 'mstar4.4.1', etc.
            resource = os.path.join(installDir, f)
            if f.startswith('mstar') and len(f) > 4 and os.path.isdir(resource):
                if cls.isValidMStarBuildDir(resource):
                    # Strip leading 'mstar' from the directory name.
                    buildName = f[5:]
                    buildNames.append(buildName)
        return buildNames
        
    @classmethod
    def findMStarBuildDirs(cls, installDir):
        """ Return a list of mstar build directories contained in the given install directory. For example, 
            if the install directory is '/mstar' with '/mstar/mstarHome' and '/mstar/mstar4.4.1' directories
            then the list ['/mstar/mstarHome', '/mstar/mstar4.4'] is returned. Note that only valid M* build
            directories are returned. """
        if isEmptyString(installDir):
            raise ValueError("Cannot find M* builds: invalid install directory %s" % installDir)
        return [cls.getMStarBuildDir(installDir, x) for x in cls.findMStarBuildNames(installDir)]
    
    @staticmethod
    def findMStarBuilds(installDir):
        """ Return a list of mstar builds contained in the given install directory. For example, if
            the install directory is '/mstar' then may return a list containing a build object for 
            '/mstar/mstarHome', a build object for '/mstar/mstar4.4', etc. """
        if isEmptyString(installDir):
            raise ValueError("Cannot find M* builds: invalid install directory %s" % installDir)
        return [MStarBuild(x) for x in MStarBuild.findMStarBuildDirs(installDir)]


def equivalentVersions(version):
    if isEmptyString(version):
        raise ValueError("No version specified.")

    # Start with the defined version (may switch to build number).
    versions = [version]

    def majorMinorEquivalent():
        # If the version is of the form 'x.y[-whatever]' then add 'x.y.0[-whatever]',
        # e.g. '5.1' -> '5.1.0', '5.1-SNAPSHOT' -> '5.1.0-SNAPSHOT', etc.
        result = None
        match = majorMinorRegex.match(version)
        if match:
            result = match.group(1) + '.0'
            if match.group(2):
                result += match.group(2)
        return result

    def majorMinorZeroEquivalent():
        # If the version is of the form 'x.y.0[-whatever]' then add 'x.y[-whatever]',
        # e.g. '5.1.0' -> '5.1', '5.1.0-SNAPSHOT' -> '5.1-SNAPSHOT', etc.
        result = None
        match = majorMinorZeroRegex.match(version)
        if match:
            result = match.group(1)
            if match.group(2):
                result += match.group(2)
        return result

    # Only add equivalents if not a build ID (which should be unique).
    if not buildIdRegex.match(version):
        equivalentVersion = majorMinorEquivalent()
        if equivalentVersion:
            versions.append(equivalentVersion)
        equivalentVersion = majorMinorZeroEquivalent()
        if equivalentVersion:
            versions.append(equivalentVersion)

    return versions


def isEmptyString(s):
    import StringTools
    return StringTools.isEmpty(s)
