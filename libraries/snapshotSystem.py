""" Copyright (C) 2021  Caterpillar, Inc.
    snapshotSystem.py takes snapshots of the OS and DB,
    exports the model DB, zips everything up and sends the result to support! """
import minestar

__version__ = "$Revision: 1.53 $"

_logger = minestar.initApp("snapshotSystem","snapshotSystem")
import sys, os, re
import mstarpaths, mstarrun, StringTools, exportData, zipSnapshot, datastore, ServerTools, FailoverTools, i18n, datetime
import filemutex, time, logging, shutil


USER_MODE = "USER"
AUTO_MODE = "AUTO"
STANDBY_MODE = "STANDBY"


SNAPSHOT_REASON_PREFIX = "__WhySnapshotTaken"
import databaseDifferentiator
dbobject = databaseDifferentiator.returndbObject()

def packSnapshotFilename(mode, customerCode, computerName, systemName, timestamp):
    """builds a snapshot filename from pieces."""
    # NOTE: If you change this, change the unpackSnapshotFilename() method as well!!
    return "Snap_" + mode + "_" + customerCode + "_" + computerName + "_" + systemName + "_" + timestamp + ".zip"

def unpackSnapshotFilename(filename):
    """unpacks a snapshot filename into a tuple of (mode, customerCode, computerName, systemName, timestamp)"""
    fileInfo = filename.split("_")
    mode = fileInfo[1]
    customerCode = fileInfo[2]
    computerName = fileInfo[3]
    systemName = fileInfo[4]
    timestamp = fileInfo[5]+"_"+fileInfo[6].split(".")[0]
    return (mode, customerCode, computerName, systemName, timestamp)

def exportEssentialEntities(options):
    # save curr work dir:
    currDir = os.getcwd()
    # change work dir to MSTAR_DATA and delete all files therein:
    mstarData = mstarpaths.interpretPath("{MSTAR_DATA}")
    tmpExportDir =  mstarpaths.interpretFormat("{TempDBDirectory}")
    if tmpExportDir is None:
        tmpExportDir = mstarpaths.interpretPath("{MSTAR_DATA}")
    import ServerTools
    tmpExportDir = mstarpaths.getUncPathOfMapDrive(tmpExportDir)

    failOverData = tmpExportDir +os.sep+"failover"
    os.chdir(mstarData)
    minestar.rmdir(failOverData)
    os.mkdir(failOverData)
    os.chdir(failOverData)
    # get the "historical" datastore URL:
    histDb = datastore.getDataStore("_HISTORICALDB")
    # set the dbdataman script name:
    exportSpecFileName = mstarpaths.interpretPath("{MSTAR_DATA}/dbdataman_export_essential_entities.txt")
    #print "exportEssentialEntities: making export spec file %s." % (exportSpecFileName)
    exportSpecFile = open(exportSpecFileName, "w")

    delayFilter = FailoverTools.getStandbyDelayFilter()
    if delayFilter is not None:
        exportSpecFile.write("CLASS=Delay OPERATION=WriteToFile WHERE="+delayFilter+";\n")

    cycleFilter = FailoverTools.getStandbyCycleFilter()
    if cycleFilter is not None:
        exportSpecFile.write("CLASS=Cycle OPERATION=WriteToFile WHERE="+cycleFilter+";\n")
    exportSpecFile.close()

    # call dbdataman with the appropriate script:
    histDb.dbdataman("-c", exportSpecFileName)
    os.chdir(currDir)

def exportKpiSummaryDimesions(options):
    # save curr wirk dir:
    currDir = os.getcwd()
    # change work dir to MSTAR_DATA and delete all files therein:
    mstarData = mstarpaths.interpretPath("{MSTAR_DATA}")
    tmpExportDir =  mstarpaths.interpretFormat("{TempDBDirectory}")
    if tmpExportDir is None:
        tmpExportDir = mstarpaths.interpretPath("{MSTAR_DATA}")
    import ServerTools
    tmpExportDir = mstarpaths.getUncPathOfMapDrive(tmpExportDir)
    failOverData = tmpExportDir +os.sep+"failover"
    os.chdir(mstarData)
    #os.chdir(failOverData)
    # get the "summary" datastore URL:
    summDb = datastore.getDataStore("_SUMMARYDB")
    # set the export optins:
    dbname = dbobject.getDBString()
    command = ["minestar.production.service.kpisummaries.util.PrintSummariesTables"]
    output = minestar.mstarrunEval(command)
    parts = output.split("SUMMARIES_TABLES=")
    if len(parts) > 1:
      output = parts[len(parts)-1]
      tableData = eval(output)
      if tableData.has_key("DIM_TABLES"):
          dimTables = tableData.get("DIM_TABLES")
          if(dbname=="Oracle"):
              exportOptions = "FILE=_SUMMARYDB_DIMENSIONS"+dbobject.getdumpfileExt()+" TABLES=(" + dimTables + ")"
              # call export with the appropriate options:
              summDb.expWithOptions(exportOptions,summDb,"_SUMMARYDB_DIMENSIONS"+dbobject.getdumpfileExt(),1)

      if tableData.has_key("FACT_TABLES"):
            # Now also export the CYCLE_FACT_MAIN table structure (ONLY):
            factTables = tableData.get("FACT_TABLES")
            if(dbname=="Oracle"):
                exportOptions = "FILE=_SUMMARYDB_EMPTY_FACT"+dbobject.getdumpfileExt()+" ROWS=N TABLES=(" + factTables + ")"
                # call export with the appropriate options:
                summDb.expWithOptions(exportOptions,summDb,"_SUMMARYDB_EMPTY_FACT"+dbobject.getdumpfileExt(),1)
    if(dbname=="sqlserver"):
         import ServerTools,mstarrun
         # create the format files which will define the table structure in a notepad file
         summdbdeleteimport = open(failOverData+os.sep+"summDbDeleteAndImport.txt","w")
         dimTablesarr   = dimTables.split(', ')
         currentDbServer = ServerTools.getDatabaseInstanceServerName(ServerTools.getCurrentDatabaseServer(), summDb)
         standByDbServer = ServerTools.getDatabaseInstanceServerName(ServerTools.getStandbyDatabaseServer(),summDb)
         try:
             # for CYCLE_FACT_MAIN
             if tableData.has_key("FACT_TABLES"):
                 controlFile=  failOverData+os.sep+"CYCLE_FACT_MAIN.fmt"
                 bcpCmd = "bcp " +summDb.user+".dbo.CYCLE_FACT_MAIN format nul -f " +controlFile +" -c -S "+currentDbServer+" -U "+ summDb.user+" -P "+summDb.user
                 minestar.run(bcpCmd)
                 # create the data files which will have the full data from selected tables
                 datFile =   failOverData+os.sep+"CYCLE_FACT_MAIN.dat"
                 factTables = tableData.get("FACT_TABLES")
                 bcpCmdDat="bcp " +summDb.user+".dbo.CYCLE_FACT_MAIN OUT "+datFile+ " -f "+controlFile+" -x -c -S "+currentDbServer+" -U "+ summDb.user+" -P "+summDb.user
                 minestar.run(bcpCmdDat)
                 # impcmd = "bcp " +summDb.user+".dbo."+factTables+" IN "+datFile+ " -f "+controlFile+" -x -c -S "+ServerTools.getStandbyDatabaseServer()+" -U "+ summDb.user+" -P "+summDb.user;
                 # Do not import the CYCLE_FACT_MAIN data as data is huge. In Oracle only Structure gets migrated that can be taken care by makeDataStore SUMMARY.
                 # Deletion of CYCLE_FACT_MAIN is necessary to re-import rest of the tables in SUMMARY database.
                 # delete STANDBY summary data before reimporting
                 delcmd = "sqlcmd -Q \"delete from "+"dbo."+factTables+"\""+ " -S "+standByDbServer+" -U "+ summDb.user+" -P "+summDb.user
                 summdbdeleteimport.write(delcmd+"\n")
                 # summdbdeleteimport.write(impcmd+"\n")
                 summdbdeleteimport.write(delcmd)

             for tableName in dimTablesarr:
                 controlFile=  failOverData+os.sep+tableName+".fmt"
                 bcpCmd = "bcp " +summDb.user+".dbo."+tableName+" format nul -f " +controlFile +" -c -S "+currentDbServer+" -U "+ summDb.user+" -P "+summDb.user
                 minestar.run(bcpCmd)
                 # create the data files which will have the full data from selected tables
                 datFile =   failOverData+os.sep+tableName+".dat"
                 bcpCmdDat="bcp " +summDb.user+".dbo."+tableName+" OUT "+datFile+ " -f "+controlFile+" -x -c -S "+currentDbServer+" -U "+ summDb.user+" -P "+summDb.user
                 minestar.run(bcpCmdDat)
                 impcmd = "bcp " +summDb.user+".dbo."+tableName+" IN "+datFile+ " -f "+controlFile+" -x -c -S "+standByDbServer+" -U "+ summDb.user+" -P "+summDb.user
                 # delete STANDBY summary data before reimporting
                 delcmd = "sqlcmd -Q \"delete from "+"dbo."+tableName+"\""+ " -S "+standByDbServer+" -U "+ summDb.user+" -P "+summDb.user
                 summdbdeleteimport.write(delcmd+"\n")
                 summdbdeleteimport.write(impcmd+"\n")

             summdbdeleteimport.close()
         except:
             _logger.warn("Exception during bcp command execution due to incorrect STANDBY Database Server configuration. Please configure correct STANDBY Database Server information.")

    # reset working directory:
    os.chdir(currDir)

def __deleteDuplicateWhyFiles():
    '''  Every time a user initiates a snapshot,  a file is created outlining the reason why the user did so.
         The trouble is that,  because a timestamp is included in the file name,  unless they are deleted they
         accumulate in the logs directory.  This method deletes accumulated "Why" files of the same type and machine
         name as the snapshot currently being taken (eg __WhySnapshotTaken_
    '''
    for file in os.listdir(mstarpaths.interpretVar("MSTAR_LOGS")):
        if file.startswith(SNAPSHOT_REASON_PREFIX) and file.endswith(ServerTools.getCurrentServer() + ".txt"):
            os.remove(mstarpaths.interpretVar("MSTAR_LOGS") + os.sep + file)



def _listBackups():
    checkFile = mstarpaths.interpretPath("{MSTAR_LOGS}/BackupDirList_{COMPUTERNAME}.log")
    backupDir = mstarpaths.interpretPath("{MSTAR_DATA}")
    ZIP_CMD = mstarpaths.interpretPath("dir %s > %s" % (backupDir, checkFile))
    os.system(ZIP_CMD)
    return checkFile

def snapshotSystem(mode, options):
    _logger.info("Started snapshotSystem %s" % mode)
    mstarpaths.loadMineStarConfig()
    timestamp = mstarpaths.interpretFormat("{YYYY}{MM}{DD}_{HH}{NN}")

    # Determine what to include in snapshot and the reason for including / excluding it
    # Also prohibit Auto and Standby snapshots run on a computer that is not the server

    includeEssentialEntities = None
    reasonForIncludeEssentialEntities = None
    reasonForIncludeKpiSummariesInfo = None
    includeTrace = 0
    reasonForIncludeTrace = "not a User snapshot"
    includeModelDataValidation = 0
    reasonForIncludeModelDataValidation = "Model Data Validation not requested (by -x option)"
    includeOnboard = 0
    reasonForIncludeOnboard = "not requested by -o option"
    includeDXF = 0
    reasonForIncludeDXF = "not requested by -d option"
    includeExtData = 0
    includeKpiSummariesInfo = 0
    reasonForIncludeKpiSummariesInfo = "not requested by -k option"
    reasonForIncludeExtData = "not requested by -e option"
    includeThreadDumps = 0
    reasonForIncludeThreadDumps = "not a User snapshot"

    tmpExportDir =  mstarpaths.interpretFormat("{TempDBDirectory}")
    if tmpExportDir is None:
        tmpExportDir = mstarpaths.interpretPath("{MSTAR_DATA}")
    tmpExportDir = mstarpaths.getUncPathOfMapDrive(tmpExportDir)

    # if options.networkdbsystem is None:
    #     options.networkdbsystem = mstarpaths.interpretPath("{MSTAR_DATA}")
    #     _logger.info("Taking the default Mstar Data Folder %s" % options.networkdbsystem )

    if mode == AUTO_MODE:
        if not ServerTools.onServer():
            _logger.info("Requesting reason for running the snapshot")
            mstarrun.run(["whySnapshot"])
            mstarrun.run(["createServerSnapshot"])
            return
        monitorType = "H"
        lookbackVar = "SNAPSHOT_AUTO_HOURS_LOOKBACK"
        includeEssentialEntities = 0
        reasonForIncludeEssentialEntities = "it's not a Standby snapshot"
    elif mode == USER_MODE:
        monitorType = "U"
        lookbackVar = "SNAPSHOT_USER_HOURS_LOOKBACK"
        __deleteDuplicateWhyFiles()
        if options.why is None:
            _logger.info("Requesting reason for running the snapshot")
            mstarrun.run(["whySnapshot"])
        else:
            mstarrun.run(['whySnapshot', options.why])
        if options.truck is None and options.duration is None :
            _logger.info("Opening truck snapshot dialog")
            mstarrun.run(["truckSnapshot"])
        else:
            if options.truck is None and options.duration is not None:
                _logger.info("Duration may not be specified without --trucks option")
                minestar.exit()
            else:
                if options.duration is None:
                    _logger.info("Opening truck snapshot dialog")
                    mstarrun.run(["truckSnapshot", "--takeTrucks", options.truck])
                else:
                    _logger.info("Non interactive truck snapshot")
                    mstarrun.run(["truckSnapshot", "--takeTrucks", options.truck, "--duration", options.duration, "--title", options.title, "--comment", options.comment, "--endDate", options.endDate])

        includeEssentialEntities = 0
        reasonForIncludeEssentialEntities = "it's not a Standby snapshot"
        if options.noThreadDumps:
            includeThreadDumps = 0
            reasonForIncludeThreadDumps = "no thread dumps requested (by -u option)"
        elif ServerTools.onAppServer():
            includeThreadDumps = 1
            reasonForIncludeThreadDumps = "it's a User snapshot run on the server"
        else:
            includeThreadDumps = 0
            reasonForIncludeThreadDumps = "they are not included in User snapshots that are not run on the server"

        if options.validate:
            includeModelDataValidation = 1
            reasonForIncludeModelDataValidation = "Model Data Validation requested (by -x option)"

        includeTrace = 1
        reasonForIncludeTrace = "User snapshot"
    elif mode == STANDBY_MODE:
        if not ServerTools.onServer():
            _logger.critical("Stand-by snapshots can only be generated on a server")
            return
        monitorType = None
        lookbackVar = None
        includeEssentialEntities = 1
        reasonForIncludeEssentialEntities = "it's a Standby snapshot"
        includeKpiSummariesInfo = 1
        reasonForIncludeKpiSummariesInfo = "it's a Standby snapshot"
    else:
        _logger.critical("Unknown snapshot mode %s - no snapshot will be generated", mode)
        return

    if options.onboard:
        includeOnboard = 1
        reasonForIncludeOnboard = "requested by -o option"
    if options.dxf:
        includeDXF = 1
        reasonForIncludeDXF = "requested by -d option"
    if options.kpisummaries:
        includeKpiSummariesInfo = 1
        reasonForIncludeKpiSummariesInfo = "requested by -k option"
    if options.extData:
        includeExtData = 1
        reasonForIncludeExtData = "requested by -e option"

    # Run the snapshot processes
    
    # initiate thread dumps on all server processes
    if includeThreadDumps:
        _logger.info("Running thread dumps as %s" % reasonForIncludeThreadDumps)
        mstarrun.run("InvokeThreadDumps", { "passBusUrl" : 1 })
    else:
        _logger.info("Skipping thread dumps as %s" % reasonForIncludeThreadDumps)
        
    backupDirList = None
    if monitorType:
        snapshotOsLog = mstarpaths.interpretPath("{MSTAR_TEMP}/snapshotOs_{COMPUTERNAME}.log")
        _logger.info("Running snapshotOS %s and putting results into %s" % (monitorType,snapshotOsLog))
        mstarrun.run(["snapshotOs", monitorType, snapshotOsLog])
        # determine if the computer running the snapshot is the DB Server:
        if not sys.platform.startswith("win") or ServerTools.onDbServer():
            # Run the DB snapshot in "Daily" or "User" mode for both datastores:
            if monitorType == "H":
                monitorType = "D"
            _logger.info("Running snapshotDb model %s" % monitorType)
            output = minestar.mstarrunEvalRaw(["snapshotDb",  "model", monitorType])
            if output != "(no output)":
                for line in output:
                    _logger.info(line)
            _logger.info("Running snapshotDb historical %s" % monitorType)
            output = minestar.mstarrunEvalRaw(["snapshotDb",  "historical", monitorType])
            if output != "(no output)":
                for line in output:
                    _logger.info(line)
            # List contents of the DBExports (MSTAR_DATA or MSTAR_EXPORTS) directories:
            backupDirList = _listBackups()
        else:
            _logger.info("Skipping snapshotDb as not on Db Server")
    else:
        _logger.info("Skipping snapshotOs and snapshotDb as monitor type is not set")



    # Run the inspector to include a report of issues with the mine model in the snapshot
    if includeModelDataValidation:
        _logger.info("Running inspector as %s" % reasonForIncludeModelDataValidation)
        mstarrun.run(["inspectModel"])
    else:
        _logger.info("Skipping inspector as %s" % reasonForIncludeModelDataValidation)

    # export the model database into the MSTAR_TEMP directory (as MSTAR_DATA is skipped by zipSnapshot).
    # export the pitmodel database into the MSTAR_TEMP directory
    # Note that snapshot
    exportDbFile = None
    exportPitmodelDbFile = None

    exportDir = mstarpaths.interpretPath("{MSTAR_TEMP}")
    _logger.info("Running exportData _MODELDB")
    # Adding one more parameter networkdbsystem for remote data base export option.
    (exportErrorCode,exportDbFile) = exportData.exportData("_MODELDB", exportDir,0,0,0,0, timestamp=timestamp, tmpExportDir=tmpExportDir)
    _logger.info("Running exportData _PITMODELDB")
    # Adding one more parameter networkdbsystem for remote data base export option.
    (exportErrorCode,exportPitmodelDbFile) = exportData.exportData("_PITMODELDB", exportDir,0,0,0,0, timestamp=timestamp, tmpExportDir=tmpExportDir)

    # get Metrics
    if mode != STANDBY_MODE:
        try:
            mstarrun.run("generateMetrics -shifts 3")
            _logger.info("generateMetrics completed")
        except:
            _logger.info("generateMetrics failed")
    else:
        _logger.info("Skipping generateMetrics - STANDBY")
    
    # Find the number of hours to lookback
    if lookbackVar is None:
        # stand-by snapshots don't collects logs, trace and other junk
        lookbackHours = -1
    else:
        try:
            lookbackHours = int(mstarpaths.interpretVar(lookbackVar))
        except:
            _logger.warn("Option %s not set - including all files found", lookbackVar)
            lookbackHours = 0

    # Create dir for kpi summaries info and maybe essential entities
    if includeEssentialEntities or includeKpiSummariesInfo:
        #failoverdir = mstarpaths.interpretPath("{MSTAR_DATA}/failover")
        #tmpExportDir =  mstarpaths.interpretPath("{TempDBDirectory}")
        #if tmpExportDir is None:
        #    tmpExportDir =  mstarpaths.interpretPath("{MSTAR_DATA}")
        failoverdir = tmpExportDir+os.sep+"failover"
        if minestar.isDirectory(failoverdir):
            _logger.warning("Directory %s already exists - will be re-created!", failoverdir)
            try:
                minestar.rmdir(failoverdir)
            except OSError, err:
                _logger.warning("Directory %s cannot be removed - will be overwritten!", failoverdir)
        try:
            os.mkdir(failoverdir)
        except OSError, err:
            _logger.error("Failed to create snapshot failover data directory %s: %s", failoverdir, err)

    if includeEssentialEntities:
        _logger.info("Exporting Essential Entities as %s" % reasonForIncludeEssentialEntities)
        exportEssentialEntities(options)
    else:
        _logger.info("Skipping exporting Essential Entities as %s" % reasonForIncludeEssentialEntities)

    if includeKpiSummariesInfo:
        _logger.info("Exporting KPI Summaries as %s" % reasonForIncludeKpiSummariesInfo)
        exportKpiSummaryDimesions(options)
    else:
        _logger.info("Skipping exporting KPI Summaries as %s" % reasonForIncludeKpiSummariesInfo)

    # get Geoserver Layers
    if mode == STANDBY_MODE:
        _logger.info("Skipping exportGeoLayers - STANDBY")
    else:
        # Check Geoserver is a selected server
        servers = mstarpaths.interpretVar("_START").split(",")

        # Skip if Geoserver is a not a selected server
        if "GeoServer" in servers:
            try:
                mstarrun.run("-W -C exportGeoLayers -o "+mstarpaths.interpretPath("{MSTAR_TEMP}"))
                _logger.info("exportGeoLayers completed")
            except:
                _logger.info("exportGeoLayers failed")
        else:
            _logger.info("Skipping exportGeoLayers - GeoServer not available")

    # Get the path for the snapshot file and create the snapshot
    custcode = mstarpaths.interpretPath("{_CUSTCODE}")
    thisMachine = mstarpaths.interpretVar("COMPUTERNAME")
    systemName = mstarpaths.interpretPath("{MSTAR_SYSTEM}")
    zipName = packSnapshotFilename(mode, custcode, thisMachine, systemName, timestamp)
    zipPath = mstarpaths.interpretPath("{MSTAR_ADMIN}/" + zipName)
    _logger.info("Zipping snapshot")


    zipSnapshot.zipSnapshot(zipPath, exportDbFile, exportPitmodelDbFile,
                            lookbackHours, includeEssentialEntities, includeTrace, includeOnboard, includeDXF, includeExtData)
    # Stand-by snapshots go into the data backups directory.
    # Otherwise, send the snapshot to support - done by copying the Snapshot to 'outgoing'.
    if mode == STANDBY_MODE:
        #currentSystem = mstarpaths.interpretVar("MSTAR_SYSTEM")
        standbyDir = mstarpaths.interpretPath("{MSTAR_STANDBY}")
        destination = None
        if standbyDir is None or standbyDir == "" or standbyDir== "{MSTAR_STANDBY}":
            destination = mstarpaths.interpretPath("{MSTAR_DATA_BACKUPS}")
        else:
            destination = mstarpaths.interpretPath("%s/data/standby" % (standbyDir))

        if destination is None or destination == "" or destination == "{MSTAR_DATA_BACKUPS}" or destination == "{MSTAR_STANDBY}":
            _logger.info ("{MSTAR_DATA_BACKUPS}/{MSTAR_STANDBY} directory is not specified or invalid to copy stand-by snapshot.")
    else:
        destination = mstarpaths.interpretPath("{MSTAR_OUTGOING}")
    if destination is not None and destination != "" and not destination in ['{MSTAR_DATA_BACKUPS}', '{MSTAR_STANDBY}', '{MSTAR_OUTGOING}']:
        try:
            if not os.path.isdir(destination):
                os.makedirs(destination)
            _logger.info("Copying snapshot to %s/%s " % (destination, zipName))
            minestar.copy(zipPath, destination, True)
        except:
            _logger.info("Failed to copy snapshot to %s" % destination)


    # Clean up the db export if one was created
    if exportDbFile is not None:
        try:
            os.remove(exportDbFile)
            _logger.info("Removed %s", exportDbFile)
        except OSError, ex:
            _logger.warn("Failed to delete %s - %s", exportDbFile, ex)

    # Clean up the pitmodel db export if one was created
    if exportPitmodelDbFile is not None:
        try:
            os.remove(exportPitmodelDbFile)
            _logger.info("Removed %s", exportPitmodelDbFile)
        except OSError, ex:
            _logger.warn("Failed to delete %s - %s", exportPitmodelDbFile, ex)

    # Ensure the standby system in synced if required
    #dbname = dbobject.getDBString();
    #if(dbname=="Oracle"):
    if mode == STANDBY_MODE and not options.quick:
        if ServerTools.onAppServer() and not ServerTools.isStandbyDbRole():
            cmd = ["syncStandbyInformation", "-a", "-i", "config,updates,onboard,data"]
            #_logger.info("Standby Snapshot - Syncing the standby application server using command %s " % cmd)
            mstarrun.run(cmd)
        if ServerTools.getStandbyDatabaseServer() is not None:
            cmd = ["initStandbyDbFromSnapshot", "-a", zipPath]
            #_logger.info("Standby Snapshot - Initialising the standby database from the snapshot using command %s " % cmd)
            mstarrun.run(cmd)
    _logger.info("Finished snapshotSystem %s" % mode)

## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [\
      make_option("-d", "--dxf", action="store_true", help="include dxf files"),
      make_option("-k", "--kpisummaries", action="store_true", help="include KPI summaries dxf backup"),
      make_option("-o", "--onboard", action="store_true", help="include onboard files"),
      make_option("-q", "--quick", action="store_true", help="quick mode - do not update standby system"),
      make_option("-s", "--sync", action="store_true", help="Sync the cycle state cache."),
      make_option("-w", "--why", dest="why", help="the reason the system is being snapshotted - replaces dialog"),
      make_option("-t", "--trucks", dest="truck", help="A comma seperated list of trucks from which to request a snapshot"),
      make_option("-r", "--duration", dest="duration", help="The duration in HH:MM:SS the snapshot should start before now. Maximum is 24:00:00. --trucks option must also be set"),
      make_option("-n", "--endDate", dest="endDate", help="The end date and time to finish the snapshot at as number"),
      make_option("-l", "--title", dest="title", help="The title to use for the truck snapshot"),
      make_option("-m", "--comment", dest="comment", help="The comment explinaing the truck snapshot"),
      make_option("-e", "--extData", action="store_true", help="include all folders and files under data/ext-data"),
      make_option("-x", "--validate", action="store_true", help="perform model data validation"),
      make_option("-u", "--noThreadDumps", action="store_true", help="exclude all thread dumps"),
        ]

    argumentsStr = "[USER|AUTO|STANDBY]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Take the snapshot
    if len(args) >= 1:
        mode = args[0].upper()
    else:
        mode = ''

    if not mode in ['AUTO', 'STANDBY', 'USER']:
        print i18n.translate("Invalid mode: %s. Choose one of %s" % (mode, argumentsStr))
        minestar.exit()

    if ServerTools.serversEqual(ServerTools.getProductionDatabaseServer(),ServerTools.getStandbyDatabaseServer()):
        print i18n.translate("Invalid DataBase Server Configuration: Production DataBase Server cannot be equal to Standby DataBase Server.")
        minestar.exit()

    mutex = filemutex.Mutex("snapshotSystem", 120)
    try:
        try:
            mutex.lock()
            snapshotSystem(mode, options)
        except filemutex.MutexError:
            _logger.warn("snapshotSystem could not acquire lock - no snapshot possible this invocation")
            now = datetime.datetime.now()
            then = datetime.datetime.fromtimestamp(os.path.getmtime(mutex.getFilename()))
            tdelta = now - then
            seconds = tdelta.total_seconds()
            retentionTime = int(mstarpaths.interpretFormat("{SNAPSHOT_SYSTEM_FOLDER_RETENTION}")) * 3600
            if(seconds > retentionTime):
                _logger.info("The directory %s is more that an hour old. Hence Deleting it." % mutex.getFilename())
                _logger.info("Deleting directory: %s" % mutex.getFilename())
                shutil.rmtree(mutex.getFilename(),1)
                _logger.info("Rerunning snapshotSystem")
                mutex.lock()
                snapshotSystem(mode, options)
            else:
                time.sleep(300)
                try:
                    mutex.lock()
                    snapshotSystem(mode, options)
                except filemutex.MutexError:
                    _logger.warning("snapshotSystem failed in process to acquire lock on directory after waiting: %s" % mutex.getFilename())
            minestar.exit(1)

    except SystemExit:
        try: 
            mutex.release()
        except filemutex.MutexError:
            _logger.info("Ignoring mutex release exception")
    finally:
        try: 
            mutex.release()
        except filemutex.MutexError:
            _logger.info("Ignoring mutex release exception")

    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
