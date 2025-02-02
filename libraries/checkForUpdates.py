__version__ = "$Revision: 1.1 $"

import sys, os, string
import minestar, mstarpaths

logger = minestar.initApp()

def connectToUpdateServer(verbose=False):
    # Returns a connection to the update server or throws an exception

    if verbose:
        logger.info("Connecting to update server ...")
    # TO DO
    return None

def getLastUpdateTimestamp():
    # FIXME
    return time.now()

def getAvailablePatches(updateServer, verbose=False):
    # Get patches from the updates site and returns the list of updates downloaded

    available = []
    # TODO ...
    return available

def checkForUpdates(categories, email=False, verbose=False):
    # Check for updates of the nominated categories - either Extensions (not supported yet) or Patches
    
    # Get the build version
    # TODO ...
    buildVersion = "1.3.0.3-249"

    # Get the connection to the update server
    updateServer = None
    try:
        updateServer = connectToUpdateServer()
    except:
        logger.error("failed to connect to update server: %s" % reason

    # Get the new updates available
    newPatches = []
    if updateServer is not None:
        for category in categories:
            if verbose:
                logger.info("Getting updates in category %s ..." % category
            if category == 'Patches':
                existing = getDownloadedPatches(buildVersion)
                available = getAvailablePatches(updateServer, buildVersion, verbose)
                newPatches = available - existing
            else:
                logger.warning("unknown update category %s - ignoring" % category)

    # Tell the user what we found
    count = len(newPatches)
    if updateServer is None:
        msgText = "Unable to connect ot the update server to check for new MineStar updates."
    elif count > 0:
        msgText = "The following new patches are now available for download:\n\n" + string.join(newPatches, "\n")
    else:
        msgText = "There are no new patches available for download."
    logger.info(msgText)

    # Email the system admin if requested and necessary
    if email:
        systemAdmin = mstarpath.interpretVar("_EMAIL")
        if systemAdmin is None or systemAdmin.trim():
            logger.warning("Asked to email checkForUpdates results but no system adminstrator defined for this site.")
        else:
            logger.info("Emailing this information to %s" % systemAdmin)
        # TODO ...
        logger.warning("email support not added yet.")

def autoCheckForUpdates(categories, email=False, verbose=False):
    # Check for updates if it's time to do so

    # This subroutine only initiates update checking if the site configured amount of time has passed since it was last done.
    lastCheck = getLastUpdateTimestamp()
    currentTime = time.now()
    # TO DO ...

    
## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [
      make_option("-e", "--email", action="store_true", \
        help="Email the system adminstrator about updates downloaded."),
      make_option("-v", "--verbose", action="store_true", \
        help="Verbose mode."),
      ]
    argumentsStr = "auto|all"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Note: In the future, we may get this from an option setting exposed in supervisor, checking extensions and builds as well
    categories = ['Patches']

    # Check for updates as requested
    verbose = options.get("verbose")
    downloadSpec = args[0]
    if downloadSpec == 'auto':
        autoCheckForUpdates(categories, email, verbose)
    elif downloadSpec == 'all':
        checkForUpdates(categories, email, verbose)
    else:
        minestar.abort("Incorrect usage")
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
