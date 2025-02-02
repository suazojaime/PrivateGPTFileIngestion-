import re

from types import StringTypes


class Version(object):

    """
    Class representing a version. A version has a string value with no defined
    pattern, other than starting with a number. The version may be split into
    major and minor parts, depending on the presence of a split character, which
    is typically '-'. If the version ends with '-SNAPSHOT' it is considered to
    be a 'snapshot' release. 
    
    E.g. '1', '1.0', '1-SNAPSHOT', '1.2.3-SNAPSHOT', '1.0-v1', '1.8-M1',
         '1.8-M1-SNAPSHOT', '2016B', '8u65-1', etc.

    A version such as "1.0" has major of "1.0", no minor, and is not a snapshot.

    A version such as "1.0-1" has a major of "1.0", a minor of "1", and is not
    a snapshot.
    
    A version such as "1.0-1-SNAPSHOT" has a major of "1.0", a minor of "1-SNAPSHOT",
    and is a snapshot.
    """

    # Regex for a version.
    # versionRegex = re.compile('^\d+(\.\d+)*(-.+)*$')
    versionRegex = re.compile('^\d.*(-.)*$')
    
    @classmethod
    def valid(cls, version):
        """ Determines if a version string is valid. """
        return cls.invalidReason(version) is None
        # return version is not None and \
        #        isinstance(version, StringTypes) and \
        #        Version.versionRegex.match(version) is not None

    @classmethod
    def invalidReason(cls, version):
        if version is None:
            return "no value specified for version"
        if not isinstance(version, StringTypes):
            return "expected a version of string type, but found type %s" % type(version)
        if not Version.versionRegex.match(version):
            return "version string is invalid: '%s'" % version
        return None
    
    @classmethod
    def compare(cls, lhs, rhs):
        """
        Compares two version strings. A version such as "1.0" is considered equal to
        a version such as "1.0.0". A version such as "1.0-SNAPSHOT" is considered less
        than a version such as "1.0". Otherwise, natural string ordering is used for
        comparisons.
        
        :param lhs: the LHS version. Must be a valid version string. 
        :param rhs: the RHS version. Must be a valid version string.
        :return: -1 if LHS is less than RHS, +1 if LHS is greater than RHS, 0 otherwise.
        """
        if not cls.valid(lhs):
            raise ValueError("Cannot compare versions: LHS value %s is invalid." % quoted(lhs))
        if not cls.valid(rhs):
            raise ValueError("Cannot compare versions: RHS value %s is invalid ." % quoted(rhs))
        
        # Check if LHS is same as RHS.
        if lhs is rhs or lhs == rhs:
            return 0
        
        # Split LHS and RHS into (major, minor, snapshot)
        (lhsMajor,lhsMinor,lhsSnapshot) = cls.splitIntoMajorMinorSnapshot(lhs)
        (rhsMajor,rhsMinor,rhsSnapshot) = cls.splitIntoMajorMinorSnapshot(rhs)

        # Get canonical form of LHS/RHS major versions.
        (lhsMajor, rhsMajor) = cls._canonicalMajorVersions(lhsMajor, rhsMajor)
        
        # Compare majors.
        if lhsMajor < rhsMajor: return -1
        if lhsMajor > rhsMajor: return 1
        
        # Majors are the same. Compare minors.
        if lhsMinor < rhsMinor: return -1
        if lhsMinor > rhsMinor: return 1

        # Minors are the same. Compare snapshots.
        
        # e.g. '1.0' vs '1.0-SNAPSHOT' => greater than.
        if lhsSnapshot < rhsSnapshot: return 1
        
        # e.g. '1.0-SNAPSHOT' vs '1.0' => less than.
        if lhsSnapshot > rhsSnapshot: return -1
        
        # Snapshots are the same.
        return 0

    @classmethod
    def _getLeadingVersion(cls, string):
        versionPattern = re.compile('^\d+(\.\d+)*')
        match = versionPattern.match(string)
        if match:
            return string[0:match.end()]
        return None
    
    @classmethod
    def _canonicalMajorVersions(cls, lhsMajor, rhsMajor):
        """ Get the canonical form of the LHS and RHS major version strings. Adds trailing '0' to 
            the leading integers as required so that leading integers are balanced, e.g. if LHS
            is '1.0xyz' and RHS is '1.0.0xyz' then convert LHS to '1.0.0xyz'. """
        
        # Extract leading version number string, e.g. '8u65' -> '8', '1.0-1' -> '1.0'
        lhsMajorNums = cls._getLeadingVersion(lhsMajor)
        rhsMajorNums = cls._getLeadingVersion(rhsMajor)

        # Find the remaining non-integer parts of the LHS/RHS major strings (e.g. '1.2.x' -> '.x').
        lhsMajorRemain = lhsMajor[len(lhsMajorNums):]
        rhsMajorRemain = rhsMajor[len(rhsMajorNums):]
        
        # Convert majors from list of strings to list of ints (for leading ints only).
        lhsMajorNums = [x for x in lhsMajorNums.split('.') if x.isdigit()]
        rhsMajorNums = [x for x in rhsMajorNums.split('.') if x.isdigit()]

        # Convert the LHS/RHS major number strings to ints. This will ensure that '2016' is
        # greater than '4' (which would not be the case for a string ordering).
        lhsMajor = [int(x) for x in lhsMajorNums]
        rhsMajor = [int(x) for x in rhsMajorNums]

        # Ensure that majors have same length (e.g. '1' vs '1.0' => '1.0' vs '1.0'). This
        # ensures that '1.0.0' is not greater than '1.0'.
        while len(lhsMajor) < len(rhsMajor): lhsMajor.append(0)
        while len(rhsMajor) < len(lhsMajor): rhsMajor.append(0)

        # Add the remaining non-integer parts, if any. Natural string ordering is used here.
        if len(lhsMajorRemain) > 0 or len(rhsMajorRemain) > 0:
            lhsMajor.append(lhsMajorRemain or '')
            rhsMajor.append(rhsMajorRemain or '')
        
        return (lhsMajor, rhsMajor)
    
    @classmethod
    def isSnapshot(cls, version):
        """ Determines if a version is a snapshot (i.e. if it ends with '-SNAPSHOT'). """
        if not Version.valid(version):
            raise ValueError("Cannot determine snapshot: version has invalid value '%s'." % quoted(version))
        return version.endswith('-SNAPSHOT')
    
    @classmethod
    def equalTo(cls, x, y):
        """ 
        Determines if one version is equal to another version. Note that '1.0' is equal to 
        each of '1', '1.0', and '1.0.0'. 
        
        :param x the first version. Must not be None.
        :param y the second version. Must not be None.
        :return True if version X is equal to version Y, False otherwise.
        """
        return cls.compare(x, y) == 0
    
    @classmethod
    def greaterThan(cls, x, y):
        """ Returns True if version X is greater than version Y, else returns False. """
        return cls.compare(x, y) > 0
    
    @classmethod
    def lessThan(cls, x, y):
        """ Returns True if version X is less than version Y, else returns False. """
        return cls.compare(x, y) < 0
    
    @classmethod
    def greaterThanOrEqualTo(cls, x, y):
        """ Returns True if version X is greater than or equal to version Y, else returns False. """
        return cls.compare(x, y) >= 0
    
    @classmethod
    def lessThanOrEqualTo(cls, x, y):
        """ Returns True if version X is less than or equal to version Y, else returns False. """
        return cls.compare(x, y) <= 0

    @classmethod
    def minimum(cls, versions=[]):
        """ Find the minimum version from a collection of versions. Returns None if the collection is empty. """
        if versions is None:
            raise ValueError("Cannot determine minimum version: no versions specified.")
        minimum = None
        for version in versions:
            if minimum is None or cls.lessThan(version, minimum):
                minimum = version
        return minimum

    @classmethod
    def maximum(cls, versions=[]):
        """ Find the maximum version from a collection of versions. Returns None if the collection is empty. """
        if versions is None:
            raise ValueError("Cannot determine maximum version: no versions specified.")
        maximum = None
        for version in versions:
            if maximum is None or cls.greaterThan(version, maximum):
                maximum = version
        return maximum

    @classmethod
    def splitIntoMajorMinor(cls, version, splitChar='-'):
        """ 
        Split a version string into major and minor parts, based on the presence
        of the split character. For example, split('1.0-SNAPSHOT', '-') would
        return the tuple ('1.0', 'SNAPSHOT').
        
        :param version the version string to be split into major and minor parts. Must not be None.
        
        :param splitChar the split character. Defaults to '-'.
        
        :return a tuple containing the major and minor parts of the version. The minor part will be
        None if the version string does not contain the split character.
        """
        if not Version.valid(version):
            raise ValueError("Cannot split version: version has invalid value %s." % quoted(version))
        parts = version.split(splitChar, 1)
        major = parts[0]
        minor = None if len(parts) <= 1 else parts[1]
        return (major, minor)

    @classmethod
    def splitIntoMajorMinorSnapshot(cls, version, splitChar='-'):
        """ 
        Split a version string into major, minor, and snapshot parts, based on
        the presence of the split character. For example, split('1.0-SNAPSHOT', '-')
        would return the tuple ('1.0', None, 'SNAPSHOT') while split('1.0-1-SNAPSHOT', '-')
        would return the tuple ('1.0', '1', 'SNAPSHOT').
        
        :param version the version string to be split into major, minor, and snapshot parts. Must
        not be N)one.
        
        :param splitChar the split character. Defaults to '-'.
        
        :return a tuple containing the major, minor, and snapshot parts of the version. The minor
        and snapshots parts may be None.
        """
        if not Version.valid(version):
            raise ValueError("Cannot split version: version has invalid value %s." % quoted(version))
        (major, minor) = cls.splitIntoMajorMinor(version, splitChar)
        snapshot = None
        if minor == 'SNAPSHOT':
            snapshot = minor
            minor = None
        elif minor is not None and minor.endswith('-SNAPSHOT'):
            length = len(minor)
            suffix = len('-SNAPSHOT')
            snapshot = minor[length-suffix+1:length]
            minor = minor[0:length-suffix]
            if len(minor) == 0:
                minor = None
        return (major,minor,snapshot)
        
    @classmethod
    def compatible(cls, currentVersion, requiredVersion):
        """
        Determines if the current version is compatible with required version. Returns true if
        the current version is equal to or greater than the required version, e.g.
        version '1.1' is compatible with version '1.0' and version '1.1' but not
        with version '1.2'.
        
        :param currentVersion: the current version.
        :param requiredVersion: the requiredVersion.
        :return: True if the current version is compatible with the required version; False otherwise.
        """
        return cls.greaterThanOrEqualTo(currentVersion, requiredVersion)


def quoted(s):
    """ Get a quoted form of the string, handling None values. """
    return 'None' if s is None else "'%s'" % str(s)
