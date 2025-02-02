import mstarpaths
import minestar

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
for (key, value) in mstarpaths.config.items():
    print "set %s=%s" % (key, value)
import timeSettings
