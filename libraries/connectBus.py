# $Id: connectBus.py,v 1.2 2003-05-02 05:34:45 christianl Exp $
# Copyright (c) 2003, Caterpillar, Brisbane Australia.
# All rights reserved.

from java.lang import System
from com.mincom.env.base.bus import BusConnection
from com.mincom.env.base.bus import BusURL
from com.mincom.gem.metadata import MetadataAccessBean

busURL = System.getProperty( "busUrl" )

print "Connecting to Minestar on: ", busURL
url = BusURL.parse( busURL )

BusConnection.connectToBus( url )

MetadataAccessBean.getInstance( )
