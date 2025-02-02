# $Id: makeCatalogs.py,v 1.108 2008-03-11 23:40:52 johnf Exp $

import sys, os, string, types, cgi, zipfile, mstarpaths, ufstools
from xml.sax.saxutils import quoteattr

import mstarapplib, mstarpaths, ConfigurationFileIO, StringTools, JasperReports, AquilaReports, mstarrun, mstarpaths, ufs, minestar
from ConfigurationFileIO import PARAM_NAME, PARAM_DESC, PARAM_KIND, PARAM_TYPE, PARAM_CHOICES, PARAM_MODE, PARAM_MASK
from ConfigurationFileIO import PARAM_LABEL, PARAM_ENABLED_WHEN, PARAM_DEFAULT_VALUE, PARAM_OPTION, LEGAL_PARAM_KEYS, PARAM_READONLY, PARAM_MUTABLE_LIVE
from ConfigurationFileIO import PARAM_VISIBLE_WHEN, PARAM_CUSTOM, PARAM_SEPARATOR, PARAM_WIDGET, PARAM_UNITDEF, PARAM_LEVEL, PARAM_DISPLAY_ORDER
from ConfigurationFileIO import PARAM_LAYOUT, PARAM_LAYOUT_INFO, PARAM_PROCESS_ON_CHANGE, PARAM_DEFAULT_VALUE_LANGUAGE
from ConfigurationFileIO import DEFAULT_VALUE_LANGUAGES, LAYOUTS, PROCESS_ON_CHANGES

logger = minestar.initApp()


## Configuration settings ##

# Some flags
WARN_ON_NO_GROUP = 0

# Report prompt definitions table-id
REPORT_PROMPT_DEFINITIONS_TABLE = 'ReportPrompts'

# Table showing what prompts are used in what reports
REPORT_PROMPT_LISTS_TABLE = 'ReportPromptLists'

# Default tags to apply to catalogs
DEFAULT_TAGS = {
    'Reports': ['user'],
    'Pages': ['user'],
    'Collections': ['user'],
    'Tools': ['development'],
    'OptionSets': ['admin'],
    'Forms': ['general'],
    'DataSets': ['user'],
    'Documents': ['user'],
    'Permissions': ['admin'],
    }

DEFAULT_GROUP_LEVELS = {
    'window': 0,
    'tabset': 1,
    'tab': 2,
    'collapsed': 3,
    'region': 4,
    'box': 5,
    'plain': 6,
    }

# Field values which automatically imply a boolean field
AUTO_BOOLEAN_VALUES = ['true', 'false', 'yes', 'no']

# Keys supported in details dictionaries
DETAILS_IMPL = "implclass"
DETAILS_TAGS = "tags"
DETAILS_INSTANCE_TYPE = "instanceType"
DETAILS_PRIVILEGE = "privilege"

# Special keys supported for property groups
GROUP_SOURCE = "source"

# Definition of the field for entering remaining general parameters
ANY_PARAMETERS_ATTRS = {
    PARAM_NAME: "Parameters"
    }

# Template for building a region break
REGION_TEMPLATE = {
    PARAM_KIND: "group",
    PARAM_MODE: "region",
    PARAM_LABEL: "",
    }

# Template for building a period selector
PERIOD_TEMPLATE = {
    PARAM_TYPE: "string",
    PARAM_MODE: "period",
    PARAM_LABEL: "Period",
    PARAM_MASK: "1) Date Begin:,2) Date End:"
    }

# Template for building a period selector
AQRPT_PERIOD_TEMPLATE = {
    PARAM_TYPE: "string",
    PARAM_MODE: "period",
    PARAM_NAME: "Period",
    PARAM_OPTION: "Start_Date,End_Date"
    }

# Template for building a start time
AQRPT_STARTTIME_TEMPLATE = {
    PARAM_TYPE: "java.util.Date",
    PARAM_KIND: "javaclass",
    PARAM_NAME: "Start_Date",
    PARAM_LABEL: "Start Date",
    }

# Template for building an end time
AQRPT_ENDTIME_TEMPLATE = {
    PARAM_TYPE: "java.util.Date",
    PARAM_KIND: "javaclass",
    PARAM_NAME: "End_Date",
    PARAM_LABEL: "End Date",
    }

# Template for building an AQReport parameter
AQRPT_PARAM_TEMPLATE = {
    PARAM_TYPE: "string",
    }

# Template for building a formatting region break
FORMATTING_REGION = {
    PARAM_KIND: "group",
    PARAM_MODE: "collapsed",
    PARAM_LABEL: "Formatting",
    }

# Template for a template field
AQRPT_TEMPLATE_TEMPLATE = {
    PARAM_TYPE: "string",
    PARAM_NAME: "Template",
    PARAM_CHOICES: '["portrait", "landscape"]',
    PARAM_MODE: "entry",
    PARAM_DEFAULT_VALUE: "portrait",
    }

# Template for the GroupBy field
AQRPT_GROUPBY_TEMPLATE = {
    PARAM_TYPE: "string",
    PARAM_NAME: "Group By",
    PARAM_DEFAULT_VALUE: "",
    }

# Template for building a data source region
DATASOURCE_REGION = {
    PARAM_KIND: "group",
    PARAM_MODE: "region",
    PARAM_LABEL: "Data Source",
    PARAM_NAME: "Data Source Region",
    }

# Template for building a data source
DATASOURCE_TEMPLATE = {
    PARAM_TYPE: "string",
    PARAM_CHOICES: "system.DataSource",
    PARAM_NAME: "Data Source",
    PARAM_LABEL: " ",
    PARAM_DEFAULT_VALUE: "MineStar Database",
    }

# Template for a template field
OUTPUT_FMT_TEMPLATE = {
    PARAM_TYPE: "string",
    PARAM_NAME: "Output Format",
    PARAM_CHOICES: '{"pdf":"PDF","htm":"HTML","txt":"Plain Text","rep":"Business Objects"}',
    PARAM_DEFAULT_VALUE: "pdf",
    }


## Filename generation routines ##

def findFiles(searchDirs, relativePath):
    # allow to run from repository as well as installation
    if mstarpaths.runningFromRepository and relativePath.startswith("lib" + os.sep + "res"):
        relativePath = ".." + os.sep + "java" + relativePath[3:]
    result = []
    for dir in searchDirs:
        path = dir + relativePath
        if os.path.exists(path):
            result.append(path)
    return result

def findTableFiles(searchDirs, name):
    return findFiles(searchDirs, "/catalogs/%s.txt" % name)

def loadCatalogLines(searchPath, name, lang=None):
    root = ufs.getRoot(searchPath)
    ufsFile = root.get("/catalogs/%s.properties" % name)
    if ufsFile is None:
        return []
    else:
        return ufsFile.getTextLines()

def getBasenameForCatalog(name):
    # use old basenames for now to ensure no diffs while testing searching stuff
    if name == "Tools":
        return "MineStarApplications.properties"
    else:
        return "minestar%s.properties" % name


## Support routines ##

# Check that a value falls within a set of legal values. If it doesn't, log a warning and return the first legal value
def _checkEnum(value, legalValues, propertyName):
    if value in legalValues:
        return value
    else:
        defaultValue = legalValues[0]
        print "WARNING: bad %s value '%s' - assuming the default (%s) instead" % (propertyName, value, defaultValue)
        return defaultValue

# Load the list of items from a file
def loadItemList(filename):
    result = []
    f = open(filename)
    while 1:
        # Get the line, checking for EOF
        line = f.readline()
        if line == '':
            break

        # Build the result, ignoring comments and blank lines
        line =line.strip()
        if line == '' or line[0] == '#':
            continue
        result.append(line)
    f.close()
    return result


# Load the list of prompts per report from a file.
# The format is taken from DG120-Report Prompt Values4.txt, namely ...
# The first (header line) is ignored. Remaining lines are tab-separated
# fields where the first field is the report name and the second is
# the prompt name. A trailing comma on each field is also removed.
# The result is a dictionary indexed by report name where the values
# are lists.
def loadPromptsForReports(filename, promptDefns):
    result = {}
    f = open(filename)
    while 1:
        # Get the line, checking for EOF
        line = f.readline()
        if line == '':
            break

        # Build the result, ignoring comments and blank lines
        line =line.strip()
        sep = line.find("\t")
        if line == '' or line[0] == '#' or sep < 0:
            continue
        report = line[0:sep]
        if report[-1] == ',':
            report = report[0:-1]
        prompt = line[sep+1:]
        if prompt[-1] == ',':
            prompt = prompt[0:-1]
        if not promptDefns.has_key(prompt):
            print "warning: undefined prompt '%s'" % prompt
        prompts = result.get(report, [])
        prompts.append(prompt)
        result[report] = prompts
    f.close()
    return result


# Load the list of prompts per report via tables on the search list.
def loadPromptsForReportsFromTable(searchDirs, tableId, promptDefns):
    files = findTableFiles(searchDirs, tableId)
    result = {}
    # TODO: decide whether files needs to be iterated in the reverse order or not?
    for f in files:
        result.update(loadPromptsForReports(f, promptDefns))
    return result


# Load the prompts definitions from a file.
# The format is a
# The first line, blank lines and comment lines (start with #) are ignored.
# Remaining lines are a |-separated list of fields: Name|Type|Mode|Separator|Label|EnabledWhen|VisibleWhen|Mask|Custom.
# Typical Type values are string (the default), boolean, int and date.
# The result is a dictionary indexed by prompt name where the values
# are dictionaries with keys of PROMPT_XXX.
def loadPromptDefinitions(filename):
    result = {}
    f = open(filename)
    while 1:
        # Get the line, checking for EOF
        line = f.readline()
        if line == '':
            break

        # Build the result, ignoring comments and blank lines
        line =line.strip()
        sep = line.find("\t")
        if line == '' or line[0] == '#':
            continue
        defn = line.split("|")
        name = defn[0]
        type = 'string'
        mode = None
        mask = None
        separator = None
        label = None
        if len(defn) > 1:
            type = defn[1] or 'string'
        prompt = {PARAM_TYPE: type}
        if len(defn) > 2 and defn[2] != '':
            prompt[PARAM_MODE] = defn[2]
        if len(defn) > 3 and defn[3] != '':
            prompt[PARAM_SEPARATOR] = defn[3]
        if len(defn) > 4 and defn[4] != '':
            prompt[PARAM_LABEL] = defn[4]
        if len(defn) > 5 and defn[5] != '':
            prompt[PARAM_CHOICES] = defn[5]
        if len(defn) > 6 and defn[6] != '':
            prompt[PARAM_DEFAULT_VALUE] = defn[6]
        if len(defn) > 7 and defn[7] != '':
            prompt[PARAM_ENABLED_WHEN] = defn[7]
        if len(defn) > 8 and defn[8] != '':
            prompt[PARAM_VISIBLE_WHEN] = defn[8]
        if len(defn) > 9 and defn[9] != '':
            prompt[PARAM_MASK] = defn[9]
        if len(defn) > 10 and defn[10] != '':
            prompt[PARAM_WIDGET] = defn[10]
        if len(defn) > 11 and defn[11] != '':
            prompt[PARAM_CUSTOM] = defn[11]
        result[name] = prompt
    f.close()
    return result


# Load the prompts definitions via tables on the search list.
def loadPromptDefinitionsFromTable(searchDirs, tableId):
    files = findTableFiles(searchDirs, tableId)
    result = {}
    for f in files:
        result.update(loadPromptDefinitions(f))
    return result


def buildGroupsFromPrefixes(items, mappingTable, promptDefns=None, prompts=None):
    # Sort the items into their groups.
    # Items without a group go into the 'None' group.
    groups = {}
    order = []
    for i in items:
        group = None
        for row in mappingTable:
            p = row[0]
            if i[0:len(p)] == p:
                group = row[1]
                break
        if group == None and WARN_ON_NO_GROUP:
            print "warning: unable to put %s into a group" % i
        items = groups.get(group, [])
        if prompts:
            promptsForItem = prompts.get(i, [])
            # print "prompts for %s are %s" % (i, promptsForItem)
            paramsList = []
            for prompt in promptsForItem:
                paramDefn = promptDefns[prompt]
                paramDefn[PARAM_NAME] = prompt
                if paramDefn[PARAM_TYPE] == 'date':
                    paramDefn[PARAM_TYPE] = 'java.util.Date'
                    paramDefn[PARAM_KIND] = 'javaclass'
                paramsList.append(paramDefn)
            items.append((i, paramsList, {}))
        else:
            items.append(i)
        if items == []:
            order.append(group)
        groups[group] = items
    return (groups,order)


def buildGroupsFromComments(sourceLines, groupProcessor=None, groupProcessorParams=None,
                            itemProcessor=None, itemProcessorParams=None):
    '''
    Loads a dictionary from a list of lines and use the comments to intelligently group the items.
    The result is a tuple of (groups,order,groupInfo):

    * groups is a dictionary indexed by group name containing lists of items in each group
    * order is the order in which groups were found
    * groupInfo is optional interesting information about each group (the group comments by default).

    If a groupProcessor is given, that function is called for each group.
    The required signature is groupProcessor(id, comments, groupProcessorParams).
    The groupProcessor is expected to return a value which is stored for that group in the groupInfo dictionary returned.
    If an itemProcessor is given, that function is called for each item.
    The required signature is itemProcessor(id, value, comments, parsedComments, groupId, details, itemProcessorParams).
    The itemProcessor is expected to return the itemInfo stored for that item.
    This is typically just the itemId but it may also be the tuple expected by the saveGroupsXXX functions.
    groupProcessorParams and itemProcessorParams are dictionaries of additional parameters which a caller of
    this function may need to pass through to the respective processor functions.
    '''
    # Read the source and process it
    groups = {}
    order = []
    groupInfo = {}
    group = None
    (dict, comments) = ConfigurationFileIO.loadDictionaryFromLinesWithComments(sourceLines)
    for index in range(0, len(comments)):
        i = comments[index]
        id = i[0]
        text = i[1]
        if id == '':
            group = text
            # If a group of this name has not been created, add to it
            if not groups.has_key(group):
                groups[group] = []
                order.append(group)
            if len(i) > 2:
                groupComments = i[2]
            else:
                groupComments = ''
            if groupProcessor:
                groupInfo[group] = apply(groupProcessor, (group, groupComments, groupProcessorParams))
            else:
                groupInfo[group] = groupComments
        else:
            # If this is a normal entry, get the tags and part; if this is a tags, part or icon entry, skip it
            if id.endswith(".tags") or id.endswith(".privilege") or id.endswith(".icon"):
                continue
            else:
                tags = dict.get(id + ".tags")
                privilege = dict.get(id + ".privilege")
                if tags == None:
                    details = None
                else:
                    details = {DETAILS_TAGS: tags.split()}
                if privilege is not None:
                    if details is None:
                        details = {DETAILS_PRIVILEGE: privilege}
                    else:
                        details[DETAILS_PRIVILEGE] = privilege

            parsedText = i[2]
            if itemProcessor:
                itemInfo = apply(itemProcessor, (id, dict[id], text, parsedText, group, details, itemProcessorParams))
            elif details != None:
                itemInfo = (id, [], details)
            else:
                itemInfo = id
            items = groups.get(group)
            if items == None:
                items = []
                order.append(group)
            items = [ i for i in items if i is not itemInfo]
            items.append(itemInfo)
            groups[group] = items
    return (groups,order,groupInfo)


def buildGroupsFromCommentsForCatalog(searchPath, catalog, groupProcessor=None, groupProcessorParams=None,
                            itemProcessor=None, itemProcessorParams=None, lang=None):
    lines = loadCatalogLines(searchPath, catalog, lang)
    return buildGroupsFromComments(lines, groupProcessor, groupProcessorParams, itemProcessor, itemProcessorParams)


def buildGroupsForTools():
    groups = {}
    order = []
    keys = mstarapplib.findAllTargets()
    for key in keys:
        configForTool = mstarapplib.buildAppConfig({"filename":key, "args":""}, argumentsChecked=1, skipClean=1)
        group = None
        if configForTool.has_key("group"):
            group = configForTool["group"]
        else:
            # If an app has no group, don't show it as a tool
            continue
        params = getParametersForTool(key)
        details = {}
        if configForTool.has_key("job"):
            isJob = configForTool["job"]
        else:
            isJob = False
        if isJob:
            details[DETAILS_IMPL] = "{jobUrl=%s}" % configForTool["filename"]
        elif configForTool.has_key("form"):
            if configForTool.has_key("argnames"):
                details[DETAILS_IMPL] = configForTool["argnames"]
            #else:
                #print "WARNING: custom form defined for tool %s but argnames is missing - parameter order will be taken from the form" % key
        if configForTool.has_key("privilege"):
            details[DETAILS_PRIVILEGE] = configForTool["privilege"]
        if configForTool.has_key("instanceType"):
            details[DETAILS_INSTANCE_TYPE] = configForTool["instanceType"]
        if configForTool.has_key("tags"):
            tags = configForTool["tags"]
            details[DETAILS_TAGS] = tags.split(',')
            itemInfo = (key, params, details)
        elif params != None:
            itemInfo = (key, params, details)
        else:
            itemInfo = key

        items = groups.get(group, [])
        if items == []:
            order.append(group)
        items.append(itemInfo)
        groups[group] = items
    return (groups,order)


def getParametersForTool(tool):
    # If a custom form is defined, reference it by nesting it within a plain group
    if mstarapplib.applications.has_key(tool + ".form"):
        form = mstarapplib.applications[tool + ".form"]
        attrs = {PARAM_NAME:"form", PARAM_KIND:"group", PARAM_MODE:"plain", GROUP_SOURCE:form}
        return [attrs]

    # Get the list of arguments from argnames if it exists, otherwise argcheck
    if mstarapplib.applications.has_key(tool + ".argnames"):
        args = mstarapplib.applications[tool + ".argnames"].split()
    elif mstarapplib.applications.has_key(tool + ".argcheck"):
        argcheck = mstarapplib.applications[tool + ".argcheck"].strip()
        if len(argcheck) == 0:
            return None
        args = argcheck.split()
        for i in range(len(args)):
            arg = args[i]
            if arg[0] == '[' and arg[-1] == ']':
                args[i] = arg[1:-1]
                arg = args[i]
            if arg[0] == '<' and arg[-1] == '>':
                args[i] = arg[1:-1]
    else:
        args = ["..."]

    # Build the fields for editing each parameter and return as a list of dictionaries
    parameters = []
    for arg in args:
        if arg == "...":
            parameters.append(ANY_PARAMETERS_ATTRS)
        else:
            attrs = {PARAM_NAME: arg}
            for attr in LEGAL_PARAM_KEYS:
                key = "%s.arg%s_%s" % (tool,arg,attr)
                if mstarapplib.applications.has_key(key):
                    attrs[attr] = mstarapplib.applications[key]
            parameters.append(attrs)
    return parameters


# groups is a dictionary which contains the information needed to populate a set of ClassDefs,
# one group of ClassDefs per key. The value for each key is a list of the ClassDefs within that group.
# Each list element is either a string (implying no parameters) or a tuple where:
#
# * the first element is the name of ClassDef
# * the second element is an ordered list of parameters
# * the third element is a dictionary of additional details, e.g. filename relative to MSTAR_HOME
#
# Each parameter is a dictionary. Keys of interest are:
# * name
# * description
# * kind - type, javaclass, entity or group
# * type:
#   - for types: boolean|byte|char|double|float|int|long|short|string|hidden
#   - for javaclasses: java.util.Date, etc.
#   - for entities: Entity.Machine, etc.
# * choices - a map of legal values in one of the formats below:
#   - {a=atext,b="b text"} (see com.mincom.util.text.MapParser for details)
#   - listProvider:listName
# * mode,mask,separator,enabledWhen,visibleWhen,widget,option - the value for
#   the matching uidef attribute in the generated form
# * defaultValue - the default parameter value
#
# For legal keys into the details dictionary, see DETAILS_XXX.
#
def saveGroupsAsCatalog(groups, targetDir, sourceFile, typePlural, searchPath="??"):
    itemCount = 0
    groupNames = groups.keys()
    groupNames.sort()
    for name in groupNames:
        # Open the file, creating the containing directories if necessary
        pathname = "%s/%s.xml" % (targetDir,name)
        (dirname,filename) = os.path.split(pathname)
        if dirname != '' and not os.path.exists(dirname):
            os.makedirs(dirname)
        currentFile = open(pathname, 'w')

        # Write contents & close
        currentFile.write('<?xml version="1.0" encoding="us-ascii" standalone="no"?>' + "\n")
        currentFile.write('<!DOCTYPE classdefs SYSTEM "metadata.dtd">' + "\n")
        currentFile.write(('<!-- Definitions of %s in %s. DO NOT EDIT - generated from %s -->' % (typePlural, name, sourceFile)) + "\n")
        currentFile.write('<classdefs>' + "\n")

        # Dump the propertydefs and the propertygroups. Each propertygroup must have a level and we use
        # it to ensure nest correctly ...
        itemsAlreadyOutput = []
        for item in groups[name]:
            levels = []
            foundFirstTab = 0
            itemCount = itemCount + 1
            # If it's a tuple, the first element is the name and the second element is a list of parameters
            if type(item) == types.TupleType:
                itemName = item[0]
                if itemName in itemsAlreadyOutput:
                    print "WARNING: skipping %s - already output" % itemName
                    continue
                else:
                    itemsAlreadyOutput.append(itemName)
                itemParams = item[1]
                itemDetails = item[2]
                writeItemHeader(currentFile, itemName, itemDetails, typePlural)
                if itemParams != None:
                    for param in itemParams:
                        pKind = param.get(PARAM_KIND, 'type')
                        pName = param.get(PARAM_NAME, '')
                        pDesc = param.get(PARAM_DESC, '')
                        pLabel = param.get(PARAM_LABEL, None)
                        if pKind == "group":
                            pMode = param.get(PARAM_MODE, 'tab')
                            pLevel = param.get(PARAM_LEVEL, getDefaultLevelForGroup(pMode))
                            if (pMode == 'tab' or pMode == '') and not foundFirstTab:
                                # Need to output the tabset
                                foundFirstTab = 1
                                levels = movePropertyGroupLevel(currentFile, levels, pLevel - 1)
                                writePropertyGroupHeader(currentFile, levels, "__tabset__", "", "", {'mode':'tabset'})
                            levels = movePropertyGroupLevel(currentFile, levels, pLevel)
                            writePropertyGroupHeader(currentFile, levels, pName, pLabel, pDesc, param)
                        else:
                            pType = param.get(PARAM_TYPE, 'string')
                            if pType != "hidden":
                                pDefault = param.get(PARAM_DEFAULT_VALUE, None)
                                pUnitInfo = param.get(PARAM_UNITDEF, None)
                                pDefaultLang = param.get(PARAM_DEFAULT_VALUE_LANGUAGE, None)
                                pReadOnly = param.get(PARAM_READONLY, 0)
                                mutableLive = param.get(PARAM_MUTABLE_LIVE, 0)
                                pChoices = param.get(PARAM_CHOICES, '')
                                if param.has_key(DETAILS_TAGS):
                                    pTags = param[DETAILS_TAGS]
                                else:
                                    # Apply default tags, if any, for this catalog
                                    pTags = None
                                if (pChoices == 'platform.extensions'):
                                    pKind = 'javaclass'
                                    pType = 'com.mincom.util.deployment.ExtensionVersion'
                                typeInfo = formatTypeInfo(pKind, pType, pChoices)
                                uiDefInfo = formatUiDefInfo(param)
                                if len(levels) > 0:
                                    currentLevel = levels[-1]
                                else:
                                    currentLevel = 0
                                writeProperty(currentFile, currentLevel, pName, pLabel, pDesc, typeInfo, pUnitInfo, uiDefInfo, pTags, pReadOnly, pDefault, pDefaultLang,mutableLive)
            else:
                if item in itemsAlreadyOutput:
                    print "WARNING: skipping %s - already output" % item
                    continue
                else:
                    itemsAlreadyOutput.append(item)
                writeItemHeader(currentFile, item, {}, typePlural)

            # Unwind the propertygroups and close the classdef/classdefs tags
            levels.reverse()
            for level in levels:
                writePropertyGroupFooter(currentFile, level)
            currentFile.write("    </classdef>\n")
        currentFile.write('</classdefs>' + "\n")
        currentFile.close()
        print "%s created" % pathname
        if len(itemsAlreadyOutput) != len(groups[name]):
            print "duplicates detected on search path %s" % searchPath
    print "%d %s in %d groups" % (itemCount,typePlural,len(groupNames))


def writeItemHeader(currentFile, itemName, itemDetails, catalog):
    currentFile.write(('    <classdef name=%s >' % quoteattr(itemName)) + "\n")
    if itemDetails == None:
        itemDetails = {}
    if itemDetails.has_key(DETAILS_IMPL):
        currentFile.write(('        <%s name=%s />' % (DETAILS_IMPL,quoteattr(itemDetails[DETAILS_IMPL]))) + "\n")
    if itemDetails.has_key(DETAILS_PRIVILEGE):
        privilege = itemDetails[DETAILS_PRIVILEGE]
        currentFile.write(('        <privilege>%s</privilege>' % cgi.escape(privilege)) + "\n")
    if itemDetails.has_key(DETAILS_TAGS):
        tags = itemDetails[DETAILS_TAGS]
    else:
        # Apply default tags, if any, for this catalog
        tags = DEFAULT_TAGS.get(catalog, [])
    if itemDetails.has_key(DETAILS_INSTANCE_TYPE):
        instanceType = itemDetails[DETAILS_INSTANCE_TYPE]
        currentFile.write(('        <instanceType>%s</instanceType>' % cgi.escape(instanceType)) + "\n")
    for tag in tags:
        currentFile.write(('        <tag>%s</tag>' % cgi.escape(tag)) + "\n")


def quoteUiDefs(uiAttrs, onlyGroupAttributes):
    uidefs = []
    if uiAttrs.has_key(PARAM_MODE):
        uidefs.append('%s=%s' % ('mode',quoteattr(uiAttrs[PARAM_MODE])))
    if uiAttrs.has_key(PARAM_ENABLED_WHEN):
        uidefs.append('%s=%s' % ('enabledwhen',quoteattr(uiAttrs[PARAM_ENABLED_WHEN])))
    if uiAttrs.has_key(PARAM_VISIBLE_WHEN):
        uidefs.append('%s=%s' % ('visiblewhen',quoteattr(uiAttrs[PARAM_VISIBLE_WHEN])))
    if uiAttrs.has_key(PARAM_LAYOUT_INFO):
        uidefs.append('%s=%s' % ('layoutInfo',quoteattr(uiAttrs[PARAM_LAYOUT_INFO])))
    if uiAttrs.has_key(PARAM_DISPLAY_ORDER):
        uidefs.append('%s=%s' % ('displayorder',quoteattr(uiAttrs[PARAM_DISPLAY_ORDER])))
    if uiAttrs.has_key(PARAM_CUSTOM):
        uidefs.append('%s=%s' % ('custom',quoteattr(uiAttrs[PARAM_CUSTOM])))
    if onlyGroupAttributes:
        if uiAttrs.has_key(PARAM_LAYOUT):
            uidefs.append('%s=%s' % ('layout',quoteattr(_checkEnum(uiAttrs[PARAM_LAYOUT], LAYOUTS, 'layouts'))))
        if uiAttrs.has_key(GROUP_SOURCE):
            uidefs.append('%s=%s' % ('source',quoteattr(uiAttrs[GROUP_SOURCE])))
    else:
        if uiAttrs.has_key(PARAM_MASK):
            uidefs.append('%s=%s' % ('mask',quoteattr(uiAttrs[PARAM_MASK])))
        if uiAttrs.has_key(PARAM_WIDGET):
            uidefs.append('%s=%s' % ('widget',quoteattr(uiAttrs[PARAM_WIDGET])))
        if uiAttrs.has_key(PARAM_SEPARATOR):
            uidefs.append('%s=%s' % ('separator',quoteattr(uiAttrs[PARAM_SEPARATOR])))
        if uiAttrs.has_key(PARAM_OPTION):
            uidefs.append('%s=%s' % ('option',quoteattr(uiAttrs[PARAM_OPTION])))
        if uiAttrs.has_key(PARAM_PROCESS_ON_CHANGE):
            uidefs.append('%s=%s' % ('processOnChange',quoteattr(uiAttrs[PARAM_PROCESS_ON_CHANGE])))

    return uidefs


def formatTypeInfo(kind, type, choicesStr=None):
    # format the type section
    if choicesStr == None or choicesStr == '':
        choicesSection = ''
    else:
        choicesSection = formatChoices(choicesStr) + ' '
    if kind == 'type':
        typeInfo = '<type code=%s %s/>' % (quoteattr(type), choicesSection)
    elif kind == 'javaclass':
        typeInfo = '<javaclass name=%s %s/>' % (quoteattr(type), choicesSection)
    elif kind == 'entity':
        typeInfo = '<entity class=%s />' % quoteattr(type)
    else:
        print "WARNING: unknown parameter kind (%s)" % kind
        typeInfo = ''
    return typeInfo


def formatUiDefInfo(uiAttrs):
    if uiAttrs != None:
        uidefs = quoteUiDefs(uiAttrs, 0)
        if uidefs:
            return '<uidef %s />' % string.join(uidefs, ' ')
    return ''


def formatChoices(choicesStr):
    # if the string contains a double quote, surround it with single quotes, otherwise use double quotes
    return "choices=%s" % quoteattr(choicesStr)


def writeProperty(file, level, name, label, desc, typeInfo, unitInfo, uiDefInfo, tags, readonly=0, defaultValue=None, dvLanguage=None, mutableLive=0):
    levelPrefix = "    " * (level + 1)
    # If a label is not given, built a default one
    if label == None:
        labelParts = StringTools.mixedCaseSplit(name)
        for labelPart in labelParts:
            labelPart = string.capitalize(labelPart)
        label = string.join(labelParts, " ")
    if readonly == 0:
        if mutableLive == 0:
            file.write(levelPrefix + ('        <propertydef name=%s label=%s>' % (quoteattr(name), quoteattr(label)) + "\n"))
        else:
            file.write(levelPrefix + ('        <propertydef name=%s label=%s mutable-live=%s>' % (quoteattr(name), quoteattr(label), quoteattr(mutableLive)) + "\n"))
    else:
            file.write(levelPrefix + ('        <propertydef name=%s label=%s access=%s>' % (quoteattr(name), quoteattr(label),quoteattr(readonly))) + "\n")
    if tags != None:
        sTags = tags.split(',')
    	for tag in sTags:
        	file.write(('        <tag>%s</tag>' % cgi.escape(tag)) + "\n")
    file.write(levelPrefix + ('            <typedef>%s</typedef>' % typeInfo) + "\n")
    if uiDefInfo != '':
        file.write(levelPrefix + '            ' + uiDefInfo + "\n")
    # Note: empty string is a perfectly fine default value
    if defaultValue != None:
        if typeInfo.find("oolean") >= 0:
            dvAttrs = 'class="java.lang.Boolean"'
        elif typeInfo.find("ring") >= 0:
            dvAttrs = 'class="java.lang.String"'
        else:
            dvAttrs = ''
        if dvLanguage != None:
            dvAttrs = dvAttrs + (' type=%s' % quoteattr(_checkEnum(dvLanguage, DEFAULT_VALUE_LANGUAGES, 'defaultValueLanguages')))
        file.write(levelPrefix + ('            <defaultvalue %s>%s</defaultvalue>' % (dvAttrs,cgi.escape(defaultValue))) + "\n")
    if unitInfo != None and unitInfo != '':
        file.write(levelPrefix + ('            <unitdef type=%s/>' % quoteattr(unitInfo)) + "\n")
    if desc != None and desc != '':
        file.write(levelPrefix + ('            <description>%s</description>' % cgi.escape(desc)) + "\n")
    file.write(levelPrefix + "        </propertydef>\n")


def writePropertyGroupHeader(file, levels, name, label, desc, uiAttrs):
    level = levels[-1]
    levelPrefix = "    " * level
    # If a label is not given, built a default one
    if label == None:
        labelParts = StringTools.mixedCaseSplit(name)
        for labelPart in labelParts:
            labelPart = string.capitalize(labelPart)
        label = string.join(labelParts, " ")
    file.write(levelPrefix + ('        <propertygroup name=%s label=%s>' % (quoteattr(name), quoteattr(label))) + "\n")
    if desc != None and desc != '':
        file.write(levelPrefix + ('            <!-- %s -->' % cgi.escape(desc)) + "\n")

    # append the uidefs section, if any
    if uiAttrs != None:
        uidefs = quoteUiDefs(uiAttrs, 1)
        if uidefs:
            file.write(levelPrefix + '            <uigroupdef %s />' % string.join(uidefs, ' ') + "\n")


def writePropertyGroupFooter(file, level):
    levelPrefix = "    " * level
    file.write(levelPrefix + "        </propertygroup>\n")


def movePropertyGroupLevel(file, levels, newLevel):
    if levels == []:
        levels.append(newLevel)
        return levels

    lastLevel = levels[-1]
    if newLevel == lastLevel:
        writePropertyGroupFooter(file, lastLevel)
    elif newLevel > lastLevel:
        levels.append(newLevel)
    elif newLevel < lastLevel:
        writePropertyGroupFooter(file, lastLevel)
        levels.pop()
        while len(levels) > 0 and levels[-1] >= newLevel:
            lastLevel = levels.pop()
            writePropertyGroupFooter(file, lastLevel)
        levels.append(newLevel)
    return levels


def echoGroupProcessor(id, comments, params):
    """
    A test groupProcessor which simply echos parameters.
    """
    print "group: %s, comments: %s, params: %s" % (id, comments, params)


def echoItemProcessor(id, value, comments, parsedComments, groupId, details, params):
    """
    A test itemProcessor which simply echos parameters.
    """
    print "item: %s, value: %s, comments: %s, parsedComments, group: %s, params: %s" % (id, value, comments, parsedComments, groupId, params)
    return id


def buildPromptsForBusinessObjectsReport(itemId, promptDefns, prompts):
    paramsList = []
    if prompts:
        promptsForItem = prompts.get(itemId, [])
        newRegionNeeded = 0
        promptIndex = 0
        for prompt in promptsForItem:
            promptIndex += 1
            paramDefn = {}
            paramDefn.update(promptDefns[prompt])
            # If this parameter is displayed as an order include/exclude, make the label a region
            if paramDefn.get(PARAM_MODE) == 'ordered':
                regionLabel = {}
                regionLabel.update(REGION_TEMPLATE)
                regionLabel[PARAM_NAME] = " "  * promptIndex
                regionLabel[PARAM_LABEL] = paramDefn[PARAM_LABEL]
                paramsList.append(regionLabel)
                paramDefn[PARAM_LABEL] = ""
                newRegionNeeded = 1

            # If we just started a new region because of an 'ordered' parameter AND more parameters
            # follow, start another region
            elif newRegionNeeded:
                newRegionNeeded = 0
                regionLabel = {}
                regionLabel.update(REGION_TEMPLATE)
                regionLabel[PARAM_NAME] = "__region__" + `promptIndex`
                paramsList.append(regionLabel)

            # If this is the start of a date range, insert a period selector
            elif prompt == '1) Date Begin:':
                periodSelector = {}
                periodSelector.update(PERIOD_TEMPLATE)
                periodSelector[PARAM_NAME] = "__period__" + `promptIndex`
                paramsList.append(periodSelector)

            paramDefn[PARAM_NAME] = prompt
            if paramDefn[PARAM_TYPE] == 'date':
                paramDefn[PARAM_TYPE] = 'java.util.Date'
                paramDefn[PARAM_KIND] = 'javaclass'
            paramsList.append(paramDefn)

    # Add the special formatting stuff - output format, etc.
    regionLabel = {}
    regionLabel.update(FORMATTING_REGION)
    paramsList.append(regionLabel)
    paramDefn = {}
    paramDefn.update(OUTPUT_FMT_TEMPLATE)
    paramsList.append(paramDefn)

    return paramsList


def buildChoicesStrFromList(choices):
    "Build a choices string given an array of choices"
    return repr(choices)

################### begin special processing of AquilaReports to collect some stats ################

aqConvs = {}
aqFmts = {}

def _collectFieldsByValues(dict, flds, values, prefix):
    for i in range(0,len(flds)):
        fld = flds[i]
        if i >= len(values):
            continue
        value = values[i]
        if value == '':
            continue
        if dict.has_key(value):
            dict[value].append(prefix + fld)
        else:
            dict[value] = [prefix + fld]

def _aquilaSpecialProcessing(rpt):
    prefix = rpt.get(AquilaReports.TYPE_KEY) + ":"
    flds = AquilaReports.getColumns(rpt)
    convs = AquilaReports.getColumnConversions(rpt)
    _collectFieldsByValues(aqConvs, flds, convs, prefix)
    fmts = AquilaReports.getColumnFormats(rpt)
    _collectFieldsByValues(aqFmts, flds, fmts, prefix)

def _aquilaSpecialExit():
    print "Conversions:"
    for conv in aqConvs:
        data = aqConvs[conv]
        if len(data) > 5:
            print "%-20s%d" % (conv, len(data))
        else:
            print "%-20s%d\t%s" % (conv, len(data), data)
    print "\nFormats:"
    for fmt in aqFmts:
        data = aqFmts[fmt]
        if len(data) > 5:
            print "%-20s%d" % (fmt, len(data))
        else:
            print "%-20s%d\t%s" % (fmt, len(data), data)

################### end special processing of AquilaReports to collect some stats ################


def buildPromptsForAquilaReport(rpt, promptDefns, sepBeforeSpecialParameters=0):
    paramsList = []

    # All AQReports have implicit parameters: period, start time, end time
    periodSelector = {}
    periodSelector.update(AQRPT_PERIOD_TEMPLATE)
    paramsList.append(periodSelector)
    paramDefn = {}
    paramDefn.update(AQRPT_STARTTIME_TEMPLATE)
    paramsList.append(paramDefn)
    paramDefn = {}
    paramDefn.update(AQRPT_ENDTIME_TEMPLATE)
    paramsList.append(paramDefn)

    # Add the report specific parameters (after a separator as appropriate)
    params = AquilaReports.getParameters(rpt)
    if params != None:
        if sepBeforeSpecialParameters:
            regionLabel = {}
            regionLabel.update(REGION_TEMPLATE)
            regionLabel[PARAM_NAME] = " "
            paramsList.append(regionLabel)
        for param in params:
            paramDefn = {}
            specialParamSettings = promptDefns.get(param)
            if specialParamSettings != None:
                paramDefn.update(specialParamSettings)
            else:
                paramDefn.update(AQRPT_PARAM_TEMPLATE)
                paramDefn[PARAM_NAME] = param
            paramsList.append(paramDefn)

    # add the Data source region
    regionLabel = {}
    regionLabel.update(DATASOURCE_REGION)
    paramsList.append(regionLabel)
    paramDefn = {}
    paramDefn.update(DATASOURCE_TEMPLATE)
    paramsList.append(paramDefn)

    # Add the special formatting stuff - template (orientation), group by, etc.
    regionLabel = {}
    regionLabel.update(FORMATTING_REGION)
    paramsList.append(regionLabel)
    paramDefn = {}
    paramDefn.update(AQRPT_TEMPLATE_TEMPLATE)
    if rpt.get(AquilaReports.TEMPLATE_KEY) == AquilaReports.LANDSCAPE_TEMPLATE:
        paramDefn[PARAM_DEFAULT_VALUE] = "landscape"
    paramsList.append(paramDefn)

    # Columns we can group by are those at the front of the list which look like string.ascii_letters
    # Ideally, we'd work this out from the formatting and conversion info but that seems more trouble
    # than it worth (currently) given that drills are identified by number, not string, etc.
    columns = AquilaReports.getColumns(rpt)
    descs = AquilaReports.getColumnDescriptions(rpt)
    groupBys = []
    for i in range(0, len(columns)):
        column = columns[i]
        if column in ['DRILLNUMBER', 'CONSUMABLE', 'CONSUMABLE_TYPE', 'ACTUAL_NAME', 'OPERATOR', 'ACTUAL_BLAST']:
            if descs is None:
                columnDesc = column
            else:
                columnDesc = descs[i] or column
            # Manual formatting of list items is required because
            # building a dict of name-value pairs & calling repr loses the ordering of fields
            groupBys.append('"' + column + '": "' + columnDesc + '"')
    if groupBys != []:
        paramDefn = {}
        paramDefn.update(AQRPT_GROUPBY_TEMPLATE)
        paramDefn[PARAM_CHOICES] = '{"": "<None>", ' + string.join(groupBys, ", ") + "}"
        paramsList.append(paramDefn)

    _aquilaSpecialProcessing(rpt)
    return paramsList


def buildPromptsForJasperReport(report, promptDefns):
    paramsList = []
    params = JasperReports.getParameters(report)
    for param in params:
        if param.get("isForPrompting", "true") == "false":
            continue
        paramDefn = {}
        paramDefn[PARAM_NAME] = param['name']
        if param.has_key('parameterDescription'):
            paramDefn[PARAM_LABEL] = param['parameterDescription']
        paramDefn[PARAM_TYPE] = param['class']  # Note: May need to convert class names down the track
        paramDefn[PARAM_KIND] = 'javaclass'
        if param.has_key('defaultValueExpression'):
            paramDefn[PARAM_DEFAULT_VALUE] = param['defaultValueExpression']
        paramsList.append(paramDefn)

    # add the Data source region
    regionLabel = {}
    regionLabel.update(DATASOURCE_REGION)
    paramsList.append(regionLabel)
    paramDefn = {}
    paramDefn.update(DATASOURCE_TEMPLATE)
    paramsList.append(paramDefn)

    return paramsList


def buildReportPromptsItemProcessor(itemId, itemValue, itemComments, parsedComments, groupId, details, params):
    """
    An itemProcessor which builds a form for the parameters of a report.
    The supported parameters (all required) are:
    * promptDefns - dictionary of prompt definitions
    * prompts - dictionary of prompts per report
    * searchPath  - the search path for MineStar components
    * aprptDir - directory (relative to searchPath) where aqrpt files are
    * JasperReportDir - directory (relative to searchPath) where JasperReport files are
    """

    # Find the report type and generate the itemId & parameters accordingly
    promptDefns = params['promptDefns']
    ufsRoot = ufs.getRoot(params['searchPath'])
    if itemValue.endswith(".rep"):
        itemId = itemValue[0:-4]
        paramsList = buildPromptsForBusinessObjectsReport(itemId, promptDefns, params['prompts'])
    elif itemValue.endswith(".aqrpt"):
        # Use the last AQReport found on the search path
        itemValue = params['aqrptDir'] + '/' + itemValue
        fullpath = ufsRoot.get(itemValue).getPhysicalFile()
        rpt = AquilaReports.load(fullpath)
        itemId = rpt[AquilaReports.TYPE_KEY]
        paramsList = buildPromptsForAquilaReport(rpt, promptDefns)
    else:
        # Use the last JasperReport found on the search path
        itemValue = params['JasperReportDir'] + '/' + itemValue
        ufsFile = ufsRoot.get(itemValue)
        if ufsFile is not None:
            fullpath = ufsFile.getPhysicalFile()
            rpt = JasperReports.load(fullpath)
            itemId = JasperReports.getName(rpt)
            paramsList = buildPromptsForJasperReport(rpt, promptDefns)
        else:
            raise ("Jasper Report %s not found" % itemValue)

    # Build the dictionary of additional details and return
    if details == None:
        itemDetails = {DETAILS_IMPL: itemValue}
    else:
        itemDetails = details
        itemDetails[DETAILS_IMPL] = itemValue
    return (itemId,paramsList,itemDetails)

def getDefaultLevelForGroup(mode):
    if DEFAULT_GROUP_LEVELS.has_key(mode):
        return DEFAULT_GROUP_LEVELS[mode]
    else:
        return DEFAULT_GROUP_LEVELS['tab']

def __loadLinesFromJars(itemValue):
    ufsPath = mstarpaths.interpretVar("UFS_PATH")
    ufsRoot = ufs.getRoot(ufsPath)
    className = itemValue.replace('.', '/') + ".properties"
    (bcpJars, jars, classPathDirs, classPathJars) = mstarpaths.buildClassPaths(ufsRoot, 0, None, None)
    for jar in jars:
        if not jar.lower().endswith(".jar"):
            continue
        zf = zipfile.ZipFile(jar, "r")
        if className in zf.namelist():
            bytes = zf.read(className)
            lines = bytes.split("\n")
            lines = [ minestar.stripEol(line) for line in lines ]
            return lines
    raise Exception(className + " not found")

def buildOptionsFormItemProcessor(itemId, itemValue, itemComments, parsedComments, groupId, details, params):
    """
    An itemProcessor which builds a form for the option from the contents of the options file.
    The supported parameters are:
    * searchPath  - the search path for MineStar components
    """
    # filenames of the form x.y.z are shorthands for /res/x/y/z.properties
    itemValue = itemValue.strip()
    if itemValue[0] == '/':
        sourceFilename = itemValue
    else:
        sourceFilename = '/res/' + itemValue.replace('.', '/') + '.properties'

    # Read the form definition from the options file
    ufsRoot = ufs.getRoot(params['searchPath'])
    ufsFile = ufsRoot.get(sourceFilename)
    try:
        if ufsFile is None:
            lines = __loadLinesFromJars(itemValue)
        else:
            lines = ufsFile.getTextLines()
    except:
        print "ERROR: unable to read options file: %s" % sourceFilename
        lines = []
    (groups,order,groupInfo) = buildGroupsFromComments(lines, itemProcessor=buildFieldItemProcessor)

    # Convert the group data into a set of parameters
    fieldList = []
    for group in order:
        if group != None:
            field = {PARAM_NAME: group, PARAM_KIND: "group"}
            info = groupInfo.get(group)
            if info != None and info != '':
                groupParams = ConfigurationFileIO.parseComment(info, PARAM_DESC, LEGAL_PARAM_KEYS)
                field.update(groupParams)
            fieldList.append(field)
        for item in groups[group]:
            if type(item) == types.TupleType:
                #name = item[0]
                field = item[1]
                #field[PARAM_NAME] = item[0]
            else:
                field = {PARAM_NAME: item}
            fieldList.append(field)

    # Build the dictionary of additional details and return
    if details == None:
        itemDetails = {DETAILS_IMPL: itemValue}
    else:
        itemDetails = details
        itemDetails[DETAILS_IMPL] = itemValue
    return (itemId,fieldList,itemDetails)


def buildFieldItemProcessor(id, value, comments, parsedComments, groupId, details, params):
    field = parsedComments
    if parsedComments is None:
        field = {PARAM_NAME:id}
    else:
        field[PARAM_NAME] = id

    # If a label is not given, built a default one
    if not field.has_key(PARAM_LABEL):
        labelParts = StringTools.mixedCaseSplit(id)
        labelParts[0] = string.capitalize(labelParts[0])
        field[PARAM_LABEL] = string.join(labelParts, " ")

    # Guess the type from the value if none provided
    if not field.has_key(PARAM_TYPE):
        if string.lower(value) in AUTO_BOOLEAN_VALUES:
            typeCode = 'boolean'
        else:
            try:
                dummy = int(value)
                typeCode = 'int'
            except:
                try:
                    dummy = float(value)
                    typeCode = 'float'
                except:
                    typeCode = 'string'
        field[PARAM_TYPE] = typeCode
    return (id,field,details)


def buildHelpItemProcessor(id, value, comments, parsedComments, groupId, details, params):
    # Build the dictionary of additional details and return
    if details == None:
        itemDetails = {DETAILS_IMPL: value}
    else:
        itemDetails = details
        itemDetails[DETAILS_IMPL] = value
    return (id,[],itemDetails)


def buildPermissionsItemProcessor(id, value, comments, parsedComments, groupId, details, params):
    # Build the dictionary of additional details and return
    if details == None:
        itemDetails = {DETAILS_IMPL: value}
    else:
        itemDetails = details
        itemDetails[DETAILS_IMPL] = value
    return (id,[],itemDetails)


def buildDisplaysItemProcessor(id, value, comments, parsedComments, groupId, details, params):
    # Build the dictionary of additional details and return
    if details == None:
        itemDetails = {DETAILS_IMPL: value}
    else:
        itemDetails = details
        itemDetails[DETAILS_IMPL] = value
    return (id,[],itemDetails)


def __dumpReportsAsProperties(groups):
    groupNames = groups.keys()
    groupNames.sort()
    resultDict = {}
    resultComments = []
    for name in groupNames:
        resultComments.append((None, name))
        itemCount = 0
        for item in groups[name]:
            itemCount = itemCount + 1
            # If it's a tuple, the first element is the name and the second element is a list of parameters
            if type(item) == types.TupleType:
                itemName = item[0]
            else:
                itemName = item
            codeEnd = itemName.find("-")
            if codeEnd > 0:
                itemCode = itemName[0:codeEnd].strip()
            else:
                itemCode = itemName
            itemImpl = itemName + ".rep"
            if resultDict.has_key(itemCode):
                itemCode = "%s_%d" % (itemCode,itemCount)
            resultDict[itemCode] = itemImpl
            resultComments.append((itemCode,''))
    ConfigurationFileIO.saveDictionaryToFile(resultDict, "xx.properties", comments=resultComments)

def buildVersions():
    """
        Collect a list of versions of zipped extensions by looking at the ext directory.
    """
    import mstarext, mstaroverrides
    zexts = mstarext.findZippedExtensions(mstarpaths.config)
    (overrides, overridesFile) = mstaroverrides.loadOverrides()
    fileKey = "/catalogs/ChoiceLists.properties"
    if overrides.get(fileKey) is None:
        overrides[fileKey] = {}
    dict = overrides[fileKey]
    for (base, exts) in zexts.items():
        versions = exts.keys()[:]
        versions.sort(lambda a, b: cmp(float(a), float(b)))
        versions = ['"%s" : "%s"' % (x, x) for x in versions ] + [ '"MostRecent": "Most Recent", "Stable": "Stable"' ]
        key = "%s.versions" % base
        value = "{%s}" % (", ".join(versions),)
        dict[key] = value
    mstaroverrides.saveOverrides(overrides)

def buildCatalogs(catalogs, knownCatalogNames, searchPath, targetArea, systemName=None):
    if searchPath == None or len(searchPath) == 0:
        print "ERROR: unable to build catalogs as directory search path is empty"
        return

    searchDirs = searchPath.split(os.pathsep)
    for catalog in catalogs:
        # Check the name is legal
        if not(catalog in knownCatalogNames):
            print "error: unknown catalog type '%s'" % catalog
            continue

        # Parse the source information into groups
        print "\nmaking catalog %s ..." % catalog
        if catalog == 'Reports':
            promptDefns = loadPromptDefinitionsFromTable(searchDirs, REPORT_PROMPT_DEFINITIONS_TABLE)
            promptLists = loadPromptsForReportsFromTable(searchDirs, REPORT_PROMPT_LISTS_TABLE, promptDefns)
            ipParams = {'promptDefns':promptDefns, 'prompts':promptLists,
                        'searchPath':searchPath,
                        'JasperReportDir': '/reports', 'aqrptDir': '/reports'}
            (groups,order,groupInfo) = buildGroupsFromCommentsForCatalog(searchPath, catalog,
                                             itemProcessor=buildReportPromptsItemProcessor,
                                             itemProcessorParams=ipParams)
        elif catalog == 'Displays':
            (groups,order,groupInfo) = buildGroupsFromCommentsForCatalog(searchPath, catalog,
                                             itemProcessor=buildDisplaysItemProcessor)
        elif catalog == 'Documents':
            # Rebuild the documents web page while we're at it
            languages = findAllLanguages()
            for lang in languages:
                (groups,order,groupInfo) = buildGroupsFromCommentsForCatalog(searchPath, catalog, itemProcessor=buildHelpItemProcessor, lang=lang)
        elif catalog in ['Pages', 'Collections', 'DataSets']:
            (groups,order,groupInfo) = buildGroupsFromCommentsForCatalog(searchPath, catalog)
        elif catalog == 'Permissions':
            (groups,order,groupInfo) = buildGroupsFromCommentsForCatalog(searchPath, catalog,
                                            itemProcessor=buildPermissionsItemProcessor)
        elif catalog == 'Tools':
            (groups,order) = buildGroupsForTools()
        elif catalog == 'OptionSets' or catalog == 'Forms':
            ipParams = {'searchPath':searchPath}
            (groups,order,groupInfo) = buildGroupsFromCommentsForCatalog(searchPath, catalog,
                                             itemProcessor=buildOptionsFormItemProcessor,
                                             itemProcessorParams=ipParams)

        # Dump the groups into files
        targetDirectory = mstarpaths.interpretPath("%s/xml/catalogs/%s" % (targetArea,catalog))
        try:
            minestar.rmdir(targetDirectory)
        except:
            print "WARNING: failed to delete catalog directory %s - old entries may still appear" % targetDirectory
        sourceBasename = getBasenameForCatalog(catalog)
        saveGroupsAsCatalog(groups, targetDirectory, sourceBasename, catalog, searchPath)

def findAllLanguages():
    # we always have English
    langs = [ "en" ]
    import ufs, mstarpaths
    ufsRoot = ufs.getRoot(mstarpaths.interpretFormat("{UFS_PATH}"))
    phbkDir = ufsRoot.get("phrasebooks")
    if phbkDir is not None:
        for f in phbkDir.listFiles():
            if f.getName().startswith("all-Resources"):
                locale = f.getName()[14:]
                locale = locale[:locale.find('.')]
                if locale not in langs:
                    langs.append(locale)
    # add the language they really want to use
    lang = mstarpaths.interpretVar("_LANGUAGE")
    if lang not in langs:
        langs.append(lang)
    return langs

## Main program ##

if __name__ == "__main__":
    # Check usage
    allCatalogs = DEFAULT_TAGS.keys()
    allCatalogs.sort()
    args = sys.argv[1:]
    if len(args) == 0:
        print "usage:"
        print "  makeCatalogs                  - show list of catalogs"
        print "  makeCatalogs [options] all    - make all catalogs"
        print "  makeCatalogs [options] x ...  - make the specified catalogs"
        print "The -b option generates catalogs in the base area (MSTAR_HOME),"
        print "otherwise the system area (MSTAR_CONFIG) is used."
        print "Catalog names are %s." % string.join(allCatalogs, ', ')
        sys.exit(0)

    # Get the list of catalogs to make from the command line
    targetArea = "{MSTAR_CONFIG}"
    if args[0] == "-b":
        targetArea = "{MSTAR_HOME}"
        args = args[1:]
    if args[0] == 'all':
        catalogs = allCatalogs
    else:
        catalogs = args
    mstarpaths.loadMineStarConfig()
    buildCatalogs(catalogs, allCatalogs, mstarpaths.interpretVar("UFS_PATH"), targetArea)

    # Dump statistics
    #_aquilaSpecialExit()
