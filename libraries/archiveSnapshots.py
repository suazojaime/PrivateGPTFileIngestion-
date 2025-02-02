""" archiveSnapshots.py script runs deleteSnapshots restartSnapshotDb"""

import mstarpaths, sys, mstarrun, minestar, mstarpaths, os, StringTools

logger = minestar.initApp()

def archiveSnapshots():
    mstarpaths.loadMineStarConfig()
    #
    # Run the Delete snapshots process
    #
    retainHourly = mstarpaths.interpretVar("_RETAIN_HOURLY_SNAPSHOTS")
    retainDaily = mstarpaths.interpretVar("_RETAIN_DAILY_SNAPSHOTS")
    retainWeekly = mstarpaths.interpretVar("_RETAIN_WEEKLY_SNAPSHOTS")
    retainUSER = mstarpaths.interpretVar("_RETAIN_USER_SNAPSHOTS")
    print "Running DeleteMonitorSnapshot monitorDB %s %s %s %s !" % (retainHourly, retainDaily, retainWeekly, retainWeekly)
    mstarrun.run(["com.mincom.env.base.os.monitor.DeleteMonitorSnapshot", "monitorDB", retainHourly, retainDaily, retainWeekly, retainWeekly])
    #
    # set up parameters for 'SHUTDOWN COMPACT' command
    #
    monitorDBDir = mstarpaths.interpretPath("{MSTAR_LOGS}") + os.sep + "monitoring"
    shutdownScript = monitorDBDir + os.sep + "shutdown_compact.sql"
    print "monitorDB shutdown script is %s" % shutdownScript
    mstarrun.run(["org.hsqldb.util.ScriptTool", "-database", "//localhost", "-url", "jdbc:hsqldb:hsql:", "-script", shutdownScript])
    #
    # set up parameters for start of org.hsqldb.Server
    #
    monitorDBName = monitorDBDir + os.sep + "monitordb"
    print "Starting up hsqldb database %s..." % monitorDBName
    mstarrun.run(["-w", "org.hsqldb.Server",  "-database", monitorDBName])
#
#
# Main Program:
#
if __name__ == "__main__":
    archiveSnapshots()
    sys.exit(0)

