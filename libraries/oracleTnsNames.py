# A library for manipulations of the tnsnames.ora file.

from subprocess import call
import minestar, os, mstarpaths, time, datastore

logger = minestar.initApp()

TNSNAMES_MARKER = "# MineStar Database Server Configuration"
TNSNAMES_ENTRY = """
# Added %s by Python code.
%s =
  (DESCRIPTION =
    (ADDRESS_LIST =
      (ADDRESS = (PROTOCOL = TCP)(HOST = %s)(PORT = %s))
    )
    (CONNECT_DATA =
        (SERVICE_NAME = %s)
    )
  )
"""
XETNSNAMES_ENTRY = """
# Added %s by Python code.
%s =
  (DESCRIPTION =
    (ADDRESS_LIST =
      (ADDRESS = (PROTOCOL = TCP)(HOST = %s)(PORT = %s))
    )
    (CONNECT_DATA =
        (SERVICE_NAME = %s)
        (SERVER = DEDICATED)
    )
  )
"""

class TnsNamesFile:
    def __init__(self, filename,instanceNames, serverRoles,dbportRoles, reportingInstanceNames, reportingServerRoles):
        self.filename = filename
        self.instanceNames = instanceNames
        self.serverRoles = serverRoles
        self.dbportRoles = dbportRoles
        self.linesToWrite = []
        self.reportingServerRoles = reportingServerRoles
        self.reportingInstanceNames = reportingInstanceNames
        if datastore.isOracleXE():
            call(["sc", "stop", "OracleXETNSListener"])
        lines = []
        if os.path.exists(filename):
            tnsNamesFile = open(filename, "r")
            lines = tnsNamesFile.readlines()
        else:
            tnsNamesFile = open(filename, "w")


        startInsertion = False
        endInsertion = False
        while lines != []:
            for line in lines:
                line = line.rstrip()
                if not startInsertion:
                    startInsertion = line.startswith(TNSNAMES_MARKER)
                    if not startInsertion:
                        if not datastore.isOracleXE():
                            self.linesToWrite.append(line)
                        continue
                    self.insertNames()
                    continue
                if startInsertion and not endInsertion:
                    endInsertion = line.startswith(TNSNAMES_MARKER)
                    continue
                self.linesToWrite.append(line)
            lines = tnsNamesFile.readlines()

        if not startInsertion:
            self.insertNames()
        tnsNamesFile.close()
        if datastore.isOracleXE():
            call(["sc", "start", "OracleXETNSListener"])

    def insertNames(self):
        self.linesToWrite.append(TNSNAMES_MARKER + " Start")
        if self.serverRoles is not None:
            self.insertMineStarNames()
        if self.reportingServerRoles is not None:
            self.insertReportingNames()
        self.linesToWrite.append(TNSNAMES_MARKER + " End")

    def insertMineStarNames(self):
        entries = ""

        tnsnamesEntry = TNSNAMES_ENTRY
        if datastore.isOracleXE():
            tnsnamesEntry = XETNSNAMES_ENTRY
        portNumber = "1521"
        for instance in self.instanceNames:
            for role, host in self.serverRoles.items():
                if(self.dbportRoles and self.dbportRoles is not None):
                    dbPort = self.dbportRoles[role]
                    if(dbPort is not None and dbPort.upper()!="DEFAULTPORT"):
                        portNumber = dbPort
                instanceName = "%s_%s" % (instance, role)
                entry = tnsnamesEntry % (time.ctime(), instanceName, host,portNumber, instance)
                entries = entries+os.linesep+entry
                if role == "PRODUCTION":
                    # add entry for MineStar reporting
                    instanceName = "%s_%s" % (instance, "REPORTING")
                    entry = tnsnamesEntry % (time.ctime(), instanceName, host,portNumber, instance)
                    entries = entries+os.linesep+entry

        newLines = entries.split(os.linesep)
        self.linesToWrite.extend(newLines)

    def insertReportingNames(self):
        entries = ""

        tnsnamesEntry = TNSNAMES_ENTRY
        for instance in self.reportingInstanceNames:
            for role, host in self.reportingServerRoles.items():
                instanceName = "%s_%s" % (instance, role)
                portNumber = "1521"
                entry = tnsnamesEntry % (time.ctime(), instanceName, host,portNumber, instance)
                entries = entries+os.linesep+entry
        newLines = entries.split(os.linesep)
        self.linesToWrite.extend(newLines)

    def write(self):
        minestar.logit("Updating %s" % self.filename)
        file = open(self.filename, "w")
        for line in self.linesToWrite:
            file.write(line+os.linesep)
        file.close()
