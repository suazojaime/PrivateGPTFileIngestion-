# A library for manipulations of the listener.ora file.

import minestar, os, mstarpaths

logger = minestar.initApp()

LISTENER_ENTRY = """    # Added %s by Python code.
    (SID_DESC =
      (GLOBAL_DBNAME = %s)
      (ORACLE_HOME = {ORACLE_HOME})
      (SID_NAME = %s)
    )
"""
LISTENER_TEMPLATE = """
LISTENER =
  (DESCRIPTION_LIST =
    (DESCRIPTION =
      (ADDRESS = (PROTOCOL = TCP)(HOST = {COMPUTERNAME})(PORT = %s))
    )
    (DESCRIPTION =
      (ADDRESS = (PROTOCOL = IPC)(KEY = EXTPROC0))
    )
  )

SID_LIST_LISTENER =
  (SID_LIST =
    (SID_DESC =
      (SID_NAME = PLSExtProc)
      (ORACLE_HOME = {ORACLE_HOME})
      (PROGRAM = extproc)
    )
  )
"""

LISTENER_FILE_TEMPLATE = """
LISTENER =
  (DESCRIPTION_LIST =
    (DESCRIPTION =
      (ADDRESS = (PROTOCOL = TCP)(HOST = {COMPUTERNAME})(PORT = %s))
    )
    (DESCRIPTION =
      (ADDRESS = (PROTOCOL = IPC)(KEY = EXTPROC0))
    )
  )

SID_LIST_LISTENER =
  (SID_LIST =
%s)
"""

SID_ENTRY = """    (SID_DESC =
      (GLOBAL_DBNAME = %s)
      (ORACLE_HOME = %s)
      (SID_NAME = %s)
    )
"""
PROGRAM_ENTRY = """    (SID_DESC =
      (SID_NAME = %s)
      (ORACLE_HOME = %s)
      (PROGRAM = %s)
    )
"""

def textBetween(s, before, after):
    return s.split(before)[1].split(after)[0].strip()

class ListenerSidDefinition:
    def __init__(self, sidComment, globalDBName, oracleHome, sidName, program):
        self.sidComment = sidComment
        self.globalDBName = globalDBName
        self.oracleHome = oracleHome
        self.sidName = sidName
        self.program = program

    def __str__(self):
        if self.globalDBName is not None:
            s = SID_ENTRY % (self.globalDBName, self.oracleHome, self.sidName)
        else:
            s = PROGRAM_ENTRY % (self.sidName, self.oracleHome, self.program)
        if self.sidComment is not None:
            s = "    %s\n%s" % (self.sidComment, s)
        return s

class ListenerFile:
    def __init__(self, filename):
        self.filename = filename
        self.sidDescs = {}
        lastComment = None
        sidComment = None
        globalDBName = None
        oracleHome = None
        sidName = None
        program = None
        if os.access(self.filename, os.F_OK):
            for line in open(self.filename):
                if line[-1] == '\n':
                    line = line[:-1]
                line = line.strip()
                if line.startswith("#"):
                    lastComment = line
                if line.startswith("(SID_DESC"):
                    sidComment = lastComment
                    lastComment = None
                elif line.startswith("(GLOBAL_DBNAME"):
                    globalDBName = textBetween(line, "=", ")")
                elif line.startswith("(ORACLE_HOME"):
                    oracleHome = textBetween(line, "=", ")")
                elif line.startswith("(SID_NAME"):
                    sidName = textBetween(line, "=", ")")
                elif line.startswith("(PROGRAM"):
                    program = textBetween(line, "=", ")")
                elif line == ")":
                    if None not in [oracleHome, sidName] and (program is not None or globalDBName is not None) and sidName not in self.sidDescs.keys():
                        self.sidDescs[sidName] = ListenerSidDefinition(sidComment, globalDBName, oracleHome, sidName, program)
                    sidComment = None
                    globalDBName = None
                    oracleHome = None
                    sidName = None
                    program = None
        self._checkPLS()

    def _checkPLS(self):
        # this is standard and required, I think it allows PL/SQL to resolve external procedure names
        self.defineSid(None, None, mstarpaths.interpretPath("{ORACLE_HOME}"), "PLSExtProc", "extproc")

    def isSidDefined(sidName):
        return sidName in self.sidDescs.keys()

    def defineSid(self, comment, globalDBName, oracleHome, sidName, program=None):
        self.sidDescs[sidName] = ListenerSidDefinition(comment, globalDBName, oracleHome, sidName, program)

    def __str__(self):
        portRolesSpec = mstarpaths.interpretVar("_DB_PORT")
        portNumber = "1521"
        if portRolesSpec is not None and portRolesSpec != '':
            portRoles = eval(portRolesSpec)
            if("PRODUCTION" in portRoles):
                portNumber = portRoles["PRODUCTION"]
        listenerTemplate = LISTENER_FILE_TEMPLATE % (portNumber,"%s")
        return mstarpaths.interpretFormat(listenerTemplate) % "".join(map(str, self.sidDescs.values()))
        
    def write(self):
        minestar.logit("Updating %s" % self.filename)
        file = open(self.filename, "w")
        file.write(str(self))
        file.close()
