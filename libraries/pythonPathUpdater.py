import os
import sys

from pathOps import removeDuplicatePaths, removePath, prependPaths


def mstarrunDebugEnabled():
    """ Determines if mstarrun debug is enabled (i.e. if MSTARRUN_DEBUG is defined in OS environment). """
    return 'MSTARRUN_DEBUG' in os.environ


def mstarrunDebug(msg):
    """ Print a message to stdout if mstarrun debug is enabled. """
    if mstarrunDebugEnabled():
        print "debug: %s" % msg


class PythonPathUpdater(object):

    """
    Class for updating the python path.
    
    The python path is updated so that the M* python libs in ${MSTAR_HOME} are
    on the path before the M* python libs ${MSTAR_INSTALL}/mstarHome, in the 
    case that ${MSTAR_HOME} is not the same as ${MSTAR_INSTALL}/mstarHome. This
    may occur when a zip upgrade is installed, for example.
    
    The python path is also updated to include any site packages that are found
    in ${MSTAR_HOME}/bus/pythonlib/lib (installing the packages if required).
    
    If running from a source repository, the site packages are installed from 
    the ${RUNTIME}/mstar/bus/pythonlib/lib directory.
    """

    def __init__(self, mstarHome=None, mstarInstall=None):
        """
         Create a PythonPathUpdater instance. 
         
         :param mstarHome: the location of the M* home, this will initially
         be e.g. "/mstar/mstarHome" but may be e.g. "/mstar/mstar5.0.1" as 
         new upgrades are installed.
         
         :param mstarInstall: the location of the M* install, e.g. "/mstar".
         If not specified it defaults to the parent directory of 'mstarHome'. 
         """

        # Verify that at least one of 'mstarHome' and 'mstarInstall' is specified.
        if mstarHome is None and mstarInstall is None:
            raise ValueError("Must specify at least one of 'mstarHome' and 'mstarInstall' parameters")

        # If mstarInstall is not specified, assume it is '${mstarHome}/..'
        if mstarInstall is None:
            mstarInstall = os.path.abspath(os.path.dirname(mstarHome))
        self.mstarInstall = mstarInstall
        
        # If mstarHome is not specified, assume it is '${mstarInstall}/mstarHome'.
        if mstarHome is None:
            mstarHome = os.path.abspath(os.path.join(mstarInstall, 'mstarHome'))
        self.mstarHome = mstarHome

    def updatePath(self):
        sys.path = self._getSysPath()
        if mstarrunDebugEnabled():
            mstarrunDebug("updatePath: sys.path is now:")
            for path in sys.path:
                mstarrunDebug("updatePath:     %s" % path)
        if not self._isLinux():
            os.environ["PYTHONPATH"] = os.pathsep.join(sys.path)

    def _isLinux(self):
        import sys
        return sys.platform.startswith('linux')

    def _getSysPath(self):
        # Remove '/mstar/mstarHome' (it may be put back, or replaced with e.g. '/mstar/mstar5.1').
        sysPaths = removePath(paths=sys.path, path=os.path.join(self.mstarInstall, 'mstarHome'), recursive=True)
        # Prepend the M* python paths.
        sysPaths = prependPaths(existingPaths=sysPaths, newPaths=self._getPythonLibs())
        return removeDuplicatePaths(sysPaths)

    def _getPythonLibs(self):
        # - {MSTAR_HOME}/bus/pythonlib
        # - {MSTAR_HOME}/bus/pythonlib/lib/**
        # - {RUNTIME}/mstar/bus/pythonLib/lib (if running from repository)
        pythonLibs = []

        # Add {MSTAR_HOME}/bus/pythonlib/**
        mstarHomePythonLib = os.path.join(self.mstarHome, "bus", "pythonlib")
        if os.path.exists(mstarHomePythonLib):
            pythonLibs.append(mstarHomePythonLib)
            pythonLibs.extend(_getPythonLibsFrom(os.path.join(mstarHomePythonLib, 'lib')))

        # If running from the source repository, add: runtime/target/mstar/bus/pythonlib/lib/**
        from sourceRepository import SourceRepository
        sourceRepository = SourceRepository.getInstance(mstarHome=self.mstarHome)
        if sourceRepository.running:
            repositoryPythonLib = os.path.join(sourceRepository.runtimeDir, "mstar", "bus", "pythonlib")
            pythonLibs.extend(_getPythonLibsFrom(os.path.join(repositoryPythonLib, "lib")))

        # Remove duplicate python lib paths (keeping same order).
        pythonLibs = removeDuplicatePaths(pythonLibs)

        # Log python libs if debug is enabled.
        if mstarrunDebugEnabled():
            mstarrunDebug("pythonLibs:")
            for pythonLib in pythonLibs:
                mstarrunDebug("  %s" % pythonLib)

        return pythonLibs


def _getPythonLibsFrom(dir):
    pythonLibs = []

    # Check that the lib directory exists.
    if os.path.exists(dir):
        # Add the python lib directory.
        pythonLibs.append(dir)

        # Install any python packages in the directory.
        from pythonPackageManager import PythonPackageManager
        packageManager = PythonPackageManager(dir)
        packageManager.installPackages()

    return pythonLibs
