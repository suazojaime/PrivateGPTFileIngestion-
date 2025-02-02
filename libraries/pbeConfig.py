class PBEConfigSPI(object):
    
    """Service provider interface for PBE config."""
    
    def getSalt(self): raise NotImplementedError
    def getIterationCount(self): raise NotImplementedError
    def getAlgorithm(self): raise NotImplementedError
    def getPassword(self): raise NotImplementedError

class DefaultPBEConfigSPI(PBEConfigSPI):

    """The default PBEConfigSPI."""

    # @Override
    def getSalt(self):
        return "CAFEBABE".encode('utf-8')

    # @Override
    def getIterationCount(self):
        return 20

    # @Override
    def getAlgorithm(self):
        return "PBEWithMD5AndTripleDES"

    # @Override
    def getPassword(self):
        return "password"

class PBEConfigSPIFactory:

    cache = {}

    @classmethod
    def getInstance(cls, name='default', config=None):
        # Verify that a name was specified.
        if name is None:
            raise ValueError("Must specify a name when getting a PBE configuration.")
        # Check the cache for an existing instance.
        instance = cls.cache.get(name)
        if instance is None:
            instance = cls.loadInstance(name, config)
            if instance is None:
                raise ValueError("Cannot find PBE configuration '%s'" % name)
            # from binascii import hexlify
            # print "## loaded PBE configuration '%s':" % name
            # print "##   salt          : %s" % hexlify(instance.getSalt())
            # print "##   iterationCount: %d" % instance.getIterationCount()
            # print "##   algorithm     : %s" % instance.getAlgorithm()
            # print "##   password      : %s" % instance.getPassword()
            cls.cache[name] = instance
        return instance

    @classmethod
    def loadInstance(cls, name='default', config=None):
        # Check for the default configuration.
        if name == 'default':
            # Check for a custom config.
            instance = cls.importInstance('pbeConfig_custom', config)
            if instance is not None:
                return instance
            # Otherwise return the default config.
            return DefaultPBEConfigSPI()
        # Otherwise load the configuration module.
        return cls.importInstance(name, config)

    @classmethod
    def importInstance(cls, name='default', config=None):
        # Verify that a name was provided.
        if name is None:
            raise ValueError("Must specify a name when importing a PBE configuration.")
        # Import the configuration module.
        import importlib
        try:
            module = importlib.import_module(name)
        except ImportError as e:
            print "Warning: cannot import PBE configuration '%s': %s" % (name, str(e))
            return None
        # Get the 'getInstance()' function from the module.
        try:
            getInstance = getattr(module, 'getInstance')
        except AttributeError:
            print "Warning: PBE configuration '%s' does not have a 'getInstance()' function." % name
            return None
        # Invoke the 'getInstance()' function.
        return getInstance(config)

class PBEConfig(object):

    """ Interface representing the password-based encryption (PBE) configuration. """

    def __init__(self, spi):
        self.spi = spi or DefaultPBEConfigSPI()
        self._salt = None
        self._iterationCount = None
        self._algorithm = None
        self._password = None
        
    @property
    def salt(self):
        if self._salt is None:
            self._salt = self.spi.getSalt()
        return self._salt
    
    @salt.setter
    def salt(self, salt):
        self._salt = salt
        
    @property
    def iterationCount(self):
        if self._iterationCount is None:
            self._iterationCount = self.spi.getIterationCount()
        return self._iterationCount
    
    @iterationCount.setter
    def iterationCount(self, iterationCount):
        self._iterationCount = iterationCount
        
    @property
    def algorithm(self):
        if self._algorithm is None:
            self._algorithm = self.spi.getAlgorithm()
        return self._algorithm
    
    @algorithm.setter
    def algorithm(self, algorithm):
        self._algorithm = algorithm
        
    @property
    def password(self):
        if self._password is None:
            self._password = self.spi.getPassword()
        return self._password

    @password.setter
    def password(self, password):
        self._password = password
    
    @classmethod
    def getInstance(cls, name='default', config=None):
        spi = PBEConfigSPIFactory.getInstance(name=name, config=config)
        return PBEConfig(spi)
