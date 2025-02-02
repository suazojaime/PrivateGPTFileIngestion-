# An application to tell you what the valid commands
# in the application registry are, this is used for bash auto complete
import minestar
import mstarapplib
import mstarpaths

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
keys = mstarapplib.findAllTargets()
for key in keys:
    print key



