__version__ = "$Revision: 1.29 $"

import os, sys, string, time
import minestar, i18n, mstarpaths, mstarrun, mstarapplib

logger = minestar.initApp()

ALL_GROUPS = ['Admin', 'Client', 'Server']
ALL_GROUPS.sort()

def createShortcut(linkName, directory, target, args="", system=None, mstarrunOptions=None):
    """If target is None, mstarrun is used. """
    #logger.info("makeShortcuts.createShortcut(linkName=%s,directory=%s,target=%s,args=%s,system=%s,mstarrunOptions=%s): Started" %(linkName, directory, target, args, system, mstarrunOptions))
    if target is None or target == "mstarrun":
        # Special stuff for mstarrun
        if system is not None:
            args = "-s %s %s" % (system,args)
        if mstarrunOptions is not None:
            args = "-%s %s" % (mstarrunOptions,args)
    import createShortcut
    #logger.info("makeShortcuts.createShortcut: Calling createShortcut.createShortcut(%s,%s,%s,%s) " % (linkName, directory, target, args))
    createShortcut.createShortcut(linkName, directory, target, args)
    #logger.info("makeShortcuts.createShortcut: Finished")

def createEmptyDirectories(shortcutDir, shortcutSubDir=None):
    if os.access(shortcutDir, os.F_OK):
        minestar.rmdir(shortcutDir)
    if not os.access(shortcutDir, os.F_OK):
        minestar.createExpectedDirectory(shortcutDir)
    if shortcutSubDir != None:
        if os.access(shortcutSubDir, os.F_OK):
            minestar.rmdir(shortcutSubDir)
        os.mkdir(shortcutSubDir)

def makeClientShortcuts(system, clientDesktop, lang, mstarrunOptions=None):
    createEmptyDirectories(clientDesktop)
    #os.chdir(clientDesktop)
    mstarLocal = mstarpaths.interpretPath("{MSTAR_BASE_LOCAL}")
    batchFile = "mstarrun"
    args = mstarpaths.interpretPath("client")
    title = i18n.translate("Client (%s)", lang) % system
    linkName = "%s/%s" % (clientDesktop,title)
    createShortcut(linkName, mstarLocal, batchFile, args, system, mstarrunOptions)
    title = i18n.translate("Client Slow Link (%s)", lang) % system
    linkName = "%s/%s" % (clientDesktop,title)
    createShortcut(linkName, mstarLocal, batchFile, args + " slowlink.eep", system, mstarrunOptions)
    supervisor = mstarpaths.interpretPath("supervisor")
    title = i18n.translate("Supervisor (%s)", lang) % system
    linkName = "%s/%s" % (clientDesktop,title)
    createShortcut(linkName, mstarLocal, batchFile, supervisor, system, mstarrunOptions)
    title = i18n.translate("Supervisor Slow Link (%s)", lang) % system
    linkName = "%s/%s" % (clientDesktop,title)
    createShortcut(linkName, mstarLocal, batchFile, supervisor + " slowlink.eep", system, mstarrunOptions)
    if system != "main":
        simulatorClient = mstarpaths.interpretPath("simulatorClient")
        title = i18n.translate("Mine Simulator (%s)", lang) % system
        linkName = "%s/%s" % (clientDesktop,title)
        createShortcut(linkName, mstarLocal, batchFile, simulatorClient + ".eep", system, mstarrunOptions)

def makeServerShortcuts(system, serverDesktop, lang, targets=None, mstarrunOptions=None):
    createEmptyDirectories(serverDesktop)
    #os.chdir(serverDesktop)
    # use mstarHome as the directory to start in, because mstarrun will change
    # directories anyway
    mstarHome = mstarpaths.interpretVar("MSTAR_HOME")
    batchFile = "mstarrun"
    # get the list of targets to be started - None implies to use the default
    if targets is None:
        targets = mstarpaths.interpretVar("_START")
    fields = targets.split(",")
    windowsServicesEnabled = mstarpaths.interpretVar("_WINDOWS_SERVICES_ENABLED");
    if windowsServicesEnabled=="true":
        title = i18n.translate("Start Services (%s)", lang) % system
        linkName = "%s/%s" % (serverDesktop,title)
        createShortcut(linkName, mstarHome, batchFile, "windowsServices start &pause", system, mstarrunOptions)
        title = i18n.translate("Stop Services (%s)", lang) % system
        linkName = "%s/%s" % (serverDesktop,title)
        createShortcut(linkName, mstarHome, batchFile, "windowsServices stop &pause", system, mstarrunOptions)
    else:
        index = 0
        maxIndex = len(fields) - 1
        letters = "abcdefghijklmnopqrstuvwxyz"
        if len(fields) > 1:
            for appName in fields:
                config = mstarapplib.getApplicationDefinition(appName)
                shortName = appName
                if config.has_key("shortName"):
                    shortName = config["shortName"]
                title = i18n.translate("1%s Start %s", lang) % (letters[index], shortName) 
                linkName = "%s/%s" % (serverDesktop,title)
                createShortcut(linkName, mstarHome, batchFile, appName, system, mstarrunOptions)
                if config.has_key("shutdown"):
                    shutdown = config["shutdown"]
                    title = i18n.translate("3%s Stop %s", lang) % (letters[maxIndex - index], shortName)
                    linkName = "%s/%s" % (serverDesktop,title)
                    createShortcut(linkName, mstarHome, batchFile, shutdown, system, mstarrunOptions)
                restart = "restart %s" % appName
                title = i18n.translate("2%s Restart %s", lang) % (letters[index], shortName)
                linkName = "%s/%s" % (serverDesktop,title)
                createShortcut(linkName, mstarHome, batchFile, restart, system, mstarrunOptions)
                index = index + 1
        title = i18n.translate("4a Start System (%s)", lang) % system
        linkName = "%s/%s" % (serverDesktop,title)
        createShortcut(linkName, mstarHome, batchFile, "startSystem", system, mstarrunOptions)
        title = i18n.translate("4b Stop System (%s)", lang) % system
        linkName = "%s/%s" % (serverDesktop,title)
        createShortcut(linkName, mstarHome, batchFile, "stopSystem", system, mstarrunOptions)

def makeAdminShortcuts(system, adminDesktop, lang, mstarrunOptions=None):
    # NOTE: Most admin merged into supervisor, i.e. admin shortcuts should be very few!
    createEmptyDirectories(adminDesktop)
    #os.chdir(adminDesktop)
    toolkit = mstarpaths.interpretPath("{MSTAR_TOOLKIT}")
    mstarHome = mstarpaths.interpretPath("{MSTAR_HOME}")
    batchFile = "mstarrun"
    title = i18n.translate("Snapshot System (%s)", lang) % system
    includeDXFAndOnboard = mstarpaths.interpretVar("SNAPSHOT_INCLUDE_DXF_AND_ONBOARD")
    if includeDXFAndOnboard == "true":
        args = "snapshotSystem -d -o USER"
    else:
        args = "snapshotSystem USER"
    linkName = "%s/%s" % (adminDesktop,title)
    createShortcut(linkName, toolkit, batchFile, args, system, mstarrunOptions)



def makeShortcuts(groups, system, lang="en", serverListAsStr=None, mstarrunOptions=None, baseDir=None):
    #logger.info("Starting to make shortcuts")
    i18n.loadLanguage(lang)
    if baseDir is None:
        baseDir = mstarpaths.interpretPath("{MSTAR_SYSTEMS}/%s" % system)
    shortcutsDir = os.path.sep.join([baseDir, "shortcuts"])
    import ServerTools;
    for group in groups:
        #logger.info("making %s shortcuts in shortcuts dir %s  ..." % (group,shortcutsDir))
        if group == 'Client':
            print "\nmaking %s shortcuts ..." % group
            clientDesktop = shortcutsDir + os.sep + i18n.translate("ClientDesktop", lang)
            makeClientShortcuts(system, clientDesktop, lang, mstarrunOptions)
        elif group == 'Server' and ServerTools.onAppServer():
            print "\nmaking %s shortcuts ..." % group
            serverDesktop = shortcutsDir + os.sep + i18n.translate("ServerDesktop", lang)
            # no longer used ... machineDesktop = serverDesktop + mstarpaths.interpretPath("/{COMPUTERNAME}")
            makeServerShortcuts(system, serverDesktop, lang, serverListAsStr, mstarrunOptions)
        elif group == 'Admin':
            print "\nmaking %s shortcuts ..." % group
            adminDesktop = shortcutsDir + os.sep + i18n.translate("AdminDesktop", lang)
            makeAdminShortcuts(system, adminDesktop, lang, mstarrunOptions)
        #logger.info("Finished making shortcuts for group  %s in shortcuts dir %s  ..." % (group,shortcutsDir))
    #logger.info("Finished making shortcuts")

## Main program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [
      make_option("-m", "--mstarrunOpts", metavar="OPTS", help="Pass -OPTS to mstarrun for each of the target names"),
    ]
    argumentsStr = "[groups] ..."
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Show list of groups if requested
    if len(args) == 0:
        print "Basic usage:"
        print "  makeShortcuts                  - show list of groups"
        print "  makeShortcuts [options] all    - make all shortcuts"
        print "  makeShortcuts [options] x ...  - make the specified group of shortcuts"
        print "Use the -h option to obtain help on the available options."
        print "Group names are %s." % string.join(ALL_GROUPS, ', ')
        minestar.exit(0)

    # Make the nominated list of groups
    mstarrunOptions = options.mstarrunOpts
    if args[0] == 'all':
        groups = ALL_GROUPS
    else:
        groups = args
    mstarpaths.loadMineStarConfig()
    system = mstarpaths.interpretPath("{MSTAR_SYSTEM}")
    baseDir = mstarpaths.interpretPath("{MSTAR_SYSTEMS}/%s" % system)
    lang = mstarpaths.interpretVar("_LANGUAGE")
    makeShortcuts(groups, system, lang, mstarrunOptions=mstarrunOptions, baseDir=baseDir)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
