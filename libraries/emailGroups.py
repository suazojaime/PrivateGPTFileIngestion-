# support for groups of email addresses
import mstarpaths, minestar

logger = minestar.initApp()

initialised = 0
groups = {}

def __init():
    global initialised, groups
    if initialised:
        return
    initialised = 1
    groupFile = "{MSTAR_HOME}/bus/mstarrun/emailGroups.properties"
    groupFile = mstarpaths.interpretPath(groupFile)
    lines = minestar.readLines(groupFile)
    groups = {}
    for line in lines:
        fields = line.split("=")
        name = fields[0].strip()
        fields = fields[1].split(",")
        names = []
        for field in fields:
            moreFields = field.strip().split()
            for mf in moreFields:
                names.append(mf.strip())
        groups[name] = names

def __getGroup(name, groupsDone, accum):
    __init()
    names = groups.get(name)
    if not names:
        return
    for n in names:
        if n.find("@") >= 0:
            if n not in accum:
                accum.append(n)
        else:
            # group
            group = n
            if group not in groupsDone:
                groupsDone.append(group)
                __getGroup(group, groupsDone, accum)

def getGroup(name):
    accum = []
    __getGroup(name, [name], accum)
    return accum


if __name__ == "__main__":
    import sys
    print `getGroup(sys.argv[1])`
