import types
from zipfile import is_zipfile, ZipFile

import os
from fileOps import FileOps
from typeOps import isInstanceOf
from assertOps import assertIsNotNone, assertIsInstanceOf

from packageConfig import PackageConfig
from versions import Version


class PackageError(RuntimeError):
    """ Raised when an error occurs performing a package operation. """
    pass


class UnresolvedPackageError(PackageError):
    """ Raised when a package cannot be resolved. """
    pass


class ConflictingPackageError(PackageError):
    """ Raised when two packages are in conflict. """
    pass


class InvalidPackageError(PackageError):
    """ Raised when a package is invalid (e.g. missing required files, etc). """
    pass


class PackageDependencyError(PackageError):
    """ Raised when there is an error regarding package dependencies. """
    pass

class UnresolvedDependencyError(PackageDependencyError):
    """ Raised when a package dependency cannot be resolved. """
    pass


class ConflictingDependencyError(PackageDependencyError):
    """ Raised when there are conflicting package dependencies. """
    pass


class PackageIdentifier(object):

    """ Class representing a package identifier of the form name[':' version]. """

    def __init__(self, name, version=None):
        if name is None:
            raise ValueError("Cannot create package identifier: no name specified")
        if not name.strip():
            raise ValueError("Cannot create package identifier: name is empty")
        if version is not None and not Version.valid(version):
            raise ValueError("Cannot create package identifier: %s." % Version.invalidReason(version))
        self._name = name
        self._version = version

    def __eq__(self, other):
        """ Define an equality test. """
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        """ Define an non-equality test. """
        if isinstance(other, self.__class__):
            return self.__dict__ != other.__dict__
        return NotImplemented

    def __hash__(self):
        """ Define a hash operation. """
        return hash(tuple(sorted(self.__dict__.items())))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, version):
        # Check that the specified version is None, or is a valid version.
        if version is not None and not Version.valid(version):
            raise ValueError(Version.invalidReason(version))
        self._version = version
        
    def __repr__(self):
        s = self.name
        if self.version is not None:
            s += ':%s' % self.version
        return s

    # @Override
    def __eq__(self, other):
        try:
            result = self.name == other.name and self.version == other.version
        except:
            result = False
        return result

    # createFrom(PackageIdentifier)
    # createFrom(Package)
    # createFrom('geoserver')
    # createFrom('geoserver:2.5.1')
    # createFrom('geoserver:2.5.1-SNAPSHOT')
    # createFrom({'name':'geoserver'})
    @staticmethod
    def createFrom(value=None):
        # Check that a value was specified.
        if value is None:
            raise ValueError("Cannot create package identifier: no value specified")
        # Check if the value is already a package identifier.
        if isInstanceOf(value, PackageIdentifier):
            return PackageIdentifier(name=value.name, version=value.version)
        # Parse the value if it is a string.
        if isinstance(value, types.StringTypes):
            return PackageIdentifier.parseString(value)
        # Check if the value is a dict with 'name', 'version' elements.
        if isinstance(value, types.DictType):
            name = value.get('name')
            version = value.get('version')
            return PackageIdentifier(name=name, version=version)
        # Check if the value has 'name', 'version', 'timestamp' properties.
        if hasattr(value, 'name'):
            name = str(value.name) if hasattr(value, 'name') else None
            version = str(value.version) if hasattr(value, 'version') else None
            return PackageIdentifier(name=name, version=version)
        # The value type is unsupported.
        raise TypeError('Cannot create PackageIdentifier using type %s' % type(value))

    @staticmethod
    def parseString(string):
        # Pre-condition checks.
        if string is None:
            raise ValueError("No value specified for parsing package identifier.")

        remaining = string.strip()
        version = None

        # Check for a version part (if any).
        if ':' in remaining:
            parts = remaining.split(':')
            if len(parts) != 2:
                raise ValueError("Invalid package identifier: '%s'" % string)
            remaining = parts[0].strip()
            version = parts[1].strip()

        return PackageIdentifier(name=remaining, version=version)


def createPackageIdentifier(object=None):
    return PackageIdentifier.createFrom(object)


class PackageDependency(PackageIdentifier):

    """ Class representing a package dependency of the form name[':' version]['@' target]. """

    def __init__(self, name, version=None, target=None):
        # Verify that name is specified.
        if name is None:
            raise ValueError("Cannot create package dependency: no name specified.")
        super(PackageDependency, self).__init__(name, version)
        self._target = target

    def __repr__(self):
        s = super(PackageDependency, self).__repr__()
        if self.target is not None:
            s += '@%s' % self.target
        return s

    def __eq__(self, other):
        try:
            result = super(PackageDependency, self).__eq__(other) and (self._target == other.target)
        except:
            result = False
        return result

    @property
    def string(self):
        """ Get the string representation of the package dependency. Delegates to __repr__. """
        return self.__repr__()

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, target):
        self._target = target

    @staticmethod
    def createFrom(object):
        # Check that an object was specified.
        if object is None:
            raise ValueError("No object specified")
        # Check if the object is already a package dependency.
        if isInstanceOf(object, PackageDependency):
            return object
        # Check if the object is a PackageIdentifier.
        if isInstanceOf(object, PackageIdentifier):
            return PackageDependency(name=object.name, version=object.version)
        # Parse the object if it is a string.
        if isinstance(object, types.StringTypes):
            return PackageDependency.parseString(object)
        # Check if the object is a dict with 'name', 'version', 'target' elements.
        if isinstance(object, types.DictType):
            name = object.get('name')
            version = object.get('version')
            target = object.get('target')
            return PackageDependency(name=name, version=version, target=target)
        # Check if the object is a structure with 'name', 'version', 'target' properties.
        if hasattr(object, 'name'):
            name = object.name if hasattr(object, 'name') else None
            version = object.version if hasattr(object, 'version') else None
            target = object.target if hasattr(object, 'target') else None
            return PackageDependency(name=name, version=version, target=target)
        # The object type is unsupported.
        raise TypeError('Cannot create PackageDependency using type %s' % type(object))

    @staticmethod
    def parseString(string=''):
        remaining = string
        target = None

        # Strip away target, if present.
        if '@' in remaining:
            parts = remaining.split('@')
            if len(parts) > 2:
                raise PackageError("Invalid package dependency: '%s'" % string)
            remaining = parts[0]
            target = parts[1]

        # Parse the remaining string as a package identifier.
        id = PackageIdentifier.parseString(remaining)

        # Create a package dependency from the package identifier and the target (if any).
        return PackageDependency(name=id.name, version=id.version, target=target)


class Package(object):
    
    """ Class representing a package. A package has at minimum a name and a version, and can be installed. """
    
    def __init__(self, config=None, name=None, version=None, description=None, dependencies=None, timestamp=None):
        # Assign default values.
        self._name = name
        self._version = version
        self._type = None
        self._description = description
        self._dependencies = dependencies
        self._symlink = None
        self._timestamp = timestamp
        self._url = None
        self._path = None
        # Update values if a config is provided.
        if config is not None:
            if isinstance(config, types.StringTypes):
                # Examples: 'foo:1.0', 'foo:1.0-SNAPSHOT', 'foo:1.0@10000') 
                # Check for timestamp in the config string, e.g. 'foo:1.0@10000'.
                if '@' in config:
                    pos = config.index('@')
                    self._timestamp = config[pos+1:]
                    config = config[:pos]
                id = PackageIdentifier.createFrom(config)
                self._name = id.name
                self._version = id.version
            elif isInstanceOf(config, PackageConfig) or isInstanceOf(config, Package):
                self._name = config.name
                self._version = config.version
                self._type = config.type
                self._description = config.description
                self._dependencies = [PackageDependency.createFrom(d) for d in config.dependencies]
                self._symlink = config.symlink
                self._timestamp = config.timestamp
            elif isInstanceOf(config, PackageIdentifier):
                self._name = config.name
                self._version = config.version
            # TODO support dict
            else:
                raise TypeError("Cannot create package: unsupported config type %s" % type(config))
        # Check that the version (if specified) is valid.
        if self._version is not None and not Version.valid(self._version):
            raise ValueError(Version.invalidReason(self._version))

    def __eq__(self, other):
        """ Define an equality test. """
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        """ Define an non-equality test. """
        if isinstance(other, self.__class__):
            return self.__dict__ != other.__dict__
        return NotImplemented

    def __hash__(self):
        """ Define a hash operation. """
        return hash(tuple(sorted(self.__dict__.items())))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, version):
        self._version = version
        # Check that the version is valid.
        if version is not None and not Version.valid(version):
            raise ValueError(Version.invalidReason(version))

    @property
    def id(self):
        """ Get the package identifier for the package. """
        return str(PackageIdentifier.createFrom(self))

    @property
    def type(self):
        return 'bundle' if self._type is None else self._type
    
    @type.setter
    def type(self, type):
        self._type = type
        
    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def dependencies(self):
        return self._dependencies or []

    @dependencies.setter
    def dependencies(self, dependencies):
        self._dependencies = dependencies

    @property
    def symlink(self):
        return self._symlink

    @symlink.setter
    def symlink(self, symlink):
        self._symlink = symlink

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def path(self):
        """ Get the path of the package. This is only relevant for installed packages, e.g. PathPackage"""
        return self._path
    
    @path.setter
    def path(self, path):
        self._path = path
        
    def installTo(self, path):
        """ Install the package to the specified path, e.g. '/mstar/packages/foo/1.0'. """
        if path is None:
            raise ValueError("Cannot install package %s: no path specified." % self)
        # Verify that the destination path does not already exist (otherwise installing
        # one package over another; use replacePackage() if that is required).
        if os.path.exists(path):
            raise PackageError("Cannot install package %s to path %s: already exists." % (self, path))
        # Install the package contents, then create the package config (if required).
        # try:
        self._installPackageContentsTo(path)
        # except Exception as e:
        #     print "## failed to install package %s to path %s" % (self, path)
        #     raise PackageError("Failed to install package %s: %s" % (self, e))
        if not os.path.exists(path):
            raise PackageError("Package installed but path %s does not exist." % path)
        if not PackageConfig.containsConfig(path):
            self.config.store(path)
        # TODO return PathPackage(path) ?

    def _installPackageContentsTo(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
    
    def __repr__(self):
        result = self.name
        if self.version is not None:
            result += ':' + self.version
            # # Append the timestamp (if any) if the version is a snapshot.
            # if self.version.endswith('-SNAPSHOT') and self.timestamp is not None:
            #     result += '@' + self.timestamp
        return result

    def isSnapshot(self):
        """ Determines if the package represents a snapshot. """
        return self.version is not None and Version.isSnapshot(self.version)

    @property
    def config(self):
        config = PackageConfig()
        config.name = self.name
        config.version = self.version
        config.timestamp = self.timestamp
        config.description = self.description
        config.dependencies = [str(d) for d in self.dependencies]
        config.symlink = self.symlink
        return config

    @classmethod
    def createFrom(cls, value):
        """ Create a package from a value. """
        if value is None:
            raise ValueError("Cannot create package: no value specified.")
        # If the value is already a package -> just return it.
        if isInstanceOf(value, Package):
            return value
        # If the value is a PackageConfig -> create package from config.
        if isInstanceOf(value, PackageConfig):
            return Package(name=value.name, version=value.version, description=value.description,
                           dependencies=value.dependencies, timestamp=value.timestamp)
        # If the value is a string -> parse into name[:version][@timestamp]
        if isinstance(value, types.StringTypes):
            return Package(config=value)
        raise TypeError("Cannot create package from value of type %s" % type(value))
    
    @classmethod
    def load(cls, path):
        """ Load a package from a path, which may represent a directory, or a zip file. """
        if path is None:
            raise ValueError("Cannot load package: no path specified.")
        if not isinstance(path, types.StringTypes):
            raise TypeError("Cannot load package: path is not a string.")
        # If the path represents a zip file -> CompressedPackage
        from zipfile import is_zipfile
        if is_zipfile(path):
            return CompressedPackage(path)
        # If the path represents a directory -> PathPackage
        if os.path.isdir(path):
            # Check that the directory contains a package config file.
            if not PackageConfig.containsConfig(path):
                raise InvalidPackageError("No package defined in directory '%s'." % path)
            return PathPackage(path)
        # TODO if path represents a URL -> remote repository
        raise ValueError("Cannot load package: path is not a zip file or a directory.")
    
class UnresolvedPackage(Package):
    
    """ Class representing a package that is unresolved. """
    
    def __init__(self, id):
        super(UnresolvedPackage, self).__init__(None)
        id = PackageIdentifier.createFrom(id)
        self.name = id.name
        self.version = id.version
        
class LazilyConfiguredPackage(Package):

    """ A package that uses a lazily-loaded config to derive properties. """

    def __init__(self, config=None):
        super(LazilyConfiguredPackage, self).__init__(config)
        self._config = config

    @property
    def config(self):
        if self._config is None:
            self._config = self._loadConfig()
        return self._config

    def _loadConfig(self):
        """ Load the package configuration. Subclasses implement this method. """
        raise NotImplementedError("No package config available.")

    @Package.name.getter
    def name(self):
        if self._name is None:
            self._name = self.config.name
        return self._name

    @Package.version.getter
    def version(self):
        if self._version is None:
            self._version = self.config.version
        return self._version

    @Package.type.getter
    def type(self):
        if self._type is None:
            self._type = self.config.type
        return self._type

    @Package.description.getter
    def description(self):
        if self._description is None:
            self._description = self.config.description
        return self._description

    @Package.dependencies.getter
    def dependencies(self):
        if self._dependencies is None:
            self._dependencies = [PackageDependency.createFrom(d) for d in self.config.dependencies]
        return self._dependencies

    @Package.symlink.getter
    def symlink(self):
        if self._symlink is None:
            self._symlink = self.config.symlink
        return self._symlink

    @Package.timestamp.getter
    def timestamp(self):
        if self._timestamp is None:
            if self.config.timestamp is None:
                raise RuntimeError("Package %s has no timestamp." % self)
            self._timestamp = self.config.timestamp
        return self._timestamp
    
class PathPackage(LazilyConfiguredPackage):
    
    """ A package contained within a directory, e.g. 'c:\mstar\packages\geoserver\2.5.1' """
    
    def __init__(self, path, config=None):
        if path is None:
            raise ValueError("Cannot create package: 'path' not specified")
        if not os.path.exists(path):
            raise ValueError("Cannot create package: path '%s' not found" % path)
        if not os.path.isdir(path):
            raise ValueError("Cannot create package: path '%s' is not a directory" % path)
        # Create a package config, if none provided and if one exists on the path.
        if config is None and PackageConfig.containsConfig(path):
            config = PackageConfig.load(path)
        # Initialize super class with the (possible) config.
        super(PathPackage, self).__init__(config=config)
        self.path = path

    # @Override    
    def _loadConfig(self):
        if not PackageConfig.containsConfig(self.path):
            raise UnresolvedPackageError("Could not find configuration file for package at %s." % self.path)
        return PackageConfig.load(self.path)

    # @Override
    def _installPackageContentsTo(self, path):
        # Copy the package contents to the specified path.
        FileOps.getFileOps().copyDir(self.path, path)

class CompressedPackage(LazilyConfiguredPackage):

    """ A package represented by a zip file. The config can be specified in the constructor, 
        otherwise the config is assumed to exist in the base directory of the zipfile. """

    def __init__(self, zipfile, prefix=None, config=None):
        super(CompressedPackage, self).__init__(config=config)
        if zipfile is None:
            raise ValueError("No zip file specified")
        if not is_zipfile(zipfile):
            raise ValueError('Expected a zip file: %s' % zipfile)
        self._zipfile = zipfile
        self._prefix = prefix
        # If a package config was not provided, verify that a package config exists in the archive.
        if self._config is None and not self.containsPackageConfig():
            raise InvalidPackageError("Compressed package %s does not contain a package config." % zipfile)
        
    def containsPackageConfig(self):
        """ Determines if the zip file contains a package config. """
        return self.containsFile(PackageConfig.filename())

    @property
    def zipfile(self):
        return self._zipfile

    @property
    def prefix(self):
        return self._prefix
    
    # @Override
    def _loadConfig(self):
        zip = ZipFile(self.zipfile, 'r')
        try:
            return self.__loadPackageConfigFromZip(zip)
        finally:
            zip.close()

    # @Override
    def _installPackageContentsTo(self, path):
        # print '  Unpacking %s%s to %s ...' % (self.zipfile, ("/%s" % self.prefix if self.prefix is not None else ""), path)
        with ZipFile(self.zipfile, 'r') as zip:
            # TODO this could be a security risk if the zip file is unsigned and has items such as '/Windows/sneaky.exe'
            # TODO consider unpacking each item in the zip file, checking its path
            # TODO fixed in python 2.7.4 ?
            self.__extractSubsetToPath(zip, path) if self._prefix else self.__extractAllToPath(zip, path)
            # Write package config file manually if not embedded in zip file.
            if not self.containsPackageConfig():
                # Use 'self._config', as 'self.config' will just load from the zip file. 
                if self._config is None:
                    raise RuntimeError("No package config found in compressed package at %s" % path)
                self._config.store(path)

    def __extractSubsetToPath(self, zip, path):
        """ Extract a subset of items in the zip file, using the prefix. """
        prefixLen = len(self.prefix)
        for zipinfo in zip.infolist():
            name = zipinfo.filename
            if name.startswith(self.prefix) and len(name) > prefixLen:
                zipinfo.filename = name[prefixLen:]
                zip.extract(zipinfo, path)
    
    def __extractAllToPath(self, zip, path):
        """ Extract all items in the zip file. """
        zip.extractall(path)
        
    def __loadPackageConfigFromZip(self, zip):
        """ Load the package configuration contained within the zip file. """
        def prefixed(path): return self._prefixed(path)
        with zip.open(prefixed(PackageConfig.filename()), 'r') as f:
            try:
                return PackageConfig(f)
            except Exception as e:
                raise PackageError('Could not load package configuration file: %s' % e)

    def containsFile(self, path):
        """ Determines if the file exists in the zip at the specified path. """
        if path is None:
            raise ValueError("Cannot determine if compressed package contains file: no path specified.")
        def prefixed(path): return self._prefixed(path)
        zip = ZipFile(self.zipfile, 'r')
        try:    
            with zip.open(prefixed(path), 'r'):
                return True
        except Exception:
            return False
        finally:
            zip.close()
    
    def _prefixed(self, path):
        """ Adds prefix to the path (if required). """
        if self._prefix is not None:
            path = "%s%s" % (self._prefix, path)
        return path
    
class RemotePackage(LazilyConfiguredPackage):
    
    """ A package that is hosted remotely (typically as a zip file). """
    
    def __init__(self, url):
        super(RemotePackage, self).__init__()
        if url is None:
            raise ValueError("No URL specified")
        # TODO validate the URL
        self._url = url

    @property
    def url(self):
        return self._url
        
    # TODO loadConfig() -> url.get('/package.ini')
    # TODO installTo(path) -> copy zip file url.get('/package.zip') to temporary directory
    #                      -> unpack zip file to path

class ComponentPackage(PathPackage):

    """ Package for an mstar component, e.g. geoserver, mstar, etc. Installing
        the component 'foo' will copy /mstar/foo to /mstar/packages/foo/1.2.3 """

    def __init__(self, path, config):
        super(ComponentPackage, self).__init__(path, config)

    # @Override
    def _installPackageContentsTo(self, path):
        # Copy the package content.
        from fileOps import FileOps
        FileOps.getFileOps().copyDir(self.path, path)
        # Write the package config.
        self.config.store(path)

class BootstrapPackage(Package):

    """ Bootstrap package for an mstar bundle, e.g. system. Installs a config file only. """

    def __init__(self, config):
        super(BootstrapPackage, self).__init__(config)

    # @Override
    def installTo(self, path):
        # Create the path if necessary.
        if not os.path.exists(path):
            os.makedirs(path)
        # Write the package configuration to the path.
        self.config.store(path)

def isMatchingPackage(p1, p2):
    """ Determines if two packages match (same name and version). """
    if p1 is None: raise ValueError("Cannot compare packages: first package specified.")
    if p2 is None: raise ValueError("Cannot compare packages: second package not specified.")
    return isMatchingPackageName(p1, p2) and isMatchingPackageVersion(p1, p2)


def isMatchingPackageName(p1, p2):
    """ Determines if the package names match. """
    if p1 is None: raise ValueError("Cannot compare packages: first package specified.")
    if p2 is None: raise ValueError("Cannot compare packages: second package not specified.")
    return p1.name.lower() == p2.name.lower()


def isMatchingPackageVersion(p1, p2):
    """ Determines if the package versions match, e.g. '1' matches '1' and '1.0'. """
    if p1 is None: raise ValueError("Cannot compare packages: first package specified.")
    if p2 is None: raise ValueError("Cannot compare packages: second package not specified.")
    return comparePackageVersions(p1, p2) == 0


def findPackageWithMaximumVersion(packages=[]):
    """ Find the package with the maximum version in a collection of packages. """
    maximum = None
    for package in packages:
        if maximum is None or comparePackageVersions(maximum,package) < 0:
            maximum = package
    return maximum


def findPackageWithMinimumVersion(packages=[]):
    """ Find the package with the minimum version in a collection of packages. """
    minimum = None
    for package in packages:
        if minimum is None or comparePackageVersions(minimum,package) > 0:
            minimum = package
    return minimum


def comparePackageVersions(p1, p2):
    """ 
    Compare the versions of two packages. Timestamps are not considered.
     
    :param p1: the first package. Must not be None.
    :param p2: the second package. Must not be None.

    :return: -1, 0, or +1 depending on the comparison of the version of the first package to
    the version of the second package. 
    """
    assertIsInstanceOf('p1', p1, Package)
    assertIsInstanceOf('p2', p2, Package)
    return Version.compare(p1.version, p2.version)


def getPackageDependencies(package, overrides=None):
    """ Get the dependencies for the package, taking overrides (if any) into account. The
        overrides are a map of package name to a package dependency id, e.g.
        {'jdk':'jdk:1.8.1', 'geoserver':'geoserver:1.0@server'}, etc. """
    # Pre-condition checks.
    assertIsNotNone('package', package)
    assertIsInstanceOf('package', package, Package)

    overrides = overrides or {}
    dependencies = []
    for dependency in package.dependencies:
        if dependency.name in overrides:
            dependency = overrides[dependency.name]
        dependencies.append(dependency)
    return dependencies


def replacingSnapshot(availablePackage, installedPackage):
    """ Returns True if the first snapshot package replaces the second snapshot package. """
    return availablePackage.isSnapshot() and installedPackage.isSnapshot() \
           and availablePackage.timestamp > installedPackage.timestamp
