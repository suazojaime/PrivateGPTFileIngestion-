import sys, string, os, time
from Tkinter import *
import minestar

logger = minestar.initApp()

WIDTHS = [800, 1100, 1600, 3000]
WIDTH = 1100
HEIGHT = 650
EFFECTIVE_HEIGHT = HEIGHT - 20
PWIDTH = 4
FONT_SIZE = 12

LAG_TOP = 20
LAG_BOTTOM = 70
LAG_ROW_HEIGHT = 10

class DataPoint:
    def __init__(self, used, total, keph, buf, t, bugs, errors, warnings, perfs, lag, restart, kills, threshold, lagEvents, pageOpens, ecflag, slowPublish, slowSql, threads, cpu):
        self.used = used
        self.total = total
        self.keph = keph
        self.buf = buf
        self.timestamp = t
        self.bugs = bugs
        self.errors = errors
        self.warnings = warnings
        self.perfs = perfs
        self.lag = lag
        self.restart = restart
        self.kills = kills
        self.threshold = threshold
        self.lagEvents = lagEvents
        self.pageOpens = pageOpens
        self.ecflag = ecflag
        self.slowPublish = slowPublish
        self.slowSql = slowSql
        self.threads = threads
        self.cpu = cpu

    def __repr__(self):
        return "(%d,%d,%d,%d)" % (self.used, self.total, self.keph, self.buf)

def noCommas(str):
    str = noCommasDouble(str)
    str = ''.join(str.split('.'))
    return str

def noCommasDouble(str):
    str = ''.join(str.split(','))
    str = ''.join(str.split('+'))
    str = ''.join(str.split('%'))
    return str

def parseInt(s):
    try:
        return int(noCommas(s))
    except ValueError:
        print "CANNOT PARSE", s
        return 0

def parseTime(timestamp):
    y = time.localtime()[0]
    return time.strptime("%d " % y + timestamp, "%Y %b %d %H:%M:%S")

def getData(filename):
    file = open(filename)
    lines = file.readlines()
    data = []
    bugs = 0
    errors = 0
    warnings = 0
    restart = 0
    perfs = 0
    lag = 0
    ecflag = 0
    kills = 0
    threshold = 0
    lagEvents = 0
    pageOpens = 0
    slowPublish = 0
    slowSql = 0
    threads = 0
    cpu = 0
    for line in lines:
        try:
            if line.startswith("ERROR:"):
                errors = errors + 1
            elif line.startswith("BUG:"):
                bugs = bugs + 1
            elif line.startswith("WARNING:"):
                warnings = warnings + 1
            elif line.startswith("PERFORMANCE:"):
                if line.find("Publication threshold exceeded:") >= 0:
                    threshold = threshold + 1
                elif line.find("Event took") >= 0:
                    lagEvents = lagEvents + 1
                    fields = line.split()
                    if fields[6].endswith("+"):
                        # 1.3.0.1
                        v = parseInt(fields[6])
                    else:
                        # 1.3.0.2
                        v = parseInt(fields[11]) / 1000
                    if v > lag:
                        lag = v
                elif line.find("ECF Event lag") >= 0:
                    v = parseInt(line.split()[7])
                    if v > ecflag:
                        ecflag = v
                elif line.find("Slow publish") >= 0:
                    s = line.split()[6][:-1]
                    v = parseInt(s)
                    if v > slowPublish:
                        slowPublish = v
                elif line.find("Slow SQL") >= 0 or line.find("Slow QUERY") >= 0:
                    s = line.split()[6][:-1]
                    v = parseInt(s)
                    if v > slowSql:
                        slowSql = v
                else:
                    perfs = perfs + 1
            elif line.find("Kill supplier") >= 0:
                kills = kills + 1
            elif line.find("Sun Microsystems") >= 0 or line.find("Enterprise Explorer") >= 0:
                restart = 1
            elif line.find("Opening page") >= 0:
                pageOpens = pageOpens+1
            elif line.find("Speedo:") >= 0:
                if line[-1] == '\n':
                    line = line[:-1]
                try:
                    if line.find("virtual") >= 0:
                        # TAE performance stuff
                        fields = line.split()
                        physical = parseInt(fields[5][:-1])
                        virtual = parseInt(fields[7][:-1])
                        # not sure how well this really correspomds
                        used = virtual
                        total = physical
                        keph = parseInt(fields[9][:-4])
                        threads = parseInt(fields[10])
                        cpu = float(noCommasDouble(fields[12]))
                        buf = 0
                        t = parseTime(" ".join(fields[1:4]))
                    else:
                        fields = line.split()
                        used = parseInt(fields[5][:-1])
                        total = parseInt(fields[7][:-1])
                        if fields[11].find("keph") >= 0:
                            keph = parseInt(fields[11][:-5])
                        else:
                            keph = parseInt(fields[11][:-4])
                        buf = parseInt(fields[12])
                        t = parseTime(" ".join(fields[1:4]))
                        threads = parseInt(fields[14])
                        if line.find("CPU") >= 0:
                            cpu = float(noCommasDouble(fields[16]))
                except ValueError:
                    # incorrect speedo line
                    continue
                data.append(DataPoint(used, total, keph, buf, t, bugs, errors, warnings, perfs, lag, restart, kills, threshold, lagEvents, pageOpens, ecflag, slowPublish, slowSql, threads, cpu))
                restart = 0
                bugs = 0
                errors = 0
                warnings = 0
                perfs = 0
                lag = 0
                ecflag = 0
                kills = 0
                threshold = 0
                lagEvents = 0
                pageOpens = 0
                slowPublish = 0
                slowSql = 0
                threads = 0
                cpu = 0
        except:
            import traceback
            traceback.print_exc()
            print "Error in line '%s'" % line[:-1]
    file.close()
    return data

class Gui:
    def __init__(self, data, filename, options, png):
        self.data = data
        self.filename = filename
        self.root = Tk()
        self.canvas = Canvas(self.root, width=WIDTH, height=HEIGHT, background="white")
        self.canvas.grid(sticky=W+E+N+S)
        self.analyseData()
        self.repaint(options)
        self.root.bind_all('<Key>', self.keypress)
        if png:
            psfilename = filename
            psfilename = psfilename[:psfilename.rfind('.')] + ".ps"
            pngfilename = psfilename[:psfilename.rfind('.')] + ".png"
            self.canvas.postscript(file=psfilename, pageheight=HEIGHT, pagewidth=WIDTH, height=HEIGHT, width=WIDTH, pagex=WIDTH/2, pagey=HEIGHT/2)
            os.system('gs -dSAFER -sDEVICE=png16m -sOutputFile=%s -dEPSCrop -dEPSFitPage -g%dx%d -dNOPAUSE -q -dBATCH %s' % (pngfilename, WIDTH, HEIGHT, psfilename))
            print pngfilename
            os.remove(psfilename)

    def analyseData(self):
        max = 0
        maxTime = None
        minTime = None
        for point in self.data:
            if max < point.total:
                max = point.total
            # this is pointless in Java, but relevant for TAE
            if max < point.used:
                max = point.used
            point.t = time.mktime(point.timestamp) / 60
            if maxTime is None or maxTime < point.t:
                maxTime = point.t
            if minTime is None or minTime > point.t:
                minTime = point.t
        self.max = max
        self.maxTime = maxTime
        self.minTime = minTime
        self.numberDataPoints = len(self.data)
        for point in self.data:
            point.minutes = point.t
            point.x = self.calcx(point.minutes)
            point.lagStart = self.calcx(point.minutes - point.lag / 60)
            point.ecflagStart = self.calcx(point.minutes - point.ecflag / 60)
            point.slowPublishStart = self.calcx(point.minutes - point.slowPublish / 60)
            point.slowSqlStart = self.calcx(point.minutes - point.slowSql / 60)
        self.level = 2000
        if self.max > 20000:
            self.level = 5000
        if self.max > 50000:
            self.level = 10000
        if self.max > 100000:
            self.level = 20000
        if self.max > 300000:
            self.level = 50000

    def calcy(self, value):
        return EFFECTIVE_HEIGHT - ((EFFECTIVE_HEIGHT - 10) * value) / self.max

    def calcAbsY(self, value):
        return EFFECTIVE_HEIGHT - value

    def calcx(self, minutes):
        x = (minutes - self.minTime) * WIDTH / (self.maxTime - self.minTime)
        return x

    def repaint(self, options):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="white", outline="")
        if "C" in options:
            self.drawCPU()
        if "E" in options:
            self.drawECFLag()
        if "L" in options:
            self.drawLag()
        if "P" in options:
            self.drawSlowPublish()
        if "Q" in options:
            self.drawSlowSql()
        if "q" in options:
            self.drawSlowSqlLine()
        if "m" in options:
            self.drawMinuteDividers()
        if "M" in options:
            self.drawTenMegs()
        if "r" in options:
            self.drawRestarts()
        if "O" in options:
            self.drawPageOpens()
        if "t" in options:
            self.drawTime()
        if "j" in options:
            self.drawKephRunningAverage()
        if "k" in options:
            self.drawKeph()
        if "T" in options:
            self.drawTotalLine()
        if "U" in options:
            self.drawUsedLine()
        if "R" in options:
            self.drawRunningAverageUsedLine()
        self.drawErrors(options)
        if "B" in options:
            self.drawBuffered()
        if "K" in options:
            self.drawKills()
        if "E" in options:
            self.drawECFLagDurations()
        if "L" in options:
            self.drawLagDurations()
        if "h" in options:
            self.drawThreadCounts()
        if "l" in options:
            self.drawLegend()

    def printLegend(self):
        print "r - system restarts, black vertical lines"
        print "K - watchdog kills, red vertical lines"
        print "U - used memory, blue line"
        print "R - running average of used memory, cyan line"
        print "T - total memory, red line"
        print "h - thread counts, thick dark line"
        print "B - buffered events, orange line"
        print "L - lag, light cyan shading"
        print "E - ecf lag, light yellow shading"
        print "k - kephs, pink line"
        print "j - kephs running average, green line"
        print "O - page opens, purple vertical lines"
        print "P - slow publishes, pink shading"
        print "C - CPU usage - magenta shading"
        print "Q - slow SQL and slow QUERY, gray shading"
        print "q - slow SQL and slow QUERY, gray line"
        self.printErrorLegend()

    def drawKills(self):
        fillColour = "#ff0000"
        for point in self.data:
            if point.kills:
                self.canvas.create_line(point.x, 0, point.x, HEIGHT, fill=fillColour)

    def drawErrorCount(self, colour, fieldName):
        for point in self.data:
            value = point.__dict__[fieldName]
            if value > 2000:
                for i in range(value / 1000):
                    y = point.bugy
                    pw = PWIDTH + 5
                    self.canvas.create_polygon(point.x + pw, y + pw, point.x - pw, y + pw, point.x - pw, y - pw, point.x + pw, y - pw, fill=colour, outline="black")
                    point.bugy = point.bugy - 14
            elif value > 200:
                for i in range(value / 100):
                    y = point.bugy
                    pw = PWIDTH + 2
                    self.canvas.create_polygon(point.x + pw, y + pw, point.x - pw, y + pw, point.x - pw, y - pw, point.x + pw, y - pw, fill=colour, outline="black")
                    point.bugy = point.bugy - 10
            elif value > 20:
                for i in range(value / 10):
                    y = point.bugy
                    self.canvas.create_polygon(point.x + PWIDTH, y + PWIDTH, point.x - PWIDTH, y + PWIDTH, point.x - PWIDTH, y - PWIDTH, point.x + PWIDTH, y - PWIDTH, fill=colour, outline="black")
                    point.bugy = point.bugy - 10
            else:
                for i in range((value + 2) / 3):
                    y = point.bugy
                    pw = PWIDTH - 1
                    self.canvas.create_polygon(point.x, y + pw, point.x - pw, y, point.x, y - pw, point.x + pw, y, fill=colour)
                    point.bugy = point.bugy - 10

    def drawErrors(self, options):
        for point in self.data:
            point.bugy = HEIGHT - 15
        if "w" in options:
            self.drawErrorCount("yellow", "warnings")
        if "e" in options:
            self.drawErrorCount("red", "errors")
        if "b" in options:
            self.drawErrorCount("black", "bugs")
        if "p" in options:
            self.drawErrorCount("pink", "perfs")
        if "x" in options:
            self.drawErrorCount("green", "threshold")
        if "n" in options:
            self.drawErrorCount("cyan", "lagEvents")

    def printErrorLegend(self):
        print "w - warnings, yellow boxes"
        print "e - errors, red boxes"
        print "b - bugs, black boxes"
        print "p - performance, pink boxes"
        print "x - threshold warnings, green boxes"
        print "n - lag warnings, cyan boxes"

    def drawLegend(self):
        level = self.level
        while level < self.max:
            y = self.calcy(level)
            self.canvas.create_text(20, y - 5, fill="black", text = `level/1000` + "M", font=('Helvetica', FONT_SIZE))
            level = level + self.level
        self.canvas.create_text(WIDTH - 150, 10, fill="black", text = self.filename, font=('Helvetica', FONT_SIZE))

    def _calcDiv(self, width):
        divs = [ 30, 60, 120, 240, 360, 480, 720, 1440, 2880 ]
        div = divs[0]
        while div * WIDTH / (self.maxTime - self.minTime) < width:
            divs = divs[1:]
            if len(divs) == 0:
                break
            div = divs[0]
        return div

    def drawMinuteDividers(self):
        fillColour = "#b0ffb0"
        div = self._calcDiv(30)
        x = int((self.minTime * 60) / (div * 60))
        x = x * div + time.timezone / 60
        while x < self.maxTime:
            xx = self.calcx(x)
            self.canvas.create_line(xx, 0, xx, HEIGHT, fill=fillColour)
            x = x + div

    def drawTime(self):
        div = self._calcDiv(30)
        x = int((self.minTime * 60) / (div * 60))
        x = x * div + time.timezone / 60
        while x < self.maxTime:
            xx = self.calcx(x)
            if div >= 1440:
                t = time.strftime("%b %d", time.localtime(x * 60))
            else:
                t = time.strftime("%I:%M%p", time.localtime(x * 60)).lower()
                if t[0] == '0':
                    t = t[1:]
            t = t.replace(":00", "")
            self.canvas.create_text(xx, HEIGHT-5, text=t, fill="black", font=('Helvetica', FONT_SIZE))
            x = x + div

    def verticalLine(self, x, colour):
        self.canvas.create_line(x, EFFECTIVE_HEIGHT, x, 0, fill=colour)

    def shadedRectangle(self, start, end, colour):
        self.canvas.create_rectangle(start, 0, end, EFFECTIVE_HEIGHT, fill=colour, outline="")

    def shadedArea(self, startx, starty, endx, endy, colour):
        self.canvas.create_polygon(startx, EFFECTIVE_HEIGHT, startx, starty, endx, endy, endx, EFFECTIVE_HEIGHT, fill=colour, outline="")

    def drawRestarts(self):
        for point in self.data:
            if point.restart:
                self.verticalLine(point.x, "black")

    def drawPageOpens(self):
        for point in self.data:
            if point.pageOpens:
                self.verticalLine(point.x, "purple")

    def drawTenMegs(self):
        level = self.level
        while level < self.max:
            y = self.calcy(level)
            self.canvas.create_line(0, y, WIDTH, y, fill="gray")
            level = level + self.level

    def drawUsedLine(self):
        x = 0
        y = 0
        l = len(self.data)
        for point in self.data:
            oldx = x
            oldy = y
            y = self.calcy(point.used)
            x = point.x
            self.canvas.create_line(oldx, oldy, x, y, fill="blue")

    def drawRunningAverageUsedLine(self):
        x = 0
        y = 0
        running = 0
        l = len(self.data)
        for point in self.data:
            if point.restart:
                running = 0
            if running == 0:
                running = point.used
            oldx = x
            oldy = y
            running = (running * 19 + point.used) / 20
            y = self.calcy(running)
            x = point.x
            self.canvas.create_line(oldx, oldy, x, y, fill="cyan")

    def drawBuffered(self):
        x = 0
        y = 0
        l = len(self.data)
        for point in self.data:
            oldx = x
            oldy = y
            y = self.calcAbsY(point.buf)
            x = point.x
            self.canvas.create_line(oldx, oldy, x, y, fill="orange")
            self.canvas.create_line(oldx-1, oldy-1, x-1, y-1, fill="orange")

    def drawThreadCounts(self):
        x = 0
        y = 0
        l = len(self.data)
        for point in self.data:
            oldx = x
            oldy = y
            y = self.calcAbsY(point.threads - 120)
            x = point.x
            self.canvas.create_line(oldx, oldy, x, y, fill="#008000")
            self.canvas.create_line(oldx-1, oldy-1, x-1, y-1, fill="#008000")

    def drawSlowPublish(self):
        x = 0
        y = 0
        colour = "#ffe0e0"
        l = len(self.data)
        for point in self.data:
            if point.slowPublish > 0:
                self.shadedRectangle(point.slowPublishStart, point.x, colour)

    def drawSlowSql(self):
        x = 0
        y = 0
        colour = "#d0d0d0"
        l = len(self.data)
        for point in self.data:
            if point.slowSql > 0:
                self.shadedRectangle(point.slowSqlStart, point.x, colour)

    def drawSlowSqlLine(self):
        colour = "#d0d0d0"
        l = len(self.data)
        for point in self.data:
            if point.slowSql > 0:
                y = self.calcAbsY(point.slowSql * 10)
                x = point.x
                self.canvas.create_line(x, EFFECTIVE_HEIGHT, x, y, fill=colour)

    def drawLag(self):
        x = 0
        y = 0
        colour = "#e0ffff"
        l = len(self.data)
        for point in self.data:
            if point.lag > 0:
                self.shadedRectangle(point.lagStart, point.x, colour)

    def drawECFLag(self):
        x = 0
        y = 0
        colour = "#f0f0b0"
        l = len(self.data)
        for point in self.data:
            if point.ecflag > 0:
                self.shadedRectangle(point.ecflagStart, point.x, colour)

    def drawLagDurations(self):
        x = 0
        y = 0
        l = len(self.data)
        prevlag = 0
        y = LAG_TOP
        for point in self.data:
            if point.lag > 0:
                if prevlag == 0 or point.lag > prevlag:
                    self.canvas.create_text(point.lagStart, y, text=`point.lag`, fill="black", font=('Helvetica', FONT_SIZE))
                    y = y + LAG_ROW_HEIGHT
                    if y == LAG_BOTTOM:
                        y = LAG_TOP
            prevlag = point.lag

    def drawECFLagDurations(self):
        x = 0
        y = 0
        l = len(self.data)
        prevlag = 0
        y = LAG_TOP
        for point in self.data:
            if point.ecflag > 0:
                if prevlag == 0:
                    self.canvas.create_text(point.ecflagStart, y, text=`point.ecflag`, fill="black", font=('Helvetica', FONT_SIZE))
                    y = y + LAG_ROW_HEIGHT
                    if y == LAG_BOTTOM:
                        y = LAG_TOP
            prevlag = point.ecflag

    def drawKeph(self):
        x = 0
        y = 0
        running = -1
        l = len(self.data)
        lowCount = 0
        for point in self.data:
            colour = "#ff80ff"
            oldx = x
            oldy = y
            y = self.calcAbsY(point.keph)
            x = point.x
            self.canvas.create_line(oldx, oldy, x, y, fill=colour)

    def drawCPU(self):
        x = 0
        y = 0
        l = len(self.data)
        colour = "#ffb0ff"
        factor = 1.0
        for point in self.data:
            while point.cpu > factor * 100.0:
                factor = factor + 1
        for point in self.data:
            oldx = x
            oldy = y
            y = self.calcAbsY(int(point.cpu * 5.0 / factor))
            x = point.x
            self.shadedArea(oldx, oldy, x, y, colour)

    def drawKephRunningAverage(self):
        x = 0
        ry = 0
        running = -1
        l = len(self.data)
        lowCount = 0
        for point in self.data:
            colour = "#ff80ff"
            if point.restart:
                running = -1
            if running < 0:
                running = point.keph * 1.0
            oldx = x
            oldry = ry
            running = (running * 5.0 + point.keph) / 6.0
            ry = self.calcAbsY(running)
            x = point.x
            self.canvas.create_line(oldx, oldry, x, ry, fill="green")

    def drawTotalLine(self):
        x = 0
        y = 0
        l = len(self.data)
        for point in self.data:
            oldx = x
            oldy = y
            x = point.x
            y = self.calcy(point.total)
            self.canvas.create_line(oldx, oldy, x, y, fill="red")

    def keypress(self, event):
        ch = event.char
        global options, guis
        if options.find(ch) >= 0:
            options = options.replace(ch, "")
        else:
            options = options + ch
        for gui in guis:
            gui.repaint(options)
        print "Options are " + options

    def mainloop(self):
        print "--- Press a key to toggle a displayed value"
        self.root.mainloop()

def resolveFilenames(directory, pattern):
    files = os.listdir(directory)
    matching = []
    for file in files:
        if file.endswith(".png"):
            continue
        if file.find(pattern) >= 0:
            matching.append(os.sep.join([directory, file]))
    if len(matching) > 0:
        return matching
    else:
        return [ pattern ]

guis = []
options = ""

if __name__ == '__main__':
    options = "mMrRstTUlwebKxnOhC"
    args = sys.argv[1:]
    if len(args) not in [1, 2, 3, 4, 5]:
        print "Usage: logspeedo [-png] [-0|1|2|3] <pattern> [<directory>] [options]"
        sys.exit(92)
    png = False
    opts = [ x for x in args if x.startswith("-") ]
    args = [ x for x in args if not x.startswith("-") ]
    if "-png" in opts:
        png = True
        EFFECTIVE_HEIGHT = HEIGHT
    for d in [0, 1, 2, 3]:
        if ("-" + `d`) in opts:
            WIDTH = WIDTHS[d]
    filenamePattern = args[0]
    directory = "."
    if len(args) == 2:
        if os.sep in args[1] or '.' in args[1]:
            directory = args[1]
        else:
            options = args[1]
    elif len(args) == 3:
        directory = args[1]
        options = args[2]
    if not png:
        print "Using options " + options
    filenames = resolveFilenames(directory, filenamePattern)
    gui = None
    for filename in filenames:
        try:
            data = getData(filename)
            if len(data) > 0:
                gui = Gui(data, filename, options, png)
                guis.append(gui)
        except ZeroDivisionError:
            continue
    if len(guis) > 0 and not png:
        guis[0].printLegend()
        guis[0].mainloop()
