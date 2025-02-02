import os
import sys
import i18n

from pathOps import dotExe, which


class PythonConfigError(RuntimeError):

    """ Class representing python configuration errors. """

    def __init__(self, msg):
        msg = i18n.translate("Python configuration error: ") + msg
        super(PythonConfigError, self).__init__(msg)


def isLinux():
    return sys.platform.startswith('linux')


class PythonInstall(object):

    """ Class for obtaining information about a python installation. """
    
    def __init__(self, home=None, homeSource=None):
        # If a python home directory is not specified, find python on the path.
        if home is None:
            (self._home, self._homeSource) = self._lookupHomeAndHomeSource()
        else:    
            (self._home, self._homeSource) = (home, homeSource or '(unspecified)')
        self._pythonBinary = None
        self._pythonwBinary = None

    @property
    def home(self):
        return self._home

    @property
    def homeSource(self):
        return self._homeSource

    @property
    def pythonBinary(self):
        if self._pythonBinary is None:
            self._pythonBinary = self._lookupPythonBinary()
        return self._pythonBinary

    @property
    def pythonwBinary(self):
        if self._pythonwBinary is None:
            self._pythonwBinary = self._lookupPythonwBinary()
        return self._pythonwBinary
    
    def _lookupPythonBinary(self):
        python = os.path.join(self.home, 'python%s' % dotExe())
        if not os.access(python, os.F_OK):
            raise PythonConfigError(i18n.translate("'%s' not found") % python)
        if not os.access(python, os.X_OK):
            raise PythonConfigError(i18n.translate("'%s' not executable") % python)
        return python

    def _lookupPythonwBinary(self):
        pythonwExe = 'pythonw%s' % dotExe()
        pythonw = os.path.join(self.home, pythonwExe)
        if not os.access(pythonw, os.X_OK):
            pythonw = self.pythonBinary
        return pythonw
    
    def _lookupHomeAndHomeSource(self):
        python = which('python')
        if python is None:
            msg = i18n.translate("Cannot find python executable on the path.")
            raise PythonConfigError(msg)
        return (os.path.dirname(python), "(on path)")

    @classmethod
    def fromConfig(cls, config={}):
        return ConfigPythonFactory(config).getPython()
    
    @classmethod
    def fromDirectory(cls, directory):
        if directory is None:
            raise ValueError("No value specified for 'directory'")
        return PythonInstall(home=directory, homeSource='(configured directory)')
    

class ConfigPythonFactory(object):
    
    """ 
    Creates a python install object using a M* config. The config should contain
    values for MSTAR_HOME and MSTAR_INSTALL. 

    The following algorithm is used to determine the location of the python install:

    1. Python derived from the OS:
       - os.environ['MSTAR_PYTHON']

    2. If running within a source repository:
       - ${project.base}/runtime/target/python

    3. Python derived from MSTAR_HOME:
       - ${MSTAR_HOME}/python                               (if it exists)
       - ${MSTAR_INSTALL}/packages/python/${python.version} (if MSTAR_HOME is a package)

    4. Python derived from MSTAR_INSTALL: 
       - ${MSTAR_INSTALL}/python

    5. Python derived from the interpreter that called this script.

    6. Python found on the path.

    Note that options (2,3,4) are skipped if the platform is linux (since only windows
    python is bundled in M*).
    
    """
    
    def __init__(self, config):
        self.config = config or {}
        from interpreter import Interpreter
        self.interpreter = Interpreter(config)
        self._mstarInstall = None
        self._mstarHome = None

    @property
    def mstarInstall(self):
        if self._mstarInstall is None:
            self._mstarInstall = self.interpretVar('MSTAR_INSTALL')
        return self._mstarInstall

    @property
    def mstarHome(self):
        if self._mstarHome is None:
            self._mstarHome = self.interpretVar('MSTAR_HOME')
        return self._mstarHome

    def getPython(self):
        (home, homeSource) = self._lookupHomeAndHomeSource()
        # Cache source of PYTHON_HOME for later.
        self.config['PYTHON_HOME_SOURCE'] = homeSource
        return PythonInstall(home=home, homeSource=homeSource)
    
    def _lookupHomeAndHomeSource(self):    
        # Check OS environment variables first.
        (pythonHome, pythonHomeSource) = self._getPythonFromOS()

        # Check source repository, if required.
        if pythonHome is None and not isLinux():
            (pythonHome, pythonHomeSource) = self._getPythonFromSourceRepository()

        # Check under MSTAR_HOME, if required.
        if pythonHome is None and not isLinux():
            (pythonHome, pythonHomeSource) = self._getPythonFromMStarHome()

        # Check the release packages, if required.
        if pythonHome is None and not isLinux():
            (pythonHome, pythonHomeSource) = self._getPythonFromReleasePackages()

        # Check under MSTAR_INSTALL, if required.
        if pythonHome is None and not isLinux():
            (pythonHome, pythonHomeSource) = self._getPythonFromMStarInstall()

        # Check the calling interpreter, if required.
        if pythonHome is None:
            (pythonHome, pythonHomeSource) = self._getPythonFromInterpreter()

        # Check the path, if required.
        if pythonHome is None:
            (pythonHome, pythonHomeSource) = self._getPythonFromPath()

        # Verify that python home defined.
        if pythonHome is None:
            msg = i18n.translate("Cannot find python distribution")
            raise PythonConfigError(msg)
        
        # Normalize the python path.
        pythonHome = os.path.abspath(pythonHome)
        
        # Verify that python home exists.
        if not os.access(pythonHome, os.F_OK):
            msg = i18n.translate("Python distribution '%s' %s does not exist") % (pythonHome, pythonHomeSource)
            raise PythonConfigError(msg)

        # Verify that python binary exists and is executable.
        python = os.path.join(pythonHome, 'python%s' % dotExe())
        if not os.access(python, os.F_OK):
            msg = i18n.translate("Expected python binary '%s' not found") % python
            raise PythonConfigError(msg)            
        if not os.access(python, os.X_OK):
            msg = i18n.translate("Expected python binary '%s' not executable") % python
            raise PythonConfigError(msg)

        return (pythonHome, pythonHomeSource)

    def _getPythonFromOS(self):
        # Internally, MSTAR_PYTHON is used for the location of the of the parent directory of
        # the python executable. It may also be used externally by the mstarrun script.
        (pythonHome,pythonHomeSource) = (None,None)
        if 'MSTAR_PYTHON' in os.environ:
            pythonHome = os.environ['MSTAR_PYTHON']
            if 'PYTHON_HOME_SOURCE' in os.environ:
                pythonHomeSource = os.environ['PYTHON_HOME_SOURCE']
            elif 'PYTHON_HOME_SOURCE' in self.config:
                pythonHomeSource = self.config['PYTHON_HOME_SOURCE']
            else:
                pythonHomeSource = "(operating system environment: MSTAR_PYTHON)"
                # Show a warning if python is external to MSTAR_INSTALL.
                if not self._isInternalDirectory(pythonHome):
                    print i18n.translate("Warning: Using external python (at %s) instead of bundled python") % pythonHome
                    print i18n.translate("Warning: Recommend unsetting MSTAR_PYTHON environment variable.")

        return (pythonHome, pythonHomeSource)

    def _isInternalDirectory(self, directory):
        from pathOps import isSubdirectory
        # Check if the directory exists under ${MSTAR_INSTALL}.
        if isSubdirectory(directory, self.interpretPath('{MSTAR_INSTALL}')):
            return True
        # Check if the directory exists under ${REPOSITORY_RUNTIME} if running from source repository.
        if self._isRunningFromSourceRepository():
            return isSubdirectory(directory, self.interpretPath("{REPOSITORY_RUNTIME}"))
        return False

    def _isRunningFromSourceRepository(self):
        from sourceRepository import SourceRepository
        sourceRepository = SourceRepository.getInstance(mstarHome=self.interpretVar('MSTAR_HOME'))
        return sourceRepository.running

    def _getPythonFromSourceRepository(self):
        (pythonHome, pythonHomeSource) = (None, None)
        if self._isRunningFromSourceRepository():
            # TODO would not be necessary if MSTAR_INSTALL points to runtime/target/mstar?
            pythonHome = self.interpretPath("{REPOSITORY_RUNTIME}/python")
            if not os.access(pythonHome, os.F_OK):
                msg = i18n.translate("Could not find bundled python in repository; verify that 'runtime' module" +
                                     " has been installed.")
                raise PythonConfigError(msg)
            pythonHomeSource = "(bundled python under REPOSITORY_RUNTIME)"
        return (pythonHome, pythonHomeSource)

    def _getPythonFromMStarPython(self):
        (pythonHome, pythonHomeSource) = (None, None)
        if 'MSTAR_PYTHON' in os.environ:
            pythonHome = os.environ["MSTAR_PYTHON"]
            pythonHomeSource = "(operating system environment: MSTAR_PYTHON)"
        return (pythonHome, pythonHomeSource)
    
    def _getPythonFromMStarHome(self):
        # Check for ${MSTAR_HOME}/python/python${exe}
        python = os.path.join(self.mstarHome, 'python', 'python%s' % dotExe())
        if os.access(python, os.X_OK):
            pythonHome = os.path.join(self.mstarHome, 'python')
            return (pythonHome, '(bundled python under MSTAR_HOME)')

        return (None,None)

    def _getPythonFromReleasePackages(self):
        # Get the mstar instance.
        from install.mstarInstall import MStarInstall
        mstar = MStarInstall.getInstance(self.mstarInstall)
        
        # Check that packages are available.
        if not os.path.exists(mstar.packagesDir):
            return (None, None)

        # Create an mstar release.
        from mstarRelease import MStarRelease
        release = MStarRelease(mstarInstall=self.mstarInstall, mstarHome=self.mstarHome, overrides=self.config)

        # The release may not be fully installed yet.
        if not release.installed:
            return (None, None)

        # Check for python package from the release.
        python = release.getPackage('python')
        if python is not None:
            pythonHome = mstar.getPackagePath(python)
            if os.path.exists(pythonHome):
                return (pythonHome, "(package %s:%s for release %s)" % (python.name, python.version, release.version))

        # No python package found for the release.
        return (None, None)
        
    def _getPythonFromMStarInstall(self):
        # Check for ${MSTAR_INSTALL}/python/python${exe}.
        python = os.path.join(self.mstarInstall, 'python', 'python%s' % dotExe())
        if os.access(python, os.X_OK):
            pythonHome = os.path.join(self.mstarInstall, 'python')
            return (pythonHome, "(bundled python under MSTAR_INSTALL)")
        
        return (None, None)

    def _getPythonFromPath(self):
        (pythonHome, pythonHomeSource) = (None, None)
        python = which('python')
        if python is not None:
            pythonHome = os.path.dirname(python)
            pythonHomeSource = "(on path)"
            print i18n.translate("Warning: Using external python (at %s) instead of bundled python") % pythonHome
        return (pythonHome, pythonHomeSource)

    def _getPythonFromInterpreter(self):
        (pythonHome, pythonHomeSource) = (None, None)
        if sys.executable is not None and os.access(sys.executable, os.X_OK):
            pythonHome = os.path.dirname(sys.executable)
            pythonHomeSource = "(invoking python interpreter)"
        return (pythonHome, pythonHomeSource)

    def interpretPath(self, path):
        return self.interpreter.interpretPath(path)

    def interpretVar(self, var):
        return self.interpreter.interpretVar(var)

