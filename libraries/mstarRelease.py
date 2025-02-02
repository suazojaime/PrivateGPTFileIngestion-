import os


def mstarrunDebugEnabled():
    """ Determines if mstarrun debug is enabled (i.e. if MSTARRUN_DEBUG is defined in OS environment). """
    return 'MSTARRUN_DEBUG' in os.environ


def mstarrunDebug(msg):
    """ Print a message to stdout if mstarrun debug is enabled. """
    if mstarrunDebugEnabled():
        print "debug: %s" % msg


class MStarRelease(object):

    """ Class representing a minestar release. The packages of the release must be
        installed in the ${MSTAR_INSTALL}/packages directory. """

    def __init__(self, mstarInstall=None, mstarHome=None, overrides=None):
        # TODO should inject the repository
        from install.mstarInstall import MStarInstall
        self.mstarInstall = MStarInstall.getInstance(mstarInstall)
        # TODO what if mstarHome is None?
        from install.mstarBuild import MStarBuild
        self.mstarBuild = MStarBuild(mstarHome)
        self._version = None
        self._packages = None
        self._dependencies = None
        self._overrides = overrides

    @property
    def installed(self):
        """ Determines if the M* release is installed yet. During a refresh build the MineStar.ini may be
            updated before the packages are installed, leading to issues in bootstrapping. """
        # The MSTAR_HOME directory must exist.
        if not os.path.exists(self.mstarBuild.path):
            return False
        # The ${MSTAR_INSTALL}/packages directory must exist.
        if not os.path.exists(self.mstarInstall.packagesDir):
            return False
        # The system:${version} package must be installed.
        repository = self.mstarInstall.installedPackagesRepository
        if not repository.containsPackage('system:%s' % self.version):
            return False
        # Each dependency must be installed.
        return all(repository.containsPackage(dependency) for dependency in self.dependencies)

    @property
    def version(self):
        """ Get the version of the M* release. """
        return self.mstarBuild.version

    @property
    def overrides(self):
        return self._overrides

    @property
    def dependencies(self):
        """ Get the dependencies of the M* release. """
        if self._dependencies is None:
            self._dependencies = self._loadDependencies()
        return self._dependencies

    def _loadDependencies(self):
        def getConfiguredDependencies(package):
            import install.mstarPackages
            return install.mstarPackages.getPackageDependencies(package=package)

        def isSupportedDependency(dependency):
            targets = self.mstarInstall.supportedTargets
            return targets is None or dependency.target is None or dependency.target in targets

        def getPackageDependencies(package):
            # Get the configured dependencies for the package (filtered by supported targets).
            dependencies = [x for x in getConfiguredDependencies(package) if isSupportedDependency(x)]

            # Log the dependencies.
            if mstarrunDebugEnabled():
                repository = self.mstarInstall.installedPackagesRepository
                mstarrunDebug("Dependencies for M* release %s: (%s)" % (self.version, len(dependencies)))
                for dependency in dependencies:
                    mstarrunDebug("  %s    [installed:%s]" % (str(dependency).ljust(40, ' '), repository.containsPackage(dependency)))
            
            return dependencies

        return getPackageDependencies(self._findPackageOrDie('system:%s' % self.version))

    @property
    def packages(self):
        """ Get the installed packages of the release. """
        if self._packages is None:
            self._packages = self._loadPackages()
        return self._packages

    def _loadPackages(self):
        # Get the mstar system package.
        mstarSystemPackage = self._findPackageOrDie('system:%s' % self.version)

        # Get the dependencies from the mstar system package configuration.
        # (assumes that the system config contains the closure of required packages)
        packages = [self._findPackageOrDie(x) for x in self.dependencies]

        # Add the system package.
        packages.append(mstarSystemPackage)

        return packages

    def getPackage(self, name):
        """ Get a package from the release, e.g. 'geoserver'. """
        from install.packageRepositories import PackagesRepository
        repository = PackagesRepository(self.packages)
        return repository.findPackage(name)

    def getPackagePath(self, name):
        """Get a package path from the release, e.g. 'geoserver' -> '${mstarInstall}/packages/geoserver/5.6.0'"""
        pkg = self.getPackage(name)
        if pkg:
            return self.mstarInstall.getPackagePath(pkg)
        return None

    def validate(self):
        """ Validate the release by checking all dependencies are installed. """
        self._findPackageOrDie('system:%s' % self.version)
        for dependency in self.dependencies:
            self._findPackageOrDie(dependency)

    def _findPackageOrDie(self, packageId):
        """ Find the specified installed package or raise an error. """
        repository = self.mstarInstall.installedPackagesRepository
        package = repository.findPackage(packageId)
        if package is None:
            from install.packages import UnresolvedPackageError
            raise UnresolvedPackageError("Cannot resolve package '%s' for mstar release %s" % (packageId, self.version))
        return package
