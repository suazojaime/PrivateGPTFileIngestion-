"""
    A library to be shared by all MineStar Python programs.
"""
#  Copyright (c) 2020 Caterpillar

import logging
import os
import signal
import string
import sys

import lineOps
import propertyFileOps

#  --- Global Variables ---

# The cached host name.
_cachedHostName = None


def onWindowsPlatform(platformName=None):
    """Return true if running on Windows platform, false otherwise."""
    platformName = platformName or sys.platform
    return platformName.lower().startswith("win")


def hostname():
    """Get the hostname of the underlying machine."""
    global _cachedHostName
    if _cachedHostName is None:
        _cachedHostName = _lookupHostName()
    return _cachedHostName


def _lookupHostName():
    # On Windows and Linux: 'hostname' should be on the path.
    # Fallback to %COMPUTERNAME% (Windows) and $HOSTNAME (Linux) if 'hostname' call fails.

    def processHostName(s):
        """Get the name from a multipart host name, e.g. 'foo.bar.com' -> 'foo'"""
        return s if '.' not in s else s.split('.')[0]

    try:
        return processHostName(systemEval("hostname"))
    except Exception:
        for key in ['COMPUTERNAME', 'HOSTNAME']:
            if key in os.environ:
                return processHostName(os.environ[key])
    # hostname.exe failed, and no suitable environment variables.
    raise IOError("Cannot determine hostname")


def backupFile(filename, keepOriginal):
    """Make a backup of a file to filename.original"""
    if keepOriginal:
        originalFilename = filename + ".original"
        if os.path.exists(filename) and not os.path.exists(originalFilename):
            # When Zope 2.4 is used, change this to use shutil.copy2 as
            # that's safer in the case when the subsequent write fails!
            os.rename(filename, originalFilename)


def replaceBackslashesWithForwardSlashes(orig):
    return orig.replace("\\\\", "/").replace("\\", "/")


def putAll(srcMap, destMap):
    if srcMap is None:
        return
    for (key, value) in srcMap.items():
        destMap[key] = value


def guessMstarHomeFromExecutable():
    """By looking at where this executable is, guess what MSTAR_HOME should be."""
    mstarHome = sys.argv[0]
    parts = mstarHome.split(os.sep)
    parts = parts[:-3]
    mstarHome = string.join(parts, os.sep)
    return mstarHome


def stripEol(line):
    return lineOps.stripEol(line)


def readLines(filename):
    return lineOps.readLines(filename)


def readOptionalLines(filename):
    return lineOps.readOptionalLines(filename)


def stripPunctuation(str):
    return lineOps.stripPunctuation(str)


def __continueLine(line):
    return lineOps.continueLine(line)


def __cleanLine(line):
    return lineOps.cleanLine(line)


def cleanLines(lines):
    return lineOps.cleanLines(lines)


def parseJavaStylePropertyLine(line):
    return propertyFileOps.parseJavaStylePropertyLine(line)


def loadJavaStyleProperties(filename, filenames=[]):
    return propertyFileOps.loadJavaStyleProperties(filename, filenames)


def loadProperties(filename, filenames=[]):
    return propertyFileOps.loadProperties(filename, filenames)


def replaceProperties(templateFile, destFile, substs):
    return propertyFileOps.replaceProperties(templateFile, destFile, substs)


def runMaybeSavingOutput(cmd, appConfig):
    import mstarpaths

    output = None
    silent = 0
    if appConfig is not None:
        if appConfig.get("output"):
            output = mstarpaths.interpretPathOverride(appConfig["output"], appConfig)
        if "silent" in appConfig:
            silent = appConfig["silent"]
    debug(cmd)
    if output:
        runAndSaveOutput(cmd, output, silent)
    else:
        run(cmd, silent)


def getCurrentTimeConfig():
    import interpreter

    return interpreter.getCurrentTimeConfig()


def getSubprocessOutput(cmd):
    """Runs a command as a system process, piping stderr to stdout, and returning a
       file descriptor containing the combined stdout+stderr output. The caller must
       close this file descriptor."""
    import subprocess
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=False)
    (stdin, stdouterr) = (p.stdin, p.stdout)
    stdin.close()
    return stdouterr


def runAndSaveOutput(cmd, filename, silent=0, noisyWhenPattern=None):
    import mstarpaths
    import re

    filename = mstarpaths.interpretPath(filename)
    debug("Output saved to %s" % filename)
    file = open(filename, "w")
    stdouterr = getSubprocessOutput(cmd)
    if noisyWhenPattern is not None:
        noisyWhenRE = re.compile(noisyWhenPattern)
    while 1:
        line = stdouterr.readline()
        if line == "":
            print("<end of output>")
            break
        if silent > 0 and noisyWhenRE is not None and noisyWhenRE.search(line) is not None:
            silent = 0
        if silent == 0:
            print(line[:-1])
        file.write(line)
        file.flush()
    file.flush()
    file.close()


def generateCaptureCommand(cmd, appConfig, pyCmd="python"):
    import mstarpaths

    capture = mstarpaths.interpretPath("{MSTAR_HOME}/bus/pythonlib/capture.py")
    output = None
    if appConfig is not None and appConfig.get("output"):
        output = mstarpaths.interpretPathOverride(appConfig["output"], appConfig)
    if output:
        newcmd = "%s %s %s %s" % (pyCmd, capture, output, cmd)
        return newcmd
    else:
        return cmd


def run(cmd, silent=0):
    import mstardebug

    debug("Executing '%s'" % cmd)
    if silent:
        # no output allowed
        stdouterr = getSubprocessOutput(cmd)
        if mstardebug.debug:
            while 1:
                line = stdouterr.readline()
                if line == "":
                    break
                line = stripEol(line)
                print("SHHHHH: %s" % line)
    else:
        os.system(cmd)


def _killProcessWindows(process, force=False):
    """Kill a process (e.g. 'moMineTracking') running on a Windows host.
       Returns 0 if the process does not exist, 1 otherwise."""
    # Minimum supported OS is Windows 7, so taskkill should be present.
    # Add .exe to process if required.
    if "." not in process:
        process += ".exe"
    # Create the taskkill command.
    cmd = "taskkill /IM %s %s 1>nul 2>nul" % (process, "/F" if force else "")
    # Run the taskkill command.
    TASKKILL_SUCCESS = 0
    TASSKILL_ACCESS_DENIED = 1
    TASKKILL_NO_SUCH_PROCESS = 128
    try:
        exitCode = os.system(cmd)
        return exitCode in [TASKKILL_SUCCESS, TASKKILL_NO_SUCH_PROCESS]
    except OSError:
        # Process already gone (?)
        return True


def _killProcessLinux(process, force=False):
    """Kill a process (e.g. 'moJetty') running on a Linux host. Returns
       True if the process does not exist; False otherwise."""

    cmd = "ps -augx"  # | grep %s | grep -v grep" % process.replace("mo", "")
    with getSubprocessOutput(cmd) as f:
        for line in f.readlines():
            # Assumes that fields are: USER PID ....
            if process.replace("mo", "") in line:
                pid = int(line.split(None, 2)[1])
                os.kill(pid, signal.SIGTERM)


def killProcess(process, force=False):
    """Kill a process running on the host. Returns True if the process was killed; False otherwise."""
    if onWindowsPlatform():
        return _killProcessWindows(process, force)
    else:
        return _killProcessLinux(process, force)


def processList():
    import mstarpaths
    import platform

    p = platform.platform()
    if onWindowsPlatform(p):
        if not p.startswith("Windows-2000") and not p.startswith("Microsoft_Windows-2000"):
            procListFile = mstarpaths.interpretPath("{MSTAR_TEMP}/procList.txt")
            command = "tasklist.exe > %s" % procListFile
            os.system(command)
        else:
            procListFile = mstarpaths.interpretPath("{MSTAR_TEMP}/procList.txt")
            command = mstarpaths.interpretPath("{MSTAR_TOOLKIT}/pulist.exe > %s" % procListFile)
            os.system(command)
    else:
        os.system("ps augx")


def substFile(srcFilename, destFilename, mappings):
    out = open(destFilename, "w")
    for line in open(srcFilename).readlines():
        line = stripEol(line)
        line = subst(line, mappings)
        out.write(line + "\n")
    out.close()


def subst(pattern, mappings):
    """
    Do substitutions into pattern.
    Get the new values from mappings
    """
    pos = pattern.find('{')
    while pos >= 0:
        pos2 = pattern.find('}', pos + 1)
        var = pattern[pos + 1:pos2]
        val = None
        if var in mappings:
            val = mappings[var]
        if val is None:
            val = "{%s}" % var
        pattern = pattern[:pos] + val + pattern[pos2 + 1:]
        pos = pattern.find('{', pos + 1)
    return pattern


# /Y on Windows means don't prompt for confirmation of overwriting
# >nul: means send output to the null device, i.e. no output
COPY_COMMAND = 'copy /Y "%s" "%s" >nul:'
if not onWindowsPlatform():
    COPY_COMMAND = 'cp "%s" "%s"'


def makeDirsFor(filename):
    """We are going to create filename, so create the directories that it needs."""
    filename = string.replace(filename, "\\", "/")
    parts = filename.split("/")
    dirs = string.join(parts[:-1], os.sep)
    try:
        os.makedirs(dirs)
    except OSError:
        # already exists
        pass


def makeDir(dir):
    import errno
    try:
        os.makedirs(dir)
    except OSError as err:
        # Reraise the error unless it is about an already existing directory
        if err.errno != errno.EEXIST or not os.path.isdir(dir):
            raise


def copy(src, dest, log=False):
    """Copy src file to dest file."""
    makeDirsFor(dest)
    copyresult = 0
    if not onWindowsPlatform():
        src = string.replace(src, "$", "\\$")
        dest = string.replace(dest, "$", "\\$")
    cp = COPY_COMMAND % (src, dest)
    import subprocess
    try:
        subprocess.check_call(cp, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        if log:
            logit("copy %s %s" % (src, dest))
    except OSError as err:
        copyresult = 1
        logit("Failed to copy %s to %s: %s" % (src, dest, err))
    except subprocess.CalledProcessError as err:
        copyresult = 1
        logit("Failed to copy %s to %s: %s" % (src, dest, err))
    return copyresult


def move(src, dest, log=False):
    """Move src file to dest file"""
    import subprocess

    try:
        if not onWindowsPlatform():
            cmd = 'mv "%s" "%s"' % (src, dest)
            subprocess.check_call(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            if log:
                logit(cmd)
        else:
            cmd = 'copy "%s" "%s"' % (src, dest)
            subprocess.check_call(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            if log:
                logit(cmd)
            cmd = 'del "%s"' % src
            subprocess.check_call(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            if log:
                logit(cmd)
    except OSError as err:
        logit("Failed to move %s to %s: %s" % (src, dest, err))
    except subprocess.CalledProcessError as err:
        logit("Failed to move %s to %s: %s" % (src, dest, err))


def __platformPath(path):
    path = string.replace(path, "\\", "/")
    parts = string.split(path, "/")
    return string.join(parts, os.sep)


def unpack(zipf, zipDir):
    """Unpack the files in the ZipFile zip to zipDir"""
    for info in zipf.infolist():
        fullFileName = zipDir + os.sep + __platformPath(info.filename)
        makeDirsFor(fullFileName)
        if not os.path.isdir(fullFileName):
            if os.path.exists(fullFileName):
                os.remove(fullFileName)
            file = open(fullFileName, "wb")
            file.write(zipf.read(info.filename))
            file.close()
    # Changes to be put in later.
    # try:
    #    list = zipf.infolist()
    #    zipFile = zipf
    # except:
    #    zipFile = zipfile.ZipFile(zipf,'r')
    #    list = zipFile.infolist()
    # for info in list:
    #    fullFileName = zipDir + os.sep + __platformPath(info.filename)
    #    makeDirsFor(fullFileName)
    #    if not os.path.isdir(fullFileName):
    #        file = open(fullFileName, "wb")
    #        file.write(zipFile.read(info.filename))
    #        file.close()


def systemEval(command):
    """Execute the command and return the first line of stdout output. EOL will be removed."""
    with os.popen(command, "r") as f:
        return stripEol(f.readline())


def systemEvalErrRaw(command):
    """Execute the command and return all stderr output as a list of lines. EOL will be removed from each line."""
    import subprocess

    p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=False)
    with p.stderr as f:
        return [stripEol(line) for line in f.readlines()]


def systemEvalRaw(command):
    """Execute the command and return all stdout output as a list of lines. EOL will be removed from each line."""
    import subprocess

    p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=False)
    with p.stdout as f:
        return [stripEol(line) for line in f.readlines()]


def systemEval2(command):
    """Execute the command and return the first line of stdout output. EOL will be removed."""
    import subprocess

    p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=False)
    with p.stdout as f:
        return stripEol(f.readline())


def systemEvalErr(command):
    """Execute the command and return all stderr output as a single line. EOL will be removed."""
    import subprocess

    p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=False)
    with p.stderr as f:
        return stripEol(f.read())


def mstarrunEvalRaw(command):
    """mstarrun the command and return the lines of output, or "(no output)" if there was no output."""
    # TODO why not return [] for no output?
    import mstarpaths
    import types

    # Check if command is list of strings (possibly needing quoting).
    if isinstance(command, types.ListType):
        def quoted(s):
            return '"%s"' % s if ' ' in s else s

        parts = [quoted(arg) for arg in command]
        command = " ".join(parts)
    p = _getPythonCommand()
    command = mstarpaths.interpretPath("%s {MSTAR_HOME}/bus/pythonlib/mstarrun.py %s") % (p, command)
    debug("> " + command)
    with os.popen(command, "r") as f:
        output = f.readlines()
    if len(output) == 0:
        return "(no output)"
    return [stripEol(line) for line in output]


def _getPythonCommand():
    import mstarpaths

    # Get the python executable name: 'python' or 'python.exe'.
    python = mstarpaths.interpretFormat("python{EXE}")
    # Check for ${MSTAR_PYTHON}/python.exe, if not found check for ${MSTAR_INSTALL}/python/python.exe
    p = mstarpaths.interpretPath("{MSTAR_PYTHON}/%s" % python)
    if "{MSTAR_PYTHON}" in p:
        p = mstarpaths.interpretPath("{MSTAR_INSTALL}/python/%s" % python)
        if "{MSTAR_INSTALL}" in p:
            p = None
    if p:
        return p
    # Fallback to python on the path.
    return python


def mstarrunEval(command, separator=" "):
    """Invoke the command and return the output as one string."""
    result = mstarrunEvalRaw(command=command)
    return separator.join(result)


def mstarrunEvalLines(command):
    """Invoke the command and return the output as a linefeed separated string."""
    result = mstarrunEvalRaw(command=command)
    return "\n".join(result)


def isDirectory(pathName):
    """Return whether the path is a directory"""
    import stat

    return os.access(pathName, os.F_OK) and stat.S_ISDIR(os.stat(pathName)[stat.ST_MODE])


def rmdir(directory):
    """Recursively delete a directory and its contents."""
    if os.access(directory, os.F_OK):
        for f in os.listdir(directory):
            path = os.path.join(directory, f)
            if isDirectory(path):
                rmdir(path)
            else:
                os.remove(path)
        os.rmdir(directory)


def rmdirWithLogging(directory, logger, justChildren=0):
    # clean out a directory and all children. Returns a tuple of (removedDirectoriesCount,removedFilesCount).
    dirCount = 0
    fileCount = 0
    for f in os.listdir(directory):
        path = "%s%s%s" % (directory, os.sep, f)
        if isDirectory(path):
            try:
                (subDirCount, subFileCount) = rmdirWithLogging(path, logger)
                dirCount += subDirCount
                fileCount += subFileCount
            except OSError as err:
                logger.error("failed to remove directory %s: %s" % (path, err))
        else:
            try:
                os.remove(path)
                fileCount += 1
            except OSError as err:
                logger.error("failed to remove file %s: %s" % (path, err))
    if not justChildren:
        try:
            os.rmdir(directory)
            dirCount += 1
        except OSError as err:
            logger.error("failed to remove directory %s: %s" % (directory, err))
    return dirCount, fileCount


# File used to indicate directory should be cleaned before running a MineStar command
CLEAN_ME_FILE = ".cleanMeOnStartUp"


def createExpectedDirectory(dir):
    """
    Create a directory that other parts of the MineStar system will expect to exist.
    """
    import i18n
    import mstarpaths
    import time

    if dir == '':
        print("WARNING: asked to create a directory called '' - ignoring")
        return
    mode = os.F_OK | os.R_OK | os.W_OK | os.X_OK
    path = mstarpaths.interpretPath(dir)
    if os.access(path, mode):
        cleanMarker = path + os.path.sep + CLEAN_ME_FILE
        if os.path.exists(cleanMarker):
            print("Cleaning %s ..." % path)
            rmdirWithLogging(path, _getLogger(), justChildren=1)
        return
    if not os.access(path, os.F_OK):
        try:
            os.makedirs(path)
        except OSError:
            # wait a second then try again (as Windows seems to need time to catch up after a rmdir sometimes!)
            time.sleep(1)
            os.makedirs(path)
    if not os.access(path, mode):
        # permissions are wrong, try to fix them
        os.chmod(path, 0o755)
    if not os.access(path, mode):
        fatalError(None, i18n.translate("Please create %s so that MineStar can read or write files in it.") % path)


def removeMultiple(pattern):
    import glob

    for file in glob.glob(pattern):
        os.remove(file)


YES = ["YES", "yes", "Y", "y", "1", "on", "ON", "true", "TRUE", "Yes"]
NO = ["NO", "no", "N", "n", "0", "off", "OFF", "false", "FALSE", "No"]


def parseBoolean(s, description):
    """Return whether s looks like a yes or no"""
    if s in YES:
        return 1
    if s in NO:
        return 0
    import i18n
    fatalError(None, i18n.translate("The value '%s' is not an acceptable value for %s") % (s, description))


def getTemporaryFileName(prefix):
    import mstarpaths
    import tempfile

    tempfile.tempdir = mstarpaths.interpretPath("{MSTAR_TEMP}")
    tempName = tempfile.mktemp(prefix)
    return tempName


def fileChooser(startDir, filenamePattern, fileTypeDescription, xy, dialogType):
    """
     * startDir is the directory to start the browsing from.
       Will be subjected to mstarpaths.interpretPath.
       None means "{MSTAR_HOME}"
     * filenamePattern is the pattern for acceptable files.
       Uses Unix-style globbing.
     * fileTypeDescription is a human readable description of what the file type is.
       Will be subjected to i81n.translate, so just send it in English.
     * xy is a string like "300,300" which specifies the (X,Y) coordinates to put
       the dialog at.
     * dialogType must be "open" or "save" to specify the behaviour of the dialog.

    This method returns None if the user cancelled.
    """
    import mstarpaths
    import i18n

    if startDir is None:
        startDir = "{MSTAR_HOME}"
    startDir = mstarpaths.interpretPath(startDir)
    fileTypeDescription = i18n.translate(fileTypeDescription)
    value = mstarrunEval(["com.mincom.tool.scripting.python.FileSelectDialog", startDir, filenamePattern, fileTypeDescription, xy, dialogType])
    if value == "None":
        value = None
    return value


def getSubDictionary(map, keyPrefix):
    """Get the dictionary within map where the keys start with keyPrefix, stripping keyPrefix"""
    if map is None:
        return None
    keyPrefixLength = len(keyPrefix)
    result = {}
    for k in map.keys():
        if k.startswith(keyPrefix):
            subKey = k[keyPrefixLength:]
            result[subKey] = map[k]
    return result


## Controlled Entry & Exit ##

_checkedPythonPath = False


def _fixPythonPath():
    """Fix the Python path so that MineStar patches work as required."""
    # Python implicitly adds the source directory to the front of the search path.
    # We need to undo that behaviour in certain cases or patches can fail.
    global _checkedPythonPath
    if not _checkedPythonPath:
        if len(sys.path) > 1 and sys.path[0] in sys.path[1:]:
            sys.path.pop(0)
        _checkedPythonPath = True


def initApp(loggerName="", fileName=None):
    """
    Initialise the application and return the logger.
    Call this even if no logger is required.
    This method can be called safely any number of times.
    """
    _fixPythonPath()
    return _getLogger(loggerName=loggerName, fileName=fileName)


# Try and ensure our exit handler is always called - process abnormal termination


def sighandler(signum, frame):
    exit(12)


signal.signal(signal.SIGTERM, sighandler)

# Standard exit codes - application specific codes should be 1..9 or >= 20
EXIT_OK       = 0
EXIT_WARNING  = 11
EXIT_ERROR    = 12
EXIT_CRITICAL = 13
EXIT_INTERNAL = 19


def exit(exitCode=-1):
    """Exit the application. MineStar scripts should call this rather than sys.exit() directly"""
    if exitCode == -1:
        # TODO: consult the logging system to set the exit code
        exitCode = EXIT_OK
    logging.shutdown()
    sys.exit(exitCode)


def pauseAndExit(exitCode):
    """Exit the application after pausing"""
    import i18n

    raw_input(i18n.translate("This program will now exit"))
    exit(exitCode)


def pause(msg):
    import i18n

    raw_input(i18n.translate(msg))


## Logging ##

class SyslogHandler(logging.Handler):
    """A logging handler to append entries to the syslog file."""

    def __init__(self, strm=None):
        logging.Handler.__init__(self)

    def flush(self):
        pass

    def emit(self, record):
        logit(_logger.name + " | " + record.getMessage())


class FileLogHandler(logging.Handler):
    """A logging handler to append entries to a file."""
    fileName = None

    def __init__(self, strm=None, fileName=None):
        logging.Handler.__init__(self)
        self.fileName = fileName

    def flush(self):
        pass

    def emit(self, record):
        import mstarpaths

        template = "{MSTAR_LOGS}/%s_{COMPUTERNAME}_{MM}{DD}.log" % self.fileName
        file = mstarpaths.interpretPath(template)
        # (drive,tail) = os.path.splitdrive(os.getcwd())
        # print "minestar.FileLogHandler.emit: Opening log file %s current drive %s ..." % (file,drive)
        try:
            f = open(file, "a")
            formatter = logging.Formatter(fmt="%(levelname)s: %(asctime)s %(message)s", datefmt="%a %d %b %H:%M:%S")
            f.write("%s\n" % formatter.format(record))
            f.close()
        except IOError:
            print("Fatal: Unable to create log file %s" % file)
            print(string)
            exit(EXIT_INTERNAL)


_logger = None


def _getLogger(loggerName="", fileName=None):
    """
    Returns the Logger to use in MineStar scripts.
    Available Logger methods include debug, info, warn, error, exception and critical.
    See the logging library or PEP-282 for further details of usage.
    """
    global _logger
    if _logger is None:
        logging.basicConfig(format='%(name)-12s: %(levelname)-8s: %(message)s')
        _logger = logging.getLogger(loggerName)
        _logger.setLevel(logging.INFO)
        _handler = SyslogHandler()
        _handler.setLevel(logging.WARNING)
        _logger.addHandler(_handler)
    if fileName is not None:
        _handler1 = FileLogHandler(fileName=fileName)
        _handler1.setLevel(logging.INFO)
        _logger.addHandler(_handler1)

    return _logger


def abort(message, level=logging.CRITICAL, exitCode=EXIT_CRITICAL):
    """Log a critical error and abort with the nominated exitCode."""
    _logger.log(level, message)
    exit(exitCode)


def logit(string, overrides=None):
    """Append the message to the system log"""
    import mstarpaths
    import re
    import time

    month = time.strftime("%Y%m")
    template = "{MSTAR_LOGS}/syslog_%s.txt" % month
    template2 = "{MSTAR_ADD_LOGS}/syslog_%s.txt" % month
    if overrides:
        computername = overrides.get("COMPUTERNAME")
        if computername is None:
            computername = "Unknown"
        appServer = overrides.get("_HOME")
        if appServer is None:
            appServer = "AppServer"
        file = mstarpaths.interpretPathOverride(template, overrides)
        file2 = mstarpaths.interpretPathOverride(template2, overrides)
        addLogs = mstarpaths.interpretVarOverride("MSTAR_ADD_LOGS", overrides)
    else:
        computername = mstarpaths.interpretVar("COMPUTERNAME")
        appServer = mstarpaths.interpretVar("_HOME")
        file = mstarpaths.interpretPath(template)
        file2 = mstarpaths.interpretPath(template2)
        addLogs = mstarpaths.interpretVar("MSTAR_ADD_LOGS")
    if addLogs is not None and (addLogs == "" or addLogs.startswith("{")):
        addLogs = None
    timestamp = time.strftime("%a %d %b %H:%M:%S")

    # Strip usernames and passwords from the command
    cleanString = string
    if isinstance(cleanString, str):
        cleanString = re.sub(r"-u \S+", "-u ******", cleanString)
        cleanString = re.sub(r"-p \S+", "-p ******", cleanString)
        cleanString = re.sub(r"-puser:\S+", "-puser:******", cleanString)
        cleanString = re.sub(r"-ppasswd:\S+", "-ppasswd:******", cleanString)

    addLogWorked = 0
    if addLogs and file != file2 and appServer != computername:
        try:
            f = open(file2, "a")
            f.write("%s | %s | %s\n" % (timestamp, computername, cleanString))
            f.close()
            addLogWorked = 1
        except IOError:
            print("Unable to open additional system log file %s" % file2)
    try:
        # (drive,tail) = os.path.splitdrive(os.getcwd())
        # print "minestar.py.logit:  current drive %s file %s ..." % (drive,file)
        f = open(file, "a")
        f.write("%s | %s | %s\n" % (timestamp, computername, cleanString))
        f.close()
    except IOError:
        print("Fatal: Unable to create system log file %s" % file)
        if addLogWorked:
            try:
                error = "Fatal: Unable to create system log file %s" % file
                f = open(file2, "a")
                f.write("%s | %s | %s\n" % (timestamp, computername, error))
                f.close()
            except IOError:
                print("Unable to open additional system log file %s" % file2)
        exit(EXIT_INTERNAL)


def fatalError(appName, message, overrides=None):
    """Log a fatal error to the system log and exit"""
    try:
        if appName is None:
            logit("FATAL: %s" % message, overrides)
        else:
            logit("FATAL %s: %s" % (appName, message), overrides)
    except IOError:
        # that could be what the fatal error is...
        pass
    # Note: this should use _getLogger().critical() at some later date.
    # For 1.3.0.1, we're sticking with print to maximise compatibility.
    print(message)
    exit(EXIT_CRITICAL)


def debug(string):
    """Output a debug message when system debugging is enabled"""
    import mstardebug

    if mstardebug.debug:
        # Note: this should use _getLogger().debug() at some later date.
        # For 1.3.0.1, we're sticking with print to maximise compatibility.
        print(string)


## Command Line Processing ##

def _getUsage(appName="%prog", argumentStr="", purpose=None, version=None):
    """Build a usage message suitable for passing to the optparse library"""
    result = "usage: %s [options] %s" % (appName, argumentStr)
    if purpose is not None and len(purpose.strip()) > 0:
        result += "\npurpose: %s" % purpose
    if version is not None and len(version.strip()) > 0:
        result += "\nversion: %s" % version
    return result


def _getArgCountLimits(argumentsStr):
    """Returns a tuple of minCount,maxCount. If there is no maximum, maxCount is None"""
    if argumentsStr is None:
        return 0, 0
    args = argumentsStr.split()
    maxCount = len(args)
    minCount = maxCount
    for arg in args:
        if arg.startswith('[') and arg.endswith(']'):
            minCount -= 1
    if "..." in args:
        minCount -= 1
        maxCount = None
    return minCount, maxCount


def parseCommandLine(appConfig, version, optionDefns, argumentsStr, purpose=None):
    """
    Parse a command line using parseCommandLine2() after setting defaults by checking appConfig.
    appConfig - a map containing configuration details typically build by mstarrun.
    If appConfig is None, the appName and args for parseCommandLine2() are derived from sys.argv.
    If purpose is None and appConfig is not None, then purpose is taken from the description attribute of appConfig.
    returns (options,args) as returned from parse_args() in the optparse library.
    """
    # Get the application name and command line arguments
    appName = os.path.split(sys.argv[0])[1]
    args = sys.argv[1:]
    if appConfig is not None:
        if "appName" in appConfig:
            appName = appConfig.get("appName")
        if "args" in appConfig:
            args = appConfig.get("args")

    # If not specified, check appConfig for the value to use for other parameters
    if purpose is None and appConfig is not None and "description" in appConfig:
        purpose = appConfig.get("description")
    # NOTE: deriving argumentsStr from argcheck is dangerous as it means scripts behave differently
    # based on how called - python vs mstarrun ...
    # if argumentsStr is None and "argcheck" in appConfig:
    #    # Use argcheck stripping off leading options
    #    parts = appConfig.get("argcheck").split()
    #    while len(parts) > 0 and (parts[0].startswith("[-") or parts[0] == "[options]"):
    #        parts.pop(0)
    #    argumentsStr = " ".join(parts)

    # Call parseCommandLine to do the work
    return parseCommandLine2(args, appName, version, optionDefns, argumentsStr, purpose)


def _getStandardOptions():
    """Get the list of standard options"""
    from optparse import make_option

    return [make_option("-v", "--verbose", action="store_true", help="verbose mode")]


def parseCommandLine2(args, appName, version, optionDefns, argumentsStr, purpose):
    """
    Parse a command line processing the options and checking the count of remaining arguments.
    args - the command line arguments, typically sys.path[1:]
    appName - the application name, typically sys.path[0]
    optionDefns - a list of options (see the optparse library for details)
    argumentStr - a space separated string naming the arguments (... means zero or more args go here)
    purpose - a short string explaining the program
    version - a version string, usually an RCS Revision string
    returns (options,args) as returned from parse_args() in the optparse library.
    """
    import mstardebug
    import optparse

    # Init the app (just in case it hasn't been done yet) and set the logger name
    logger = initApp()
    if appName.endswith(".py"):
        appName = appName[0:-3]
    logger.name = appName

    # Strip the RCS stuff from the version string, if required
    if version is not None and len(version) > 2 and version[0] == '$' and version[-1] == '$':
        version = version[1:-1].strip()
        versionParts = version.split(':')
        if len(versionParts) > 1:
            version = versionParts[1].strip()

    # Add the standard options onto the end of the application specific ones
    allOptionDefns = _getStandardOptions()
    if optionDefns is not None:
        allOptionDefns = optionDefns + allOptionDefns

    # Parse the options
    usage = _getUsage(appName, argumentsStr, purpose, version)
    parser = optparse.OptionParser(usage=usage, option_list=allOptionDefns, version=version)
    (options, args) = parser.parse_args(args)

    # Enable debug if verbose mode is enabled or system debugging is enabled
    if mstardebug.debug or options.verbose:
        logger.setLevel(logging.DEBUG)

    # Check that the count of remaining arguments is legal
    (minCount, maxCount) = _getArgCountLimits(argumentsStr)
    if maxCount is not None:
        argsFound = len(args)
        if minCount == maxCount and argsFound != maxCount:
            abort("incorrect number of arguments - %d expected, %d found" % (maxCount, argsFound))
        elif argsFound < minCount or argsFound > maxCount:
            abort("incorrect number of arguments - %d..%d allowed, %d found" % (minCount, maxCount, argsFound))
    return options, args


def recursiveFileList(base, directory):
    """Get a list of the files contained (recursively) within a directory, relative to the base. """
    directory = os.path.normpath(directory)
    result = []
    for f in os.listdir(directory):
        path = os.path.join(directory, f)
        if os.path.isdir(path):
            result = result + recursiveFileList(base, path)
        else:
            relpath = path[len(base) + 1:]
            result.append(relpath)
    return result


def confirmOperation(msg):
    print(msg)
    reply = raw_input("Confirm [Y/n]")
    if reply != "" and reply.upper() != "Y":
        return 0
    return 1


def readFile(filename):
    """Return the contents of a file, as a string. Returns False if an error occurs reading from the file."""
    try:
        with open(filename, "r") as f:
            return f.read()
    except Exception:
        return False
