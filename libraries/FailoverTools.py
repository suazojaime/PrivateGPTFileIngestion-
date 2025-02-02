import os, fnmatch
import minestar, mstarpaths, datastore, ConfigurationFileIO

def deleteHistoricalStandbyData():
    # save curr work dir:
    currDir = os.getcwd()
    # change work dir to MSTAR_DATA
    mstarData = mstarpaths.interpretPath("{MSTAR_DATA}")
    os.chdir(mstarData)
    # get the "historical" datastore URL:
    histDb = datastore.getDataStore("_HISTORICALDB", "STANDBY")
    # set the dbdataman script name:
    exportSpecFileName = mstarpaths.interpretPath("{MSTAR_TEMP}/dbdataman_delete_essential_entities.txt")
    exportSpecFile = open(exportSpecFileName, "w")
    exportSpecFile.write('CLASS=Cycle OPERATION=Delete;\n')
    exportSpecFile.write('CLASS=Delay OPERATION=Delete;\n')
    exportSpecFile.close()
    histDb.dbdataman("-c", exportSpecFileName)

def getStandbyDelayFilter():
    mstarData = mstarpaths.interpretPath("{MSTAR_DATA}")
    oids = []
    oidFiles = fnmatch.filter(os.listdir(mstarData), "*ReferencedDelayOids.lst")
    for oidFile in oidFiles:
        #print "Processing delay oid file %s" % oidFile
        oidLines = ConfigurationFileIO.loadLinesFromFile(os.path.sep.join([mstarData, oidFile]))
        for oidLine in oidLines:
            if len(oidLine) == 0: continue
            oids.append(ConfigurationFileIO.cleanLine(oidLine))
    delayFilter = '"status != 7'
    if len(oids) > 0:
        delayFilter = delayFilter + ' OR delay_oid in ('
        i=1
        for oid in oids:
            delayFilter = delayFilter + oid
            if i < len(oids):
                delayFilter = delayFilter + ","
            i = i+1
        delayFilter = delayFilter + ')'
    cycleOidList = getStandbyCycleOids()
    if cycleOidList is not None:
        delayFilter = delayFilter + '-UNION- delay_oid in (select delayoid from cycledelay where oid in ' + cycleOidList + ')'
    delayFilter = delayFilter + '"'
    return delayFilter

def getStandbyCycleFilter():
    oidList = getStandbyCycleOids()
    if oidList is not None:
        return '"cycle_oid in ' + oidList + '"'
    return None

def getStandbyCycleOids():
    mstarData = mstarpaths.interpretPath("{MSTAR_DATA}")
    oids = []
    oidFiles = fnmatch.filter(os.listdir(mstarData), "*ActiveCycleOids.lst")
    for oidFile in oidFiles:
        #print "Processing cycle oid file %s" % oidFile
        oidLines = ConfigurationFileIO.loadLinesFromFile(os.path.sep.join([mstarData, oidFile]))
        for oidLine in oidLines:
            if len(oidLine) == 0: continue
            oids.append(ConfigurationFileIO.cleanLine(oidLine))
    if len(oids) > 0:
        oidList = '('
        i=1
        for oid in oids:
            oidList = oidList + oid
            if i < len(oids):
                oidList = oidList + ","
            i = i+1
        oidList = oidList + ')'
        return oidList
    return None

def updateNextOid(modelDb, histDb):
    histUser = histDb.user
    # Now ensure the next_oid value is correctly set - either from cycles or delays
    import databaseDifferentiator
    dataobject = databaseDifferentiator.returndbObject()
    modelDb.javaUpdate(dataobject.updateNextOid('c') % histUser)
    modelDb.javaUpdate(dataobject.updateNextOid('d') % histUser)
