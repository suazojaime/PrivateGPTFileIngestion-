from java.lang import Integer
from com.mincom.util.general import IntegerHistogram

def sum(children, key):
    tot = 0
    for i in range(children.size()):
        child = children.get(i)
        val = child.get(key)
        if val is None:
            continue
        tot = tot + val
    return tot

def max(children, key):
    m = Integer.MIN_VALUE
    for i in range(children.size()):
        child = children.get(i)
        v = child.get(key)
        if v is not None and v > m:
            m = v
    return m

def min(children, key):
    m = Integer.MAX_VALUE
    for i in range(children.size()):
        child = children.get(i)
        v = child.get(key)
        if v is not None and v < m:
            m = v
    return m

def avg(children, key):
    tot = 0
    count = 0
    for i in range(children.size()):
        child = children.get(i)
        v = child.get(key)
        if v is None:
            continue
        tot = tot + v
        count = count + 1
    if count == 0:
        return 0
    return tot / count

def histogramSum(children, key):
    count = children.size()
    if count == 0:
        return None
    sum = children.get(0).get(key)
    for i in range(1, count):
        h = children.get(i).get(key)
        if sum is None:
            sum = h
        else:
            sum = IntegerHistogram.add(sum, h)
    return sum

def valueWhere(children, returnKey, whereKey, whereValue):
    for i in range(children.size()):
        child = children.get(i)
        if child.get(whereKey) == whereValue:
            return child.get(returnKey)
    return None

def valueFromAnyChild(children, key):
    "Find any child which has the key and return it."
    for i in range(children.size()):
        child = children.get(i)
        if child.containsKey(key):
            return child.get(key)
    return None
