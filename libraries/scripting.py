from com.mincom.base.resource import ResourceManager
from com.mincom.base.resource import ResTools
from minestar.platform.deployment import MstarPaths

#def hasExtension(name):
#    ExtensionTools.reload()
#    library = ExtensionTools.getExtensionLibrary()
#    ext = library.getExtensionByShortName(name)
#    if ext is not None:
#        versions = ExtensionTools.getInstalledExtensionVersions()
#        version = versions[ext.getName()]
#        return version is not None
#    return 0

def __context(name):
    import sys
    if not sys.minestar.has_key(name):
        raise NameError(name)
    return sys.minestar[name]

def field(name):
    """return the value of the named field"""
    return __context('form').getFieldValue(name)

def property(name):
    from com.mincom.util.general import BeanTools
    return BeanTools.getPropertyValue(firstSelectedItem(), name)

def page():
    return __context('page')

def firstSelectedItem():
    return __context('page').getFirstSelectedItem()

def testConfigOption(bundleName, option):
    rp = ResourceManager.getProviderForName(bundleName)
    return ResTools.resolveboolean(rp, option)

def getConfigOption(bundleName, option):
    return getConfigOptionWithDefault(bundleName, option, None)


def getConfigOptionWithDefault(bundleName, option, default):
    """ Testing the return of a resource value using ResTools.
    >>> getConfigOptionWithDefault('testBundleName', 'testOption', 'testDefault')
    u'testDefault'
    """

    rp = ResourceManager.getProviderForName(bundleName)
    return ResTools.resolve(rp, option, default)

def getConfigPathOption(bundleName, option):
    return getConfigPathOptionWithDefault(bundleName, option, None)


def getConfigNetworkPathOption(bundleName, option):
    return getConfigNetworkPathOptionWithDefault(bundleName, option, None)


def getConfigPathOptionWithDefault(bundleName, option, default):
    rp = ResourceManager.getProviderForName(bundleName)
    return MstarPaths.interpretPath(ResTools.resolve(rp, option, default))

def getConfigNetworkPathOptionWithDefault(bundleName, option, default):
    rp = ResourceManager.getProviderForName(bundleName)
    return interpretNetworkPath(ResTools.resolve(rp, option, default))

def define(name):
    from java.lang import System
    return System.getProperty(name)

def interpretPath(path):
    return MstarPaths.interpretPath(path)

def interpretNetworkPath(path):
    return MstarPaths.interpretNetworkPath(path)

def interpretVar(var):
    return MstarPaths.interpretVar(var)



# Enable doctest
#if __name__ == "__main__":
#    import doctest
#    doctest.testmod()
