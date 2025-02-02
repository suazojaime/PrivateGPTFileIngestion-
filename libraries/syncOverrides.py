__version__ = "$Revision: 1.1 $"

import os, sys, csv
import minestar, mstarpaths, ufs, mstaroverrides, compareOverrides

logger = minestar.initApp()

# Column names in the CSV file for the keep-list
COL_OPTION_SET = "OptionSet"
COL_SETTING = "Setting"

def syncOverrides(keepListFile, masterOverridesFile, overrideFiles, commit=0, verbose=0):
    # Load the keep list
    if os.path.exists(keepListFile):
        logger.info("Loading properties to keep from %s ..." % keepListFile)
        keep = _loadKeepList(keepListFile)
        if keep is None or len(keep.keys()) == 0:
            logger.error("cannot synchronize overrides as keep-list file (%s) empty" % keepListFile)
            return
    else:
        logger.error("cannot synchronize overrides as keep-list file (%s) missing" % keepListFile)
        return

    # Load the master settings    
    logger.info("Loading master overrides from %s ..." % masterOverridesFile)
    masterOverrides = compareOverrides.loadOverrides(masterOverridesFile)
    if masterOverrides is None or len(masterOverrides.keys()) == 0:
        logger.error("cannot synchronize overrides as master overrides (%s) empty" % masterOverridesFile)
        return

    for i in range(len(overrideFiles)):
        ovFile = overrideFiles[i]
        if i > 0:
            logger.info("")
        logger.info("Synchonizing %s ..." % ovFile)
        oldOverrides = compareOverrides.loadOverrides(ovFile)

        # Copy the master then merge the settings to keep
        newOverrides = masterOverrides.copy()
        kept = 0
        for optionSet in keep:
            settings = keep[optionSet]
            if oldOverrides.has_key(optionSet):
                oldOptionSet = oldOverrides.get(optionSet, {})
                newOptionSet = newOverrides.get(optionSet, {})
                for k in settings:
                    if oldOptionSet.has_key(k):
                        currentValue = oldOptionSet[k]
                        newOptionSet[k] = currentValue
                        if verbose:
                            logger.info("keeping %s::%s = %s" % (optionSet,k,currentValue))
                        kept += 1
        logger.info("Setting counts: %d in master, %d in original, %d kept, %d after merge" % (_total(masterOverrides), _total(oldOverrides), kept, _total(newOverrides)))
         
        # Back-up and save
        if not commit:
            logger.info("No changes made to %s - use commit mode to save changes" % ovFile)
        else:
            bakFile = ovFile + ".bak"
            logger.info("Saving existing overrides to %s ..." % bakFile)
            mstaroverrides.saveOverridesToFile(bakFile, oldOverrides.items())
            logger.info("Saving new overrides to %s with %d settings kept ..." % (ovFile,kept))
            mstaroverrides.saveOverridesToFile(ovFile, newOverrides.items())
        
def _loadKeepList(csvFile):
    "load a list of properties to keep from a csv file with two columns: option-set and property key. Returns a dict of optionSetName to a list of settings to keep."
    keep = {}
    file = open(csvFile, "rb")
    reader = csv.DictReader(file)
    for row in reader:
        optionSet = row[COL_OPTION_SET]
        setting = row[COL_SETTING]
        if keep.has_key(optionSet):
            settings = keep[optionSet]
        else:
            settings = []
        settings.append(setting)
        keep[optionSet] = settings
    return keep

def _total(overrides):
    "return the total number of settings in an overrides dictionary"
    count = 0
    for i in overrides.keys():
        count += len(overrides[i].keys())
    return count


# Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [\
        make_option("-c", "--commit", action="store_true", help="commit mode - do not just notify the user"),\
        make_option("-k", "--keepListFile", help="CSV file containing properties to keep - columns are OptionSet and SettingName"),\
        ]
    argumentsStr = "masterOverridesFile overridesFile ..."
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Get the UFS root as it is required for looking up defaults
    mstarpaths.loadMineStarConfig()
    ufsPath = mstarpaths.interpretVar("UFS_PATH")
    ufsRoot = ufs.getRoot(ufsPath)

    # Load the overrides files and compare them
    keepListFile = options.keepListFile
    if not keepListFile:
        keepListFile = mstarpaths.interpretPath("{MSTAR_PATHS}/keepOverrides.csv")
    masterOverridesFile = args[0]
    overrideFiles = args[1:]
    syncOverrides(keepListFile, masterOverridesFile, overrideFiles, options.commit, options.verbose)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
