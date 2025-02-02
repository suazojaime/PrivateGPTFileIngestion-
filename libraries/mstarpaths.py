# A module to assist in interpretation of paths for MineStar systems.
# Responsibilities are:
# 1. interpret variables from MineStar.properties, and strings including them
# 2. load MineStar.properties and similar files
# 3. figure out Java class paths
#
# Written by John Farrell

import os
import re
import string
import sys

import ServerTools
import i18n
import minestar
import ufs
from mstarRepositoryOps import repositoryHome, repositoryRuntimeTarget
from pathOps import simplifyPath


# TODO duplicated in mstarrun.mstarrunDebug() -- should move to a common function.

def mstarrunValidateReleaseEnabled():
    """ Determines if mstarrun validate is enabled (i.e. if MSTARRUN_VALIDATE is defined in OS environment). """
    return 'MSTARRUN_VALIDATE' in os.environ


def mstarrunValidateRelease(config):
    """ Validate the M* release specified in the config. """
    if mstarrunValidateReleaseEnabled() and 'MSTAR_INSTALL' in config and 'MSTAR_HOME' in config:
        from mstarRelease import MStarRelease
        release = MStarRelease(mstarInstall=config['MSTAR_INSTALL'], mstarHome=config['MSTAR_HOME'])
        mstarrunDebug("Validating M* build %s" % release.version)
        release.validate()


def mstarrunDebugEnabled():
    """ Determines if mstarrun debug is enabled (i.e. if MSTARRUN_DEBUG is defined in OS environment). """
    return 'MSTARRUN_DEBUG' in os.environ


def mstarrunDebug(msg):
    """ Print a message to stdout if mstarrun debug is enabled. """
    if mstarrunDebugEnabled():
        print "debug: %s" % msg


# name of the properties file holding licencing information
LICENCING_PROPERTIES = "{MSTAR_INSTALL}/LICENSE.key"

# Which properties sets to load - relative to MSTAR_HOME so entries in MineStar.overrides are easy to find
PROPERTIES_FILES = ["/MineStar.properties", "/Versions.properties", "/Workgroup.properties", "/Enterprise.properties", "/Database.properties"]

MSTARRUN_DIR = "{MSTAR_HOME}/bus/mstarrun"
# extensions jar files can have
JAR_EXTS = ['.zip', '.jar']

# Determines if unsecured and secured configurations need loading.
configLoaded = False
secureConfigLoaded = False

# TODO replace references with 'installedJava.javaBinary' and 'installedJava.javawBinary'
java = None
javaw = None

# support running direct from a repository
# TODO replace with 'isRunningFromRepository()'
runningFromRepository = 0

# fields to parse eagerly, so that batch files don't need to call GetProperty and Python doesn't
# need to call parse().
EAGER_PARSE = []
# how to parse composite fields
FIELDS = {
    "_DATABASE": "_MACHINE _INSTANCE _USER _PASS",
    "_BACKUP": "_EXPORT _START",
    "_MACHINE99": "_MACHINE _DRIVEC _DRIVED _DRIVEE _DRIVEF _DRIVEG _DRIVEH _DRIVEI _DRIVEJ _DRIVEK _DRIVEL _DRIVEM _DRIVEN",
}
for (key, value) in FIELDS.items():
    FIELDS[key] = value.split()

# known contents of the bus properties file
# TODO deprecate this and replace with getConfig()
config = None

# where we got the settings in config from
# TODO deprecate this and replace with getSources()
sources = None


def setConfig(value=None):
    """ Set the global config. """
    global config
    config = value
    # Clear the interpreter and source repository. Subsequent calls to getInterpreter()
    # and getSourceRepository() will create new instances using the config, which SHOULD
    # contain a value for 'MSTAR_HOME' by that point.
    setInterpreter(None)
    setSourceRepository(None)
    setInstalledJava(None)
    setInstalledPython(None)


def getConfig(reload=False):
    """ Get the global config. Will contain at least MSTAR_HOME, MSTAR_INSTALL, and MSTAR_BUILD. """
    global config, sources
    if config is None:
        (sources, config) = __bootstrapConfigInit()
    return config


def setSources(value=None):
    """ Set the global sources. """
    global sources
    sources = value


def getSources():
    """ Get the global sources. Will contain at least MSTAR_HOME, MSTAR_INSTALL, and MSTAR_BUILD. """
    global config, sources
    if sources is None:
        (sources, config) = __bootstrapConfigInit()
    return sources


# the name of the main system
DEFAULT_SYSTEM = "main"

# The variable interpreter. Value assigned when the global config is updated.
_interpreter = None


def getInterpreter(reload=False):
    """ Get the variable interpreter. """
    global _interpreter
    if _interpreter is None or reload:
        from interpreter import Interpreter
        return Interpreter(getConfig())
    return _interpreter


def setInterpreter(interpreter):
    """ Set the variable interpreter. """
    global _interpreter
    _interpreter = interpreter


# The global repository. Value assigned when the global config is updated.
_sourceRepository = None


def getSourceRepository(mstarHome=None, reload=False):
    """ Get the global repository. """
    global _sourceRepository
    if _sourceRepository is None or reload:
        # If mstarHome is not provided, get it from the config. Note that the config must be bootstrapped first.
        if mstarHome is None:
            mstarHome = getInterpreter().interpretVar('MSTAR_HOME')
        from sourceRepository import SourceRepository
        return SourceRepository.getInstance(mstarHome=mstarHome)
    return _sourceRepository


def setSourceRepository(repository=None):
    """ Set the global repository """
    global _sourceRepository
    _sourceRepository = repository
    # Update (deprecated) global property 'runningFromRepository'
    global runningFromRepository
    if _sourceRepository is not None:
        runningFromRepository = _sourceRepository.running
    else:
        runningFromRepository = False


def isRunningFromRepository(mstarHome=None, reload=None):
    """ Determine if running from a source repository. """
    return getSourceRepository(mstarHome=mstarHome, reload=reload).running


# The java install. Value assigned when bootstrapping.
_installedJava = None


def getInstalledJava(reload=False):
    global _installedJava
    if _installedJava is None or reload:
        from javaInstall import JavaInstall
        _installedJava = JavaInstall.fromConfig(getConfig())
        # Update the global java + javaw variables.
        # TODO remove global variables java + javaw; replace with getInstalledJava().javaBinary, etc.
        global java, javaw
        java = _installedJava.javaBinary
        javaw = _installedJava.javawBinary
    return _installedJava


def setInstalledJava(installedJava):
    global _installedJava
    _installedJava = installedJava


# The python install. Value assigned when bootstrapping.
_installedPython = None


def getInstalledPython(reload=False):
    global _installedPython
    if _installedPython is None or reload:
        from pythonInstall import PythonInstall
        _installedPython = PythonInstall.fromConfig(getConfig())
    return _installedPython


def setInstalledPython(installedPython):
    global _installedPython
    _installedPython = installedPython


class MineStarConfigError:
    def __init__(self, explanation):
        self.explanation = explanation

    def __repr__(self):
        return "MineStarConfigError('%s')" % self.explanation


def parse(key):
    """
    Retrieve the value for a composite configuration item and parse it using the
    field names given above in FIELDS. Return a dictionary from names to values.
    """
    if not config.has_key(key):
        minestar.fatalError(None, i18n.translate(
            "You have no property definition for %s: this is a required property.") % key)
    value = interpretFormat(config[key])
    fields = value.split()
    fieldNames = FIELDS[key]
    props = {}
    for index in range(min(len(fields), len(fieldNames))):
        name = fieldNames[index]
        field = fields[index]
        if field == "~":
            break
        props[name] = interpretFormat(field)
    return props


def setEnvironment():
    """ Copies the entries in the global config that have string type to the OS environment. """
    # XXX I'm not sure why it is necessary to pollute the OS environment with
    #     internal M* properties. There are some OS environment properties that 
    #     are used to configure the correct location of python and java, which 
    #     I have removed.
    import types
    for (key, value) in config.items():
        if isinstance(value, types.StringTypes):
            # Don't copy java or python configuration variables; can only come from the OS.
            if key not in ['JAVA_HOME', 'MSTAR_PYTHON', 'PYTHONHOME', 'PYTHONPATH']:
                os.environ[key] = value


def _interpretRepositoryHome(override):
    return interpretFormatOverride(repositoryHome(), override)


def _interpretRepositoryRuntime(override):
    return interpretFormatOverride(repositoryRuntimeTarget(), override)


def _interpretRepositoryLib(app, override):
    return interpretFormatOverride(repositoryRuntimeTarget() + '/' + app, override)


def simplifyPath(path):
    """ Simplify a path by replacing '/', '\', '..', etc.  """
    import pathOps
    return pathOps.simplifyPath(path)


def _resolvePossibleSymbolicLink(path):
    # Simplify the path (replace '/' with '\', etc) before resolving symlinks.
    import symlink
    return symlink.resolvePossibleSymbolicLink(simplifyPath(path))


def interpretVarOverride(var, override):
    return getInterpreter().interpretVar(var, override)


def interpretVar(var):
    return interpretVarOverride(var, None)


def interpretFormatOverride(pattern, overrides):
    return getInterpreter().interpretPattern(pattern, overrides)


def saveOverridesToConfig(overrides, source):
    """Update the configuration with the given overrides."""
    for key in overrides.keys():
        config[key] = overrides[key]
        sources[key] = source


def interpretPathOverride(pattern, overrides):
    """
    interpret {var} patterns
    interpret \ and / as local system file separators
    interpret .. as local system parent directory
    """
    return getInterpreter().interpretPath(pattern, overrides)


def interpretFormat(pattern):
    return interpretFormatOverride(pattern, None)


def interpretPath(pattern):
    return interpretPathOverride(pattern, None)


def interpretNetworkPath(pattern):
    path = interpretPath(pattern)
    if not ServerTools.onAppServer():
        """ This is client. Find network path using base_central up to data folder of it.  """
        index = path.rfind(os.sep)
        fileName = path[index:]
        folderPath = path[0:index]
        folderName = folderPath[folderPath.rfind(os.sep):]
        networkPath = interpretPath("{MSTAR_BASE_CENTRAL}") + os.sep + folderName + os.sep
        if os.path.exists(networkPath):
            return os.path.abspath(networkPath) + fileName
        else:
            return path
    else:
        """  If we are already on the server, just return network path """
        return path


def interpretPathShort(pattern):
    return shortPathName(interpretPath(pattern))


def relativeFileName(desired, current):
    """
    Given current, which is the current directory, and desired, which is a path
    name to a desired file, return a relative path name to that file.
    """
    desiredFields = desired.split(os.sep)
    currentFields = current.split(os.sep)
    if len(desiredFields) == 0 or len(currentFields) == 0:
        return desired
    if sys.platform.startswith("win"):
        # drive letter can vary in case
        desiredFields[0] = desiredFields[0].upper()
        currentFields[0] = currentFields[0].upper()
    if desiredFields[0] != currentFields[0]:
        return desired
    while len(desiredFields) > 0 and len(currentFields) > 0 and desiredFields[0] == currentFields[0]:
        desiredFields = desiredFields[1:]
        currentFields = currentFields[1:]
    for dir in currentFields:
        desiredFields = [os.pardir] + desiredFields
    return string.join(desiredFields, os.sep)


def shortPathName(desired):
    relative = relativeFileName(desired, os.getcwd())
    if len(relative) < len(desired):
        return relative
    else:
        return desired


def getUfsLibDirs(ufsRoot):
    ufsDirs = []
    ufsDirs.append(ufsRoot.getSubdir("lib"))
    if isRunningFromRepository():
        try:
            ufsDirs.append(ufsRoot.getSubdir("../../../runtime/target/mstar/lib"))
        except ufs.UfsException:
            pass
    return ufsDirs


def buildClassPaths(ufsRoot, reduceCommandLineLength, extraJars, extraCPDirs, fixedClassPath=None, shorten=True):
    ufsDirs = getUfsLibDirs(ufsRoot)
    bcps = []
    cps = []
    cpdirs = []
    cpNamedJars = []
    namedJars = None;
    if fixedClassPath is not None:
        namedJars = fixedClassPath.split(os.pathsep)
    filesDone = []
    for ufsDir in ufsDirs:
        bcpFile = ufsDir.getFile("BOOTCPJARS")
        bcpFiles = []
        if bcpFile is not None:
            for physFile in bcpFile.getAllPhysicalFiles():
                bcpFiles = bcpFiles + minestar.readOptionalLines(physFile)
        filenames = ufsDir.listFileNames()
        # check that BOOTCPJARS lists files which exist and add those which do to the bcp
        for file in bcpFiles:
            filesDone.append(file)
            if file not in filenames:
                # maybe in build target if running from repository
                if isRunningFromRepository():
                    buildFile = os.sep.join([interpretPath("{REPOSITORY_MSTAR_HOME}/lib"), file])
                    if os.path.exists(buildFile):
                        if shorten is True:
                            addIfNotAlreadyThere(bcps, shortPathName(os.path.normpath(buildFile)))
                        else:
                            addIfNotAlreadyThere(bcps, os.path.normpath(buildFile))
                    else:
                        pass
                        # minestar.logit("BOOTCPJARS lists " + file + " which does not exist")
            else:
                if shorten is True:
                    addIfNotAlreadyThere(bcps, shortPathName(ufsDir.get(file).getPhysicalFileName()))
                else:
                    addIfNotAlreadyThere(bcps, shortPathName(ufsDir.get(file).getPhysicalFileName()))
    # development classpath
    devcps = []
    if isRunningFromRepository():
        devcps = __getDevelopmentClasspath()
        devcps = [p for p in devcps if os.path.basename(p) not in filesDone]
        filesDone = filesDone + [os.path.basename(p) for p in devcps if isAJar(p)]
    # add remaining jars in reverse extension order
    libDirs = []
    for ufsDir in ufsDirs:
        libDirs.extend(ufsDir.getPhysicalDirectories())
        libSubDirs = ufsDir.listSubdirNames()
        for subdir in libSubDirs:
            ufsSubDir = ufsDir.getSubdir(subdir)
            libDirs.extend(ufsSubDir.getPhysicalDirectories())

    libDirs.reverse()
    for dir in libDirs:
        for file in listDir(dir):
            if file == "CVS" or file.startswith(".#"):
                continue
            pathName = os.sep.join([dir, file])
            if os.path.isdir(pathName):
                continue
            else:
                if file not in filesDone and isAJar(file) and isANamedJar(file, namedJars):
                    if shorten is True:
                        addIfNotAlreadyThere(cps, shortPathName(pathName))
                    else:
                        addIfNotAlreadyThere(cps, pathName)
                    filesDone.append(file)
                    if namedJars is not None:
                        addIfNotAlreadyThere(cpNamedJars, pathName)
    if extraJars is not None:
        ed = interpretPath(extraJars)
        if os.access(ed, os.R_OK):
            for file in os.listdir(ed):
                if file not in filesDone and isAJar(file) and isANamedJar(file, namedJars):
                    filesDone.append(file)
                    pathName = os.sep.join([ed, file])
                    addIfNotAlreadyThere(cps, pathName)
                    if namedJars is not None:
                        addIfNotAlreadyThere(cpNamedJars, pathName)
    if extraCPDirs is not None:
        ed = interpretPath(extraCPDirs)
        for dir in ed.split(os.pathsep):
            if os.access(dir, os.R_OK):
                addIfNotAlreadyThere(cps, dir)
                addIfNotAlreadyThere(cpdirs, dir)
    return (bcps, bcps + devcps + cps, cpdirs, cpNamedJars)


def addIfNotAlreadyThere(array, entry):
    if entry not in array:
        array.append(entry)


def listDir(d):
    ds = os.listdir(d)
    ds.sort()
    return ds


def isAJar(p):
    return p[-4:].lower() in JAR_EXTS


def isANamedJar(p, namedJars):
    if namedJars is None:
        return True
    for namedJar in namedJars:
        if re.match(namedJar, p) is not None:
            return True
    return False


def loadConfig(filename):
    """
    Return (sources, config) where
    * sources is a dict from keys to filenames
    * config is a dict from keys to values
    The given filename is absolute.
    """
    if os.access(filename, os.R_OK):
        minestar.debug("Loading %s" % filename)
        return minestar.loadJavaStyleProperties(filename, [])
    else:
        minestar.debug("Unable to open %s" % filename)
        return ({}, {})


SYSTEM_HOME_PATTERN = "{MSTAR_SYSTEMS}/%s"


def __setScriptVariables(config, sources, scriptVariableFile):
    realFileName = interpretPathOverride(scriptVariableFile, config)
    for line in minestar.readLines(realFileName):
        fields = line.split("=")
        key = fields[0].strip()
        value = fields[1].strip()
        v = interpretPathOverride(value, config)
        config[key] = v
        sources[key] = "(inferred from %s in %s)" % (value, realFileName)


def loadBootstrapConfig():
    """Load the bootstrap config without interpreting the vars."""
    realFileName = interpretPathOverride("{MSTAR_HOME}/bus/mstarrun/bootstrap_properties.txt", config)
    result = {}
    for line in minestar.readLines(realFileName):
        fields = line.split("=")
        key = fields[0].strip()
        value = fields[1].strip()
        result[key] = value
    return result


def __bootstrapConfigInit():
    """
    The initial bootstrap that sets MSTAR_HOME, MSTAR_INSTALL, and MSTAR_BUILD.

    MSTAR_HOME, MSTAR_INSTALL, and MSTAR_BUILD are typically set in the OS environment by 
    the mstarrun shell script (e.g. mstarrun.bat) or the mstarrun python script (e.g. 
    mstarrun.py).
    """

    config = {}
    sources = {}

    # Derive MSTAR_HOME from OS environment.
    # (changes MSTAR_HOME back in case they overrode it)
    if 'MSTAR_HOME' not in os.environ:
        raise RuntimeError("No value defined for MSTAR_HOME in the OS environment")
    mstarHome = os.environ["MSTAR_HOME"]
    if mstarHome[-1] == os.sep:
        mstarHome = mstarHome[:-1]
    config["MSTAR_HOME"] = mstarHome
    sources["MSTAR_HOME"] = "(location of mstarrun.py)"

    # Derive MSTAR_INSTALL from OS environment.
    if 'MSTAR_INSTALL' not in os.environ:
        raise RuntimeError("No value defined for MSTAR_INSTALL in the OS environment")
    mstarInstall = os.environ["MSTAR_INSTALL"]
    if mstarInstall[-1] == os.sep:
        mstarInstall = mstarInstall[:-1]
    config["MSTAR_INSTALL"] = mstarInstall
    sources["MSTAR_INSTALL"] = "(location of mstarrun.py)"

    # Derive MSTAR_BUILD from the OS environment.
    if 'MSTAR_BUILD' not in os.environ:
        raise RuntimeError("No value defined for MSTAR_BUILD in the OS environment")
    config["MSTAR_BUILD"] = os.environ["MSTAR_BUILD"]
    sources["MSTAR_BUILD"] = "(operating system environment)"

    mstarrunDebug('bootstrap: MSTAR_HOME=%s %s' % (config['MSTAR_HOME'], sources['MSTAR_HOME']))
    mstarrunDebug('bootstrap: MSTAR_INSTALL=%s %s' % (config['MSTAR_INSTALL'], sources['MSTAR_INSTALL']))
    mstarrunDebug('bootstrap: MSTAR_BUILD=%s %s' % (config['MSTAR_BUILD'], sources['MSTAR_BUILD']))

    return (sources, config)


def __bootstrapConfig(system, systemSource):
    # Get the initial bootstrap config (MSTAR_HOME, MSTAR_INSTALL, MSTAR_BUILD)
    (sources, config) = __bootstrapConfigInit()

    # Update the global config / sources.
    setConfig(config)
    setSources(sources)

    sources["MSTAR_SYSTEM"] = systemSource
    config["MSTAR_SYSTEM"] = system
    # installation properties are loaded from LICENSE.key
    __loadInstallationProperties(sources, config, system)

    # Bootstrap MSTAR_SYSTEMS
    if not config.has_key("MSTAR_SYSTEMS"):
        sources["MSTAR_SYSTEMS"] = "(default = {MSTAR_HOME}/systems)"
        config["MSTAR_SYSTEMS"] = interpretPathOverride("{MSTAR_HOME}/systems", config)
    sources["MSTAR_SYSTEM_HOME"] = "(inferred from MSTAR_SYSTEMS)"
    config["MSTAR_SYSTEM_HOME"] = interpretPathOverride("{MSTAR_SYSTEMS}/%s/" % "{MSTAR_SYSTEM}", config)

    # Bootstrap MSTAR_BASE_LOCAL and MSTAR_BASE_CENTRAL
    __configureBootstrapValue("MSTAR_LOCAL", "MSTAR_BASE_LOCAL", config, sources)
    __configureBootstrapValue("MSTAR_CENTRAL", "MSTAR_BASE_CENTRAL", config, sources)

    # Platform
    platform = sys.platform
    if platform.startswith("linux"):
        platform = "linux"
    config["MSTAR_PLATFORM"] = platform
    sources["MSTAR_PLATFORM"] = "(Python sys.platform)"

    # set COMPUTERNAME
    hostname = minestar.hostname()
    if platform.startswith("win"):
        config["COMPUTERNAME"] = hostname
        sources["COMPUTERNAME"] = "(operating system environment)"
        config["EXE"] = ".exe"
        sources["EXE"] = "(known for operating system)"
    else:
        config["COMPUTERNAME"] = hostname
        sources["COMPUTERNAME"] = "(hostname command)"
        config["EXE"] = ""
        sources["EXE"] = "(known for operating system)"

    # Put in a default minestarServer env variable
    os.environ["minestarServer"] = hostname

    # Check if running from a source repository.
    global runningFromRepository
    runningFromRepository = isRunningFromRepository()

    # Where do executables (e.g. mstarrun) live? Depends type (install vs source).
    #
    # Type     Location                                Example
    # ====     ========                                =======
    # Install  ${MSTAR_HOME}/bus/bin                   /mstar/mstarHome/bus/bin
    # Source   ${REPOSITORY_MSTAR_HOME}/bus/bin        /sbox/trunk/runtime/target/mstar/bus/bin

    mstarHomeVar = "REPOSITORY_MSTAR_HOME" if runningFromRepository else "MSTAR_HOME"
    config["MSTAR_BIN"] = interpretPathOverride("{%s}/bus/bin" % mstarHomeVar, config)
    sources["MSTAR_BIN"] = "(inferred from %s and platform)" % mstarHomeVar

    # Where do libraries (e.g. jar files) live? ${MSTAR_HOME}/lib (install) or ${REPOSITORY_MSTAR_HOME}/lib (source)
    config["MSTAR_LIB"] = interpretPathOverride("{%s}/lib" % mstarHomeVar, config)
    sources["MSTAR_LIB"] = "(inferred from %s)" % mstarHomeVar

    # Get the repository properties.
    if runningFromRepository:
        config["REPOSITORY_HOME"] = getSourceRepository().homeDir
        sources["REPOSITORY_HOME"] = "(running from repository)"
        config["REPOSITORY_RUNTIME"] = getSourceRepository().runtimeDir
        sources["REPOSITORY_RUNTIME"] = "(running from repository)"
        config["REPOSITORY_EXTENSIONS_EXTRA"] = os.environ.get("REPOSITORY_EXTENSIONS_EXTRA")
        sources["REPOSITORY_EXTENSIONS_EXTRA"] = "(running from repository - operating system environment )"

    # Validate the M* release, if requested.
    if mstarrunValidateReleaseEnabled():
        mstarrunValidateRelease(config)

    # Get the python properties (may depend on repository properties)
    __findPythonProperties(sources, config)
    __updatePythonPath(sources, config)

    # Get the JDK properties (depends on repository properties).
    __findJavaProperties(sources, config)

    # __findOracleHome(sources, config)

    # print "mstarpaths.__bootstrapConfig: Finished with config %s " % config
    # print "mstarpaths.__bootstrapConfig: Finished with sources %s " % sources


def __configureBootstrapValue(base, key, config, sources):
    """Bootstrap a directory value from a base value and a key.

    The following strategy is used:

     1. Use key from cfg if already configured</li>
     2. Use base/{MSTAR_SYSTEM} if base configured</li>
     3. Use {MSTAR_SYSTEM_HOME} if that is configured</li>
     4. Use {MSTAR_SYSTEMS/MSTAR_SYSTEM} if that is configured</li>
     5. Use {MSTAR_HOME}/systems/{MSTAR_SYSTEM} if that is configured</li>

     If all of these fail a warning message is printed.

     see MstarPaths.configureBootstrapValue
    """
    if config.has_key(key):
        return
    if config.has_key(base):
        config[key] = interpretPathOverride('%s/{MSTAR_SYSTEM}/' % config[base], config)
        sources[key] = '(inferred from %s)'
        return
    if config.has_key('MSTAR_SYSTEM_HOME'):
        config[key] = interpretPathOverride('{MSTAR_SYSTEM_HOME}', config)
        sources[key] = '(inferred from MSTAR_SYSTEM_HOME)'
        return
    if config.has_key('MSTAR_SYSTEMS'):
        config[key] = interpretPathOverride('{MSTAR_SYSTEMS}/{MSTAR_SYSTEM}', config)
        sources[key] = '(inferred from MSTAR_SYSTEMS)'
        return
    if config.has_key('MSTAR_HOME'):
        config[key] = interpretPathOverride('{MSTAR_HOME}/systems/{MSTAR_SYSTEM}', config)
        sources[key] = '(inferred from MSTAR_HOME)'
        return
    print "WARNING: Could not configure %s" % key


def findJavaHome():
    global sources, config
    __findJavaProperties(sources, config)


def __addDontChange(sources, config, newSources, newConfig):
    for key in newConfig.keys():
        if config.has_key(key):
            oldSource = sources[key]
            newSource = newSources[key]
            message = "Setting %s from %s cannot override the value from %s" % (key, newSource, oldSource)
            raise MineStarConfigError(message)
        else:
            config[key] = newConfig[key]
            sources[key] = newSources[key]


def __loadInstallationProperties(sources, config, system):
    filename = getInstallFilePathForSystem(system, config)
    (installSources, installConfig) = __getInstallationProperties(filename)
    __addDontChange(sources, config, installSources, installConfig)


def __findJavaProperties(sources, config):
    # Requires global config to contain MSTAR_HOME
    installedJava = getInstalledJava()

    config['JAVA_HOME'] = installedJava.home
    sources['JAVA_HOME'] = installedJava.homeSource
    mstarrunDebug("bootstrap: jdk.home=%s %s" % (config['JAVA_HOME'], sources['JAVA_HOME']))

    config['JAVA_VERSION'] = installedJava.version
    sources['JAVA_VERSION'] = installedJava.versionSource
    mstarrunDebug("bootstrap: jdk.version=%s %s" % (config['JAVA_VERSION'], sources['JAVA_VERSION']))

    # TODO Global java + javaw is nasty. Replace with mstarpaths.installedJava.javaBinary, etc.
    global java, javaw
    java = installedJava.javaBinary
    javaw = installedJava.javawBinary
    mstarrunDebug("bootstrap: jdk.java=%s" % java)
    mstarrunDebug("bootstrap: jdk.javaw=%s" % javaw)


def __updatePythonPath(sources, config):
    # Update the python path now that the python config is loaded. Sometimes python code is called
    # directly without going through mstarrun or mstarrunlib (e.g. 'mstarrun overrides' which then
    # calls 'python.exe overrides.py') and such code typically only loads the config. But this code
    # may also require python lib extensions (e.g. the crypto code) so the python path needs to be
    # updated here.
    from pythonPathUpdater import PythonPathUpdater
    PythonPathUpdater(mstarInstall=config['MSTAR_INSTALL'], mstarHome=config['MSTAR_HOME']).updatePath()

    # Show the path if debugging.
    if mstarrunDebugEnabled():
        for path in sys.path:
            mstarrunDebug("bootstrap: python path: %s" % path)


def __findPythonProperties(sources, config):
    # Requires global config to contain MSTAR_HOME
    installedPython = getInstalledPython()

    config['MSTAR_PYTHON'] = installedPython.home
    sources['MSTAR_PYTHON'] = installedPython.homeSource
    mstarrunDebug("bootstrap: python.home=%s %s" % (config['MSTAR_PYTHON'], sources['MSTAR_PYTHON']))
    mstarrunDebug("bootstrap: python.binary=%s" % installedPython.pythonBinary)


# there is Java code in MstarPaths.java which needs to be kept in sync with this list
DIRECTORY_OVERRIDE_VARS = [ "MSTAR_CONFIG", "MSTAR_LOGS", "MSTAR_TRACE", "MSTAR_TEMP", "MSTAR_MESSAGES", "MSTAR_DATA",
                            "MSTAR_ADMIN", "MSTAR_UPDATES", "MSTAR_HELP", "MSTAR_REPORTS", "MSTAR_DATA_BACKUPS","TempDBDirectory", "MSTAR_STANDBY",
                            "MSTAR_OUTGOING", "MSTAR_SENT", "MSTAR_ONBOARD", "MSTAR_ADD_LOGS", "MSTAR_BO_JARS", "MSTAR_VIMS", "MSTAR_FLUID_IMPORT", "MSTAR_CACHE",
                            "MSTAR_CREDS", "SQL_SERVER_LOGPATH", "SQL_SERVER_MDFPATH"]


def __loadDirectoryOverrides(sources, config):
    """If {MSTAR_SYSTEM_HOME}/MineStar.directories exists, load values from it"""
    file = interpretPathOverride("{MSTAR_SYSTEM_HOME}/MineStar.directories", config)
    if os.access(file, os.R_OK):
        minestar.debug("Loading directory overrides from %s" % file)
        (s, c) = minestar.loadJavaStyleProperties(file, [])
    else:
        minestar.debug("No directory overrides found")
        (s, c) = ({}, {})
    config['MSTAR_BASE_LOCAL'] = _loadOverrideOrSystemHome(c, config, 'MSTAR_BASE_LOCAL')
    config['MSTAR_BASE_CENTRAL'] = _loadOverrideOrSystemHome(c, config, 'MSTAR_BASE_CENTRAL')
    config['MSTAR_DISK_VOLUMES'] = c.get('MSTAR_DISK_VOLUMES')
    for key in DIRECTORY_OVERRIDE_VARS:
        if c.has_key(key):
            sources[key] = s[key]
            config[key] = interpretPathOverride(c[key], config)


def _loadOverrideOrSystemHome(c, config, var):
    return c.get(var) or (config.has_key(var) and config[var]) or config['MSTAR_SYSTEM_HOME']


def getDeploymentType():
    licenseFile = interpretPath(LICENCING_PROPERTIES)
    if licenseFile is not None:
        (sources, depVal) = loadConfig(licenseFile)
        depType = depVal.get("deploymentType")
        if depType is None:
            depType = "Client"
        return depType
    return "Client"


def __reEstablishNetworkShare(sources, config):
    if ServerTools.getCurrentServer() is None:
        # this occurs when the system is new
        return

    if not ServerTools.onAppServer() and os.sys.platform.startswith("win"):
        try:
            try:
                centralOverrides = config['MSTAR_BASE_CENTRAL']
            except:
                # this occurs when the system is new
                return
            import mstaroverrides
            centralOverridesFile = interpretPathOverride(
                '{MSTAR_BASE_CENTRAL}/config/%s' % (mstaroverrides.OVERRIDES_NAME), config)

            if (centralOverrides != ""):
                servertmpDB_ExportDir = getPropertyFromFile(centralOverrides + '/MineStar.directories', 'TempDBDirectory')
                if (servertmpDB_ExportDir != None):
                    config['TempDBDirectory'] = servertmpDB_ExportDir

            # if the file exists we're ok, just exit
            if os.path.isfile(centralOverridesFile):
                return

            # check for existing share
            (drive, path) = os.path.splitdrive(centralOverrides)
            result = os.system('dir %s >nul 2>nul' % (drive))
            if result != 0:

                # The file doesn't exists so try and
                # re-establish a network share with known information
                overridesFile = interpretPathOverride('{MSTAR_BASE_LOCAL}/config/%s' % (mstaroverrides.OVERRIDES_NAME),
                                                      config)
                if not os.path.isfile(overridesFile):
                    _Mbox(('Error loading configuration',
                           'Unable to load configuration local overrides file at %s.'
                           ) % (overridesFile), 0)
                    sys.exit(1)
                (sources, allOverrides) = minestar.loadJavaStyleProperties(overridesFile, [])
                appServer = allOverrides['/MineStar.properties._HOME']

                mapResult = os.system('net use %s \\\\%s\\mstarFiles >nul 2>nul' % (drive, appServer))
                if mapResult != 0:
                    _Mbox('Error loading configuration',
                          'Unable to load configuration from %s. Windows mapped drive is not ' % (centralOverridesFile) +
                          'accessible and/or could not be mapped. ' +
                          'Correct MineStar directory configuration or mapped drive to MineStar application server configuration',
                          0)
                    sys.exit(1)
                if not os.path.isfile(centralOverridesFile):
                    _Mbox('Error loading configuration',
                          'Unable to load configuration from %s. Windows mapped drive is not ' % (centralOverridesFile) +
                          'accessible and/or could not be mapped. ' +
                          'Correct MineStar directory configuration or mapped drive to MineStar application server configuration',
                          0)
                    sys.exit(1)
                return
        except Exception as e:
            print e
            _Mbox('Error loading configuration',
                  'Unable to load configuration from application server. Windows mapped drive is not ' +
                  'accessible and/or could not be mapped. ' +
                  'Correct mapped drive to MineStar application server configuration', 0)
            sys.exit(1)


def _Mbox(title, text, style):
    import ctypes
    print '%s: %s' % (title, text)
    ctypes.windll.user32.MessageBoxA(None, text, title, 0x10 | 0x0)


def __getDevelopmentClasspath():
    import mstarext
    devcp = []
    cvsdirs = ['base', 'util', 'env', 'gem', 'jive', 'mctools', 'networkmender', 'uifacadeimpl', 'uifacade',
               'jiveclient', 'terrain-bridge', 'geometry']
    devs = []

    # Add the tools.jar from the JDK8 (does not exist in JDK9+)
    toolsPath = interpretPath("{JAVA_HOME}/lib/tools.jar");
    if os.access(toolsPath, os.R_OK):
        devcp.append(toolsPath)

    # Add any extensions
    ps = [str(p).lower() for p in mstarext.parts]
    for extDir in ps:
        devs.append(interpretPath("{REPOSITORY_HOME}/" + extDir))
        devs.append(interpretPath("{REPOSITORY_EXTENSIONS_HOME}/" + extDir))

    devs = devs + [interpretPath("{MSTAR_HOME}/..")]
    devs = devs + [interpretPath("{REPOSITORY_HOME}/fleetcommander/target/classes")]
    devs = devs + [interpretPath("{REPOSITORY_HOME}/%s/target/classes" % cvsdir) for cvsdir in cvsdirs]
    ebo = interpretPath(interpretPath("{REPOSITORY_HOME}"))
    for f in os.listdir(ebo):
        if f.lower() in ps:
            devs = devs + [os.sep.join([ebo, f, "target/classes"])]

    for cvsdir in cvsdirs:
        devBaseDir = interpretPath("{REPOSITORY_HOME}/" + cvsdir)
        devs.append(devBaseDir)

    for dev in devs:
        dexists = os.access(dev, os.F_OK)
        if dexists:
            c = interpretPath(dev + "/classes")
            cexists = os.access(c, os.F_OK)
            r = interpretPath(dev + "/res")
            rexists = os.access(r, os.F_OK)
            devr = interpretPath(dev + "/src/main/res")
            devrexists = os.access(devr, os.F_OK)
            if cexists:
                devcp.append(c)
            if rexists:
                devcp.append(r)
            if devrexists:
                devcp.append(devr)
            if not cexists and not rexists and not devrexists:
                devcp.append(dev)
    # print "mstarpaths.__getDevelopmentClasspath: returning devcp %s " % devcp
    return devcp


def __addReleaseProperties(sources, config):
    relFile = getReleaseInfoFile(config)
    if relFile is not None:
        (rs, rc) = loadConfig(relFile)
        config["MSTAR_MAJOR"] = rc["MAJOR"]
        config["MSTAR_MINOR"] = rc["MINOR"]
        sources["MSTAR_MAJOR"] = relFile
        sources["MSTAR_MINOR"] = relFile
    else:
        print "Cannot find release file to extract version information"


def getReleaseInfoFile(config=None):
    root = ufs.getRoot(interpretVarOverride("UFS_PATH", config))
    relFile = root.get("releaseInfo.txt")
    if relFile is not None:
        return relFile.getPhysicalFileName()
    return None


def hasExtension(config, id):
    loadedExtensions = config["LOADED_EXTENSIONS"]
    for e in loadedExtensions:
        if e.id == id:
            return True
    return False


def dumpConfig(options=None):
    _dumpConfig(config=config, keys=None, options=options)


def _dumpConfig(config, keys=None, options=None):
    if keys is None:
        keys = sorted(config.keys())
    elif type(keys) is str:
        keys = (keys)
    for key in keys:
        value = _getConfigValueString(config, key, options)
        print "%s: %s" % (key, value)


def _dumpConfigAndSources(config, sources=None, keys=None, options=None):
    if keys is None:
        keys = sorted(config.keys())
    elif type(keys) is str:
        keys = (keys)
    for key in keys:
        source = '(unknown)'
        if sources is not None and sources.has_key(key):
            source = sources[key]
        value = '<NO VALUE>'
        if config.has_key(key):
            value = _getConfigValueString(config, key, options)
        print "%s: %s %s" % (key, value, source)


def _getConfigValueString(config, key, options=None):
    from configvalue import getConfigValueString
    return getConfigValueString(config, key, options)


def __addReleaseDependencies(sources, config):
    """ Set the release dependencies (geoserver, postgis, jetty, etc). """
    # Config must contain entries for COMPUTERNAME, _HOME (obtained when properties loaded)
    from mstarReleaseDependencies import MStarReleaseDependencies
    dependencies = MStarReleaseDependencies(sources, config)
    dependencies.setJettyProperties()
    dependencies.setGeoserverProperties()
    dependencies.setPostgisProperties()
    dependencies.setToolkitProperties()

    mstarrunDebug("addReleaseDependencies: _GEOSERVER_HOME: %s" % config.get('_GEOSERVER_HOME'))
    mstarrunDebug("addReleaseDependencies: _POSTGIS_HOME  : %s" % config.get('_POSTGIS_HOME'))
    mstarrunDebug("addReleaseDependencies: _JETTY_HOME    : %s" % config.get('_JETTY_HOME'))
    mstarrunDebug("addReleaseDependencies: MSTAR_TOOLKIT  : %s" % config.get('MSTAR_TOOLKIT'))


def loadConfigForSystem(system, systemSource):
    """
    Load and return MineStar.properties for the specified system.
    This does not set the config and sources fields in this module.
    Look for additional MineStar.<platform>.properties files according
    to the platform we are running on, and load them as well. Note: this does
    not load the Secure.overrides.  This needs to be done from loadSecureConfigForSystem
    """
    global sources, config

    __bootstrapConfig(system, systemSource)

    # derived properties
    __setScriptVariables(config, sources, "{MSTAR_HOME}/bus/mstarrun/bootstrap_properties.txt")
    __loadDirectoryOverrides(sources, config)
    __reEstablishNetworkShare(sources, config)
    # create directories for logging etc
    __createExpectedDirectories(config)
    # find overrides (note: we load only the public overrides)
    import mstaroverrides
    (overrides, overridesFile) = mstaroverrides.loadOverridesForSystem(system, config)
    # print "mstarpaths.loadConfigForSystem: After loadOverridesForSystem: config %s " % config
    # find out what files to load
    propertiesFilesToLoad = ["{MSTAR_HOME}%s" % f for f in PROPERTIES_FILES]
    propertiesFilesToLoad.append("{MSTAR_HOME}/bus/mstarrun/MineStar.{MSTAR_PLATFORM}.properties")
    propertiesFilesToLoad.append("{MSTAR_HOME}/bus/mstarrun/mstarrun.properties")
    mstarHome = config["MSTAR_HOME"]

    # load the properties files and then any overrides for them
    for propsFile in propertiesFilesToLoad:
        actualFileName = interpretPathOverride(propsFile, config)
        (propsFileSources, propsFileConfig) = loadConfig(actualFileName)
        # print "mstarpaths.loadConfigForSystem: Back from loadConfig"
        overrideKey = actualFileName
        if overrideKey.startswith(mstarHome):
            overrideKey = overrideKey[len(mstarHome):]
        overrideKey = "/".join(overrideKey.split(os.sep))
        if overrides.has_key(overrideKey):
            ors = overrides[overrideKey]
            minestar.debug("Keys %s in %s are overridden" % (`ors.keys()`, overrideKey))
            propsFileConfig.update(ors)
            for k in ors.keys():
                propsFileSources[k] = overridesFile
        else:
            minestar.debug("%s has no overrides" % overrideKey)
        __addDontChange(sources, config, propsFileSources, propsFileConfig)
    # print "mstarpaths.loadConfigForSystem: Finished for loop: config %s " % config
    __setScriptVariables(config, sources, "{MSTAR_HOME}/bus/mstarrun/extra_properties.txt")
    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject(config, 'mpaths')
    dbobject.finddbHome(sources, config)

    import mstarext
    mstarext.loadExtensions(sources, config)
    # print "mstarpaths.loadConfigForSystem: Finished loadExtensions: config %s " % config
    # add release stuff
    __addReleaseProperties(sources, config)
    __addReleaseDependencies(sources, config)


def loadMineStarConfig(system=None, systemSource=None, forceReload=0):
    """
    Load MineStar.properties for the current system and set the sources and config attributes in this module.
    Most mstarrun Python applications should call this when they start up, unless they use invocation=import.
    """
    global config, sources, configLoaded, secureConfigLoaded
    # print "mstarpaths.loadMineStarConfig: Started"

    # Figure out the system.
    if not system:
        system = os.environ.get("MSTAR_SYSTEM")
        systemSource = "(operating system environment)"
    elif not systemSource:
        systemSource = "(passed in)"
    if not system:
        system = DEFAULT_SYSTEM
        systemSource = "(default)"

    # Modify the python path for UFS only if there is a change.
    modifyPythonPath = False

    # Load the unsecured config, if required.
    if not configLoaded or forceReload:
        # Load the (non-secure) config.
        # print "mstarpaths.loadMineStarConfig: Calling loadConfigForSystem"
        loadConfigForSystem(system, systemSource)
        # print "mstarpaths.loadMineStarConfig: After loadConfigForSystem: config['UFS_PATH'] %s " % config["UFS_PATH"]
        configLoaded = True
        modifyPythonPath = True

    # Load the secure config, if required.
    if not secureConfigLoaded or forceReload:
        (secureConfig, secureSources) = loadSecureConfigForSystem(config, system)
        # TODO use mstaroverrides.merge() instead of update?
        config.update(secureConfig)
        sources.update(secureSources)
        secureConfigLoaded = True
        modifyPythonPath = True

    # Make sure that future imports use the right path
    if modifyPythonPath:
        __modifyPythonPathForUFS(config["UFS_PATH"])


def loadSecureConfigForSystem(config, system):
    """Load configuration from the Secure.overrides file"""
    import mstaroverrides

    (fullyQualifiedSources, fullyQualifiedConfig) = mstaroverrides.loadSecureOverridesForSystemFullyQualified(system,
                                                                                                              config)
    # Merge secure overrides into config
    sources = {}
    config = {}
    contents = fullyQualifiedConfig.get("CONTENTS") or ''
    bundles = contents.split(',')
    for fullyQualifiedKey in fullyQualifiedConfig:
        for bundle in bundles:
            if fullyQualifiedKey.startswith(bundle):
                key = fullyQualifiedKey[len(bundle) + 1:]
                config[key] = fullyQualifiedConfig[fullyQualifiedKey]
                sources[key] = fullyQualifiedSources[fullyQualifiedKey]
    return config, sources


def getPythonPaths():
    """ Get the M* python path from UFS (as a list of directories). """
    import ufs

    # Get the UFS root.
    root = ufs.getRoot(interpretVar("UFS_PATH"))

    # Get the physical directories (if any) matching the UFS path.
    def getPhysicalDirectories(path):
        directories = []
        ufsDir = root.get(path)
        if ufsDir is not None:
            directories = ufsDir.getPhysicalDirectories()
        return directories

    # Add the M* python library, and M* python library packages, if they exist.
    dirs = []
    dirs.extend(getPhysicalDirectories("bus/pythonlib"))
    dirs.extend(getPhysicalDirectories("bus/pythonlib/lib"))
    dirs.reverse()

    return dirs


def __modifyPythonPathForUFS(ufsPath):
    # Remove a directory from python sys.path
    def removeFromSysPath(directory):
        while directory in sys.path:
            sys.path.remove(directory
                            )

    # Get the pythonlib and pythonlib/lib directories.
    dirs = getPythonPaths()

    # Remove these directories from the python sys path.
    for d in dirs:
        removeFromSysPath(d)

    # The pythonlib from the original installation is in the path. This is not used if we have a replacement build,
    # so we remove it. If there is no replacement build then this directory will be in the UFS path anyway and will
    # be added back.
    removeFromSysPath(interpretPath("{MSTAR_INSTALL}/mstarHome/bus/pythonlib"))
    removeFromSysPath(interpretPath("{MSTAR_INSTALL}/mstarHome/bus/pythonlib/lib"))

    # Add the UFS pythonlibs to the python sys path.    
    sys.path = sys.path + dirs


def __createExpectedDirectories(config):
    "Create all the directories that other components will think exist"
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_TEMP}", config))
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_LOGS}", config))
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_TRACE}", config))
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_DATA}", config))
    # [Ram 7-Jan-2009] The following line is commented out so that onboard directory will not
    # be created by default. It will be created by makeSystem, if the profile is server profile
    # minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_ONBOARD}", config))
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_ADMIN}", config))

    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_CONFIG}/logs", config))
    # MSTAR-3973 - [Ram 9-Mar-2009] Created the following four directories as a part of the makeSystem
    # This is based on the PGM field follow testing
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_SYSTEM_HOME}/updates/builds", config))
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_CONFIG}/xml/cycles", config))
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_CONFIG}/xml/units", config))
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_CONFIG}/xml/catalogs/Displays", config))

    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_OUTGOING}", config))
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_OUTGOING}/in-progress", config))
    minestar.createExpectedDirectory(interpretPathOverride("{MSTAR_SENT}", config))

    addLogs = interpretPathOverride("{MSTAR_ADD_LOGS}", config)
    if addLogs is not None and (addLogs == "" or addLogs.startswith("{")):
        addLogs = None
    if addLogs:
        minestar.createExpectedDirectory(addLogs)


def interpretClasspath(path):
    "Translate a class path to the appropriate format for this platform"
    if path is None:
        return None
    path = string.join(path.split(';'), ':')
    path = string.join(path.split(':'), os.pathsep)
    return path


def getSuiteForSystem(system):
    file = getInstallFilePathForSystem(system)
    try:
        (files, installation) = minestar.loadProperties(file, [])
        return installation["suite"]
    except:
        return "Personal"


def getDirectoryForSystem(system, mstarHome, mstarInstall):
    """this can be called before the configuration is loaded"""
    file = getInstallFilePathForSystem(system, {"MSTAR_HOME": mstarHome, "MSTAR_INSTALL": mstarInstall})
    try:
        (files, installation) = __getInstallationProperties(file)
        return installation["MSTAR_SYSTEMS"] + os.sep + system
    except:
        return mstarHome + os.sep + "systems" + os.sep + system


def getInstallFilePathForSystem(system, overrides=None):
    return interpretPathOverride(LICENCING_PROPERTIES, overrides)


def __getInstallationProperties(filename):
    (installSources, installConfig) = minestar.loadProperties(filename, [])
    # support ~ expansion in directories
    for key in ['MSTAR_SYSTEMS', 'MSTAR_LOCAL', 'MSTAR_CENTRAL']:
        if installConfig.has_key(key):
            installConfig[key] = os.path.expanduser(installConfig[key])
    return (installSources, installConfig)


def getOptionSet(optionSetUfsName, optionSetJavaName):
    "returns a Map of properties with overrides applied. NOTE: This does not work for JAR files!"
    import ufs, mstarpaths, mstaroverrides
    # Load the option set
    ufsRoot = ufs.getRoot(mstarpaths.interpretFormat("{UFS_PATH}"))
    config = ufsRoot.get(optionSetUfsName)
    content = config.loadMapAndSources()[1]
    # Apply the overrides
    overrides = mstaroverrides.loadOverrides()
    minestar.putAll(overrides[0].get(optionSetJavaName), content)
    return content


def validateFile(filename, options=None):
    # check for full file path.

    if sys.platform.startswith("win"):
        if ":" not in filename and not filename.startswith("\\"):
            print "INFO: Directory path not mentioned, checking default directory"
            filename = os.path.dirname(os.path.realpath(filename)) + os.sep + filename

    if not (os.path.isfile(filename) and os.access(filename, os.R_OK)):
        msg = i18n.translate("ERROR: %s - File not Found or not Accessible" % filename)
        print msg
        minestar.exit()
    return filename


def getPropertyFromFile(filePath, propertyName):
    if os.access(filePath, os.R_OK):
        try:
            minestar.debug("Reading %s" % filePath)
            fileProperties = minestar.loadJavaStyleProperties(filePath, [])
            propertyValue = fileProperties.__getitem__(1)[propertyName]
        except:
            propertyValue = None
            print "WARNING: Property %s not Found in the File: %s " % (propertyName, filePath)
    else:
        minestar.debug("Unable to open %s" % filePath)
        propertyValue = None
    return propertyValue


def getUncPathOfMapDrive(path):
    # returns UNC path of mapped drive
    if path is not None and ":" not in path and path.startswith("\\"):
        if not path.startswith("\\\\"):
            return os.sep + path
        return path
    elif path is not None and ":" in path:
        drive = path.split(":")[0]
        command = 'net use %s:' % drive
        import subprocess
        output = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in iter(output.stdout.readline, ''):
            if "Remote" in line:
                fields = path.split(":")
                uncPath = line[line.index("\\"):].strip()
                for field in fields:
                    if field == drive:
                        continue
                    path = uncPath + field

    return path
