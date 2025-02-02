# Phrasebook code stolen from the portal.
# Originally written by IanC

import re, string, mstarpaths, os, mstarrun, mstarpaths, dictionary, i18n, phrasebook
import minestar

logger = minestar.initApp()

# Statistic keys
STATS_KEYS_ATTEMPTED = 'keys attempted'
STATS_KEYS_SUCCEEDED = 'keys succeeded'

def filenameWithLocale(filename, locale):
    '''
    merge a locale name into a Java properties file
    e.g. merging the locale es_CO into abc.properties gives abc_es_CO.properties
    '''
    if locale == None or locale == '':
        return filename
    else:
        (root, ext) = os.path.splitext(filename)
        return root + '_' + locale + ext

def _translateValue(phraseBook, value, defaultValue=None):
    "Look in the phrasebooks and try to translate the value."
    if value is None or len(value) == 0:
        return defaultValue
    if value[-1] == ':':
        value = value[0:-1]
        suffix = ':'
    elif value[-1] == ' ':
        value = value[0:-1]
        suffix = ' '
    elif len(value) > 3 and value[-3:] == '...':
        value = value[0:-3].strip()
        suffix = ' ...'
    else:
        suffix = ''
    if len(value) == 0:
        return suffix
    found = phraseBook.get(value)
    if found is not None and len(found) > 0:
        return found + suffix
    if defaultValue is None:
        return None
    else:
        return defaultValue + suffix
        
def _getKeysAndTranslateComments(fileName, dict, comments, phraseBook, groupMaskPattern):
    "Get the key list and translate comments"
    if comments is None:
        keyList = dict.keys()
        newComments = None
    elif groupMaskPattern is None:
        keyList = dict.keys()
        newComments = []
        for (key, text) in comments:
            newComments.append((key, _translateValue(phraseBook, text)))
    else:
        maskRE = re.compile(groupMaskPattern)
        keyList = []
        newComments = []
        keep = 1
        obj = None
        try:
            for obj in comments:
                (key, text) = obj
                if key is None or key == '':
                    keep = maskRE.match(text) is None
                    if keep:
                        # NOTE: We do *not* translate group titles because they are used
                        # for localisation reporting purposes.
                        newComments.append((key, text))
                elif keep:
                    keyList.append(key)
                    newComments.append((key, _translateValue(phraseBook, text, text)))
        except ValueError:
            print "Error translating %s" % fileName
            print obj
    return (keyList, newComments)

def _translateDictNormally(keyList, dict, phraseBook):
    newDict = {}
    keys_attempted = 0
    keys_succeeded = 0
    for k in keyList:
        if phraseBook is None:
            newDict[k] = dict[k]
            continue
        keys_attempted = keys_attempted + 1
        newDict[k] = _translateValue(phraseBook, dict[k])
        if newDict[k] is not None:
            keys_succeeded = keys_succeeded + 1
    return (newDict, keys_attempted, keys_succeeded)

def translateDictionary(fileName, dict, comments, phraseBook):
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
    '''
    groupMaskPattern = r'^(Images|Help|Settings)'
    (keyList, newComments) = _getKeysAndTranslateComments(fileName, dict, comments, phraseBook, groupMaskPattern)
    # Translate the requested keys
    (newDict, keysAttempted, keysSucceeded) = _translateDictNormally(keyList, dict, phraseBook)
    # Return the new dictionary, its formatting information and translation stats
    stats = { STATS_KEYS_ATTEMPTED: keysAttempted, STATS_KEYS_SUCCEEDED: keysSucceeded }
    return (newDict, newComments, stats)

def _translateDictAsMenu(keyList, dict, phraseBook):
    newDict = {}
    keys_attempted = 0
    keys_succeeded = 0
    for k in keyList:
        if k.endswith('.items') or k.endswith('.command') or k.startswith('mask.'):
            continue
        if phraseBooks is None:
            newDict[k] = dict[k]
            continue
        keys_attempted = keys_attempted + 1
        if k.endswith('.tooltip'):
            newDict[k] = _translateValue(phraseBooks, dict[k])
            if newDict[k] is not None:
                keys_succeeded = keys_succeeded + 1
        else:
            # Translate just the description and derive the mnemonic
            fields = dict[k].split(',')
            fields[0] = _translateValue(phraseBooks, fields[0].strip())
            if fields[0] is not None:
                keys_succeeded = keys_succeeded + 1
                if len(fields) > 1:
                    fields[1] = ''      # for 1st char, could set this to fields[0][0]
                newDict[k] = string.join(fields, ',')
    return (newDict, keys_attempted, keys_succeeded)

def translateMenu(fileName, dict, comments, phraseBook):
    '''
    Translate and optionally filter a formatted dictionary holding a Jive menu.

    The following special rules apply:
    1. Action commands, menu structures are menu masks are not translated
       (this currently assumes that these are within sections starting with
       'Commands', 'Structures' and 'Masks' accordingly)
    2. tooltips are always translated
    3. Only the description for actions and menus is translated
       and the mnenomic is thrown away.
    '''
    groupMaskPattern = r'^(Commands|Structures|Masks)'
    (keyList, newComments) = _getKeysAndTranslateComments(fileName, dict, comments, phraseBook, groupMaskPattern)
    # Translate the requested keys
    (newDict, keysAttempted, keysSucceeded) = _translateDictAsMenu(keyList, dict, phraseBook)
    # Return the new dictionary, its formatting information and translation stats
    stats = { STATS_KEYS_ATTEMPTED: keysAttempted, STATS_KEYS_SUCCEEDED: keysSucceeded }
    return (newDict, newComments, stats)

def findResourceFiles(directory):
    '''
    find the configuration files in a directory.
    At the moment, the files are assumed to have a .properties suffix, not have
    an underscore within them (this removes noise due to localised versions) and
    not be in a directory called test.
    '''
    configFiles = []
    os.path.walk(directory, _appendConfigFiles, configFiles)
    return configFiles

def _appendConfigFiles(files, dirname, names):
    if dirname.endswith('test'):
        return
    for name in names:
        if string.find(name, '_') != -1:
            continue
        match = re.search(r'\.properties$', name)
        if match:
            fullname = dirname + os.sep + name
            files.append(fullname)
            
if __name__ == '__main__':
    if mstarpaths.runningFromRepository:
        res = mstarpaths.interpretPath("{MSTAR_HOME}/../res")
    else:
        res = mstarpaths.interpretPath("{MSTAR_LIB}/res")
    files = findResourceFiles(res)
    resources = []
    security = []
    config = []
    menu = []
    mapping = []
    statistics = []
    formatting = []
    unknown = []
    for file in files:
        if file.endswith("Resource.properties") or file.endswith("resource.properties") or file.endswith("Resources.properties"):
            resources.append(file)
        elif file.endswith("Security.properties"):
            security.append(file)
        elif file.endswith("Config.properties") or file.endswith("config.properties"):
            config.append(file)
        elif file.endswith("Menu.properties"):
            menu.append(file)
        elif file.endswith("Mapping.properties") or file.endswith("Mappings.properties"):
            mapping.append(file)
        elif file.endswith("Formatting.properties"):
            formatting.append(file)
        elif file.endswith("Statistics.properties"):
            # these are really just resources
            statistics.append(file)
        else:
            unknown.append(file)
    locale = "es"
    phraseBook = phrasebook.getPhraseBook(locale)
    # translate localisable strings
    translatable = resources + statistics
    for file in translatable:
        print i18n.translate("Translating resources file %s") % file
        # Convert the file and save the results
        (dict, comments) = dictionary.loadDictionaryFromFileWithComments(file)
        (newDict, newComments, stats) = translateDictionary(file, dict, comments, phraseBook)
        new_filename = filenameWithLocale(file, locale)
        dictionary.saveDictionaryToFile(newDict, new_filename, comments=newComments)
    # translate menus
    translatable = menu
    for file in translatable:
        print i18n.translate("Translating menu file %s") % file
        # Convert the file and save the results
        (dict, comments) = dictionary.loadDictionaryFromFileWithComments(file)
        (newDict, newComments, stats) = translateMenu(file, dict, comments, phraseBook)
        new_filename = filenameWithLocale(file, locale)
        dictionary.saveDictionaryToFile(newDict, new_filename, comments=newComments)
