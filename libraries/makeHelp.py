# -*- coding: utf-8 -*-
__version__ = "$Revision: 1.0 $"

import minestar
import mstarpaths
from helpDoc import HelpDoc

logger = minestar.initApp()


def makeHelp(languageCode=None):
    if languageCode is None:
        languageCode = mstarpaths.interpretVar("_LANGUAGE")
        if languageCode is not None:
            logger.info("Using configured language code '%s'." % languageCode)
        else:
            languageCode = 'en'
            logger.info("Using default language code '%s'." % languageCode)
    helpDoc = HelpDoc(languageCode)
    helpDoc.install()


def main(appConfig=None):
    optionDefns = []
    argumentsStr = "[language]"
    (options, args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)
    languageCode = None if len(args) == 0 else args[0]
    makeHelp(languageCode)


if __name__ == "__main__":
    """entry point when called from python"""
    main()
