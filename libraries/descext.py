import mstarpaths, os, mstarext
import minestar

logger = minestar.initApp()

def main(args):
    zexts = mstarext.findZippedExtensions(mstarpaths.config)
    args = args['args']
    for arg in args:
        print
        for (k, v) in zexts.items():
            for (k2, v2) in v.items():
                if v2.root == arg:
                    print "Version %s is in file %s" % (k2, v2.filename)
                    print "Compulsory: " + `v2.compulsory`
                    print "Invisible: " + `v2.invisible`
                    print "Reasons: " + `v2.reasons`
        names = mstarext.getAllUnzippedExtensionNames(mstarpaths.config)
        names = [ str(mstarext.canonicaliseExtensionName(name)) for name in names ]
        if arg in names:
            dir = mstarpaths.interpretPath("{MSTAR_HOME}/ext/%s" % arg)
            if os.access(dir, os.F_OK):
                print "Found unzipped in " + dir
