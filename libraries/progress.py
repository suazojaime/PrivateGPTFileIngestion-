# Library for progress monitoring.

import sys, time
import minestar

logger = minestar.initApp()

class ProgressFrame:
    """Progress that has been made in any level of the task
       completedValue is the amount you get towards the total for completing this task
       proportion is the proportion of the parent task that this one represents
    """
    def __init__(self, completedValue, description, proportion):
        self.completedValue = completedValue
        self.description = description
        self.fractionDone = 0.0
        self.proportion = proportion
        self.failure = 0

    def progress(self, fractionDone):
        self.fractionDone = fractionDone

    def progressMade(self):
        return self.completedValue * self.fractionDone

    def progressReport(self):
        return "%s description %f %d" % (self.description, self.fractionDone, self.completedValue)

class FailureProgressFrame:
    """Progress that has been made in any level of the task
       completedValue is the amount you get towards the total for completing this task
       proportion is the proportion of the parent task that this one represents
    """
    def __init__(self, description):
        self.description = description
        self.failure = 1

    def progressReport(self):
        return "FAILURE %s" % self.description

class ProgressFrameStack:
    "Progress that has been made at all levels of the task"
    def __init__(self, completedValue, description, filename):
        self.setFileName(filename)
        self.stack = []
        self.completedValue = completedValue
        self.push(ProgressFrame(completedValue, description, 1.0))

    def push(self, frame):
        self.stack = [frame] + self.stack
        self.reportToFile()

    def pop(self):
        finished = self.stack[0]
        self.stack = self.stack[1:]
        top = self.stack[0]
        top.fractionDone = top.fractionDone + finished.proportion
        if top.fractionDone > 1.0:
            top.fractionDone = 1.0

    def done(self, silent=0):
        "The current task has finished"
        if len(self.stack) > 1:
            self.pop()
        else:
            top = self.stack[0]
            top.fractionDone = 1.0
        if not silent:
            self.reportToFile()
        
    def reportToFile(self):
        if self.filename == "-":
            print self.quickReport()
        elif self.filename is not None:
            file = open(self.filename, "a")
            file.write("%s %s\n" % (self.quickReport(), str(time.ctime())))
            file.close()
    
    def progressAmount(self):
        "Total progress so far"
        total = 0.0
        failure = 0
        for frame in self.stack:
            if frame.failure:
                failure = 1
            else:
                total = total + frame.progressMade()
        if failure:
            total = -total
        return int(total)
        
    def top(self):
        if len(self.stack) == 0:
            return None
        else:
            return self.stack[0]
            
    def fail(self, description):
        self.push(FailureProgressFrame(description))

    def progressReport(self):
        for frame in self.stack:
            print frame.progressReport()
        print "PROGRESS: %d/%d" % (self.progressAmount(), self.completedValue)
        
    def quickReport(self):
        return "%d %d %s" % (self.progressAmount(), self.completedValue, self.stack[0].description)
        
    def setFileName(self, filename):
        self.filename = filename
        if self.filename is not None:
            file = open(self.filename, "w+")
            file.close()

__stack = None
__filename = None

def start(completedValue, description, filename=None):
    "Start monitoring a task"
    global __stack, __filename
    if filename is not None:
        setFileName(filename)
    __stack = ProgressFrameStack(completedValue, description, __filename)

def getProgress():
    "Return (progressSoFar, amountForCompletion)"
    global __stack
    if __stack is None:
        return (0,0)
    else:
        return (__stack.progressAmount(), __stack.completedValue)

def task(proportion, description):
    "Start a new subtask"
    global __stack
    if __stack is None:
        return
    top = __stack.top()
    if top is None:
        raise "task already complete"
    __stack.push(ProgressFrame(int(proportion * top.completedValue), description, proportion))
    
def __done(silent=0):
    global __stack
    if __stack is None:
        return
    __stack.done(silent)

def done():
    "Subtask is completed"
    __done(0)
    
def fail(message):
    "The whole process fails"
    global __stack
    if __stack is None:
        return
    __stack.fail(message)

def nextTask(proportion, description):
    "That subtask was completed, move on to another one"
    __done(1)
    task(proportion, description)

def quickReport():
    "A one line report of how progress is going"
    if __stack is None:
        return "no progress monitoring"
    else:
        return __stack.quickReport()
        
def setFileName(filename):
    "Specify the file to write progress information to"
    global __stack, __filename
    __filename = filename
    if __stack is not None:
        __stack.setFileName(filename)
    
# Test functions
def func1():
    task(0.33, "a")
    #nextTask(0.33, "b")
    nextTask(0.33, "c")
    done()

def func2():
    pass

def func3():
    task(0.33, "x")
    nextTask(0.33, "y")
    nextTask(0.33, "z")
    #raise "it's buggered mate"
    done()

def func():
    global __stack
    task(0.2, "func1")
    func1()
    nextTask(0.3, "func2")
    func2()
    nextTask(0.49, "func3")
    func3()
    done()

if __name__ == "__main__":
    start(1000, "func", "-")
    try:
        func()
        done()
    except:
        fail(sys.exc_info()[0])
        import traceback
        traceback.print_tb(sys.exc_info()[2])
