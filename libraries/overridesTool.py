import mstaroverrides
import minestar

from annotatedProperties import AnnotatedProperty


class OverridesTool:

    def __init__(self, config):
        if config is None:
            from overridesFactory import OverridesConfig
            config = OverridesConfig()
        self.config = config
        self._minestarOverrides = None        # loaded from MineStar.overrides file
        self._secureOverrides = None          # loaded from Secure.overrides file
        self._overridesFactory = None         # the combined overrides factory
        self._unsecuredOverridesFactory = None
        self._secureOverridesFactory = None

    @property    
    def overridesFactory(self):
        if self._overridesFactory is None:
            from overridesFactory import CombinedOverridesFactory,CachingOverridesFactory
            factory = CombinedOverridesFactory([self.unsecuredOverridesFactory, self.securedOverridesFactory])
            self._overridesFactory = CachingOverridesFactory(factory)
        return self._overridesFactory

    @property
    def unsecuredOverridesFactory(self):
        if self._unsecuredOverridesFactory is None:
            from overridesFactory import MineStarOverridesFactory, CachingOverridesFactory
            factory = MineStarOverridesFactory.createInstance(self.config)
            self._unsecuredOverridesFactory = CachingOverridesFactory(factory)
        return self._unsecuredOverridesFactory

    @property    
    def securedOverridesFactory(self):
        if self._secureOverridesFactory is None:
            from overridesFactory import SecureOverridesFactory, CachingOverridesFactory
            factory = SecureOverridesFactory.createInstance(self.config)
            self._secureOverridesFactory = CachingOverridesFactory(factory)
        return self._secureOverridesFactory

    @property
    def overrides(self):
        """ Get the overrides. Combines both the secured and the unsecured overrides. """
        return self.overridesFactory.load()

    @property
    def unsecuredOverrides(self):
        """ Returns the overrides that are currently unsecured (i.e., are not contained in the Secure.overrides file). """
        return self.unsecuredOverridesFactory.load()

    @property
    def securedOverrides(self):
        """ Returns the overrides that are currently secured (i.e. are encrypted in the Secure.overrides file). """
        return self.securedOverridesFactory.load()

    @property
    def unsecurableOverrides(self):
        """ Returns the overrides that are not securable. This is a (possibly empty) subset
            of the combined overrides, and includes just those overrides whose property 
            definition is not annotated with '@secure'. """
        return mstaroverrides.filterOverrides(self.overrides, AnnotatedProperty.Filters.isNotSecure)

    @property
    def securableOverrides(self):
        """ Returns the overrides that are securable. This is a (possibly empty) subset of 
            the combined overrides, and includes the overrides whose property definition is
            annotated with '@secure'. It may be that some of the overrides are currently
            contained in the MineStar.overrides file, and some are currently contained in 
            the Secure.overrides file. """
        return mstaroverrides.filterOverrides(self.overrides, AnnotatedProperty.Filters.isSecure)

    @property
    def migratingOverrides(self):
        """ Find the overrides that can migrate from unsecured storage to secured storage. """
        return mstaroverrides.filterOverrides(self.unsecuredOverrides, AnnotatedProperty.Filters.isSecure)

    def migrateSecureOverrides(self):
        """ Move secure overrides from MineStar.overrides file into Secure.overrides file. """
        # Get the securable and unsecurable overrides before updating files (in
        # case the overrides are reloaded after file modification).
        unsecurable = self.unsecurableOverrides
        secureable = self.securableOverrides

        if len(secureable) > 0:
            self.unsecuredOverridesFactory.store(unsecurable)
            self.securedOverridesFactory.store(secureable)

    @property
    def unmigratingOverrides(self):
        """ Find the overrides that can migrate from secured storage to unsecured storage. """
        return mstaroverrides.filterOverrides(self.securedOverrides, AnnotatedProperty.Filters.isSecure)

    def unmigrateSecureOverrides(self):
        """ Move secure overrides from Secure.overrides file into MineStar.overrides file. """
        self.unsecuredOverridesFactory.store(self.overrides)

        # Remove the Secure.overrides file.
        # TODO it may be simpler to delete the secure overrides file, but then also need to create a backup.
        self.securedOverridesFactory.store({})

    def canMigrate(self):
        """ Determines if there are overrides that can be migrated. """
        return len(self.migratingOverrides) > 0

    def setProperties(self, properties={}):
        for (name, value) in properties.items():
            self.setProperty(name, value)

    def setProperty(self, name, value):
        minestar.debug("Setting value of property %s to %s ..." % (name, value))
        (bundle, property) = self._getBundleAndProperty(name)
        if property is None:
            print "ERROR: unknown property '%s'" % name
            return
        key = _toOverridesKey(bundle, property.name)
        minestar.debug("Property %s maps to key %s" % (name, key))
        # Load the overrides from the appropriate factory.
        factory = self.securedOverridesFactory if property.secure else self.unsecuredOverridesFactory
        overrides = factory.load()
        # Check if updating or removing the property.
        changed = False
        # Delete override if no value specified, or if the value is the same as the default.
        if value == '' or value == property.value:
            if key in overrides:
                del overrides[key]
                changed = True
        # Update override if key not present, or if the value is not the same as the override.
        elif (key not in overrides) or (value != overrides[key]):
            overrides[key] = property.valueToString(value)
            changed = True
        minestar.debug("Properties changed: %s" % changed)
        # Update the overrides file only if there has been a change.
        if changed:
            # Add or remove the bundle from CONTENTS, as required.
            present = len([x for x in overrides if x.startswith(bundle)]) > 0
            contents = overrides['CONTENTS'].split(',')
            if present and bundle not in contents:
                contents.append(bundle)
            if not present and bundle in contents:
                contents.remove(bundle)
            overrides['CONTENTS'] = ','.join(contents)
            # Store the overrides in the appropriate factory.
            factory.store(overrides)

    def getProperty(self, name):
        minestar.debug("Getting value of property %s ..." % name)
        (bundle, property) = self._getBundleAndProperty(name)
        if property is None:
            print "ERROR: unknown property '%s'" % name
            return
        key = _toOverridesKey(bundle, property.name)
        minestar.debug("Property %s maps to key %s" % (name, key))
        value = "<default>" if key not in self.overrides else self.overrides[key]
        print "%s=%s" % (property.name, value)

    def showPropertyInfo(self, name):
        minestar.debug("Getting info for property %s ..." % name)
        (bundle, property) = self._getBundleAndProperty(name)
        if property is None:
            print "ERROR: unknown property '%s'" % name
            return
        key = _toOverridesKey(bundle, property.name)
        minestar.debug("Property %s maps to key %s" % (name, key))
        currentValue = property.value if key not in self.overrides else self.overrides[key]
        print "Name         : %s" % property.name
        print "Current value: %s" % currentValue
        print "Default value: %s" % (property.value or "")
        print "Annotations  : %d" % len(property.annotations)
        for annotation in property.annotations:
            if annotation.arguments is None:
                print "   @%s" % annotation.name
            else:
                print "   @%s: %s" % (annotation.name, annotation.arguments)

    def _getBundleAndProperty(self, name):
        annotatedPropertiesMap = self._getAnnotatedPropertiesMap()
        for bundle in annotatedPropertiesMap:
            properties = annotatedPropertiesMap[bundle]
            # Check for _DB_SERVER_ROLES
            if name in properties:
                return (bundle, properties[name])
            # Check for /MineStar.properties._DB_SERVER_ROLES
            for property in properties.values():
                key = _toOverridesKey(bundle, property.name)
                if name == key:
                    return (bundle, property)
        return (None, None)

    def _getAnnotatedPropertiesMap(self):
        import mstarpaths
        from annotatedProperties import AnnotatedProperties
        annotatedPropertiesMap = {}
        for propertiesFile in self._getPropertyFilesToLoad():
            actualFileName = mstarpaths.interpretPath(propertiesFile)
            definitions = AnnotatedProperties.loadFromFile(actualFileName)
            bundle = _fileNameToBundleName(actualFileName)
            annotatedPropertiesMap[bundle] = definitions
        return annotatedPropertiesMap

    def _getPropertyFilesToLoad(self):
        import mstarpaths
        propertiesFilesToLoad = ["{MSTAR_HOME}%s" % f for f in mstarpaths.PROPERTIES_FILES]
        propertiesFilesToLoad.append("{MSTAR_HOME}/bus/mstarrun/MineStar.{MSTAR_PLATFORM}.properties")
        propertiesFilesToLoad.append("{MSTAR_HOME}/bus/mstarrun/mstarrun.properties")
        return propertiesFilesToLoad


def _toOverridesKey(bundle, propertyName):
    return "%s.%s" % (bundle, propertyName)


def _fileNameToBundleName(actualFileName):
    import mstarpaths, os
    mstarHome = mstarpaths.interpretPath("{MSTAR_HOME}")
    bundle = actualFileName
    if bundle.startswith(mstarHome):
        bundle = bundle[len(mstarHome):]
    return "/".join(bundle.split(os.sep))
