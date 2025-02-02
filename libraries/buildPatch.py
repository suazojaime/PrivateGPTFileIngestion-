import mstarpaths, sys, zipfile, os, re, fnmatch, shutil, time, minestar, mstarext, ConfigurationFileIO
from xml.dom import minidom


__version__ = "$Revision: 1.22 $"

logger = minestar.initApp()

DIRECTORIES_TO_IGNORE = [".", "..", "CVS"]
MANUAL_PATCH_FILES = ["mstarrun.py"]

EXTENSION_MARKER = "extensionmarker"
DEFAULT_REPOS_PATH = "{MSTAR_HOME}/../../../../.."

MINESTAR_EXTENSION_DIRECTORY_PATTERN = "%s/minestar/fleetcommander/src/main/config/ext"
PLATFORM_EXTENSION_DIRECTORY_PATTERN = "%s/%s/src/main/config"

DEFAULT_BUILD_DIR_PATTERN = "%s/sandbox"
DEFAULT_PLATFORM_BUILD_OUTPUT_PATTERN = "%s/platform_build_output/%s/classes"
DEFAULT_MINESTAR_BUILD_OUTPUT_PATTERN = "%s/classes"

PLATFORM_CVS_MODULE_NAMES = ["gem", "jive", "env"]
MINESTAR_CVS_MODULE_NAME = "mo-cutdown"

TYPE_CLASS = "class"
TYPE_UFS_FILE = "ufs"
TYPE_RES = "res"

PATCH_METADATA = {
    'patchId': '',
    'name': '',
    'newMineStarVersion' : '',
    'patchVersion': '',
    'shortDescription': '',
    'description': '',
    'scope': '',
    'risks': '',
    'installation': 'Standard patch installation process',
    'postinstall': '',
    'uninstall': 'Contact Cat_IPSD_Product_Hotline@cat.com',
    'postuninstall': '',
    'validation': '',
    'obsoletes': '',
    'related': '',
    'contact': 'Cat_IPSD_Product_Hotline@cat.com',
    'restart': 'All of MineStar',
    'timestamp': '',
    }

EXTENSION_XML_TEMPLATE = \
            "<?xml version=\"1.0\" encoding=\"us-ascii\" standalone=\"no\"?>" + os.linesep + \
            "<!-- Created by Patch Builder $Revision: 1.22 $ -->" + os.linesep + os.linesep + \
            "<extension id=\"%(patchId)s\" name=\"%(name)s\" compulsory=\"false\" invisible=\"true\" patch=\"true\" servicePack=\"false\" version=\"%(patchVersion)s\">" + os.linesep + \
            "<shortDescription>%(shortDescription)s</shortDescription>" + os.linesep + \
            "<description>%(description)s</description>" + os.linesep + \
            "<scope>%(scope)s</scope>" + os.linesep + \
            "<risks>%(risks)s</risks>" + os.linesep + \
            "<installation>%(installation)s</installation>" + os.linesep + \
            "<postinstall>%(postinstall)s</postinstall>" + os.linesep + \
            "<uninstall>%(uninstall)s</uninstall>" +os.linesep + \
            "<postuninstall>%(postuninstall)s</postuninstall>" + os.linesep + \
            "<validation>%(validation)s</validation>" + os.linesep + \
            "<obsoletes>%(obsoletes)s</obsoletes>" + os.linesep + \
            "<related>%(related)s</related>" + os.linesep + \
            "<contact>%(contact)s</contact>" + os.linesep + \
            "<restart>%(restart)s</restart>" + os.linesep + \
            "<timestamp>%(timestamp)s</timestamp>" + os.linesep + \
            "<id>%(name)s</id>" + os.linesep + \
            "</extension>"

README_TEMPLATE = \
            "DESCRIPTION" + os.linesep + "%(description)s" + os.linesep + os.linesep + "REQUIRED SYSTEM" + os.linesep + "%(patchVersion)s" + os.linesep + \
            os.linesep + "SCOPE OF CHANGE" + os.linesep + "%(scope)s" + os.linesep + os.linesep + "RISKS AND CONTINGENCIES" + os.linesep + "%(risks)s" + os.linesep + \
            os.linesep + "INSTALLATION PROCESS" + os.linesep + "%(installation)s" + os.linesep + os.linesep + "RESTARTS" + os.linesep + "%(restart)s" + os.linesep + \
            os.linesep + "POST INSTALL" + os.linesep + "%(postinstall)s" + os.linesep + os.linesep + "ROLLBACK PROCESS" + os.linesep + "%(uninstall)s" + os.linesep + \
            os.linesep + "POST UNINSTALL" + os.linesep + "%(postuninstall)s" + os.linesep + os.linesep + "TESTING/VALIDATION" + os.linesep + "%(validation)s" + os.linesep + \
            os.linesep + "OBSOLETES" + os.linesep + "%(obsoletes)s" + os.linesep + os.linesep + "RELATED BUG(S)/ENHANCEMENT(S)" + os.linesep + "%(related)s" + os.linesep + \
            os.linesep + "CONTACTS" + os.linesep + "%(contact)s"


# given a manifest file generated from a cvs rlog, generate a patch directory containing
# files that will be included in the patch
def generatePatchDirectory(reposDir, buildDir, patchDir, manifestFileName):

    manifestFile = open(manifestFileName, "r")
    lines = manifestFile.readlines(1000)
    while lines != []:
        for line in lines:
            moduleInfo = getModuleForManifestLine(line)
            if moduleInfo is None:
                continue
            moduleName = moduleInfo[0]
            fileType = moduleInfo[1]
            fileName = moduleInfo[2]
            outputPath = moduleInfo[3]

            buildPath = None
            extensionPath = None
            sourcePath = None
            if moduleName == "minestar":
                buildPath = mstarpaths.interpretPath(DEFAULT_MINESTAR_BUILD_OUTPUT_PATTERN % buildDir)
                extensionPath = mstarpaths.interpretPath(MINESTAR_EXTENSION_DIRECTORY_PATTERN % reposDir)
            else:
                buildPath = mstarpaths.interpretPath(DEFAULT_PLATFORM_BUILD_OUTPUT_PATTERN % (buildDir, moduleName))
                extensionPath = mstarpaths.interpretPath(PLATFORM_EXTENSION_DIRECTORY_PATTERN % (reposDir, moduleName))
            reposPath = reposPath = mstarpaths.interpretPath("%s/%s" % (reposDir, moduleName))

            if fileType == TYPE_CLASS:
                sourcePath = buildPath
            elif fileType == TYPE_RES:
                sourcePath = reposPath
            else:
                sourcePath = reposPath

            fullFileName = os.sep.join([sourcePath, fileName])
            if fileType != TYPE_CLASS:
                if not os.path.exists(fullFileName):
                    print "Skipping deleted file %s" % fullFileName
                    continue

            print "Processing file %s from module %s " % (fileName, moduleName)
            ufsPath = None
            extension = None
            if fileType == TYPE_UFS_FILE:
                ufsPath = inferUFSLocation(reposPath, extensionPath, fullFileName)
                extension = guessExtension(ufsPath, extensionPath, fullFileName)
                if extension is None:
                    print "Cannot determine extension. Skipping..."
                    continue

            manualPatch = os.path.basename(fileName) in MANUAL_PATCH_FILES
            addToPatchDirectory(patchDir, sourcePath, outputPath, fileType, fileName, extension, ufsPath, manualPatch)
        lines = manifestFile.readlines(1000)
    manifestFile.close()

    print "Finished generating patch directory %s" % patchDir

def getModuleForManifestLine(line):
    line = line.strip()
    for moduleName in PLATFORM_CVS_MODULE_NAMES:
        fileType=None
        fileName=None
        outputPath=None
        if line.startswith(moduleName+"@"):
            line = line[len(moduleName+"@"):]
            if line.endswith(moduleName+".zip"):
                return None
            if line.startswith("src/main/java/"):
                fileName = line[len("src/main/java/"):]
                outputPath = os.path.dirname(fileName)
                fileType = TYPE_CLASS
            elif line.startswith("src/test/java/"):
                fileName = line[len("src/test/java/"):]
                outputPath = os.path.dirname(fileName)
                fileType = TYPE_CLASS
            elif line.startswith("res/"):
                fileName = line
                outputPath = os.path.dirname(line[len("res/"):])
                fileType = TYPE_RES
            elif line.startswith("src/res/"):
                fileName = line
                outputPath = os.path.dirname(line[len("src/main/res/"):])
                fileType = TYPE_RES
            elif line.startswith("src/main/config/"):
                fileName = line
                outputPath = os.path.dirname(line[len("src/main/config/"):])
                fileType = TYPE_UFS_FILE
            elif line.startswith("src/Database/"):
                fileName = line
                outputPath = os.path.dirname(line[len("src/Database/"):])
                fileType = TYPE_UFS_FILE
            else:
                print "Unknown %s file type for line %s" % (moduleName, line)
                return None
            return (moduleName, fileType, fileName, outputPath)
    if line.startswith(MINESTAR_CVS_MODULE_NAME+"@"):
        line = line[len(MINESTAR_CVS_MODULE_NAME+"@/CVSROOT/minestar/"):]
        #ignore TAE stuff
        if line.startswith("create/ext/Assignment/Assignment_Management/bin"):
            return None
        if line.startswith("java/src/"):
            fileName = line[len("java/src/"):]
            outputPath = os.path.dirname(fileName)
            fileType = TYPE_CLASS
        elif line.startswith("java/res/"):
            fileName = line
            outputPath = os.path.dirname(line[len("java/res/"):])
            fileType = TYPE_RES
        elif line.startswith("create/"):
            fileName = line
            outputPath = os.path.dirname(line[len("create/"):])
            if re.compile("create/ext/mp.*\.zip").match(line) is not None:
                return None
            fileType = TYPE_UFS_FILE
        else:
            print "Unknown %s file type for line %s" % (MINESTAR_CVS_MODULE_NAME, line)
            return None
        return ("minestar", fileType, line, outputPath)
    return None

def addToPatchDirectory(patchDir, sourceDir, outputPath, fileType, file, extension, ufsPath, manual):
    if os.path.isdir(file):
        return
    if fileType == TYPE_CLASS:
        addClassFile(sourceDir, patchDir, outputPath, file)
    elif fileType == TYPE_RES:
        fileToCopy = os.sep.join([sourceDir, file])
        addResourceFileOrLib(patchDir, extension, os.sep.join(["res", outputPath]), fileToCopy, manual)
    else:
        fileToCopy = os.sep.join([sourceDir, file])
        addResourceFileOrLib(patchDir, extension, ufsPath, fileToCopy, manual)

def addResourceFileOrLib(patchDir, extension, packageDir, fileToCopy, manual):
    if extension is None:
        extension = "MineStar";
    extension = mstarpaths.interpretPath(extension)
    fileDest=None; extDir = None
    if manual:
        fileDest = os.sep.join([patchDir, "manual", extension, packageDir])
        extDir = os.sep.join([patchDir, "manual", extension])
    else:
        fileDest = os.sep.join([patchDir, extension, packageDir])
        extDir = os.sep.join([patchDir, extension])

    #print "UFS: copy %s to %s" % (fileToCopy, fileDest)
    minestar.makeDir(fileDest)
    shutil.copy(fileToCopy, fileDest)

    extMarker = os.sep.join([extDir, EXTENSION_MARKER])
    if not os.path.exists(extMarker):
        extensionMarker = open(extMarker, "w")
        extensionMarker.close()

deletedDirectories = []

def addClassFile(buildDir, patchDir, packageDir, fileName):
    baseClassName = os.path.basename(fileName)
    baseClassName = baseClassName[0:len(baseClassName) - 5]
    classPath = os.sep.join([buildDir, packageDir])
    classFiles = []
    try:
        classFiles = fnmatch.filter(os.listdir(classPath), "*.class")
    except:
        if classPath not in deletedDirectories:
            print "Directory %s does not exist in build output - ignoring" % classPath
        deletedDirectories.append(classPath)
        return

    for classFile in classFiles:
        baseClassNameToCheck = os.path.basename(classFile)
        if baseClassNameToCheck.startswith(baseClassName) or baseClassNameToCheck.startswith(baseClassName+"$"):
            fileToCopy = os.sep.join([classPath, classFile])
            fileDest = os.sep.join([patchDir, "classes", packageDir])
            #print "copy %s to %s" % (fileToCopy, fileDest)
            #print "copying class file %s" % classFile
            minestar.makeDir(fileDest)
            shutil.copy(fileToCopy, fileDest)

def guessExtension(ufspath, baseDir, file):
    # the new way
    current = file
    current = os.path.abspath(os.sep.join([current, os.path.pardir]))
    while os.path.isdir(current) and  not baseDir == current:
        ex = os.sep.join([current, "extension.xml"])
        if os.path.exists(ex):
            xmldoc = minidom.parse(ex).documentElement
            return xmldoc.attributes["root"].value
        else:
            current = os.path.abspath(os.sep.join([current, os.path.pardir]))
    return None

def inferUFSLocation(reposPath, baseDir, file):
    #look for extension.xml in an ancestor directory
    current = file
    current = os.path.abspath(os.sep.join([current, os.path.pardir]))
    while not baseDir == current:
        ex = os.sep.join([current, "extension.xml"])
        if os.path.exists(ex) or current == reposPath or current == os.path.abspath(os.sep.join([reposPath, "java"])):
            # found the extension this file is in
            currPat = os.path.abspath(current)
            if file.startswith(currPat):
                return os.path.dirname(file[len(currPat)+1:])
        else:
            current = os.path.abspath(os.sep.join([current, os.path.pardir]))
    return None

def findNewTempDir():
    result = None
    baseDir = mstarpaths.interpretPath("{MSTAR_TEMP}/update")
    code = 0
    while result is None:
        dirName = "%s%s" % (baseDir, code)
        if os.path.exists(dirName):
            files = os.listdir(dirName)
            if files == []:
                result = dirName
            else:
                code = code+1
        else:
            minestar.makeDir(dirName)
            result = dirName
    return result

# build the manifest
def buildManifest(patchDir):
    manifestFile = "manifest.txt"
    manifest = open(manifestFile, "w")
    files = recursiveFileList(None)
    for file in files:
        manifest.write(file + "\n")
    manifest.close()

def buildDetailsFile():
    try:
        user = os.environ['USERNAME']
    except:
        try:
            user = os.environ['USER']
        except:
            user = "MineStar Builder"
    detailsFile = "details.txt"
    details = open(detailsFile, "w")
    details.write("Patch %(name)s\n" % PATCH_METADATA)
    details.write("User %s\n" % user)
    details.write("Time %(timestamp)s\n" % PATCH_METADATA)
    try:
        hostname = os.environ['COMPUTERNAME']
    except:
        try:
            hostname = os.environ['HOSTNAME']
        except:
            hostname = "Build Machine"
    details.write("Machine %s\n" % hostname)
    details.close()

def makeJarFileName(patchDir, fileName):
    jarFileName = os.sep.join([patchDir, "MineStar", "lib", fileName + ".zip"])
    minestar.makeDirsFor(jarFileName)
    return jarFileName

def buildJarFile(patchDir, patchId):
    jarFileName = makeJarFileName(patchDir, patchId)
    zf = zipfile.ZipFile(jarFileName, "w", zipfile.ZIP_DEFLATED)
    os.chdir("classes")
    files = recursiveFileList(None)
    for file in files:
        zf.write(file, file)
    zf.close()
    os.chdir(patchDir)
    minestar.rmdir("classes")

def unbuildJarFile(patchDir, patchId):
    import minestar, os
    jarFileName = makeJarFileName(patchDir, patchId)
    if os.access(jarFileName, os.F_OK):
        zf = zipfile.ZipFile(jarFileName)
        classesDir = os.sep.join([patchDir, "classes"])
        minestar.unpack(zf, classesDir)
        zf.close()
        os.remove(jarFileName)
        lib = os.sep.join([patchDir, "MineStar", "lib"])
        if len(os.listdir(lib)) == 0:
            minestar.rmdir(lib)

def zipPatch(patchDir, patchFile, patchId):
    # zip the files
    (head, tail) = os.path.split(patchDir)
    zf = zipfile.ZipFile(patchFile, "w", zipfile.ZIP_DEFLATED)
    files = recursiveFileList(patchDir)
    os.chdir(head)
    for file in files:
        relativePath = file[len(patchDir):]
        zf.write(file, patchId + relativePath.strip())
    zf.close()

def recursiveFileList(prefix):
    result = []
    files = os.listdir(os.getcwd())
    for file in files:
        if os.path.isdir(file):
            if file not in DIRECTORIES_TO_IGNORE:
                p = prefix
                if p is None:
                    p = file
                else:
                    p = p + os.sep + file
                os.chdir(file)
                result = result + recursiveFileList(p)
                os.chdir("..")
        else:
            if prefix is None:
                result.append(file)
            else:
                result.append(prefix + os.sep + file)
    return result

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [\
        make_option("-d", "--patchDir", help="the directory containing the files to be included in the patch"),\
        make_option("-r", "--reposDir", help="the top level directory of the repository"),\
        make_option("-b", "--buildDir", help="the top level build directory"),\
        make_option("-m", "--manifestFile", help="the name of the file containing a list of inclusions for the patch"),\
        make_option("-e", "--metadataFile", help="the name of the file containing the patch metadata"),\
        make_option("-t", "--patchTimestamp", help="the timestamp of the patch"),\
        make_option("-n", "--patchName", help="the name of the patch"),\
        make_option("-o", "--patchVersion", help="old release version of MineStar this patch upgrades from"),\
        make_option("-w", "--newVersion", help="new release version of MineStar this patch upgrades to"),\
        ]
    argumentsStr = "..."
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    mstarpaths.loadMineStarConfig()
    patchDir = options.patchDir
    reposDir = options.reposDir
    buildDir = options.buildDir
    manifestFile = options.manifestFile
    patchName = options.patchName
    patchTimestamp = options.patchTimestamp
    metadataFile = options.metadataFile

    if patchName is None:
        print "Patch name must be specified"
        minestar.exit(1)

    if metadataFile is not None:
        if os.access(metadataFile, os.F_OK):
            fileMetadata = ConfigurationFileIO.loadDictionaryFromFile(metadataFile)
            for key, value in fileMetadata.items():
                if (value): PATCH_METADATA[key] = value
        else:
            print "Invalid metadata file %s" % metadataFile
            minestar.exit(1)

    if options.patchVersion is not None:
        PATCH_METADATA['patchVersion'] = options.patchVersion
    if options.newVersion is not None:
        PATCH_METADATA['newMineStarVersion'] = options.newVersion

    patchId = patchName
    if patchTimestamp is None:
        #patch timestamp is not specified on the command line
        t = time.time()
        patchTimestamp = time.strftime("%Y%m%d%H%M", time.localtime(t))
    else:
        #patch timestamp is specified on the command line
        patchId = patchTimestamp + "_" + patchName

    PATCH_METADATA['name'] = patchName
    PATCH_METADATA['timestamp'] = patchTimestamp
    PATCH_METADATA['patchId'] = patchId

    if patchDir is None:
        patchDir = findNewTempDir()

    patchFile = None
    if len(args) > 0:
        patchFile = mstarpaths.interpretPath(args[0])
    if patchFile is None:
        patchFileDir = os.sep.join([patchDir, os.path.pardir])
        patchFile = os.sep.join([os.path.abspath(patchFileDir), patchId + ".zip"])
    print "Patch will be created in file %s" % patchFile

    if reposDir is None:
        reposDir = mstarpaths.interpretPath(DEFAULT_REPOS_PATH)

    #fallback - determine the MineStar version we are patching
    if PATCH_METADATA['patchVersion'] == "":
        PATCH_METADATA['patchVersion'] = mstarext.getMineStarVersion()

    # if we are upgrading a whole build then add some extra descriptions
    if options.patchVersion is not None:
        PATCH_METADATA['shortDescription'] = "Upgrade version %(patchVersion)s of MineStar to version %(newMineStarVersion)s" % PATCH_METADATA
        PATCH_METADATA['description'] = "This patch upgrades version %(patchVersion)s of MineStar to version %(newMineStarVersion)s and supercedes all previously issues patches" % PATCH_METADATA
        PATCH_METADATA['scope'] = "All files updated since last MineStar release"
        PATCH_METADATA['obsoletes'] = "All previously issued patches for prior release"

    # if we have a manifest file we need to generate the contents of the patch directory
    if manifestFile is not None:
        if not os.access(manifestFile, os.F_OK):
            print "Manifest file %s does not exist or cannot be read" % manifestFile
            minestar.exit(1)
        if buildDir is None:
            buildDir = mstarpaths.interpretPath(DEFAULT_BUILD_DIR_PATTERN % reposDir)

        generatePatchDirectory(reposDir, buildDir, patchDir, manifestFile)

    # write the extension.xml and readme files
    XML_PATCH_METADATA = PATCH_METADATA.copy()
    from xml.sax import saxutils
    for key, value in XML_PATCH_METADATA.items():
        if value is None:
            print "No patch metadata value for %s" % key
        else:
            XML_PATCH_METADATA[key] = saxutils.escape(value)

    extFileName = os.sep.join([patchDir, "extension.xml"])
    extensionFile = open(extFileName, "w")
    extensionFile.write(EXTENSION_XML_TEMPLATE % XML_PATCH_METADATA)
    extensionFile.close()

    readmeFile = open(os.sep.join([patchDir, "readme.txt"]), "w")
    readMeTxt = README_TEMPLATE % PATCH_METADATA
    readMeTxt = readMeTxt.replace("$crlf ", os.linesep)
    readmeFile.write(readMeTxt)
    readmeFile.close()

    print "Packing patch......."
    os.chdir(patchDir)
    minestarEm = None
    if os.access(os.sep.join([patchDir, "classes"]), os.F_OK):
        buildJarFile(patchDir, patchId)
        minestarEm = os.sep.join([patchDir, "MineStar", "extensionmarker"])
        if not os.access(minestarEm, os.F_OK):
            em = file(minestarEm, "w")
            em.close()
    buildManifest(patchDir)
    buildDetailsFile()
    zipPatch(patchDir, patchFile, patchId)
    unbuildJarFile(patchDir, patchId)
    if minestarEm is not None:
        minestar.rmdir(os.sep.join([patchDir, "MineStar"]))
    print "Patch %s completed" % patchFile
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
