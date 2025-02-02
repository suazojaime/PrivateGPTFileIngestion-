import minestar

logger = minestar.initApp()

import datastore, sys, mstarpaths

mstarpaths.loadMineStarConfig()
ds = datastore.getDataStore(sys.argv[1])
print ds.javaSelect(sys.argv[2])
