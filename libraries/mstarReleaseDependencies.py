import os


class MStarReleaseDependencies(object):

    """ Sets the release dependencies in the minestar config. """
    
    def __init__(self, sources, config):
        self.sources = sources
        self.config = config
        from interpreter import Interpreter
        self.interpreter = Interpreter(config)
        self.release = self._loadRelease()

    def _loadRelease(self):
        mstarInstallDir = self._interpretPath('{MSTAR_INSTALL}')
        mstarHomeDir = self._interpretPath('{MSTAR_HOME}')
        from mstarRelease import MStarRelease
        release = MStarRelease(mstarInstall=mstarInstallDir, mstarHome=mstarHomeDir, overrides=self.config)
        if release.installed:
            return release
        return None

    def setGeoserverProperties(self):
        (geoserverHome, geoserverHomeSource) = self._defaultTuple('geoserver')
        # The geoserver package should only be installed if the machine is an app server.
        package = self._getPackage('geoserver')
        if package is not None:
            (geoserverHome, geoserverHomeSource) = self._packageTuple(package)
        self.sources['_GEOSERVER_HOME'] = geoserverHomeSource
        self.config['_GEOSERVER_HOME'] = geoserverHome

    def setPostgisProperties(self):
        (postgisHome, postgisHomeSource) = self._defaultTuple('postgis')
        # The postgis package should only be installed if the machine is an app server.
        package = self._getPackage('postgis')
        if package is not None:
            (postgisHome, postgisHomeSource) = self._packageTuple(package)
        self.sources['_POSTGIS_HOME'] = postgisHomeSource
        self.config['_POSTGIS_HOME'] = postgisHome

    def setJettyProperties(self):
        (jettyHome, jettyHomeSource) = self._defaultTuple('jetty')
        # The jetty package should only be installed if the machine is an app server.
        package = self._getPackage('jetty')
        if package is not None:
            (jettyHome, jettyHomeSource) = self._packageTuple(package)
        self.sources['_JETTY_HOME'] = jettyHomeSource
        self.config['_JETTY_HOME'] = jettyHome

    def setToolkitProperties(self):
        (toolkitHome, toolkitHomeSource) = self._defaultTuple('toolkit')
        # The toolkit package should only be installed if the machine is running windows.
        package = self._getPackage('toolkit')
        if package is not None:
            (toolkitHome, toolkitHomeSource) = self._packageTuple(package)
        self.sources['MSTAR_TOOLKIT'] = toolkitHomeSource
        self.config['MSTAR_TOOLKIT'] = toolkitHome

    def _getPackage(self, name):
        return None if self.release is None else self.release.getPackage(name)

    def _defaultTuple(self, name):
        path = "{MSTAR_INSTALL}/%s" % name
        source = "(inferred from MSTAR_INSTALL)"
        return (path, source)

    def _packageTuple(self, package):
        path = self._packagePath(package)
        source = self._packageSource(package)
        return (path, source)

    def _packagePath(self, package):
        # Get the actual package path from the M* install.
        from install.mstarInstall import MStarInstall
        mstar = MStarInstall.getInstance(self._interpretPath('{MSTAR_INSTALL}'))
        return mstar.getPackagePath(package)

    def _packageSource(self, package):
        return "(package %s:%s for release %s)" % (package.name, package.version, self.release.version)

    def _interpretPath(self, path):
        return self.interpreter.interpretPath(path)
