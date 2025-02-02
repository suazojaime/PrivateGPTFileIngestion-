import mstarftp, sys
import minestar

logger = minestar.initApp()

mstarftp.ftpCommand(mstarftp.PUT, sys.args[1:])
