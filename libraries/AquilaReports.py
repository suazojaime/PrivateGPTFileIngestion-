import minestar

logger = minestar.initApp()

# Keys into the dictionary returned by load()
TYPE_KEY                = "TYPE"
TEMPLATE_KEY            = "TEMPLATE_NAME"
TITLE_KEY               = "TITLE"
SUBTITLE_KEY            = "SUBTITLE"
TITLE_DATE_FORMAT_KEY   = "TITLE_DATE_FORMAT"

# Keys that clients shouldn't need because functions exist
_PARAMETERS_KEY      = "PARAMETERS"
_COLUMNS_KEY         = "COLUMNS"
_COLUMN_DESCS_KEY    = "COLUMN_DESC"
_COLUMN_CONVS_KEY    = "COLUMN_CONV"
_COLUMN_FORMATS_KEY  = "COLUMN_FORMAT"

# Templates used for setting the orientation
LANDSCAPE_TEMPLATE = "HTMLLANDSCAPE"
PORTRAIT_TEMPLATE  = "HTML"


def load(filename):
    "load the AQreport in filename and returns the result as a dictionary"

    # this is close enough for now
    (sources, properties) = minestar.loadJavaStyleProperties(filename, [])
    result = {}
    for key in properties.keys():
        result[key] = trimValue(properties[key])
    return result


def getParameters(dict):
    "returns None if parameters are not defined in a report, otherwise the list of parameters"
    if dict.has_key(_PARAMETERS_KEY):
        return dict[_PARAMETERS_KEY].split("|")
    else:
        return None

        
def getColumns(dict):
    "returns None if columns are not defined in a report, otherwise the list of columns"
    if dict.has_key(_COLUMNS_KEY):
        return dict[_COLUMNS_KEY].split("|")
    else:
        return None

        
def getColumnDescriptions(dict):
    "returns None if column descriptions are not defined in a report, otherwise the list of column descriptions"
    if dict.has_key(_COLUMN_DESCS_KEY):
        return dict[_COLUMN_DESCS_KEY].split("|")
    else:
        return None


def getColumnConversions(dict):
    "returns None if column conversions are not defined in a report, otherwise the list of column conversions"
    if dict.has_key(_COLUMN_CONVS_KEY):
        return dict[_COLUMN_CONVS_KEY].split("|")
    else:
        return None


def getColumnFormats(dict):
    "returns None if column formats are not defined in a report, otherwise the list of column formats"
    if dict.has_key(_COLUMN_FORMATS_KEY):
        return dict[_COLUMN_FORMATS_KEY].split("|")
    else:
        return None


def getQueryFor(dict, dbType):
    "returns the query to use for a given database type or the default query if no db specific query is defined"
    queryKey = "SQL_QUERY_" + dbType
    if dict.has_key(queryKey):
        return dict[queryKey]
    else:
        return dict.get("SQL_QUERY_DEFAULT")


def getAboveIncludeFiles(dict):
    "return the list of filenames to include above the report body"
    result = []
    for i in range(1, 10):
        if dict.has_key("INCLUDE_ABOVE" + i):
            result.append(dict["INCLUDE_ABOVE" + i])
    return result


def getBelowIncludeFiles(dict):
    "return the list of filenames to include below the report body"
    result = []
    for i in range(1, 10):
        if dict.has_key("INCLUDE_BELOW" + i):
            result.append(dict["INCLUDE_BELOW" + i])
    return result


def trimValue(value):
    "strip surrounding whitespace then take off surrounding double-quotes if any"
    result = value.strip()
    if len(result) > 0 and result[0] == '"' and result[-1] == '"':
        return result[1:-1]
    else:
        return result

    
