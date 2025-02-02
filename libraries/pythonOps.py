
def hasFunction(object, methodName):
    """ Determines if the object has a named function (a callable property). """
    # TODO there is probably a better way to do this
    return hasattr(object, methodName) and callable(getattr(object, methodName))

def hasProperty(object, propertyName):
    """ Determines if a pyhton object has a proeprty. """
    # TODO there is probably a better way to do this
    return propertyName in dir(object)
