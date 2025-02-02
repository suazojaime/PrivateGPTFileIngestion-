# A program to execute MineStar executables.
# Responsibilities are:
# 1. Running assorted types of files
# 2. Loading all necessary environment variables and building command lines
# 3. Interpreting a registry of applications
import os, sys, dircache

DEV_CLASSPATH = ["{DEVELOPMENT}/classes", "{DEVELOPMENT}/res"]
MINESTAR_INI = "MineStar.ini"


# TODO copied from mstarrpaths.mstarrunDebug() -- should move to a common function.

def mstarrunDebugEnabled():
    """ Determines if mstarrun debug is enabled (i.e. if MSTARRUN_DEBUG is defined in OS environment). """
    return 'MSTARRUN_DEBUG' in os.environ

def mstarrunDebug(msg):
    """ Print a message to stdout if mstarrun debug is enabled. """
    if mstarrunDebugEnabled():
        print "debug: %s" % msg

def _getSystemForIniLookup():
    """ Get the System for looking up the build from the MineStar.ini file. Return None for the default
        system. Assume that -s is always the first arg if not already determined. """
    if "MSTAR_SYSTEM" in os.environ:
        return os.environ["MSTAR_SYSTEM"]
    elif len(sys.argv) > 2 and sys.argv[1] == '-s':
        return sys.argv[2]
    else:
        return None

def getLocalBuild(buildFile, systemName=None):
    """ Read the local build setting from buildFile. If systemName is None, the system is taken from the environment
        or command line. Returns None if not found. """
    # Get default system name if not specified.
    if systemName is None:
        systemName = _getSystemForIniLookup()
    # Load the minestar config.    
    from install.minestarIni import MineStarIni
    config = MineStarIni.load(buildFile)
    try:
        # Get build for system name, with fallback to 'main' if required.
        build = config.getBuild(systemName)
        if build is None and systemName != 'main':
            build = config.getBuild('main')
        return build    
    except Exception:
        return None

def setLocalBuild(buildFile, buildName, systemName=None):
    """ Set the local build for a system. The system name defaults to 'main', the build name defaults to 'Home'. """
    from install.minestarIni import MineStarIni
    config = MineStarIni.loadOrCreate(path=buildFile)
    config.setBuild(systemName=systemName or 'main', buildName=buildName or 'Home')
    config.store(buildFile)    
    
def mstarrunSubprocess():
    # are we a subprocess of another mstarrun command? If so, we can trust the environment variables
    return os.environ.get("MSTAR_HOME") and os.environ.get("MSTAR_BIN") and os.environ.get("MSTAR_SYSTEMS")

# we completely ignore the MSTAR_HOME environment setting, and
# figure out where MSTAR_HOME is from where the Python code is.
# If you use the batch file / shell script, it will be the same
# anyway, but sometimes we want to use mstarrun as a Python program,
# and then we cannot afford to pick up wrong environment settings.
mstarHome = None
fields = sys.argv[0].split(os.sep)
for i in range(len(fields)):
    if fields[i] == "systems":
        break
    if fields[i] == "bus":
        mstarHome = os.sep.join(fields[:i])
        break
if not mstarHome and len(fields) == 1:
    fields = os.path.abspath(fields[0]).split(os.sep)
    for i in range(len(fields)):
        if fields[i] == "bus":
            mstarHome = os.sep.join(fields[:i])
            break
if not mstarHome:
    if mstarrunSubprocess():
        mstarHome = os.environ["MSTAR_HOME"]
    else:
        # couldn't find bus directory, this is dodgy
        mstarHome = os.sep.join(fields[:-3])
mstarHome = os.path.abspath(mstarHome)
if mstarHome[-1] == os.sep:
    mstarHome = mstarHome[:-1]

# If a MineStar.ini file exists in the parent directory (e.g. at ${mstarHome}/../MineStar.ini), then
# it contains the actual build to run and we set MSTAR_INSTALL to the parent. Otherwise, we set
# MSTAR_INSTALL to MSTAR_HOME.
#
# MSTAR_INSTALL is used for finding the LICENSE.key file and 3rd party stuff like Java & Python.
#
# Note: must use absolute paths to ensure that symbolic links are fully resolved.

mstarBuildFile = os.path.abspath(os.path.join(mstarHome, os.pardir, MINESTAR_INI))
if os.path.exists(mstarBuildFile):
    mstarInstall = os.path.abspath(os.path.dirname(mstarBuildFile))
    mstarBuild = getLocalBuild(mstarBuildFile)
    if mstarBuild is None:
        print "WARNING: Using original build as %s file found with no build setting inside it" % MINESTAR_INI
    else:
        mstarBuildDir =  os.path.abspath(os.path.join(mstarInstall, "mstar" + mstarBuild))
        if os.path.exists(mstarBuildDir):
            mstarHome = mstarBuildDir
        else:
            print "WARNING: Using original build as %s file found but build setting (%s) refers to a non-existent directory (%s)"  % (MINESTAR_INI,mstarBuild,mstarBuildDir)
else:
    mstarInstall = mstarHome
    mstarBuild = "As Installed"

if __name__ == '__main__':
    os.environ["MSTAR_HOME"] = mstarHome
    os.environ["MSTAR_INSTALL"] = mstarInstall
    os.environ["MSTAR_BUILD"] = mstarBuild


def updatePythonPath():
    global mstarHome, mstarInstall
    from pythonPathUpdater import PythonPathUpdater
    PythonPathUpdater(mstarInstall=mstarInstall, mstarHome=mstarHome).updatePath()

# Need to update python path *before* calling mstarrunlib, to ensure
# that the configured M* python code is called, e.g. if the build is
# 5.1 then the /mstar/mstar5.1/bus/pythonlib/mstarrunlib.py script is
# loaded, not the /mstar/mstarHome/bus/pythonlib/mstarrunlib.py script.
updatePythonPath()

# Do not delete this line; imports injected are used by callers.
from mstarrunlib import *

def run(cmdline, overrides = {}, checkSystemExists=1):
    import mstarrunlib
    mstarrunlib.run(cmdline, overrides, checkSystemExists)

if __name__ == '__main__':
    run(sys.argv[1:])
