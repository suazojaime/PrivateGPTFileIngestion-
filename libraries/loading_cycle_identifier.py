### change code due to jython:pcf
#from app_cycle_id import CycleIdentifer, CycleIds, SegmentIds, WaitingCycleIdentifier
#from thresholds import is_travel_distance_none, is_travel_distance_long, is_travel_empty_distance_ok

__author__ = 'shattar'


class _BaseLoadingCycleIdentifier(CycleIdentifer):

    _STATE_INITIAL = 0
    _STATE_ACTIVE = 1

    def __init__(self, identifier):
        """
        The base class for loading type cycle identifiers.

        This provides a skeleton for walking through the typical loading cycle process and only defers to the child
        class where things are intended to differ.

        :param identifier: The cycle identifier.
        :type identifier: :class:`int`
        """
        CycleIdentifer.__init__(self, identifier)
        self._state = self._STATE_INITIAL
        self._travel_distance_total = 0.0
        self._travel_distance_before_dump = 0.0
        self._travel_distance_after_dump = 0.0
        self._have_seen_dump = False
        self._have_seen_final_dump = False
        self._stopped_empty_duration = 0.0

        # Default values for travel distance thresholds
        self._travel_distance_none_threshold = TRAVEL_DISTANCE_NONE_THRESHOLD
        self._travel_distance_short_threshold = TRAVEL_DISTANCE_SHORT_THRESHOLD

    def reinit(self, properties=None):
        """
        Reinitialized the cycle identifier so that it can be used again.

        :param properties: The machine properties.
        :type identifier: :class:`dict`
        """
        CycleIdentifer.reinit(self, properties)
        self._state = self._STATE_INITIAL
        self._travel_distance_total = 0.0
        self._travel_distance_before_dump = 0.0
        self._travel_distance_after_dump = 0.0
        self._have_seen_dump = False
        self._have_seen_final_dump = False
        self._stopped_empty_duration = 0.0

        # Get the travel distance thresholds from the provided machine properties
        self._travel_distance_none_threshold = self.properties.get('travel_distance_none',
                                                                   TRAVEL_DISTANCE_NONE_THRESHOLD)
        self._travel_distance_short_threshold = self.properties.get('travel_distance_short',
                                                                    TRAVEL_DISTANCE_SHORT_THRESHOLD)


    def update(self, solver, segment):
        """
        Update a loading cycle identifier with the next segment.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if self._state == self._STATE_INITIAL:
            self._state = self._state_initial(solver, segment)

        elif self._state == self._STATE_ACTIVE:
            dig = {SegmentIds.DIG}
            dump = {SegmentIds.DUMP, SegmentIds.PARTIAL_DUMP}
            other = {SegmentIds.TRAVEL_LOADED, SegmentIds.TRAVEL_EMPTY, SegmentIds.MISC, SegmentIds.BACKDRAG,
                     SegmentIds.STOPPED_EMPTY, SegmentIds.STOPPED_LOADED}
            ignore = {SegmentIds.IDLE}

            if segment.identifier in dig:
                self._stopped_empty_duration = 0.0
                self._state = self._state_active_dig(solver, segment)

            elif segment.identifier in dump:
                self._stopped_empty_duration = 0.0
                if not self._have_seen_final_dump:
                    self._travel_distance_after_dump = 0.0
                self._have_seen_dump = True
                self._travel_distance_before_dump = self._travel_distance_total - self._travel_distance_after_dump
                solver.mark_segment()
                self._state = self._state_active_dump(solver, segment)

            elif segment.identifier in other:
                # Update travel distance
                self._travel_distance_total += segment.distance
                if self._have_seen_dump:
                    self._travel_distance_after_dump += segment.distance
                    if segment.identifier == SegmentIds.TRAVEL_EMPTY:
                        self._have_seen_final_dump = True
                self._travel_distance_before_dump = self._travel_distance_total - self._travel_distance_after_dump

                # Update stopped duration
                if segment.identifier == SegmentIds.STOPPED_EMPTY:
                    self._stopped_empty_duration += segment.duration
                elif (segment.identifier == SegmentIds.STOPPED_LOADED) and self._have_seen_final_dump:
                    self._stopped_empty_duration += segment.duration
                else:
                    self._stopped_empty_duration = 0.0

                solver.mark_segment()
                self._state = self._state_active_other(solver, segment)

            elif segment.identifier in ignore:
                self._state = self._state_active_ignore(solver, segment)

            else:
                solver.abandon_marked_segments()
                self._state = self._STATE_INITIAL

        else:
            solver.abandon_marked_segments()
            self._state = self._STATE_INITIAL

    def _state_initial(self, solver, segment):
        """
        Update when in the initial state, waiting for a dig to kick off the cycle.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        new_state = self._STATE_INITIAL
        dig = {SegmentIds.DIG}
        if segment.identifier in dig:
            # Start
            solver.mark_segment(cycle_start=True)
            self.reinit()
            new_state = self._STATE_ACTIVE
        return new_state

    def _state_active_dig(self, solver, segment):
        """
        Update when in the active 'dig' state, needs to be overriden with a specific implementation.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        :raises NotImplementedError: Abstact method
        """
        raise NotImplementedError('Abstract method')

    def _state_active_dump(self, solver, segment):
        """
        Update when in the active 'dump' state, needs to be overriden with a specific implementation.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        :raises NotImplementedError: Abstact method
        """
        raise NotImplementedError('Abstract method')

    def _state_active_other(self, solver, segment):
        """
        Update when in the active 'other' state, needs to be overriden with a specific implementation.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        :raises NotImplementedError: Abstact method
        """
        raise NotImplementedError('Abstract method')

    def _state_active_ignore(self, solver, segment):
        """
        Update when in the active 'ignore' state.

        Ends the cycle if the 'ignored' segment happened after the final dump, otherwise, continues on with the cycle,
        ignoring the current segment.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        new_state = self._STATE_ACTIVE
        if self._have_seen_final_dump:
            solver.abandon_marked_segments()
            new_state = self._STATE_INITIAL
        else:
            solver.ignore_segment()
        return new_state


class PileCleanupCycleIdentifier(_BaseLoadingCycleIdentifier):
    def __init__(self):
        """
        Pile Cleanup cycle identifier implementation.

        A sequence of segments that starts with a Dig where the of travel that occurs prior to delivering the material
        is extremely short.  Can include backdragging.
        """
        _BaseLoadingCycleIdentifier.__init__(self, CycleIds.PILE_CLEANUP)

    def _state_active_dig(self, solver, segment):
        """
        Update when in the active 'dig' state.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if is_travel_distance_none(self._travel_distance_total, self._travel_distance_none_threshold):
            # Double dig, stay active
            solver.mark_segment()
        else:
            if self._have_seen_final_dump:
                # We have seen the final dump and we got this far without ending the cycle,
                # then we can claim and start a new potential cycle.
                solver.claim_marked_segments()
            else:
                # Didn't see a dump, can't count this.
                solver.abandon_marked_segments()
            solver.mark_segment(cycle_start=True)

        self.reinit()
        return self._STATE_ACTIVE

    def _state_active_dump(self, solver, segment):
        """
        Update when in the active 'dump' state.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        new_state = self._STATE_ACTIVE
        if self._have_seen_final_dump:
            # We already know this is a cleanup cycle, otherwise we would have bailed after identifying the final dump.
            # Now we are just looking to see if this subsequent segment should also be included in this cycle.
            if is_travel_empty_distance_ok(self._travel_distance_before_dump, self._travel_distance_after_dump,
                                           self._travel_distance_short_threshold):
                solver.claim_marked_segments()
            else:
                solver.abandon_marked_segments()
                new_state = self._STATE_INITIAL
        elif not is_travel_distance_none(self._travel_distance_before_dump, self._travel_distance_none_threshold):
            # This is not cleanup because we already accumulated too much travel distance
            solver.abandon_marked_segments()
            new_state = self._STATE_INITIAL
        else:
            # Claim it now, if it ends up being loading or load and carry,
            # they will trump cleanup due to their higher priority
            solver.claim_marked_segments()
        return new_state

    def _state_active_other(self, solver, segment):
        """
        Update when in the active 'other' state.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        new_state = self._STATE_ACTIVE
        if self._have_seen_final_dump:
            if not is_travel_distance_none(self._travel_distance_before_dump, self._travel_distance_none_threshold):
                # Have seen the final dump, and the distance travelled before the final dump
                # was too long to be considered cleanup
                solver.abandon_marked_segments()
                new_state = self._STATE_INITIAL

            else:
                # Have seen the final dump, and we know it is cleanup.
                # We are just looking to see if this segment should also be included in the cycle.
                if is_travel_empty_distance_ok(self._travel_distance_before_dump, self._travel_distance_after_dump,
                                               self._travel_distance_short_threshold):
                    if self._stopped_empty_duration > 0.0:
                        if WaitingCycleIdentifier.is_stopped_duration_long(self._stopped_empty_duration):
                            # Stopped too long to continue
                            solver.abandon_marked_segments()
                            new_state = self._STATE_INITIAL

                        else:
                            # Stopped, but not for long, just wait
                            pass

                    else:
                        # Not stopped, and travel empty distance is ok
                        solver.claim_marked_segments()

                else:
                    solver.abandon_marked_segments()
                    new_state = self._STATE_INITIAL

        elif not is_travel_distance_none(self._travel_distance_before_dump, self._travel_distance_none_threshold):
            # Can't travel too much prior to the dump if it is to be considered cleanup
            solver.abandon_marked_segments()
            new_state = self._STATE_INITIAL

        elif WaitingCycleIdentifier.is_stopped_duration_long(self._stopped_empty_duration):
            # Stopped too long to continue
            solver.abandon_marked_segments()
            new_state = self._STATE_INITIAL

        return new_state


class LoadingCycleIdentifier(_BaseLoadingCycleIdentifier):
    def __init__(self):
        """
        Loadind cycle identifier implementation.

        A sequence of segments that starts with a Dig where a relatively short distance of travel occurs prior to
        delivering the material.
        """
        _BaseLoadingCycleIdentifier.__init__(self, CycleIds.LOADING)

    def _state_active_dig(self, solver, segment):
        """
        Update when in the active 'dig' state.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if is_travel_distance_none(self._travel_distance_total, self._travel_distance_none_threshold):
            # Double dig, stay active
            solver.mark_segment()
        else:
            if self._have_seen_final_dump:
                # We have seen the final dump and we got this far without ending the cycle,
                # then we can claim and start a new potential cycle.
                solver.claim_marked_segments()
            else:
                # Didn't see a dump, can't count this.
                solver.abandon_marked_segments()
            solver.mark_segment(cycle_start=True)

        self.reinit()
        return self._STATE_ACTIVE

    def _state_active_dump(self, solver, segment):
        """
        Update when in the active 'dump' state.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        new_state = self._STATE_ACTIVE
        if self._have_seen_final_dump:
            # We already know this is a loading cycle, otherwise we would have bailed after identifying the final dump.
            # Now we are just looking to see if this subsequent segment should also be included in this cycle.
            if is_travel_empty_distance_ok(self._travel_distance_before_dump, self._travel_distance_after_dump,
                                           self._travel_distance_short_threshold):
                solver.claim_marked_segments()
            else:
                solver.abandon_marked_segments()
                new_state = self._STATE_INITIAL
        elif is_travel_distance_long(self._travel_distance_before_dump, self._travel_distance_short_threshold):
            # Definitely not loading because we have already accumulated too much travel distance
            solver.abandon_marked_segments()
            new_state = self._STATE_INITIAL
        elif not is_travel_distance_none(self._travel_distance_before_dump, self._travel_distance_none_threshold):
            # This is loading (or load and carry).  If it is load and carry,
            # then load and carry will claim it with higher priority
            solver.claim_marked_segments()
        else:
            # Travel distance before dump is none, so it could be cleanup
            pass

        return new_state

    def _state_active_other(self, solver, segment):
        """
        Update when in the active 'other' state.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        new_state = self._STATE_ACTIVE
        if self._have_seen_final_dump:
            if is_travel_distance_long(self._travel_distance_before_dump, self._travel_distance_short_threshold) or \
                    is_travel_distance_none(self._travel_distance_before_dump, self._travel_distance_none_threshold):
                # Have seen the final dump and the distance travelled before the final dump
                # was too short or long to be considered loading
                solver.abandon_marked_segments()
                new_state = self._STATE_INITIAL

            else:
                # Have seen the final dump and we know it is loading.
                # We are just looking to see if this segment should also be included in the cycle.
                if is_travel_empty_distance_ok(self._travel_distance_before_dump, self._travel_distance_after_dump,
                                               self._travel_distance_short_threshold):
                    if self._stopped_empty_duration > 0.0:
                        if WaitingCycleIdentifier.is_stopped_duration_long(self._stopped_empty_duration):
                            # Stopped too long to continue
                            solver.abandon_marked_segments()
                            new_state = self._STATE_INITIAL

                        else:
                            # Stopped, but not for long, just wait
                            pass

                    else:
                        # Not stopped, and travel empty distance is ok
                        solver.claim_marked_segments()

                else:
                    solver.abandon_marked_segments()
                    new_state = self._STATE_INITIAL

        elif is_travel_distance_long(self._travel_distance_before_dump, self._travel_distance_short_threshold):
            # Travelled too far to be truck loading
            solver.abandon_marked_segments()
            new_state = self._STATE_INITIAL

        elif WaitingCycleIdentifier.is_stopped_duration_long(self._stopped_empty_duration):
            # Stopped too long to continue
            solver.abandon_marked_segments()
            new_state = self._STATE_INITIAL

        return new_state


class LoadAndCarryCycleIdentifier(_BaseLoadingCycleIdentifier):
    def __init__(self):
        """
        Load and Carry cycle identifier implementation.

        A sequence of segments that starts with a Dig where a relatively long distance of travel occurs prior to
        delivering the material.
        """
        _BaseLoadingCycleIdentifier.__init__(self, CycleIds.LOAD_AND_CARRY)

    def _state_active_dig(self, solver, segment):
        """
        Update when in the active 'dig' state.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        if is_travel_distance_none(self._travel_distance_total, self._travel_distance_none_threshold):
            # Double dig, stay active
            solver.mark_segment()
        else:
            if self._have_seen_final_dump:
                # Only grab the activity leading up to this if the next cycle is also
                # load and carry.  If it was part of the last cycle, it was already claimed anyway
                pass
            else:
                # Didn't see a dump, can't count this.
                solver.abandon_marked_segments()
            solver.mark_segment(cycle_start=True)

        self.reinit()
        return self._STATE_ACTIVE

    def _state_active_dump(self, solver, segment):
        """
        Update when in the active 'dump' state.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """

        # These following two lines are only for testing.  Uncomment in order to recreate a bug that used to exist.
        # self._travel_distance_total += segment.distance
        # self._travel_distance_before_dump = self._travel_distance_total - self._travel_distance_after_dump

        new_state = self._STATE_ACTIVE
        if self._have_seen_final_dump:
            # We already know this is a load and carry cycle, otherwise we would have bailed after identifying
            # the final dump.  New we are just looking to see if this subsequent segment should also be included
            # in this cycle.
            if is_travel_empty_distance_ok(self._travel_distance_before_dump, self._travel_distance_after_dump,
                                           self._travel_distance_short_threshold):
                solver.claim_marked_segments()
            else:
                solver.abandon_marked_segments()
                new_state = self._STATE_INITIAL
        elif is_travel_distance_long(self._travel_distance_before_dump, self._travel_distance_short_threshold):
            # Definitely not cleanup or truck loading because we have already accumulated too much travel distance.
            # We can claim this a load and carry
            solver.claim_marked_segments()
        else:
            # If could be cleanup or truck loading, can't claim it yet
            pass
        return new_state

    def _state_active_other(self, solver, segment):
        """
        Update when in the active 'other' state.

        :param solver: The solver that is used to resolve the requests this cycle identifier.
        :type solver: :class:`~app_cycle_id.solver.Solver`
        :param segment: The current segment to be processed.
        :type segment: :class:`~app_cycle_id.segment.Segment`
        """
        new_state = self._STATE_ACTIVE
        if self._have_seen_final_dump:
            if is_travel_distance_long(self._travel_distance_before_dump, self._travel_distance_short_threshold):
                # We have seen the final dump, and we know it is load and carry.  We are just looking to see if this
                # segment should also be included in the cycle.
                if is_travel_empty_distance_ok(self._travel_distance_before_dump, self._travel_distance_after_dump,
                                               self._travel_distance_short_threshold):
                    if self._stopped_empty_duration > 0.0:
                        if WaitingCycleIdentifier.is_stopped_duration_long(self._stopped_empty_duration):
                            # Stopped too long to continue
                            solver.abandon_marked_segments()
                            new_state = self._STATE_INITIAL

                        else:
                            # Stopped, but not for long, just wait
                            pass

                    else:
                        # Not stopped, and travel empty distance is ok
                        solver.claim_marked_segments()

                else:
                    solver.abandon_marked_segments()
                    new_state = self._STATE_INITIAL

            else:
                # Not long enough to be considered a load and carry, and we have seen the final dump,
                # so we have to abandon.
                solver.abandon_marked_segments()
                new_state = self._STATE_INITIAL

        elif WaitingCycleIdentifier.is_stopped_duration_long(self._stopped_empty_duration):
            # Stopped too long to continue
            solver.abandon_marked_segments()
            new_state = self._STATE_INITIAL

        else:
            # Can't claim until we see the final dump
            pass

        return new_state
