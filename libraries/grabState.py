import mstarpaths, sys, mstarrun, minestar

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
outputFile = "{MSTAR_TRACE}/State_{YYYY}{MM}{DD}_{HH}{NN}.ser"
timeConfig = minestar.getCurrentTimeConfig()
outputFile = mstarpaths.interpretPathOverride(outputFile, timeConfig)
outputFile = mstarpaths.interpretPath(outputFile)
print outputFile
mstarrun.run(["com.mincom.explorer.page.admin.ser.GrabSystemState", sys.argv[1], outputFile])
