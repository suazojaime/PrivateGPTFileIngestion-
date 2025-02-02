import minestar

logger = minestar.initApp()

def reimport(args):
    import datastore, minestar
    ds = datastore.getDataStore(args[0])
    filename = args[1]
    if ds is None:
        minestar.fatalError("reimport", "Datastore %s not found" % args[0])
    else:
        print "Import %s to %s" % (filename, ds.connectionString)
        ds.reimport(filename,ds)

if __name__ == '__main__':
    import mstarrun, sys, mstarpaths
    mstarpaths.loadMineStarConfig()
    config = mstarrun.loadSystem(sys.argv[1:])
    args = config["args"]
    reimport(args)
