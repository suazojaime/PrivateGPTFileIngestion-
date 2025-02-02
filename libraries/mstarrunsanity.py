# An application to check mstarrun definitions and make sure they are sensible
import mstarapplib, string, i18n, sys, os, mstarpaths
import minestar

logger = minestar.initApp()

# known typos
BAD_SUBKEYS = ["passBusURL", "argCheck"]

mstarpaths.loadMineStarConfig()
mstarapplib.loadApplications()

applications = mstarapplib.applications
appSources = mstarapplib.appSources
# check for keys which I know are errors
for (key, value) in applications.items():
    if key.find('.') < 0:
        print "Invalid key: " + key
    elif len(string.split(key, '.')) > 2:
        print "Strange key: " + key
    else:
        appName = key[:key.find('.')]
        subkey = key[len(appName)+1:]
        if subkey in BAD_SUBKEYS:
            print "Key " + key + " is wrong"
# look for targets defined in multiple files
for (appName, sources) in appSources.items():
    if len(sources) > 1:
        print "%s is defined in multiple files: %s" % (appName, `sources`)
# check all target files exist
targets = mstarapplib.findAllTargets()
for target in targets:
    defn = mstarapplib.getApplicationDefinition(target)
    if not defn.has_key("description"):
        print "Target '%s' has no description" % target
    if defn.has_key("filename"):
        filename = defn["filename"]
        if filename.find(".") < 0:
            # filename is an mstarrun target
            if filename not in targets:
                print "Filename for target '%s' has unknown filename '%s'" % (target, filename)
        else:
            filename = mstarpaths.interpretPath(filename)
            if filename.find(os.sep) < 0:
                # Java class?
                pass
            else:
                filenameToCheck = mstarpaths.interpretPath("{MSTAR_HOME}" + os.sep + filename)
                if not os.access(filenameToCheck, os.F_OK):
                    print "File for target '%s' does not exist: '%s'" % (target, filename)
    else:
        print "Target '%s' has no filename key" % target
