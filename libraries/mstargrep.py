import mstarpaths, sys, glob
import minestar

logger = minestar.initApp()

if len(sys.argv) != 3:
    print "Usage: mstargrep filePattern linePattern"
    print sys.argv
    sys.exit(12)
filePattern = sys.argv[1]
linePattern = sys.argv[2]
filePattern = mstarpaths.interpretPath(filePattern)
for filename in glob.glob(filePattern):
    file = open(filename, "r")
    for line in file.readlines():
        if line.find(linePattern) >= 0:
            if line[-1] == '\n':
                line = line[:-1]
            print line
    file.close()
