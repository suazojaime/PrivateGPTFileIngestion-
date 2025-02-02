import os, minestar

class UfsException:
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return "UfsException[%s]" % self.message

class UfsObject:
    pass

class UfsFile(UfsObject):
    def __init__(self, parent, name, physicalFile):
        if physicalFile is None:
            raise UfsException("physicalFile may not be None")
        self.parent = parent
        self.name = name
        self.physicalFile = physicalFile

    def __str__(self):
        return "UfsFile[%s/%s: %s]" % (self.parent.getName(), self.name, self.physicalFile)

    def getPhysicalFileName(self):
        return self.physicalFile

    def getName(self):
        return self.name

    def getParent(self):
        return self.parent

    def getAllPhysicalFiles(self):
        return self.parent._getAllPhysicalFiles(self.name)

    def isADirectory(self):
        return 0

    def isAFile(self):
        return 1

    def getPhysicalFile(self):
        "Return a string which is the absolute path name"
        return self.physicalFile

    def getPath(self):
        return self.parent.getPath() + "/" + self.name

    def getTextContent(self):
        "Semantics of text files is that all physical files get concatenated"
        files = self.getAllPhysicalFiles()
        files.reverse()
        content = ""
        for file in files:
            content = content + open(file).read() + "\n"
        return content

    def getTextLines(self):
        "Semantics of text files is that all physical files get concatenated"
        files = self.getAllPhysicalFiles()
        files.reverse()
        lines = []
        for file in files:
            lines = lines + open(file).readlines()
        lines = [ minestar.stripEol(line) for line in lines ]
        return lines

    def loadMapAndSources(self):
        return self.loadJavaStyleProperties([])

    def loadJavaStyleProperties(self, filenames):
        """
            Load properties from a file exactly as for a Java properties file,
            except that we also interpret #includes as for the C preprocessor.
        """
        files = self.getAllPhysicalFiles()
        result = {}
        sources = {}
        for file in files:
            lines = open(file).readlines()
            lines = minestar.cleanLines(lines)
            for line in lines:
                if line.startswith("#include "):
                    newFileName = minestar.stripPunctuation(line[9:].strip())
                    newFile = self.getParent().get(newFileName)
                    if newFile.getPath() not in filenames:
                        (newSources, newResult) = newFile.loadJavaStyleProperties(filenames)
                        filenames.append(newFile.getPath())
                        for (key, value) in newResult.items():
                            result[key] = value
                            sources[key] = newSources[key]
                else:
                    (key, value) = minestar.parseJavaStylePropertyLine(line)
                    result[key] = value
                    sources[key] = file
        return (sources, result)

class UfsDirectory(UfsObject):
    def __init__(self, ufsPath, pathToHere, name, parent):
        self.name = name
        self.ufsPath = ufsPath
        self.parent = parent
        self.pathToHere = pathToHere
        # self.dirs is a list of directory names (strings) in Python
        self.dirs = self.ufsPath._locatePhysicalDirectories(self.pathToHere)
        if len(self.dirs) == 0:
            raise UfsException("No physical directories")
        self.revdirs = self.dirs[:]
        self.revdirs.reverse()

    def exists(self):
        return len(self.dirs) > 0

    def getSubdir(self, name):
        if os.pardir == name:
            return self.parent
        return UfsDirectory(self.ufsPath, self.pathToHere + os.sep + name, name, self)

    def getName(self):
        return self.name

    def __str__(self):
        return "UfsDirectory[%s: %s]" % (self.name, str(self.dirs))

    def __getExpectedFile(self, filename):
        return self.ufsPath.getExpectedFile(filename, self.pathToHere)

    def getFile(self, filename):
        "Get a file from the directory. Result is a UfsFile object."
        f = self.__getExpectedFile(filename)
        if f is None or minestar.isDirectory(f):
            return None
        else:
            return UfsFile(self, filename, f)

    def listFileNames(self):
        "Return a sorted list of names of files in the directory. Result is a list of strings."
        filenames = []
        for d in self.dirs:
            for f in os.listdir(d):
                pathname = d + os.sep + f
                if not minestar.isDirectory(pathname) and not f.startswith('.'):
                    if f not in filenames:
                        filenames.append(f)
        filenames.sort()
        return filenames

    def listSubdirNames(self):
        "Return a sorted list of names of subdirectories in the directory. Result is a list of strings."
        filenames = []
        for d in self.dirs:
            for f in os.listdir(d):
                pathname = d + os.sep + f
                if minestar.isDirectory(pathname) and f != 'CVS' and not f.startswith('.'):
                    if f not in filenames:
                        filenames.append(f)
        filenames.sort()
        return filenames

    def listFiles(self):
        "Return a sorted list of files in the directory. Result is a list of UfsFiles."
        return [ self.getFile(name) for name in self.listFileNames() ]

    def listSubdirs(self):
        "Return a sorted list of subdirectories in the directory. Result is a list of UfsDirectories."
        return [ self.getSubdir(name) for name in self.listSubdirNames() ]

    def _getAllPhysicalFiles(self, name):
        "Return the absolute physical path names of all physical files in this directory with the given name."
        return self.ufsPath.getAllPhysicalFiles(name, self.pathToHere)

    def get(self, path):
        path = path.strip()
        path = os.sep.join(path.split('/'))
        path = os.sep.join(path.split('\\'))
        fields = path.split(os.sep)
        if len(fields) > 0 and fields[0] == "":
            fields = fields[1:]
        if len(fields) == 0 or (len(fields) == 1 and fields[0] == ""):
            return self
        if "" in fields:
            raise UfsException("empty element in path")
        d = self
        for field in fields[:-1]:
            try:
                d = d.getSubdir(field)
            except UfsException:
                return None
        parent = d
        d = parent.getFile(fields[-1])
        if d is None:
            try:
                d = parent.getSubdir(fields[-1])
            except UfsException:
                d = None
        return d


    def getParent(self):
        return self.parent

    def isADirectory(self):
        return 1

    def isAFile(self):
        return 0

    def getPath(self):
        if self.parent is None:
            return ""
        else:
            return self.parent.getPath() + "/" + self.name

    def getPhysicalDirectories(self):
        "Return physical directories in path order"
        return self.dirs[:]

def getRoot(ufsPath):
    if ufsPath is None:
        raise RuntimeError("ufsPath may not be None")
    return UfsDirectory(UFSPath(ufsPath), "", "", None)

def parseUFSPath(path):
    exts = []
    while 1:
        path = path.strip()
        if len(path) == 0:
            break
        elif path.startswith("("):
            (first, rest) = path.split(")", 1)
            exts.append(first[1:])
            path = rest.strip()
            if path.startswith(";"):
                path = path[1:]
        elif path.find(";") >= 0:
            (first, rest) = path.split(";", 1)
            exts.append(first)
            path = rest
        else:
            exts.append(path)
            break
    return exts

def parseExt(path):
    exts = []
    while 1:
        path = path.strip()
        if len(path) == 0:
            break
        elif path.find(";") >= 0:
            (first, rest) = path.split(";", 1)
            exts.append(first)
            path = rest
        else:
            exts.append(path)
            break
    return exts

def _joinPath(base, sub1=None, sub2=None):
    if sub1 and sub1[0] in ["/", "\\"]:
        sub1 = sub1[1:]
    if sub2 and sub2[0] in ["/", "\\"]:
        sub2 = sub2[1:]
    if sub2 is None:
        return os.path.join(base, sub1)
    else:
        return os.path.join(base, sub1, sub2)

class UFSPath:
    "A class representing the complete UFS path"

    def __init__(self, path):
        self.extensions = [ UFSExtension(ext) for ext in parseUFSPath(path)]

    def __str__(self):
        return "[%s]" % ",".join([str(ext) for ext in self.extensions])

    def _locatePhysicalDirectories(self, logicalDirectory):
        "Return the physical directories corresponding to the logical directory"
        files = []
        for ext in self.extensions:
            files = files + ext.getPhysicalDirectories(logicalDirectory)
        return files

    def getExtensions(self):
        return self.extensions[:]

    def getExpectedFile(self, filename, subdir):
        es = self.getExtensions()
        es.reverse()
        for e in es:
            f = e.getExpectedFile(filename, subdir)
            if f is not None:
                return f
        return None

    def listFileNames(filter, subdir):
        result = []
        for e in self.extensions:
            fromE = e.listFileNames(filter, subdir)
            result = result + fromE
        return result

    def listSubdirNames(self, subdir):
        result = []
        for e in self.extensions:
            fromE = e.listSubdirNames(subdir)
            result = result + fromE
        return result

    def getAllPhysicalFiles(self, name, subdir):
        result = []
        for e in self.extensions:
            fromE = e.getExpectedFile(name, subdir)
            if fromE is not None:
                result.append(fromE)
        return result

    def getPhysicalDirectories(self, subdir):
        result = []
        for e in self.extensions:
            fromE = e.getPhysicalDirectories(subdir)
            result = result + fromE
        return result

class UFSExtension:
    "A class representing a UFS extension"

    def __init__(self, path):
        self.directories = parseExt(path)
        self.name = None
        # infer extension name
        dir = self.directories[0]
        ancestor = os.path.dirname(dir)
        if ancestor == '' or ancestor == os.sep:
            ancestor = None
        while ancestor is not None:
            if os.path.basename(ancestor) == "ext":
                self.name = dir[len(ancestor)+1:]
                break
            old = ancestor
            ancestor = os.path.dirname(ancestor)
            if ancestor == '' or ancestor == os.sep or old == ancestor:
                ancestor = None
        if self.name is None:
            self.name = self.directories[0]

    def __str__(self):
        return "[%s]" % ",".join(self.directories)

    def getPhysicalExtensionDirectory(self):
        return self.directories[0]

    def getDirectories(self):
        return self.directories[:]

    def getExpectedFile(self, filename, subdir):
        ds = self.directories[:]
        ds.reverse()
        for d in ds:
            f = _joinPath(d, subdir, filename)
            if os.access(f, os.F_OK):
                return f
        return None

    def listFileNames(self, filter, subdir):
        result = []
        for d in self.directories:
            sd = _joinPath(d, subdir)
            if not os.access(sd, os.F_OK):
                continue
            files = os.listdir(sd)
            for f in files:
                absf = os.sep.join(sd, f)
                if f.startswith('.') or os.path.isdir(absf):
                    continue
                if filter is None or filter.match(f):
                    result.append(absf)
        return result

    def listSubdirNames(self, subdir):
        result = []
        for d in self.directories:
            sd = _joinPath(d, subdir)
            if not os.access(sd, os.F_OK):
                continue
            files = os.listdir(sd)
            for f in files:
                absf = os.sep.join(sd, f)
                if f.startswith('.') or f == 'CVS':
                    continue
                if os.path.isdir(absf):
                    result.append(absf)
        return result

    def getPhysicalDirectories(self, subdir):
        result = []
        for d in self.directories:
            maybeDir = _joinPath(d, subdir)
            if os.access(maybeDir, os.F_OK) and os.path.isdir(maybeDir):
                result.append(maybeDir)
        return result

if __name__ == "__main__":
    import mstarpaths, ufs
    mstarpaths.loadMineStarConfig()
    ufsPath = mstarpaths.interpretVar("UFS_PATH")
    print ufsPath
    ufsRoot = ufs.getRoot(ufsPath)
    f = ufsRoot.get("/res/com/mincom/works/page/bev/Config.properties")
    print f.getAllPhysicalFiles()
    # print f.getTextContent()
