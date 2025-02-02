__version__ = "$Revision: 1.10 $"

import os, sys
import minestar, mstarpaths, i18n, mstarrun

logger = minestar.initApp()


__LINUX_DESKTOP_TEMPLATE = """[Desktop Entry]
Encoding=UTF-8
Exec='{target}' {arguments}
Name={name}
Path={dirName}
Terminal=true
TerminalOptions=\s--noclose
Type=Application
"""

def createShortcut(linkName, dirName, target=None, arguments=""):
    """
    Create a shortcut for the native Operating System.
    linkName - the name of the shortcut 
    dirName - the directory to run the command in
    target - the program part of the command to run. If None or "mstarrun", mstarrun is used.
    arguments - the arguments part of the command to run
    """
    if target is None:
        target = "mstarrun"
    if arguments is None:
        arguments = ""
    if sys.platform.startswith("win"):
        if target == "mstarrun":
            target = mstarpaths.interpretPath("{MSTAR_HOME}/bus/bin/mstarrun.bat")
        elif target == "mstarclient":
            target =  mstarpaths.interpretPath("{MSTAR_HOME}/bus/bin/mstarclient.bat")
        elif target == "startjetty":
            target =  mstarpaths.interpretPath("{MSTAR_HOME}/bus/bin/startjetty.bat")
        __createWindowsShortcut(linkName, dirName, target, arguments)
    else:
        if target == "mstarrun":
            target = mstarpaths.interpretPath("{MSTAR_HOME}/bus/bin/mstarrun")
        __createLinuxShortcut(linkName, dirName, target, arguments)

def __createWindowsShortcut(linkName, dirName, target, arguments="", mode="C", description=None):
    #logger.info("createShortcut.__createWindowsShortcut(%s, %s, %s, %s, %s) Started " % (linkName, dirName, target, arguments, mode) )
    # Create a shortcut for Windows. Full details of the options that you can use with the shortcut utility are described in
    # the "Shortcut Creation Options"document stored in the toolkit directory of any MineStar installation.
    linkFileName = mstarpaths.interpretPath(linkName) + ".lnk"
    baseOptionStr = "/F:" + "\"" + linkFileName + "\"" + " /A:" + mode + " /T:" + "\"" + target + "\"" + " /W:" + "\"" + dirName + "\"" + " /R:1 /I:" + target
    if len(arguments) > 0:
       if description == None:
          cmd = ["shortcut", baseOptionStr + " /P:" + "\"" + arguments + "\" > nul"]
          #logger.info("createShortcut.__createWindowsShortcut Running command %s " % cmd)
          mstarrun.run(cmd)
       else:
          mstarrun.run(["shortcut", baseOptionStr + " /D:\"" + description + "\"" + " /P:" + "\"" + arguments + "\" > nul"])
    else:
       if description == None:
          mstarrun.run(["shortcut", baseOptionStr + "  > nul"])
       else:
          mstarrun.run(["shortcut", baseOptionStr + " /D:\"" + description + "  > nul"])
    print i18n.translate("%s generated") % linkFileName
    #logger.info("createShortcut.__createWindowsShortcut(%s, %s, %s, %s, %s) Finished " % (linkName, dirName, target, arguments, mode) )

def __createLinuxShortcut(linkName, dirName, target=None, arguments=""):
    """Create a shortcut for KDE or GNOME."""
    linkFileName = mstarpaths.interpretPath(linkName)
    params = {'dirName': dirName, 'target': target, 'arguments': arguments, 'name': linkName}
    shortcutText = minestar.subst(__LINUX_DESKTOP_TEMPLATE, params)
    try:
        file = open(linkFileName, "w")
        file.write(shortcutText)
        file.close()
        print i18n.translate("%s generated") % linkFileName
    except IOError:
        print i18n.translate("Failed to write to %s") % (linkFileName)


## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = "linkName dirName target [arguments]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Create the shortcut
    linkName = args[0]
    dirName = args[1]
    target = args[2]
    if len(args) > 3:
        arguments = args[3]
    else:
        arguments = None
    createShortcut(linkName, dirName, target, arguments)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
