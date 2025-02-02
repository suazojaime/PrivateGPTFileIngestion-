from configs import AbstractConfig
from types import DictType, ListType, StringTypes


class PropertiesConfig(AbstractConfig):

    """ Class for processing a properties configuration file, with lines of the form 'x=y'. """

    def __init__(self, properties={}):
        super(PropertiesConfig, self).__init__()
        # If properties are specified, must be a map.
        if properties is not None and not isinstance(properties, DictType):
            raise TypeError("Cannot create %s: unsupported properties of type %s." % (self.filedesc(), type(properties)))
        self._properties = properties or {}

    @classmethod
    def filename(cls):
        return 'Properties.config'

    @classmethod
    def filedesc(cls):
        return "Properties config"

    @property
    def properties(self):
        return self._properties

    # Allows "config['x']" instead of "config.properties['x']", etc.
    def __getitem__(self, item, defaultValue=None):
        return self._getProperty(name=item, defaultValue=defaultValue)

    # Allows "config['x'] = 1" instead of "config.properties['x'] = 1", etc.
    def __setitem__(self, key, value):
        self._setProperty(name=key, value=value)

    # Allows "if 'x' in config", etc.
    def __contains__(self, item):
        return self.properties.__contains__(item)

    def _getProperty(self, name, defaultValue=None):
        """ Get the value of the named property, with fallback to the default value if the property is not found. """
        return self.properties.get(name, defaultValue)

    def _setProperty(self, name, value):
        """ Set the value of the named property. A value of None will delete the property. """
        if value is None:
            if name in self.properties:
                del self.properties[name]
        else:
            self.properties[name] = value

    # @Override
    def dump(self):
        return str(self.properties)

    @classmethod
    def readfp(cls, f):
        processor = lambda x,y: cls.processLoadedProperty(x, y)
        properties = PropertiesLoader(processor=processor).load(f)
        return cls(properties=properties)

    def writefp(self, f):
        processor = lambda x, y: self.processStoredProperty(x, y)
        PropertiesStorer(processor=processor).store(self.properties, f)

    @classmethod
    def processLoadedProperty(cls, name, value):
        """ Get the property processor used by the implementation when loading properties. Subclasses
            may map the name or the value of the loaded property, etc. """
        return (name, value)

    @classmethod
    def processStoredProperty(cls, name, value):
        """ Get the properties processor used by the implementation when storing properties. Subclasses
            may map the name or the value of the stored property, etc. """
        return (name, value)


class PropertyConverter:

    """ Class for converting property values to other types. """

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def toList(self):
        """ Convert the property value to a list object. """
        if self.value is None:
            return None
        if isinstance(self.value, ListType):
            return self.value
        if isinstance(self.value, StringTypes):
            return self.value.split(',')
        raise TypeError("Cannot convert property %s with type %s to a list." % (self.name, type(self.value)))

    def toString(self):
        """ Convert the property value to a string object. """
        if self.value is None:
            return None
        if isinstance(self.value, StringTypes):
            return self.value
        if isinstance(self.value, ListType):
            return ','.join(self.value)
        return str(self.value)


class PropertiesStorer:

    """ Class for storing properties. """

    def __init__(self, processor=None):
        if processor is None:
            processor = lambda x, y: (x, y)
        self.processor = processor

    def store(self, properties, fp):
        """ Store properties to the file object. """
        for name in sorted(properties.iterkeys()):
            value = properties.get(name)
            (name, value) = self.processor(name, value)
            if name is not None:
                fp.write("%s=%s\n" % (self.escape(name), self.escape(str(value)) if value else ''))

    def escape(self, string):
        for s in ['\\', '=', ' ']:
            string = string.replace(s, '\\%s' % s)
        return string


class PropertiesLoader(object):

    """ Class for loading properties. """

    def __init__(self, processor=None):
        if processor is None:
            processor = lambda x, y: (x, y)
        self.processor = processor

    def load(self, fp):
        """ Load properties from the file object. """
        # Check that the path is valid for loading.
        # Load the properties.
        # TODO not using loadJavaStyleProperties() ... didn't work for some reason.
        # TODO need to handle multi-line values, escaped characters, etc.
        properties = {}
        for line in fp:
            if not self._skipLine(line):
                (name, value) = line.split('=', 1)  # TODO this does not handle escaped '=' !
                (name, value) = self.processor(self.unescape(name.strip()), self.unescape(value.strip()))
                if name is not None and value is not None:
                    properties[name] = value
        return properties

    def _skipLine(self, line):
        line = line.strip()
        return not line or line.startswith('#') or line.startswith(';') or line.startswith('\n')

    def unescape(self, string):
        for s in ['=', ' ', '\\']:
            string = string.replace('\\%s' % s, s)
        return string
