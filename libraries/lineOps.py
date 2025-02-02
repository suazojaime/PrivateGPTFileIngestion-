""" Line operations """

import string

WHITE_SPACE_CHARS = " \t\r\n\f"

def getLinesFromFile(filename):
    """ Get the content of a file as a list of lines """
    with open(filename) as inFile:
        return inFile.readlines()

def cleanLines(lines):
    """ Clean lines of gunk """
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
        if line[0] != '#' or line.startswith("#include "):
            goodLines.append(line)
    return goodLines

def continueLine(line):
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

def cleanLine(line):
    """Remove new lines from end of line, and white space from the beginning."""
    line = stripEol(line)
    spaces = 0
    while len(line) > spaces and line[spaces] in WHITE_SPACE_CHARS:
        spaces = spaces + 1
    if spaces == 0:
        return line
    else:
        return line[spaces:]

def stripEol(line):
    """ Strip EOL from a line. """
    while len(line) > 0 and line[-1] in ['\n', '\r']:
        line = line[:-1]
    return line

def readLines(filename):
    """Return all non-blank, non-comment lines from the file"""
    lines = []
    for line in getLinesFromFile(filename):
        line = stripEol(string.strip(line))
        if len(line) == 0:
            continue
        if line[0] == '#' and not line.startswith("#include"):
            continue
        lines.append(line)
    return lines

def readOptionalLines(filename):
    """
    Read all non-blank, non-comment lines from the file, but if the
    file does not exist, just treat it as if it had no lines.
    """
    try:
        return readLines(filename)
    except IOError:
        return []

PUNCTUATION = "!@#$%^&*()~`-_=+[{]};:',<.>/?" + '"'

def stripPunctuation(str):
    """ Strip punctuation characters from a line """
    while len(str) > 0 and str[0] in PUNCTUATION:
        str = str[1:]
    while len(str) > 0 and str[-1] in PUNCTUATION:
        str = str[:-1]
    return str

def replaceLine(line, substs):
    """ Replace substitutions in a line """
    pos = 0
    while line.find("%", pos) >= 0:
        pos = line.find("%", pos)
        nextpos = line.find("%", pos+1)
        if nextpos > pos:
            key = line[pos+1:nextpos]
            if len(key) > 0 and substs.has_key(key):
                value = substs[key]
            else:
                value = "%" + key + "%"
            line = line[:pos] + value + line[nextpos+1:]
            pos = pos+2
        else:
            break
    return line
