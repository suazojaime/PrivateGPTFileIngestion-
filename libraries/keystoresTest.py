import unittest
import javaobj

from keystores import *
from java import Java


class KeystoresTestCase(unittest.TestCase):

    def test_SecretKeySpec(self):
        secretKeySpec = SecretKeySpec(algorithm='AES')

        # Create a java object from the secret key spec.
        object = secretKeySpec.toJavaObject()
        self.assertEqual(Java.getClassName(object), 'javax.crypto.spec.SecretKeySpec')
        self.assertEqual(object.algorithm, secretKeySpec.algorithm)
        self.assertEqual(object.key, secretKeySpec.keyData)

        # Serialize/deserialize the java object.
        encoding = Java.writeJavaObject(object)
        (object,_) = Java.readJavaObject(encoding)

        # Create a secret key spec from the java object.
        v = SecretKeySpec.fromJavaObject(object)
        self.assertEqual(v.algorithm, secretKeySpec.algorithm)
        self.assertEqual(v.keyData, secretKeySpec.keyData)
        self.assertEqual(v.keySize, secretKeySpec.keySize)

    def test_SealedObject(self):
        # Create a sealed object.
        sealedObject = SealedObject()
        sealedObject.sealAlg = 'foo'
        sealedObject.encryptedContent = 'bar'.encode('utf-8')
        sealedObject.paramsAlg = 'foo'
        sealedObject.encodedParams = 'bar'.encode('utf-8')

        # Convert sealed object to a java object.
        object = sealedObject.toJavaObject()
        self.assertEqual(Java.getClassName(object), 'javax.crypto.SealedObject')

        self.assertEqual(object.sealAlg, sealedObject.sealAlg)
        self.assertEqual(object.encryptedContent, sealedObject.encryptedContent)
        self.assertEqual(object.paramsAlg, sealedObject.paramsAlg)
        self.assertEqual(object.encodedParams, sealedObject.encodedParams)

        # Serialize/deserialize the java object.
        encoding = Java.writeJavaObject(object)
        (object,_) = Java.readJavaObject(encoding)

        # Convert java object to sealed object.
        v = SealedObject.fromJavaObject(object)
        self.assertEqual(v.sealAlg, sealedObject.sealAlg)
        self.assertEqual(v.encryptedContent, sealedObject.encryptedContent)
        self.assertEqual(v.paramsAlg, sealedObject.paramsAlg)
        self.assertEqual(v.encodedParams, sealedObject.encodedParams)

    def test_SealedObjectForKeyProtector(self):
        # Create a sealed object.
        sealedObject = SealedObjectForKeyProtector()
        sealedObject.sealAlg = 'foo'
        sealedObject.encryptedContent = 'bar'.encode('utf-8')
        sealedObject.paramsAlg = 'foo'
        sealedObject.encodedParams = 'baz'.encode('utf-8')

        # Convert sealed object to a java object.
        object = sealedObject.toJavaObject()
        self.assertEqual(Java.getClassName(object), 'com.sun.crypto.provider.SealedObjectForKeyProtector')

        # Verify that the properties have the expected types.
        self.assertIsInstance(object.sealAlg, javaobj.JavaString)
        self.assertIsInstance(object.paramsAlg, javaobj.JavaString)
        self.assertIsInstance(object.encryptedContent, javaobj.JavaByteArray)
        self.assertIsInstance(object.encodedParams, javaobj.JavaByteArray)

        # Verify that the properties have the expected values.
        self.assertEqual(object.sealAlg, sealedObject.sealAlg)
        self.assertEqual(object.encryptedContent, sealedObject.encryptedContent)
        self.assertEqual(object.paramsAlg, sealedObject.paramsAlg)
        self.assertEqual(object.encodedParams, sealedObject.encodedParams)

        # Serialize/deserialize the java object.
        encoding = Java.writeJavaObject(object)
        (object,_) = Java.readJavaObject(encoding)

        # Convert java object to sealed object.
        v = SealedObjectForKeyProtector.fromJavaObject(object)
        self.assertEqual(v.sealAlg, sealedObject.sealAlg)
        self.assertEqual(v.encryptedContent, sealedObject.encryptedContent)
        self.assertEqual(v.paramsAlg, sealedObject.paramsAlg)
        self.assertEqual(v.encodedParams, sealedObject.encodedParams)

if __name__ == '__main__':
    unittest.main()
