""" grabSnapshot.py script runs mstarrun targets grabDBsnapshot and grabOSSnapshot,
                    then runs JasperReport to create PDF report files. """

import mstarpaths, sys, mstarrun, minestar, mstarpaths, os

logger = minestar.initApp()

def grabSnap(mode):
    mstarpaths.loadMineStarConfig()

    mstarrun.run(["grabOSSnapshot", mstarpaths.interpretPath("{COMPUTERNAME}"), mstarpaths.interpretPath("{MSTAR_TOOLKIT}"), mstarpaths.interpretPath("{_DISK_VOLUMES}"), "3", "U"])
    mstarrun.run(["grabDBSnapshot", mstarpaths.interpretPath("{MSTAR_TOOLKIT}"), "model", "0.98", "U"])
    mstarrun.run(["grabDBSnapshot", mstarpaths.interpretPath("{MSTAR_TOOLKIT}"), "historical", "0.98", "U"])
    #
    # establish ZIP file target name in the format "Snap_<MODE:{AUTO|USER}>_<CUSTOMER_CODE>_<SYSTEM_NAME>_YYYYMMDD_HHMI.ZIP"
    #
    timestamp = mstarpaths.interpretFormat("{YYYY}{MM}{DD}_{HH}{NN}")
    custcode = mstarpaths.interpretPath("{_CUSTCODE}")
    ZIP_FILE = mstarpaths.interpretPath("{MSTAR_ADMIN}") + os.sep + "Snap_" + mode + "_" + custcode + "_" + timestamp + ".ZIP"
    print "grabSnapshot: ZIP File name is %s" % ZIP_FILE
    mstarrun.run(["zipSnapshot", mstarpaths.interpretPath("{MSTAR_SYSTEM_HOME}"), ZIP_FILE])

#
# Main Program:
#
if __name__ == "__main__":
    # Check usage
    if len(sys.argv) != 2:
        print "Usage: grabSnapshot.py MODE:[AUTO|USER]"
        print sys.argv
        sys.exit(12)
    grabSnap(sys.argv[1])
