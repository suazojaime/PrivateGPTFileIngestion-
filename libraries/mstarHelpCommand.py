import sys
import mstarpaths


def showVersion():
    version = mstarpaths.interpretVar("CURRENT_BUILD")
    print version
    return 0


def showRelease():
    from install.releaseInfo import ReleaseInfo

    releaseInfo = ReleaseInfo.load(mstarpaths.interpretPath("{MSTAR_HOME}"))
    if releaseInfo is None:
        print "ERROR: Cannot find MineStar release info."
        return 1

    from install.mstarInstall import MStarInstall
    install = MStarInstall.getInstance()

    systemName = mstarpaths.interpretVar("MSTAR_SYSTEM")
    build = install.getMStarBuildForSystemName(systemName)
    if build is None:
        print "ERROR: Cannot find build for MineStar system %s." % systemName
        return 1

    from mstarRelease import MStarRelease
    release = MStarRelease(mstarHome=mstarpaths.interpretVar("MSTAR_HOME"))

    repository = install.installedPackagesRepository

    print "Release           : %s" % releaseInfo.version
    print "Deployment type   : %s" % install.licenseKey.deploymentType
    print "Build version     : %s" % build.version
    print "Build path        : %s" % build.path
    sys.stdout.write("Build dependencies: ")
    prefix = ""
    for dependency in release.dependencies:
        sys.stdout.write("%s%s  [Installed:%s]\n" % (prefix, str(dependency).ljust(32, ' '), repository.containsPackage(dependency)))
        sys.stdout.flush()
        prefix = "                    "
    sys.stdout.flush()
    return 0


def showSystem():
    systemName = mstarpaths.interpretVar("MSTAR_SYSTEM")
    systemPath = mstarpaths.interpretPath("{MSTAR_SYSTEMS}/%s" % systemName)
    print "Name: %s" % systemName
    print "Path: %s" % systemPath
    return 0


def showJava():
    print "Java Home   : %s" % mstarpaths.interpretVar("JAVA_HOME")
    print "Java Version: %s" % mstarpaths.interpretVar("JAVA_VERSION")
    return 0


def showPython():
    print "Python Home   : %s" % mstarpaths.interpretVar("MSTAR_PYTHON")
    return 0


def showPythonPath():
    for path in sys.path:
        print "%s" % path
    return 0


def showSetting(name):
    from configvalue import getConfigValueString
    value = getConfigValueString(config=mstarpaths.getConfig(), key=name)
    print "%s: %s" % (name, value or "(undefined)")


def run(args=[], config={}):
    arg = args[0]
    if arg == "version":
        return showVersion()
    if arg == "release":
        return showRelease()
    if arg == "system":
        return showSystem()
    if arg == "setting":
        return showSetting(args[1])
    if arg == "java":
        return showJava()
    if arg == "python":
        return showPython()
    if arg == "python-path":
        return showPythonPath()
    raise Exception("Unknown command: mstarHelpCommand: '%s'" % arg)


def main():
    mstarpaths.loadMineStarConfig()
    run(args=sys.argv[1:], config=mstarpaths.getConfig())


if __name__ == "__main__":
    """entry point when called from python"""
    main()
