import os
import zipfile

from abc import ABCMeta, abstractmethod
from fileOps import FileOps
from typeOps import isCollectionOf, isInstanceOf
from packageConfig import PackageConfig
from packages import Package, PathPackage, findPackageWithMaximumVersion, CompressedPackage
from types import StringTypes


class RepositoryError(RuntimeError):
    """ Class indicating a repository error. """
    pass


class ReadOnlyRepositoryError(RepositoryError): 
    """ Class indicating that a write operation was requested on a read-only repository. """
    pass


class PackageRepository(object):
    
    """ Operations on a package repository: install(), uninstall(), find(), contains() """

    __metaclass__ = ABCMeta

    _repositoryID = 1

    def __init__(self):
        # Initially there are no packages loaded.
        self._packages = None
        # Assign a repository ID.
        self._repositoryID = PackageRepository._repositoryID
        PackageRepository._repositoryID += 1

    @property
    def repositoryID(self):
        return self._repositoryID

    def __repr__(self):
        return "%s(id=%s)" % (type(self), self.repositoryID)

    def refresh(self):
        """ Refresh the repository. This will remove loaded packages from the cache, etc. """
        self._packages = None

    @property
    def packages(self):
        """ Return the collection of installed packages in the repository. """
        if self._packages is None:
            self._packages = self._loadPackages()
        return self._packages

    @packages.setter
    def packages(self, packages):
        """ Update the collection of packages contained in the repository. """
        if packages is not None:
            for p in packages:
                if p is None:
                    raise ValueError("Cannot update repository: package is null.")
                if not isInstanceOf(p, Package):
                    raise TypeError("Cannot update repository: package has incorrect type %s." % type(p))
        self._packages = packages

    @abstractmethod
    def _loadPackages(self):
        """ Load the installed packages in the repository. """
        pass
    
    # containsPackage('geoserver')
    # containsPackage('geoserver:2.5.1')
    # containsPackage(PackageConfig('geoserver-2.5.1/package.ini'))
    # containsPackage(PathPackage('packages/geoserver-2.5.1'))
    # containsPackage({'name':'geoserver'})
    # containsPackage({'name':'geoserver', 'version':'2.5.1'})
    def containsPackage(self, package):
        """ Determine if the repository contains the specified package. """
        matcher = createPackageMatcher(package)
        return any(matcher(p) for p in self.packages)

    # findPackages('geoserver')
    # findPackages('geoserver:2.5.1')
    # findPackages(PackageConfig('geoserver-2.5.1/package.ini'))
    # findPackages(Package(PackageConfig('geoserver-2.5.1/package.ini')))
    def findPackages(self, package):
        """ Find the installed packages (if any) matching the package pattern. """
        # Convert the package pattern to a package.
        matcher = createPackageMatcher(package)
        return [p for p in self.packages if matcher(p)]
    
    # findPackage('foo')
    # findPackage('foo:1.0')
    # findPackage(... etc ...)
    def findPackage(self, package):
        """ Find the installed package (if any) matching the package pattern. """
        matches = self.findPackages(package)
        if len(matches) == 0:
            foundPackage = None
        elif len(matches) == 1:
            foundPackage = matches[0]
        # Multiple matches, so return the package with the maximum version.
        else:
            foundPackage = findPackageWithMaximumVersion(matches)
        return foundPackage

    # installPackage(PathPackage('installer/geoserver-2.5.1'))
    # installPackage(CompressedPackage('installer/geoserver-2.5.1.zip'))
    def installPackage(self, package):
        """ Install the package within the repository. Does not install dependencies. 
            Returns True if the package was installed, False otherwise. """
        if package is None:
            raise ValueError("Cannot install package: no package specified.")
        if not isInstanceOf(package, Package):
            raise TypeError("Cannot install package: unsupported package type: %s." % type(package))
        
        installedPackage = False
        # Install the package if not already installed.
        if not self.containsPackage(package):
            # Install the package.
            print 'Installing package %s ...' % package
            if self._installPackage(package):
                installedPackage = True
            # Refresh the repository so that packages are reloaded.
            self.refresh()
        return installedPackage
    
    @abstractmethod
    def _installPackage(self, package):
        pass

    # uninstallPackage(geoserver)         -> uninstalls the specified package object
    # uninstallPackage('geoserver')       -> uninstalls all 'geoserver' packages
    # uninstallPackage('geoserver:2.5.1') -> uninstalls the geoserver:2.5.1 package
    def uninstallPackage(self, package):
        """ Uninstall the packages (if any) matching the package pattern. Does not uninstall any dependencies. 
            Returns the collection of packages that were uninstalled. """
        if package is None:
            raise ValueError("No package specified.")
        uninstalledPackages = []
        # Find the packages to uninstall.
        matcher = createPackageMatcher(package)
        matches = [p for p in self.packages if matcher(p)]
        # Uninstall each matching package.
        for p in matches:
            print 'Uninstalling package %s ...' % p
            if self._uninstallPackage(p):
                uninstalledPackages.append(p)
        # Refresh the repository so that packages are reloaded.
        self.refresh()
        return uninstalledPackages

    @abstractmethod
    def _uninstallPackage(self, package):
        pass

    def replacePackage(self, package):
        """ Replace the installed package with the new package (e.g. for snapshots).
            Returns True if the package was replaced; False otherwise. """
        if package is None:
            raise ValueError("Cannot replace package: no package specified")
        if not isInstanceOf(package, Package):
            raise TypeError("Cannot replace package: unsupported package type: %s." % type(package))
        if package.name is None:
            raise ValueError("Cannot replace package: no package name specified.")
        if package.version is None:
            raise ValueError("Cannot replace package: no package version specified.")
        replacedPackages = False
        # Find the installed package (if any) matching the replacement package.
        packageToReplace = self.findPackage(package)
        # If there's a matching installed package, then uninstall it and install the new package.
        if packageToReplace is not None:
            print 'Replacing package %s ...' % packageToReplace
            if self._uninstallPackage(packageToReplace) and self._installPackage(package):
                replacedPackages = True
        # Refresh the repository so that packages are reloaded.
        self.refresh()
        return replacedPackages

    def createReadOnly(self):
        """ Create a new, read-only version of this repository. """
        return ReadOnlyRepository(self)
    
    @classmethod
    def createEmpty(cls):
        """ Create a new, empty repository. Returns an in-memory repository. """
        return PackagesRepository(packages=[])
    
    @classmethod
    def createFrom(cls, value):
        """ 
        Create a package repository from a value. Supported values include:
        - None -- returns None
        - Package -- returns a read-only repository representing the specified package.
        - [Package] -- returns a read-only repository representing the specified packages.
        - PackageRepository -- returns the repository
        - [PackageRepository] -- returns a repository bundle representing the specified repositories.
        - path to archive -- returns a repository representing the archive
        - path to directory -- returns a repository representing the directory.
        """
        if value is None:
            return None
        if isInstanceOf(value, Package):
            return PackagesRepository(packages=[value])
        if isInstanceOf(value, PackageRepository):
            return value
        if isinstance(value, StringTypes):
            import zipfile
            if zipfile.is_zipfile(value):
                return CompressedRepository(zipfilePath=value)
            import os
            if os.path.isdir(value):
                return PathRepository(path=value)
            raise ValueError(
                "Cannot create package repository: value '%s' does not represent path to an archive or directory.")
        if isCollectionOf(value,Package):
            return PackagesRepository(packages=value)
        if isCollectionOf(value,PackageRepository):
            return RepositoryBundle(value)
        raise TypeError("Cannot create package repository: value has unsupported type %s." % type(value))


def createPackageMatcher(package):
    # Convert that package pattern (it may be a string, e.g. 'foo:1.0') to a package object.
    from packages import PackageIdentifier
    packageID = PackageIdentifier.createFrom(package)
    package = Package(name=packageID.name, version=packageID.version)
    def matcher(p):
        from packages import isMatchingPackageName, isMatchingPackageVersion
        result = False
        # Check that package names match.
        if isMatchingPackageName(p, package):
            result = package.version is None or isMatchingPackageVersion(p, package)
        return result
    return matcher


class DelegatingPackageRepository(PackageRepository):

    """ A package repository that proxies all operations to a delegate. """

    __metaclass__ = ABCMeta
    
    def __init__(self, delegate):
        super(DelegatingPackageRepository, self).__init__()
        if delegate is None:
            raise ValueError("Cannot create repository: no delegate repository specified.")
        if not isInstanceOf(delegate, PackageRepository):
            raise TypeError("Cannot create repository: delegate has incorrect type %s." % type(delegate))
        self.delegate = delegate

    # @Override
    def refresh(self):
        self.delegate.refresh()

    @PackageRepository.packages.getter
    def packages(self):
        return self.delegate.packages
    
    # @Override
    def containsPackage(self, package):
        return self.delegate.containsPackage(package)

    # @Override
    def findPackages(self, package):
        return self.delegate.findPackages(package)

    # @Override
    def findPackage(self, package):
        return self.delegate.findPackage(package)
    
    # @Override
    def installPackage(self, package):
        return self.delegate.installPackage(package)

    # @Override
    def uninstallPackage(self, package):
        return self.delegate.uninstallPackage(package)

    # @Override
    def packageURL(self, package):
        return self.delegate.packageURL(package)

    # Abstract methods ... should never be called directly (e.g. should call installPackage() rather
    # than _installPackage()), but an implementation is required.
    
    def _installPackage(self, package):
        return self.delegate._installPackage(package)
    
    def _uninstallPackage(self, package):
        return self.delegate._uninstallPackage(package)
    
    def _loadPackages(self):
        return self.delegate._loadPackages()
    
    
class ReadOnlyRepositoryMixin(object):

    """ Mixin class for read-only repository operations. """

    # @Override
    def _installPackage(self, package):
        raise ReadOnlyRepositoryError("Cannot install package '%s': repository is read-only." % package)

    # @Override
    def _uninstallPackage(self, package):
        raise ReadOnlyRepositoryError("Cannot uninstall package '%s': repository is read-only." % package)

    # Convenience methods so that errors are raised when the methods are called, instead
    # raising errors when the _installPackage() or _uninstallPackage() methods are called.
    # Makes error reporting and logging cleaner.
    
    # @Override
    def installPackage(self, package):
        raise ReadOnlyRepositoryError("Cannot install package '%s': repository is read-only." % package)

    # @Override
    def uninstallPackage(self, package):
        raise ReadOnlyRepositoryError("Cannot uninstall package '%s': repository is read-only." % package)

    # @Override
    def replacePackage(self, package):
        raise ReadOnlyRepositoryError("Cannot replace package '%s': repository is read-only." % package)


class ReadOnlyRepository(ReadOnlyRepositoryMixin,DelegatingPackageRepository):

    """ Wraps another repository for read-only operations. """

    def __init__(self, delegate):
        super(ReadOnlyRepository, self).__init__(delegate)


class PathRepository(PackageRepository):

    """ Operations on a local repository, e.g. all packages stored under c:\mstar\packages. """
    
    def __init__(self, path):
        super(PathRepository, self).__init__()
        # Check that a path was specified.
        if path is None:
            raise ValueError('Cannot create repository: no path specified.')
        if not isinstance(path, StringTypes):
            raise TypeError('Cannot create path repository: path has incorrect type %s.' % type(path))
        # If the path exists (it may not yet for write repositories) then make sure it is a directory.
        if os.path.exists(path) and not os.path.isdir(path):
            raise ValueError('Cannot create repository: path "%s" is not a directory' % path)
        self._path = path
        # print "## created PathRepository(id=%s, path=%s)" % (self.repositoryID, self.path)

    def __repr__(self):
        return 'PathRepository{path:"%s"}' % self.path
    
    @property
    def path(self):
        return self._path

    # @Override
    def _installPackage(self, package):
        # Install the package to the path, e.g. geoserver:2.5.1 would be stored at 'c:\mstar\packages\geoserver-2.5.1'.
        packagePath = self.__packagePath(package)
        package.installTo(packagePath)
        return True

    # @Override
    def _uninstallPackage(self, package):
        # Remove the package from the path, e.g. remove directory 'c:\mstar\packages\geoserver-2.5.1'.
        packagePath = self.__packagePath(package)
        print '  Removing package %s at %s ...' % (package, packagePath)
        FileOps.getFileOps().removeDir(packagePath)
        if os.path.exists(packagePath):
            raise RuntimeError("Failed to completely remove directory %s" % packagePath)
        return True

    # @Override
    def _loadPackages(self):
        packages = []
        # Load packages only if path exists (may not exist yet for write repositories).
        if os.path.exists(self.path):
            packages = self.__findPackagesStartingFrom(self.path)
        return packages

    def __findPackagesStartingFrom(self, path):
        packages = []
        # Check files until a package config is found.
        for f in os.listdir(path):
            if f == PackageConfig.filename():
                p = os.path.join(path, f)
                if not os.path.isdir(p):
                    # Create a package (if possible) from the path.
                    package = self.__createPackage(path)
                    if package is not None:
                        packages.append(package)
                    # No need to keep looking in this path.
                    return packages
        # No file found that is a package config, so
        # recursively check subdirectories.
        for f in os.listdir(path):
            p = os.path.join(path, f)
            if os.path.isdir(p):
                packages += self.__findPackagesStartingFrom(p)
        return packages

    def __createPackage(self, path):
        try:
            # Create the package from the directory.
            return PathPackage(path)
        except:
            # Got an error creating the package: ignore
            return None

    def __packagePath(self, package):
        # Create package path of form 'packages/geoserver/2.5.1', etc.
        return os.path.join(self.path, package.name, str(package.version))


class CompressedRepository(ReadOnlyRepositoryMixin,PackageRepository):

    """ Operations on a compressed repository, i.e. a zip file containing 'package.ini' 
        files, typically in a '/packages' directory. This is a read-only repository by
        default. """

    def __init__(self, zipfilePath):
        super(CompressedRepository, self).__init__()
        if zipfilePath is None:
            raise ValueError('Cannot create repository: no zipfile specified.')
        if not os.path.exists(zipfilePath) or not os.access(zipfilePath, os.F_OK):
            raise ValueError('Cannot create repository: zipfile "%s" is not accessible.' % zipfilePath)
        if not zipfile.is_zipfile(zipfilePath):
            raise ValueError('Cannot create repository: zipfile "%s" is invalid.' % zipfilePath)
        self._zipfilePath = zipfilePath

    def __repr__(self):
        return 'CompressedRepository{zipFilePath:"%s"}' % self.zipfilePath

    @property
    def zipfilePath(self):
        return self._zipfilePath

    # @Override
    def _loadPackages(self):
        zip = zipfile.ZipFile(self.zipfilePath, 'r')
        try:
            return self._getPackagesFromZipFile(zip)
        finally:
            if zip is not None: zip.close()

    def _getPackagesFromZipFile(self, zip):
        packages = []
        for item in zip.namelist():
            package = self._createPackageFromZipFileItem(zip, item)
            if package is not None:
                packages.append(package)
        return packages

    def _createPackageFromZipFileItem(self, zip, item):
        # Look for an item of the form '/**/package.ini'.
        if item.endswith(PackageConfig.filename()):
            # Get the prefix of the item. All members to be unpacked will
            # start with this prefix.
            prefix = item[:-len(PackageConfig.filename())]
            # XXX No URL available for package in a compressed repository ... ?
            return CompressedPackage(zipfile=self.zipfilePath, prefix=prefix)

class PackagesRepository(PackageRepository):

    """ A repository containing a fixed collection of packages. """

    def __init__(self, packages=[]):
        super(PackagesRepository, self).__init__()
        if packages is not None and not isCollectionOf(packages, Package):
            raise TypeError("Cannot create repository: expected list of packages.")
        self._loadablePackages = packages or []
        # print "## created PackagesRepository(id=%s, packages=%s)" % (self.repositoryID, self._loadablePackages)

    def __repr__(self):
        return "PackagesRepository{packages:%s}" % self._loadablePackages

    # @Override
    def _loadPackages(self):
        return self._loadablePackages

    # @Override
    def _installPackage(self, package):
        self._loadablePackages.append(package)
        return True

    # @Override
    def _uninstallPackage(self, package):
        self._loadablePackages.remove(package)
        return True


class RepositoryBundle(ReadOnlyRepositoryMixin, PackageRepository):
    
    """ A read-only repository containing other repositories, in preference order. """
    
    def __init__(self, repositories = []):
        super(RepositoryBundle, self).__init__()
        self._repositories = repositories
        # print "## created RepositoryBundle(id=%s, repositories=%s)" % (self.repositoryID, self.repositories)

    def __repr__(self):
        return "RepositoryBundle{repositories=%s}" % self.repositories

    @property
    def repositories(self):
        return self._repositories

    # @Override
    def _loadPackages(self):
        map = {}
        for repository in self.repositories:
            for package in repository.packages:
                key = package.id
                if key not in map:
                    map[key] = package
        return map.values()

    # @Override
    def installPackage(self, package):
        raise NotImplementedError("Cannot install package '%s': repository is read-only" % package)

    # @Override
    def uninstallPackage(self, package):
        raise NotImplementedError("Cannot uninstall package '%s': repository is read-only" % package)

    # @Override
    def replacePackage(self, package):
        raise NotImplementedError("Cannot replace package '%s': repository is read-only" % package)

def createRepositoryFrom(value):
    """ Create a repository from a value. See PackageRepository.createFrom.__doctype__. """
    return PackageRepository.createFrom(value)
