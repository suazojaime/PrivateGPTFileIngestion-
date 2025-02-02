import sys, glob, os, mstarpaths, datastore, createTraceReport
from string import *

""" runSqlTrace.py: This scripts controls the running of Sql trace in current sessions.
                    The connection is identitied by the MSTAR_DATABASE parameter for 
                    which the information is retrieved from Minestar.Properties using
                    the datastore.py library. ORACLE_ADMIN_PATH specifies the root of
                    the Oracle\Admin directory where TRC Trace files will be generated.
                    The third parameter specifies either 'ALL' programs or a specific
                    program name to be traced eg. 'BUSOBJ.EXE'. 
                    This script calls Run_Start_Trace.SQL and Run_Stop_Trace.SQL stored
                    in directtory specified by the ORACLE_UTILITY constant.
                    Once Tracing is stopped script createTraceReport.py is called for 
                    each new trace file found to create a formatted report.
     - Parameter 1: MSTAR_DATABASE eg. _MODELDB or _HISTORICALDB etc..
     - Parameter 2: ORACLE_ADMIN_PATH eg. 'X:\Oracle\Admin'
     - Parameter 3: TRACE_WHAT eg. 'ALL' or 'BUSOBJ.EXE'
"""
#
# Version 2: Provide a _DATABASE parameter to find in Minestar.Properties file:
#
if len(sys.argv) != 4:
    print "Usage: RunSQLTrace.py MSTAR_DATABASE ORACLE_ADMIN_PATH ALL|PROGRAM"
    print sys.argv
    sys.exit(12)
#
# Initialize parameters and Constants
#
mstarpaths.loadMineStarConfig()
mstarpaths.setEnvironment()
mstar_db = sys.argv[1]
oracle_admin = sys.argv[2]
if sys.argv[3] == 'ALL':
    trace_what = '%'
else:
    trace_what = sys.argv[3]
myDS = []
myDS = datastore.getDataStore(mstar_db)
if myDS != None:
    print "Performing SQL Trace on DataStore %s" % (myDS.linkName)
    (mstar_user, mstar_instance, mstar_machine) = (myDS.linkName).split('_')
else:
    print "Database %s cannot be found in MineStar.Propoerties!" % mstar_db
    sys.exit(12)
#
SQLPLUS = 'sqlplus.exe'
ORACLE_UTILITY = mstarpaths.interpretPath("{MSTAR_DATABASE}/oracle/Schemautilities")
#
# Setup path to Oracle\Admin\{DB_INSTANCE\udump directory
#
SQL_Trace_Path = oracle_admin + '\\' + mstar_instance + '\\udump'
#
# Get a listing of existing .TRC files as NOT to process these later
# If directory is invalid print out message and exit!
#
try:
    os.chdir(SQL_Trace_Path)
except:
    print "Invalid SQL Trace file directory %s determined from ORACLE_ADMIN parameter %s!" % \
          (SQL_Trace_Path, oracle_admin)
    print " NO SQL Trace run, check ORACLE_ADMIN parameter and try again!"
    sys.exit(12)
#
oldTraceFiles = os.listdir('.')
#
# Run SqlPlus script to set SQL Trace in ALL MSTAR_USER sessions:
#
os.chdir(mstarpaths.interpretPath(ORACLE_UTILITY))
start_trace_cmd = SQLPLUS +' '+mstarpaths.interpretVar("_DB_ADMIN_USER")+ '/'+mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")+'@' + mstar_instance + '_' + mstar_machine + \
                  ' @Run_Start_Trace ' + mstar_user + ' ' + trace_what
print start_trace_cmd
os.system(start_trace_cmd)
#
# Display message to prompt user to press any key to stop trace
print "\n\n SQL Trace is running, press <CTRL>Z and <ENTER> to stop SQL Trace:"

dummy = sys.stdin.read()

stop_trace_cmd = SQLPLUS +' '+mstarpaths.interpretVar("_DB_ADMIN_USER")+ '/'+mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")+'@' + mstar_instance + '_' + mstar_machine + \
                 ' @Run_Stop_Trace ' + mstar_user + ' ' + trace_what
print stop_trace_cmd
os.system(stop_trace_cmd)

print "\n\nFinished Tracing, now creating TKPROF Trace Report Files\n"

os.chdir(SQL_Trace_Path)

newFiles = os.listdir('.')
for Trace_File in newFiles:
    if Trace_File not in oldTraceFiles:
        createTraceReport.RunTraceReport(Trace_File, mstar_user, mstar_instance, mstar_machine)
