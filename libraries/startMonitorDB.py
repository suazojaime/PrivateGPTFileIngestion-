""" startMonitorDB.py script runs mstarrun targets startSnapshotDb"""

import mstarpaths, sys, mstarrun, minestar, mstarpaths, os, StringTools

logger = minestar.initApp()

def startMonitorDB():
    mstarpaths.loadMineStarConfig()
    #
    # set up parameters for start of org.hsqldb.Server
    #
    monitorDBDir = mstarpaths.interpretPath("{MSTAR_LOGS}") + os.sep + "monitoring"
    monitorDBName = monitorDBDir + os.sep + "monitordb"
    print "Starting up hsqldb database %s..." % monitorDBName
    mstarrun.run(["-w", "org.hsqldb.Server",  "-database", monitorDBName])
#
#
# Main Program:
#
if __name__ == "__main__":
    startMonitorDB()
    sys.exit(0)

