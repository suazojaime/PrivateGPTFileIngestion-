import mstarpaths, os, zipfile, xml.dom.minidom, stat, minestar, string, sys, StringTools

UNPACK_EXTENSIONS_TO = "{MSTAR_TEMP}/ext"
UNPACK_ZIPS_TO = "{MSTAR_TEMP}/zip"
CONFIG_LOGS = "{MSTAR_LOGS}/config"
BACKUP_PREFIX = "extensions_used_"
BACKUP = "extensions_used_%s.log"
REPOSITORY_EXTENSIONS = ['catfiles']

# this is used to find out what patches are really being used without replicating all the logic
patchesActuallyUsed = []
# this is used to detect patch id conflicts
patchFilesByID = {}
# this is where patches and zipped extensions were unzipped to
# this is needed because we have a bug in the unzipping and need to check that it unzipped OK
unzipDirs = []
parts = []

# Cached value of extensions package directory.
# XXX This should not change?
_extensionsPackageDir = None

def mstarrunDebugEnabled():
    """ Determines if mstarrun debug is enabled (i.e. if MSTARRUN_DEBUG is defined in OS environment). """
    return 'MSTARRUN_DEBUG' in os.environ


def mstarrunDebug(msg):
    """ Print a message to stdout if mstarrun debug is enabled. """
    if mstarrunDebugEnabled():
        print "debug: %s" % msg

def getBoolean(element, attr):
    if not element.getAttribute(attr):
        return 0
    return element.getAttribute(attr).lower() in ["true"]

def getString(element, attr, required, default=""):
    s = element.getAttribute(attr)
    if not s and required:
        raise ExtensionException("Required attribute %s not found" % attr)
    if s:
        return s
    else:
        return default

def getElementString(element, subelement, required, default=""):
    element.normalize()
    es = element.getElementsByTagName(subelement)
    if es.length == 0:
        if required:
            raise ExtensionException("Required subelement %s not found" % subelement)
        else:
            return default
    try:
        return "".join([es.item(i).firstChild.data for i in range(es.length)])
    except:
        return default

class ExtensionException:
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

def readRootFromExtensionXml(extXml):
    with open(extXml, 'rt') as f:
        bytes = f.read()
        try:
            dom = xml.dom.minidom.parseString(bytes)
            rootElement = dom.documentElement
            root = getString(rootElement, "root", True, None)
            compulsory = getBoolean(rootElement, "compulsory")
            return (root, compulsory)
        except:
            value = sys.exc_info()[1]
            raise ExtensionException("Error in XML file %s: %s" % (extXml, value))

class Extension:
    def __init__(self):
        pass

    def _parse(self, bytes):
        "bytes is the content of extension.xml"
        try:
            dom = xml.dom.minidom.parseString(bytes)
        except:
            value = sys.exc_info()[1]
            raise ExtensionException("Error in XML: %s" % value)
        rootElement = dom.documentElement
        self.compulsory = getBoolean(rootElement, "compulsory")
        self.depends = getString(rootElement, "depends", False)
        self.id = getString(rootElement, "id", False, None)
        self.invisible = getBoolean(rootElement, "invisible")
        self.patch = getBoolean(rootElement, "patch")
        self.servicePack = getBoolean(rootElement, "servicePack")
        self.name = getString(rootElement, "name", False, None)
        self.part = getString(rootElement, "privilege", False, None)
        if not self.patch:
            self.root = getString(rootElement, "root", True, None)
        # patch-specific stuff
        if self.patch:
            self.timestamp = getElementString(rootElement, "timestamp", True, None)
            self.version = getString(rootElement, "version", False)
            if self.version == "":
                mesg = "%s is an invalid patch: does not specify a version" % self.id
                # can't log this message, we are too early for logit to work
                raise ExtensionException(mesg)

        # web extension specific stuff
        self.webdirectory = getString(rootElement, "webdirectory", False, None)
        if self.webdirectory != "":
            self.webcontext = getString(rootElement, "webcontext", False, "")

    def ufsdirs(self):
        u = [ self.ufsDir ]
        if self.__dict__.get("extraUfsDir") is not None:
            u.append(self.extraUfsDir)
        return u

class ZippedExtension(Extension):
    def __init__(self, filename, base=None):
        self.filename = filename
        self.base = base
        self.__load()
        self.reasons = []

    def zf(self):
        return zipfile.ZipFile(self.filename, "r")

    def __load(self):
        import hashlib
        hash = hashlib.new("md5")
        zipf = self.zf()
        infos = zipf.infolist()[:]
        self.infos = infos
        exbytes = None
        for info in infos:
            hash.update(`info.CRC`)
            (head, tail) = os.path.split(info.filename)
            if len(tail) == 0:
                # directory entry
                continue
            if head.find("patch_details") > 0:
                continue
            if tail == "extension.xml":
                self.root = head
                self.sortOrder = _getSortOrder(self.root)
                exbytes = zipf.read(info.filename)
        zipf.close()
        self.digest = hash.hexdigest()
        if exbytes is None:
            raise ExtensionException("Cannot find extension.xml")
        self._parse(exbytes)
        if self.patch or self.servicePack:
            self.extensions = []
            for info in infos:
                (head, tail) = os.path.split(info.filename)
                if tail == "extensionmarker":
                    if head.startswith(self.root):
                        self.extensions.append(head[len(self.root)+1:])
                    else:
                        print "%s has an extension marker in a strange place. Expecting %s." % (info.filename, self.root)

    def __str__(self):
        return "ZippedExtension[%s]" % self.filename

    def __repr__(self):
        return "ZippedExtension[%s]" % self.filename

    def isCompulsory(self):
        return self.compulsory

    def isInvisible(self):
        return self.invisible

    def id(self):
        return self.id

    def getFlag(self, key):
        return self.__dict__.get(key)

    def isPatch(self):
        return self.patch

    def isServicePack(self):
        return self.servicePack

    def patchKey(self):
        if not self.patch:
            return None
        return "patch_%s" % self.id

    def isEnabled(self, config):
        "Is the patch enabled in this configuration?"
        if not self.patch:
            return False
        key = self.patchKey()
        if config.get(key) is None:
            return False
        return minestar.parseBoolean(config[key], key)

def __readDigest(digestFileName):
    digest = None
    if os.access(digestFileName, os.R_OK):
        tsf = open(digestFileName, "r")
        lines = tsf.readlines()
        tsf.close()
        digest = lines[0].strip()
    return digest

def __writeDigest(digestFileName, digest):
    file = open(digestFileName, "w")
    file.write(digest)
    file.close()

def __installZippedExtension(zext, mstarConfig):
    """
        Install the extension in a temporary area given a ZippedExtension object.
        Return the name of the directory which must go on the UFS_PATH.
    """
    # make sure the temporary extension directory exists
    unpackExtensionsTo = mstarpaths.interpretPathOverride(UNPACK_EXTENSIONS_TO, mstarConfig)
    return __installZippedExtensionTo(zext, mstarConfig, unpackExtensionsTo)

def __installZippedExtensionTo(zext, mstarConfig, unpackExtensionsTo):
    """
        Install the extension to the specified directory given a ZippedExtension object.
        Return the name of the directory which must go on the UFS_PATH.
    """
    # If the extension root is 'foo/bar' then the extension directory will be '${mstarSystem}/tmp/ext/foo/bar'
    # on Unix and '${mstarSystem}\tmp\ext\foo\bar' on Windows,
    extDir = mstarpaths.interpretPathOverride(os.path.join(unpackExtensionsTo, zext.root), mstarConfig)
    if zext.isPatch() or zext.isServicePack():
        zext.ufsDirs = {}
    else:
        if zext.root is None:
            print zext.__dict__
        zext.ufsDir = extDir
    unzipDirs.append((extDir, zext))
    minestar.createExpectedDirectory(unpackExtensionsTo)
    tsFile = os.sep.join([extDir, "digest"])
    # is it already installed?
    digest = __readDigest(tsFile)
    mstarrunDebug("Extension '%s' has zip digest of %s and cached digest of %s" % (zext.id, zext.digest, digest))
    if digest != zext.digest:
        procid = "PID %d [%s]" % (os.getpid(), " ".join(sys.argv))
        if len(zext.reasons) > 0:
            reasons = " because %s" % ", ".join(zext.reasons)
        else:
            reasons = ""
        minestar.logit("%s: Installing modified extension %s from %s%s" % (procid, zext.id, zext.filename, reasons), mstarConfig)
        try:
            # delete any old version
            if os.access(extDir, os.F_OK):
                minestar.rmdir(extDir)
            unpack(zext.zf(), unpackExtensionsTo, digest)
            minestar.createExpectedDirectory(extDir)
            __writeDigest(tsFile, zext.digest)
        except OSError:
            import traceback
            exc = sys.exc_info()
            minestar.logit(procid + " " + "\n".join(traceback.format_exception(exc[0], exc[1], exc[2])), mstarConfig)
            print "Cannot unpack extension %s. Another process may have file locked.\nShutdown all MineStar processes and retry. If problem persists contact MineStar Support." % zext.filename
            sys.exit(125)
    if zext.isPatch() or zext.isServicePack():
        for info in zext.infos:
            (head, tail) = os.path.split(info.filename)
            if tail == "extensionmarker":
                if head.startswith(zext.root):
                    zext.ufsDirs[head[len(zext.root)+1:]] = os.sep.join([unpackExtensionsTo, head])

def _getLatestUsedZips(mstarConfig):
    "get the name of the file containing the latest list of used zips"
    dir = mstarpaths.interpretPathOverride(CONFIG_LOGS, mstarConfig)
    if not os.access(dir, os.R_OK):
        return None
    files = os.listdir(dir)
    last = -1
    result = None
    import stat
    for file in files:
        if file.startswith(BACKUP_PREFIX):
            mtime = os.stat(os.sep.join([dir, file]))[stat.ST_MTIME]
            if mtime > last:
                 result = file
                 last = mtime
    if result is None:
        return None
    return os.sep.join([dir, result])

def _modtime(f):
    "string representation of the modification time of a file"
    import stat, time
    mtime = os.stat(f)[stat.ST_MTIME]
    return time.strftime("%Y%m%d%H%M", time.localtime(mtime))

def __recordUsedZips(filenames, mstarConfig):
    """
        Record that a particular set of zip files was used, so that we can observe configuration changes in the system.
        filenames is the list of filenames that we'll be writing out.
    """
    filenames.sort()
    filenames = [ f + " " + _modtime(f) for f in filenames ]
    latest = _getLatestUsedZips(mstarConfig)
    backup = 1
    if latest is not None:
        latestContents = minestar.readLines(latest)
        if len(filenames) == len(latestContents):
            sameSoFar = 1
            for i in range(len(filenames)):
                if filenames[i] != latestContents[i]:
                    sameSoFar = 0
                    break
            if sameSoFar:
                backup = 0
    if backup:
        import time
        timestamp = time.strftime("%Y%m%d%H%M%S")
        destfile = mstarpaths.interpretPathOverride(CONFIG_LOGS + "/" + BACKUP % timestamp, mstarConfig)
        minestar.makeDirsFor(destfile)
        f = open(destfile, "w")
        for line in filenames:
            f.write(line + "\n")
        f.close()

def alphabetical(s):
    for c in s:
        if c not in string.ascii_letters:
            return 0
    return 1

def __determineRequiredExtensions(zexts, desiredExts):
    """
        Given all the zipped extensions available, and a list of desired extensions, return the list of
        zipped extensions which should be used. This includes desired and compulsory ones.
        desiredExts are optional extensions which should be loaded if we see them.
    """
    remainingDesiredExts = desiredExts[:]
    toInstall = []
    for ext in zexts:
        compulsory = 0
        desired = ext.root in desiredExts
        if ext.isCompulsory():
            compulsory = 1
        if not compulsory and not desired:
            # we don't want this extension anyway
            continue
        if ext.root in remainingDesiredExts:
            i = remainingDesiredExts.index(ext.root)
            del remainingDesiredExts[i]
        toInstall.append(ext)
        if compulsory:
            ext.reasons.append("it is a compulsory extension")
        if desired:
            ext.reasons.append("%s was listed in _SUBSYSTEMS" % ext.root)
    return (toInstall, remainingDesiredExts)

def compareVersions((v1, e1), (v2, e2)):
    try:
        f1 = float(v1)
        f2 = float(v2)
        return cmp(f1, f2)
    except ValueError:
        return cmp(`v1`, `v2`)

def findPatches(mstarConfig):
    "This is run after findZippedExtensions, so zips of patches will already be unpacked"
    extzip = mstarpaths.interpretPathOverride("{MSTAR_UPDATES}", mstarConfig)
    patches = findPatchesInDir(mstarConfig, extzip)
    unzipDir = mstarpaths.interpretPathOverride(UNPACK_ZIPS_TO, mstarConfig)
    for file in os.listdir(unzipDir):
        file = os.sep.join([unzipDir, file])
        if minestar.isDirectory(file):
            patches = patches + findPatchesInDir(mstarConfig, file)
    return patches

def findZippedExtensions(mstarConfig):
    """Find all installed zipped extensions and return a list of ZippedExtension objects"""
    unzipDir = mstarpaths.interpretPathOverride(UNPACK_ZIPS_TO, mstarConfig)
    minestar.createExpectedDirectory(unzipDir)

    # Find zipped extensions in ${MSTAR_HOME}/ext   (the pre-configured extensions).
    extzip = mstarpaths.interpretPathOverride("{MSTAR_HOME}/ext", mstarConfig)
    zexts = findZippedExtensionsInDir(mstarConfig, extzip)

    # Find zipped extensions in ${MSTAR_SYSTEM}/updates   (the custom extensions).
    updates = mstarpaths.interpretPathOverride("{MSTAR_UPDATES}", mstarConfig)
    zexts = zexts + findZippedExtensionsInDir(mstarConfig, updates)

    # Check for embedded extensions in ${MSTAR_SYSTEM]/tmp/ext directory.
    for file in os.listdir(unzipDir):
        file = os.sep.join([unzipDir, file])
        if minestar.isDirectory(file):
            zexts = zexts + findZippedExtensionsInDir(mstarConfig, file)

    # Replace each zipped extension with the latest in the extensions package (if required).
    return replaceWithUpdatedZippedExtensions(zexts, mstarConfig)

def replaceWithUpdatedZippedExtensions(extensions, mstarConfig=None):
    """Replace each extension with its update."""
    result = []
    updates = getZippedExtensionUpdates(mstarConfig, extensions)
    for extension in extensions:
        id = extension.id
        if id in updates:
            extension = updates[id].target
        result.append(extension)
    return result

class ExtensionUpdate:

    def __init__(self):
        self.source = None
        self.target = None

def isMatchingExtension(ext1, ext2):
    """Determines if two zipped extensions match (same id and same digest)."""
    def hasSameDigest(ext1, ext2):
        """Determines if ext1 has the same digest value as ext2."""
        return hasattr(ext1, 'digest') and hasattr(ext2, 'digest') and ext1.digest == ext2.digest

    return (ext1.id == ext2.id) and hasSameDigest(ext1, ext2)

def isLaterExtension(ext1, ext2):
    """Determines if ext1 is a later extension that ext2"""
    if hasattr(ext1, 'filename') and hasattr(ext2, 'filename'):
        timestamp1 = os.path.getmtime(ext1.filename)
        timestamp2 = os.path.getmtime(ext2.filename)
        return timestamp1 > timestamp2
    return False

def getZippedExtensionUpdates(mstarConfig, extensions):
    """Get the map of extension updates: id -> ExtensionUpdate"""
    result = {}

    # Get the available extensions in the extensions package.
    availableExtensions = getPackageExtensions(mstarConfig)
    for extension in extensions:
        id = extension.id
        available = getExtensionWithId(availableExtensions, id)
        # Replace extension if available has different digest and a later timestamp.
        if available and not isMatchingExtension(available, extension) and isLaterExtension(available, extension):
            update = ExtensionUpdate()
            update.source = extension
            update.target = available
            result[id] = update
    return result

def getPackageExtensions(mstarConfig=None):
    """Find the extensions that are available in the extensions package for the release."""
    return _findZippedExtensionsInExtensionPackageDir(mstarConfig)

def getExtensionWithId(extensions, id):
    for extension in extensions:
        if extension.id == id:
            return extension
    return None

def _findZippedExtensionsInUpdatesDir(mstarConfig):
    """Find the zipped extensions in the updates directory, e.g. /mstarFiles/systems/main/updates """
    updatesDir = mstarpaths.interpretPathOverride("{MSTAR_UPDATES}", mstarConfig)
    return findZippedExtensionsInDir(mstarConfig, updatesDir)

def _findZippedExtensionsInExtensionPackageDir(mstarConfig):
    """Find the zipped extensions in the extensions package directory, e.g /mstar/packages/extensions/5.6.0-1."""
    extensionsPackageDir = _getExtensionsPackageDir(mstarConfig)
    if extensionsPackageDir and os.access(extensionsPackageDir, os.F_OK):
        return findZippedExtensionsInDir(mstarConfig, extensionsPackageDir)
    return []

def _getExtensionsPackageDir(mstarConfig):
    """Get the extensions package path for the current release."""
    global _extensionsPackageDir
    if _extensionsPackageDir is None:
        _extensionsPackageDir = _loadExtensionsPackageDir(mstarConfig)
    return _extensionsPackageDir

def _loadExtensionsPackageDir(mstarConfig):
    """Find the directory containing the extensions package, e.g. /mstar/packages/extensions/5.6.0-1"""
    mstarInstallDir = mstarpaths.interpretPathOverride("{MSTAR_INSTALL}", mstarConfig)
    mstarHomeDir = mstarpaths.interpretPathOverride("{MSTAR_HOME}", mstarConfig)

    try:
        # Get a MineStar release and check that it is installed (may be some bootstrapping issues).
        from mstarRelease import MStarRelease
        mstarRelease = MStarRelease(mstarInstall=mstarInstallDir, mstarHome=mstarHomeDir)
        if not mstarRelease.installed:
            return None

        # Get the extensions package (if it exists) and derive its path.
        extensionsPackage = mstarRelease.getPackage('extensions')
        if extensionsPackage:
            return mstarRelease.getPackagePath(extensionsPackage)
    except:
        # Problem fetching packages. etc. Probably a bootstrapping issue. Assume
        # then that no extensions package is available (yet).
        pass

    return None

def _checkExtension(arg, dirname, names):
    (exts, baseDirLen) = arg
    if "extension.xml" in names:
        exts.append(dirname[baseDirLen:])

def getAllUnzippedExtensionNames(mstarConfig):
    exts = []
    directory = mstarpaths.interpretPathOverride("{MSTAR_HOME}/ext", mstarConfig)
    baseDirLen = len(directory) + 1
    os.path.walk(directory, _checkExtension, (exts, baseDirLen))
    return exts

def getUnzippedExtension(name):
    directory = mstarpaths.interpretPath("{MSTAR_HOME}/ext/%s" % name)
    if os.access(directory, os.F_OK):
        return directory
    else:
        return None

def __findAllExtensionNames(mstarConfig):
    zexts = findZippedExtensions(mstarConfig)
    all = zexts[:]
    names = [ ext.root for ext in all ]
    names = names + getAllUnzippedExtensionNames(mstarConfig)
    names = [ str(canonicaliseExtensionName(name)) for name in names ]
    ns = []
    for name in names:
        if name not in ns:
            ns.append(name)
    ns.sort()
    return ns

def loadPatchFromFile(filename):
    if not zipfile.is_zipfile(filename):
        print "File %s is not a valid zip file" % filename
        return None
    f = os.path.basename(filename)
    try:
        zext = ZippedExtension(filename, f[:-4])
        if not zext.isPatch():
            return None
    except ExtensionException, ex:
        # if this is an error it will be reported somewhere else
        return None
    return zext

def loadServicePackFromFile(filename):
    if not zipfile.is_zipfile(filename):
        print "File %s is not a valid zip file" % filename
        return None
    f = os.path.basename(filename)
    try:
        zext = ZippedExtension(filename, f[:-4])
        if not zext.isServicePack():
            return None
    except ExtensionException, ex:
        # if this is an error it will be reported somewhere else
        return None
    return zext

def findPatchesInDir(mstarConfig, zipdir):
    if os.access(zipdir, os.F_OK):
        files = os.listdir(zipdir)
    else:
        files = []
    patches = []
    for file in files:
        f = zipdir + os.sep + file
        if file.lower().endswith(".zip"):
            zext = loadPatchFromFile(f)
            if zext is not None:
                version = zext.version
                for v in [s.strip() for s in version.split(',')]:
                    patches.append(zext)
    return patches

def getServicePack(mstarConfig, zipdir):
    if os.access(zipdir, os.F_OK):
        files = os.listdir(zipdir)
    else:
        files = []
    sp = mstarpaths.interpretVarOverride("MSTAR_SERVICE_PACK", mstarConfig)
    for file in files:
        f = zipdir + os.sep + file
        if file.lower().endswith(".zip"):
            zext = loadServicePackFromFile(f)
            if zext is not None and zext.id == sp:
                return zext
    return None

def __unpackMultipleExtensions(mstarConfig, file, baseFileName):
    """
        Unpack a zip of zips to a temporary area.
        file is the full path of the zip file to be unpacked.
        baseFileName is the short file name of the zip file to be unpacked.
    """
    dirName = baseFileName[:-4]
    fileDir = mstarpaths.interpretPathOverride(UNPACK_ZIPS_TO + os.sep + dirName, mstarConfig)
    minestar.createExpectedDirectory(fileDir)
    digestFile = fileDir + os.sep + "digest"
    zipFile = zipfile.ZipFile(file, "r")
    import hashlib
    hash = hashlib.new("md5")
    infos = zipFile.infolist()[:]
    for info in infos:
        hash.update(`info.CRC`)
    digest = __readDigest(digestFile)
    if hash.hexdigest() != digest:
        for info in infos:
            fullFileName = fileDir + os.sep + platformPath(info.filename)
            makeDirsFor(fullFileName)
            if not os.path.isdir(fullFileName):
                file = open(fullFileName, "wb")
                file.write(zipFile.read(info.filename))
                file.close()
        __writeDigest(digestFile, hash.hexdigest())
    zipFile.close()

def findZippedExtensionsInDir(mstarConfig, zipdir):
    """
        Find any extensions in the zipdir directory.
        As this is required as part of mstarpaths's start up procedure, in particular just before
        it makes the UFS_PATH, the mstarpaths config has not yet been set. Consequently, a subset
        of that config is passed in as the mstarConfig parameter.
    """
    try:
        files = os.listdir(zipdir)
    except OSError:
        # directory probably doesn't exist
        files = []
    zexts = []
    for file in files:
        f = zipdir + os.sep + file
        if file.lower().endswith(".zip"):
            if not zipfile.is_zipfile(f):
                print "File %s is not a valid zip file" % f
                continue
            try:
                zext = ZippedExtension(f, f[:-4])
                if zext.isPatch():
                    continue
                zexts.append(zext)
            except ExtensionException, ex:
                if ex.message.startswith("Cannot find extension.xml"):
                    __unpackMultipleExtensions(mstarConfig, f, file)
                else:
                    print "Error loading %s: %s" % (f, ex)

    # print "## findZippedExtensionsInDir() dir=%s" % zipdir
    # for extension in zexts:
    #     print "## findZippedExtensionsInDir()  %s" % extension.id

    return zexts

def unpack(zipf, zipDir, expectedDigest):
    "Unpack the files in the ZipFile zip to zipDir"
    import hashlib
    hash = hashlib.new("md5")
    for info in zipf.infolist():
        fullFileName = zipDir + os.sep + platformPath(info.filename)
        makeDirsFor(fullFileName)
        if info.filename.endswith("/"):
            continue
        with open(fullFileName, "wb") as f:
            f.write(zipf.read(info.filename))
        hash.update(`info.CRC`)
    digest = hash.hexdigest()
    complain = False
    # we can't log to syslog here as we haven't figured out where MSTAR_LOGS is yet.
    for info in zipf.infolist():
         fullFileName = zipDir + os.sep + platformPath(info.filename)
         if not os.access(fullFileName, os.F_OK):
             complain = True
             print "MSTAR-3781 Unpacked file %s but it does not exist at %s" % (info.filename, fullFileName)
    if complain:
        print "MSTAR-3781 Expected digest was %s but digest calculated during unpacking was %s" % (expectedDigest, digest)
        print "Please send this message to MineStar support, clear your MineStar temp directory, and restart MineStar."
        sys.exit(32)
    zipf.close()

def makeDirsFor(filename):
    "We are going to create filename, so create the directories that it needs."
    filename = string.replace(filename, "\\", "/")
    parts = filename.split("/")
    dirs = string.join(parts[:-1], os.sep)
    try:
        os.makedirs(dirs)
    except OSError:
        # already exists
        pass

def platformPath(path):
    path = string.replace(path, "\\", "/")
    parts = path.split("/")
    return string.join(parts, os.sep)

def __fixSlashes(s):
    s = s.replace("\\", "/")
    fields = s.split("/")
    fields = [ x.strip() for x in fields ]
    fields = [ x for x in fields if len(x) > 0 ]
    return "/".join(fields)

def __getDesiredExtensions(config):
    result = ["Platform/Platform_Management"]
    platformDoc = mstarpaths.interpretPathOverride("{MSTAR_HOME}/ext/English/Platform_Documentation", config)
    if os.path.exists(platformDoc):
        result.append("English/Platform_Documentation")
    if config.has_key("_BUSPACKAGE"):
        result.append(config["_BUSPACKAGE"])
    if config.has_key("_SUBSYSTEMS"):
        result = result + [x for x in config["_SUBSYSTEMS"].split(",") if x != '']
    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject(config,'mpaths')
    result = result + dbobject.getDatabaseExtensions(config)
    # the _SUBSYSTEMS variable sometimes has backslashes in it, which can cause us
    # to not know when we've found an extension we want
    result = [ __fixSlashes(x) for x in result ]
    return result

def __getDevelopmentResourceDirs(config):
    runningFromRepository = mstarpaths.runningFromRepository
    dirs = []
    if runningFromRepository:
        for id in ["jive", "env", "gem", "fleetcommander", "uifacadeimpl", "uifacade", "jiveclient", "terrain-bridge", "geometry", "web/war"]:
            # Add the ${module}/src/main directory (if ${module}/src/main/res is present).
            dir = mstarpaths.interpretPathOverride("{REPOSITORY_HOME}/%s/src/main" % id, config)
            if os.path.exists(os.path.join(dir, "res")):
                dirs.append(dir)
            # Add the ${module}/src/main/config directory (if present).
            c = os.path.join(dir, "config")
            if os.path.exists(c):
                dirs.append(c)
            # Add ${module}/target/config directory (if present).
            c = mstarpaths.interpretPathOverride("{REPOSITORY_HOME}/%s/target/config" % id, config)
            if os.path.exists(c):
                dirs.append(c)
        # res.zip like util-res.zip are unzipped to this directory for mstarrun in source code, e.g. mstarrun makeCatalogs all
        dirs.append(mstarpaths.interpretPathOverride("{REPOSITORY_HOME}/devenv/target/mstar/mstarHome", config))
    # Add the paths specified in DEVELOPMENT property (if defined).
    development = mstarpaths.interpretVarOverride("DEVELOPMENT", config)
    if development is not None and len(development.strip()) > 0:
        devs = development.strip().split(os.pathsep)
        for dev in devs:
            dexists = os.access(dev, os.F_OK)
            if dexists:
                c = mstarpaths.interpretPath(dev + "/classes")
                cexists = os.access(c, os.F_OK)
                r = mstarpaths.interpretPath(dev + "/res")
                rexists = os.access(r, os.F_OK)
                if rexists or not cexists:
                    dirs.append(dev)
    return dirs

def __patchOrder(p1, p2):
    if p1.filename < p2.filename:
        return -1
    if p2.filename < p1.filename:
        return 1
    return 0

mineStarVersion = None

def getMineStarVersion(config=None):
    global mineStarVersion
    if mineStarVersion is None:
        file = mstarpaths.getReleaseInfoFile(config)
        import ConfigurationFileIO
        dict = ConfigurationFileIO.loadDictionaryFromFile(file)
        mineStarVersion = dict["MAJOR"]
    return mineStarVersion

def __installPatchesFor(mstarConfig, allPatches, loadedExtensions, servicePack):
    installedPatches = []
    ufsDirs = []
    allPatches.sort(__patchOrder)
    loadedExtensionNames = []
    allPatches.sort(lambda p1, p2: cmp(p1.timestamp, p2.timestamp))
    if servicePack is not None:
        __installZippedExtension(servicePack, mstarConfig)
    for ext in loadedExtensions:
        pu = ext.ufsdirs()[:]
        if servicePack is not None and ext.root in servicePack.extensions:
            spUfsDir = servicePack.ufsDirs[ext.root]
            pu.append(spUfsDir)
        for patch in allPatches:
            if ext.root in patch.extensions:
                __installZippedExtension(patch, mstarConfig)
                patchUfsDir = patch.ufsDirs[ext.root]
                pu.append(patchUfsDir)
                if patch not in installedPatches:
                    installedPatches.append(patch)
                    # this data is used by the printPatches target
                    patchesActuallyUsed.append((patch.filename, patch.id))
                    if patchFilesByID.get(patch.id) is not None:
                        print "Patch %s is ambiguous: patch %s has the same ID (%s)" % (patch.filename, patchFilesByID[patch.id], patch.id)
                        sys.exit(82)
                    patchFilesByID[patch.id] = patch.filename
        ufsDirs.append(pu)
    return (installedPatches, ufsDirs)

class DirectoryExtension(Extension):
    def __init__(self, root, ufsDir):
        self.root = root
        self.sortOrder = _getSortOrder(root)
        self.ufsDir = ufsDir
        extensionXml = os.sep.join([ufsDir, "extension.xml"])
        with open(extensionXml, 'rt') as f:
            Extension._parse(self, f.read())
    def __str__(self):
        return "DirectoryExtension[%s]" % self.root

    def __repr__(self):
        return self.__str__()

def _getSortOrder(root):
    if root.startswith("mp-"):
        return 1/0
    if root == "Platform/Platform_Management":
        return 8
    elif root in ["Platform/Base", "Platform/Util", "Platform/GEM", "Platform/Environment", "Platform/Jive"]:
        return 4
    elif root.startswith("Platform/"):
        # mp-platform stuff
        return 2
    elif root == "MineStar":
        return 6
    else:
        return 10

def __installUnzippedExtensions(config, neededExts, usedExtensions):
    # desired extensions which come unpacked
    extHome = mstarpaths.interpretPathOverride("{MSTAR_HOME}/ext", config)
    placesToLook = []
    if mstarpaths.runningFromRepository:
        # REPOSITORY_EXTENSIONS contains the name of extensions that are shipped with minestar.  When running out
        # of the repository these extensions are always included.
        otherdir = mstarpaths.interpretPathOverride("{REPOSITORY_HOME}", config)
        for otherextpaths in [ x + "/src/main/config/" for x in  REPOSITORY_EXTENSIONS]:
            fullotherextpath = os.sep.join([otherdir, otherextpaths])
            if os.path.isdir(fullotherextpath):
                placesToLook.append(fullotherextpath)
            else:
                print "WARNING: Expected directory " + fullotherextpath + " is missing"
        # Look for additional override directory to indicate where to search for custom extensions.  We search
        # the environment variable REPOSITORY_EXTENSIONS_EXTRA which is expected to be a single or list of paths
        # separated by the OS path separator
        extraRepositoryExtensions = mstarpaths.interpretVarOverride("REPOSITORY_EXTENSIONS_EXTRA", config)
        if not StringTools.isEmpty(extraRepositoryExtensions):
            extraDirs = [x for x in extraRepositoryExtensions.split(os.pathsep) if not StringTools.isEmpty(x)]
            placesToLook.extend(extraDirs)
    placesToLook.append(extHome)

    if mstarpaths.runningFromRepository:
        # Web extension locations during development
        placesToLook.append(mstarpaths.interpretPathOverride("{REPOSITORY_MSTAR_HOME}/ext/Web", config));

        # The optional web extensions. These will be installed to runtime/target/extensions/Web if required.
        webExtensionsDir = mstarpaths.interpretPathOverride("{REPOSITORY_EXTENSIONS_HOME}/Web", config)
        if not os.path.exists(webExtensionsDir):

            print "NOTE: to support running from source, it is necessary to install some extensions. This may take a while ..."

            os.mkdir(webExtensionsDir)
            availableExtensionsDir = mstarpaths.interpretPathOverride("{REPOSITORY_EXTENSIONS_HOME}", config)
            for extension in findZippedExtensionsInDir(config, availableExtensionsDir):
                if extension.id.startswith("minestar-web"):
                    print "Installing web extension %s ..." % extension.id
                    __installZippedExtensionTo(extension, config, availableExtensionsDir)

        placesToLook.append(webExtensionsDir)

    # try to find desired or compulsory unzipped extensions in various places
    found = []
    for dir in placesToLook:
        extXmls = []
        findExtXmls(dir, extXmls)
        for exml in extXmls:
            (root, compulsory) = readRootFromExtensionXml(exml)
            if compulsory or root in neededExts:
                (fullPath,filename) = os.path.split(exml)
                if os.path.exists(fullPath) and root not in [ ext.root for ext in usedExtensions ]:
                    found.append(root)
                    ext = DirectoryExtension(root, fullPath)
                    usedExtensions.append(ext)
    for ext in usedExtensions:
        d = mstarpaths.simplifyPath("%s/../res" % ext.ufsDir)
        if os.path.exists(d):
            ext.extraUfsDir = mstarpaths.simplifyPath("%s/.." % ext.ufsDir)
        # Hack: Add ${project}/target/config/${ext.root}, if it exists. This will
        #       overwrite existing extraUfsDir (fix to come later)
        if mstarpaths.runningFromRepository and 'src' in ext.ufsDir:
            # e.g. fleetcommander/src/main/config/ext/Assignment/Assignment_Management -> fleetcommander/target/config/ext
            d = mstarpaths.simplifyPath("%s/../../../../../../target/config/ext/%s" % (ext.ufsDir, ext.root))
            if os.path.isdir(d):
                # TODO this may overwrite existing value.
                ext.extraUfsDir = d

    stillNeeded = [ root for root in neededExts if root not in found ]
    return stillNeeded

def findExtXmls(dir, putThemInHere):
    f = os.sep.join([dir, 'extension.xml'])
    if os.path.exists(f):
        putThemInHere.append(f)
    else:
        for f in os.listdir(dir):
            dirf = os.sep.join([dir, f])
            if os.path.isdir(dirf) and not f.startswith(".") and not f.startswith("sandbox"):
                findExtXmls(dirf, putThemInHere)

def __installZippedExtensions(mstarConfig, neededExts, usedExtensions):
    """
        mstarConfig is the partially created dictionary of MineStar properties.
        overrideExtensions is a path of zip files of extensions to use which have been specified on the command line.
        desiredExts is a list of directory names of extensions that the system is configured to load
    """
    allZippedExts = findZippedExtensions(mstarConfig)
    (zipExts, stillNeeded) = __determineRequiredExtensions(allZippedExts, neededExts)
    for zext in zipExts:
        if  zext.root not in [ ext.root for ext in usedExtensions ]:
            __installZippedExtension(zext, mstarConfig)
            usedExtensions.append(zext)
    return stillNeeded

def loadExtensions(sources, config):
    """
        sources is the sources of the configuration
        config is the configuration so far for the system being loaded
    """
    global patchFilesByID, parts
    patchFilesByID.clear()
    desiredExts = __getDesiredExtensions(config)
    stillNeeded = desiredExts[:]
    loadedExtensions = []
    stillNeeded = __installUnzippedExtensions(config, stillNeeded, loadedExtensions)
    stillNeeded = __installZippedExtensions(config, stillNeeded, loadedExtensions)
    usedZips = [zext.filename for zext in loadedExtensions if zext.__class__ == ZippedExtension]
    mstarHome = config["MSTAR_HOME"]
    mstarExt = DirectoryExtension("MineStar", mstarHome)
    loadedExtensions.append(mstarExt)
    for ext in loadedExtensions:
        if ext.part is not None:
            parts.append(ext.part)

    # preserve ordering in the desired list
    i = 0
    for des in desiredExts:
        i = i + 1
        matching = [ ext for ext in loadedExtensions if ext.root == des ]
        if len(matching) > 0:
            matching[0].sortOrder = matching[0].sortOrder + i / 1000.0
    loadedExtensions.sort(lambda e1, e2: cmp(e1.sortOrder, e2.sortOrder))
    # Now that we know all the extensions, install the related patches
    allPatches = findPatches(config)
    allPatches = [ p for p in allPatches if p.isEnabled(config) ]
    sp = getServicePack(config, mstarpaths.interpretPathOverride("{MSTAR_UPDATES}", config))
    drUFS = []
    if mstarpaths.runningFromRepository:
        drUFS = __getDevelopmentResourceDirs(config)
    (installedPatches, ufsPathDirs) = __installPatchesFor(config, allPatches, loadedExtensions, sp)
    ufsPathDirs = drUFS + ufsPathDirs
    for patch in allPatches:
        patch.infos = None
    usedZips = usedZips + [ patch.filename for patch in installedPatches ]
    __recordUsedZips(usedZips, config)
    # developer directories
    if not mstarpaths.runningFromRepository:
        devResDirs = __getDevelopmentResourceDirs(config)
        for ext in devResDirs:
            ufsPathDirs.append(ext)
    # the system extension
    ufsPathDirs.append(mstarpaths.interpretPathOverride("{MSTAR_CONFIG}", config))
    if os.environ.has_key("EXTRA_UFS_PATH"):
        ufsPathDirs.append(os.environ.get("EXTRA_UFS_PATH"))

    # set the UFS_PATH
    ufsPath = buildUFSPath(ufsPathDirs)
    sources["UFS_PATH"] = "(it's complicated)"
    config["UFS_PATH"] = ufsPath
    sources["LOADED_EXTENSIONS"] = "(it's complicated)"
    config["LOADED_EXTENSIONS"] = loadedExtensions
    mineStarVersion = getMineStarVersion(config)

def buildUFSPath(ufsPathDirs):
    """Create a ';' separated list of unique UFS path directories."""
    paths = []
    for p in ufsPathDirs:
        if type(p) == type(""):
            path = p
        elif len(p) == 1:
            path = p[0]
        else:
            path = "(%s)" % ";".join(p)
        # Add the path if it is unique.
        if path not in paths:
            paths.append(path)
    return ";".join(paths)

def getExtensionsForProduct(mstarConfig, product):
    allExtensionNames = __findAllExtensionNames(mstarConfig)
    start = product + "/"
    return [ e for e in allExtensionNames if e.startswith(start) ]

def verifyCommandLicense():
    import mstaroverrides, mstarrun
    (overridePairs, ovFile) = mstaroverrides.loadOverrides()
    versionOverrides = overridePairs.get("/Versions.properties", {})
    subSystems = versionOverrides.get("_SUBSYSTEMS", {})
    if 'Autonomy' in subSystems:
        print ("Verifying the Command License for Autonomy Extn...")
        mstarrun.run(["com.mincom.util.permission.privilege.CheckCommandLicense","COMMAND"])

def canonicaliseExtensionName(name):
    name = name.strip()
    name = "/".join(name.split("\\"))
    while name[0] == '/':
        name = name[1:]
    fields = name.split("/")
    fields = [ f for f in fields if f != "" ]
    name = "/".join(fields)
    return name

if __name__ == "__main__":
    mstarpaths.loadMineStarConfig()
    print __findAllExtensionNames(mstarpaths.config)
    print getExtensionsForProduct(mstarpaths.config, "Platform")
