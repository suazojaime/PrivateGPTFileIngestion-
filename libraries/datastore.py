import minestar
logger = minestar.initApp()
import string, os, sys, i18n, mstardebug, databaseDifferentiator, re
import mstarpaths, progress, ufs, ServerTools, mstarrun

mstarpaths.loadMineStarConfig()

dataStorePool = {}
dbobject = databaseDifferentiator.returndbObject()
FREE_EXTENTS_PERCENT = 40
ORACLE_SCRIPTS = "{MSTAR_DATABASE}/oracle"
NO_LOGICAL_NAME = "(undefined)"
# same as ORACLE_SCRIPTS, but for the UFS
ORACLE_UFS = "/bus/database/oracle"
OCI9_URL_PATTERN = dbobject.dbURLPattern();
THIN_URL_PATTERN = dbobject.thinURLPattern()

COUNT_AGED_ENTITIES = """select count(*), class_id from %s group by class_id"""


FUNCTION_PARAMS = {
    "SERVER" : { "_MODELDB" : ("model", 100), "_HISTORICALDB" : ("historical", 1000), "_TEMPLATEDB" : ("template", 15), "_REPORTINGDB" : ("reporting", 60),"_BOAUDITDB" : ("boaudit", 60),"_CFG":("config",60),"_DVL":("",60),"_DWH":("datawarehouse",60),"_DCL":("",60) },
    "LAPTOP" : { "_MODELDB" : ("model", 60), "_HISTORICALDB" : ("historical", 100), "_TEMPLATEDB" : ("template", 15), "_REPORTINGDB" : ("reporting", 60),"_BOAUDITDB" : ("boaudit", 60), "_CFG":("config",60),"_DVL":("",60),"_DWH":("datawarehouse",60),"_DCL":("",60) }
    }

class NoODBCError:
    def __init__(self, mesg):
        self.mesg = mesg

def getDefaultDatabaseHost():
    defaultHost = ServerTools.getCurrentDatabaseServer()
    if defaultHost is None:
        defaultHost = "localhost"
    return defaultHost

def isOracleXE():
    minestar.logit("datastore.isOracleXE: Started")
    oracleHome = mstarpaths.interpretPath("{ORACLE_HOME}")
    minestar.logit("datastore.isOracleXE: Oracle home %s" % oracleHome)
    try:
        oracleExeIndex =  oracleHome.index("oraclexe")
        minestar.logit("datastore.isOracleXE: Using Oracle Express")
        return True
    except ValueError:
        minestar.logit("datastore.isOracleXE: Not using Oracle Express")
        return False

def expectedResultCodes():
    """Return the result codes expected from DataStore.probe().  We call checkDataStores to get this information
       so it is only stored in one place"""
    if not hasattr(DataStore, 'expected'):
        DataStore.expected = [ 'OK' ]
        DataStore.expected.extend(minestar.mstarrunEvalRaw(['checkDataStores', '-resultCodes']))
    return DataStore.expected

class DataStore:
    def __init__(self, logicalName, dbRole=None):
        minestar.logit("datastore.DataStore.__init__: logicalName %s  " % logicalName);
        self.valid = 0
        # the size in megabytes of the file chunks for the instance
        self.filesize = 60
        # the function of the data store, e.g. model or historical
        self.function = "unknown"
        if logicalName is not None:
            self.desc = mstarpaths.interpretFormat("{%s}" % logicalName)
            self._guessFunction(logicalName)
            self.logicalName = logicalName
            dbPrefix = None
            if logicalName in ["_MODELDB", "_TIMESERIESDB", "_HISTORICALDB", "_TEMPLATEDB", "_SUMMARYDB", "_REPORTINGDB", "_PITMODELDB", "_GISDB", "_BOAUDITDB","_CFG", "_DVL", "_DWH", "_DCL"]:
                dbPrefix = mstarpaths.interpretVar("_DBPREFIX")
            if dbPrefix is None:
                dbPrefix = ""
            fields = self.desc.split()

            minestar.logit("datastore.DataStore.__init__: len(fields) %s  " % len(fields));
            if len(fields) != 4 and len(fields) != 3 and len(fields) != 2:
                error = i18n.translate("The %s data store is badly defined - 2, 3 or 4 fields expected, %d found!") % (logicalName, len(fields))
                print error
                return

            if len(fields) == 4:
                self.role = fields[0]
                self.instance = fields[1]
                self.user = dbPrefix+fields[2]
                self.password = dbPrefix+fields[3]
            elif len(fields) == 3:
                self.role = mstarpaths.interpretVar("_DBROLE")
                self.instance = fields[0]
                self.user = dbPrefix+fields[1]
                self.password = dbPrefix+fields[2]
            else:
                self.user = dbPrefix+fields[0]
                self.password = dbPrefix+fields[1]
                self.role = mstarpaths.interpretVar("_DBROLE")
                self.instance = mstarpaths.interpretVar("_INSTANCE1")
                self.instance2 =mstarpaths.interpretVar("_INSTANCE2")
            #minestar.logit("datastore.DataStore.__init__: self.instance  " % self.instance);
            #minestar.logit("datastore.DataStore.__init__: mstarpaths.interpretVar(\"_INSTANCE1\")  " % mstarpaths.interpretVar("_INSTANCE1"));
            if dbRole is not None:
                self.role = dbRole
            self.create(self.logicalName, self.role, self.instance, self.user, self.password)
            if len(fields) >= 5 and fields[4] != "~":
                self.exportType = fields[4]
            if len(fields) >= 6 and fields[5] != "~":
                self.backupTime = fields[5]

    def create(self, logicalName, role, instance, username, password):
        self.logicalName = logicalName
        self.role = role
        self.instance = instance
        self.user = username
        self.password = password
        self.instanceName = "%s_%s" % (self.instance, self.role)
        self.connectionString = "%s/%s@%s" % (self.user, self.password, self.instanceName)
        self.printConnectionString = "%s/********@%s" % (self.user,self.instanceName)
        if(dbobject.getDBString()=="Oracle"):
            if self.user.upper() == "SYS":
                self.connectionString = '"%s as SYSDBA"' % self.connectionString
                self.printConnectionString = '"%s as SYSDBA"' % self.printConnectionString
        self.linkName = ("%s_%s" % (self.user, self.instanceName)).upper()
        if(dbobject.getDBString()=="Oracle"):
            self.jdbcUrl = OCI9_URL_PATTERN % self.instanceName
        else:
            portRolesSpec = mstarpaths.interpretVar("_DB_PORT")
            portNumber = ""
            if portRolesSpec is not None and portRolesSpec != '':
                portRoles = eval(portRolesSpec)
                if(role in portRoles):
                    portNumber = ":" + portRoles[role]
            self.jdbcUrl = OCI9_URL_PATTERN % (self.instanceName + portNumber)

        host = ServerTools.getDatabaseServer(role)
        if(THIN_URL_PATTERN==""):
            self.thinUrl =""
        else:
            self.thinUrl = THIN_URL_PATTERN % (host, self.instance)
        self.valid = 1
        self.connection = None
        self.extentData = None
        # not sure what this is for
        self.exportType = None
        # time of day to do backup
        self.backupTime = None

    def isSameAs(self, ds):
        "compare this data store to another one and return true if the role, instance and user are the same"
        if ds == None:
            return false
        return self.role == ds.role and self.instance == ds.instance and self.user == ds.user

    def _guessFunction(self, logicalName):
        "Given the logical name of the database, guess the function and filesize"
        size = mstarpaths.interpretVar("MSTAR_SCHEMA_SIZE").upper()
        if FUNCTION_PARAMS.get(size) is None:
            size = "SERVER"
        params = FUNCTION_PARAMS[size].get(logicalName)
        if params is not None:
            (self.function, self.filesize) = params

    def tnsping(self):
        executable = mstarpaths.interpretPath("{ORACLE_HOME}/bin/tnsping{EXE}")
        command = "%s %s" % (executable, self.instanceName)
        minestar.logit(command)
        output = minestar.systemEvalRaw(command)
        if len(output) == 0:
            return 0
        return output[-1].startswith("OK")

    def checkCorrectComputer(self):
        thisComputer = ServerTools.getCurrentServer()
        allowedHosts = ServerTools.getAllowedDatabaseHosts()
        if not thisComputer.upper() in allowedHosts:
            print i18n.translate("You can only do this operation while running on one of %s. This host is %s.") % (allowedHosts, thisComputer)
            minestar.pauseAndExit(73)

    def _moveSqlnetOraFile(self):
        sqlnetFile = mstarpaths.interpretPath("{TNS_ADMIN}/sqlnet.ora")
        backupFile = sqlnetFile + ".backup"
        if os.access(sqlnetFile, os.F_OK):
            minestar.logit("Moving %s to %s, because it stops us from working" % (sqlnetFile, backupFile))
            minestar.move(sqlnetFile, backupFile, True)

    def _getInstanceOverrides(self, homeDir):
        overrides = { "HOME" : homeDir, "INSTANCE" : self.instance }
        if sys.platform.startswith("win"):
            overrides["DRIVE"] = ":"
            overrides["PWDFILE_DIR"] = "database"
        else:
            overrides["DRIVE"] = ""
            overrides["PWDFILE_DIR"] = "dbs"
        overrides["ORADIM"] = mstarpaths.interpretPath("{ORACLE_HOME}/bin/oradim{EXE}")
        overrides["ORAPWD"] = mstarpaths.interpretPath("{ORACLE_HOME}/bin/orapwd{EXE}")
        return overrides

    def _findOracleDirectory(self, name, homeDir):
        pathname = mstarpaths.interpretPath("{ORACLE_HOME}/../%s/%s" % (name, self.instance))
        if os.access(pathname, os.F_OK):
            return pathname
        pathname = mstarpaths.interpretPath("{ORACLE_HOME}/%s/%s" % (name, self.instance))
        if os.access(pathname, os.F_OK):
            return pathname
        overrides = self._getInstanceOverrides(homeDir)
        pathname = _interpret("{HOME}{DRIVE}" + INSTANCE_DATA, overrides)
        return pathname

    def trashInstance(self, homeDir, ds=None):
        if dbobject.getDBString()=="Oracle":
            """Do everything possible to remove all trace of this instance"""

            if sys.platform.startswith("win"):
                self.checkCorrectComputer()

            minestar.logit("trashInstance %s" % self.instance)
            overrides = self._getInstanceOverrides(homeDir)
            initOra = _interpret(INIT_ORA, overrides)

            instanceOra = _interpret(INSTANCE_ORA, overrides)
            if os.access(initOra, os.F_OK):
                print "Trashing %s" % initOra
                os.remove(initOra)
            if os.access(instanceOra, os.F_OK):
                print "Trashing %s" % instanceOra
                os.remove(instanceOra)
            if sys.platform.startswith("win"):
                print i18n.translate("Trashing %s service" % self.instance)
                minestar.run(_interpret(ORADIM_TRASH_COMMAND, overrides))
            else:
                print i18n.translate("Stopping %s service" % self.instance)
                minestar.run(_interpret(STOP_SERVICE_COMMAND, overrides))
                minestar.pause(_interpret("You must now remove this entry in the /etc/oratab: %s:{ORACLE_HOME}:Y <Hit enter to continue>" % self.instance, overrides))
            spfileOra = _interpret(INSTANCE_SPFILE, overrides)
            if os.access(spfileOra, os.F_OK):
                print "Trashing %s" % spfileOra
                os.remove(spfileOra)

            # trash the admin files live
            print i18n.translate("Trashing %s admin files" % self.instance)
            adminDir = _interpret(INSTANCE_ADMIN, overrides)
            try:
                minestar.rmdir(adminDir)
            except OSError:
                # file is in use
                print i18n.translate("%s admin files are in use, waiting...." % self.instance)
                import time
                time.sleep(5)
                print i18n.translate("Retrying trashing %s admin files" % self.instance)
                minestar.rmdir(adminDir)

            # trash the data files
            print i18n.translate("Trashing %s data files") % self.instance
            dataDir = _interpret("{HOME}{DRIVE}" + INSTANCE_DATA, overrides)
            try:
                minestar.rmdir(dataDir)
            except OSError:
                # control01.ctl is in use
                print i18n.translate("%s data files are in use, waiting...." % self.instance)
                import time
                time.sleep(3)
                print i18n.translate("Retrying trashing %s data files" % self.instance)
                minestar.rmdir(dataDir)
            pwdFile = _interpret(mstarpaths.interpretPath(INSTANCE_PWDFILE), overrides)
            if os.access(pwdFile, os.F_OK):
                print i18n.translate("Trashing %s password file" % self.instance)
                os.remove(pwdFile)
            controlFile = mstarpaths.interpretPath("%s/control01.ctl" % _interpret(INSTANCE_ADMIN, overrides))
            if os.access(controlFile, os.F_OK):
                print i18n.translate("Control file %s still exists!") % controlFile
        else:
            dbobject.trashSQLServerDb(homeDir, ds)

    def createAdminUser(self):
        mstarrun.run("createDbAdmin")

    def createInstance(self, homeDir, dataDirs,reporting=False):
        """Assuming that this instance does not exist, create it."""
        # minestar.logit("datastore.createInstance: started")

        if sys.platform.startswith("win"):
            self.checkCorrectComputer()

        overrides = self._getInstanceOverrides(homeDir)
        # minestar.logit("datastore.createInstance: overrides is  %s " % overrides)
        dirs = [ _interpret(d, overrides) for d in CREATE_INSTANCE_DIRS ]
        dirs = dirs + [ _interpret(d + overrides["DRIVE"] + INSTANCE_DATA, overrides) for d in dataDirs ]
        for d in dirs:
            try:
                os.makedirs(d)
            except OSError:
                # already exists
                pass

        # create service
        if sys.platform.startswith("win"):
            progress.nextTask(0.02, "Creating Oracle service")

            # minestar.logit("datastore.createInstance: creating Oracle service using minestar.run(%s) " % _interpret(ORADIM_10G_COMMAND % INIT_ORA, overrides))
            print i18n.translate("Creating Oracle service")
            minestar.run(_interpret(ORADIM_10G_COMMAND % INIT_ORA, overrides))
            # minestar.logit("datastore.createInstance: Finished creating Oracle service")

        # instantiate scripts
        progress.task(0.02, "Copying initialisation files")
        print i18n.translate("Copying initialisation files")
        # minestar.logit("datastore.createInstance: Calling _makeSubsts")
        substs = _makeSubsts(self.instance, self.instanceName, homeDir, dataDirs, self.filesize)

        if not sys.platform.startswith("win"):
            progress.nextTask(0.02, "Creating Oracle instance files")
            print i18n.translate("Creating Oracle instance files")
           #  minestar.logit("datastore.createInstance: Not windows: Running ORAPWD_COMMAND")
            minestar.run(_interpret(ORAPWD_COMMAND, overrides))

        # it seems that if Oracle is running a TNS listener for the service (e.g. because it
        # used to exist), you MUST use TNS to connect. However, if Oracle is not running such a
        # listener, you MUST NOT use TNS to connect. Consequently we have to know whether the
        # TNS listener is going or not to know how to connect.
        minestar.logit("datastore.createInstance: Calling tnsping")
        if self.tnsping():
            substs["_CONNECT_STRING"] = "@%s" % self.instanceName
        else:
            substs["_CONNECT_STRING"] = ""

        minestar.logit("datastore.createInstance: Calling _instantiate for initOraTemplate")
        size = mstarpaths.interpretVar("MSTAR_SCHEMA_SIZE").upper()
        if isOracleXE():
            _instantiate(INITXE_ORA_TEMPLATE, INIT_ORA, overrides, substs)
        elif size == "SERVER":
            if reporting:
                _instantiate(INIT_ORA_TEMPLATE_REPORTING,INIT_ORA,overrides,substs)
            else:
                _instantiate(INIT_ORA_TEMPLATE, INIT_ORA, overrides, substs)
        else:
            if reporting:
                _instantiate(INIT_ORA_LAPTOP_TEMPLATE_REPORTING, INIT_ORA, overrides, substs)
            else:
                _instantiate(INIT_ORA_LAPTOP_TEMPLATE, INIT_ORA, overrides, substs)
        minestar.logit("datastore.createInstance: Calling _instantiate for INITSID_ORA")
        _instantiate(INITSID_ORA_TEMPLATE, INSTANCE_ORA, overrides, substs)
        if reporting:
            _instantiate(CREATE_TABLESPACES_TEMPLATE_REPORTING, CREATE_TABLESPACES, overrides, substs)
            _instantiate(CREATE_DATABASE_TEMPLATE_REPORTING, CREATE_DATABASE, overrides, substs)
            _instantiate(CREATE_DICTIONARY_TEMPLATE_REPORTING, CREATE_DICTIONARY, overrides, substs)
            createScript = _interpret(CREATE_DATABASE, overrides)
            dictionaryScript = _interpret(CREATE_DICTIONARY, overrides)
            tablespaceScript = _interpret(CREATE_TABLESPACES, overrides)
        else:
            _instantiate(CREATE_TABLESPACES_TEMPLATE, CREATE_TABLESPACES, overrides, substs)
            _instantiate(CREATE_DATABASE_TEMPLATE, CREATE_DATABASE, overrides, substs)
            _instantiate(CREATE_DICTIONARY_TEMPLATE, CREATE_DICTIONARY, overrides, substs)
            createScript = _interpret(CREATE_DATABASE, overrides)
            dictionaryScript = _interpret(CREATE_DICTIONARY, overrides)
            tablespaceScript = _interpret(CREATE_TABLESPACES, overrides)

        # create_database script
        progress.nextTask(0.40, "Creating Oracle instance")
        # minestar.logit("datastore.createInstance: Creating Oracle instance")
        print i18n.translate("Creating Oracle instance")
        _sqlplusWithSID(self.instance, ["/NOLOG", "@" + createScript])
        # create_dictionary script
        progress.nextTask(0.40, "Creating Oracle dictionary")
        print i18n.translate("Creating Oracle dictionary")
        # minestar.logit("datastore.createInstance: Creating Oracle dictionary")
        _sqlplusWithSID(self.instance, ["/NOLOG", "@" + dictionaryScript])
        #
        if not sys.platform.startswith("win"):
            minestar.pause(_interpret("You must now add this entry in the /etc/oratab: %s:{ORACLE_HOME}:Y <Hit enter to continue>" % self.instance, overrides))
        #
        progress.nextTask(0.02, "Reconfiguring Oracle service")
        print i18n.translate("Reconfiguring Oracle service")
        # minestar.logit("datastore.createInstance: Reconfiguring Oracle service")
        minestar.run(_interpret(START_SERVICE_COMMAND, overrides))
        #
        progress.nextTask(0.10, "Creating tablespaces")
        print i18n.translate("Creating tablespaces")
        # minestar.logit("datastore.createInstance: Creating tablespaces")
        _sqlplusWithSID(self.instance, ["/NOLOG", "@" + tablespaceScript])
        #
        progress.nextTask(0.01, "Fixing sqlnet.ora")
        # minestar.logit("datastore.createInstance: Fixing sqlnet.ora")
        self._moveSqlnetOraFile()
        #
        progress.nextTask(0.02, "Adding to listener.ora and restarting listener")
        # minestar.logit("datastore.createInstance: adding to listener.ora")
        dbobject.updateListenerOra(self.instance)
        # minestar.logit("datastore.createInstance: restarting listener")
        restartListener()
        #
        # minestar.logit("Done")
        progress.done()

    def dbdataman(self, option, script, batchSize=5000):
        if option[0] != '-':
            raise "Incorrect argument to dbdataman"
        return minestar.mstarrunEvalLines(["minestar.platform.persistence.service.importexport.DBDataMan", option, self.logicalName, self.role, `batchSize`, script])

    def sqlplus(self, script, args=None):
        """Execute a script against this database using sqlplus."""
        if not isSqlplusAvailable():
            minestar.logit("sqlplus %s %s: sqlplus not available" % (self.connectionString, script))
            return
        if args is not None:
            argStr = string.join(args)
        else:
            argStr = ""
        sqlplus = mstarpaths.interpretPath("{ORACLE_HOME}/bin/sqlplus{EXE} -L -s")
        if len(script) < 70:
            command = "%s %s @%s %s" % (sqlplus, self.connectionString, script, argStr)
            prntcommand = "%s %s @%s %s" % (sqlplus, self.printConnectionString, script, argStr)
            minestar.logit(prntcommand)
            minestar.run(command)
        else:
            # Oracle cannot cope with the length of the script name!
            # Try to shorten it by changing directories.
            # This could break logging which we want in the current directory.
            cwd = os.getcwd()
            initScript = script
            (directory, script) = os.path.split(initScript)
            os.chdir(directory)
            minestar.logit("'%s' is too long for sqlplus, temporarily changing from %s to %s" % (initScript, cwd, os.getcwd()))
            command = "%s %s @%s %s" % (sqlplus, self.connectionString, script, argStr)
            minestar.logit(command)
            minestar.run(command)
            os.chdir(cwd)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def select(self, sql):
        self.connect()
        cursor = self.connection.cursor()
        cursor.execute(sql)
        metadata = cursor.description
        data = cursor.fetchall()
        cursor.close()
        return (metadata, data)

    def _getThinURL(self):
        if self.thinUrl is None:
            return "null"
        else:
            return self.thinUrl

    def javaSelect(self, sql):
        """
        Do a select by invoking a Java program. This is slower, but
        does not require mxODBC or anything.
        """
        debug = "false"
        if mstardebug.debug:
            debug = "true"
        if self.role != "PRODUCTION":
            dbName = self.role+"."+self.logicalName
        else:
            dbName = self.logicalName
        command = ["com.mincom.tool.scripting.python.PythonSelect", dbName, sql, debug]
        output = minestar.mstarrunEval(command)
        if output is None:
            return None
        parts = output.split("QUERY RESULT: ")
        if len(parts) > 1:
            output = parts[len(parts)-2]
            if output == '[]':
                return None
            return eval(output)
        else:
            return None

    def javaUpdate(self, sql):
        """
        Do an update by invoking a Java program. This is slower, but
        does not require mxODBC or sqlplus.
        """
        if self.role != "PRODUCTION":
            dbName = self.role+"."+self.logicalName
        else:
            dbName = self.logicalName
        command = ["com.mincom.tool.scripting.python.PythonUpdate", dbName, sql]
        output = minestar.mstarrunEval(command)
        if output is None or output == "(no output)":
            return None
        parts = output.split("QUERY RESULT: ")
        if len(parts) > 1:
            output = parts[len(parts)-2]
            return eval(output)
        else:
            return None

    def dbName(self):
        return self.role+"."+self.logicalName

    def probe(self, debug = "false"):
        """
        Check to see whether the instance is working.
        Possible responses are:
         * OK - the datastore seems to be OK
         * BAD - the datastore is bad for an unknown reason
         * URL - the datastore URL could not be used
         * USER - bad user name or password
         * READONLYUSER - bad readonly user name or password
         * INSTANCE - the instance could not be contacted
         * DRIVER - the JDBC driver could not be loaded
        """
        dbName = self.dbName()
        command = ["checkDataStores", dbName, debug, "-xml"]
        # debug mode interferes with interpreting the results
        # mstardebug is probably already loaded, so get rid of it to force reloading from the new file
        del sys.modules["mstardebug"]
        import mstardebug
        if mstardebug.debug:
            print "************************************************"
            print "WARNING: debug is on - checkDataStores will fail"
            print "************************************************"
            minestar.logit("************************************************")
            minestar.logit("WARNING: debug is on - checkDataStores will fail")
            minestar.logit("************************************************")

        # Run the checkDataStores command
        expected = expectedResultCodes()
        output = minestar.mstarrunEvalRaw(command)
        minestar.logit("Output from CheckDataStores follows...")
        minestar.logit(output);

        # Parse result
        isResult = re.compile("<result>(\w+)</result>")
        status = "NONE"
        for part in output:
            match = isResult.match(part)
            if match:
                status = match.group(1)
                break

        # Check status is valid
        if status not in expected:
            print "************************************************************************"
            print "ERROR: Unexpected result '" + status + "' from checkDataStores"
            print "OUTPUT:"
            print ("\n").join(output)
            print "************************************************************************"
            status = "BAD"
        return status

    def execute(self, sqls):
        # allowed to pass in one string
        if type(sqls) == type(""):
            sqls = [sqls]
        self.connect()
        cursor = self.connection.cursor()
        for sql in sqls:
            cursor.execute(sql)
        cursor.close()
        self.commit()

    def getAllLinks(self):
        return self.javaSelect("select DB_LINK, USERNAME, PASSWORD, HOST from USER_DB_LINKS")

    def detectODBC(self):
        "Returns an error message or else empty string"
        mesg = handleError(self.execute, "select * from dual")
        if type(mesg) != type(""):
            mesg = ""
        return mesg

    def dropAll(self,db=None,fromStandBy=None):
        if(dbobject.getDBString()=="Oracle"):
            self.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/schema_drop_all.sql"))
        else :
            dbobject.dropall(db,fromStandBy)


    def reimport(self, filename,db=None,fromStandBy=None):
        if(dbobject.getDBString()=="Oracle"):
            self.dropAll()
            self.imp(filename)
        else:
            dbobject.restore(filename,db,fromStandBy)
            dbobject.dropDbUser(db,fromStandBy)
            #calling checkdatastores for standby db
            if fromStandBy=='true':
                dbobject.createUser(db,fromStandBy)
                dbobject.refreshUser(db,fromStandBy)
            else:
                mstarrun.run("checkDataStores")


    def coalesceTablespaces(self):
        """Let Oracle reclaim space for dropped objects"""
        self.sqlplus(mstarpaths.interpretPathShort("{MSTAR_HOME}/bus/mstarrun/sql/coalesce_tablespaces.sql"))

    def dropDBLink(self, linkName):
        #get current links so we can see if link actually exists
        links = self.getAllLinks()
        if links is None:
            minestar.fatalError("datastore.py", "Cannot find database links - database connection must be broken")
        for row in links:
            if row[0].upper() == linkName.upper():
                self.sqlplus(mstarpaths.interpretPathShort("{MSTAR_HOME}/bus/mstarrun/sql/drop_db_link.sql"), [linkName])
                return

    def dropAllDBLinks(self):
        links = self.getAllLinks()
        if links is None:
            minestar.fatalError("datastore.py", "Cannot find database links - database connection must be broken")
        for row in links:
            self.dropDBLink(row[0])

    def createDBLink(self, targetDB):
        "Create a link from this database to targetDB"
        if type(targetDB) == type(""):
            target = getDataStore(targetDB)
        elif type(targetDB) == type(self):
            target = targetDB
        else:
            raise "Target DB must be a logical name or a DataStore object"
        self.sqlplus(mstarpaths.interpretPathShort("{MSTAR_HOME}/bus/mstarrun/sql/create_db_link.sql"),
            [ target.linkName, target.instanceName, target.user, target.password ])

    def exp(self, filename):
        command = "exp %s FILE=%s" % (self.connectionString, filename)
        minestar.run(command)

    def expWithOptions(self, optionString,db=None,filename=None,snapshot=0):
        if(dbobject.getDBString()=="Oracle"):
            oraHome = mstarpaths.interpretPath("{ORACLE_HOME}")
            if oraHome == "(no Oracle installed)":
                mesg = i18n.translate("ORACLE_HOME not set")
                minestar.logit(mesg)
                logger.info(mesg)
                return "Fail"
            optionFile = minestar.getTemporaryFileName("exp")
            file = open(optionFile, "w")
            file.write(optionString)
            file.close()
            #expdp command export on the server , not on the client machine, SO it should be run on DB server.
            if ServerTools.onDbServer() and ((db.logicalName=='_SUMMARYDB'and snapshot==0) or (db.logicalName=='_HISTORICALDB')):
                command = "expdp %s parfile=%s" % (self.connectionString, optionFile)
            else:
                command = "exp %s parfile=%s" % (self.connectionString, optionFile)
            return minestar.run(command)

        else:
            return dbobject.backUpDatabase(db,filename)

    def expExtended(self, options):

        command = "exp %s %s" % (self.connectionString, options)
        minestar.run(command)

    def imp(self, filename,db=None,fromStandBy=None):
        if(dbobject.getDBString()=="Oracle"):
            dirname = os.path.dirname(filename)
            basefilename = os.path.basename(filename)
            logfile = basefilename[0:-4]
            datapump=0
            if "DATAPUMP" in basefilename:
                self.datapumpReadWrite(dirname)
                usernameStart =basefilename.find('PUMP')+4
                username = basefilename[usernameStart:-4]
                command = "impdp %s DUMPFILE=%s DIRECTORY=datapump" % (self.connectionString, basefilename)
                command = command + " remap_schema=" +username+ ":"+self.user+ " TABLE_EXISTS_ACTION='REPLACE'  Transform=OID:n JOB_NAME= 'IMPORT_DUMP'"
                datapump=1
            else:
                command = "imp %s FILE=%s FULL=Y IGNORE=Y" % (self.connectionString, filename)
            import subprocess
            proc = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE)
            for line in iter(proc.stderr.readline,''):
                if'IMP-00010' in line:
                    print('---The dump you are importing seems to be from a higher version of Oracle. Import the dump from the same version of Oracle. '
                          '\nFor more information please contact DBA.---')
                    sys.exit(1)
                print(line.rstrip())
                sys.stdout.flush()
            proc.stderr.close()
            if(datapump==1):
                print i18n.translate("Ignore Errors: ORA-39083,ORA-39082,ORA-01917")

        else:
            dbobject.restore(filename,db,fromStandBy)
            dbobject.dropDbUser(db,fromStandBy)
            #calling checkdatastores for standby db
            if fromStandBy=='true':
                dbobject.createUser(db,fromStandBy)
                dbobject.refreshUser(db,fromStandBy)
            else:
                os.system("mstarrun checkDataStores")


    def createTableSpaces(self, homeDir, dataDirs,reporting=False):
        """
        Create the tablespaces in this instance. This is normally done by createInstance but for OracleXE the instance exists but the tablespaces don't.
        """
        overrides = self._getInstanceOverrides(homeDir)
        minestar.logit("datastore.createTableSpaces: overrides is  %s " % overrides)
        dirs = [ _interpret(d, overrides) for d in CREATE_INSTANCE_DIRS ]
        dirs = dirs + [ _interpret(d + overrides["DRIVE"] + INSTANCE_DATA, overrides) for d in dataDirs ]
        for d in dirs:
            try:
                os.makedirs(d)
            except OSError:
                # already exists
                pass
        substs = _makeSubsts(self.instance, self.instanceName, homeDir, dataDirs, self.filesize)
        # it seems that if Oracle is running a TNS listener for the service (e.g. because it
        # used to exist), you MUST use TNS to connect. However, if Oracle is not running such a
        # listener, you MUST NOT use TNS to connect. Consequently we have to know whether the
        # TNS listener is going or not to know how to connect.
        minestar.logit("datastore.createTableSpaces: Calling tnsping")
        if self.tnsping():
            substs["_CONNECT_STRING"] = "@%s" % self.instanceName
        else:
            substs["_CONNECT_STRING"] = ""
        if isOracleXE() == True:
            _instantiate(STARTUP_TEMPLATE, STARTUP, overrides, substs)
            startupScript = _interpret(STARTUP, overrides)
            _instantiate(SHUTDOWN_TEMPLATE, SHUTDOWN, overrides, substs)
            shutdownScript = _interpret(SHUTDOWN, overrides)
            _instantiate(MOVE_XE_SYSTEM_FILE_TEMPLATE, MOVE_XE_SYSTEM_FILE, overrides, substs)
            _instantiate(SELECT_XE_SYSTEM_FILE_TEMPLATE, SELECT_XE_SYSTEM_FILE, overrides, substs)
            _instantiate(ALTER_XE_SYSTEM_FILE_TEMPLATE, ALTER_XE_SYSTEM_FILE, overrides, substs)
            minestar.logit("datastore.createTableSpaces: Moving system file")
            progress.nextTask(0.10, "Moving system file")
            print i18n.translate("Moving system file")
            cmd = _interpret(MOVE_XE_SYSTEM_FILE, overrides)+" "+_interpret(SELECT_XE_SYSTEM_FILE, overrides)+" "+_interpret(ALTER_XE_SYSTEM_FILE, overrides)+" "+shutdownScript+" "+startupScript
            minestar.logit("datastore.createTableSpaces: Running command %s" % cmd)
            minestar.run(cmd)
            minestar.logit("datastore.createTableSpaces: Finished Moving system file")
            minestar.logit("datastore.createTableSpaces: Copying control file")
            progress.nextTask(0.10, "Copying control file")
            print i18n.translate("Copying control file")
            _instantiate(ALTER_XE_CONTROL_TEMPLATE, ALTER_XE_CONTROL, overrides, substs)
            alterXEControlScript = _interpret(ALTER_XE_CONTROL, overrides)
            _sqlplusWithSID(self.instance, ["/NOLOG", "@" + alterXEControlScript])
            _instantiate(COPY_XE_CONTROL_TEMPLATE, COPY_XE_CONTROL, overrides, substs)
            minestar.run(_interpret(COPY_XE_CONTROL, overrides))
            _sqlplusWithSID(self.instance, ["/NOLOG", "@" + startupScript + " open"])
            minestar.logit("datastore.createTableSpaces: Finished Copying control file")
            minestar.logit("datastore.createTableSpaces: Altering XE database")
            _instantiate(ALTER_XE_DATABASE_TEMPLATE, ALTER_XE_DATABASE, overrides, substs)
            alterDatabaseScript = _interpret(ALTER_XE_DATABASE, overrides)
            progress.nextTask(0.10, "Altering XE database")
            print i18n.translate("Altering XE database")
            _sqlplusWithSID(self.instance, ["/NOLOG", "@" + alterDatabaseScript])
            minestar.logit("datastore.createTableSpaces: Finished altering XE database")
            minestar.logit("datastore.createTableSpaces: Creating and setting XE temporary and undo tablespaces")
            _instantiate(CREATE_XE_TABLESPACES_TEMPLATE, CREATE_XE_TABLESPACES, overrides, substs)
            xeTablespaceScript = _interpret(CREATE_XE_TABLESPACES, overrides)
            progress.nextTask(0.10, "Creating XE temp and undo tablespaces")
            print i18n.translate("Creating XE temp and undo tablespaces")
            _sqlplusWithSID(self.instance, ["/NOLOG", "@" + xeTablespaceScript])
            minestar.logit("datastore.createTableSpaces: Finished creating XE temp and undo tablespaces")
        minestar.logit("datastore.createTableSpaces: Creating tablespaces")
        if reporting:
            _instantiate(CREATE_TABLESPACES_TEMPLATE_REPORTING, CREATE_TABLESPACES, overrides, substs)
            tablespaceScript = _interpret(CREATE_TABLESPACES, overrides)
            progress.nextTask(0.10, "Creating tablespaces for reporting")
            print i18n.translate("Creating tablespaces for reporting")
            _sqlplusWithSID(self.instance, ["/NOLOG", "@" + tablespaceScript])
            minestar.logit("datastore.createTableSpaces: Finished creating tablespaces for reporting")
        else:
            _instantiate(CREATE_TABLESPACES_TEMPLATE, CREATE_TABLESPACES, overrides, substs)
            tablespaceScript = _interpret(CREATE_TABLESPACES, overrides)
            progress.nextTask(0.10, "Creating tablespaces")
            print i18n.translate("Creating tablespaces")
            _sqlplusWithSID(self.instance, ["/NOLOG", "@" + tablespaceScript])
            minestar.logit("datastore.createTableSpaces: Finished creating tablespaces")

    def createUser(self,reporting=False):
        """
        Create a new user in this instance. If the user already exists, it will be updated to have the correct permissions etc.
        """
        syspass = mstarpaths.interpretVar("_DB_SYS_AUTH")
        useradminpass = mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")
        sysDs = self.inSameInstance(mstarpaths.interpretVar("_DB_SUPER_ADMIN"), syspass)
        sysAdminDs = self.inSameInstance(mstarpaths.interpretVar("_DB_ADMIN_USER"), useradminpass)
        if not reporting:
            sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/create_user"), [self.user, self.password])
        else:
            sysDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/create_user_reporting.sql"), [self.user, self.password])

    def createReadOnlyUser(self):
        """
        Create a new user in this instance. If the user already exists, it will be updated to have the correct permissions etc.
        """
        readonlyUser = mstarpaths.interpretVar("_READONLYUSER")
        readonlyPassword = mstarpaths.interpretVar("_READONLYPASSWORD")
        syspass = mstarpaths.interpretVar("_DB_SYS_AUTH")
        useradminpass = mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")
        sysDs = self.inSameInstance(mstarpaths.interpretVar("_DB_ADMIN_USER"), useradminpass)
        sysDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/create_readonly_user"), [readonlyUser, readonlyPassword])
        self.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_readonly_permissions"), [readonlyUser])
        msreadDs = self.inSameInstance(readonlyUser, readonlyPassword)
        msreadDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/create_readonly_synonyms"), [self.user])

    def purgeRecycleBin(self):
        """
        Purge the recycle bin
        """
        syspass = mstarpaths.interpretVar("_DB_SYS_AUTH")
        useradminpass = mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")
        sysDs = self.inSameInstance(mstarpaths.interpretVar("_DB_SUPER_ADMIN"), syspass)
        sysDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/purge_recycle_bin"))

    def refreshUser(self):
        "Update rights of the user"
        minestar.logit("Calling refreshUser for database %s user %s" % (self.logicalName,self.user));
        syspass = mstarpaths.interpretVar("_DB_SYS_AUTH")
        sysDs = self.inSameInstance(mstarpaths.interpretVar("_DB_SUPER_ADMIN"), syspass)
        useradminpass = mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")
        sysAdminDs = self.inSameInstance(mstarpaths.interpretVar("_DB_ADMIN_USER"), useradminpass)
        sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_permissions"), [self.user])
        if self.logicalName == "_HISTORICALDB" or self.logicalName == "_SUMMARYDB" or self.logicalName == "_PITMODELDB" or self.logicalName == "_GISDB":
            modelDs = getDataStore("_MODELDB")
            sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants"), [modelDs.user, self.user.upper(), "ALL"])
            if self.logicalName == "_HISTORICALDB":
                summDs = getDataStore("_SUMMARYDB")
                sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants"), [summDs.user, self.user.upper(), "SELECT"])
            if self.logicalName == "_PITMODELDB":
                histDs = getDataStore("_HISTORICALDB")
                sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants"), [histDs.user, self.user.upper(), "SELECT"])
            templateDs = getDataStore("_TEMPLATEDB")
            sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants"), [templateDs.user, self.user.upper(), "SELECT"])
        if self.logicalName == "_MODELDB":
            histDs = getDataStore("_HISTORICALDB")
            sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants"), [histDs.user, self.user.upper(), "SELECT"])
            summDs = getDataStore("_SUMMARYDB")
            sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants"), [summDs.user, self.user.upper(), "SELECT"])
            pitmodelDs = getDataStore("_PITMODELDB")
            sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants"), [pitmodelDs.user, self.user.upper(), "SELECT"])
            templateDs = getDataStore("_TEMPLATEDB")
            sysAdminDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants"), [templateDs.user, self.user.upper(), "ALL"])
        if self.logicalName == "_CFG":
            dvlDs = getDataStore("_DVL")
            sysDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants_reporting"), [dvlDs.user.upper(), self.user.upper(), "SELECT,REFERENCES"])
        if self.logicalName == "_DVL":
            dwhDs = getDataStore("_DWH")
            sysDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants_reporting"), [dwhDs.user.upper(), self.user.upper(), "SELECT, REFERENCES"])
        if self.logicalName == "_DWH":
            dvlDs = getDataStore("_DVL")
            sysDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/SchemaUtilities/set_user_grants_reporting"), [dvlDs.user.upper(), self.user.upper(), "SELECT, REFERENCES"])

    def inSameInstance(self, userName, password):
        """Return a data store object which is in the same instance as this one, but with a different user.
           Note that this does not modify the database, it just creates a DataStore object.
        """
        return createDataStore(self.role, self.instance, userName, password)

    def countAgedEntities(self):
        entities = {"HEALTH_EVENT", "ADMIN_EVENT", "ASSIGNMENT_EVENT", "NOTIFICATION_EVENT", "PRODUCTION_EVENT"}
        result = 0
        for entity in entities:
            count_output = self.javaSelect(COUNT_AGED_ENTITIES % entity)
            if count_output:
                for select_tuple in count_output:
                    result += select_tuple[0]
        return result

    def datapumpReadWrite(self,dir):
        """This method is used to provide read write grants on datapump directory"""
        syspass = mstarpaths.interpretVar("_DB_SYS_AUTH")
        useradminpass = mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")
        sysDs = self.inSameInstance(mstarpaths.interpretVar("_DB_ADMIN_USER"), useradminpass)
        sysDs.sqlplus(mstarpaths.interpretPathShort(ORACLE_SCRIPTS + "/Backupdb/datapump_grant.sql"), [dir,self.user])


def getDataStore(logicalName, role=None):
    """Use this method to look up data stores rather than create them directly."""
    if role is None:
        if not dataStorePool.has_key(logicalName):
            ds = DataStore(logicalName)
            if not ds.valid:
                ds = None
                return None
            dataStorePool[logicalName] = ds
            dataStorePool[ds.linkName] = ds
        ds = dataStorePool[logicalName]
    else:
        ds = DataStore(logicalName, role)
    return ds

def createDataStore(role, instance, user, password):
    """Create a DataStore which might not be defined in MineStar.properties"""
    linkName = "%s_%s_%s" % (user, instance, role)
    if not dataStorePool.has_key(linkName):
        ds = DataStore(None)
        ds.create(NO_LOGICAL_NAME, role, instance, user, password)
        dataStorePool[linkName] = ds
    return dataStorePool[linkName]

def handleError(func, arg=None):
    """Invoke a function and return an almost meaningful error message if it doesn't work."""
    value = None
    try:
        value = func(arg)
    except ImportError:
        import traceback
        value = i18n.translate("(no mxODBC)")
        traceback.print_exc(sys.exc_info()[2])
    except NoODBCError:
        value = i18n.translate("(no ODBC)")
    except:
        import traceback
        value = i18n.translate("(error)")
        traceback.print_exc(sys.exc_info()[2])
    return value

# these are absolute file names
INSTANCE_ADMIN = "{HOME}{DRIVE}/mstarData/admin/{INSTANCE}/"
INSTANCE_ARCHIVE = "{HOME}{DRIVE}/oracle/admin/{INSTANCE}/"
INIT_ORA = INSTANCE_ADMIN + "pfile/init.ora"
INITXE_ORA = INSTANCE_ADMIN + "pfile/initXE.ora"
INSTANCE_ORA = "{ORACLE_HOME}/{PWDFILE_DIR}/init{INSTANCE}.ora"
INSTANCE_SPFILE = "{ORACLE_HOME}/{PWDFILE_DIR}/spfile{INSTANCE}.ora"
INSTANCE_DATA = "/mstarData/oradata/{INSTANCE}"
if sys.platform.startswith("win"):
    INSTANCE_PWDFILE = "{ORACLE_HOME}/{PWDFILE_DIR}/PWD{INSTANCE}.ora"
else:
    INSTANCE_PWDFILE = "{ORACLE_HOME}/{PWDFILE_DIR}/orapw{INSTANCE}"
CREATE_INSTANCE_DIRS = [
    INSTANCE_ADMIN + "adhoc", INSTANCE_ADMIN + "archive", INSTANCE_ADMIN + "bdump",
    INSTANCE_ADMIN + "cdump", INSTANCE_ADMIN + "create", INSTANCE_ADMIN + "exp",
    INSTANCE_ADMIN + "pfile", INSTANCE_ADMIN + "udump", INSTANCE_ARCHIVE + "archive",
    "{ORACLE_HOME}/{PWDFILE_DIR}", "{HOME}{DRIVE}" + INSTANCE_DATA
]
CREATE_TABLESPACES = INSTANCE_ADMIN + "create/create_tablespaces.sql"
CREATE_XE_TABLESPACES = INSTANCE_ADMIN + "create/create_xe_tablespaces.sql"
ALTER_XE_DATABASE = INSTANCE_ADMIN + "create/alterXEdatabase.sql"
ALTER_XE_SYSTEM_FILE = INSTANCE_ADMIN + "create/alterXEsystemFile.sql"
MOVE_XE_SYSTEM_FILE = INSTANCE_ADMIN + "create/moveXEsystemFile.bat"
SELECT_XE_SYSTEM_FILE = INSTANCE_ADMIN + "create/selectXEsystemFile.sql"
ALTER_XE_CONTROL = INSTANCE_ADMIN + "create/alterXEcontrolFiles.sql"
COPY_XE_CONTROL = INSTANCE_ADMIN + "create/copyXEcontrol.bat"
SHUTDOWN = INSTANCE_ADMIN + "create/shutdown.sql"
STARTUP = INSTANCE_ADMIN + "create/startup.sql"
CREATE_DATABASE = INSTANCE_ADMIN + "create/create_database.sql"
CREATE_DICTIONARY = INSTANCE_ADMIN + "create/create_dictionary.sql"

# these are file names from the UFS
INIT_ORA_TEMPLATE = ORACLE_UFS + "/DBInstance/init.ora.template"
INIT_ORA_LAPTOP_TEMPLATE = ORACLE_UFS + "/DBInstance/init.ora.laptop.template"
INITXE_ORA_TEMPLATE = ORACLE_UFS + "/DBInstance/initXE.ora.template"
INITSID_ORA_TEMPLATE = ORACLE_UFS + "/DBInstance/initSID.ora.template"
CREATE_TABLESPACES_TEMPLATE = ORACLE_UFS + "/DBInstance/create_tablespaces.sql.template"
CREATE_XE_TABLESPACES_TEMPLATE = ORACLE_UFS + "/DBInstance/create_XE_tablespaces.sql.template"
ALTER_XE_SYSTEM_FILE_TEMPLATE = ORACLE_UFS + "/DBInstance/alterXEsystemFile.sql.template"
MOVE_XE_SYSTEM_FILE_TEMPLATE = ORACLE_UFS + "/DBInstance/moveXEsystemFile.bat.template"
SELECT_XE_SYSTEM_FILE_TEMPLATE = ORACLE_UFS + "/DBInstance/selectXEsystemFile.sql.template"
ALTER_XE_CONTROL_TEMPLATE = ORACLE_UFS + "/DBInstance/alterXEcontrolFiles.sql.template"
COPY_XE_CONTROL_TEMPLATE = ORACLE_UFS + "/DBInstance/copyXEcontrol.bat.template"
SHUTDOWN_TEMPLATE = ORACLE_UFS + "/DBInstance/shutdown.sql.template"
STARTUP_TEMPLATE = ORACLE_UFS + "/DBInstance/startup.sql.template"
ALTER_XE_DATABASE_TEMPLATE = ORACLE_UFS + "/DBInstance/alterXEdatabase.sql.template"
CREATE_DATABASE_TEMPLATE = ORACLE_UFS + "/DBInstance/create_database.sql.template"
CREATE_DICTIONARY_TEMPLATE = ORACLE_UFS + "/DBInstance/create_dictionary.sql.template"

# these files are used for creating reporting instance
#templates
INIT_ORA_TEMPLATE_REPORTING = ORACLE_UFS + "/DBInstance/init.ora.reporting.template"
INIT_ORA_LAPTOP_TEMPLATE_REPORTING = ORACLE_UFS + "/DBInstance/init.ora.reporting.laptop.template"
CREATE_TABLESPACES_TEMPLATE_REPORTING = ORACLE_UFS + "/DBInstance/create_reporting_tablespaces.sql.template"
CREATE_DATABASE_TEMPLATE_REPORTING = ORACLE_UFS + "/DBInstance/create_database.sql.template"
CREATE_DICTIONARY_TEMPLATE_REPORTING = ORACLE_UFS + "/DBInstance/create_dictionary.sql.template"

# these are commands
syspass = mstarpaths.interpretVar("_DB_SYS_AUTH")
ORADIM_NEW_COMMAND = '{ORADIM} -new -sid {INSTANCE} -intpwd ' + syspass + ' -startmode auto -pfile "%s"'
ORADIM_10G_COMMAND = '{ORADIM} -NEW -SID {INSTANCE} -SYSPWD ' + syspass + ' -STARTMODE auto -SRVCSTART system -pfile "%s"'
ORAPWD_COMMAND = '{ORAPWD} file={ORACLE_HOME}/{PWDFILE_DIR}/orapw{INSTANCE} password=' + syspass + ' force=y'
ORADIM_TRASH_COMMAND = '{ORADIM} -DELETE -SID {INSTANCE}'
CREATE_COMMAND = '{ORACLE_HOME}/bin/sqlplus{EXE} /NOLOG @"%s"'

if sys.platform.startswith("win"):
    START_SERVICE_COMMAND = '{ORADIM} -edit -sid {INSTANCE} -startmode auto'
else:
    START_SERVICE_COMMAND = '{ORACLE_HOME}/bin/dbstart'
if not sys.platform.startswith("win"):
    STOP_SERVICE_COMMAND = '{ORACLE_HOME}/bin/dbshut'

def _interpret(path, overrides):
    path = mstarpaths.interpretPathOverride(path, overrides)
    return mstarpaths.interpretPath(path)

def _ufsInterpret(path):
    ufsRoot = ufs.getRoot(mstarpaths.interpretVar("UFS_PATH"))
    ufsFile = ufsRoot.get(path)
    print path
    return ufsFile.getPhysicalFile()

def _instantiate(src, dest, overrides, substs):
    #minestar.logit("datastore.py._instantiate: Started: src %s dest %s overrides %s substs %s " % (src,dest, overrides, substs));
    src = _ufsInterpret(src)
    dest = _interpret(dest, overrides)
    minestar.replaceProperties(src, dest, substs)
    #minestar.logit("datastore.py._instantiate: Finished: src %s dest %s overrides %s substs %s " % (src,dest, overrides, substs));

def _makeSubsts(instance, instanceName, homeDir, dataDirs, filesize):
    substs = {}
    for (k, v) in mstarpaths.config.items():
        substs[k] = v
    if sys.platform.startswith("win"):
        homeDir = homeDir + ":"
    substs["_DRIVE_HOME"] = homeDir
    substs["_INSTANCE"] = instance
    substs["_INSTANCE_NAME"] = instanceName
    substs["_SQLPLUS_ECHO"] = "off"
    substs["_FILESIZE"] = str(filesize)
    lastDataDir = homeDir
    for i in [1, 2]:
        if len(dataDirs) < i:
            d = lastDataDir
        else:
            d = dataDirs[i-1]
            lastDataDir = d
        if sys.platform.startswith("win"):
            d = d + ":"
        substs["_DRIVE_DATA%d" % i] = d
    return substs

def _sqlplusWithSID(instanceName, args):
    sqlplus = mstarpaths.interpretPath("{ORACLE_HOME}/bin/sqlplus{EXE}")
    if sys.platform.startswith("win"):
        batchFile = minestar.getTemporaryFileName(instanceName + "_CREATION_") + ".bat"
        f = open(batchFile, "w")
        f.write("set ORACLE_SID=%s\n" % instanceName)
        f.write("set ORACLE_HOME=%s\n" % mstarpaths.interpretPath("{ORACLE_HOME}"))
        f.write("set TNS_ADMIN=%s\n" % mstarpaths.interpretPath("{TNS_ADMIN}"))
        f.write("%s %s\n" % (sqlplus, string.join(args)))
        f.close()
        cmd = "%s\System32\cmd.exe" % os.environ["windir"]
        cmd = "%s /c %s" % (cmd, batchFile)
        minestar.logit(cmd)
        os.system(cmd)
        #os.spawnve(os.P_WAIT, cmd, ["/c", batchFile], os.environ)
    else:
        script = minestar.getTemporaryFileName(instanceName + "_CREATION_") + ".sh"
        f = open(script, "w")
        f.write("#!/bin/bash\n")
        f.write("export ORACLE_SID=%s\n" % instanceName)
        f.write("export ORACLE_HOME=%s\n" % mstarpaths.interpretPath("{ORACLE_HOME}"))
        f.write("export TNS_ADMIN=%s\n" % mstarpaths.interpretPath("{TNS_ADMIN}"))
        f.write("%s %s\n" % (sqlplus, string.join(args)))
        f.close()
        os.system("/bin/bash %s" % script)

def restartListener():
    tnslsnr = mstarpaths.interpretPath("{ORACLE_HOME}/bin/lsnrctl{EXE}")
    if not os.access(tnslsnr, os.F_OK):
        print i18n.translate("TNS listener cannot be restarted, as %s does not exist") % tnslsnr
        minestar.logit(i18n.translate("TNS listener cannot be restarted, as %s does not exist") % tnslsnr)
    elif not os.access(tnslsnr, os.X_OK):
        print i18n.translate("TNS listener %s is not executable") % tnslsnr
        minestar.logit(i18n.translate("TNS listener %s is not executable") % tnslsnr)
    else:
        import time
        minestar.logit("Restarting TNS listener")
        os.system("%s stop" % tnslsnr)
        # wait to make sure the service has stopped, not just the command to tell it to stop
        time.sleep(3)
        os.system("%s start" % tnslsnr)

def stopListener():
    tnslsnr = mstarpaths.interpretPath("{ORACLE_HOME}/bin/lsnrctl{EXE}")
    if not os.access(tnslsnr, os.F_OK):
        print i18n.translate("TNS listener cannot be stopped, as %s does not exist") % tnslsnr
        minestar.logit(i18n.translate("TNS listener cannot be stopped, as %s does not exist") % tnslsnr)
    elif not os.access(tnslsnr, os.X_OK):
        print i18n.translate("TNS listener %s is not executable") % tnslsnr
        minestar.logit(i18n.translate("TNS listener %s is not executable") % tnslsnr)
    else:
        import time
        minestar.logit("Stopping TNS listener")
        os.system("%s stop" % tnslsnr)

def startListener():
    tnslsnr = mstarpaths.interpretPath("{ORACLE_HOME}/bin/lsnrctl{EXE}")
    if not os.access(tnslsnr, os.F_OK):
        print i18n.translate("TNS listener cannot be started, as %s does not exist") % tnslsnr
        minestar.logit(i18n.translate("TNS listener cannot be started, as %s does not exist") % tnslsnr)
    elif not os.access(tnslsnr, os.X_OK):
        print i18n.translate("TNS listener %s is not executable") % tnslsnr
        minestar.logit(i18n.translate("TNS listener %s is not executable") % tnslsnr)
    else:
        import time
        minestar.logit("Starting TNS listener")
        os.system("%s start" % tnslsnr)


def _noWhiteSpace(s):
    return filter(lambda c: c not in string.whitespace, s)

def getSystemDataStores():
    """Return (model, historical, template, summary, reporting, boaudit) data stores as defined in MineStar.properties"""
    return (getDataStore("_MODELDB"), getDataStore("_HISTORICALDB"), getDataStore("_TIMESERIESDB"), getDataStore("_TEMPLATEDB"), getDataStore("_SUMMARYDB"), getDataStore("_REPORTINGDB"), getDataStore("_BOAUDITDB"))

def getInternalDataStores():
    return (getDataStore("_PITMODELDB"),getDataStore("_GISDB"))

def getReportingDataStores():
    return (getDataStore("_CFG","DATAWAREHOUSE"),getDataStore("_DVL","DATAWAREHOUSE"),getDataStore("_DWH","DATAWAREHOUSE"),getDataStore("_DCL","DATAWAREHOUSE"))

def getOptionalDataStores():
    aquila = None
    if mstarpaths.interpretVar("_AQUILADB_USED") == "true":
        aquila = getDataStore("_AQUILADB")
    caes = None
    if mstarpaths.interpretVar("_CAESDB_USED") == "true":
        caes = getDataStore("_CAESDB")
    return (aquila, caes)

def getUniqueDataStoreInstances():
    (model, historical, timeseries, template, summary, reporting, boaudit) = getSystemDataStores()
    (pitmodel,gis) = getInternalDataStores()
    (aquila, caes) = getOptionalDataStores()
    result = []
    candidates = [ model, historical, template, summary, reporting, pitmodel, gis, boaudit, aquila, caes ]
    for c in candidates:
        if c is not None and c.instance not in result:
            result.append(c.instance)
    return result

def getReportingDataStoreInstances():
    (dvl,cfg,dwh,dcl) = getReportingDataStores()
    result = []
    candidates = [dvl,cfg,dwh,dcl]
    for c in candidates:
        if c is not None and c.instance not in result:
            result.append(c.instance)
    return result

def getEntityDataStores():
    """Return (model, historical) data stores as defined in MineStar.properties"""
    return (getDataStore("_MODELDB"), getDataStore("_HISTORICALDB"))

def isSqlplusAvailable():
    sqlplus = mstarpaths.interpretPath("{ORACLE_HOME}/bin/sqlplus{EXE}")
    return os.access(sqlplus, os.X_OK)

