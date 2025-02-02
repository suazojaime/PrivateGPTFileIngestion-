def isCollectionOf(v, type):
    """ Determines if the value is a collection with every element an instance of the type. """
    if isinstance(v, list) or isinstance(v, set):
        return all(isInstanceOf(elem, type) for elem in v)
    return False


def isInstanceOf(v, targetType):
    """ Determines if an object is (possibly) an instance of the target type. """
    return isinstance(v, targetType) or isDerivedType(type(v), targetType)


def isDerivedType(baseType, parentType):
    """ Determines if a base type is (possibly) derived from a parent type. """
    # If the same types: success.
    if baseType == parentType:
        return True

    # If the types have the same name and (possibly) same module: success.
    #
    # There are issues with python paths and modules here: a package object created from
    # 'import packages.Package' is not considered to be an instance of 'install.packages.Package',
    # and vice versa. So 'install.' is stripped from the module name before any comparisons.
    #
    if baseType.__name__ == parentType.__name__:
        def removePrefixes(s):
            prefixes = ['install.']  # TODO needs to be configured
            for prefix in prefixes:
                if s.startswith(prefix):
                    return s[len(prefix):]
            return s

        if removePrefixes(baseType.__module__) == removePrefixes(parentType.__module__):
            return True

    # Otherwise check the base types.
    return any(isDerivedType(t, parentType) for t in baseType.__bases__)


