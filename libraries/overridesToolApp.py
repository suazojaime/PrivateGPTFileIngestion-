import sys


def parseArgs(argv=[]):
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-system", default="main", help="The name of the MineStar system.")
    parser.add_argument("-list", action="store_true", help="List all overrides.")
    parser.add_argument("-listSecure", action="store_true", help="List overrides that are securely stored.")
    parser.add_argument("-listUnsecure", action="store_true", help="List overrides that are not securely stored.")
    parser.add_argument("-listMigrate", action="store_true", help="List overrides that can migrate from unsecured storage to secured storage.")
    parser.add_argument("-listUnmigrate", action="store_true",help="List overrides that can migrate from secured storage to unsecured storage.")
    parser.add_argument("-migrate", action="store_true", help="Moves overrides from unsecured storage to secured storage.")
    parser.add_argument("-unmigrate", action="store_true", help="Moves overrides from secured storage to unsecured storage.")
    parser.add_argument("-minestarFile", help="Location of the MineStar.overrides [default: {MSTAR_CONFIG}/MineStar.overrides]")
    parser.add_argument("-secureFile", help="Location of the Secure.overrides [default: {MSTAR_CREDS}/Secure.overrides]")
    parser.add_argument("-keyStoreFile", help="Location of the key store file [default: {MSTAR_CREDS}/keystore.jks]")
    parser.add_argument("-set", metavar="<name=value>{;<name=value>}", help="Set an override for a property.")
    parser.add_argument("-get", metavar="<name>", help="Get the override for a property.")
    parser.add_argument("-info", metavar="<name>", help="Show information for a property.")
    parser.add_argument("-verbose", action="store_true", help="Show verbose output.")
    return parser.parse_args(argv)


def removeFirstArg(argv=[]):
    return [] if len(argv) <= 1 else argv[1:]


def createOverridesTool(args):
    from overridesTool import OverridesTool
    return OverridesTool(createOverridesConfig(args))


def createOverridesConfig(args={}):
    from overridesFactory import OverridesConfig
    overridesConfig = OverridesConfig()
    if args.minestarFile is not None:
        overridesConfig.minestarOverridesFile = args.minestarFile
    if args.secureFile is not None:
        overridesConfig.secureOverridesFile = args.secureFile
    if args.keyStoreFile is not None:
        overridesConfig.keyStoreFile = args.keyStoreFile
    if args.get is not None:
        overridesConfig.propertyName = args.get
    return overridesConfig


def dumpOverrides(overrides):
    # Get the sorted property names.
    propertyNames = overrides.keys()
    propertyNames.sort()
    # Print each property name and its value (ignoring 'CONTENTS' property, if present).
    for propertyName in propertyNames:
        propertyValue = overrides.get(propertyName)
        if not propertyName == 'CONTENTS':
            print "%s=%s" % (propertyName, propertyValue)


def commandSelected(args):
    return args.list or args.listSecure or args.listUnsecure or args.listMigrate or args.listUnmigrate \
        or args.migrate or args.unmigrate or args.set or args.get or args.info


def main(appConfig=None):
    """ Entry point when called from mstarrun. """

    # Parse the arguments.
    args = parseArgs(removeFirstArg(sys.argv))

    # Default to listing the overrides.
    if not commandSelected(args):
        args.list = True

    # Set verbose if required.
    if args.verbose:
        import mstardebug
        mstardebug.debug = True

    # Load the initial minestar config (so that mstarpaths can be interpreted).
    import mstarpaths
    mstarpaths.loadMineStarConfig(appConfig)

    # Create overrides tool from the parsed arguments.
    # TODO pass appConfig, systemName, etc.
    overridesTool = createOverridesTool(args)

    # Perform requested action.

    # List all the overrides.
    if args.list:
        dumpOverrides(overridesTool.overrides)

    # List the secured overrides only.
    if args.listSecure:
        dumpOverrides(overridesTool.securedOverrides)

    # List the unsecured overrides only.
    if args.listUnsecure:
        dumpOverrides(overridesTool.unsecuredOverrides)

    # List the migrating overrides only.
    if args.listMigrate:
        dumpOverrides(overridesTool.migratingOverrides)

    # List the unmigrating overrides only.
    if args.listUnmigrate:
        dumpOverrides(overridesTool.unmigratingOverrides)

    # Migrate overrides from unsecure storage to secure storage.
    if args.migrate:
        overridesTool.migrateSecureOverrides()

    # Migrate overrides from secure storage to unsecure storage.
    if args.unmigrate:
        overridesTool.unmigrateSecureOverrides()

    if args.set:
        (name, value) = _parsePropertyNameAndValue(args.set.strip())
        overridesTool.setProperty(name, value)

    if args.get:
        overridesTool.getProperty(args.get.strip())

    if args.info:
        overridesTool.showPropertyInfo(args.info.strip())


def _parsePropertyNameAndValue(s):
    from StringTools import splitString
    nameAndValue = splitString(s, separator='=')
    if len(nameAndValue) != 2:
        raise Exception("Invalid property setting: expected <name>=<value> but found '%s'" % s)
    return nameAndValue

if __name__ == "__main__":
    """entry point when called from python"""
    main()
