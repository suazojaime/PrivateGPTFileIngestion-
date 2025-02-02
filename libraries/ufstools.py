import minestar, ufs

logger = minestar.initApp()

def copyTree(sourceDir, destDir, showDetails=0):
    import os, shutil
    "copy a UFS directory tree to a target directory"

    if sourceDir is None:
        return
    minestar.makeDir(destDir)
    files = sourceDir.listFiles()
    for file in files:
        sourceFile = file.getPhysicalFileName()
        destFile = destDir + os.sep + file.getName()
        if showDetails:
            print "copying %s to %s" % (sourceFile,destFile)
        shutil.copy2(sourceFile, destFile)
    subdirs = sourceDir.listSubdirs()
    for subdir in subdirs:
        copyTree(subdir, destDir + os.sep + subdir.getName())

def getLocaleForFile(dir):
    import os
    current = dir
    while not os.path.exists(os.sep.join([current, "extension.xml"])):
         current = os.path.dirname(current)
    id = readIDFromExtensionXml(os.sep.join([current, "extension.xml"]))
    if '-' not in id or id.find('-') > 2:
        return None
    return id[:id.find('-')]

def readIDFromExtensionXml(extXml):
    import mstarext, xml, sys
    f = file(extXml)
    bytes = f.read()
    # try / except / finally is broken until Python 2.5
    try:
        try:
            dom = xml.dom.minidom.parseString(bytes)
            id = dom.documentElement.getAttribute("id")
            return id
        except:
            value = sys.exc_info()[1]
            raise mstarext.ExtensionException("Error in XML file %s: %s" % (extXml, value))
    finally:
        f.close()

