#! /usr/bin/env python

import minestar

logger = minestar.initApp()

# print md5 checksum for a directory tree

bufsize = 8096
fnfilter = None
rmode = 'r'

usage = """
usage: sum5 [-b] [-t] [-l] [-s bufsize] [directory]
-b        : read files in binary mode
-t        : read files in text mode (default)
-l        : print last pathname component only
-s bufsize: read buffer size (default %d)
directory : pathname of directory, default is current directory
""" % bufsize

import sys
import string
import os
import hashlib
import regsub

StringType = type('')
FileType = type(sys.stdin)

def sum(dir, out, excludeListFile=None):
    allFiles = Walk(dir, 1, '*', 0)
    
    if excludeListFile != None:
        excludeList = loadLinesFromFile(excludeListFile)
    else:
        excludeList = []
    if dir == '.':
        prefixSize = 0
    else:
        prefixSize = len(dir) + 1
    files = Mask(allFiles, prefixSize, excludeList)
    
    sts = 0
    for f in files:
        # Trim the directory name of the title of the file
        title = f[prefixSize:]
        sts = printsum(f, title, out) or sts
    return sts

def printsum(file, title, out = sys.stdout):
    try:
        fp = open(file, rmode)
    except IOError, msg:
        sys.stderr.write('%s: Can\'t open: %s\n' % (title, msg))
        return 1
    if fnfilter:
        file = fnfilter(file)
    sts = printsumfp(fp, file, title, out)
    fp.close()
    return sts

def printsumfp(fp, file, title, out = sys.stdout):
    m = hashlib.md5()
    try:
        while 1:
            data = fp.read(bufsize)
            if not data: break
            m.update(data)
    except IOError, msg:
        sys.stderr.write('%s: I/O error: %s\n' % (title, msg))
        return 1
    out.write('%s %s\n' % (hexify(m.digest()), title))
    return 0

def hexify(s):
    res = ''
    for c in s:
        res = res + '%02x' % ord(c)
    return res

def Walk( root, recurse=0, pattern='*', return_folders=0, excludePatterns=[] ):
    import fnmatch, os, string
    
    # initialize
    result = []

    # must have at least root folder
    try:
        names = os.listdir(root)
    except os.error:
        return result

    # expand pattern
    pattern = pattern or '*'
    pat_list = string.splitfields( pattern , ';' )
        
    # check each file
    for name in names:
        fullname = os.path.normpath(os.path.join(root, name))

        # grab if it matches our pattern and entry type
        for pat in pat_list:
            if fnmatch.fnmatch(name, pat):
                for expat in excludePatterns:
                    if fnmatch.fnmatch(name, expat):
                        break
                if os.path.isfile(fullname) or (return_folders and os.path.isdir(fullname)):
                    result.append(fullname)
                continue
                                
        # recursively scan other folders, appending results
        if recurse:
            if os.path.isdir(fullname) and not os.path.islink(fullname):
                result = result + Walk( fullname, recurse, pattern, return_folders , excludePatterns)
                        
    return result

def Mask(files, prefixSize, excludePatterns):
    import fnmatch, os, string

    result = []
    for f in files:
        name = f[prefixSize:]
        #print "CHECKING %s" % name
        excluded = 0
        for expat in excludePatterns:
            if fnmatch.fnmatch(name, expat):
                #print "EXCLUDING %s" % f
                excluded = 1
                break
        if not excluded:
            result.append(f)
    return result

def loadLinesFromFile(filename):
    '''
    load a file and return its lines, ignoring comments which start with a #
    '''

    # read in the lines
    try:
        inFile = open(filename)
        lines = inFile.readlines()
        inFile.close()
    except IOError, ex:
        raise ex

    realLines = []
    for line in lines:
        if len(line) > 0:
            if line[0] != '#':
                realLines.append(line.strip())
    return realLines

def main(args = sys.argv[1:], out = sys.stdout):
    global fnfilter, rmode, bufsize
    import getopt
    try:
        opts, args = getopt.getopt(args, 'blts:')
    except getopt.error, msg:
        sys.stderr.write('%s: %s\n%s' % (sys.argv[0], msg, usage))
        return 2
    for o, a in opts:
        if o == '-l':
            fnfilter = os.path.basename
        if o == '-b':
            rmode = 'rb'
        if o == '-t':
            rmode = 'r'
        if o == '-s':
            bufsize = string.atoi(a)
    if not args:
        args = ['.']
    return sum(args[0], out, 'CHECKSUMS.SKIP')

if __name__ == '__main__' or __name__ == sys.argv[0]:
    sys.exit(main(sys.argv[1:], sys.stdout))
