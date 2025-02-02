import sys, glob, os, formatSQLTraceRpt
from string import *

""" createTraceReport.py: Run Oracles TKPROF.EXE utility to create a formatted 
                          SQL Trace Report file from a raw TRC Trace file supplied
                          as the first parameter. Calls script formatSQLTraceRpt.py
                          to identify any slow SQL in the formatted trace report.
     - Parameter 1: Name of Oracle Trace file produced during a session trace
     - Parameter 2: MSTAR_USER eg. 'MWADM' the user whose SQL sessions were traced
     - Parameter 3: MSTAR_DB eg. 'HIST', the database on which the SQL Trace was run
     - Parameter 4: MSTAR_MACHINE eg. 'MSTAR1' the Oracle database server host name.
"""

def RunTraceReport(oracle_trace, mstar_user, mstar_db, mstar_machine):
  #
  # Initialize parameters and Constants
  #
  oracle_prefix = oracle_trace.split('.', 1)[0]
  trace_report = oracle_prefix + '.LOG'
  slow_report = 'SLOW_' + oracle_prefix + '.LST'

  TK_PROF = 'TKPROF.exe'

  tkprof_cmd = TK_PROF + ' ' + oracle_trace + ' ' + trace_report + ' explain=' + \
             mstar_user + '/' + mstar_user + '@' + mstar_db + '_' + mstar_machine + \
            ' table=' + mstar_user + '.plan_table ' + \
            'sort=(FCHDSK,FCHQRY,FCHCU,PRSCU,PRSDSK,PRSMIS,EXEDSK,EXEQRY,EXECU)'

  os.system(tkprof_cmd)
  #
  # NOTE: The 3 parameter is the Seconds Per SQL Operation Threshold
  #
  formatSQLTraceRpt.findSlowSQLInTrace(trace_report, slow_report, 2)

if __name__ == '__main__':
  if len(sys.argv) != 5:
    print "Usage: createTraceReport.py ORA09999.TRC MSTAR_USER DB_INSTANCE MACHINE"
    print sys.argv
    sys.exit(12)
  RunTraceReport(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])  
