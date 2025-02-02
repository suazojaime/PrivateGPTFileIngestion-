import minestar
__version__ = "$Revision: 1.3 $"
logger = minestar.initApp()
import sys, os, string, time
import mstarpaths, mstaroverrides, mstarrun, i18n, datastore, oracleListener,oracleTnsNames, ServerTools,databaseDifferentiator

## Main Program ##

def main(appConfig=None):
    """entry point when called from mstarrun"""

    mstarpaths.loadMineStarConfig()
    dbobject = databaseDifferentiator.returndbObject()
    if not ServerTools.onServer():
        print i18n.translate("You can only do this operation while running on one of %s. This host is %s.") % (allowedHosts, thisComputer)
        minestar.exit()
    dbobject.isdbInstalled()

    dbobject.updateTnsNameFile()
    print i18n.translate("Finished updating database connection configuration")
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
