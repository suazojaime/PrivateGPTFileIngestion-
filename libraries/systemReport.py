# A library which handles creation of the system report

import mstarapplib, string, i18n, mstarpaths, os
import minestar

logger = minestar.initApp()

REPORT_SUMMARY_HEADER = "<!-- Report Summary"
REPORT_SUMMARY_FOOTER = "End Report Summary -->"
PROBLEM_SUMMARY = "PROBLEM SUMMARY:"
STATUS = "STATUS:"

STATUS_GOOD = "GOOD"
STATUS_WARNING = "WARNING"
STATUS_ERROR = "ERROR"
STATUS_FATAL = "FATAL"

STATUS_COLOURS = {
    None : "#00c0c0",
    STATUS_GOOD : "#00c000",
    STATUS_WARNING : "#ffff00",
    STATUS_ERROR : "#c00000",
    STATUS_FATAL : "#c000c0"
    }

def getColourForStatus(status):
    return STATUS_COLOURS[status]

class ReportSummary:
    def __init__(self, title, problemSummary, status):
        self.title = title
        self.problemSummary = problemSummary
        self.status = status

    def toHtml(self):
        lines = []
        if self.status is not None:
            lines.append("%s %s" % (STATUS, self.status))
        if self.problemSummary is not None:
            lines.append("%s %s" % (PROBLEM_SUMMARY, self.problemSummary))
        return """
%s
%s
%s
""" % (REPORT_SUMMARY_HEADER, "\n".join(lines), REPORT_SUMMARY_FOOTER)
        
def parseReportSummary(title, lines):
    problemSummary = None
    status = None
    for line in lines:
        if line[-1] == "\n":
            line = line[:-1]
        line = line.strip()
        if line.startswith(PROBLEM_SUMMARY):
            problemSummary = line[len(PROBLEM_SUMMARY):].strip()
        elif line.startswith(STATUS):
            status = line[len(STATUS):].strip()
    return ReportSummary(title, problemSummary, status)

def getReportSummary(filename):
    """
    Open the file, find the HTML for the report summary, and create the object.
    Return None if there isn't one there.
    """
    file = open(filename)
    lines = file.readlines()
    catching = 0
    summary = []
    title = None
    for line in lines:
        line = line.strip()
        # look for title
        if not title:
            ts = line.find("<TITLE>")
            if ts >= 0:
                line = line[ts+7:]
                cs = line.find("<")
                if cs >= 0:
                    line = line[:cs]
                title = line
        # look for system report
        if catching:
            if line == REPORT_SUMMARY_FOOTER:
                catching = 0
                break
            else:
                summary.append(line)
        elif line == REPORT_SUMMARY_HEADER:
            catching = 1
        else:
            continue
    file.close()
    return parseReportSummary(title, summary)

SYSTEM_REPORT_HEADER = """<HTML><HEAD>
<TITLE>System Report for %s at %s</TITLE>
</HEAD>
<BODY>
<H1>System Report for %s at %s</H1>
"""

SYSTEM_REPORT_FOOTER = """
</BODY>
</HTML>
"""

def startSystemReport(sysReportFileName):
    "Start production of the system report"
    file = open(sysReportFileName, "w")
    timestamp = mstarpaths.interpretFormat("{HH}:{NN} {YYYY}/{MM}/{DD}")
    customer = mstarpaths.interpretVar("_CUSTCODE")
    file.write(SYSTEM_REPORT_HEADER % (customer, timestamp, customer, timestamp))
    file.close()

def finishSystemReport(sysReportFileName, reportsDir):
    "Complete production of the system report"
    file = open(sysReportFileName, "a")
    file.write("<UL>\n")
    reports = os.listdir(reportsDir)
    for filename in reports:
        if sysReportFileName.endswith(filename):
            continue
        if filename.endswith(".html"):
            fullFileName = reportsDir + os.sep + filename
            summary = getReportSummary(fullFileName)
            title = summary.title
            if title is None:
                title = filename
            file.write("<LI><A HREF=\"%s\">%s</A>\n" % (filename, title))
            if summary.status is not None and summary.status != STATUS_GOOD:
                colour = getColourForStatus(summary.status)
                mesg = summary.problemSummary
                file.write('<FONT COLOR="%s">%s</FONT>\n' % (colour, mesg))
    file.write("</UL>\n")
    file.write(SYSTEM_REPORT_FOOTER)
    file.close()
