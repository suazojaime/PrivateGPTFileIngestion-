
try:
    from StringIO import StringIO as BytesIO  # python 2
except ImportError:
    from io import BytesIO                    # python3

import ctypes
import struct
import javaobj


class Java:

    """ Class for Java operations. """

    class Convertable(object):

        """ Class for converting to/from javaobj.JavaObject values. """

        def toJavaObject(self):
            """ Convert this object to its equivalent javaobj.JavaObject implementation. """
            raise NotImplementedError

        @classmethod
        def fromJavaObject(cls, object):
            """ Create an object from the equivalent javaobj.JavaObject implementation. """
            raise NotImplementedError

    class Encodable(object):

        """ Class for encoding/decoding javaobj.JavaObject values. """

        def encodeJava(self):
            """ Create a java encoding of the javaobj.JavaObject instance (i.e., serialize). """
            # Default implementation works only for Convertable types.
            if isinstance(self, Java.Convertable):
                return Java.writeJavaObject(self.toJavaObject())
            # Subclasses need to provide implementation.
            raise NotImplementedError

        @classmethod
        def decodeJava(cls, encoding):
            """ Create a javaobj.JavaObject instance from the java encoding (i.e., deserialize). """
            if encoding is None:
                return None
            # Default implementation works only for Convertable types.
            if issubclass(cls, Java.Convertable):
                (object,_) = Java.readJavaObject(encoding)
                return cls.fromJavaObject(object)
            # Subclasses need to provide implementation.
            raise NotImplementedError

    @classmethod
    def pythonByteStringToJavaByteArray(cls, value):
        """ 
        Convert a python byte string value (containing ints in range [0..255])
        to a Java byte[] value (containing bytes in the range [-128..127]).

         :param value the value to convert. May be None, or a byte string (type: bytes).

         :return None of the value is None, else a javaobj.JavaByteArray containing the
         converted bytes of the value.
        """
        # Check for null.
        if value is None:
            return None
        # Check that the python object is a byte string.
        if not isinstance(value, bytes):
            raise ValueError("Cannot convert value of type %s to JavaByteArray." % type(value))
        signedBytes = [ctypes.c_byte(ord(b)).value for b in value]
        data = struct.pack("%db" % len(value), *signedBytes)
        return javaobj.JavaByteArray(data, cls.getClass('[B'))

    @classmethod
    def javaByteArrayToPythonByteString(cls, value):
        """
        Convert the value returned by javaobj for a byte[] (where each byte
        is in the range [-128..127]) to a python byte string (where each byte
        is in the range [0..255]). Return type is 'bytes'.

        :param value None, or a javaobj.JavaByteArray instance.

        :return None if the value is None, else a byte string (type: bytes) containing
        the converted bytes of the JavaByteArray value.
        """
        # Check for null.
        if value is None:
            return None
        # Check that value is a JavaByteArray.
        if not isinstance(value, javaobj.JavaByteArray):
            raise ValueError("Cannot convert value of type %s from a JavaByteArray." % type(value))
        # Note that a JavaByteArray is a subclass of bytearray.
        unsignedBytes = [ctypes.c_ubyte(sb).value for sb in value]
        return struct.pack("%dB" % len(value), *unsignedBytes)

    @classmethod
    def javaStringToPythonString(cls, value):
        """ Convert a javaobj.JavaString value to a python str object. """
        if value is None:
            return None
        # Verify that the provided value is a JavaString.
        if not isinstance(value, javaobj.JavaString):
            raise ValueError("Expected value of type JavaString but found type %s." % type(value))
        # A JavaString is a subclass of str, so just return the value.
        return value

    @classmethod
    def pythonStringToJavaString(cls, value):
        """ Convert the python value to a JavaString. """
        if value is None:
            return None
        if isinstance(value, javaobj.JavaString):
            return value
        if isinstance(value, str):
            result = javaobj.JavaString(value)
            return result
        if isinstance(value, unicode):
            return javaobj.JavaString(value)
        raise ValueError("Cannot convert object of type %s to a JavaString." % type(value))

    @classmethod
    def getClassName(cls, object):
        className = object.get_class().name
        if className is None:
            raise ValueError("No class name defined for java object of type %s." % type(object))
        return className

    @classmethod
    def isSubclass(cls, object, className):
        clazz = object.get_class()
        while clazz:
            if clazz.name == className:
                return True
            clazz = clazz.superclass
        return False

    @classmethod
    def readJavaObject(cls, data, pos=0, ignoreRemainingData=True):
        """ Read a java object from the serialized data. Returns tuple (object, objectSize). """
        dataStream = BytesIO(data[pos:])
        object = javaobj.load(dataStream, ignore_remaining_data=ignoreRemainingData)
        objectSize = dataStream.tell()
        return (object, objectSize)

    @classmethod
    def writeJavaObject(cls, object={}):
        """ Write a java object (a javaobj.JavaObject typically returned by readJavaObject() or
            created manually) of the specified type and create serialized data. Returns bytestring. """
        if object is None:
            pass
        elif not isinstance(object, javaobj.JavaObject):
            raise ValueError("Cannot write java object: object has incorrect type %s." % type(object))
        return javaobj.dumps(object)

    # The cache of java class objects.
    _javaClassCache = {}

    @classmethod
    def getClass(cls, name):
        return cls._javaClassCache.get(name)

    @classmethod
    def createClass(cls, name, flags=0x00, serialVersionUID=None, fields=[], superClassName=None):
        """ Create a java class (a javaobj.JavaClass) value."""

        # Verify that a name is specified.
        if name is None:
            raise ValueError("Cannot create java class: no name specified.")

        # If the flags indicate that the class is serializable, verify that a serial version UID is specified.
        if flags & 0x02:
            if serialVersionUID is None:
                # TODO should generate a random and unique UID here.
                raise ValueError("Cannot create java class: class is serializable but no serial version UID specified.")

        # If a serialVersionUID is specified, add the 'serializable' flag.
        if serialVersionUID is not None:
            flags = flags | 0x02

        # Get the class cache.
        cache = cls._javaClassCache

        # Check if the class already exists in the cache.
        if name in cache:        
            raise ValueError("Cannot create java class: class already exists with name '%s'." % name)

        # Create the class descriptor.
        clazz = javaobj.JavaClass()
        clazz.name = name
        clazz.serialVersionUID = serialVersionUID
        clazz.flags = flags
        clazz.fields_names = [field[0] for field in fields]
        clazz.fields_types = [field[1] for field in fields]

        # Locate superclass in the class cache, if specified.
        if superClassName is not None:
            clazz.superclass = cache.get(superClassName)
            if clazz.superclass is None:
                raise ValueError("Cannot create java class '%s': unknown superclass '%s'." % (clazz.name, superClassName))

        # print "## created class: %s" % clazz.name
        # print "##   field names: %s" % clazz.fields_names
        # print "##   field types: %s" % clazz.fields_types

        # Put the class into the cache.
        cache[name] = clazz

        return clazz

    class Object(javaobj.JavaObject):

        """ Base class for Java object definitions. """

        def __init__(self, className):
            super(Java.Object, self).__init__()
            # Check that a class name is provided.
            if className is None:
                raise ValueError("Cannot create Java.Object: no class name specified.")
            # Get the class descriptor from the cache.
            self.classdesc = Java.getClass(className)
            if self.classdesc is None:
                raise ValueError("Cannot create Java.Object: unknown class name '%s'" % className)

        @property
        def className(self):
            return self.classdesc.name

        @classmethod
        def getClassName(cls):
            return cls().className


# Create common Java classes. Serial version UID values obtained by inspection of JDK 1.8 source code.
Java.createClass(name='Ljava/lang/String', serialVersionUID=-6849794470754667710L) # java.lang.String

# Create common Java array classes. Generated serial version UID.
Java.createClass(name='[B', serialVersionUID=-5984413125824719648L) # byte[]
Java.createClass(name='[I', serialVersionUID=-5984413125824719647L) # int[]
Java.createClass(name='[C', serialVersionUID=-5984413125824719646L) # char[]
Java.createClass(name='[Z', serialVersionUID=-5984413125824719645L) # boolean[]
Java.createClass(name='[D', serialVersionUID=-5984413125824719644L) # double[]
Java.createClass(name='[F', serialVersionUID=-5984413125824719643L) # float[]
Java.createClass(name='[J', serialVersionUID=-5984413125824719642L) # long[]
Java.createClass(name='[S', serialVersionUID=-5984413125824719641L) # short[]
