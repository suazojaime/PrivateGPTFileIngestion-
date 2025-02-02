import mstarftp, sys
import minestar

logger = minestar.initApp()

mstarftp.ftpCommand(mstarftp.DEL, sys.args[1:])
