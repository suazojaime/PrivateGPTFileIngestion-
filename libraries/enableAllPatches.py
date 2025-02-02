import mstarext, os, minestar, mstaroverrides, time, mstarpaths, sys

VERSIONS = "/Versions.properties"
TRUE="true"

class Patch:
    def __init__(self, patchFile):
        self.patchFile = patchFile
        self.zext = mstarext.loadPatchFromFile(self.patchFile)
        self.key = self.zext.patchKey()
        self.id = self.zext.id

    def install(self):
        destFile = os.sep.join([updatesDir, os.path.basename(self.patchFile)])
        minestar.copy(self.patchFile, destFile)
        overrides = mstaroverrides.Overrides()
        overrides.put(VERSIONS, self.key, TRUE)
        overrides.save()
        # wait for file operations to complete
        time.sleep(1)

    def uninstall(self):
        overrides = mstaroverrides.Overrides()
        overrides.remove(VERSIONS, self.key)
        overrides.save()
        # wait for file operations to complete
        time.sleep(1)
        
mstarpaths.loadMineStarConfig()
updatesDir = mstarpaths.interpretPath("{MSTAR_UPDATES}")
args = sys.argv[1:]
onOff = args[0]
done = 0
for filename in args[1:]:
    if not os.access(filename, os.R_OK):
        print "Cannot read file '%s' - no action taken." % filename
        continue
    if os.path.isdir(filename):
        print "%s is a directory - no action taken." % filename
        continue
    p = Patch(filename)        
    if onOff == "on":
        p.install()
        print "%s installed." % p.id
        done = done + 1
    else:
        p.uninstall()
        print "%s uninstalled." % p.id
        done = done + 1
if done:        
    print "Do you need to run makeCatalogs now?"        
