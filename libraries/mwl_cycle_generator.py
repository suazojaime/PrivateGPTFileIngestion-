### change code due to jython:pcf
#from app_cycle_id import CycleGenerator, WaitingCycleIdentifier,\
#    KeyOnEngineOffCycleIdentifier, EngineShutdownCycleIdentifier, OtherCycleIdentifier
#from mwl_cycle import MwlCycle
#from loading_cycle_identifier import LoadingCycleIdentifier, LoadAndCarryCycleIdentifier, PileCleanupCycleIdentifier
#from roading_cycle_identifier import RoadingCycleIdentifier

__author__ = 'shattar'


class MwlCycleGenerator(CycleGenerator):

    def __init__(self):
        """
        Medium Wheel Loader (MWL) cycle generator.

        This is the MWL specific implementation of cycle generator.
        It generates :class:`~app_cycle_id.mwl.mwl_cycle.MwlCycle` type cycle records using the following cycle
        identifiers:

            #. :class:`~app_cycle_id.mwl.loading_cycle_identifier.LoadAndCarryCycleIdentifier`
            #. :class:`~app_cycle_id.mwl.loading_cycle_identifier.LoadingCycleIdentifier`
            #. :class:`~app_cycle_id.mwl.loading_cycle_identifier.PileCleanupCycleIdentifier`
            #. :class:`~app_cycle_id.mwl.tramming_cycle_identifier.RoadingCycleIdentifier`
            #. :class:`~app_cycle_id.cycle_identifier.WaitingCycleIdentifier`
            #. :class:`~app_cycle_id.cycle_identifier.KeyOnEngineOffCycleIdentifier`
            #. :class:`~app_cycle_id.cycle_identifier.EngineShutdownCycleIdentifier`
            #. :class:`~app_cycle_id.cycle_identifier.OtherCycleIdentifier`
        """
        cycle_identifier_list = [
            LoadAndCarryCycleIdentifier(),
            LoadingCycleIdentifier(),
            PileCleanupCycleIdentifier(),
            RoadingCycleIdentifier(),
            WaitingCycleIdentifier(),
            KeyOnEngineOffCycleIdentifier(),
            EngineShutdownCycleIdentifier(),
            OtherCycleIdentifier()
        ]
        CycleGenerator.__init__(self, cycle_identifier_list, cycle_class=MwlCycle)
