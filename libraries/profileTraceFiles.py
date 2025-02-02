import sys, glob, os, mstarpaths, datastore, createTraceReport
from string import *

""" profileTraceFiles.py: This scripts controls the running of TKPROF for files in a given directory.
                    The connection is identitied by the MSTAR_DATABASE parameter for 
                    which the information is retrieved from Minestar.Properties using
                    the datastore.py library. ORACLE_ADMIN_PATH specifies the root of
                    the Oracle\Admin directory where TRC Trace files will be generated.
     - Parameter 1: MSTAR_DATABASE eg. _MODELDB or _HISTORICALDB etc..
     - Parameter 2: ORACLE_ADMIN_PATH eg. 'X:\Oracle\Admin'
     - Parameter 3: TRACE_SIBDIR eg. '200409141100'
"""
#
# Version 2: Provide a _DATABASE parameter to find in Minestar.Properties file:
#
if len(sys.argv) != 4:
    print "Usage: profileTraceFiles.py MSTAR_DATABASE ORACLE_ADMIN_PATH ALL|PROGRAM"
    print sys.argv
    sys.exit(12)
#
# Initialize parameters and Constants
#
mstarpaths.loadMineStarConfig()
mstarpaths.setEnvironment()
mstar_db = sys.argv[1]
oracle_admin = sys.argv[2]
trace_dir = sys.argv[3]
#
myDS = []
myDS = datastore.getDataStore(mstar_db)
if myDS != None:
   print "Performing SQL Trace on DataStore %s" % (myDS.linkName)
   (mstar_user, mstar_instance, mstar_machine) = (myDS.linkName).split('_')
else:
   print "Database %s cannot be found in MineStar.Propoerties!" % mstar_db
   sys.exit(12)
#
# Setup path to Oracle\Admin\{DB_INSTANCE\udump directory
#
SQL_Trace_Path = oracle_admin + '\\' + mstar_instance + '\\udump\\' + trace_dir
#
os.chdir(SQL_Trace_Path)

newFiles = os.listdir('.')
for Trace_File in newFiles:
    createTraceReport.RunTraceReport(Trace_File, mstar_user, mstar_instance, mstar_machine)
