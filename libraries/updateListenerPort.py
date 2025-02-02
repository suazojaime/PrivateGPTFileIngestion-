import minestar
logger = minestar.initApp()


# Get the database dependent object from databaseDifferentiator.
import os, sys, string,mstarpaths, i18n, progress

import databaseDifferentiator
mstarpaths.loadMineStarConfig()
dbobject = databaseDifferentiator.returndbObject()


def checkCurrentDatabaseServer():
    import ServerTools
    db = ServerTools.getCurrentDatabaseServer()
    if not db:
        print i18n.translate("updateListenerPort.main: database server has not been configured.")
        minestar.exit(0)

    if not isSameHost(db, ServerTools.getCurrentServer()):
        print i18n.translate("updateListenerPort.main: updateListenerPort should be run from Database Server (%s) only (current: %s)") % (db, ServerTools.getCurrentServer())
        minestar.exit(0)

def isSameHost(a, b):
    if a.upper() == b.upper():
        return True;
    # More sophisticated match.  Try looking up the addresses and see if
    # we can ascertain if these addresses map to the same host
    try:
        a_addr = socket.gethostbyaddr(a)
        b_addr = socket.gethostbyaddr(b)
        # See if the two tuples match.  The primary hostname matches, or
        # There is an IP address in common
        return a_addr == b_addr or a_addr[0] == b_addr[0] or len(set(a_addr[2]).intersection(b_addr[2])) > 0
    except socket.error as e:
        # One of the addresses is malformed or name lookup is not working.
        # We suppress this error and just display the one which shows that
        # the names don't match.
        return False

def main(appConfig=None):
    """entry point when called from mstarrun"""

    checkCurrentDatabaseServer()
    try:
        progress.start(1000, "updateListenerPort")
        minestar.logit("updateListenerPort.main: Calling datastore.getSystemDataStores");
        progress.task(0.2, "Stop Listener..")
        dbobject.stopDSListener()
        portnum = databaseDifferentiator.getDbPort()
        progress.nextTask(0.6, "Update Listner ORA")
        minestar.logit("updateListenerPort.main: Updating Listener ORA with port %s " % portnum);
        dbobject.modifyListenerPort(portnum)
        progress.nextTask(0.8, "Update TNS Names")
        dbobject.UpdateTnsNames()
        progress.nextTask(0.9, "Restarting Listener")
        # Restart tns listener
        dbobject.startDSListener()
        # done
        mesg = "updateListenerPort.main: Done"
        minestar.logit(mesg);
        print mesg
    except:
        minestar.logit("updateListenerPort.main: Caught exception");
        progress.fail(sys.exc_info()[0])
        import traceback
        traceback.print_exc()
    progress.done()
    minestar.exit(0)

if __name__ == "__main__":
    """entry point when called from python"""
    main()

