import minestar
__version__ = "$Revision: 1.3 $"

# Revision 1.0  2004/11/04 12:38:54  jerryz
#          Script to call com.mincom.env.base.os.monitor.MonitorSystem
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
    argumentsStr = "[U|H]"
    if len(sys.argv) > 1:
         runType = sys.argv[1]
    else:
         runType = "U"
    appConfig = {}
    appConfig["args"] = runType
    thisMachine = mstarpaths.interpretVar("COMPUTERNAME")
    if len(sys.argv) > 2:
        logFile = sys.argv[2]
    else:
        logFile = mstarpaths.interpretPath("{MSTAR_LOGS}/snapshotOs_" + thisMachine + "_" + runType + "_{HH}{NN}.log")

    # Process the arguments
    mstarrun.run(["com.mincom.env.base.os.monitor.MonitorSystem", runType, logFile])

    # Finalize and exit
    minestar.exit()


if __name__ == '__main__':
    """Entry point when called from Python"""
    mstarpaths.loadMineStarConfig()
    main()
