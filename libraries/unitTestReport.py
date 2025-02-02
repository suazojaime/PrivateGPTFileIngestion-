import mstarpaths, minestar, systemReport, os

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()
reportsDir = mstarpaths.interpretPath("{MSTAR_LOGS}/unittests")
minestar.createExpectedDirectory(reportsDir)
sysReportFileName = mstarpaths.interpretPath(reportsDir + os.sep + "index.html")
systemReport.startSystemReport(sysReportFileName)
systemReport.finishSystemReport(sysReportFileName, reportsDir)
