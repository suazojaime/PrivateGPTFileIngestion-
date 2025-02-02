import datetime
from functools import total_ordering
from types import StringTypes


class Timestamp:

    """ Class representing timestamps used within minestar scripts. Only useful for comparisons. """

    FORMAT = "%Y%m%d%H%M%S"

    def __init__(self):
        raise RuntimeError("Do not create an instance of this class!")

    @classmethod
    def _currentTimestamp(cls):
        now = datetime.datetime.utcnow()
        return Timestamp._fromString(Timestamp._toString(now))

    @classmethod
    def _toString(cls, dt):
        # Only 3 characters of microseconds.
        return "%s%03d" % (dt.strftime("%Y%m%d%H%M%S"), dt.microsecond/1000)
    
    @classmethod
    def _fromString(cls, timestampStr):
        dt = datetime.datetime.strptime(timestampStr, "%Y%m%d%H%M%S%f")
        # Only three significant digits of microseconds.
        return dt.replace(microsecond=dt.microsecond/1000)

    @classmethod
    def now(cls):
        return cls._toString(cls._currentTimestamp())
    
    @classmethod
    def before(cls, timestamp):
        """ Return a timestamp that is before this specified timestamp (by some arbitrary amount). """
        if timestamp is None:
            raise ValueError("No timestamp specified.")
        dt = cls._fromString(timestamp)
        return cls._toString(dt - datetime.timedelta(hours=1))

    @classmethod
    def after(cls, timestamp):
        """ Return a timestamp that is after this specified timestamp (by some arbitrary amount). """
        if timestamp is None:
            raise ValueError("No timestamp specified.")
        dt = cls._fromString(timestamp)
        return cls._toString(dt + datetime.timedelta(hours=1))
        
