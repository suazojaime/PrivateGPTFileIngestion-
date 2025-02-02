# A module to support the MineStar application library
# Also understands about building application configurations
import mstardebug, mstarpaths, string, i18n, sys, os, ufs
import types

# the registry of all applications
APP_REGISTRY="catalogs/Applications.properties"
# known application definitions
applications = None
# files that apps are defined in
appSources = None
# keys which should be interrepted as booleans
BOOLEAN_ITEMS = [ "passBusUrl", "newWindow", "closeWindow", "enableAssertions", "noJavaCopy", "noConsole", "winServiceWrapFilename", "includeBase" ]
# keys which should be interpreted as ints
INT_ITEMS = []

# Map of java tracing codes to actual jvm options - %s is the application name
JAVA_PROFILING_OPTIONS = {
    "yourkit":  "-agentlib:yjpagent",
    "samples":  "-Xrunhprof:cpu=samples,thread=y,depth=12,cutoff=0,file={MSTAR_TRACE}/%s.hprof.txt",
    "times":    "-Xrunhprof:cpu=times,thread=y,depth=12,cutoff=0,file={MSTAR_TRACE}/%s.hprof.txt",
    "heap":     "-Xrunhprof:heap=all,thread=y,depth=12,cutoff=0,file={MSTAR_TRACE}/%s.hprof.txt",
    "basic":    "-Xprof",
    "objects":  "-Xaprof",
    "gc":       "-Xloggc:{MSTAR_TRACE}/%s.gc.txt",
    "cl":       "-verbose:class",
    "jni":      "-verbose:jni",
    "2d":       "-Dsun.java2d.trace=log,timestamp,count",
    "forms":    "-Ddebug.form=true",
    }

def __processSources(keySources):
    global appSources
    appSources = {}
    for (key, source) in keySources.items():
        fields = key.split(".")
        if len(fields) == 2:
            appName = fields[0]
            subkey = fields[1]
            # TODO
            if subkey == "extensions":
                print source
            if appSources.has_key(appName):
                sources = appSources[appName]
                if source not in sources:
                    sources.append(source)
            else:
                appSources[appName] = [source]
        else:
            import i18n
            print i18n.translate("Key '%s' in file %s is wrong") % (key, source)

def loadApplications():
    """
    Load the Applications.properties file
    """
    global applications
    if applications is not None:
        # already loaded
        return
    if mstardebug.debug:
        print "App registry is at %s" % APP_REGISTRY
    (keySources, applications) = ufs.getRoot(mstarpaths.interpretFormat("{UFS_PATH}")).get(APP_REGISTRY).loadJavaStyleProperties([])
    __processSources(keySources)

# Application properties can be specified as any combination of the following
#     appName.propertyKey = valueForAnyHost
#     appName.propertyKey@hostName1 = valueForSpecificHost1
#     appName.propertyKey@hostName2 = valueForSpecificHost2
#     appName.propertyKey@DEV = value when running from repository
#     ...
# The first of the three specifies a value that applies to any host.
# the second and third only apply to the host with name hostName1 and hostName2 respectively.
# Therefore, if you are running mstarrun on the machine hostName1, then valueForSpecificHost1 will be used; if you are running on hostName2, then valueForSpecificHost2
# will be used; and if you are running on any other machine, valueForAnyHost will be used.
# This change was made to allow client memory settings to be associated with the machine the client is running on as Controllers tend to have more powerful PCs.
# See MSTAR-7167
def getHostSpecificConfig(appConfig, atHostName, hostSpecificConfig):
    for (propertyKeyAtHostName, value) in hostSpecificConfig.items():
        if (propertyKeyAtHostName.endswith(atHostName)):
            atPos = propertyKeyAtHostName.find("@")
            propertyKey = propertyKeyAtHostName[:atPos]
            #print "mstarapplib.getApplicationDefinition: picked host specific override: host %s propertyKey %s value %s" % (propertyKeyAtHostName[atPos+1:],propertyKey,value)
            appConfig[propertyKey] = value


def getApplicationDefinition(appName):
    loadApplications()
    appNameDot = appName + "."
    prefixLen = len(appNameDot)
    appConfig = {}
    hostSpecificConfig = {}
    for (key, value) in applications.items():
        if key.startswith(appNameDot):
            propertyKey = key[prefixLen:]
            atPos = propertyKey.find("@")
            #print "mstarapplib.getApplicationDefinition: full key %s propertyKey %s value %s hostLen %s" %(key,propertyKey,value,atPos)
            if (atPos > 0):
                # print "mstarapplib.getApplicationDefinition: value specific to host found: propertyKey %s host %s value %s" % (propertyKey[:atPos],propertyKey[atPos+1:],value)
                hostSpecificConfig[propertyKey]=value
            else:
                appConfig[propertyKey] = value
    # Now run through the host specific config values applying any that apply to the current hostName and throwing the rest away
    import minestar
    atHostName = "@" + minestar.hostname()
    getHostSpecificConfig(appConfig, atHostName, hostSpecificConfig)

    # Support filenames defined with 'regex' matching (eg WebServiceFacade.filename)
    if 'directory' in appConfig and 'filename' in appConfig:
        directory = mstarpaths.interpretPath(appConfig.get('directory'))
        filename = appConfig.get('filename')
        pathname = os.path.join(directory, filename)
        if os.path.exists(directory) and not os.path.exists(pathname):
            import re
            for f in os.listdir(directory):
                if re.match(filename, f):
                    # print "Using %s for %s\n" % (f, filename)
                    appConfig['filename'] = f
                    break

    # A pretty lazy hack but this gives us developer overrides pretty cheaply
    if mstarpaths.runningFromRepository:
        getHostSpecificConfig(appConfig, "@DEV", hostSpecificConfig)
    if not appConfig.has_key("appName"):
        appConfig["appName"] = appName
    return appConfig

def __processCommandLineArgs(args, expectFilename):
    """Process the command line args and return a partial application config.
    """
    cmdLineConfig = {}
    appArgs = []
    inAppArgs = not expectFilename
    eat = 0
    args = args.split() if isinstance(args, types.StringTypes) else args
    for i in range(len(args)):
        arg = args[i]
        if eat:
            eat = eat - 1
        elif inAppArgs:
            appArgs.append(arg)
        elif arg[0] == '-':
            handled = 1
            if len(arg) > 0:
                # if len(arg) > 2 and arg[1] == 'w' and arg[2] == 's':
                if arg == "-ws":
                    cmdLineConfig["createServiceConfig"] = 1
                elif arg[1] == 'a':
                    cmdLineConfig["enableAssertions"] = 1
                elif arg[1] == 'A':
                    cmdLineConfig["enableAssertions"] = 0
                elif arg[1] == 'b':
                    cmdLineConfig["passBusUrl"] = 1
                elif arg[1] == 'B':
                    cmdLineConfig["passBusUrl"] = 0
                elif arg[1] == 'c':
                    cmdLineConfig["noConsole"] = 1
                elif arg[1] == 'C':
                    cmdLineConfig["noConsole"] = 0
                elif arg[1] == 'd':
                    mstardebug.debug = 1
                elif arg[1] == 'D':
                    mstardebug.debug = 0
                elif arg[1] == 'e':
                    cmdLineConfig["debug"] = 1
                elif arg[1] == 'g' and i+1 < len(args):
                    cmdLineConfig["progressFile"] = args[i+1]
                    eat = 1
                elif arg[1] == 'j':
                    cmdLineConfig["noJavaCopy"] = 1
                elif arg[1] == 'J':
                    cmdLineConfig["noJavaCopy"] = 0
                elif arg[1] == 'n' and i+1 < len(args):
                    cmdLineConfig["appName"] = args[i+1]
                    eat = 1
                elif arg[1] == 'p' and i+1 < len(args):
                    if args[i+1] == '?':
                        _dumpProfilingOptions()
                        sys.exit(1)
                    if len(arg) > 2:
                        cmdLineConfig["profiling"] = arg[2:]
                    else:
                        cmdLineConfig["profiling"] = args[i+1]
                        eat = 1
                elif arg[1] == 'P' and i+1 < len(args):
                    cmdLineConfig["profilerFile"] = args[i+1]
                    eat = 1
                elif arg[1] == 's' and i+1 < len(args):
                    cmdLineConfig["system"] = args[i+1]
                    eat = 1
                elif arg[1] == 'w':
                    cmdLineConfig["newWindow"] = 1
                elif arg[1] == 'W':
                    cmdLineConfig["newWindow"] = 0
                else:
                    handled = 0
            else:
                inAppArgs = 1
            if not handled:
                appArgs.append(arg)
        else:
            cmdLineConfig["filename"] = arg
            inAppArgs = 1
    cmdLineConfig["args"] = appArgs
    return cmdLineConfig


def __printUsage():
    print "Usage: mstarrun {OPTION} COMMAND"
    print ""
    print "Options:"
    print ""
    print "  -s <system>          The MineStar system name [default: 'main']."
    print "  -a                   Enable assertions."
    print "  -A                   Disable assertions [default]."
    print "  -b                   Pass the bus URL to the command."
    print "  -B                   Do not pass the bus URL to the command [default]."
    print "  -c                   Not using a console."
    print "  -C                   Using a console [default]."
    print "  -d                   Enable debug output."
    print "  -D                   Disable debug output [default]."
    print "  -j                   Do not make a copy of the Java executable."
    print "  -J                   Copy the Java executable (if required) [default]."
    print "  -w                   Do not open in a new window [default]."
    print "  -W                   Open in a new window."
    print ""
    print "Help Options:"
    print ""
    print "  --help                      Show help message and exit."
    print "  --help:commands             Show available mstarrun commands and exit."
    print "  --help:version              Show the MineStar version and exit."
    print "  --help:release              Show the MineStar release information and exit."
    print "  --help:system               Show the MineStar system information (e.g. for 'main') and exit."
    print "  --help:overrides            Show the MineStar overrides and exit."
    print "  --help:extensions           Show the installed MineStar extensions and exit."
    print "  --help:license              Show the MineStar license information and exit."
    print "  --help:settings             Show the MineStar settings and exit."
    print "  --help:settings:<name>      Show the value for a MineStar setting and exit."
    print "  --help:java                 Show the Java settings and exit."
    print "  --help:java:path            Show the Java paths and exit."
    print "  --help:java:class=<name>    Find a class on the Java path and exit."
    print "  --help:java:resource=<name> Find a resource on the Java path and exit."
    print "  --help:python               Show the Python settings and exit."
    print "  --help:python:path          Show the Python paths and exit."
    print "  --help:ufs:path             Show the UFS paths and exit."
    print ""
    print "Commands:"
    print ""
    print "  Run 'mstarrun --help:commands' to show the available commands."


def __convertCommandLineArgs(args, expectFileName):
    import types
    args = args.split() if isinstance(args, types.StringTypes) else args
    for arg in args:
        # Skip non-options.
        if not arg.startswith("-"):
            break
        # Check for generic help.
        if arg == "--help":
            __printUsage()
            sys.exit(0)
        # Check for specific help.
        elif arg.startswith("--help:"):
            if arg == "--help:commands":
                return (["targets"], True)
            if arg == "--help:version":
                return (["mstarHelpCommand", "version"], True)
            if arg == "--help:release":
                return (["mstarHelpCommand", "release"], True)
            if arg == "--help:system":
                return (["mstarHelpCommand", "system"], True)
            # Check for showing a single setting.
            if arg.startswith("--help:settings:"):
                property = arg[len("--help:settings:"):]
                if property == None or len(property) == 0:
                    print "ERROR: no setting specified."
                    __printUsage()
                    sys.exit(1)
                return (["mstarHelpCommand", "setting", property], True)
            # Check for showing all settings.
            if arg == "--help:settings":
                return (["set"], True)
            if arg == "--help:overrides":
                return (["overrides", "-list"], True)
            if arg == "--help:license":
                return (["licenseHelpApp", "status"], True)
            if arg == "--help:java":
                return (["mstarHelpCommand", "java"], True)
            if arg == "--help:java:path":
                return (["java", "path"], True)
            if arg == "--help:java:system":
                return (["java", "system"], True)
            if arg.startswith("--help:java:class="):
                className = arg[len("--help:java:class="):]
                return (["java", "find-class", className], True)
            if arg.startswith("--help:java:resource="):
                resource = arg[len("--help:java:resource="):]
                return (["java", "find-resource", resource], True)
            if arg == "--help:python":
                return (["mstarHelpCommand", "python"], True)
            if arg == "--help:python:path":
                return (["mstarHelpCommand", "python-path"], True)
            if arg == "--help:ufs:path":
                return (["ufspath"], True)
            if arg == "--help:extensions":
                return (["extensions", "--list"], True)
            # Specific help requested is unknown.
            print "ERROR: unknown help option: '%s'." % arg
            print ""
            __printUsage()
            sys.exit(1)
    return (args, expectFileName)


def _dumpProfilingOptions():
    import i18n
    print i18n.translate("The available profiling codes (and matching jvm options) are:")
    print
    keys = JAVA_PROFILING_OPTIONS.keys()
    keys.sort()
    for key in keys:
        print "%s\t(%s)" % (key,JAVA_PROFILING_OPTIONS[key])
    print
    print i18n.translate("Multiple codes can be specified separated by commas, e.g. -p gc,class")

def parseCommandLine(args, expectFilename):
    """Return command line dict with system set and also source of that system setting (for debugging)"""
    (args, expectFilename) = __convertCommandLineArgs(args, expectFilename)
    cmdLineConfig = __processCommandLineArgs(args, expectFilename)

    # Get the system name and system name source.
    if "system" in cmdLineConfig:
        systemSource = "(command line)"
    elif "MSTAR_SYSTEM" in os.environ:
        cmdLineConfig["system"] = os.environ["MSTAR_SYSTEM"]
        systemSource = "(operating system environment)"
    else:
        cmdLineConfig["system"] = mstarpaths.DEFAULT_SYSTEM
        systemSource = "(default)"

    # Check if extensions should be derived.
    if "extensions" not in cmdLineConfig:
        if "MSTAR_EXTENSIONS" in os.environ:
            cmdLineConfig["extensions"] = os.environ["MSTAR_EXTENSIONS"]

    return (cmdLineConfig, systemSource)

def levenshtein(s1, s2):
    """ Return the Levenshtein Distance between two strings, ie. the minimum number of edits required to
        change s1 to s2.
    >>> levenshtein('a', 'a')
    0
    >>> levenshtein('a', 'b')
    1
    >>> levenshtein('a123', 'a1234')
    1
    >>> levenshtein('Two Very Different Strings', 'not alike at all!')
    21
    """

    len1 = len(s1)
    len2 = len(s2)

    matrix = [range(len1 + 1)] * (len2 + 1)
    for i in range(len2 + 1):
      matrix[i] = range(i, i + len1 + 1)
    for i in range(0, len2):
      for j in range(0, len1):
        if s1[j] == s2[i]:
          matrix[i + 1][j + 1] = min(matrix[i + 1][j] + 1, matrix[i][j + 1] + 1, matrix[i][j])
        else:
          matrix[i + 1][j + 1] = min(matrix[i + 1][j] + 1, matrix[i][j + 1] + 1, matrix[i][j] + 1)
    return matrix[len2][len1]

def getSuggestions(target, apps, max_distance=1):
    """ Return a list of suggested alternatives for an unmatched target.

    >>> getSuggestions('match', ['Match this', 'Match', 'match this', '!match', 'but not this'])
    ['Match this', 'Match', 'match this', '!match']
    >>> getSuggestions('match none', ['match', 'Match', 'No match'])
    []
    """
    lTarget = target.lower()
    return filter(lambda app: app.lower().startswith(lTarget) or levenshtein(lTarget, app.lower()) <= max_distance, apps)

def getUnambiguousMatchOrFail(target):
    import i18n
    import textwrap
    extractApp = lambda key: key[:key.find('.')]
    apps = set(map(extractApp, applications))
    suggested = getSuggestions(target, apps)

    # If suggestion is unambiguous and we only differ in case, then use that
    for suggestedItem in suggested:
        if target == suggestedItem:
            return None
        if target.lower() == suggestedItem.lower():
            newTarget = suggestedItem
            print i18n.translate("Using target '%s' (was '%s')") % (newTarget, target)
            return newTarget
    print i18n.translate("Target '%s' is not defined") % target
    if len(suggested) > 0:
        print "You may need one of these targets:\n  " +  '\n  '.join(textwrap.wrap(', '.join(suggested)))
    sys.exit(125)

def __checkArguments(ac, args, filename):
    if ac.has_key("argcheck"):
        matches = checkArguments(args, ac["argcheck"])
        if isAMatchError(matches):
            print i18n.translate("Incorrect arguments: %s") % `matches`
            if ac.has_key("usage"):
                print i18n.translate("Usage: mstarrun %s %s") % (filename, ac["usage"])
            else:
                print i18n.translate("Usage: mstarrun %s %s") % (filename, ac["argcheck"])
            sys.exit(89)

def buildAppConfig(cmdLineConfig, argumentsChecked=0, skipClean=0):
    if not cmdLineConfig.has_key("filename"):
        print "Usage: mstarrun <something.xoc|eep|py|jy|mscript|sh|bat|exe|<Java class>>"
        sys.exit(1)
    # now try to run the application
    filename = cmdLineConfig["filename"]
    originalFileName = None
    # mstarrun targets can point to other mstarrun targets
    # Each may add parameters, and set new values
    # Values set by a target override those of the target they refer to.
    inApplicationLibrary = 1
    appConfigs = []
    filenames = [filename]
    del cmdLineConfig["filename"]
    # implicitDot gets set when a target defines an extension subkey so that it behaves like
    # the filename is of that type
    implicitDot = 0
    while inApplicationLibrary:
        dotPos = string.find(filename, '.')
        if not implicitDot and dotPos < 0:
            ac = getApplicationDefinition(filename)
            if ac is None or len(ac) == 0:
                break
            if not argumentsChecked:
                argumentsChecked = 1
                __checkArguments(ac, cmdLineConfig["args"], filename)
            ac["appName"] = filename
            appConfigs.append(ac)
            if not ac.has_key("filename"):
                filename = getUnambiguousMatchOrFail(filename)
                #skip if the target is not defined FLT-369
                if filename is None:
                    break
                continue
            filename = ac["filename"]
            if filename in filenames:
                print i18n.translate("Infinite loop in target definitions: %s") % `filenames`
                sys.exit(43)
            filenames.append(filename)
            if ac.get("extension") is not None:
                implicitDot = 1

            # if we are running from the repository then optionally use an alternative filename
            filenameOptions = filename.split("|")
            optNr = 0
            if len(filenameOptions) > 1 and mstarpaths.runningFromRepository:
                optNr = 1
            originalFileName = filenameOptions[optNr]
            filename = mstarpaths.interpretPath(originalFileName)

        else:
            inApplicationLibrary = 0
            cmdLineConfig["filename"] = filename
    appConfig = {}
    argSets = []
    for ac in appConfigs:
        if ac.has_key("args"):
            argSets = [ac["args"]] + argSets
            del ac["args"]
        for (key, value) in ac.items():
            # NOTE: next if test works around a bug - remove once bug fixed!
            if key == "tags" and appConfig.has_key(key):
                continue
            appConfig[key] = value
    # command line settings override those in the registry
    for (key, value) in cmdLineConfig.items():
        appConfig[key] = value
    appConfig["args"] = coalesceArgs(argSets + [cmdLineConfig["args"]])
    appConfig["originalFilename"] = originalFileName
    if skipClean == 0:
        cleanAppConfig(appConfig)
    if not appConfig.has_key("middleware"):
        appConfig["middleware"] = "CORBA"
    if not appConfig.has_key("enableAssertions"):
        appConfig["enableAssertions"] = 0
    if appConfig.has_key("fixedClassPath"):
        origValue=appConfig["fixedClassPath"]
        appConfig["fixedClassPath"] = origValue.replace(";", os.pathsep)
    if appConfig.has_key("extraCPDirs"):
        origValue=appConfig["extraCPDirs"]
        appConfig["extraCPDirs"] = origValue.replace(";", os.pathsep)
    return appConfig

class MatchError:
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return self.message

def isAMatchError(match):
    import types
    return type(match) == types.InstanceType

def matchArgument(actual, pattern):
    """
        Return None or a tuple (pattern, actual)
        If the pattern is wrapped in <>, always match.
        Otherwise, treat it as an RE.
    """
    import re
    if (pattern[0], pattern[-1]) == ("<", ">"):
        return (pattern, actual)
    else:
        match = re.compile(pattern).match(actual)
        if match is None:
            mesg = i18n.translate("Actual '%s' doesn't match pattern '%s'") % (actual, pattern)
            return MatchError(mesg)
        else:
            return (pattern, actual)

def matchArguments(actualArgs, argPattern, fields):
    """
        Return None if the args don't match.
        <identifier> matches any 1 argument
        [identifier] matches 0 or 1 arguments
        ... matches any sequence of args
    """
    if len(actualArgs) == 0 and len(fields) == 0:
        return []
    elif len(fields) == 0:
        return MatchError(i18n.translate("No arguments to match"))
    else:
        # try to match first pattern to first arg
        pattern = fields[0]
        if (pattern[0], pattern[-1]) == ("[", "]"):
            # optional parameter
            if len(actualArgs) == 0:
                return matchArguments(actualArgs, argPattern, fields[1:])
            match = matchArgument(actualArgs[0], pattern[1:-1])
            if isAMatchError(match):
                return matchArguments(actualArgs, argPattern, fields[1:])
            else:
                match = (pattern, actualArgs[0])
                matches = matchArguments(actualArgs[1:], argPattern, fields[1:])
                if isAMatchError(matches):
                    return matches
                else:
                    return [match] + matches
        elif pattern == "...":
            # any number of parameters
            for count in range(len(actualArgs) + 1):
                matches = matchArguments(actualArgs[count:], argPattern, fields[1:])
                if not isAMatchError(matches):
                    return [(pattern, actualArgs[:count])] + matches
            return MatchError(i18n.translate("'...' cannot match any sequence correctly"))
        else:
            if len(actualArgs) == 0:
                return MatchError(i18n.translate("No argument to match '%s'") % pattern)
            match = matchArgument(actualArgs[0], fields[0])
            if isAMatchError(match):
                return match
            matches = matchArguments(actualArgs[1:], argPattern, fields[1:])
            if isAMatchError(matches):
                return matches
            return [match] + matches

def checkArguments(actualArgs, argPattern):
    patternFields = string.split(argPattern)
    matches = matchArguments(actualArgs, argPattern, patternFields)
    return matches

def __parseArgs(str):
    import re
    str = str.strip()
    expr = re.compile("(\"[^\"]*\"|\S+)(?:\s+(\"[^\"]*\"|\S+))*")
    match = expr.match(str)
    if match is not None:
        tok = match.group(1)
        str = str[len(tok):]
        others = __parseArgs(str)
        if others is None:
            others = []
        return [tok] + others
    else:
        return []

def coalesceArgs(argSets):
    "Do all the argument substitutions"
    allArgs = []
    for argSet in argSets:
        if type(argSet) == type(""):
            args = __parseArgs(argSet)
            allArgs.append(args)
        else:
            allArgs.append(argSet)
    while len(allArgs) > 1:
        rhs = allArgs[-1]
        lhs = allArgs[-2]
        result = []
        for i in range(len(lhs)):
            l = lhs[i]
            if l == "%*":
                result = result + rhs
            else:
                lresult = ""
                percent = 0
                for char in l:
                    if char == '%':
                        if percent:
                            lresult = lresult + "%"
                            percent = 0
                        else:
                            percent = 1
                    elif percent:
                        if char == '*':
                            lresult = lresult + string.join(rhs)
                        elif char in "123456789":
                            d = int(char)
                            if d <= len(rhs):
                                lresult = lresult + rhs[d-1]
                        percent = 0
                    else:
                        lresult = lresult + char
                result.append(lresult)
        lhs = result
        allArgs[-2:] = [lhs]
    if len(allArgs) == 0:
        return []
    else:
        return allArgs[0]

def findAllTargets():
    loadApplications()
    keys = []
    for key in applications.keys():
        pos = string.find(key, '.')
        if pos >= 0:
            app = key[:pos]
            if app not in keys:
                keys.append(app)
    keys.sort()
    return keys

def cleanAppConfig(config):
    """Interpret values in the app config which are not meant to be strings"""
    for (key, value) in config.items():
        if key in BOOLEAN_ITEMS:
            config[key] = int(value)
        if key in INT_ITEMS:
            config[key] = int(value)
        if key == "args" and type(value) == type(""):
            config[key] = string.split(value)
    if config.has_key("MSTAR_HOME"):
        # silly to override this
        del config["MSTAR_HOME"]
    if not config.has_key("closeWindow"):
        config["closeWindow"] = 1
    if not config.has_key("system"):
        raise "System not specified"

# Enable doctest
if __name__ == "__main__":
    import doctest
    doctest.testmod()

