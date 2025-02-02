import mstarpaths, mstarrun, i18n, sys
import minestar

logger = minestar.initApp()

overrides = {}

def createShortcut(linkName, directory, target, args=""):
    directory = mstarpaths.interpretPathOverride(directory, overrides)
    target = mstarpaths.interpretPathOverride(target, overrides)
    mstarrun.run(["createShortcut", i18n.translate(linkName) + ".lnk", directory, target, args])

mstarpaths.loadMineStarConfig()
server = mstarpaths.interpretPath("{_SERVER}")
simulator = mstarpaths.interpretPath("{MSTAR_HOME}/MineSimulator")
simulatorDesktop = mstarpaths.interpretPath("{MSTAR_HOME}/MineSimulator/SimulatorDesktop")
if not os.access(simulator, os.F_OK):
    print i18n.translate("%s does not exist - please create it.")
    sys.exit(12)
if os.access(simulatorDesktop, os.F_OK):
    minestar.rmdir(simulatorDesktop)
os.mkdir(simulatorDesktop)
os.chdir(simulatorDesktop)
overrides["_SIMULATOR"] = simulator
overrides["_MINEEMULATOR"] = mstarpaths.interpretPath(simulator + "/ME")
createShortcut("A - Delete Existing Simulations", simulator, "{_SIMULATOR}/cleanME.bat")
createShortcut("B - Synchronise with Operational Mine Model", "{_SIMULATOR}/DataMigrator", "{_SIMULATOR}/DataMigrator/migrate_op.bat")
createShortcut("C - Start Mine Tracking", "
