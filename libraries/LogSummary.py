#!/usr/bin/env python

import sys, os, pickle, glob

def stripEol(line):
    while len(line) > 0 and line[-1] in ['\n', '\r']:
        line = line[:-1]
    return line

def resolveFilenames(dirs):
    matching = []
    for d in dirs:
        if '*' in d:
            files = glob.glob(d)
        elif os.path.isdir(d):
            files = os.listdir(d)
            matching = matching + [ os.sep.join([d, f]) for f in files if f.endswith(".log") ]
        elif os.path.isfile(d):
            matching.append(d)
    return matching

NUMS = "nums"

erasures = [
    ("Slow SQL", [2], 5),
    ("Slow QUERY", [2], 5),
    ("Slow publish", [2], ':'),
    ("Slow hibernate", [], ':'),
    ("EventPersistifier lag:", [2]),
    ("*in report params", [4]),
    ("Load report from machine", [4, 10]),
    ("Cycle jitter correction", [9,10,11,13,14]),
    ("Event took", [2, 8], ":"),
    ("Unable to obtain assignment for truck", [6]),
    ("Unable to assign truck", [4]),
    ("Machine operator event from machine", [5], ":"),
    ("Python node processing time", [], ":"),
    ("Event component creation", [], ":"),
    ("cycle data incomplete - loading tool is null unable", [14]),
    ("cycle data incomplete - loading tool is null", [9]),
    ("cycle data incomplete - source location is null", [9]),
    ("cycle data incomplete - end processor is null", [9]),
    ("cycle data incomplete - end sink location is null", [10]),
    ("cycle data incomplete - material is null", [8]),
    ("Grade determination enabled and no load info for truck", [9]),
    ("No load or dipper info for truck", [7]),
    ("Looks like unmatched loader cycle for", [6], "{"),
    ("Error decoding packet", [3,5]),
    ("Error unmarshalling event info", [], 4),
    ("Will not create lookup column", [6, 9, 12]),
    ("Error caching property value.", [], 4),
    ("End cycle debounce correction", [10, 11, 12, 14, 15]),
    ("Found delay straddling cycle boundary", [], ':'),
    ("Bad event payload received", [], 4),
    ("Publication threshold exceeded", [6]),
    ("Publication Threshold exceeded", [8]),
    ("detected a zero length path", [7], '['),
    ("ECF Event lag", [3]),
    ("Event Machine Position Report took", [5], ':'),
    ("Event Machine Service Hours took", [5], ':'),
    ("Event Machine Operator Response took", [5], ':'),
    ("Event Machine Delay Report took", [5], ':'),
    ("Event Unable to Assign took", [5], ':'),
    ("Event Machine Health Event Deactivate", [5, 7], ':'),
    ("Event Machine Health Event Activate", [5, 7], ':'),
    ("Event Automatic Assignment took", [4], ':'),
    ("Event Manual Assignment took", [4], ':'),
    ("Event Dipper Report took", [4], ':'),
    ("Event Cycle Report took", [4], ':'),
    ("Event Machine Startup took", [4], ':'),
    ("Event Assignment Message took", [4], ':'),
    ("Event Assignment Acknowledge took", [4], ':'),
    ("Event Load Report took", [4], ':'),
    ("Event QueueMonitorUpdate took", [3], ':'),
    ("Event TimeSyncError took", [3], ':'),
    ("Event Acknowledge took", [3], ':'),
    ("Event Re-Assignment took", [3], ':'),
    ("Event Machine Position and State took", [6], ':'),
    ("Event AssignAck took", [3], ':'),
    ("*events are buffered", [0]),
    ("*Assuming empty", [1]),
    ("Error processing child changed", [], ":"),
    ("Error processing entity change", [], ":"),
    ("Error processing", [2,3,4,5,6]),
    ("Exception raising alarm for bad", [], 8),
    ("Exception raising alarm for duplicate", [], 8),
    ("Exception raising alarm for unlicensed", [], 7),
    ("Exception raising alarm for unscheduled", [], 7),
    ("Exception thrown by", [], 5),
    ("Unable to resolve entities returned from", [], 7),
    ("Unable to resolve entities:", [], ":"),
    ("Unable to resolve entity", [4]),
    ("Unknown machine class oid:", [], ":"),
    ("*^^^^", [0, 7]),
    ("Machine operator event received with no valid machine", [8,9,10,11,12]),
    ("Machine operator event received with no valid personnel", [], ':'),
    ("Failed to find a previous loader cycle", [], ':'),
    ("Failed to compute path", [], ':'),
    ("Problem getting alternate material", [11]),
    ("Error saving CycleStateCache", [], "["),
    ("Beep", [1]),
    ("Cannot initialize value", [3,6]),
    ("failed to create cycle ending", [6,7,8,10]),
    ("query against", [2], ":"),
    ("failed to save cycle state", [], '='),
    ("query against BeaconManager failed", [4]),
    ("Publication Threshold exceeded", [8]),
    ("Unable to resolve entities returned from select OID from <table> where id", [14]),
    ("cycle data incomplete - processor", [5], ':'),
    ("*contains extension with id", [1, 6]),
    ("Found delay that", [], ":"),
    ("No match for grade block name", [6,10], ':'),
    ("Thread '", [NUMS], "["),
    ("TAE is not available for action", [6, 9]),
    ("*callbacks for service provider", [2], ":"),
    ("Unable to determine path", [6, 8, 10]),
    ("Last cycle for", [3]),
    ("Activity does not exist", [], '.'),
    ("Found delay from series not returned", [], ':'),
    ("Last cycle is not active", [], ':'),
    ("Load report contains invalid grade", [], ':'),
    ("Looks like unmatched", [], ':'),
    ("No key properties defined", [], ':'),
    ("Problem encountered", [8]),
    ("Truck is loaded", [], ':'),
    ("Assignment failed - timeout", [], ":"),
    ("Python node processing", [], ":"),
    ("Buffered event count is very", [6]),
    ("BufferedNode", [1,3], ":"),
    ("Unable to execute SQL", [], 5),
    ("Took too long", [], ":"),
    ("Error handling shift end", [], ":"),
    ("Publication processing time", [], ":"),
    ("Could not process event", [], ":"),
    ("Too many retries", [], "="),
    ("Error delivering to", [], "="),
    ("Invalid route to", [3], "."),
    ("Invalid route:", [], ":"),
    ("*is being disconnected", [1]),
    ("Abnormal connection termination", [4], "!"),
    ("rid:", [1]),
    ("Looking for OID", [], ":"),
    ("Unable to contact subscriber", [], ":"),
    ("Unable to obtain ordered path", [], ":"),
    ("Failed to get path", [5], ":"),
    ("No fuel bays", [4], ":"),
    ("These entities do not exist", [], ":"),
    ("Unable to monitor fuel", [14]),
    ("*RPC took too long:", [6]),
    ("Server side of", [], ':')
    ]

SLOW = "__slow__"
ERROR = "__error__"
WARNING = "__warning__"

def noCommas(str):
    str = ''.join(str.split(','))
    str = ''.join(str.split('.'))
    return str

def parseInt(s):
    if type(s) == type(0):
        return s
    try:
        return int(noCommas(s))
    except ValueError:
        print s
        return 0

def summarise(filename, counts):
    totalSlow = counts[SLOW]
    totalError = counts[ERROR]
    totalWarning = counts[WARNING]
    vm = filename[:filename.find("_")]
    vm = vm.split(os.sep)[-1]
    for line in file(filename):
        if line.startswith("ERROR:") or line.startswith("WARNING:") or line.startswith("PERFORMANCE:"):
            line = stripEol(line)
            if line.find("Thread") >= 0:
                line = line[:line.rfind("Thread")]
            if line.find("[") >= 0:
                line = line[:line.rfind("[")]
            toks = line.split()
            lineType = toks[0][:-1]
            message = '%s' % (" ".join(toks[4:]))
            toks = message.split()
            if len(toks) > 0 and toks[0] == "Slow":
                if toks[2] == "took":
                    n = parseInt(toks[3])/1000
                else:
                    n = toks[2][:-1]
                totalSlow += parseInt(n)
            for rule in erasures:
                start = rule[0]
                erase = rule[1]
                extra = None
                if len(rule) == 3:
                    extra = rule[2]
                if start.startswith("*"):
                    start = start[1:]
                    match = message.find(start) >= 0
                else:
                    match = message.startswith(start)
                if match:
                    if type(extra) == type(0):
                        message = " ".join(toks[:extra])
                    elif type(extra) == type('a'):
                        message = " ".join(toks)
                        if message.find(extra) >= 0:
                            message = message[:message.find(extra)]
                    else:
                        message = " ".join(toks)
                    toks = message.split()
                    for e in erase:
                        if e == NUMS:
                            for i in range(len(toks)):
                                if toks[i][0] in "0123456789":
                                    toks[i] = "###"
                        elif e < len(toks):
                            toks[e] = "???"
                    message = " ".join(toks)
                    break
            key = (vm, lineType, message)
            count = counts.get(key)
            if count is None:
                count = 1
                if lineType == "ERROR":
                    totalError = totalError + 1
                else:
                    totalWarning = totalWarning + 1
            else:
                count = count + 1
            counts[key] = count
    counts[SLOW] = totalSlow
    counts[ERROR] = totalError
    counts[WARNING] = totalWarning
    return counts

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) < 2:
        print "Usage: LogSummary <file> <dir/file> <dir/file> ..."
        sys.exit(92)
    summaryFile = args[0]
    if summaryFile.endswith(".log"):
        print "Your summary file may not be %s: it might get confused with the real log files" % summaryFile
        print "Try using a .csv file for the summary."
        sys.exit(93)
    if summaryFile.rfind('.') > summaryFile.rfind(os.sep):
        pickleFile = summaryFile[:summaryFile.rfind('.')] + ".pickle"
    else:
        pickleFile = os.path.dirname(summaryFile) + os.sep + "summary.pickle"
    print "Pickle file is %s" % pickleFile
    if os.path.isfile(pickleFile):
        counts = pickle.load(open(pickleFile))
    else:
        counts = { SLOW : 0, ERROR : 0, WARNING : 0 }
    args = args[1:]
    filenames = resolveFilenames(args)
    errorCount = 0
    warningCount = 0
    for f in filenames:
        summarise(f, counts)
    sumFile = file(summaryFile, "w")
    for (k,count) in counts.items():
        if type(k) == type(""):
            sumFile.write('%s, %d\n' % (k, count))
    for mt in ["ERROR", "WARNING", "PERFORMANCE"]:
        mesgs = []
        for (k,count) in counts.items():
            if type(k) == type((1,2,3)) and len(k) == 3:
                (vm, lineType, message) = k
                if mt == lineType:
                    mesgs.append((vm, lineType, message, count))
        mesgs.sort(lambda a,b: cmp(a[2], b[2]))
        for k in mesgs:
            (vm, lineType, message, count) = k
            sumFile.write('"%s", %s, %s, %s\n' % (message.replace(",", " "), lineType, vm, count))
    sumFile.close()
    pickle.dump(counts, open(pickleFile, 'w'))
    print "%d errors, %d warnings, %d seconds slowness" % (counts[ERROR], counts[WARNING], counts[SLOW])
    print "Summary written to %s" % summaryFile
