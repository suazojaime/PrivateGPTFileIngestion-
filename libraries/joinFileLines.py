import sys, glob
from string import *

""" joinFileLines.py: This script takes a file containg a list strings and 
    creates an output with all strings joined on a single line 
     - Parameter 1: the input filename
     - Parameter 2: the output file name. """

if len(sys.argv) != 3:
    print "Usage: joinFileLines.py filein fileout"
    print sys.argv
    sys.exit(12)
filein = sys.argv[1]
fileout = sys.argv[2]
file1 = open(filein, "r")
file2 = open(fileout, "w")
lineout = ''
for line in file1.readlines():
    if line[-1] == '\n':
        line = line[:-1]
    if line.strip() != '':
      lineout = lineout + line
file2.write("%s\n" % lineout)
file1.close()
file2.close()
