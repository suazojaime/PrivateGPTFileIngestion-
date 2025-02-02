from ciphers import Cipher, CipherFactory

class PropertyEncryptor(object):

    def encryptProperties(self, properties={}):
        """ Encrypt the value of each property in the map, returning a new map. """
        encryptedProperties = {}
        for property in properties:
            value = properties[property]
            encryptedProperties[property] = self.encryptProperty(property, value)
        return encryptedProperties

    def decryptProperties(self, properties={}):
        """ Decrypt the value of each property in the map, returning a new map. """
        decryptedProperties = {}
        for property in properties:
            value = properties[property]
            decryptedProperties[property] = self.decryptProperty(property, value)
        return decryptedProperties

    def encryptProperty(self, propertyName, propertyValue):
        """ Encrypt a property. """
        raise NotImplementedError

    def decryptProperty(self, propertyName, propertyValue):
        """ Decrypt a property. """
        raise NotImplementedError

class SimplePropertyEncryptor(PropertyEncryptor):
    
    """ A property encryptor that always returns the property value for encrypt/decrypt operations. """
    
    # @Override
    def encryptProperty(self, propertyName, propertyValue):
        return propertyValue
    
    # @Override
    def decryptProperty(self, propertyName, propertyValue):
        return propertyValue
    
class KeyStorePropertyEncryptor(PropertyEncryptor):

    """ A property encryptor using a secret key within a keystore. """

    def __init__(self, keyStore, secretKeyAlias):
        super(KeyStorePropertyEncryptor, self).__init__()
        # Check that a key store has been specified.
        if keyStore is None:
            raise ValueError("No keystore specified for creating KeyStorePropertyEnryptor")
        # Check that a secret key alias has been specified.
        if secretKeyAlias is None:
            raise ValueError("No alias specified for locating secret key in KeyStorePropertyEncryptor")
        self._keyStore = keyStore
        self._secretKeyAlias = secretKeyAlias
        self._delegate = None
        self._secretKey = None
        from pbeConfig import PBEConfig
        # TODO need to get a config here...
        self._password = PBEConfig.getInstance().password
        
    @property
    def keyStore(self):
        return self._keyStore
    
    @property
    def secretKeyAlias(self):
        return self._secretKeyAlias
    
    # @Override
    def encryptProperty(self, propertyName, propertyValue):
        return self.delegate.encryptProperty(propertyName, propertyValue)

    # @Override
    def decryptProperty(self, propertyName, propertyValue):
        return self.delegate.decryptProperty(propertyName, propertyValue)

    @property
    def delegate(self):
        if self._delegate is None:
            self._delegate = self._createDelegate()
        return self._delegate

    def _createDelegate(self):
        return CipherPropertyEncryptor.createFromSecretKey(self.secretKey)

    @property
    def secretKey(self):
        """ Get the secret key (for secure overrides) from the key store. """
        if self._secretKey is None:
            self._secretKey = self.__createOrLoadSecretKey()
        return self._secretKey

    def __createOrLoadSecretKey(self):
        secretKey = self.__loadSecretKey()
        if secretKey is None:
            secretKey = self.__createSecretKey()
            self.keyStore.setSecretKey(alias=self.secretKeyAlias, secretKey=secretKey, password=self._password)
            self.keyStore.store()
        return secretKey
    
    def __createSecretKey(self):
        from ciphers import SecretKeyFactory
        algorithm = 'AES' # TODO get this from OverridesConfig
        key = SecretKeyFactory().createSecretKey(algorithm)
        from keystores import SecretKeySpec
        return SecretKeySpec(algorithm=algorithm, key=key)
    
    def __loadSecretKey(self):
        return self.keyStore.getSecretKey(self.secretKeyAlias)

    @classmethod
    def createInstance(cls, keyStoreConfig):
        """ Create a new instance of a KeyStorePropertyEncryptor. Uses defaults where necessary
            for key store location, key store passwords, etc. """
        # Create a key store config, if required.
        if keyStoreConfig is None:
            raise Exception("A key store config is required to create a key store property encryptor.")
        
        # Get the key store.
        from keystores import JavaKeyStore
        keyStore = JavaKeyStore.createOrLoad(keyStoreConfig)
        
        return KeyStorePropertyEncryptor(keyStore=keyStore, secretKeyAlias='secure-overrides')
        
class CipherPropertyEncryptor(PropertyEncryptor):

    """ Encrypts/decrypts values in properties. """

    ENCRYPTED_PREFIX = 'ENC('
    ENCRYPTED_SUFFIX = ')'

    WEAK_CIPHER_ALGORITHMS = ['DES','RC2']
    
    def __init__(self, cipherName, key):
        super(CipherPropertyEncryptor, self).__init__()
        # Check that a supported cipher algorithm is provided.
        if cipherName is None:
            raise Exception("No cipher algorithm specified")
        transformation = Cipher.Transformation.parse(cipherName)
        if transformation.algorithm in self.WEAK_CIPHER_ALGORITHMS:
            raise Exception("Cipher algorithm %s not supported: too weak" % cipherName)
        self.cipherName = transformation.__repr__()
        self.key = key
        self.cipherFactory = CipherFactory()
        
    @classmethod
    def createFromSecretKey(cls, secretKey):
        return cls(secretKey.algorithm, secretKey.keyData)
    
    def __createCipher(self):
        return self.cipherFactory.createCipher(self.cipherName, self.key)
    
    # @Override
    def encryptProperty(self, propertyName, propertyValue):
        # Create an encryption cipher. An IV will be created for the cipher.
        cipher = self.__createCipher()
        cipher.initForEncryption()

        # Update the cipher with the property name as associated data, if required.
        if cipher.supportsMAC:
            header = propertyName or ''
            cipher.updateAAD(header)
            
        # Encrypt the property value.
        encrypted = cipher.encrypt(propertyValue)
        
        # Create a MAC, if required.
        mac = bytearray()
        if cipher.supportsMAC:
            mac = cipher.digest()
        
        # Create a message from (iv, encrypted, mac)
        message = cipher.iv + encrypted + mac
        payload = self.__encodeValue(message)
        
        # TODO whiten cipherText array
        
        return payload
    
    # @Override
    def decryptProperty(self, propertyName, propertyValue):
        # Create a cipher.
        cipher = self.__createCipher()
        
        # Extract the IV from the payload.
        payload = self.__decodeValue(propertyValue)
        if len(payload) < cipher.blockSize:
            raise CryptoException("Invalid length for encrypted property %s" % propertyName)
        iv = payload[:cipher.blockSize]
        payload = payload[cipher.blockSize:]

        # Initialize the cipher with the IV.
        cipher.initForDecryption(iv=iv)

        # Extract the MAC from the payload, if present.
        mac = bytearray()
        if cipher.supportsMAC:
            payloadLen = len(payload) - cipher.macLength
            mac = payload[payloadLen:]
            payload = payload[:payloadLen]
            
        # Update the cipher with the property name as associated data, if required.    
        if cipher.supportsMAC:
            header = propertyName or ''
            cipher.updateAAD(header)

        # Decrypt (what's left of) the payload.
        decrypted = cipher.decrypt(payload)
        
        # Verify the generated MAC, if required.
        if cipher.supportsMAC:
            cipher.verify(mac)

        return decrypted

    def __encodeValue(self, value):
        return "%s%s%s" % (self.ENCRYPTED_PREFIX, base64Encode(value), self.ENCRYPTED_SUFFIX)

    def __decodeValue(self, encodedValue):
        # Check that the value is encrypted.
        if not self.__isEncrypted(encodedValue):
            raise Exception("Cannot decrypt value: not encrypted")
        # Extract the base64-encoded value part.
        base64EncodedValue = encodedValue[len(self.ENCRYPTED_PREFIX):len(encodedValue)-len(self.ENCRYPTED_SUFFIX)]
        return base64Decode(base64EncodedValue)

    def __isEncrypted(self, value):
        return value is not None and value.startswith(self.ENCRYPTED_PREFIX) and value.endswith(self.ENCRYPTED_SUFFIX)

def base64Encode(value):
    import base64
    return base64.b64encode(value)

def base64Decode(value):
    import base64
    return base64.b64decode(value)

def hexEncodeBytes(bytes):
    import binascii
    return binascii.hexlify(bytes)
