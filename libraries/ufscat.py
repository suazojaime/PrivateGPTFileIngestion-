import os, ufs, mstarpaths, sys, string
import minestar

logger = minestar.initApp()

args = sys.argv[1:]
mstarpaths.loadMineStarConfig()
root = ufs.getRoot(mstarpaths.interpretVar("UFS_PATH"))
obj = root.get(args[0])
if obj is None:
    print "%s does not exist" % args[0]
else:
    print str(obj)
    if obj.isADirectory():
        print "%s is a directory" % obj.getPath()
    else:
        print obj.getTextContent()
