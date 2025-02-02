import logging

def logDebug(message):
    if message:
        logging.debug(message)

def logWarning(message):
    if message:
        logging.warning(message)

def logError(message):
    if message:
        logging.error(message)
        
def hexify(v):
    import binascii
    return binascii.hexlify(v) if v is not None else 'None'


class CryptoException(Exception): pass
# TODO create subclasses: BadPaddingException, etc.

class Cipher(object):

    """ Class representing an abstract cipher. """
    
    class Mode:

        """ Defines various cipher mode constants. """

        ENCRYPT = 1
        DECRYPT = 2

    class BlockMode:

        """ Defines various block cipher mode constants. """

        ECB = 'ECB'    # electronic code book
        CBC = 'CBC'    # cipher block chaining 
        CFB = 'CFB'    # cipher feedback mode
        GCM = 'GCM'    # galois counter mode
        OCB = 'OCB'    # offset code book mode
        EAX = 'EAX'    # ???
        CTR = 'CTR'    # counter mode
        CCM = 'CCM'    # counter mode with CBC MAC.
        
        @staticmethod
        def default():
            """ Get the default block mode. """
            return Cipher.BlockMode.CFB

        @staticmethod
        def defaultBlockModeForAlgorithm(algorithm):
            if algorithm == 'DES' or algorithm == 'DESede':
                return Cipher.BlockMode.CBC
            if algorithm == 'AES':
                return Cipher.BlockMode.GCM
            return Cipher.BlockMode.default()
        
        @staticmethod
        def values():
            """ Get a list of all block mode values. """
            return [Cipher.BlockMode.ECB, Cipher.BlockMode.CBC, Cipher.BlockMode.CFB,
                    Cipher.BlockMode.GCM, Cipher.BlockMode.OCB, Cipher.BlockMode.EAX,
                    Cipher.BlockMode.CTR, Cipher.BlockMode.CCM]
        
        @staticmethod
        def supportsMAC(mode):
            """ Determine if the block mode supports message authentication codes. """
            return mode in [Cipher.BlockMode.GCM, Cipher.BlockMode.OCB, 
                            Cipher.BlockMode.EAX, Cipher.BlockMode.CCM]
        
        @staticmethod
        def parse(string):
            """ Parse a cipher block mode string and return matching cipher block mode constant. """
            for mode in Cipher.BlockMode.values():
                if string == mode:
                    return mode
            raise CryptoException("Unknown cipher block mode: '%s'" % string)
        
    class Padding:

        """ Defines various padding constants. Consistent with JCE padding names. """

        NONE  = 'NoPadding'
        PKCS1 = 'PKCS1Padding'
        PKCS5 = 'PKCS5Padding'
        PKCS7 = 'PKCS7Padding'
        OAEPWithSHA1AndMGF1 = 'OAEPWithSHA-1AndMGF1Padding'
        OAEPWithSHA256AndMGF1 = 'OAEPWithSHA-256AndMGF1Padding'
        
        @staticmethod
        def default():
            """ Get the default padding value. """
            return Cipher.Padding.NONE
        
        @staticmethod
        def defaultPaddingForBlockMode(blockMode):
            if blockMode == Cipher.BlockMode.GCM:
                return Cipher.Padding.NONE
            return Cipher.Padding.default()
        
        @staticmethod
        def values():
            """ Get a list of all padding values. """
            return [Cipher.Padding.NONE,Cipher.Padding.PKCS1,Cipher.Padding.PKCS5,
                    Cipher.Padding.OAEPWithSHA1AndMGF1,Cipher.Padding.OAEPWithSHA256AndMGF1]

        @staticmethod
        def parse(string):
            """ Parse a padding string and return the corresponding padding constant. """
            for padding in Cipher.Padding.values():
                if string == padding:
                    return padding
            raise CryptoException("Unknown cipher padding: '%s'" % string)
        
        
    class Transformation:
        
        """ Class representing a cipher transformation, containing an algorithm, and 
            optional block mode and padding, e.g. 'DES', 'AES/GCM/NoPadding'. """
        
        # The cache of known cipherName -> Transformation mappings.
        cache = {}
        
        def __init__(self, algorithm, blockMode=None, padding=None):
            self.algorithm = algorithm
            self.blockMode = blockMode
            self.padding = padding
            
        def __repr__(self):
            if self.blockMode is None or self.padding is None:
                return self.algorithm
            return "%s/%s/%s" % (self.algorithm, self.blockMode, self.padding)
        
        @classmethod
        def parse(cls, cipherName):
            """ Parse a cipher name and return the transformation. """
            # Check for existing transformation in the cache,
            if cipherName in Cipher.Transformation.cache:
                return cls.cache[cipherName]
            
            # Create new transformation and store in the cache.
            transformation = cls._parseCipherName(cipherName)
            cls.cache[cipherName] = transformation
            return transformation
        
        @classmethod
        def _parseCipherName(cls, cipherName):
            tokens = cipherName.split('/')
            # The cipher name is in the form: algorithm , e.g. 'DES', 'AES'.
            if len(tokens) == 1:
                algorithm = tokens[0]
                blockMode = Cipher.BlockMode.defaultBlockModeForAlgorithm(algorithm)
                padding = Cipher.Padding.defaultPaddingForBlockMode(blockMode)
                transformation = cls(algorithm, blockMode, padding)
            # The cipher name is in the form: algorithm/mode/padding, e.g. 'DES/CBC/PKCS5Padding', etc.
            elif len(tokens) == 3:
                algorithm = tokens[0]
                blockMode = Cipher.BlockMode.parse(tokens[1])
                padding = Cipher.Padding.parse(tokens[2])
                transformation = cls(algorithm, blockMode, padding)
            else:
                raise CryptoException("Invalid cipher name: '%s'" % cipherName)
            return transformation
        
    @staticmethod
    def hasBlockMode(cipherName, blockMode):
        """ Determines if the cipher name has the block mode. """
        return Cipher.getBlockMode(cipherName) == blockMode

    @staticmethod
    def isECB(cipherName):
        """ Determines if the cipher name indicates ECB mode. """
        return Cipher.hasBlockMode(cipherName, Cipher.BlockMode.ECB)

    @staticmethod
    def isGCM(cipherName):
        """ Determines if the cipher name indicates GCM mode. """
        return Cipher.hasBlockMode(cipherName, Cipher.BlockMode.GCM)

    @staticmethod
    def getAlgorithm(cipherName):
        """ Get the algorithm name from a cipher name, e.g. if the cipher name
            is 'DES' then the algorithm name is 'DES', and if the cipher name 
            is 'AES/GCM/NoPadding' then the algorithm name is 'AES'. """
        transformation = Cipher.Transformation.parse(cipherName)
        return transformation.algorithm

    @staticmethod
    def getBlockSize(algorithm):
        """ Get the block size (in bytes) for a cipher algorithm."""
        algorithm = Cipher.getAlgorithm(algorithm)
        if algorithm == 'DES' or algorithm == 'DESede':
            return 8 # 64 its
        if algorithm == 'AES':
            return 16 # 128 bits
        # TODO add support for RSA?
        raise CryptoException("Cannot determine block size for cipher algorithm: %s" % algorithm)

    @staticmethod
    def getBlockMode(cipherName):
        """ Get the block mode from the cipher name, e.g. if the cipher name
            is 'AES/GCM/NoPadding' then the block mode is 'GCM', and if the 
            cipher name is 'DES' then the block mode is CFB (the default block
            mode). Returns None if the block mode cannot be determined. """
        transformation = Cipher.Transformation.parse(cipherName)
        return transformation.blockMode
        
    @classmethod
    def getPadding(cls,cipherName):
        """ Get the padding algorithm (implicitly) contained in the cipher name. """
        transformation = Cipher.Transformation.parse(cipherName)
        return transformation.padding
    
    @staticmethod
    def getKeySize(cipherName):
        algorithm = Cipher.Transformation.parse(cipherName).algorithm
        if algorithm == 'DES':
            return 56
        if algorithm == 'DESede':
            return 168   # 3 x 56
        if algorithm == 'AES':
            return 128
        # TODO add support for RSA (1024 or 2048)
        raise CryptoException("Cannot determine key size for cipher algorithm %s" % algorithm)
    
    @classmethod
    def requiresIV(cls, cipherName):
        """ Determines if the cipher requires an IV. """
        blockMode = Cipher.getBlockMode(cipherName)
        return not blockMode in [Cipher.BlockMode.ECB, Cipher.BlockMode.CCM]
    
    def __init__(self, cipherName, key, rng=None):
        # TODO should be using 'transform' (with algorithm, mode, padding properties) not 'cipherName'
        self.cipherName = cipherName
        self.key = key
        self.rng = rng or newRandomNumberGenerator()
        self.cipherMode = None
        self.iv = None
        # Only for those ciphers that support MAC (e.g. AES/GCM/*, etc)
        self.macLength = None
        self.nonce = None
        
    def initForEncryption(self, iv=None):
        """ Initialize the cipher for encryption. """
        logDebug("Initializing cipher %s for encryption, iv=%s" % (self.cipherName, hexify(iv)))
        self.cipherMode = Cipher.Mode.ENCRYPT
        self.iv = iv or self.generateIV()
        
    def initForDecryption(self, iv=None):
        """ Initialize the cipher for decryption. """
        logDebug("Initializing cipher %s for decryption, iv=%s" % (self.cipherName, hexify(iv)))
        self.cipherMode = Cipher.Mode.DECRYPT
        if iv is None and Cipher.requiresIV(self.cipherName):
            raise CryptoException("No IV specified for cipher '%s'." % self.cipherName)
        # TODO verify that len(iv) == block size? Although AES may have 12-byte IV?
        self.iv = iv
    
    def encrypt(self, plainText):
        """ Encrypt the plain text (as byte array) and return cipher text (as byte array). """
        raise CryptoException("Cipher '%s' does not support 'encrypt' operation." % self.cipherName)
    
    def decrypt(self, cipherText):
        """ Decrypt the cipher text (as byte array) and return the plain text (as byte array). """
        raise CryptoException("Cipher '%s' does not support 'decrypt' operation." % self.cipherName)

    def updateAAD(self, data):
        """ Updates the associated authentication data for the cipher. Only for ciphers 
            that support MAC (AES/GCM/*, etc). """
        raise CryptoException("Cipher '%s' does not support 'update' operation." % self.cipherName)

    def digest(self):
        """ Returns the MAC of the cipher. Only for for ciphers that support MAC (AES/GCM/*, etc). """
        
    def verify(self):
        """ Verifies the digest of the cipher. Only for ciphers that support MAC (AES/GCM/*, etc). """
        raise CryptoException("Cipher '%s' does not support 'verify' operation" % self.cipherName)

    def encryptAndDigest(self, cipherText):
        """ Encrypts and digests the data in one operation. Only for ciphers that support MAC (AES/GCM/*, etc). """
        raise CryptoException("Cipher '%s' does not support 'encryptAndDigest()' operation." % self.cipherName)
    
    def decryptAndVerify(self, cipherText, mac):
        """ Decrypts and verifies the data in one operation. Only for ciphers that support MAC (AES/GCM/*, etc). """
        raise CryptoException("Cipher '%s' does not support 'decryptAndVerify()' operation." % self.cipherName)
    
    @property
    def supportsMAC(self):
        """ Indicates if the cipher supports message authentication codes (and will thus
            allow the update(), digest(), and verify() methods). """
        return Cipher.BlockMode.supportsMAC(self.blockMode)
    
    @property
    def blockMode(self):
        """ Gets the block mode of the cipher. """
        return Cipher.getBlockMode(self.cipherName)
    
    @property
    def padding(self):
        return Cipher.getPadding(self.cipherName)
    
    @property
    def algorithm(self):
        """ Gets the algorithm name of the cipher, e.g. if the cipher name is 'AES/GCM/NoPadding'
            then the algorithm name is 'AES', and if the cipher name is 'DES' then the algorithm
            name is 'DES', etc. """
        return Cipher.getAlgorithm(self.cipherName)
    
    @property
    def blockSize(self):
        """ Get the block size of the cipher. """
        return Cipher.getBlockSize(self.cipherName)

    def generateIV(self):
        """ Generate an IV for the cipher. """
        # TODO An IV is not necessary for ECB/CTR modes.
        # TODO ... or return a block of zero bytes, per PyCrypto?
        return self.rng.read(self.blockSize)
    
class PyCryptoAdapter:
    
    """ Class for adapting  Cipher.* values to PyCrypto.* values. """

    _blockModeMappings = None

    @classmethod
    def getBlockMode(cls, blockMode):
        """ Get the PyCrypto block mode matching the Cipher.BlockMode """
        mappings = cls._getBlockModeMappings()
        if blockMode in mappings:
            return mappings[blockMode]
        return None
    
    @classmethod
    def _getBlockModeMappings(cls):
        if cls._blockModeMappings is None:
            cls._blockModeMappings = cls._loadBlockModeMappings()
        return cls._blockModeMappings

    @classmethod
    def _loadBlockModeMappings(cls):
        # Using AES as it has all the modes defined.
        mappings = {}
        for mode in Cipher.BlockMode.values():
            try:
                from Crypto.Cipher import AES
                mapping = getattr(AES, 'MODE_%s' % mode)
                mappings[mode] = mapping
            except AttributeError:
                # Possible that an incompatible version of PyCrypto library is on
                # the path. Location of the AES file will show where PyCrypto is 
                # located. If the system Python is used it may contain an old version 
                # of PyCrypto that needs to be replaced with PyCryptoDome.
                logWarning("Could not map cipher block mode %s to a Crypto.Cipher.* mode" % mode)
                logWarning("AES module loaded from file %s" % AES.__file__)
                raise CryptoException("Could not map cipher block mode %s. Incompatible crypto implementation?" % mode)
        return mappings

class PyCryptoCipher(Cipher):
    
    """ A cipher that wraps a PyCrypto Cipher. """
    
    def __init__(self, cipherName, key, rng=None):
        super(PyCryptoCipher, self).__init__(cipherName, key, rng)
        self._cipher = None
        self._padder = None
        self._allowedOps = self._createAllowedOps()
    
    def _createAllowedOps(self, ops=[]):
        allowedOps = [self.initForEncryption, self.initForDecryption]
        if ops is not None:
            allowedOps.extend(ops)
        return allowedOps
    
    def _checkAllowedOp(self, op):
        if op is not None and not op in self._allowedOps:
            raise CryptoException("Invalid crypto operation %s" % op)
        
    @property
    def padder(self):
        if self._padder is None:
            algorithm = Cipher.getPadding(self.cipherName)
            self._padder = Padder.createPadder(algorithm, self.blockSize)
        return self._padder

    @property
    def cipher(self):
        """ Get the underlying PyCrypto cipher object. """
        if self._cipher is None:
            if self.cipherMode is None:
                raise CryptoException("Cipher '%s' has not been initialized." % self.cipherName)
            self._cipher = self._createCipher()
        return self._cipher

    def _createCipher(self):
        raise NotImplementedError

    @cipher.setter
    def cipher(self, cipher):
        """ Set the underlying PyCrypto cipher object. """
        self._cipher = cipher

    def pad(self, m):
        """ Add padding to the message 'm'. """
        return self.padder.add(m)

    def strip(self, m):
        """ Strip padding from the message 'm'. """
        return self.padder.strip(m)

    # @Override    
    def initForEncryption(self, iv=None):
        self._checkAllowedOp(self.initForEncryption)
        super(PyCryptoCipher, self).initForEncryption(iv=iv)
        if self.supportsMAC:
            self.nonce = self.iv
            self.macLength = 16
        self._allowedOps = self._createAllowedOps([self.updateAAD, self.encrypt, self.digest])    
            
    # @Override    
    def initForDecryption(self, iv=None):
        self._checkAllowedOp(self.initForDecryption)
        super(PyCryptoCipher, self).initForDecryption(iv=iv)
        if self.supportsMAC:
            self.nonce = self.iv
            self.macLength = 16
        self._allowedOps = self._createAllowedOps([self.updateAAD, self.decrypt, self.verify])
            
    # @Override
    def encrypt(self, data):
        self._checkAllowedOp(self.encrypt)
        # Verify that cipher has been initialized for encryption.
        if self.cipherMode != Cipher.Mode.ENCRYPT:
            raise CryptoException("Cipher %s has not been initialized for encryption." % self.cipherName)
        # Encrypt the padded data.
        encrypted = self.cipher.encrypt(self.pad(data))
        # self.cipher = None
        self._allowedOps = self._createAllowedOps([self.digest])
        return encrypted
    
    # @Override
    def decrypt(self, encrypted):
        self._checkAllowedOp(self.decrypt)
        # Verify that cipher has been initialized for decryption.
        if self.cipherMode != Cipher.Mode.DECRYPT:
            raise CryptoException("Cipher %s has not been initialized for decryption." % self.cipherName)
        # Decrypt the data then remove the padding.
        padded = self.cipher.decrypt(encrypted)
        decrypted = self.strip(padded)
        # self.cipher = None
        self._allowedOps = self._createAllowedOps([self.verify])
        return decrypted
    
    # @Override    
    def updateAAD(self, data):
        self._checkAllowedOp(self.updateAAD)
        self.cipher.update(data)
        # self._allowedOps is unchanged.
        
    # @Override    
    def digest(self):
        self._checkAllowedOp(self.digest)
        self._allowedOps = self._createAllowedOps()
        return self.cipher.digest()
        
    # @Override
    def verify(self, mac):
        self._checkAllowedOp(self.verify)
        self.cipher.verify(mac)
        self._allowedOps = self._createAllowedOps()

    # @Override
    def encryptAndDigest(self, data):
        """ Encrypt and digest the data. Returns tuple (encryptedData, mac). """
        self._checkAllowedOp(self.encrypt)
        self._checkAllowedOp(self.digest)
        # Verify that cipher has been initialized for encryption.
        if self.cipherMode != Cipher.Mode.ENCRYPT:
            raise CryptoException("Cipher %s has not been initialized for encryption." % self.cipherName)
        (encrypted, mac) = self.cipher.encrypt_and_digest(self.pad(data))
        # self.cipher = None
        self._allowedOps = self._createAllowedOps()
        return (encrypted, mac)
    
    # @Override
    def decryptAndVerify(self, cipherText, mac):
        """ Decrypt and verify the encrypted data and MAC. """
        self._checkAllowedOp(self.decrypt)
        self._checkAllowedOp(self.verify)
        # Verify that cipher has been initialized for decryption.
        if self.cipherMode != Cipher.Mode.DECRYPT:
            raise CryptoException("Cipher %s has not been initialized for decryption." % self.cipherName)
        decrypted = self.cipher.decrypt_and_verify(cipherText, mac)
        # self.cipher = None
        self._allowedOps = self._createAllowedOps()
        return self.strip(decrypted)
    
class DESCipher(PyCryptoCipher):

    """ Implementation of DES cipher wrapping PyCrypto DES cipher. """
    
    ALGORITHM = 'DES'
    
    def __init__(self, cipherName, key, rng=None):
        super(DESCipher, self).__init__(cipherName, key, rng)

    # @Override
    def _createCipher(self):
        logDebug("Creating DES cipher, block mode=%s, iv=%s" % (self.blockMode, hexify(self.iv)))
        
        # Verify that an IV is available.
        if self.iv is None:
            raise CryptoException("An IV is required to create cipher '%s'." % self.cipherName)

        # Get the PyCrypto block mode.
        blockMode = PyCryptoAdapter.getBlockMode(self.blockMode)
        if blockMode is None:
            raise CryptoException("Cannot create DES cipher: block mode %s is not supported by crypto provider." % self.blockMode)

        from Crypto.Cipher import DES
        return DES.new(key=self.key, mode=blockMode, iv=self.iv)

class TripleDESCipher(PyCryptoCipher):
    
    """ Implementation of the TripleDES (DESede) )cipher wrapping PyCrypto DESede cipher. """
    
    ALGORITHM = 'DESede'
    
    def __init__(self, cipherName, key, rng=None):
        super(TripleDESCipher, self).__init__(cipherName, key, rng)
        
    # @Override
    def _createCipher(self):
        logDebug("Creating TripleDES cipher, block mode=%s, iv=%s" % (self.blockMode, hexify(self.iv)))

        # Verify that an IV is available.
        if self.iv is None:
            raise CryptoException("An IV is required to create cipher '%s'." % self.cipherName)

        # Get the PyCrypto block mode.
        blockMode = PyCryptoAdapter.getBlockMode(self.blockMode)
        if blockMode is None:
            raise CryptoException("Cannot create TripleDES cipher: block mode %s is not supported by crypto provider." % self.blockMode)

        from Crypto.Cipher import DES3
        return DES3.new(key=self.key, mode=blockMode, iv=self.iv)

class AESCipher(PyCryptoCipher):
    
    """ Implementation of AES cipher wrapping PyCrypto AES cipher. """
    
    ALGORITHM = 'AES'
    
    def __init__(self, cipherName, key, rng=None):
        super(AESCipher, self).__init__(cipherName, key, rng)
    
    # @Override
    def _createCipher(self):
        logDebug("Creating AES cipher, block mode=%s, iv=%s" % (self.blockMode, hexify(self.iv)))
        
        # TODO verify that blockSize=16, and keySize in (16,24,32)

        # Get the PyCrypto cipher mode.
        blockMode = PyCryptoAdapter.getBlockMode(self.blockMode)
        if blockMode is None:
            raise CryptoException("Cannot create AES cipher: block mode %s is not supported by crypto provider." % self.blockMode)

        # Require a nonce and macLength if cipher supports MAC.
        if self.supportsMAC:
            if self.nonce is None:
                raise CryptoException("A nonce is required to create cipher '%s'." % self.cipherName)
            if self.macLength is None:
                raise CryptoException("A tag length is required to create cipher '%s'." % self.cipherName)
            from Crypto.Cipher import AES
            return AES.new(key=self.key, mode=blockMode, nonce=self.nonce, mac_len=self.macLength)
        
        # For other modes, require an IV.
        if self.iv is None and Cipher.requiresIV(self.cipherName):
            raise CryptoException("An IV is required to create cipher '%s'." % self.cipherName)

        from Crypto.Cipher import AES
        return AES.new(key=self.key, mode=blockMode, iv=self.iv)

def newRandomNumberGenerator():
    """ Returns a new random number generator. """
    from Crypto import Random
    return Random.new()

class CipherFactory(object):

    """ Class for creating ciphers. """
    
    ciphers = [DESCipher, TripleDESCipher, AESCipher]
    
    def __init__(self, rng=None):
        """ Create a new cipher factory with given RNG (or new RNG is created). """
        self.rng = rng or newRandomNumberGenerator()
        
    def createCipher(self, cipherName, key):
        """ Create a Cipher instance for the given cipher name and secret key. """
        # Verify that a cipher name is specified.
        if cipherName is None:
            raise ValueError("Cannot create cipher: no cipher name specified.")
        # Verify that a key is specified.
        if key is None:
            raise ValueError("Cannot create cipher: no key specified.")
        
        logDebug("Creating cipher: cipherName=%s" % cipherName)
        
        transformation = Cipher.Transformation.parse(cipherName)
        
        # TODO fail if the algorithm is DES, RC4, etc.
        
        # Block mode ECB is not supported (too weak).
        if transformation.blockMode == Cipher.BlockMode.ECB:
            raise CryptoException("Cipher mode ECB is not supported")

        # Create the appropriate cipher, according to the algorithm.      
        for cipher in CipherFactory.ciphers:
            if transformation.algorithm == cipher.ALGORITHM:
                return cipher(cipherName, key, self.rng)
        
        raise ValueError("Cannot create cipher: unsupported name '%s'." % cipherName)
        
    
class SecretKeyFactory(object):
    
    """ Class for creating secret keys. """
    
    def __init__(self, rng=None):
        self.rng = rng or newRandomNumberGenerator()
        
    def createSecretKey(self, algorithm):
        if algorithm is None:
            raise CryptoException("Must specify an algorithm when creating a secret key")
        logDebug("Creating secret key for algorithm '%s'." % algorithm)
        keySize = Cipher.getKeySize(algorithm)
        key = self.rng.read(keySize/8)
        return key

class Padder(object):

    """ Interface for padding operations. """
    
    def __init__(self, algorithm):
        self._algorithm = algorithm
        
    @property
    def algorithm(self):
        return self._algorithm
    
    def add(self, m):
        """ Add padding to the message 'm'. """
        raise NotImplementedError

    def strip(self, m):
        """ Strip padding from the message 'm'. """
        raise NotImplementedError

    @classmethod
    def createPadder(cls, algorithm, blockSize=None):
        """ Create a padder instance from the padding algorithm (and optional block size). """
        if algorithm == Cipher.Padding.NONE:
            return NoPadder()
        if algorithm == Cipher.Padding.PKCS5:
            return PKCS5Padder()
        if algorithm == Cipher.Padding.PKCS7:
            return PKCS7Padder(blockSize)
        raise CryptoException("Unsupported padding algorithm: %s" % algorithm)
    
class NoPadder(Padder):
    
    """ Implementation of the NoPadding operation. """
    
    def __init__(self):
        super(NoPadder, self).__init__(algorithm=Cipher.Padding.NONE)
        
    # @Override
    def add(self, m):
        return m

    # @Override
    def strip(self, m):
        return m
    
class PKCS5Padder(Padder):

    """ Implementation of PKCS#5 padding. """

    def __init__(self):
        super(PKCS5Padder, self).__init__(algorithm=Cipher.Padding.PKCS5)
        self.delegate = PKCS7Padder(8)
        
    # @Override
    def add(self, m):
        """Add PKCS#5 padding to a message.""" 
        return self.delegate.add(m)

    # @Override
    def strip(self, m):
        """ Strip PKCS#5 padding from a message. """
        return self.delegate.strip(m)

class PKCS7Padder(Padder):

    """ Implementation of PKCS#7 padding. """

    def __init__(self, blockSize):
        super(PKCS7Padder, self).__init__(algorithm=Cipher.Padding.PKCS7)
        if blockSize <= 0 or blockSize > 255:
            raise ValueError("Invalid block size for PKCS#7 padding: %d" % blockSize)
        self.blockSize = blockSize

    # @Override    
    def add(self, m):
        """ Add PKCS#7 padding to a message. """
        from Crypto.Util import Padding
        return Padding.pad(m, self.blockSize, 'pkcs7')

    # @Override
    def strip(self, m):
        """ Strip PKCS#7 padding from a message. """
        from Crypto.Util import Padding
        return Padding.unpad(m, self.blockSize, 'pkcs7')
