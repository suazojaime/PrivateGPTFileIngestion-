import mstarpaths, datastore, mstarrun, minestar, os, sys, string, i18n, progress,databaseDifferentiator

APP = "emptyReportingDataStore"
dbobject = databaseDifferentiator.returndbObject()

def emptyReportingDataStore(dbName):
    # Assume _CFG, _DVL, _DWH and _DCL are configured in MineStar.properties
    # Instance names may not be more than 8 characters.
    # We must be on the database server host!
    # Usage emptyDataStores <logical data store name>
    try:
        progress.start(1000, "emptyReportingDataStores")
        progress.task(0.01, "Loading configuration")
        cwd = os.getcwd()
        os.chdir(mstarpaths.interpretPath("{MSTAR_SYSTEM_HOME}"))
        # if not processing 'all' get the datastore specs
        if dbName != "all":
            emptyDS = datastore.getDataStore(dbName,"DATAWAREHOUSE")
            if emptyDS != None:
                progress.nextTask(0.5, "Dropping data store %s contents" % dbName)
                emptyDS.dropAll(emptyDS)
            else:
                print "Data Store %s not found" % dbName
        # done
        progress.done()
        os.chdir(cwd)
    except:
        progress.fail(sys.exc_info()[0])
        import traceback
        traceback.print_exc()

#
## Main Program ##
#
# emptyDataStore receives 1 parameter,
#  Mandatory: DataStoreName eg. _DVL

def u(s):
    if sys.platform.startswith("win"):
        return s.upper()
    return s

if __name__ == '__main__':
    #dbobject.Dbhome();

    import mstarrun
    config = mstarrun.loadSystem(sys.argv[1:])
    args = []
    if config.has_key("args"):
        args = config["args"]
    dbNames = args[0]
    dbIds = string.split(dbNames, ',')
    for dbName in dbIds:
        print "calling emptyReportingDataStores() with DbName = %s" % (dbName)
        emptyReportingDataStore(dbName)
