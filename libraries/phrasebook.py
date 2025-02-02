## PhraseBook IO routines ##
import mstarpaths, os, dictionary
import minestar

logger = minestar.initApp()

def _unescapeDoubleQuotes(s):
    'replace each sequence of double-quotes with just one of them'
    return s.replace('""', '"')

def _dequoteString(s):
    """
    if a string is surrounded by double-quotes, strip them and replace a sequence of two double-quotes
    within the string by one
    """
    if len(s) > 2 and s[0] == '"' and s[-1] == '"':
        s = _unescapeDoubleQuotes(s[1:len(s) - 1])
    return s

def _getAllPhraseBooks(locale):
    phbks = []
    directory = mstarpaths.interpretPath("{MSTAR_HOME}")
    os.path.walk(directory, _checkPhraseBook, (locale, phbks))
    return phbks

def _checkPhraseBook(arg, dirname, names):
    (locale, phbks) = arg
    pattern = "_%s." % locale
    for name in names:
        if name.endswith(".phbk"):
            if name.find(pattern) >= 0:
                phbks.append(dirname + os.sep + name)

_ORIGINAL_TEXT_HDG = "Original_Text"
_LOCAL_TEXT_HDG = "Local_Text"

def getPhraseBook(locale, sep="\t", javaEscapes=1, dequoteStrings=1, jargonStyle=None):
    phraseBooks = _getAllPhraseBooks(locale)
    pbs = [ loadPhraseBook(filename) for filename in phraseBooks ]
    return PhraseBook(None, None, pbs)

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
    try:
        inFile = open(filename)
        lines = inFile.readlines()
        inFile.close()
    except IOError, ex:
        raise ex
    # Parse the lines
    if len(lines) > 0 and lines[0].find(_ORIGINAL_TEXT_HDG) >= 0:
        del lines[0]
    result = {}
    for line in lines:
        fields = line.split(sep)
        if len(fields) == 0:
            continue
        original = fields[0].strip()
        if len(fields) > 1:
            replace = fields[1].strip()
        else:
            replace = ''
        if dequoteStrings:
            original = _dequoteString(original)
            replace = _dequoteString(replace)
        if javaEscapes:
            original = dictionary.loadConvert(original)
            replace = dictionary.loadConvert(replace)
        if jargonStyle:
            original = jargon2javaString(original)
            replace = jargon2javaString(replace)
        result[original] = replace
    return PhraseBook(result, filename)
    
class PhraseBook:
    def __init__(self, dict, filename, phraseBooks=None):
        """
        If dict is None and phraseBooks is not, then this is a composite phrase book
        consisting of the union of those in the list phraseBooks.
        """
        self.dict = dict
        self.filename = filename
        self.phraseBooks = phraseBooks

    def save(self, filename, sep="\t", useJavaEscapes=1, quoteStrings=1,
                    onlyKeys=0):
        '''
        save a phrase-book dictionary to a filename ('-' means stdout).
        See loadPhraseBook() for formatting details.
        If a dictionary key has no value, the key is written out as the value.
        sep is the separator character between fields.
        If useJavaEscapes is true (which it is by default),
        certain embedded characters are converted to Java escape sequences.
        If quoteStrings is true, string are quoted so that special embedded
        characters are correctly imported into Excel.
        If onlyKeys is true, only the keys are dumped, one per line.
        '''
        try:
            if filename == '-':
                outFile = sys.stdout
            else:
                outFile = open(filename, "w")
            dict = self.dict
            keys = dict.keys()
            keys.sort()
            if onlyKeys:
                outFile.write("%s\n" % _ORIGINAL_TEXT_HDG)
            else:
                outFile.write("%s%s%s\n" % (_ORIGINAL_TEXT_HDG,sep,_LOCAL_TEXT_HDG))
            for key in keys:
                value = dict[key] or key
                if useJavaEscapes:
                    key = saveConvert(key, escapeSpace=0)
                    value = saveConvert(value, escapeSpace=0)
                if quoteStrings:
                    key = _quoteString(key)
                    value = _quoteString(value)
                if onlyKeys:
                    outFile.write("%s\n" % key)
                else:
                    outFile.write("%s%s%s\n" % (key,sep,value))
            if filename != '-':
                outFile.close()
        except IOError, ex:
            raise ex
            
    def get(self, key):
        if self.dict is not None:
            return self.dict.get(key)
        else:
            # composite
            for pb in self.phraseBooks:
                value = pb.get(key)
                if value is not None and len(value) > 0:
                    return value
            return None
