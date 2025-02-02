# An application to print the help file for a target

import minestar, sys

logger = minestar.initApp()

def main(args):
    import mstarapplib, i18n, sys, mstarpaths
    mstarpaths.loadMineStarConfig()
    mstarapplib.loadApplications()
    params = args["args"]
    for appName in params:
        if not mstarapplib.appSources.has_key(appName):
            mstarapplib.noSuchTarget(appName)
        defn = mstarapplib.getApplicationDefinition(appName)
        if defn.get('help') is not None:
            f = mstarpaths.interpretPath(defn.get('help'))
            f = open(f)
            for line in f.readlines():
                sys.stdout.write(line)
            f.close()
        else:
            print "No help for '%s'" % appName
