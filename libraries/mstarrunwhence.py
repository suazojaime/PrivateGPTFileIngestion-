# An application to tell you where variable settings are coming from
import mstarpaths, mstarrun
import minestar

logger = minestar.initApp()

def main(args):
    sources = mstarpaths.sources
    keys = mstarpaths.config.keys()
    keys.sort()
    for k in keys:
        v = sources.get(k)
        if v is not None:
            print "%s: %s" % (k, v)
        else:
            print "%s: (unknown)" % k


