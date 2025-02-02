#from past.builtins import xrange
#from app_cycle_id import Cycle, SegmentIds, CycleIds
#from .thresholds import is_travel_distance_none, TRAVEL_DISTANCE_NONE_THRESHOLD
# from ..machine_properties import default_machine_properties
import math

__author__ = 'shattar'

NAN = float('nan')


class MwlCycle(Cycle):

    __slots__ = ['_identifier', '_segment_list', '_start_location', '_dest_location',
                 'moved_payload', 'moved_payload_accuracy',
                 'dig_time', 'loaded_travel_time', 'loaded_wait_time',
                 'dump_time', 'empty_travel_time', 'empty_wait_time', 'other_time']

    def __init__(self, identifier=None):
        """
        Medium Wheel Loader cycle record.

        Implements a cycle record with additional Medium Wheel Loader specific statistics.

        :param identifier: The cycle identifier.
        :type identifier: :class:`int`
        """

        # Common
        Cycle.__init__(self, identifier=identifier)

        # MWL specific (maybe put this in the 'mwl' package and derive from 'Cycle'?)
        self.moved_payload = NAN  #: (:class:`float`) -- Total moved payload, in tonnes.
        self.moved_payload_accuracy = NAN  #: (:class:`int`) -- Accuracy category, 0 through 3, higher is better.
        self.dig_time = NAN  #: (:class:`float`) -- Time spent digging, in seconds.
        self.loaded_travel_time = NAN  #: (:class:`float`) -- Time spent travelling loaded, in seconds.
        self.loaded_wait_time = NAN  #: (:class:`float`) -- Time spent waiting loaded, in seconds.
        self.dump_time = NAN  #: (:class:`float`) -- Time spent dumping, in seconds.
        self.empty_travel_time = NAN  #: (:class:`float`) -- Time spent travelling empty, in seconds.
        self.empty_wait_time = NAN  #: (:class:`float`) -- Time spent waiting empty, in seconds.
        self.other_time = NAN  #: (:class:`float`) -- Time spent doing other stuff, in seconds.

    @property
    def stored_payload(self):
        """(:class:`float`) -- Total stored payload in tonnes."""
        ###change code due to jython jar issue:pcf
        ###  return math.fsum([segment.stored_payload for segment in self.segment_list])
        return sum([segment.stored_payload for segment in self.segment_list])

    ### change code due to jython:pcf
    def getMoved_payload(self):
        return self.moved_payload

    def update_statistics(self, properties=None):
        """
        This method is called by the cycle generator in order to update derived statistics after all of
        the segments have been properly associate to the cycle.

        This is responsible for calculating some of the more complication statistics, such as moved payload.

        :param properties: The machine properties.
        :type identifier: :class:`dict`
        """
        Cycle.update_statistics(self, properties=properties)

        if properties is None:
            properties = default_machine_properties

        travel_distance_none_threshold = properties.get('travel_distance_none', TRAVEL_DISTANCE_NONE_THRESHOLD)

        number_of_segments = len(self.segment_list)

        is_dig = [(segment.identifier == SegmentIds.DIG) for segment in self.segment_list]
        is_loaded_travel = [(segment.identifier == SegmentIds.TRAVEL_LOADED) for segment in self.segment_list]
        is_dump = [((segment.identifier == SegmentIds.DUMP) or
                    (segment.identifier == SegmentIds.PARTIAL_DUMP))
                   for segment in self.segment_list]
        is_empty_travel = [((segment.identifier == SegmentIds.TRAVEL_EMPTY) or
                            (segment.identifier == SegmentIds.BACKDRAG))
                           for segment in self.segment_list]
        is_loaded_stopped = [(segment.identifier == SegmentIds.STOPPED_LOADED) for segment in self.segment_list]
        is_empty_stopped = [(segment.identifier == SegmentIds.STOPPED_EMPTY) for segment in self.segment_list]

        # Mark the loaded portion of the cycle
        is_loaded = [False]*number_of_segments
        if any(is_dig) or any(is_loaded_travel):
            if any(is_dump):
                # The first travel empty after the first dump is the first unloaded segment
                seen_dump = False
                for idx in xrange(number_of_segments):
                    if seen_dump and is_empty_travel[idx]:
                        break
                    elif is_dump[idx]:
                        seen_dump = True
                    is_loaded[idx] = True
            elif any(is_empty_travel):
                # The first travel empty is the first unloaded segment
                for idx in xrange(number_of_segments):
                    if is_empty_travel[idx]:
                        break
                    is_loaded[idx] = True
            else:
                is_loaded = [True]*number_of_segments

        # The dig location is the location of the last dig
        dig_indices = [idx for idx, keep in enumerate(is_dig) if keep]
        if len(dig_indices) > 0:
            last_dig_idx = dig_indices[-1]
            self._start_location = (
                self.segment_list[last_dig_idx].latitude,
                self.segment_list[last_dig_idx].longitude,
                self.segment_list[last_dig_idx].altitude
            )
        else:
            last_dig_idx = -1
            self._start_location = None

        # The dump location is the location of the last loaded dump
        # (the first dump prior to the first travel empty)
        loaded_dump_indices = [idx for idx, keep in enumerate(zip(is_dump, is_loaded)) if all(keep)]
        if len(loaded_dump_indices) > 0:
            final_dump_idx = loaded_dump_indices[-1]
            self._dest_location = (
                self.segment_list[final_dump_idx].latitude,
                self.segment_list[final_dump_idx].longitude,
                self.segment_list[final_dump_idx].altitude
            )
        else:
            self._dest_location = None

        # Determine the moved payload
        # If this is not a loading cycle, moved payload is NaN
        if (any(is_dig) or any(is_loaded_travel)) and (self.identifier not in (CycleIds.PILE_CLEANUP,)):
            # Find the first travel loaded after the last dig
            # May want to threshold the travel loaded distance first to avoid blips
            # of loaded travel, but not not
            loaded_travel_indices = [idx for idx, keep in enumerate(is_loaded_travel) if keep and (idx > last_dig_idx)]
            if len(loaded_travel_indices) > 0:
                first_loaded_travel_idx = loaded_travel_indices[0]
            else:
                first_loaded_travel_idx = last_dig_idx + 1

            # Now that we know where to start from (the first travel loaded after the last dig), we can loop forward
            # looking for the best payload prioor to the first dump
            payload = NAN
            payload_accuracy = 0
            have_seen_dump_away_from_pile = False
            travel_distance_total = 0
            for idx in xrange(first_loaded_travel_idx, number_of_segments):
                segment_payload = self.segment_list[idx].payload
                segment_payload_accuracy = self.segment_list[idx].payload_accuracy
                segment_distance = self.segment_list[idx].distance

                # Advance forward, accumulating travel distance, until we have travelled enough to have moved
                # the payload away from the dig location.
                travel_distance_total += segment_distance

                if is_dump[idx]:
                    if is_travel_distance_none(travel_distance_total, travel_distance_none_threshold):
                        # We have not travelled away from the dig location yet.
                        # The operator has not committed to "moving" this payload.
                        # Let them tip off and adjust the weight.
                        # Any payload that we have captured before this has not been moved.
                        # Now we know they have dumped some off, so know we don't actually
                        # know the moved weight at this point.

                        # Grab the best weight we have up until this point...
                        if segment_payload_accuracy > 0 and segment_payload_accuracy >= payload_accuracy:
                            payload = segment_payload
                            payload_accuracy = segment_payload_accuracy

                        # ...but call the accuracy 0 so that it is replaced with the next weight if it comes.
                        payload_accuracy = 0

                    else:
                        have_seen_dump_away_from_pile = True

                        # Each dump we encounter we have to figure out if we had a payload measurement prior to it.
                        # If we had a payload measurement prior to the dump, then we can use it as the cycle payload.
                        # If we didn't have a payload measurement prior to the dump, then we can keep looking as a last
                        # ditch effort to capture something.

                        # If we don't have a weight yet, then potentially use this one if it's any good.
                        if math.isnan(payload):
                            if segment_payload_accuracy > 0 and segment_payload_accuracy >= payload_accuracy:
                                payload = segment_payload
                                payload_accuracy = segment_payload_accuracy

                elif have_seen_dump_away_from_pile:
                    if is_empty_travel[idx]:
                        # We are now travelling empty.  If a dump occurred prior to this, then we can assume we are
                        # travelling empty because of the dump and we can't measure the carried payload any more because
                        # it is gone.
                        # If we haven't seen a dump yet, then we are just carrying a small amount of material and we can
                        # keep looking for the best measurement of it.
                        break
                    elif segment_payload_accuracy > 0 and segment_payload_accuracy > payload_accuracy:
                        # If this is after the dump, then we want the earliest payload weight, assuming things
                        # that are closer to the dump are more reflective of what was dumped at the dump.
                        payload = segment_payload
                        payload_accuracy = segment_payload_accuracy

                elif segment_payload_accuracy > 0 and segment_payload_accuracy >= payload_accuracy:
                    # If this is prior to the dump, then we want the latest payload weight, assuming things
                    # that are closer to the dump are more reflective of what was dumped at the dump.
                    payload = segment_payload
                    payload_accuracy = segment_payload_accuracy

                # I have a payload now and I have seen a dump away from the pile.  We have to be done.
                if have_seen_dump_away_from_pile and not math.isnan(payload):
                    break

            self.moved_payload = payload
            self.moved_payload_accuracy = payload_accuracy
        else:
            self.moved_payload = NAN

        # Allocate the duration to different buckets
        self.dig_time = math.fsum([segment.duration
                                   for segment, keep in zip(self.segment_list, is_dig) if keep])

        self.loaded_travel_time = math.fsum([segment.duration
                                             for segment, keep in zip(self.segment_list, is_loaded_travel) if keep])

        self.dump_time = math.fsum([segment.duration
                                    for segment, keep in zip(self.segment_list, is_dump) if keep])

        self.empty_travel_time = math.fsum([segment.duration
                                            for segment, keep in zip(self.segment_list, is_empty_travel) if keep])

        self.loaded_wait_time = math.fsum([segment.duration
                                           for segment, keep in zip(self.segment_list, is_loaded_stopped) if keep])

        self.empty_wait_time = math.fsum([segment.duration
                                          for segment, keep in zip(self.segment_list, is_empty_stopped) if keep])

        self.other_time = self.duration - (self.dig_time + self.loaded_travel_time + self.dump_time +
                                           self.empty_travel_time + self.loaded_wait_time + self.empty_wait_time)
