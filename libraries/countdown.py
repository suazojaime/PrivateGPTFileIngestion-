# $Id: countdown.py,v 1.2 2004-12-16 05:07:08 ianc Exp $
# Simple test program for counting down from 10 to 1

import sys, time
import minestar

logger = minestar.initApp()

def main(args):
    for i in range(10, 0, -1):
        print i
        sys.stdout.flush()
        time.sleep(1)

if __name__ == "__main__":
    main(sys.argv)

