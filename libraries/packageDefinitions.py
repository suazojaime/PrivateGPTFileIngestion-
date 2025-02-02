from packageConfig import PackageConfig
from packages import PackageDependency


class PackageDefinitions(object):

    def __init__(self):
        self.packageConfigs = {}
        # Create the package definitions map.
        self.packageDefinitions = {}
        for p in PackageDefinitions._packageDefinitionValues:
            self.packageDefinitions[p['version']] = p

    def getPackageConfigs(self, version):
        """ Get the package configs (as a map) for the specified release version. """
        if version in self.packageConfigs:
            return self.packageConfigs[version]
        packageConfigs = self._loadPackageConfigs(version)
        if packageConfigs is not None:
            self.packageConfigs[version] = packageConfigs
        return packageConfigs

    def _loadPackageConfigs(self, version):
        packageConfigs = {}
        release = self._findCompatibleRelease(version)
        if release is not None:
            packageConfigs = self._createPackageConfigs(version, self.packageDefinitions[release])
        return packageConfigs

    def _findCompatibleRelease(self, version):
        result = None
        for key in self.packageDefinitions:
            packageDefinition = self.packageDefinitions[key]
            release = packageDefinition['version']
            from versions import Version
            if Version.greaterThanOrEqualTo(release, version):
                result = release
        return result

    def _createPackageConfigs(self, version, packageDefinition):
        map = {}
        # Create a package config for each package definition.
        for key in packageDefinition['packages']:
            # Create an initial config.
            config = self._createPackageConfig(packageDefinition['packages'][key])
            # Resolve version placeholders in the config properties.
            config.version = self._replaceBuildVersionInString(config.version, version)
            config.description = self._replaceBuildVersionInString(config.description, version)
            config.dependencies = self._replaceBuildVersionInList(config.dependencies, version)
            # Assign the correct symlink property.
            config.symlink = key if key is not "mstar" else "mstar%s" % config.version
            map[key] = config
        # Resolve the dependencies in each package config.
        for key in map:
            config = map[key]
            config.dependencies = self._resolveDependencies(config, map)
        return map

    def _createPackageConfig(self, properties):
        """ Create a package config from properties. Must contain 'name' and 'version', optionally
            'description' and 'dependencies'. """
        config = PackageConfig()
        config.name = properties['name']
        config.version = properties['version']
        if 'description' in properties:
            config.description = properties['description']
        if 'dependencies' in properties:
            config.dependencies = properties['dependencies']
        return config

    def _resolveDependencies(self, config, map):
        resolved = []
        for dependency in config.dependencies:
            resolved.append(self._resolveDependency(dependency, map))
        return resolved

    def _resolveDependency(self, dependency, map):
        dependency = PackageDependency.createFrom(dependency)
        for key in map:
            config = map[key]
            if config.name == dependency.name:
                dependency.version = config.version
                return dependency
        raise Exception("Unresolved package dependency: %s" % dependency)

    def _replaceBuildVersionInString(self, string, version):
        return None if string is None else string.replace("${build.version}", version)

    def _replaceBuildVersionInList(self, list, version):
        return None if list is None else [x.replace("${build.version}", version) for x in list]

    _packageDefinitions408 = {
        "version": "4.0.8",
        "packages": {
            "contexts": {
                "name": "contexts",
                "version": "${build.version}"
            },
            "Detect": {
                "name": "detect",
                "version": "${build.version}"
            },
            "geoserver": {
                "name": "geoserver",
                "version": "2.8.3"
            },
            "jetty": {
                "name": "jetty",
                "version": "9.3.8"
            },
            "jdk": {
                "name": "jdk",
                "version": "1.6"
            },
            "python": {
                "name": "python",
                "version": "2.7.3"
            },
            "toolkit": {
                "name": "toolkit",
                "version": "${build.version}"
            },
            "webapps": {
                "name": "webapps",
                "version": "${build.version}"
            },
            "mstar": {
                "name": "mstar",
                "version": "${build.version}"
            },
            "system": {
                "name": "system",
                "version": "${build.version}",
                "description": "Package configuration for the CAT MineStar ${build.version} release",
                "dependencies": [
                    "contexts",
                    "detect",
                    "geoserver@server",
                    "jetty@server",
                    "python",
                    "jdk",
                    "toolkit",
                    "webapps",
                    "mstar"
                ]
            }
        }
    }
    
    _packageDefinitions441 = {
        "version": "4.4.1",
        "packages": {
            "ext": {
                "name": "extensions",
                "version": "${build.version}"
            },
            "geoserver": {
                "name": "geoserver",
                "version": "2.8.3",
                "dependencies": ["postgis"]
            },
            "jetty": {
                "name": "jetty",
                "version": "9.3.8"
            },
            "jdk": {
                "name": "jdk",
                "version": "1.8"
            },
            "postgis": {
                "name": "postgis",
                "version": "2.1.5"
            },
            "python": {
                "name": "python",
                "version": "2.7.3"
            },
            "toolkit": {
                "name": "toolkit",
                "version": "${build.version}"
            },
            "mstar": {
                "name": "mstar",
                "version": "${build.version}"
            },
            "system": {
                "name": "system",
                "version": "${build.version}",
                "description": "Package configuration for the CAT MineStar ${build.version} release",
                "dependencies": [
                    "extensions",
                    "geoserver@server",
                    "jetty@server",
                    "postgis@server",
                    "python",
                    "jdk",
                    "toolkit",
                    "mstar"
                ]
            }
        }
    }

    _packageDefinitionValues = [_packageDefinitions408, _packageDefinitions441]

