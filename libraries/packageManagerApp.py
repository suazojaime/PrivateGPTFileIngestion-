import sys

from packageManager import *
from packageRepositories import *
from packageChanges import *


class PackageManagerApp(object):

    def __init__(self, options):
        self.options = options
        self._repository = None
        self._packageManager = None
        self._supportedTargets = None
        self._mstar = None
        self._installDir = None
        
    @property
    def mstar(self):
        if self._mstar is None:
            from mstarInstall import MStarInstall
            self._mstar = MStarInstall.getInstance(self.installDir)
        return self._mstar
    
    @property
    def installDir(self):
        def loadInstallDir():
            # Use the specified installDir, or fallback to default install dir.
            if self.options.installDir is not None:
                return self.options.installDir
            import mstarpaths
            return mstarpaths.interpretPath("{MSTAR_INSTALL}")
            
        if self._installDir is None:
            self._installDir = loadInstallDir()
        return self._installDir
    
    @property
    def packagesSource(self):
        if self.options.packagesSource is not None:
            return self.options.packagesSource
        return self.mstar.packagesDir

    @property
    def repository(self):
        if self._repository is None:
            if self.packagesSource is None:
                raise RuntimeError("No packages source specified.")
            self._repository = createRepositoryFrom(self.packagesSource)
        return self._repository

    @property
    def availablePackagesSource(self):
        return self.options.availablePackagesSource

    @property
    def installedPackagesSource(self):
        # Try '--installed-packages-source' first, with fallback to the default install directory.
        if self.options.installedPackagesSource is not None:
            return self.options.installedPackagesSource
        return self.mstar.packagesDir

    @property
    def availablePackagesRepository(self):
        # Use alternative source, if specified.
        if self.availablePackagesSource is not None:
            return ReadOnlyRepository(createRepositoryFrom(self.availablePackagesSource))
        # Otherwise use the default available packages repository.
        return self.mstar.availablePackagesRepository

    @property
    def installedPackagesRepository(self):
        # Use the alternative source, if specified.
        if self.installedPackagesSource is not None:
            return createRepositoryFrom(self.installedPackagesSource)
        # Otherwise use the default installed packages repository.
        return self.mstar.installedPackagesRepository

    @property
    def packageManager(self):
        if self._packageManager is None:
            self._packageManager = PackageManager(available=self.availablePackagesRepository,
                                                  installed=self.installedPackagesRepository,
                                                  supportedTargets=self.supportedTargets)
        return self._packageManager
    
    @property
    def supportedTargets(self):
        if self._supportedTargets is None:
            self._supportedTargets = self._loadSupportedTargets()
        return self._supportedTargets

    def _loadSupportedTargets(self):
        from mstarInstall import MStarInstall
        return MStarInstall.getInstance(self.installDir).supportedTargets

    def listPackages(self):
        for package in self.repository.packages:
            print '%s:%s' % (package.name, package.version)

    def listPackageUpdates(self):
        changes = [change for change in self.packageManager.changes() if change.action != PackageChange.SKIP]
        print 'There are %s package update(s) available' % len(changes)
        for change in changes:
            if change.action == PackageChange.INSTALL:
                print 'install: %s (%s)' % (change.available, change.reason)
            elif change.action == PackageChange.UPGRADE:
                print 'upgrade: %s (%s)' % (change.available, change.reason)

    def installPackage(self, package):
        self.packageManager.install(package)

    def uninstallPackage(self, package):
        # TODO there may be a build that depends on the package!
        self.packageManager.uninstall(package)

    def updatePackages(self):
        changes = [change for change in self.packageManager.changes() if change.action != PackageChange.SKIP]
        print 'There are %s package update(s) available.' % len(changes)
        for change in changes:
            self.packageManager.install(change.available)

    def showPackageInfo(self, packageID):
        package = self.repository.findPackage(packageID)
        if package is None:
            print "ERROR: Cannot find package '%s'." % packageID
            return

        print "Package %s:" % packageID
        print "  Name         : %s" % package.name
        print "  Version      : %s" % package.version
        print "  Description  : %s" % package.description
        print "  Dependencies :"
        for dependency in package.dependencies:
            print "    %s" % dependency
        print "  Symbolic Link: %s" % package.symlink
        print "  Timestamp    : %s" % package.timestamp

    def run(self):
        if self.options.listPackages:
            self.listPackages()
        elif self.options.listPackageUpdates:
            self.listPackageUpdates()
        elif self.options.installPackage is not None:
            self.installPackage(self.options.installPackage)
        elif self.options.uninstallPackage is not None:
            self.uninstallPackage(self.options.uninstallPackage)
        elif self.options.updatePackages:
            self.updatePackages()
        elif self.options.showPackageInfo is not None:
            self.showPackageInfo(self.options.showPackageInfo)
        else:
            self.options.usage()
            
def run(args=[]):
    # Load the M* configuration.
    import mstarpaths
    mstarpaths.loadMineStarConfig()
    # Run the package manager app.
    PackageManagerApp(createOptions(args)).run()
    
def createOptions(args=[]):
    parser = createArgumentParser()
    options = parser.parse_args(args)
    options.usage = parser.print_help
    return options

def createArgumentParser():
    import mstarpaths
    defaultInstallDir = mstarpaths.interpretPath("{MSTAR_INSTALL}")
    from argparse import ArgumentParser
    parser = ArgumentParser(description='Minestar Package Manager')
    parser.add_argument('--list', dest='listPackages', action='store_true',
                        help='List the packages.')
    parser.add_argument('--info', dest='showPackageInfo', metavar="<packageID>",
                        help='Show information about a package')
    parser.add_argument('--updates', dest='listPackageUpdates', action='store_true',
                        help='Show package updates.')
    parser.add_argument('--install', dest='installPackage', metavar="<packageId>",
                        help='Install a package (from available sources).')
    parser.add_argument('--uninstall', dest='uninstallPackage', metavar="<packageId>",
                        help='Uninstall a package (from installed packages).')
    parser.add_argument('--update', dest='updatePackages', action='store_true',
                        help='Update installed packages.')
    parser.add_argument('--install-dir', dest='installDir', metavar="<directory>", default=defaultInstallDir,
                        help='The CAT MineStar install directory (defaults to %s).' % defaultInstallDir)
    parser.add_argument('--packages-source', dest='packagesSource', metavar="<packages source>",
                        help='The source for packages (may be directory or zip file) (defaults to %s).' % defaultInstallDir)
    parser.add_argument('--available-packages-source', dest='availablePackagesSource', metavar='<packages source>',
                        help='The source for available packages. Defaults to [empty].')
    parser.add_argument('--installed-packages-source', dest='installedPackagesSource', metavar='<packages source>',
                        help='The source for installed packages (defaults to %s).' % defaultInstallDir)
    parser.add_argument('--parameters-file', dest='parametersFile', metavar='<file>',
                        help='Path to file containing parameters.')
    return parser

def processArgs(args=[]):
    processedArgs = []
    for i,arg in enumerate(args):
        # If the argument indicates that a parameters file, then load the
        # arguments from that parameters file.
        if arg == '--parameters-file':
            file = args[i+1]
            with open(file, 'rt') as f:
                processedArgs += f.read().split()
        else:
            processedArgs.append(arg)
    return processedArgs

if __name__ == '__main__':
    run(processArgs(sys.argv[1:]))
