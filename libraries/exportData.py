import minestar
logger = minestar.initApp()
import os, mstardebug, i18n, adminPrefixIfOld, mstarpaths, sys, ServerTools

# These are the options for the different types of exports
mstarpaths.loadMineStarConfig()
import databaseDifferentiator
dbobject = databaseDifferentiator.returndbObject()
OPTIONS = {
    "consistent" : [
        "log={1}/{2}.log",
        "file={1}/{2}"+dbobject.getdumpfileExt(),
        "consistent=y",
        "direct=n"
    ],
    "direct" : [
        "log={1}/{2}.log",
        "file={1}/{2}"+dbobject.getdumpfileExt(),
        "direct=y",
        "consistent=y"
    ],
    "datapump" : [
        "DIRECTORY=datapump",
        "DUMPFILE={2}"+dbobject.getdumpfileExt(),
        "LOGFILE={2}.log",
        "JOB_NAME='EXPORT_DUMP'"
    ]
}

def _formatExportOptions(options, params):
    newOptions = ""
    for line in options:
        newLine = line
        if newLine.find("{1}") >= 0:
            newLine = mstarpaths.interpretFormatOverride(line, params)
        if newLine.find("{2}") >= 0:
            newLine = mstarpaths.interpretPathOverride(line, params)
        # newOptions.append(newLine)
        newOptions= newOptions + os.linesep + newLine
    return newOptions

def buildZipFilename(dbName, customerCode, timestamp):
    return "%s_%s_%s.zip" % (dbName,customerCode,timestamp)

def buildExportFilename(dbName, customerCode, timestamp):
    return "%s_direct_export_%s_%s" % (dbName,customerCode,timestamp)+ dbobject.getdumpfileExt()

def sendExportErrorsMail(msg):
    import smtplib, mstaremail

    if not mstaremail.isExternalEmailEnabled() and not mstaremail.isInternalEmailEnabled():
        minestar.logit("Email not enabled, not sending any : " + msg)
        return

    subject = "DBEXPORT ERRORS on host %s !" % mstarpaths.interpretVar("COMPUTERNAME")

    (fromaddr, server) = mstaremail.__getSMTP()
    toaddrs = mstarpaths.interpretVar("_EMAILRECIPIENT")

    # Add the From: and To: headers at the start!
    message = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % (fromaddr, toaddrs, subject))
    message = message + msg

    try:
        server.set_debuglevel(1)
        server.sendmail(fromaddr, toaddrs, message)
        server.quit()
    except:
        minestar.logit("Could not sendExportErrorMail() failed!")

def _validateArchive(archive, logFile):
    import string
    valid = True
    checkFile = "%s.txt" % logFile[:-4]
    logFile = string.replace(logFile, "\\","/")
    import mstarrunlib
    mstarrunlib.configureJava()
    ZIP_CMD = _escapeCmd(mstarpaths.interpretPath("{JAVA_HOME}/bin/jar{EXE}")) + (" -tvf %s > %s" % (archive, checkFile))
    # verify the contents of the archive:
    os.system(ZIP_CMD)
    #
    infile = open(checkFile, "r")
    finished = 0
    found = 0
    findIdx = -1
    lineCount = 0
    in_line = infile.readline()
    while (finished == 0):
        if (in_line == '') or (in_line is None):
           finished = 1
           break
        lineCount = lineCount + 1
        findIdx = string.find(in_line, logFile, 0)
        if findIdx >= 0:
            valid = False
            break
        in_line = infile.readline()

    # check if not found then log an error:
    #if valid != 0:
    #    msg = "ERROR: DBEXPORT Archive File %s could not be validated because it could not be opened!" % archive
    #    minestar.logit(msg)
    #    sendExportErrorsMail(msg)
    #else:
    #    msg = "SUCCESS: DBEXPORT archived OK!"
    #    sendExportErrorsMail(msg)

    # close and remove the checkfile:
    infile.close()
    os.remove(checkFile)
    return valid

def _escapeCmd(cmd):
    if cmd.find(" ") >= 0:
        return '"' + cmd + '"'
    else:
        return cmd

def _get_export_type(dbName):
    dbs_require_nondirect_export = ['_MODELDB', '_PITMODELDB']
    if dbName in dbs_require_nondirect_export:
        return 'consistent'
    return 'direct'

def exportData(dbName, exportDir=None, doZip=1, backupZip=1, sendExport=0, sendEmailOnError=0, timestamp=None ,tmpExportDir=None):
    """
    Export the named database.
    exportDir - the directory to export to; if None, MSTAR_DATA is used
    tmpExportDir - the remote DB system's temp directory to export to; if None, MSTAR_DATA is used
    doZip - zip the backed up database or not
    backupZip - copy the zip to MSTAR_DATA_BACKUPS or not
    sendExport - send the export to support or not
    timestamp - the string to use as the timestamp or None to use the current date and time
    Returns (errorCode,name of the exported file).
    """
    validAll = 0
    validExp = 0
    validZip = 0
    if timestamp is None:
        timestamp = mstarpaths.interpretFormat("{YYYY}{MM}{DD}_{HH}{NN}")
    customerCode = mstarpaths.interpretFormat("{_CUSTCODE}")
    import datastore
    db = datastore.getDataStore(dbName)
    if db is None or not db.valid:
        print i18n.translate("DataStore %s is not defined or is badly defined") % dbName
        return (8,None)
    # MSPATH-1837 - Presently configuration always has db.exportType = None. Getting this configuration needs to be fixed.
    if not db.exportType:
        exportType = _get_export_type(dbName)
    else:
        exportType = db.exportType
    if exportType not in OPTIONS.keys():
        print i18n.translate("Unknown export type %s for data store %s") % (exportType, dbName)
        return(31,None)
    exportName = "%s_%s_export_{_CUSTCODE}_%s" % (dbName,'direct',timestamp)
    exportName = mstarpaths.interpretFormat(exportName)
    if exportDir is None:
        exportDir = mstarpaths.interpretPath("{MSTAR_DATA}")
    #Checking the temp directory to export to; if None, MSTAR_DATA is used
    if tmpExportDir is None:
        tmpExportDir = mstarpaths.interpretPath("{MSTAR_DATA}")

    #tmpExportDirPrefix = os.sep+os.sep+ServerTools.getCurrentDatabaseServer();
    #if (not ServerTools.onDbServer()):
    #    if (not tmpExportDir.startswith(tmpExportDirPrefix)):
    #        logger.error("Invalid Remote DataBase system temp Directory %s" % tmpExportDir )
    #        logger.error("Example Remote DataBase system shared Directory starts with %s" % tmpExportDirPrefix )
    #        minestar.exit()

    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject()
    if ServerTools.onDbServer() and (db.logicalName =='_SUMMARYDB' or db.logicalName=='_HISTORICALDB')and (dbobject.getDBString()=="Oracle"):
        params = { "1" : tmpExportDir, "2" : exportName+"_datapump"+db.user}
        fileName = tmpExportDir + os.sep + exportName  +"_datapump"+db.user+ dbobject.getdumpfileExt()
        options = _formatExportOptions(OPTIONS['datapump'], params)
        db.datapumpReadWrite(tmpExportDir)
    else:
        params = { "1" : tmpExportDir, "2" : exportName}
        fileName = tmpExportDir + os.sep + exportName + dbobject.getdumpfileExt()
        options = _formatExportOptions(OPTIONS[exportType], params)




    # do the export and record what we did



    output = db.expWithOptions(options,db,fileName)
    if output == "Fail":
        mesg = i18n.translate("Failed to export data store %s to %s") % (dbName, fileName)
        minestar.logit(mesg)
        logger.info(mesg)
        # not sure what to set the export error code to because there are no guidelines, and
        # as far as I can see it is no used by the calling code
        return(15, None)
    #if output != "(no output)":
    #    for line in output:
    #        logger.info(line)
    mesg = i18n.translate("Exported data store %s to %s") % (dbName, fileName)
    minestar.logit(mesg)
    logger.info(mesg)

    # Set up log file name to check for errors:
    logfile = "%s.log" % fileName[:-4]
    # Validate the export Log file

    (hasErrors, numOraErrs, numExpErrs)  = dbobject.validateExport(logfile, fileName)
    if sendEmailOnError and numOraErrs != 0 or numOraErrs != 0:
        msg = i18n.translate("ERROR: DBEXPORT found %d ORA- Errors and %d EXP- Errors found in logFile %s! " % (numOraErrs, numOraErrs, logfile))
        sendExportErrorsMail(msg)

    import time
    time.sleep( 5 )
    # zip the result if requested
    if doZip:
        import mstarrun
        # re-create a shorter export Name eg. without "direct_export"
        archive = buildZipFilename(dbName,customerCode,timestamp)
        archive = mstarpaths.interpretFormat(archive)
        archiveShortName = archive
        archive = tmpExportDir + os.sep + archive
        fileName = archive
        if os.access(archive, os.F_OK):
            os.remove(archive)
        import databaseDifferentiator
        dbobject = databaseDifferentiator.returndbObject()    
        if ServerTools.onDbServer() and (db.logicalName =='_SUMMARYDB' or db.logicalName=='_HISTORICALDB')and (dbobject.getDBString()=="Oracle"):
            filePattern = tmpExportDir + os.sep + exportName + "_datapump"+db.user+".*"
            fileJustDmp = tmpExportDir + os.sep + exportName +"_datapump"+ db.user+dbobject.getdumpfileExt()
        else:
            filePattern = tmpExportDir + os.sep + exportName + ".*"
            fileJustDmp = tmpExportDir + os.sep + exportName + dbobject.getdumpfileExt()
        import mstarrunlib
        mstarrunlib.configureJava()
        import time
        time.sleep( 5 )
        ZIP_CMD = _escapeCmd(mstarpaths.interpretPath("{JAVA_HOME}/bin/jar{EXE}")) + (" -cfM %s %s" % (archive,filePattern))
        # zip the exports
        os.system(ZIP_CMD)
        if os.access(archive, os.F_OK):
            os.remove(fileJustDmp)

        # Validate the Archive:
        validZip = _validateArchive(archive, logfile)
        if not validZip and sendEmailOnError:
            msg = "ERROR: DBEXPORT Archive File %s could not be validated because it could not be opened!" % archive
            minestar.logit(msg)
            sendExportErrorsMail(msg)
        archive = tmpExportDir + os.sep + archiveShortName
        minestar.copy(archive, exportDir, True)
        # make a backup copy if requested and the directory is configured
        backupDir = mstarpaths.interpretPath("{MSTAR_DATA_BACKUPS}")
        if backupZip and backupDir is not None and backupDir != "" and backupDir != '{MSTAR_DATA_BACKUPS}':
            archive2 = backupDir + os.sep + archiveShortName
            minestar.copy(archive, archive2, True)
            mesg = i18n.translate("Archive of %s copied to %s") % (dbName, archive2)
            minestar.logit(mesg)
            logger.info(mesg)
        if exportDir <> tmpExportDir:
            if os.path.exists(archive):
               os.remove(archive)
    else:
        #if not ServerTools.onDbServer():
        if exportDir <> tmpExportDir:
            #Re-Trying to Copy the File one more times when copy fails
            delayTime = 3
            for trial in range(1,5):
                result = minestar.copy(fileName, exportDir, True)
                if result == 0:
                    logger.info("File %s copied Successfully " % fileName)
                    break
                logger.info("Failed to Copy File: %s Re-Trying...%s " % (fileName,trial))
                time.sleep( trial * delayTime )

            if os.path.exists(fileName):
                os.remove(fileName)
            #replacing the remote file path with application server path were the file is copied
            fileName = fileName.replace(tmpExportDir,exportDir)
            mesg = i18n.translate("Archive of %s copied to %s") % (dbName, fileName)
            minestar.logit(mesg)
            logger.info(mesg)
        else:
            #replacing the remote file path with application server path were the file is copied
            fileName = fileName.replace(tmpExportDir,exportDir)

    # ftp the file if requested
    # TODO: Test !!!
    if sendExport:
        import sendToSupport
        sendToSupport.ftpToSupport(archive, "no")
        mesg = i18n.translate("Database archive %s FTPed to support") % archive
        minestar.logit(mesg)
        print mesg

    # Return success and the filename created
    if doZip:
        if validExp == 0 and validZip == 0:
            mesg = i18n.translate("DBEXPORT Successfull Database archive %s created OK.") % archive
            minestar.logit(mesg)
    validAll = validExp + validZip
    return (validAll,fileName)


## Main Program ##

# exportData receives 1 to 5 parameters,
# 1) Mandatory: DataStoreName eg. _MODELDB
# 2) Optional:  ExportDir - export directory (MSTAR_DATA is used if not set)
# 3) Optional:  DoZip - true or false (default is true)
# 4) optional:  BackupZip - true or false (default is true)
# 5) Optional:  SendToSupport - true or false (default is false)

if __name__ == '__main__':
    import mstarrun
    config = mstarrun.loadSystem(sys.argv[1:])
    args = []
    if config.has_key("args"):
        args = config["args"]
    dbName = args[0]
    exportDir = None
    doZip = 1
    backupZip = 1
    sendExport = 0
    sendEmailOnError = 0
    if len(args) > 1:
        exportDir = args[1]
        if len(args) > 2:
            doZip = args[2] == "true"
            if len(args) > 3:
                backupZip = args[3] == "true"
                if len(args) > 4:
                    sendExport = args[4] == "true"
                    if len(args) > 5:
                        sendEmailOnError = args[5] == "true"
    (errorCode,filename) = exportData(dbName, exportDir, doZip, backupZip, sendExport, sendEmailOnError)
    sys.exit(errorCode)

