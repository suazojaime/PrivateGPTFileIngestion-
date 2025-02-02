# An application to turn mstarrun debugging on or off
import mstarpaths, sys
from i18n import translate
import minestar

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
filename = mstarpaths.interpretPath("{MSTAR_HOME}/bus/pythonlib/mstardebug.py")
args = sys.argv[1:]
if len(args) > 0:
    command = args[0]
    if translate('on') == command:
        file = open(filename, "w")
        file.write("debug = 1\n")
        file.close()
    elif translate('off') == command:
        file = open(filename, "w")
        file.write("debug = 0\n")
        file.close()
    else:
        print "Unknown parameter: use 'debug %s' or 'debug %s'" % (translate("on"), translate("off"))
# mstardebug is probably already loaded, so get rid of it to force reloading from the new file
del sys.modules["mstardebug"]
import mstardebug
if mstardebug.debug:
    print translate("debug is %s") % translate("on")
else:
    print translate("debug is %s") % translate("off")
