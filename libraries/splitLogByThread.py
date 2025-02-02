import sys, os, string, types, cgi, zipfile, datetime, re, minestar, time, stat

# Given a log file or trace file, split the file into multiple files (in a new sub directory) based on the
# thread id of the process that wrote the log entry.

def _split_logs(logfile, dayttime):

    # Look for a match on : mmm dd hh:mm:ss [nnnn] where nnnn is the thread id.
    pattern=re.compile("([a-zA-Z]{3}) (\d{2}) (\d{2}:\d{2}:\d{2}) \[(\d+)\]")

    # To keep the file handle open for commonly used files
    threadfiles  = dict()

    # Keep track of number of times we write to a file
    threadwrites = dict()

    if not minestar.isDirectory(dayttime):
        minestar.makeDir(dayttime)

    with open(logfile) as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                thread_id = match.group(4)
                if thread_id.isdigit():
                    try:
                        _filepath = dayttime + "/" + thread_id + ".log"
                        threadfiles, threadwrites = _write_log(thread_id, line, _filepath, threadfiles, threadwrites)
                    except:
                        print "Error : occured writing line : " + line
                        print "Error : " + str(sys.exc_info())
                        sys.exit(1)

    print logfile + " split into " + str(len(threadwrites)) + " files in folder " + dayttime

def _write_log(thread_id, line, _filepath, threads, threadwrites):

    # Open the file in append mode and put the file handle into a dictionary for possible reuse.
    threads.setdefault(thread_id, open(_filepath, "a"))
    threads[thread_id].write(line)

    # Keep a note of how many times this thread file has been written to.
    threadwrites.setdefault(thread_id, 0)
    threadwrites[thread_id] = threadwrites[thread_id] + 1

    # Close any files that have less than 50 writes to them to prevent too many open files exception.
    if threadwrites[thread_id] < 50:
        threads[thread_id].close()
        del threads[thread_id]

    return threads, threadwrites

## Main Program ##

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) != 1:
        print ("usage:")
        print ("  splitLogByThread xxxx    - Split the specified logfile into multiple files named by the thread id")
        sys.exit(0)

    now = datetime.datetime.now()
    dayttime = now.strftime("%Y%m%d%H%M%S")

    logfile = args[0]
    if not os.path.exists(logfile):
        print (logfile + " does not exist")
        sys.exit(0)

    _split_logs(logfile, dayttime)

