import os, sys, zipfile, string, shutil, stat
"""
This program can't import any MineStar python, because Windows doesn't allow the directory
to be renamed while those files are in use. Hence, this is a standalone program.
"""

COPY_COMMAND = "copy %s %s"
if not sys.platform.startswith("win32"):
    COPY_COMMAND = "cp %s %s"

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

def copy(src, dest):
    "Copy src file to dest file."
    makeDirsFor(dest)
    if not sys.platform.startswith("win32"):
        src = string.replace(src, "$", "\\$")
        dest = string.replace(dest, "$", "\\$")
    cp = COPY_COMMAND % (src, dest)
    print cp
    os.system(cp)

def platformPath(path):
    path = string.replace(path, "\\", "/")
    parts = path.split("/")
    return string.join(parts, os.sep)

def unpack(zipf, zipDir):
    "Unpack the files in the ZipFile zip to zipDir"
    for info in zipf.infolist():
        fullFileName = zipDir + os.sep + platformPath(info.filename)
        makeDirsFor(fullFileName)
        if not os.path.isdir(fullFileName):
            file = open(fullFileName, "wb")
            file.write(zipf.read(info.filename))
            file.close()
            sys.stdout.write(".")
    print

def copyByPath(src, dest):
    filename = src[-1]
    src = string.join(src, os.sep)
    if type(dest) == type([]):
        dest = string.join(dest, os.sep)
    overwrite = dest + os.sep + filename
    if os.access(overwrite, os.F_OK):
        # we would overwrite a file
        backup = dest + os.sep + filename + ".original"
        copy(overwrite, backup)
    copy(src, overwrite)

def copyTree(src, dest):
    srcDir = string.join(src, os.sep)
    destDir = string.join(dest, os.sep)
    if os.access(srcDir, os.F_OK):
        if os.access(destDir, os.F_OK):
            shutil.rmtree(destDir, 1)
        shutil.copytree(srcDir, destDir)

def copyBundledStuff(src, dest):
    srcJDK = src + os.sep + "jdk"
    destJDK = dest + os.sep + "jdk"
    if os.access(srcJDK, os.F_OK) and not os.access(destJDK, os.F_OK):
        print "Copying bundled JDK"
        copyTree([src, "jdk"], [dest, "jdk"])
    srcPython = src + os.sep + "python"
    destPython = dest + os.sep + "python"
    if os.access(srcPython, os.F_OK) and not os.access(destPython, os.F_OK):
        print "Copying bundled Python"
        copyTree([src, "python"], [dest, "python"])

def isDirectory(pathName):
    "Return whether the path is a directory"
    import os, stat
    return os.access(pathName, os.F_OK) and stat.S_ISDIR(os.stat(pathName)[stat.ST_MODE])

def rmdir(directory):
    "Recursively delete a directory and its contents."
    import os
    if os.access(directory, os.F_OK):
        for f in os.listdir(directory):
            path = "%s%s%s" % (directory, os.sep, f)
            if isDirectory(path):
                rmdir(path)
            else:
                os.remove(path)
        os.rmdir(directory)

NOT_REAL_SYSTEMS = ["CVS"]
SYSTEM_DIRS_TO_DELETE = ["logs", "tmp", "trace", "patches", "shortcuts"]

def copySystemsConfigs(mstarOld, mstarNew):
    # need to copy across the MSTAR_FILES setting
    copyByPath([mstarOld, "LICENSE.key"], [mstarNew])
    systemsDir = mstarOld + os.sep + "systems"
    if not os.access(systemsDir, os.F_OK):
        # systems don't live under the mstar directory
        return
    mstarrunBatch = string.join([mstar, "bus", "bin", "mstarrun.bat"], os.sep)
    for file in os.listdir(systemsDir):
        sysDir = systemsDir + os.sep + file
        if stat.S_ISDIR(os.stat(sysDir).st_mode):
            if file not in NOT_REAL_SYSTEMS:
                # make the system directory in the new area if it does not already exist
                newSysDir = mstarNew + os.sep + "systems" + os.sep + file
                try:
                    os.makedirs(newSysDir)
                except OSError:
                    # already exists
                    pass
                for d in SYSTEM_DIRS_TO_DELETE:
                    rmdir(os.sep.join([newSysDir, d]))
                print "System %s: copying config settings" % file
                copyTree([mstarOld, "systems", file, "config"], [mstarNew, "systems", file, "config"])
                print "System %s: copying Minestar.directories" % file
                copyByPath([mstarOld, "systems", file, "MineStar.directories"], [mstarNew, "systems", file])
                print "System %s: applying system options" % file
                os.system(string.join([mstarrunBatch, "-s", file, "applySystemOptions"]))
                os.system(string.join([mstarrunBatch, "-s", file, "makeCatalogs all"]))

# Note: script cannot use MineStar libraries so next routine copied from minestar.py ...
def readLines(filename):
    "Return all non-blank, non-comment lines from the file"
    import string
    lines = []
    for line in open(filename).readlines():
        line = string.strip(line)
        if len(line) > 0 and line[-1] == '\n':
            line = line[:-1]
        if len(line) == 0:
            continue
        if line[0] == '#' and not line.startswith("#include"):
            continue
        lines.append(line)
    return lines

WIN_REGISTRATION_CMD = "C:\WINNT\system32\regsvr32 /s %s"

def registerWindowsComponents(dir):
    if not sys.platform.startswith("win"):
        return
    listPath = dir + os.sep + "register.lst"
    if not os.access(listPath, os.F_OK):
        return
    print "Registering Windows components in %s" % dir
    for file in readLines(listPath):
        fullPath = dir + os.sep + file
        system(WIN_REGISTRATION_CMD % fullPath)

mstar = "mstar"
if not os.access(mstar, os.F_OK):
    print "You must run this script in the directory containing '%s'" % mstar
    sys.exit(1)
args = sys.argv[1:]
if len(args) < 1:
    print "Usage: upgrade <zipfile> [quick]"
    sys.exit(2)
newzip = args[0]
quick = (len(args) > 1)
if not os.access(newzip, os.R_OK):
    print "Can't read file %s" % newzip
    sys.exit(4)
os.chdir(mstar)
newzip = os.pardir + os.sep + args[0]
newdir = args[0][:-4]
rmdir(newdir)
os.mkdir(newdir)
zipf = zipfile.ZipFile(newzip)
print "Unzipping new build (%d files)" % len(zipf.namelist())
unpack(zipf, newdir)
# hack the MineStar.ini file
f = file("MineStar.ini", "w")
f.write("[MineStar]\nbuild = %s\n" % newdir[5:])
f.close()
# Copy across the setup changes
os.system("mstarrun -s main revertBuild")
if not quick:
     os.system("mstarrun makeDataStores all")
