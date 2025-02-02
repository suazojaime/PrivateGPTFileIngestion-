import collections
### change code due to jython:pcf
#from segment_identifier import SegmentIds

__author__ = 'shattar'


class CycleIdentifer(object):
    def __init__(self, identifier):
        """
        Base class for all cycle identifier implementations.

        :param identifier: Cycle identifier.
        :type identifier: :class:`int`
        """
        self._identifier = identifier
        self.properties = None

    @property
    def identifier(self):
        """(:class:`int`) -- Cycle identifier."""
        return self._identifier

    def reinit(self, properties=None):
        """
        Reinitializes the identifier such that it can be used again on another sequence of segments.
        This default implementation does nothing.

        :param properties: The machine properties.
        :type identifier: :class:`dict`
        """
        if properties is not None:
            self.properties = properties
        elif self.properties is None:
            self.properties = default_machine_properties

    def update(self, solver, segment):
        """
        Update the cycle identifier with the next segment.  This is an abstract method and must be implemented by
        child classes.

        Given this observed segment, the cycle identifier should do one of the following things:

        - nothing
        - mark the segment using :meth:`solver.mark_segment() <app_cycle_id.solver.Solver.mark_segment>`
        - ignore the segment using :meth:`solver.ignore_segment() <app_cycle_id.solver.Solver.ignore_segment>`

        In addition, the cycle identifier can make a decision on what to do with the already marked segments:

        - nothing, yet
        - claim marked segments using
          :meth:`solver.claim_marked_segments() <app_cycle_id.solver.Solver.claim_marked_segments>`
        - abandon marked segments using
          :meth:`solver.abandon_marked_segments() <app_cycle_id.solver.Solver.abandon_marked_segments>`

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        :raises NotImplementedError: Abstract method
        """
        raise NotImplementedError('Abstract method')


class OtherCycleIdentifier(CycleIdentifer):
    def __init__(self):
        """
        Implementation of a cycle identifier for the 'Other' application.
        """
        CycleIdentifer.__init__(self, CycleIds.OTHER)

    def update(self, solver, segment):
        """
        Update the 'Other' cycle identifier with the next segment.

        This cycle identifier marks and claims every segment.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        solver.mark_segment()
        solver.claim_marked_segments()


class WaitingCycleIdentifier(CycleIdentifer):

    _STOPPED_DURATION_SHORT = 30.0  # Seconds

    def __init__(self):
        """
        Implementation of a cycle identifier for the 'Waiting' application.
        """
        CycleIdentifer.__init__(self, CycleIds.WAITING)
        self._stopped_duration = 0.0
        self._number_of_segments = 0

    @classmethod
    def is_stopped_duration_short(cls, duration):
        if duration <= cls._STOPPED_DURATION_SHORT:
            return True
        return False

    @classmethod
    def is_stopped_duration_long(cls, duration):
        return not cls.is_stopped_duration_short(duration)

    def reinit(self, properties=None):
        """
        Reinitialized the cycle identifier so that it can be used again.

        :param properties: The machine properties.
        :type identifier: :class:`dict`
        """
        CycleIdentifer.reinit(self, properties)
        self._stopped_duration = 0.0
        self._number_of_segments = 0

    def update(self, solver, segment):
        """
        Update the 'Waiting' cycle identifier with the next segment.

        This cycle identifier marks and claims every segment that is an idle segment.

        This cycle identifier also claims contiguous stopped segments as long as the total duration exceeds a threshold.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if segment.identifier == SegmentIds.IDLE:
            self._stopped_duration += segment.duration
            self._number_of_segments += 1
            solver.mark_segment()
            solver.claim_marked_segments()

        elif segment.identifier in {SegmentIds.STOPPED_LOADED, SegmentIds.STOPPED_EMPTY}:
            self._stopped_duration += segment.duration
            self._number_of_segments += 1
            solver.mark_segment()

            if self._number_of_segments >= Solver.LONGEST_UNRESOLVED_SEGMENT_SEQUENCE:
                if self.is_stopped_duration_long(self._stopped_duration):
                    solver.claim_marked_segments()

        else:
            if self.is_stopped_duration_long(self._stopped_duration):
                solver.claim_marked_segments()
            else:
                solver.abandon_marked_segments()
            self._stopped_duration = 0.0
            self._number_of_segments = 0


class KeyOnEngineOffCycleIdentifier(CycleIdentifer):
    def __init__(self):
        """
        Implementation of a cycle identifier for the 'Key On - Engine Off' application.
        """
        CycleIdentifer.__init__(self, CycleIds.KEY_ON_ENGINE_OFF)

    def update(self, solver, segment):
        """
        Update the 'Key On - Engine Off' cycle identifier with the next segment.

        This cycle identifier marks and claims every segment that is a key on, engine off segment.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if segment.identifier == SegmentIds.KEY_ON_ENGINE_OFF:
            solver.mark_segment()
            solver.claim_marked_segments()


class EngineShutdownCycleIdentifier(CycleIdentifer):
    def __init__(self):
        """
        Implementation of a cycle identifier for the 'Engine Shutdown' application.
        """
        CycleIdentifer.__init__(self, CycleIds.ENGINE_SHUTDOWN)

    def update(self, solver, segment):
        """
        Update the 'Engine Shutdown' cycle identifier with the next segment.

        This cycle identifier marks and claims every segment that is a key-off and engine-on segment.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if segment.identifier == SegmentIds.KEY_OFF_ENGINE_ON:
            solver.mark_segment()
            solver.claim_marked_segments()
