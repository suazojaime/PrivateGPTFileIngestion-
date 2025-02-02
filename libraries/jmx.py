__author__ = 'poveydg'
import sys, mstarpaths, mstarapplib, re, mstarrun

def getJmxPort(defn):
    jmxPort = defn.get('JMX_PORT')
    if jmxPort is not None:
        m = re.search('-Dcom.sun.management.jmxremote.port=(\d+)', jmxPort)
        if m is not None:
            return m.group(1)
    return None

def rewriteParams(params, jmxPort):
    newParams = []
    newParams.append('minestar.management.JmxClient')
    newParams.append('-port')
    newParams.append(jmxPort)
    newParams += params[2:]
    return newParams

def run(params):
    # Load application config
    mstarpaths.loadMineStarConfig()
    mstarapplib.loadApplications()

    # Process params
    appName = params[1]

    # Look up JMX port from application definition
    if not mstarapplib.appSources.has_key(appName):
        print "No such application %s" % appName
        sys.exit(-1)
    defn = mstarapplib.getApplicationDefinition(appName)
    jmxPort = getJmxPort(defn)
    if jmxPort is None:
        print "Could not locate JMX_PORT for application %s" % appName
        sys.exit(-1)

    # Rewrite params so we pass a -port option to the JMX client
    mstarrun.run(rewriteParams(params, jmxPort), {}, 0)


if __name__ == '__main__':
    run(sys.argv)
