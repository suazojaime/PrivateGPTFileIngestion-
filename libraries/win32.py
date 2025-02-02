#  Copyright (c) 2020 Caterpillar

import minestar

logger = minestar.initApp()

WINDOWS_COLOURS = {
    "black" : '0', "blue" : "1", "green" : "2", "aqua" : "3", "red" : "4", "purple" : "5", "yellow" : "6", "white" : "7",
    "gray" : '8', "light blue" : "9", "light green" : "a", "light aqua" : "b", "light red" : "c", "light purple" : "d",
    "light yellow" : "e", "bright white" : "f", "grey" : "8", "cyan" : "b", "azul" : "1", "amarillo": "6", "negro" : "0",
    "blanco" : "7", "verde" : "2", "rojo" : "4", "gris" : "8"
    }

def win32ColorCommand(appConfig):
    if not appConfig.has_key("foreground") and not appConfig.has_key("background"):
        return None
    fg = "7"
    bg = "0"
    if appConfig.has_key("foreground"):
        appFg = appConfig["foreground"]
        appFg = appFg.lower()
        if WINDOWS_COLOURS.has_key(appFg):
            fg = WINDOWS_COLOURS[appFg]
    if appConfig.has_key("background"):
        appBg = appConfig["background"]
        appBg = appBg.lower()
        if WINDOWS_COLOURS.has_key(appBg):
            bg = WINDOWS_COLOURS[appBg]
    return "color %s%s" % (bg, fg)

def executeNewWindow(cmd, appName, appConfig):
    import mstardebug, os, minestar, mstarpaths, mstarrunlib
    scriptName = mstarpaths.interpretPath("{MSTAR_TEMP}/" + appName + `os.getpid()` + ".bat")
    if mstardebug.debug:
        print scriptName
    if os.access(scriptName, os.F_OK):
        os.remove(scriptName)
    file = open(scriptName, "w")
    colourCmd = win32ColorCommand(appConfig)
    if colourCmd is not None:
        file.write(colourCmd + "\n")
    pyCmd = mstarrunlib.getPythonPath()
    if appConfig.get("noConsole"):
        pyCmd = "start /min " + mstarrunlib.getPythonPath(1)
    file.write(minestar.generateCaptureCommand(cmd, appConfig, pyCmd) + "\n")
    if appConfig.has_key("closeWindow"):
        closeWindow = appConfig["closeWindow"]
    else:
        closeWindow = 1
    if closeWindow:
        file.write("exit\n")
    file.close()
    minestar.runMaybeSavingOutput("start /min \"%s\" \"%s\"" % (appName, scriptName), None)
