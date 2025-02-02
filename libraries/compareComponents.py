__version__ = "$Revision: 1.1 $"

import os, sys, zipfile
import minestar, mstarpaths, makeBuildManifest, ufs

logger = minestar.initApp()

def checkBuildManifest(inputFile, skipPatternsFile=None, resultsFile=None, differencesFile="buildDifferences.zip"):
    # Load the skip patterns, if any
    skipPatterns = []
    if skipPatternsFile is None:
        logger.info("No skip patterns file specified")
    else:
        logger.info("Loading skip patterns from %s ..." % skipPatternsFile)
        skipPatterns = makeBuildManifest.loadSkipPatterns(skipPatternsFile)
        logger.info("Found %d skip patterns" % len(skipPatterns))

    # Generate the comparison between expected and actual
    logger.info("Loading expected manifest from %s ..." % inputFile)
    expected = loadBuildManifest(inputFile, skipPatterns)
    logger.info("Generating manifest for current build ...")
    classLocations = {}
    actual = makeBuildManifest.getBuildManifest(classLocations, skipPatterns)
    local = makeBuildManifest.dumpManifestToString(actual)
    logger.info("Comparing expected vs actual ...")
    (matches, mismatches, missing, extras) = compareBuildManifests(expected, actual)
    # Dump the comparison
    if resultsFile is None:
        output = sys.stdout
        outputName = "standard output"
    else:
        output = open(resultsFile, "w")
        outputName = resultsFile
    logger.info("Dumping comparison to %s ..." % outputName)
    dumpComparison(len(expected), len(actual), matches, mismatches, missing, extras, output)
    buildDifferenceZip(mismatches, differencesFile, classLocations, local)
    if output is not sys.stdout:
        output.close()

def loadBuildManifest(inputFile, skipPatterns=None):
    # Read the lines from the manifest file and return the manifest as a dictionary
    try:
        fp = open(inputFile, "r")
        lines = fp.readlines()
        fp.close()
    except IOError, msg:
        logger.error('%s: I/O error: %s\n' % (inputFile, msg))
    return parseManifestLines(lines, skipPatterns)

def loadBuildManifestFromString(s, skipPatterns=None):
    return parseManifestLines(s.split("\n"), skipPatterns)

def parseManifestLines(lines, skipPatterns):
    # Parse the lines in a manifest
    manifest = {}
    for line in lines:
        fields = line.strip().split("\t")
        checksum = fields[0]
        id = fields[1]
        phys = fields[2]
        if idMatchesSkipPatterns(id, skipPatterns):
            continue
        manifest[id] = (checksum, phys)
    return manifest

def idMatchesSkipPatterns(id, skipPatterns):
    if skipPatterns is None:
        return 0
    for pat in skipPatterns:
        if pat.search(id):
            return 1
    return 0

def compareBuildManifests(expected, actual):
    # Compare two manifest and return the tuple of (number of matches, mismatched items, missing items, extra items)
    matches = 0
    mismatches = []
    missing = []
    extras = actual.keys()[:]
    for eKey in expected:
        if eKey in actual:
            extras.remove(eKey)
            # field 0 is checksum, field 1 is physical location
            if expected[eKey][0] == actual[eKey][0]:
                matches += 1
            else:
                mismatches.append(eKey)
        else:
            missing.append(eKey)
    return (matches, mismatches, missing, extras)

def dumpComparison(totalExpected, totalActual, totalMatches, mismatches, missing, extras, output=sys.stdout):
    # Dump the comparison results to a file/stream
    mismatchCount = len(mismatches)
    missingCount = len(missing)
    extraCount = len(extras)
    issueCount = mismatchCount + missingCount + extraCount
    summary1 = "%d issues found (%d mismatches, %d missing, %d extra)" % (issueCount,mismatchCount,missingCount,extraCount)
    summary2 = "%d matches out of %d expected (%d actual)" % (totalMatches,totalExpected,totalActual)
    summary = "SUMMARY:\n" + summary1 + " - " + summary2 + "\n"
    if output is not sys.stdout:
        logger.info(summary)
    output.write(summary)
    _dumpList(mismatches, "Mismatched items", output)
    _dumpList(missing, "Missing items", output)
    _dumpList(extras, "Extra items", output)

def buildDifferenceZip(mismatches, filename, classLocations, localManifestString):
    zf = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED)
    zf.writestr("localManifest.txt", localManifestString)
    byloc = {}
    ufsRoot = makeBuildManifest.getUfsRootWithoutCfg(silent=1)
    for mismatch in mismatches:
        if mismatch.startswith("class:"):
            location = classLocations[mismatch]
            if byloc.get(location) is None:
                byloc[location] = []
            byloc[location].append(mismatch[6:])
        else:
            addUfsFileToZip(mismatch, ufsRoot, zf)
    for (loc, classes) in byloc.items():
        logger.info("Recording differences found in %s (%d)" % (loc, len(classes)))
        addClassesToZip(loc, classes, zf)
    zf.close()

def addUfsFileToZip(location, ufsRoot, diffzip):
    (type,title) = location.split(":", 1)
    nameInArchive = type + title
    ufsFile = ufsRoot.get(title)
    try:
        fp = open(ufsFile.getPhysicalFile(), "r")
    except IOError, msg:
        logger.error('%s: Can\'t open: %s\n' % (title, msg))
        return
    diffzip.writestr(nameInArchive, fp.read())
    try:
        fp.close()
    except IOError, msg:
        logger.error('%s: Can\'t close: %s\n' % (title, msg))

def addClassesToZip(location, classes, diffzip):
    zf = zipfile.ZipFile(location, "r")
    for className in zf.namelist():
        if className in classes:
            bytes = zf.read(className)
            diffzip.writestr("class/" + className, bytes)
    zf.close()

def _dumpList(list, title, output=sys.stdout):
    list.sort()
    output.write("\n%s (%d):\n" % (title,len(list)))
    output.write("\n".join(list))
    output.write("\n")


## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = "originalBuildDir [newBuildDir]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Load the manifest and compare the build against it
    originalBuildDir = args[0]
    newBuildDir = None
    if len(args) > 1:
        newBuildDir = args[1]
    else:
        mstarpaths.loadMineStarConfig()
        newBuildDir = mstarpaths.interpretPath("{MSTAR_HOME}")
    compareComponents(originalBuildDir, newBuildDir)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
