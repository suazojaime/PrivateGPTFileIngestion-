import minestar, i18n, mstarpaths, os, sys

logger = minestar.initApp()

PUT = "PUT"
GET = "GET"
DEL = "DEL"
DIR = "DIR"

ASCII = "ascii"
BINARY = "binary"

ASCII_ALIASES = [ "ASC", "asc", "ascii", "ASCII", ASCII ]
BINARY_ALIASES = [ "BIN", "bin", "binary", "BINARY", BINARY ]

def isFtpPutEnabled():
    return minestar.parseBoolean(mstarpaths.interpretVar("_FTP_ENABLED_PUT"), "mstarftp")

def isFtpGetEnabled():
    return minestar.parseBoolean(mstarpaths.interpretVar("_FTP_ENABLED_GET"), "mstarftp")

def makeFileName():
    # generate a name for the command file
    sleepTime = 0
    while 1:
        currentTime = minestar.getCurrentTimeConfig()
        ftpConfig = mstarpaths.interpretFormatOverride("{MSTAR_TEMP}/FTPCONFIG_{YYYY}{MM}{DD}_{HH}{NN}{SS}.txt", currentTime)
        ftpConfig = mstarpaths.interpretPath(ftpConfig)
        if filepath != ".":
            ftpConfig = mstarpaths.interpretPath(filepath + os.sep + ftpConfig)
        # watch out for another FTP command in progress
        if not os.access(ftpConfig, os.F_OK):
            break
        # file in use, wait a bit and try again
        time.sleep(15 + sleepTime)
        sleepTime = sleepTime + 1

class WriteToFileCallback:
    def __init__(self, fileName, fileType):
        self.file = open(fileName, "wb")
        self.fileName = fileName
        self.fileType = fileType
        self.count = 0

    def write(self, stuff):
        if self.fileType == ASCII:
            self.file.write(stuff + "\n")
        else:
            self.count = self.count + len(stuff)
            self.file.write(stuff)
        self.file.flush()

    def close(self):
        self.file.close()
        print "Wrote %d bytes to %s" % (self.count, self.fileName)

def get(ftp, filename, fileFullPath, fileType=BINARY):
    """
    ftp is the FTP connection object
    filename is the name we send to the FTP server
    fileFullPath is where we want to put the result
    fileType is ASCII or BINARY
    """
    command = "RETR %s" % filename
    callback = WriteToFileCallback(fileFullPath, fileType)
    if fileType == ASCII:
        ftp.retrlines(command, callback.write)
    else:
        ftp.retrbinary(command, callback.write)
    callback.close()

def put(ftp, filename, fileFullPath, fileType=BINARY):
    command = "STOR %s" % filename
    if fileType == ASCII:
        f = open(fileFullPath, "r")
        ftp.storlines(command, f)
    else:
        f = open(fileFullPath, "rb")
        ftp.storbinary(command, f)
    f.close()

def ftpOperation(action, site, user, password, filename, filepath=".", fileType=BINARY):
    mstarpaths.loadMineStarConfig()
    if fileType in ASCII_ALIASES:
        fileType = ASCII
    elif fileType in BINARY_ALIASES:
        fileType = BINARY
    else:
        minestar.fatalError("mstarftp", i18n.translate("File type '%s' is unknown") % fileType)
    if action not in [PUT, GET, DEL, DIR]:
        minestar.fatalError("mstarftp", i18n.translate("Action '%s' is unknown") % action)
    # find the full path name of the local file
    if filepath != ".":
        fileFullPath = mstarpaths.interpretPath(filepath + os.sep + filename)
    else:
        fileFullPath = filename
    # check that the file can be read or written
    if action == PUT:
        if not os.access(fileFullPath, os.F_OK):
            minestar.fatalError("mstarftp PUT", i18n.translate("File %s does not exist") % fileFullPath)
        if not os.access(fileFullPath, os.R_OK):
            minestar.fatalError("mstarftp PUT", i18n.translate("File %s is not readable") % fileFullPath)
    elif action == GET:
        if not os.access(filepath, os.F_OK):
            minestar.fileError("mstarftp GET", i18n.translate("Directory %s does not exist") % filepath)
        if not os.access(filepath, os.W_OK):
            minestar.fileError("mstarftp GET", i18n.translate("Directory %s is not writeable") % filepath)
    # do the FTP
    os.chdir(mstarpaths.interpretPath(filepath))
    import ftplib
    ftp = ftplib.FTP(site)
    ftp.login(user, password)
    # I've commented out the change directory command below as there is no incoming directory on the
    # FTP server and we don't have permissions to create one.  If it ends up being needed,  just un-commnet
    # the line below.
    # ftp.cwd("incoming")
    if action == DIR:
        minestar.logit(i18n.translate("FTP INFO: Checking %s on %s" % (filename, site)))
        ftp.dir(filename)
    elif action == DEL:
        minestar.logit(i18n.translate("FTP INFO: Removing %s from %s" % (filename, site)))
        ftp.delete(filename)
    elif action == GET:
        minestar.logit(i18n.translate("FTP INFO: Retrieving %s from %s to %s" % (filename, site, filepath)))
        get(ftp, filename, fileFullPath, fileType)
    else:
        minestar.logit(i18n.translate("FTP INFO: Putting %s on %s from %s" % (filename, site, filepath)))
        put(ftp, filename, fileFullPath, fileType)
        ftp.dir(filename)
    ftp.quit()

def ftpMaster(action, filename, filepath=".", fileType=BINARY):
    mstarpaths.loadMineStarConfig()
    ftpOperation(action, mstarpaths.interpretVar("_FTPSITE"), mstarpaths.interpretVar("_FTPUSER"),
        mstarpaths.interpretVar("_FTPPASSWORD"), filename, filepath, fileType)

def ftpCommand(action, args):
    file = args[0]
    # default path is "."
    if len(args) > 1:
        path = args[1]
    else:
        path = "."
    # used to be that any parameter meant ASCII, but now a parameter which is
    # recognisably binary will be interpreted as such
    if len(args) > 2:
        if args[2] in mstarftp.BINARY_ALIASES:
            fileType = mstarftp.BINARY
        else:
            fileType = mstarftp.ASCII
    else:
        # default is binary
        fileType = mstarftp.BINARY
    ftpMaster(action, file, path, fileType)

if __name__ == "__main__":
    args = sys.argv[1:]
    actionOK = (args[0] in [PUT, GET, DEL, DIR])
    if actionOK and len(args) == 7:
        ftpOperation(args[0], args[1], args[2], args[3], args[4], args[5], args[6])
    elif actionOK and len(args) == 5:
        ftpOperation(args[0], args[1], args[2], args[3], args[4])
    elif actionOK and len(args) == 4:
        ftpMaster(args[0], args[1], args[2], args[3])
    elif actionOK and len(args) == 2:
        ftpMaster(args[0], args[1])
    else:
        import i18n
        print i18n.translate("You're not really supposed to be running this program!")
        print i18n.translate("Usage: mstarftp action [site user password] filename [filepath filetype]")
        print i18n.translate("  [site user password] come from MineStar.properties");
        print i18n.translate("  filepath defaults to '.'")
        print i18n.translate("  filetype defaults to BINARY")
        print i18n.translate("  action may be %s %s %s %s" % (PUT, GET, DEL, DIR))
        sys.exit(115)
