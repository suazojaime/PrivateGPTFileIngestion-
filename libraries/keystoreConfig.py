class KeyStoreConfigSPI(object):

    """ Service Provider Interface for KeyStoreConfig """

    def getKeyStoreFile(self):
        """Get the location of the keystore file."""
        raise NotImplementedError

    def getKeyStorePassword(self):
        """ Get the password for decrypting the keystore."""
        raise NotImplementedError

class DefaultKeyStoreConfigSPI(KeyStoreConfigSPI):

    # @Override
    def getKeyStoreFile(self):
        return "keystore.jks"

    # @Override
    def getKeyStorePassword(self):
        return "keystore"

class KeyStoreConfigSPIFactory:

    cache = {}

    @classmethod
    def getInstance(cls, name='default', config=None):
        instance = cls.cache.get(name)
        if instance is None:
            instance = cls.loadInstance(name, config)
            if instance is None:
                raise ValueError("Cannot find key store configuration '%s'" % name)
            # print "## loaded keystore configuration '%s':" % name
            # print "##   keyStoreFile    : %s" % instance.getKeyStoreFile()
            # print "##   keyStorePassword: %s" % instance.getKeyStorePassword()
            cls.cache[name] = instance
        return instance

    @classmethod
    def loadInstance(cls, name='default', config=None):
        if name == 'default':
            instance = cls.importInstance(name='keystoreConfig_custom', config=config)
            if instance is not None:
                return instance
            return DefaultKeyStoreConfigSPI()
        return cls.importInstance(name, config)

    @classmethod
    def importInstance(cls, name, config=None):
        # Verify that a name was provided.
        if name is None:
            raise ValueError("Must specify a name when importing a keystore configuration.")
        # Import the module.
        import importlib
        try:
            module = importlib.import_module(name)
        except ImportError as e:
            print "Warning: Cannot import keystore configuration '%s': %s" % (name, str(e))
            return None
        # Look for the 'getInstance()' function.
        try:
            getInstance = getattr(module, 'getInstance')
        except AttributeError:
            print "Warning: keystore configuration '%s' does not have a 'getInstance()' function" % name
            return None
        # Invoke the function.
        return getInstance(config)

class KeyStoreConfig(object):

    """ Interface representing the key store configuration. """

    def __init__(self, spi=None):
        self.spi = spi or DefaultKeyStoreConfigSPI()
        self._keyStoreFile = None
        self._keyStorePassword = None

    def __repr__(self):
        return "{keyStoreFile:%s,keyStorePassword:%s}" % (self._keyStoreFile,self._keyStorePassword)

    @property
    def keyStoreFile(self):
        """ Get the location of the key store file. """
        if self._keyStoreFile is None:
            self._keyStoreFile = self.spi.getKeyStoreFile()
        return self._keyStoreFile

    @keyStoreFile.setter
    def keyStoreFile(self, keyStoreFile):
        self._keyStoreFile = keyStoreFile

    @property
    def keyStorePassword(self):
        """ Get the password for accessing the key store. """
        if self._keyStorePassword is None:
            self._keyStorePassword = self.spi.getKeyStorePassword()
        return self._keyStorePassword

    @keyStorePassword.setter
    def keyStorePassword(self, keyStorePassword):
        self._keyStorePassword = keyStorePassword

    @staticmethod
    def getInstance(name='default', config=None):
        """ Get an instance of the key store defaults. Currently using defaults version 1. """
        spi = KeyStoreConfigSPIFactory.getInstance(name=name, config=config)
        return KeyStoreConfig(spi)
