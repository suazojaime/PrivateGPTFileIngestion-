from com.mincom.env.ecf.proxy import EntityResolution

def getMachineState(ecfEvent):
    entity = EntityResolution.getInstance(cfEvent.getRef())
    name = entity.get('name')
    state = entity.get('macState')
    return "%s is now in state %s" % (name, state)
