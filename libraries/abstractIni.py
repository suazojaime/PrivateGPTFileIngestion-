import cStringIO

from ConfigParser import ConfigParser
from configs import AbstractConfig


def hasFunction(object, methodName):
    """ Determines if the object has a named function (a callable property). """
    return hasattr(object, methodName) and callable(getattr(object, methodName))


class AbstractIni(AbstractConfig):

    """ Base class for operations on a *.ini file. """
    
    def __init__(self, source=None):
        """
        Create an abstract ini from the source.

        @param source the source of the initialization data. May be None (no initialization),
        or a file object (representing path to the initialization file, or an object with a
        'readfp()' or 'readlines()' method for reading the initialization data.
        """
        super(AbstractIni, self).__init__()
        # Set default values.
        self._parser = ConfigParser()
        # Nothing to do if source is None.
        if source is None:
            pass
        # If the source is a file, then load the config from the file.
        elif isinstance(source, file):
            self._parser.readfp(source)
        # If the source has a readfp() function, then load the config from the file
        # (e.g. from a File object).
        elif hasFunction(source, 'readfp'):
            self._parser.readfp(source)
        # If the source has a readlines() function, then load the config from the 
        # lines (e.g. from a ZipFile object).
        elif hasFunction(source, 'readlines'):
            text = listToString(source.readlines(), '')
            self._parser.readfp(cStringIO.StringIO(text))
        else:
            raise TypeError('Unsupported source type: %s' % type(source))

    def __repr__(self):
        return "{name:%s,version:%s}" % (self.name,self.version)
    
    @property
    def parser(self):
        return self._parser

    def hasSection(self, section):
        """ Determine if the section is present. """
        return self.parser.has_section(section)

    def hasOption(self, section, option):
        """ Determine if the section contains the option. """
        return self.parser.has_option(section, option)
    
    def getOption(self, section, option):
        """ Get the option in the section, or die. """
        if self.hasOption(section, option):
            return self.parser.get(section, option)
        raise KeyError("Missing option '%s' in section '%s' of configuration file" % (option, section))

    def getOptionWithDefault(self, section, option, defaultValue=None):
        """ Get the option in the section, or return a default value. """
        if self.hasOption(section, option):
            return self.parser.get(section, option)
        return defaultValue
    
    def getOptions(self, section):
        """ Get the options in the section. Returns empty collection if the section does not exist. """
        options = []
        if self.parser.has_section(section):
            options = self.parser.options(section)
        return options

    # @Override
    def dump(self):
        return '\n'.join(self.lines)

    # @Override
    def writefp(self, f):
        for line in self.lines:
            f.write(line + "\n")

    @classmethod
    def readfp(cls, fp):
        return cls(fp)

    @property
    def lines(self):
        return self.linesToWrite()

    def linesToWrite(self):
        """ Return the collection of lines to write to the configuration file. """
        raise NotImplementedError()


def stringToList(string, separator=','):
    """ Split a single line into a list, using the separator character (defaults to ','). """
    return singleLineStringToList(string, separator)

def listToString(list, separator=','):
    """ Convert a list to a string, joining on the separator (defaults to ','). """
    return separator.join(list)

def singleLineStringToList(string, separator=','):
    """ Split a single line into a list, using the separator character (defaults to ','). """
    # TODO check if the separator char is escaped, e.g. 'x\,y,z' represents list ['x,y', 'z'].
    strings = []
    for p in string.split(separator):
        p = p.strip()
        if p is not "":
            strings.append(p)
    return strings

def multiLineStringToList(string):
    """ Split a multiple-line string into a list, splitting on line breaks. """
    strings = []
    for p in string.splitlines():
        p = p.strip()
        if p is not "":
            strings.append(p)
    return strings

def escape(string):
    """ Escape characters that are not legal in a configuration value. """
    for ch in ':#=;':
        string = string.replace(ch, '\\%s' % ch)
    return string
