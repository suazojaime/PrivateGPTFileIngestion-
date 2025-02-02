import socket

import minestar

logger = minestar.initApp()
import mstarpaths, datastore, mstarrun, os, sys, string, i18n, progress,databaseDifferentiator

APP = "createDataStores"
# Get the database dependent object from databaseDifferentiator.
dbobject =databaseDifferentiator.returndbObject()
REPORTING_REPOSITORY = dbobject.reportingRepository()
Instancechecker= ""

def check(ds, name):
    if ds is None:
        error = i18n.translate("The %s data store is not defined!") % name
        progress.fail(error)
        minestar.fatalError(APP, error)
    if(dbobject.getDBString()=="Oracle"):
        if len(ds.instance) > 8 :
            error = i18n.translate("Oracle will not accept '%s' as an instance name, use only 8 characters") % ds.instance
            progress.fail(error)
            minestar.fatalError(APP, error)
    if(dbobject.getDBString()=="sqlserver"):
        if len(ds.instance) > 16 :
            error = i18n.translate("sqlserver will not accept '%s' as an instance name, use only 16 characters") % ds.instance
            progress.fail(error)
            minestar.fatalError(APP, error)

def fix(dsName, ds, homeDir, dataDirs, reporting=False):
    if not reporting:
        Instancechecker=dbobject.createDataStoreFixops(dsName, ds, homeDir, dataDirs)
    else:
        Instancechecker=dbobject.createReportingDataStore(dsName,ds,homeDir,dataDirs)
    minestar.logit("createDataStores.fix: ... finished")
    progress.done()
    return  Instancechecker

def checkCurrentDatabaseServer():
    import ServerTools
    db = ServerTools.getCurrentDatabaseServer()
    if not db:
        print i18n.translate("createDataStores.main: database server has not been configured.")
        minestar.exit(0)

    if not isSameHost(db, ServerTools.getCurrentServer()):
         print i18n.translate("createDataStores.main: CreateDataStores should be run from Database Server (%s) only (current: %s)") % (db, ServerTools.getCurrentServer())
         minestar.exit(0)

def isSameHost(a, b):
    if a.upper() == b.upper():
        return True;
    # More sophisticated match.  Try looking up the addresses and see if 
    # we can ascertain if these addresses map to the same host
    try:
        a_addr = socket.gethostbyaddr(a)
        b_addr = socket.gethostbyaddr(b)
	# See if the two tuples match.  The primary hostname matches, or
	# There is an IP address in common
        return a_addr == b_addr or a_addr[0] == b_addr[0] or len(set(a_addr[2]).intersection(b_addr[2])) > 0
    except socket.error as e:
	# One of the addresses is malformed or name lookup is not working.
	# We suppress this error and just display the one which shows that
	# the names don't match.
        return False

def getLetters(s):
    "Get the set of letters from a string"
    result = []
    if s is not None:
        for c in s:
            if c.upper() in string.ascii_uppercase:
                c = c.upper()
                if c not in result:
                    result.append(c)
    return result

def backup(dsName, ds):
    eStatus = ds.entityProbe()
    if eStatus == "ENTITIES":
        # data store contains data, let's export it to be sure
        filename = dbobject.backupFileName(dsName)
        ds.exp(filename)
        print i18n.translate("%s database exported to %s for safe-keeping.") % (dsName, filename)

def fixDataStores(model, historical, timeseries, template, reporting, summary, pitmodel, gis, boaudit, homeDrive, dataDrive, aquila=None, caes=None):
    modelHistSame = model.isSameAs(historical)
    count = 6
    if modelHistSame:
        count = count - 1
    if aquila is not None:
        count = count + 1
    if caes is not None:
        count = count + 1
    percent = 1.0/count

    # Do the historical first so that if the instance needs to be created it gets the correct
    # tablespace sizing for a historical
    progress.task(percent, "Building historical instance and user")
    Instancechecker=fix("historical", historical, homeDrive, dataDrive)

    if(Instancechecker!= "instance"):
      if not modelHistSame:
        progress.nextTask(percent, "Building model instance and user")
        fix("model", model, homeDrive, dataDrive)
      progress.nextTask(percent, "Building timeseries instance and user")
      fix("timeseries", timeseries, homeDrive, dataDrive)
      progress.nextTask(percent, "Building template instance and user")
      fix("template", template, homeDrive, dataDrive)
      progress.nextTask(percent, "Building reporting instance and user")
      fix("reporting", reporting, homeDrive, dataDrive)
      progress.nextTask(percent, "Building summary instance and user")
      fix("summary", summary, homeDrive, dataDrive)
      progress.nextTask(percent, "Building pitmodel instance and user")
      fix("pitmodel", pitmodel, homeDrive, dataDrive)
      progress.nextTask(percent, "Building boaudit instance and user")
      fix("boaudit", boaudit, homeDrive, dataDrive)
      if aquila is not None:
        progress.nextTask(percent, "Building aquila instance and user")
        fix("aquila", aquila, homeDrive, dataDrive)
      if caes is not None:
        progress.nextTask(percent, "Building caes instance and user")
        fix("caes", caes, homeDrive, dataDrive)
    progress.done()
    return Instancechecker

def refreshDataStoresUsers(model, historical, timeseries, template, reporting, summary, pitmodel, gis, boaudit, homeDrive, dataDrive, aquila=None, caes=None):
    modelHistSame = model.isSameAs(historical)
    count = 6
    if modelHistSame:
        count = count - 1
    if aquila is not None:
        count = count + 1
    if caes is not None:
        count = count + 1
    percent = 1.0/count
    progress.task(percent, "refresh historical db")
    dbobject.refreshUser(historical)
    if not modelHistSame:
        progress.nextTask(percent, "refresh model db")
        dbobject.refreshUser(model)
    progress.nextTask(percent, "refresh template db")
    dbobject.refreshUser(template)
    progress.nextTask(percent, "refresh timeseries db")
    dbobject.refreshUser(timeseries)
    progress.nextTask(percent, "refresh reporting db")
    dbobject.refreshUser(reporting)
    progress.nextTask(percent, "refresh summary db")
    dbobject.refreshUser(summary)
    progress.nextTask(percent, "refresh pitmodel db")
    dbobject.refreshUser(pitmodel)
    progress.nextTask(percent, "refresh boaudit db")
    dbobject.refreshUser(boaudit)
    if aquila is not None:
        progress.nextTask(percent, "refresh aquila db")
        dbobject.refreshUser(aquila)
    if caes is not None:
        progress.nextTask(percent, "refresh caes db")
        dbobject.refreshUser(caes)
    progress.done()


def refreshSchemas(model, historical, timeseries, template, pitmodel):
    mesg = "Dropping all objects from %s" % model.linkName
    progress.task(0.08, mesg)
    print mesg
    #model.dropAll()
    if model.isSameAs(historical):
        mesg = "No need to drop all objects in historical - same as model"
        progress.nextTask(0.08, mesg)
        print mesg
    else:
        mesg = "Dropping all objects from %s" % historical.linkName
        progress.nextTask(0.08, mesg)
        print mesg
        #historical.dropAll()

    mesg = "Dropping all objects from %s" % timeseries.linkName
    progress.nextTask(0.08, mesg)
    print mesg
    timeseries.dropAll(timeseries)

    mesg = "Dropping all objects from %s" % template.linkName
    progress.nextTask(0.08, mesg)
    print mesg
    template.dropAll(template)

    mesg = "Dropping all objects from %s" % pitmodel.linkName
    progress.nextTask(0.08, mesg)
    print mesg
    pitmodel.dropAll(pitmodel)

    progress.nextTask(0.70, "Refreshing schema in template data store and propagating")
    mstarrun.run("makeDataStores all")

    mesg = "Populating platform tables for %s" % model.linkName
    progress.nextTask(0.03, mesg)
    print mesg
    progress.done()

def fixReportingDataStores(cfg,dvl,dwh,dcl,homeDrive,dataDrive):
    progress.task(0, "Building cfg instance and user")
    Instancechecker=fix("cfg", cfg, homeDrive, dataDrive,True)
    if Instancechecker!= "instance":
        fix("dvl", dvl, homeDrive, dataDrive,True)
        fix("cfg", cfg, homeDrive, dataDrive,True)
        fix("dwh", dwh, homeDrive, dataDrive,True)
        fix("dcl", dcl, homeDrive, dataDrive,True)
    progress.done()
    return Instancechecker

def _ufsInterpret(path):
    import ufs
    ufsRoot = ufs.getRoot(mstarpaths.interpretVar("UFS_PATH"))
    ufsFile = ufsRoot.get(path)
    if ufsFile is None:
        return None
    return ufsFile.getPhysicalFile()

def main(appConfig):
    # Assume _MODELDB, _HISTORICALDB, _TIMESERIESDB, _TEMPLATEDB, _GISDB , _BOAUDITDB and _REPORTINGDB are configured in MineStar.properties
    # Instance names may not be more than 8 characters. Model and template must be on the same host.
    # We must be on the database server host (for windows)!
    # Usage createDataStores [<target>] <size> <homeDrive> [<dataDrives>]
    if sys.platform.startswith("win"):
        checkCurrentDatabaseServer()
    try:
        progress.start(1000, "createDataStores")
        progress.task(0.01, "Loading configuration")
        cwd = os.getcwd()
        os.chdir(mstarpaths.interpretPath("{MSTAR_SYSTEM_HOME}"))
        #dbobject.Dbhome()
        # get the command line parameters
        args = appConfig["args"]
        reportingInstance = False
        minestarInstance = True
        if args[0].lower().startswith('r'):
            reportingInstance = True
            minestarInstance = False
            reportingServerRoleSpec = mstarpaths.interpretVar("_DB_SERVER_ROLES_REPORTING")
            if reportingServerRoleSpec is None or reportingServerRoleSpec.strip() == '':
                print 'createDataStores.main: Failed, Server details not specified in the supervisor'
                return
        elif args[0].lower().startswith('all'):
            reportingInstance = True
            minestarInstance = True

        count = 3
        if not reportingInstance and minestarInstance:
            count = 2
        size = args[count-2]
        mstarpaths.config['MSTAR_SCHEMA_SIZE'] = size
        if sys.platform.startswith("win"):
            homeDrive = getLetters(args[count-1])[0]
        else:
            homeDrive = args[count-1]
        dataDrive = [homeDrive]
        if len(args) > count:
            if sys.platform.startswith("win"):
                dataDrive = getLetters(args[count])
            else:
                dataDrive = args[count]
        else:
            dataDrive = [homeDrive]

        dbobject.UpdateTnsNames()
        if minestarInstance:
            minestar.logit("createDataStores.main: Calling datastore.getSystemDataStores");
            # check the data stores and ensure the instances and users are created
            (model, historical, timeseries, template, summary, reporting, boaudit) = datastore.getSystemDataStores()
            minestar.logit("createDataStores.main: model.instance is %s " % model.instance);
            minestar.logit("createDataStores.main: Calling datastore.getInternalDataStores");
            (pitmodel,gis) = datastore.getInternalDataStores()
            minestar.logit("createDataStores.main: Calling datastore.getOptionalDataStores");
            (aquila, caes) = datastore.getOptionalDataStores()

            #minestar.logit("createDataStores.main: Checking data store definitions");
            progress.nextTask(0.01, "Checking data store definitions")
            check(model, "model")
            if not model.isSameAs(historical):
                check(historical, "historical")
                check(timeseries, "timeseries")
                check(template, "template")
                check(reporting, "reporting")
                check(summary, "summary")
                check(pitmodel, "pitmodel")
                check(boaudit, "boaudit")
            if aquila is not None:
                check(aquila, "aquila")
            if caes is not None:
                check(caes, "caes")
            progress.nextTask(0.67, "Building instances and users")
            minestar.logit("createDataStores.main: Calling fixDataStores");
            Instancechecker=fixDataStores(model, historical, timeseries, template, reporting, summary, pitmodel, gis, boaudit, homeDrive, dataDrive, aquila, caes)
            if(Instancechecker!= "instance"):
              refreshDataStoresUsers(model, historical, timeseries, template, reporting, summary, pitmodel, gis, boaudit, homeDrive, dataDrive, aquila, caes)
            dbobject.createDataStoreMainopsRestart()
             # import the BusinessObjects reporting repository
            #minestar.logit("createDataStores.main: Importing reporting repository");
            progress.nextTask(0.03, "Importing reporting repository")
            repos = _ufsInterpret(REPORTING_REPOSITORY)
            if repos is None:
                minestar.logit("Reporting repository not found")
            else:
                minestar.logit("Reporting repository installed from %s" % repos)
                reporting.imp(repos,reporting)

            # create the schemas
            #minestar.logit("createDataStores.main: Refreshing schemas");
            progress.nextTask(0.11, "Running makeDataStores to set up database schemas")
            if(Instancechecker!= "instance"):
               refreshSchemas(model, historical, timeseries, template, pitmodel)

            # NOTE: reporting periods will move into ReferenceData soon
            #minestar.logit("createDataStores.main: Populating reporting periods");
            progress.nextTask(0.03, "Populating reporting periods")
            # mstarrun.run("populateReportingPeriods")

            # done
            mesg = "createDataStores.main: Done"
            minestar.logit(mesg);
            print mesg
            progress.done()
            os.chdir(cwd)
        if reportingInstance:
            minestar.logit('create reporting data warehouse instance')
            (cfg,dvl,dwh,dcl) = datastore.getReportingDataStores()
            ReportingInstancechecker = fixReportingDataStores(cfg,dvl,dwh,dcl,homeDrive,dataDrive)
            minestar.logit('result of fix data stores '+str(ReportingInstancechecker))
    except:
        minestar.logit("createDataStores.main: Caught exception");
        progress.fail(sys.exc_info()[0])
        import traceback
        traceback.print_exc()

