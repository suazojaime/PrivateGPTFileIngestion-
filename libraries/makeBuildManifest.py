__version__ = "$Revision: 1.5 $"

# Default skip patterns file
MANIFEST_SKIP_FILE = "{MSTAR_HOME}/MANIFEST.SKIP"

import os, sys, re, md5, zipfile
import minestar, mstarpaths, ufs

logger = minestar.initApp()

def checkBuildManifest(outputFilename, classLocations, skipPatternsFile=None):
    # Load the skip patterns, if any
    skipPatterns = []
    if skipPatternsFile is None:
        logger.info("No skip patterns file specified")
    else:
        logger.info("Loading skip patterns from %s ..." % skipPatternsFile)
        skipPatterns = loadSkipPatterns(skipPatternsFile)
        logger.info("Found %d skip patterns" % len(skipPatterns))

    # Generate the manifest and dump it
    logger.info("Generating manifest for current build ...")
    manifest = getBuildManifest(classLocations, skipPatterns)
    logger.info("Dumping manifest to %s ..." % outputFilename)
    dumpManifest(manifest, outputFilename)
    logger.info("Saved %d items in the manifest" % len(manifest))

def loadSkipPatterns(inputFile):
    # Read the patterns to skip from a file and return them as a list of compiled regular expressions. Blank lines and lines beginning with # in the file are ignored.
    try:
        fp = open(inputFile, "r")
        lines = fp.readlines()
        fp.close()
    except IOError, msg:
        logger.error('%s: I/O error: %s\n' % (inputFile, msg))

    # Parse the lines into a list of patterns
    result = []
    for line in lines:
        line = line.strip()
        if len(line) == 0 or line[0] == '#':
            continue
        result.append(re.compile(line))
    return result

def idMatchesSkipPatterns(id, skipPatterns):
    #if len(skipPatterns) == 0:
    #    return false
    for pat in skipPatterns:
        if pat.search(id):
            return 1
    return 0

def getUfsRootWithoutCfg(silent=0):
    mstarpaths.loadMineStarConfig()
    ufsPath = mstarpaths.interpretVar("UFS_PATH")
    mstarCfg = mstarpaths.interpretVar("MSTAR_CONFIG")
    if ufsPath.endswith(mstarCfg):
        ufsPath = ufsPath[:-len(mstarCfg) + 1]
        if not silent:
            logger.info("removing %s from the search path" % mstarCfg)
    else:
        if not silent:
            logger.warn("unable to find MSTAR_CONFIG on the search path - can't remove it")
    return ufs.getRoot(ufsPath)

def getBuildManifest(classLocations, skipPatterns=[]):
    manifest = {}
    ufsRoot = getUfsRootWithoutCfg()
    appendFiles(manifest, ufsRoot, skipPatterns)
    (bcp, cp, classPathDirs, classPathJars) = mstarpaths.buildClassPaths(ufsRoot, 0, None, None)
    for jar in cp:
        if isAMineStarJar(jar):
            appendClasses(manifest, jar, classLocations, skipPatterns)
    return manifest

def isAMineStarJar(jar):
    if os.path.basename(jar).startswith("20") and jar.endswith(".zip"):
        # looks like a MineStar patch, which has no manifest
        return 1
    import zipfile
    zf = zipfile.ZipFile(jar)
    result = 0
    try:
        bytes = zf.read("META-INF/MANIFEST.MF")
        lines = bytes.split("\n")
        for line in lines:
            line = line.strip()
            if line.endswith("MineStar"):
                result = 1
                break
            elif line.endswith("Caterpillar MineStar Solutions"):
                result = 1
                break
    except KeyError:
        pass
    zf.close()
    return result

def appendFiles(manifest, ufsDir, skipPatterns=[]):
    # Checksum the files in this directory
    for ufsFile in ufsDir.listFiles():
        path = ufsFile.getPath()
        isText = path.endswith(".properties") or path.endswith(".py") or path.endswith(".txt")
        if isText:
            id = "text:" + path
        else:
            id = "file:" + path
        if idMatchesSkipPatterns(id, skipPatterns):
            continue
        if manifest.has_key(id):
            print "warning: duplicate id found: %s" % id
            continue
        if not (id.endswith(".jar") or id.endswith(".zip")) or not isAMineStarJar(ufsFile.getPhysicalFile()):
            # note: classes are done in classpath order instead
            checksum = _checksumUfsFile(ufsFile, id, text=isText)
            manifest[id] = (checksum, ufsFile.getPhysicalFileName())
    # Loop over subdirectories
    for ufsSubdir in ufsDir.listSubdirs():
        if ufsSubdir.getFile("extension.xml") is not None:
           # this is an extension, which really exists at the top of the UFS tree, not in it.
           continue
        appendFiles(manifest, ufsSubdir, skipPatterns)

def appendClasses(manifest, jar, classLocations, skipPatterns=[]):
    import classfile
    # Checksum the classes in this jar
    zf = zipfile.ZipFile(jar, "r")
    for className in zf.namelist():
        id = "class:" + className
        classLocations[id] = jar
        if manifest.get(id) is not None:
            continue
        m = md5.md5()
        bytes = zf.read(className)
        if className.endswith(".class") and (className.startswith("com/mincom") or className.startswith("minestar")):
            bytes = [ ord(c) for c in bytes ]
            bytes = classfile.nullLineNumbers(bytes)
            bytes = "".join([ chr(c) for c in bytes ])
        m.update(bytes)
        checksum = _hexify(m.digest())
        manifest[id] = (checksum, jar)
    zf.close()

def _checksumUfsFile(ufsFile, title, bufsize=4096, rmode='r', text=0):
    m = md5.md5()
    try:
        fp = open(ufsFile.getPhysicalFile(), rmode)
    except IOError, msg:
        logger.error('%s: Can\'t open: %s\n' % (title, msg))
        return -1
    try:
        if text:
            pattern = re.compile(r'\$Id\:.*\$')
            for line in fp:
                (line, count) = pattern.subn(r'\$Id\$', line)
                m.update(line)
                if count:
                    logger.debug('matched CVS string in %s' % title)
        else:
            while 1:
                data = fp.read(bufsize)
                if not data: break
                m.update(data)
    except IOError, msg:
        logger.error('%s: I/O error: %s\n' % (title, msg))
        return -2
    try:
        fp.close()
    except IOError, msg:
        logger.error('%s: Can\'t close: %s\n' % (title, msg))
    return _hexify(m.digest())

def _hexify(s):
    res = ''
    for c in s:
        res = res + '%02x' % ord(c)
    return res

def dumpManifest(manifest, outputFilename):
    sortedKeys = manifest.keys()
    sortedKeys.sort()
    output = open(outputFilename, "w")
    for ufsName in sortedKeys:
        (hash, physName) = manifest[ufsName]
        output.write("%s\t%s\t%s\n" % (hash, ufsName, physName))
    output.close()

def dumpManifestToString(manifest):
    lines = []
    sortedKeys = manifest.keys()
    sortedKeys.sort()
    for ufsName in sortedKeys:
        (hash, physName) = manifest[ufsName]
        lines.append("%s\t%s\t%s" % (hash, ufsName, physName))
    return "\n".join(lines)

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = "outputFilename"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Generate the build manifest and dump it
    outputFilename = args[0]
    mstarpaths.loadMineStarConfig()
    skipPatternsFile = mstarpaths.interpretPath(MANIFEST_SKIP_FILE)
    if not os.path.exists(skipPatternsFile):
        skipPatternsFile = None
    classLocations = {}
    checkBuildManifest(outputFilename, classLocations, skipPatternsFile)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
