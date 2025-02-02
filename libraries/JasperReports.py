import string
import xml.sax
from xml.sax.handler import *
import minestar

logger = minestar.initApp()

## NOTE: This library should ultimately supporting parsing, changing and writing of JasperReport files.
## Currently, it uses SAX and only supports extraction of report parameters.
## In the future, it should support a treee-based structure, e.g. Fredrik Lundh's elementtree,
## David Mertz's xml_objectify, DOM if all else fails.

_NAME_KEY       = "name"
_PARAMETERS_KEY = "parameters"


class _JasperReportHandler(ContentHandler):
    """Basic extractor for JapserReport report definitions"""

    def __init__(self):
        self.name = ""
        self.inParameters = 0
        self.parameters = []
        self.inParamDesc = 0
        self.paramDesc = None
        self.inParamDefault = 0
        self.paramDefault = None

    def startElement(self, name, attrs):
        if name == "jasperReport":
            self.name = attrs['name']
        elif name == "parameter":
            self.inParameters = 1
            dict = {}
            dict.update(attrs)
            self.parameters.append(dict)
            self.paramDesc = None
            self.paramDefault = None
        elif self.inParameters and name == "parameterDescription":
            self.inParamDesc = 1
        elif self.inParameters and name == "defaultValueExpression":
            self.inParamDefault = 1
            
    def characters(self, content):
        if self.inParamDesc:
            if self.paramDesc == None:
                self.paramDesc = content
            else:
                self.paramDesc = self.paramDesc + content
        elif self.inParamDefault:
            if self.paramDefault == None:
                self.paramDefault = content
            else:
                self.paramDefault = self.paramDefault + content

    def endElement(self, name):
        if name == "parameter":
            lastParam = self.parameters[-1]
            if self.paramDesc != None:
                lastParam["parameterDescription"] = self.paramDesc
            if self.paramDefault != None:
                lastParam["defaultValueExpression"] = self.paramDefault
            self.inParameters = 0
            #print "found parameter:"
            #for k in lastParam.keys():
            #    print "\t%s: %s" % (k, lastParam[k])
        elif name == "parameterDescription":
            self.inParamDesc = 0
        elif name == "defaultValueExpression":
            self.inParamDefault = 0

    def getCollectedName(self):
        return self.name

    def getCollectedParameters(self):
        return self.parameters
    
def load(filename):
    "load the report in filename and returns the result (only the name & parameters currently) as a dictionary"
    result = {}
    parser = xml.sax.make_parser()
    handler = _JasperReportHandler()
    parser.setContentHandler(handler)
    parser.parse(filename)
    result[_NAME_KEY]       = handler.getCollectedName()
    result[_PARAMETERS_KEY] = handler.getCollectedParameters()
    return result


def getName(dict):
    "returns the name of the report"
    return dict[_NAME_KEY]

def getParameters(dict):
    "returns [] if no parameters are not defined in a report, otherwise the list of parameters"
    return dict[_PARAMETERS_KEY]
