import minestar, sys, mstarpaths

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
for proc in sys.argv[1:]:
    minestar.killProcess(proc, 1)
