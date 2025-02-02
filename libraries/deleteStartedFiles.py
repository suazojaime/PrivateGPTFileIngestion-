# An application to delete the file which indicates that an object server has started
import mstarpaths, sys, os
import minestar

logger = minestar.initApp()

needed = sys.argv[1:]
mstarpaths.loadMineStarConfig()
for x in needed:
    path = mstarpaths.interpretPath("{MSTAR_TEMP}/%s.started" % x)
    if os.access(path, os.F_OK):
        os.remove(path)
