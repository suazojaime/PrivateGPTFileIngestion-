# Revision 1.0  2008/10/15 moghaib
# new
import mstarrun, mstarpaths, minestar
import shutil, os, zipfile
import wikiUtils

logger = minestar.initApp()

mstarpaths.loadMineStarConfig()

JAVA_CLASS = "minestar.platform.automation.handler.AutomatedTestHandler"

def run():
    logger.info('calling mstarrun makeSystem main')
    os.system("mstarrun makeSystem main")

    # Update the override file with DB options given in automation.xml file
    logger.info('calling automated test handler')
    command = ["minestar.platform.automation.handler.AutomatedTestHandler", "updateOverridesFile"]
    output = minestar.mstarrunEval(command)

    if output.find("SUCCESS"):
        logger.info('Successfully Updated Overrides File!')

        command = ["minestar.platform.automation.handler.AutomatedTestHandler", "updateAssignmentOptions"]
        output = minestar.mstarrunEval(command)
        logger.info('Successfully Updated DefaultIAssignmentOptions File!')

        logger.info('calling mstarrun checkDataStores')
        os.system("mstarrun checkDataStores")

        logger.info('calling mstarrun emptyDataStore _MODELDB,_HISTORICALDB,_SUMMARYDB,_REPORTINGDB,_TEMPLATEDB,_PITMODELDB,_GISDB')
        os.system("mstarrun emptyDataStore _MODELDB,_HISTORICALDB,_SUMMARYDB,_REPORTINGDB,_TEMPLATEDB,_PITMODELDB,_GISDB")
        
        logger.info('calling mstarrun makeDataStores all')
        os.system("mstarrun makeDataStores all")

        logger.info('Starting MineStar')
        os.system("mstarrun startSystem")

        logger.info('Building Small Test Mine')
        os.system("mstarrun -b com.mincom.works.test.testmine.BuildTestMine -small")

        logger.info('Running IPretend in acclerated mode')
        os.system("mstarrun -b IPretend -accelerated -length 1")
    else:
        logger.info('Unable to update Overrides file.')

    logger.info('Automated Test Framework Process Completed!')

if __name__ == '__main__':
    run()
