import re

from mstarpaths import interpretFormatOverride, interpretPathOverride

#
# Helper functions for processing config values.
#

# Regex for a placeholder used in a config value, e.g. "{MSTAR}".
_placeholderRegex = re.compile("{[A-Z0-9_]+}")

# Regex for a string that possibly contains a path placeholder, e.g. "{MSTAR_HOME}/foo".
_possiblePathRegex = re.compile("{[A-Z0-9_]+}/[a-zA-Z0-9_-]+")


def _containsPlaceHolder(string):
    """ Return True if the string contains a placeholder, e.g. "{MSTAR_HOME}". """
    return string is not None and _placeholderRegex.search(string) is not None

def _containsPossiblePath(string):
    """ Return True if the string contains a placeholder followed by a path element, e.g. "{MSTAR_HOME}/foo". """
    return string is not None and _possiblePathRegex.search(string) is not None

def _isStringValue(value):
    """ Return True if the value is a string type. """
    return value is not None and (type(value) == type('') or type(value) == type(u''))

def _resolvePlaceholders(value, config):
    """ Resolve placeholders in the value. """
    loopCount = 0 # Don't expand value too many times.
    while loopCount < 100 and _isStringValue(value) and _containsPlaceHolder(value):
        newValue = interpretPathOverride(value, config) if _containsPossiblePath(value) else interpretFormatOverride(value, config)
        if newValue is None:
            newValue = ''
        loopCount += 1
        # Stop expanding if the new value is not different to the old value,
        # even if it still contains '{' ... '}', e.g. if value is "{0}".
        if value == newValue:
            break
        value = newValue
    return value

def getConfigValueString(config,key,options=None):
    """ Get the string representation of a config value. If 'expand' is present
        in the options and the value contains a '{...}' substring then the value
        is processed via the 'interpretVarOverride' function. """
    value = ''
    if config.has_key(key):
        value = config[key]
        # If the value is a string and the 'resolve' option is set, then interpret the value
        # if it contains a placeholder (e.g. "{MSTAR_HOME}", "{MSTAR_HOME}/foo"..
        if _isStringValue(value) and options is not None and options.has_key('resolve'):
            value = _resolvePlaceholders(value, config)
    return value
