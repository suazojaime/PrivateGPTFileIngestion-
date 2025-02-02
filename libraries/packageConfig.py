from abstractIni import AbstractIni, multiLineStringToList
from timestampedConfig import Timestamp
from types import DictType, StringTypes
from versions import Version


class PackageConfig(AbstractIni):
    
    """ Operations on a package configuration (contained in a package.ini file). """

    def __init__(self, source=None, name=None, version=None, description=None, timestamp=None, dependencies=None):
        super(PackageConfig, self).__init__(source)
        self._name = name
        self._version = version
        self._description = description
        self._type = None
        self._dependencies = dependencies
        self._symlink = None
        self._timestamp = timestamp
        if version is not None and not Version.valid(version):
            raise ValueError("Cannot create package config: %s" % Version.invalidReason(version))
        
    # @Override
    @classmethod
    def filename(cls):
        return 'package.ini'

    # @Override
    @classmethod
    def filedesc(cls):
        return "Package Configuration"

    @property
    def name(self):
        if self._name is None:
            self._name = self.getOption('Package', 'name')
        return self._name
    
    @name.setter
    def name(self, name):
        self._name = name
        
    @property
    def version(self):
        if self._version is None:
            self._version = self._loadVersion()
        return self._version
    
    def _loadVersion(self):
        version = self.getOption('Package', 'version')
        if not Version.valid(version):
            raise ValueError("Invalid package config: %s" % Version.invalidReason(version))
        return version
    
    @version.setter
    def version(self, version):
        self._version = version
        
    @property
    def description(self):
        if self._description is None:
            self._description = self.getOptionWithDefault('Package', 'description', None)
        return self._description
    
    @description.setter
    def description(self, description):
        self._description = description
        
    @property
    def type(self):
        if self._type is None:
            self._type = self.getOptionWithDefault('Package','type', 'bundle')
        return self._type
    
    @type.setter
    def type(self, type):
        self._type = type
        
    @property
    def dependencies(self):
        if self._dependencies is None:
            self._dependencies = multiLineStringToList(self.getOptionWithDefault('Package', 'dependencies', ''))
        return self._dependencies
    
    @dependencies.setter
    def dependencies(self, dependencies):
        self._dependencies = dependencies

    
    @property
    def symlink(self):
        if self._symlink is None:
            if self.hasOption('Install', 'symlink'):
                self._symlink = self.getOption('Install','symlink')
        return self._symlink

    @symlink.setter
    def symlink(self, symlink):
        self._symlink = symlink

    @property
    def timestamp(self):
        if self._timestamp is None:
            # Use the timestamp in the config, otherwise use the current time.
            if self.hasOption('Install', 'timestamp'):
                self._timestamp = self.getOption('Install', 'timestamp')
            else:
                self._timestamp = Timestamp.now()
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp):
        self._timestamp = timestamp

    # @Override
    def linesToWrite(self):
        lines = [
            '[Package]',
            'name=%s' % self.name,
            'version=%s' % self.version,
            'timestamp=%s' % self.timestamp,
            'type=%s' % self.type
        ]
        
        # Add the description, if any.
        if self.description is not None:
            lines.append('description=%s' % self.description)
            
        # Add the dependencies.
        lines.append('dependencies=')
        for dependency in self.dependencies:
            lines.append('  %s' % dependency)

        # Add the timestamp.
        lines.append('[Install]')
        lines.append('timestamp=%s' % self.timestamp)
        
        # Add the symlink, if any.
        if self.symlink is not None:
            lines.append('symlink=%s' % self.symlink)

        return lines

    @classmethod
    def createFrom(cls, value):
        """
        Create a PackageConfig from a string or dict, etc.

        If the value is a string, it should be of the form 'name[:version][@timestamp]',
        e.g. 'foo', 'foo:1.0', 'foo:1.0-SNAPSHOT', 'foo:1.0@10000', etc.

        If the value is a dict, it must contain keys 'name', 'version', and may also 
        contain keys 'timestamp', 'description', 'dependencies', etc.
        """
        if value is None:
            raise ValueError("Cannot create package config: no object specified.")
        # Check if the object is already a package config.
        if isinstance(value, PackageConfig):
            return value
        from packages import Package, PackageIdentifier
        if isinstance(value, PackageIdentifier):
            return cls._createFromPackageIdentifier(value)
        if isinstance(value, Package):
            return cls._createFromPackage(value)
        # Check for a string, e.g. 'foo:1.2.3', 'foo:1.2.3@10000', etc.
        if isinstance(value, StringTypes):
            return cls._createFromString(value)
        # Check for a map.
        if isinstance(value, DictType):
            return cls._createFromMap(value)
        raise TypeError("Cannot create package config from object of type %s." % type(value))

    @classmethod
    def _createFromPackageIdentifier(cls, packageId):
        if packageId.version is None:
            raise ValueError("Cannot create package config: no package version specified in package ID '%s'" % packageId)
        return PackageConfig(name=packageId.name, version=packageId.version)
    
    @classmethod
    def _createFromPackage(cls, package):
        config = PackageConfig()
        config.name = package.config.name
        config.version = package.config.version
        config.description = package.config.description
        config.dependencies = package.config.dependencies
        config.symlink = package.config.symlink
        config.type = package.config.type
        return config
    
    @classmethod
    def _createFromString(cls, string):
        remaining = string
        timestamp = None
        
        # String should be of the form name:version[@timestamp]
        if '@' in string:
            parts = string.split('@')
            if len(parts) > 2:
                raise ValueError("Invalid package config string: '%s'" % string)
            remaining = parts[0]
            timestamp = parts[1]
            if not timestamp:
                raise ValueError("Invalid package config string: '%s'" % string)
            
        from packages import PackageIdentifier
        packageId = PackageIdentifier.createFrom(remaining)
        if packageId.version is None:
            raise ValueError("Cannot create package config: no package version specified in string '%s'" % string)
        
        return PackageConfig(name=packageId.name, version=packageId.version, timestamp=timestamp)

    @classmethod
    def _createFromMap(cls, map):
        # Check that the map contains a name.
        if 'name' not in map:
            raise ValueError("Cannot create package config from map: no name specified.")
        config = PackageConfig()
        for (name, value) in map.items():
            setattr(config, name, value)
        return config
