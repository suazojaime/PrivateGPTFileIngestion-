import time, sys
import minestar

logger = minestar.initApp()

delay = int(sys.argv[1])
time.sleep(delay)
