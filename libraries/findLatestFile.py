import sys, glob, os, stat, time, string
""" findLatestFile.py - finds the most recent file name 
    in the given directory path based on a given Pattern
     - Parameter 1: the Pattern eg. MODELDB_*.ZIP
     - Parameter 2: the directory to search eg. G:\BACKUPS """

if len(sys.argv) == 1:
    pattern = "MODELDB_*.ZIP"
    directory = "."
if len(sys.argv) == 2:
    pattern = sys.argv[1]
    directory = "."
else:
    pattern = sys.argv[1]
    directory = sys.argv[2]

limitInSeconds = 365 * 24 * 3600
files = glob.glob(directory + os.sep + pattern)
for file in files:
    path = file.split(os.sep)
    statInfo = os.stat(file)
    ageInSeconds = time.time() - statInfo[stat.ST_MTIME]
    if ageInSeconds < limitInSeconds:
       newName = path[-1]
       newPath = path[:]
       newPath[-1] = newName
       newFile = string.join(newPath, os.sep)
       limitInSeconds = ageInSeconds
print newFile,
