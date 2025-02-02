# Code for manipulating Java properties files
# Originally by IanC
import re, minestar

logger = minestar.initApp()

strictKeyValueSeparators = "=:"
whiteSpaceChars = " \t\r\n\f"
keyValueSeparators = strictKeyValueSeparators + whiteSpaceChars
loadTranslation = { 't' : '\t', 'r' : '\r', 'n': '\n', 'f': '\f' }
saveTranslation = { '\\': '\\\\', '\t': '\\t', '\n': '\\n', '\r': '\\r', '\f': '\\f' }
hex = "0123456789abcdef"

def _continueLine(line):
    """
    Return whether a line is continued on the next line.
    Translated from java.util.Properties JDK 1.3
    """
    slashCount = 0
    index = len(line) - 1
    while index >= 0 and line[index] == '\\':
        slashCount = slashCount + 1
        index = index - 1
    return (slashCount % 2) == 1

def _cleanLine(line):
    """
    Remove new lines from end of line, and white space from the beginning.
    """
    if line.endswith('\n'):
        line = line[:-1]
    return line.lstrip()

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
    
def _readGoodLines(filename):
    # read in the lines
    try:
        inFile = open(filename)
        lines = inFile.readlines()
        inFile.close()
    except IOError, ex:
        raise ex
    # clean new lines and gunk
    # Note: This code is really ugly so it is bug-compatible with the JDK.
    # However we keep #-style comments (but still throw away !-style ones) so
    # that we can match them with keys later on.
    goodLines = []
    index = 0
    while index < len(lines):
        line = _cleanLine(lines[index])
        index = index + 1
        if len(line) == 0:
            continue
        firstChar = line[0]
        if firstChar == '!':
            continue
        while _continueLine(line):
            if index == len(lines):
                break
            nextline = _cleanLine(lines[index])
            index = index + 1
            # drop continuation character
            line = line[:-1] + nextline
        goodLines.append(line)
    return goodLines

_groupHeadingRE = re.compile(r'^##\s*(.+)\s*##$')

def _parseKeyValueLine(line, namePrefix, javaEscapes):
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
    line = _cleanLine(line[sepIndex:])
    if len(line) > 0 and line[0] in strictKeyValueSeparators:
        line = line[1:]
    line = _cleanLine(line)
    if javaEscapes:
        actualKey = loadConvert(key)
        value = loadConvert(line)
    else:
        actualKey = key
        value = line
    return (actualKey, value)

def loadDictionaryFromFileWithComments(filename, namePrefix=None, javaEscapes=1):
    '''
    load a dictionary from a file exactly as for a Java properties file.
    The result is a tuple containing 2 elements: the dictionary and a list of comments.
    See saveDictionaryToFile() for details on how the comments list is structured.
    '''
    # parse the lines
    lines = _readGoodLines(filename)
    result = {}
    comments = []
    lastComment = None
    lastGroupComment = None
    for line in lines:
        groupHeading = _groupHeadingRE.match(line)
        if groupHeading:
            # group head ## BLAH ##
            comments.append(('', groupHeading.group(1).strip()))
            lastComment = None
            lastGroupComment = None
        elif line.startswith('##'):
            # group comment ## BLAH
            if lastGroupComment is None:
                lastGroupComment = line[2:].strip()
            else:
                lastGroupComment = lastGroupComment + ' ' + line[2:].strip()
        elif line.startswith('#'):
            # comment # BLAH
            if lastComment is None:
                lastComment = line[1:].strip()
            else:
                lastComment = lastComment + ' ' + line[1:].strip()
        else:
            # normal key
            (actualKey, value) = _parseKeyValueLine(line)
            result[actualKey] = value
            if lastGroupComment is not None:
                # For groups, the key is empty and the 'comment' is the heading so
                # group comments in the 3rd slot of the tuple
                if len(comments) > 0:
                    comments[-1] = comments[-1] + (lastGroupComment,)
                lastGroupComment = None
            comments.append((actualKey, lastComment))
            lastComment = None
    return (result, comments)
    
_lineRE = re.compile(r'^', re.MULTILINE)

def text2comment(text, prefixPerLine):
    if text.find('\n') == -1:
        return prefixPerLine + text
    else:
        return _lineRE.sub(prefixPerLine, text)

def saveConvert(s, escapeSpace):
    result = ""
    i = 0
    lens = len(s)
    while i < lens:
        ch = s[i]
        i = i + 1
        if ch == '\\' and i < lens and s[i] == 'u':
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

def saveDictionaryToFile(dict, filename, keepOriginal=1, namePrefix='', sep=' = ', comments=[]):
    '''
    save a dictionary to a file as name=value pairs, one per line,
    prepending the name prefix to each name.
    - comments - an optional list of name,text tuples giving the order in which to
      output pairs and the comment text to output immediately before each one.
      If a list entry has no name and only text, that text is output in 'group header'
      style (## blah blah blah ##) will a blank line or two immediately before it as
      appropriate. Names not found in the list are output after those that are.

    Returns 1 if everything succeeded
    '''
    minestar.backupFile(filename, keepOriginal)
    try:
        outFile = open(filename, 'w')
        keys = dict.keys()
        # Output the comments and pairs in the order requested        
        for comment in comments:
            key = comment[0]
            text = comment[1]
            if key:
                try:
                    keys.remove(key)
                    value = dict[key]
                except ValueError:
                    value = None
                # Comment out keys where the value is None
                if value == None:
                    prefix = "!"
                else:
                    prefix = ""
                if text:
                    commentText = text2comment(text, prefix + "# ")
                    outFile.write("\n%s\n" % commentText)
                outFile.write("%s%s%s%s\n" % (prefix, saveConvert(namePrefix + key, 1), sep, saveConvert(str(value), 0)))
            elif text:
                # group heading
                outFile.write("\n\n## %s ##\n\n" % text)
                if len(comment) > 2:
                    outFile.write("## %s\n\n" % comment[2])
        # Now output the remainder in sorted order
        keys.sort()
        for key in keys:
            outFile.write("%s%s%s\n" % (saveConvert(namePrefix + key, 1), sep, saveConvert(str(dict[key]), 0)))
        outFile.close()
        return 1
    except IOError, ex:
        raise ex
