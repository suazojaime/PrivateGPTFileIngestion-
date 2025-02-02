import mstarpaths, sys, mstarrun
import minestar

logger = minestar.initApp()

busUrl = sys.argv[1]
kind = sys.argv[2]
target = sys.argv[3]
file = mstarpaths.interpretPath(sys.argv[4])
mstarrun.run(["com.mincom.env.service.admin.tool.SendConfig", busUrl, kind, target, file])
