__version__ = "$Revision: 1.3 $"

import os, sys, re, zipfile, csv, types
import minestar, mstarpaths, ufs, mstaroverrides, ConfigurationFileIO, makeCatalogs

logger = minestar.initApp()

# Output record formats
OUTPUT_FMT_WIDE = "%-20s\t%-20s\t%s"
OUTPUT_FMT_NARROW =      "%-20s\t%s"

# Dictionary Keys
FLD_OPTION_SET = 'OptionSet'
FLD_TYPE = 'Type'
FLD_GROUP = 'Group'
FLD_OPTION_SET_LABEL = 'OptionSetLabel'
FLD_SETTING = 'Setting'
FLD_DEFAULT = 'Default'
FLD_VALUE = 'Value%d'

# Type codes
TYPE_OPTIONS = "Options"
TYPE_SECURITY = "Security"
TYPE_VERSIONS = "Versions"
TYPE_CALENDAR = "Calendar"
TYPE_LOGGING = "Logging"
TYPE_UNKNOWN = "Unknown"

# Indicator strings
IND_OBSOLETE = 'Obsolete'
IND_DEFAULT = '-'

# Files containing special settings
SPECIAL_SETTINGS = {
    "/Versions.properties": TYPE_VERSIONS,
    "com.mincom.util.calendar.Config": TYPE_CALENDAR,
    "com.mincom.base.log.topology.TopologyConfig": TYPE_LOGGING,
    "MineStarLoggingConfig": TYPE_LOGGING,
    }

def compareOverrides(overrideFiles, ufsRoot, output=sys.stdout, filterPattern=None, csvFormat=0, differencesOnly=0):
    overrides = []
    for i in range(len(overrideFiles)):
        overrides.append(loadOverrides(overrideFiles[i]))
    _displayDifferences(output, overrides, ufsRoot, filterPattern, csvFormat, differencesOnly)

def loadOverrides(overridesFile):
    (sources, allOverrides) = minestar.loadJavaStyleProperties(overridesFile, [])
    try:
        contents = allOverrides['CONTENTS'].split(",")
    except:
        logger.error("Missing CONTENTS entry in %s" % overridesFile)
        return {}
    result = {}
    for optionSet in contents:
        overrides = minestar.getSubDictionary(allOverrides, optionSet + ".")
        result[optionSet] = overrides
    return result

def _displayDifferences(output, overrides, ufsRoot, filterPattern=None, csvFormat=0, differencesOnly=0):
    searchPath = mstarpaths.interpretVar("UFS_PATH")
    diffs = generateRecords(overrides, ufsRoot, searchPath)

    # Dump the header
    if csvFormat:
        header = ['Type','Group','OptionSetLabel','OptionSet','Setting', 'Default']
        for i in range(len(overrides)):
            header.append(_title(overrides[i],'System %d' % i))
        writer = csv.writer(output)
        writer.writerow(header)
    else:
        output.write(OUTPUT_FMT_WIDE % ('OptionSet','Setting', 'Default'))
        for i in range(len(overrides)):
            output.write("\t%s" % _title(overrides[i],'System %d' % i))
        output.write("\n")

    # Dump the records
    filterRE = None
    if filterPattern:
        # Patterns starting with ! mean to exclude those records
        if filterPattern[0] == '!':
            filterRE = re.compile(filterPattern[1:])
            excludeRE = 1
        else:
            filterRE = re.compile(filterPattern)
            excludeRE = 0
    for diff in diffs:
        optionSet = diff[FLD_OPTION_SET]
        if filterRE:
            if not excludeRE and re.search(filterRE, optionSet) is None:
                continue
            if excludeRE and not re.search(filterRE, optionSet) is None:
                continue
        fldSetting = diff[FLD_SETTING]
        fldDefault = _formatValue(diff[FLD_DEFAULT])
        if differencesOnly and _overridesAreSame(diff, len(overrides)):
            continue
        if csvFormat:
            row = [diff[FLD_TYPE],diff[FLD_GROUP],diff[FLD_OPTION_SET_LABEL],optionSet,fldSetting,fldDefault]
            for i in range(len(overrides)):
                row.append(_formatValue(diff[FLD_VALUE % i]))
            writer.writerow(row)
        else:
            output.write(OUTPUT_FMT_WIDE % (optionSet,fldSetting,fldDefault))
            for i in range(len(overrides)):
                output.write("\t%s" % _formatValue(diff[FLD_VALUE % i]))
            output.write("\n")

def _title(overrides, default):
    systemOptions = overrides['/MineStar.properties']
    return systemOptions.get('_CUSTCODE', default)

def _formatValue(value):
    if value is None:
        return IND_DEFAULT
    else:
        return value

def _overridesAreSame(diff, count):
    firstValue = diff[FLD_VALUE % 0]
    for i in range(1,count):
        value = diff[FLD_VALUE % i]
        if value != firstValue:
            return 0
    return 1

def generateRecords(overrides, ufsRoot, searchPath):
    optionSetDisplayInfo = loadDisplayInformation('OptionSets', searchPath)
    securityDisplayInfo = loadDisplayInformation('Permissions', searchPath)
    allOptionSetIds = _getAllKeys(overrides)
    result = []
    for optionSet in allOptionSetIds:
       _addOverridesForOptionSet(result, optionSet, overrides, ufsRoot, optionSetDisplayInfo, securityDisplayInfo)
    return result

def _getAllKeys(dicts):
    unionDict = {}
    for dict in dicts:
        unionDict.update(dict)
    return unionDict.keys()

def _addOverridesForOptionSet(result, optionSet, overrides, ufsRoot, optionSetDisplayInfo, securityDisplayInfo):

    # Find the common stuff for this option-set
    defaults = getDefaults(optionSet, ufsRoot)
    groupAndLabel = (None,None)
    specialType = SPECIAL_SETTINGS.get(optionSet)
    if specialType:
        fldType = specialType
        groupAndLabel = ("Special",fldType)
    elif securityDisplayInfo.has_key(optionSet):
        fldType = TYPE_SECURITY
        groupAndLabel = securityDisplayInfo[optionSet]
    elif optionSetDisplayInfo.has_key(optionSet):
        fldType = TYPE_OPTIONS
        groupAndLabel = optionSetDisplayInfo[optionSet]
    else:
        fldType = TYPE_UNKNOWN
    optionSetFields = {FLD_OPTION_SET:optionSet, FLD_TYPE: fldType, FLD_GROUP:groupAndLabel[0], FLD_OPTION_SET_LABEL:groupAndLabel[1]}

    # Find the set of settings across all the overrides that are custom for this option-set
    settingsUnionDict = {}
    for overridesSet in overrides:
        settingsForOptionSet = overridesSet.get(optionSet)
        if settingsForOptionSet:
            settingsUnionDict.update(settingsForOptionSet)
    settings = settingsUnionDict.keys()

    # Build the data records
    for k in settings:
        dict = optionSetFields.copy()
        dict[FLD_SETTING] = k
        dict[FLD_DEFAULT] = defaults.get(k, IND_OBSOLETE)
        for i in range(len(overrides)):
            fldName = FLD_VALUE % i
            values = overrides[i].get(optionSet)
            if values:
                fldValue = values.get(k)
            else:
                fldValue = None
            dict[fldName] = fldValue
        result.append(dict)

def getDefaults(optionSet, ufsRoot):

    # filenames of the form x.y.z are shorthands for /res/x/y/z.properties
    optionSet = optionSet.strip()
    if optionSet[0] == '/':
        sourceFilename = optionSet
    else:
        sourceFilename = '/res/' + optionSet.replace('.', '/') + '.properties'

    # Read the form definition from the options file
    ufsFile = ufsRoot.get(sourceFilename)
    try:
        if ufsFile is None:
            lines = __loadLinesFromJars(optionSet, ufsRoot)
        else:
            lines = ufsFile.getTextLines()
    except:
        logger.error("unable to read options file: %s" % sourceFilename)
        return {}

    # Parse the name-value pairs
    (dict,comments) = ConfigurationFileIO.loadDictionaryFromLinesWithComments(lines)
    return dict

def __loadLinesFromJars(optionSet, ufsRoot):
    className = optionSet.replace('.', '/') + ".properties"
    (bcpJars, jars, classPathDirs, classPathJars) = mstarpaths.buildClassPaths(ufsRoot, 0, None, None)
    for jar in jars:
        if not jar.lower().endswith(".jar"):
            continue
        zf = zipfile.ZipFile(jar, "r")
        if className in zf.namelist():
            bytes = zf.read(className)
            lines = bytes.split("\n")
            lines = [ minestar.stripEol(line) for line in lines ]
            return lines
    raise "Not found"

def loadDisplayInformation(catalog, searchPath):
    # returns a dictionary mapping option-set id's to tuples of (group,option-set name)

    ipParams = {'searchPath':searchPath}
    (groups,order,groupInfo) = makeCatalogs.buildGroupsFromCommentsForCatalog(searchPath, catalog,
                                             itemProcessor=makeCatalogs.buildOptionsFormItemProcessor,
                                             itemProcessorParams=ipParams)
    groupNames = groups.keys()
    result = {}
    for name in groupNames:
        for item in groups[name]:
            if type(item) == types.TupleType:
                itemName = item[0]
                itemDetails = item[2]
                detailsImpl = itemDetails.get(makeCatalogs.DETAILS_IMPL)
                result[detailsImpl] = (name,itemName)
    return result


## Old code ##

def _generateDifferences(firstOverrides, secondOverrides, ufsRoot):
    result = []
    for optionSet in firstOverrides.keys():
        optionSet1 = firstOverrides[optionSet]
        optionSet2 = secondOverrides.get(optionSet, {})
        if optionSet1 != optionSet2:
            _addDifferencesBetweenOptionSets(result, optionSet, optionSet1, optionSet2, ufsRoot)
    return result

def _addDifferencesBetweenOptionSets(result, optionSet, dict1, dict2, ufsRoot):
    # This routine appends tuples to a list iff the values in the 2 dictionaries for keys do not match
    FLD_1ST_VALUE = FLD_VALUE % 0
    FLD_2ND_VALUE = FLD_VALUE % 1
    defaults = getDefaults(optionSet, ufsRoot)
    dict2Keys = dict2.keys()
    for k in dict1.keys():
        if k in dict2Keys:
            dict2Keys.remove(k)
            if dict1[k] == dict2[k]:
                continue
            else:
                # Key in both dictionaries - values differ
                dict = {FLD_OPTION_SET:optionSet, FLD_SETTING:k, FLD_1ST_VALUE:dict1[k], FLD_2ND_VALUE:dict2[k], FLD_DEFAULT:defaults.get(k, IND_OBSOLETE)}
                result.append(dict)
        else:
            # Key not found in second dictionary
            dict = {FLD_OPTION_SET:optionSet, FLD_SETTING:k, FLD_1ST_VALUE:dict1[k], FLD_2ND_VALUE:None, FLD_DEFAULT:defaults.get(k, IND_OBSOLETE)}
            result.append(dict)
    for k in dict2Keys:
        # Key not found in first dictionary
        dict = {FLD_OPTION_SET:optionSet, FLD_SETTING:k, FLD_1ST_VALUE:None, FLD_2ND_VALUE:dict2[k], FLD_DEFAULT:defaults.get(k, IND_OBSOLETE)}
        result.append(dict)


## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [\
        make_option("-c", "--csvFile", help="generate CSV format to the named file"),\
        make_option("-d", "--differencesOnly", action="store_true", help="if multiple overrides files, only show entries that differ"),\
        make_option("-p", "--pattern", dest="filterPattern", help="OptionSet name filter pattern (use ! as first character to exclude)"),\
        ]
    argumentsStr = "overridesFile ..."
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Get the UFS root as it is required for looking up defaults
    mstarpaths.loadMineStarConfig()
    ufsPath = mstarpaths.interpretVar("UFS_PATH")
    ufsRoot = ufs.getRoot(ufsPath)

    # Load the overrides files and compare them
    overrideFiles = args
    csvFormat = options.csvFile != None
    if csvFormat:
        try:
            output = open(options.csvFile, "wb")
        except IOERROR, err:
            logger.error("failed to open file %s: %s" % (options.csvFile,err))
    else:
        output = sys.stdout
    compareOverrides(overrideFiles, ufsRoot, output, options.filterPattern, csvFormat, options.differencesOnly)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
