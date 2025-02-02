import mstarpaths, i18n, sys, os, string, mstarftp, minestar, mstaremail, ftplib, time

logger = minestar.initApp()

UPLOADING   = ".uploading"
FILE_LOCKED = ".ftpLocked"

class ftpDirCommandCallback:
    '''
    Output from certain calls to the "dir" command on the FTP server come through here. We need to trap this
    info because various methods within this script require it.  Amongst other things,  we need to use the file
    size on the FTP server to perform certain validation on files to be sent.  Whatever you do,  don't
    rely on the "size" command contained in Python's FTP library. It CANNOT be relied on at all.  It returns
    different sizes at whim.  It is a piece of crap.  Also,  we need to trap the output so that we can build
    a list of files to download from the FTP dir command.
    '''

    def __init__(self, custDir):
        self.custDir = custDir
        self.dirListing = []

    def buildDirListing(self, line):
        colList = line.split()
        #if colList size == 9. Then the FTP server has Linux Directory list Style. if colList size == 4 then the FTP server has windows Directory list Style
        if len(colList) == 9:
            #  If doing a dir on a directory,  discard the line beginning with "total",  as it contains no
            #  file information. Also discard subdirectories as we only take files from the top level directory.
            if (colList[0] == "total") or (colList[0][0] == "d"):
               return
            self.dirListing.append(colList[8])
        else:
            self.dirListing.append(colList[3])

    def getDirListing(self):
        return self.dirListing

    def storeFileSizeOnServer(self, line):
        '''
        Store the size of the file on the server so that we can access it later.  BTW, I purposely didn't
        use the "size" method contained in Python's FTP library in the code below. The size function as it exists
        now CANNOT be relied on at all.  It returns different file sizes at whim.  It is vicious,  capricious and
        malicious.
        '''
        # Get the file size on the FTP server.
        colList = line.split()
        #if the colList length == 9, then we treat it as Linux Directory Listing.else Windows.
        if len(colList) == 9:
            sizeOnServer = colList[4]
        else:
            sizeOnServer = colList[2]
        # Convert the size to a long.
        sizeOnServer = long(sizeOnServer)
        self.sizeOnServer = sizeOnServer

    def getFileSize(self):
        return self.sizeOnServer


def __writeToFTPLog(path, fileName, message=""):
    ftpFilename = mstarpaths.interpretPath("{MSTAR_LOGS}/FTP.log")
    file = open(ftpFilename, "a")
    if path != "":
       file.write("%s" % path)
    if fileName != "":
       file.write(" %s" % fileName)
    if message != "":
       file.write(" %s"% message)
    file.write("\n")
    file.close()


def __emailAboutFTP(recipient, subject, message):
    try:
        if mstaremail.isExternalEmailEnabled():
            mstaremail.quickEmail(recipient, subject, message)
    except:
        import traceback
        msg = "EMAIL ERROR: Cannot send ftp email\n%s" % traceback.format_exc(sys.exc_info()[0])
        logger.error(msg)
        minestar.logit(msg)

def ftpToSupport(fileToSend, moveFileAfterSending, filetype=mstarftp.BINARY, ftpConnection=None):
    #
    # FTP the supplied file to MineStar Support.
    #
    thisMachine = mstarpaths.interpretVar("COMPUTERNAME")
    mstarpaths.loadMineStarConfig()
    ftpMachine = mstarpaths.interpretVar("_FTPSERVER")
    (path, fileName) = os.path.split(fileToSend)
    if path == "":
       path = "."
    if ftpMachine.upper() != thisMachine.upper():
        minestar.fatalError("sendToSupport", i18n.translate("Can only perform FTP operations on the FTP server itself"))
    else:
        custDir = mstarpaths.interpretVar("_CUSTCODE")
        if ftpConnection == None:
           ftpConnection = __login()

        if not __finalChecksPassOK(ftpConnection, fileName, ftpMachine, fileToSend, custDir):
           minestar.move(fileToSend, mstarpaths.interpretPath("{MSTAR_SENT}") + os.sep + fileName, True)
           return

        try:
            # Rename uploading files to have a ".uploading" extension so that the scripts that download files
            # don't download them halfway through their upload.
            minestar.move(fileToSend, fileToSend + UPLOADING, True)
            mstarftp.ftpMaster(mstarftp.PUT, fileName + UPLOADING, path, filetype)

            # After a big file has been sent,  our FTP connection may have timed out. There's currently no easy
            # way to test whether this is the case,  so just get another connection anyway.
            ftpConnection = __login()

            # Now that the file has uploaded,  rename it back to its original file name,  both locally and
            # on the FTP server.
            ftpConnection.rename(fileName + UPLOADING, fileName)
            minestar.move(fileToSend + UPLOADING, fileToSend, True)
            __moveFileAfterSend(fileToSend, moveFileAfterSending)
            __writeToFTPLog(path, fileName, filetype)

            recipient = mstarpaths.interpretVar("_EMAILRECIPIENT")
            subject = i18n.translate("%s has been FTPed from MineStar at %s") % (fileName, mstarpaths.interpretVar("_CUSTCODE"))
            message = i18n.translate("For your information...")
            __emailAboutFTP(recipient, subject, message)
        except:
            import traceback
            traceback.print_exc()
            minestar.fatalError("sendToSupport", i18n.translate("Cannot establish connection on the FTP server - Transfer failed!"))


def __login():
    ftpConnection = ftplib.FTP(mstarpaths.interpretVar("_FTPSITE"))
    ftpUser = mstarpaths.interpretVar("_FTPUSER")
    ftpPassword = mstarpaths.interpretVar("_FTPPASSWORD")
    ftpConnection.login(ftpUser, ftpPassword)
    return ftpConnection

def __finalChecksPassOK(ftpConnection, fileNameOnServer, ftpServer, localFileName, custDir):
    '''
    Do any final checks that need to be done on the file before we send it. Current checks are:

    1. Check to see whether the file exists on the server before we send it.  Do this because someone may
    have already manually FTP'ed the file.  Note that it's not good enough to just look for the filename
    of the file that we want to send,  we also need to look for variations of the name in case it is currently
    being uploaded or downloaded from the server.

    2. Enter any new checks added here.
    '''
    #  First,  get a directory listing from the server.
    dirListing = []
    callback = ftpDirCommandCallback(custDir)
    ftpConnection.dir(callback.buildDirListing)
    dirListing = callback.getDirListing()
    recipient = mstarpaths.interpretVar("_EMAILRECIPIENT")
    subject = i18n.translate("%s has already been FTPed to MineStar - it is not being sent again.") % (fileNameOnServer)
    message = i18n.translate("File is from customer %s" % custDir)
    if fileNameOnServer in dirListing:
       if __fileSizeOnServer(ftpConnection, custDir, fileNameOnServer) == __checkLocalFileSize(localFileName):
          __emailAboutFTP(recipient, subject, message)
          return False
    if (fileNameOnServer + FILE_LOCKED) in dirListing:
       if __fileSizeOnServer(ftpConnection, custDir, (fileNameOnServer + FILE_LOCKED)) == __checkLocalFileSize(localFileName + FILE_LOCKED):
          __emailAboutFTP(recipient, subject, message)
          return False
    if (fileNameOnServer + UPLOADING) in dirListing:
       # todo - need to check last access on the ftp server.
       if __fileSizeOnServer(ftpConnection, custDir, (fileNameOnServer + UPLOADING)) == __checkLocalFileSize(localFileName + UPLOADING):
          __emailAboutFTP(recipient, subject, message)
          return False
    return True


def __fileSizeOnServer(ftpConnection, custDir, fileName):
    '''
    Check the file size on the server.  Whatever you do,  don't rely on the "size" method contained in Python's
    FTP library. It CANNOT be relied on at all.  It returns different sizes at whim.  It is a piece of crap.
    '''
    callback = ftpDirCommandCallback(custDir)
    # The callback from the 'dir' command will store the file's size for validation purposes later.
    ftpConnection.dir(fileName, callback.storeFileSizeOnServer)
    return callback.getFileSize()


def __checkLocalFileSize(fileName):
    "Check the size of the downloaded file on the local system."
    try:
        stats = os.stat(fileName)
        localSize = stats[6]
        # Convert the size to a long.
        localSize = long(localSize)
        return localSize
    except:
        return 0


def messageToSupport(fileToSend, recipient="support", subject=None):
    (path, fileName) = os.path.split(fileToSend)
    if subject is None:
        subject = mstarpaths.interpretFormat("{_CUSTCODE} MineStar file %s") % fileName
    if mstaremail.isExternalEmailEnabled():
        mstaremail.email(recipient, subject, fileToSend)


def attachToSupport(fileToSend, recipient="support", subject=None, messageFile=None):
    (path, fileName) = os.path.split(fileToSend)
    if subject is None:
        subject = mstarpaths.interpretFormat("{_CUSTCODE} MineStar file %s attached") % fileName
    if mstaremail.isExternalEmailEnabled():
        mstaremail.email(recipient, subject, messageFile, [fileToSend])


def __moveFileAfterSend(file, moveFileAfterSending):
    #  Move files to the system's "sent" directory after they have been FTP'ed to MineStar Support.
    if moveFileAfterSending == "yes":
        # get the path of the sent directory to move files to after they have been sent.
        (path, sendBasename) = os.path.split(file)
        sentFile = mstarpaths.interpretPath("{MSTAR_SENT}/%s" % sendBasename)
        # move the file
        minestar.makeDirsFor(sentFile)
        minestar.move(file, sentFile, True)


def __moveFileToInProgressDir(file):
    #  Before FTPing the contents of the system's "outgoing" directory,  move the file to an "in-progress"
    #  subdirectory so that multiple FTP jobs don't try to send the same file twice.

    #  Split the file into its path and its file name.
    (path, sendBasename) = os.path.split(file)
    #  Create a path to the in-progress directory
    inProgressDir = mstarpaths.interpretPath("%s/in-progress" % path)
    #  Construct the path of the destination file.
    destFile = mstarpaths.interpretPath("%s/%s" % (inProgressDir, sendBasename))
    #  Move the file
    minestar.makeDirsFor(destFile)
    minestar.move(file, destFile, True)
    return destFile


def checkBeforeSend(args):
    '''
    Params : args are method, file name, optional file type
    Perform the following checks before starting the sendToSupport process.
      1. Check the command line arguments for problems before allowing methods using these arguments to proceed.
      2. Check that a sendToSupport process is not already running. Do this because we don't want multiple send
         jobs running simultaneously and killing the FTP connection.
    '''
    method = args[0]
    #  Check that the method of sending makes sense.
    if method not in ["FTP", "MSG", "ATT"]:
       minestar.fatalError("sendToSupport", i18n.translate("Invalid send method specified. Send method is %s") % method)
       print i18n.translate("Invalid send method '%s'") % method
       sys.exit(10)
    #  Check that the method of sending is permitted.
    if method == "FTP" and not mstarftp.isFtpPutEnabled():
       minestar.fatalError("sendToSupport", i18n.translate("Send method is FTP and FTP put is not enabled"))
    if method in ["MSG", "ATT"] and not mstaremail.isExternalEmailEnabled():
       minestar.fatalError("sendToSupport", i18n.translate("Send method is %s and external email is not enabled") % method)
    checkPartiallySentFiles()


def checkPartiallySentFiles():
    '''
    This method checks the partially-sent files in the in-progress directory for the following things :

    1. Check the outgoing/in-progress directory for files that have been left there indefinitely when their
       transfer fails.  As an arbritrary check,  we will assume that any file that is still in the in-progress
       directory that has a timestamp greater than 12 hours from the current time has encountered a problem.
       Failed uploads will be logged and moved back to the outgoing directory to be picked up in the next upload
       run.  An email telling someone that this has occurred will also be sent.
    2. Check to see whether any of the files in the in-progress directory have been accessed within the last 2
       minutes.  If any have been accessed within the last 2 minutes,  we will assume that there is another FTP
       job running and abort this run.
    '''
    #  Get a directory listing of the "in-progress" directory.
    progressDir = mstarpaths.interpretPath("{MSTAR_OUTGOING}/in-progress")
    #  Check that an in-progress directory exists.  If it doesn't,  these checks are irrelevant.
    if not os.access(progressDir, os.F_OK):
       print "ASASSSASASSSA"
       return
    filesToCheck = os.listdir(progressDir)
    #  Abort the run if we find that there is another FTP job running.
    abortRun = False
    #  Iterate through the directory listing,  checking the files as you go.
    for file in filesToCheck:
        absFilePath = os.sep.join([progressDir, file])
        #  Get the time that the file was last accessed.
        intAccessTime = os.stat(absFilePath).st_atime
        #  Add 12 hours to the time of last access. Don't use create or mod time for this check;  if you use these
        #  values it means that if the _original_ file was created more than 12 hours ago the next run will pick
        #  it up as a failure regardless of what stage of being sent it is at.
        checkTime = intAccessTime + 43200
        if checkTime < time.time():
           #  The file was accessed more than 12 hours ago,  assume that a problem has occurred while sending it.
           __processFailedUpload(absFilePath, file)
        checkRunTime = intAccessTime + 300
        if checkRunTime > time.time():
           #  This file has been accessed within the last 2 minutes,  so just to be safe,  let's assume that
           #  another FTP job is running.
           abortRun = True
    #  If we need to abort,  wait until we've finished processing all the partially-sent files.
    if abortRun:
       __abortSendRun()


def __processFailedUpload(absFilePath, file):
    '''
    The supplied file has failed in its upload;  move it back to the "outgoing" directory.
    '''
    (path, fileName) = os.path.split(file)
    finalFileName = __moveFileBackToOutgoingDir(absFilePath, fileName)
    message = i18n.translate("was previously sent, but the send operation failed! It has been moved to the outgoing directory to be re-sent.")
    __writeToFTPLog(path, finalFileName, message)
    recipient = mstarpaths.interpretVar("_EMAILRECIPIENT")
    subject = i18n.translate("Problem was detected with FTP of file -  %s") % (finalFileName)
    message = i18n.translate("The file has been moved back to the outgoing directory to be re-sent!")
    __emailAboutFTP(recipient, subject, message)


def __abortSendRun():
    recipient = mstarpaths.interpretVar("_EMAILRECIPIENT")
    subject = i18n.translate("Another sendToSupport process is already FTPing files to MineStar!")
    message = i18n.translate(" You must wait until it finishes!")
    #minestar.fatalError("sendToSupport", i18n.translate("Another sendToSupport process is already FTPing files to MineStar. You must wait until it finishes."))
    __emailAboutFTP(recipient, subject, message)
    __writeToFTPLog("", "", subject + message)
    print("%s  %s" % (subject, message))
    sys.exit(10)


def sendToSupport(args, moveFileAfterSending, file):
    '''
    Args are method, file name, optional file type

    This method sends the supplied file from a MineStar system's "outgoing" directory to MineStar support,  using
    either FTP,  MSG,  or ATT,  then move the file to the "sent" director.
    '''
    checkBeforeSend(args)
    method = args[0]
    # If a file to send has been supplied with the command line arguments,  send it.  But if a file has not been
    # supplied from the command line,  assume that one has been supplied with this method call (aka the "file" param).
    if len(args) > 1:
        fileToSend = mstarpaths.interpretPath(args[1])
    else:
        fileToSend = file
    # check that the file exists
    if not os.access(fileToSend, os.F_OK):
        # File doesn't exist,  which means that another FTP job has probably already sent and moved it.
        print i18n.translate("File '%s' doesn't exist - possibly already sent and moved by another FTP job") % fileToSend
        return
    print i18n.translate("Sending file - " + fileToSend)
    movedFileToSend = __moveFileToInProgressDir(fileToSend)
    if method == "FTP":
        ftpConnection = __login()
        if len(args) > 2:
           ftpToSupport(movedFileToSend, moveFileAfterSending, args[2], ftpConnection)
        else:
           ftpToSupport(movedFileToSend, moveFileAfterSending, mstarftp.BINARY, ftpConnection)
    elif method == "MSG":
        if len(args) > 2:
            messageToSupport(movedFileToSend, args[2])
        else:
            messageToSupport(movedFileToSend)
        __moveFileAfterSend(movedFileToSend, moveFileAfterSending)
    else:
        if len(args) > 2:
            attachToSupport(movedFileToSend, recipient)
        else:
            attachToSupport(movedFileToSend)
        __moveFileAfterSend(movedFileToSend, moveFileAfterSending)


def sendAllToSupport(args):
    '''
    The purpose of this method is to send all files from the outgoing directory under \mstar\systems\<system_name>\
    using either FTP, MSG,  or ATT.  Once sent,  they are moved from the outgoing directory to the sent directory.
    '''
    checkBeforeSend(args)
    # get a directory listing of the outgoing directory.
    outgoingDir = mstarpaths.interpretPath("{MSTAR_OUTGOING}")
    # get a listing of the directory.
    filesToSend = os.listdir(outgoingDir)
    # iterate through the files to send,  sending them as you go.
    for file in filesToSend:
        #  Get the absolute path of the file so that we can test to see whether it is a directory.
        absFilePath = os.sep.join([outgoingDir, file])
        #  We only want to send files,  not directories
        if not minestar.isDirectory(absFilePath):
           sendToSupport(args, "yes", outgoingDir + os.sep + file)


def __moveFileBackToOutgoingDir(file, fileName):
    #  Construct the path of the destination file.
    destFile = os.sep.join([mstarpaths.interpretPath("{MSTAR_OUTGOING}"), fileName])
    #  Check that the Outgoing directory exists.
    minestar.makeDirsFor(destFile)
    #  If the file has had a file extension of ".uploading" added,  strip it off, before we move it.
    minestar.move(file, destFile.replace(UPLOADING, "", 2), True)
    return destFile


if __name__ == '__main__':
    import mstarrun
    args = mstarrun.loadSystem(sys.argv[1:])["args"]
    #  can now call in a way that sends all the files in the outgoing directory.  Still support the old way of
    #  calling sendToSupport however.
    if len(args) > 1:
        sendToSupport(args, "yes", args[1])
    else:
        sendAllToSupport(args)
