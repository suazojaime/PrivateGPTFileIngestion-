__version__ = "$Revision: 1.1 $"
import minestar
logger = minestar.initApp()
import os, mstarpaths, datastore, sys, i18n, mstarrun, progress

from optparse import make_option


def importToModelAndHist(model, hist, filename):
    # import the file to the model and the historical
    progress.task(0.55, "importing %s to model" % filename)
    mstarrun.run("importDataFromXml -f %s" % filename)
    progress.done()

def checkDataStores(model, hist, template):
    progress.task(0.33, "checking historical")
    if hist.probe() != "OK":
        print "Historical database is not ready for this operation, run checkDataStores"
        sys.exit(30)
    progress.nextTask(0.33, "checking model")
    if model.probe() != "OK":
        print "Model database is not ready for this operation, run checkDataStores"
        sys.exit(31)
    progress.nextTask(0.33, "checking template")
    if template.probe() != "OK":
        print "Template database is not ready for this operation, run checkDataStores"
        sys.exit(32)
    progress.done()
    progress.done()

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = "[modelxmlfile]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    if len(args) == 0:
        print "Usage: replaceDataStoresWithXml exportFile"
        minestar.exit()

    filename = args.pop(0)
    if not os.path.exists(filename):
        print "File %s does not exist" % filename
        minestar.exit()
    mstarpaths.loadMineStarConfig()
    progress.start(1000, "replaceDataStoresWithXml")
    hist = datastore.getDataStore("_HISTORICALDB")
    model = datastore.getDataStore("_MODELDB")
    # we assume that the template is up to date
    template = datastore.getDataStore("_TEMPLATEDB")
    progress.task(0.03, "checking data stores")
    checkDataStores(model, hist, template)
    progress.nextTask(0.10, "dropping schemas in model and historical")
    model.dropAll(model)
    hist.dropAll(hist)
    progress.nextTask(0.20, "creating schema in model and historical")
    mstarrun.run("makeDataStores all")
    progress.done()
    progress.nextTask(0.50, "importing to model and historical")
    importToModelAndHist(model, hist, filename)

    progress.done()
    progress.done()

if __name__ == "__main__":
    """entry point when called from python"""
    main()

