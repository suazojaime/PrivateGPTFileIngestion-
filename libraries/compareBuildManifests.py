__version__ = "$Revision: 1.1 $"

import os, sys, zipfile
import minestar, mstarpaths, makeBuildManifest, checkBuildManifest

logger = minestar.initApp()

def compareBuildManifests(manifest1File, manifest2File, skipPatternsFile=None, resultsFile=None):
    # Load the skip patterns, if any
    skipPatterns = []
    if skipPatternsFile is None:
        logger.info("No skip patterns file specified")
    else:
        logger.info("Loading skip patterns from %s ..." % skipPatternsFile)
        skipPatterns = makeBuildManifest.loadSkipPatterns(skipPatternsFile)
        logger.info("Found %d skip patterns" % len(skipPatterns))

    # Generate the comparison between expected and actual        
    logger.info("Loading first manifest from %s ..." % manifest1File)
    manifest1 = checkBuildManifest.loadBuildManifest(manifest1File, skipPatterns)
    logger.info("Loading second manifest from %s ..." % manifest2File)
    manifest2 = checkBuildManifest.loadBuildManifest(manifest2File, skipPatterns)
    logger.info("Comparing manifests ...")
    (matches, mismatches, missing, extras) = checkBuildManifest.compareBuildManifests(manifest1, manifest2)

    # Dump the comparison
    if resultsFile is None:
        output = sys.stdout
        outputName = "standard output"
    else:
        output = open(resultsFile, "w")
        outputName = resultsFile
    logger.info("Dumping comparison to %s ..." % outputName)
    checkBuildManifest.dumpComparison(len(manifest1), len(manifest2), matches, mismatches, missing, extras, output)
    if output is not sys.stdout:
        output.close()
   

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = "manifest1File manifest2File [resultsFile]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Load the manifest and compare the build against it
    manifest1File = args[0]
    manifest2File = args[1]
    resultsFile = None
    if len(args) > 2:
        resultsFile = args[2]
    mstarpaths.loadMineStarConfig()
    skipPatternsFile = mstarpaths.interpretPath(makeBuildManifest.MANIFEST_SKIP_FILE)
    if not os.path.exists(skipPatternsFile):
        skipPatternsFile = None
    compareBuildManifests(manifest1File, manifest2File, skipPatternsFile, resultsFile)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
