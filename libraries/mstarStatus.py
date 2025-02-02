import sys
import re

class MStarStatus(object):

    NOT_RUNNING = "not-running"
    SERVICES_RUNNING = "services-running"
    PROCESSES_RUNNING = "processes-running"
    UNKNOWN = "unknown"

class MStarStatusChecker(object):

    """ Class for determining the M* run status. """

    def __init__(self):
        if sys.platform.startswith('win'):
            self._provider = WindowsMStarStatusProvider()
        elif sys.platform.contains('nix'):
            self._provider = LinuxMStarStatusProvider()
        else:
            self._provider = MStarStatusProvider()

    @property
    def status(self):
        return self._provider.status()

class MStarStatusProvider(object):

    def status(self):
        raise Exception("Cannot determine M* status on platform '%s': unsupported platform" % sys.platform)

class WindowsMStarStatusProvider(MStarStatusProvider):

    def __init__(self):
        super(WindowsMStarStatusProvider, self).__init__()
        self._taskPattern = re.compile('^mo[A-Z].*exe')

    # @Override
    def status(self):
        if self._mstarServicesRunning():
            return MStarStatus.SERVICES_RUNNING
        if self._mstarProcessesRunning():
            return MStarStatus.PROCESSES_RUNNING
        return MStarStatus.NOT_RUNNING

    def _mstarServicesRunning(self):
        # Run equivalent of: sc query | findStr "SERVICE_NAME:" | findstr "M\*"
        lines = _getSubprocessOutput('sc query')
        for line in lines:
            if 'SERVICE_NAME:' in line and 'M*' in line:
                return True
        return False

    def _mstarProcessesRunning(self):
        # Run equivalent of: tasklist | findstr "^mo[A-Z].*exe"
        lines = _getSubprocessOutput('tasklist')
        for line in lines:
            if self._taskPattern.match(line):
                return True
        return False

class LinuxMStarStatusProvider(MStarStatusProvider):

    def __init__(self):
        super(LinuxMStarStatusProvider, self).__init__()

    # @Override
    def status(self):
        lines = _getSubprocessOutput('/bin/ps -ef')
        # TODO examine each line for 'mo[A-Z] pattern?
        raise Exception("Cannot determine M* status on platform '%s': not implemented yet" % sys.platform)


def _getSubprocessOutput(cmd):
    import subprocess
    try:
        output = subprocess.check_output(cmd)
        return output.split('\n')
    except subprocess.CalledProcessError as e:
        print "*** Warning: failed to execute command '%s' : %s" % (e.cmd, e.output)
        return []
