import os
import sys
from abc import abstractmethod

import mstarpaths

class PostgisError(RuntimeError):
    """ Indicates a general postgis error. """
    pass


class PostgisNotFoundError(PostgisError):
    """ Indicates that postgis was not found on the system. """
    pass
   

class PostgisRunningError(PostgisError):
    """ Indicates that PostrgeSQL is running when it should be shutdown. """
    def __init__(self):
        super(PostgisRunningError, self).__init__("postgresql is already running")


class PostgisCommandError(PostgisError):
    
    """ Indicates that a postgis command failed. """
    
    def __init__(self, command, exitCode):
        self._command = command
        self._exitCode = exitCode

    @property
    def command(self):
        return self._command
    
    @property
    def exitCode(self):
        return self._exitCode

    def __str__(self):
        return "Failed to execute postgis command: %s" % self.command
    
class Options(object):
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        
        
class PostgisControl(object):

    """ Class for controlling PostgreSQL. """
    
    APP_NAME = "PostgreSQL"
    
    def __init__(self, postgisHomeDir=None, postgisDataDir=None, postgisDatabase=None, postgisUser=None, options=None):
        # Values will be checked when properties are accessed.
        self._postgisHomeDir = postgisHomeDir
        self._postgisDataDir = postgisDataDir
        self._postgisDatabase = postgisDatabase
        self._postgisUser = postgisUser
        self._options = options or Options()
        # Get the SPI implementation.
        if sys.platform.startswith("win"):
            self._spi = WindowsPostgisControlSPI(control=self)
        else:
            self._spi = LinuxPostgisControlSPI(control=self)
    
    @property
    def options(self):
        return self._options
    
    @property
    def postgisHomeDir(self):
        if self._postgisHomeDir is None:
            postgisHomeDir = mstarpaths.interpretPath("{_POSTGIS_HOME}")
            if postgisHomeDir in [None,'{_POSTGIS_HOME}']:
                raise PostgisError("No value specified for POSTGIS_HOME")
            self._postgisHomeDir = postgisHomeDir
        return self._postgisHomeDir
    
    @property
    def postgisDataDir(self):
        if self._postgisDataDir is None:
            postgisDataDir = mstarpaths.interpretPath("{_POSTGIS_DATA_DIR}")
            if postgisDataDir in [None,'{_POSTGIS_DATA_DIR}']:
                raise PostgisError("No value specified for POSTGIS_DATA_DIR")
            self._postgisDataDir = postgisDataDir
        return self._postgisDataDir

    @property
    def postgisDatabase(self):
        if self._postgisDatabase is None:
            postgisDatabase = mstarpaths.interpretPath("{_POSTGIS_DATABASE}")
            if postgisDatabase in [None,'{_POSTGIS_DATABASE}']:
                raise PostgisError("No value specified for POSTGIS_DATABASE")
            self._postgisDatabase = postgisDatabase
        return self._postgisDatabase
    
    @property
    def postgisUser(self):
        if self._postgisUser is None:
            postgisUser = mstarpaths.interpretVar("_POSTGIS_USER")
            if postgisUser in [None,'{_POSTGIS_USER}']:
                raise PostgisError("No value specified for POSTGIS_USER")
            self._postgisUser = postgisUser
        return self._postgisUser
    
    @property
    def postgisLogFile(self):
        return os.path.join(self.postgisDataDir, 'postgresql.log')

    @property
    def spi(self):
        return self._spi

    @property
    def installed(self):
        """ Determines if postgis is installed. """
        return self.spi.installed()
    
    @property
    def running(self):
        """ Determines if postgis is running. """
        return self.spi.running()
    
    def initDB(self):
        """ Initialize the database. """
        if self.options.verbose:
            print "Initializing %s for user %s ..." % (self.APP_NAME, self.postgisUser)
        return self.spi.initDB()
    
    def registerService(self, serviceName, startAutomatically=False):
        """ Register the database as a Windows service. """
        if self.options.verbose:
            print "Registering windows service %s via %s ..." % (serviceName, self.APP_NAME)
        return self.spi.registerService(serviceName, startAutomatically)
    
    def unregisterService(self, serviceName):
        """ Unregister the database as a Windows service. """
        if self.options.verbose:
            print "Unregister windows service %s via %s ..." % (serviceName, self.APP_NAME)
        return self.spi.unregisterService(serviceName)
    
    def start(self):
        """ Start the database. """
        if self.options.verbose:
            print "Starting %s ..." % self.APP_NAME
        return self.spi.start()
    
    def stop(self):
        """ Stop the database. """
        if self.options.verbose:
            print "Stopping %s ... " % self.APP_NAME
        return self.spi.stop()
    
    def installExtension(self, extensionName):
        """ Install an extension in the database. """
        if self.options.verbose:
            print "Installing %s extension %s ..." % (self.APP_NAME, extensionName)
        return self.spi.installExtension(extensionName)


class PostgisControlSPI(object):
    
    """ Service provider interface for postgres control operations. """
    
    def __init__(self, control):
        self._control = control
        
    @property
    def control(self):
        return self._control
    
    @property
    def options(self):
        return self.control.options
    
    @property
    def postgisHomeDir(self):
        return self.control.postgisHomeDir
    
    @property
    def postgisDataDir(self):
        return self.control.postgisDataDir
    
    @property
    def postgisDatabase(self):
        return self.control.postgisDatabase
    
    @property
    def postgisUser(self):
        return self.control.postgisUser
    
    @property
    def postgisLogFile(self):
        return self.control.postgisLogFile

    @abstractmethod
    def installed(self):
        raise NotImplementedError()
    
    @abstractmethod
    def running(self):
        raise NotImplementedError()
    
    @abstractmethod
    def initDB(self):
        """" Initialize the database. """
        raise NotImplementedError()
    
    @abstractmethod
    def registerService(self, serviceName, startAutomatically):
        """ Register the database as a Windows service. """
        raise NotImplementedError()
    
    @abstractmethod
    def unregisterService(self, serviceName):
        """ Unregister the database as a Windows service. """
        raise NotImplementedError()
    
    @abstractmethod
    def start(self):
        """ Start the database. """
        raise NotImplementedError()
    
    @abstractmethod
    def stop(self):
        """ Stop the database. """
        raise NotImplementedError()

    @abstractmethod
    def installExtension(self, extensionName):
        """ Install an extension in the database. """
        raise NotImplementedError()
    
    def _initdbCommand(self, pgctl):
        return [pgctl, "initdb", "-s", "-D", self.postgisDataDir, "-o", "-U %s -E utf8 -A trust" % self.postgisUser]
    
    def _registerCommand(self, pgctl, service, startType):
        return [pgctl, "register", "-N", service, "-D", self.postgisDataDir, "-S", startType]
    
    def _unregisterCommand(self, pgctl, service):
        return [pgctl, "unregister", "-N", service]
    
    def _startCommand(self, pgctl):
        return [pgctl, "start", "-s", "-w", "-D", self.postgisDataDir, "-U", self.postgisUser, "-l", self.postgisLogFile]
    
    def _stopCommand(self, pgctl):
        return [pgctl, "stop", "-s", "-w", "-D", self.postgisDataDir, "-l", self.postgisLogFile]

    def _stopImmediateCommand(self, pgctl):
        return [pgctl, "stop", "-s", "-w", "-D", self.postgisDataDir, "-m", "immediate", "-l", self.postgisLogFile]

    def _installExtensionCommand(self, psql, extension):
        return [psql, "-d", self.postgisDatabase, "-U", self.postgisUser, "-c", "CREATE EXTENSION IF NOT EXISTS %s" % extension]

    def _exec(self, command=[]):
        import subprocess
        if self.options.verbose:
            print "Running %s command: %s" % (PostgisControl.APP_NAME, command)
        try:
            subprocess.call(command)
        except subprocess.CalledProcessError as e:
            output = e.output.replace('\n', '').replace('\r', '')
            print "Error: Failed to execute postgis command: %s" % command
            print "Error:   exitCode: %s, output: %s" % (e.returncode, output)
            raise PostgisCommandError(' '.join(command), e.returncode)


class WindowsPostgisControlSPI(PostgisControlSPI):
    
    """ Windows implementation of service provider interface for postgres control operations. """
    
    def __init__(self, control):
        super(WindowsPostgisControlSPI, self).__init__(control)
        self._pgctl = None
        self._psql = None
    
    def _findBinary(self, name):
        return mstarpaths.interpretPath("%s/bin/%s" % (self.postgisHomeDir, name))
    
    def _findBinaryOrFail(self, name):
        binary = self._findBinary(name)
        if not os.access(binary, os.X_OK):
            raise PostgisNotFoundError("Cannot access postgis command: %s" % binary)
        return binary
        
    @property
    def pgctl(self):
        if self._pgctl is None:
            self._pgctl = self._findBinaryOrFail("pg_ctl.exe")
        return self._pgctl
    
    @property
    def psql(self):
        if self._psql is None:
            self._psql = self._findBinaryOrFail("psql.exe")
        return self._psql

    # @Override
    def installed(self):
        return self._findBinary("pg_ctl.exe") is not None and self._findBinary("psql.exe") is not None

    # @Override
    def running(self):
        return os.path.exists(os.path.join(self.postgisDataDir, "postmaster.pid"))

    # @Override
    def initDB(self):
        self._exec(self._initdbCommand(self.pgctl))
        
    # @Override
    def registerService(self, serviceName, startAutomatically=False):
        startType = "auto" if startAutomatically else "demand"
        self._exec(self._registerCommand(self.pgctl, serviceName, startType))
        sys.stdout.write("  Successfully registered %s\n\n" % serviceName)

    # @Override
    def unregisterService(self, serviceName):
        # Force PostgreSQL to stop immediately before we try and unregister the service
        self._exec(self._stopImmediateCommand(self.pgctl))
        sys.stdout.write("Successfully stopped %s\n" % serviceName)
        self._exec(self._unregisterCommand(self.pgctl, serviceName))
        sys.stdout.write("Successfully unregistered %s\n" % serviceName)

    # @Override
    def start(self):
        self._exec(self._startCommand(self.pgctl))
        
    # @Override
    def stop(self):
        try:
            # Be gentle
            self._exec(self._stopCommand(self.pgctl))
        except:
            # Be brutal
            import subprocess
            subprocess.call("taskkill /IM postgres.exe")
    
    # @Override
    def installExtension(self, extension):
        self._exec(self._installExtensionCommand(self.psql, extension))


class LinuxPostgisControlSPI(PostgisControlSPI):
    
    """ Linux implementation of service provider interface for postgres control operations. """
    
    def __init__(self, control):
        super(LinuxPostgisControlSPI, self).__init__(control)
        self._pgctl = None
        self._psql = None
  
    def _findBinaries(self):
        """ Find the postgresql binaries on the system. Returns (None,None) if no binaries
            are found, otherwise returns tuple (pgctl, psql) representing the pgctl binary
            and the psql binary respectively. """
        print "This is a UNIX based system, looking for installed postgresql ..."

        # Find the postgresql base path.
        # TODO should allow path(s) to be configured.
        basepgpath = os.path.join(os.sep, "usr", "lib", "postgresql")
        if not os.path.exists(basepgpath):
            return (None,None)

        # Verify that postgresql is installed. Try different versions until valid install found.
        for version in os.listdir(basepgpath):
            pgpath = os.path.join(basepgpath, version)
            pgctl = os.path.join(pgpath, 'bin', 'pg_ctl')
            psql = os.path.join(pgpath, 'bin', 'psql')
            if os.path.isfile(pgctl) and os.path.isfile(psql):
                return (pgctl, psql)

        # No binaries found.
        return (None, None)
        
    def _findBinariesOrDie(self):
        (pgctl, psql) = self._findBinaries()
        if pgctl is None or psql is None:
            raise PostgisNotFoundError("Cannot find postgresql implementation on system")
        return (pgctl, psql)

    @property
    def pgctl(self):
        if self._pgctl is None:
            (self._pgctl, self._psql) = self._findBinariesOrDie()
        return self._pgctl
    
    @property
    def psql(self):
        if self._psql is None:
            (self._pgctl, self._psql) = self._findBinariesOrDie()
        return self._psql
    
    # @Override
    def installed(self):
        return self.pgctl is not None and self.psql is not None
    
    def running(self):
        return UnixProcess.isRunning("postgres")
        
    # @Override
    def initDB(self):
        self._exec(self._initdbCommand(self.pgctl))
    
    # @Override
    def registerService(self, serviceName, startAutomatically):
        raise PostgisError("Cannot register a windows service on non-Windows platform.")
    
    # @Override
    def unregisterService(self, serviceName):
        raise PostgisError("Cannot unregister a windows service on a non-Windows platform.")
    
    # @Override
    def start(self):
        self._exec(self._startCommand(self.pgctl))
        
    # @Override
    def stop(self):
        self._exec(self._stopCommand(self.pgctl))
    
    # @Override
    def installExtension(self, extension):
        self._exec(self._installExtensionCommand(self.psql, extension))

class UnixProcess(object):

    @classmethod
    def isRunning(cls, processId):
        """ Determines if the process is running. """
        psIdLen = len(processId)
        if psIdLen > 0:
            psIdLen = psIdLen - 1
            regprocessId = "[" + processId[0] + "]" + processId[-psIdLen:]
            output = cls.find(regprocessId)
            import re
            return re.search(processId, output) is not None
        
    @classmethod
    def find(cls, processId):
        """ Find the process. """
        from subprocess import Popen, PIPE
        ps = Popen("ps -ef | grep "+processId, shell=True, stdout=PIPE)
        output = ps.stdout.read()
        ps.stdout.close()
        ps.wait()
        return output

if __name__ == '__main__':
    control = PostgisControl(postgisHomeDir='C:\\sbox\\mstar\\BRANCH_MSTAR_501\\runtime-dev\\target\\mstar\\packages\\postgis\\2.3.2',
                             postgisDataDir='C:\\tmp\\mstarFiles\\systems\\main\\data\\postgis')
    control.registerService('M*GeoDatabase')
    control.unregisterService('M*GeoDatabase')
