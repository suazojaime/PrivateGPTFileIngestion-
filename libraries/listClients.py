import os, sys, glob, re
import minestar, mstarpaths

logger = minestar.initApp()

def listClients(logsDirectory=None):
    # List the clients that have connected to MineStar by analysing files in logsDirectory. If logsDirectory is None, MSTAR_LOGS is used.

    # Use the default logs directory if required
    if logsDirectory is None:
        mstarpaths.loadMineStarConfig()
        logsDirectory = mstarpaths.interpretPath("{MSTAR_LOGS}")

    # Search the MineTracking logs for client connection details
    computers = {}
    fileNames = glob.glob(os.path.join(logsDirectory, "MineTracking*.log"))
    for fn in fileNames:
        logger.info("searching %s" % fn)
        file = open(fn, "r")
        for line in file.readlines():
            match = re.search(r"on machine (\w+), .* for subscription \'ProxyPubsub client\'", line)
            if match:
                pc = match.group(1)
                computers[pc] = 1
        file.close()

    # Dump the list of PCs
    ids = computers.keys()
    ids.sort()
    logger.info("Actual clients found: %s" % (", ".join(ids)))
    logger.info("Total clients found: %d" % len(ids))

def main(appConfig=None):
    args = appConfig["args"]
    if len(args) == 0:
        dir = mstarpaths.interpretPath("{MSTAR_LOGS}")
    else:
        dir = mstarpaths.interpretPath(args[0])
    listClients(dir)

if __name__ == "__main__":
    """entry point when called from python"""
    main()
