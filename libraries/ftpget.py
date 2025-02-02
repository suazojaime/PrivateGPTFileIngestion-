import mstarftp, sys
import minestar

logger = minestar.initApp()

mstarftp.ftpCommand(mstarftp.GET, sys.args[1:])
