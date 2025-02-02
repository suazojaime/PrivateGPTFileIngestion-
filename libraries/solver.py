### change code due to jython:pcf
#from app_cycle_id import CycleIds
#from _array import Matrix, Vector, where_eq, all_ne, cols_where_eq

__author__ = 'shattar'


class Solver(object):

    _NOT_CLAIMED = 0
    _MARKED = 1
    _CLAIMED = 2
    _IGNORED = 255

    LONGEST_UNRESOLVED_SEGMENT_SEQUENCE = 100

    def __init__(self, cycle_identifier_list):
        """
        Implements a pattern recognition algorithm to identify the hidden state from a sequence of observations.

        In more specific terms, this is used to identify what application a piece of equipment is being utilized in from
        a sequence of observed segments of machine activity.  The hidden state is the application, and the observations
        are the sequence of segments.

        This does not utilize HMM (Hidden Markov Model), however, it is used to solve the same type of problem.

        :param cycle_identifier_list: List of cycle identifier objects, in priority order where the first cycle type in
            the list is the highest priority cycle type.
        :type cycle_identifier_list: list of :class:`~app_cycle_id.cycle_identifier.CycleIdentifer`
        """
        self._cycle_identifier_list = cycle_identifier_list
        self._log_idx = 0
        self._obj_idx = 0
        self._backtrace = None
        self._starts = None
        self._dirty = None
        self._first_unresolved_segment_idx = 0

    def reinit(self, properties=None):
        """
        Reinitializes the solver such that it can be used again on another sequence of segments.

        :param properties: The machine properties.
        :type identifier: :class:`dict`
        """
        self._log_idx = 0
        self._obj_idx = 0
        self._backtrace = None
        self._starts = None
        self._dirty = None
        self._first_unresolved_segment_idx = 0
        for c in xrange(len(self._cycle_identifier_list)):
            self._cycle_identifier_list[c].reinit(properties=properties)

    def solve(self, segment_list):
        """
        Identifies the application cycles from a given sequence of segments.  Given an observed sequence of segments,
        what is the most likely sequence of application cycles that led to the observance of those segments?

        :param segment_list: The sequence of observed segments.
        :type segment_list: list of :class:`~app_cycle_id.segment.Segment`
        :param properties: The properties to use for the solver.
        :type properties: :class:`dict`
        :returns: *tuple*

            **cycle_ids** (list of :class:`int`) -- A list of cycle identifiers the same length as the segment_list

            **cycle_starts** (list of :class:`bool`) -- A list of booleans the same length as the segment_list,
            indicating whether or not the segment is the start of a cycle.
        """
        number_of_cycle_identifiers = len(self._cycle_identifier_list)
        number_of_segment_records = len(segment_list)

        # Initialize the backtrace
        self._backtrace = Matrix(rows=number_of_cycle_identifiers, cols=number_of_segment_records,
                                 initial_value=self._NOT_CLAIMED, dtype='uint8')

        # Initialize the cycle start flags
        self._starts = Matrix(rows=number_of_cycle_identifiers, cols=number_of_segment_records,
                              initial_value=False, dtype='bool')

        # Initialize the dirty vector
        self._dirty = set()

        # Allocate final cycle id vector
        cycle_id_indices = Vector(cols=number_of_segment_records, initial_value=-1, dtype='int32')
        cycle_ids = Vector(cols=number_of_segment_records, initial_value=CycleIds.NONE, dtype='int32')
        cycle_starts = Vector(cols=number_of_segment_records, initial_value=False, dtype='bool')

        self._first_unresolved_segment_idx = 0
        beginning_of_session_idx = 0

        for l in xrange(number_of_segment_records):
            self._log_idx = l
            # self._dirty[:] = False
            self._dirty.clear()

            # If the new segment is not contiguous with the previous segment, then the process needs to start fresh
            # from this segment, leaving what's left of the previous contiguous set of segments unresolved
            if l > 0:
                ### change code due to jython:pcf
                delta = float(segment_list[l].start_timestamp.getTime() - segment_list[l-1].start_timestamp.getTime()) / 1000.0
                duration = segment_list[l-1].duration
                if abs(delta - duration) > 5.0:  # 5 seconds to account for timestamps second resolution, and RTC jitter
                    for c in xrange(number_of_cycle_identifiers):
                        self._cycle_identifier_list[c].reinit()
                    reset_slice = slice(self._first_unresolved_segment_idx, l)
                    self._backtrace[:, reset_slice] = self._NOT_CLAIMED
                    self._starts[:, reset_slice] = False
                    cycle_id_indices[reset_slice] = -1
                    self._first_unresolved_segment_idx = l
                    beginning_of_session_idx = l

            # Call all of the individual cycle identifiers
            for c in xrange(number_of_cycle_identifiers):
                self._obj_idx = c
                self._cycle_identifier_list[c].update(self, segment_list[l])

            # If the first unresolved segment is too old...
            # then force all undecided cycle identifers to abandon and reinitialize.
            if (l - self._first_unresolved_segment_idx) + 1 >= self.LONGEST_UNRESOLVED_SEGMENT_SEQUENCE:
                temp = self._backtrace[:, self._first_unresolved_segment_idx]
                marked_cycle_indices = where_eq(temp, self._MARKED)
                for c in marked_cycle_indices:
                    self._obj_idx = c
                    self.abandon_marked_segments()
                    self._cycle_identifier_list[c].reinit()

            # For everything that has changed, see if it can be resolved.
            for dirty_idx in self._dirty:
                # Check to see if this segment is resolved, which means there aren't any more 'marked' slots.
                temp = self._backtrace[:, dirty_idx]

                if all_ne(temp, self._MARKED):

                    # This segment is resolved, find the owner, which is the highest priority claimer
                    c = where_eq(temp, self._CLAIMED)

                    if len(c) > 0:
                        c = c[0]  # The first, highest priority
                    else:
                        c = number_of_cycle_identifiers-1  # The last, lowest priority catch all
                        raise RuntimeError('Unclaimed Segment')

                    # Store the owner index and identifier
                    cycle_id_indices[dirty_idx] = c

                    # This resolved segment allows us to advance forward, identifying cycle starts along the way
                    if dirty_idx == self._first_unresolved_segment_idx:
                        # Loop from this newly resolved segment to the next unresolved segment
                        idx = self._first_unresolved_segment_idx
                        while True:
                            if idx >= number_of_segment_records:
                                # Everything is resolved
                                self._first_unresolved_segment_idx = number_of_segment_records
                                break
                            elif cycle_id_indices[idx] < 0:
                                # We have encountered an unresolved segment, leave off here
                                self._first_unresolved_segment_idx = idx
                                break
                            else:
                                cycle_ids[idx] = self._cycle_identifier_list[cycle_id_indices[idx]].identifier
                                if idx == beginning_of_session_idx:
                                    cycle_starts[idx] = True
                                elif self._starts[cycle_id_indices[idx], idx]:
                                    cycle_starts[idx] = True
                                else:
                                    # Go back until one of these things happen:
                                    # - Find a segment with the same cycle id, in which case, this is not a start
                                    # because an earlier segment must be the start.
                                    # OR
                                    # - Find a segment that is a different cycle id, but flagged to be ignored,
                                    # in which case, just continue searching backwards.
                                    # OR
                                    # - Find a segment that was a different cycle id, but not flagged to be ignored,
                                    # in which case, this must be the start of a new cycle
                                    for back_idx in xrange(idx-1, beginning_of_session_idx-1, -1):
                                        if cycle_id_indices[back_idx] == cycle_id_indices[idx]:
                                            # Not a start
                                            break
                                        elif self._backtrace[cycle_id_indices[idx], back_idx] == self._IGNORED:
                                            # Keep going, ignore this segment.  However, if this is the first segment,
                                            # and we still haven't figured it out yet, we have to call it a start
                                            if back_idx == 0:
                                                cycle_starts[idx] = True
                                        else:
                                            # This is different and not ignored
                                            cycle_starts[idx] = True
                                            break
                            idx += 1

        return cycle_ids, cycle_starts

    def claim_marked_segments(self):
        """
        Claims all marked segments for current cycle identifier object.
        """
        marked = cols_where_eq(self._backtrace, self._obj_idx, self._MARKED,
                               min_col_index=self._first_unresolved_segment_idx,
                               max_col_index=self._log_idx)
        self._backtrace[self._obj_idx, marked] = self._CLAIMED
        self._dirty.update(marked)

    def abandon_marked_segments(self):
        """
        Abandons all marked segments for the current cycle identifier object.
        """
        marked = cols_where_eq(self._backtrace, self._obj_idx, self._MARKED,
                               min_col_index=self._first_unresolved_segment_idx,
                               max_col_index=self._log_idx)
        self._backtrace[self._obj_idx, marked] = self._NOT_CLAIMED
        self._dirty.update(marked)

    def mark_segment(self, cycle_start=False):
        """
        Marks the current segment as potentially belonging to the current cycle identifier object.

        :param cycle_start: True if this segment is the start of a cycle, otherwise, False.  Default is False.
        :type cycle_start: :class:`bool`
        """
        self._backtrace[self._obj_idx, self._log_idx] = self._MARKED
        if cycle_start:
            self._starts[self._obj_idx, self._log_idx] = True

    def ignore_segment(self):
        """
        Ignores the current segment with respect to the current cycle identifier object.
        """
        self._backtrace[self._obj_idx, self._log_idx] = self._IGNORED
