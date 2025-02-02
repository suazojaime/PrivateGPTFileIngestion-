# TODO copy license from jks.py to here 

import os
import javaobj

from java import Java
from asn1 import ASN1

from pyasn1_modules import rfc5208,rfc3447

def debug(message):
    if message:
        import logging
        logging.debug(message)
        
def hexify(v, limit=None):
    """Hexify a value (including None)."""
    import binascii
    if v is None: return 'None'
    suffix = ''
    if limit is not None and len(v) > limit:
        v = v[:limit]
        suffix = '...'
    return binascii.hexlify(v) + suffix

# Copied from jks/util.py:
import struct
b8 = struct.Struct('>Q')
b4 = struct.Struct('>L') # unsigned
b2 = struct.Struct('>H')
b1 = struct.Struct('B') # unsigned

class FileOps:

    """Class for handling file operations."""
    
    def createDir(self, path):
        """Create a directory path, including intermediate directories. Returns True if created, False otherwise. """
        try:
            os.makedirs(path)
        except:
            return False
        return os.path.exists(path)

    def backupFile(self, file):
        if os.path.exists(file):
            # Warning: will overwrite existing backup file.
            backupFile = file + ".original"
            import shutil
            shutil.copy2(file, backupFile)
        
    def moveFile(self, src, dest):
        # Move source file to destination file.    
        import shutil
        shutil.move(src, dest)

class KeyStoreException(Exception): pass
class KeyStoreFormatException(KeyStoreException): pass
class KeyStoreIntegrityException(KeyStoreException): pass

class PrivateKey(object):

    """ Interface representing a private key (more properly a PrivateKeyInfo?). """
    
    @property
    def algorithm(self):
        """ Get the algorithm of the private key. """
        raise NotImplementedError
    
    @property
    def keyParams(self):
        raise NotImplentedError
    
    @property
    def keyData(self):
        """ Get the raw key data of the private key. """
        raise NotImplementedError
    
    @property    
    def certificateChain(self):
        """ Get the (possibly empty) certificate chain associated with the private key. Returns List<Certificate>. """
        raise  NotImplementedError
        
    # TODO add other methods when required.
    
class Certificate(object):
    
    """ Interface representing a certificate. """
    
    @property
    def certificateType(self):
        """ Get the type of the certificate (X.509, PEM, etc). """
        raise NotImplementedError

    @property
    def certificateData(self):
        """ Get the certificate data. """
        raise NotImplementedError
        
    # TODO add other methods when required.
    
class CertificateSpec(Certificate):
    
    """ Class representing a specified certificate. """
    
    def __init__(self, certificateType, certificateData):
        super(CertificateSpec, self).__init__()
        # Verify that a certificate type was provided.
        if certificateType is None:
            raise ValueError("A certificate type must be specified when creating a certificate.")
        # Verify that a certificate data was provided.
        if certificateData is None:
            raise ValueError("A certificate data must be specified when creating a certificate.")
        self._certificateType = certificateType
        self._certificateData = certificateData
        
    @Certificate.certificateType.getter    
    def certificateType(self):
        return self._certificateType
    
    @Certificate.certificateData.getter
    def certificateData(self):
        return self._certificateData
    
class SecretKey(object):

    """ Interface representing a secret key. """

    @property
    def algorithm(self):
        """ Get the algorithm of the secret key. """
        raise NotImplementedError

    @property
    def keyData(self):
        """ Get the raw key data for the secret key. """
        raise NotImplementedError
    
    @property
    def keySize(self):
        """ Get the size of the secret key (in bits). """
        raise NotImplementedError

class SecretKeySpec(SecretKey, Java.Convertable):

    """ Implementation of SecretKey that contains key specification."""

    def __init__(self, algorithm, key=None):
        super(SecretKeySpec, self).__init__()
        # Verify that an encryption algorithm has been specified.
        if algorithm is None:
            raise ValueError("Cannot create SecretKeySpec: no algorithm specified.")
        # Generate a secret key from the algorithm, if required.
        if key is None:
            from ciphers import SecretKeyFactory
            key = SecretKeyFactory().createSecretKey(algorithm)
        # Verify that the key is a byte array.    
        if not isinstance(key, bytes):
            raise ValueError("Cannot create SecretKeySpec: incorrect type for key: %s" % type(key))
        self._algorithm = algorithm
        self._keyData = key

    @SecretKey.algorithm.getter
    def algorithm(self):
        return self._algorithm

    @SecretKey.keyData.getter
    def keyData(self):
        return self._keyData

    @SecretKey.keySize.getter
    def keySize(self):
        return len(self.keyData) * 8

    # @Override
    def toJavaObject(self):
        object = JavaSecretKeySpec()
        object.algorithm = Java.pythonStringToJavaString(self.algorithm)
        object.key = Java.pythonByteStringToJavaByteArray(self.keyData)
        return object
    
    # @Override
    @classmethod
    def fromJavaObject(cls, object):
        algorithm = Java.javaStringToPythonString(object.algorithm)
        key = Java.javaByteArrayToPythonByteString(object.key)
        return cls(algorithm, key)
    
class KeyStore(object):
    
    """ Interface for a key store. """

    def __init__(self, keyStoreConfig=None):
        self._entries = None                  # Map<Alias,KeyStoreEntry>
        self._secretKeys = None               # Map<Alias,SecretKey>, derived from the entries
        self._privateKeys = None              # Map<Alias,PrivateKey>, derived from the entries
        self._certificates = None             # Map<Alias,Certificate>, derived from the entries
        self._keyStoreConfig = keyStoreConfig # The key store configuration.
        
    @property
    def keyStoreConfig(self):
        if self._keyStoreConfig is None:
            # TODO need to get a config here ..
            from keystoreConfig import KeyStoreConfig
            self._keyStoreConfig = KeyStoreConfig.getInstance()
        return self._keyStoreConfig
    
    @keyStoreConfig.setter
    def keyStoreConfig(self, keyStoreConfig):
        self._keyStoreConfig = keyStoreConfig
        
    @property
    def entries(self):
        """ Get the entries in the key store, indexed by alias. Returns Map<Alias,KeyStoreEntry> """
        if self.entries is None:
            self._entries = self._loadEntries()
        return self._entries
    
    def _loadEntries(self):
        """ Load the entries from the key store. """
        raise NotImplementedError
    
    @property
    def privateKeys(self):
        """ Get the private keys in the key store, indexed by alias. Returns Map<Alias,PrivateKey> """
        if self._privateKeys is None:
            self._privateKeys = self._loadPrivateKeys()
        return self._privateKeys
    
    def _loadPrivateKeys(self):
        """ Create a map of each private key entry and its alias. """
        return dict([(a,e.object) for (a,e) in self.entries.items() if isinstance(e.object,PrivateKey)])
    
    @property
    def certificates(self):
        """ Get the certificates in the key store, indexed by alias. Returns Map<Alias,Certificate> """
        if self._certificates is None:
            self._certificates = self._loadCertificates()
        return self._certificates
    
    def _loadCertificates(self):
        """ Create a map of each certificate entry and its alias. """
        return dict([(a,e.object) for (a,e) in self.entries.items() if isinstance(e.object,Certificate)])

    @property
    def secretKeys(self):
        """ Return the secret keys in the key store, indexed by alias. Returns Map<Alias,SecretKey> """
        if self._secretKeys is None:
            self._secretKeys = self._loadSecretKeys()
        return self._secretKeys

    def _loadSecretKeys(self):
        """ Create a map of each secret key entry and its alias. """
        return dict([(a,e.object) for (a,e) in self.entries.items() if isinstance(e.object,SecretKey)])
    
    def getSecretKey(self, alias):
        """ Get the secret key with the matching alias. Returns None if there are no
            secret keys or if no secret key is found matching the alias. """
        return self.secretKeys.get(alias)

    def setSecretKey(self, alias, secretKey, password):
        """ Set a secret key in the store. """
        # Create a secret key entry from the secret key.
        entry = self._createSecretKeyEntry(secretKey, password)
        entry.alias = alias
        entry.timestamp = getTimestamp()
        # Put the entry into the entries map.
        self.entries[alias] = entry
        # Clear the secret keys since the entries map has changed.
        self._secretKeys = None
        
    def _createSecretKeyEntry(self, secretKey, password):
        raise KeyStoreException("Key store does not support creating secret keys.")
    
    def store(self, keyStoreConfig=None):
        """ Persist the key store. """
        raise KeyStoreException("Key store does not support persisting.")
    
def getTimestamp():
    """ Get a timestamp (the current time in milliseconds since the epoch). """
    import time
    # time() should return a value with fractional seconds, so can multiple by 1000 for milliseconds.
    return int(time.time() * 1000)

class JavaKeyStore(KeyStore):

    """ Implementation of key store using JKS. """

    MAGIC_NUMBER_JKS = b4.pack(0xFEEDFEED)
    MAGIC_NUMBER_JCEKS = b4.pack(0xCECECECE)
    SIGNATURE_WHITENING = b"Mighty Aphrodite"
    
    def __init__(self, entries={}, storeType='jceks', keyStoreConfig=None):
        super(JavaKeyStore, self).__init__(keyStoreConfig=keyStoreConfig)
        self._storeType = storeType or 'jceks'
        self._entries = entries or {}
        self._keyStoreConfig = keyStoreConfig
        
        debug("Loaded JKS key store with %d entries: %d private keys, %d certificates, and %d secret keys." % \
              (len(self.entries), len(self.privateKeys), len(self.certificates), len(self.secretKeys)))

        for (alias,privateKey) in self.privateKeys.items():
            debug("Private Key: %s" % alias)
            debug("  Algorithm: %s" % str(privateKey.algorithm))
            debug("  Key Data : %s" % hexify(privateKey.keyData, limit=32))
        for (alias,certificate) in self.certificates.items():
            debug("Certificate: %s" % alias)
            debug("  Type     : %s" % certificate.type)
        for (alias,secretKey) in  self.secretKeys.items():
            debug("Secret Key : %s" % alias)
            debug("  Algorithm: %s" % secretKey.algorithm)
            debug("  Key Size : %d" % secretKey.keySize)
            debug("  Key Data : %s" % hexify(secretKey.keyData, limit=32))

    @property
    def storeType(self):
        return self._storeType
    
    @KeyStore.entries.getter
    def entries(self):
        return self._entries
    
    # @Override
    def _createSecretKeyEntry(self, secretKey, password):
        # If the secret key contains its specification, then create a JKS secret key entry.
        if isinstance(secretKey, SecretKeySpec):
            secretKey = EncryptedSecretKey.createFromSecretKeySpec(secretKeySpec=secretKey, password=password)
            return KeyStoreEntry(object=secretKey)
        # Don't know how to handle opaque secret keys.
        raise KeyStoreException("Cannot create a secret key entry for secret key of type %s." % type(secretKey))
    
    # @Override
    def store(self, keyStoreConfig=None):
        # Use the local keyStoreConfig if a config was not provided.
        if keyStoreConfig is None:
            keyStoreConfig = self.keyStoreConfig

        keyStoreFile = keyStoreConfig.keyStoreFile
        debug("Saving keystore with %d entries to file %s ..." % (len(self.entries), keyStoreFile))
        
        # Get the encoding of the key store.
        encoder = JavaKeyStoreEncoder(password=keyStoreConfig.keyStorePassword)
        encoding = encoder.encode(self)

        # Create the parent directory for the key store file (if required).
        fileOps = FileOps()
        
        # Create the key store directory, if required.
        keyStoreDir = os.path.dirname(keyStoreFile)
        if not os.path.exists(keyStoreDir) and not fileOps.createDir(keyStoreDir):
            raise KeyStoreException("Cannot write key store: failed to create key store directory %s" % keyStoreDir)
        
        # Encode the key store to a temporary file.
        temporaryKeyStoreFile = keyStoreFile + ".temp"
        try:
            # Write the encoding to the temporary file.
            with open(temporaryKeyStoreFile, 'wb') as f:
                f.write(encoding)
            # Create a backup of the existing keystore file.
            fileOps.backupFile(keyStoreFile)
            # Move the temporary file to the keystore file.
            fileOps.moveFile(temporaryKeyStoreFile, keyStoreFile)
        except Exception as e:
            raise KeyStoreException("Failed to write key store file: %s" % str(e))
        finally:
            # Remove the temporary file if it exists.
            if os.path.exists(temporaryKeyStoreFile):
                os.remove(temporaryKeyStoreFile)
        
    @classmethod
    def load(cls, keyStoreConfig=None, config=None):
        """ Load a java key store using the (optional) key store config. """
        if keyStoreConfig is None:
            from keystoreConfig import KeyStoreConfig            
            keyStoreConfig = KeyStoreConfig.getInstance(config=config)
        
        # Check that the key store file exists.
        keyStoreFile = keyStoreConfig.keyStoreFile
        if not os.path.exists(keyStoreFile):
            raise KeyStoreException("Cannot load key store: file '%s' not found." % keyStoreFile)
        
        # Load the java key store.
        return JavaKeyStoreDecoder.decodeConfig(keyStoreConfig)
    
    @classmethod
    def create(cls, keyStoreConfig=None, config=None):
        """ Create a new java key store using the (optional) key store config. """
        if keyStoreConfig is None:
            from keystoreConfig import KeyStoreConfig
            keyStoreConfig = KeyStoreConfig.getInstance(config=config)

        debug("Creating a new key store at %s" % keyStoreConfig.keyStoreFile)
        
        # Create a new key store, then persist it.
        keyStore = cls(entries={}, keyStoreConfig=keyStoreConfig)
        keyStore.store()
        
        return keyStore
    
    @classmethod
    def createOrLoad(cls, keyStoreConfig=None, config=None):
        """ Create or load a key store using the key store config. """
        if keyStoreConfig is None:
            from keystoreConfig import KeyStoreConfig
            keyStoreConfig = KeyStoreConfig.getInstance(config=config)
        if not os.path.exists(keyStoreConfig.keyStoreFile):
            return JavaKeyStore.create(keyStoreConfig)
        else:
            return JavaKeyStore.load(keyStoreConfig)
        

class JavaKeyStoreIO:

    def readData(self, data, pos=0):
        length = b4.unpack_from(data, pos)[0]; pos += 4
        data = data[pos:pos+length]; pos += length
        return (data, pos)

    def writeData(self, data, pos=0):
        encoding = bytearray()
        encoding.extend(b4.pack(len(data)))
        encoding.extend(data)
        return bytes(encoding)

    def readCount(self, data, pos=0):
        count = b4.unpack_from(data, pos)[0]; pos += 4
        return (count, pos)

    def writeCount(self, count):
        return b4.pack(count)

    def readUtf8(self, data, pos=0, name=None):
        size = b2.unpack_from(data, pos)[0]; pos += 2
        try:
            return (data[pos:pos+size].decode('utf-8'), pos+size)
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            source = " for '%s'" % name if name else ""
            raise KeyStoreException("Failed to decode UTF-8 data%s: %s" % (source, str(e)))

    def writeUtf8(self, data, name=None):
        """ Write the data as a UTF-8 value. """
        encoding =  bytearray()
        encoding.extend(b2.pack(len(data)))
        try:
            encoding.extend(data.encode('utf-8'))
        except (UnicodeEncodeError,UnicodeDecodeError) as e:
            source = " for '%s' " % name if name else ""
            raise KeyStoreException("Failed to encode UTF-8 data%s: %s" % (source, str(e)))
        return bytes(encoding)

    def readJavaObject(self, data, pos=0):
        """ Read a serialized java object from the data. Returns (object, pos). """
        (object, objectSize) = Java.readJavaObject(data=data, pos=pos)
        return (object, pos + objectSize)

    def writeJavaObject(self, object):
        """ Write a serialized java object to the data. """
        return Java.writeJavaObject(object)
    
class JavaKeyStoreCodec(object):

    VERSION = 2
    
    class StoreType:
        
        JKS = 'jks'
        JCEKS = 'jceks'
        
    class Tag:

        """ The key store tags. """
        
        PRIVATE_KEY = 1
        CERTIFICATE = 2
        SECRET_KEY = 3

    def __init__(self):
        self.io = JavaKeyStoreIO()
        
class JavaKeyStoreDecoder(JavaKeyStoreCodec):
    
    """ Class for decoding a java key store. """
    
    def __init__(self, password, decryptOnLoad=True):
        super(JavaKeyStoreDecoder, self).__init__()
        if password is None:
            raise KeyStoreException("Must specify a store password when creating a java key store decoder.")
        self.storeType = None
        self.password = password
        self.decryptOnLoad = decryptOnLoad
        self.java = Java
        
    def decode(self, data, pos=0):
        """ Decode the serialized java key store contained in the data. """
        
        # Get the store type based on the magic number in the data.
        (magic,pos) = self.decodeMagicNumber(data, pos)
        self.storeType = self._magicNumberToStoreType(magic)
        
        # Check that the version is 2.
        (version,pos) = self.decodeVersion(data, pos)
        if version != JavaKeyStoreDecoder.VERSION:
            raise KeyStoreException('Unsupported keystore version; expected v%r, found v%r' % (JavaKeyStoreDecoder.VERSION,version))

        # Slurp the entry count.
        (entryCount,pos) = self.decodeEntryCount(data, pos)
        
        # Slurp the entries.
        entries = {}
        for i in range(entryCount):
            # Slurp the next entry.
            (entry, pos) = self.decodeEntry(data, pos)
            # Check for duplicate entry.
            if entry.alias in entries:
                raise KeyStoreException("Duplicate entries with alias '%s'" % entry.alias)
            entries[entry.alias] = entry
        
        # Check the hash value.
        self.verifyHash(data, pos)
        
        return JavaKeyStore(entries=entries, storeType=self.storeType)
    
    def decodeMagicNumber(self, data, pos):
        magic = data[pos:pos+4]; pos += 4
        return (magic, pos)
    
    def _magicNumberToStoreType(self, magicNumber):
        if magicNumber == JavaKeyStore.MAGIC_NUMBER_JKS:
            return JavaKeyStoreDecoder.StoreType.JKS
        if magicNumber == JavaKeyStore.MAGIC_NUMBER_JCEKS:
            return JavaKeyStoreDecoder.StoreType.JCEKS
        raise KeyStoreException("Invalid key store format: invalid magic number")
        
    def decodeVersion(self, data, pos):
        version = b4.unpack_from(data, pos)[0]; pos += 4
        return (version, pos)
    
    def decodeEntryCount(self, data, pos):
        entryCount = b4.unpack_from(data, pos)[0]; pos += 4
        return (entryCount, pos)
    
    def decodeEntry(self, data, pos):
        # Slurp the tag, alias, and timestamp.
        entry = KeyStoreEntry()
        (entry.tag,pos) = self.decodeTag(data, pos)
        (entry.alias,pos) = self.decodeAlias(data, pos)
        (entry.timestamp, pos) = self.decodeTimestamp(data, pos)
        # Slurp the entry object, keeping track of the encoded object data.
        encodingStartPos = pos
        (entry.object, pos) = self.decodeEntryObject(data, pos, entry.tag)
        encodingEndPos = pos
        entry.encoding = data[encodingStartPos:encodingEndPos]

        return (entry, pos)
    
    def decodeTag(self, data, pos):
        tag = b4.unpack_from(data, pos)[0]; pos += 4
        if tag == 1:
            tag = JavaKeyStoreDecoder.Tag.PRIVATE_KEY
        elif tag == 2:
            tag = JavaKeyStoreDecoder.Tag.CERTIFICATE
        elif tag == 3:
            tag = JavaKeyStoreDecoder.Tag.SECRET_KEY
        else:
            raise KeyStoreException("Invalid key store: unsupported key store entry tag %r" % tag)
        return (tag, pos)
    
    def decodeAlias(self, data, pos):
        return self.io.readUtf8(data, pos, 'alias')

    def decodeTimestamp(self, data, pos):
        timestamp = int(b8.unpack_from(data, pos)[0]); pos += 8 # milliseconds since UNIX epoch
        return (timestamp, pos)
    
    def decodeEntryObject(self, data, pos, tag):
        # Decode object according to the tag.
        if tag == JavaKeyStoreDecoder.Tag.PRIVATE_KEY:
            (object,pos) = self.decodePrivateKeyEntry(data, pos)
        elif tag == JavaKeyStoreDecoder.Tag.CERTIFICATE:
            (object,pos) = self.decodeCertificateEntry(data, pos)
        elif tag == JavaKeyStoreDecoder.Tag.SECRET_KEY:
            (object,pos) = self.decodeSecretKeyEntry(data, pos)
        else:
            raise KeyStoreException("Invalid key store: unsupported key store entry tag %r" % tag)
        
        # Decrypt the object with the store password, if requested.
        if self.decryptOnLoad and not object.decrypted:
            try:
                object.decrypt(self.password)
            except Exception as e:
                print "*** Decryption Error ***"
                import traceback
                traceback.print_exc()
                print "************************"
                # # Ignore any decryption error. Entry will need to be manually decrypted later.
                # pass
                raise KeyStoreException("Failed to decrypt key store entry", e)
            
        return (object,pos)
    
    def decodePrivateKeyEntry(self, data, pos):
        (encryptedPrivateKeyInfo,pos) = self.decodeEncryptedPrivateKeyInfo(data, pos)
        (certificateCount,pos) = self.io.readCount(data, pos)
        certificateChain = []
        for _ in range(certificateCount):
            (certificate,pos) = self.decodeCertificate(data, pos)
            certificateChain.append(certificate)
        privateKey = EncryptedPrivateKey(encryptedPrivateKeyInfo=encryptedPrivateKeyInfo, 
                                         certificateChain=certificateChain)                            
        return (privateKey, pos)

    def decodeEncryptedPrivateKeyInfo(self, data, pos):
        (encoding, pos) = self.io.readData(data, pos)
        encryptedPrivateKeyInfo = EncryptedPrivateKeyInfo.decodeASN1(encoding)
        return (encryptedPrivateKeyInfo, pos)
    
    def decodeCertificateEntry(self, data, pos):
        return self.decodeCertificate(data, pos)
    
    def decodeCertificate(self, data, pos):
        (certificateType,pos) = self.io.readUtf8(data, pos, name="certificate type")
        (certificateData,pos) = self.io.readData(data, pos)
        certificate = CertificateSpec(certificateType, certificateData)
        return (certificate, pos)
    
    def decodeSecretKeyEntry(self, data, pos):
        # Decode a serialized javax.crypto.SealedObject instance.
        (object,pos) = self.io.readJavaObject(data, pos)
        
        # Check that the object is an instance of the SealedObject interface.
        sealedObjectType = 'javax.crypto.SealedObject'
        if not Java.isSubclass(object, sealedObjectType):
            msg = "Cannot decode secret key entry: expected sealed object of type '%s' but found type '%s'." % \
                  (sealedObjectType, Java.getClassName(object))
            raise KeyStoreException(msg)
        
        # Create a encrypted secret key using the sealed object.
        secretKey = EncryptedSecretKey(SealedObject.fromJavaObject(object))
        
        return (secretKey, pos)
    
    def verifyHash(self, data, pos):
        import hashlib
        
        # Check keystore integrity (uses UTF-16BE encoding of the store password).
        hashFn = hashlib.sha1
        hashDigestSize = hashFn().digest_size

        # The hash is calculated over the encoded store password + SIGNATURE + slurped data.
        passwordUtf16 = self.password.encode('utf-16be')
        expectedHash = hashFn(passwordUtf16 + JavaKeyStore.SIGNATURE_WHITENING + data[:pos]).digest()
        foundHash = data[pos:pos+hashDigestSize]

        # Check that the expected hash matches the found hash.
        if len(foundHash) != hashDigestSize:
            tmpl = "Key store integrity check failure: incorrect hash size; found %d bytes, expected %d bytes."
            raise KeyStoreException(tmpl % (len(foundHash), hashDigestSize))
        
        if expectedHash != foundHash:
            raise KeyStoreException("Key store integrity check failure; incorrect keystore password?")
        
        return pos+hashDigestSize


    @classmethod
    def decodeConfig(cls, keyStoreConfig):
        """ Decode a key store using the file and password specified in the key store config. """
        keyStore = cls.decodeFile(file=keyStoreConfig.keyStoreFile, password=keyStoreConfig.keyStorePassword)
        keyStore.keyStoreConfig = keyStoreConfig
        return keyStore
    
    @classmethod
    def decodeFile(cls, file, password):
        """ Decode a java key store from the file and the password. """
        debug("Decoding keystore from file '%s' ..." % file)
        with open(file, 'rb') as f:
            return cls.decodeData(f.read(), password)
    
    @classmethod
    def decodeData(cls, data, password):
        """ Decode a java key store from the data and the password. """
        return JavaKeyStoreDecoder(password=password).decode(data)

class Encrypted(object):

    """ Class representing a encrypted object that must be decrypted before attributes are accessed. """
    
    def __init__(self, type):
        super(Encrypted, self).__init__()
        self._type = type
        self._delegate = None
    
    @property
    def delegate(self):
        if self._delegate is None:
            raise KeyStoreException("Cannot access %s: not yet decrypted." % self._type)
        return self._delegate
    
    @property    
    def decrypted(self):
        """ Determines if the object is decrypted. """
        return not self._delegate is None
    
    def decrypt(self, password):
        """ Decrypt the object, if not already decrypted. """
        if self._delegate is None:
            self._delegate = self._decryptPayload(password)
        return self._delegate
    
    def _decryptPayload(self, password):
        """ Decrypt the payload of the encrypted object. """
        raise NotImplementedError

class RSAPrivateKey(ASN1.Encodable, ASN1.Convertable):

    """ Class representing a raw RSA private key. """
    
    # RSAPrivateKey ::= SEQUENCE {
    #   version           Version,
    #   modulus           INTEGER,  -- n
    #   publicExponent    INTEGER,  -- e
    #   privateExponent   INTEGER,  -- d
    #   prime1            INTEGER,  -- p
    #   prime2            INTEGER,  -- q
    #   exponent1         INTEGER,  -- d mod (p-1)
    #   exponent2         INTEGER,  -- d mod (q-1)
    #   coefficient       INTEGER,  -- (inverse of q) mod p
    #   otherPrimeInfos   OtherPrimeInfos OPTIONAL
    # }
    class ASN1Type(rfc3447.RSAPrivateKey,ASN1.Encodable): pass
        
    def __init__(self):
        super(RSAPrivateKey, self).__init__()
        self.version = 0
        self.modulus = 0
        self.privateExponent = 0
        self.publicExponent = 0
        # TODO add more attributes: prime1, prime2, etc.
        
    # @Override
    def encodeASN1(self, format='ber'):
        return self.ASN1Type.encodeASN1(format)

    # @Override
    @classmethod
    def decodeASN1(cls, encoding, format='ber'):
        object = cls.ASN1Type.decodeASN1(encoding, format)
        return cls.fromASN1Object(object)

    # @Override    
    def toASN1Object(self):
        object = RSAPrivateKey.ASN1Type()
        object.version = ASN1.Integer(self.version or 0)
        object.modulus = ASN1.Integer(self.modulus or 0)
        object.publicExponent = ASN1.Integer(self.publicExponent or 0)
        object.privateExponent = ASN1.Integer(self.privateExponent or 0)
        # TODO handle more attributes: prime1, prime2, etc.
        print "## created RSAPrivateKey.ASN1Type() value: %s" % type(object)
        return object

    # @Override    
    @classmethod
    def fromASN1Object(cls, object):
        # Check for null.
        if object is None:
            return None
        # Verify that the object is an ASN.1 RSAPrivateKey value.
        if not isinstance(object, RSAPrivateKey.ASN1Type):
            raise TypeError("Cannot create RSAPrivateKey from ASN.1 object with type %s." % type(object))
        key = RSAPrivateKey()
        key.version = int(object['version'])
        key.modulus = int(object['modulus'])
        key.publicExponent = int(object['publicExponent'])
        key.privateExponent = int(object['privateExponent'])
        # TODO handle more attributes: prime1, prime2, etc.
        return key

def tupleToDottedOID(tuple):
    return '.'.join(map(str, tuple))

class PrivateKeyInfo(ASN1.Encodable, ASN1.Convertable):

    """ Class representing a PrivateKeyInfo as specified in RFC5208. """

    # From RFC5208:
    #
    #   PrivateKeyInfo ::= SEQUENCE {
    #     version Version,
    #     privateKeyAlgorithm AlgorithmIdentifier {{PrivateKeyAlgorithms}},
    #     privateKey PrivateKey,
    #     attributes [0] Attributes OPTIONAL }
    #
    #   Version ::= INTEGER {v1(0)} (v1,...)
    #
    #   PrivateKey ::= OCTET STRING
    # 
    #   Attributes ::= SET OF Attribute
    #
    # See: https://tools.ietf.org/html/rfc5208
    class ASN1Type(rfc5208.PrivateKeyInfo,ASN1.Encodable): pass

    def __init__(self):
        super(PrivateKeyInfo, self).__init__()
        
    def createPrivateKey(self):
        if self.algorithmId == '1.2.840.113549.1.1.1':
            return self.createRSAPrivateKey()
        raise KeyStoreException("Unsupported private key algorithm: %s" % self.algorithmId)

    def createRSAPrivateKey(self):
        object = RSAPrivateKey.decodeASN1(self.privateKey)
        debug("RSA Private Key:")
        debug("  version=%d" % object.version)
        debug("  modulus=%r" % object.modulus)
        debug("  publicExponent=%r" % object.publicExponent)
        debug("  privateExponent=%r" % object.privateExponent)
        return object

    # @Override
    def encodeASN1(self, format='ber'):
        return self.toASN1Object().encodeASN1(format)
    
    # @Override
    def toASN1Object(self):
        object = PrivateKeyInfo.ASN1()
        object['version'] = ASN1.Integer(self.version)
        object['privateKeyAlgorithm']['algorithm'] = ASN1.ObjectIdentifier(self.algorithmId)
        object['privateKeyAlgorithm']['parameters'] = ASN1.OctetString(self.algorithmParams)
        object['privateKey'] = ASN1.OctetString(self.privateKey)
        return object
    
    # @Override
    @classmethod
    def decodeASN1(cls, encoding, format='ber'):
        """ Create a PrivateKeyInfo from a BER encoding. """
        object = PrivateKeyInfo.ASN1Type.decodeASN1(encoding, format)
        return cls.fromASN1Object(object)
    
    @classmethod
    def fromASN1Object(cls, object):
        # Check for null.
        if object is None:
            return None
        # Verify that object is an ASN.1 PrivateKeyInfo value.
        if not isinstance(object, PrivateKeyInfo.ASN1Type):
            raise TypeError("Cannot create PrivateKeyInfo from object with type %s." % type(object))
        privateKeyInfo = PrivateKeyInfo()
        privateKeyInfo.version = int(object['version'])
        privateKeyInfo.algorithmId = tupleToDottedOID(object['privateKeyAlgorithm']['algorithm'].asTuple())
        privateKeyInfo.algorithmParams = object['privateKeyAlgorithm']['parameters'].asOctets()
        privateKeyInfo.privateKey = object['privateKey'].asOctets()
        # TODO should also store the attributes ...
        
        # Sanity check ...
        # privateKeyInfo.createPrivateKey()
        
        return privateKeyInfo

class EncryptedPrivateKeyInfo(ASN1.Encodable, ASN1.Convertable):

    """ Class representing an EncryptedPrivateKeyInfo that must be decrypted before use. """

    # From RFC5208:
    # 
    #   EncryptedPrivateKeyInfo ::= SEQUENCE {
    #     encryptionAlgorithm  EncryptionAlgorithmIdentifier,
    #     encryptedData        EncryptedData }
    # 
    #   EncryptionAlgorithmIdentifier ::= AlgorithmIdentifier 
    #
    #   EncryptedData ::= OCTET STRING
    #
    # See: https://tools.ietf.org/html/rfc5208
    class ASN1Type(rfc5208.EncryptedPrivateKeyInfo, ASN1.Encodable): pass

    def __init__(self):
        super(EncryptedPrivateKeyInfo, self).__init__()
        self.algorithmId = None
        self.algorithmParams = None
        self.encryptedPrivateKey = None

    def decrypt(self, password):
        """ Decrypt the EncryptedPrivateKeyInfo using the password to derive a PrivateKeyInfo. """
        encodedPrivateKeyInfo = self._decryptPrivateKeyInfoEncoding(password)
        return PrivateKeyInfo.decodeASN1(encodedPrivateKeyInfo)

    def _decryptPrivateKeyInfoEncoding(self, password):
        from pbeCiphers import PBECipherFactory
        from ciphers import CryptoException
        cipher = PBECipherFactory.createCipher(self.algorithmId, self.algorithmParams)
        try:
            return cipher.decrypt(self.encryptedPrivateKey, password)
        except CryptoException as e:
            # TODO should be catching more specific decryption errors, and letting other errors through.
            raise KeyStoreException("Failed to decrypt private key; wrong password?", e)
        
    # @Override
    def encodeASN1(self, format='ber'):
        return self.toASN1Object().encodeASN1(format)
    
    # @Override
    @classmethod
    def decodeASN1(cls, encoding, format='ber'):
        """ Create an EncryptedPrivateKeyInfo from an ASN.1 encoding. """
        object = EncryptedPrivateKeyInfo.ASN1Type.decodeASN1(encoding, format)
        return cls.fromASN1Object(object)

    # @Override
    def toASN1Object(self):
        object = EncryptedPrivateKeyInfo.ASN1Type()
        object['encryptionAlgorithm']['algorithm'] = ASN1.ObjectIdentifier(self.algorithmId)
        object['encryptionAlgorithm']['parameters'] = ASN1.OctetString(self.algorithmParams)
        object['encryptedData'] = ASN1.OctetString(self.encryptedPrivateKey)
        return object

    # @Override
    @classmethod
    def fromASN1Object(cls, object):
        """ Create an EncryptedPrivateKeyInfo value from an ASN.1 object. """
        # Check for null.
        if object is None: 
            return None
        # Verify that the object is an ASN.1 EncryptedPrivateKeyInfo value.
        if not isinstance(object, EncryptedPrivateKeyInfo.ASN1Type):
            raise TypeError("Cannot create EncryptedPrivateKeyInfo from object with type %s." % type(object))
        encryptedPrivateKeyInfo = EncryptedPrivateKeyInfo()
        encryptedPrivateKeyInfo.algorithmId = tupleToDottedOID(object['encryptionAlgorithm']['algorithm'].asTuple())
        encryptedPrivateKeyInfo.algorithmParams = object['encryptionAlgorithm']['parameters'].asOctets()
        encryptedPrivateKeyInfo.encryptedPrivateKey = object['encryptedData'].asOctets()
        return encryptedPrivateKeyInfo
    
class PrivateKeySpec(PrivateKey):
    
    """ Class representing a fully-specified private key. """
    
    def __init__(self, algorithm=None, algorithmParams=None, keyData=None, privateKeyInfo=None):
        super(PrivateKeySpec, self).__init__()
        # Extract algorithm, etc from privateKeyInfo if provided.
        if privateKeyInfo is not None:
            algorithm = privateKeyInfo.algorithmId
            algorithmParams = privateKeyInfo.algorithmParams
            keyData = privateKeyInfo.privateKey
        # Verify that algorithm and key data are specified. Parameters are optional, 
        # depending on the algorithm.    
        if algorithm is None: 
            raise ValueError("Cannot create private key: no algorithm specified.")
        if keyData is None: 
            raise ValueError("Cannot create private key: no key data specified.")
        # Assign attributes from parameters.
        self._algorithm = algorithm
        self._algorithmParams = algorithmParams
        self._keyData = keyData
        
    @PrivateKey.algorithm.getter    
    def algorithm(self):
        return self._algorithm
    
    @property
    def algorithmParams(self):
        """ Get the algorithm parameters for the private key. """
        return self._algorithmParams
    
    @PrivateKey.keyData.getter
    def keyData(self):
        return self._keyData
    
    def createPrivateKeyInfo(self):
        """ Create a PrivateKeyInfo from the private key. """
        return PrivateKeyInfo(algorithmId=self.algorithm, algorithmParams=self.algorithmParams, privateKey=self.keyData)
    
class EncryptedPrivateKey(Encrypted,PrivateKey):
    
    """ Class representing an encrypted private key that must be decrypted before use. """
    
    def __init__(self, encryptedPrivateKeyInfo, certificateChain=[]):
        super(EncryptedPrivateKey, self).__init__(type="EncryptedPrivateKey")
        
        # Verify that a payload has been specified and that it has correct type.
        if encryptedPrivateKeyInfo is None:
            raise ValueError("Cannot create encrypted private key: no encryption data specified.")
        if not isinstance(encryptedPrivateKeyInfo, EncryptedPrivateKeyInfo):
            raise ValueError("Cannot create encrypted private key: encryption data has incorrect type: %s" % type(encryptedPrivateKeyInfo))
        
        self._encryptedPrivateKeyInfo = encryptedPrivateKeyInfo
        self._certificateChain = certificateChain or []
        
    @PrivateKey.algorithm.getter    
    def algorithm(self):
        return self.delegate.algorithm
    
    @PrivateKey.keyData.getter
    def keyData(self):
        return self.delegate.keyData
    
    @PrivateKey.certificateChain.getter
    def certificateChain(self):
        return self._certificateChain
    
    @property
    def encryptedPrivateKeyInfo(self):
        return self._encryptedPrivateKeyInfo
    
    # @Override    
    def _decryptPayload(self, password):
        privateKeyInfo = self.encryptedPrivateKeyInfo.decrypt(password)
        return PrivateKeySpec(privateKeyInfo=privateKeyInfo)

class SealedObject(Java.Convertable,Java.Encodable):

    """ Class representing a sealed object, that can be decrypted. """
    
    def __init__(self):
        self._sealAlg = None
        self._encryptedContent = None
        self._paramsAlg = None
        self._encodedParams = None
        
    @property
    def sealAlg(self):
        return self._sealAlg

    @sealAlg.setter
    def sealAlg(self, sealAlg):
        self._sealAlg = sealAlg

    @property
    def encryptedContent(self):
        return self._encryptedContent

    @encryptedContent.setter
    def encryptedContent(self, encryptedContent):
        self._encryptedContent = encryptedContent

    @property
    def paramsAlg(self):
        return self._paramsAlg

    @paramsAlg.setter
    def paramsAlg(self, paramsAlg):
        self._paramsAlg = paramsAlg

    @property
    def encodedParams(self):
        return self._encodedParams

    @encodedParams.setter
    def encodedParams(self, encodedParams):
        self._encodedParams = encodedParams

    # @Override
    def toJavaObject(self):
        return self.populateJavaObject(JavaSealedObject())
        
    def populateJavaObject(self, object):    
        object.sealAlg = Java.pythonStringToJavaString(self.sealAlg)
        object.encryptedContent = Java.pythonByteStringToJavaByteArray(self.encryptedContent)
        object.paramsAlg = Java.pythonStringToJavaString(self.paramsAlg)
        object.encodedParams = Java.pythonByteStringToJavaByteArray(self.encodedParams)
        return object
    
    # @Override
    @classmethod
    def fromJavaObject(cls, object):
        """ Create SealedObject from a javaobj.JavaObject value. """
        # Check for null.
        if object is None:
            return None

        # Check that the object is a JavaObject.
        if not isinstance(object, javaobj.JavaObject):
            raise ValueError("Expected a value of type JavaObject, but found type %s." % type(object))
        
        # Convert to Python value.
        sealedObject = cls()
        sealedObject.sealAlg = Java.javaStringToPythonString(object.sealAlg)
        sealedObject.encryptedContent = Java.javaByteArrayToPythonByteString(object.encryptedContent)
        sealedObject.paramsAlg = Java.javaStringToPythonString(object.paramsAlg)
        sealedObject.encodedParams = Java.javaByteArrayToPythonByteString(object.encodedParams)
        
        return sealedObject
    
    def decrypt(self, password):
        """ Decrypt the sealed object using the password. """
        # Verify that algorithms are consistent.
        if self.paramsAlg != self.sealAlg:
            raise KeyStoreException("Cannot decrypt sealed object: conflicting sealing algorithms: %s vs %s." % (self.sealAlg, self.paramsAlg))
        
        # Get the encrypted content.
        encryptedContent = self.encryptedContent
        if encryptedContent is None or len(encryptedContent) == 0:
            raise KeyStoreException("Cannot decrypt sealed object: no encrypted content found.")

        # Decrypt the content.
        try:
            from pbeCiphers import PBECipherFactory
            cipher = PBECipherFactory().createCipher(self.sealAlg, self.encodedParams)
            return cipher.decrypt(encryptedContent, password)
        except Exception as e:
            print "*** SealedObject Decryption Error ***"
            import traceback
            traceback.print_exc(e)
            print "*************************************"
            raise KeyStoreException("Failed to decrypt sealed object", e)

    @classmethod
    def createInstance(self):
        """ Create an instance of the default implementation for the SealedObject interface. """
        return SealedObjectForKeyProtector()


class SealedObjectForKeyProtector(SealedObject):

    # @Override
    def toJavaObject(self):
        """ Convert the python object to a Java object. """
        return self.populateJavaObject(JavaSealedObjectForKeyProtector())

class EncryptedSecretKey(Encrypted, SecretKey):
    
    """ Class representing an encrypted secret key that must be decrypted before use. The
        payload is a javax.crypto.SealedObject instance. """
    
    def __init__(self, sealedObject):
        super(EncryptedSecretKey, self).__init__(type="EncryptedSecretKey")
        # Verify that a sealed object was provided.
        if sealedObject is None:
            raise ValueError("Cannot create encrypted secret key: no sealed object specified.")
        if not isinstance(sealedObject, SealedObject):
            raise ValueError("Cannot create encrypted secret key: sealed object has incorrect type %s." % type(sealedObject))
        self.sealedObject = sealedObject

    @SecretKey.algorithm.getter
    def algorithm(self):
        return self.delegate.algorithm

    @SecretKey.keyData.getter
    def keyData(self):
        return self.delegate.keyData
    
    @SecretKey.keySize.getter
    def keySize(self):
        return self.delegate.keySize

    # @Override
    def _decryptPayload(self, password):
        # Get the decrypted content from the sealed object.
        content = self.sealedObject.decrypt(password)
        
        # The decrypted content is a serialized javax.crypto.SecretKey instance.
        (object,_) = Java.readJavaObject(content)
        type = object.get_class()
        if type.name == 'javax.crypto.spec.SecretKeySpec':
            return self._createSecretKeyFromJavaSecretKeySpecObject(object)
        elif type.name == 'java.security.KeyRep':
            return self._createSecretKeyFromJavaKeyRepObject(object)
        else:
            raise KeyStoreException("Unsupported secret key implementation: %s" % type.name)
    
    def _createSecretKeyFromJavaSecretKeySpecObject(self, object):
        algorithm = object.algorithm
        key = Java.javaByteArrayToPythonByteString(object.key)
        return SecretKeySpec(algorithm=algorithm, key=key)

    def _createSecretKeyFromJavaKeyRepObject(self, object):
        # Sanity check.
        if object.type.constant != 'SECRET':
            raise KeyStoreException("Expected value 'SECRET' for KeyRep.type enum value, found '%s'" % object.type.constant)
        
        # Get the key bytes according to the key encoding.
        keyEncoding = object.format
        if keyEncoding == "RAW":
            key = Java.javaByteArrayToPythonByteString(object.encoded) 
        elif keyEncoding == "X.509":
            raise KeyStoreException("X.509 encoding for KeyRep objects not yet implemented")
        elif keyEncoding == "PKCS#8":
            raise KeyStoreException("PKCS#8 encoding for KeyRep objects not yet implemented")
        else:
            raise KeyStoreException("Unexpected key encoding '%s' found in serialized java.security.KeyRep object; expected one of 'RAW', 'X.509', 'PKCS#8'." % key_encoding)

        return SecretKeySpec(algorithm=object.algorithm, key=key)
        
    @classmethod
    def createFromSecretKeySpec(cls, secretKeySpec, password):
        """ Create a EncryptedSecretKey from a SecretKeySpec. """
        sealedObject = SealedObjectFactory().createSealedObject(object=secretKeySpec, password=password)
        return EncryptedSecretKey(sealedObject)
        
class JavaKeyStoreEncoder(JavaKeyStoreCodec):

    """ Class for encoding a java key store. """
    
    def __init__(self, password=''):
        super(JavaKeyStoreEncoder, self).__init__()
        if password is None:
            raise KeyStoreException("Must specify a store password when creating a java key store encoder.")
        self.password = password
    
    def encode(self, store):
        """ Encoded the key store. """
        if store is None:
            raise ValueError("Must specify a key store to encode.")
        encoding = bytearray()
        storeType = store.storeType if isinstance(store, JavaKeyStore) else 'jceks'
        encoding.extend(self.encodeMagicNumber(storeType))
        encoding.extend(self.encodeKeyStoreVersion())
        encoding.extend(self.encodeEntriesCount(store.entries))
        for (alias,entry) in store.entries.items():
            encoding.extend(self.encodeEntry(entry))
        encoding.extend(self.generateHash(encoding))
        return  bytes(encoding)
    
    def encodeMagicNumber(self, type):
        if type == 'jks':
            return JavaKeyStore.MAGIC_NUMBER_JKS
        if type is None or type == 'jceks':
            return JavaKeyStore.MAGIC_NUMBER_JCEKS
        raise KeyStoreException("Unsupported key store type: %s" % type)
    
    def encodeKeyStoreVersion(self):
        return b4.pack(2)

    def encodeEntriesCount(self, entries={}):
        return b4.pack(len(entries))

    def encodeEntry(self, entry):
        encoding = bytearray()
        encoding.extend(self.encodeEntryTag(entry))
        encoding.extend(self.encodeAlias(entry))
        encoding.extend(self.encodeTimeStamp(entry))
        encoding.extend(self.encodeEntryObject(entry))
        return bytes(encoding)

    def encodeEntryTag(self, entry):
        encoding = bytearray()
        if isinstance(entry.object, PrivateKey):
            encoding.extend(b4.pack(JavaKeyStoreEncoder.Tag.PRIVATE_KEY))
        elif isinstance(entry.object, Certificate):
            encoding.extend(b4.pack(JavaKeyStoreEncoder.Tag.CERTIFICATE))
        elif isinstance(entry.object, SecretKey):
            encoding.extend(b4.pack(JavaKeyStoreEncoder.Tag.SECRET_KEY))
        else:    
            raise KeyStoreException("Unsupported key store entry type: %s" % type(entry))
        return bytes(encoding)
    
    def encodeAlias(self, entry):
        return self.io.writeUtf8(entry.alias)

    def encodeTimeStamp(self, entry):
        return b8.pack(entry.timestamp)
    
    def encodeEntryObject(self, entry):
        if entry.encoding is None:
            entry.encoding = self._generateEntryEncoding(entry)
        return entry.encoding

    def _generateEntryEncoding(self, entry):
        """ Generate the encoding of the content of the key store entry. """
        if entry.object is None:
            raise KeyStoreException("Cannot encode key store entry '%s': no object to encode." % entry.alias)
        if isinstance(entry.object, EncryptedSecretKey):
            return self._encodeEncryptedSecretKey(entry.object)
        if isinstance(entry.object, EncryptedPrivateKey):
            return self._encodeEncryptedPrivateKey(entry.object)
        if isinstance(entry.object, CertificateSpec):
            return self._encodeCertificateSpec(entry.object)
        raise KeyStoreException("Cannot encoded key store entry '%s': unsupported object %s" % (entry.alias, type(entry.object)))

    def _encodeEncryptedSecretKey(self, encryptedSecretKey):
        return encryptedSecretKey.sealedObject.encodeJava()
    
    def _encodeEncryptedPrivateKey(self, encryptedPrivateKey):
        # return ASN1.EncryptedPrivateKeyInfo.encodeASN1(encryptedPrivateKey.encryptedPrivateKeyInfo)
        return encryptedPrivateKey.encryptedPrivateKeyInfo.encodeASN1()
    
    def _encodeCertificateSpec(self, certificateSpec):
        io = JavaKeyStoreIO()
        encoding = bytearray()
        encoding.extend(io.writeUtf8(certificateSpec.certificateType))
        encoding.extend(io.writeData(certificateSpec.certificateData))
        return bytes(encoding)
    
    def generateHash(self, data):
        import hashlib
        hashFn = hashlib.sha1
        passwordUtf16 = self.password.encode('utf-16be')
        return hashFn(passwordUtf16 + JavaKeyStore.SIGNATURE_WHITENING + data).digest()

class KeyStoreEntry(object):
    
    """ Class representing a key store entry. """
    
    def __init__(self, alias=None, timestamp=None, encoding=None, object=None):
        self._alias = alias          # The alias of the entry in the key store
        self._timestamp = timestamp  # The timestamp of the entry in the key store
        self._encoding = encoding    # The encoding of the entry in the key store.
        self._object = object        # The object of the entry in the key store (the decoded encoding).
        
    @property
    def alias(self):
        return self._alias

    @alias.setter
    def alias(self, alias):
        self._alias = alias

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp):
        self._timestamp = timestamp

    @property
    def object(self):
        return self._object
    
    @object.setter
    def object(self, object):
        self._object = object
        
    @property
    def encoding(self):
        """ Get the encoding of the key store entry object. """
        return self._encoding

    @encoding.setter
    def encoding(self, encoding):
        self._encoding = encoding

    @property
    def decrypted(self):
        """ Determines if the key store entry is decrypted. """
        return self.object.decrypted

    def decrypt(self, password=None):
        """ Decrypt the key store entry, using the (optional) password. """
        if not self.decrypted:
            self.object.decrypt(password)

class SealedObjectFactory(object):
    
    """ Factory class for creating SealedObject instances. """
    
    def __init__(self, config=None):
        if config is None:
            from pbeConfig import PBEConfig
            # TODO need to get a global config here...
            config = PBEConfig.getInstance()
        self.config = config
        
    def createSealedObject(self, object, password):
        # Verify that an object is provided.
        if object is None:
            raise ValueError("Cannot create SealedObject: no object specified.")
        # Verify that the object can be encoded to Java.
        if isinstance(object, Java.Encodable):
            content = object.encodeJava()
        elif isinstance(object, Java.Convertable):
            content = Java.writeJavaObject(object.toJavaObject())
        else:
            raise ValueError("Cannot create SealedObject: object of type %s cannot be encoded to Java." % type(object))
        return self._createSealedObject(content, password)
    
    def _createSealedObject(self, content, password):
        object = SealedObject.createInstance()
        object.sealAlg = self.config.algorithm
        object.encryptedContent = self._encryptContent(content, password)
        object.paramsAlg = self.config.algorithm
        object.encodedParams = self._generateEncodedParameters()
        return object
        
    def _encryptContent(self, content, password):
        from pbeCiphers import PBECipherFactory
        # Get password, if necessary.
        if password is None: 
            password = self.config.password
        # Create the encoded parameters.
        parameters = self._generateEncodedParameters()
        # Encrypt according to the algorithm.
        cipher = PBECipherFactory.createCipher(self.config.algorithm, parameters)
        return cipher.encrypt(content, password)
    
    def _generateEncodedParameters(self):
        from pbeCiphers import PBEParameter
        parameters = PBEParameter(self.config.salt, self.config.iterationCount)
        return parameters.encodeASN1()

class JavaSecretKeySpec(Java.Object):
    
    """ Class representing a javax.crypto.spec.SecretKeySpec instance. """
    
    def __init__(self, className='javax.crypto.spec.SecretKeySpec'):
        super(JavaSecretKeySpec, self).__init__(className)
        self.algorithm = None
        self.key = None
        
class JavaSealedObject(Java.Object):
    
    """ Class representing a javax.crypto.SealedObject instance. """
    
    def __init__(self, className='javax.crypto.SealedObject'):
        super(JavaSealedObject, self).__init__(className)
        self.encryptedContent = None
        self.encodedParams = None
        self.sealAlg = None
        self.paramsAlg = None
        
    @classmethod
    def createFrom(cls, object):
        """ Create a new sealed object from the specified object. """
        if object is None:
            raise ValueError("Cannot create JavaSealedObject from null object.")
        # Check if the object is a JavaSealedObject (e.g. from creating a new entry).
        if isinstance(object, JavaSealedObject):
            return object
        # Check if the object is a generated Java object (e.g. from deserializing an entry)
        if isinstance(object, javaobj.JavaObject):
            sealedObject = JavaSealedObject(className=Java.getClassName(object))
            sealedObject.sealAlg = object.sealAlg
            sealedObject.paramsAlg = object.paramsAlg
            sealedObject.encryptedContent = object.encryptedContent
            sealedObject.encodedParams = object.encodedParams
            return sealedObject
        raise ValueError("Cannot create JavaSealedObject from object of type %s" % type(object))
    
class JavaSealedObjectForKeyProtector(JavaSealedObject): 
    
    """ Class representing a com.sun.crypto.provider.SealedObjectForKeyProtector instance. """

    def __init__(self, className='com.sun.crypto.provider.SealedObjectForKeyProtector'):
        super(JavaSealedObjectForKeyProtector, self).__init__(className=className)

    
def createJavaClass_SecretKeySpec():
    # From the JDK 1.8 source code:
    #
    #  package package javax.crypto.spec;
    # 
    #  public class SecretKeySpec implements KeySpec, SecretKey {
    #    private static final long serialVersionUID = 6577238317307289933L;
    #    private byte[] key;
    #    private String algorithm;
    #    ..
    #  }
    return Java.createClass(name='javax.crypto.spec.SecretKeySpec',
                            serialVersionUID=6577238317307289933L,
                            fields=[('key','[B'),('algorithm', 'Ljava/lang/String')])

def createJavaClass_SealedObject():
    # From the JDK 1.8 source code:
    #
    #   package javax.crypto;
    # 
    #   public class SealedObject implements Serializable {
    #     static final long serialVersionUID = 4482838265551344752L;
    #     private byte[] encryptedContent = null;
    #     private String sealAlg = null;
    #     private String paramsAlg = null;
    #     protected byte[] encodedParams = null;
    #     ...
    #   }
    
    fields = [('encryptedContent','[B'), ('sealAlg', 'Ljava/lang/String'),\
              ('paramsAlg', 'Ljava/lang/String'), ('encodedParams', '[B')]
    return Java.createClass(name='javax.crypto.SealedObject', 
                            serialVersionUID=4482838265551344752L, 
                            fields=fields)
    
def createJavaClass_SealedObjectForKeyProtector():
    # From the JSK 1.8 source code:
    #
    #   package com.sun.crypto.provider;
    #
    #   final class SealedObjectForKeyProtector extends SealedObject {
    #     static final long serialVersionUID = -3650226485480866989L;
    #     ...
    #   }
    return Java.createClass(name='com.sun.crypto.provider.SealedObjectForKeyProtector',
                            serialVersionUID=-3650226485480866989L,
                            superClassName='javax.crypto.SealedObject')

# Create Java classes needed for serialization.
createJavaClass_SecretKeySpec()
createJavaClass_SealedObject()
createJavaClass_SealedObjectForKeyProtector()
