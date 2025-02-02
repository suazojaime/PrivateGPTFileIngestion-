import minestar
logger = minestar.initApp()
import mstarpaths, datastore, os, zipfile, re

__version__ = "$Revision: 1.2 $"

def main(appConfig=None):
    """entry point when called from mstarrun"""
    argumentsStr = "<datastore> <dumpfile>"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, [], argumentsStr)
    if len(args) == 0:
        print "Usage: import " + argumentsStr
        minestar.exit()
    datastorename = args[0]
    filename = args[1]
    mstarpaths.loadMineStarConfig()
    ds = datastore.getDataStore(datastorename)
    if filename.endswith(".zip"):
        dir = os.path.split(filename)[0]
        minestar.unpack(zipfile.ZipFile(filename), dir)
        import databaseDifferentiator
        dbobject = databaseDifferentiator.returndbObject()
        filename = filename[0:-4] + dbobject.getdumpfileExt()

    #checking whether the database specific file is used (.dmp or .bak), cross usage is prohibited.
    oracleSuffix = "dmp";
    sqlSuffix = "bak";
    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject()
    if (dbobject.getDBString()=="sqlserver"):
        if not filename.lower().endswith(sqlSuffix):
            print "ERROR: Oracle dmp files cannot be imported into SQL SERVER"
            minestar.exit()
    else:
        if not filename.lower().endswith(oracleSuffix):
            print "ERROR: SQL BAK files cannot be imported into ORACLE"
            minestar.exit()
    filename = mstarpaths.validateFile(filename,options)
    # import the file to the model and the historical
    ds.reimport(filename,ds)

    dataDir = mstarpaths.interpretPath("{MSTAR_DATA}")
    print "Removing Cycle DAT and LST Files as they are now invalid"
    for f in os.listdir(dataDir):
        if re.search('\.dat', f) or re.search('\.lst', f):
            os.remove(os.path.join(dataDir, f))

if __name__ == "__main__":
    """entry point when called from python"""
    main()
