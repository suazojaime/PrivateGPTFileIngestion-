""" stopMonitorDB.py script runs stopSnapshotDb"""

import mstarpaths, sys, mstarrun, minestar, mstarpaths, os, StringTools, ServerTools

logger = minestar.initApp()

def stopMonitorDB():
    mstarpaths.loadMineStarConfig()
    #
    # set up parameters for 'SHUTDOWN COMPACT' command
    #
    monitorDBDir = mstarpaths.interpretPath("{MSTAR_LOGS}") + os.sep + "monitoring"
    shutdownScript = monitorDBDir + os.sep + "shutdown_compact.sql"
    dbServer = "//" + ServerTools.getCurrentDatabaseServer()
    print "monitorDB shutting down MonitorDb on server %s, script is %s" % (dbServer, shutdownScript)
    mstarrun.run(["org.hsqldb.util.ScriptTool", "-database", dbServer, "-url", "jdbc:hsqldb:hsql:", "-script", shutdownScript])
#
#
# Main Program:
#
if __name__ == "__main__":
    stopMonitorDB()
    sys.exit(0)

