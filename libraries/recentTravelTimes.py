#  Copyright (c) 2020 Caterpillar

import minestar
__version__ = "$Revision: 1.6 $"

logger = minestar.initApp()
import sys, os, time
import mstarpaths, ufs, datastore, mstarrun
import databaseDifferentiator

dbobject = databaseDifferentiator.returndbObject()

def dumpRecentTravelTimes(days):
    """dump the recent travel times to a file. Returns true if everything succeeded. """

    # Find the script using UFS
    ufsPath = mstarpaths.interpretVar("UFS_PATH")
    ufsRoot = ufs.getRoot(ufsPath)
    if dbobject.getDBString() == "sqlserver":
        scriptFile = "/reports/queries/traveltime_segmentanalysis_mssql.sql"
    else:
        scriptFile = "/reports/queries/traveltime_segmentanalysis.sql"

    ufsFile = ufsRoot.get(scriptFile)
    if ufsFile is not None:
        script = ufsFile.getPhysicalFile()
    else:
        logger.error("Unable to find %s on the UFS path", scriptFile)
        return False

    # Run the script
    # old: sqlExtract = mstarpaths.interpretPath("{MSTAR_DATA}/traveltime_segmentanalysis_output.txt")
    travelData = mstarpaths.interpretPath("{MSTAR_DATA}/TravelTimeData.txt")
    hist = datastore.getDataStore("_HISTORICALDB")
    logger.info("script=%s", script)
    if dbobject.getDBString() == "sqlserver":
        dbobject.sqlcmdForExport(hist, script, hist.user, hist.user, travelData, [days])
    else:
        hist.sqlplus(script, [travelData, days])

    if not os.access(travelData, os.F_OK):
        logger.error("Could not extract the data from data store %s", hist.connectionString)
        return False

    # logger.info("Data extracted to %s", travelData)
    # mstarrun.run(["com.mincom.works.cc.test.RoadTimeData", sqlExtract, travelData])
    logger.info("Data summarized to %s", travelData)
    return True


## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = "days"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Dump the recent travel times
    mstarpaths.loadMineStarConfig()
    days = args[0]
    if dumpRecentTravelTimes(days):
        minestar.exit()
    else:
        minestar.exit(minestar.EXIT_ERROR)

if __name__ == "__main__":
    """entry point when called from python"""
    main()
