import os
from propertiesConfig import PropertiesConfig


class LicenseKey(PropertiesConfig):

    """ Class representing a license key configuration file. """

    KEY_MSTAR_SYSTEMS = 'MSTAR_SYSTEMS'
    KEY_SUITE = 'suite'
    KEY_DEPLOYMENT_TYPE = 'deploymentType'
    KEY_DEFAULT_EXTENSIONS = 'defaultExtensions'

    DEFAULT_SUITE = 'Enterprise'
    DEFAULT_DEPLOYMENT_TYPE = 'Server'
    DEFAULT_EXTENSIONS = 'Pit_Link,Machine_Tracking,Assignment,Production,Material_Tracking,Health'
    DEFAULT_MSTAR_SYSTEMS = '~/mstarFiles/systems'
    
    def __init__(self, properties={}, suite=None, deploymentType=None, defaultExtensions=None, mstarSystems=None):
        super(LicenseKey, self).__init__(properties)
        self.suite = suite if suite is not None else self.suite
        self.deploymentType = deploymentType if deploymentType is not None else self.deploymentType
        self.defaultExtensions = defaultExtensions if defaultExtensions is not None else self.defaultExtensions
        self.mstarSystems = mstarSystems if mstarSystems is not None else self.mstarSystems

    @classmethod
    def filename(cls):
        return 'LICENSE.key'

    @classmethod
    def filedesc(cls):
        return "License Key"

    @property
    def mstarSystems(self):
        return self._getProperty(LicenseKey.KEY_MSTAR_SYSTEMS, LicenseKey.defaultMStarSystems())

    @mstarSystems.setter
    def mstarSystems(self, mstarSystems):
        self._setProperty(LicenseKey.KEY_MSTAR_SYSTEMS, mstarSystems)

    @property
    def suite(self):
        return self._getProperty(LicenseKey.KEY_SUITE, LicenseKey.DEFAULT_SUITE)

    @suite.setter
    def suite(self, suite):
        self._setProperty(LicenseKey.KEY_SUITE, suite)

    @property
    def deploymentType(self):
        return self._getProperty(self.KEY_DEPLOYMENT_TYPE, LicenseKey.DEFAULT_DEPLOYMENT_TYPE)

    @deploymentType.setter
    def deploymentType(self, deploymentType):
        self._setProperty(self.KEY_DEPLOYMENT_TYPE, deploymentType)

    @property
    def defaultExtensions(self):
        return self._getProperty(LicenseKey.KEY_DEFAULT_EXTENSIONS, LicenseKey.DEFAULT_EXTENSIONS)

    @defaultExtensions.setter
    def defaultExtensions(self, defaultExtensions):
        self._setProperty(LicenseKey.KEY_DEFAULT_EXTENSIONS, defaultExtensions)

    @staticmethod
    def defaultMStarSystems():
        userHomeDir = os.path.expanduser('~')
        return os.path.join(userHomeDir, 'mstarFiles', 'systems')
