# An application to tell you what the valid targets in the application registry are.
import mstarapplib, string, i18n, mstarpaths, os
import minestar

logger = minestar.initApp()

doc = []

def loadDoc():
    global doc
    docFileName = mstarpaths.interpretPath("{MSTAR_HOME}/bus/mstarrun/targetdoc.txt")
    if os.access(docFileName, os.R_OK):
        docFile = open(docFileName)
        doc = [ line.strip() for line in docFile.readlines() ]
        for line in doc:
            if len(line) > 0 and line[-1] == "\n":
                line = line[:-1]
        docFile.close()

def findDocFor(target):
    using = 0
    opening = "[%s]" % target
    text = ""
    for line in doc:
        if line == opening:
            using = 1
        elif line.startswith("[") and line.endswith("]") and using:
            break
        elif using:
            text = text + line + "\n"
    return text

mstarpaths.loadMineStarConfig()
targets = mstarapplib.findAllTargets()
appSources = mstarapplib.appSources
mstarHome = mstarpaths.interpretPath("{MSTAR_HOME}")
loadDoc()
print "<HTML><HEAD><TITLE>Mstarrun Targets</TITLE></HEAD><BODY>"
print "<h1>Mstarrun Targets</H1>"
print "<TABLE>"
colours = ["cccccc", "ffff99", "ffcccc", "ddddff", "ccffcc"]
i = 0
for target in targets:
    defn = mstarapplib.getApplicationDefinition(target)
    del defn["appName"]
    # name and description
    desc = None
    if defn.has_key("description"):
        desc = defn["description"]
    colour = colours[i%len(colours)]
    print '<TR><TD BGCOLOR="%s">' % colour
    if desc is not None:
        desc = i18n.translate(desc)
        if not desc.endswith("."):
            desc = desc + "."
        print '<DT>%s<DD><B>%s</B><BR>' % (target, desc)
        del defn["description"]
    else:
        print '<DT>%s<DD>' % target
    # sources of the definition
    sources = appSources[target]
    for j in range(len(sources)):
        src = sources[j]
        if src.startswith(mstarHome):
            src = src[len(mstarHome)+1:]
            sources[j] = src
    print "<I>This target is defined in %s</I>" % string.join(sources, ", ")
    targetDoc = findDocFor(target)
    if len(targetDoc) > 0:
        print "<P>"
        print targetDoc
    # keys in the definition
    keys = defn.keys()[:]
    if len(keys) > 0:
        keys.sort()
        print "<TABLE BORDER=1>"
        for key in keys:
            print "<TR><TD>%s</TD><TD>%s</TD></TR>" % (key, defn[key])
        print "</TABLE>"
    print "</TD></TR>"
    i = i + 1
print "</TABLE>"
print "</HTML></BODY>"
