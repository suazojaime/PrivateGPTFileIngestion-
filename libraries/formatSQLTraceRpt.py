import sys, glob, os
from string import *
""" formatSQLTraceRpt.py: Formats an TKPROF.EXE created SQL Trace report file
                          to isolate slow SQL commands and write these to file.
                          Main procedure 'findSlowSQLInTrace()' uses the third
                          parameter, SecondsPerSQLOperation, to provide a threshold
                          above which SQL commands are deemed SLOW and written to file.
     - Parameter 1: Formated SQL Trace file name produced by TKPROF.EXE
     - Parameter 2: SLOW_SQL report file name output file
     - Parameter 3: Threshold Seconds Per SQL Opertion
"""
#
# Procedure to read file and ignore lines
#     until a specified character is found in column 1.
# Returns the number of lines read.
#
def readLinesIgnoreUntilString(infile, in_string):
    import string
    global finished
    in_line = ''
    localCount = 0
    found = 0
    findIdx = -1
    while found == 0:
        in_line = infile.readline()
        if in_line == '':
           finished = 1
           break
        localCount = localCount + 1
        findIdx = in_line.startswith(in_string)
        if findIdx != -1:
            found = 1
            break
    return localCount
#
# Procedure to read file into Buffer
#     until a specified character is found in column 1.
# Returns the number of lines read.
#
def readLinesIntoBufferUntilString(infile, in_string, inBuffer):
    import string
    global finished
    in_line = ''
    strLenght = len(in_string)
    inBuffer = []
    lineCount = 0
    found = 0
    findIdx = -1
    while found == 0:
        in_line = infile.readline()
        if in_line == '':
           finished = 1
           break
        lineCount = lineCount + 1
#        print "Reading line to add to Buffer:> %s" % in_line
        inBuffer.append(in_line[:-1])
        findIdx = string.find(in_line, in_string, 0)
        if findIdx == 0:
#            print "Found string %s in line %s!\n" % (in_string, in_line)
            found = 1
            break
    return inBuffer
#
# This Procedure writes out lines containted in the Buffer
#
def writeBufferToFile(outFile, outBuffer):
    line = ''
    outCount = 0
    for line in outBuffer:
       outFile.write("%s\n" % line)
       outCount = outCount + 1
    return outCount

def ExecIsSlow(inLine, threshPerOperation):
#
# Initialize varialbes:
#
    inTotal = ''
    inTotal = inLine[0]
    if inTotal == '': return 0
    isSlow = 0
    strOpers = ''
    Opers = 0
    strCPU = ''
    CPUSecs = 0.0
    strElapsed = ''
    Elapsed = 0.0
    strDisk = ''
    DiskRead = 0
    strQuery = ''
    Queries = 0
    strCurr = ''
    Current = 0
    strRows = ''
    Rows = 0
#
# Split total line into it's components:
#
    strOpers = inTotal[6:14]
    strCPU = inTotal[15:24]
    strElapsed = inTotal[25:35]
    strDisk = inTotal[36:46]
    strQuery = inTotal[47:57]
    strCurr = inTotal[58:68]
    strRows = inTotal[69:80]
#    print "Total: %6s  %8s %10s %10s %10s %10s  %10s." % (strOpers, strCPU, strElapsed, strDisk, strQuery, strCurr, strRows)
#
# Convert to numerical values:
#
    Opers = int(strOpers)
    CPUSecs = float(strCPU)
    Elapsed = float(strElapsed)
    DiskRead = int(strDisk)
    Queries = int(strQuery)
    Current = int(strCurr)
    Rows = int(strRows)

#    print "Total: %6d  %5.2f %7.2f %10d %10d %10d  %10d." % (Opers, CPUSecs, Elapsed, DiskRead, Queries, Current, Rows)

    if (Opers > 0):
        if (Elapsed / Opers) > threshPerOperation:
            isSlow = 1
    return isSlow
#
# Boolean function to determine if a string is a valid number:
#
def isNumber(inStr):
    astring = s.strip()
    astring = astring.replace('.', '')
    astring = astring.replace(' ', '')
    return astring.isdigit()
#
# Main Proc:
#
def findSlowSQLInTrace(filein, fileout, secsPerOper):
    print "\nProcessing SQL Trace File %s into file %s !\n" % (filein, fileout)
    file1 = open(filein, "r")
    file2 = open(fileout, "w")
    total_line = ''
    lineout = ''
    line  = ''
    in_count = 0
    outcount = 0
    this_count = 0
    lineBuff = []
    slowSQL = 0
    countSlow = 0
    global finished
    finished = 0
#
# Main Processsing:
#
# 1. Read up to the first two '***' lines and ignore!
#
    in_count = readLinesIgnoreUntilString(file1, '*****')
    in_count = in_count + readLinesIgnoreUntilString(file1, '*****')
    while finished == 0:
        lineBuff = readLinesIntoBufferUntilString(file1, 'total ', lineBuff)
        if (lineBuff == []) or (lineBuff == ['']):
            break
        total_line = lineBuff[-1:]
#        print total_line
        slowSQL = ExecIsSlow(total_line, secsPerOper)
        if slowSQL == 1:
           countSlow = countSlow + 1
           file2.write("\n Slow SQL No. %d found:" % countSlow)
           file2.write("\n **********************\n\n")
           outcount = outcount + writeBufferToFile(file2, lineBuff)
        in_count = in_count + readLinesIgnoreUntilString(file1, '*****')
#
# Ending Messages:
#
    print " Total lines read: %d !" % in_count
    print " Total lines written %d !" % outcount
    if countSlow > 0:
       print "\nFound %d slow SQL statement(s)! Please review file %s" % (countSlow, fileout)
    else:
       print"\nFound NO SQL statements in the Trace file that exceed elapsed Threshold of %2.2f Seconds per Operation !" % secsPerOper
    file1.close()
    file2.close()

if __name__ == '__main__':
#
# Check Params:
#
    if len(sys.argv) < 3:
       print "Usage: formatSQLTraceRpt.py Trace_File.trc.log SLOW_SQL_Report.lst SecondsPerSQLOperation (Optional)"
       print sys.argv
       sys.exit(12)
#    print sys.argv
    thisfilein = sys.argv[1]
    thisfileout = sys.argv[2]
    if len(sys.argv) > 3:
        ThreshPerOperation = float(sys.argv[3])
    else:
        ThreshPerOperation = 1
    findSlowSQLInTrace(thisfilein, thisfileout, ThreshPerOperation)
