### change code due to jython:pcf
#from app_cycle_id import CycleIds
#from solver import Solver
#from cycle import Cycle
#from payload import associate_payloads_and_loads
#from segment import associate_payloads_to_segments, associate_locations_to_segments
# from _array import where
from minestar.health.util.ccdscycles.com.jython import CycleGeneratorType

__author__ = 'shattar'


### change code due to jython:pcf
class CycleGenerator(CycleGeneratorType):
    def __init__(self, cycle_identifier_list, cycle_class=Cycle):
        """
        Cycle Generator base class.

        This is the default implementation for generating cycles from segments, given a list of cycle identifiers and a
        class that represents a cycle record.

        :param cycle_identifier_list: Prioritized list of cycle identifier objects.
        :type cycle_identifier_list: list of :class:`~app_cycle_id.cycle_identifier.CycleIdentifer`
        :param cycle_class: The specific class implementing the :class:`Cycle <app_cycle_id.cycle.Cycle>` interface.
        :type cycle_class: :class:`type`
        """
        self._solver = Solver(cycle_identifier_list)
        self._cycle_class = cycle_class

    def _update_cycle_statistics(self, cycle_list, properties=None):
        """
        Called after the cycles are identified in order to update the statistics of each cycle in the cycle list.

        :param cycle_list: List of cycles.
        :type cycle_list: list of :class:`~app_cycle_id.cycle.Cycle`
        :param properties: The machine properties.
        :type identifier: :class:`dict`
        """
        for cycle in cycle_list:
            cycle.update_statistics(properties=properties)

    def generate_cycles(self, segment_list, payload_list=None, load_list=None, location_list=None, status_list=None, sales_model=None):
        """
        Generates a list of cycles given a list of segments.

        Optionally, additional records can be supplied in order to provide additional cycle statistics.

        :param segment_list: List of segment records.
        :type segment_list: list of :class:`~app_cycle_id.segment.Segment`
        :param payload_list: List of payload records.
        :type payload_list: list of :class:`~app_cycle_id.payload.Payload`
        :param load_list: List of load records.
        :type load_list: list of :class:`~app_cycle_id.payload.Load`
        :param location_list: List of location records
        :type location_list: list of :class:`~app_cycle_id.location.Location`
        :param status_list: List of status records (not yet implemented)
        :type status_list: list of :class:`Status`
        :param sales_model: Sales model of machine used to look up properties.
        :type sales_model: :class:`str`
        :returns: (list of :class:`~app_cycle_id.cycle.Cycle`) -- List of cycle records.
        """
        # Get machine properties from the sales model
        if isinstance(sales_model, str):
            machine_properties = machine_properties_dict.get(sales_model[:3], default_machine_properties)
        else:
            machine_properties = default_machine_properties

        # Associate payload and load records
        associate_payloads_and_loads(load_list, payload_list)

        # Associate payloads to segments
        associate_payloads_to_segments(segment_list, payload_list)

        # Associate locations to segments
        associate_locations_to_segments(segment_list, location_list)

        # Identify the application cycle for each segment
        self._solver.reinit(properties=machine_properties)
        cycle_ids, cycle_starts = self._solver.solve(segment_list)

        # Create application cycle list and associate cycles and segments
        cycle_start_segment_indices = where(cycle_starts)
        # cycle_start_segment_indices, = np.where(cycle_starts)
        number_of_cycles = len(cycle_start_segment_indices)
        cycle_list = [None]*number_of_cycles
        for cycle_idx in xrange(number_of_cycles):
            first_segment_idx = cycle_start_segment_indices[cycle_idx]
            cycle = self._cycle_class(identifier=cycle_ids[first_segment_idx])

            # Associate the first segment with the current cycle
            cycle.segment_list.append(segment_list[first_segment_idx])
            segment_list[first_segment_idx].cycle_record = cycle

            # Find the last segment of this cycle
            for segment_idx in xrange(first_segment_idx+1, len(cycle_ids)):
                if cycle_ids[segment_idx] == CycleIds.NONE:
                    break
                elif cycle_ids[segment_idx] == cycle_ids[first_segment_idx]:
                    if cycle_starts[segment_idx]:
                        # Found another segment of this cycle id, but it is the start of a new cycle,
                        # so we've found the end
                        break
                    else:
                        # Found another segment that belongs to the current cycle,
                        # Associate the segment with the current cycle
                        cycle.segment_list.append(segment_list[segment_idx])
                        segment_list[segment_idx].cycle_record = cycle
                else:
                    # Found a segment that belongs to a different cycle id, but this cycle may still continue
                    # after this segment due to interrupted cycles, continue searching
                    pass

            # Add the new cycle entry
            cycle_list[cycle_idx] = cycle

        self._update_cycle_statistics(cycle_list, properties=machine_properties)

        return cycle_list
