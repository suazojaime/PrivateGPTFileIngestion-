import minestar
__version__ = "$Revision: 1.1 $"

#          Script to call com.mincom.env.base.os.monitor.MonitorDB
#          supplying the name of the output file

logger = minestar.initApp()
import datastore, mstarpaths, sys, mstarrun, os

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """Entry point when called from mstarrun"""
    import string
    # Process options and check usage
    optionDefns = [make_option("-s", "--sss", help="Specify a system")]
    argumentsStr = "[model|historical]"
    targetDb = sys.argv[1]
    if len(sys.argv) > 2:
         runType = sys.argv[2]
    else:
         runType = "U"
    appConfig = {}
    appConfig["args"] = [targetDb, runType]
    thisMachine = mstarpaths.interpretVar("COMPUTERNAME")
    if len(sys.argv) > 3:
        logFile = sys.argv[3]
    else:
        logFile = mstarpaths.interpretPath("{MSTAR_LOGS}/snapshotDb_" + thisMachine + "_" + runType + "_" + targetDb + "_{HH}{NN}.log")

    # Process the arguments
    mstarrun.run(["com.mincom.env.base.os.monitor.MonitorDB", targetDb, runType, logFile])

    # Finalize and exit
    minestar.exit()


if __name__ == '__main__':
    """Entry point when called from Python"""
    mstarpaths.loadMineStarConfig()
    main()
