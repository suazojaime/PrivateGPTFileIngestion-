import string

import os
import sys


def isSubdirectory(childDir, parentDir):

    """ Determine if first directory is a subdirectory of the second directory. """

   # See: http://stackoverflow.com/questions/3812849/how-to-check-whether-a-directory-is-a-sub-directory-of-another-directory

    def splitPath(path):
        parts = []
        while True:
            (newPath, tail) = os.path.split(path)
            if newPath == path:
                if path:
                    parts.append(path)
                break
            parts.append(tail)
            path = newPath
        parts.reverse()
        return parts

    def normalizedParts(path):
        return splitPath(os.path.realpath(os.path.abspath(os.path.normpath(path))))

    # Check if directories are the same.
    if childDir == parentDir:
        return True

    # Split each directory into normalized parts.
    childDirParts = normalizedParts(childDir)
    parentDirParts = normalizedParts(parentDir)

    # Parent cannot have more parts than child.
    if len(parentDirParts) > len(childDirParts):
        return False

    # Zip along parts while same, expect child parts to exhaust first.
    return all(x == y for (x, y) in zip(childDirParts, parentDirParts))


# TODO can use os.path.* operations here now?
def simplifyPath(path):
    """ Simplify a path by replacing '/' and '\' with platform-dependent separators, removing '..', etc. """
    # change '/' and '\' to platform-dependent separators
    if os.sep == '\\':
        # MSTAR-2941 Windows - preserve command line flags such as "/c".
        for i in range(len(path)):
            if path[i] == '/':
                if i > 0 and path[i-1] == ' ' and (len(path) <= i+2 or path[i+2] == ' '):
                    # looks like a command line flag
                    pass
                else:
                    path = path[:i] + os.sep + path[i+1:]
    else:
        path = os.sep.join(path.split('/'))
    path = os.sep.join(string.split(path, '\\'))
    # change '..' to platform-dependent parent directory
    path = os.pardir.join(string.split(path, '..'))
    # resolve parent directories if possible
    components = path.split(os.sep)
    components = [ components[x] for x in range(len(components)) if x == 0 or components[x] != '' ]
    try:
        p = components.index(os.pardir)
        while p > 0:
            components[p-1:p+1] = []
            p = components.index(os.pardir)
    except ValueError:
        pass
    path = os.sep.join(components)
    # Check for path representing a Windows drive, e.g. "D:" must be changed to "D:\".
    if len(path) > 1 and path[-1] == ':' and os.sep == '\\':
        path += '\\'
    return path


def which(program):
    """
    Finds a program on the path.

    :param program: the program to find on the path. May be specified as 'java' or 'java.exe'
    """
    extensions = ['', '.exe', '.bat', '.cmd'] if sys.platform.startswith('win32') else ['']

    def executable(f):
        for extension in extensions:
            binary = f + extension
            if os.path.isfile(binary) and os.access(binary, os.X_OK):
                return True
        return False

    for path in os.environ['PATH'].split(os.pathsep):
        p = os.path.join(path, program)
        if executable(p):
            return p

    return None

def dotExe():
    """ Get the extension for executable binaries ('.exe' on windows; '' on other platforms). """
    import sys
    return '.exe' if sys.platform.startswith('win') else ''


def removeDuplicatePaths(paths):
    """ Remove duplicates from a collection of paths. """
    result = []
    uppers = []

    for path in paths:
        pathUpper = os.path.abspath(path).upper()
        if not pathUpper in uppers:
            result.append(path)
            uppers.append(pathUpper)

    return result


def removePath(paths, path, recursive=False):
    # Remove a path from a collection of paths.
    result = []

    targetPath = os.path.abspath(path).upper()

    def matchingPath(p):
        p = os.path.abspath(p).upper()
        if recursive:
            return isSubdirectory(p, targetPath)
        else:
            return p == targetPath

    for path in paths:
        if not matchingPath(path):
            result.append(path)

    return result


def prependPaths(existingPaths, newPaths=[]):
    """ Prepend the new paths before the existing paths. """
    result = []
    for path in newPaths:
        result.append(path)
    for path in existingPaths:
        result.append(path)
    return result


def appendPaths(existingPaths, newPaths=[]):
    """ Append the new paths after the existing paths. """
    result = []
    for path in existingPaths:
        result.append(path)
    for path in newPaths:
        result.append(path)
    return result
