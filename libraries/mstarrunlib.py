#  Copyright (c) 2022-2024 Caterpillar

# This is the "second half of mstarrun". By putting it in a separate file we allow it to be patched. However the code
# contains many implicit references to mstarrun.
import os
import sys
import types

import ServerTools
import minestar
import mstardebug
import mstarpaths

# well-known Java classes
EXPLORER = "com.mincom.explorer.uif.BusAppMain"
OBJECT_SERVER = "com.mincom.env.service.server.ObjectServer"
JYTHON_INTERPRETER = "org.python.util.jython"
# -D options which don't work when you read them from a file
NO_DEFINES = ['java.library.path', 'emma.properties', 'app.name', 'enable.pid', 'java.locale.providers', 'java.security.properties', 'file.encoding']
SERVICE_CONFIG_DIR = "{MSTAR_CONFIG}/service"

def mstarrunDebug(msg):
    if 'MSTARRUN_DEBUG' in os.environ:
        print "debug: %s" % msg


def _getMstarInstall():
    """ Get the configured MSTAR_INSTALL value. """
    return mstarpaths.interpretVar('MSTAR_INSTALL')


def _getMStarHome():
    """ Get the configured MSTAT_HOME value. """
    return mstarpaths.interpretVar('MSTAR_HOME')


def executeNewWindow(cmd, appName, appConfig):
    if sys.platform.startswith("win"):
        # Dirty hack - escape the %t timestamp option for GC logging
        cmd = cmd.replace("-%t", "-%%t")
        import win32
        win32.executeNewWindow(cmd, appName, appConfig)
    else:
        desktop_session = os.environ.get("DESKTOP_SESSION")
        if desktop_session is None:
            desktop_session = os.environ.get("XDG_CURRENT_DESKTOP")
        if desktop_session is not None: #easier to match if we doesn't have  to deal with caracter cases
            desktop_session = desktop_session.lower()
            if desktop_session == "gnome":
                import gnome
                gnome.executeNewWindow(cmd, appName, appConfig)
            elif desktop_session == "lxde":
                import lxde
                lxde.executeNewWindow(cmd, appName, appConfig)
            elif desktop_session == "none":
                import none
                none.executeNewWindow(cmd, appName, appConfig)
            else:
                import kde
                kde.executeNewWindow(cmd, appName, appConfig)
        else:
            print "ERROR: Could not find desktop type, check env variables DESKTOP_SESSION or XDG_CURRENT_DESKTOP"


def __protect(s):
    """Wrap s so that it won't fall apart in a command line"""
    if not s.startswith('--') and s.find(' ') >= 0 and s.find('"') < 0:
        s = '"%s"' % s
    return s


def execute(command, args, appConfig):
    newWindow = 0
    appName = None
    if appConfig is not None and appConfig.has_key("newWindow"):
        newWindow = appConfig["newWindow"]
    if appConfig is not None and appConfig.has_key("appName"):
        appName = appConfig["appName"]
    if appName is None:
        appName = "minestar"
    args = quoteSpaces(args)
    cmd = ' '.join([command] + args)
    if newWindow:
        executeNewWindow(cmd, appName, appConfig)
    else:
        minestar.runMaybeSavingOutput(cmd, appConfig)


def quoteSpaces(args):
    """Quote spaces to be passed to the command line"""
    result = list(args)
    for i in range(len(result)):
        result[i] = __protect(result[i])
    return result


def runObjectServer(appName, appConfig, args, busUrl):
    filename = appConfig["filename"]
    if appConfig.get("vmstyle") is None:
        appConfig["vmstyle"] = "server"
    runJava(appName, appConfig, OBJECT_SERVER, [filename] + args, busUrl)


def __import(name):
    # Fast path: see if the module has already been imported.
    try:
        return sys.modules[name]
    except KeyError:
        pass
    # If any of the following calls raises an exception,
    # there's a problem we can't handle -- let the caller handle it.
    import imp
    (fp, pathname, description) = imp.find_module(name)
    try:
        return imp.load_module(name, fp, pathname, description)
    finally:
        # Since we may exit via an exception, close fp explicitly.
        if fp:
            fp.close()


def __getPythonPath():
    """ Get the M* python path (as a path-separated string, e.g. "/mstar/foo:/mstar/bar", etc). """
    return os.pathsep.join(mstarpaths.getPythonPaths())


def runPython(appName, appConfig, args, busUrl):
    """
    Invocation types:
      - import: means import module and call its main method
      - external: means run as an external program
    """
    import ufs
    os.environ["PYTHONPATH"] = __getPythonPath()
    filename = appConfig["filename"]
    invocation = "external"
    if appConfig.has_key("invocation"):
        invocation = appConfig["invocation"]
    if invocation == "import":
        if appConfig.get("progressFile") is not None:
            import progress
            progress.setFileName(mstarpaths.interpretPath(appConfig["progressFile"]))
        fields = filename.split(".")
        module = __import(fields[0])
        module.main(appConfig)
    else:
        # assume invocation is "external"
        originalFilename = appConfig["originalFilename"]
        if originalFilename is not None and originalFilename.find('{') < 0:
            # not relative to MSTAR_HOME, so assumed to be in the UFS
            ufsRoot = ufs.getRoot(mstarpaths.interpretPath("{UFS_PATH}"))
            ufsFile = ufsRoot.get(originalFilename)
            if ufsFile is not None:
                filename = ufsFile.getPhysicalFile()
            else:
                minestar.fatalError("mstarrun", "Cannot locate python file %s" % originalFilename)
        pyArgs = [ filename ]
        if busUrl:
            pyArgs.append(busUrl)
        pyArgs = pyArgs + args
        execute(getPythonPath(), pyArgs, appConfig)


def getPythonPath(w = 0):
    ws = ""
    if w:
        ws = "w"
    # TODO use mstarpaths.installedPython.pythonBinary?    
    pyPath = mstarpaths.interpretPath("{MSTAR_PYTHON}/python%s{EXE}" % ws)
    if not os.access(pyPath, os.X_OK):
         pyPath = mstarpaths.interpretPath("{MSTAR_PYTHON}python%s{EXE}" % ws)
    return pyPath


def runExplorer(appName, appConfig, args):
    filename = appConfig["filename"]
    if appConfig.get("vmstyle") is None:
        appConfig["vmstyle"] = "client"
    runJava(appName, appConfig, EXPLORER, [filename] + args, None)


def runJython(appName, appConfig, args, busUrl):
    import ufs
    originalFilename = appConfig["filename"]
    ufsRoot = ufs.getRoot(mstarpaths.interpretPath("{UFS_PATH}"))
    ufsFile = ufsRoot.get(originalFilename)
    if ufsFile is not None:
        filename = ufsFile.getPhysicalFile()
    else:
        filename = originalFilename
    if busUrl:
        args = [busUrl] + args
    runJava(appName, appConfig, JYTHON_INTERPRETER, [filename] + args, None)


def runShellScript(appName, appConfig, args, busUrl):
    import i18n
    if sys.platform.startswith("win"):
        print i18n.translate("You can't run shell scripts on Windows. Use a batch file instead.")
        sys.exit(88)
    import stat
    filename = appConfig["filename"]
    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)
    if len(args) > 0:
        for i in range(len(args)):
            args[i] = __protect(args[i])
        cmdArgs = ' '.join(args)
        filename = filename + " " + cmdArgs
    shArgs = ["-c", filename]
    execute("/bin/bash", shArgs, appConfig)


def runBatchFile(appName, appConfig,  args, busUrl):
    import i18n
    if not sys.platform.startswith("win"):
        print i18n.translate("You can only run batch files on Windows, you should provide an alternate shell script (.sh) file.")
        sys.exit(163)
    filename = appConfig["filename"]
    shArgs = ["/c", filename] + args
    execute("cmd", shArgs, appConfig)


def runWindowsExe(appName, appConfig, args, busUrl):
    import i18n
    filename = appConfig["filename"]
    if not sys.platform.startswith("win"):
        print i18n.translate("You can only run exe files on Windows, can't run %s") % filename
        sys.exit(164)
    execute(filename, args, appConfig)


def runExecutable(appName, appConfig, args, busUrl):
    import i18n
    if sys.platform.startswith("win"):
        runWindowsExe(appName, appConfig, args, busUrl)
    else:
        print i18n.translate("Let's just pretend we executed %s") % appConfig["filename"]


def __execMScriptCommand(command, config, uniqueness):
    """
    uniqueness is a unique number to distinguish this command from others, so we
    can generate unique file names and so on.
    """
    import mstarapplib
    if command is None:
        return
    (cmdLineConfig, systemSource) = mstarapplib.parseCommandLine(command.split(), 1)
    appConfig = mstarapplib.buildAppConfig(cmdLineConfig)
    minestar.putAll(config, appConfig)
    appConfig["unique"] = str(uniqueness)
    mstarapplib.cleanAppConfig(appConfig)
    if not appConfig.has_key("appName"):
        appConfig["appName"] = appConfig["filename"]
    if mstardebug.debug:
        print appConfig
    __runApplication(appConfig, command)


def runMScript(appName, appConfig, args, busUrl):
    import i18n
    filename = appConfig["filename"]
    lines = open(filename).readlines()
    outstandingCommand = None
    outstandingConfig = {}
    lineNumber = 0
    for line in lines:
        lineNumber = lineNumber + 1
        if line[-1] == '\n':
            line = line[:-1]
        line = line.rstrip()
        if len(line) == 0:
            continue
        if line.lstrip().startswith('#'):
            continue
        if line.startswith(' '):
            if outstandingCommand is None:
                outstandingCommand = line.strip()
            else:
                fields = line.split('=', 1)
                if len(fields) != 2:
                    print i18n.translate("Expected key=value: %s") % line
                else:
                    key = fields[0]
                    value = fields[1]
                    outstandingConfig[key.strip()] = value.strip()
        else:
            if outstandingCommand is None:
                outstandingCommand = line
            else:
                __execMScriptCommand(outstandingCommand, outstandingConfig, lineNumber)
                outstandingConfig = {}
                outstandingCommand = line
    __execMScriptCommand(outstandingCommand, outstandingConfig, lineNumber)


def __checkCorrectJavaExecutable(java, exePath):
    replace = False
    if os.access(exePath, os.F_OK):
        import stat
        javaStats = os.stat(java)
        exeStats = os.stat(exePath)
        replace = (javaStats[stat.ST_SIZE] != exeStats[stat.ST_SIZE])
        if replace:
            minestar.logit("Replacing %s, it is not the same size as %s" % (exePath, java))
    return replace


def copyJavaExecutable(appName, appConfig, dir="{MSTAR_TEMP}"):
    # Get the installed JDK and binaries.
    jdk = mstarpaths.getInstalledJava()        
    java = jdk.javaBinary
    javaw = jdk.javawBinary

    # Check if the binaries can be used, without copying.
    if appConfig.get("profilerFile"):
        # Might to good to support an explicitly specified directory rather than assuming jplauncher is on the path ...
        exePath = mstarpaths.interpretPath("jplauncher{EXE} -jp_input=%s" % appConfig["profilerFile"])
        return exePath, java
    if appConfig.get("noConsole") and appConfig.get("noJavaCopy"):
        return javaw, javaw
    if appConfig.get("noJavaCopy"):
        return java, java
    if not sys.platform.startswith("win"):
        return java, java

    # If the JDK is not embedded, then copy it locally, so that local binaries can be created.
    if not __isEmbeddedJDK(jdk):
        jdk = __createLocalJDK(jdk, dir)

    # Get the preferred java binary.
    preferredJava = javaw if appConfig.get("noConsole") else java
    
    # To avoid confusion with Windows Explorer
    if sys.platform == "win32" and appName == "explorer":
        appName = "mstarExplorer"

    # Create a copy of the preferred java, using the application name (e.g. 'mojetty.exe'). 
    # This will allow the process to be identified and terminated, if required.
    exePath = mstarpaths.interpretPath("%s/bin/mo%s{EXE}" % (jdk.home, appName))
    __copyExe(exePath, preferredJava)

    return exePath, java

def __isEmbeddedJDK(jdk):
    from pathOps import isSubdirectory
    # Check if the JDK is located under ${MSTAR_INSTALL}.
    mstarInstall = _getMstarInstall()
    if isSubdirectory(jdk.home, mstarInstall):
         return True
    
    # Check if the JDK is located under ${REPOSITORY_RUNTIME}.
    if mstarpaths.isRunningFromRepository():
        runtimeJdk = mstarpaths.getSourceRepository().libDir('jdk')
        if isSubdirectory(jdk.home, runtimeJdk):
            return True
        
    return False


def __createLocalJDK(jdk, directory):
    """ Create a local JDK (if required) by copying the external JDK (e.g. C:\Java8) 
        to the local directory (e.g. C:\mstarFiles\systems\main\tmp). """
    jdkHomeDir = mstarpaths.interpretPath('%s/jdk-%s' % (directory, jdk.version))
    # Copy the external JDk to the local JDK, if required.
    if not __hasJDKLayout(jdkHomeDir):
        import shutil
        # Remove target directory if it exists (it may be corrupted by cleaning the {MSTAR_TEMP} directory).
        if os.path.exists(jdkHomeDir):
            minestar.logit("Removing local JDK at %s ..." % jdkHomeDir)
            shutil.rmtree(jdkHomeDir)
        # Copy external JDK to local JDK (ignoring any shared archive files).
        minestar.logit("Creating local JDK by copying %s to %s ..." % (jdk.home, jdkHomeDir))
        shutil.copytree(jdk.home, jdkHomeDir, ignore=shutil.ignore_patterns('*.jsa'))
    # Create a java install from the local JDK.
    from javaInstall import JavaInstall
    return JavaInstall.fromDirectory(jdkHomeDir)


def __hasJDKLayout(directory):
    """ Check that a directory has a valid JDK layout: it exists, and contains a regular 
        file (cleaning MSTAR_TEMP may sometimes remove files but not directories). """
    # Check that the directory exists.
    if not os.path.exists(directory):
        return False
    # Check that the directory contains at least one regular file.
    for f in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, f)):
            return True
    return False


def __copyExe(exePath, preferredJava):
    replace = __checkCorrectJavaExecutable(preferredJava, exePath)
    if not os.access(exePath, os.F_OK) or replace:
        # not there, so copy it
        if sys.platform == "win32":
            minestar.copy(preferredJava, exePath)
        else:
            # some sort of Unix, I guess
            file = open(exePath, "w")
            file.write('%s "$@"\n' % preferredJava)
            file.close()
    if not os.access(exePath, os.X_OK):
        # not executable
        os.chmod(exePath, 0755)


def standardDefines(appName, appConfig):
    # -D options that MineStar programs expect
    javaLibraryDirs = getJavaLibraryPathDirs(appConfig)
    defines = {
        "MSTAR_HOME": mstarpaths.interpretPath("{MSTAR_HOME}"),
        "MSTAR_SYSTEM": mstarpaths.interpretPath("{MSTAR_SYSTEM}"),
        "app.name": appName
    }

    try:
        enablepid = appConfig["enablepid"]
    except:
        enablepid = "false"

    defines["enable.pid"] = enablepid

    defines["MSTAR_INSTALL"] = mstarpaths.interpretPath("{MSTAR_INSTALL}")
    import databaseDifferentiator
    dbobject = databaseDifferentiator.returndbObject()
    dbobject.setDefines(defines)
    if not sys.platform.startswith("win"):
        if len(javaLibraryDirs) > 0:
            defines["LD_LIBRARY_PATH"] = os.pathsep.join(javaLibraryDirs)
        else:
            defines["LD_LIBRARY_PATH"] = dbobject.returnLibraryPath()
        os.environ["LD_LIBRARY_PATH"] = defines["LD_LIBRARY_PATH"]
    defines["jdk.home"] = mstarpaths.interpretPath("{JAVA_HOME}")
    defines["user.timezone"] = mstarpaths.interpretVarOverride("_TIMEZONE", appConfig)
    defines["user.language"] = mstarpaths.interpretVarOverride("_LANGUAGE", appConfig)
    defines["user.region"] = mstarpaths.interpretVarOverride("_COUNTRY", appConfig)
    defines["python.home"] = mstarpaths.interpretPath("{MSTAR_HOME}/bus/jythonlib")
    # UFS Path is now ONLY calculated in Java
    #defines["UFS_PATH"] = mstarpaths.interpretVar("UFS_PATH")
    defines["java.security.policy"] = mstarpaths.interpretPath("{MSTAR_HOME}/bus/mstarrun/security.policy")
    defines["java.security.properties"] = mstarpaths.interpretPath("{MSTAR_HOME}/bus/mstarrun/java.security.properties")
    defines["DEVELOPMENT"] = mstarpaths.interpretPath("DEVELOPMENT")
    if len(javaLibraryDirs) > 0:
        # [Gordon Aug-10-2016] Added os.pathsep to end of java library path as Java not happy in some cases without it
        defines["java.library.path"] = os.pathsep.join(javaLibraryDirs) + os.pathsep
        #print "mstarrunlib.standardDefines java.library.path = %s" % defines["java.library.path"]
        minestar.debug("java.library.path = %s" % defines["java.library.path"])
    return defines


def listDlls(ufsDir):
    dotdll = "." + mstarpaths.interpretVar("_SHARED")
    files = ufsDir.listFiles()
    files = [ x for x in files if x.getName().endswith(dotdll) ]
    return files


def getJavaOpts(appConfig):
    """Return the JAVA_OPTS specified for this application"""
    javaOptsStr = mstarpaths.interpretPathOverride("{JAVA_OPTS}", appConfig)
    if not javaOptsStr or javaOptsStr.startswith("{"):
        return []
    javaOpts = javaOptsStr.split()
    # For Jetty, if SSL is disabled then strip out SSL options:
    appName = appConfig.get("appName")
    if appName == "Jetty":
        javaOpts = filterJettyOpts(javaOpts)
    return javaOpts


def getWrapperOpts(appConfig):
    """Return the wrapper options specified for this application"""
    wrapperOptions = appConfig.get("wrapperOptions")
    if wrapperOptions is None:
        return []

    # Comma ',' is both a separator between args and can be used *within* an arg if it is escaped using '\\,'
    # Do a __COMMA__ replacement first so we don't split incorrectly.
    wrapperOptionsTemp = wrapperOptions.replace('\\,','__COMMA__')
    wrapperOptsTemp = wrapperOptionsTemp.split(',')
    wrapperOpts = []
    for opt in wrapperOptsTemp:
        wrapperOpts.append(opt.replace('__COMMA__',','))

    # For Jetty, if SSL is disabled then strip out SSL options:
    appName = appConfig.get("appName")
    if appName == "Jetty":
        wrapperOpts = filterJettyOpts(wrapperOpts)
    return wrapperOpts


def filterJettyOpts(opts):
    """For Jetty, filter out SSL options if SSL is disabled"""
    sslEnabled = mstarpaths.interpretVar("RMI_OVER_SSL")
    if sslEnabled == "true":
        minestar.debug("**** Jetty and SSL is enabled")
    else:
        minestar.debug("**** Jetty and SSL is disbled")
        # Strip SSL options
        minestar.debug("**** Jetty Original opts: %s" % opts)
        opts = [x for x in opts if ".ssl" not in x and ".secure" not in x]
        minestar.debug("**** Jetty Stripped opts: %s" % opts)
    return opts


def appendJettyArgs(args):
    """For Jetty, enable HTTPS and SSL modules if SSL is enabled"""
    sslEnabled = mstarpaths.interpretVar("RMI_OVER_SSL")
    keyStore = mstarpaths.interpretPath("{RMI_SSL_KEYSTORE}")
    trustStore = mstarpaths.interpretPath("{RMI_SSL_TRUSTSTORE}")
    if sslEnabled == "true" and os.path.exists(keyStore) and os.path.exists(trustStore):
        minestar.debug("**** Jetty and SSL IS enabled: enabling https and ssl modules")
        args.append("--module=https")
        args.append("--module=ssl")


def getJavaLibraryPathDirs(appConfig):
    # returns the list of directories to put on the Java library path
    # support JNI for dlls in bin directories
    import ufs

    result = []
    ufsBinDir = ufs.getRoot(mstarpaths.interpretVar("UFS_PATH")).get("bin")
    theBusBinDir = ufs.getRoot(mstarpaths.interpretVar("UFS_PATH")).get("bus/bin")

    # If there is a '-Djava.library.path' option already present, then include it.
    javaOpts = getJavaOpts(appConfig)
    for javaOpt in javaOpts:
        javaOpt = mstarpaths.interpretFormat(javaOpt)
        if javaOpt.startswith("-Djava.library.path="):
            fields = javaOpt.split("=", 1)
            if len(fields) == 2:
                result.append(fields[1])

    if ufsBinDir is not None:
        ufsDirs = [ufsBinDir] + [theBusBinDir]
        allDlls = [listDlls(ud) for ud in ufsDirs]
        # DLLs in an architecture-specific directory will hide those of the same name in the bin directory.
        names = []
        for dlls in allDlls:
            for d in dlls:
                if d.getName() not in names:
                    names.append(d.getName())
                    dirName = os.path.dirname(d.physicalFile)
                    if dirName not in result:
                        minestar.debug("found " + d.getName() + " in " + dirName)
                        result.append(dirName)
    # now add the DB directory
    pathDirs = os.environ["PATH"].split(os.pathsep)
    import databaseDifferentiator
    dbobj = databaseDifferentiator.returndbObject()
    for dir in pathDirs:
        if dir.upper().find(dbobj.getDBString().upper()) > 0 and dir not in result:
            result.append(dir)
            minestar.debug("adding path dll dir " + dir)
    dbLib = dbobj.returnLibraryPath()
    if os.access(dbLib, os.X_OK):
        minestar.debug("adding Db lib dir " + dbLib)
        if dbLib not in result:
            result.append(dbLib)

    if sys.platform.startswith("win") and not "C:\Windows\System32" in result:
        minestar.debug("Adding C:\Windows\System32 to java.library.path")
        result.append("C:\Windows\System32")

    return _removeDuplicates(result)


def __copyTempJars(ufsRoot):
    import stat, shutil
    templib = mstarpaths.interpretPath("{MSTAR_TEMP}/lib")
    try:
        ufsDir = ufsRoot.getSubdir("lib/tmp")
    except:
        return
    libDirs = ufsDir.getPhysicalDirectories()
    for dir in libDirs:
        for file in os.listdir(dir):
            if file[-4:].lower() in mstarpaths.JAR_EXTS:
                src = os.sep.join([dir, file])
                dest = os.sep.join([templib, file])
                copy = 0
                if not os.access(dest, os.F_OK):
                    copy = 1
                else:
                    srcModtime = os.stat(src)[stat.ST_MTIME]
                    destModtime = os.stat(dest)[stat.ST_MTIME]
                    if srcModtime != destModtime:
                        copy = 1
                if copy:
                    try:
                        minestar.makeDirsFor(dest)
                        shutil.copy2(src, dest)
                        minestar.logit("Copy temp jar: from %s to %s" % (src, dest))
                    except:
                        print "Copy failed: %s probably locked by another process" % dest


def configureJava():
    mstarpaths.getInstalledJava(reload=True)


def runJarFile(appName, appConfig, filename, args, busUrl):
    configureJava()
    (jvm, java) = copyJavaExecutable(appName, appConfig, "{MSTAR_TEMP}")
    osIsWindows = sys.platform.startswith("win")
    # do not send all the MineStar stuff to a JAR file app, as it's probably not ours
    jvmArgs = createJvmArgs(appName, appConfig, java, False, osIsWindows, False, True,"{MSTAR_TEMP}")
    jvmArgs.append("-jar")
    jvmArgs.append(filename)
    # bus URL
    if busUrl:
        jvmArgs.append(busUrl)
    # command line arguments
    if args is not None:
        # these args will be quoted by execute, so we don't need to do it here
        jvmArgs = jvmArgs + args
    # For Jetty, if SSL is enabled, enable the 'https' and 'ssl' modules
    if appName == "Jetty":
        appendJettyArgs(jvmArgs)
    # execute
    execute(jvm, jvmArgs, appConfig)


def formJavaConfig(appName, appConfig, classname, args, busUrl, createServiceConfig):
    #minestar.logit("mstarrunlib.formJavaConfig: args %s " % args)
    configureJava()
    if createServiceConfig:
        dir = SERVICE_CONFIG_DIR
    else:
        dir = "{MSTAR_TEMP}"
    (jvm, java) = copyJavaExecutable(appName, appConfig, dir)
    osIsWindows = sys.platform.startswith("win")
    # do we want to generate a short command line?
    reduceCommandLineLength = True
    shorten = not createServiceConfig
    jvmArgs = createJvmArgs(appName, appConfig, java, reduceCommandLineLength, osIsWindows, True, shorten, dir)
    # bus URL
    if busUrl:
        args.insert(0, busUrl)
    jvmArgs.append(classname)
    # command line arguments
    if args is not None:
        # these args will be quoted by execute, so we don't need to do it here
        jvmArgs = jvmArgs + args
    return jvm, jvmArgs


def runJava(appName, appConfig, classname, args, busUrl):
    (jvm, jvmArgs) = formJavaConfig(appName, appConfig, classname, args, busUrl, False)
    execute(jvm, jvmArgs, appConfig)


def _writeWindowsServiceConfig(appName, appConfig, classname, args, busUrl):
    (jvm, jvmArgs) = formJavaConfig(appName, appConfig, classname, args, busUrl, True)
    pid = `os.getpid()`
    javaLibraryPath = getJavaLibraryPathDirs(appConfig)
    _writeWindowsServiceConfigToFile(appName, pid, jvm, javaLibraryPath, jvmArgs, appConfig)


def isBaseJar(filename):
    name = filename.split(os.path.sep)[-1]
    return name.startswith("base-") and name.endswith(".jar") and not isTestJar(filename) and not isSourcesJar(filename)


def isTanukiWrapperJar(filename):
    name = filename.split(os.path.sep)[-1]
    return name.startswith("tanuki-wrapper-") and name.endswith(".jar")


def isSourcesJar(filename):
    name = filename.split(os.path.sep)[-1]
    return name.endswith("-sources.jar")


def isTestJar(filename):
    name = filename.split(os.path.sep)[-1]
    return name.endswith("-tests.jar")


def createJvmArgs(appName, appConfig, java, reduceCommandLineLength, osIsWindows, useMineStar=True, shorten=True,propertyFileDir="{MSTAR_TEMP}"):
    import ufs
    defines = standardDefines(appName, appConfig)
    ufsPath = mstarpaths.interpretVar("UFS_PATH") + ";" + mstarpaths.interpretPath("{MSTAR_TEMP}")
    ufsRoot = ufs.getRoot(ufsPath)
    # class paths
    __copyTempJars(ufsRoot)
    nestedCP = "target/classes"

    (bootClassPath, classPath, classPathDirs, classPathJars) = mstarpaths.buildClassPaths(ufsRoot, reduceCommandLineLength, appConfig.get("extraJars"), appConfig.get("extraCPDirs"), appConfig.get("fixedClassPath"), shorten)

    # Find the class path element containing the M* 'base' module classes.
    # Looking for jar file of the form '${MSTAR_HOME}/lib/base-${version}.jar'. Ignore jars with '-tests' or '-sources' classifier.
    # MO-7908: base is now built externally
    baseClassPath = [x for x in classPath if isBaseJar(x)]
    if len(baseClassPath) == 0:
        raise RuntimeError("Cannot determine base classpath")
    #print "mstarrunlib.createJvmArgs: 1: nestedCP %s mstarpaths.runningFromRepository %s baseClassPath %s " % (nestedCP,mstarpaths.runningFromRepository,baseClassPath)

    # build command line parameters
    jvmArgs = []

    # Relax constraints on access to certain java modules. Otherwise certain operations
    # may not be permitted (e.g. setting properties via reflection).
    # For example, Spring currently has a bug preventing use
    #     https://github.com/spring-projects/spring-framework/issues/22791
    for module in ['java.base/java.lang']:
        jvmArgs.append("--add-opens %s=ALL-UNNAMED" % module)

    vmStyle = appConfig.get("vmstyle")
    if vmStyle:
        vmArg = "-%s" % vmStyle
        jvmArgs.append(vmArg)
    if appConfig.get("enableAssertions"):
        # turn on assertions
        jvmArgs.append("-ea")
    # JVM memory sizes
    javaMemoryOpts = mstarpaths.interpretPathOverride("{JAVA_MEM64}", appConfig)
    if javaMemoryOpts.startswith("{"):
        javaMemoryOpts = mstarpaths.interpretPathOverride("{JAVA_MEM}", appConfig)
    if not javaMemoryOpts.startswith("{"):
        opts = javaMemoryOpts.split()
    else:
        opts = [ "-Xmx256m" ]
    jvmArgs = jvmArgs + opts

    # RMI networking configuration (required for multi-homed hosts)
    javaRmiOpts = mstarpaths.interpretPathOverride("{JAVA_RMI}", appConfig)
    if not javaRmiOpts.startswith("{"):
        jvmArgs = jvmArgs + javaRmiOpts.split()

#    javaProcessDisplayOpts = mstarpaths.interpretPathOverride("{PROCESS_DISPLAYNAME}", appConfig)
#    if not javaProcessDisplayOpts.startswith("{"):
#        javaProcessDisplayOpts="-Dvisualvm.display.name=\"" + javaProcessDisplayOpts + "\""
#        jvmArgs = jvmArgs + javaProcessDisplayOpts.split()
    if mstarpaths.runningFromRepository or appConfig.get("debug"):
        javaDebugOpts = mstarpaths.interpretPathOverride("{DEBUG}", appConfig)
        if not javaDebugOpts.startswith("{"):
            jvmArgs = jvmArgs + javaDebugOpts.split()
    if useMineStar:
        # [Ram Sep-17-2009] To add JMX Port argument
        javaJMXOpts = mstarpaths.interpretFormatOverride("{JMX_PORT}", appConfig)
        if not javaJMXOpts.startswith("{"):
            opts = javaJMXOpts.split()
        else:
            opts = [ "" ]
        jvmArgs = jvmArgs + opts
    if useMineStar:
        # [Ram Sep-17-2009] To add arguments required for heap or thread dump
        javaDiagOpts = mstarpaths.interpretFormatOverride("{JAVA_DIAGNOSTIC_OPTS}", appConfig)
        if not javaDiagOpts.startswith("{"):
            opts = javaDiagOpts.split()
        else:
            opts = [ "" ]
        jvmArgs = jvmArgs + opts

    # JVM profiling
    pid = `os.getpid()`
    javaProfiling = appConfig.get("profiling")
    if javaProfiling is not None:
        _includeJavaProfiling(javaProfiling, jvmArgs, osIsWindows, appName + pid)
        print "Using special JVM args " + str(jvmArgs)
    _includeJavaOptions(appConfig, jvmArgs, defines)
    if useMineStar:
        _includeExtensionOptions(appConfig, jvmArgs, defines)
    # build up JVM args
    if reduceCommandLineLength:
        # work around Windows command line length limitations
        definesFileName = _writeDefinesToFile(appName, propertyFileDir, defines, jvmArgs)
    else:
        for (name, value) in defines.items():
            jvmArgs.append('-D%s=%s' % (name, value))
    # classpaths
    if useMineStar and len(bootClassPath) > 0:
        jvmArgs.append("-Xbootclasspath/p:%s" % os.pathsep.join(bootClassPath))
    # class to run
    #print "mstarrunlib.createJvmArgs: useMineStar %s reduceCommandLineLength %s " % (useMineStar,reduceCommandLineLength)
    if useMineStar:
        if reduceCommandLineLength:
            jvmArgs.append("-Djava.class.path=" + os.pathsep.join(baseClassPath))
            # if classPathDirs is not empty, set the system property
            if classPathDirs:
                # Set minestar.extraCPDirs so the mstarPaths logic implemented in Java will add the directories to the classpath
                jvmArgs.append("-Dminestar.extraCPDirs=" + os.pathsep.join(classPathDirs))
            # if classPathJars is not empty, set the system property
            if classPathJars:
                jvmArgs.append("-Dminestar.fixedClasspath=" + os.pathsep.join(classPathJars))
            jvmArgs.append("minestar.platform.bootstrap.ComplexCommandLine")
            jvmArgs.append(definesFileName)
        else:
            # We're not using the trickery used to reduce the command-line length (because, perhaps, we're running in Linux)
            # So combine the jars and directories onto the same Classpath instead of the directories passed into minestar.extraCPDirs
            cpEntries = []
            if classPathJars:
                cpEntries.extend(classPathJars)
            else :
                cpEntries.extend(classPath)
            # if classPathDirs is not empty, set the system property
            if classPathDirs:
                cpEntries.extend(classPathDirs)
            jvmArgs.append("-Djava.class.path=" + os.pathsep.join(cpEntries))
    return jvmArgs


def _removeDuplicates(items):
    from collections import OrderedDict
    return list(OrderedDict.fromkeys(items))


def _appendOptions(jvmArgs, opts, defines):
    # append -D options, putting them into defines if possible (so they don't go on the command line)
    for opt in opts:
        opt = mstarpaths.interpretFormat(opt)
        if opt.startswith('"') and opt.endswith('"') and opt[1:3] == "-D":
            opt = opt[1:-1]
        if opt.startswith("-D"):
            fields = opt[2:].split("=", 1)
            if len(fields) != 2 or fields[0] in NO_DEFINES:
                jvmArgs.append(opt)
            else:
                defines[fields[0]] = mstarpaths.interpretPath(fields[1])
        else:
            jvmArgs.append(opt)


def _includeExtensionOptions(appConfig, jvmArgs, defines):
    # extension-specific settings
    for extension in mstarpaths.config["LOADED_EXTENSIONS"]:
        extension = extension.root.split('/')[-1]
        key = (extension + "_OPTS").upper()
        value = mstarpaths.interpretVarOverride(key, appConfig)
        if value is not None:
            _appendOptions(jvmArgs, value.split(), defines)


def _includeJavaProfiling(what, jvmArgs, windowsEscaping, appName):
    import mstarapplib
    codes = what.split(",")
    for code in codes:
        opt = mstarapplib.JAVA_PROFILING_OPTIONS.get(code)
        if opt is not None:
            # support substitution of MSTAR_TRACE, appName, etc. into the options
            if opt.find("%s") >= 0:
                opt = mstarpaths.interpretPath(opt % (appName + "_" + code))
            if windowsEscaping and opt.find("=") >= 0:
                opt = '"' + opt + '"'
            jvmArgs.append(opt)


def _includeJavaOptions(appConfig, jvmArgs, defines):
    # other options defined by the user
    javaOpts = getJavaOpts(appConfig)
    if javaOpts:
        _appendOptions(jvmArgs, javaOpts, defines)


def _writeDefinesToFile(appName, dir, defines, jvmArgs):
    # put -D options in a file
    if not minestar.isDirectory(mstarpaths.interpretPath(dir)):
        os.mkdir(mstarpaths.interpretPath(dir))
    definesFileName = mstarpaths.interpretPath("%s/%s.properties" % (dir,appName))
    file = open(definesFileName, "w")
    for (name, value) in defines.items():
        if name not in NO_DEFINES:
            value = "\\\\".join(value.split('\\'))
            file.write("%s=%s\n" % (name, value))
        else:
            jvmArgs.append('-D%s=%s' % (name, value))
    file.close()
    return definesFileName


def _writeOptionsToConfigFile(file, wrapperParameterName, options, i):
    # Writes out an array of options with form 'name=value' or just 'name'.
    # If there is an option -Xbootclasspath/p:<classes>, it is split on the : and the <classes> is passed to mstarpaths.interpretPath. This stops the forward slash in the option name being converted to a backslash
    # If there is an option -Djetty.home=<dirPath>, it makes sure there is a slash on the end of the dirPath
    # Options with form 'name=value' have their value passed to mstarpaths.interpretPath
    # Options that don't contain an equals sign are paassed to mstarpaths.interpretPath before writing out
    # wrapperParameterName is the name of the parameter in the wrapper config file e.g. "wrapper.java.additional"
    # options is the array of options
    # i is the initial value for the wrapper parameter name
    # Returns the next value to use for the wrapper parameter name

    options = _obfuscateJettyPasswords(options)

    for option in options:
        if option.find("-Xbootclasspath/p:") > -1:
            bootClassPath = mstarpaths.interpretPath(option.split("-Xbootclasspath/p:")[1])
            file.write("%s.%s=-Xbootclasspath/p:%s\n" % (wrapperParameterName, i, bootClassPath))
        elif option.find("-createServiceConfig") == -1:
            optionArray = option.split("=")
            if len(optionArray) == 2:
                name = optionArray[0]
                value = mstarpaths.interpretPath(optionArray[1])
                if name == "-Djetty.home":
                    value = "%s%s" % (value, os.sep)
                #print "mstarrunlib._writeOptionsToConfigFile: writing out wrapper option %s as %s=%s" % (option,name,value)
                file.write("%s.%s=%s=%s\n" % (wrapperParameterName, i, name, value))
            else:
                # Fixup some windows escape characters
                value = mstarpaths.interpretPath(option)
                value = value.replace("%%t", "%t")
                #print "mstarrunlib._writeOptionsToConfigFile: writing out wrapper option %s " % option
                file.write("%s.%s=%s\n" % (wrapperParameterName, i, value))
        i = i + 1
    return i


def _obfuscateJettyPasswords(opts):
    """Replace plain text passwords for Jetty with the obfuscated (OBF) equivalent"""
    import passwordUtils
    result = []
    for opt in opts:
        # Check for Jetty password options
        # eg -Djetty.sslContext.keyStorePassword=password
        if opt.find("-Djetty.sslContext.") > -1 and opt.find("Password=") > -1:
            # print "mstarrunlib._obfuscateJettyPasswords: opt %s " % opt
            optTokens = opt.split("=")
            optName = optTokens[0]
            optValue = mstarpaths.interpretPath(optTokens[1])
            if optValue.startswith("OBF:"):
                # Already obfuscated
                # deobfuscatedValue = passwordUtils.deobfuscate(optValue)
                # print "mstarrunlib._obfuscateJettyPasswords: plaintext '%s'" % deobfuscatedValue
                result.append(opt)
            else:
                # print "mstarrunlib._obfuscateJettyPasswords: plaintext '%s'" % optValue
                obfuscatedValue = passwordUtils.obfuscate(optValue)
                # print "mstarrunlib._obfuscateJettyPasswords: obftext '%s'" % obfuscatedValue
                # deobfuscatedValue = passwordUtils.deobfuscate(obfuscatedValue)
                # print "mstarrunlib._obfuscateJettyPasswords: checktext '%s'" % deobfuscatedValue
                # if optValue != deobfuscatedValue:
                #     raise RuntimeError("Obfuscation failure")
                obfucatedOpt = "%s=%s" % (optName, obfuscatedValue)
                result.append(obfucatedOpt)
        else:
            result.append(opt)
    return result


def _writeWindowsServiceConfigToFile(appName, pid, jvm, javaLibraryPath, jvmArgs, appConfig):
    # write config file to run as windows service
    # jvm is the full path to the executable to run
    # javaLibraryPath is the list of directories to put in the library path
    # jvmArgs is the list of args to pass to the jvm
    if not minestar.isDirectory(mstarpaths.interpretPath(SERVICE_CONFIG_DIR)):
        os.mkdir(mstarpaths.interpretPath(SERVICE_CONFIG_DIR))
    serviceConfigFileName = mstarpaths.interpretPath("%s/%sService.conf" % (SERVICE_CONFIG_DIR,appName))

    file = open(serviceConfigFileName, "w")
    file.write("wrapper.java.command=%s\n\n" % jvm)
    # Split the jvmArgs into two lists: The options to pass to the jvm, which begin with a "-"; and a list containing the parameters and main class to run
    # Also, remove the java.library.path option as this is passed in separately
    parameters = []

    # Add the licences
    licenseFile = appConfig.get("wrapperLicense")
    if licenseFile is not None:
        licensePath = mstarpaths.interpretPath("{MSTAR_HOME}/bus/service/%s" % licenseFile)
        file.write("#include %s\n\n" % licensePath)

    # For windows services, the main class must be specified as winServiceMainClass and can only have one of the 3 values checked below
    mainClass = appConfig.get("winServiceMainClass")
    wrapFilename = appConfig.get("winServiceWrapFilename")
    if mainClass=="org.tanukisoftware.wrapper.WrapperSimpleApp":
        if not wrapFilename:
            parameters.append("minestar.platform.bootstrap.ServiceCommandLine")
    if wrapFilename:
        appConfig['wrapperClassPath'] = os.path.join(appConfig['directory'], appConfig['filename'])
    else:
        # Next append the properties file to the parameters
        for arg in jvmArgs:
            if arg.find("%s.properties" % appName) > -1: # Append the properties file
                parameters.append(arg)
                break

    # Next append the overrides file
    if (mainClass=="org.tanukisoftware.wrapper.WrapperSimpleApp" and not wrapFilename) or mainClass=="minestar.platform.bootstrap.ObjectServerWrapperListener": # Append MineStar.overrides file name
        minestarOverridesFile = mstarpaths.interpretPath("{MSTAR_BASE_CENTRAL}/config/MineStar.overrides")
        parameters.append(minestarOverridesFile)
    # For xoc's running using WrapperSimpleApp the 4th parameter is the ObjectServer
    filename = appConfig["filename"]

    # This needs to be handled this way so that we can deal with the new jetty deployment method and tanuki licensing
    # For developers running from the executable jetty start.jar is not a problem, however when running as a service
    # tanuki requires the jar file to not be executable, and to provide the full path to the jar file and in our
    # deployment that means we would require two licenses per deployment, and hence each machine would need two unique
    # licenses unless we had ha standard deployment to a none changeable path.
    if 'winServiceStartClass' in appConfig:
        filename = appConfig['winServiceStartClass']

    if filename[-4:] == '.xoc' and mainClass=="org.tanukisoftware.wrapper.WrapperSimpleApp":
        parameters.append("com.mincom.env.service.server.ObjectServer")
    # Next parameter is the bus url
    if filename[-4:] == '.xoc' or (appConfig.has_key("passBusUrl") and int(appConfig["passBusUrl"])==1):
        parameters.append(createBusUrl())
    # Finally append the file
    parameters.append(filename)
    options = []
    initMemory = None
    maxMemory = None
    classPath = []
    extraCPDirs = None
    for arg in jvmArgs:
        #print "mstarrunlib._writeWindowsServiceConfigToFile: arg %s " % arg
        if arg.find("-") == 0 or arg.find("\"-") == 0:
            if arg.find("-Xms") > -1:
                tmpInit = arg.split("-Xms")[1]
                tmpInit = tmpInit.replace("m", "")
                tmpInit = tmpInit.replace("M", "")
                initMemory = tmpInit
            elif arg.find("-Xmx") > -1:
                tmpMax = arg.split("-Xmx")[1]
                tmpMax = tmpMax.replace("m", "")
                tmpMax = tmpMax.replace("M", "")
                maxMemory = tmpMax
            elif arg.find("java.class.path") > -1:
                classPath = arg.split("=")[1]
            elif arg.find("minestar.fixedClasspath") > -1:
                classPath = arg.split("=")[1]
            elif arg.find("minestar.extraCPDirs") > -1:
                extraCPDirs = arg.split("=")[1]
            elif arg.find("java.library.path") == -1 and arg.find("file.encoding") == -1:
                # it isn't the java.library.path or file.encoding (which are both specified as custom wrapper options)
                options.append(arg.strip("\""))

    #print "mstarrunlib._writeWindowsServiceConfigToFile: mainClass %s " % mainClass
    #print "mstarrunlib._writeWindowsServiceConfigToFile: options %s " % options
    #print "mstarrunlib._writeWindowsServiceConfigToFile: parameters %s " % parameters
    #print "mstarrunlib._writeWindowsServiceConfigToFile: initMemory %s " % initMemory
    #print "mstarrunlib._writeWindowsServiceConfigToFile: maxMemory %s " % maxMemory
    file.write("wrapper.java.mainclass=%s\n\n" % mainClass)
    mstarLib = mstarpaths.interpretPath("{MSTAR_LIB}")

    cpJars = classPath.split(os.pathsep)
    # Remove 'tests' jars from classPath
    cpJars = [x for x in cpJars if not isTestJar(x)]
    # Include tanuki-wrapper in classPath
    i = 1
    for f in os.listdir(mstarLib):
        if isTanukiWrapperJar(f):
            file.write("wrapper.java.classpath.%s=%s\\%s\n" % (i, mstarLib, f))
            i = i + 1
            break

    # If we are using the WrapperJarApp then assume we are launching an 'executable JAR' which does nor require
    # any other classpath.
    if mainClass != "org.tanukisoftware.wrapper.WrapperJarApp":
        # Include other jars in classPath
        for cpJar in cpJars:
            file.write("wrapper.java.classpath.%s=%s\n" % (i,cpJar))
            i = i + 1
        if extraCPDirs:
            cpDirs = extraCPDirs.split(os.pathsep)
            for cpDir in cpDirs:
                file.write("wrapper.java.classpath.%s=%s\n" % (i,cpDir))
                i = i + 1
        wrapperClassPath = appConfig.get("wrapperClassPath")
        if wrapperClassPath is not None:
            for path in wrapperClassPath.split(","):
                file.write("wrapper.java.classpath.%s=%s\n" % (i,mstarpaths.interpretPath(path)))
                i = i + 1
    file.write("\n")

    i = 1
    file.write("wrapper.java.library.path.%s=%s\n" % (i,mstarLib))
    for jlp in javaLibraryPath:
        i = i + 1
        file.write("wrapper.java.library.path.%s=%s\n" % (i,jlp))
    file.write("\n")

    wrapperOpts = getWrapperOpts(appConfig)
    if wrapperOpts:
        options = wrapperOpts

    _writeOptionsToConfigFile(file,"wrapper.java.additional", options, 1)
    file.write("\n")

    if initMemory is not None:
        file.write("wrapper.java.initmemory=%s\n" % initMemory)
    if maxMemory is not None:
        file.write("wrapper.java.maxmemory=%s\n\n" % maxMemory)

    wrapperParameters = appConfig.get("wrapperParameters")
    if wrapperParameters is not None:
        additionalParams = wrapperParameters.split(",")
        if not wrapFilename:
            parameters = additionalParams
        else:
            for additionalParam in additionalParams:
                parameters.append(additionalParam)

    # For Jetty, if SSL is enabled, enable the 'https' and 'ssl' modules
    if appName == "Jetty":
        appendJettyArgs(parameters)

    i = 1
    for param in parameters:
        # I've used interpretFormatOverride because we need to translate variables as for the Jetty parameter Jetty.wrapperParameters={_JETTY_HOME}/etc/jetty.xml
        # but we don't want to use interpretPath because it converts forward slashes to back slashes causing problems with, for example,  MineTracking parameter localhost:14009/minestar
        #print "mstarrunlib._writeWindowsServiceConfigToFile: writing out parameter %s interpreted as %s" % (param,mstarpaths.interpretFormatOverride(param,None))
        file.write("wrapper.app.parameter.%s=%s\n" % (i,mstarpaths.interpretFormatOverride(param,None)))
        i = i + 1
    file.write("\n")

    minestarLoggingConfig = mstarpaths.getOptionSet("/res/MineStarLoggingConfig.properties", "MineStarLoggingConfig")
    logEnabled = minestarLoggingConfig["_WIN_SVC_WRAPPER_LOG_ENABLED"]

    # obtain wrapper startup time for the specific service
    # fetches from a config value set in supervisor - system
    if appName=="CyclesKpiSummaries":
        startupTimeout = mstarpaths.interpretVar("cycleskpisummaries.wrapper.startup.timeout")
    elif appName=="CommsServer":
        startupTimeout = mstarpaths.interpretVar("commsserver.wrapper.startup.timeout")
    elif appName=="FsbServer":
        startupTimeout = mstarpaths.interpretVar("fsbserver.wrapper.startup.timeout")
    elif appName=="GeoServer":
        startupTimeout = mstarpaths.interpretVar("geoserver.wrapper.startup.timeout")
    elif appName=="MineTracking":
        startupTimeout = mstarpaths.interpretVar("minetracking.wrapper.startup.timeout")
    elif appName=="CommsController":
        startupTimeout = mstarpaths.interpretVar("commscontroller.wrapper.startup.timeout")
    elif appName=="CycleGenerator":
        startupTimeout = mstarpaths.interpretVar("cyclegenerator.wrapper.startup.timeout")
    elif appName=="IAssignmentServer":
        startupTimeout = mstarpaths.interpretVar("assignmentserver.wrapper.startup.timeout")
    elif appName=="StandardJobExecutor":
        startupTimeout = mstarpaths.interpretVar("standardjobexecutor.wrapper.startup.timeout")
    else:
        startupTimeout = 900

    file.write("wrapper.lang.windows.encoding=UTF-8\n")
    file.write("wrapper.lang.unix.encoding=UTF-8\n")
    file.write("wrapper.startup.timeout=" + ("%d" % float(startupTimeout)) + "\n")
    if appName != "FsbServer":
        # Disable automatic restart for all processes other than FsbServer
        file.write("wrapper.disable_restarts=TRUE\n" )
        file.write("wrapper.disable_restarts.automatic=TRUE\n" )
    file.write("wrapper.shutdown.timeout=3600\n" )
    file.write("wrapper.jvm_exit.timeout=240\n" )
    file.write("# MineStar processes cannot be individually restarted.  All processes must be restarted in a particular order.\n" )
    file.write("# Disable JVM response checking (set it to only check once a day and never time out) so that JVM restarts are never attempted:\n" )
    file.write("wrapper.ping.interval=3600\n" )
    file.write("wrapper.logfile.close.timeout=-1\n" )
    file.write("wrapper.ping.timeout=0\n" )
    file.write("\n")
    file.write("wrapper.console.format=LTM\n" )
    if logEnabled is None or logEnabled == "true":
        file.write("wrapper.console.loglevel=INFO\n")
    else:
        file.write("wrapper.console.loglevel=NONE\n")
    file.write("wrapper.logfile=%s\n" % mstarpaths.interpretPath("{MSTAR_BASE_LOCAL}/logs/%s_Service_{COMPUTERNAME}_YYYYMMDD.log" % appName) )
    file.write("wrapper.logfile.format=M\n" )
    if logEnabled is None or logEnabled == "true":
        file.write("wrapper.logfile.loglevel=INFO\n" )
    else:
        file.write("wrapper.logfile.loglevel=NONE\n" )
    file.write("wrapper.logfile.maxsize=0\n" )
    file.write("wrapper.logfile.maxfiles=0\n" )
    file.write("wrapper.logfile.rollmode=DATE\n" )
    file.write("wrapper.syslog.loglevel=NONE\n")
    file.write("\n")
    file.write("wrapper.console.title=@app.long.name@\n" )
    file.write("wrapper.ntservice.name=M*%s\n" % appName )
    file.write("wrapper.ntservice.displayname=M*%s\n" % appName )
    description = appConfig.get("description")
    if description is None:
        description = appName
    file.write("wrapper.ntservice.description=%s\n" %  description)

    # Figure out the dependencies of the service. Explicit dependencies are specified in
    # the application config, but there are two exceptions:
    #
    #  1. The MineTracking service is dependent upon the appropriate database service
    #     (if running on the DB server).
    # 
    #  2. The GeoServer service is dependent upon the GeoDatabase service (if GeoDatabase
    #     is a service to be installed on this machine).

    dependency = appConfig.get("dependency")
    secondDependency = None

    # Handle GeoServer.
    if appName == 'GeoServer':
        services = mstarpaths.interpretVar('_START')
        # Remove 'M*GeoDatabase' as a dependency if GeoDatabase not installed on this machine.
        if dependency == 'M*GeoDatabase' and 'GeoDatabase' not in services:
            dependency = None
        # Add 'M*GeoDatabase' as a dependency if GeoDatabase is installed on this machine.    
        elif dependency != 'M*GeoDatabase' and 'GeoDatabase' in services:
            secondDependency = 'M*GeoDatabase'

    # Handle MineTracking.
    if appName == 'MineTracking' and ServerTools.onDbServer():
        secondDependency = dependency
        dependency = _getDatabaseDependency()

    # Write the dependencies (if any).
    i = 1
    if dependency:
        file.write("wrapper.ntservice.dependency.%d=%s\n" % (i, dependency))
        i = i+1
    if secondDependency:
        file.write("wrapper.ntservice.dependency.%d=%s\n" % (i, secondDependency))

    startMode = mstarpaths.interpretVar("_WINDOWS_SERVICES_START_MODE")
    if startMode is None or startMode == "Automatic":
        startMode = "AUTO_START"
    else:
        startMode = "DEMAND_START"

    file.write("wrapper.ntservice.starttype=%s\n" % startMode )
    file.write("wrapper.ntservice.interactive=false\n" )
    if appName == "FsbServer":
        file.write("wrapper.ntservice.recovery.1.failure=RESTART\n")
        file.write("wrapper.ntservice.recovery.2.failure=RESTART\n")
        file.write("wrapper.ntservice.recovery.3.failure=RESTART\n")
        # SHUTDOWN on clean exit
        file.write("wrapper.on_exit.0=SHUTDOWN\n")
        # RESTART on unclean exit (exit code != 0)
        file.write("wrapper.on_exit.default=RESTART\n")

    file.close()
    return serviceConfigFileName


def _getDatabaseDependency():

    """ Get the windows service dependency for the configured database. """
    
    def getSQLServerDependency():
        dbinstance = mstarpaths.interpretVar("_INSTANCE1")
        if dbinstance:
            return "MSSQL$%s" % dbinstance
        import windowsServices
        if windowsServices.isServiceInstalled("MSSQLSERVER"):
            return "MSSQLSERVER"
        if windowsServices.isServiceInstalled("SQLEXPRESS"):
            return "SQLEXPRESS"
        return None

    # Figure out the type of database that is used.    
    import databaseDifferentiator
    db = databaseDifferentiator.returndbObject()
    if db.getDBString() == "sqlserver":
        dependency = getSQLServerDependency()
    else:
        dependency = db.getDBString()+"Service%s" % mstarpaths.interpretVar("_INSTANCE1")
    return dependency


def _writeClasspathToFile(pid, classPath):
    # put classpath in a file
    classpathFileName = mstarpaths.interpretPath("{MSTAR_TEMP}/classpath%s.txt" % pid)
    file = open(classpathFileName, "w")
    for item in classPath:
        file.write("%s\n" % item)
    file.close()
    return classpathFileName


def createBusUrl():
    # The Bus Initialisation Gadget will override _HOME and write it back out so that other stuff can find it
    return mstarpaths.interpretFormat("{_HOME}:{MSTAR_BUS_PORT}/{_BUS_NAME}")


def stripFileName(filename):
    dotPos = filename.rfind('.')
    if dotPos > 0:
        filename = filename[:dotPos]
    filename = os.sep.join(filename.split('/'))
    filename = os.sep.join(filename.split('\\'))
    slashPos = filename.rfind(os.sep)
    if slashPos > 0:
        filename = filename[slashPos+1:]
    return filename


def __getInterpretedArgs(appConfig, key):
    """parse a list of numbers separated by anything"""
    if not appConfig.get(key):
        return []
    s = appConfig[key]
    result = []
    v = 0
    inNum = 0
    for c in s:
        if c in "0123456789":
            inNum = 1
            v = v * 10 + int(c)
        else:
            if inNum:
                result.append(v)
            v = 0
            inNum = 0
    if inNum:
        result.append(v)
    return result


def __runApplication(appConfig, cmdline):
    import i18n, ufs
    # print "mstarrunlib.__runApplication appConfig %s" % appConfig
    # print "mstarrunlib.__runApplication cmdline %s" % cmdline
    if not appConfig.get("quiet"):
        minestar.logit("mstarrun %s" % cmdline)
    if not appConfig.has_key("filename"):
        print i18n.translate("An application definition must have filename attribute: %s") % `appConfig`
        print i18n.translate("The application '%s' may not be defined at all.") % appConfig["appName"]
        sys.exit(43)
    filename = mstarpaths.interpretPath(appConfig["filename"])
    appConfig["filename"] = filename
    if appConfig.has_key("directory"):
        dir = appConfig["directory"]
        dir = mstarpaths.interpretPath(dir)
        if not os.access(dir, os.F_OK | os.X_OK):
            print i18n.translate("Can't access working directory %s") % (dir,)
            sys.exit(199)
        os.chdir(dir)
    # arguments to the target
    if not appConfig.has_key("args"):
        appArgs = []
    else:
        appArgs = appConfig["args"]
    # interpret any args which need to be
    interpretedArgs = __getInterpretedArgs(appConfig, "argpaths")
    for index in interpretedArgs:
        appArgs[index] = mstarpaths.interpretPath(appArgs[index])
    interpretedArgs = __getInterpretedArgs(appConfig, "argformats")
    for index in interpretedArgs:
        appArgs[index] = mstarpaths.interpretFormat(appArgs[index])
    # check to see if this is dealing with a windows service
    if appConfig.has_key("createServiceConfig"):
        createServiceConfig = appConfig["createServiceConfig"]
    else:
        createServiceConfig = 0
    #print "mstarrunlib.__runApplication: createServiceConfig %s " % createServiceConfig

    # should we pass a bus URL?
    passBusUrl = 0
    busUrl = None
    if appConfig.has_key("passBusUrl"):
        passBusUrl = int(appConfig["passBusUrl"])
    # object servers always want a bus URL
    if filename[-4:] == '.xoc':
        passBusUrl = 1
    if passBusUrl:
        busUrl = createBusUrl()
    # make sure we have some sort of app name
    appName = None
    if appConfig.has_key("appName"):
        appName = appConfig["appName"]
    madeUpAppName = 0
    if appName is None:
        madeUpAppName = 1
        appName = stripFileName(filename)
    # now we go silent
    if appConfig.get("silent"):
        sys.__stdin__.close()
        sys.__stderr__.close()
    # try to figure out where the file really is
    if filename.endswith(".mscript") and not os.access(filename, os.F_OK):
        mstarHome = _getMStarHome()
        if filename.startswith(mstarHome):
            filename = filename[len(mstarHome):]
            ufsRoot = ufs.getRoot(mstarpaths.config["UFS_PATH"])
            ufsFile = ufsRoot.get(filename)
            newFileName = None
            if ufsFile is not None:
                newFileName = ufsFile.getPhysicalFile()
            if newFileName is not None:
                filename = newFileName
                appConfig["filename"] = filename
    # now run the target
    if createServiceConfig:
        _writeWindowsServiceConfig(appName, appConfig, filename, appArgs, busUrl)
    elif filename.endswith('.xoc'):
        runObjectServer(appName, appConfig, appArgs, busUrl)
    elif filename.endswith('.py'):
        runPython(appName, appConfig, appArgs, busUrl)
    elif filename.endswith('.eep'):
        runExplorer(appName, appConfig, appArgs)
    elif filename.endswith('.jy'):
        runJython(appName, appConfig, appArgs, busUrl)
    elif filename.endswith('.mscript'):
        runMScript(appName, appConfig, appArgs, busUrl)
    elif filename.endswith('.sh'):
        runShellScript(appName, appConfig, appArgs, busUrl)
    elif filename.lower().endswith('.bat'):
        if not sys.platform.startswith("win") and (os.path.isfile(filename.replace('.bat','.sh'))):
            appConfig["filename"] = filename.replace('.bat','.sh')
            runShellScript(appName, appConfig, appArgs, busUrl)
        else:
            runBatchFile(appName, appConfig, appArgs, busUrl)
    elif filename.lower().endswith('.exe'):
        runWindowsExe(appName, appConfig, appArgs, busUrl)
    elif filename.lower().endswith('.jar'):
        runJarFile(appName, appConfig, filename, appArgs, busUrl)
    elif appConfig.get("extension") == "exe":
        runExecutable(appName, appConfig, appArgs, busUrl)
    else:
        # assume the file name is a class name
        if madeUpAppName:
            appName = filename.split('.')[-1]
        runJava(appName, appConfig, filename, appArgs, busUrl)


def __loadInitial(system, systemSource):
    """Load all configuration and the application registry"""
    import mstarapplib
    mstarpaths.loadMineStarConfig(system, systemSource)
    mstarapplib.loadApplications()
    mstarpaths.setEnvironment()


def __systemExists(system):
    import i18n
    systemHome = mstarpaths.getDirectoryForSystem(system, _getMStarHome(), _getMstarInstall())
    exists = os.access(systemHome, os.F_OK)
    if not exists:
        print i18n.translate("Directory %s does not exist") % systemHome
    return exists


def isRunningMakeSystem(cmdLineConfig):
    if not cmdLineConfig.has_key("filename"):
        return False
    filename = cmdLineConfig["filename"]
    return filename is not None and filename.lower().startswith('makesystem')


def loadSystem(cmdline, expectFilename=0, checkSystemExists=1):
    """Parse the command line and load the configuration for the correct system"""
    import i18n, mstarapplib
    (cmdLineConfig, systemSource) = mstarapplib.parseCommandLine(cmdline, expectFilename)
    system = cmdLineConfig["system"]
    if isRunningMakeSystem(cmdLineConfig):
        checkSystemExists = False
        if cmdLineConfig.has_key('args'):
            systemArg = cmdLineConfig['args']
            if systemArg is not None and len(systemArg) >= 1:
                system = systemArg[0]
                systemSource = "(makeSystem)"
    if checkSystemExists and not __systemExists(system):
        minestar.fatalError("mstarrun", i18n.translate("System '%s' does not exist") % system)
    __loadInitial(system, systemSource)
    return cmdLineConfig

def updatePythonPath():
    # Remove pythonPathUpdater module if it is already loaded (ensures that the python script
    # from '${MSTAR_HOME}' is used instead of from '${MSTAR_INSTALL}/mstarHome').
    if 'pythonPathUpdater' in sys.modules:
        module = sys.modules['pythonPathUpdater']
        if module and module.__name__ != '__main__':
            del sys.modules[module.__name__]
    # This should load the most recent python path updater.
    import pythonPathUpdater
    # Verify that MSTAR_INSTALL and MSTAR_HOME are defined.
    if 'MSTAR_INSTALL' not in os.environ:
        raise RuntimeError("Cannot update python path: MSTAR_INSTALL not specified in OS environment.")
    mstarInstall = os.environ['MSTAR_INSTALL']
    if 'MSTAR_HOME' not in os.environ:
        raise RuntimeError("Cannot update python path: MSTAR_HOME not specified in OS environment.")
    mstarHome = os.environ['MSTAR_HOME']
    pythonPathUpdater.PythonPathUpdater(mstarInstall=mstarInstall, mstarHome=mstarHome).updatePath()
    ModuleReloader().reload()

_updatedPythonPath = False


class ModuleReloader(object):

    def reload(self):
        """ Reload modules that are no longer on sys.path (if python path was updated). """
        for moduleName in sys.modules:
            self.reloadModuleIfRequired(moduleName)

    def reloadModuleIfRequired(self, moduleName):
        """ Reloads a module if it is not found on the sys.path (e.g. because path no longer includes /mstar/mstarHome') """
        module = sys.modules[moduleName]
        if module and module.__name__ != '__main__' and hasattr(module, '__file__') and not self.onSysPath(module.__file__):
            mstarrunDebug("reloading module '%s' ..." % module.__name__)
            reload(module)

    def onSysPath(self, path):
        """ Determines if a path is on the sys.path """
        from pathOps import isSubdirectory
        return any(isSubdirectory(path, x) for x in sys.path)


# The python path was updated when mstarrun.py was loaded, but if mstar has been upgraded
# (e.g. from 4.0.8 to 5.0.1) then required python packages have not been installed. So
# update the path again, just in case. But only do this once.
def updatePythonPathIfRequired():
    global _updatedPythonPath
    if not _updatedPythonPath:
        updatePythonPath()
        _updatedPythonPath = True


def run(cmdline, overrides = {}, checkSystemExists=1):
    mstarrunDebug("mstarrunlib: running from %s" % __file__)
    updatePythonPathIfRequired()
    # Parse the command line so we know the system.
    if isinstance(cmdline, types.StringTypes):
        cmdline = cmdline.split()
    elif isinstance(cmdline, types.ListType):
        cmdline = map(str, cmdline)
    cmdLineConfig = loadSystem(cmdline, 1, checkSystemExists)
    import mstarapplib
    appConfig = mstarapplib.buildAppConfig(cmdLineConfig)
    minestar.putAll(overrides, appConfig)
    mstarrunDebug("mstarrunlib: calling '%s' cmdLine" % cmdline)
    __runApplication(appConfig, ' '.join(cmdline))
    return appConfig
