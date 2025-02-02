#  Copyright (c) 2020 Caterpillar

import i18n
import minestar
import os
import progress
import re
import shutil
import sys
import time


# This class is common for all the database specific operations

def getDbServerRoleSpec():
    import mstarpaths
    return mstarpaths.interpretVar("_DB_SERVER_ROLES")


def getReportServerRoleSpec():
    import mstarpaths
    return mstarpaths.interpretVar("_DB_SERVER_ROLES_REPORTING")


def getDbPortRoleSpec():
    import mstarpaths
    return mstarpaths.interpretVar("_DB_PORT")


def getDbAdminUsernameSpec():
    """Get the DB admin username spec."""
    import mstarpaths
    return mstarpaths.interpretVar("_DB_ADMIN_USER")


def getDbAdminPasswordSpec():
    """Get the DB admin password spec."""
    import mstarpaths
    return mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")


def getDbTypeSpec():
    """Get the database type spec."""
    import mstarpaths
    return mstarpaths.interpretVar("_INSTANCE1_TYPE")


def getDbPort():
    serverRoleSpec = getDbServerRoleSpec()
    dbportRolesSpec = getDbPortRoleSpec()
    dbportRoles = {}
    portNumber = "1521"
    if serverRoleSpec is not None and serverRoleSpec != '':
        serverRoles = eval(serverRoleSpec)
    if dbportRolesSpec is not None and dbportRolesSpec != '':
        dbportRoles = eval(dbportRolesSpec)

    for role, host in serverRoles.items():
        if dbportRoles and dbportRoles is not None:
            dbport = dbportRoles[role]
            if dbport is not None and dbport.upper() != "DEFAULTPORT" and dbport != '':
                portNumber = dbport

    return portNumber


# This method returns the object of database specific class
def returndbObject(config=None, className=None):
    result = None

    if className == 'mpaths':
        dbtype = config["_INSTANCE1_TYPE"]
    else:
        dbtype = getDbTypeSpec()

    if dbtype == "oracle":
        result = oracledbSpecific()
    elif dbtype == "sqlserver":
        result = sqldbSpecific()
    elif dbtype == "postgresql":
        result = postgresqldbSpecific()
    return result


class databaseDifferentiator:
    # className is required because of mstarpaths.py for this class we can not directly check mstarpaths.interpretVar("_INSTANCE1_TYPE")

    #    def __init__(self,config=None,className=None):

    def __init__(self):
        self._sysUser = None
        self._sysPassword = None

    # Method will return location of the repository file as per the database type.
    def reportingRepository(self):
        raise NotImplementedError("Subclass must implement abstract method")

    # Method to provide backup file location as per the database type

    def backupFileName(self, dsName):
        raise NotImplementedError("Subclass must implement abstract method")

    # This method will be used in the createDataStore.py fix method.
    # It will create database instances and users

    def createDataStoreFixops(self, dsName, ds, homeDir, dataDirs):
        raise NotImplementedError("Subclass must implement abstract method")

    # This method will find out the database home

    def Dbhome(self):
        raise NotImplementedError("Subclass must implement abstract method")

    # This method is oracle specific method.
    def UpdateTnsNames(self):
        raise NotImplementedError("Subclass must implement abstract method")

    # Method is used in create datastore for listenora restart.
    def createDataStoreMainopsRestart(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def updateListenerOra(self, instance):
        raise NotImplementedError("Subclass must implement abstract method")

    def updateTnsNameFile(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def isdbInstalled(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def findMSSQLHome(self, msVer, sources, config):
        raise NotImplementedError("Subclass must implement abstract method")

    def finddbHome(self, sources, config):
        raise NotImplementedError("Subclass must implement abstract method")

    def getDatabaseExtensions(self, config):
        raise NotImplementedError("Subclass must implement abstract method")

    def setDefines(self, defines):
        raise NotImplementedError("Subclass must implement abstract method")

    def returnLibraryPath(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def getDBString(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def selectViewMetadata(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def getdumpfileExt(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def validateExport(self, logFile, fileName):
        raise NotImplementedError("Subclass must implement abstract method")

    def updateNextOid(self, cycleordelay):
        raise NotImplementedError("Subclass must implement abstract method")

    def dbURLPattern(self):
        raise NotImplementedError("Subclass must implement abstract method")

    def refreshUser(self, ds):
        raise NotImplementedError("Subclass must implement abstract method")

    def trashSQLServerDb(self, homeDir, ds):
        raise NotImplementedError("Subclass must implement abstract method")

    @property
    def sysUser(self):
        """Get the database administrator username."""
        if self._sysUser is None:
            self._sysUser = getDbAdminUsernameSpec()
        return self._sysUser

    @property
    def sysPassword(self):
        """Get the database administrator password."""
        if self._sysPassword is None:
            self._sysPassword = getDbAdminPasswordSpec()
        return self._sysPassword


class oracledbSpecific(databaseDifferentiator):

    """Oracle database adapter."""

    def reportingRepository(self):
        return "reports/BOREPOSITORY.DMP"

    def backupFileName(self, dsName):
        import mstarpaths
        return mstarpaths.interpretPath("{MSTAR_TEMP}/%sbackup_{YYYY}{MM}{DD}{HH}{NN}.dmp" % dsName)

    def createReportingDataStore(self, dsName, ds, homeDir, dataDirs):
        APP = "createDataStores"
        progress.task(0.02, "Adding entry to listener.ora")
        minestar.logit("createReportingDataStore.fix: Started ds.instance = %s " % ds.instance)
        minestar.logit("createReportingDataStore.fix: Started dsName = %s " % dsName)
        # self.updateListenerOra(ds.instance)
        # probe it to find out what's wrong
        progress.nextTask(0.04, "Probing data store to determine its status")
        status = ds.probe()
        minestar.logit("createReportingDataStore.fix: After probing datastore, status is %s " % status)
        if status in ["BAD", "URL", "DRIVER", "TOOLONG"]:
            minestar.logit("createReportingDataStore.fix: Data store '%s' is broken: status is %s" % (dsName, status))
            error = i18n.translate("Data store '%s' is broken: status is %s") % (dsName, status)
            progress.fail(error)
            minestar.fatalError(APP, error)
        if status == "INSTANCE":
            progress.nextTask(0.9, "Creating instance")
            ds.createInstance(homeDir, dataDirs, True)
            status = ds.probe()
        if status == "TABLESPACES":
            minestar.logit("createDataStores.fix: creating tablespaces ...")
            progress.nextTask(0.04, "Creating tablespaces")
            ds.createTableSpaces(homeDir, dataDirs, True)
            status = ds.probe()
        if status == "USER":
            minestar.logit("createDataStores.fix: creating user ...")
            progress.nextTask(0.04, "Creating user")
            ds.createUser(True)
            status = ds.probe()
        if status == "OK":
            minestar.logit("createReportingDataStore.fix: refreshing user ...")
            ds.refreshUser()
        if status != "OK":
            minestar.logit(
                "createReportingDataStore.fix: Data store '%s' can not be created: status is %s" % (dsName, status))
            error = i18n.translate("Data store '%s' can not be created: status is %s") % (dsName, status)
            progress.fail(error)
            minestar.fatalError(APP, error)

    def createDataStoreFixops(self, dsName, ds, homeDir, dataDirs):
        # do whatever's needed to get the data store created to the point where we can put a schema into it
        # make sure data store is in listener.ora, in case it has been trashed
        # we have to do this first or the probe will fail
        APP = "createDataStores"

        APP = "createDataStores"
        progress.task(0.02, "Adding entry to listener.ora")
        minestar.logit("createDataStores.fix: Started ds.instance = %s " % ds.instance)
        minestar.logit("createDataStores.fix: Started dsName = %s " % dsName)
        self.updateListenerOra(ds.instance)
        # probe it to find out what's wrong
        progress.nextTask(0.04, "Probing data store to determine its status")
        status = ds.probe()
        minestar.logit("createDataStores.fix: After probing datastore, status is %s " % status)
        if status in ["BAD", "URL", "DRIVER", "TOOLONG"]:
            minestar.logit("createDataStores.fix: Data store '%s' is broken: status is %s" % (dsName, status))
            error = i18n.translate("Data store '%s' is broken: status is %s") % (dsName, status)
            progress.fail(error)
            minestar.fatalError(APP, error)
        if status == "INSTANCE":
            progress.nextTask(0.9, "Creating instance")
            ds.createInstance(homeDir, dataDirs)
            minestar.logit("createDataStores.main: Calling createDbAdmin")
            ds.createAdminUser()
            status = ds.probe()
        if status == "TABLESPACES":
            minestar.logit("createDataStores.fix: creating tablespaces ...")
            progress.nextTask(0.04, "Creating tablespaces")
            ds.createTableSpaces(homeDir, dataDirs)
            status = ds.probe()
        if status == "USER":
            minestar.logit("createDataStores.fix: creating user ...")
            progress.nextTask(0.04, "Creating user")
            ds.createUser()
            status = ds.probe()
        if status == "READONLYUSER":
            minestar.logit("createDataStores.fix: creating readonly user ...")
            progress.nextTask(0.04, "Creating readonly user")
            ds.createReadOnlyUser()
            status = ds.probe()
        if status == "OK":
            minestar.logit("createDataStores.fix: refreshing user ...")
            ds.refreshUser()
        if status != "OK":
            minestar.logit("createDataStores.fix: Data store '%s' can not be created: status is %s" % (dsName, status))
            error = i18n.translate("Data store '%s' can not be created: status is %s") % (dsName, status)
            progress.fail(error)
            minestar.fatalError(APP, error)

    def Dbhome(self):
        # check that ORACLE_HOME is set in the environment and ./bin is in path.

        oraHome = os.environ.get('ORACLE_HOME')
        if oraHome is None:
            print "ORACLE_HOME is not set"
            print "Please check the Oracle installation - a System REBOOT may be required!"
            sys.exit(1)
        print "Using ORACLE_HOME %s" % oraHome
        oraBin = oraHome + os.sep + "bin"
        osPath = os.environ['PATH']
        if sys.platform.startswith("win"):
            osPath = osPath.upper()
            oraBin = oraBin.upper()
        if osPath.find(oraBin) < 0:
            print "Could NOT Find ORACLE_HOME\\bin %s in PATH %s" % (oraBin, osPath)
            print "\nPlease check the Oracle installation - a System REBOOT may be required!"
            sys.exit(1)

    def UpdateTnsNames(self):
        # ensure tnsnames.ora is ok
        progress.nextTask(0.01, "Checking (and updating if required) tnsnames.ora")
        minestar.logit("createDataStores.main: Calling configureDataStoreConnections.updateTnsNames")
        self.updateTnsNameFile()

    def updateTnsNameFile(self):
        import mstarpaths, oracleTnsNames, datastore
        serverRoleSpec = getDbServerRoleSpec()
        dbPortRoleSpec = getDbPortRoleSpec()
        serverRoles = {}
        dbPortRoles = {}
        updateReporting = False
        updateMinestar = False
        if dbPortRoleSpec is not None and dbPortRoleSpec != '':
            dbPortRoles = eval(dbPortRoleSpec)
        if serverRoleSpec is not None and serverRoleSpec != '':
            serverRoles = eval(serverRoleSpec)
            instanceNames = datastore.getUniqueDataStoreInstances()
            updateMinestar = True

        reportingServerRoleSpec = mstarpaths.interpretVar("_DB_SERVER_ROLES_REPORTING")
        if reportingServerRoleSpec is not None and reportingServerRoleSpec != '':
            reportingServerRoles = eval(reportingServerRoleSpec)
            # get the reporting datawarehouse details
            reportingInstanceNames = datastore.getReportingDataStoreInstances()
            updateReporting = True

        comment = "# Updated %s by Python code." % time.ctime()
        dirname = mstarpaths.interpretPath("{TNS_ADMIN}")
        filename = mstarpaths.interpretPath("{TNS_ADMIN}/tnsnames.ora")
        msg = "Updating tnsnames file %s for database " % filename
        if os.path.isfile(filename):
            minestar.logit("Backup tnsnames.ora")
            shutil.copyfile(filename, dirname + "/tnsnames_ora.bkp")
        print i18n.translate(msg)
        minestar.logit(msg)
        if updateReporting and updateMinestar:
            tnsnamesFile = oracleTnsNames.TnsNamesFile(filename, instanceNames, serverRoles, dbPortRoles,
                                                       reportingInstanceNames, reportingServerRoles)
        elif updateMinestar:
            tnsnamesFile = oracleTnsNames.TnsNamesFile(filename, instanceNames, serverRoles, dbPortRoles, None, None)
        elif updateReporting:
            tnsnamesFile = oracleTnsNames.TnsNamesFile(filename, None, None, None, reportingInstanceNames,
                                                       reportingServerRoles)
        tnsnamesFile.write()

    def createDataStoreMainopsRestart(self):
        # restart the TNS listener as listener.ora may have been modified
        import datastore
        progress.nextTask(0.01, "Restarting TNS listener")
        # minestar.logit("createDataStores.main: Calling restartListener");
        datastore.restartListener()

    def stopDSListener(self):
        # stop the TNS listener
        import datastore
        progress.nextTask(0.01, "Stopping TNS listener")
        # minestar.logit("createDataStores.main: Calling restartListener");
        datastore.stopListener()

    def startDSListener(self):
        # start the TNS listener
        import datastore
        progress.nextTask(0.01, "Starting TNS listener")
        datastore.startListener()

    def updateListenerOra(self, instance):
        import oracleListener, mstarpaths
        comment = "# Updated %s by Python code." % time.ctime()
        filename = mstarpaths.interpretPath("{TNS_ADMIN}/listener.ora")
        minestar.logit("Adding %s to %s" % (instance, filename))
        lf = oracleListener.ListenerFile(filename)
        lf.defineSid(comment, instance, mstarpaths.interpretPath("{ORACLE_HOME}"), instance)
        lf.write()

    def modifyListenerPort(self, portnum):
        import mstarpaths
        dirname = mstarpaths.interpretPath("{TNS_ADMIN}")
        filename = mstarpaths.interpretPath("{TNS_ADMIN}/listener.ora")
        if os.path.isfile(filename):
            minestar.logit("Backup listener.ora")
            shutil.copyfile(filename, dirname + "/listener_ora.bkp")
        minestar.logit("Adding %s to %s" % (portnum, filename))
        with open(filename, 'r+') as listenerorafile:
            listenercont = listenerorafile.read()
            listenercont = re.sub(r"(PORT\s*=\s*)\d+(\s*\))", r'\1 ' + portnum + r'\2', listenercont)
            # listenercont = re.search(r"(PORT\s*=\s*)\d+(\s*\))", listenercont)
            # listenercont = listenercont.group(1)+portnum+listenercont.group(2)
            listenerorafile.seek(0)
            listenerorafile.write(listenercont)
            listenerorafile.truncate()

    def isdbInstalled(self):
        import mstarpaths
        if not os.path.exists(mstarpaths.interpretPath("{TNS_ADMIN}")):
            print i18n.translate("Cannot update Oracle files. Oracle is not installed on this machine.")
            minestar.exit()

    def finddbHome(self, sources, config):
        import mstarpaths
        if os.environ.get("ORACLE_HOME") is not None:
            ohome = os.environ["ORACLE_HOME"]
            if ohome.endswith(os.sep):
                ohome = ohome[:-1]
            config["ORACLE_HOME"] = ohome
            sources["ORACLE_HOME"] = "(operating system environment)"
        elif sys.platform.startswith("win"):
            # look in the registry
            try:
                import _winreg
                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\ORACLE\ALL_HOMES\ID0")
                oracleHome = _winreg.QueryValueEx(key, "PATH")[0]
                _winreg.CloseKey(key)
                config["ORACLE_HOME"] = oracleHome
                sources["ORACLE_HOME"] = "(registry HKEY_LOCAL_MACHINE\SOFTWARE\ORACLE\ALL_HOMES\ID0\PATH)"
            except:
                config["ORACLE_HOME"] = "(no Oracle installed)"
                sources["ORACLE_HOME"] = "(not found)"
        else:
            oracleHome = minestar.systemEval2("which sqlplus")
            if len(oracleHome) > 0:
                fields = oracleHome.split(os.sep)
                oracleHome = os.sep.join(fields[:-2])
                config["ORACLE_HOME"] = oracleHome
                sources["ORACLE_HOME"] = "(which sqlplus)"
        if os.environ.get("TNS_ADMIN") is not None:
            config["TNS_ADMIN"] = os.environ["TNS_ADMIN"]
            sources["TNS_ADMIN"] = "(operating system environment)"
        if config.get("TNS_ADMIN") is None and config.get("ORACLE_HOME") is not None:
            config["TNS_ADMIN"] = mstarpaths.interpretPathOverride("{ORACLE_HOME}/network/admin", config)
            sources["TNS_ADMIN"] = "(inferred from {ORACLE_HOME}/network/admin)"
        if os.environ.get("ORACLE_VERSION"):
            config["ORACLE_VERSION"] = os.environ["ORACLE_VERSION"]
            sources["ORACLE_VERSION"] = "(operating system environment)"
        else:
            cmdPath = mstarpaths.interpretPathOverride("{ORACLE_HOME}/bin/sqlplus{EXE}", config)
            if os.access(cmdPath, os.X_OK):
                output = minestar.systemEvalRaw(cmdPath + " -v help=yes")
                versionInfo = output[1]
                version = versionInfo.split()[2]
                config["ORACLE_VERSION"] = version
                sources["ORACLE_VERSION"] = "(%s -v help=yes)" % cmdPath
            else:
                config["ORACLE_VERSION"] = "unknown"
                sources["ORACLE_VERSION"] = "(can't execute %s)" % cmdPath

    def findMSSQLHome(msVer, sources, config):
        import _winreg
        try:
            keyStr = "SOFTWARE\\Microsoft\\Microsoft SQL Server\\" + msVer + "\\Tools\\ClientSetup"
            key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, keyStr)
            sqlHome = _winreg.QueryValueEx(key, "Path")[0]
            _winreg.CloseKey(key)
            config["MSSQL_HOME"] = sqlHome
            sources[
                "MSSQL_HOME"] = "(registry HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\" + msVer + "\\Tools\\ClientSetup\\Path)"
            return True
        except:
            return False

    def getDatabaseExtensions(self, config):
        if "ORACLE_VERSION" in config:
            version = config["ORACLE_VERSION"]
            if version.startswith("11"):
                return ["Platform/Database/Oracle11"]
            elif version.startswith("12"):
                return ["Platform/Database/Oracle12"]
            elif version.startswith("18"):
                return ["Platform/Database/Oracle18"]
        # Default to Oracle 10.
        return ["Platform/Database/Oracle10"]

    def setDefines(self, defines):
        import mstarpaths
        defines["ORACLE_HOME"] = mstarpaths.interpretPath("{ORACLE_HOME}")

    def returnLibraryPath(self):
        import mstarpaths
        return mstarpaths.interpretPath("{ORACLE_HOME}/lib")

    def getDBString(self):
        return "Oracle"

    def selectViewMetadata(self):
        viewMetaData = """select cols.table_name AS VIEW_NAME,
       cols.column_name,
       cols.data_type,
       cols.nullable
       from all_Tab_columns cols,
       user_views views
       where cols.table_name = views.view_name
       order by cols.table_name""".replace("\n", " ")
        return viewMetaData

    def getdumpfileExt(self):
        return ".dmp"

    def validateExport(self, logFile, fileName):
        import string
        error = False
        numOraErrs = 0
        numExpErrs = 0
        try:
            infile = open(logFile, "r")
            finished = 0
            findIdx = -1
            lineCount = 0
            in_line = infile.readline()
            while finished == 0:
                in_line = infile.readline()
                if (in_line == '') or (in_line is None):
                    finished = 1
                    break
                lineCount = lineCount + 1
                findIdx = string.find(in_line, "ORA-", 0)
                if findIdx == 0:
                    findIdx = string.find(in_line, "ORA-01455", 0)
                    if findIdx == 0:
                        continue
                    print "Found string %s in line %s!\n" % ("ORA-", in_line)
                    findIdx = 0
                    error = True
                    numOraErrs = numOraErrs + 1
                findIdx = string.find(in_line, "EXP-00091", 0)
                # ignore EXP-00091:
                if findIdx == 0:
                    continue
                findIdx = string.find(in_line, "EXP-", 0)
                if findIdx == 0:
                    findIdx = string.find(in_line, "EXP-00008", 0)
                    if findIdx == 0:
                        continue
                    print "Found string %s in line %s!\n" % ("EXP-", in_line)
                    findIdx = 0
                    error = True
                    numExpErrs = numExpErrs + 1
            if numOraErrs != 0 or numExpErrs != 0:
                if os.access(fileName, os.F_OK):
                    os.remove(fileName)
                msg = i18n.translate("ERROR: DBEXPORT found %d ORA- Errors and %d EXP- Errors found in logFile %s! " % (
                numOraErrs, numExpErrs, logFile))
                minestar.logit(msg)
        except IOError:
            msg = i18n.translate("WARNING: DBEXPORT unable to open logFile %s, export must have failed! " % logFile)
            minestar.logit(msg)
            print msg
        return error, numOraErrs, numExpErrs

    def updateNextOid(self, cycleordelay):
        if cycleordelay == 'c':
            return ("update system_info set next_oid = nvl((select to_char(1+round(to_number(max(cycle_oid))/10000))" +
                    "from %s.cycle where 1+round(to_number(cycle_oid)/10000) > to_number(next_oid)), next_oid)")
        elif cycleordelay == 'd':
            return ("update system_info set next_oid = nvl((select to_char(1+round(to_number(max(delay_oid))/10000))" +
                    "from %s.delay where 1+round(to_number(delay_oid)/10000) > to_number(next_oid)), next_oid)")

    def dbURLPattern(self):
        return "jdbc:oracle:oci:@%s"

    def thinURLPattern(self):
        return "jdbc:oracle:thin:@%s:1521:%s"

    def refreshUser(self, ds):
        return

    def trashSQLServerDb(self, homeDir, ds):
        return


class sqldbSpecific(databaseDifferentiator):

    """SQLServer database adapter."""

    SQL_SCRIPTS = "{MSTAR_DATABASE}/sqlserver"
    INSTANCE_DATA = "/mstarData/sqldata/{INSTANCE}"
    INSTANCE_ADMIN = "{HOME}{DRIVE}/mstarData/admin/{INSTANCE}/"
    CREATE_INSTANCE_DIRS = [
        # INSTANCE_ADMIN + "adhoc", INSTANCE_ADMIN + "archive", INSTANCE_ADMIN + "bdump",
        # INSTANCE_ADMIN + "cdump", INSTANCE_ADMIN + "create", INSTANCE_ADMIN + "exp",
        # INSTANCE_ADMIN + "pfile", INSTANCE_ADMIN + "udump",
        "{MSSQL_HOME}/{PWDFILE_DIR}", "{HOME}{DRIVE}" + INSTANCE_DATA
    ]

    def reportingRepository(self):
        return "false"

    def UpdateTnsNames(self):
        progress.nextTask(0.01, "Checking instance name")
        minestar.logit("createDataStores.main: Calling updateTnsNames")
        self.updateTnsNameFile()

    def dbURLPattern(self):
        return "jdbc:sqlserver:@%s"

    def thinURLPattern(self):
        return ""

    def updateNextOid(self,cycleordelay):
        if cycleordelay == 'c':
            return ("update system_info set next_oid = isnull((select Convert(varchar(25),1+round(max(cycle_oid)/10000))"+
                    "from %s.cycle where 1+round(cycle_oid/10000) > next_oid), next_oid)")
        elif cycleordelay == 'd':
            return ("update system_info set next_oid = isnull((select Convert(varchar(25),1+round(max(delay_oid)/10000))"+
                    "from %s.delay where 1+round(delay_oid/10000) > next_oid), next_oid)")

    def updateListenerOra(self, instance):
        return

    def updateTnsNameFile(self):
        import mstarpaths, datastore
        serverRoleSpec = mstarpaths.interpretVar("_DB_SERVER_ROLES")
        serverRoles = {}
        if serverRoleSpec is not None and serverRoleSpec != '':
            serverRoles = eval(serverRoleSpec)
            instanceNames = datastore.getUniqueDataStoreInstances()
            if instanceNames is not None:
                comment = "# Updated %s by Python code." % time.ctime()
                msg = "database instances %s and roles=%s" % (instanceNames, serverRoles)
                print i18n.translate(msg)
                minestar.logit(msg)
            else:
                msg = "database instance is not created"
                print i18n.translate(msg)
                minestar.logit(msg)
                sys.exit(1)

    def modifyListenerPort(self, portnum):
        return

    def stopDSListener(self):
        return

    def startDSListener(self):
        return

    def finddbHome(self, sources, config):
        if os.environ.get("MSSQL_HOME") is not None:
            ohome = os.environ["MSSQL_HOME"]
            if ohome.endswith(os.sep):
                ohome = ohome[:-1]
            config["MSSQL_HOME"] = ohome
            sources["MSSQL_HOME"] = "(operating system environment)"
        elif sys.platform.startswith("win"):
            # look in the registry
            msVer = "120"
            found = self.findMSSQLHome(msVer, sources, config)
            if not found:
                msVer = "110"
                found = self.findMSSQLHome(msVer, sources, config)
                if not found:
                    msVer = "100"
                    found = self.findMSSQLHome(msVer, sources, config)
                    if not found:
                        config["MSSQL_HOME"] = "(no SQL Server installed)"
                        sources["MSSQL_HOME"] = "(not found)"
        else:
            # to do which sqlcmd
            return
            #  if os.environ.get("MSSQL_VERSION"):
            #   config["MSSQL_VERSION"] = os.environ["MSSQL_VERSION"]
            #   sources["MSSQL_VERSION"] = "(operating system environment)"
            #  else:
            #      self.autoDetectDBVersion(sources, config)

    def findMSSQLHome(self, msVer, sources, config):
        import _winreg
        try:
            keyStr = "SOFTWARE\\Microsoft\\Microsoft SQL Server\\" + msVer + "\\Tools\\ClientSetup"
            key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, keyStr)
            sqlHome = _winreg.QueryValueEx(key, "Path")[0]
            _winreg.CloseKey(key)
            config["MSSQL_HOME"] = sqlHome
            sources[
                "MSSQL_HOME"] = "(registry HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\" + msVer + "\\Tools\\ClientSetup\\Path)"
            return True
        except:
            return False

    def getdumpfileExt(self):
        return ".bak"

    def createDataStoreMainopsRestart(self):
        return

    def Dbhome(self):
        # check that MSSQL_HOME is set in the environment and ./bin is in path.

        sqlHome = os.environ.get("MSSQL_HOME")
        if sqlHome is None:
            print "MSSQL_HOME is not set"
            print "Please check the MS SQL installation - a System REBOOT may be required!"
            sys.exit(1)
        print "Using MSSQL_HOME %s" % sqlHome
        sqlBin = sqlHome + os.sep + "Tools" + os.sep + "Binn"
        osPath = os.environ['PATH']
        if sys.platform.startswith("win"):
            osPath = osPath.upper()
            sqlBin = sqlBin.upper()
        if osPath.find(sqlBin) < 0:
            print "Could NOT Find MSSQL_HOME\\bin %s in PATH %s" % (sqlBin, osPath)
            print "\nPlease check the MSSQL installation - a System REBOOT may be required!"
            sys.exit(1)

    def getDatabaseExtensions(self, config):
        return ["Platform/Database/SqlServer"]

    def getDBString(self):
        return "sqlserver"

    def returnLibraryPath(self):
        import mstarpaths
        return mstarpaths.interpretPath("{MSSQL_HOME}/SDK/Lib")

    def setDefines(self, defines):
        import mstarpaths
        defines["MSSQL_HOME"] = mstarpaths.interpretPath("{MSSQL_HOME}")

    def createDataStoreFixops(self, dsName, ds, homeDir, dataDirs):
        import mstarpaths
        APP = "createDataStores"
        instance = "instance"
        progress.task(0.02, "Adding entry to listener.ora")
        minestar.logit("createDataStores.fix: Started ds.instance = %s " % ds.instance)
        minestar.logit("createDataStores.fix: Started dsName = %s " % dsName)
        # create admin user if it is not created
        minestar.logit("createDataStores.fix: Create Admin User ")
        saAdminPass = mstarpaths.interpretVar("_DB_SYS_AUTH")
        if not saAdminPass:
            minestar.logit(
                "createDataStores.fix: sa credential is required in supervisor.Unable to run CreateDataStores")
            error = i18n.translate("sa credential is required in supervisor.Unable to run CreateDataStores")
            progress.fail(error)
            minestar.fatalError(APP, error)
        ds.createAdminUser()
        # probe it to find out what's wrong
        progress.nextTask(0.04, "Probing data store to determine its status")
        status = ds.probe()
        minestar.logit("createDataStores.fix: After probing datastore, status is %s " % status)
        if status in ["BAD", "URL", "DRIVER", "TOOLONG"]:
            minestar.logit("createDataStores.fix: Data store '%s' is broken: status is %s" % (dsName, status))
            error = i18n.translate("Data store '%s' is broken: status is %s") % (dsName, status)
            progress.fail(error)
            minestar.fatalError(APP, error)
        if status == "INSTANCE":
            import mstarpaths, ServerTools
            # server =ServerTools.getCurrentDatabaseServer()
            minestar.logit("createDataStores:Cannot connect to SQL Server")
            minestar.logit("createDataStores: Instance: %s or %s not exists" % (ds.instance, ds.instance2))
            error = i18n.translate("Instances provided in Supervisor does not exists in SQL server")
            if dsName == "historical":
                print(error)
            progress.done()
            return instance
            # progress.fail(error)
            # minestar.fatalError(APP, error)
        if status == "DATABASE":
            minestar.logit("createDataStores.fix: creating database...")
            progress.nextTask(0.04, "Creating database")
            self.createDatabase(ds, homeDir, dataDirs)
            status = ds.probe()
        if status == "LOGIN":
            minestar.logit("createDataStores.fix: creating login ...")
            progress.nextTask(0.04, "Creating login")
            self.createLogin(ds, homeDir)
            status = ds.probe()
        if status == "USER":
            minestar.logit("createDataStores.fix: creating user ...")
            progress.nextTask(0.04, "Creating user")
            self.createUser(ds)
            status = ds.probe()
        if status == "SCHEMAS":
            minestar.logit("createDataStores.fix: creating schema ...")
            self.createSchemas(ds)
            status = ds.probe()
        if status == "READONLYLOGIN":
            minestar.logit("createDataStores.fix: creating readonly login ...")
            progress.nextTask(0.04, "Creating readonly login")
            self.createReadOnlyLogin(ds)
            status = ds.probe()
        if status == "READONLYUSER":
            minestar.logit("createDataStores.fix: creating readonly user ...")
            progress.nextTask(0.04, "Creating readonly user")
            self.createReadOnlyUser(ds)
            status = ds.probe()
        if status == "OK":
            minestar.logit("createDataStores.fix: refreshing user ...")
            # self.refreshUser(ds)
            status = ds.probe()
        if status != "OK":
            minestar.logit("createDataStores.fix: Data store '%s' can not be created: status is %s" % (dsName, status))
            error = i18n.translate("Data store '%s' can not be created: status is %s") % (dsName, status)
            progress.fail(error)
            minestar.fatalError(APP, error)

    def createReportingDataStore(self, dsName, ds, homeDir, dataDirs):
        APP = "createDataStores"
        instance = "instance"
        progress.task(0.02, "Adding entry to listener.ora")
        minestar.logit("createDataStores.fix: Started ds.instance = %s " % ds.instance)
        minestar.logit("createDataStores.fix: Started dsName = %s " % dsName)
        # probe it to find out what's wrong
        progress.nextTask(0.04, "Probing data store to determine its status")
        status = ds.probe()
        minestar.logit("createDataStores.fix: After probing datastore, status is %s " % status)
        if status in ["BAD", "URL", "DRIVER", "TOOLONG"]:
            minestar.logit("createDataStores.fix: Data store '%s' is broken: status is %s" % (dsName, status))
            error = i18n.translate("Data store '%s' is broken: status is %s") % (dsName, status)
            progress.fail(error)
            minestar.fatalError(APP, error)
        if status == "INSTANCE":
            import mstarpaths, ServerTools
            # server =ServerTools.getCurrentDatabaseServer()
            minestar.logit("createDataStores:Cannot connect to SQL Server")
            minestar.logit("createDataStores: Instance: %s or %s not exists" % (ds.instance, ds.instance2))
            progress.done()
            return instance
            # progress.fail(error)
            # minestar.fatalError(APP, error)
        if status == "DATABASE":
            minestar.logit("createDataStores.fix: creating database...")
            progress.nextTask(0.04, "Creating database")
            self.createDatabase(ds, homeDir, dataDirs)
            status = ds.probe()
        if status == "LOGIN":
            minestar.logit("createDataStores.fix: creating login ...")
            progress.nextTask(0.04, "Creating login")
            self.createLogin(ds, homeDir)
            status = ds.probe()
        if status == "USER":
            minestar.logit("createDataStores.fix: creating user ...")
            progress.nextTask(0.04, "Creating user")
            self.createUser(ds)
            status = ds.probe()
        if status == "SCHEMAS":
            minestar.logit("createDataStores.fix: creating schema ...")
            self.createSchemas(ds)
            status = ds.probe()
        if status == "OK":
            minestar.logit("createDataStores.fix: refreshing user ...")
            self.refreshUser(ds)
            status = ds.probe()
        if status != "OK":
            minestar.logit("createDataStores.fix: Data store '%s' can not be created: status is %s" % (dsName, status))
            error = i18n.translate("Data store '%s' can not be created: status is %s") % (dsName, status)
            progress.fail(error)
            minestar.fatalError(APP, error)

    def createDatabase(self, ds, homeDir, dataDirs):
        FUNCTION_PARAMS = {
            "SERVER": {"_MODELDB": "100", "_HISTORICALDB": "1000", "_TIMESERIESDB": "1000", "_TEMPLATEDB": "15", "_REPORTINGDB": "60",
                       "_CFG": "60", "_DVL": "60", "_DWH": "60", "_DCL": "60"},
            "LAPTOP": {"_MODELDB": "60", "_HISTORICALDB": "100", "_TIMESERIESDB": "100", "_TEMPLATEDB": "15", "_REPORTINGDB": "60",
                       "_CFG": "60", "_DVL": "60", "_DWH": "60", "_DCL": "60"}
        }
        import mstarpaths
        overrides = self._getInstanceOverrides(homeDir, ds)
        print("datastore.createTableSpaces: overrides is  %s " % overrides)
        dirs = [self._interpret(d, overrides) for d in self.CREATE_INSTANCE_DIRS]
        print(d)
        dirs = dirs + [self._interpret(d + overrides["DRIVE"] + self.INSTANCE_DATA, overrides) for d in dataDirs]
        for d in dirs:
            try:
                os.makedirs(d)
            except OSError:
                # already exists
                pass
        dbname = ds.user
        instance = ds.instance
        sysUser = self.sysUser
        sysPass = self.sysPassword
        # dir =homeDir+":"
        size = mstarpaths.interpretVar("MSTAR_SCHEMA_SIZE").upper()
        collationType = mstarpaths.interpretVar("_SQL_COLLATION_TYPE")
        containmentType = mstarpaths.interpretVar("_SQL_CONTAINMENT_TYPE")

        osIsWindows = sys.platform.startswith("win")

        overrideMdfPath = mstarpaths.interpretPath("{SQL_SERVER_MDFPATH}")
        overrideLogPath = mstarpaths.interpretPath("{SQL_SERVER_LOGPATH}")
        primeDataDr = dataDirs[0] if dataDirs else homeDir
        secDataDr = dataDirs[1] if len(dataDirs)>1 else primeDataDr
        if overrideMdfPath is not None and overrideMdfPath != "":
            mdfPath = (overrideMdfPath + "\\" + dbname + ".mdf" )if osIsWindows else (overrideMdfPath + "/"+ dbname + ".mdf")
        else:
            mdfPath = (primeDataDr+":\\mstarData\\sqldata\\" + instance +"\\" +dbname + ".mdf") if osIsWindows else ("/mstarData/sqldata/" + instance +"/" +dbname + ".mdf")
        if overrideLogPath is not None and overrideLogPath != "":
            ldfPath = (overrideLogPath + "\\" + dbname + "_log.ldf" )if osIsWindows else (overrideLogPath + "/"+ dbname + "_log.ldf")
        else:
            ldfPath = (secDataDr+":\\mstarData\\sqldata\\" + instance +"\\" +dbname + "_log.ldf") if osIsWindows else ("/mstarData/sqldata/" + instance +"/" +dbname + "_log.ldf")

        if FUNCTION_PARAMS.get(size) is None:
            size = "SERVER"
        fileSize = FUNCTION_PARAMS[size].get(ds.logicalName)
        if fileSize is None:
            fileSize = "60"
        self.sqlcmd(ds, mstarpaths.interpretPathShort(
                self.SQL_SCRIPTS + "/SchemaUtilities/create_database.sql"), sysUser, sysPass,
                        [dbname, mdfPath, ldfPath, fileSize, fileSize, collationType, containmentType])

    def createReadOnlyLogin(self, ds):
        import mstarpaths
        readonlyUser = mstarpaths.interpretVar("_READONLYUSER")
        readonlyPassword = mstarpaths.interpretVar("_READONLYPASSWORD")
        sysUser = self.sysUser
        sysPass = self.sysPassword
        dbname = ds.user
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/create_login.sql"), sysUser,
                    sysPass, [readonlyUser, readonlyPassword, dbname])
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/create_readonly_user.sql"),
                    sysUser, sysPass, [readonlyUser, readonlyPassword, dbname])

    def createReadOnlyUser(self, ds):
        import mstarpaths
        readonlyUser = mstarpaths.interpretVar("_READONLYUSER")
        readonlyPassword = mstarpaths.interpretVar("_READONLYPASSWORD")
        sysUser = self.sysUser
        sysPass = self.sysPassword
        dbname = ds.user
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/create_readonly_user.sql"),
                    sysUser, sysPass, [readonlyUser, readonlyPassword, dbname])
        # self.sqlcmd(ds,mstarpaths.interpretPathShort(self.SQL_SCRIPTS+ "/SchemaUtilities/test.sql"),['test'])

    def createLogin(self, ds, homeDir):
        import mstarpaths
        sysUser = self.sysUser
        sysPass = self.sysPassword
        dbname = ds.user
        src = mstarpaths.interpretPath("{MSTAR_HOME}\\bus\\bin\\ConvFunction.dll")
        path = homeDir + ":" + "\mstarData\sqldata"
        minestar.copy(src, path)
        auth_src = mstarpaths.interpretPath("{MSTAR_BIN}\\sqljdbc_auth.dll")
        xa_src = mstarpaths.interpretPath("{MSTAR_BIN}\\sqljdbc_xa.dll")
        path = "C:\\windows\\System32"
        minestar.copy(auth_src, path)
        minestar.copy(xa_src, path)
        backup_path = mstarpaths.interpretPath("{MSTAR_TEMP}")
        if not os.path.exists(backup_path): os.makedirs(backup_path)
        minestar.copy(auth_src, backup_path)
        minestar.copy(xa_src, backup_path)
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/create_login.sql"), sysUser,
                    sysPass, [ds.user, ds.password, dbname])
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/create_user.sql"), sysUser,
                    sysPass, [ds.user, ds.password, dbname])

    def createUser(self, ds, fromStandBy=None, reporting=False):
        import mstarpaths
        sysUser = self.sysUser
        sysPass = self.sysPassword
        dbname = ds.user
        if not reporting:
            self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/create_user.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, ds.password, dbname])
        else:
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/create_user_reporting.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, ds.password, dbname])

    def refreshUser(self, ds, fromStandBy=None):
        """Update rights of the user"""
        import mstarpaths, datastore
        minestar.logit("Calling refreshUser for database %s user %s" % (ds.logicalName, ds.user))
        sysUser = self.sysUser
        sysPass = self.sysPassword
        # self.sqlcmd(ds,mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_permissions.sql"),sysUser,sysPass, [ds.user])
        if ds.logicalName == "_HISTORICALDB" or ds.logicalName == "_TIMESERIESDB" or ds.logicalName == "_SUMMARYDB" or ds.logicalName == "_PITMODELDB" or ds.logicalName == "_GISDB" or ds.logicalName == "_TEMPLATEDB":
            modelDs = datastore.getDataStore("_MODELDB")
            templateDs = datastore.getDataStore("_TEMPLATEDB")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, modelDs.user, ds.user.upper()])
            if ds.logicalName == "_HISTORICALDB":
                timeseriesDs = datastore.getDataStore("_TIMESERIESDB")
                self.sqlcmd(ds, mstarpaths.interpretPathShort(
                    self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"), sysUser, sysPass,
                            ["STANDBY", fromStandBy, timeseriesDs.user, ds.user.upper()])
                summDs = datastore.getDataStore("_SUMMARYDB")
                # self.sqlcmd(ds,mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"),sysUser,sysPass, [summDs.user, ds.user.upper()])
                self.sqlcmd(ds, mstarpaths.interpretPathShort(
                    self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"), sysUser, sysPass,
                            ["STANDBY", fromStandBy, summDs.user, ds.user.upper()])
                self.sqlcmd(ds, mstarpaths.interpretPathShort(
                    self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"), sysUser, sysPass,
                            ["STANDBY", fromStandBy, ds.user.upper(), templateDs.user])
            if ds.logicalName == "_TIMESERIESDB":
                self.sqlcmd(ds, mstarpaths.interpretPathShort(
                    self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"), sysUser, sysPass,
                            ["STANDBY", fromStandBy, ds.user.upper(), templateDs.user])
            if ds.logicalName == "_SUMMARYDB":
                histDs = datastore.getDataStore("_HISTORICALDB")
                self.sqlcmd(ds, mstarpaths.interpretPathShort(
                    self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"), sysUser, sysPass,
                            ["STANDBY", fromStandBy, histDs.user, ds.user.upper()])
                self.sqlcmd(ds, mstarpaths.interpretPathShort(
                    self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"), sysUser, sysPass,
                            ["STANDBY", fromStandBy, ds.user.upper(), templateDs.user])
                #  self.sqlcmd(ds,mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"),sysUser,sysPass, [histDs.user, ds.user.upper()])
            if ds.logicalName == "_PITMODELDB":
                histDs = datastore.getDataStore("_HISTORICALDB")
                self.sqlcmd(ds, mstarpaths.interpretPathShort(
                    self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"), sysUser, sysPass,
                            ["STANDBY", fromStandBy, histDs.user, ds.user.upper()])
                self.sqlcmd(ds, mstarpaths.interpretPathShort(
                    self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"), sysUser, sysPass,
                            ["STANDBY", fromStandBy, ds.user.upper(), histDs.user])
                self.sqlcmd(ds, mstarpaths.interpretPathShort(
                    self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"), sysUser, sysPass,
                            ["STANDBY", fromStandBy, ds.user.upper(), templateDs.user])
            templateDs = datastore.getDataStore("_TEMPLATEDB")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, templateDs.user, ds.user.upper()])
        if ds.logicalName == "_MODELDB":
            histDs = datastore.getDataStore("_HISTORICALDB")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, histDs.user, ds.user.upper()])
            timeseriesDs = datastore.getDataStore("_TIMESERIESDB")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, timeseriesDs.user, ds.user.upper()])
            summDs = datastore.getDataStore("_SUMMARYDB")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, summDs.user, ds.user.upper()])
            pitmodelDs = datastore.getDataStore("_PITMODELDB")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, pitmodelDs.user, ds.user.upper()])
            templateDs = datastore.getDataStore("_TEMPLATEDB")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, templateDs.user, ds.user.upper()])
            modelDs = datastore.getDataStore("_MODELDB")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, modelDs.user, ds.user.upper()])
        if ds.logicalName == "_REPORTINGDB":
            templateDs = datastore.getDataStore("_TEMPLATEDB")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, templateDs.user])
        if ds.logicalName == "_CFG":
            dvlDs = datastore.getDataStore("_DVL")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, ds.user.upper()])
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, dvlDs.user.upper()])
        if ds.logicalName == "_DCL":
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, ds.user.upper()])
        if ds.logicalName == "_DVL":
            cfgDs = datastore.getDataStore("_CFG")
            dwhDs = datastore.getDataStore("_DWH")
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, ds.user.upper()])
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, cfgDs.user.upper()])
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_select.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, dwhDs.user.upper()])
        if ds.logicalName == "_DWH":
            self.sqlcmd(ds,
                        mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/set_user_grants_all.sql"),
                        sysUser, sysPass, ["STANDBY", fromStandBy, ds.user, ds.user.upper()])

    def createSchemas(self, ds):
        import mstarpaths
        sysUser = self.sysUser
        sysPass = self.sysPassword
        dbname = ds.user
        schemaName = ds.user
        try:
            self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/create_schema.sql"),
                        sysUser, sysPass, [schemaName, ds.user, dbname])
        except:
            print("error")

    def backUpDatabase(self, ds, filename):
        import mstarpaths
        sysUser = self.sysUser
        sysPass = self.sysPassword
        dbname = ds.user
        # dirPrefix = os.sep+os.sep+ServerTools.getCurrentDatabaseServer()
        # if not (filename.upper().startswith(dirPrefix.upper())):
        #    filename= os.sep+os.sep+ mstarpaths.interpretVar("COMPUTERNAME")+filename.split(":")[1]
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/Backupdb/Backup_Database.sql"), sysUser,
                    sysPass, [dbname, filename])

    def dropall(self, ds, fromStandBy=None):
        import mstarpaths
        sysUser = ds.user
        sysPass = ds.password
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/schema_drop_all.sql"),
                    sysUser, sysPass, ["STANDBY", fromStandBy])

    def restore(self, filename, ds, fromStandBy=None):
        import mstarpaths, ServerTools
        sysUser = self.sysUser
        sysPass = self.sysPassword
        dbname = ds.user
        drive = filename.split(":")[0] + ":"
        if fromStandBy == 'true':
            filename = os.sep + os.sep + ServerTools.getCurrentDatabaseServer() + filename.split(":")[1]
        else:
            filename = filename
        instance = ds.instance
        containmentType = mstarpaths.interpretVar("_SQL_CONTAINMENT_TYPE")
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/Restore_Database.sql"),
                    sysUser, sysPass, ["STANDBY", fromStandBy, dbname, filename, drive, instance, containmentType])

    def sqlcmd(self, ds, script, user, password, args=[]):
        import mstarpaths, ServerTools
        if len(args) > 0 and args[0] == "STANDBY":
            del args[0]
            if args[0] == 'true':
                del args[0]
                server = ServerTools.getStandbyDatabaseServer()
            else:
                del args[0]
                server = ServerTools.getCurrentDatabaseServer()
        else:
            server = ServerTools.getCurrentDatabaseServer()

        databaseserver = ServerTools.getDatabaseInstanceServerName(server, ds)
        sqlcmd = mstarpaths.interpretPath("sqlcmd{EXE}")

        if sys.platform.startswith("win"):
            sqlcmd += " -S" + databaseserver + " -U" + user + " -P" + '"' + password + '"'
        else:
            sqlcmd += " -S" + server + " -U" + user + " -P" + password

        mstartmp = mstarpaths.interpretPath("{MSTAR_TEMP}")
        filename = os.path.basename(script)

        runFile = mstartmp + os.sep + filename
        print("runFile = " + runFile)

        sqlcmd += " -i" + runFile + " -m 1"

        if filename != "schema_drop_all.sql":
            sqlcmd += " -h -1"

        countfile = 0
        if filename == "schema_drop_all.sql":
            fileoutname = os.path.splitext(filename)[0] + "out.sql"
            tmpfile = mstartmp + os.sep + fileoutname
            sqlcmd += " -o" + tmpfile
            countfile = 1

        self.createTempFile(script, runFile, args)

        minestar.run(sqlcmd)
        minestar.logit("running command " + self.clearUserAndPassword(sqlcmd, user, password))

        if countfile == 1:
            countfile = 0

            tmprunfile = mstartmp + os.sep + os.path.splitext(filename)[0] + "run.sql"
            self.createTempFile(tmpfile, tmprunfile, args)

            if sys.platform.startswith("win"):
                sqlcmd2 = mstarpaths.interpretPath("sqlcmd{EXE}") + " -S" + databaseserver + " -U" + user + " -P" + password
            else:
                sqlcmd2 = mstarpaths.interpretPath("sqlcmd{EXE}") + " -H" + server + " -U" + user + " -P" + password
            cmd2 = sqlcmd2 + " -i" + tmpfile
            minestar.run(cmd2)
            minestar.logit("running command " + self.clearUserAndPassword(cmd2, user, password))

    def createTempFile(self, inputFile, outputFile, args=[]):
        with open(inputFile, "r") as infile, open(outputFile, "w+") as outfile:
            outfile.seek(0)
            outfile.truncate()
            for line in infile:
                if args:
                    count = 1
                    for arg in args:
                        vartoreplace = "$(var" + str(count) + ")"
                        line = str.replace(line, vartoreplace, arg)
                        count += 1
                outfile.write(line)

    def _interpret(self, path, overrides):
        import mstarpaths
        path = mstarpaths.interpretPathOverride(path, overrides)
        return mstarpaths.interpretPath(path)

    def _getInstanceOverrides(self, homeDir, ds):
        overrides = {"HOME": homeDir, "INSTANCE": ds.instance}
        if sys.platform.startswith("win"):
            overrides["DRIVE"] = ":"
            overrides["PWDFILE_DIR"] = "database"
        else:
            overrides["DRIVE"] = ""

        # overrides["ORADIM"] = mstarpaths.interpretPath("{ORACLE_HOME}/bin/oradim{EXE}")
        # overrides["ORAPWD"] = mstarpaths.interpretPath("{ORACLE_HOME}/bin/orapwd{EXE}")
        return overrides

    def validateExport(self, logFile, fileName):
        return False, 0, 0

    def sqlcmdForExport(self, ds, script, user, password, filename=None, args=[]):
        import mstarpaths, ServerTools
        server = ServerTools.getCurrentDatabaseServer()
        databaseserver = ServerTools.getDatabaseInstanceServerName(server, ds)
        sqlcmd = mstarpaths.interpretPath("sqlcmd{EXE}") + " -S" + databaseserver + " -U" + user + " -P" + password
        cmd = sqlcmd + " -i" + script
        if filename:
            cmd = cmd + " -o" + filename

        if args:
            cmd = cmd + " -v"
            count = 1
            for arg in args:
                cmd += " var" + str(count) + "=" + "\"" + arg + "\""
                count += 1

        minestar.run(cmd)
        minestar.logit("running command" + self.clearUserAndPassword(cmd, user, password))

    def createLinkServer(self, ds, serverrole):
        import mstarpaths, ServerTools
        standbyServer = ServerTools.getStandbyDatabaseServer()
        productionServer = ServerTools.getProductionDatabaseServer()
        instanceName = ds.instance
        sysUser = self.sysUser
        sysPass = self.sysPassword
        linktostandby = standbyServer + os.sep + instanceName
        linktoproduction = productionServer + os.sep + instanceName
        if serverrole == "standby":
            linkServer = linktoproduction
        else:
            linkServer = linktostandby
        self.sqlcmdForLinkedServers(ds, serverrole,
                                    mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/dblinks/create_dblink.sql"),
                                    sysUser, sysPass, [linkServer])
        self.sqlcmdForLinkedServers(ds, serverrole,
                                    mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/dblinks/dblink_domainlogin.sql"),
                                    sysUser, sysPass, [linkServer])

    def sqlcmdForLinkedServers(self, ds, serverrole, script, user, password, args=[]):
        import mstarpaths, ServerTools
        if serverrole == "standby":
            server = ServerTools.getStandbyDatabaseServer()
        else:
            server = ServerTools.getProductionDatabaseServer()
        databaseserver = ServerTools.getDatabaseInstanceServerName(server, ds)
        sqlcmd = mstarpaths.interpretPath("sqlcmd{EXE}") + " -S" + databaseserver + " -U" + user + " -P" + password
        cmd = sqlcmd + " -i" + script + " -m 1"
        if args:
            cmd = cmd + " -v"
            count = 1
            for arg in args:
                cmd += " var" + str(count) + "=" + "\"" + arg + "\""
                count += 1

        minestar.run(cmd)
        minestar.logit("running command" + self.clearUserAndPassword(cmd, user, password))

    def clearUserAndPassword(self, cmd, user, password):
        return cmd.replace("-P"+password, "-P********").replace("-P\""+password+"\"", "-P********").replace("-U"+user, "-U********")

    def trashSQLServerDb(self, homeDir, ds):
        import mstarpaths

        if sys.platform.startswith("win"):
            self.checkCorrectComputer()

        sysUser = self.sysUser
        sysPass = self.sysPassword
        dbPrefix = mstarpaths.interpretVar("_DBPREFIX")
        readOnlyUser = mstarpaths.interpretVar("_READONLYUSER")
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/trash_sqlServer_Db.sql"),
                    sysUser, sysPass, [dbPrefix, readOnlyUser])
        print "Trashed all the instances of %s" % dbPrefix

    def checkCorrectComputer(self):
        import ServerTools
        thisComputer = ServerTools.getCurrentServer()
        allowedHosts = ServerTools.getAllowedDatabaseHosts()
        if not thisComputer.upper() in allowedHosts:
            print i18n.translate("You can only do this operation while running on one of %s. This host is %s.") % (
            allowedHosts, thisComputer)
            import minestar
            minestar.pauseAndExit(73)
        else:
            currentDatabaseServer = ServerTools.getCurrentDatabaseServer()
            if currentDatabaseServer != thisComputer:
                print i18n.translate(
                    "current database server is different from local system.Do you want to continue trash server?")
                userinput = raw_input("Press y or n")
                if userinput != 'y' or userinput != 'Y':
                    import minestar
                    minestar.pauseAndExit(73)

    def dropDbUser(self, ds, fromStandBy):
        import mstarpaths
        sysUser = self.sysUser
        sysPass = self.sysPassword
        dbuser = ds.user
        self.sqlcmd(ds, mstarpaths.interpretPathShort(self.SQL_SCRIPTS + "/SchemaUtilities/drop_db_user.sql"), sysUser,
                    sysPass, ["STANDBY", fromStandBy, dbuser])


class postgresqldbSpecific(databaseDifferentiator):

    """PostgreSQL implementation of database."""

    @databaseDifferentiator.sysUser.getter
    def sysUser(self):
        # Get the defined sys user, or fallback to 'postgres'.
        result = databaseDifferentiator.sysUser.fget(self)
        if result is None:
            result = "postgres"
        return result

    @databaseDifferentiator.sysPassword.getter
    def sysPassword(self):
        # Get the defined sys password, or fallback to 'postgres'.
        result = databaseDifferentiator.sysPassword.fget(self)
        if result is None:
            result = "postgres"
        return result

    def getDBString(self):
        return "postgresql"

    def dbURLPattern(self):
        return "jdbc:postgresql:@%s"

    def thinURLPattern(self):
        return ""

    def reportingRepository(self):
        return "false"

    def homeDir(self):
        if "POSTGRESQL_HOME" not in os.environ:
            raise Exception("POSTGRESQL_HOME environment variable is not set")
        ohome = os.environ["POSTGRESQL_HOME"]
        if ohome.endswith(os.sep):
            ohome = ohome[:-1]
        return ohome

    def finddbHome(self, sources, config):
        # Database may be running remotely.
        if "POSTGRESQL_HOME" in os.environ:
            config["POSTGRESQL_HOME"] = self.homeDir()
            sources["POSTGRESQL_HOME"] = "(operating system environment)"
        else:
            config["POSTGRESQL_HOME"] = "(not found)"
            sources["POSTGRESQL_HOME"] = "(not found)"

    def setDefines(self, defines):
        import mstarpaths
        defines["POSTGRESQL_HOME"] = mstarpaths.interpretPath("{POSTGRESQL_HOME}")

    def getDatabaseExtensions(self, config):
        return ["Platform/Database/PostgreSQL"]

    def returnLibraryPath(self):
        return os.path.join(self.homeDir(), "lib")
