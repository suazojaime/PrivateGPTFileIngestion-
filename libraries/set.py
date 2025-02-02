import os
import minestar

logger = minestar.initApp()

keys = os.environ.keys()[:]
keys.sort()
for key in keys:
    print "%s=%s" % (key, os.environ[key])
