import minestar

logger = minestar.initApp()

## Phrase book generation routines ##
def buildPhraseBook(files, groupMaskPattern, masterPhraseBook, menuRules):
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
                if key.endswith('.items') or key.endswith('.command') or key.startswith('mask.'):
                    continue
                elif not key.endswith(".tooltip"):
                    comma_sep = value.find(',')
                    if comma_sep >= 0:
                        value = value[0:comma_sep]
            # Skip mnemonics (could be either case for the first letter)
            elif key.find("nemonic") >= 1:
                continue
            value = re.sub(extraStuffRE, '', value)
            result[value] = masterPhraseBook.get(value, None)
    return result

def buildPhraseBookFromFiles(files, groupMaskPattern=None, bookPath=None,
        masterBookPath=None, menuRules=0, onlyKeys=0):
    '''
    Call buildPhraseBook on the list of files.
    If bookPath is specified, that filename is created or overriden with a
    phrase book. NOTE: If the future, existing contents from bookPath, if any,
    should first be merged before it is overridden.
    masterBookPath is the path name of a book to consult for initial translations.
    If onlyKeys is true, the dumped phrase book contains only keys.
    If menuRules is true, each file is parsed as a Jive menu and only the text labels
    and tooltips are potentially added to the phrase book (depending on the
    groupMaskPattern).
    '''
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
