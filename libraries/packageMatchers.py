from packages import isMatchingPackageName, isMatchingPackageVersion, isCompatiblePackageVersion
from packages import createPackageIdentifier

class PackageVersionMatcher:
    
    def __init__(self, version, type='exact'):
        self.version = version
        self.type = type
    
    def matches(self, package):
        package = createPackageIdentifier(package)
        if self.type == 'exact':
            return isMatchingPackageVersion(package.version, self.version)
        elif self.type == 'compatible':
            return isCompatiblePackageVersion(package.version, self.version)
        raise Exception('Invalid version matcher type: %s' % self.type)
    
class PackageMatcher(object):

    """ A package matching class. """

    def __init__(self, id=None, matchingType='exact'):
        if id is None:
            raise Exception("Cannot create PackageMatcher: no 'id' specified")
        self._id = id
        self._matchingType = matchingType

    @property
    def id(self):
        return self._id

    @property
    def matchingType(self):
        return self._matchingType

    def matches(self, package):
        package = createPackageIdentifier(package)
        # Fail if the package name does not match the expected name.
        if not isMatchingPackageName(package.name, self.id.name):
            return False
        # Fail if the package version does not match the expected version.
        if self.id.version is not None:
            versionMatcher = PackageVersionMatcher(self.id.version, self.matchingType)
            if not versionMatcher.matches(package):
                return False
        # Assert: package name and version are matched.
        return True

# createPackageMatcher('geoserver')
# createPackageMatcher('geoserver:2.5.1')
# createPackageMatcher({'name':'geoserver'})
def createPackageMatcher(source, matchingType='exact'):
    """ Create a package matcher from the source, and an optional matching type. """
    # Check that a source was specified.
    if source is None:
        raise Exception("Cannot create PackageMatcher: no 'source' specified")
    # If the source is already a package matcher, then create a new package matcher.
    if isinstance(source, PackageMatcher):
        return PackageMatcher(source.id, matchingType)
    # Otherwise create a package identifier from the source, and
    # create a package matcher from that identifier.
    return PackageMatcher(createPackageIdentifier(source), matchingType)
