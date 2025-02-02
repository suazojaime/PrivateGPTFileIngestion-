__version__ = "$Revision: 1.3 $"

import os
import minestar, mstarpaths

logger = minestar.initApp()


def cleanTempDir(later=0):
    "If later is true, the directory is simply marked for later clean-up. This is required as Java locks jars in extensions and patches."
    mstarpaths.loadMineStarConfig()
    tmpDir = mstarpaths.interpretPath("{MSTAR_TEMP}")
    # As recursively deleting everything under a directory is very harmful if MSTAR_TEMP is badly set, we make a sanity check first
    if tmpDir.endswith("tmp"):
        if later:
            logger.info("Marking %s for clean-up on next mstarrun command" % tmpDir)
            cleanMarker = tmpDir + os.path.sep + minestar.CLEAN_ME_FILE
            file = open(cleanMarker, "wb")
            file.close()
        else:
            logger.info("Cleaning %s ..." % tmpDir)
            (dirCount,fileCount) = minestar.rmdirWithLogging(tmpDir, logger, justChildren=1)
            logger.info("Removed %d directories and %d files" % (dirCount,fileCount))
    else:
        logger.warning("Not cleaning MSTAR_TEMP (%s) because it doesn't look correct" % tmpDir)


# Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = ""
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Delete the temporary directory
    cleanTempDir()
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
