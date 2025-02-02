from typeOps import isInstanceOf


def assertIsInstanceOf(name, value, targetType):
    """
    Assert that the value is an instance of the target type.

    :param name: the name of the value, used when creating an error message.
    :param value: the value to be inspected.
    :param targetType: the target type for the value.
    :raise: TypeError if the value is not an instance of the target type.
    """
    if not isInstanceOf(value, targetType):
        raise TypeError("Expected '%s' of type %s but found %s" % (name, targetType, type(value)))


def assertIsNotNone(name, value):
    """
    Assert that the value is not None.

    :param name: the name of the value, used when creating an error message.
    :param value: the value to be inspected.
    :raise: ValueError if the value is None.
    """
    if value is None:
        raise ValueError("No value defined for '%s'" % name)
