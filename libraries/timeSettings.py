# generate a batch file to set environment variables to indicate the time
# a number of days ago

import time, sys
import minestar

logger = minestar.initApp()

def pad(s, needed):
    while len(s) < needed:
        s = "0" + s
    return s

ago = 0
if len(sys.argv) > 1:
   ago = int(sys.argv[1])
t = time.localtime(time.time() - ago * 24 * 3600)
result = {}
result["YYYY"] = pad(`t[0]`, 4)
result["MM"] = pad(`t[1]`, 2)
result["DD"] = pad(`t[2]`, 2)
result["HH"] = pad(`t[3]`, 2)
result["NN"] = pad(`t[4]`, 2)
result["SS"] = pad(`t[5]`, 2)

for (key, value) in result.items():
    print "set %s=%s" % (key, value)
