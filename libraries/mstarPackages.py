import os


def isNotEmptyString(s):
    return s is not None and s.strip()


def _parsePackageOverrides(overridesStr):
    """ Get the package overrides from the M* overrides file. Returns a map of
        package name to PackageDependency instance. """

    def getDependencyIDs():
        # Get the dependency IDs from the _PACKAGES variable.
        dependencyIDs = []
        if isNotEmptyString(overridesStr):
            dependencyIDs = [x.strip() for x in overridesStr.split(',')]
        return dependencyIDs

    def getDependencies():
        from packages import PackageDependency
        return [PackageDependency.createFrom(dependency) for dependency in getDependencyIDs()]

    # Get the dependency overrides map from the _PACKAGES variable.
    overrides = {}
    for dependency in getDependencies():
        overrides[dependency.name] = dependency
    return overrides


def getPackageOverrides():
    """ Get the default package overrides from the MineStar.overrides file. """

    # Note: Not using the usual overrides from mstarpaths.config because this function
    #       may be called during bootstrapping, so the mstarpaths.config may not yet
    #       contain the _PACKAGES variable. The MineStar.overrides file will be loaded
    #       directly, and the '/Versions.properties._PACKAGES' property inspected.

    def getConfigDirFrom(settings):
        if settings is None:
            return None
        if 'MSTAR_CONFIG' in settings:
            return settings['MSTAR_CONFIG']
        if 'MSTAR_SYSTEM_HOME' in settings:
            return os.path.join(settings['MSTAR_SYSTEM_HOME'], 'config')
        return None

    # Get the ${MSTAR_CONFIG} value from the os.environ, or default config.
    configDir = getConfigDirFrom(os.environ)
    if configDir is None:
        import mstarpaths
        configDir = getConfigDirFrom(mstarpaths.config)
        if configDir is None:
            return {}

    # Check if an overrides file exists.
    overridesFile = os.path.join(configDir, 'MineStar.overrides')
    if not os.access(overridesFile, os.F_OK):
        return {}

    # Load the overrides from the overrides file.
    import mstaroverrides
    (bundles, _) = mstaroverrides.loadOverridesFromFile(overridesFile)
    if '/Versions.properties' not in bundles:
        return {}

    # Check for '/Versions.properties._PACKAGES' value.
    bundle = bundles['/Versions.properties']
    if '_PACKAGES' not in bundle:
        return {}

    return _parsePackageOverrides(bundle['_PACKAGES'])


def getPackageDependencies(package, overrides=None):
    """ Get the dependencies for the M* package, taking overrides (if any) into account.

        Overrides are specified as a map of dependencies, indexed by dependency name. For example,
            { 'geoserver': 'geoserver:2.11.1@server' }

        If no overrides are specified the default overrides (from the '/Versions.properties._PACKAGES' setting
        in MineStar.overrides file) are used. """

    # Get the default overrides if none provided.
    if overrides is None:
        overrides = getPackageOverrides()

    # if '_PACKAGES' in overrides:
    #     overrides = _parsePackageOverrides(overrides['_PACKAGES'])

    import packages
    return packages.getPackageDependencies(package, overrides)
