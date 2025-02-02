import minestar

logger = minestar.initApp()

def win32ColorCommand(appConfig):
    if not appConfig.has_key("foreground") and not appConfig.has_key("background"):
        return None
    appFg = "white"
    if appConfig.has_key("foreground"):
        appFg = appConfig["foreground"]
        appFg = appFg.lower()
    appFg = appFg.replace("light ","")
    return "setterm -fore %s -clear all" % appFg

def executeNewWindow(cmd, appName, appConfig):
    import mstarpaths, mstardebug, minestar, os
    scriptName = mstarpaths.interpretPath("{MSTAR_TEMP}/" + appName + `os.getpid()`)
    if appConfig.has_key("unique"):
        scriptName = "%s_%s" % (scriptName, appConfig["unique"])
    if mstardebug.debug:
        print scriptName
    if os.access(scriptName, os.F_OK):
        os.remove(scriptName)
    file = open(scriptName, "w")
    colourCmd = win32ColorCommand(appConfig)
    if colourCmd is not None:
        file.write(colourCmd + "\n")
    file.write(minestar.generateCaptureCommand(cmd, appConfig) + "\n")
    closeWindow = appConfig["closeWindow"]
    if not closeWindow:
        file.write('echo -n "Press any key to close this window "\n')
        file.write("read\n")
    file.close()
    os.chmod(scriptName, 0740)
    minestar.run("bash \"%s\" &" % scriptName)
