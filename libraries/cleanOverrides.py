__version__ = "$Revision: 1.1 $"

import os, sys
import minestar, mstarpaths, ufs, mstaroverrides, compareOverrides

logger = minestar.initApp()


def cleanOverrides(overrideFiles, ufsRoot, commit=0, all=0):
    for i in range(len(overrideFiles)):
        ovFile = overrideFiles[i]
        if i > 0:
            logger.info("")
        logger.info("Checking %s ..." % ovFile)
        overrides = compareOverrides.loadOverrides(ovFile)
        (obsoleteSets,obsoleteOptions,defaultValues) = _findObsolete(overrides, ufsRoot, all)

        # Report the results
        for i in obsoleteSets:
            logger.info("obsolete option-set - %s" % i)
        for i in obsoleteOptions:
            logger.info("obsolete setting - %s::%s" % i)
        for i in defaultValues:
            logger.info("default value - %s::%s" % i)

        # Check if there is anything to do
        changesToBeMade = len(obsoleteSets) + len(obsoleteOptions) + len(defaultValues)
        if changesToBeMade == 0:
            logger.info("No changes required to %s" % ovFile)
            continue
        if not commit:
            logger.info("No changes made to %s - use commit mode to make the %d changes recommended" % (ovFile,changesToBeMade))
            continue
        
        # Back-up then clean-up
        bakFile = ovFile + ".bak"
        logger.info("Saving existing overrides to %s ..." % bakFile)
        mstaroverrides.saveOverridesToFile(bakFile, overrides.items())
        for i in obsoleteSets:
            del overrides[i]
        for i in obsoleteOptions + defaultValues:
            (optionSet,setting) = i
            settings = overrides[optionSet]
            del settings[setting]
        logger.info("Saving new overrides to %s with %d changes made..." % (ovFile,changesToBeMade))
        mstaroverrides.saveOverridesToFile(ovFile, overrides.items())
        
def _findObsolete(overrides, ufsRoot, all=0):
    searchPath = mstarpaths.interpretVar("UFS_PATH")
    diffs = compareOverrides.generateRecords([overrides], ufsRoot, searchPath)

    # Find the obsolete stuff
    obsoleteSets = []
    obsoleteOptions = []
    defaultValues = []
    for diff in diffs:
        # Skip permissions and calendar settings unless explicitly asked otherwise
        optionSetType = diff[compareOverrides.FLD_TYPE]
        if optionSetType == compareOverrides.TYPE_VERSIONS:
            continue
        if not (all or optionSetType in [compareOverrides.TYPE_OPTIONS, compareOverrides.TYPE_UNKNOWN]):
            continue

        # Check if the option-set is obsolete and if so, remember it (but just once)
        optionSet = diff[compareOverrides.FLD_OPTION_SET]
        if optionSet in obsoleteSets:
            continue
        if diff[compareOverrides.FLD_OPTION_SET_LABEL] is None:
            obsoleteSets.append(optionSet)
            continue

        # Check the option still exists and that the value is not the default
        fldSetting = diff[compareOverrides.FLD_SETTING]
        fldDefault = diff[compareOverrides.FLD_DEFAULT]
        fldValue = diff[compareOverrides.FLD_VALUE % 0]
        if fldDefault is compareOverrides.IND_OBSOLETE:
            obsoleteOptions.append((optionSet,fldSetting))
        elif fldDefault == fldValue:
            defaultValues.append((optionSet,fldSetting))

    return (obsoleteSets,obsoleteOptions,defaultValues)

    
# Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [\
        make_option("-c", "--commit", action="store_true", help="commit mode - do not just notify the user"),\
        make_option("-a", "--all", action="store_true", help="all settings - not just options"),\
        ]
    argumentsStr = "overridesFile ..."
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Get the UFS root as it is required for looking up defaults
    mstarpaths.loadMineStarConfig()
    ufsPath = mstarpaths.interpretVar("UFS_PATH")
    ufsRoot = ufs.getRoot(ufsPath)

    # Load the overrides files and compare them
    overrideFiles = args
    cleanOverrides(overrideFiles, ufsRoot, options.commit, options.all)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
