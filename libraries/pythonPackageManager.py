import os


def mstarrunDebug(msg):
    if 'MSTARRUN_DEBUG' in os.environ:
        print "debug: %s" % msg


class PythonPackageManager:

    """ Class for managing python packages. """

    def __init__(self, dir):
        self._dir = dir
        self._installedPackages = None

    @property
    def packagesDir(self):
        # This must match packages directory name in runtime/pom.xml file.
        return os.path.join(self._dir, '.packages')

    @property
    def installedPackages(self):
        """Get the list of installed packages."""
        if self._installedPackages is None:
            self._installedPackages = self._readInstalledPackages()
        return self._installedPackages

    def isInstalled(self, zipfile):
        """Determine if a package / zipfile is installed."""
        package = self._zipfileToPackageName(zipfile)
        return package in self.installedPackages

    def _zipfileToPackageName(self, zipfile):
        """Convert zipfile to a package name, e.g. '/x/y/foo.zip' -> 'foo' """
        packageName = os.path.basename(zipfile)
        if packageName.endswith('.zip'):
            packageName = packageName[:-4]
        return packageName

    def _setInstalled(self, package, installed=True):
        if installed:
            if not package in self.installedPackages:
                self.installedPackages.append(package)
                self._writeInstalledPackages()
        else:
            if package in self.installedPackages:
                del self.installedPackages[package]
                self._writeInstalledPackages()

    def installPackages(self):
        """Install packages that match the system and architecture."""
        (system, architecture) = _getPythonPlatform()
        platform = (system + "-" + architecture).lower()
        for zipfile in self.findPackages():
            if self.matchesPlatform(zipfile, platform):
                self.installPackage(zipfile)

    def findPackages(self):
        packages = []
        if os.path.exists(self.packagesDir):
            for file in os.listdir(self.packagesDir):
                if file.endswith('.zip'):
                    packages.append(os.path.join(self.packagesDir, file))
        return packages

    supportedPlatforms = ['windows-x86', 'windows-x64', 'linux-x86', 'linux-x64']

    # Compatible platforms for backwards compatibility.
    compatiblePlatforms = {
        # old platform   : new platform
        'windows-amd64'  : 'windows-x64',
        'windows-x86_64' : 'windows-x64',
        'linux-amd64'    : 'linux-x64',
        'linux-x86_64'   : 'linux-x64',
    }

    def matchesPlatform(self, filename, platform):
        f = os.path.basename(filename)

        # Remove the trailing '.zip' part of the file name, if present.
        if f.endswith('.zip'):
            f = f[:-4]

        def findPlatform(_filename, _platforms):
            for _platform in _platforms:
                if _filename.endswith(_platform):
                    return _platform
            return None

        # Does the filename have supported platform suffix?
        p = findPlatform(f, self.supportedPlatforms)
        if p is not None:
            return p == platform

        # Does the filename have compatible platform suffix?
        p = findPlatform(f, self.compatiblePlatforms.keys())
        if p is not None:
            return self.compatiblePlatforms[p] == platform

        # The file name has no platform suffix: matched.
        return True

    def installPackage(self, zipfile):
        """Install package represented as a zip file."""
        package = self._zipfileToPackageName(zipfile)
        if not self.isInstalled(package):
            self._installPackage(package, zipfile)
            self._setInstalled(package, True)

    def _installPackage(self, package, zipfile):
        # Verify that package is specified.
        if package is None:
            raise ValueError("No 'package' specified for installing package.")

        # Verify that zipfile is specified.
        if zipfile is None:
            raise ValueError("No 'zipfile' specified for installing package.")
        if not os.path.exists(zipfile):
            raise Exception("Cannot install package '%s': zipfile '%s' does not exist." % (package, zipfile))

        mstarrunDebug("Installing python package %s ..." % zipfile)

        from zipfile import ZipFile
        zf = None
        try:
            # Unzip the file into the directory.
            zf = ZipFile(zipfile, "r")
            zf.extractall(self._dir)
        except IOError as e:
            print "%s: I/O error: %s" % (zipfile, str(e))
        finally:
            # Close the zipfile.
            if zf is not None:
                zf.close()

    def _readInstalledPackages(self):
        installedPackages = []
        propertiesFile = self.installedPackagesFile
        if os.path.exists(propertiesFile):
            with open(propertiesFile, 'rt') as f:
                for line in f.readlines():
                    line = line.strip()
                    if len(line) > 0 and not line.startswith("#"):
                        installedPackages.append(line)
        return installedPackages

    def _writeInstalledPackages(self):
        with open(self.installedPackagesFile, 'wt') as f:
            for package in self.installedPackages:
                f.write(package + '\n')

    @property
    def installedPackagesFile(self):
        return os.path.join(self.packagesDir, 'installed-packages.properties')


def _getPythonPlatform():
    import platform
    system = platform.system()
    # 64-bit architectures end in '64', e.g. 'x64', 'x86-64', 'amd64', etc.
    architecture = 'x64' if platform.machine().endswith('64') else 'x86'
    return (system, architecture)
