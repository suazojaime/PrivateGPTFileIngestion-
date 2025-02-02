import minestar
logger = minestar.initApp()
import mstarpaths, os, mstarrun, i18n, sys, datastore

INSTALL = "_INSTALL"

def getCheckedDataStore(name):
    ds = datastore.getDataStore(name)
    if ds is None or not ds.valid:
        print i18n.translate("Definition for %s is invalid") % name
        sys.exit(2)
    return ds

mstarpaths.loadMineStarConfig()
model = getCheckedDataStore("_MODELDB")
hist = getCheckedDataStore("_HISTORICALDB")
substs = {}
for (key, value) in mstarpaths.config.items():
    substs[key] = value
substs["_MODELMACHINE"] = model.host
substs["_MODELUSER"] = model.user
substs["_MODELPASS"] = model.password
substs["_MODELINST"] = model.instance
substs["_HISTMACHINE"] = hist.host
substs["_HISTUSER"] = hist.user
substs["_HISTPASS"] = hist.password
substs["_HISTINST"] = hist.instance
# some substitutions explicitly require Unix style filenames
substs["_REVHOME"] = minestar.replaceBackslashesWithForwardSlashes(substs["MSTAR_HOME"])
substs["_REVADMIN"] = substs["_REVHOME"] + "/admin"

replacePropertiesFiles = mstarpaths.interpretPath("{MSTAR_HOME}/toolkit/ReplacePropertiesList.txt")
for line in open(replacePropertiesFiles).readlines():
    if len(line) > 0 and line[-1] == '\n':
        line = line[:-1]
    if len(line) == 0 or line.startswith("#"):
        continue
    fields = line.split()
    template = mstarpaths.interpretPath(fields[0])
    dest = mstarpaths.interpretPath(fields[1])
    if template[0] == ".":
        template = substs["MSTAR_HOME"] + template[1:]
    if dest[0] == ".":
        dest = substs["MSTAR_HOME"] + dest[1:]
    minestar.replaceProperties(template, dest, substs)
