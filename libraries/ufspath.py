import mstarpaths, os
import minestar

logger = minestar.initApp()

def main(args):
    ufspath = mstarpaths.interpretVar("UFS_PATH")
    dirs = ufspath.split(";")
    for d in dirs:
        print d
