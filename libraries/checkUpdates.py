__version__ = "$Revision: 1.1 $"

import os
import minestar, mstarext, mstarpaths

logger = minestar.initApp()

DIRECTORIES_TO_IGNORE = [".", "..", "CVS"]

def jartf(zext):
    jar = mstarpaths.java
    jar = jar[:jar.rfind(os.sep)]
    jar = mstarpaths.interpretPath("%s/jar{EXE}" % jar)
    cmd = "%s tf %s" % (jar, zext.filename)
    lines = minestar.systemEvalRaw(cmd)
    return lines

def checkExpectedFiles(dir, files, source):
    errors = 0
    good = 0
    for f in files:
        path = os.sep.join([dir, f])
        if not os.access(path, os.R_OK):
            errors = errors + 1
            logger.error("%s from %s NOT FOUND: expected at %s" % (f, source, path))
        else:
            good = good + 1
    return (errors, good)

def checkPatches():
    mstarpaths.loadMineStarConfig()
    et = 0
    gt = 0
    logger.info("Found %d unzip directories to check ..." % len(mstarext.unzipDirs))
    for (dir, zext) in mstarext.unzipDirs:
        logger.info("Checking unzip of %s" % zext.filename)
        expectedFiles = jartf(zext)
        (e,g) = checkExpectedFiles(dir, expectedFiles, zext.filename)
        et = et + e
        gt = gt + g
    logger.info("%d files found OK" % gt)
    logger.info("%d files not found" % et)

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = ""
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)
    checkPatches()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
