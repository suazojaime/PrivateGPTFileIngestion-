import minestar, os, i18n, mstarpaths, sys, mstarrun, StringTools, ServerTools, subprocess,datetime

logger = minestar.initApp()

# Dictionary of tasks indexed by computer role
ALL_TASKS = {"AppServer":["cleanExpiredFiles", "snapshotSystem", "snapshotOs", "syncStandbyInformation"],
             "Client":   ["cleanExpiredFiles", "snapshotSystem", "snapshotOs"],
             "DbServer": ["cleanExpiredFiles", "snapshotSystem", "snapshotOs", "cleanExpiredData", "exportDataStores", "rmanToolsFullDB", "rmanToolsIncrDB", "rmanToolsArcDB", "purgeRecycleBin","dbHealthMonitor"],
             "Detect":   ["cleanExpiredFiles"],
            }
ALL_OPTION = {"all"}

def _regScheduledTask(mstarTask, params, startTime, frequency, duration=None, repeat=0, taskLabel=None):
    """ Generate an event for the Windows Task Scheduler utility"""
    mstarHome = mstarpaths.interpretPath("{MSTAR_HOME}")
    mstarRun = "%s%s%s%s%s\\mstarrun.bat" % (mstarHome, os.sep, "bus", os.sep, "bin")
    mstarSystem = mstarpaths.interpretPath("{MSTAR_SYSTEM}")
    args = "-s %s %s" % (mstarSystem,mstarTask)

    if params is not None and len(params) > 0:
        args = args + " " + params

    if taskLabel != None:
        mstarTask = taskLabel

    if duration == None and repeat == 0:
            createCmd = 'schtasks /Create /SC %s /ST %s /RU SYSTEM /RL HIGHEST /TN %s /TR "%s %s' % (frequency, startTime,mstarTask, mstarRun, args)
    else:
        if repeat is 0:
            createCmd = 'schtasks /Create /SC %s /ST %s /DU %s /RU SYSTEM /RL HIGHEST  /TN %s /TR "%s %s' % (frequency, startTime,duration, mstarTask, mstarRun, args)
        elif duration is None:
            createCmd = 'schtasks /Create /SC %s /ST %s /MO %s /RU SYSTEM /RL HIGHEST  /TN %s /TR "%s %s' % (frequency, startTime,repeat, mstarTask, mstarRun, args)
        else:
            #Optional "repeat within a duration command". ex: to create a task running every hour but should run at max 10 hours from starting time (here duration is 10 hours) .
            createCmd = 'schtasks /Create /SC %s /ST %s /DU %s /K /MO %s /RU SYSTEM /RL HIGHEST /TN %s /TR "%s %s' % (frequency,startTime,duration, repeat, mstarTask, mstarRun, args)

    #checkTaskExist(task) will return 0 if task already exist
    if not(checkTaskExist(mstarTask)):
        #Task Exist,So deleting the old task and creating a new task
        deleteTask(mstarTask)
        createTask(createCmd)
    else:
        #Task does not exist, So creating a new task
        createTask(createCmd)

#  If task exist : 0 will be returned , If task does not exist: 1 will be returned
def checkTaskExist(mstarTask):
    checkTask= "schtasks /QUERY /FO CSV /TN %s" % mstarTask
    # checkTask process, connected to the Python interpreter through pipes:
    prog = subprocess.Popen(checkTask, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    prog.communicate()
    return prog.returncode

def deleteTask(mstarTask):
    deleteCmd = "schtasks /Delete /F /TN %s " % mstarTask
    subprocess.call(deleteCmd)

def createTask(schtasks_cmd):
    subprocess.call(schtasks_cmd)

# When ever an build upgrade is done, we need to change the
# Scheduled Tasks path to current working directory with appropriate build name.
def updateTaskPath(mstarTask, params,taskLabel=None):
    import mstarpaths
    mstarHome = mstarpaths.interpretPath("{MSTAR_HOME}")
    mstarRun = "%s%s%s%s%s\\mstarrun.bat" % (mstarHome, os.sep, "bus", os.sep, "bin")
    mstarSystem = mstarpaths.interpretPath("{MSTAR_SYSTEM}")

    args = "-s %s %s" % (mstarSystem,mstarTask)

    if params is not None and len(params) > 0:
        args = args + " " + params

    if taskLabel != None:
            mstarTask = taskLabel

    #  If task exist : 0 will be returned , If task does not exist: 1 will be returned
    if not (checkTaskExist(mstarTask)):
        changeCmd = 'schtasks /Change /TN %s /TR "%s %s' % (mstarTask,mstarRun,args)
        subprocess.call(changeCmd)

def updateTask(roles):
    # Work out the Tasks to be registered from the list of roles
    allTasks = []
    for role in roles:
        roleTasks = ALL_TASKS.get(role)
        for task in roleTasks:
            found = 0
            for regTask in allTasks:
                #check if same task already added for diff role.
                if task == regTask:
                    found = 1
            if found == 0:
                allTasks.append(task)

    # If this computer is configured for FTP, register sendAllToSupport as a task
    ftpComputer = mstarpaths.interpretFormat("{_FTPSERVER}")
    thisComputer = mstarpaths.interpretFormat("{COMPUTERNAME}")
    if ftpComputer.upper() == thisComputer.upper():
        allTasks.append("sendAllToSupport")

    # Register tasks depending on type of installation
    now = datetime.datetime.now()
    timestamp = now.strftime("%I:%M")

    # SyncSystemInfo should be started after snapshotStandby - so adding additional 3 mins
    syncTime = now + datetime.timedelta(minutes = 3)
    syncTime = syncTime.strftime("%I:%M")
    rmanEnabledTask = mstarpaths.interpretFormat("{_RMAN_ENABLED_TASK}")

    for taskName in allTasks:
        repeat = 0

        # Register 'exportDataStores' Tasks
        if taskName == "exportDataStores":
            taskParams = "all"
            tempTime = mstarpaths.interpretFormat("{DBEXPORT_START}")
            scheduleTime = tempTime[-5:]
            scheduleFrequency = "DAILY"
            updateTaskPath(taskName, taskParams)

        #Register 'snapshotSystem' Tasks
        elif taskName == "snapshotSystem":
            includeDXFAndOnboard = mstarpaths.interpretVar("SNAPSHOT_INCLUDE_DXF_AND_ONBOARD")
            if includeDXFAndOnboard == "true":
                taskParams = "-d -o AUTO"
            else:
                taskParams = "AUTO"
            scheduleTime = mstarpaths.interpretFormat("{SNAPSHOT_SYSTEM_START}")
            scheduleFrequency = "DAILY"
            updateTaskPath(taskName, taskParams)
            # Register 'snapshotStandby' Task for Application Server
            if roles[0] == "AppServer":
                taskParams = "-d -o -s STANDBY"
                scheduleTime = timestamp
                scheduleFrequency = "MINUTE"
                repeat = mstarpaths.interpretFormat("{SNAPSHOT_STANDBY_START}")
                updateTaskPath(taskName, taskParams, taskName+'Standby')

        # Register 'syncStandbyInformation' Task , Start time will be 3 minutes after SNAPSHOT_STANDBY_STARTTime
        if taskName == "syncStandbyInformation":
            if not ServerTools.isStandbyDbRole():
                taskParams = "-s -i config,updates,onboard,data"
                scheduleFrequency = "MINUTE"
                scheduleTime = syncTime
                startInterval = mstarpaths.interpretFormat("{SYNC_STANDBY_START}")
                updateTaskPath(taskName, taskParams)

        # Register 'rmanToolsFullDB' Task
        elif ((rmanEnabledTask == "true") and (taskName == "rmanToolsFullDB")):
            taskParams = "-dFullDBBackup -o"+ mstarpaths.interpretFormat("{_MSTAR_RMAN_BASE_DIR}")
            scheduleTime = mstarpaths.interpretFormat("{_ADMIN_RMAN_FULL_DB_BACKUP_TIME}")
            repeat = mstarpaths.interpretFormat("{_ADMIN_RMAN_FULL_DB_BACKUP_FREQUENCY}")
            scheduleFrequency = "WEEKLY"
            taskName = "rmanTools"
            updateTaskPath(taskName, taskParams, taskName+'FullDB')

        # Register 'rmanToolsIncrDB' Task
        elif ((rmanEnabledTask == "true") and (taskName == "rmanToolsIncrDB")):
            taskParams = "-dIncrDBBackup -o"+ mstarpaths.interpretFormat("{_MSTAR_RMAN_BASE_DIR}")
            scheduleTime = mstarpaths.interpretFormat("{_ADMIN_RMAN_INCR_DB_BACKUP_TIME}")
            scheduleFrequency = "Hourly"
            repeat = mstarpaths.interpretFormat("{_ADMIN_RMAN_INCR_DB_BACKUP_FREQUENCY}")
            taskName = "rmanTools"
            updateTaskPath(taskName, taskParams, taskName+'IncrDB')

        # Register 'rmanToolsArcDB' Task
        elif ((rmanEnabledTask == "true") and (taskName == "rmanToolsArcDB")):
            taskParams = "-dArchiveDBBackup -o"+ mstarpaths.interpretFormat("{_MSTAR_RMAN_BASE_DIR}")
            scheduleTime = mstarpaths.interpretFormat("{_ADMIN_RMAN_ARC_DB_BACKUP_TIME}")
            scheduleFrequency = "HOURLY"
            repeat = mstarpaths.interpretFormat("{_ADMIN_RMAN_ARC_DB_BACKUP_FREQUENCY}")
            taskName = "rmanTools"
            updateTaskPath(taskName, taskParams, taskName+'ArcDB')

        # Register 'purgeRecycleBin' Task
        elif ((taskName == "purgeRecycleBin") and (mstarpaths.interpretVar("_INSTANCE1_TYPE") == "oracle")):
            taskParams = "_MODELDB,_HISTORICALDB,_SUMMARYDB,_PITMODELDB,_PERFMONITORDB,_REPORTINGDB,_TEMPLATEDB,_GISDB"
            scheduleTime = mstarpaths.interpretFormat("{_ADMIN_PURGE_RECYCLE_BIN_TIME}")
            scheduleFrequency = "MONTHLY"
            repeat = mstarpaths.interpretFormat("{_ADMIN_PURGE_RECYCLE_BIN_FREQUENCY}")
            updateTaskPath(taskName, taskParams)

        # Register 'snapshotOs' Task
        if taskName == "snapshotOs":
            taskParams = "H"
            startInterval= int(mstarpaths.interpretFormat("{SNAPSHOT_OS_START}"))
            startTime = now + datetime.timedelta( hours=1, minutes= startInterval)
            scheduleTime = startTime.strftime("%I:%M")
            scheduleFrequency = "hourly"
            updateTaskPath(taskName, taskParams)

	    # Register 'cleanExpiredFiles' Task
        elif taskName == "cleanExpiredFiles":
            taskParams = ""
            scheduleTime = mstarpaths.interpretFormat("{_ADMINTIDY_START}")
            scheduleFrequency = "Daily"
            updateTaskPath(taskName, taskParams)

        # Register 'cleanExpiredData' Task
        elif taskName == "cleanExpiredData":
            taskParams = ""
            scheduleTime = mstarpaths.interpretFormat("{_ADMINDATA_START}")
            scheduleFrequency = "DAILY"
            updateTaskPath(taskName, taskParams)

        # Register 'sendAllToSupport' Task
        elif taskName == "sendAllToSupport":
            taskParams = "FTP"
            scheduleTime = timestamp
            startInterval = int(mstarpaths.interpretFormat("{SEND_ALL_START}"))
            syncTime = now + datetime.timedelta(minutes = startInterval)
            syncTime = syncTime.strftime("%I:%M")
            scheduleFrequency = "hourly"
            updateTaskPath(taskName, taskParams)

    print "Update Schedule Task Completed - Check the windows Task Scheduler"

def makeScheduledTasks(roles):
    # Work out the Tasks to be registered from the list of roles
    allTasks = []
    for role in roles:
        roleTasks = ALL_TASKS.get(role)
        for task in roleTasks:
            found = 0
            for regTask in allTasks:
                #check if same task already added for diff role.
                if task == regTask:
                    found = 1
            if found == 0:
                allTasks.append(task)

    # If this computer is configured for FTP, register sendAllToSupport as a task
    ftpComputer = mstarpaths.interpretFormat("{_FTPSERVER}")
    thisComputer = mstarpaths.interpretFormat("{COMPUTERNAME}")
    if ftpComputer.upper() == thisComputer.upper():
        allTasks.append("sendAllToSupport")

    # Register tasks depending on type of installation
    now = datetime.datetime.now()
    timestamp = now.strftime("%I:%M")

    # SyncSystemInfo should be started after snapshotStandby - so adding additional 3 mins
    syncTime = now + datetime.timedelta(minutes = 3)
    syncTime = syncTime.strftime("%I:%M")
    rmanEnabledTask = mstarpaths.interpretFormat("{_RMAN_ENABLED_TASK}")

    for taskName in allTasks:
        repeat = 0

        # Register 'exportDataStores' Tasks
        if taskName == "exportDataStores":
            taskParams = "all"
            tempTime = mstarpaths.interpretFormat("{DBEXPORT_START}")
            scheduleTime = tempTime[-5:]
            scheduleFrequency = "DAILY"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency)

        #Register 'snapshotSystem' Tasks
        elif taskName == "snapshotSystem":
            includeDXFAndOnboard = mstarpaths.interpretVar("SNAPSHOT_INCLUDE_DXF_AND_ONBOARD")
            if includeDXFAndOnboard == "true":
                taskParams = "-d -o AUTO"
            else:
                taskParams = "AUTO"
            scheduleTime = mstarpaths.interpretFormat("{SNAPSHOT_SYSTEM_START}")
            scheduleFrequency = "DAILY"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency)
            # Register 'snapshotStandby' Task for Application Server
            if roles[0] == "AppServer":
                taskParams = "-d -o -s STANDBY"
                scheduleTime = timestamp
                scheduleFrequency = "MINUTE"
                repeat = mstarpaths.interpretFormat("{SNAPSHOT_STANDBY_START}")
                _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency, None, repeat, taskName+'Standby')

        # Register 'syncStandbyInformation' Task , Start time will be 3 minutes after SNAPSHOT_STANDBY_STARTTime
        if taskName == "syncStandbyInformation":
            if not ServerTools.isStandbyDbRole():
                taskParams = "-s -i config,updates,onboard,data"
                scheduleFrequency = "MINUTE"
                scheduleTime = syncTime
                startInterval = mstarpaths.interpretFormat("{SYNC_STANDBY_START}")
                _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency, None,startInterval)

        # Register 'rmanToolsFullDB' Task
        elif ((rmanEnabledTask == "true") and (taskName == "rmanToolsFullDB")):
            taskParams = "-d FullDBBackup -o "+ mstarpaths.interpretFormat("{_MSTAR_RMAN_BASE_DIR}")
            scheduleTime = mstarpaths.interpretFormat("{_ADMIN_RMAN_FULL_DB_BACKUP_TIME}")
            repeat = mstarpaths.interpretFormat("{_ADMIN_RMAN_FULL_DB_BACKUP_FREQUENCY}")
            scheduleFrequency = "WEEKLY"
            taskName = "rmanTools"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency,None , repeat, taskName+'FullDB')

        # Register 'rmanToolsIncrDB' Task
        elif ((rmanEnabledTask == "true") and (taskName == "rmanToolsIncrDB")):
            taskParams = "-d IncrDBBackup -o "+ mstarpaths.interpretFormat("{_MSTAR_RMAN_BASE_DIR}")
            scheduleTime = mstarpaths.interpretFormat("{_ADMIN_RMAN_INCR_DB_BACKUP_TIME}")
            scheduleFrequency = "Hourly"
            repeat = mstarpaths.interpretFormat("{_ADMIN_RMAN_INCR_DB_BACKUP_FREQUENCY}")
            taskName = "rmanTools"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency, None, repeat, taskName+'IncrDB')

        # Register 'rmanToolsArcDB' Task
        elif ((rmanEnabledTask == "true") and (taskName == "rmanToolsArcDB")):
            taskParams = "-d ArchiveDBBackup -o "+ mstarpaths.interpretFormat("{_MSTAR_RMAN_BASE_DIR}")
            scheduleTime = mstarpaths.interpretFormat("{_ADMIN_RMAN_ARC_DB_BACKUP_TIME}")
            scheduleFrequency = "HOURLY"
            repeat = mstarpaths.interpretFormat("{_ADMIN_RMAN_ARC_DB_BACKUP_FREQUENCY}")
            taskName = "rmanTools"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency, None, repeat, taskName+'ArcDB')

        # Register 'purgeRecycleBin' Task
        elif ((taskName == "purgeRecycleBin") and (mstarpaths.interpretVar("_INSTANCE1_TYPE") == "oracle")):
            taskParams = "_MODELDB,_HISTORICALDB,_SUMMARYDB,_PITMODELDB,_PERFMONITORDB,_REPORTINGDB,_TEMPLATEDB,_GISDB"
            scheduleTime = mstarpaths.interpretFormat("{_ADMIN_PURGE_RECYCLE_BIN_TIME}")
            scheduleFrequency = "MONTHLY"
            repeat = mstarpaths.interpretFormat("{_ADMIN_PURGE_RECYCLE_BIN_FREQUENCY}")
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency, None, repeat)

        # Register 'snapshotOs' Task
        if taskName == "snapshotOs":
            taskParams = "H"
            startInterval= int(mstarpaths.interpretFormat("{SNAPSHOT_OS_START}"))
            startTime = now + datetime.timedelta( hours=1, minutes= startInterval)
            scheduleTime = startTime.strftime("%I:%M")
            scheduleFrequency = "hourly"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency,None, repeat)

	    # Register 'cleanExpiredFiles' Task
        elif taskName == "cleanExpiredFiles":
            taskParams = ""
            scheduleTime = mstarpaths.interpretFormat("{_ADMINTIDY_START}")
            scheduleFrequency = "Daily"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency)

        # Register 'cleanExpiredData' Task
        elif taskName == "cleanExpiredData":
            taskParams = ""
            scheduleTime = mstarpaths.interpretFormat("{_ADMINDATA_START}")
            scheduleFrequency = "DAILY"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency)

        # Register 'sendAllToSupport' Task
        elif taskName == "sendAllToSupport":
            taskParams = "FTP"
            scheduleTime = timestamp
            startInterval = int(mstarpaths.interpretFormat("{SEND_ALL_START}"))
            syncTime = now + datetime.timedelta(minutes = startInterval)
            syncTime = syncTime.strftime("%I:%M")
            scheduleFrequency = "hourly"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency)

        # Register 'dbHealthMonitor' Task
        elif ((taskName == "dbHealthMonitor") and (mstarpaths.interpretVar("_INSTANCE1_TYPE") == "oracle")):
            taskParams = ""
            scheduleTime = mstarpaths.interpretFormat("{_DB_HEALTH_MONITOR_TIME}")
            scheduleFrequency = "DAILY"
            _regScheduledTask(taskName, taskParams, scheduleTime, scheduleFrequency)

    print "Make Schedule Task Completed - Check the windows Task Scheduler"


## Main program ##

def _printUsage():
    print "usage: makeScheduledTasks [options] all"
    print "       makeScheduledTasks [options] machineRole1 machineRole2 ..."
    print "       Available machines roles: AppServer DbServer Client Detect"
    print "       makeScheduledTasks update"

def run(task):
    import sys
    roles = task
    if sys.platform.startswith("win"):
        if "update" in task:
            roles = ["AppServer","DbServer","Client"]
            updateTask(roles)
            print "Successfully updated all the existing Scheduled Tasks"
            sys.exit(0)

        if "all" in task:
            roles = ["AppServer","DbServer","Client"]
        elif not set(ALL_TASKS.keys()).issuperset(set(task)):
            _printUsage()
            sys.exit(0)
        makeScheduledTasks(roles)
    else:
        print "       Ignoring makeScheduledTasks for UNIX based system"

def main():
    # Check usage
    args = sys.argv[1:]
    if len(args) < 1:
        _printUsage()
        sys.exit(0)
    # Parse the options
    mstarpaths.loadMineStarConfig()

    while len(args) > 0 and args[0].startswith("-"):
        args = args[1:]
    # Make the tasks
    if len(args) > 0:
        roles = args[0:]
        run(roles)
    else:
        _printUsage()
        sys.exit(1)

if __name__ == '__main__':
    main()
