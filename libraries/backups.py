import os

from fileOps import FileOps
from propertiesConfig import PropertiesConfig
from mstarInstall import MStarInstall

class BackupsConfig(PropertiesConfig):

    FILE_NAME = 'backups.properties'

    KEY_DIR_NAME = 'backups.dir.name'
    KEY_IGNORED_RESOURCES = 'backups.resources.ignore'

    DEFAULT_DIR_NAME = 'backups'
    DEFAULT_IGNORED_RESOURCES = []

    def __init__(self, path):
        super(BackupsConfig, self).__init__(path)
        self._dirName = BackupsConfig.DEFAULT_DIR_NAME
        self._ignoredResources = BackupsConfig.DEFAULT_IGNORED_RESOURCES

    @property
    def dirName(self):
        return self._dirName

    @dirName.setter
    def dirName(self, dirName):
        self._dirName = dirName

    @property
    def ignoredResources(self):
        return self._ignoredResources

    @ignoredResources.setter
    def ignoredResources(self, ignoredResources):
        self._ignoredResources = ignoredResources

    # @Override
    def _propertiesToSave(self):
        """ Get the properties to save when storing. """
        return {'backups.dir.name':self.dirName,
                'backups.resources.ignore':self.ignoredResources}

    # @Override
    def _parseProperties(self, properties):
        dirName = BackupsConfig.DEFAULT_DIR_NAME
        if BackupsConfig.KEY_DIR_NAME in properties:
           dirName = properties[BackupsConfig.KEY_DIR_NAME]
        self.dirName = dirName

        ignoredResources = BackupsConfig.DEFAULT_IGNORED_RESOURCES
        if BackupsConfig.KEY_IGNORED_RESOURCES in properties:
            ignoredResources = properties[BackupsConfig.KEY_IGNORED_RESOURCES]
        self.ignoredResources = ignoredResources

class Backups(object):

    """ Performs backup operations for the M* system. """

    def __init__(self, installDir):
        self._installDir = installDir
        self._config = None
        self._backupsDir = None

    @property
    def installDir(self):
        return self._installDir

    @property
    def config(self):
        if self._config is None:
            self._config = self._loadConfig()
        return self._config

    def _loadConfig(self):
        mstar = MStarInstall.getInstance(self.installDir)
        config = BackupsConfig(os.path.join(mstar.configDir, BackupsConfig.FILE_NAME))
        if os.path.exists(config.path):
            config.load()
        return config

    @property
    def backupsDir(self):
        if self._backupsDir is None:
            self._backupsDir = os.path.join(self.installDir, self.config.dirName)
        return self._backupsDir

    def _backupResource(self, resource, options={}):
        """ Backup a file/directory at the path. """
        if resource is not None and os.path.exists(resource):
            # Create backups directory if required.
            if not os.path.exists(self.backupsDir):
                os.makedirs(self.backupsDir)
            # Copy the resource to the backups directory.
            source = os.path.join(self.installDir, resource)
            target = os.path.join(self.backupsDir, resource)
            FileOps.getFileOps(options).moveResource(source, target)
        return True

    def backup(self, options={}):
        """ Backup the installed directory. """
        for resource in os.listdir(self.installDir):
            if not resource in self.config.ignoredResources:
                self._backupResource(resource, options)
        return True

    def restore(self, options={}):
        """ Restore the backups into the install directory. """
        if os.path.exists(self.backupsDir) and os.path.isdir(self.backupsDir):
            for file in os.listdir(self.backupsDir):
                self._restoreResource(file, options)
        return True

    def _restoreResource(self, resource, options={}):
        source = os.path.join(self.backupsDir, resource)
        target = os.path.join(self.installDir, resource)
        FileOps.getFileOps(options).copyResource(source, target)
