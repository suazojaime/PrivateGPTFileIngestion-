import glob
import os
import stat
import string
import sys
import time

import minestar
import mstardebug

logger = minestar.initApp()

# List of filenames that are never marked
NEVER_MARK_FILENAMES = ["readme.txt"]

# List of subdirectories that are never marked
NEVER_MARK_SUBDIRS = ["edge-adapter"]

# The default prefix to mark old files
MARKED_FOR_DELETION = "_MARKED_FOR_DELETION_"

# The default limit in days
DEFAULT_LIMIT_DAYS = 5


def addPrefix(pattern, directory, limitInDays=DEFAULT_LIMIT_DAYS, prefix=MARKED_FOR_DELETION, recursive=0):
    """returns the number of files marked for deletion"""
    files = glob.glob(directory + os.sep + pattern)
    count = 0
    for file in files:
        if markOldFileWithPrefix(file, limitInDays, prefix):
            count += 1

    # recurse if requested
    if recursive:
        for file in os.listdir(directory):
            path = directory + os.sep + file
            if minestar.isDirectory(path):
                count += addPrefix(pattern, path, limitInDays, prefix, recursive)

    return count


def retainRecentAddPrefix(pattern, directory, minNumFiles=1, limitInDays=DEFAULT_LIMIT_DAYS, prefix=MARKED_FOR_DELETION,
                          recursive=0):
    import re
    files = glob.glob(directory + os.sep + pattern)
    prefixToFile = {}
    count = 0
    # group files according to prefix
    for file in files:
        path = file.split(os.sep)
        r = re.search('[a-zA-Z]*', path[-1])
        group = r.group(0)

        if group in prefixToFile:
            files = prefixToFile[group]
        else:
            files = []

        files.append(file)
        prefixToFile[group] = files

    # sort each group according to date
    for group in prefixToFile:
        files = prefixToFile[group]
        if len(files) == 1:
            continue
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        # except first n files, mark every other file if age > limit
        n = minNumFiles
        for i in range(n, len(files)):
            if markOldFileWithPrefix(files[i], limitInDays, prefix):
                count += 1

    # recurse if requested
    if recursive:
        for file in os.listdir(directory):
            path = directory + os.sep + file
            if minestar.isDirectory(path):
                count += retainRecentAddPrefix(pattern, path, minNumFiles, limitInDays, prefix, recursive)
    return count


def markOldFileWithPrefix(file, limitInDays=DEFAULT_LIMIT_DAYS, prefix=MARKED_FOR_DELETION):
    """Rename the file with the given prefix if it is older than the given limit.  Return True if the file was renamed"""
    path = file.split(os.sep)
    subdir = path[-2]
    filename = path[-1]

    if subdir in NEVER_MARK_SUBDIRS:
        # subdir is excluded
        if mstardebug.debug:
            logger.info("%s is in an excluded subdirectory" % file)
        return False

    if filename in NEVER_MARK_FILENAMES:
        # File is excluded
        if mstardebug.debug:
            logger.info("%s has an excluded filename" % file)
        return False

    if filename.startswith(prefix):
        # Already marked with the prefix
        return False

    try:
        statInfo = os.stat(file)
    except OSError as err:
        logger.warn("failed to get file information for %s - %s" % (file, err))
        return False

    ageInSeconds = time.time() - statInfo[stat.ST_MTIME]
    limitInSeconds = limitInDays * 24 * 3600
    if ageInSeconds > limitInSeconds:
        newName = prefix + filename
        newPath = path[:]
        newPath[-1] = newName
        newFile = string.join(newPath, os.sep)
        try:
            os.rename(file, newFile)
            logger.info("marked %s" % file)
            return True
        except OSError as err:
            logger.warn("failed to mark %s - %s" % (file, err))
    else:
        if mstardebug.debug:
            logger.info("%s is not ready for cleanup" % file)

    return False


def main():
    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    else:
        pattern = "*.null"
    if len(sys.argv) > 2:
        directory = sys.argv[2]
    else:
        directory = "."
    if len(sys.argv) > 3:
        limit = int(sys.argv[3])
    else:
        limit = DEFAULT_LIMIT_DAYS
    if len(sys.argv) > 4:
        prefix = sys.argv[4]
    else:
        prefix = MARKED_FOR_DELETION
    print("Pattern is %s" % pattern)
    print("Directory is %s" % directory)
    print("Limit is %s" % limit)
    print("Prefix is %s" % prefix)
    addPrefix(pattern, directory, limit, prefix)


if __name__ == "__main__":
    main()
