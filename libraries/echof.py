import mstarpaths, sys, string
import minestar

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
for arg in sys.argv[1:]:
    print mstarpaths.interpretFormat(arg),
print
