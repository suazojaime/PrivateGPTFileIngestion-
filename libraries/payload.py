__author__ = 'shattar'
### change code due to jython:pcf
from minestar.health.util.ccdscycles.com.jython import PayloadType
from minestar.health.util.ccdscycles.com.jython import LoadType


def _no_duplicates(iterable):
    seen = set()
    seen_add = seen.add
    for item in iterable:
        if item not in seen:
            seen_add(item)
            yield item


def associate_payloads_and_loads(load_list, payload_list):
    """
    Associates payloads and loads together.

    :param load_list: List of loads to associate to payloads.
    :type load_list: list of :class:`Load`
    :param payload_list: List of payloads to associate to loads.
    :type payload_list: list of :class:`Payload`
    """
    if payload_list is not None:
        for payload in payload_list:
            payload.set_load_record(load_list)

    if load_list is not None:
        for load in load_list:
            load.remove_duplicate_payloads()

### change code due to jython:pcf
class Load(LoadType):
    __slots__ = ['start_timestamp', 'start_hour_meter', 'end_timestamp', 'payload_list']

    def __init__(self, start_timestamp=None, start_hour_meter=None, end_timestamp=None, java_object=None):
        """
        Load Record.

        :param start_timestamp: Start timestamp of the load in milliseconds.
        :type start_timestamp: :class:`long`
        :param start_hour_meter: Start hour meter of the load.
        :type start_hour_meter: :class:`float`
        :param end_timestamp: End timestamp of the load in milliseconds.
        :type end_timestamp: :class:`long`
        :param java_object: Java object that represents a load, can be used instead of specifying the attributes
            individually.
        :type java_object: :class:`JLoad`
        """
        self.start_timestamp = start_timestamp  #: (:class:`long`) -- Start timestamp of the load in milliseconds.
        self.start_hour_meter = start_hour_meter  #: (:class:`float`) -- Start hour meter of the load.
        self.end_timestamp = end_timestamp  #: (:class:`long`) -- End timestamp of the load in milliseconds.
        self.payload_list = []  #: (list of :class:`Payload`) -- List of payloads associated with this load.
        if java_object is not None:
            # Don't know the java object interface for Location
            pass

    def remove_duplicate_payloads(self):
        """
        Removes duplicate payloads in the payload list.
        """
        self.payload_list = [payload for payload in _no_duplicates(self.payload_list)]

### change code due to jython:pcf
class Payload(PayloadType):
    __slots__ = ['timestamp', 'calculation_method', 'weight', 'load_start_timestamp', 'load_start_hour_meter',
                 'load_record']

    def __init__(self, timestamp=None, calculation_method=None, weight=None, load_start_timestamp=None,
                 load_start_hour_meter=None, java_object=None):
        """
        Payload Record.

        :param timestamp: Timestamp of the payload in milliseconds.
        :type timestamp: :class:`long`
        :param calculation_method: Calculation method of the payload.
        :type calculation_method: :class:`int`
        :param weight: Payload weight in tonnes.
        :type weight: :class:`float`
        :param load_start_timestamp: Start timestamp of the stored load record in milliseconds.
        :type load_start_timestamp: :class:`long`
        :param load_start_hour_meter: Start hour meter of the stored load record.
        :type load_start_hour_meter: :class:`float`
        :param java_object: Java object that represents a payload, can be used instead of specifying the attributes
            individually.
        :type java_object: :class:`JPayload`
        """
        self.timestamp = timestamp  #: (:class:`long`) -- Timestamp of the payload in milliseconds.
        self.calculation_method = calculation_method  #: (:class:`int`) -- Calculation method of the payload.
        self.weight = weight  #: (:class:`float`) -- Payload weight in tonnes.

        self.load_start_timestamp = load_start_timestamp
        """(:class:`long`) -- Start timestamp of the stored load record in milliseconds."""

        self.load_start_hour_meter = load_start_hour_meter
        """(:class:`float`) -- Start hour meter of the stored load record."""

        self.load_record = None  #: (:class:`Load`) -- Load record associated with this payload.

        if java_object is not None:
            # Don't know the java object interface for Location
            pass

    def set_load_record(self, load_list):
        """
        Find the load record that this payload is a part of, if it exists, and set it.

        :param load_list: A list of potential load records.
        :type load_list: list of :class:`Load`
        :returns: (:class:`Load`) -- The load associated with this payload, otherwise, `None`
        """
        if load_list is None:
            self.load_record = None
        elif self.load_start_timestamp is None:
            self.load_record = None
        else:
            indices = [idx for idx, load in enumerate(load_list) if self.load_start_timestamp == load.start_timestamp]
            if len(indices) > 0:
                if self.load_start_hour_meter is not None:
                    indices = [idx for idx in indices if self.load_start_hour_meter == load_list[idx].start_hour_meter]
                if len(indices) > 0:
                    self.load_record = load_list[indices[0]]
                    self.load_record.payload_list.append(self)
                else:
                    self.load_record = None
            else:
                self.load_record = None
        return self.load_record

    @property
    def is_stored(self):
        """(:class:`bool`) -- `True` if this payload is stored, otherwise, `False`."""
        return False if self.load_record is None else True
