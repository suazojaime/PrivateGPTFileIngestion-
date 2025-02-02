import mstarrun, sys, minestar

logger = minestar.initApp()

if sys.platform.startswith("win"):
    mstarrun.run("windowsServices update")
    mstarrun.run("makeShortcuts all")
