import mstarpaths

class ConfigException:
    def __init__(self, mesg):
        self.mesg = mesg

    def __str__(self):
        return "ConfigException[%s]" % self.mesg

class OracleDatabase:
    "A single database, either RAC or single instance."
    def __init__(self):
        pass

class SingleInstanceDatabase(OracleDatabase):
    def __init__(self, server):
        # the machine on which the instance runs
        self.server = server

    def __createPrimary(self):
        # add -silent when it's going
        dbcaArgs = ("-createDatabase -templateName %s -gdbName %s -sid %s -sysPassword %s -systemPassword %s " + \
            "-emConfiguration LOCAL -dbsnmpPassword %s -sysmanPassword %s -initParams %s -variables %s -recoveryAreaDestination %s") % \
            (self.templateSi, self.config.name, self.config.name, self.sysPassword, self.systemPassword, self.snmpPassword, self.sysmanPassword,
            self.initParams, self.variables, self.fraDest)
        self.server.dbca(dbcaArgs)

class RacDatabase(OracleDatabase):
    def __init__(self, servers):
        self.servers = servers

    def __createPrimary(self):
        if self.asmPassword is None:
            raise ConfigException("No ASMSYSPASSWORD specified, and it is required for RAC")
        # TODO
        # nodeInfo "something derived from self.aNodes"
        # add -silent when it's going
        dbcaArgs = ("-createDatabase -templateName %s -gdbName %s -sid %s -sysPassword %s -systemPassword %s -emConfiguration LOCAL " + \
            "-dbsnmpPassword %s -sysmanPassword %s -initParams %s -storageType ASM -asmSysPassword %s -nodeinfo %s -datafileDestination %s " + \
            "-recoveryAreaDestination %s -diskGroupName DATA -recoveryGroupName RECOVERY") % \
            (self.templateRac, self.config.name, self.config.name, self.sysPassword, self.systemPassword, self.snmpPassword, self.sysmanPassword,
            self.initParams, self.asmPassword, nodeInfo, self.dataDest, self.fraDest)
        self.servers[0].dbca(dbcaArgs)

class OracleConfig:
    def __init__(self):
        self.base = mstarpaths.interpretVar("DB_ORACLE_BASE")
        self.oracleHome = mstarpaths.interpretVar("DB_ORACLE_HOME")
        self.admin = mstarpaths.interpretVar("DB_ADMIN")
        self.dataDest = mstarpaths.interpretVar("DB_DATA_DEST")
        self.fraDest = mstarpaths.interpretVar("DB_FRA_DEST")
        self.asmHome = mstarpaths.interpretVar("DB_ASM_HOME")
        self.crsHome = mstarpaths.interpretVar("DB_CRS_HOME")

        self.name = mstarpaths.interpretVar("DB_NAME")
        self.sysPassword = mstarpaths.interpretVar("DB_SYS_PASSWORD")
        self.systemPassword = mstarpaths.interpretVar("DB_SYSTEM_PASSWORD")
        self.snmpPassword = mstarpaths.interpretVar("DB_SNMP_PASSWORD")
        self.sysmanPassword = mstarpaths.interpretVar("DB_SYSMAN_PASSWORD")
        self.backupDrive = mstarpaths.interpretVar("DB_BACKUP_PATH")

class OracleServer:
    """A particular machine on which Oracle is installed.
       We assume elsewhere that the Oracle installation directories are the same on all machines on which Oracle is
       installed for ease of administration etc, but I don't feel comfortable embedding that assumption too deeply
       into the code.
    """
    def __init__(self, config, sid, uniqueName, dataDest, fraDest, aNodes, bNodes, mgtBase, asmSid=None, asmPassword=None):
        import mstarpaths
        self.sysPassword = config.sysPassword
        self.systemPassword = config.systemPassword
        self.snmpPassword = config.snmpPassword
        self.sysmanPassword = config.sysmanPassword
        self.config = config
        self.sid = sid
        self.uniqueName = uniqueName
        self.dataDest = dataDest
        self.fraDest = fraDest
        self.aNodes = aNodes
        self.bNodes = bNodes
        self.mgtBase = mgtBase
        self.templateRac = mstarpaths.interpretPath("%s/MineStar-RAC.dbt" % self.mgtBase)
        self.templateSi = mstarPaths.interpretPath("%s/MineStar-SI.dbt" % self.mgtBase)
        self.asmSid = asmSid
        self.asmPassword = asmPassword
        self.adminBase = mstarpaths.interpretPath("%s/admin/%s" % (self.config.base, self.uniqueName))
        self.bdump = mstarpaths.interpretPath("%s/bdump" % self.adminBase)
        self.adump = mstarpaths.interpretPath("%s/adump" % self.adminBase)
        self.udump = mstarpaths.interpretPath("%s/udump" % self.adminBase)
        self.cdump = mstarpaths.interpretPath("%s/cdump" % self.adminBase)
        self.initParams = "db_unique_name=%s,background_dump_dest=%s,audit_file_dest=%s,user_dump_dest=%s,core_dump_dest=%s" % \
            (self.uniqueName, self.bdump, self.adump, self.udump, self.cdump)
        self.variables = "DB_UNIQUE_NAME=%s,DATADEST=%s,FRADEST=%s" % (self.config.name, self.dataDest, self.fraDest)
        # derived properties
        self.dbcaCommand = self.getOracleExe("dbca")
        self.sqlplusCommand = self.getOracleExe("sqlplus")
        self.rmanCommand = self.getOracleExe("rman")

    def getOracleExe(self, exeName):
        import mstarpaths
        return mstarpaths.interpretPath("%s/bin/%s{EXE}" % (self.oracleHome, exeName))

    def getCrsExe(self, exeName):
        import mstarpaths
        return mstarpaths.interpretPath("%s/bin/%s{EXE}" % (self.crsHome, exeName))

    def dbca(self, params):
        import minestar
        minestar.run("%s %s" % (self.dbcaCommand, params))

    def sqlplus(self, args):
        import minestar
        cmd = "%s -s /nolog %s" % (self.sqlplusCommand, args)
        minestar.run(cmd)

    def rman(self, args):
        import minestar
        cmd = "%s %s" % (self.rmanCommand, args)
        minestar.run(cmd)

def getRacScript(scriptName, dir=None):
    import mstarpaths
    if dir is None:
        path = mstarpaths.interpretPath("{MSTAR_HOME}/bus/rac/%s" % scriptName)
    else:
        path = mstarpaths.interpretPath("{MSTAR_HOME}/bus/rac/%s/%s" % (dir, scriptName))
    return path

def getServer(cfg, serverNum):
    if self.option == OPTION1:
        if serverNum == 1:
            return OracleServer(self, self.name, "%s_B" % self.name, dataDest, fraDest, [2], [1], mgtBase)
        elif serverNum == 2:
            return OracleServer(self, self.name, "%s_A" % self.name, dataDest, fraDest, [2], [1], mgtBase)
        elif serverNum == 3:
            return OracleServer(self, self.name, "%s_A" % self.name, dataDest, fraDest, [2], [1], mgtBase)
        else:
            raise ConfigException("Option %s takes 3 servers numbered 1 to 3" % OPTION1)
    elif self.option == OPTION2:
        if serverNum == 1:
            return OracleServer(self, self.name, "%s_B" % self.name, dataDest, fraDest, [2,3], [1], mgtBase)
        elif serverNum == 2:
            return OracleServer(self, "%s1" % self.name, "%s_A" % self.name, dataDest, fraDest, [2,3], [1], mgtBase, "+ASM1")
        elif serverNum == 3:
            return OracleServer(self, "%s2" % self.name, "%s_A" % self.name, dataDest, fraDest, [2,3], [1], mgtBase, "+ASM2")
        else:
            raise ConfigException("Option %s takes 3 servers numbered 1 to 3" % OPTION1)
    else:
            raise ConfigException("What's option %s" % self.option)

class DatabaseSet:
    def __init__(self, dbs, primary, standby):
        """ Each element of the list dbs is an instance of OracleDatabase.
         primary is the index of the primary database in that list.
         standby is the index of the standby database in that list.
        """
        self.dbs = dbs
        self.primary = primary
        self.standby = standby

    def createPrimary(self):
        self.dbs[primary].__createPrimary()

def createPrimaryDatabase(config):
    """ Extract the parameters for the primary database and create the OracleDatabase instance.
    """
    type = mstarpaths.interpretVar("DB_PRIMARY_TYPE")
    servers = mstarpaths.interpretVar("DB_PRIMARY_SERVERS")
    if servers is None:
        raise ConfigException("No servers defined for primary database")
    print "servers = " + servers
    if type == "SINGLE":
        server = OracleServer()
        db = SingleInstanceDatabase(server)
    elif type == "RAC":
        pass
    else:
        raise ConfigException("Primary database neither SINGLE nor RAC")

def createDatabaseSet():
    config = OracleConfig()
    primary = createPrimaryDatabase(config)
    standby = createStandbyDatabase(config)
    p = 0
    s = 1
    dbos = mstarpaths.interpretVar("DB_ON_STANDBY")
    if dbos != "false":
        p = 1
        s = 0
    return DatabaseSet([primary, standby], p, s)


mstarpaths.loadMineStarConfig()
dbs = createDatabaseSet()
dbs.createPrimary()

#config.sqlplus(mstarpaths.interpretFormat("@initparams_%s-%s" % (server1.uniqueName, option)))
#config.sqlplus("@create_primary")
#config.rman("target / nocatalog cmdfile=configure.rman appendlog=create_primary.log")
