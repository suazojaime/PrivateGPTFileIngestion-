#  Copyright (c) 2020-2024 Caterpillar

# Starts and stops the system as windows services
#
# In this script, appName refers to the application names such as MineTracking, StandardJobExecutor, etc as defined
# in the _START environment variable in MineStar.properties. An appName is converted to serviceName by prepending
# "M*". It is converted to a service configuration file name by suffixing "Service.conf".

import datetime
import os
import re
import subprocess
import sys
import time

import minestar
import mstarpaths
import mstarrun
import mstarrunlib
from postgisControl import PostgisControl

# The collection of all possible app names. The services to start should be a subset of these app names,
# although new app names may be added in the future before this lists gets updated.
ALL_APP_NAMES = [
    "CommsServer", "FsbServer", "GeoDatabase", "GeoServer", "MineTracking",
    "PathPlanner", "CommsController", "CyclesKpiSummaries", "CycleGenerator",
    "IAssignmentServer", "StandardJobExecutor", "Jetty", "WebFeatureService", "FieldInformationService", "FieldInformationService2", "ApexServer"
]

# The location of the service configuration directory.
SERVICE_CONFIG_DIR = "{MSTAR_CONFIG}/service"

# The name of the GeoDatabase application.
GEODATABASE_APP_NAME = "GeoDatabase"
GEODATABASE_SERVICE_NAME = "M*GeoDatabase"

# The timeout period (in minutes) for starting and stopping Windows services.
# Change with the '--timeout' option.
timeoutInMinutes = 10

logger = minestar.initApp()


def reversed(v=[]):
    """Return a reversed copy of the list."""
    copy = list(v)
    copy.reverse()
    return copy


class ServiceStatusCode:

    """Class representing service status codes."""

    NOT_INSTALLED = 1060      # Service is not installed.


class ServiceStatus:

    """Class representing windows service states."""

    def __init__(self, name):
        if name is None:
            raise ValueError("No 'name' specified")
        self._name = name

    def __repr__(self):
        return self._name

    @property
    def name(self):
        return self._name

    def isStartable(self):
        """Returns True if the status indicates that the service is startable, e.g can request start."""
        return self in [ServiceStatus.STOPPED, ServiceStatus.STOP_PENDING,
                        ServiceStatus.PAUSED, ServiceStatus.PAUSE_PENDING]

    def isStarting(self):
        """Returns True if the status indicates that the service is starting (but not yet running). Given
           sufficient time the service will eventually start."""
        return self in [ServiceStatus.START_PENDING, ServiceStatus.CONTINUE_PENDING]

    def isStoppable(self):
        """Returns True if the status indicates that the service is stoppable, e.g. the state can
           transition to STOPPED."""
        return self not in [ServiceStatus.UNKNOWN, ServiceStatus.STOP_PENDING, ServiceStatus.STOPPED]

    def isStopping(self):
        """Returns True if the status indicates that the service is stopping (but not yet stopped). Given
           sufficient time, the service will eventually stop."""
        return self in [ServiceStatus.STOP_PENDING]

    @classmethod
    def fromStatusCode(cls, statusCode):
        """ Get a ServiceStatus instance from a status code. """
        # See: See https://msdn.microsoft.com/en-us/library/windows/desktop/ee126211.aspx
        map = {
            1: ServiceStatus.STOPPED,
            2: ServiceStatus.START_PENDING,
            3: ServiceStatus.STOP_PENDING,
            4: ServiceStatus.RUNNING,
            5: ServiceStatus.CONTINUE_PENDING,
            6: ServiceStatus.PAUSE_PENDING,
            7: ServiceStatus.PAUSED,
        }
        if statusCode is None:
            raise ValueError("No 'statusCode' specified")
        return map.get(statusCode, ServiceStatus.UNKNOWN)

# ServiceStatus enums.
ServiceStatus.START_PENDING = ServiceStatus("start_pending")
ServiceStatus.RUNNING = ServiceStatus("running")
ServiceStatus.PAUSE_PENDING = ServiceStatus("pause_pending")
ServiceStatus.PAUSED = ServiceStatus("paused")
ServiceStatus.CONTINUE_PENDING = ServiceStatus("continue_pending")
ServiceStatus.CONTINUE = ServiceStatus("continue")
ServiceStatus.STOP_PENDING = ServiceStatus("stop_pending")
ServiceStatus.STOPPED = ServiceStatus("stopped")
ServiceStatus.UNKNOWN = ServiceStatus("unknown")


def regenerateServices():
    """Regenerates the config and property files for each of the services defined by the _START mstarrun variable."""
    _exitIfNotApplicationServer()
    _exitIfWindowsServicesNotEnabled()
    # Skip GeoDatabase as it doesn't need a service config file
    appsNeedingServiceConfig = [x for x in _appNames() if x != GEODATABASE_APP_NAME]
    # Generate a service config for each app that requires it.
    for appName in appsNeedingServiceConfig:
        _regenerateServiceConfig(appName)


def _regenerateServiceConfig(appName):
    createServiceFileCommand = "-ws %s" % appName
    mstarrunlib.run(createServiceFileCommand)


def installServices():
    """Install the windows services for a system. The list of services to run are those defined
       by the _START mstarrun variable."""
    _exitIfNotApplicationServer()
    _exitIfWindowsServicesNotEnabled()
    for appName in _appNames():
        _installService(appName)


def reinstallServices():
    """Reinstall the windows services for a system. The list of services to run are those defined
       by the _START mstarrun variable."""
    _exitIfNotApplicationServer()
    _exitIfWindowsServicesNotEnabled()
    removeAllServices()
    installServices()


def _installService(appName, printQueryResult=True):
    """Install the service for an application, if not already installed. Returns (status,exitCode). """
    serviceName = _serviceName(appName)
    (serviceStatus, exitCode) = _queryService(serviceName, printResult=printQueryResult)
    if exitCode == ServiceStatusCode.NOT_INSTALLED:
        if appName == GEODATABASE_APP_NAME:
            startMode = mstarpaths.interpretVar("_WINDOWS_SERVICES_START_MODE")
            startAutomatically = startMode != "Manual"
            postgis = PostgisControl()
            postgis.registerService(GEODATABASE_SERVICE_NAME, startAutomatically)
        else:
            _regenerateServiceConfig(appName)
            _servicectrl("install", [_appConfFile(appName)])
            # Enable the Service / Recovery / Enable actions for stops with errors flag
            subprocess.check_output(["sc", "failureflag", serviceName, "1"])
        (serviceStatus, exitCode) = _queryService(serviceName, printResult=False)
    return (serviceStatus, exitCode)


def removeServices():
    """Remove the windows services for a system. The list of services to run are those defined
       by the _START mstarrun variable."""
    _exitIfNotApplicationServer()
    removeAllServices()


def _removeServices(serviceNames, printQueryResult=True):
    """Remove multiple windows services"""
    for serviceName in serviceNames:
        _removeService(serviceName, printQueryResult=printQueryResult)


def _removeService(serviceName, printQueryResult=True):
    """Remove a single windows service"""
    # Check if the service is installed.
    (serviceStatus, exitCode) = _queryService(serviceName, printResult=printQueryResult)
    if exitCode == ServiceStatusCode.NOT_INSTALLED:
        # Nothing to do
        return (serviceStatus, exitCode)

    # Stop the service if required.
    if serviceStatus.isStoppable():
        _stopService(serviceName, waitTillStopped=True, printQueryResult=printQueryResult)

    # Special case: Use pg_ctl to unregister M*GeoDatabase
    if serviceName.endswith(GEODATABASE_APP_NAME):
        postgis = PostgisControl()
        postgis.unregisterService(GEODATABASE_SERVICE_NAME)
        (serviceStatus, exitCode) = _queryService(serviceName, printResult=printQueryResult)
        if exitCode == ServiceStatusCode.NOT_INSTALLED:
            # Done
            return (serviceStatus, exitCode)

    # Remove the service.
    subprocess.call(['sc', 'delete', serviceName])

    # Return the service state.
    return _queryService(serviceName, printResult=printQueryResult)


def _servicectrl(action, appConfFiles):
    workingDirectory = mstarpaths.interpretPath("{MSTAR_LOGS}")
    wrapperExe = mstarpaths.interpretPath("{MSTAR_BIN}\wrapper.exe")
    dateTimeStr = datetime.datetime.now().strftime('%Y%d%m%H%M%S')
    serviceControlCmd = mstarpaths.interpretPath("{MSTAR_BIN}\servicectrl.exe") + " %s %s %s %s %s" % \
        (dateTimeStr, action, workingDirectory, wrapperExe, " ".join(appConfFiles))
    mstarrun.run(serviceControlCmd)
    try:
        with open(mstarpaths.interpretPath("{MSTAR_LOGS}\\servicectrl_" + dateTimeStr + ".log"), "r") as servicectrlLog:
            content = servicectrlLog.readlines()
            print " ".join(content)
    except Exception as e:
        print "failed to communicate with servicectrl sub-process: %s" % e

    sys.stdout.flush()


def isServiceInstalled(serviceName):
    workingDirectory = mstarpaths.interpretPath("{MSTAR_LOGS}")
    wrapperExe = mstarpaths.interpretPath("{MSTAR_BIN}\wrapper.exe")
    dateTimeStr = datetime.datetime.now().strftime('%Y%d%m%H%M%S')
    suffix = "%s_installed_%s" % (dateTimeStr, serviceName)
    logfilePath = mstarpaths.interpretPath("{MSTAR_LOGS}\\servicectrl_%s.log" % suffix)
    # Remove the existing log file, if it exists.
    if os.path.exists(logfilePath):
        os.remove(logfilePath)
    # Run the service control command.
    serviceControlCmd = mstarpaths.interpretPath("{MSTAR_BIN}\servicectrl.exe") + " %s isInstalled %s %s %s" % \
                                                (suffix, workingDirectory, wrapperExe, serviceName)
    mstarrun.run(serviceControlCmd)
    try:
        with open(logfilePath, 'r') as servicectrlLog:
            return any(line for line in servicectrlLog.readlines() if "exists" in line)
    except Exception:
        return False


def startServices():
    """Start the windows services for a system. The list of services to run are those defined by
       the _START mstarrun variable. If necessary, the services are installed."""
    _exitIfNotApplicationServer()
    _exitIfWindowsServicesNotEnabled()
    _startServices(_serviceNames(_appNames()))


def _startServices(serviceNames, printQueryResult=True):
    pendingServices = []
    # check for any process which have not yet shutdown
    startupFailures = 0

    for serviceName in serviceNames:
        # Start services in parallel EXCEPT for M*MineTracking,M*FsbServer,M*Geodatabase
        waitTillStarted = serviceName == "M*MineTracking" or serviceName == "M*FsbServer" or serviceName == ("M*" + GEODATABASE_APP_NAME)
        (serviceStatus, exitCode) = _startService(serviceName=serviceName, waitTillStarted=waitTillStarted, printQueryResult=printQueryResult)
        # If the service is not running: it either failed, or is pending.
        if serviceStatus != ServiceStatus.RUNNING:
            if exitCode != 0:
                startupFailures += 1
            else:
                pendingServices.append(serviceName)

    # If there are no startup failures, then wait for the pending services to start.
    if startupFailures == 0 and pendingServices:
        startupFailures = _waitForServicesToHaveStatus(pendingServices, ServiceStatus.RUNNING)

    if startupFailures == 0:
        sys.stdout.write("\n\nAll services started successfully.")
    else:
        count = "All" if startupFailures == len(serviceNames) else "Some"
        sys.stdout.write("\n\n%s services FAILED to start." % count)


def _startService(serviceName, waitTillStarted=False, printQueryResult=True):
    (serviceStatus, exitCode) = _queryService(serviceName, printResult=printQueryResult)
    if serviceStatus.isStartable():
        sys.stdout.write("Starting service %s...\n" % serviceName)
        try:
            subprocess.check_output(["sc", "start", serviceName])
            if waitTillStarted:
                _waitForServicesToHaveStatus([serviceName], ServiceStatus.RUNNING)
                (serviceStatus, exitCode) = _queryService(serviceName, printResult=False)
                if exitCode != 0:
                    sys.stdout.write("\nFailed to start service: %s\n" % serviceName)
        except Exception as e:
            sys.stdout.write("\nFailed to start service: %s %s\n" % (serviceName, e))
            (serviceStatus, exitCode) = (ServiceStatus.UNKNOWN, -1)
    return (serviceStatus, exitCode)


def _waitForServicesToHaveStatus(serviceNames, wantedStatus):
    pendingServiceNames = list(serviceNames)
    startupFailures = 0
    if len(pendingServiceNames) > 0:

        def getNextTimeout():
            return datetime.datetime.now() + datetime.timedelta(minutes=timeoutInMinutes)

        class ServiceRequest(object):

            def __init__(self, name, initialStatus):
                self.name = name
                self.initialStatus = initialStatus
                self.timeout = getNextTimeout()

            def hasTimedOut(self):
                return datetime.datetime.now() > self.timeout

        def showPendingServicesStatus():
            if len(pendingServiceNames) > 0:
                sys.stdout.write("\nWaiting for %d service(s) to be %s: %s " %
                                 (len(pendingServiceNames), wantedStatus, pendingServiceNames))
                sys.stdout.flush()

        def removePendingService(s):
            pendingServiceNames.remove(s)
            showPendingServicesStatus()

        def createServiceRequest(serviceName):
            (status, exitCode) = _queryService(serviceName)
            return ServiceRequest(name=serviceName, initialStatus=status)

        # Create a service request for each service.
        requests = {x: createServiceRequest(x) for x in serviceNames}

        showPendingServicesStatus()
        dotCounter = 1

        while len(pendingServiceNames) > 0:
            for serviceName in pendingServiceNames:
                request = requests[serviceName]
                # Get the status of the service.
                (serviceStatus, exitCode) = _queryService(serviceName)
                # If the wanted status matches the current status -> success
                if serviceStatus == wantedStatus:
                    sys.stdout.write("\n%s is %s\n" % (serviceName, serviceStatus))
                    removePendingService(serviceName)
                # If wanting service to run but service has error -> fail.
                elif wantedStatus == ServiceStatus.RUNNING and exitCode > 0:
                    if exitCode == ServiceStatusCode.NOT_INSTALLED:
                        msg = "Failed to start service %s: not installed" % serviceName
                    else:
                        msg = "Failed to start service %s: exit code %d" % (serviceName, exitCode)
                    sys.stdout.write("\n%s\n" % msg)
                    removePendingService(serviceName)
                    startupFailures = startupFailures + 1
                # If the service request has timed out -> fail (unless transitioning from non-PENDING to PENDING).
                elif request.hasTimedOut():
                    if wantedStatus == ServiceStatus.STOPPED:
                        # Reset timeout if transitioning from non-STOPPING to STOPPING (allow more time to stop).
                        if not request.initialStatus.isStopping() and serviceStatus.isStopping():
                            sys.stdout.write("\nService %s is %s ... resetting timeout.\n" % (serviceName, serviceStatus))
                            request.timeout = getNextTimeout()
                            continue
                    if wantedStatus == ServiceStatus.RUNNING:
                        # Reset timeout if transitioning from non-STARTING to STARTING (allow more time to start).
                        if not request.initialStatus.isStarting() and serviceStatus.isStarting():
                            sys.stdout.write("\nService %s is %s ... resetting timeout.\n" % (serviceName, serviceStatus))
                            request.timeout = getNextTimeout()
                            continue
                    # Otherwise the service status is not PENDING and timeout has expired, so fail.
                    sys.stdout.write("\nService %s has timed out.\n" % serviceName)
                    removePendingService(serviceName)
                    startupFailures = startupFailures+1

            # Sleep for a bit if there are still services pending.
            if len(pendingServiceNames) > 0:
                # Show a dot every 5 seconds.
                dotCounter += 1
                if (dotCounter % 5) == 0:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                    dotCounter = 0
                time.sleep(1)

    return startupFailures


def stopServices():
    """Stop the windows services for a system. The list of services to run are those defined by
       the _START mstarrun variable."""
    _exitIfWindowsServicesNotEnabled()
    # Stop the services in the reverse order from which they were started.
    _stopServices(reversed(_serviceNames(_appNames())))


def updateServices(asNeeded=False):
    """If windows services are enabled reinstall the services, otherwise remove them"""
    _exitIfNotApplicationServer()
    if isWindowsServicesEnabled():
        if asNeeded:
            _updateServicesAsNeeded()
        else:
            reinstallServices()
    else:
        removeAllServices()


def _updateServicesAsNeeded():
    """Updates services, installing a configured service if not installed, and
       removing an installed service that is not configured.
       It will not touch a configured service that is installed and running."""
    configured = _appNames()
    for appName in ALL_APP_NAMES:
        if appName in configured:
            _installService(appName)
        else:
            _removeService(_serviceName(appName))


def _stopServices(serviceNames):
    print "Performing automatic thread dump before system shutdown"
    mstarrun.run(["-b", "InvokeThreadDumps"])

    for serviceName in serviceNames:
        _stopService(serviceName, waitTillStopped=True)


def _stopService(serviceName, waitTillStopped=False, printQueryResult=True):
    (serviceStatus, exitCode) = _queryService(serviceName=serviceName, printResult=printQueryResult)
    if serviceStatus.isStoppable():
        sys.stdout.write("Stopping service %s...\n" % serviceName)
        try:
            subprocess.check_output(["sc", "stop", serviceName])
            if waitTillStopped:
                _waitForServicesToHaveStatus([serviceName], ServiceStatus.STOPPED)
            (serviceStatus, exitCode) = _queryService(serviceName=serviceName, printResult=False)
            if exitCode != 0:
                sys.stdout.write("Failed to stop service %s\n" % serviceName)
        except Exception as e:
            sys.stdout.write("Failed to stop service %s: %s\n" % (serviceName, e))
            (serviceStatus, exitCode) = (ServiceStatus.UNKNOWN, -1)
    return (serviceStatus, exitCode)

def queryServices():
    """Query the current status of the MineStar windows services"""
    _exitIfNotApplicationServer()
    _exitIfWindowsServicesNotEnabled()
    _queryServices(_serviceNames(_appNames()))


def _queryServices(serviceNames):
    for serviceName in serviceNames:
        _queryService(serviceName, True)


def _queryService(serviceName, printResult=False):
    """Query the Windows service, optionally printing the result."""
    state = ServiceStatus.UNKNOWN
    exitCode = -1
    try:
        cmdOut = subprocess.check_output(["sc", "query", serviceName])
        # Expected output format: "    STATE    : 1 STOPPED"
        # print cmdOut
        stateMatch = re.search("\s+STATE\s+:\s+(\d+)\s+(\w+)", cmdOut)
        if stateMatch:
            state = ServiceStatus.fromStatusCode(int(stateMatch.group(1)))
        exitCodeMatch = re.search("\s+SERVICE_EXIT_CODE\s+:\s+(\d+)\s+", cmdOut)
        if exitCodeMatch:
            exitCode = int(exitCodeMatch.group(1))
        if exitCode == -1:
            exitCodeMatch = re.search("\s+WIN32_EXIT_CODE\s+:\s+(\d+)\s+", cmdOut)
            if exitCodeMatch:
                exitCode = int(exitCodeMatch.group(1))
    except subprocess.CalledProcessError as e:
        # Leave state as UNKNOWN
        exitCode = e.returncode
    except Exception as e:
        # Leave (state,exitCode) as (UNKNOWN,-1)
        print "EXCEPTION : %s" % e

    if printResult:
        if exitCode == 0:
            sys.stdout.write("%s is %s\n" % (serviceName, state))
        elif exitCode == ServiceStatusCode.NOT_INSTALLED:
            sys.stdout.write("%s is not installed\n" % serviceName)
        else:
            sys.stdout.write("%s is %s [%d]\n" % (serviceName, state, exitCode))

    return state, exitCode


def isWindowsServicesEnabled():
    import ServerTools
    windowsServicesEnabled = mstarpaths.interpretVar("_WINDOWS_SERVICES_ENABLED")
    return ServerTools.onAppServer() and windowsServicesEnabled == "true"


def _exitIfNotApplicationServer():
    import ServerTools
    if not ServerTools.onAppServer():
        msg = "Windows services command(s) can be used on application server only."
        print msg
        minestar.logit(msg)
        minestar.exit()


def _exitIfWindowsServicesNotEnabled():
    if not isWindowsServicesEnabled():
        msg = "Windows services is not enabled. (It can be enabled in Supervisor->Platform->System->Services by checking 'Run as Windows Services'.)"
        print msg
        minestar.logit(msg)
        minestar.exit()


def _appNames():
    """Return the list of enabled MineStar applications."""
    configuredApps = mstarpaths.interpretVar("_START") or ""
    return [x.strip() for x in configuredApps.split(",")]


def _possibleAppNames():
    """Return the list of possible MineStar applications."""
    # Create the union of all known app names + the enabled app names (in case new apps are added).
    possibles = ALL_APP_NAMES[:]
    for appName in _appNames():
        if appName not in possibles:
            possibles.append(appName)
    return possibles


def _appConfFile(appName):
    """Return the name of the Windows service configuration file for the given MineStar application."""
    return mstarpaths.interpretPath("%s/%sService.conf" % (SERVICE_CONFIG_DIR, appName))


def _serviceName(appName):
    """Return the name of the Windows service for the given MineStar application"""
    return "M*" + appName


def _serviceNames(appNames):
    """Return the names of the Windows services for the given MineStar applications"""
    return [_serviceName(x) for x in appNames]


def removeAllServices():
    """Remove all Windows services for MineStar applications"""
    # Remove the services in the reverse order from which they were started.
    _removeServices(reversed(_serviceNames(_possibleAppNames())))


def _getChoicesList(choicesListName):
    command = ["getChoicesList", choicesListName]
    # debug mode interferes with interpreting the results
    # mstardebug is probably already loaded, so get rid of it to force reloading from the new file
    del sys.modules["mstardebug"]
    import mstardebug
    if mstardebug.debug:
        print "************************************************"
        print "WARNING: debug is on - windowsServices._getChoicesList will fail"
        print "************************************************"
        minestar.logit("************************************************")
        minestar.logit("WARNING: debug is on - windowsServices._getChoicesList will fail")
        minestar.logit("************************************************")
    output = minestar.mstarrunEvalRaw(command)
    print "Output from getChoicesList follows..."
    print output
    if output == "(no output)":
        choiceList = None
    else:
        choiceList = output[len(output) - 1]
    # print "Last line is '%s'" % choiceList
    return choiceList


def main(appConfig=None):
    """Entry point when called from mstarrun"""

    def showUsage():
        print "Usage: windowsServices [--timeout <minutes>] start|stop|query|install|update|reinstall|regenerate|remove|removeAll"

    def showHelp():
        print "Performs windows services for MineStar."
        showUsage()

    def getOptsAndArgs():
        import getopt
        try:
            longOpts = ["timeout=", "help"]
            return getopt.getopt(sys.argv[1:], shortopts=[], longopts=longOpts)
        except getopt.GetoptError as e:
            print "*** Error: %s ***" % e
            showUsage()
            return (None, None)

    (options, args) = getOptsAndArgs()

    if options is None and args is None:
       minestar.exit(1)

    # Check if showing help.
    for (name, value) in options:
        if name == '--help':
            showHelp()
            minestar.exit(1)

    mstarpaths.loadMineStarConfig()
    _exitIfNotApplicationServer()

    # Check for options.
    for (name, value) in options:
        if name == '--timeout':
            global timeoutInMinutes
            timeoutInMinutes = int(value)
        else:
            print "Error: Invalid option %s" % name
            showUsage()
            minestar.exit(1)

    # Make sure an argument was specified.
    if len(args) != 1:
        showUsage()
        minestar.exit(1)

    arg = args[0]
    if arg == "start":
        startServices()
    elif arg == "stop":
        stopServices()
    elif arg == "update":
        updateServices()
    elif arg == "query":
        queryServices()
    elif arg == "install":
        installServices()
    elif arg == "reinstall":
        installServices()
    elif arg == "remove":
        removeServices()
    elif arg == "removeAll":
        removeAllServices()
    elif arg == "regenerate":
        regenerateServices()
    else:
        print "Error: invalid argument '%s'" % arg
        showUsage()
        minestar.exit(1)

    minestar.exit(0)


if __name__ == "__main__":
    """entry point when called from python"""
    main()
