################################################################################
###
### %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
### %%                                                                       %%
### %%  COPYRIGHT (C) 1999-2016 CATERPILLAR INC.   ALL RIGHTS RESERVED.      %%
### %%      This work contains proprietary information which may             %%
### %%      constitute a trade secret and/or be confidential.                %%
### %%                                                                       %%
### %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
###
### FILENAME :  MstarGeoClientPublishTest.py
###
### DESCRIPTION :
###     This script can be used to confirm that features can be published to the
###     GeoServer.
###
### LANGUAGE :
###    Python (2.7 or later I think)
###
### HISTORY :
###     V01 (3/23/2016) (M Johnson)
###         Initial Version.
###     V02 (15/04/2016) (M Abdullah)
###         Added gzip request capabilities.
################################################################################

import urllib2
import base64
import random
from datetime import datetime
import zlib
import xml.dom.minidom
import os
import sys
import gzip
import StringIO
import getopt

compress = 0

try:
    opts, args = getopt.getopt(sys.argv[1:], 'gx:y:r:h:v:m:', ["gz", "gzip", "xpos", "ypos", "xCols", "yRows","ref", "machineId"])
except:
    print "Usage: MstarGeoClientPublishTest -g [--gz, --gzip] -x -y -r -h -v -m [--xpos --ypos --ref --xCols --yRows --machineId]"
    sys.exit(2)

REFERENCE = '8'
startx = 510
starty = 940
xCols = 10
yRows = 2
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
    elif o in ("-h", "--xCols"):
        xCols = int(a)
    elif o in ("-v", "--yRows"):
        yRows = int(a)

USER = 'MineStar'
PASS = 'MineStar'
HOST = '127.0.0.1'
PORT = '7071'
WORKSPACE = 'MS_MINESTAR'
OBSTACLES = 'MS_OBSTACLES'
z = 176.0
CELL_SIZE = '0.5'
TIMESTAMP = datetime.utcnow().isoformat().split('.', 1)[0] + 'Z'

if __name__ == "__main__":
    url = 'http://' + HOST + ':' + PORT + '/minestar/wfs'

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
    body += ' http://'+ HOST + ':' + PORT + '/minestar/wfs?SERVICE=WFS&amp;VERSION=1.1.0&amp;REQUEST=DescribeFeatureType&amp;TYPENAME='
    body += WORKSPACE + ':' + OBSTACLES + '\">' + os.linesep
    body += '  <wfs:Insert>' + os.linesep
    body += '    <feature:' + OBSTACLES + ' xmlns:feature=\"http://'+ WORKSPACE +'\">' + os.linesep
    body += '      <feature:GEOM>'
    body +=         '<gml:MultiPoint>'

    for y in range(0, yRows):
        for x in range(0, xCols):
            body += '<gml:pointMember><gml:Point><gml:pos>'
            body += repr(startx + x) + ' ' + repr(starty - y) + ' ' + repr(z)
            body += '</gml:pos></gml:Point></gml:pointMember>'

    body +=         '</gml:MultiPoint>'
    body +=       '</feature:GEOM>' + os.linesep
    body += '      <feature:REFERENCE>' + REFERENCE + '</feature:REFERENCE>' + os.linesep
    body += '      <feature:MACHINE_ID>' + str(MACHINEID) + '</feature:MACHINE_ID>' + os.linesep
    body += '      <feature:CELL_SIZE>' + CELL_SIZE + '</feature:CELL_SIZE>' + os.linesep
    body += '      <feature:TIMESTAMP>' + TIMESTAMP + '</feature:TIMESTAMP>' + os.linesep
    body += '    </feature:' + OBSTACLES + '>' + os.linesep
    body += '  </wfs:Insert> ' + os.linesep
    body += '</wfs:Transaction>' + os.linesep

    print '-----URL-----' + os.linesep, url
    if len(body) > 2000:
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
    if compress:
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
