import datastore, minestar
import string, os, sys, i18n, mstardebug, time, databaseDifferentiator, re
import mstarpaths, configureDataStoreConnections, progress, ufs, ServerTools

__version__ = "$Revision: 1.0 $"
# rmanInstance - export directory for rman backup
def main(appConfig=None):
    import mstarrun
    optionDefns = []
    argumentsStr = "[driveName] [dataDir]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)
    driveName = args[0]
    dataDir = args[1]
    createInstance(driveName,dataDir)
    createRmanUser()      

# these are absolute file names
ORACLE_UFS = "/bus/database/oracle"
INSTANCE_ADMIN = "{HOME}{DRIVE}/rmanData/admin/RMANDB/"
INIT_ORA = INSTANCE_ADMIN + "pfile/init.ora"
INITXE_ORA = INSTANCE_ADMIN + "pfile/initXE.ora"
INSTANCE_ORA = "{ORACLE_HOME}/{PWDFILE_DIR}/initRMANDB.ora"
INSTANCE_SPFILE = "{ORACLE_HOME}/{PWDFILE_DIR}/spfileRMANDB.ora"
INSTANCE_DATA = "/rmanData/oradata/RMANDB"
if sys.platform.startswith("win"):
    INSTANCE_PWDFILE = "{ORACLE_HOME}/{PWDFILE_DIR}/PWDRMANDB.ora"
else:
    INSTANCE_PWDFILE = "{ORACLE_HOME}/{PWDFILE_DIR}/orapwRMANDB"

CREATE_TABLESPACES = INSTANCE_ADMIN + "create/create_tablespaces.sql"
CREATE_DATABASE = INSTANCE_ADMIN + "create/create_database.sql"
CREATE_DICTIONARY = INSTANCE_ADMIN + "create/create_dictionary.sql"

# these are file names from the UFS
INIT_ORA_TEMPLATE = ORACLE_UFS + "/DBInstance/init_RMAN.ora.template"
INITSID_ORA_TEMPLATE = ORACLE_UFS + "/DBInstance/initSID_RMAN.ora.template"
CREATE_TABLESPACES_TEMPLATE = ORACLE_UFS + "/DBInstance/create_tablespaces_RMAN.sql.template"
CREATE_DATABASE_TEMPLATE = ORACLE_UFS + "/DBInstance/create_database_RMAN.sql.template"
CREATE_DICTIONARY_TEMPLATE = ORACLE_UFS + "/DBInstance/create_dictionary.sql.template"

syspass = mstarpaths.interpretVar("_DB_SYS_AUTH")
ORADIM_NEW_COMMAND = '{ORADIM} -new -sid RMANDB -intpwd ' + syspass + ' -startmode auto -pfile "%s"'
ORADIM_10G_COMMAND = '{ORADIM} -NEW -SID RMANDB -SYSPWD ' + syspass + ' -STARTMODE auto -SRVCSTART system -pfile "%s"'
ORAPWD_COMMAND = '{ORAPWD} file={ORACLE_HOME}/{PWDFILE_DIR}/orapwRMANDB password=' + syspass + ' force=y'
ORADIM_TRASH_COMMAND = '{ORADIM} -DELETE -SID RMANDB'
CREATE_COMMAND = '{ORACLE_HOME}/bin/sqlplus{EXE} /NOLOG @"%s"'
INSTANCE_ADMIN = "{HOME}{DRIVE}/rmanData/admin/RMANDB/"
INIT_ORA = INSTANCE_ADMIN + "pfile/init.ora"
INSTANCE_ORA = "{ORACLE_HOME}/{PWDFILE_DIR}/initRMANDB.ora"
INSTANCE_SPFILE = "{ORACLE_HOME}/{PWDFILE_DIR}/spfileRMANDB.ora"
INSTANCE_DATA = "/rmanData/oradata/RMANDB"
ROLE = mstarpaths.interpretVar("_DBROLE")
FILESIZE = 60
INSTANCENAME = "RMANDB_HOST"
INSTANCE = "RMANDB"


CREATE_INSTANCE_DIRS = [
    INSTANCE_ADMIN + "adhoc", INSTANCE_ADMIN + "archive", INSTANCE_ADMIN + "bdump",
    INSTANCE_ADMIN + "cdump", INSTANCE_ADMIN + "create", INSTANCE_ADMIN + "exp",
    INSTANCE_ADMIN + "pfile", INSTANCE_ADMIN + "udump", INSTANCE_ADMIN + "script",
    "{ORACLE_HOME}/{PWDFILE_DIR}", "{HOME}{DRIVE}" + INSTANCE_DATA
]

if sys.platform.startswith("win"):
    START_SERVICE_COMMAND = '{ORADIM} -edit -sid RMANDB -startmode auto'
else:
    START_SERVICE_COMMAND = '{ORACLE_HOME}/bin/dbstart'

def createInstance(homeDir, dataDirs):
        """Assuming that this instance does not exist, create it."""
        # minestar.logit("datastore.createInstance: started")
        overrides = _getInstanceOverrides(homeDir)
        # minestar.logit("datastore.createInstance: overrides is  %s " % overrides)
        dirs = [ datastore._interpret(d, overrides) for d in CREATE_INSTANCE_DIRS ]
        dirs = dirs + [ datastore._interpret(d + overrides["DRIVE"] + INSTANCE_DATA, overrides) for d in dataDirs ]
        for d in dirs:
            try:
                os.makedirs(d)
            except OSError:
                # already exists
                pass

        # create service
        if sys.platform.startswith("win"):
            datastore.progress.nextTask(0.02, "Creating RMAN Oracle service")
            print datastore.i18n.translate("Creating RMAN Oracle service")
            minestar.run(datastore._interpret(ORADIM_10G_COMMAND % INIT_ORA, overrides))

        progress.task(0.02, "Copying initialisation files")
        print i18n.translate("Copying initialisation files")
       
        substs = datastore._makeSubsts(INSTANCE, INSTANCENAME, homeDir, dataDirs, FILESIZE)

        if not sys.platform.startswith("win"):
            progress.nextTask(0.02, "Creating Oracle instance files")
            print i18n.translate("Creating Oracle instance files")
          
            minestar.run(datastore._interpret(ORAPWD_COMMAND, overrides))

        # it seems that if Oracle is running a TNS listener for the service (e.g. because it
        # used to exist), you MUST use TNS to connect. However, if Oracle is not running such a
        # listener, you MUST NOT use TNS to connect. Consequently we have to know whether the
        # TNS listener is going or not to know how to connect.
        minestar.logit("datastore.createInstance: Calling tnsping")
        if tnsping():
            substs["_CONNECT_STRING"] = "@%s" % INSTANCENAME
        else:
            substs["_CONNECT_STRING"] = ""

        minestar.logit("datastore.createInstance: Calling _instantiate for initOraTemplate")
        datastore._instantiate(INIT_ORA_TEMPLATE, INIT_ORA, overrides, substs)
        minestar.logit("datastore.createInstance: Calling _instantiate for INITSID_ORA")
        datastore._instantiate(INITSID_ORA_TEMPLATE, INSTANCE_ORA, overrides, substs)
        datastore._instantiate(CREATE_TABLESPACES_TEMPLATE, CREATE_TABLESPACES, overrides, substs)
        datastore._instantiate(CREATE_DATABASE_TEMPLATE, CREATE_DATABASE, overrides, substs)
        datastore._instantiate(CREATE_DICTIONARY_TEMPLATE, CREATE_DICTIONARY, overrides, substs)
        createScript = datastore._interpret(CREATE_DATABASE, overrides)
        dictionaryScript = datastore._interpret(CREATE_DICTIONARY, overrides)
        tablespaceScript = datastore._interpret(CREATE_TABLESPACES, overrides)
        # create_database script
        progress.nextTask(0.40, "Creating RMAN instance")
        # minestar.logit("datastore.createInstance: Creating RMAN instance")
        print i18n.translate("Creating RMAN instance")
        datastore._sqlplusWithSID(INSTANCE, ["/NOLOG", "@" + createScript])
        # create_dictionary script
        progress.nextTask(0.40, "Creating RMAN dictionary")
        print i18n.translate("Creating RMAN dictionary")
        # minestar.logit("datastore.createInstance: Creating RMAN dictionary")
        datastore._sqlplusWithSID(INSTANCE, ["/NOLOG", "@" + dictionaryScript])
        #
        if not sys.platform.startswith("win"):
            minestar.pause(datastore._interpret("You must now add this entry in the /etc/oratab: %s:{ORACLE_HOME}:Y <Hit enter to continue>" % INSTANCE, overrides))
        #
        progress.nextTask(0.02, "Reconfiguring RMAN service")
        print i18n.translate("Reconfiguring RMAN service")
        # minestar.logit("datastore.createInstance: Reconfiguring RMAN service")
        minestar.run(datastore._interpret(START_SERVICE_COMMAND, overrides))
        #
        progress.nextTask(0.10, "Creating tablespaces")
        print i18n.translate("Creating tablespaces")
        # minestar.logit("datastore.createInstance: Creating tablespaces")
        datastore._sqlplusWithSID(INSTANCE, ["/NOLOG", "@" + tablespaceScript])

        progress.nextTask(0.02, "Adding to listener.ora and restarting listener")
        # minestar.logit("datastore.createInstance: adding to listener.ora")
        updateListenerOra(INSTANCE)
        # minestar.logit("datastore.createInstance: restarting listener")
        datastore.restartListener()
        #
        # minestar.logit("Done")
        progress.done()
    

def updateListenerOra(instance):
       import oracleListener,mstarpaths
       comment = "# Updated %s by Python code." % configureDataStoreConnections.time.ctime()
       filename = mstarpaths.interpretPath("{TNS_ADMIN}/listener.ora")
       minestar.logit("Adding %s to %s" % (instance, filename))
       lf = oracleListener.ListenerFile(filename)
       lf.defineSid(comment, instance, mstarpaths.interpretPath("{ORACLE_HOME}"), instance)
       lf.write()

def createRmanUser():
    """
    Create a new user in this instance. If the user already exists, it will be updated to have the correct permissions etc.
    """
    serverRoleSpec = mstarpaths.interpretVar("_DB_SERVER_ROLES")
    role = "HOST"
    syspass = mstarpaths.interpretVar("_DB_SYS_AUTH")
    sysuser = mstarpaths.interpretVar("_DB_ADMIN_USER")
    useradminpass = mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")
    sysDs = datastore.createDataStore(role,INSTANCE,"sys", syspass)
    sysDs.sqlplus(mstarpaths.interpretPathShort(datastore.ORACLE_SCRIPTS + "/SchemaUtilities/create_user_RMAN"), ["RMAN", "RMAN"])
    sysDs.sqlplus(mstarpaths.interpretPathShort(datastore.ORACLE_SCRIPTS + "/SchemaUtilities/set_user_RMAN_permissions"), ["RMAN"])

def _getInstanceOverrides(homeDir):
    overrides = { "HOME" : homeDir, "INSTANCE" :INSTANCE }
    if configureDataStoreConnections.sys.platform.startswith("win"):
        overrides["DRIVE"] = ":"
        overrides["PWDFILE_DIR"] = "database"
    else:
        overrides["DRIVE"] = ""
        overrides["PWDFILE_DIR"] = "dbs"
    overrides["ORADIM"] = mstarpaths.interpretPath("{ORACLE_HOME}/bin/oradim{EXE}")
    overrides["ORAPWD"] = mstarpaths.interpretPath("{ORACLE_HOME}/bin/orapwd{EXE}")
    return overrides

def tnsping():
    executable = mstarpaths.interpretPath("{ORACLE_HOME}/bin/tnsping{EXE}")
    command = "%s %s" % (executable, INSTANCENAME)
    minestar.logit(command)
    output = minestar.systemEvalRaw(command)
    if len(output) == 0:
        return 0
    return output[-1].startswith("OK")



if __name__ == "__main__":
    """entry point when called from python"""
    main()
