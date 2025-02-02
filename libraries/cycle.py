import math
### change code due to jython:pcf
#import cycle_identifier
from minestar.health.util.ccdscycles.com.jython import CycleType
from java.lang import System as js

__author__ = 'shattar'

NAN = float('nan')

class Cycle(CycleType):

    __slots__ = ['_identifier', '_segment_list', '_start_location', '_dest_location']

    def __init__(self, identifier=None):
        """
        Cycle Record base class.

        This is the bare minimum cycle record that only supports the common subset of statistics.
        Child classes are expected to implement additional custom.

        :param identifier: The cycle identifier.
        :type identifier: :class:`int`
        """
        self._identifier = identifier
        self._segment_list = []
        self._start_location = None
        self._dest_location = None

    def update_statistics(self, properties=None):
        """
        This method is called by the cycle generator in order to update derived statistics after all of
        the segments have been properly associate to the cycle.

        The base class implementation doesn't do anything.

        :param properties: The machine properties.
        :type identifier: :class:`dict`
        """
        pass

    @property
    def identifier(self):
        """(:class:`int`) -- The cycle identifier."""
        return self._identifier

### change code due to jython:pcf
    def getStartTs(self):
        return self.cycle_start_timestamp

### change code due to jython:pcf
    def getEndTs(self):
        return self.cycle_end_timestamp

### change code due to jython:pcf
    def getIdentifier(self):
        """(:class:`int`) -- The cycle identifier."""
        return self._identifier

### change code due to jython:pcf
    def getStart_hour_meter(self):
        return self.first_segment_hour_meter

    def getStartLatitude(self):
        return self.start_location_latitude

    def getStartLongitude(self):
        return self.start_location_longitude

    def getStartAltitude(self):
        return self.start_location_altitude

    def getDestinationLatitude(self):
        return self.dest_location_latitude

    def getDestinationLongitude(self):
        return self.dest_location_longitude

    def getDestinationAltitude(self):
        return self.dest_location_altitude

    @property
    def segment_list(self):
        """(list of :class:`~app_cycle_id.segment.Segment`) -- List of segments that are in this cycle."""
        return self._segment_list

    @property
    def cycle_start_timestamp(self):
        """(:class:`long`) -- Timestamp of the start of this cycle, in milliseconds."""
        return self.first_segment_timestamp

    @property
    def cycle_end_timestamp(self):
        """(:class:`long`) -- Timestamp of the end of this cycle, in milliseconds."""
        last_segment_timestamp = self.last_segment_timestamp
        if last_segment_timestamp is not None:
            last_segment_duration = self.segment_list[-1].duration
### change code due to jython:pcf : change date to time
            return last_segment_timestamp.time + long(round(last_segment_duration * 1000.0))
        else:
            return None

### change code due to jython:pcf
    def getSegmentList(self):
        """(list of :class:`~app_cycle_id.segment.Segment`) -- List of segments that are in this cycle."""
        return self._segment_list

    @property
    def first_segment_timestamp(self):
        """(:class:`long`) -- Timestamp of the first segment in this cycle, in milliseconds."""
        if len(self.segment_list) > 0:
            return self.segment_list[0].start_timestamp
        else:
            return None

    @property
    def first_segment_hour_meter(self):
        """(:class:`float`) -- Hour meter of the first segment in this cycle."""
        if len(self.segment_list) > 0:
            return self.segment_list[0].start_hour_meter
        else:
            return None

    @property
    def last_segment_timestamp(self):
        """(:class:`long`) -- Timestamp of the last segment in this cycle, in milliseconds."""
        if len(self.segment_list) > 0:
            return self.segment_list[-1].start_timestamp
        else:
            return None

    @property
    def last_segment_hour_meter(self):
        """(:class:`float`) -- Hour meter of the last segment in this cycle."""
        if len(self.segment_list) > 0:
            return self.segment_list[-1].start_hour_meter
        else:
            return None

    @property
    def duration(self):
        """(:class:`float`) -- Duration of the cycle in seconds."""
        if self.segment_list is None:
            return None
        else:
            return math.fsum([segment.duration for segment in self.segment_list])

    @property
    def distance(self):
        """(:class:`float`) -- Distance travelled during the cycle in kilometers."""
        if self.segment_list is None:
            return None
        else:
            return math.fsum([segment.distance for segment in self.segment_list])

    @property
    def fuel(self):
        """(:class:`float`) -- Fuel used during the cycle in liters."""
        if self.segment_list is None:
            return None
        else:
            return math.fsum([segment.fuel for segment in self.segment_list])

    @property
    def start_location(self):
        """(`tuple` of :class:`float`) -- (latitude, longitude, altitude) for the cycle start location."""
        if self._start_location is None:
            if self.segment_list:
                segment = self.segment_list[0]
                return (
                    segment.latitude,
                    segment.longitude,
                    segment.altitude
                )
            else:
                return None
        else:
            return self._start_location

    @property
    def start_location_latitude(self):
        """(:class:`float`) -- Latitude of the cycle start location in degrees, or NaN if unknown."""
        try:
            return self.start_location[0]
        except (TypeError, IndexError):
            return NAN

    @property
    def start_location_longitude(self):
        """(:class:`float`) -- Longitude of the cycle start location in degrees, or NaN if unknown."""
        try:
            return self.start_location[1]
        except (TypeError, IndexError):
            return NAN

    @property
    def start_location_altitude(self):
        """(:class:`float`) -- Altitude of the cycle start location in meters, or NaN if unknown."""
        try:
            return self.start_location[2]
        except (TypeError, IndexError):
            return NAN

    @property
    def dest_location(self):
        """(`tuple` of :class:`float`) -- (latitude, longitude, altitude) for the cycle destination location."""
        return self._dest_location

    @property
    def dest_location_latitude(self):
        """(:class:`float`) -- Latitude of the cycle destination location in degrees, or NaN if unknown."""
        try:
            return self.dest_location[0]
        except (TypeError, IndexError):
            return NAN

    @property
    def dest_location_longitude(self):
        """(:class:`float`) -- Longitude of the cycle destination location in degrees, or NaN if unknown."""
        try:
            return self.dest_location[1]
        except (TypeError, IndexError):
            return NAN

    @property
    def dest_location_altitude(self):
        """(:class:`float`) -- Altitude of the cycle destination location in meters, or NaN if unknown."""
        try:
            return self.dest_location[2]
        except (TypeError, IndexError):
            return NAN

    def __str__(self):
        return cycle_identifier.CycleIds.get_strings_from_ids(self.identifier)
