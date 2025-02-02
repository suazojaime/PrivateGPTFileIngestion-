__version__ = "$Revision: 1.1 $"

import os, sys, csv
import minestar

logger = minestar.initApp()


def viewPhraseBookInfo(filename):
    (totals,translatedCounts) = getStats(filename)
    showStats(totals, translatedCounts)

def getStats(filename):
    "returns a tuple of (count,translated) where each item is a dictionary of type to the count for that type"

    # Open the file and skip the header record
    file = open(filename, "rb")
    reader = csv.DictReader(file, delimiter='\t')
    reader.next()

    # Process the file keeping some history for error reporting if required    
    totals = {}
    translatedCounts = {}
    context = ''
    text = ''
    try:
        for row in reader:
            context = row['Context']
            type = _getType(context)
            if totals.has_key(type):
                totals[type] += 1
            else:
                totals[type] = 1
                translatedCounts[type] = 0
            text = row['Text']
            translation = row.get('Translation')
            if translation != None and len(translation.strip()) > 0:
                translatedCounts[type] += 1
    except:
        print "ERROR reading file - last good row ...\n%s\t%s" % (context,text)
    file.close()
    return (totals,translatedCounts)

def _getType(context):
    sep = context.find('.')
    if (sep > 0):
        return context[:sep]
    else:
        return context

def showStats(totals, translatedCounts):
    types = totals.keys()
    types.sort()
    allTotal = 0
    allTrans = 0
    for type in types:
        total = totals[type]
        trans = translatedCounts[type]
        allTotal += total
        allTrans += trans
        showStat(type,trans,total)
    showStat('ALL',allTrans,allTotal)

def showStat(type,trans,total):
    percent = (trans * 100.0)/total
    print "%-12s = %5.2f%% translated (%d of %d)" % (type,percent,trans,total)


# Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = []
    argumentsStr = "file"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Load the overrides files and compare them
    viewPhraseBookInfo(args[0])
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
