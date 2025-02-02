__version__ = "$Revision: 1.1 $"

import os, sys, re, zipfile
import minestar, mstarpaths, ufs, mstaroverrides, ConfigurationFileIO

logger = minestar.initApp()

# Output record formats
OUTPUT_FMT_WIDE = "%-20s\t%-20s\t%s\t%s\t%s\n"
OUTPUT_FMT_NARROW =      "%-20s\t%s\t%s\t%s\n"

# Dictionary Keys
FLD_OPTION_SET = 'OptionSet'
FLD_SETTING = 'Setting'
FLD_DEFAULT = 'Default'
FLD_1ST_VALUE = 'FirstValue'
FLD_2ND_VALUE = 'SecondValue'

# Indicator strings
IND_OBSOLETE = 'Obsolete'
IND_DEFAULT = '-'

def compareOverrides(firstFile, secondFile, ufsRoot, filterPattern=None):
    firstOverrides = _loadOverrides(firstFile)
    secondOverrides = _loadOverrides(secondFile)
    _displayDifferences(sys.stdout, firstOverrides, secondOverrides, ufsRoot, filterPattern)

def _loadOverrides(overridesFile):
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

def _displayDifferences(output, firstOverrides, secondOverrides, ufsRoot, filterPattern=None, narrowFormat=0):
    #output.write("1st overrides has %d keys\n" % len(firstOverrides.keys()))
    #output.write("2nd overrides has %d keys\n" % len(secondOverrides.keys()))
    diffs = _generateDifferences(firstOverrides, secondOverrides, ufsRoot)

    # Dump the information
    title1 = _title(firstOverrides,'1st')
    title2 = _title(secondOverrides,'2nd')
    if narrowFormat:
        output.write(OUTPUT_FMT_NARROW % ('Setting', 'Default', title1, title2))
    else:
        output.write(OUTPUT_FMT_WIDE % ('OptionSet','Setting', 'Default', title1, title2))

    filterRE = None
    if filterPattern:
        # Patterns starting with ! mean to exclude those records
        if filterPattern[0] == '!':
            filterRE = re.compile(filterPattern[1:])
            excludeRE = 1
        else:
            filterRE = re.compile(filterPattern)
            excludeRE = 0
    lastOptionSet = None
    for diff in diffs:
        optionSet = diff[FLD_OPTION_SET]
        if filterRE:
            if not excludeRE and re.search(filterRE, optionSet) is None:
                continue
            if excludeRE and not re.search(filterRE, optionSet) is None:
                continue
        if optionSet != lastOptionSet and narrowFormat:
            output.write(optionSet + ":\n")
        fldSetting = diff[FLD_SETTING]
        fldValue1 = _formatValue(diff[FLD_1ST_VALUE])
        fldValue2 = _formatValue(diff[FLD_2ND_VALUE])
        fldDefault = _formatValue(diff[FLD_DEFAULT])
        if narrowFormat:
            output.write(OUTPUT_FMT_NARROW %         (fldSetting,fldDefault,fldValue1,fldValue2))
        else:
            output.write(OUTPUT_FMT_WIDE % (optionSet,fldSetting,fldDefault,fldValue1,fldValue2))
        lastOptionSet = optionSet

def _title(overrides, default):
    systemOptions = overrides['/MineStar.properties']
    return systemOptions.get('_CUSTCODE', default)

def _formatValue(value):
    if value is None:
        return IND_DEFAULT
    else:
        return value

def _generateDifferences(firstOverrides, secondOverrides, ufsRoot):
    result = []
    for optionSet in firstOverrides.keys():
        optionSet1 = firstOverrides[optionSet]
        optionSet2 = secondOverrides.get(optionSet, {})
        if optionSet1 != optionSet2:
            _addDifferencesBetweenOptionSets(result, optionSet, optionSet1, optionSet2, ufsRoot)
    return result

def _addDifferencesBetweenOptionSets(result, optionSet, dict1, dict2, ufsRoot):
    defaults = __getDefaults(optionSet, ufsRoot)
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

def __getDefaults(optionSet, ufsRoot):

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

# Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = "firstFile secondFile [filterPattern]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Load the two overrides files and diff them
    firstFile = args[0]
    secondFile = args[1]
    filterPattern=None
    if len(args) > 2:
        filterPattern = args[2]
    mstarpaths.loadMineStarConfig()
    ufsPath = mstarpaths.interpretVar("UFS_PATH")
    ufsRoot = ufs.getRoot(ufsPath)
    compareOverrides(firstFile, secondFile, ufsRoot, filterPattern)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
