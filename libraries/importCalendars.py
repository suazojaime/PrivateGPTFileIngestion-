import minestar
logger = minestar.initApp()
import mstarpaths, datastore, sys, i18n, os
import databaseDifferentiator

cleanORA = """
delete from R_CALENDAR;
delete from R_CALENDAR_LOOKUP;
delete from R_CUSTOMER_DEFAULTS;
exit
"""
cleansql = """
delete from R_CALENDAR;
delete from R_CALENDAR_LOOKUP;
delete from R_CUSTOMER_DEFAULTS;
"""
dbobject = databaseDifferentiator.returndbObject()
filename = sys.argv[1]
mstarpaths.loadMineStarConfig()
hist = datastore.getDataStore("_HISTORICALDB")
model = datastore.getDataStore("_MODELDB")
dss = [ hist ]
if model != hist:
    dss.append(model)
model.checkCorrectComputer()
hist.checkCorrectComputer()
sqlFileName = mstarpaths.interpretPath("{MSTAR_TEMP}/importCalendars%d.sql" % os.getpid())
sqlFile = open(sqlFileName, "w")
if(dbobject.getDBString()=="sqlserver"):
    sqlFile.write(cleansql)
else:
    sqlFile.write(cleanORA)
sqlFile.close()
if(dbobject.getDBString()=="sqlserver"):
    dbobject.sqlcmd(hist,sqlFileName,hist.user, hist.password)
    dbobject.sqlcmd(model,sqlFileName,model.user, model.password) 
else:
    hist.sqlplus(sqlFileName)
    model.sqlplus(sqlFileName)

hist.imp(filename,hist)
model.imp(filename,model)
