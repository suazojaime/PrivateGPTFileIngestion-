from abc import abstractmethod
import os

import ConfigurationFileIO
import mstarpaths
import mstaroverrides

def debug(message):
    import mstardebug
    if mstardebug.debug:
        print message

class OverridesConfig(object):

    DEFAULT_SECRET_KEY_CIPHER = 'AES/GCM/NoPadding'
    
    def __init__(self, system='main', config=None, minestarOverridesFile=None, secureOverridesFile=None):
        self._system = system
        self._config = config
        self._keyStoreFile = None
        self._keyStoreConfig = None
        self._minestarOverridesFile = minestarOverridesFile
        self._secureOverridesFile = secureOverridesFile
        self._keyStore = None
        self._secretKey = None
        self._propertyEncryptor = None

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    @property
    def system(self):
        return self._system

    @system.setter
    def system(self, system):
        self._system = system

    @property
    def keyStoreFile(self):
        """ Get the location of the key store file. """
        if self._keyStoreFile is None:
            self._keyStoreFile = self.keyStoreConfig.keyStoreFile
        return self._keyStoreFile

    @keyStoreFile.setter
    def keyStoreFile(self, keyStoreFile):
        self._keyStoreFile = keyStoreFile
        # Update the key store file in the key store config (if available).
        if self._keyStoreConfig is not None:
            self._keyStoreConfig.keyStoreFile = keyStoreFile
            
    @property
    def keyStoreConfig(self):
        if self._keyStoreConfig is None:
            from keystoreConfig import KeyStoreConfig
            self._keyStoreConfig = KeyStoreConfig.getInstance(config=self.config)
            # Update the key store file in the key store config with the local key store file.
            if self._keyStoreFile is not None:
                self._keyStoreConfig.keyStoreFile = self._keyStoreFile
        return self._keyStoreConfig

    @property
    def minestarOverridesFile(self):
        if self._minestarOverridesFile is None:
            self._minestarOverridesFile = mstarpaths.interpretPathOverride(mstaroverrides.OVERRIDES_FILE, self.config)
        return self._minestarOverridesFile

    @minestarOverridesFile.setter
    def minestarOverridesFile(self, minestarOverridesFile):
        self._minestarOverridesFile = minestarOverridesFile

    @property
    def secureOverridesFile(self):
        if self._secureOverridesFile is None:
            self._secureOverridesFile = mstarpaths.interpretPathOverride(mstaroverrides.SECURE_OVERRIDES_FILE, self.config)
        return self._secureOverridesFile

    @secureOverridesFile.setter
    def secureOverridesFile(self, secureOverridesFile):
        self._secureOverridesFile = secureOverridesFile

    @property
    def keyStore(self):
        """ Get the keystore. """
        if self._keyStore is None:
            self._keyStore = self._createOrLoadKeyStore()
        return self._keyStore

    def _createOrLoadKeyStore(self):
        from keystores import JavaKeyStore
        return JavaKeyStore.createOrLoad(self.keyStoreConfig)

    @property
    def propertyEncryptor(self):
        if self._propertyEncryptor is None:
            self._propertyEncryptor = self._createPropertyEncryptor()
        return self._propertyEncryptor

    def _createPropertyEncryptor(self):
        from propertyEncryptors import KeyStorePropertyEncryptor
        return KeyStorePropertyEncryptor.createInstance(self.keyStoreConfig)


class OverridesFactory(object):

    """ Class representing an overrides factory, for managing overrides. """
    
    def __init__(self):
        pass
    
    @abstractmethod
    def load(self):
        """ 
        Load the overrides. Returns overrides represented as a properties map, in the
        form Map<FullyQualifiedPropertyNameOrCONTENTS,PropertyValue>.
        
        For example: the overrides loaded from a file may be returned as:
        
        {
          '/MineStar.properties.foo':1,
          '/MineStar.properties.bar':2,
          '/Versions.properties.baz':3,
          'CONTENTS':'/MineStar.properties,/Versions.properties'
        }
          
        This map may be converted to an option set map of the form
        Map<OptionSet,Map<PropertyName,PropertyValue>> using the function
        mstaroverrides.propertiesMapToOptionSetMap().
          
        """
        raise NotImplementedError

    @abstractmethod
    def store(self, overrides={}):
        """ Store the overrides. The overrides are represented as a properties map,
            in the form (Map<FullyQualifiedPropertyNameOrCONTENTS,PropertyValue>. """
        raise NotImplementedError

    def requiresReload(self):
        """ Determines if the overrides require reloading (e.g. a file has changed since
            the previous load/store operation. """
        return False

class DummyOverridesFactory(OverridesFactory):

    """ A dummy overrides factory that returns loads nothing. """
    
    def __init__(self):
        super(DummyOverridesFactory, self).__init__()
        
    # @Override
    def load(self):
        # Return an empty map.
        return {}

    # @Override
    def store(self, overrides={}):
        # Do nothing.
        pass

class FileOverridesFactory(OverridesFactory):
    
    """ Class representing a file-based overrides factory. """

    def __init__(self, overridesFile=None, config=None):
        super(FileOverridesFactory, self).__init__()
        self._overridesFile = overridesFile
        self._config = config
        self._lastModifiedTime = None
        
    @property
    def config(self):
        return self._config
    
    @property
    def overridesFile(self):
        """ Get the overrides file for the factory. """
        if self._overridesFile is None:
            self._overridesFile = self.defaultOverridesFile()
        return self._overridesFile
    
    def defaultOverridesFile(self):
        """ Get the default overrides file for the factory. """
        raise NotImplementedError

    # @Override
    def load(self):
        return self.loadProperties(self.overridesFile)

    def loadProperties(self, file):
        if file is None:
            raise ValueError("Cannot load overrides: no overrides file specified")
        debug("Loading properties from overrides file '%s' ..." % file)
        # Check that the overrides file is specified.
        # Only load properties if file exists (may be creating a new overrides file).
        if os.path.exists(file):
            properties = ConfigurationFileIO.loadDictionaryFromFile(file)
            self._lastModifiedTime = os.path.getmtime(file)
        else:
            properties = {}
        return properties
    
    # @Override
    def store(self, overrides={}):
        """ Stores the overrides to the overrides file. The overrides are represented as a
            properties map in the form Map<FullyQualifiedPropertyNameOrCONTENTS,PropertyValue>. """
        self.storeProperties(overrides, self.overridesFile)

    def storeProperties(self, properties, file):
        # Check that file is specified.
        if file is None:
            raise ValueError("Cannot store overrides: no file specified.")
        debug("Storing properties to overrides file '%s' ..." % file)

        from fileOps import FileOps
        f = FileOps.getFileOps()
        f.createDir(os.path.dirname(file))
        
        temporaryFile = file + ".temp"
        
        # Store the properties to the temporary file first, then move to original file (with backup).
        try:
            self._storeOverrides(temporaryFile, properties)
            f.moveFile(temporaryFile, file, {'backup': True, 'backup.suffix': '.original', 'overwrite': True})
        finally:
            if os.path.exists(temporaryFile):
                os.remove(temporaryFile)
        
        # Update the timestamp for the overrides factory.
        self._lastModifiedTime = os.path.getmtime(file)
        
    def _storeOverrides(self, file, properties):
        # Check for 'CONTENTS' entry.
        if len(properties) > 0 and 'CONTENTS' not in properties:
            import mstaroverrides
            optionSetMap = mstaroverrides.propertiesMapToOptionSetMap(properties)
            properties['CONTENTS'] = mstaroverrides.overridesGetDictKeys(optionSetMap)
        ConfigurationFileIO.saveDictionaryToFile(properties, file)
        
    def requiresReload(self):
        # Loading required if not already loaded.
        if self._lastModifiedTime is None:
            return True
        # Compare current modification time of the file with the last known modification time.
        return os.path.getmtime(self.overridesFile) > self._lastModifiedTime
    
class MineStarOverridesFactory(FileOverridesFactory):

    """ Overrides factory for unsecured properties in an overrides file. Typically
        used for the MineStar.overrides file. """
    
    def __init__(self, overridesFile=None, config=None):
        super(MineStarOverridesFactory, self).__init__(overridesFile=overridesFile, config=config)
        
    # @Override    
    def defaultOverridesFile(self):
        return mstarpaths.interpretPathOverride(mstaroverrides.OVERRIDES_FILE, self.config)
    
    @staticmethod
    def createInstance(overridesConfig):
        """ Create a new factory using the overrides config. """
        if overridesConfig is None:
            raise Exception("An overrides config is required to create a MineStarOverridesFactory instance.")
        return MineStarOverridesFactory(overridesFile=overridesConfig.minestarOverridesFile, 
                                        config=overridesConfig.config)
    
class SecureOverridesFactory(FileOverridesFactory):
    
    """ Overrides factory for secured properties in an overrides file. Typically
        used for the Secure.overrides file. """
    
    def __init__(self, propertyEncryptor, overridesFile=None, config=None):
        super(SecureOverridesFactory, self).__init__(overridesFile, config)
        if propertyEncryptor is None:
            raise ValueError("Must specify a property encryptor for encrypted overrides.")
        self.propertyEncryptor = propertyEncryptor

    # @Override
    def defaultOverridesFile(self):
        return mstarpaths.interpretPathOverride(mstaroverrides.SECURE_OVERRIDES_FILE, self.config)
    
    # @Override
    def loadProperties(self, file):
        # Decrypt the properties after loading.
        properties = super(SecureOverridesFactory, self).loadProperties(file)
        return self.decryptProperties(properties)

    def decryptProperties(self, properties):
        return self.propertyEncryptor.decryptProperties(properties)
    
    # @Override
    def storeProperties(self, properties, file):
        # Encrypt the properties before storing.
        encryptedProperties = self.encryptProperties(properties)
        super(SecureOverridesFactory, self).storeProperties(encryptedProperties, file)
    
    def encryptProperties(self, properties):
        return self.propertyEncryptor.encryptProperties(properties)
    
    @classmethod
    def createInstance(cls, overridesConfig):
        """ Create a new instance of the SecureOverridesFactory, using defaults where necessary. """
        if overridesConfig is None:
            raise ValueError("An overrides config is required to create a SecureOverridesFactory instance.")
        return SecureOverridesFactory(overridesFile=overridesConfig.secureOverridesFile,
                                      propertyEncryptor=overridesConfig.propertyEncryptor,
                                      config=overridesConfig.config)
        
class CombinedOverridesFactory(OverridesFactory):

    """ Combines multiple override factories. """
    
    def __init__(self, factories=[]):
        super(CombinedOverridesFactory, self).__init__()
        if factories is None or len(factories) == 0:
            raise ValueError("Must specify at least one factory when creating combined overrides factory.")
        self.factories = factories
        
    # @Override    
    def load(self):
        from mstaroverrides import optionSetMapToPropertiesMap, propertiesMapToOptionSetMap, mergeOverrides
        combinedOverrides = {}
        for factory in self.factories:
            localOverrides = factory.load()
            # Merge/Copy only if overrides loaded from the factory.
            if len(localOverrides) > 0:
                # Merge if there are existing combined overrides, otherwise just copy the local overrides.
                if len(combinedOverrides) > 0:
                    merged = mergeOverrides(propertiesMapToOptionSetMap(combinedOverrides),
                                            propertiesMapToOptionSetMap(localOverrides))
                    combinedOverrides = optionSetMapToPropertiesMap(merged)
                else:
                    combinedOverrides = localOverrides.copy()
        return combinedOverrides
    
    @staticmethod
    def createInstance(overridesConfig):
        """ Create a factory using the overrides configuration. """
        if overridesConfig is None:
            raise ValueError("An overrides config is required to create a CombinedOverridesFactory instance.")
        unsecuredOverridesFactory = CachingOverridesFactory(MineStarOverridesFactory.createInstance(overridesConfig))
        securedOverridesFactory = CachingOverridesFactory(SecureOverridesFactory.createInstance(overridesConfig))
        return CombinedOverridesFactory([unsecuredOverridesFactory, securedOverridesFactory])
    
    # @Override
    def requiresReload(self):
        # Reload required if any factory requires a reload. Not very efficient.
        return True in [f.requiresReload() for f in self.factories]
    
class CachingOverridesFactory(OverridesFactory):

    """ An overrides factory that caches its result, reloading only if required. """
    
    def __init__(self, delegate):
        super(CachingOverridesFactory, self).__init__()
        self._delegate = delegate
        self._overrides = None
        
    # @Overrides    
    def load(self):
        # Load if overrides have not been loaded, or a reload is required.
        if self._overrides is None or self.requiresReload():
            self._overrides = self._delegate.load()
        return self._overrides
    
    # @Overrides
    def store(self, overrides={}):
        self._delegate.store(overrides)
    
    # @Override
    def requiresReload(self):
        return self._delegate.requiresReload()
