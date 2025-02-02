from lineOps import cleanLine


class Annotation(object):

    """ An annotation contains a name, and optionally arguments, e.g. '@readOnly', '@label foo'. """

    def __init__(self, name, arguments=None):
        self.name = name
        self.arguments = arguments

    def __repr__(self):
        return '@%s' % self.name if self.arguments is None else '@%s %s' % (self.name, self.arguments)

    @classmethod
    def parseLine(cls, line=None):
        """ Create an annotation by parsing a line, e.g. '@readOnly', '@label foo'. Returns None if the line is not an annotation. """
        annotation = None
        if line is not None and line.startswith('@'):
            tokens = cleanLine(line[1:]).split(' ')
            if len(tokens) == 1:
                annotation = cls(tokens[0])
            elif len(tokens) > 1:
                name = tokens[0]
                arguments = cleanLine(line[len(name)+1:])
                annotation = cls(name, arguments)
        return annotation

    @classmethod
    def parseLines(cls, lines=[]):
        """ Create a list of annotations by parsing a list of lines, e.g. ['@readOnly', '@label foo']. May return an empty list. """
        annotations = []
        for line in lines:
            annotation = cls.parseLine(line)
            if annotation is not None:
                annotations.append(cls.parseLine(line))
        return annotations


class AnnotatedProperty(object):

    """ A property that contains annotations. """

    class Type:

        String = "string"
        Map = "map"
        Integer = "integer"

    PROPERTIES_WITH_TYPE_MAP = ["_DB_SERVER_ROLES", "_DB_SERVER_ROLES_REPORTING", "_DB_PORT"]

    def __init__(self, name, value, annotations=[]):
        self.name = name                   # String
        self.value = value                 # String
        self.annotations = annotations     # List<Annotation>
        self.type = AnnotatedProperty.Type.String
        if name in self.PROPERTIES_WITH_TYPE_MAP:
            self.type = AnnotatedProperty.Type.Map

    def __repr__(self):
        return "{name:%s,value:%s,annotations:%s}" % (self.name, self.value, self.annotations)

    def hasAnnotation(self, annotationName):
        """ Determine if the property contains an annotation with the specified name. """
        return annotationName in self.getAnnotationNames()

    def getAnnotation(self, annotationName):
        """ Get the annotation with the specified name, or None if the annotation cannot be found. """
        if self.annotations is not None:
            for annotation in self.annotations:
                if annotation.name == annotationName:
                    return annotation
        return None

    def getAnnotationNames(self):
        """ Get a list of the annotation names. """
        return [x.name for x in self.annotations]
    
    @property
    def secure(self):
        return 'secure' in self.getAnnotationNames()

    def stringToValue(self, s):
        """Convert a string to a value of this property's type."""
        if s is None:
            return None
        if self.type is AnnotatedProperty.Type.String:
            return "%s" % s
        if self.type is AnnotatedProperty.Type.Integer:
            return "%d" % s
        if self.type is AnnotatedProperty.Type.Map:
            return Conversions.valueToMap(s)
        return s

    def valueToString(self, value):
        """Convert a value of this property's type to a string."""
        if value is None:
            return None
        if self.type is AnnotatedProperty.Type.String:
            return value
        if self.type is AnnotatedProperty.Type.Integer:
            return "%d" % value
        if self.type is AnnotatedProperty.Type.Map:
            return Conversions.mapToString(value)

    class Filters:
        
        @classmethod
        def isSecure(cls, p):
            return p is not None and p.secure
        
        @classmethod
        def isNotSecure(cls, p):
            return not cls.isSecure(p)
        
class AnnotatedProperties(object):

    """ A map of (name => AnnotatedProperty) and associated operations. """

    def __init__(self, map={}):
        self._map = map

    def getProperties(self):
        """ Get the map of property names to annotated properties. """
        return self._map

    def hasProperty(self, name):
        """ Determines if the property is present. """
        return name in self._map

    def getProperty(self, name):
        """ Get the annotated property associated with the property name, or None if not found. """
        return self._map[name] if name in self._map else None

    @classmethod
    def getPropertiesWithAnnotation(cls, annotationName, annotationsMap={}):
        """ Get the properties with the annotation name. Returns (possibly empty) list. """
        result = {}
        for propertyName in annotationsMap:
            property = annotationsMap[propertyName]
            if property.hasAnnotation(annotationName):
                result[propertyName] = property
        return result

    @classmethod
    def loadFromFile(cls, file):
        """ Load the annotated properties from the file. """
        return cls.loadFromLines(lines=_loadLinesFromFile(file), map={})

    @classmethod
    def loadFromBundle(cls, bundle=[]):
        """ Load the annotated properties from a bundle. Returns Map<PropertyName,AnnotatedProperty>. """
        map = {}
        for file in bundle:
            lines = _loadLinesFromFile(file)
            cls.loadFromLinesIntoMap(lines, map)
        return map
    
    @classmethod
    def loadFromLines(cls, lines=[], map={}):
        """ Load the annotated properties from the list of lines. """
        return cls.loadFromLinesIntoMap(lines, map)

    @classmethod
    def loadFromLinesIntoMap(cls, lines=[], map={}):
        comments = []
        for line in lines:
            if line.startswith('#'):
                from lineOps import cleanLine
                comments.append(cleanLine(line[1:]))
            elif len(line) == 0:
                comments = []
            else:
                (key,value) = _parseKeyAndValue(line)
                annotations = _parseAnnotations(comments)
                map[key] = AnnotatedProperty(key,value,annotations)
                comments = []
        return map
    
def _loadLinesFromFile(file):
    from lineOps import getLinesFromFile, cleanLine
    return [cleanLine(line) for line in getLinesFromFile(file)]

def _parseKeyAndValue(line):
    import propertyFileOps
    return propertyFileOps.parseJavaStylePropertyLine(line)

def _parseAnnotations(comments):
    return Annotation.parseLines(comments)


class Conversions:

    @classmethod
    def valueToMap(cls, v):
        """Convert a value (string, dict) to a map."""
        import types
        if v is None:
            return None
        if isinstance(v, types.DictType):
            return v
        if not isinstance(v, types.StringTypes):
            raise Exception("Cannot convert value to a map: invalid input type")
        return cls._stringToMap(v)

    @classmethod
    def _stringToMap(cls, s):
        if s is None:
            return None
        s = s.strip()
        if not s.startswith("{") or not s.endswith("}"):
            raise Exception("Cannot convert string to a map: invalid format '%s'" % s)
        s = s[1:-1]
        m = {}
        from StringTools import splitString
        for token in splitString(s, separator=","):
            pair = splitString(token, separator=":")
            if len(pair) != 2:
                raise Exception("Cannot convert string to map: invalid map element '%s'" % token)
            m[_stripQuotes(pair[0])] = _stripQuotes(pair[1])
        return m

    @classmethod
    def mapToString(cls, v):
        """Convert a map (string or dict) to a string of form '{\"x\":\"1\", ...}' ."""
        import types
        if v is None:
            return None
        if isinstance(v, types.StringTypes):
            return cls.mapToString(cls.valueToMap(v))
        if not isinstance(v, types.DictType):
            raise Exception("Cannot convert value to a string: '%s' (not a map)" % v)
        items = ["\"%s\":\"%s\"" % (name, value) for (name, value) in v.items()]
        return "{" + ",".join(items) + "}"

def _stripQuotes(s):
    if s is None:
        return s
    s = s.strip()
    if len(s) < 2:
        return s
    if s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    if s[0] == "'" and s[-1] == "'":
        return s[1:-1]
    return s
