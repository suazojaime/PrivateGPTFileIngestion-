from abc import ABCMeta, abstractmethod, abstractproperty

import os

from pathOps import simplifyPath
from symlink import resolvePossibleSymbolicLink


class SourceRepository(object):
    
    __metaclass__ = ABCMeta
    
    @property
    def running(self):
        return False
    
    @property
    def homeDir(self):
        raise NotImplementedError

    @property
    def runtimeDir(self):
        raise NotImplementedError

    @abstractmethod    
    def interpretVar(self, var):
        raise NotImplementedError
    
    @classmethod
    def getInstance(cls, mstarHome=None):
        if mstarHome is not None:
            return MStarHomeSourceRepository(mstarHome=mstarHome)
        return DummySourceRepository()

    
class MStarHomeSourceRepository(SourceRepository):

    """ Class for source repository operations. """

    def __init__(self, mstarHome):
        super(MStarHomeSourceRepository, self).__init__()
        if mstarHome is None:
            raise ValueError("No 'mstarHome' value specified.")
        self._mstarHome = mstarHome
        self._homeDir = None
        self._runtimeDir = None
        self._running = None

    @property
    def running(self):
        """ Determines if running M* from the source repository. """
        return self._mstarHome.endswith("config")

    @property
    def homeDir(self):
        if self._homeDir is None:
            # If mstarHomeDir is       :  /sbox/mstar/fleetcommander/src/main/config
            # then repositoryHomeDir is:  /sbox/mstar
            self._homeDir = simplifyPath(os.path.join(self._mstarHome, '..', '..', '..', '..'))
        return self._homeDir

    @property
    def runtimeDir(self):
        # e.g. /sbox/mstar/runtime/target
        return os.path.join(self.homeDir, 'runtime', 'target')

    def libDir(self, lib):
        # e.g. /sbox/mstar/runtime/target/geoserver
        return os.path.join(self.runtimeDir, lib)

    def interpretVar(self, var):
        if var == 'REPOSITORY_HOME':
            return self.homeDir
        if var == 'REPOSITORY_RUNTIME':
            return self.runtimeDir
        elif var == "REPOSITORY_MSTAR_HOME":
            return self.libDir('mstar')
        elif var == "REPOSITORY_EXTENSIONS_HOME":
            return self.libDir('extensions')
        elif var == "_GEOSERVER_HOME" or var == "REPOSITORY_GEOSERVER_HOME":
            # Geoserver uses Jetty, so must resolve any symbolic links (and need to normalize path first).
            return resolvePossibleSymbolicLink(self.libDir('geoserver'))
        elif var == "_POSTGIS_HOME" or var == "REPOSITORY_POSTGIS_HOME":
            return resolvePossibleSymbolicLink(self.libDir('postgis'))
        elif var == "_JETTY_HOME" or var == "REPOSITORY_JETTY_HOME":
            # Jetty cannot process symbolic links, so must resolve the (normalized) path.
            return resolvePossibleSymbolicLink(self.libDir('jetty'))

        return None

class DummySourceRepository(SourceRepository):

    """ Dummy implementation of SourceRepository interface. Always returns False to 'running' """
    
    @property
    def running(self):
        return False
    
    def interpretVar(self, var):
        raise NotImplementedError
