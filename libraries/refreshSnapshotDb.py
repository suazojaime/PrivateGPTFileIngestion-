""" refreshSnapshotDb.py script runs deleteSnapshots restartSnapshotDb"""

import mstarpaths, sys, mstarrun, minestar, mstarpaths, os, StringTools

logger = minestar.initApp()

def refreshSnapshotDb():
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
    # export the MonitorDB data:
    mstarrun.run(["exportSnapshotDb"])
    # stop SnapshotDb
    mstarrun.run(["stopSnapshotDb"])
    # start MonitorDB
    mstarrun.run(["startSnapshotDb"])
#
#
# Main Program:
#
if __name__ == "__main__":
    refreshSnapshotDb()
    sys.exit(0)

