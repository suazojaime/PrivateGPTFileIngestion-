from java.lang import Double

class NoSuchNode:
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "[%s]" % self.message

def getChildCalled(node, names):
    found = []
    for name in names:
        node = node.getChildCalled(name)
        if node is None:
            raise NoSuchNode("Found %s but not %s" % (str(found), name))
        else:
            found.append(name)
    return node

def serverName(node):
    "Given a node representing an object server, return the name of the server."
    return `node`

def slowSqls(node):
    persistenceStats = getChildCalled(node, ["statistics", "persistence"])
    return persistenceStats.getAllStats().get("virtual.slowsqls.total")

def slowPublishes(node):
    pubStats = getChildCalled(node, ["statistics", "pubsub", "publications"])
    return pubStats.getAllStats().get("virtual.pub.slowPublishes.total")

def ecfEventsReceived(node):
    subnode = getChildCalled(node, ["statistics", "pubsub", "subscriptions", "ProxyPubsub"])
    if subnode is None:
        return 0
    return subnode.getAllStats().get("pubsub.stat.sub.eventsin")

def eventReceivePushes(node):
    subnode = getChildCalled(node, ["statistics", "pubsub", "subscriptions", "ProxyPubsub"])
    if subnode is None:
        return 0
    histogram = subnode.getAllStats().get("notify.stat.sub.bytesin")
    if histogram is None:
        return 0
    return histogram.getCount()

def subscribePacketSizes(node):
    subnode = getChildCalled(node, ["statistics", "pubsub", "subscriptions", "ProxyPubsub"])
    if subnode is None:
        return 0
    histogram = subnode.getAllStats().get("notify.stat.sub.bytesin")
    if histogram is None:
        return 0
    return Double(histogram.getAverage()).intValue()

def uptime(node):
    stats = getChildCalled(node, ["statistics"])
    millis = stats.getAllStats().get("objserver.uptime")
    if millis < 10000:
        return "%d milliseconds" % (millis,)
    seconds = millis / 1000
    if seconds < 300:
        return "%d seconds" % (seconds,)
    minutes = seconds / 60
    hours = minutes / 60
    minutes = minutes % 60
    days = hours / 24
    hours = hours % 24
    if days > 0:
        return "%d days %d hours %d minutes" % (days, hours, minutes)
    elif hours > 0:
        return "%d hours %d minutes" % (hours, minutes)
    else:
        return "%d minutes" % (minutes,)


