from packages import Package, PackageError, comparePackageVersions, replacingSnapshot
from packageRepositories import PackageRepository


class PackageChange(object):
    
    """ Class representing a package change. """

    # Actions.
    SKIP = 'skip'                 # Do not modify the repository.
    INSTALL = 'install'           # Install the package into the repository.
    REPLACE = 'replace'           # Replace the package in the repository (used for snapshots).
    UNINSTALL = 'uninstall'       # Remove the package from the repository.
    
    # Reasons for the install action.
    REASON_NOT_INSTALLED = 'package not installed'
    REASON_ALREADY_INSTALLED = 'package already installed'
    REASON_NEWER_VERSION = 'package has newer version'
    REASON_NOT_SUPPORTED = 'not supported'
    REASON_FORCE_REPLACE = 'package always replaced'
    
    # Install policies.
    POLICY_INSTALL = 'install'  # The package will be installed if it does not already exist.
    POLICY_UPGRADE = 'upgrade'  # The package will be installed only if it represents an upgrade over existing package.
    POLICY_FORCE = 'force'      # The package will be always be installed (replace existing package if required).
    
    def __init__(self, action=None, reason=None):
        self._available = None
        self._installed = None
        self._action = action or PackageChange.SKIP
        self._reason = reason or PackageChange._getDefaultReasonForAction(self._action)
        
    def __repr__(self):
        return '{from:%s, to:%s, action:%s, reason:%s}' % (self.available, self.installed, self.action, self.reason)
    
    @property
    def available(self):
        return self._available
    
    @available.setter
    def available(self, available):
        self._available = available
        
    @property
    def installed(self):
        return self._installed
    
    @installed.setter
    def installed(self, installed):
        self._installed = installed

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, action):
        self._action = action

    @property
    def skip(self):
        """ Indicates if the change represents a 'skip' action. """
        return self.action == PackageChange.SKIP

    @property
    def install(self):
        """ Indicates if the change represents an 'install' action. """
        return self.action == PackageChange.INSTALL
    
    @property
    def replace(self):
        """ Indicates if the change represents a 'replace' action. """
        return self.action == PackageChange.REPLACE
        
    @property
    def uninstall(self):
        """ Indicates if the change represents an 'uninstall' action. """
        return self.action == PackageChange.UNINSTALL

    @property
    def reason(self):
        if self._reason is None:
            return PackageChange._getDefaultReasonForAction(self.action)
        return self._reason
    
    @reason.setter
    def reason(self, reason):
        self._reason = reason
        
    @staticmethod
    def _getDefaultReasonForAction(action):
        if action == PackageChange.INSTALL:
            return PackageChange.REASON_NOT_INSTALLED
        elif action == PackageChange.REPLACE:
            return PackageChange.REASON_NEWER_VERSION
        elif action == PackageChange.SKIP:
            return PackageChange.REASON_ALREADY_INSTALLED
        elif action == PackageChange.UNINSTALL:
            return None
        raise ValueError('Invalid change action: %s' % action)


class PackageChangeFactory(object):

    """ Class for creating package changes. The default policy is INSTALL. """
    
    def __init__(self, policy=None):
        policy = policy or PackageChange.POLICY_INSTALL
        def isValidPolicy(policy):
            return policy is PackageChange.POLICY_INSTALL \
                   or policy is PackageChange.POLICY_UPGRADE \
                   or policy is PackageChange.POLICY_FORCE
        if not isValidPolicy(policy):
            raise ValueError("Invalid package change policy: %s." % policy)
        self._policy = policy
        
    @property    
    def policy(self):
        return self._policy

    def create(self, availablePackage, installedPackage=None, installedRepository=None):
        """
        Compare an available package against an installed package and return a package change.
        The packages must have the same name, although the versions may be different.
        
        The install policy may be INSTALL (always install a package if possible, even if
        another version of the package is already installed), or UPGRADE (only install a
        package if it is not installed, or has a higher version than the installed 
        package). The default install policy is INSTALL.
                
        The following rules apply:
        
        - If there is no installed package, the available package will be installed.
        
        - If the available package has a lower version than the installed package, it will
          be skipped if the install policy is UPGRADE, and installed if the install policy
          is INSTALL.
        
        - If the available package has the same version as the installed package, it will
          be skipped, unless both packages are snapshots and the available package has a
          later timestamp than the installed package, in which the installed package is
          replaced.
        
        - If the available package has a higher version than the installed package, it will
          be installed, regardless of the install policy.
        
        :param availablePackage: the available package. Must not be None.
         
        :param installedPackage: the installed package. May be None.
        
        :param installedRepository: the repository of the installed packages, used to find the
        installed package if required. May be None.
        
        :param policy: the install policy. Defaults to INSTALL.
        
        :return: a package change object indicating if the package should be skipped, replaced,
        or installed.
        """
        # Pre-conditions.
        if availablePackage is None:
            raise ValueError("Cannot compare packages: no 'available package' specified.")
        if not isinstance(availablePackage, Package):
            raise TypeError("Cannot compare packages: 'available package' has incorrect type %s." % type(availablePackage))

        def isUpgradePolicy(): return self.policy == PackageChange.POLICY_UPGRADE
        def isForcePolicy(): return self.policy == PackageChange.POLICY_FORCE
        def isInstallPolicy(): return self.policy == PackageChange.POLICY_INSTALL

        # Get the installed package from the installed packages repository, if required.
        if installedPackage is None and installedRepository is not None:
            if not isinstance(installedRepository, PackageRepository):
                raise TypeError("Cannot compare packages: 'installed packages repository' has incorrect type %s." % type(installedRepository))
            # Get the installed package from the repository, based on the policy.            
            if isUpgradePolicy():
                # Find the package by name and by maximum version.
                installedPackage = installedRepository.findPackage(availablePackage.name)
            else:
                # Find the package by name and by version.
                installedPackage = installedRepository.findPackage(availablePackage)
                
        if installedPackage is not None:
            if not isinstance(installedPackage, Package):
                raise TypeError("Cannot compare packages: 'installed package' has incorrect type %s." % type(installedPackage))
            if availablePackage.name != installedPackage.name:
                raise PackageError("Cannot compare packages: names conflict: '%s' vs '%s'." % (availablePackage.name, installedPackage.name))

        # Create the initial change.
        change = PackageChange()
        change.available = availablePackage

        # If the package is not installed: INSTALL
        if installedPackage is None:
            (change.action, change.reason) = (PackageChange.INSTALL, PackageChange.REASON_NOT_INSTALLED)
        # Otherwise: check if available package represents an upgrade over the installed package.
        else:
            change.installed = installedPackage
            comparison = comparePackageVersions(availablePackage, installedPackage)

            # If available package has lower version than installed package: SKIP or INSTALL.
            if comparison < 0:
                if isUpgradePolicy():
                    (change.action, change.reason) = (PackageChange.SKIP, PackageChange.REASON_ALREADY_INSTALLED)
                else:
                    (change.action, change.reason) = (PackageChange.INSTALL, PackageChange.REASON_NOT_INSTALLED)
            # Available package and installed package have same version: SKIP or REPLACE.
            elif comparison == 0:
                if isForcePolicy():
                    (change.action, change.reason) = (PackageChange.REPLACE, PackageChange.REASON_FORCE_REPLACE)
                elif replacingSnapshot(availablePackage, installedPackage):
                    (change.action, change.reason) = (PackageChange.REPLACE, PackageChange.REASON_NEWER_VERSION)
                else:
                    (change.action, change.reason) = (PackageChange.SKIP, PackageChange.REASON_ALREADY_INSTALLED)
            # If available package has higher version than installed package: INSTALL
            elif comparison > 0:
                (change.action, change.reason) = (PackageChange.INSTALL, PackageChange.REASON_NEWER_VERSION)

        return change

class PackageChanges(object):

    def __init__(self):
        self.installs = []
        self.upgrades = []
        self.skips = []

    def hasInstall(self):
        return len(self.installs) > 0

    def hasUpgrade(self):
        return len(self.upgrades) > 0
