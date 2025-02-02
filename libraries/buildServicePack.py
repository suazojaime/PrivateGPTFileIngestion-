import minestar, mstarpaths, os, xml, mstarext, zipfile, StringIO, tempfile, sys, shutil

__version__ = "$Revision: 1.14 $"

logger = minestar.initApp()

PATCH_METADATA_STRING = """
patchId:
name:
newMineStarVersion:
patchVersion:
shortDescription:
description:%s
scope:
risks:
installation:Supervisor
postinstall:
uninstall:
postuninstall:
validation:
obsoletes:
related:
contact:
restart:
timestamp:
"""

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
            print "Error reading file %s" % f

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
    def __init__(self, filename, id, name, tempDir, build, patchVersion=None):
        self.filename = filename
        self.id = id
        self.name = name
        self.tempDir = tempDir
        self.ids = []
        self.classZips = []
        self.classes = os.sep.join([self.tempDir, "classes"])
        self.build = build
        self.patchVersion = patchVersion
        self.description = ""

    def addPatch(self, patch):
        if patch.id in self.ids:
            print "Duplicate patch %s not added again" % patch.id
            return
        print "Adding patch %s to service pack" % patch.id
        zf = zipfile.ZipFile(patch.filename, "r")
        for info in zf.infolist():
            if not info.filename.startswith(patch.id + "/"):
                print "Found %s in patch %s?" % (info.filename, patch.id)
                continue
            zname = info.filename[len(patch.id) + 1:]
            bytes = zf.read(info.filename)
            if info.filename == (patch.id + "/MineStar/lib/" + patch.id + ".zip"):
                print "    Unpacking classes file %s" % info.filename
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
                        name = os.sep.join([self.tempDir, "patch_details", patch.id, zname])
                    else:
                        name = os.sep.join([self.tempDir, zname])

                    # write the description to the xml file so that it can used in the patch consolidation
                    if zname in ["extension.xml"]:
                        dom = xml.dom.minidom.parseString(bytes)
                        rootElement = dom.documentElement
                        patchname = mstarext.getString(rootElement, "name", 1)
                        descrip = patchname + ": " + mstarext.getElementString(rootElement, "shortDescription", 1)
                        self.description = self.description + descrip + "$crlf "

                    minestar.makeDirsFor(name)
                    f = file(name, "wb")
                    f.write(bytes)
                    f.close()
                    print "    %s" % name
        zf.close()
        self.ids.append(patch.id)

    def addPatchMetadata(self):
        outputDir = mstarpaths.interpretPath("{MSTAR_TEMP}")
        s = PATCH_METADATA_STRING % (self.description)
        f = file(os.sep.join([outputDir, "patch_metadata.txt"]), "w")
        f.write(s.strip())
        f.close()
        metadir = os.sep.join([outputDir, "patch_metadata.txt"])
        return metadir

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [\
        make_option("-b", "--buildNum", help="the MineStar build number"),\
        make_option("-i", "--id", help="the id of the service service pack"),\
        make_option("-n", "--name", help="the name of the service service pack"),\
        make_option("-d", "--outputDir", help="the directory to create the service service pack"),\
        make_option("-o", "--patchVersion", help="old release version of MineStar this service pack upgrades from"),\
        ]
    argumentsStr = "..."
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    mstarpaths.loadMineStarConfig()
    name = options.name
    id = options.id
    build = options.buildNum
    patchVersion = options.patchVersion
    outputDir = options.outputDir

    patchFile = None
    if len(args) > 0:
        patchFile = mstarpaths.interpretPath(args[0])

    if id is None or name is None or build is None:
        print "Usage: buildServicePack <-i id> <-n name> <-b build> [-o patchVersion] [patchfile]"
        sys.exit(1)

    mstarpaths.loadMineStarConfig()
    if outputDir is None:
        outputDir = mstarpaths.interpretPath("{MSTAR_TEMP}")
    outfile = os.sep.join([outputDir, id + ".zip"])
    if os.path.exists(outfile):
        print "Output file %s already exists - deleting..." % outfile
        os.remove(outfile)

    allPatches = []
    if patchFile is not None:
        print "Building service pack for single patch file %s" % patchFile
        addPatches(patchFile, allPatches)
    else:
        for f in os.listdir("."):
            addPatches(os.sep.join([".", f]), allPatches)
    allPatches.sort(lambda p1, p2: cmp(p1.timestamp, p2.timestamp))
    tempdir = tempfile.mkdtemp("", "servicePack", mstarpaths.interpretPath("{MSTAR_TEMP}"))
    servicePack = ServicePackBuilder(outfile, id, name, tempdir, build, patchVersion)
    for patch in allPatches:
        servicePack.addPatch(patch)
    # add and get the metadata
    metadir = servicePack.addPatchMetadata()
    # get the timestamp and extension id
    import time
    tstamp = time.strftime("%Y%m%d%H%M")
    extid = tstamp + "_" + id
    # reconstruct the output file
    outfile = os.sep.join([outputDir, extid + ".zip"])
    import mstarrun
    mstarrun.run(["buildPatch", "-d", tempdir, "-n", id, "-e", metadir, "-t", tstamp, outfile])
    minestar.rmdir(tempdir)
    print "Service pack is %s" % outfile

if __name__ == '__main__':
    """entry point when called from python"""
    main()
