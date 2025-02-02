import os, ufs, mstarpaths, sys, string
import minestar

logger = minestar.initApp()

args = sys.argv[1:]
mstarpaths.loadMineStarConfig()
root = ufs.getRoot(mstarpaths.interpretVar("UFS_PATH"))
if len(args) == 0:
    obj = root
else:
    obj = root.get(args[0])
if obj is None:
    print "No such path"
else:
    print "PATH: %s" % obj.getPath()
    if obj.isADirectory():
        print "PHYSICAL: %s" % str(obj.getPhysicalDirectories())
        subdirs = obj.listSubdirNames()
        for subdir in subdirs:
            print string.ljust(str(subdir), 40) + "<directory>"
        files = obj.listFiles()
        for file in files:
            print string.ljust(file.getName(), 40) + `file.getAllPhysicalFiles()`
    else:
        print "PHYSICAL: %s" % obj.getPhysicalFile()
        print "ALL: %s" % `obj.getAllPhysicalFiles()`
