import collections

__author__ = 'shattar'


class SegmentIds(object):
    """
    Segment identifier values, strings, and conversion functions.

    :cvar MISC: Miscellaneous
    :cvar IDLE: Idle
    :cvar STOPPED_EMPTY: Stopped Empty
    :cvar STOPPED_LOADED: Stopped Loaded
    :cvar KEY_ON_ENGINE_OFF: Key-On, Engine-Off, like initial key on or stall
    :cvar KEY_OFF_ENGINE_ON: Key-Off, Engine-On, like delayed engine shutdown
    :cvar KEY_OFF_ENGINE_OFF: Key-Off, Engine-Off
    :cvar DIG: Dig
    :cvar TRAVEL_LOADED: Travel Loaded
    :cvar DUMP: Dump
    :cvar PARTIAL_DUMP: Partial Dump
    :cvar TRAVEL_EMPTY: Travel Empty
    :cvar BACKDRAG: Backdrag
    """

    MISC = 15
    IDLE = 16
    STOPPED_EMPTY = 22
    STOPPED_LOADED = 21
    KEY_ON_ENGINE_OFF = 26
    KEY_OFF_ENGINE_ON = 28
    KEY_OFF_ENGINE_OFF = 27  # 40
    DIG = 0
    TRAVEL_LOADED = 1
    DUMP = 2
    PARTIAL_DUMP = 24
    TRAVEL_EMPTY = 3
    BACKDRAG = 25

    _id_to_string = {
        MISC: 'Miscellaneous',
        IDLE: 'Machine Idle',
        STOPPED_EMPTY: 'Stopped Empty',
        STOPPED_LOADED: 'Stopped Loaded',
        KEY_ON_ENGINE_OFF: 'Key On - Engine Off',
        KEY_OFF_ENGINE_ON: 'Key Off - Engine On',
        KEY_OFF_ENGINE_OFF: 'Key Off - Engine Off',
        DIG: 'Dig',
        TRAVEL_LOADED: 'Travel Loaded',
        DUMP: 'Dump',
        PARTIAL_DUMP: 'Partial Dump',
        TRAVEL_EMPTY: 'Travel Empty',
        BACKDRAG: 'Backdrag'
    }

    _string_to_id = {string: identifier for identifier, string in _id_to_string.items()}

    @classmethod
    def get_strings_from_ids(cls, ids):
        """
        Converts segment identifiers to strings.

        :param ids: A scalar segment identifier, or sequence of segment identifiers, to convert to strings.
        :type ids: :class:`int` or list of :class:`int`
        :returns: (:class:`str` or list of :class:`str`) -- A string, or sequence of strings, representing the name of
            the segments.
        """
        if isinstance(ids, collections.Sequence):
            return [cls._id_to_string[segment_id] for segment_id in ids]
        else:
            return cls._id_to_string[ids]

    @classmethod
    def get_ids_from_strings(cls, strings):
        """
        Converts segment strings to identifiers.

        :param strings: A string, or sequence of strings, to convert to segment identifiers.
        :type strings: :class:`str` or list of :class:`str`
        :returns: (:class:`int` or list of :class:`int`) -- A scalar segment identifier, or sequence of segment
            identifiers, mapped from the string name of the segment.
        """
        if isinstance(strings, basestring):
            return cls._string_to_id[strings]
        else:
            return [cls._string_to_id[segment_string] for segment_string in strings]
