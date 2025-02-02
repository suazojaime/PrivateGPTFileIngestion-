import mstarpaths, mstaroverrides, sys
import minestar

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
args = sys.argv[1:]
(overrides, overridesFile) = mstaroverrides.loadOverrides()
# for (filename, fileOverrides) in overrides.items():
#     print filename
#     for (key, value) in fileOverrides.items():
#         print "    %s = %s" % (str(key), str(value))
print "Initially:"
print "    _MODELDB is %s" % mstarpaths.interpretFormat("{_MODELDB}")
print "    _HISTORICALDB is %s" % mstarpaths.interpretFormat("{_HISTORICALDB}")
print "    _TEMPLATEDB is %s" % mstarpaths.interpretFormat("{_TEMPLATEDB}")
print "    _REPORTINGDB is %s" % mstarpaths.interpretFormat("{_REPORTINGDB}")
print "    _SUMMARYDB is %s" % mstarpaths.interpretFormat("{_SUMMARYDB}")
if len(args) > 0:
    overrides["/MineStar.properties"]["_INSTANCE1"] = args[0]
    if len(args) > 1:
        overrides["/MineStar.properties"]["_INSTANCE2"] = args[1]
        overrides["/MineStar.properties"]["_INSTANCE3"] = args[1]
    else:
        overrides["/MineStar.properties"]["_INSTANCE2"] = args[0]
        overrides["/MineStar.properties"]["_INSTANCE3"] = args[0]
    mstaroverrides.saveOverrides(overrides)
mstarpaths.loadMineStarConfig(forceReload=1)
print "Now:"
print "    _MODELDB is %s" % mstarpaths.interpretFormat("{_MODELDB}")
print "    _HISTORICALDB is %s" % mstarpaths.interpretFormat("{_HISTORICALDB}")
print "    _TEMPLATEDB is %s" % mstarpaths.interpretFormat("{_TEMPLATEDB}")
print "    _REPORTINGDB is %s" % mstarpaths.interpretFormat("{_REPORTINGDB}")
print "    _SUMMARYDB is %s" % mstarpaths.interpretFormat("{_SUMMARYDB}")
