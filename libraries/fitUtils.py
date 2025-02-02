import sys

def manager(name):
    return sys.minestarContext.getManagerFromName(name)

def peekModelEntities():
    return fixture.peekModelEntities()

def modelEntities():
    return fixture.modelEntities()

def peekCycles():
    return fixture.peekCycles()

def cycles():
    return fixture.cycles()

def peekEvents():
    return fixture.peekEvents()

def events():
    return fixture.events()

def peekProperytEvents():
    return fixture.peekPropertyEvents()

def propertyEvents():
    return fixture.propertyEvents()

def findEntity(entities, classdef):
    for e in entities:
        if e.getClassDef().getName() == classdef:
            return e
    return None

def search(managerName, name):
    from com.mincom.env.ecf import ManagerException
    try:
        return manager(managerName).findByName(name)
    except ManagerException:
        return "not found"

def rand(lo, hi):
    import random
    return random.randint(lo, hi)
