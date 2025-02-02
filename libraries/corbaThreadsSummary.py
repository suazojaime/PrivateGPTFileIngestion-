from java.lang import Double

def getChildCalled(node, names):
    for name in names:
        node = node.getChildCalled(name)
    return node

def threadName(node):
    "Given a node representing a CORBA thread, return the name of the thread."
    return `node`

def inUseFor(node):
    if node.getStats().containsKey("inUseFor"):
        return node.getStats().get("inUseFor")
    else:
        return -1


