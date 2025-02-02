#  Copyright (c) 2020 Caterpillar

import minestar
import datastore, mstarpaths, sys, os

logger = minestar.initApp()


def report(logFile, count):
    logFile.write(`count` + "\n")


def cleanExpiredData(doCycles):
    # Save current working directory and chage to MSTAR_DATA (in case of any data exports)
    cwd = os.getcwd()
    os.chdir(mstarpaths.interpretPath("{MSTAR_DATA}"))

    # Set up values for DBDataMan run...
    mstarpaths.loadMineStarConfig()

    minestar.createExpectedDirectory(mstarpaths.interpretPath("{MSTAR_DATA}"))

    historical = datastore.getDataStore("_HISTORICALDB")
    pitmodel = datastore.getDataStore("_PITMODELDB")
    gis = datastore.getDataStore("_GISDB")

    # Set up a log file:
    logFileName = mstarpaths.interpretPath("{MSTAR_LOGS}/deleteAgedEntities_{YYYY}{MM}{DD}{HH}{NN}{SS}.log")
    logFile = open(logFileName, "w")

    cleanExpiredDataForDataStore(historical, logFile, doCycles)
    cleanExpiredGisData(gis, logFile, doCycles)

    # Close logfile
    logFile.close()

    # Change back to where executed from:
    os.chdir(cwd)


def cleanExpiredDataForDataStore(dataStore=None, logFile=None, doCycles=False):
    import makeDBDataManTemplate
    if dataStore is None:
        return

    # create a DBDataMan deletions file from the template:
    tempFileName = makeDBDataManTemplate.makeDBDataManTemplate(dataStore.logicalName,doCycles)
    print "Running DBDataMan deletions file %s" % tempFileName
    countBefore = dataStore.countAgedEntities()
    report(logFile, countBefore)
    batchSize = int(mstarpaths.interpretVar("_ADMINDATA_BATCHSIZE"))
    output = dataStore.dbdataman("-ct", tempFileName, batchSize)
    logFile.write(output + "\n")
    countAfter = dataStore.countAgedEntities()
    report(logFile, countAfter)


def cleanExpiredGisData(dataStore=None, logFile=None, doCycles=False):
    import makeDBDataManTemplate, mstarrun
    if dataStore is None:
        return

    # create a DBDataMan deletions file from the template:
    tempFileName = makeDBDataManTemplate.makeDBDataManTemplate(dataStore.logicalName,doCycles)
    print "Running GISDBDataMan deletions file %s" % tempFileName
    output = minestar.mstarrunEvalLines(["gisDBDataMan", "-input", tempFileName])
    logFile.write(output + "\n")

if __name__ == '__main__':
    import mstarrun
    config = mstarrun.loadSystem(sys.argv[1:])
    args = []
    if config.has_key("args"):
        args = config["args"]
    doCycles = ('--includeCycleData' in args)
    cleanExpiredData(doCycles)
