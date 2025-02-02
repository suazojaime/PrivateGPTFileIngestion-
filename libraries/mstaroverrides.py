# Utility routines for maintaining the MineStar.overrides file

import os, string, datetime
import mstarpaths, minestar, ConfigurationFileIO

OVERRIDES_DIR = "{MSTAR_CONFIG}"
SECURE_OVERRIDES_DIR = "{MSTAR_CREDS}"
OVERRIDES_NAME = "MineStar.overrides"
SECURE_OVERRIDES_NAME = "Secure.overrides"
BACKUP_NAME = "MineStar_overrides_%s.log"
BACKUP_PREFIX = "MineStar_overrides_"
CONFIG_LOGS = "{MSTAR_LOGS}/config"
OVERRIDES_FILE = os.sep.join([OVERRIDES_DIR, OVERRIDES_NAME])
SECURE_OVERRIDES_FILE = os.sep.join([SECURE_OVERRIDES_DIR, SECURE_OVERRIDES_NAME])
CONTENTS = 'CONTENTS'

def _getLatestOverridesBackup(config):
    dir = mstarpaths.interpretPathOverride(CONFIG_LOGS, config)
    if not os.access(dir, os.R_OK):
        return None
    files = os.listdir(dir)
    last = -1
    result = None
    import stat
    for file in files:
        if file.startswith(BACKUP_PREFIX):
            mtime = os.stat(os.sep.join([dir, file]))[stat.ST_MTIME]
            if mtime > last:
                 result = file
                 last = mtime
    if result is None:
        return None
    return os.sep.join([dir, result])

def backupOverrides(config=None):
    """
    Backup the current {MSTAR_CONFIG}/MineStar.overrides file to {MSTAR_LOGS}/config/MineStar_overrides_<timestamp>.log
    This should be performed before saving any changes to the {MSTAR_CONFIG}/MineStar.overrides file.
    """
    overridesFile = mstarpaths.interpretPathOverride(OVERRIDES_FILE, config)
    now = datetime.datetime.now()
    timestamp = "%s%03d" % (now.strftime("%Y%m%d%H%M%S"), now.microsecond/1000)
    destfile = mstarpaths.interpretPathOverride(os.sep.join([CONFIG_LOGS, BACKUP_NAME % timestamp]), config)
    minestar.copy(overridesFile, destfile)

def loadOverrides(config=None):
    """Load overrides for the current system"""
    (config, system) = initSystemAndConfig(config)
    return loadOverridesForSystem(system, config)


def migrateOverridesForSystem(system, config=None):
    """Migrate any secure overrides from MineStar.overrides to Secure.overrides"""
    # Check that the (unsecured) overrides file exists.
    overridesFile = mstarpaths.interpretPathOverride(OVERRIDES_FILE, config)
    if not os.path.exists(overridesFile):
        minestar.logit("Overrides file not found for system %s" % system, config)
        return ({}, overridesFile)

    # Get the location of the secured overrides file.
    secureOverridesFile = mstarpaths.interpretPathOverride(SECURE_OVERRIDES_FILE, config)

    # Migrate the securable properties from the unsecured overrides file to the secured overrides file.
    from overridesTool import OverridesTool
    tool = OverridesTool(config)
    tool.minestarOverridesFile = overridesFile
    tool.secureOverridesFile = secureOverridesFile
    tool.migrateSecureOverrides()


def initSystemAndConfig(config):
    system = mstarpaths.interpretVarOverride("MSTAR_SYSTEM", config)
    # Use the global config if none is provided.
    if config is None: config = mstarpaths.config
    return config, system


def loadSecureOverrides(config=None):
    (config, system) = initSystemAndConfig(config)
    return loadSecureOverridesForSystemFullyQualified(system, config)


def loadCombinedOverrides(config=None):
    (config, system) = initSystemAndConfig(config)
    return loadCombinedOverridesForSystem(system, config)

def saveOverrides(overrides,config=None):
    """Save overrides for the current system.
       The overrides parameter is a list of (OptionSet, dict) pairs or a dict of dicts.
    """
    if type(overrides) == type({}):
        overrides = overrides.items()
    backupOverrides(config)
    overridesFile = mstarpaths.interpretPathOverride(OVERRIDES_FILE,config)
    saveOverridesToFile(overridesFile, overrides)

def loadCombinedOverridesForSystem(system, config):
    overridesFile = mstarpaths.interpretPathOverride(OVERRIDES_FILE, config)
    if not os.path.exists(overridesFile):
        minestar.logit("Overrides file not found for system %s" % system, config)
        return ({}, overridesFile)
    
    # Load the unsecured overrides.
    (result, source) = loadOverridesForSystem(system, config)

    # Load the secured overrides and merge with unsecured overrides.
    (secureResult, secureSource) = loadSecureOverridesForSystem(system, config)
    if secureResult:
        result = mergeOverrides(result, secureResult)
        source = source + ", " + secureSource
    
    return (result, source)


def loadSecureOverridesForSystem(system, config):
    secureOverridesFile = mstarpaths.interpretPathOverride(SECURE_OVERRIDES_FILE, config)
    if not os.path.exists(secureOverridesFile):
        return {}, {}
    
    (_, secureOverrides) = loadSecureOverridesForSystemFullyQualified(system, config)
    result = propertiesMapToOptionSetMap(secureOverrides)
    
    return (result, secureOverridesFile)


def loadOverridesForSystem(system, config):
    """
    returns a dictionary of option-set names to overrides (name-variable pairs).
    An option-set name is:
    * relative to MSTAR_HOME if it starts with a /, e.g. /MineStar.properties, /explorer/bin/minestar.eep
    * relative to the classpath otherwise, e.g. com.mincom.x.y.Config.properties
    The config parameter is a bootstrap configuration which is just enough to allow use to locate the overrides file.
    """
    overridesFile = mstarpaths.interpretPathOverride(OVERRIDES_FILE, config)
    if not os.path.exists(overridesFile):
        minestar.logit("Overrides file not found for system %s" % system, config)
        return ({}, overridesFile)
    return loadOverridesFromFile(overridesFile, config)

def loadSecureOverridesForSystemFullyQualified(system, config):
    """
    returns a tuple containing (sources, values) where sources is a dictionary mapping the key value to a source
    (in this case the name of the Secure.overrides file) and values is a dictionary mapping the key to the override
    value.

    In either case the key is the fully qualified key (including the option set name).

    e.g. {'/MineStar.properties._DBPREFIX' : 'ms'}

    c.f. loadSecureOverridesForSystem which returns a list of option sets and then individual keys under that.

    The config parameter is a bootstrap configuration which is just enough to allow use to locate the overrides file.
    """
    #if not mstarpaths.config:
    #    minestar.logit("MineStar config is not yet initialized" % system, config)
    #    return ({}, {})
    secureOverridesFile = mstarpaths.interpretPathOverride(SECURE_OVERRIDES_FILE, config)
    if not os.path.exists(secureOverridesFile):
        minestar.logit("Secure Overrides file not found for system %s" % system, config)
        return ({}, {})

    minestar.debug("Loading secure overrides from %s" % secureOverridesFile)

    # Load the secure overrides (as a properties map).
    from overridesFactory import OverridesConfig, SecureOverridesFactory
    overridesConfig = OverridesConfig(system=system, config=config, secureOverridesFile=secureOverridesFile)
    output = SecureOverridesFactory.createInstance(overridesConfig).load()

    # Add the sources.    
    sources = propertiesMapToSourcesMap(output, secureOverridesFile)

    return (sources,output)

def loadOverridesFromFile(overridesFile, config=[]):
    """ Load the overrides tuple (result,source) from the specified file. 
    
        The first element of the tuple ('result') is a map of option set to
        properties, e.g.
          
        {
          '/MineStar.properties': {'foo':'1', 'bar':'2'}, 
          '/Versions.properties': {'baz':'3'} 
        } 
        
        Note that there is no 'CONTENTS' entry in the map.
         
        The second element of the tuple ('source') is the source for the
        result, e.g. '/mstarFiles/systems/main/config/MineStar.overrides'.
          
        """
    minestar.debug("Loading overrides from %s" % overridesFile)
    (sources, allOverrides) = minestar.loadJavaStyleProperties(overridesFile, [])
    try:
        contents = allOverrides[CONTENTS].split(",")
    except:
        if config:
            minestar.logit("Missing CONTENTS entry in %s" % overridesFile, config)
        return ({}, overridesFile)
    result = {}
    for optionSet in contents:
        overrides = minestar.getSubDictionary(allOverrides, optionSet + ".")
        result[optionSet] = overrides
    return (result, overridesFile)

def saveOverridesToFile(file, pairs):
    "save a list of (OptionSet,dictionary) pairs into a file in overrides format"
    outputDict = {}
    contents = []
    for pair in pairs:
        prefix = pair[0]
        dict = pair[1]
        if dict != None and len(dict.keys()) > 0:
            contents.append(prefix)
            for k in dict.keys():
                outputDict[prefix + "." + k] = dict[k]
    outputDict["CONTENTS"] = string.join(contents, ",")
    minestar.makeDirsFor(file)
    ConfigurationFileIO.saveDictionaryToFile(outputDict, file)

class Overrides:
    def __init__(self):
        self.overrides = loadCombinedOverrides()[0]

    def save(self):
        saveOverrides(self.overrides)

    def __repr__(self):
        return `self.overrides`

    def get(self, file, key):
        if self.overrides.has_key(file):
            fileDict = self.overrides[file]
            if fileDict.has_key(key):
                return fileDict[key]
        return None

    def put(self, file, key, value):
        if self.overrides.get(file) is None:
            self.overrides[file] = {}
        self.overrides[file][key] = value

    def remove(self, file, key):
         fileDict = self.overrides.get(file)
         if fileDict is None:
             return
         del fileDict[key]
         if len(fileDict) == 0:
             del self.overrides[file]

def overridesPairDict(tuple):
    """ Get the dict from an overrides pair. """
    return __validateOverridesTuple(tuple)[0]

def overridesPairSource(tuple):
    """ Get the source from an overrides pair. """
    return __validateOverridesTuple(tuple)[1]

def __validateOverridesTuple(tuple):
    if tuple is None:
        raise Exception("No tuple specified")
    if len(tuple) != 2:
        raise Exception("Invalid tuple length %s" % len(tuple))
    return tuple

def overridesDictToPairs(dict):
    """ Convert overrides dict to a list of overrides pairs. """
    pairs = []
    for (key,value) in dict.items():
        # Can only create a pair from a key whose value is a dict.
        if type(value) == type({}):
            pairs.append((key, value))
    return pairs

def __validateOverridesDict(dict):
    if dict is None:
        raise Exception("No overrides dict specified")
    return dict

def overridesPairsToDict(pairs):
    """ Convert a list of overrides pairs to an overrides dict. """
    dict = {}
    for pair in pairs:
        dict[pair[0]] = pair[1]
    return dict

def overridesGetDictKeys(overrides={}):
    """ Get the keys in the overrides map that have dict type (e.g.
        '/MineStar.properties', '/Version.properties, etc, but not 'CONTENTS'). """
    keys = []
    for (key,value) in overrides.items():
        if type(value) == type({}):
            if not key in keys:
                keys.append(key)
    return keys

def overridesAddContentsKey(overrides={}):
    """ Add the 'CONTENTS' key to an overrides map. """
    overrides[CONTENTS] = ','.join(overridesGetDictKeys(overrides))
    return overrides

def mergeOverrides(x, y):
    """
     Merge the overrides contained in X with the overrides contained in Y. Overrides in
     Y take preference. The CONTENTS are present in the merged overrides only if X or Y
     already contained CONTENTS (it is not added if not present in either X or Y)

     So if X is:
     
       {'/MineStar.properties':{'foo':1, 'bar':2}}
        
     and Y is
      
       {'/MineStar.properties':{'foo':99, 'baz':3}, '/Version.properties':{'qux':4}}
        
     then the merged overrides will be:
     
       {'/MineStar.properties':{'foo':99, 'bar':2, 'baz':3},
        '/Version.properties':{'qux':4} }
        
      since the 'foo' in Y is preferred over the 'foo' in X.
      
      Both the X and the Y overrides are represented as an option set map (of the 
      form Map<OptionSet,Map<PropertyName,PropertyValue>>) and the result will
      be an option set map. 
    """

    # Pre-condition checks.
    if x is None:
        raise Exception("Cannot merge overrides: no 'x' overrides specified.")
    if y is None:
        raise Exception("Cannot merge overrides: no 'y' overrides specified")

    # Start with an empty merge.
    merged  = {}

    # Add the overrides in X.
    for content in x:
        fromDict = x[content]
        if type(fromDict) == type({}):
            toDict = {}
            merged[content] = toDict
            for key in fromDict:
                toDict[key] = fromDict[key]

    # Add the overrides in Y.
    for content in y:
        fromDict = y[content]
        if type(fromDict) == type({}):
            if merged.has_key(content):
                toDict = merged[content]
            else:
                toDict = {}
                merged[content] = toDict
            for key in fromDict:
                toDict[key] = fromDict[key]

    # Merge the CONTENTS, if present in X or Y.
    if x.has_key(CONTENTS) or y.has_key(CONTENTS):
        merged[CONTENTS] = overridesGetDictKeys(merged)

    return merged


def optionSetMapToPropertiesMap(optionSetMap={}):
    """ 
    Convert overrides represented as an option set map (e.g. in the form
    Map<BundleName,Map<PropertyName,PropertyValue>>) to overrides represented as
    properties (e.g. Map<FullyQualifiedPropertyName,PropertyValue) + 'CONTENTS'
    property).
    
    For example the option set map:
        
        { 
          '/MineStar.properties': { 'foo':1, 'bar':2 },
          '/Versions.properties': { 'baz':3 } 
        }
          
    would be converted to the properties map:
          
       { 
         'CONTENTS':'/MineStar.properties,/Versions.properties',
         '/MineStar.properties.foo':1,
         '/MineStar.properties.bar':2,
         '/Versions.properties.baz':3 
       }
         
    """
    
    propertiesMap = {}
    contents = []
    for (bundleName,properties) in optionSetMap.items():
        contents.append(bundleName)
        for (propertyName, propertyValue) in properties.items():
            fullyQualifiedName = bundleName + "." + propertyName
            propertiesMap[fullyQualifiedName] = propertyValue
    propertiesMap[CONTENTS] = ','.join(contents)
    return propertiesMap

def propertiesMapToOptionSetMap(propertiesMap):
    """ 
    Convert overrides represented as a properties  map (e.g. in the form
    Map<FullyQualifiedPropertyName,PropertyValue>> + 'CONTENTS' property) to
    overrides represented as an option set map (e.g. in the form
    Map<BundleName,Map<PropertyName,PropertyValue>>). 

    For example the properties map:
          
       { 
         'CONTENTS':'/MineStar.properties,/Versions.properties',
         '/MineStar.properties.foo':1,
         '/MineStar.properties.bar':2,
         '/Versions.properties.baz':3 
       }
         
    would be converted to the option set map:
        
        { 
          '/MineStar.properties': { 'foo':1, 'bar':2 },
          '/Versions.properties': { 'baz':3 } 
        }
          
    """
    optionSetMap = {}
    optionSets = [i for i in (propertiesMap.get(CONTENTS) or '').split(",") if i]
    for optionSet in optionSets:
        for (fullyQualifiedPropertyName, propertyValue) in propertiesMap.items():
            if fullyQualifiedPropertyName.startswith(optionSet+'.'):
                propertyName = fullyQualifiedPropertyName[len(optionSet)+1:]
                if not optionSet in optionSetMap:
                    optionSetMap[optionSet] = {}
                optionSetMap[optionSet][propertyName] = propertyValue
    return optionSetMap

def propertiesMapToSourcesMap(propertiesMap,source):
    """ 
    Create a sources map by setting each value in the properties map to the specified source.
    
    For example if the map is {x:1, y:2, z:3} and the source is '/foo/bar' then
    the resulting map is {z:'/foo/bar', y:'/foo/bar', z:'/foo/bar'}.
    """
    sources = {}
    for propertyName in propertiesMap:
        sources[propertyName] = source
    return sources


def filterOverrides(overrides={}, filter=None):
    """ Filter the overrides by including only those overrides that match. 
    
    The overrides are represented as a properties map in the form
    Map<FullyQualifiedPropertyNameOrCONTENTS,PropertyValue>.
    
    The filter is applied to an AnnotatedProperty object, containing the 
    property name, property value, and the property annotations.
    
    Example filters:
    - secure override   : lambda p: p is not None and p.hasAnnotation('secure')
    - unsecure override : lambda p: p is not None and not p.hasAnnotation('secure')
    - undefined override: lambda p: p is None
    - defined override  : lambda p: p is not None
    
    :param overrides: overrides represented as a properties map in the form 
                      Map<FullyQualifiedPropertyNameOrCONTENTS,PropertyValue>.
    
    :param filter:    The filter to apply when matching overrides. This
                      filter is applied to an AnnotatedProperty object representing
                      the override.
    
    :return: the overrides represented as a new properties map in the form
             Map<FullyQualifiedPropertyNameOrCONTENTS,PropertyValue>. This map
             will be empty if no overrides match the filter.
    """
    optionSets = [i for i in (overrides.get('CONTENTS') or '').split(",") if i]
    filteredOptionSets = []
    filteredOverrides = {}
    for optionSet in optionSets:
        from bundles import Bundles
        properties = Bundles.getPropertiesForBundleName(optionSet)
        localOverrides = minestar.getSubDictionary(overrides, optionSet+".")
        for (propertyName,propertyValue) in localOverrides.items():
            property = properties.get(propertyName) or None
            if filter(property):
                # Add the fully-qualified property name to the filtered overrides.
                filteredOverrides[optionSet + '.' + propertyName] = propertyValue
                # Add the option set name to the filtered option sets.
                if not optionSet in filteredOptionSets:
                    filteredOptionSets.append(optionSet)
    # Add a CONTENTS property.
    filteredOverrides['CONTENTS'] = ','.join(filteredOptionSets)
    return filteredOverrides
