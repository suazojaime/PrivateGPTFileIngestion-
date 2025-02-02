### change code due to jython:pcf
#from math import radians, sin, cos, sqrt, asin, isnan, isinf
### change code due to jython:pcf
from minestar.health.util.ccdscycles.com.jython import LocationType

__author__ = 'shattar'

NAN = float('nan')


def is_gps_location_valid(latitude, longitude):
    """
    Determines the validity of a given latitude and longitude coordinate.

    :param latitude: The GPS latitude, in degrees
    :type latitude: :class:`float`
    :param longitude: The GPS longitude, in degrees
    :type longitude: :class:`float`
    :returns: (:class:`bool`) -- `True` if the location is valid, otherwise, `False`
    """
    if (latitude is None) or (longitude is None):
        return False
    else:
        is_non_zero = (latitude != 0) or (longitude != 0)
        ##change code due to jython jar issue:pcf
        ### is_non_nan = not (isnan(latitude) or isinf(latitude) or isnan(longitude) or isinf(longitude))
        is_non_nan = not (latitude!=latitude or latitude==float('Inf') or latitude==-float('Inf') or longitude!=longitude or longitude==float('Inf') or longitude==-float('Inf'))
        return is_non_nan and is_non_zero


### change code due to jython:pcf
class Location(LocationType):
    __slots__ = ['timestamp', 'hour_meter', 'latitude', 'longitude', 'altitude']

    EARTH_RADIUS_METERS = 6371009.0  #: (:class:`float`) -- Earth's radius in meters.

    def __init__(self, timestamp=None, hour_meter=None, latitude=NAN, longitude=NAN, altitude=NAN,
                 java_object=None):
        """
        Location Record.

        :param timestamp: Timestamp in milliseconds.
        :type timestamp: :class:`long`
        :param hour_meter: Hour meter.
        :type hour_meter: :class:`float`
        :param latitude: GPS latitude in degrees.
        :type latitude: :class:`float`
        :param longitude: GPS longitude in degrees.
        :type longitude: :class:`float`
        :param altitude: GPS altitude in meters.
        :type altitude: :class:`float`
        :param java_object: Java object that represents a location, can be used instead of specifying the attributes
            individually.
        :type java_object: :class:`JLocation`
        """
        self.timestamp = timestamp  #: (:class:`long`) -- Timestamp in milliseconds.
        self.hour_meter = hour_meter  #: (:class:`float`) -- Hour meter.
        self.latitude = latitude  #: (:class:`float`) -- GPS latitude in degrees.
        self.longitude = longitude  #: (:class:`float`) -- GPS longitude in degrees.
        self.altitude = altitude  #: (:class:`float`) -- GPS altitude in meters.
        if java_object is not None:
            # Don't know the java object interface for Location
            raise NotImplementedError('Have not implement the Java Location object')

    @property
    def is_valid(self):
        """(:class:`bool`) -- `True` if the location is valid, otherwise, `False`"""
        return is_gps_location_valid(self.latitude, self.longitude)

    def distance_from(self, another_location):
        """
        Estimate the great circle distance between this and another earth location.

        :param another_location: Another location object
        :type another_location: :class:`Location`
        :returns: (:class:`float`) -- The distance, in meters, if both locations are valid, otherwise, `float('nan')`
        """
        if self.is_valid and another_location.is_valid:
            this_latitude = radians(self.latitude)
            this_longitude = radians(self.longitude)
            another_latitude = radians(another_location.latitude)
            another_longitude = radians(another_location.longitude)
            delta_latitude = radians(another_latitude - this_latitude)
            delta_longitude = radians(another_longitude - this_longitude)
            a = sin(delta_latitude/2.0)**2
            b = cos(this_latitude) * cos(another_latitude) * (sin(delta_longitude/2.0)**2)
            c = min(1, sqrt(a+b))
            return 2.0 * self.EARTH_RADIUS_METERS * asin(c)
        else:
            return NAN
