import mstarrun, sys
import minestar

logger = minestar.initApp()

# run an mstarrun target with no output

mstarrun.run(sys.argv[1:], { "silent" : 1 })
