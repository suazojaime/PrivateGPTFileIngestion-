import minestar
logger = minestar.initApp()
import mstarpaths, datastore, os, zipfile, sys

__version__ = "$Revision: 1.2 $"

def deleteBadFiles():
    files = os.listdir(".")
    for f in files:
        if f.endswith(".bad"):
            os.remove(f)

def processBadFiles():
    files = os.listdir(".")
    for f in files:
        if f.endswith(".bad"):
            print "IMPORT ERROR: %s" % f

def load(line, ds):
    line = line % ds.connectionString
    os.system(line)

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""
    #logger.info("importExportData.main: Started")
    optionDefns = [\
        make_option("-r", "--role", choices=['PRODUCTION', 'STANDBY', 'TEST'], help="the database role to load into"),\
        make_option("-d", "--datastore", choices=['_MODELDB', '_HISTORICALDB', '_SUMMARYDB'], help="the database to load into"),\
        make_option("-i", "--ignore", action="store_true", help="ignore missing directory and exit without error"),\
        ]
    argumentsStr = "<directory>"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    if len(args) == 0 or options.datastore is None:
        print "Usage: importExportedData [-r role] -d datastore [-i] <directory>"
        minestar.exit()
    dir = args[0]
    try:
        #logger.info("importExportData.main: Changing to directory %s " % dir)
        os.chdir(dir)
    except OSError:
        print "Can't find directory %s." % dir
        # This is possible on a system that hasn't put any data into the relevant areas yet - e.g. in development
        if options.ignore:
            sys.exit(0)
        else:
            sys.exit(1)
    #logger.info("importExportData.main: Loading MineStar config ")
    mstarpaths.loadMineStarConfig()
    role = options.role
    if role is None:
        role = "PRODUCTION"
    #logger.info("importExportData.main: Getting datastore %s role %s " % (options.datastore, role))
    ds = datastore.getDataStore(options.datastore, role)
    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject()
    dbname = dbobject.getDBString();
    if(dbname=="sqlserver" and options.datastore=='_SUMMARYDB'):
        filename = os.sep.join([dir, "summDbDeleteAndImport.txt"])
    else:
        filename = os.sep.join([dir, "import.txt"])

    #logger.info("importExportData.main: Reading import.txt file %s " % filename)
    for line in [ line.strip() for line in file(filename).readlines() if not line.startswith("@") ]:
        #logger.info("importExportData.main: Line is %s " % line)
        if(dbname=="sqlserver"):
            if line.startswith("cd"):
                os.chdir(line[3:])
            elif line.startswith("bcp"):
                os.system(line)
            elif line == "processBadFiles":
                os.chdir(os.pardir)
        else:
            if line.startswith("cd"):
                os.chdir(line[3:])
                deleteBadFiles()
            elif line == "processBadFiles":
                processBadFiles()
                os.chdir(os.pardir)
            elif line.startswith("sqlldr"):
                load(line, ds)
        #logger.info("importExportData.main: Finished line %s " % line)
    #logger.info("importExportData.main: Finished")

if __name__ == "__main__":
    """entry point when called from python"""
    main()
