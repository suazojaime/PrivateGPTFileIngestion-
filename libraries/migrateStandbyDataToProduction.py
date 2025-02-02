__version__ = "$Revision: 1.8 $"

import minestar
logger = minestar.initApp()
import sys, os,fnmatch
import mstarpaths, mstarrun, datastore, ServerTools


MIGRATE_SPEC = "CLASS=%s OPERATION=Migrate TARGET=%s;\n"
ESSENTIAL_CLASSES = ["Delay", "Cycle", "ProdRqst", "ScheduledBreak", "ShiftChange", "Personnel", "Transport", "TieDown"]
OTHER_CLASSES = ["Alarm", "Operator", "ProductionEvent", "AdministrationEvent", "AssignmentEvent", "HealthEvent", "NotificationEvent", "OperatorShift", "FluidAndSmuRecord"]

def migrateStandbyData(options):
    #create link in standby historical database to point to production
    hist = datastore.getDataStore("_HISTORICALDB")
    standbyHist = datastore.getDataStore("_HISTORICALDB", "STANDBY")
    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject()
    if(dbobject.getDBString()=="Oracle"):
        standbyHist.dropDBLink(hist.linkName)
        standbyHist.createDBLink(hist)
        logger.info("Link to production historical database created")
    else:
        dbobject.createLinkServer(hist,"production")
        dbobject.createLinkServer(standbyHist,"standby")
        logger.info("Link to production historical database created")

    # save curr work dir:
    currDir = os.getcwd()
    mstarData = mstarpaths.interpretPath("{MSTAR_DATA}")
    os.chdir(mstarData)
    # set the dbdataman script name:
    migrateSpecFileName = mstarpaths.interpretPath("{MSTAR_TEMP}/dbdataman_migrate.txt")
    migrateSpecFile = open(migrateSpecFileName, "w")
    MIGRATE_CLASSES = []
    if options.nonessential:
        MIGRATE_CLASSES = OTHER_CLASSES
    else:
        MIGRATE_CLASSES = ESSENTIAL_CLASSES
        if not options.essential:
            MIGRATE_CLASSES.extend(OTHER_CLASSES)

    for className in MIGRATE_CLASSES:
        migrateSpecFile.write(MIGRATE_SPEC % (className, hist.linkName))
    migrateSpecFile.close()

    # call dbdataman with the appropriate script:
    batchSize = int(mstarpaths.interpretVar("_ADMINDATA_BATCHSIZE"))
    standbyHist.dbdataman("-c", migrateSpecFileName, batchSize)
    os.chdir(currDir)

    #create link in standby summaries database to point to production
    summDb = datastore.getDataStore("_SUMMARYDB")
    standbySumm = datastore.getDataStore("_SUMMARYDB", "STANDBY")
    if(dbobject.getDBString()=="Oracle"):
        standbySumm.dropDBLink(summDb.linkName)
        standbySumm.createDBLink(summDb)
        logger.info("Link to production summaries database created")
    else:
        dbobject.createLinkServer(summDb,"production")
        dbobject.createLinkServer(standbySumm,"standby")
        logger.info("Link to production summaries database created")

    mstarrun.run(['migrateKpiSummaries', "-c", "-r STANDBY", "-t "+summDb.linkName ])

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    if not ServerTools.onServer():
        minestar.abort("This script can only be run from a server")

    # Process options and check usage
    optionDefns = [
      make_option("-e", "--essential", action="store_true", \
        help="Only migrate essential records - cycles, delays etc."),
      make_option("-n", "--nonessential", action="store_true", \
        help="Only migrate non-essential records - events, shift change records etc."),
      ]
    argumentsStr = "..."
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    mstarpaths.loadMineStarConfig()

    #ensure we are using the productin database
    logger.info("Switching to using production database")
    mstarrun.run(["switchActiveDatabase", "-r", "PRODUCTION"])
    mstarpaths.loadMineStarConfig(forceReload=1)
    #now copy the active delays etc across
    logger.info("Initialising production database from standby snapshot")
    migrateStandbyData(options)

    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()

