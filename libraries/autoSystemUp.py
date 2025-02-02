import mstarpaths, os, mstarrun, minestar, mstarapplib, i18n, progress, sys

logger = minestar.initApp()

def main(appConfig):
    # get the list of targets to be started
    targets = mstarpaths.interpretVar("_START")
    fields = targets.split(",")
    progress.start(1000, "Bringing the system up")
    perApp = 1.0 / len(fields)

    # We want the services to start in new windows.
    completeAppConfig = { "newWindow" : 1 }
    if appConfig.get("debug"):
        # Propagate the debug if we have it turned on.
        completeAppConfig["debug"] = 1

    try:
        for appName in fields:
            whatsHappening = i18n.translate("Starting %s") % appName
            progress.task(perApp, whatsHappening)
            mstarpaths.loadMineStarConfig(forceReload=1)
            config = mstarapplib.getApplicationDefinition(appName)
            if config.get("beforeStart") is not None:
                mstarrun.run(mstarpaths.interpretPath(config["beforeStart"]))
            mstarrun.run(appName, completeAppConfig)
            if config.get("afterStart") is not None:
                mstarrun.run(mstarpaths.interpretPath(config["afterStart"]))
            progress.done()
        progress.done()
    except:
        progress.fail(sys.exc_info()[0])
