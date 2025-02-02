import hashlib

from asn1 import ASN1
from keystores import hexify # TODO move to another module to remove dependency on keystores

class PBEParameter(ASN1.Convertable, ASN1.Encodable):

    """ Class representing PBE parameters. """

    # PBEParameter ::= SEQUENCE {
    #   salt OCTET STRING (SIZE(8)),
    #   iterationCount INTEGER 
    #  }
    class ASN1Type(ASN1.Sequence, ASN1.Encodable):

        """ Class representing the ASN.1 type 'PBEParameter'. """
        
        componentType = ASN1.components([('salt', ASN1.OctetString()),\
                                         ('iterationCount', ASN1.Integer())])

    def __init__(self, salt, iterationCount):
        self._salt = salt
        self._iterationCount = iterationCount

    def __repr__(self):
        return "{salt:%s, iterationCount:%d}" % (hexify(self._salt), self._iterationCount)

    @property
    def salt(self):
        return self._salt

    @property
    def iterationCount(self):
        return self._iterationCount

    # @Override
    def encodeASN1(self, format='ber'):
        return self.toASN1Object().encodeASN1(format)

    # @Override
    @classmethod
    def decodeASN1(cls, encoding, format='ber'):
        """ Create a PBEParameter from an ASN.1 encoding. """
        object = PBEParameter.ASN1Type.decodeASN1(encoding, format)
        return cls.fromASN1Object(object)

    # @Override
    def toASN1Object(self):
        object = PBEParameter.ASN1Type()
        object['salt'] = ASN1.OctetString(self.salt)
        object['iterationCount'] = ASN1.Integer(self.iterationCount)
        return object

    # @Override
    @classmethod
    def fromASN1Object(cls, object):
        # Check for null.
        if object is None:
            return None
        # Verify that object is an ASN.1 PBEParameter value.
        if not isinstance(object, PBEParameter.ASN1Type):
            raise TypeError("Cannot create PBEParameter from ASN.1 object with type %s." % type(object))
        # Get the attributes from the ASN.1 object.
        salt = object['salt'].asOctets()
        iterationCount = int(object['iterationCount'])
        # Create the PBEParameter.
        return cls(salt=salt, iterationCount=iterationCount)

class PBECipher(object):

    """ Interface representing a cipher using password-based encryption. """

    def __init__(self, algorithm):
        if algorithm is None or len(algorithm) == 0:
            raise ValueError("Cannot create PBE cipher: no algorithm specified.")
        self._algorithm = algorithm

    @property
    def algorithm(self):
        return self._algorithm

    def encrypt(self, data, password):
        """ Encrypt the data using a key derived from the password. """
        raise NotImplementedError

    def decrypt(self, data):
        """ Decrypt the data using a key derived from the password. """
        raise NotImplementedError

class PBECipherSun(PBECipher):

    """ Base class for the Sun PBE ciphers. """

    def __init__(self, algorithm):
        super(PBECipherSun, self).__init__(algorithm)

    def _deriveKeyAndIV(self, password):
        if len(self.salt) != 8:
            raise ValueError("Expected 8-byte salt for %s, found %d bytes" % (self.algorithm, len(self.salt)))

        # Note: unlike JKS, the PBEWithMD5AndTripleDES algorithm as implemented for JCE keystores uses an ASCII string for the password, not a regular Java/UTF-16BE string.
        # It validates this explicitly and will throw an InvalidKeySpecException if non-ASCII byte codes are present in the password.
        # See PBEKey's constructor in com/sun/crypto/provider/PBEKey.java.
        try:
            passwordBytes = password.encode('ascii')
        except (UnicodeDecodeError, UnicodeEncodeError):
            raise ValueError("Key password contains non-ASCII characters")

        # Ensure that salt halves are not identical.
        saltHalves = ([self.salt[0:4], self.salt[4:8]])
        if saltHalves[0] == saltHalves[1]:
            saltHalves[0] = self._invertSaltHalf(saltHalves[0])

        derived = b""
        for i in range(2):
            toBeHashed = saltHalves[i]
            for k in range(self.iterationCount):
                toBeHashed = hashlib.md5(toBeHashed + passwordBytes).digest()
            derived += toBeHashed

        key = derived[:-8] # = 24 bytes
        iv = derived[-8:]
        return (key, iv)

    def _invertSaltHalf(self, saltHalf):
        """
        JCE's proprietary PBEWithMD5AndTripleDES algorithm as described in the OpenJDK sources calls for inverting the first salt half if the two halves are equal.
        However, there appears to be a bug in the original JCE implementation of com.sun.crypto.provider.PBECipherCore causing it to perform a different operation:

        for (i=0; i<2; i++) {
            byte tmp = salt[i];
            salt[i] = salt[3-i];
            salt[3-1] = tmp;     // <-- typo '1' instead of 'i'
        }

        The result is transforming [a,b,c,d] into [d,a,b,d] instead of [d,c,b,a] (verified going back to the original JCE 1.2.2 release for JDK 1.2).
        See source (or bytecode) of com.sun.crypto.provider.PBECipherCore (JRE <= 7) and com.sun.crypto.provider.PBES1Core (JRE 8+):
        """
        salt = bytearray(saltHalf)
        salt[2] = salt[1]
        salt[1] = salt[0]
        salt[0] = salt[3]
        return bytes(salt)


class PBECipherSunJKS(PBECipherSun):

    """ Implementation of Sun's proprietary JKS key protection algorithm. """

    NAME = "PBEWithSHA1AndXor"           # TODO guessed this name, confirm correct name
    OID = '1.3.6.1.4.1.42.2.17.1.1'

    def __init__(self):
        super(PBECipherSunJKS, self).__init__(PBECipherSunJKS.OID)

    # @Override
    def decrypt(self, data, password):
        # Copied from jks/sun_crypto.py
        passwordBytes = password.encode('utf-16be') # Java chars are UTF-16BE code units

        data = bytearray(data)
        (iv, data, check) = (data[:20], data[20:-20], data[-20:])
        xoring = zip(data, self._keystream(iv, passwordBytes))
        key = bytearray([d^k for d,k in xoring])

        # Verify the integrity of the encrypted data.
        if hashlib.sha1(bytes(passwordBytes + key)).digest() != check:
            raise BadHashCheckException("Bad hash check on private key; wrong password?")
        key = bytes(key)

        return key

    # TODO implement encrypt(data, password) operation

    def _keystream(self, iv, password):
        cur = iv
        while 1:
            xhash = hashlib.sha1(bytes(password + cur)) # hashlib.sha1 in python 2.6 does not accept a bytearray argument
            cur = bytearray(xhash.digest())             # make sure we iterate over ints in both Py2 and Py3
            for byte in cur:
                yield byte

    @classmethod
    def createPBECipher(cls, parameters=None):
        return cls()


class PBECipherSunJCE(PBECipherSun):

    """ Implementation of Sun's proprietary and unpublished PBEWithMD5AndTripleDES algorithm,
        a variant of PBEWithMD5AndDES. """

    NAME = 'PBEWithMD5AndTripleDES'
    OID  = '1.3.6.1.4.1.42.2.19.1'

    def __init__(self, salt, iterationCount):
        super(PBECipherSunJCE, self).__init__(PBECipherSunJCE.OID)
        # TODO verify that the salt length is 8 bytes.
        self._salt = salt
        self._iterationCount = iterationCount

    @property
    def salt(self):
        return self._salt

    @property
    def iterationCount(self):
        return self._iterationCount

    # @Override
    def encrypt(self, data, password):
        (key,iv) = self._deriveKeyAndIV(password)
        cipher = self._createCipher(key)
        cipher.initForEncryption(iv=iv)
        return cipher.encrypt(data)

    # @Override
    def decrypt(self, data, password):
        (key, iv) = self._deriveKeyAndIV(password)
        cipher = self._createCipher(key)
        cipher.initForDecryption(iv=iv)
        return cipher.decrypt(data)

    def _createCipher(self, key):
        from ciphers import CipherFactory
        cipher = CipherFactory().createCipher(cipherName='DESede/CBC/PKCS5Padding', key=key)
        return cipher

    @classmethod
    def createPBECipher(cls, parameters):
        """ Create a Sun JCE PBE cipher. The parameters are expected to be a byte string containing
            a BER-encoded PBEParameter value. """
        if parameters is None:
            raise ValueError("Cannot create PBE cipher '%s': no parameters specified." % cls.NAME)
        # Verify that the parameters are a byte string.
        if not isinstance(parameters, bytes):
            raise ValueError("Cannot create PBE cipher '%s': expected parameters of type byte[] but found type %s." % \
                             (cls.NAME, type(parameters)))
        # Create PBEParameter from ASN.1 encoding.
        parameters = PBEParameter.decodeASN1(parameters)
        return cls(salt=parameters.salt, iterationCount=parameters.iterationCount)


class PBECipherFactory(object):

    """ Class for creating PBECipher instances. """

    # Mappings of algorithm names and algorithm.
    ciphers = [PBECipherSunJCE, PBECipherSunJKS]

    @classmethod
    def createCipher(cls, algorithm, parameters=None):
        """ Create a PBE cipher from the algorithm and the optional parameters. """
        # Verify that an algorithm is specified.
        if algorithm is None:
            raise ValueError("Cannot create PBE cipher: no algorithm specified.")
        # Find the matching cipher type from the algorithm.
        for cipher in cls.ciphers:
            if algorithm == cipher.NAME or algorithm == cipher.OID:
                return cipher.createPBECipher(parameters)
        raise ValueError("Cannot create PBE cipher: unsupported algorithm: '%s'." % algorithm)
