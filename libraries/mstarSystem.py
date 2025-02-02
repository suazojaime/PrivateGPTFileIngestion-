import os
import shutil


class MStarSystem(object):

    """ Class representing an M* system, e.g. /mstarFiles/systems/main """

    def __init__(self, path):
        if path is None:
            raise ValueError("No path specified for MStarSystem")
        if not os.path.exists(path):
            raise ValueError("Path for MStarSystem does not exist: %s" % path)
        if not os.path.isdir(path):
            raise ValueError("Path for MStarSystem is not a directory: %s" % path)
        self._path = path
        self._name = os.path.basename(path)
        self._overrides = None
        self._secureOverrides = None

    @property
    def path(self):
        return self._path

    @property
    def name(self):
        return self._name

    @property
    def updatesDir(self):
        return os.path.join(self.path, 'updates')

    @property
    def updatesBuildsDir(self):
        return os.path.join(self.updatesDir, 'builds')

    def createZipUpgrade(self, build, buildName=None):
        """ Create an archive of a M* build that can be used for zip upgrades. For example, an M* build
            located at /tmp/mstar with version 5.1 will create the file ${path}/updates/builds/mstar5.1.zip. """
        if build is None:
            raise ValueError("No value specified for build")
        name = os.path.join(self.updatesBuildsDir, 'mstar%s' % (buildName or build.version))
        return shutil.make_archive(base_name=name, format='zip', root_dir=build.path)
