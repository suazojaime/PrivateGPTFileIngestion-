### change code due to jython:pcf
#from app_cycle_id import CycleIdentifer, CycleIds, SegmentIds, WaitingCycleIdentifier
#from thresholds import is_travel_distance_long

__author__ = 'shattar'


class RoadingCycleIdentifier(CycleIdentifer):

    _STATE_INITIAL = 0
    _STATE_TRAVEL_EMPTY = 1

    def __init__(self):
        """
        Roading cycle identifier implementation.

        Characterized by mostly travel empty segments that do not occur within the context of another application.
        """
        CycleIdentifer.__init__(self, CycleIds.ROADING)
        self._state = self._STATE_INITIAL
        self._travel_distance = 0.0
        self._stopped_duration = 0.0
        self._number_of_segments = 0

        # Default values for travel distance thresholds
        self._travel_distance_short_threshold = TRAVEL_DISTANCE_SHORT_THRESHOLD

    def reinit(self, properties=None):
        """
        Reinitialized the cycle identifier so that it can be used again.

        :param properties: The machine properties.
        :type identifier: :class:`dict`
        """
        CycleIdentifer.reinit(self, properties)
        self._state = self._STATE_INITIAL
        self._travel_distance = 0.0
        self._stopped_duration = 0.0
        self._number_of_segments = 0

        # Get the travel distance thresholds from the provided machine properties
        self._travel_distance_short_threshold = self.properties.get('travel_distance_short',
                                                                    TRAVEL_DISTANCE_SHORT_THRESHOLD)

    def update(self, solver, segment):
        """
        Update a roading cycle identifier with the next segment.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if self._state == self._STATE_INITIAL:
            self._state = self._state_initial(solver, segment)
        elif self._state == self._STATE_TRAVEL_EMPTY:
            self._state = self._state_travel_empty(solver, segment)
        else:
            solver.abandon_marked_segments()
            self.reinit()

    def _state_initial(self, solver, segment):
        """
        Update when in the initial state, waiting for a travel empty to kick off the cycle.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if segment.identifier == SegmentIds.TRAVEL_EMPTY:
            # Start
            solver.mark_segment()
            self._travel_distance = segment.distance
            self._stopped_duration = 0.0
            self._number_of_segments = 1
            # If travel distance is long, claim it
            if is_travel_distance_long(self._travel_distance, self._travel_distance_short_threshold):
                solver.claim_marked_segments()
            return self._STATE_TRAVEL_EMPTY
        else:
            return self._STATE_INITIAL

    def _state_travel_empty(self, solver, segment):
        """
        Update when in the travel empty state, continue to claim travel empty segments if they are long enough.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if segment.identifier == SegmentIds.TRAVEL_EMPTY:
            # Continue
            solver.mark_segment()
            self._travel_distance += segment.distance
            self._stopped_duration = 0.0
            self._number_of_segments += 1

            if self._number_of_segments >= Solver.LONGEST_UNRESOLVED_SEGMENT_SEQUENCE:
                # If the travel distance is long, claim it
                if is_travel_distance_long(self._travel_distance, self._travel_distance_short_threshold):
                    solver.claim_marked_segments()

            return self._STATE_TRAVEL_EMPTY

        elif segment.identifier == SegmentIds.STOPPED_EMPTY:
            stopped_duration = self._stopped_duration + segment.duration

            if WaitingCycleIdentifier.is_stopped_duration_long(stopped_duration):
                if is_travel_distance_long(self._travel_distance, self._travel_distance_short_threshold):
                    solver.claim_marked_segments()
                else:
                    solver.abandon_marked_segments()
                return self._STATE_INITIAL

            # Continue
            solver.mark_segment()
            self._travel_distance += segment.distance
            self._stopped_duration = stopped_duration
            self._number_of_segments += 1

            if self._number_of_segments >= Solver.LONGEST_UNRESOLVED_SEGMENT_SEQUENCE:
                # If the travel distance is long, claim it
                if is_travel_distance_long(self._travel_distance, self._travel_distance_short_threshold):
                    solver.claim_marked_segments()

            return self._STATE_TRAVEL_EMPTY

        else:
            if is_travel_distance_long(self._travel_distance, self._travel_distance_short_threshold):
                solver.claim_marked_segments()
            else:
                # Abandon
                solver.abandon_marked_segments()
            return self._STATE_INITIAL
