import minestar
logger = minestar.initApp()
import mstarpaths, datastore, sys, i18n
import databaseDifferentiator
expcom ="""
SET NOCOUNT ON
Exec InsertGenerator 'R_CALENDAR'
Exec InsertGenerator 'R_CALENDAR_LOOKUP'
Exec InsertGenerator 'R_CUSTOMER_DEFAULTS'
"""
dbobject = databaseDifferentiator.returndbObject()
filename = sys.argv[1]
mstarpaths.loadMineStarConfig()
hist = datastore.getDataStore("_HISTORICALDB")
hist.checkCorrectComputer()

if(dbobject.getDBString()=="sqlserver"):
    SQL_SCRIPTS = "{MSTAR_DATABASE}/sqlserver"
    dbobject.sqlcmdForExport(hist,mstarpaths.interpretPathShort(SQL_SCRIPTS + "/SchemaUtilities/historical_InsertGenerator.sql"),hist.user,hist.user)
    sqlFileName = mstarpaths.interpretPath("{MSTAR_TEMP}/exportCommands.sql")
    sqlFile = open(sqlFileName, "w")
    sqlFile.write(expcom)
    sqlFile.close()
    dbobject.sqlcmdForExport(hist,sqlFileName,hist.user,hist.user,filename)

else:
    expOptions = "file=%s tables=R_CALENDAR,R_CALENDAR_LOOKUP,R_CUSTOMER_DEFAULTS rows=yes indexes=no" % filename
    hist.expExtended(expOptions)



