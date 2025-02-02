#               new script to run org.hsqldb.ScriptTool to 'export' the data to a file.
#
#               Command format: mstarrun org.hsqldb.util.ScriptTool -url jdbc:hsqldb:hsql: 
#                                                                   -database cururentDBServer 
#                                                                   -user dbmonitor -password "DBMONITOR" 
#                                                                   -script st.sql > monitordb.bak

""" exportMonitorDB.py exportFile.name"""
import minestar
logger = minestar.initApp()
import mstarpaths, sys, mstarrun, mstarpaths, datastore, os, StringTools, ServerTools

def exportMonitorDB():
    mstarpaths.loadMineStarConfig()
    #
    # set up parameters for 'SHUTDOWN COMPACT' command
    #
    monitorDBDir = mstarpaths.interpretPath("{MSTAR_LOGS}") + os.sep + "monitoring"
    shutdownScript = monitorDBDir + os.sep + "st.sql"
    dbServer = "//" + ServerTools.getCurrentDatabaseServer()
    print "monitorDB export script is %s for dataabse on %s" % (shutdownScript, dbServer)
    mstarrun.run(["org.hsqldb.util.ScriptTool", "-database", dbServer, "-url", "jdbc:hsqldb:hsql:",
                  "-script", shutdownScript, ">", monitorDBDir + os.sep + "monitordb.bak"])
#
#
# Main Program:
#
if __name__ == "__main__":
    exportMonitorDB()
    sys.exit(0)

