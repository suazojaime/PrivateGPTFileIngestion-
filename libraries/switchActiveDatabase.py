import mstarpaths, sys, os, minestar, i18n, mstaroverrides

__version__ = "$Revision: 1.2 $"

logger = minestar.initApp()

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [\
        make_option("-r", "--role", help="the database role"),\
        make_option("-p", "--prefix", help="the database user name prefix"),\
        ]
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, "")

    newRole = options.role
    newPrefix = options.prefix
    if newRole is None and newPrefix is None:
        print "Usage: %s [-r <DatabaseRole>] [-p <UsernamePrefix>]" % sys.argv[0]

    mstarpaths.loadMineStarConfig()
    overrides = mstaroverrides.Overrides()

    validChoices = []
    for dbRoleName in eval(mstarpaths.interpretVar("_DB_SERVER_ROLES")):
        validChoices = [dbRoleName] + validChoices
    if newRole is not None:
        if not newRole in validChoices:
            print i18n.translate("Invalid database role %s. Valid choices are %s" % (newRole, validChoices))
            minestar.exit(1)
        print i18n.translate("New database role is %s" % newRole)
        overrides.put("/MineStar.properties", "_DBROLE", newRole)
    if newPrefix is not None:
        print i18n.translate("New database username prefix is %s" % newPrefix)
        overrides.put("/MineStar.properties", "_DBPREFIX", newPrefix)

    overrides.save()
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
    
