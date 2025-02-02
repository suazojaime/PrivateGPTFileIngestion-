languages = {"en": {}}

def loadLanguage(lang):
    if languages.get(lang) is not None:
        return
    import ufs, mstarpaths
    ufsRoot = ufs.getRoot(mstarpaths.interpretFormat("{UFS_PATH}"))
    dict = {}
    try:
        pbDir = ufsRoot.getSubdir("phrasebooks")
        pbFiles = pbDir.listFiles()
        for phbk in pbFiles:
            if not phbk.getName().endswith(("%s.txt"%lang)):
                continue
            for line in phbk.getTextContent().split("\n"):
                fields = line.split("\t")
                if len(fields) != 3:
                    continue
                dict[fields[1]] = fields[2]
    except ufs.UfsException:
        print "WARNING: No phrasebooks found"
    languages[lang] = dict

def translate(text, lang="en"):
    return translateLanguage(text, lang)

def translateLanguage(key, lang):
    loadLanguage(lang)
    if not languages.has_key(lang):
        return key
    if languages[lang].has_key(key):
        result = languages[lang][key]
        if result is None or result == "":
            return "[%s]" % key
        return result
    else:
        return key

def isTranslated(key, lang):
    loadLanguage(lang)
    if not languages.has_key(lang):
        return 0
    if languages[lang].has_key(key):
        return 1
    else:
        return
