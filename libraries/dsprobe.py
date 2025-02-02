import minestar
logger = minestar.initApp()
import sys, datastore, mstarpaths

if __name__ == '__main__':
    mstarpaths.loadMineStarConfig()
    name = sys.argv[1]
    ds = datastore.getDataStore(name)
    value = ds.probe()
    print value
    if value == "OK":
        value = ds.entityProbe()
        print value
    else:
        print ds.probe("true")
