# An application to tell you what the untranslated strings used my mstarrun are.
import mstarrun, string, i18n, sys
import minestar

logger = minestar.initApp()

def findAllStrings():
    # this is kinda hard, many of them are embedded in the code
    keys = mstarrun.findAllTargets()
    strings = []
    for key in keys:
        desc = None
        descKey = key + ".description"
        if mstarrun.applications.has_key(descKey):
            desc = mstarrun.applications[descKey]
            if desc is not None:
                strings.append(desc)
    return strings
    
if len(sys.argv) > 1:
    strings = findAllStrings()
    for locale in sys.argv[1:]:
        if locale == "en":
            continue
        localePrinted = 0
        for string in strings:
            if not i18n.isTranslated(string, locale):
                if not localePrinted:
                    print "[%s]" % locale
                    localePrinted = 1
                print string
        if localePrinted:
            print
    
