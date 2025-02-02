# Library for access to the MineStar bus.
# John Farrell 20030519

# Java imports
from com.mincom.env.base.bus import BusConnection
from com.mincom.env.service.pubsub import Pubsub
# python imports

def connectToBus(busUrl):
    BusConnection.connectToBus(busUrl)

def createSubscription(name, constraint):
    return Pubsub.createSubscription(name, constraint)

def waitForever():
    from threading import Condition
    condition = Condition()
    condition.acquire()
    condition.wait()
