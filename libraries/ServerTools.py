import minestar, mstarpaths, mstarrun

currentDatabaseServer = None

def serversEqual(thisServer, thatServer):
    if thisServer is None or thatServer is None:
        return 0
    thisServer = thisServer.upper()
    thatServer = thatServer.upper()
    if thisServer == thatServer:
        return 1
    # we are here because the servers may have been specified with one having the domain name suffix and the other not
    # so we will just compare the server name part and ignore the domain name suffix
    thisParts = thisServer.split(".")
    thatParts = thatServer.split(".")
    return thisParts[0] == thatParts[0]

def onServer():
    thisMachine = getCurrentServer()
    allowedHosts   = getAllowedDatabaseHosts()
    appHosts  = getAllowedServers()
    allowedHosts.extend(appHosts)
    currentAppServer = mstarpaths.interpretVar("_HOME")
    if currentAppServer is not None and currentAppServer != '':
        allowedHosts.append(currentAppServer)
    for host in allowedHosts:
        if serversEqual(thisMachine, host):
            return 1
    return 0

def onAppServer():
    return isAppServer(getCurrentServer())

def onDbServer():
    thisMachine = getCurrentServer()
    dbMachine   = getCurrentDatabaseServer()
    return serversEqual(thisMachine, dbMachine)

def isStandbyDbRole():
    currentDbRole = mstarpaths.interpretVar("_DBROLE")
    return currentDbRole == "STANDBY"

def isAppServer(computerName):
    appMachine  = mstarpaths.interpretVar("_HOME")
    return serversEqual(computerName, appMachine)

def getCurrentServer():
    return mstarpaths.interpretVar("COMPUTERNAME")

def getCurrentDatabaseServer():
    global currentDatabaseServer
    if currentDatabaseServer is not None:
        return currentDatabaseServer
    currentDbRole = mstarpaths.interpretVar("_DBROLE")
    currentDatabaseServer = getDatabaseServer(currentDbRole)
    return currentDatabaseServer

def getProductionDatabaseServer():
    return getDatabaseServer("PRODUCTION")

def getStandbyDatabaseServer():
    return getDatabaseServer("STANDBY")

def getDatabaseServer(role):
    serverRoleSpec = mstarpaths.interpretVar("_DB_SERVER_ROLES")
    serverRoles = {}
    if serverRoleSpec is not None and serverRoleSpec != '':
        serverRoles = eval(serverRoleSpec)
        if serverRoles.has_key(role):
            return serverRoles[role]
    return None

def getAllowedDatabaseHosts():
    rolesSpec = mstarpaths.interpretVar("_DB_SERVER_ROLES")
    roleHosts = {}
    if rolesSpec != None and rolesSpec != '':
        roleHosts = eval(rolesSpec)
    hosts = []
    for h in roleHosts.values():
        hosts.append(h.upper())
    return hosts

def getAllowedServers():
    allowedSpec = mstarpaths.interpretVar("_ALLOWED_SERVERS")
    allowedHosts = []
    if allowedSpec != None and allowedSpec != '':
        specs = [ x.strip() for x in allowedSpec.split(",") ]
        allowedHosts = specs
    return allowedHosts

def getDatabaseInstanceServerName(server, dataSource):
    if server is None or dataSource is None:
        print("Server or dataSource should not be None")
        return None
    import os
    if dataSource.instance != '':
        databaseserver = server+os.sep+dataSource.instance
    else:
        databaseserver = server

    return databaseserver
