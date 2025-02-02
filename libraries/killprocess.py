import minestar, sys, mstarpaths

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
force = 0
for proc in sys.argv[1:]:
    if proc == "--force":
        force = 1
    else:
        minestar.killProcess(proc, force)
