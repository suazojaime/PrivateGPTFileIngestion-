def getChildCalled(node, names):
    for name in names:
        node = node.getChildCalled(name)
    return node

def managerName(node):
    "Given a node representing a manager, return the name of the manager."
    return `node`

def findManagerStatistic(node, key):
    stats = getChildCalled(node, ["statistics"])
    if stats is None:
        # submanager node
        return node.getAllStats().get(key)
    else:
        # manager node
        return stats.getAllStats().get(key)
