import locale
import time
import types

DEFAULT_LANGUAGE = "en"
DEFAULT_COUNTRY = "US"
DEFAULT_TIME_ZONE = "Australia/Brisbane"
DEFAULT_DEFAULT_DAY_START = "6AM"

# TimeZone guessing stuff - tuple implies to check daylight saving and use the second entry if none
TIME_ZONE_GUESS_BY_HOUR = {
    -12: "Pacific/Auckland",
    -11: "Pacific/Noumea",
    -10: ("Australia/Sydney", "Australia/Brisbane"),
    -9: "Asia/Jayapura",
    -8: "Australia/Perth",
    -7: "Asia/Jakarta",
    -6: "Asia/Colombo",
    -5: "Asia/Karachi",
    -4: "Asia/Dubai",
    -3: "Europe/Moscow",
    -2: "Africa/Johannesburg",
    -1: "Europe/Stockholm",
    0: "Europe/London",
    1: "Atlantic/Azores",
    2: "Atlantic/South_Georgia",
    3: "America/Sao_Paulo",
    4: "America/Santiago",
    5: "America/Montreal",
    6: "America/Chicago",
    7: ("America/Denver", "America/Phoenix"),
    8: "America/Los_Angeles",
    9: "America/Anchorage",
    10: "Pacific/Honolulu",
    11: "Pacific/Pago_Pago"
}
SECS_PER_HOUR = 3600

def _guessTimeZone():
    "guess the timezone string in Java format, e.g. Australia/Brisbane"
    # Can probably get from the OS but Python and Java seem to use different identification schemes
    timezones = TIME_ZONE_GUESS_BY_HOUR.get(time.timezone / SECS_PER_HOUR)
    if type(timezones) == types.TupleType:
        # If there is no daylight saving, use the second entry otherwise the first
        if time.daylight != 0:
            return timezones[0]
        else:
            return timezones[1]
    else:
        return timezones

def guessSystemOverrides(computer, suite):
    "returns a dictionary of likely overrides for a system given a computer name and a suite"
    result = {}
    result["_HOME"] = computer
    result["_DBROLE"] = "PRODUCTION"
    result["REPORT_SERVER"] = computer

    # Add this back in once the exception it causes is sorted out
    #result["_FTPSERVER"] = computer

    # Guess the localisation settings as best we can
    localeInfo = locale.getdefaultlocale()[0]
    if localeInfo == None:
        # Default this value in on the odd occasion where locale is not returned correctly by the OS.
        localeInfo = "en_AU"
        print 'Forcing localeInfo to be set to : %s' % localeInfo
    language = localeInfo[0:2]
    if language != DEFAULT_LANGUAGE:
        result["_LANGUAGE"] = localeInfo[0:2]
    country = localeInfo[2:]
    if country != DEFAULT_COUNTRY:
        result["_COUNTRY"] = localeInfo[3:]
    if country == "US":
        result["_UNITSET"] = "miningImperial"
    timeZoneGuess = _guessTimeZone()
    if timeZoneGuess != None and timeZoneGuess != DEFAULT_TIME_ZONE:
        result["_TIMEZONE"] = timeZoneGuess

    # For non-Enterprise installs, assume a single db instance & a cut-down set of services
    if suite == "Personal":
        result["_INSTANCE1"] = "HIST"
        result["_START"] = "MineTracking,StandardJobExecutor"
    elif suite == "Workgroup":
        result["_INSTANCE1"] = "HIST"
        result["_START"] = "CommsServer,MineTracking,StandardJobExecutor,CommsController"
    return result

