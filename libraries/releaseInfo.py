from propertiesConfig import PropertiesConfig
from types import DictType, StringTypes


class ReleaseInfo(PropertiesConfig):

    """ Class for handling release info properties file. """

    def __init__(self, properties={}, major=None, minor=None, majorShort=None, version=None, revision=None):
        super(ReleaseInfo, self).__init__(properties)
        self.major = major if major is not None else self.major
        self.minor = minor if minor is not None else self.minor
        self.majorShort = majorShort if majorShort is not None else self.majorShort
        self.revision = revision if revision is not None else self.revision
        if version is not None: self.version = version
        self._version = None
        
    @classmethod
    def filename(cls):
        return 'releaseInfo.txt'

    @classmethod
    def filedesc(cls):
        return "Release Info"

    @property
    def major(self):
        return self._getProperty('MAJOR')

    @major.setter
    def major(self, major):
        self._setProperty('MAJOR', major)

    @property
    def minor(self):
        return self._getProperty('MINOR')

    @minor.setter
    def minor(self, minor):
        self._setProperty('MINOR', minor)

    @property
    def majorShort(self):
        return self._getProperty('MAJOR_SHORT')

    @majorShort.setter
    def majorShort(self, majorShort):
        self._setProperty('MAJOR_SHORT', majorShort)

    @property
    def version(self):
        if self._version is None:
            self._version = self._lookupVersion()
        return self._version
        
    def _lookupVersion(self):
        # TODO verify that 'VERSION' appears in releaseInfo.txt
        version = self._getProperty('VERSION')
        if version is None:
            # Get the MAJOR version, with optional MINOR version.
            version = self._getProperty('MAJOR')
            if version is not None and 'MINOR' in self._properties:
                minor = self._getProperty('MINOR')
                version = version + "-" + minor
        return version

    @version.setter
    def version(self, version):
        self._setProperty('VERSION', version)

    @property
    def revision(self):
        return self._getProperty('REVISION')

    @revision.setter
    def revision(self, revision):
        self._setProperty('REVISION', revision)

    @classmethod
    def createFrom(cls, object):
        """ Create a release info from the object (may be a ReleaseInfo, or a map). """
        # TODO consider removing this method?
        # Check for null.
        if object is None:
            return None
        # Check if object is already a release info.
        if isinstance(object, ReleaseInfo):
            return object
        # Check if the object is string, e.g. '1.2.3-SNAPSHOT'
        if isinstance(object, StringTypes):
            releaseInfo = ReleaseInfo()
            def splitIntoMajorAndMinor(s):
                parts = s.split('-', 1)
                major = parts[0]
                minor = None if len(parts) <= 1 else parts[1]
                return (major, minor)
            (releaseInfo.major, releaseInfo.minor) = splitIntoMajorAndMinor(object)
            return releaseInfo
        # Check if the object is a map.
        if isinstance(object, DictType):
            releaseInfo = ReleaseInfo()
            for name in ['major', 'minor', 'minorShort', 'version', 'revision']:
                if name in object:
                    releaseInfo.__setattr__(name, object[name])
            return releaseInfo
        raise TypeError("Cannot create release info: unsupported type %s" % type(object))
