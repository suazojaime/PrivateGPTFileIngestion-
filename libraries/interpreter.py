import i18n
import os

from pathOps import simplifyPath


class VariableError(RuntimeError):
    """ Base class for variable errors. """
    pass


class MissingVariableError(VariableError):

    """ Class indicating that a variable is missing. """

    def __init__(self, variable):
        msg = i18n.translate("Missing required variable: %s") % variable
        super(MissingVariableError, self).__init__(msg)
        self._variable = variable

    @property
    def variable(self):
        return self._variable


class TooManySubstitutionsError(VariableError):

    """ Class indicating that there are too many variable substitutions. """

    def __init__(self, pattern):
        super(TooManySubstitutionsError, self).__init__()
        self.message = i18n.translate("Too many substitutions for pattern '%s'.") % pattern
        
        
def getCurrentTimeConfig():
    import time
    t = time.localtime()
    result = {}
    _addTimeField(result, "YYYY", t[0])
    _addTimeField(result, "MM", t[1])
    _addTimeField(result, "DD", t[2])
    _addTimeField(result, "HH", t[3])
    _addTimeField(result, "NN", t[4])
    _addTimeField(result, "SS", t[5])
    return result

def _addTimeField(dict, pattern, value):
    value = str(value)
    while len(value) < len(pattern):
        value = "0" + value
    dict[pattern] = value


def _possibleSeparatorFor(s):
    # Get the separator char: - '/' if s contains '/' and not '\'
    #                         - '\' if s contains '\' and not '/'
    #                         - otherwise the os path separator.
    if '/' in s and '\\' not in s:
        sep = '/'
    elif '\\' in s and '/' not in s:
        sep = '\\'
    else:
        sep = os.path.sep
    return sep


class Interpreter(object):

    """ Class for interpreting variables and paths, with placeholder substitution. """

    def __init__(self, config=None):
        # Don't use 'config or {}', need to keep actual config reference.
        self.config = config if config is not None else {}
        self._localOverrides = {}
        self._sourceRepository = None
        # print "## Interpreter::init() config=%s" % config

    def _getSourceRepository(self, overrides=None):
        if self._sourceRepository is None:
            # Get MSTAR_HOME (without using interpreter).
            mstarHome = self._lookupMStarHome(overrides or {})
            from sourceRepository import SourceRepository
            self._sourceRepository = SourceRepository.getInstance(mstarHome=mstarHome)
        return self._sourceRepository
    
    def _lookupMStarHome(self, overrides={}):
        # Try looking up MSTAR_HOME
        mstarHome = overrides.get('MSTAR_HOME') if 'MSTAR_HOME' in overrides else self.config.get('MSTAR_HOME')
        mstarInstall = overrides.get('MSTAR_INSTALL') if 'MSTAR_INSTALL' in overrides else self.config.get('MSTAR_INSTALL')
        # If no MSTAR_HOME, try deriving as '{MSTAR_INSTALL}/mstarHome'.
        if mstarHome is None and mstarInstall is not None:
            sep = _possibleSeparatorFor(mstarInstall)
            mstarHome = mstarInstall + sep + 'mstarHome'
            self._localOverrides['MSTAR_HOME'] = mstarHome
        # If no MSTAR_INSTALL, derive from MSTAR_HOME (which may represent a repository).    
        if mstarInstall is None and mstarHome is not None:
            # Within a repository: ${mstarHome}/../../../../runtime/target
            # Otherwise          : ${mstarHome}/..
            sep = _possibleSeparatorFor(mstarHome)
            if mstarHome.endswith('config'):
                mstarInstall = sep.join([mstarHome, '..', '..', '..', '..', 'runtime', 'target'])
            else:
                mstarInstall = mstarHome + sep + '..'
            self._localOverrides['MSTAR_INSTALL'] = mstarInstall
        return mstarHome        
        
    def interpretVar(self, var, overrides=None):
        # Combine the local overrides and the user overrides (preference to user overrides).
        if len(self._localOverrides) > 0:
            combined = self._localOverrides.copy()
            if overrides is not None:
                combined.update(overrides)
            overrides = combined
        
        # Get the value from the user overrides, if present. 
        if overrides and var in overrides:
            return overrides[var]

        # Check for special cases if running from a source repository.
        sourceRepository = self._getSourceRepository(overrides)
        if sourceRepository.running:
            value = sourceRepository.interpretVar(var)
            if value is not None:
                # TODO cache (var,value) in self.config?
                return value

        # Check local config again (may have been updated when creating repository).
        if var in self._localOverrides:
            return self._localOverrides[var]
        
        # Get the value from the local config, if present.
        if var in self.config:
            return self.config[var]

        # Could not interpret the variable, fail if 'MSTAR_HOME' was requested.
        if var == 'MSTAR_HOME':
            raise MissingVariableError('MSTAR_HOME')

        return None

    def interpretPath(self, path, overrides=None):
        return simplifyPath(self.interpretPattern(path, overrides))
    
    def interpretPattern(self, pattern, overrides=None):
        # Create local overrides combining the local time ('{YYYY}', etc)
        # and the supplied overrides (if any).
        localOverrides = getCurrentTimeConfig()
        if overrides is not None:
            localOverrides.update(overrides)
        return VariableSubstitution(interpreter=self).interpret(pattern, localOverrides)


class VariableSubstitution(object):

    """ Class for performing variable substitution. """

    def __init__(self, interpreter, maxLoopCount=100):
        self.interpreter = interpreter
        self.maxLoopCount = maxLoopCount

    def interpret(self, pattern, overrides=None):
        originalPattern = pattern
        loopCount = 0
        # Get the initial variable (if any).
        (p1,p2) = self._findVariable(pattern)
        while p1 >= 0 and p2 > (p1+1):
            # Try replacing the variable. If the new pattern is the same
            # as the old pattern then there are no more substitutions.
            oldPattern = pattern
            pattern = self._replaceVariable(pattern, (p1,p2), overrides)
            if pattern == oldPattern:
                break
            # Check that the number of substitutions is reasonable.    
            loopCount += 1
            if loopCount > self.maxLoopCount:
                raise TooManySubstitutionsError(originalPattern)
            # Find the next variable (if any) and repeat.    
            (p1,p2) = self._findVariable(pattern)
        return pattern

    @staticmethod
    def _findVariable(s):
        result = (-1, -1)
        if s is not None:
            p1 = s.find('{')
            p2 = -1 if p1 < 0 else s.find('}')
            result = (p1, p2)
        return result

    def _replaceVariable(self, pattern, (p1,p2), overrides):
        var = pattern[p1+1:p2]
        val = self.interpreter.interpretVar(var, overrides)
        if val is None:
            val = "{%s}" % var
        return pattern[:p1] + str(val) + pattern[p2+1:]
