""" Property file operations """

from lineOps import readLines, stripEol, stripPunctuation, cleanLines, cleanLine, getLinesFromFile, replaceLine
import string
import os

STRICT_KEY_VALUE_SEPARATORS = "=:"
WHITE_SPACE_CHARS = " \t\r\n\f"
KEY_VALUE_SEPARATORS = STRICT_KEY_VALUE_SEPARATORS + WHITE_SPACE_CHARS

def loadProperties(filename, filenames=[]):
    """
    Return (sources, properties) where:
     * sources is a dict from keys to file names they were found in
     * properties is a dict from keys to values
    filenames is the files which have already been included, to detect recursion
    """
    result = {}
    sources = {}
    filenames.append(filename)
    for line in readLines(filename):
        line = stripEol(line)
        if line.startswith("#include"):
            newfile = string.strip(line[8:])
            newfile = stripPunctuation(newfile)
            fields = filename.split(os.sep)
            fields[-1] = newfile
            newfile = string.join(fields, os.sep)
            if newfile not in filenames:
                (newSources, newResult) = loadProperties(newfile, filenames)
                for (key, value) in newResult.items():
                    result[key] = value
                    sources[key] = newSources[key]
        else:
            fields = string.split(line, "=", 1)
            if len(fields) != 2:
                print "Unable to interpret '%s' in file %s" %(line, filename)
                continue
            fields = map(string.strip, fields)
            if len(fields[0]) == 0:
                continue
            result[fields[0]] = fields[1]
            sources[fields[0]] = filename
    return (sources, result)

def loadJavaStyleProperties(filename, filenames=[]):
    """
        Load properties from a file exactly as for a Java properties file,
        except that we also interpret #includes as for the C preprocessor.
    """
    return loadJavaStylePropertiesFromLines(filename, filenames, getLinesFromFile(filename))


def loadJavaStylePropertiesFromLines(filename, filenames, lines_from_file):
    """Load properties from an array of lines."""
    lines = cleanLines(lines_from_file)
    result = {}
    sources = {}
    for line in lines:
        if line.startswith("#include"):
            newfile = stripPunctuation(line[8:].strip())
            fields = filename.split(os.sep)
            fields[-1] = newfile
            newfile = os.sep.join(fields)
            if newfile not in filenames:
                (newSources, newResult) = loadJavaStyleProperties(newfile, filenames)
                filenames.append(newfile)
                for (key, value) in newResult.items():
                    result[key] = value

                    sources[key] = newSources[key]
        else:
            (key, value) = parseJavaStylePropertyLine(line)
            result[key] = value
            sources[key] = filename
    return (sources, result)


def parseJavaStylePropertyLines(lines):
    properties = {}
    for line in lines:
        if not line.startswith('#'):
            (key, value) = parseJavaStylePropertyLine(line)
            properties[key] = value
    return properties

def parseJavaStylePropertyLine(line):
    sepIndex = 0
    while sepIndex < len(line):
        ch = line[sepIndex]
        if ch == '\\':
            sepIndex = sepIndex + 1
        elif ch in KEY_VALUE_SEPARATORS:
            break
        sepIndex = sepIndex + 1
    key = line[:sepIndex]
    line = cleanLine(line[sepIndex:])
    if len(line) > 0 and line[0] in STRICT_KEY_VALUE_SEPARATORS:
        line = line[1:]
    line = __loadConvert(cleanLine(line))
    actualKey = __loadConvert(key)
    return (actualKey, line)

def replaceProperties(templateFile, destFile, substs):
    import i18n
    try:
        file = open(destFile, "w")
        for line in open(templateFile).readlines():
            line = replaceLine(stripEol(line), substs)
            file.write(line + "\n")
        file.close()
        print i18n.translate("Substituted properties in %s") % destFile
    except IOError:
        print i18n.translate("Failed to subsititute from %s to %s") % (templateFile, destFile)

LOAD_TRANSLATION = { 't' : '\t', 'r' : '\r', 'n': '\n', 'f': '\f' }

def __loadConvert(s):
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
                if LOAD_TRANSLATION.has_key(ch):
                    ch = LOAD_TRANSLATION[ch]
                result = result + ch
        else:
            result = result + ch
    return result
