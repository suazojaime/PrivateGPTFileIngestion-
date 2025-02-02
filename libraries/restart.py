import mstarpaths, os, mstarrun, minestar, mstarapplib, i18n, sys

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
# what app?
appName = sys.argv[1]
# shut it down
config = mstarapplib.getApplicationDefinition(appName)
if config.has_key("shutdown"):
    print i18n.translate("Stopping %s") % appName
    shutdown = mstarpaths.interpretPath(config["shutdown"])
    mstarrun.run(shutdown)
else:
    print i18n.translate("Don't know how to shutdown %s") % appName
# start
print i18n.translate("Starting %s") % appName
mstarrun.run(appName, { "newWindow" : 1 })
