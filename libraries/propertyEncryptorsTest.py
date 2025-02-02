import unittest

from ciphers import *
from keystores import *
from keystoreConfig import KeyStoreConfig
from propertyEncryptors import *


class PropertyEncryptorsTest(unittest.TestCase):

    def test_CipherPropertyEncryptor(self):
        text = '/MineStar.properties,/Versions.properties'
        encryptor = CipherPropertyEncryptor.createFromSecretKey(self.createSecretKey())
        cipherText = encryptor.encryptProperty('CONTENTS', text)
        clearText = encryptor.decryptProperty('CONTENTS', cipherText)
        self.assertEqual(text, clearText)

    def test_KeyStorePropertyEncryptor(self):
        text = '/MineStar.properties,/Versions.properties'
        secretKey = self.createSecretKey()

        keystore = self.createKeyStore()
        keystore.setSecretKey(alias='alias', secretKey=secretKey, password='password')
        # Need to decrypt the secret key because it is an encrypted secret key in the key store.
        keystore.getSecretKey(alias='alias').decrypt('password')

        encryptor = KeyStorePropertyEncryptor(keyStore=keystore, secretKeyAlias='alias')
        cipherText = encryptor.encryptProperty('CONTENTS', text)
        clearText = encryptor.decryptProperty('CONTENTS', cipherText)
        self.assertEqual(text, clearText)

    def createKeyStore(self):
        config = KeyStoreConfig()
        return JavaKeyStore(keyStoreConfig=config)

    def createSecretKey(self):
        key = SecretKeyFactory().createSecretKey(algorithm='AES')
        return SecretKeySpec(algorithm='AES', key=key)
    
if __name__ == '__main__':
    unittest.main()
