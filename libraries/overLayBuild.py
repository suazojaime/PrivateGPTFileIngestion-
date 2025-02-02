import minestar, mstarpaths, os, xml, mstarext, zipfile, StringIO, tempfile, sys, shutil
from optparse import make_option

__version__ = "$Revision: 1.14 $"

logger = minestar.initApp()
mstarpaths.loadMineStarConfig()

# MineStar source class files
# For 3.0 GA all the mp-* domain classes will be stored under zip packages.
zipmodList = ["mp-base.zip","mp-env.zip","mp-gem.zip","mp-jive.zip","mp-platform.zip","mp-util.zip"]
jarfileList = ["mcexplorer.jar","mciworks.jar","mctool.jar","mscapead.jar","networkmender.jar"]

# getting MSTAR_HOME, MSTAR_TEMP & MSTAR_UPDATES directory for extraction
mstarHome = mstarpaths.interpretPath("{MSTAR_HOME}")
mstarTemp = mstarpaths.interpretPath("{MSTAR_TEMP}")
mstarUpdates = mstarpaths.interpretPath("{MSTAR_UPDATES}")
mstarExt = os.sep.join([mstarHome,"ext"])

# jad command
JAD = "jad -f -nonlb -d %s -s %s -o %s"

class NoExtensionXml:
    def __init__(self):
        pass

class Zip:
    def __init__(self, f):
        self.broken = False
        try:
            self.filename = f
            self.readXml()
        except:
            self.broken = True
            (exctype, value) = sys.exc_info()[:2]
            if exctype == NoExtensionXml:
                # some other zip file we can't find an extension.xml in
                return
            try:
                if value.message == "Required subelement timestamp not found":
                    # It's an extension
                    return
            except:
                #maybe we can't extract value.message
                print
            logger.error("Error reading file %s" % f)

    def readXml(self):
        bytes = None
        zf = zipfile.ZipFile(self.filename, "r")
        for info in zf.infolist():
            (head, tail) = os.path.split(info.filename)
            if head.find("patch_details") > 0:
                continue
            if tail == "extension.xml" and len(info.filename.split(os.path.sep)) <= 2:
                bytes = zf.read(info.filename)
        zf.close()
        if bytes is None:
            raise NoExtensionXml()
        dom = xml.dom.minidom.parseString(bytes)
        rootElement = dom.documentElement
        self.id = mstarext.getString(rootElement, "id", 1, None)
        self.patch = mstarext.getBoolean(rootElement, "patch")
        self.timestamp = mstarext.getElementString(rootElement, "timestamp", 1, None)

def addPatches(d, putThemInHere):
    if os.path.isdir(d):
        return
    try:
        z = Zip(d)
        if z.broken:
            return
        if z.patch:
            putThemInHere.append(z)
    except NoExtensionXml:
        # zip of zips
        zf = zipfile.ZipFile(d, "r")
        for info in zf.infolist()[:]:
            z = Zip(StringIO.StringIO(zf.read(info.filename)))
            if z.patch:
                putThemInHere.append(z)
        zf.close()
    except zipfile.BadZipfile:
        # some other sort of file, e.g. readme.txt
        pass

class ServicePackBuilder:
    def __init__(self,tempDir):
        self.tempDir = tempDir
        self.ids = []
        self.classZips = []
        self.classes = os.sep.join([self.tempDir, "classes"])
        self.description = ""

    def addPatch(self, patch):
        if patch.id in self.ids:
            logger.warning("Duplicate patch %s not added again" % patch.id)
            return
        logger.info("Extracting patch %s " % patch.id)
        zf = zipfile.ZipFile(patch.filename, "r")
        for info in zf.infolist():
            if not info.filename.startswith(patch.id + "/"):
                logger.info("Found %s in patch %s?" % (info.filename, patch.id))
                continue
            zname = info.filename[len(patch.id) + 1:]
            bytes = zf.read(info.filename)
            if info.filename == (patch.id + "/MineStar/lib/" + patch.id + ".zip"):
                logger.info("Unpacking classes file %s" % info.filename)
                cf = zipfile.ZipFile(StringIO.StringIO(bytes))
                minestar.unpack(cf, self.classes)
                cf.close()
            elif info.filename.endswith(".jar"):
                name = os.sep.join([self.tempDir, zname])
                minestar.makeDirsFor(name)
                f1 = file(name, "wb")
                f1.write(zf.read(info.filename))
                f1.close
            else:
                # truncate the trailing slash
                totalLen = len(zname)
                posSlash = zname.rfind("/")+1
                if totalLen != posSlash:
                    if zname in ["details.txt", "manifest.txt", "extension.xml", "readme.txt"]:
                        continue
                    else:
                        name = os.sep.join([self.tempDir, zname])
                        minestar.makeDirsFor(name)
                        f = file(name, "wb")
                        f.write(bytes)
                        f.close()
                        logger.info("    %s" % name)
        zf.close()
        self.ids.append(patch.id)

def extractMineStarZipFiles(archivefile,extractDir):
    if os.path.exists(archivefile):
        zf = zipfile.ZipFile(archivefile, "r")
        for info in zf.infolist():
            zname = info.filename
            bytes = zf.read(zname)
            if zname.endswith(".jar"):
                cf = zipfile.ZipFile(StringIO.StringIO(bytes))
                if isAMineStarJar(cf):
                    logger.info("    Unpacking classes file %s" % zname)
                    minestar.unpack(cf, extractDir)
                cf.close()
        zf.close()

def extractMineStarJarFiles(jarFile,extractDir):
    if os.path.exists(jarFile):
        logger.info("    Unpacking classes file %s" % jarFile)
        jf = zipfile.ZipFile(jarFile, "r")
        if isAMineStarJar(jf):
            minestar.unpack(jf,extractDir)
        jf.close()

def isAMineStarJar(zf):
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
    return result

def mergeNonclassFiles(patchDir):
    # copy all the mstar extension directory files
    logger.info("  Processing MineStar Extension directories...")
    dirtoExclude = ["manual","classes","patch_details","MineStar"]
    syncDir(patchDir,mstarExt,dirtoExclude)

    logger.info("  Processing MineStar main directories...")
    # copy all MineStar files from patch directory
    mstarsrc = os.sep.join([patchDir,"MineStar"])
    syncDir(mstarsrc,mstarHome)

    logger.info("  Processing MineStar manual directories...")
    # copy all manual MineStar files from patch directory
    mstarmanual = os.sep.join([patchDir,"manual","MineStar"])
    syncDir(mstarmanual,mstarHome)
        
def mergeClassFiles(src,patchDir):
    for i in range(0, len(zipmodList)):
        zfName = zipmodList[i]
        modsrcPath = os.sep.join([mstarExt,zfName])
        extractMineStarZipFiles(modsrcPath,src)
    logger.info("    MineStar Class ZIP files unpacking complete.")

    mstarLib = os.sep.join([mstarHome,"lib"])
    for i in range(0, len(jarfileList)):
        jfName = jarfileList[i]
        jarsrcPath = os.sep.join([mstarLib,jfName])
        extractMineStarJarFiles(jarsrcPath,src)

    logger.info("    MineStar Class JAR files unpacking complete.")

    # initializing extracted classes and util resource directories from the patch
    classesDir = os.sep.join([patchDir,"classes"])
    UtilDir = os.sep.join([patchDir,"Platform","Util","res"])

    # copy the classes extracted from patches to the main directory
    syncDir(classesDir,src)
    syncDir(UtilDir,src)

    decompileDir = os.sep.join([mstarHome,"decompiledClasses"])
    logger.info("  Decompilation Started. All the classes will be decomiled to %s " % decompileDir)
    # call decompile method to decompile the classes using jad
    decompile(src,decompileDir)
    logger.info("  Decompilation complete.")

def decompile(src, dest):
    files = os.listdir(src)
    for file in files:
        filePath = "%s%s%s" % (src, os.sep, file)
        if os.path.isdir(filePath):
            (newPath, lastBit) = os.path.split(filePath)
            destPath = os.path.join(dest,lastBit)
            decompile(filePath,destPath)
        else:
            destPath = os.sep.join([dest, file])
            if file.endswith(".class") and file.find("$") > 0:
                continue
            elif file.endswith(".class"):
                minestar.makeDirsFor(destPath)
                cmd = JAD % (dest, "java", filePath)       
                os.system(cmd)
                logger.info("    Decompiled the class: %s" % file)
            else:
                logger.info("    Copying resource file %s to %s" % (file,dest))
                minestar.makeDirsFor(destPath)
                minestar.copy(filePath, dest, True)

def syncDir(src,dest,excludeDir=None):
    if os.access(src, os.F_OK):
        for f in os.listdir(src):
            if isExcludedDir(f,excludeDir):
                continue
            srcPath = "%s%s%s" % (src, os.sep, f)
            if os.path.isdir(srcPath):
                (newPath, lastBit) = os.path.split(srcPath)
                destPath = os.path.join(dest, lastBit)
                syncDir(srcPath,destPath)
            else:
                destPath = os.sep.join([dest, f])
                if (f == "extensionmarker"):
                    continue
                logger.info("    Copying file %s to %s" % (f,dest))
                minestar.makeDirsFor(destPath)
                minestar.copy(srcPath, dest, True)

def isExcludedDir(dirName,excludeDir):
    result = 0
    if not excludeDir is None:
        for dir in excludeDir:
            if dirName == dir:
                logger.warning("    The directory \"%s\" is ignored " % dir)
                result = 1

    return result          

def main(appConfig=None):
    """entry point when called from mstarrun"""
    optionDefns = [\
        make_option("-d", "--outputDir", help="the directory to create overlay"),\
        ]
    argumentsStr = "..."
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)
    patchDir = options.outputDir
    # if there is no outputdir supplied the assign a default one
    extractPatchesDir = os.sep.join([mstarTemp,"extractedFromPatches"])
    if patchDir is None:
        patchDir = extractPatchesDir

    logger.info("All the software updates will be extrated to %s " % patchDir)

    allPatches = []
    for f in os.listdir(mstarUpdates):
        addPatches(os.sep.join([mstarUpdates, f]), allPatches)
    allPatches.sort(lambda p1, p2: cmp(p1.timestamp, p2.timestamp))
  
    servicePack = ServicePackBuilder(patchDir)
    for patch in allPatches:
        servicePack.addPatch(patch)

    logger.info("Merging the non-class files from the patch directory...")
    mergeNonclassFiles(patchDir)
    logger.info("Merging the class files from the patch directory...")
    
    extractClassesDir = os.sep.join([patchDir,"allClasses"])
    mergeClassFiles(extractClassesDir,patchDir)

    logger.info('Extracting and Merging complete...')

if __name__ == '__main__':
    """entry point when called from python"""
    main()
