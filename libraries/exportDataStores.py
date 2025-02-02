import minestar
logger = minestar.initApp()
import sys, string
import mstarpaths, datastore, backupToTape, ServerTools,os

DATA_STORES = {
    'Historical':   '_HISTORICALDB',
    'Model':        '_MODELDB',
    'Reporting':    '_REPORTINGDB',
    'Summary':      '_SUMMARYDB',
    'PitModel':     '_PITMODELDB',
    'Template':     '_TEMPLATEDB',
    'GIS':          '_GISDB',
    'BOAUDIT':      '_BOAUDITDB',
    }

OPTIONAL_DATA_STORES = {
    'Aquila':       '_AQUILADB',
    'CAES':         '_CAESDB',
    }

def exportDataStores(dataStores, exportDir=None, doZip=1, doAll=0, doEmailOnError=False,tmpExportDir=None):
    """
    Export a list of named data stores.
    exportDir - the directory to export to; if None, MSTAR_DATA is used
    doZip - zip the database dumps or not
    """
    valid = 0
    backupOption = mstarpaths.interpretVar("BACKUP_TO_TAPE")
    filesToBackup = []
    for ds in dataStores:
        internalName = DATA_STORES.get(ds) or OPTIONAL_DATA_STORES.get(ds)
        if internalName is None:
            print "WARNING: unknown data store %s - ignoring" % ds
        else:
            print "Now exporting datastores %s:" % ds
            import  exportData
            (valid,fileName) = exportData.exportData(internalName, exportDir, doZip, 1, 0, doEmailOnError,None,tmpExportDir)
            # For a 'Scheduled exportDataStores all' kick off a tape backup if 'valid'..
            if doAll == 1 and backupOption == "true":
                if valid == 0:
                    filesToBackup.append(fileName)

    if doAll == 1 and backupOption == "true":
        for fileName in filesToBackup:
            backupToTape.backupToTape(fileName)

## Main Program ##


def _printUsage(all, msg=None):
    if msg:
        print msg
    print "usage:"
    print "  exportDataStores                  - show this help"
    print "  exportDataStores [options] all    - export all data stores"
    print "  exportDataStores [options] x ...  - export the specified data stores"
    print "Data store names are %s." % string.join(all, ', ')
    print "The -txxx option specifies xxx as the DataBase system temp Directory - MSTAR_DATA is the default."
    print "The -dxxx option specifies xxx as the output directory - MSTAR_DATA is the default."
    print "The -Z option disables zipping of results."
    print "The -E option sends email if an error occurs."

if __name__ == '__main__':
    import mstarrun
    config = mstarrun.loadSystem(sys.argv[1:])
    args = []
    if config.has_key("args"):
        args = config["args"]

    # Check the usage
    allDataStores = DATA_STORES.keys()
    for ds in OPTIONAL_DATA_STORES.keys():
        usedKey = OPTIONAL_DATA_STORES.get(ds) + "_USED"
        used = mstarpaths.interpretVar(usedKey)
        if used != "true":
            continue
        if datastore.getDataStore(OPTIONAL_DATA_STORES.get(ds)) is not None:
            allDataStores.append(ds)
    allDataStores.sort()
    if len(args) == 0:
        _printUsage(allDataStores)
        sys.exit(0)

    # Parse the options
    doZip = 1
    doEmailOnError = False
    exportDir = None
    tmpExportDir = None
    while args[0].startswith("-"):
        if args[0] == "-Z":
            doZip = 0
        elif args[0].startswith("-d"):
            exportDir = args[0][2:]
        elif args[0].startswith("-E"):
            doEmailOnError = True
        else:
            _printUsage(allDataStores, "Unknown option %s" % args[0])
            sys.exit(1)
        args = args[1:]
    tmpExportDir =  mstarpaths.interpretPath("{TempDBDirectory}")
    tmpExportDir = mstarpaths.getUncPathOfMapDrive(tmpExportDir)
    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject()
    defaultDbExportDir = mstarpaths.interpretPath("{MSTAR_DATA}")
    if (dbobject.getDBString()=="sqlserver"):
        if tmpExportDir is None and ServerTools.onDbServer():
            tmpExportDir= defaultDbExportDir
        elif not ServerTools.onDbServer() and (tmpExportDir is None or tmpExportDir == '' or tmpExportDir == defaultDbExportDir):
            logger.error("Please specify shared path in Database system temp directory.")
            minestar.exit(1)
    elif tmpExportDir is None or tmpExportDir == '':
        tmpExportDir= defaultDbExportDir
    dirPrefix = os.sep+ServerTools.getCurrentDatabaseServer()
    if (tmpExportDir.upper().startswith(dirPrefix.upper())):
        tmpExportDir = os.sep+tmpExportDir
    # Get the data stores to export
    doAll = 0
    if args[0] == 'all':
        dataStores = allDataStores
        doAll = 1
    else:
        dataStores = args
    exportDataStores(dataStores, exportDir, doZip, doAll, doEmailOnError,tmpExportDir)
