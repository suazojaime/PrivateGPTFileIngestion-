__author__ = 'shattar'

# Kilometers
TRAVEL_DISTANCE_NONE_THRESHOLD = 0.005
TRAVEL_DISTANCE_SHORT_THRESHOLD = 0.040

_TRAVEL_EMPTY_DISTANCE_FACTOR = 2.0


def is_travel_distance_none(distance, travel_distance_none_threshold):
    """
    Determines if the travel distance is virtually zero.

    :param distance: Distance travelled in kilometers.
    :type distance: :class:`float`
    :param travel_distance_none_threshold: Distance threshold in kilometers.
    :type travel_distance_none_threshold: :class:`float`
    :returns: (:class:`bool`) -- `True` if the travel distance is effectively none, otherwise, `False`
    """
    if distance <= travel_distance_none_threshold:
        return True
    else:
        return False


def is_travel_distance_short(distance, travel_distance_short_threshold):
    """
    Determines if the travel distance short.

    A travel distance of short includes 'none'.

    :param distance: Distance travelled in kilometers.
    :type distance: :class:`float`
    :param travel_distance_short_threshold: Distance threshold in kilometers.
    :type travel_distance_short_threshold: :class:`float`
    :returns: (:class:`bool`) -- `True` if the travel distance is short, otherwise, `False`
    """
    if distance <= travel_distance_short_threshold:
        return True
    else:
        return False


def is_travel_distance_long(distance, travel_distance_short_threshold):
    """
    Determines if the travel distance long.

    A travel distance of long is mutually exclusive with 'short' and 'none'.

    :param distance: Distance travelled in kilometers.
    :type distance: :class:`float`
    :param travel_distance_short_threshold: Distance threshold in kilometers.
    :type travel_distance_short_threshold: :class:`float`
    :returns: (:class:`bool`) -- `True` if the travel distance is long, otherwise, `False`
    """
    if distance > travel_distance_short_threshold:
        return True
    else:
        return False


def is_travel_empty_distance_ok(travel_loaded_distance, travel_empty_distance, travel_distance_short_threshold):
    """
    Compares two travel distances, the travel loaded distance and the travel empty distance, to determine if they are
    close enough to be considered part of the same cycle.

    :param travel_loaded_distance: The travel loaded distance, in kilometers.
    :type travel_loaded_distance: :class:`float`
    :param travel_empty_distance: The travel loaded distance, in kilometers.
    :type travel_empty_distance: :class:`float`
    :param travel_distance_short_threshold: Distance threshold in kilometers.
    :type travel_distance_short_threshold: :class:`float`
    :returns: (:class:`bool`) -- `False` if the travel empty distance is too long for the travel loaded distance,
        otherwise, `True`
    """
    base_distance = max(travel_loaded_distance, travel_distance_short_threshold)
    ok_distance = base_distance * _TRAVEL_EMPTY_DISTANCE_FACTOR
    if travel_empty_distance > ok_distance:
        return False
    else:
        return True
