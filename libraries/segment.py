#from segment_identifier import SegmentIds
#from location import is_gps_location_valid
import math
### change code due to jython:pcf
from minestar.health.util.ccdscycles.com.jython import SegmentType

__author__ = 'shattar'

NAN = float('nan')


def associate_payloads_to_segments(segment_list, payload_list):
    """
    Associates payloads to the segments that the payloads were measured in.

    :param segment_list: List of segments to which payloads will be associated.
    :type segment_list: list of :class:`Segment`
    :param payload_list: List of payloads to associate to segments.
    :type payload_list: list of :class:`~app_cycle_id.payload.Payload`
    """
    if payload_list is not None:
        payload_set = set(payload_list)
        for idx in xrange(len(segment_list)):
            start_timestamp = segment_list[idx].start_timestamp
            if idx < len(segment_list)-1:
                end_timestamp = segment_list[idx+1].start_timestamp
            else:
                end_timestamp = start_timestamp + int(math.ceil(segment_list[idx].duration * 1000.0))
            segment_list[idx].payload_list = [payload for payload in payload_set
                                              if start_timestamp <= payload.timestamp < end_timestamp]
            # Remove the consumed payloads
            payload_set.difference_update(segment_list[idx].payload_list)


def associate_locations_to_segments(segment_list, location_list):
    """
    Sets the latitude and longitude of each segment, from the provided list of locations, if the segments location is
    not already set.

    :param segment_list: List of segments to associate a location to.
    :type segment_list: list of :class:`Segment`
    :param location_list: List of locations to associate to segments.
    :type location_list: list of :class:`~app_cycle_id.location.Location`
    """
    if location_list is not None:
        location_dict = None
        for segment in segment_list:
            if not is_gps_location_valid(segment.latitude, segment.longitude):
                if location_dict is None:
                    location_dict = {location.timestamp: location for location in location_list}
                try:
                    location = location_dict[segment.start_timestamp]
                    segment.latitude = location.latitude
                    segment.longitude = location.longitude
                    segment.altitude = location.altitude
                except KeyError:
                    # Location not found
                    segment.latitude = NAN
                    segment.longitude = NAN
                    segment.altitude = NAN


def _parse_payload_accuracy(raw_accuracy):
    """
    Parses the given raw payload accuracy to determine if it is just an integer accuracy 0, 1, 2, 3 or if it is
    payload calculation method, which is multiple fields encoded into 4 nibbles, one of which is accuracy.

    The payload calculation method is formatted as follows:
    ----------------------------------------------------------------------------
    |    Filter Type    |    Accuracy    |    Undefined    |    Sensor Type    |
    ----------------------------------------------------------------------------

    Filter Type:
    0001b - Dynamic Averaging
    0010b - 2-Pole Butterworth Low Pass

    Accuracy:
    0000b - None
    0001b - Low
    0010b - Medium
    0011b - High

    Undefined:
    0000b

    Sensor Type:
    0001b - Hydraulic Pressure Sensors, both Head End and Rod End
    0010b - Hydraulic Pressure Sensors, One End
    0011b - Resistive Load Cell

    :param raw_accuracy: The payload accuracy or payload calculation method.
    :type raw_accuracy: :class:`float` or :class:`int`
    :returns: (:class:`int`) -- The parsed accuracy.
    """
    if raw_accuracy is None:
        parsed_accuracy = None
    else:
        int_accuracy = int(round(raw_accuracy))
        if int_accuracy > 0:
            upper_byte = (0xFF00 & int_accuracy) >> 8
            if upper_byte > 0:
                parsed_accuracy = upper_byte & 0x0F
            else:
                parsed_accuracy = int_accuracy
        else:
            parsed_accuracy = 0
    return parsed_accuracy


### change code due to jython:pcf
class Segment(SegmentType):

    __slots__ = ['identifier', 'start_timestamp', 'start_hour_meter',
                 'duration', 'idle_duration',
                 'distance', 'fuel',
                 'payload', 'payload_accuracy',
                 'latitude', 'longitude', 'altitude',
                 '_stored_payload',
                 'cycle_record', 'payload_list']

    def __init__(self, identifier=None, start_timestamp=None, start_hour_meter=None, duration=None,
                 idle_duration=None, distance=None, fuel=None, payload=None, payload_accuracy=None,
                 latitude=NAN, longitude=NAN, altitude=NAN, stored_payload=None,
                 java_object=None):
        """
        Segment Record.

        :param identifier: Identifier of the segment.
        :type identifier: :class:`int`
        :param start_timestamp: Java-style Unix timestamp at the start of the segment, in milliseconds.
        :type start_timestamp: :class:`long`
        :param start_hour_meter: Hour meter at the start of the segment.
        :type start_hour_meter: :class:`float`
        :param duration: Duration of the segment in seconds.
        :type duration: :class:`float`
        :param idle_duration: Idle duration in seconds.
        :type idle_duration: :class:`float`
        :param distance: Total absolute distance travelled during the segment in kilometers.
        :type distance: :class:`float`
        :param fuel: Total fuel used during the segment in liters.
        :type fuel: :class:`float`
        :param payload: Best available payload measurement during the segment in tonnes.
        :type payload: :class:`float`
        :param payload_accuracy: Accuracy of the best available payload measurement during the segment.
        :type payload_accuracy: :class:`int`
        :param latitude: GPS latitude at the start of the segment.
        :type latitude: :class:`float`
        :param longitude: GPS longitude at the start of the segment.
        :type longitude: :class:`float`
        :param altitude: GPS altitude at the start of the segment.
        :type altitude: :class:`float`
        :param stored_payload: Stored payload measurement encountered during the segment in tonnes.
        :type stored_payload: :class:`float`
        :param java_object: Java object that represents a segment, can be used instead of specifying the attributes
            individually.
        :type java_object: :class:`JSegment`
        """
        self.identifier = identifier  #: (:class:`int`) -- Cycle identifier.
        self.start_timestamp = start_timestamp  #: (:class:`long`) -- Segment start timestamp in milliseconds.
        self.start_hour_meter = start_hour_meter  #: (:class:`float`) -- Segment start hour meter.
        self.duration = duration  #: (:class:`float`) -- Duration in seconds.
        self.idle_duration = idle_duration  #: (:class:`float`) -- Idle duration in seconds.
        self.distance = distance  #: (:class:`float`) -- Travel distance in kilometers.
        self.fuel = fuel  #: (:class:`float`) -- Fuel used in liters.
        self.payload = payload  #: (:class:`float`) -- Best available payload measurement in tonnes.

        self.payload_accuracy = _parse_payload_accuracy(payload_accuracy)
        """(:class:`int`) -- Accuracy of the best available payload."""

        self.latitude = latitude  #: (:class:`float`) -- GPS latitude at the start of the segment.
        self.longitude = longitude  #: (:class:`float`) -- GPS longitude at the start of the segment.
        self.altitude = altitude  #: (:class:`float`) -- GPS altitude at the start of the segment.
        self._stored_payload = stored_payload  #: (:class:`float`) -- Stored payload measured in tonnes.

        self.cycle_record = None
        """(:class:`~app_cycle_id.cycle.Cycle`) -- Cycle that this segment belongs to."""

        self.payload_list = None
        """(list of :class:`~app_cycle_id.payload.Payload`) -- List of payloads measured during this segment."""

        if java_object is not None:
            # Initialize with the java object
            # public Date getStartTs();
            # public BigDecimal getDistanceTraveled();
            # public BigDecimal getFuelConsumed();
            # public String getSegmentCd();
            # public BigDecimal getSegmentDuration();
            self.identifier = SegmentIds.get_ids_from_strings(java_object.getSegmentCd())
            self.start_timestamp = java_object.getStartTs()
            self.duration = java_object.getSegmentDuration()
            self.distance = java_object.getDistanceTraveled()
            self.fuel = java_object.getFuelConsumed()

        # If the gps location is invalid, then set it to NaNs
        if not is_gps_location_valid(self.latitude, self.longitude):
            self.latitude = NAN
            self.longitude = NAN
            self.altitude = NAN

    @property
    def is_start_of_cycle(self):
        """(:class:`bool`) -- `True` if this segment is the start of a cycle, otherwise, `False`."""
        if self.cycle_record is None:
            return False
        else:
            return True if self.start_timestamp == self.cycle_record.first_segment_timestamp else False

    @property
    def cycle_identifier(self):
        """(:class:`int`) -- Cycle identifier of this segment."""
        if self.cycle_record is None:
            return None
        else:
            return self.cycle_record.identifier

    @property
    def stored_payload(self):
        """(:class:`float`) -- Stored payloads measured during this segment."""
        if self.payload_list is None:
            if self._stored_payload is None:
                return 0.0
            else:
                return self._stored_payload
        else:
            return math.fsum([payload.weight for payload in self.payload_list if payload.is_stored])

    def __str__(self):
        return SegmentIds.get_strings_from_ids(self.identifier)
