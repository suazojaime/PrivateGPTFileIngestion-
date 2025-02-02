import mstarftp, sys
import minestar

logger = minestar.initApp()

mstarftp.ftpCommand(mstarftp.DIR, sys.args[1:])
