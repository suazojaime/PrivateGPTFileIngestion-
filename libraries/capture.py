# Python program to run another program and capture the output in a file
# The first arg is the pattern for the file to be captured to,
# and remaining args are the command line to be executed.
#
# author John Farrell

import mstarpaths, string, minestar, os, sys

logger = minestar.initApp()

# this program is not run directly by mstarrun, so it has to do this
# sort of stuff itself.
os.environ["MSTAR_HOME"] = minestar.guessMstarHomeFromExecutable()
mstarpaths.loadMineStarConfig()
mstarpaths.setEnvironment()
# finished setting up, now to run the command
if len(sys.argv) == 1:
    print "Nothing to do"
else:
    filename = sys.argv[1]
    args = sys.argv[2:]
    for i in range(len(args)):
        if args[i].startswith("-D"):
            args[i] = '"%s"' % args[i]
    cmd = string.join(args)
    minestar.runAndSaveOutput(cmd, filename)
