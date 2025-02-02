# Application to load an exported model into a model and historical and make
# a compatible model/historical pair.

import minestar
__version__ = "$Revision: 1.22 $"

logger = minestar.initApp()
import mstarpaths, datastore, sys, i18n, mstarrun, progress

from optparse import make_option

import databaseDifferentiator
dbobject = databaseDifferentiator.returndbObject()

def importToModelAndHist(model, hist, summ, filename,options=None):
    # If the filename is a zip file, assume the dmp file is buried within it
    if filename.endswith(".zip"):
        import os, zipfile
        dir = os.path.split(filename)[0]
        minestar.unpack(zipfile.ZipFile(filename), dir)
        filename = filename[0:-4] + dbobject.getdumpfileExt()

    # import the file to the model and the historical
    progress.task(0.5, "importing to model")
    if options.standby:
        model.reimport(filename,model,'true')
        progress.task(0.6, "dropping historical")
        hist.dropAll(hist,'true')
        progress.task(0.7, "dropping summary")
        summ.dropAll(summ,'true')
    else:
        model.reimport(filename,model)
        progress.task(0.6, "dropping historical")
        hist.dropAll(hist)
        progress.task(0.7, "dropping summary")
        summ.dropAll(summ)
    progress.done()

def importToPitmodel(pitmodel, filename,options=None):
    # If the filename is a zip file, assume the dmp file is buried within it
    if filename.endswith(".zip"):
        import os, zipfile
        dir = os.path.split(filename)[0]
        minestar.unpack(zipfile.ZipFile(filename), dir)
        filename = filename[0:-4] +  dbobject.getdumpfileExt()

    # import the file to the pitmodel database
    progress.task(0.5, "importing to pitmodel")
    if options.standby:
        pitmodel.reimport(filename,pitmodel,'true')
    else:
        pitmodel.reimport(filename,pitmodel)
    progress.done()

def checkDataStores(model, hist, template, pitmodel):
    databases = [ [ hist,        'Historical',  30 ],
                  [ model,       'Model',       31 ],
                  [ template,    'Template',    32 ],
                  [ pitmodel,    'Pitmodel',    33 ]]
    for [db, dbname, rval] in databases:
        progress.nextTask(0.25, 'checking ' + dbname)
        result = db.probe()
        if (result != 'OK'):
            print 'checkDataStores failed for', dbname, 'database with result:', result
            print 'Rerun checkDataStores', db.dbName()
            sys.exit(rval)
    progress.done()


def _importFileValidation(Model,PitModel):
    if Model is None:
        print "ERROR: Please select a Model Dump File"
        minestar.exit()

    #Validating whether file exist and accessible
    Model =mstarpaths.validateFile(Model)
    if PitModel is not None:
        PitModel = mstarpaths.validateFile(PitModel)

    #checking whether the database specific file is used (.dmp or .bak), cross usage is prohibited.
    oracleSuffix = ".dmp";
    sqlSuffix = ".bak";

    if (dbobject.getDBString()=="sqlserver"):
        if not Model.lower().endswith(sqlSuffix):
            print "ERROR: Only .bak files can be imported into SQL SERVER"
            minestar.exit()
        if PitModel is not None:
            if not PitModel.lower().endswith(sqlSuffix):
                print "ERROR: Only .bak files can be imported into SQL SERVER"
                minestar.exit()
    else:
        if not Model.lower().endswith(oracleSuffix):
            print "ERROR: Only .dmp files can be imported into ORACLE"
            minestar.exit()
        if PitModel is not None:
            if not PitModel.lower().endswith(oracleSuffix):
                print "ERROR: Only .dmp files can be imported into ORACLE"
                minestar.exit()


def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [
      make_option("-s", "--standby", action="store_true", \
        help="Operate on the standby database."),
      make_option("-r", "--raw", action="store_true", \
        help="Raw import: skip consistency check."),
      ]

    argumentsStr = "[modeldumpfile] [pitmodeldumpfile]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    if len(args) == 0:
        print "Usage: replaceDataStoresWithModel [-s] modeldumpfile [pitmodeldumpfile]"
        minestar.exit()

    dbRole = None
    if options.standby:
        dbRole = "STANDBY"
        print "Operating on the standby database"

    filenameModel = args.pop(0)
    filenamePitmodel = None
    if len(args) > 0:
        filenamePitmodel = args.pop(0)
    #Validate the file before importing.
    _importFileValidation(filenameModel,filenamePitmodel)
    filenameModel = mstarpaths.validateFile(filenameModel)
    if (filenamePitmodel):
        filenamePitmodel = mstarpaths.validateFile(filenamePitmodel)

    mstarpaths.loadMineStarConfig()
    progress.start(1000, "replaceDataStoresWithModel")
    hist = datastore.getDataStore("_HISTORICALDB", dbRole)
    model = datastore.getDataStore("_MODELDB", dbRole)
    summ = datastore.getDataStore("_SUMMARYDB", dbRole)
    # we assume that the template is up to date
    template = datastore.getDataStore("_TEMPLATEDB", dbRole)
    pitmodel = datastore.getDataStore("_PITMODELDB", dbRole)
    progress.task(0.03, "checking data stores")
    if (dbobject.getDBString()=="Oracle"):
        checkDataStores(model, hist, template, pitmodel)
    elif (dbobject.getDBString()=="sqlserver"):
        if(dbRole=="STANDBY"):
            mstarrun.run("checkDataStores STANDBY._HISTORICALDB x")
            mstarrun.run("checkDataStores STANDBY._MODELDB x")
            mstarrun.run("checkDataStores STANDBY._PITMODELDB x")
            mstarrun.run("checkDataStores STANDBY._TEMPLATEDB x")
        else:
            checkDataStores(model, hist, template, pitmodel)
    progress.nextTask(0.30, "importing to model and historical")
    importToModelAndHist(model, hist, summ, filenameModel,options)
    if filenamePitmodel is None:
        if options.standby:
            pitmodel.dropAll(pitmodel,'true')
        else:
            pitmodel.dropAll(pitmodel)
    else:
        importToPitmodel(pitmodel, filenamePitmodel,options)
    progress.nextTask(0.50, "upgrading schema in model and historical")
    mdsArgs = ""
    if options.raw:
        mdsArgs = "-raw"
    if(dbobject.getDBString()=="sqlserver"):
        if(dbRole=="STANDBY"):
            dbobject.createUser(model,'true')
            dbobject.refreshUser(model,'true')
            dbobject.createUser(pitmodel,'true')
            dbobject.refreshUser(pitmodel,'true')
            mstarrun.run("makeDataStores -standby " + mdsArgs + " all")
        else:
            mstarrun.run("makeDataStores" + mdsArgs + " all")
    elif(dbobject.getDBString()=="Oracle"):
        if(dbRole=="STANDBY"):
            print "Executing makeDataStores -standby %s all" % (mdsArgs)
            mstarrun.run("makeDataStores -standby " + mdsArgs + " all")
        else: mstarrun.run("makeDataStores " + mdsArgs + " all")
    progress.done()
    progress.done()

if __name__ == "__main__":
    """entry point when called from python"""
    main()

