import mstarpaths, datastore, mstarrun, minestar, os, sys, string, i18n, progress,databaseDifferentiator

APP = "purgeRecycleBin"
dbobject = databaseDifferentiator.returndbObject()

def purgeRecycleBin(dbName):
    # Assume _MODELDB, _HISTORICALDB, _TEMPLATEDB and _REPORTINGDB are configured in MineStar.properties
    # Instance names may not be more than 8 characters.
    # We must be on the database server host!
    # Usage purgeRecycleBin <logical data store name>
    try:
        progress.start(1000, "purgeRecycleBin")
        progress.task(0.01, "Loading configuration")
        cwd = os.getcwd()
        os.chdir(mstarpaths.interpretPath("{MSTAR_SYSTEM_HOME}"))
        # if not processing 'all' get the datastore specs
        if dbName != "all":
            purgeDS = datastore.getDataStore(dbName)
            if purgeDS != None:
                progress.nextTask(0.5, "Purging data store %s contents" % dbName)
                purgeDS.purgeRecycleBin()
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
# purgeRecycleBin receives 1 parameter,
#  Mandatory: DataStoreName eg. _MODELDB

def u(s):
    if sys.platform.startswith("win"):
        return s.upper()
    return s

if __name__ == '__main__':
    #dbobject.Dbhome();

    import mstarrun
    currentDbType = mstarpaths.interpretVar("_INSTANCE1_TYPE")
    if currentDbType == 'oracle' :
        config = mstarrun.loadSystem(sys.argv[1:])
        args = []
        if config.has_key("args"):
            args = config["args"]
        dbNames = args[0]
        dbIds = string.split(dbNames, ',')
        for dbName in dbIds:
            print "calling purgeRecycleBin() with DbName = %s" % (dbName)
            purgeRecycleBin(dbName)
    else:
        print "Usage: INSTANCE TYPE and database connection settings should be Oracle."
