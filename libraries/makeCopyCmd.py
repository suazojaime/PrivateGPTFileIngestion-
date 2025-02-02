import sys, glob, string
from string import *

""" makeCopyCmd.py: This script takes a file containg a list of filenames as 
    produced by jar.exe and creates a file with a series of 'copy /Y <fileName>' 
    commands. These can then be used as a BATch file to copy the files extracted.
     - Parameter 1: File name containting list of files to be copied
     - Parameter 2: Output file name (BAT) that can be run to copy files"""

if len(sys.argv) != 3:
    print "Usage: makeCopyCmd.py filein.txt fileout.bat"
    print sys.argv
    sys.exit(12)
filein = sys.argv[1]
fileout = sys.argv[2]
file1 = open(filein, "r")
file2 = open(fileout, "w")
lineout = ''
line2 = ''
for line in file1.readlines():
    if line[-1] == '\n':
        line = line[:-1]
    line2 = string.replace(line, '/', '\\')
    lineout = "copy /Y " + line2[10:] + " ."
    file2.write("%s\n" % lineout)
file1.close()
file2.close()
