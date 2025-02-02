# An application to tell you what the valid targets in the application registry are.
import mstarapplib, string, i18n, mstarpaths, sys
import minestar

logger = minestar.initApp()

def printTarget(key):
    desc = None
    descKey = key + ".description"
    if mstarapplib.applications.has_key(descKey):
        desc = mstarapplib.applications[descKey]
    if desc is not None:
        print "%s: %s" % (key, i18n.translate(desc))
    else:
        print key

mstarpaths.loadMineStarConfig()
keys = mstarapplib.findAllTargets()
args = sys.argv[1:]
args = [ a.strip().lower() for a in args ]
for key in keys:
    if len(args) == 0 or args[0] == "all":
        tags = None
        tagsKey = key + ".tags"
        if (len(args) > 0 and args[0] == "all") or not mstarapplib.applications.has_key(tagsKey):
            printTarget(key)
        else:
            tags = mstarapplib.applications[tagsKey]
            tags = tags.split(",")
            doIt = 1
            tags = [ t.strip().lower() for t in tags ]
            if not "development" in tags:
                printTarget(key)
    else:
        operation = "or"
        if "and" in args:
            operation = "and"
        tags = None
        tagsKey = key + ".tags"
        if mstarapplib.applications.has_key(tagsKey):
            tags = mstarapplib.applications[tagsKey]
            tags = tags.split(",")
            tags = [ t.strip().lower() for t in tags ]
            if operation == "or":
                for a in args:
                    if a.lower() in tags:
                        printTarget(key)
                        break
            else:
                match = 1
                for a in args:
                    if a == "and":
                        continue
                    if a.lower() not in tags:
                        match = 0
                        break
                if match:
                    printTarget(key)



