import minestar, os, mstardebug, i18n, adminPrefixIfOld, mstarpaths, sys

logger = minestar.initApp()

TIVOLI_DIR = """c:\Program Files\Tivoli\tsm\baclient"""

def backupToTape(fileName=None):
    """
    Backup the named file to tape.
    Returns errorCode
    """
    valid = 0

    # do the export and record what we did
    mesg = i18n.translate("Copying file %s to backup tape.") % (fileName)
    minestar.logit(mesg)

    dateStamp = mstarpaths.interpretFormat("{YYYY}{MM}{DD}")

    logFile = mstarpaths.interpretPath("{MSTAR_LOGS}/BackupToTape_%s.log" % dateStamp)
    os.chdir("C:/Program Files/Tivoli/tsm/baclient")
    tapeCmd = "dsmc.exe incr %s >> %s" % (fileName, logFile)
    os.system(tapeCmd)
    # TODO: Test !!!
    testCmd = "dsmc.exe q backup %s >> %s" % (fileName, logFile)
    os.system(testCmd)

    return valid


## Main Program ##

# backupToTape receives 1 to 5 parameters,
# 1) Mandatory: fileName eg. _MODELDB_TCM_20051014_0145.zip

if __name__ == '__main__':
    import mstarrun
    config = mstarrun.loadSystem(sys.argv[1:])
    args = []
    if config.has_key("args"):
        args = config["args"]
    fileName = args[0]
    errorCode = backupToTape(fileName)
    sys.exit(errorCode)

