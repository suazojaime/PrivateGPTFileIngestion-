import minestar
logger = minestar.initApp()
import mstarpaths, datastore, mstarrun, os, sys, string, i18n, createDataStores

cwd = os.getcwd()
mstarpaths.loadMineStarConfig()
os.chdir(mstarpaths.interpretPath("{MSTAR_SYSTEM_HOME}"))
# command line parameters
args = sys.argv[1:]
dbName = args[0]
if sys.platform.startswith("win"):
    homeDrive = createDataStores.getLetters(args[1])[0]
else:
    homeDrive = args[1]
db = datastore.getDataStore(dbName)
if db is None:
    print "Definition for %s not found in MineStar properties, use _MODELDB, _HISTORICALDB for example" % dbName
else:
    db.trashInstance(homeDrive, db)
