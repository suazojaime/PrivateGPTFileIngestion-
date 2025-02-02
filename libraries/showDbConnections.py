import minestar
__version__ = "$Revision: 1.4 $"

logger = minestar.initApp()
import datastore, mstarpaths, sys, mstarrun, os


## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """Entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [make_option("-x", "--xxx", help="Specify a database")]
    argumentsStr = "arg1"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Process the arguments
    # (model, historical, template, summary, reporting) = datastore.getSystemDataStores()
    db = args[0]
    ds = datastore.getDataStore(db)
    if ds is not None:
        syspass = mstarpaths.interpretVar("_DB_SYS_AUTH")
        useradminpass = mstarpaths.interpretVar("_DB_ADMIN_USER_PASSWD")
        ds1 = ds.inSameInstance(mstarpaths.interpretVar("_DB_ADMIN_USER"), useradminpass)
        # print "Got DataStore connection for %s to %s_%s (%s)" %  (ds.user, ds.instance, ds.host, ds.connectionString)
        import databaseDifferentiator
        dbobject = databaseDifferentiator.returndbObject()

        dblocation ="{MSTAR_DATABASE}"+"/"+dbobject.getDBString().lower()+"/"
        scriptName = dblocation+"SchemaUtilities/show_connections.sql"
        if(dbobject.getDBString() == "Oracle"):
            ds1.sqlplus(mstarpaths.interpretPathShort(scriptName))
        elif(dbobject.getDBString()=="sqlserver"):
            dbobject.sqlcmd(ds,mstarpaths.interpretPathShort(scriptName),ds.user,ds.password)

if __name__ == '__main__':
    """Entry point when called from Python"""
    mstarpaths.loadMineStarConfig()
    main()
