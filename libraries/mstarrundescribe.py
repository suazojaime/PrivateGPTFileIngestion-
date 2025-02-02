# An application to tell you what the definition for a target is

import minestar

logger = minestar.initApp()

def main(args):
    import mstarapplib, i18n, sys, mstarpaths
    mstarpaths.loadMineStarConfig()
    mstarapplib.loadApplications()
    params = args["args"]
    verbose = 0
    for appName in params:
        if appName.startswith("-"):
            verbose = 1
            continue
        if not mstarapplib.appSources.has_key(appName):
            appName = mstarapplib.getUnambiguousMatchOrFail(appName)
        defn = mstarapplib.getApplicationDefinition(appName)
        # where is it defined?
        sources = mstarapplib.appSources[appName]
        print "Application %s is defined in %s" % (appName, `sources`)
        if verbose:
            defn = mstarapplib.buildAppConfig({ "filename" : appName, "args" : [], "system" : args["system"] })
        # the definition
        keys = defn.keys()[:]
        keys.sort()
        for key in keys:
            print "%s=%s" % (key, defn[key])
        print
