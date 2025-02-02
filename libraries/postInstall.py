__version__ = "$Revision: 1.59 $"

# after installation, fix things

import os, sys
import minestar, mstarpaths, mstarrun, cleanTempDir, systemReport

logger = minestar.initApp()

def fixBinExecutables():
    # make all of the executables executable
    binDir = mstarpaths.interpretPath("{MSTAR_BIN}")
    for filename in os.listdir(binDir):
        file = binDir + os.sep + filename
        if not os.access(file, os.X_OK):
            os.chmod(file, 0x550)

def copyReportingLogo():
    sourceFile = mstarpaths.interpretPath("{MSTAR_HOME}/ext/ReportingUtilities/reports/logo.bmp")
    targetFile = "c:\logo.bmp"
    if not os.path.exists(targetFile) and os.path.exists(sourceFile):
        minestar.copy(sourceFile, targetFile)

def createVimsUnprocessed():
    vimsUnprocessed = mstarpaths.interpretPath("{MSTAR_DATA}/VIMSFiles/unprocessed")
    if minestar.isDirectory(vimsUnprocessed):
        print "\n%s already exists" % vimsUnprocessed
    else:
        print "\nCreating %s ..." % vimsUnprocessed
        minestar.createExpectedDirectory(vimsUnprocessed)

from optparse import make_option

def main(appConfig=None):

    # Process options and check usage
    argumentsStr = ""
    (options,args) = minestar.parseCommandLine(appConfig, __version__, None, argumentsStr)

    mstarpaths.loadMineStarConfig()
    if sys.platform.startswith("linux"):
        # known fixes for Linux
        fixBinExecutables()

    # Clean out the MSTAR_TEMP directory
    cleanTempDir.cleanTempDir()

    # Upgrade/init the system area
    mstarrun.run("makeSystem -u main", checkSystemExists=0)

    try:
        if sys.platform.startswith("win"):
            # known fixes for Windows
            copyReportingLogo()
            createVimsUnprocessed()
    except:
        minestar.fatalError(None, i18n.translate("Cannot create VIMS directory.") % path)

# If this program exits successfully, we explicitly put out a special, non-zero exit code (10).
# The mstarPostInstall wrapper script looks for this value and notifies the install program
# (via a temporary file) whether this step worked or failed.
main()
sys.exit(10)
