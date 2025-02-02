#!/usr/bin/env python

import zipfile, sys, os, mstarpaths

mstarpaths.loadMineStarConfig()
TEMP = mstarpaths.interpretPath("{MSTAR_TEMP}/diff/result")
JAD = "jad -f -nonlb -d %s -s %s -o %s"

javap = mstarpaths.java
javap = javap[:javap.rfind(os.sep)]
javap = mstarpaths.interpretPath("%s/javap{EXE}" % javap)
JAVAP = "%s -s -private -verbose -classpath %s %s"

DIFF = "diff %s %s"

useJad = 1
ret = os.system(mstarpaths.interpretFormat("jad{EXE}"))
if ret != 256:
    print "Unable to run jad - decompiling won't happen"
    useJad = 0

def stripEol(line):
    while len(line) > 0 and line[-1] in ['\n', '\r']:
        line = line[:-1]
    return line

def systemEvalRaw(command):
    "Execute the command and return all lines of output"
    import popen2
    stdout = popen2.popen3(command)[0]
    output = stdout.readlines()
    stdout.close()
    result = []
    for line in output:
        result.append(stripEol(line))
    return result

def javap(filename, resultFileName):
    classname = filename.replace("/", ".")[:-6]
    cmd = JAVAP % (javap, TEMP, classname)
    result = systemEvalRaw(cmd)
    f = open(resultFileName, "w")
    for line in result:
        f.write("%s\n" % line)
    f.close()

def diff(file1, file2, resultFileName):
    makeDirsFor(resultFileName)
    cmd = DIFF % (file1, file2)
    result = systemEvalRaw(cmd)
    f = open(resultFileName, "w")
    for line in result:
        f.write("%s\n" % line)
    f.close()
    return result

def jad(classfile, ext):
    directory = classfile[:classfile.rfind("/")]
    cmd = JAD % (directory, ext, classfile)
    os.system(cmd)
    return classfile[:-6] + "." + ext

def makeDirsFor(filename):
    "We are going to create filename, so create the directories that it needs."
    filename = filename.replace("\\", "/")
    parts = filename.split("/")
    dirs = os.sep.join(parts[:-1])
    try:
        os.makedirs(dirs)
    except OSError:
        # already exists
        pass

def writeBytes(bytes, filename):
    makeDirsFor(filename)
    cf = open(filename, "wb")
    cf.write(bytes)
    cf.close()

def dumpDiffSummary(filename, diffs):
    f = open(filename, "w")
    for (name, output, real1, real2) in diffs:
        f.write("%s - %s VS %s\n" % (name, real1, real2))
        for o in output:
            f.write("    %s\n" % o)
        f.write("\n")
    f.close()

def main(appConfig=None):
    difffile1 = zipfile.ZipFile(sys.argv[1])
    difffile2 = zipfile.ZipFile(sys.argv[2])
    manifestText1 = difffile1.read("localManifest.txt")
    manifestText2 = difffile2.read("localManifest.txt")
    import checkBuildManifest
    manifest1 = checkBuildManifest.loadBuildManifestFromString(manifestText1)
    manifest2 = checkBuildManifest.loadBuildManifestFromString(manifestText2)
    print len(manifest1), len(manifest2)
    import minestar
    minestar.rmdir(TEMP)
    diffSummary = []
    for name in difffile1.namelist():
        if name == "localManifest.txt":
            continue
        print "Processing %s" % name
        base = name[name.find('/'):]
        if name.startswith("text"):
            key = "text:" + base
        elif name.startswith("file"):
            key = "file:" + base
        else:
            key = "class:" + base[1:]
        #key = name[:name.find('/')] + ":" + name[name.find('/'):]
        realfile1 = manifest1[key][1]
        realfile2 = manifest2[key][1]
        bytes1 = difffile1.read(name)
        try:
            bytes2 = difffile2.read(name)
        except KeyError:
            print "------- FILE %s NOT IN %s" % (name, sys.argv[1])
        if name.startswith("class/"):
            classfile = TEMP + os.sep + name
            writeBytes(bytes1, classfile)
            javap1 = classfile[:-6] + ".javap1"
            javap(name, javap1)
            if useJad:
                jad1 = jad(classfile, "jad1")
            writeBytes(bytes2, classfile)
            javap2 = classfile[:-6] + ".javap2"
            javap(name, javap2)
            if useJad:
                jad2 = jad(classfile, "jad2")
            difffile = classfile[:-6] + ".diff"
            output = diff(javap1, javap2, difffile)
            diffSummary.append((name,output,realfile1,realfile2))
            if useJad:
                jaddifffile = classfile[:-6] + "_jad.diff"
                output = diff(jad1, jad2, jaddifffile)
                diffSummary.append((name,output,realfile1,realfile2))
        else:
            f1 = TEMP + "/" + name + ".1"
            writeBytes(bytes1, f1)
            f2 = TEMP + "/" + name + ".2"
            writeBytes(bytes2, f2)
            difffile = TEMP + "/" + name + ".diff"
            output = diff(f1, f2, difffile)
            diffSummary.append((name,output,realfile1,realfile2))
    dumpDiffSummary(TEMP + os.sep + "diffSummary.txt", diffSummary)

if __name__ == '__main__':
    main()
        
