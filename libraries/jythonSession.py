import mstarpaths, sys, mstarrun
import minestar

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
script = mstarpaths.interpretPath("{MSTAR_HOME}/bus/jythonlib/connectBus.py")
mstarrun.run(["org.python.util.jython", "-DbusUrl=%s" % sys.argv[1], "-i", script])
