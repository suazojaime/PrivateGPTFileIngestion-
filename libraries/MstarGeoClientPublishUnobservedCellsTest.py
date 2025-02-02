################################################################################
###
### %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
### %%                                                                       %%
### %%  COPYRIGHT (C) 1999-2017 CATERPILLAR INC.   ALL RIGHTS RESERVED.      %%
### %%      This work contains proprietary information which may             %%
### %%      constitute a trade secret and/or be confidential.                %%
### %%                                                                       %%
### %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
###
### FILENAME :  MstarGeoClientPublishUnobservedCellsTest.py
###
### DESCRIPTION :
###     This script can be used to confirm that features can be published to the
###     GeoServer.
###
### LANGUAGE :
###    Python (2.7 or later I think)
###
################################################################################

import StringIO
import base64
import getopt
import gzip
import os
import sys
import urllib2
import xml.dom.minidom
import zlib
from datetime import datetime

compress = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], 'gx:y:r:m:', ["gz", "gzip", "xpos", "ypos", "ref"])
except:
    print "Usage: MstarGeoClientPublishUnobservedCellsTest -g [--gz, --gzip] -x -y -r [--xpos --ypos --ref]"
    sys.exit(2)

REFERENCE = '8'
startx = 510
starty = 940
MACHINEID = 0
for o, a in opts:
    if o in ("-g", "--gz", "--gzip"):
        compress = 1
    elif o in ("-x", "--xpos"):
        startx = int(a)
    elif o in ("-y", "--ypos"):
        starty = int(a)
    elif o in ("-r", "--ref"):
        REFERENCE = a
    elif o in ("-m", "--machineId"):
        MACHINEID = a

USER = 'minestar'
PASS = 'm*geoserver'
HOST = '127.0.0.1'
PORT = '7070'
WORKSPACE = 'MS_MINESTAR'
UNOBSERVED_CELLS = 'MS_UNOBSERVED_CELLS'
z = 176.0
cellSize = 2.0
CELL_SIZE = '2.0'
TIMESTAMP = datetime.utcnow().isoformat().split('.', 1)[0] + 'Z'

def addCoordinates(x, y, z):
    ret = '<gml:pointMember><gml:Point><gml:pos>'
    ret += repr(x) + ' ' + repr(y) + ' ' + repr(z)
    ret += '</gml:pos></gml:Point></gml:pointMember>'
    return ret

if __name__ == "__main__":
    url = 'http://' + HOST + ':' + PORT + '/geoserver/wfs'

    base64string = base64.encodestring('%s:%s' % (USER, PASS)).replace('\n', '')
    headers = {}
    headers['Authorization'] = 'Basic %s' % base64string
    headers['Accept'] = '*/*'
    headers['Accept-Encoding'] = 'gzip'
    if (compress):
        headers['Content-Encoding'] = 'gzip'
    headers['Content-Type'] = 'application/xml'

    body = ''
    body += '<wfs:Transaction xmlns:wfs=\"http://www.opengis.net/wfs\"' + os.linesep
    body += '                 xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"' + os.linesep
    body += '                 service=\"WFS\" version=\"1.1.0\"' + os.linesep
    body += '                 xmlns:gml=\"http:/s/www.opengis.net/gml\"' + os.linesep
    body += '                 xmlns:ogc=\"http://www.opengis.net/ogc\"' + os.linesep
    body += '                 xsi:schemaLocation=\"http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd'
    body += ' http://' + WORKSPACE
    body += ' http://'+ HOST + ':' + PORT + '/geoserver/wfs?SERVICE=WFS&amp;VERSION=1.1.0&amp;REQUEST=DescribeFeatureType&amp;TYPENAME='
    body += WORKSPACE + ':' + UNOBSERVED_CELLS + '\">' + os.linesep
    body += '  <wfs:Insert>' + os.linesep
    body += '    <feature:' + UNOBSERVED_CELLS + ' xmlns:feature=\"http://'+ WORKSPACE +'\">' + os.linesep
    body += '      <feature:GEOM>'
    body +=         '<gml:MultiPointZ>'

    # just publish a 3x3 square unobserved cell
    body += addCoordinates(startx, starty, z)
    body += addCoordinates(startx + cellSize, starty, z)
    body += addCoordinates(startx + cellSize * 2, starty, z)

    body += addCoordinates(startx, starty + cellSize, z)
    body += addCoordinates(startx + cellSize, starty + cellSize, z)
    body += addCoordinates(startx + cellSize * 2, starty + cellSize, z)

    body += addCoordinates(startx, starty + cellSize * 2, z)
    body += addCoordinates(startx + cellSize, starty + cellSize * 2, z)
    body += addCoordinates(startx + cellSize * 2, starty + cellSize * 2, z)

    body +=         '</gml:MultiPointZ>'
    body +=       '</feature:GEOM>' + os.linesep
    body += '      <feature:REFERENCE>' + REFERENCE + '</feature:REFERENCE>' + os.linesep
    body += '      <feature:MACHINE_ID>' + str(MACHINEID) + '</feature:MACHINE_ID>' + os.linesep
    body += '      <feature:CELL_SIZE>' + CELL_SIZE + '</feature:CELL_SIZE>' + os.linesep
    body += '      <feature:TIMESTAMP>' + TIMESTAMP + '</feature:TIMESTAMP>' + os.linesep
    body += '    </feature:' + UNOBSERVED_CELLS + '>' + os.linesep
    body += '  </wfs:Insert> ' + os.linesep
    body += '</wfs:Transaction>' + os.linesep

    print '-----URL-----' + os.linesep, url
    if(len(body) > 2000):
        print '-----BODY-----' + os.linesep, body[0:1000], os.linesep + '...' + os.linesep, body[-1000:]
    else:
        print '-----BODY-----' + os.linesep, body

        ## Try compressing the body
    if (compress):
        bodySizeBefore = float(len(body))
        s = StringIO.StringIO()
        g = gzip.GzipFile(fileobj=s, mode='w')
        g.write(body)
        g.close()
        gzipped_body = s.getvalue()
        bodySizeAfter = float(len(gzipped_body))
        print 'Compression ratio: ', bodySizeBefore/bodySizeAfter
    else:
        print "No compression used...."

    print 'Waiting for response...'
    sys.stdout.flush()
    if (compress):
        request=urllib2.Request(url=url, data=gzipped_body, headers=headers)
    else:
        request=urllib2.Request(url=url, data=body, headers=headers)

    try:
        response = urllib2.urlopen(request)
        responseStr = response.read()
        print '----Response----' + os.linesep,

        decompressedXML = zlib.decompress(responseStr, 16+zlib.MAX_WBITS)
        xml = xml.dom.minidom.parseString(decompressedXML)
        prettyXML = xml.toprettyxml()
        print prettyXML
    except urllib2.HTTPError, err:
        print "HTTP Error: " + repr(err.code) + ' ' + err.reason
    except urllib2.URLError,err:
        print err.reason

    print 'Done.'
