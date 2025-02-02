#!/usr/bin/env python

import sys, os, xml.dom.minidom, datetime, time, string

firstTimestamp = None
ipaddrDict = {}

def getDom(filename):
    "return a DOM tree for the named file"
    dom = xml.dom.minidom.parse(filename)
    rootElement = dom.documentElement
    rootElement.normalize()
    return rootElement

def elements(node):
    es = []
    for child in node.childNodes:
        if child.nodeType == xml.dom.Node.ELEMENT_NODE:
            es.append(child)
    return es

def childNamed(node, name):
    es = elements(node)
    for e in es:
        if e.nodeName == name:
            return e
    return None

def calcTimeDiff(value):
    global firstTimestamp
    newTimestamp = datetime.datetime(*time.strptime(value, "%Y/%m/%d %H:%M:%S")[0:6])
    if firstTimestamp == None:
        firstTimestamp = newTimestamp
    difference = newTimestamp - firstTimestamp
    return difference.seconds * 1000

def printField(field, prefix):
    if field.nodeName == "Field":
        value = field.getAttribute("value")
        name = field.getAttribute("name")
        format = field.getAttribute("format")
        if format in ["UTC", "TTIME5"]:
            value = "[Date(start.getTime()+%i)]" % calcTimeDiff(value)
        p = prefix
        if p is None:
            p = name
        else:
            p = "%s/%s" % (p, name)
        print "|%s|%s|" % (p, value)
    else:
        bits = elements(field)
        for b in bits:
            p = prefix
            if field.nodeName == "Message":
               p = None
            elif p is None:
                p = field.getAttribute("name")
            else:
                p = "%s/%s" % (p, field.getAttribute("name"))
            printField(b, p)

def calcMachineName(ipaddr):
    global ipaddrDict
    if ipaddr not in ipaddrDict:
        ipaddrDict[ipaddr] = "m%i" % (len(ipaddrDict)+1)
    return ipaddrDict[ipaddr]

def printPacket(child):
    ipaddr = child.getAttribute("ipaddr")
    message = childNamed(child, "Message")
    type = message.getAttribute("name")
    print "!|com.mincom.fit.TmacPacketFixture|"
    print "|_type_|%s|" % type
    print "|_machine_|${%s}|" % calcMachineName(ipaddr)
    printField(message, None)
    print

def printPackets(node):
    children = elements(node)
    for child in children:
        printPacket(child)

domTree = getDom(sys.argv[1])
printPackets(domTree)

