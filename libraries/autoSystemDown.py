import minestar
import mstarapplib
import mstarpaths
import mstarrun
import time
import sys

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
# get the list of targets to be started, and reverse it
targets = mstarpaths.interpretVar("_START")
fields = targets.split(",")
backwards = []
print "Performing automatic thread dump before system shutdown"
mstarrun.run(["-b", "InvokeThreadDumps"])
for appName in fields:
    backwards = [appName] + backwards
for appName in backwards:
    config = mstarapplib.getApplicationDefinition(appName)
    if config.has_key("shutdown"):
        print "Stopping %s" % appName
        shutdown = mstarpaths.interpretPath(config["shutdown"])
        mstarrun.run(shutdown)
        # Give MineTracking some extra time to shutdown
        # MineTracking may hang during shutdown if FsbServer is shutdown first
        if appName == "MineTracking":
            print "Giving MineTracking some time to shutdown..."
            time.sleep(15)
            # if linux, kill Minetracking after 15 secs
            if not sys.platform.startswith('win'):
                minestar.killProcess(appName, 1)
                import os
                # kill minetracking via it's jmx port
                os.system('fuser -n tcp -k 9001')
    else:
        print "Don't know how to shutdown %s" % appName
