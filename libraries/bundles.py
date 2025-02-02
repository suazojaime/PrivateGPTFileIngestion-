import os

import mstarpaths
import ufs

class Bundles(object):
    
    """ Class for managing bundles. """
    
    @classmethod
    def getBundleNamesFromProperties(cls, properties):
        """ Get the bundle names from the 'CONTENTS' in the properties. """
        bundleNames = []
        if 'CONTENTS' in properties:
            contents = properties['CONTENTS']
            bundleNames = contents.split(',')
        return bundleNames
    
    @classmethod
    def getBundle(cls, bundleName, config=None):
        """ Get the (possibly empty) bundle for the bundle name. """
        if bundleName is None:
            return []
        # Get bundle from MSTAR_CONFIG if bundle name has leading '/' (e.g. '/MineStar.overrides').
        if bundleName.startswith('/'):
            bundle = cls._getBundleFromSystem(bundleName, config)
            if bundle is not None:
                return bundle
            # Get the bundle by removing the leading '/'.
            return cls._getBundleOnUFSPath(bundleName[1:])
        # Otherwise get bundle as resource property files on the UFS path.
        return cls._getBundleOnUFSPath("/res/%s.properties" % bundleName.replace('.','/'))

    @classmethod
    def _getBundleFromSystem(cls, bundleName, config=None):
        # Check for {MSTAR_CONFIG}/$bundleName
        path = mstarpaths.interpretPathOverride("{MSTAR_CONFIG}", config)
        f = os.path.join(path, bundleName[1:])
        if os.path.exists(f):
            return [f]
        # Check for {MSTAR_CREDS}/$bundleName
        path = mstarpaths.interpretPathOverride("{MSTAR_CREDS}", config)
        f = os.path.join(path, bundleName[1:])
        if os.path.exists(f):
            return [f]
        return None

    @classmethod
    def _getBundleOnUFSPath(cls,bundleName):
        ufsPath = mstarpaths.interpretVar("UFS_PATH")
        root = ufs.getRoot(ufsPath)
        bundle = root.get(bundleName)
        return bundle.getAllPhysicalFiles() if bundle is not None else []

    @classmethod
    def getPropertiesForBundleName(cls, bundleName):
        return cls.getPropertiesForBundle(Bundles.getBundle(bundleName))
    
    @classmethod
    def getPropertiesForBundle(cls, bundle):
        """ Get the annotated properties of a bundle. Returns Map<PropertyName,AnnotatedProperty>. """
        # Check for null.
        if bundle is None:
            return {}
        # Get the annotated properties for the bundle.    
        from annotatedProperties import AnnotatedProperties
        return AnnotatedProperties.loadFromBundle(bundle)
        

    @classmethod
    def isBundleName(cls, str):
        return (str is not None) and ((type(str) == type('')) or (type(str) == type(u'')))
