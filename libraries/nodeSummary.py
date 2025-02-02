def getChildCalled(node, names):
    for name in names:
        node = node.getChildCalled(name)
    return node

def nodeName(node):
    "Given a node representing a connection node, return the name of the node."
    return `node`
