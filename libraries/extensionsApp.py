import os
import sys
import minestar
import mstarext
import mstarpaths


def writeMessage(msg):
    sys.stdout.write(msg)
    sys.stdout.flush()


def copyFile(src, dst):
    # If the destination file is a directory, then append the basename of the source file.
    # e.g. copyFile('/x/y/z/foo.txt', '/a/b/c') => copyFile('/x/y/z/foo.txt', '/a/b/c/foo.txt')
    if os.path.exists(dst) and os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    import shutil
    shutil.copyfile(src, dst)


def removeFile(path):
    if os.path.exists(path) and os.path.isfile(path):
        os.remove(path)


def asBoolean(v):
    """Converts the value to a boolean, or raises an error."""
    if v is None or v is False or v == 'false':
        return False
    if v is True or v == 'true':
        return True
    raise TypeError("Cannot convert value %s of type %s to a boolean value" % (v, type(v)))


def isZippedExtension(extension):
    return isinstance(extension, mstarext.ZippedExtension)


def extensionIDs(extensions):
    """Get a collection of extension IDs from a collection of extensions."""
    return [x.id for x in extensions]


class ApplicationError(Exception):

    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return "ERROR: %s" % self.message


class ApplicationWarning(Exception):

    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return "WARNING: %s" % self.message


class Extensions:

    def __init__(self):
        self._extensions = []

    def append(self, extension):
        if not isinstance(extension, mstarext.Extension):
            raise TypeError("Item is not of type %s" % mstarext.Extension)
        if extension.id not in extensionIDs(self._extensions):
            self._extensions.append(extension)

    def remove(self, extension):
        if not isinstance(extension, mstarext.Extension):
            raise TypeError("Item is not of type %s" % mstarext.Extension)
        if extension is not None and extension.id in extensionIDs(self._extensions):
            self._extensions.remove(extension)

    def extend(self, extensions):
        for extension in extensions:
            self.append(extension)

    def __contains__(self, extension):
        if not isinstance(extension, mstarext.Extension):
            raise TypeError("Item is not of type %s" % mstarext.Extension)
        return extension.id in extensionIDs(self._extensions)

    def __iter__(self):
        return self._extensions.__iter__()

    def __len__(self):
        return len(self._extensions)


class Config:

    def __init__(self):
        self._subsystems = None

    def isEnabled(self, extension):
        """Determines if an extension is enabled in the configuration."""
        return extension.root in self._getSubsystems()

    def enabled(self):
        return self._getSubsystems()

    def enable(self, extension):
        """Enable an extension in the configuration."""
        writeMessage("Enabling extension '%s' ... " % extension.id)
        try:
            subsystems = self._getSubsystems()
            subsystems.append(extension.root)
            self._setSubsystems(subsystems)
        except:
            writeMessage("failed\n")
            raise
        writeMessage("ok\n")

    def disable(self, extension):
        """Disable an extension in the configuration."""
        writeMessage("Disabling extension '%s' ... " % extension.id)
        try:
            subsystems = self._getSubsystems()
            subsystems.remove(extension.root)
            self._setSubsystems(subsystems)
        except:
            writeMessage("failed\n")
            raise
        writeMessage("ok\n")

    def _getSubsystems(self):
        if self._subsystems is None:
            self._subsystems = self._loadSubsystems()
        return self._subsystems

    def _setSubsystems(self, subsystems):
        self._storeSubsystems(subsystems)
        self._subsystems = None

    def _loadSubsystems(self):
        import mstaroverrides
        (overridesDict, overridesFile) = mstaroverrides.loadOverrides()
        versionOverrides = overridesDict.get("/Versions.properties", {})
        subSystemsStr = versionOverrides.get("_SUBSYSTEMS", '')
        return subSystemsStr.split(',')

    def _storeSubsystems(self, subsystems):
        subsystems = subsystems or []
        import mstaroverrides
        (overridesDict, overridesFile) = mstaroverrides.loadOverrides()
        versionOverrides = overridesDict.get("/Versions.properties", {})
        versionOverrides["_SUBSYSTEMS"] = ",".join(subsystems)
        mstaroverrides.saveOverridesToFile(overridesFile, mstaroverrides.overridesDictToPairs(overridesDict))


# knownExtensions:
#   - unzipped extensions in ${MSTAR_HOME}/ext
#   - zipped extensions in ${MSTAR_UPDATES}
#   - zipped extensions in ${MSTAR_INSTALL}/packages
#
# An extension is enabled iff:
#    extension.root in subsystems or (extension in unzipped extensions and extension.compulsory)
#
# installed extension : [x for x in knownExtensions and x.enabled]
# available extensions: [x for x in knownExtensions and not x.enabled]
#
# "install an extension" means:
#  - if the extension is available:
#     - copy the extension zip to ${MSTAR_UPDATES} (if it is zipped)
#     - enable the extension
#
# "remove an extension" means:
#  - if the extension is installed and the extension is not compulsory:
#     - disable the extension
#
class ExtensionsApp(object):

    def __init__(self, config=None):
        self._config = config
        self._extensions = None
        self._unzippedExtensions = None
        self._zippedExtensions = None
        self.config = Config()

    def listInstalledExtensions(self):
        """ List the installed extensions."""
        extensions = self.installedExtensions
        self._listExtensions(extensions)

    def listAvailableExtensions(self):
        extensions = self.availableExtensions
        self._listExtensions(extensions)

    def _listExtensions(self, extensions=[]):
        if extensions:
            def format(x, y):
                print "%s  %s" % (x.ljust(40), y)
            format("ID", "NAME")
            format("==", "====")
            for extension in extensions:
                format(extension.id, extension.name)

    def showStatus(self, extensionId):
        """Show the install status of the extension."""
        # Find the extension to install.
        extension = self.findExtension(extensionId)
        if extension is None:
            raise ApplicationError("Cannot find extension '%s'" % extensionId)
        status = "installed" if self.isEnabledExtension(extension) else "not installed"
        print "Extension '%s' is %s." % (extension.id, status)

    def installExtension(self, extensionId, overwrite=False):

        def loadExtension():
            """Load an extension zip file."""
            # Check if installing from a zip file.
            writeMessage("Loading extension from file '%s' ..." % extensionId)
            try:
                extension = mstarext.ZippedExtension(extensionId)
            except:
                writeMessage("failed\n")
                raise
            writeMessage("ok\n")
            # Check that extension was loaded.
            if extension is None:
                raise ApplicationError("Cannot find extension '%s'" % extensionId)
            return extension

        def findExtension():
            """Find an extension matching the extension id."""
            # Find an available extension (if any) in the 'extensions' package.
            availableExtensions = self._findMStarPackagesZippedExtensions()
            availableExtension = mstarext.getExtensionWithId(availableExtensions, extensionId)

            # Find a user-supplied extension (if any) in the updates directory.
            suppliedExtensions = self._findMStarUpdatesZippedExtensions()
            suppliedExtension = mstarext.getExtensionWithId(suppliedExtensions, extensionId)

            # Check that an extension was found.
            if not availableExtension and not suppliedExtension:
                raise ApplicationError("Cannot find extension '%s'" % extensionId)

            if availableExtension and not suppliedExtension:
                return availableExtension
            elif suppliedExtension and not availableExtension:
                return suppliedExtension
            elif mstarext.isLaterExtension(availableExtension, suppliedExtension):
                return availableExtension
            return suppliedExtension

        # Load or discover the extension.
        extension = None
        if extensionId.endswith(".zip") and os.path.exists(extensionId):
            extension = loadExtension()
        else:
            extension = findExtension()

        # Not handling patches / service packs yet (not sure how to update config).
        writeMessage("Validating extension '%s' ... " % extension.id)
        try:
            if isinstance(extension, mstarext.ZippedExtension):
                if extension.isPatch():
                    raise ApplicationError("Cannot install: extension '%s' is a patch" % extension.id)
                if extension.isServicePack():
                    raise ApplicationError("Cannot install: extension '%s' is a service pack" % extension.id)
        except:
            writeMessage("failed\n")
            raise
        writeMessage("ok\n")

        # Check if the extension is already installed. Can overwrite an installed zipped extension.
        if self.isInstalledExtension(extension):
            if not overwrite:
                raise ApplicationWarning("Extension '%s' is already installed (use '--force' option to re-install)." % extension.id)
            if not isZippedExtension(extension):
                raise ApplicationWarning("Extension '%s' is already installed and cannot be re-installed." % extension.id)

        # Install the extension to ${MSTAR_UPDATES} directory, if necessary.
        if isZippedExtension(extension):
            installing = True

            # Check if zipped extension file already exists.
            existing = self._findInstalledZippedExtension(extension)
            if existing:
                # Don't replace existing extension if not overwriting.
                if not overwrite:
                    installing = False
                # Don't replace existing extension if it is the same file as the required extension.
                elif os.path.abspath(extension.filename) == os.path.abspath(existing.filename):
                    installing = False
                # Remove existing extension (overwriting, and not same file as requested extension).
                else:
                    self._removeZippedExtension(existing)

            # Install the zipped extension file.
            if installing:
                self._installZippedExtension(extension)

        # Update the M* configuration, if required.
        if not self.config.isEnabled(extension):
            self.config.enable(extension)

    def _installZippedExtension(self, extension):
        writeMessage("Installing extension '%s' to '%s' ... " % (extension.id, self.getMStarZippedExtensionsDir()))
        try:
            copyFile(extension.filename, self.getMStarZippedExtensionsDir())
        except:
            writeMessage("failed\n")
            raise
        writeMessage("ok\n")

    def _removeZippedExtension(self, extension):
        if not os.path.exists(extension.filename):
            return
        writeMessage("Removing extension '%s' from '%s' ..." % (extension.id, os.path.dirname(extension.filename)))
        try:
            removeFile(extension.filename)
        except:
            writeMessage("failed\n")
            raise
        writeMessage("ok\n")

    def _findInstalledZippedExtension(self, extension):
        for installed in self._findMStarUpdatesZippedExtensions():
            if installed.id == extension.id:
                return installed
        return None

    def _canInstallZippedExtensionFile(self, extension):
        return not any(x for x in self._findMStarUpdatesZippedExtensions() if x.id == extension.id)

    def _canRemoveZippedExtensionFile(self, extension):
        return any(x for x in self._findMStarUpdatesZippedExtensions() if x.id == extension.id)

    def removeExtension(self, extensionId, force=False):
        # Find the requested extension.
        extension = self.findExtension(extensionId)
        if extension is None:
            raise ApplicationError("Cannot find extension '%s'" % extensionId)

        # Check if the extension is installed.
        if not self.isInstalledExtension(extension) and not force:
            raise ApplicationWarning("Extension '%s' is not installed (use '--force' option for cleanup)." % extension.id)

        # Check not removing a compulsory unzipped extension.
        if extension.compulsory and extension in self.unzippedExtensions:
            raise ApplicationError("Can not remove compulsory extension '%s' " % extension.id)

        # Disable extension.
        if self.config.isEnabled(extension):
            self.config.disable(extension)

        # Remove the zipped extension from ${MSTAR_UPDATES}, if required.
        if isZippedExtension(extension):
            existing = self._findInstalledZippedExtension(extension)
            if existing:
                self._removeZippedExtension(existing)

    def isEnabledExtension(self, extension):
        # Configured extensions are enabled.
        if self.config.isEnabled(extension):
            return True
        # Compulsory unzipped extensions are enabled.
        if extension.compulsory and extension in self.unzippedExtensions:
            return True
        return False

    def isInstalledExtension(self, extension):
        return extension.id in [x.id for x in self.installedExtensions]

    def isAvailableExtension(self, extension):
        return extension.id in [x.id for x in self.availableExtensions]

    def isZippedExtension(self, extension):
        return extension in self.zippedExtensions

    def isUnzippedExtension(self, extension):
        return extension in self.unzippedExtensions

    def findExtension(self, extensionId):
        for extension in self.extensions:
            if extensionId == extension.id:
                return extension
        return None

    def checkExtensions(self):
        # The installed extensions are in ${MSTAR_HOME}/ext and ${MSTAR_UPDATES}.
        unzippedExtensions = self._loadUnzippedExtensions()
        zippedExtensions = self._loadZippedExtensions(fromUpdates=True, fromPackages=False)

        for configuredExtensionRoot in self.config.enabled():
            def findConfiguredExtension():
                for x in self.extensions:
                    if x.root == configuredExtensionRoot:
                        return x
                return None

            # Verify that the extension exists.
            extension = findConfiguredExtension()
            if extension is None:
                print "WARNING: Extension with root '%s' is configured but is unknown." % configuredExtensionRoot
                continue

            # Verify that the extension is installed.
            if extension not in unzippedExtensions and extension not in zippedExtensions:
                print "WARNING: Extension '%s' (with root '%s') is configured but is not installed." % (extension.id, extension.root)
                continue

        # Check for extensions that have an update available.
        updates = mstarext.getZippedExtensionUpdates(None, zippedExtensions)
        if updates:
            size = len(updates)
            params = ("is", 1, "update") if size == 1 else ("are", len(updates), "updates")
            print "There %s %s extension %s available:" % params
            for id in updates:
                update = updates[id]
                print "  Extension: %s" % id
                print "       From: %s" % update.source.filename
                print "       To  : %s" % update.target.filename
            print "Run the following command: mstarrun extensions --update"

    def updateExtensions(self):
        zippedExtensions = self._loadZippedExtensions(fromUpdates=True, fromPackages=False)
        updates = mstarext.getZippedExtensionUpdates(None, zippedExtensions)
        for id in updates:
            update = updates[id]
            writeMessage("Updating extension %s ...\n" % id)
            writeMessage("  Removing file '%s' ..." % update.source.filename)
            try:
                removeFile(update.source.filename)
                writeMessage("ok\n")
            except:
                writeMessage("failed\n")
                raise
            writeMessage("  Copying file '%s' ..." % update.target.filename)
            try:
                copyFile(update.target.filename, self.getMStarZippedExtensionsDir())
                writeMessage("ok")
            except:
                writeMessage("failed")
                raise
    def showExtensionInfo(self, expression=None):
        for extension in self.getExtensions(expression):
            print "Extension: %s" % extension.id
            if hasattr(extension, 'version'):
                print "  Version   : %s" % extension.version
            print "  Name      : %s" % extension.name
            print "  Part      : %s" % extension.part
            print "  Root      : %s" % extension.root
            print "  Compulsory: %s" % extension.compulsory
            print "  Depends   : %s" % extension.depends
            print "  Invisible : %s" % extension.invisible
            if hasattr(extension, 'ufsDir'):
                print "  Location  : %s" % extension.ufsDir
            elif hasattr(extension, 'filename'):
                print "  Location  : %s" % extension.filename
            if hasattr(extension, 'digest'):
                print "  Digest    : %s" % extension.digest
            print "  Enabled   : %s" % self.isEnabledExtension(extension)

    def getExtensions(self, expression=None):
        """Get all extensions that match the expression."""
        return [x for x in self.extensions if self.matchExtension(x, expression)]

    def getAvailableExtensions(self, expression=None):
        """Get all available extensions that match the expression."""
        return [x for x in self.availableExtensions if self.matchExtension(x, expression)]

    def matchExtension(self, extension, expression=None):
        """Determines if the extension matches the expression."""
        if not expression:
            matched = True
        elif 'id' in expression:
            matched = extension.id == expression['id']
        elif 'part' in expression:
            matched = extension.part == expression['part']
        elif 'name' in expression:
            matched = extension.name == expression['name']
        elif 'root' in expression:
            matched = extension.root == expression['root']
        elif 'compulsory' in expression:
            matched = extension.compulsory == asBoolean(expression['compulsory'])
        elif 'invisible' in expression:
            matched = extension.invisible == asBoolean(expression['invisible'])
        elif 'enabled' in expression:
            matched = self.isEnabledExtension(extension) == asBoolean(expression['enabled'])
        elif 'and' in expression:
            matched = all(self.matchExtension(extension, x) for x in expression['and'])
        elif 'or' in expression:
            matched = any(self.matchExtension(extension, x) for x in expression['or'])
        elif 'not' in expression:
            matched = not self.matchExtension(extension, expression['not'])
        elif 'true' in expression:
            matched = True
        elif 'false' in expression:
            matched = False
        else:
            raise ApplicationError("Cannot match expression %s" % expression)
        return matched

    @property
    def extensions(self):
        if self._extensions is None:
            self._extensions = self._loadExtensions()
        return self._extensions

    @property
    def installedExtensions(self):
        return [x for x in self.extensions if self.isEnabledExtension(x)]

    @property
    def availableExtensions(self):
        return [x for x in self.extensions if not self.isEnabledExtension(x)]

    def _loadExtensions(self):
        extensions = Extensions()
        extensions.extend(self.unzippedExtensions)
        extensions.extend(self.zippedExtensions)
        return extensions

    @property
    def unzippedExtensions(self):
        if self._unzippedExtensions is None:
            self._unzippedExtensions = self._loadUnzippedExtensions()
        return self._unzippedExtensions

    def _loadUnzippedExtensions(self):
        def getUnzippedExtensionNames():
            names = mstarext.getAllUnzippedExtensionNames(self._config)
            return [str(mstarext.canonicaliseExtensionName(x)) for x in names]
        extensions = Extensions()
        for name in getUnzippedExtensionNames():
            dir = os.path.join(self.getMStarUnzippedExtensionsDir(), name)
            if os.access(dir, os.F_OK):
                extensions.append(mstarext.DirectoryExtension(name, dir))
        return extensions

    @property
    def zippedExtensions(self):
        if self._zippedExtensions is None:
            self._zippedExtensions = mstarext.replaceWithUpdatedZippedExtensions(self._loadZippedExtensions())
        return self._zippedExtensions

    def _loadZippedExtensions(self, fromUpdates=True, fromPackages=True):
        extensions = Extensions()
        if fromUpdates:
            extensions.extend(self._findMStarUpdatesZippedExtensions())
        if fromPackages:
            extensions.extend(self._findMStarPackagesZippedExtensions())
        return extensions

    def _findMStarUpdatesZippedExtensions(self):
        return self._findZippedExtensionsInDir(self.getMStarZippedExtensionsDir())

    def _findMStarPackagesZippedExtensions(self):
        """Find the zipped extensions in the ${MSTAR_INSTALL}/packages/extensions/${MSTAR_VERSION}/**
           directory (if it exists)."""
        zippedExtensions = []
        extensionsPackageDir = self.getExtensionsPackageDir()
        if extensionsPackageDir is not None:
            zippedExtensions = self._findZippedExtensionsInDir(extensionsPackageDir)
        return zippedExtensions

    def _findZippedExtensionsInDir(self, dir):
        return mstarext.findZippedExtensionsInDir(mstarConfig=None, zipdir=dir)

    def getMStarZippedExtensionsDir(self):
        return mstarpaths.interpretPath("{MSTAR_UPDATES}")

    def getMStarUnzippedExtensionsDir(self):
        return mstarpaths.interpretPath("{MSTAR_HOME}/ext")

    def getExtensionsPackageDir(self):
        """Find the directory containing the extensions package for the M* release."""
        mstarInstallDir = mstarpaths.interpretPath("{MSTAR_INSTALL}")
        mstarHomeDir = mstarpaths.interpretPath("{MSTAR_HOME}")
        from mstarRelease import MStarRelease
        mstarRelease = MStarRelease(mstarInstall=mstarInstallDir, mstarHome=mstarHomeDir)
        extensionsPackage = mstarRelease.getPackage("extensions")
        if extensionsPackage is not None:
            from install.mstarInstall import MStarInstall
            mstarInstall = MStarInstall.getInstance(mstarInstallDir)
            extensionsPackageDir = mstarInstall.getPackagePath(extensionsPackage)
            if os.path.exists(extensionsPackageDir):
                return extensionsPackageDir
        return None


def createOptionDefns():
    from optparse import make_option
    return [
        make_option("--list", action="store_true", help="List the installed extensions (subject to --where). Equivalent to '--list:installed' command."),
        make_option("--list:installed", dest="listInstalled", action="store_true", help="List the installed extensions (subject to --where)."),
        make_option("--list:available", dest="listAvailable", action="store_true", help="List the available extensions (subject to --where)."),
        make_option("--info", action="store_true", help="Show details for all extensions (subject to --where)."),
        make_option("--info:installed", dest="infoInstalled", action="store_true", help="Show details for installed extensions (subject to --where)."),
        make_option("--info:available", dest="infoAvailable", action="store_true", help="Show details for available extensions (subject to --where)."),
        make_option("--status", metavar="<id>", help="Get the status of the extension (using extension ID)"),
        make_option("--install", metavar="<id>", help="Install an available extension (using ID, or from a zip file)."),
        make_option("--remove", metavar="<id>", help="Remove an installed extension (using extension ID). Use '--force' for cleanups."),
        make_option("--reinstall", metavar="<id>", help="Re-install an available extension (using extension ID). Equivalent to install with '--force' option."),
        make_option("--check", action='store_true', help="Check for missing extensions and updates."),
        make_option("--update", action='store_true', help="Update extensions to latest version"),
        make_option("--where", metavar="<expression>", help="Filter the extensions using an expression, e.g. 'id=devtools'."),
        make_option("--force", action="store_true", help="Force install/remove of extension if required.")
    ]


def createExpr(lhs, rhs):
    if lhs is None:
        return rhs
    if rhs is None:
        return lhs
    return "and(%s, %s)" % (lhs, rhs)


def parseExpression(expression):
    """Parse a expression string to return a expression map, e.g. the expression string
       'and(name=foo,compulsory=false)' would return the expression map
       {'and': {'name':'foo', 'compulsory':'false'}}."""

    import re
    if not expression:
        return None
    expression = expression.strip()
    if not expression:
        return None
    expressionMap = {}
    # Check for parentheses: "(name=foo)"
    if len(expression) > 2 and expression[0] == '(' and expression[-1] == ')':
        return parseExpression(expression[1:-1])
    # Check for unary expressions.
    m = re.match("not\s(.+)", expression)
    if m:
        return {'not': parseExpression(m.group(1))}
    # Check for string, e.g. 'xyz'
    m = re.match("'(.*)'", expression)
    if m:
        expressionMap['_value'] = m.group(1)
        expression = expression[len(m.group(0)):].strip()
    # Check for 'name[=value]'
    m = re.match("([a-zA-Z]+)(\s?=\s?([a-zA-Z0-9/_\-]+))?", expression)
    if m:
        name = m.group(1)
        value = m.group(3) or ('false' if name == 'false' else 'true')
        expressionMap[name] = value
        expression = expression[len(m.group(0)):].strip()
    # Check for '... and ...', '... or ...'
    def isAndExpr(c):
        return c.startswith("and ") or c.startswith("and(") or c.startswith("and (")
    def isOrExpr(c):
        return c.startswith("or ") or c.startswith("or(") or c.startswith("or (")
    while isAndExpr(expression) or isOrExpr(expression):
        m = re.match("and\s+(.*)", expression)
        if m:
            expressionMap = {'and': [expressionMap, parseExpression(m.group(1))]}
            expression = expression[len(m.group(0)):].strip()
            continue
        m = re.match("or\s+(.*)", expression)
        if m:
            expressionMap = {'or': [expressionMap, parseExpression(m.group(1))]}
            expression = expression[len(m.group(0)):].strip()
            continue
    # Fail if any expression left over.
    if expression:
        raise ApplicationError("Invalid expression: '%s'" % expression)
    return expressionMap


def run(appConfig=None):
    (options, args) = minestar.parseCommandLine(appConfig, "1.0", createOptionDefns(), appConfig['argcheck'])
    app = ExtensionsApp(config=appConfig)
    if options.list or options.listInstalled:
        app.listInstalledExtensions()
    elif options.listAvailable:
        app.listAvailableExtensions()
    elif options.info:
        app.showExtensionInfo(expression=parseExpression(options.where))
    elif options.infoInstalled:
        app.showExtensionInfo(expression=parseExpression(createExpr("enabled=true", options.where)))
    elif options.infoAvailable:
        app.showExtensionInfo(expression=parseExpression(createExpr("enabled=false", options.where)))
    elif options.status:
        app.showStatus(options.status)
    elif options.install:
        app.installExtension(extensionId=options.install, overwrite=options.force)
    elif options.remove:
        app.removeExtension(extensionId=options.remove, force=options.force)
    elif options.reinstall:
        app.installExtension(extensionId=options.reinstall, overwrite=True)
    elif options.check:
        app.checkExtensions()
    elif options.update:
        app.updateExtensions()
    else:
        # TODO show usage
        raise ApplicationError("No command specified")
    return 0


def main(appConfig=None):
    try:
        return run(appConfig)
    except ApplicationWarning as e:
        print "WARNING: %s" % e.message
        return 0
    except ApplicationError as e:
        print "ERROR: %s" % e.message
        return 1
