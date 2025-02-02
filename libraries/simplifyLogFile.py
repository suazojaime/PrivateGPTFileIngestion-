import sys
import minestar

logger = minestar.initApp()

counts = {}

def count(key):
    global counts
    if not counts.has_key(key):
        counts[key] = 0
    counts[key] = counts[key] + 1
    
def parseNumber(token):
    token = "".join(token.split(","))
    return int(token)
    
FAKE_TOKS = [ None ] * 10

file = open(sys.argv[1])
eat = 0
print "------------------------------------------------------------------------------------------"
for line in file:
    if eat > 0:
        eat = eat - 1
        continue
    if line[-1] == "\n":
        line = line[:-1]
    toks = line.split() + FAKE_TOKS
    if toks[0] == "INFO:":
        if toks[4] == "Speedo:":
            count("Speedo")
            continue
        if toks[4] == "Assignment" and toks[5] == "succeeded:":
            count("Assignment succeeded")
            continue
        if toks[4] == "Attempt" and toks[7] == "duplicate":
            count("Attempt to create duplicate event")
            continue
        if toks[4] == "Mobile" and toks[6] == "Automatically":
            count("Mobile Delay Automatically Terminated")
            continue
        if toks[4] == "Invalid" and toks[5] == "waypoint":
            count("Invalid waypoint description")
            continue
        if toks[4] == "Started" and toks[5] == "manager":
            continue
        if toks[4] == "dCon" and toks[5] == "ID":
            continue
        if toks[8] == "IP" and toks[9] == "address":
            continue
        if toks[5] == "Waypoint" and toks[6] == "Update":
            continue
        if toks[4] == "NotifyProducer.subscription_change":
            continue
        if toks[7] == "current" and toks[8] == "login":
            count("Could not find current login for machine")
            continue
    elif toks[0] == "PERFORMANCE:":
        if toks[4] == "Slow" and (toks[5] in ["SQL", "publish", "QUERY"]):
            count("Slow " + toks[5])
            continue
        if toks[5] == "threshold" and toks[6] == "exceeded:":
            count("Publication threshold exceeded")
            continue
        if toks[5] == "queue" and toks[6] == "watchdog":
            size = parseNumber(toks[10])
            if size < 100:
                continue
            else:
                count("dCon queue watchdog")
        try:
            tookIndex = toks.index("took")
            if tookIndex >= 0 and toks[tookIndex+2] == "seconds" and toks[tookIndex+5] == "processed:":
                count("slow event processing")
                continue
        except ValueError:
            pass
    elif toks[0] == "ERROR:":
        if toks[4] == "Problem" and toks[5] == "checking" and toks[6] == "Material":
            count("Problem checking material")
            continue
        elif toks[4] == "[ArrivalTimeMonitor]":
            count("ArrivalTimeMonitor")
            continue
        elif toks[7] == "Entity.Machine.location" and toks[11] == "resolved:":
            count("machine locations not resolved")
            continue
        elif toks[7] == "Entity.Machine.currentRoad" and toks[11] == "resolved:":
            count("current road not resolved")
            continue
        elif toks[7] == "Entity.Machine.fromDestination" and toks[11] == "resolved:":
            count("from destinations not resolved")
            continue
    elif toks[0] == "WARNING:":
        if toks[4] == "Assignment" and toks[5] == "failed":
            count("Assignment failed")
            continue
        if toks[4] == "detected" and toks[6] == "zero":
            count("detected a zero length path")
            continue
    elif toks[2] == "Handoff" and toks[5] == "pubsub":
        count("Handoff event to pubsub")
        eat = 1
        continue
    elif toks[0] == "THROWABLE:":
        if toks[9] == "sendAssignment" and toks[13] == "timeout":
            count("Timeout in sendAssignment")
            continue
        if toks[1] == "java.lang.OutOfMemoryError":
            count("out of memory error")
            continue
        if toks[1] == "com.mincom.works.cc.route.InvalidRouteException:":
            count("Invalid Route Exception")
            continue
    elif toks[0] in ["at", "STACKTRACE:", "<<"]:
        continue
    elif len(line.strip()) == 0 or line.startswith("*"):
        continue
    print line
print
for (key, value) in counts.items():
    print key, value
