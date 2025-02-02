# This script is untested and may not work.  If you're looking in here you probably actually want the script
# called makeScheduledTasks.py instead.  Or maybe not.  Who can say...?

import minestar

logger = minestar.initApp()

def schedule(command):
    import mstarpaths
    taskFile = mstarpaths.interpretPath("{MSTAR_ADMIN}/ScheduledTasks.txt")
    file = open(taskFile, "a")
    file.write(command + "\n")
    file.close()

if __name__ == '__main__':
    import mstarrun
    config = mstarrun.loadSystem(sys.argv[1:])
    args = config["args"]
    schedule(" ".join(args))
