import minestar

logger = minestar.initApp()

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
    file.write(minestar.generateCaptureCommand(cmd, appConfig) + "\n")
    closeWindow = appConfig["closeWindow"]
    if not closeWindow:
        file.write('echo -n "Press any key to close this window "\n')
        file.write("read\n")
    file.close()
    os.chmod(scriptName, 0740)
    minestar.run("xterm -T %s -e \"%s\" &" % (appName, scriptName))
