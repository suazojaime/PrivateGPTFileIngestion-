import unittest
import javaobj

from java import Java


class JavaTestCase(unittest.TestCase):

    def test_JavaByteArrayTests(self):
        # Null checks.
        self.assertIsNone(Java.pythonByteStringToJavaByteArray(None))
        self.assertIsNone(Java.javaByteArrayToPythonByteString(None))

        b = 'foo'.encode('utf-8')
        self.assertIsInstance(b, bytes)

        # Convert to java byte array.
        object = Java.pythonByteStringToJavaByteArray(b)
        self.assertIsInstance(object, javaobj.JavaByteArray)

        # Convert back to python byte string.
        v = Java.javaByteArrayToPythonByteString(object)
        self.assertIsInstance(v, bytes)

        # Verify same values.
        self.assertEqual(len(v), len(b))
        self.assertEqual(v, b)

        # Fail if converting a bytearray.
        with self.assertRaises(ValueError):
            Java.pythonByteStringToJavaByteArray(bytearray())

    def test_JavaStringTests(self):
        # Null checks.
        self.assertIsNone(Java.pythonStringToJavaString(None))
        self.assertIsNone(Java.javaStringToPythonString(None))

        s = 'foo'
        self.assertIsInstance(s, str)

        # Convert Python value to Java object.
        object = Java.pythonStringToJavaString(s)
        self.assertIsInstance(object, javaobj.JavaString)

        # Convert Java object to python value.
        v = Java.javaStringToPythonString(object)
        self.assertIsInstance(v, str)

        # Check values are the same.
        self.assertEquals(v, s)

    def test_JavaClassTests(self):
        clazz = Java.getClass('[B')
        self.assertIsNotNone(clazz)
        self.assertEqual(clazz.name, '[B')

        clazz = Java.getClass('Ljava/lang/String')
        self.assertIsNotNone(clazz)
        self.assertEqual(clazz.name, 'Ljava/lang/String')

    def test_JavaSerializationTests(self):
        # Create x.y.Foo class if required.
        if Java.getClass('x.y.Foo') is None:
            Java.createClass(name='x.y.Foo', serialVersionUID=1234567890L,
                             fields=[('byteValue','B'), ('intValue','I'), \
                                     ('stringValue','Ljava/lang/String'), \
                                     ('byteArrayValue','[B')])

        # Create an instance of x.y.Foo class.
        object = JavaFoo()
        object.byteValue = 1
        object.intValue = 1
        object.stringValue = 'foo'
        object.byteArrayValue = 'foo'.encode('utf-8')

        # Encode then decode the java object.
        encoding = Java.writeJavaObject(object)
        (v,size) = Java.readJavaObject(encoding)
        self.assertEqual(size, len(encoding))

        self.assertEqual(Java.getClassName(v), 'x.y.Foo')
        self.assertEqual(v.byteValue, object.byteValue)
        self.assertEqual(v.intValue, object.intValue)
        self.assertEqual(v.stringValue, object.stringValue)
        self.assertEqual(v.byteArrayValue, object.byteArrayValue)


class JavaFoo(Java.Object):

    def __init__(self, className='x.y.Foo'):
        super(JavaFoo, self).__init__(className=className)
        self.byteValue = None
        self.intValue = None
        self.stringValue = None
        self.byteArrayValue = None


class JavaBar(Java.Object):

    def __init__(self, className='x.y.Bar'):
        super(JavaBar, self).__init__(className=className)
        self.intValue = None
        self.stringValue = None
        self.byteArrayValue = None

if __name__ == '__main__':
    unittest.main()
