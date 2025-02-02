from packageChanges import PackageChange, PackageChangeFactory
from packages import PackageIdentifier, PackageDependency, Package, ConflictingPackageError, UnresolvedPackageError
from packageRepositories import PackageRepository, PackagesRepository
from versions import Version


class PackageManager(object):
    
    """ Operations for managing packages: install, uninstall, list, changes, etc. """
    
    def __init__(self, available=None, installed=None, 
                 supportedTargets=['client','server'], 
                 policy=PackageChange.POLICY_INSTALL):
        # Create an empty 'available' repository if not supplied.
        if available is None:
            available = PackagesRepository([])
        # ... otherwise verify that supplied value is valid.
        elif not isinstance(available, PackageRepository):
            raise TypeError("Cannot create package manager: 'available' repository has invalid type %s." % type(available))
        # Create an empty 'installed' repository if not supplied.
        if installed is None:
            installed = PackagesRepository([])
        # ... otherwise verify that supplied value is valid.
        elif not isinstance(installed, PackageRepository):
            raise TypeError("Cannot create package manager: 'installed' repository has invalid type %s." % type(installed))
        self._available = available
        self._installed = installed
        self._supportedTargets = supportedTargets
        self._policy = policy
        
    @property
    def available(self):
        return self._available

    @property
    def installed(self):
        return self._installed
    
    @property
    def supportedTargets(self):
        return self._supportedTargets
    
    @supportedTargets.setter
    def supportedTargets(self, supportedTargets):
        self._supportedTargets = supportedTargets

    @property
    def policy(self):
        return self._policy
    
    def refresh(self):
        """ Refresh the 'available' and 'installed' repositories. """
        self.available.refresh()
        self.installed.refresh()

    def closure(self, package=None):
        """ Return collection containing the closure of a package and its dependencies. If no
            package is specified then the closure of all installed packages is returned. """
        closure = Closure(resolverFn=self.__resolvePackage, dependenciesFn=self.__supportedDependencies)
        if package is not None:
            result = closure.ofPackage(package)
        else:
            result = closure.ofPackages(self.installed.packages)
        return result

    # install('geoserver')
    # install('geoserver:2.5.1')
    # install(PathPackage('packages/geoserver-2.5.1'))
    def install(self, package, options=None):
        """
        Install a package (and optionally its dependencies). 
        
        :param package: the package to be installed. May be specified as a package identifier 
        (e.g. 'foo', 'foo:1.0'), or as a package object. If specified as a package identifier
        then the package must exist in the installed or available repositories. If specified
        as a package the supplied package will installed.
        
        :param options: a map of installed options. Supported options:
               - 'installDependencies' - indicates that the package's dependencies should also
                 be installed. Defaults to True.
        
        :return the collection of installed packages. May be empty if no packages were installed.
        
        :raise UnresolvedPackageError if the package cannot be resolved within the available
        packages repository.
        
        """
        return self._installPackage(package=package, options=options, processed=[])

    def _installPackage(self, package, options=None, processed=[]):
        if package is None:
            raise TypeError("Cannot install package: no package specified.")

        # print "## install() package=%s" % package
        # print "## install() available:"
        # for p in self.available.packages:
        #     print "## install()   %s" % p
        # print "## install() installed:"
        # for p in self.installed.packages:
        #     print "## install()   %s" % p
            
        # Resolve the package if required.
        if not isinstance(package, Package):
            resolved = self.available.findPackage(package)
            if resolved is None:
                resolved = self.installed.findPackage(package)
            if resolved is None:
                raise UnresolvedPackageError("Cannot resolve package '%s'." % package)
            package = resolved
            # print "## install() resolved=%s" % resolved

        # Checks if a package has already been processed.
        def alreadyProcessed(pkg):
            return any((p.name == pkg.name and p.version == pkg.version) for p in processed)

        # If the package has already been processed: done.
        if alreadyProcessed(package):
            return []

        # Mark the package as processed.
        processed.append(package)

        installed = []

        # Check if the package can be installed, according to the install policy.
        change = self.__createPackageChange(package)
        if change.replace and self.installed.replacePackage(package):
            installed.append(package)
        if change.install and self.installed.installPackage(package):
            installed.append(package)

        def getPackageDependencies(pkg):
            if options is not None and 'dependencies' in options:
                return options['dependencies']
            return pkg.dependencies

        def supportedDependencies(pkg):
            dependencies = []
            for dependency in getPackageDependencies(pkg):
                if self.isSupportedDependency(dependency):
                    dependencies.append(PackageDependency(name=dependency.name, version=dependency.version))
            return dependencies

        # Install the package's dependencies, if required.
        if installDependencies(options) and self.installed.containsPackage(package):
            for dependency in supportedDependencies(package):
                packageID = PackageIdentifier(dependency.name, dependency.version)
                installed.extend(self._installPackage(packageID, options, processed))

        return installed

    # uninstall('geoserver')
    # uninstall('geoserver:2.5.1')
    # uninstall(PathPackage('packages\\geoserver-2.5.1'))
    def uninstall(self, package, options=None):
        """ Uninstall a package (and optionally all its dependencies). Returns 
            a collection of uninstalled packages. """
        uninstalled = []
        installedPackage = self.installed.findPackage(package)
        while installedPackage is not None:
            # Uninstall the package.
            uninstalled.extend(self.installed.uninstallPackage(installedPackage))
            # Uninstall the dependencies, if required.
            if uninstallDependencies(options):
                for dependency in self.__supportedDependencies(installedPackage):
                    uninstalled.extend(self.uninstall(dependency, options))
            # Check for other versions of the package (e.g. if uninstalling 'foo:*')
            installedPackage = self.installed.findPackage(package)
        return uninstalled

    def hasChanges(self):
        """ Determines if there any package changes. """
        return len(self.changes()) > 0

    def changes(self):
        """ Return a collection of package changes between the available and installed packages. """
        changes = []
        for package in self.available.packages:
            change = self.__createPackageChange(package)
            if not change.skip:
                changes.append(change)
        return changes

    def update(self):
        """ Update the packages by applying any changes. """
        for change in self.changes():
            # Apply package change if INSTALL, REPLACE, or UNINSTALL.
            package = change.available
            if change.install:
                self.installed.installPackage(package)
            elif change.replace:
                self.installed.replacePackage(package)
            elif change.uninstall:
                self.installed.uninstallPackage(package)
                
    def __resolvePackage(self, package):
        # Look for a matching installed package.
        resolved = self.installed.findPackage(package)
        if resolved is None:
            # Look for a matching available packages.
            resolved = self.available.findPackage(package)
            # Cannot find package in available or installed packages -> cannot resolve.
            if resolved is None:
                print "Error: unable to resolve package %s" % package
                print "     : Available packages: %s" % self.available.packages
                print "     : Installed packages: %s" % self.installed.packages
                raise UnresolvedPackageError("Cannot resolve package package.")
        return resolved

    def isSupportedDependency(self, dependency):
        # Include the dependency only if it has no target, or the target is supported.
        return dependency.target is None or dependency.target in self.supportedTargets

    def __supportedDependencies(self, package):
        dependencies = [PackageDependency(name=d.name, version=d.version) for d in package.dependencies if self.isSupportedDependency(d)]
        # for dependency in package.dependencies:
        #     # Include the dependency only if it has no target, or the target is supported.
        #     if dependency.target is None or dependency.target in self.supportedTargets:
        #         dependencies.append(PackageDependency(name=dependency.name, version=dependency.version))
        return dependencies

    def __createPackageChange(self, package):
        # Compare the package against the installed packages in the repository.
        factory = PackageChangeFactory(policy=self.policy)
        return factory.create(availablePackage=package, installedRepository=self.installed)


def installDependencies(options={}):
    return options is None or options.get('installDependencies', True)


def uninstallDependencies(options={}):
    return options is not None and options.get('uninstallDependencies', False)


class Closure(object):
    
    """ Class for determining the closure of a package or of a collection of packages. """
    
    def __init__(self, resolverFn, dependenciesFn):
        self.resolverFn = resolverFn
        self.dependenciesFn = dependenciesFn
    
    def ofPackages(self, packages):
        """ Get the closure of a collection of packages. """
        closure = {}
        for package in packages:
            self._closureOfPackage(package, closure)
        return closure
    
    def ofPackage(self, package):
        """ Get the closure of a single package. """
        closure = {}
        self._closureOfPackage(package, closure)
        return closure

    def _closureOfPackage(self, packageID, closure={}):
        package = self.resolverFn(packageID)
        
        # Check if there is a conflicting version of the package in the closure.
        if package.name in closure:
            existing = closure[package.name]
            if Version.compare(existing.version, package.version) != 0:
                raise ConflictingPackageError("Conflicting versions for package '%s' in closure: %s vs %s." 
                                              % (package.name, package.version, existing.version))
        # Otherwise add the package (and its dependencies) to the closure.
        else:
            closure[package.name] = package
            # Add the dependencies of the package.
            for dependency in self.dependenciesFn(package):
                packageID = PackageIdentifier(name=dependency.name, version=dependency.version)
                self._closureOfPackage(packageID=packageID, closure=closure)

