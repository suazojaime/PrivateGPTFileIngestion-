# delete old unit test reports

import mstarpaths, minestar, systemReport, os

logger = minestar.initApp()

def deleteExistingReports(reportsDir):
    for filename in os.listdir(reportsDir):
        file = reportsDir + os.sep + filename
        os.remove(file)

mstarpaths.loadMineStarConfig()
reportsDir = mstarpaths.interpretPath("{MSTAR_LOGS}/unittests")
minestar.createExpectedDirectory(reportsDir)
deleteExistingReports(reportsDir)
