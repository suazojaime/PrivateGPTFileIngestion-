import sys, os
import minestar

logger = minestar.initApp()

srcfile = sys.argv[1]
destfile = sys.argv[2]
os.makedirs(os.path.dirname(srcfile))
file = open(srcfile, "w")
file.write("<HTML><HEAD><TITLE>Coverage Redirection</TITLE></HEAD>\n<BODY><A HREF=\"file:%s\">Clover Coverage Report<A></BODY></HTML>\n" % destfile)
file.close()
