import zipfile, sys, os, string, glob
import minestar

logger = minestar.initApp()

def recursiveFileList(base, directory):
    directory = os.path.normpath(directory)
    result = []
    files = os.listdir(directory)
    for file in files:
        path = directory + os.sep + file
        if os.path.isdir(path):
            result = result + recursiveFileList(base, path)
        else:
            relpath = path[len(base) + 1:]
            result.append(relpath)
    return result

zipFileName = sys.argv[1]
filesToZip = sys.argv[2]
zf = zipfile.ZipFile(zipFileName, "w", zipfile.ZIP_DEFLATED)
#
# work out if 'fileToZip' is a pattern
#
if (string.find(filesToZip, "*") != -1 or string.find(filesToZip, "?") != -1):
    #
    # it's a pattern
    #
    for file in glob.glob(filesToZip):
        zf.write(file, file)
else:
    #
    # it's a file or directory
    #
    for file in sys.argv[2:]:
        if os.path.isdir(file):
            base = os.path.split(file)[1]
            rfl = recursiveFileList(file, file)
            for f in rfl:
                p = os.path.normpath(file + os.sep + f)
                zf.write(p, base + os.sep + f)
        else:
            zf.write(file, file)
zf.close()
