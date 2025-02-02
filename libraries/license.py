import os
import datetime
import shutil

from propertyFileOps import loadJavaStyleProperties

class License:
    
    """ Class representing a minestar license file. """
    
    PRODUCT_PREFIX = 'property_product.'
    
    def __init__(self, path):
        self.__path = path
        self.__properties = None
        self.__productNames = None

    @property
    def version(self):
        return self.__getProperty('version')

    @property
    def creationDate(self):
        return _timestampStringToDate(self.__getProperty('creationDate'))
    
    @property
    def startDate(self):
        return _timestampStringToDate(self.__getProperty('startDate'))
    
    @property
    def expiryDate(self):
        return _timestampStringToDate(self.__getProperty('expirationDate'))
 
    @property
    def supportType(self):
        return self.__getProperty('property_supportType')
    
    @property
    def supportExpiryDate(self):
        return _timestampStringToDate(self.__getProperty('property_supportExpiry'))
    
    @property
    def signature(self):
        return self.__getProperty('signature')
    
    @property
    def customerName(self):
        return self.__getProperty('property_customerName')
    
    @property
    def siteName(self):
        return self.__getProperty('property_siteName')
    
    @property
    def productNames(self):
        if self.__productNames is None:
            self.__productNames = self.__loadProductNames()
        return self.__productNames
        
    def __loadProductNames(self):    
        result = []
        for key in self.__getPropertiesStartingWith(self.PRODUCT_PREFIX):
            value = self.__properties[key]
            if value.lower() == 'true':
                result.append(key[len(self.PRODUCT_PREFIX):])
        return result
    
    def __getPropertiesStartingWith(self, prefix):
        result = {}
        if self.__properties is None:
            self.__properties = self.__loadProperties()
        for key in self.__properties:
            if key.startswith(prefix):
                result[key] = self.__properties[key]
        return result
    
    def __getProperty(self, key):
        # Load the properties if required.
        if self.__properties is None:
            self.__properties = self.__loadProperties()
        # Check if the key exists.    
        if not self.__properties.has_key(key):
            return None
        # Return the property associated with the key.
        return self.__properties[key]
    
    def __loadProperties(self):
        if not os.access(self.__path, os.R_OK):
            raise Exception ('Cannot access license file at "%s"' % self.__path)
        (sources,properties) = loadJavaStyleProperties(self.__path)
        return properties

    def saveAs(self, path):
        # Verify that license was (or can be) loaded.
        if self.__properties is None:
            self.__loadProperties()
        # Copy the file to the path.
        copyFile(self.__path, path)

def _timestampStringToDate(timestampStr):
    if (timestampStr is None) or timestampStr == '' or timestampStr == 'none':
        return None
    timestamp = _timestampStrToSecondsSinceEpoch(timestampStr)
    return datetime.datetime.utcfromtimestamp(timestamp)

def _timestampStrToSecondsSinceEpoch(timestampStr):
    # Timestamp in license file is stored as milliseconds, but python timestamp
    # functions expect seconds. 
    return long(timestampStr) / 1e3

# TODO copied from install.py -- should move to common code 
def copyFile(src, dst):
    # If the destination file is a directory, then append the basename of the source file.
    # e.g. copyFile('/x/y/z/foo.txt', '/a/b/c') => copyFile('/x/y/z/foo.txt', '/a/b/c/foo.txt')
    if os.path.exists(dst) and os.path.isdir(dst):
        dst = os.path.join(dst, os.path.basename(src))
    shutil.copyfile(src, dst)
