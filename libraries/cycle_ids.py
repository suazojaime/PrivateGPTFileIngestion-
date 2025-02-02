import collections

__author__ = 'shattar'


class CycleIds(object):
    """
    Cycle identifier values, strings, and conversion functions.

    :cvar NONE: No Cycle Id
    :cvar OTHER: Other
    :cvar WAITING: Waiting
    :cvar KEY_ON_ENGINE_OFF: Key On - Engine Off
    :cvar ENGINE_SHUTDOWN: Engine Shutdown
    :cvar LOADING: Loading (like Truck Loading)
    :cvar LOAD_AND_CARRY: Load and Carry (like Hopper Charging)
    :cvar ROADING: Roading
    :cvar PILE_CLEANUP: Pile Cleanup
    """

    NONE = 255
    OTHER = 4
    WAITING = 8
    KEY_ON_ENGINE_OFF = 12  # Needs to be defined still!!
    ENGINE_SHUTDOWN = 11
    LOADING = 2
    LOAD_AND_CARRY = 0
    ROADING = 5
    PILE_CLEANUP = 3

    _id_to_string = {
        NONE: 'None',
        OTHER: 'Other',
        WAITING: 'Waiting',
        KEY_ON_ENGINE_OFF: 'Key On - Engine Off',
        ENGINE_SHUTDOWN: 'Engine Shutdown',
        LOADING: 'Loading',
        LOAD_AND_CARRY: 'Load and Carry',
        ROADING: 'Roading',
        PILE_CLEANUP: 'Pile Cleanup'
    }

    _string_to_id = {string: identifier for identifier, string in _id_to_string.items()}

    @classmethod
    def get_strings_from_ids(cls, ids):
        """
        Converts cycle identifiers to strings.

        :param ids: A scalar cycle identifier, or sequence of cycle identifiers, to convert to strings.
        :type ids: :class:`int` or list of :class:`int`
        :returns: (:class:`str` or list of :class:`str`) -- A string, or sequence of strings, representing the name of
            the cycles.
        """
        if isinstance(ids, collections.Sequence):
            return [cls._id_to_string[cycle_id] for cycle_id in ids]
        else:
            return cls._id_to_string[ids]

    @classmethod
    def get_ids_from_strings(cls, strings):
        """
        Converts cycle strings to identifiers.

        :param strings: A string, or sequence of strings, to convert to cycle identifiers.
        :type strings: :class:`str` or list of :class:`str`
        :returns: (:class:`int` or list of :class:`int`) -- A scalar cycle identifier, or sequence of cycle
            identifiers, mapped from the string name of the cycle.
        """
        if isinstance(strings, basestring):
            return cls._string_to_id[strings]
        else:
            return [cls._string_to_id[cycle_string] for cycle_string in strings]
