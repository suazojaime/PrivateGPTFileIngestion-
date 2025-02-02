import difflib  # if using Zope 2.3.x, need to port this back to Python 1.52
import dircache
import os
import re
import string
import sys
import time
from cgi import escape

import minestar
import mstardebug
from lineOps import getLinesFromFile as loadLinesFromFile, continueLine

# NOTE: This would ideally be several modules but I'm not sure how to make
# Zope extension modules find each other. :-(

# Some constants used for building and accessing parameter definitions
PARAM_NAME = 'name'
PARAM_DESC = 'description'
PARAM_KIND = 'kind'
PARAM_TYPE = 'type'
PARAM_CHOICES = 'choices'
PARAM_MODE = 'mode'
PARAM_MASK = 'mask'
PARAM_LABEL = 'label'
PARAM_ENABLED_WHEN = 'enabledWhen'
PARAM_VISIBLE_WHEN = 'visibleWhen'
PARAM_READONLY = 'readonly'
PARAM_COMMENT = 'comment'
PARAM_DEFAULT_VALUE = 'defaultValue'
PARAM_OPTION = "option"
PARAM_SEPARATOR = "separator"
PARAM_WIDGET = "widget"
PARAM_UNITDEF = "unitdef"
PARAM_CUSTOM = "custom"
PARAM_MUTABLE_LIVE = "mutable-live"
PARAM_LEVEL = "level"
PARAM_LAYOUT = "layout"
PARAM_TAGS = "tags"
PARAM_LAYOUT_INFO = "layoutInfo"
PARAM_PROCESS_ON_CHANGE = "processOnChange"
PARAM_DEFAULT_VALUE_LANGUAGE = "defaultValueLanguage"
PARAM_DISPLAY_ORDER = "displayOrder"
PARAM_SECURE = "secure"

# We don't support all of values above because some are implicit
LEGAL_PARAM_KEYS = [PARAM_TYPE, PARAM_CHOICES, PARAM_MODE, PARAM_MASK, PARAM_LABEL, PARAM_ENABLED_WHEN, PARAM_READONLY,
                    PARAM_DESC, PARAM_COMMENT, PARAM_DEFAULT_VALUE, PARAM_OPTION, PARAM_VISIBLE_WHEN, PARAM_SEPARATOR,
                    PARAM_WIDGET, PARAM_UNITDEF, PARAM_CUSTOM, PARAM_MUTABLE_LIVE, PARAM_LEVEL, PARAM_KIND, PARAM_LAYOUT, PARAM_TAGS, PARAM_LAYOUT_INFO,
                    PARAM_PROCESS_ON_CHANGE, PARAM_DEFAULT_VALUE_LANGUAGE, PARAM_DISPLAY_ORDER, PARAM_SECURE]
DEFAULT_PARAM = PARAM_DESC

DEFAULT_VALUE_LANGUAGES = ['literal', 'python', 'java']
LAYOUTS = ['vertical', 'horizontal', 'custom']
PROCESS_ON_CHANGES = ['false', 'true']


## Tracing ##

def debug(msg):
    if mstardebug.debug:
        print msg


def debug_trace(level, msg):
    """output developer trace - hack this while debugging"""

    SHOW_LEVELS_BELOW = 0               # set to 0 to switch trace off
    FNAME = 'c:/tmp/igc.trace'          # destination filename

    if level < SHOW_LEVELS_BELOW:
        try:
            with open(FNAME, 'a') as f:
                f.write(msg + "\n")
                #print '>>> %s' % msg
        except Exception:
            pass

## Dictionary IO routines ##

strictKeyValueSeparators = "=:"
whiteSpaceChars = " \t\r\n\f"
keyValueSeparators = strictKeyValueSeparators + whiteSpaceChars

loadTranslation = {'t': '\t', 'r': '\r', 'n': '\n', 'f': '\f'}

# TODO replace with lineOps.cleanLine()
def cleanLine(line):
    """
    Remove new lines from end of line, and white space from the beginning.
    """
    import lineOps
    return lineOps.cleanLine(line)

def loadConvert(s):
    """
    Interpret escape characters in a key or value.
    Pass thru unicode escapes as they are.
    Process backslash escapes.
    """
    result = ""
    i = 0
    lens = len(s)
    while i < lens:
        ch = s[i]
        i = i + 1
        if ch == '\\':
            if i == lens:
                break
            ch = s[i]
            i = i + 1
            if ch == 'u':
                result = result + "\\u"
                j = 0
                while j < 4:
                    if i == lens:
                        break
                    result = result + s[i]
                    i = i + 1
                if i == lens:
                    break
            else:
                if loadTranslation.has_key(ch):
                    ch = loadTranslation[ch]
                result = result + ch
        else:
            result = result + ch
    return result

def loadDictionaryFromFile(filename, namePrefix=None, javaEscapes=1):
    '''
    load a dictionary from a file exactly as for a Java properties file.
    '''
    return loadDictionaryFromFileWithComments(filename, namePrefix, javaEscapes)[0]

def loadDictionaryFromFileWithComments(filename, namePrefix=None, javaEscapes=1):
    '''
    load a dictionary from a file exactly as for a Java properties file.
    The result is a tuple containing 2 elements: the dictionary and a list of comments.
    See saveDictionaryToFile() for details on how the comments list is structured.
    '''
    # read in the lines
    lines = loadLinesFromFile(filename)
    return loadDictionaryFromLinesWithComments(lines, namePrefix, javaEscapes)

def loadDictionaryFromLinesWithComments(lines, namePrefix=None, javaEscapes=1):
    '''
    load a dictionary from a list of lines exactly as for a Java properties file.
    The result is a tuple containing 2 elements: the dictionary and a list of comments.
    See saveDictionaryToFile() for details on how the comments list is structured.
    '''
    # clean new lines and gunk
    # Note: This code is really ugly so it is bug-compatible with the JDK.
    # However we keep #-style comments (but still throw away !-style ones) so
    # that we can match them with keys later on.
    goodLines = []
    index = 0
    while index < len(lines):
        line = cleanLine(lines[index])
        index = index + 1
        if len(line) == 0:
            continue
        firstChar = line[0]
        if firstChar == '!':
            continue
        while continueLine(line):
            if index == len(lines):
                break
            nextline = cleanLine(lines[index])
            index = index + 1
            # drop continuation character
            line = line[:-1] + nextline
        goodLines.append(line)

    # parse the lines
    lines = goodLines
    result = {}
    comments = []
    groupHeadingRE = re.compile(r'^##\s*(.+)\s*##$')
    lastComment = None
    lastGroupComment = None
    for line in lines:
        groupHeading = groupHeadingRE.match(line)
        if groupHeading:
            if lastGroupComment is not None:
                # For groups, the key is empty and the 'comment' is the heading so
                # group comments in the 3rd slot of the tuple
                if len(comments) > 0:
                    comments[-1] = comments[-1] + (lastGroupComment,)
            comments.append(('', string.strip(groupHeading.group(1))))
            lastComment = None
            lastGroupComment = None
            continue
        elif len(line) >= 2 and line[0:2] == '##':
            if lastGroupComment is None:
                lastGroupComment = string.strip(line[2:])
            else:
                lastGroupComment = lastGroupComment + "\n" + string.strip(line[2:])
            continue
        elif line[0] == '#':
            if lastComment is None:
                lastComment = string.strip(line[1:])
            else:
                lastComment = lastComment + "\n" + string.strip(line[1:])
            continue

        sepIndex = 0
        while sepIndex < len(line):
            ch = line[sepIndex]
            if ch == '\\':
                sepIndex = sepIndex + 1
            elif ch in keyValueSeparators:
                break
            sepIndex = sepIndex + 1
        key = line[:sepIndex]
        if namePrefix:
            key = key[len(namePrefix):]
        line = cleanLine(line[sepIndex:])
        if len(line) > 0 and line[0] in strictKeyValueSeparators:
            line = line[1:]
        line = cleanLine(line)
        if javaEscapes:
            actualKey = loadConvert(key)
            result[actualKey] = loadConvert(line)
        else:
            actualKey = key
            result[actualKey] = line
        if lastGroupComment is not None:
            # For groups, the key is empty and the 'comment' is the heading so
            # group comments in the 3rd slot of the tuple
            if len(comments) > 0:
                comments[-1] = comments[-1] + (lastGroupComment,)
            lastGroupComment = None
        if lastComment is None:
            parsedComment = None
        else:
            parsedComment = parseComment(lastComment, PARAM_DESC, LEGAL_PARAM_KEYS)
        comments.append((actualKey,lastComment,parsedComment))
        lastComment = None

    # Handle trailing group comments
    if lastGroupComment is not None:
        # For groups, the key is empty and the 'comment' is the heading so
        # group comments in the 3rd slot of the tuple
        if len(comments) > 0:
            comments[-1] = comments[-1] + (lastGroupComment,)

    return (result,comments)

saveTranslation = { '\\': '\\\\', '\t': '\\t', '\n': '\\n', '\r': '\\r', '\f': '\\f' }
hex = "0123456789abcdef"


def parseComment(s, defaultKey, legalKeys):
    """
    convert a set of comment lines to a set of name-value pairs.
    Lines of the form "@xxx yyyy" get parsed into entries.
    Any text before the first of these gets stored against the defaultKey.
    A warning is output if xxx is not found in legalKeys.
    """
    result = {}
    if s is None:
        return result
    defaultValue = ''
    if type(s) != type(""):
        raise "Not a string: %s" % `s`
    lines = s.split("\n")
    for line in lines:
        if len(line) == 0:
            continue
        if line[0] == '@':
            restOfLine = line[1:]
            if restOfLine.find(' ') >= 0:
                (key,value) = restOfLine.split(' ', 1)
                value = value.strip()
            else:
                key = restOfLine
                value = ''
            if not(key in legalKeys):
                print "warning: unexpected key (%s) found" % key
            result[key] = value
        else:
            if len(defaultValue) == 0:
                defaultValue = line
            else:
                defaultValue = defaultValue + ' ' + line
    result[defaultKey] = defaultValue
    return result

HEX_CHARACTERS = "abcdefABCDEF0123456789"

def saveConvert(s, escapeSpace):
    result = ""
    i = 0
    lens = len(s)
    while i < lens:
        ch = s[i]
        i = i + 1
        if ch == '\\' and i + 4 < lens and s[i] == 'u' and s[i+1] in HEX_CHARACTERS and s[i+2] in HEX_CHARACTERS and s[i+3] in HEX_CHARACTERS and s[i+4] in HEX_CHARACTERS:
            result = result + '\\'
        elif saveTranslation.has_key(ch):
            result = result + saveTranslation[ch]
        elif ch == ' ' and escapeSpace:
            result = result + "\ "
        elif ord(ch) < 32 or ord(ch) > 127:
            result = result + "\\u"
            v = ord(ch)
            for shift in [12, 8, 4, 0]:
                result = result + hex[(v >> shift) & 15]
        else:
            result = result + ch
    return result


def saveDictionaryToFile(dict, filename, keepOriginal=True, namePrefix='', sep=' = ', comments=[]):
    '''
    save a dictionary to a file as name=value pairs, one per line,
    prepending the name prefix to each name.
    - comments - an optional list of name,text tuples giving the order in which to
      output pairs and the comment text to output immediately before each one.
      If a list entry has no name and only text, that text is output in 'group header'
      style (## blah blah blah ##) with a blank line or two immediately before it as
      appropriate. Names not found in the list are output after those that are.

    Returns 1 if everything succeeded
    '''
    writer = DictionaryWriter(dictionary=dict, keepOriginal=keepOriginal, namePrefix=namePrefix,
                              separator=sep, comments=comments)
    writer.write(filename)


def getTimeZoneAwareTimeStamp(config=None):
    """Get a timezone-aware timestamp. This means calling out to Java as python does not handle timezones."""
    def getTimeZone(config):
        if config is None:
            import mstarpaths
            config = mstarpaths.getConfig()
        timezone = ""
        if config is not None and "_TIMEZONE" in config:
            timezone = config['_TIMEZONE']
        return timezone
    # Call out to java with current timezone.
    command = ["minestar.platform.bootstrap.DateStringUtil", getTimeZone(config)]
    output = minestar.mstarrunEval(command)
    debug("DateStringUtil output: %s" % output)
    # Extract time-zone aware date from output, if present.
    if "JavaTimeZoneAwareDate" in output:
        parsedout = output.split("JavaTimeZoneAwareDate=")
        if len(parsedout) > 1:
            return parsedout[1]
    # Output did not contain timezone-aware date. No timestamp available.
    return None


class DictionaryWriter:

    def __init__(self, dictionary, keepOriginal=True, namePrefix='', separator=' = ', comments=[], timestamper=None):
        self.dictionary = dictionary
        self.keepOriginal = keepOriginal
        self.namePrefix = namePrefix
        self.separator = separator
        self.comments = comments
        self.timestamper = timestamper or getTimeZoneAwareTimeStamp

    def write(self, filename):
        # Get the timestamp if writing to an overrides file. Do this before opening
        # (and truncating) the config file, as calculating the timestamp may require
        # reading from the the same config file.
        timestamp = None
        if "overrides" in filename:
            timestamp = self.timestamper()
        # Back up the file before writing new file.
        backupFile(filename, self.keepOriginal)
        # Write the dictionary (and optional timestamp) to the new file.
        # TODO safer to write to a temporary file, then rename, in case of errors.
        with open(filename, 'wt') as f:
            keys = self.dictionary.keys()
            self.writeTimeStamp(timestamp, f)
            self.writeComments(keys, f)
            self.writeProperties(keys, f)

    def writeTimeStamp(self, timestamp, f):
        if timestamp is not None:
            f.write("#%s\n" % timestamp)

    def writeComments(self, keys, f):
        # Output the comments and pairs in the order requested
        for comment in self.comments:
            self.writeComment(keys, comment, f)

    def writeComment(self, keys, comment, f):
        (key, text) = (comment[0], comment[1])
        if key:
            try:
                keys.remove(key)
                value = self.dictionary[key]
            except ValueError:
                value = None
            # Comment out keys where the value is None
            prefix = '!' if value is None else ""
            if text:
                commentText = self.text2comment(text, prefix + "# ")
                f.write("\n%s\n" % commentText)
            f.write("%s%s%s%s\n" % (prefix,
                                    saveConvert(self.namePrefix + key, escapeSpace=True),
                                    self.separator,
                                    saveConvert(str(value), escapeSpace=False)))
        elif text:
            f.write("\n\n## %s ##\n\n" % text)
            if len(comment) > 2:
                f.write("## %s\n\n" % comment[2])

    def text2comment(self, text, prefixPerLine):
        if string.find(text, '\n') == -1:
            return prefixPerLine + text
        else:
            lineRE = re.compile(r'^', re.MULTILINE)
            return lineRE.sub(prefixPerLine, text)

    def writeProperties(self, keys, f):
        # Now output the remainder in sorted order
        keys.sort()
        for key in keys:
            f.write("%s%s%s\n" % (saveConvert(self.namePrefix + key, escapeSpace=True),
                                  self.separator,
                                  saveConvert(str(self.dictionary[key]), escapeSpace=False)))

def reportGroupCounts(files, usePrefixOnly=1):
    '''
    report the group counts in a set of dictionary files.
    The result is a tuple with 2 entries:
    1. a dictionary of all-group-names to group-total-counts.
    2. a list of dictionaries, one per file.
    If usePrefixOnly is true, groups names of a form 'aa - bb'
    get treated as 'aa'.
    '''

    totals = {}
    counts_per_file = []
    for f in files:
        dict, comments = loadDictionaryFromFileWithComments(f)
        counts = {}
        current_group = 'NONE'
        for comment in comments:
            key = comment[0]
            text = comment[1]
            if key is None or key == '':
                if usePrefixOnly:
                    current_group = getGroupPrefix(text)
                else:
                    current_group = text
            else:
                # If the value is empty, we ignore the key
                if dict[key] == '':
                    continue
                if counts.has_key(current_group):
                    counts[current_group] += 1
                else:
                    counts[current_group] = 1
                if totals.has_key(current_group):
                    totals[current_group] += 1
                else:
                    totals[current_group] = 1
        counts_per_file.append(counts)
    return (totals, counts_per_file)

def getGroupPrefix(s):
    pos = s.find('-')
    if pos > 0:
        return string.strip(s[:pos])
    else:
        return s


## Diff detection/formatting routines ##

def checkFilesForChanges(files):
    '''
    finds which files in a list have a .original file
    '''

    changedFiles = []
    for f in files:
        if os.path.exists(f + '.original'):
            changedFiles.append(f)
    return changedFiles


def findChangedFiles(directory):
    '''
    find the files in a directory which have a .original file
    '''

    changedFiles = []
    os.path.walk(top=directory, func=__appendOriginals, arg=changedFiles)
    return changedFiles


def __appendOriginals(changedFiles, dirname, names):
    for name in names:
        if name.endswith(".original"):
            newName = name[:-9]
            changedFiles.append(os.path.join(dirname, newName))


def diffFilesAsHTML(file1, file2, smartDiff=1):
    '''
    return the differences between two files as HTML
    '''

    isProperties = re.search(r'\.(properties|eep|eed)$', file2)
    if smartDiff and isProperties:
        if re.search(r'MineStar\.properties$', file2):
            javaFormat = 0
        else:
            javaFormat = 1
        dict1 = loadDictionaryFromFile(file1, javaEscapes=javaFormat)
        dict2 = loadDictionaryFromFile(file2, javaEscapes=javaFormat)
        return diffDictionariesAsHTML(dict1, dict2)
    else:
        lines1 = loadLinesFromFile(file1)
        lines2 = loadLinesFromFile(file2)
        result = diffLinesAsHTML(lines1, lines2)
        # If the result contains binary characters, return a message
        if re.search(r'[\x00\x80-\xff]', result):
            return 'Binary files - unable to compare'
        else:
            return result


def diffLinesAsHTML(a, b):
    '''
    return the differences between two lists of strings as HTML

    The result is the first line annotated with the edits required to get
    to the second list. However, if the two lists are the same, a message
    is returned indicating this.
    '''

    if a == b:
        return 'No changes detected'

    # This code is taken from Tim Peter's ndiff.py script in the python distribution.
    # Tim's code has a fancy replace but the plain output will do us for now.
    # He also treats spaces as junk but we make them significant.
    output = []
    cruncher = difflib.SequenceMatcher(None, a, b)
    for tag, alo, ahi, blo, bhi in cruncher.get_opcodes():
        if tag == 'replace':
            addDiffPlainReplace(output, a, alo, ahi, b, blo, bhi)
        elif tag == 'delete':
            addDiffLines(output, '-', a, alo, ahi)
        elif tag == 'insert':
            addDiffLines(output, '+', b, blo, bhi)
        elif tag == 'equal':
            addDiffLines(output, ' ', a, alo, ahi)
        else:
            raise ValueError, 'unknown tag ' + `tag`

    return "<pre>\n" + string.join(output, '') + "\n<pre>"


def addDiffPlainReplace(output, a, alo, ahi, b, blo, bhi):
    assert alo < ahi and blo < bhi
    # dump the shorter block first -- reduces the burden on short-term
    # memory if the blocks are of very different sizes
    if bhi - blo < ahi - alo:
        addDiffLines(output, '+', b, blo, bhi)
        addDiffLines(output, '-', a, alo, ahi)
    else:
        addDiffLines(output, '-', a, alo, ahi)
        addDiffLines(output, '+', b, blo, bhi)

def addDiffLines(output, tag, x, lo, hi):
    # Leave unchanged lines as is and bold the changes
    if tag == ' ':
        fmt = "%s %s"
    else:
        fmt = "<b>%s %s</b>"

    for i in xrange(lo, hi):
        output.append(fmt % (tag, escape(x[i])))


def diffDictionariesAsHTML(dict1, dict2):
    '''
    return the differences between two dictionaries as HTML
    '''

    result = ''
    dict1keys = dict1.keys()
    dict2keys = dict2.keys()
    for key in dict1keys:
        value1 = dict1[key]
        try:
            value2 = dict2[key]
            dict2keys.remove(key)
            if value1 != value2:
                result = result + ("<b>%s changed:</b><br>was: %s<br>now: %s<br>" %
                                   (escape(key), escape(value1), escape(value2)))
        except KeyError:
            result = result + \
              ("<b>%s deleted:</b><br>was: %s<br>" % (escape(key), escape(value1)))
    for key in dict2keys:
        result = result + \
          ("<b>%s added:</b><br>now: %s<br>" % (escape(key), escape(dict2[key])))
    if result == '':
        result = 'No changes detected'
    return result


## Permission IO routines ##

def loadPermissionsFromPropertiesFile(filename):
    '''
    '''

    properties = loadDictionaryFromFile(filename)

    # convert properties to permissions
    permissions = {}
    for p in properties.keys():
        permissions[permissionIdToName(p)] = rolesStringToList(properties[p])
    return permissions


def savePermissionsToPropertiesFile(permissions, filename, keepOriginal=1):
    '''
    '''

    properties = {}
    for p in permissions.keys():
        properties[permissionNameToId(p)] = rolesListToString(permissions[p])
    return saveDictionaryToFile(properties, filename, keepOriginal)


## Permission conversion routines ##

_INHERIT_POLICY = "INHERIT"
_ANYONE_POLICY  = "ANYONE"

def permissionIdToName(s):
    if s[:5] == 'edit.':
        tag = 'edit '
        rest = s[5:]
    elif s[:5] == 'view.':
        tag = 'view '
        rest = s[5:]
    elif s[:7] == 'action.':
        tag = ''
        rest = s[7:]
    else:
        tag = ''
        rest = s
    return tag + string.replace(rest, '-', ' ')

def permissionNameToId(s):
    start = s[:5]
    if start == 'edit ':
        tag = 'edit.'
        rest = s[5:]
    elif start == 'view ':
        tag = 'view.'
        rest = s[5:]
    else:
        tag = 'action.'
        rest = s
    return tag + string.replace(rest, ' ', '-')

def rolesStringToList(s):
    if s == '':
        return [_ANYONE_POLICY]
    elif s == 'DISABLED':
        return []
    else:
        if string.find(s, _INHERIT_POLICY) == 0:
            s = string.strip(s[len(_INHERIT_POLICY):])
            roles = [_INHERIT_POLICY]
        else:
            roles = []
        roles.extend(string.split(s, ','))
        return roles

def rolesListToString(roles):
    if roles is None or len(roles) == 0:
        return 'DISABLED'
    elif roles[0] == _ANYONE_POLICY:
        return ''
    else:
        if len(roles) > 0 and roles[0] == _INHERIT_POLICY:
            return _INHERIT_POLICY + " " + string.join(roles[1:], ',')
        else:
            return string.join(roles, ',')


## General support routines ##

def getFileDetails(files):
    '''
    return a dictionary where the keys are filenames (passed in) and the values are
    (sizeInBytes,lastModifiedDateTime) tuples. If a file is not found,
    the value for that key is None.
    '''
    result = {}
    for f in files:
        if os.path.exists(f):
            result[f] = (os.path.getsize(f), os.path.getmtime(f))
        else:
            result[f] = None
    return result

def getFileExists(f):
    return os.path.exists(f)

def getFileDetailsForDirectory(dir):
    '''
    return a dictionary where the keys are filenames in a directory and the values are
    (sizeInBytes,lastModifiedDateTime) tuples. If a file is not found,
    the value for that key is None.
    '''
    return getFileDetails(getFilesInDirectory(dir))

def getFilesInDirectory(dir):
    result = []
    for f in dircache.listdir(dir):
        result.append(os.path.join(dir, f))
    return result

def findConfigFiles(directory):
    '''
    find the configuration files in a directory.
    At the moment, the files are assumed to have a .properties suffix, not have
    an underscore within them (this removes noise due to localised versions) and
    not be in a directory called test.
    '''

    configFiles = []
    os.path.walk(top=directory, func=__appendConfigFiles, arg=configFiles)
    return configFiles


def __appendConfigFiles(configFiles, dirname, names):
    # Ignore directories starting with 'test', e.g. 'testFoo', 'testBar'.
    if len(dirname) > 4 and dirname[-4:] == 'test':
        return

    def isFile(s):
        return os.path.isfile(os.path.join(dirname, s))

    def isConfigFile(s):
        return isFile(s) and '_' not in s and s.endswith(".properties")

    configFiles.extend([os.path.join(dirname, name) for name in names if isFile(name) and isConfigFile(name)])


def backupFile(filename, keepOriginal=1):
    if keepOriginal:
        originalFilename = filename + ".original"
        if os.path.exists(filename) and not os.path.exists(originalFilename):
            # When Zope 2.4 is used, change this to use shutil.copy2 as
            # that's safer in the case when the subsequent write fails!
            os.rename(filename, originalFilename)

def filenameWithLocale(filename, locale):
    '''
    merge a locale name into a Java properties file
    e.g. merging the locale es_CO into abc.properties gives abc_es_CO.properties
    '''
    if locale is None or locale == '':
        return filename
    else:
        (root, ext) = os.path.splitext(filename)
        return root + '_' + locale + ext

def getLocalesForFilename(filename):
    'given a filename, get the list of (non-default) locales which are defined for it'
    locales = []
    # To do
    return locales


def linesToTable(lines, sep=None, maxsplit=0):
    '''
    convert a list of lines to a list of lists by parsing each line into fields.
    See string.split() for the meanings of the sep and maxsplit parameters.
    '''
    result = []
    for line in lines:
        flds = string.split(line, sep, maxsplit)
        result.append(flds)
    return result


## PhraseBook IO routines ##

_ORIGINAL_TEXT_HDG = "Original_Text"
_LOCAL_TEXT_HDG = "Local_Text"

def loadPhraseBook(filename, sep="\t", javaEscapes=1, dequoteStrings=1, jargonStyle=None):
    '''
    load a phrase-book as a dictionary.
    Phrase-books are text files containing tab-separated fields, one record per line.
    The first field is the original text and the second field is the replacement text.
    Other fields are ignored. If the first record contains 'Original_Text', it is ignored.
    sep is the separator character between fields.
    If javaEscapes is true, java escape sequences are interpreted within the strings.
    If dequoteStrings is true, strings surrounded in double quotes are treated as a CSV field, i.e.
    the double-quotes are stripped and an internal sequence of two double-quotes are replaced with one.
    If jargonStyle is true, string are converted from jargon to java style.
    '''

    # Read in the lines
    lines = loadLinesFromFile(filename)

    # Parse the lines
    if len(lines) > 0 and string.find(lines[0], _ORIGINAL_TEXT_HDG) >= 0:
        del lines[0]
    result = {}
    for line in lines:
        fields = string.split(line, sep)
        if len(fields) == 0:
            continue
        original = string.strip(fields[0])
        if len(fields) > 1:
            replace = string.strip(fields[1])
        else:
            replace = ''
        if dequoteStrings:
            original = _dequoteString(original)
            replace = _dequoteString(replace)
        if javaEscapes:
            original = loadConvert(original)
            replace = loadConvert(replace)
        if jargonStyle:
            original = jargon2javaString(original)
            replace = jargon2javaString(replace)
        result[original] = replace
    return result

def savePhraseBook(dict, filename, sep="\t", useJavaEscapes=True, quoteStrings=True, onlyKeys=False):
    """
    save a phrase-book dictionary to a filename ('-' means stdout).
    See loadPhraseBook() for formatting details.
    If a dictionary key has no value, the key is written out as the value.
    sep is the separator character between fields.
    If useJavaEscapes is true (which it is by default),
    certain embedded characters are converted to Java escape sequences.
    If quoteStrings is true, string are quoted so that special embedded
    characters are correctly imported into Excel.
    If onlyKeys is true, only the keys are dumped, one per line.
    """

    def savePhraseBookTo(f):
        keys = dict.keys()
        keys.sort()
        if onlyKeys:
            f.write("%s\n" % _ORIGINAL_TEXT_HDG)
        else:
            f.write("%s%s%s\n" % (_ORIGINAL_TEXT_HDG, sep, _LOCAL_TEXT_HDG))
        for key in keys:
            value = dict[key] or key
            if useJavaEscapes:
                key = saveConvert(key, escapeSpace=False)
                value = saveConvert(value, escapeSpace=False)
            if quoteStrings:
                key = _quoteString(key)
                value = _quoteString(value)
            if onlyKeys:
                f.write("%s\n" % key)
            else:
                f.write("%s%s%s\n" % (key, sep, value))

    # Special case: '-' means write to stdout (so don't close the file).
    if filename == '-':
        savePhraseBookTo(sys.stdout)
    else:
        with open(filename, "w") as f:
            savePhraseBookTo(f)

def _quoteString(s):
    '''
    ensure a string is safe to use in a CSV file, i.e. if it contains a comma or double quote, then
    enclose it in double quotes and replace each embedded double-quote with two of them
    '''
    if s.find('"') >= 0 or s.find(',') >= 0:
        return '"%s"' % _escapeDoubleQuotes(s)
    else:
        return s

def _dequoteString(s):
    """
    if a string is surrounded by double-quotes, strip them and replace a sequence of two double-quotes
    within the string by one
    """
    if len(s) > 2 and s[0] == '"' and s[-1] == '"':
        s = _unescapeDoubleQuotes(s[1:len(s) - 1])
    return s

def _escapeDoubleQuotes(s):
    'replace each double-quote with a pair of them'
    return string.replace(s, '"', '""')

def _unescapeDoubleQuotes(s):
    'replace each sequence of double-quotes with just one of them'
    return string.replace(s, '""', '"')


## Phrase Book processing routines ##

def compactPhraseBook(dict):
    '''
    find the phrase book entries where the replacement text differs from the original.
    '''
    result = {}
    for key in dict.keys():
        value = dict[key]
        if key != value:
            result[key] = value
    return result

def translatedPhrases(phraseBookPath):
    "return the list of translated phrases in a phrase book"
    pb =loadPhraseBook(phraseBookPath)
    compacted = compactPhraseBook(pb)
    return compacted.keys()


## Jargon phrase books to Java format conversion routines ##

_mnemonicRE = re.compile(r'\&(\w)')
_parameterRE = re.compile(r'\?(\d)')

def jargon2javaString(s):
    '''
    Translate a resource string from jargon style to java style, i.e.:
    - a & embedded immediately before a character is removed (mnenomics are handled differently)
    -?n is replaced with {n}
    '''
    s = re.sub(_mnemonicRE, r'\1', s)
    s = re.sub(_parameterRE, r'{\1}', s)
    return s


def jargon2java(inPath, outPath='-'):
    '''
    load a phrase book from inPath, convert it to java format and dump it to outPath.
    '''
    print "loading phrase book from %s ..." % inPath
    pb = loadPhraseBook(inPath, javaEscapes=0, dequoteStrings=1, jargonStyle=1)
    print "compacting phrase book ..."
    filtered = compactPhraseBook(pb)
    print "saving phrase book to %s ..." % outPath
    savePhraseBook(filtered, outPath)


## Phrase book generation routines ##

def buildPhraseBook(files, groupMaskPattern=None, masterPhraseBook={}, menuRules=0):
    '''
    load a set of resource files, mask out the requested groups, if any, and
    build a dictionary of unique phrases. The phrases are stored as keys in the
    result with selected trailing sequences (':', '*', ':*', '...') stripped.
    If a masterPhraseBook is specified and a phrase is found within it,
    then the translated value is stored as the value.
    Otherwise, None is stored as the value.
    If menuRules is true, each file is parsed as a Jive menu and only the text labels
    and tooltips are potentially added to the phrase book (depending on the
    groupMaskPattern).
    '''
    extraStuffRE = re.compile(r'\s*(:\*|\*|:|\.\.\.)$')
    result = {}
    for file in files:
        dict,comments = loadDictionaryFromFileWithComments(file)
        if groupMaskPattern is not None:
            dict,comments,stats = translateDictionary(dict, comments, None, groupMaskPattern)
        for key,value in dict.items():
            if menuRules:
                if len(key) > 6 and key[-6:] == '.items' or \
                   len(key) > 8 and key[-8:] == '.command' or \
                   len(key) > 5 and key[:5] == 'mask.':
                       continue
                elif not(len(key) > 8 and key[-8:] == ".tooltip"):
                    comma_sep = string.find(value, ',')
                    if comma_sep >= 0:
                        value = value[0:comma_sep]

            # Skip mnemonics (could be either case for the first letter)
            elif string.find(key, "nemonic") >= 1:
                continue
            #print "key: %s, value: %s<" % (key,value)
            value = re.sub(extraStuffRE, '', value)
            result[value] = masterPhraseBook.get(value, None)
    return result


def buildPhraseBookFromListInFile(file, groupMaskPattern=None, bookPath=None,
                                  masterBookPath=None, menuRules=0, onlyKeys=0):
    '''
    load a list of filenames from a file ('-' means stdin) and call buildPhraseBook.
    If bookPath is specified, that filename is created or overriden with a
    phrase book. NOTE: If the future, existing contents from bookPath, if any,
    should first be merged before it is overridden.
    masterBookPath is the path name of a book to consult for initial translations.
    If onlyKeys is true, the dumped phrase book contains only keys.
    If menuRules is true, each file is parsed as a Jive menu and only the text labels
    and tooltips are potentially added to the phrase book (depending on the
    groupMaskPattern).
    '''

    # Get the list of files
    try:
        if file == '-':
            listFile = sys.stdin
        else:
            listFile = open(file)
        files = []
        while 1:
            file = listFile.readline()
            if file == '': break
            if file[0] == '#': continue     # Allow comments
            files.append(string.strip(file))
        listFile.close()
    except IOError, ex:
        raise ex

    # Load the master phrase book, if any
    if masterBookPath is not None and masterBookPath != '':
        masterBook = loadPhraseBook(masterBookPath)
    else:
        masterBook = {}

    # Build the result, dump it as a phrase book if requested and return it
    result = buildPhraseBook(files, groupMaskPattern, masterBook, menuRules)
    if bookPath is not None and bookPath != '':
        savePhraseBook(result, bookPath, onlyKeys=onlyKeys)
    return result


## Dictionary Translation routines ##

# Statistic keys
STATS_KEYS_ATTEMPTED = 'keys attempted'
STATS_KEYS_SUCCEEDED = 'keys succeeded'
# Do these later if and when considered interesting
#STATS_COMMENTS_ATTEMPTED = 'comments attempted'
#STATS_COMMENTS_SUCCEEDED = 'comments succeeded'

def translateDictionary(dict, comments=None, phraseBooks=[], groupMaskPattern=None,
                        asMenu=0, magicPrefix=''):
    '''
    translate and optionally filter a formatted dictionary. This function is
    designed to support generation of an initial resource bundle from an
    appropriately formatted Java resource file where groups of resources (e.g.
    Images, Help contexts) are excluded from the process and a guess is made
    for commonly used button labels, say, via consulting an optional list of
    phrase books.

    Comments is a list of dictionary formatting information (see saveDictionaryToFile()
    in ConfigurationFileIO.py). If comments is none, no masking of entries is done.
    Otherwise, only the keys specified in the formatting information are considered.

    The result is a tuple containing 3 elements:
    1. a dictionary where:
       - entries are removed if comments != None and groupMaskPattern != None and
         an entry's key is in one of the groups which match the mask
       - if a list of phrase books is provided, values are replaced with entries
         found in the phraseBook dictionaries (or None) if not found
    2. updated comment information (filtered and translated)
    3. a dictionary of statistics on how the translation went. Keys are:
       - 'keys attempted' - # of keys for which translation was attempted
       - 'keys succeeded' - # of keys which were successfully translated

    If asMenu is true, the following special rules also apply:
    1. Action commands, menu structures are menu masks are not translated
       (this currently assumes that these are within sections starting with
       'Commands', 'Structures' and 'Masks' accordingly)
    2. tooltips are always translated
    3. Only the description for actions and menus is translated
       and the mnenomic is thrown away.

    If magicPrefix is non-empty, the phrase books are ignored and that prefix
    is added to every phrase found. This is useful for testing how well software
    is prepared for localisation before phrase books enter the equation.
    '''

    debug("TRANSLATION STARTED AT %s - asMenu=%s, groupMaskPattern=%s" % (time.asctime(), asMenu, groupMaskPattern))

    # Get the key-list and updated comments
    if comments is None:
        keyList = dict.keys()
        newComments = None
    elif groupMaskPattern is None:
        keyList = dict.keys()
        newComments = []
        for comment in comments:
            newComments.append((comment[0], _translateValue(phraseBooks, comment[1])))
    else:
        maskRE = re.compile(groupMaskPattern)
        keyList = []
        newComments = []
        keep = 1
        for comment in comments:
            key = comment[0]
            text = comment[1]
            if key is None or key == '':
                keep = maskRE.match(text) is None
                if keep:
                    # NOTE: We do *not* translate group titles because they are used
                    # for localisation reporting purposes.
                    newComments.append((key, text))
            elif keep:
                keyList.append(key)
                newComments.append((key, _translateValue(phraseBooks, text, text)))

    # Translate the requested keys
    keys_attempted = 0
    keys_succeeded = 0
    newDict = {}
    if asMenu:
        for k in keyList:
            if len(k) > 6 and k[-6:] == '.items' or \
               len(k) > 8 and k[-8:] == '.command' or \
               len(k) > 5 and k[:5] == 'mask.':
                   continue
            if magicPrefix != '':
                newDict[k] = magicPrefix + dict[k]
                continue
            if phraseBooks is None:
                newDict[k] = dict[k]
                continue
            if len(k) > 8 and k[-8:] == '.tooltip':
                keys_attempted = keys_attempted + 1
                newDict[k] = _translateValue(phraseBooks, dict[k])
                if newDict[k] is not None: keys_succeeded = keys_succeeded + 1
            else:
                # Translate just the description and derive the mnemonic
                fields = string.split(dict[k], ',')
                desc = string.strip(fields[0])
                keys_attempted = keys_attempted + 1
                fields[0] = _translateValue(phraseBooks, desc)
                if fields[0] is not None:
                    keys_succeeded = keys_succeeded + 1
                    if len(fields) > 1:
                        fields[1] = ''      # for 1st char, could set this to fields[0][0]
                    newDict[k] = string.join(fields, ',')
    else:
        for k in keyList:
            if magicPrefix != '':
                newDict[k] = magicPrefix + dict[k]
                continue
            if phraseBooks is None:
                newDict[k] = dict[k]
                continue
            keys_attempted = keys_attempted + 1
            debug("translating '%s' (%s)" % (dict[k], k))
            newDict[k] = _translateValue(phraseBooks, dict[k])
            if newDict[k] is not None: keys_succeeded = keys_succeeded + 1

    # Return the new dictionary, it's formatting information and translation stats
    if magicPrefix != '':
        keys_attempted = len(keyList)
        keys_succeeded = keys_attempted
    stats = {
      STATS_KEYS_ATTEMPTED: keys_attempted,
      STATS_KEYS_SUCCEEDED: keys_succeeded,
#      STATS_COMMENTS_ATTEMPTED: comments_attempted,
#      STATS_COMMENTS_SUCCEEDED: comments_succeeded,
      }
    return (newDict, newComments, stats)


def _translateValue(phraseBooks, value, defaultValue=None):
    if value is None or len(value) == 0:
        return defaultValue
    if value[-1] == ':':
        value = value[0:-1]
        suffix = ':'
    elif len(value) > 3 and value[-3:] == '...':
        value = string.strip(value[0:-3])
        suffix = ' ...'
    else:
        suffix = ''
    if phraseBooks is not None:
        for pb in phraseBooks:
            found = pb.get(value)
            # If the phrase book doesn't match or matches with an empty string,
            # then keep searching
            if found is not None and len(found) > 0:
                debug("found '%s'" % value)
                return found + suffix
        debug("failed to find '%s'" % value)
    if defaultValue is None:
        return None
    else:
        return defaultValue + suffix


def translateMenu(dict, comments=None, phraseBooks=[]):
    '''
    translate and optionally filter a formatted dictionary holding a Jive menu.
    This is a convenience wrapper around translateDictionary() with asMenu set to
    true and an appropriate groupMaskPattern passed in.
    '''
    return translateDictionary(dict, comments, phraseBooks,
                               r'^(Commands|Structures|Masks)', asMenu=1)



def getUntranslatedPhrases(default_fname, generated_fname, groupMaskPattern, asMenu=0):
    '''
    Get the phrases in a file which are not translated in a generated file
    excluding the nominated group mask pattern.
    '''

    # Get the data
    (default_dict, default_cmts)     = loadDictionaryFromFileWithComments(default_fname, javaEscapes=0)
    (generated_dict, generated_cmts) = loadDictionaryFromFileWithComments(generated_fname, javaEscapes=0)

    # Find the unprocessed ones
    result = []
    maskRE = re.compile(groupMaskPattern)
    keep = 1
    for index in range(0, len(default_cmts)):
        key = default_cmts[index][0]
        comment = default_cmts[index][1]
        if key is None or key == '':
            keep = maskRE.match(comment) is None
        elif keep:
            if not generated_dict.has_key(key):
                phrase = default_dict[key]
                if asMenu:
                    fields = string.split(phrase, ',')
                    phrase = string.strip(fields[0])
                result.append(phrase)
    return result


## Test routines ##

def _test_basicIO():
    # Test basic IO
    dict = {'a':'ABC', 'x':'XYZ', 'q':'qaz'}
    print saveDictionaryToFile(dict, 'C:/tmp/saveToFileTest.properties', '_')
    print saveDictionaryToFile(dict, 'C:/tmp/saveToFileCommented.properties',
      comments=[('x','Xeena'),(None,'Group Alpha', 'Alpha is A1'),('a',"Alpha\nline 2")])
    (dict, comments) = loadDictionaryFromFileWithComments('C:/tmp/saveToFileCommented.properties')
    print "dict: %s" % dict
    print "comments: %s" % comments

def _test_dictIO():
    # John's test
    import sys
    for filename in sys.argv[1:]:
        print filename
        dict = loadDictionaryFromFile(filename)
        print dict
        print
        saveDictionaryToFile(dict, 'test.properties', 0)

def _test_permissionIO():
    # Test permission IO
    p1 = loadPermissionsFromPropertiesFile('C:/tmp/testSecurity.properties')
    print "loaded:\n" + str(p1)
    p2 = {'edit.travel-times': [], 'edit.unload-times': ['Builder','Controller'],
          'edit.description': ['ANYONE'], 'edit':['INHERIT', 'Builder']}
    savePermissionsToPropertiesFile(p1, 'C:/tmp/test1Security.properties')
    savePermissionsToPropertiesFile(p2, 'C:/tmp/test2Security.properties')

def _test_diffDetection():
    # Test difference detection
    print "File differences by search ..."
    changed = findChangedFiles('C:/tmp')
    for i in changed:
        print "::: %s :::" % i
        print diffFilesAsHTML(i + '.original', i)
    print "File differences by list ..."
    print checkFilesForChanges([
      'C:/tmp/test1Security.properties', 'C:/tmp/test3Security.properties',
      'C:/tmp/saveToFileTest.properties'])

def _test_fileDetails():
    print "File Details ..."
    print getFileDetailsForDirectory('C:/tmp')

def _test_phraseBookIO():
    print "::: Phrase Book IO :::"
    phrases = {'OK':'&Aceptor', 'Cancel':'Cancelar', '?0 Labels ?1':'?0 Etiquetas ?1',
               'xxx':None, 'yyy':'yyy'}
    savePhraseBook(phrases, 'C:/tmp/es_es.pb')
    print "save completed"
    pb = loadPhraseBook('C:/tmp/es_es.pb', jargonStyle=1)
    print "load results: %s" % pb
    print "compacted results: %s" % compactPhraseBook(pb)
    pb = loadPhraseBook('extended_es.phbk', dequoteStrings=1)
    print "load results: %s" % pb
    print "compacted results: %s" % compactPhraseBook(pb)
    savePhraseBook(pb, 'C:/tmp/extended_es.phbk', quoteStrings=1)
    print "quoted save completed - check c:/tmp/extended_es.phbk"

def _test_translate():
    dict = {'ok': 'OK', 'cancel':'Cancel', 'width':'44', 'height':'55'}
    cmts = [
        ('', 'Labels'), ('ok', 'ok button label'), ('cancel', ''),
        ('', 'Settings'), ('width', ''), ('height', '')]
    phrases = {'OK':'Aceptor', 'Cancel':'Cancelar', 'Labels': 'Etiquetas'}

    print "::: translation with no masking :::"
    newDict,newCmts,stats = translateDictionary(dict, cmts, [phrases])
    print "dict: %s" % newDict
    print "comments: %s" % newCmts

    print "::: translation with Setting masking :::"
    mask = r'^(Settings|Images|Help)'
    newDict,newCmts,stats = translateDictionary(dict, cmts, [phrases], mask)
    print "dict: %s" % newDict
    print "comments: %s" % newCmts

def _test_translateMenu():
    print "::: translating menu to Spanish :::"
    fname = 'C:/tmp/testMenu.properties'
    (dict, cmts) = loadDictionaryFromFileWithComments(fname)
    pb = loadPhraseBook('C:/tmp/es_es.phbk')
    print "loaded menu & phrase book"
    newDict,newCmts,stats = translateMenu(dict, cmts, [pb])
    fname_es = filenameWithLocale(fname, 'es')
    saveDictionaryToFile(newDict, fname_es, comments=newCmts)
    print "translated and saved - see %s for output" % fname_es
    print "stats: %s" % stats


def test_reportGroups(fname):
    print "::: loading filenames from %s :::" % fname
    try:
        if fname == '-':
            listFile = sys.stdin
        else:
            listFile = open(fname)
        files = []
        while 1:
            file = listFile.readline()
            if file == '': break
            if file[0] == '#': continue     # Allow comments
            files.append(string.strip(file))
        listFile.close()
    except IOError, ex:
        raise ex

    (totals, dicts) = reportGroupCounts(files)
    print "group totals: %s" % totals
    for i in range(0, len(dicts)):
        print "::: %s :::" % files[i]
        print dicts[i]

def _test_xx(a, b="b"):
    return "a is %s, b is %s" % (a,b)


## Test harness ##

if __name__ == '__main__':
    # If an argument is provided, run that function with remaining args as parameters.
    if len(sys.argv) > 1:
        fn = sys.argv[1]
        # If the fn ends in $, don't show the result
        quiet = fn[-1] == '$'
        if quiet:
            fn = fn[0:-1]
        result = apply(globals()[fn], sys.argv[2:])
        if quiet:
            print "%s completed" % fn
        else:
            print "%s returned: %s" % (fn, result)
        sys.exit()

    # Otherwise, call the test functions with no mandatory parameters.
    #_test_basicIO()
    ##_test_dictIO()
    #_test_permissionIO()
    #_test_diffDetection()
    #_test_fileDetails()
    _test_phraseBookIO()
    _test_translate()
    #_test_translateMenu()
