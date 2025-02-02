from java.lang import System
from minestar.platform.deployment import MstarPaths
from minestar.platform.bootstrap import OptionSets
from com.mincom.base.resource import ResTools
from com.mincom.util.permission.privilege import Privilege
from com.mincom.util.permission.privilege import ProductName
from com.mincom.util.permission.license import LicenseFactory

def system(key):
    return System.getProperty(key)

def interpret(format):
    return MstarPaths.interpretFormat(format)

def variable(name):
    return MstarPaths.interpretVar(name)

def option(optionSetName, key):
    optionSet = OptionSets.getOptionSet(optionSetName)
    if optionSet is None:
        return None
    result = ResTools.resolve(optionSet, key)
    return result

def options(optionSetName):
    optionSet = OptionSets.getOptionSet(optionSetName)
    if optionSet is None:
        return None
    keys = optionSet.getKeys()
    result = {}
    iter = keys.iterator()
    while iter.hasNext():
        key = iter.next()
        result[key] = ResTools.resolve(optionSet, key)
    return result
    
def isOptionTrue(optionSetName, key, defaultValue):
    optionSet = OptionSets.getOptionSet(optionSetName)
    if optionSet is None:
        return defaultValue
    value = ResTools.resolveboolean(optionSet, key)
    if value is None:
        return defaultValue
    return value

def isPrivileged(privilege):
    return Privilege.hasPrivilege(Privilege(privilege))

def optionSets():
    return OptionSets.getOptionSetNames()

def isLicensed(license):
    product = ProductName.findProductName(license)
    if product:
        return LicenseFactory.isProductLicensed(product)
    return False
