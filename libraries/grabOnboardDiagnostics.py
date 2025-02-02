import mstarpaths, sys, minestar, os, ftplib, i18n, mstarftp, zipfile

logger = minestar.initApp()

COMPRESSED = 0

def _handleError(step, args):
    code = int(args.split()[0])
    if step.startswith("cwd ") and code == 550:
        mesg = i18n.translate("Directory '%s' does not exist") % step[4:]
    elif step.startswith("get ") and code == 550:
        mesg = i18n.translate("File '%s' does not exist") % step[4:]
    elif code == 502:
        mesg = i18n.translate("Command for step '%s' is not implemented") % step
    else:
        mesg = i18n.translate("Error %d in step '%s'") % (code, step)
    minestar.fatalError("grabOnboardDiagnostics", mesg)
    
class DirEntry:
    def __init__(self, size, time, date, filename):
        self.size = size
        self.time = time
        self.date = date
        self.filename = filename

class DirCallback:
    def __init__(self, machineName):
        self.lines = []
        self.machineName = machineName
        self.entries = None

    def line(self, s):
        self.lines = self.lines + [s]

    def getEntries(self):
        if self.entries is None:
            self.entries = []
            for line in self.lines[:-3]:
                fields = line.strip().split()
                if len(fields) != 4:
                    minestar.logit("Unexpected entry on machine %s FTP server: %s" % (self.machineName, line))
                else:
                    self.entries.append(DirEntry(int(fields[0]), fields[1], fields[2], fields[3]))
        return self.entries

def compressedGet(ftp, filename, fileFullPath):
    """
    ftp is the FTP connection object
    filename is the name we send to the FTP server
    fileFullPath is where we want to put the result
    """
    if COMPRESSED:
        command = "RETR -deflate %s" % filename
    else:
        command = "RETR %s" % filename
    callback = mstarftp.WriteToFileCallback(fileFullPath, mstarftp.BINARY)
    ftp.retrbinary(command, callback.write)
    callback.close()
    
def _decompress(fileName):
    import zlib
    (fdir, zFileName) = os.path.split(fileName)
    newFileName = zFileName[8:]
    newFileName = fdir + os.sep + newFileName
    # read from compressed file
    zFile = open(fileName, "rb")
    zContents = zFile.read()
    zFile.close()
    # uncompress
    z = zlib.decompressobj(15)
    uContents = z.decompress(zContents)
    #print len(zContents), "->", len(uContents)
    # write to uncompressed file
    uFile = open(newFileName, "wb")
    uFile.write(uContents)
    uFile.flush()
    uFile.close()

def doFtp(machineIP, machineName, destDir):
    os.chdir(destDir)
    compressedFiles = []
    try:
        step = "connect"
        ftp = ftplib.FTP(machineIP)
        step = "login"
        ftp.login()
        step = "cwd Storage Card"
        ftp.cwd("Storage Card")
        step = "cwd DIAG"
        ftp.cwd("DIAG")
        step = "dir"
        dirCallback = DirCallback(machineName)
        ftp.dir(dirCallback.line)
        for entry in dirCallback.getEntries():
            if entry.size == 0:
                continue
            step = "get " + entry.filename
            print step
            if COMPRESSED:
                fileName = destDir + os.sep + "deflate_" + entry.filename
            else:
                fileName = destDir + os.sep + entry.filename
            compressedGet(ftp, entry.filename, fileName)
            compressedFiles.append(fileName)
        step = "quit"
        ftp.quit()
    except ftplib.error_perm:
        _handleError(step, sys.exc_info()[1].args[0])
    if COMPRESSED:
        # decompress compressed files
        for fileName in compressedFiles:
            _decompress(fileName)

def grabOnboardDiagnostics(args):
    equipmentName = args[0]
    equipmentIP = args[1]
    destRootDir = None
    if len(args) > 2:
        destRootDir = mstarpaths.interpretPath(args[2])
    diagnosticsDir = mstarpaths.interpretPath("{ONBOARD_DIAGNOSTICS}")
    minestar.createExpectedDirectory(diagnosticsDir)
    if destRootDir is None:
        destRootDir = diagnosticsDir
    else:
        minestar.createExpectedDirectory(destRootDir)
    machineDir = mstarpaths.interpretPath("%s/%s_%s" % (destRootDir, equipmentName, equipmentIP))
    minestar.createExpectedDirectory(machineDir)    
    doFtp(equipmentIP, equipmentName, machineDir)

if __name__ == '__main__':
    import mstarrun
    args = mstarrun.loadSystem(sys.argv[1:])["args"]
    grabOnboardDiagnostics(args)
