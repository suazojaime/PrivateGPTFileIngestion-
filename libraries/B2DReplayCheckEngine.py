import Tkinter as tk
import xml.etree.ElementTree as ET
import copy
import datetime as dt
import time
import sys
import argparse

class NonWeightedValue:
    def __init__(self,
                 name,
                 oid,
                 magnitude,
                 unit,
                 unit_type,
                 lower_limit,
                 upper_limit,
                 used,
                 relevant_to_db):
        self.name = name
        self.oid = oid
        self.value = UnitTypeMagnitude(magnitude, unit, unit_type)
        self.relevantToDb = relevant_to_db
        self.used = used
        self.lowerLimit = lower_limit
        self.upperLimit = upper_limit

    def reset_values(self):
        self.value.reset_magnitude()
        self.used = False

    def set_is_used(self):
        self.used = True


class WeightedValue:
    ZERO_VALUE = 0.0

    def __init__(self,
                 name,
                 oid,
                 magnitude,
                 unit,
                 unit_type,
                 weight_magnitude,
                 lower_limit,
                 upper_limit,
                 used,
                 relevant_to_db):
        self.name = name
        self.oid = oid
        self.value = UnitTypeMagnitude(magnitude, unit, unit_type)
        self.weightMagnitude = weight_magnitude
        self.lowerLimit = lower_limit
        self.upperLimit = upper_limit
        self.relevantToDb = relevant_to_db
        self.used = used
        self.weightValueMagnitude = magnitude * weight_magnitude

    def reset_values(self):
        self.value.reset_magnitude()
        self.weightMagnitude = self.ZERO_VALUE
        self.weightValueMagnitude = self.value.magnitude * self.weightMagnitude
        self.used = False

    def set_is_used(self):
        self.used = True


class CompositeWeightedValue:
    def __init__(self,
                 parent,
                 children):

        self.parent = NonWeightedValue(parent.name,
                                       parent.oid,
                                       parent.value.magnitude,
                                       parent.value.unit,
                                       parent.value.unitType,
                                       parent.lowerLimit,
                                       parent.upperLimit,
                                       parent.used,
                                       parent.relevantToDb)

        self.children = {}
        for child_key, child_value in children.iteritems():
            self.children[child_key] = WeightedValue(children[child_key].name,
                                                     children[child_key].oid,
                                                     children[child_key].value.magnitude,
                                                     children[child_key].value.unit,
                                                     children[child_key].value.unitType,
                                                     children[child_key].weightMagnitude,
                                                     children[child_key].lowerLimit,
                                                     children[child_key].upperLimit,
                                                     children[child_key].used,
                                                     children[child_key].relevantToDb)

    def reset_values(self):
        self.parent.reset_values()

        for child_key, child_value in self.children.iteritems():
            self.children[child_key].reset_values()


class UnitTypeMagnitude:
    LOG_UNIT = 'unit'
    LOG_UNIT_TYPE = 'unitType'
    LOG_MAGNITUDE = 'magnitude'
    ZERO_VALUE = 0.0

    def __init__(self,
                 magnitude,
                 unit,
                 unit_type):
        self.magnitude = magnitude
        self.unit = unit
        self.unitType = unit_type

    @classmethod
    def fromXML(cls,
                unit_type_magnitude_XML):
        magnitude_text = unit_type_magnitude_XML.get(UnitTypeMagnitude.LOG_MAGNITUDE)

        try:
            magnitude = int(magnitude_text)
        except ValueError:
            try:
                magnitude = float(magnitude_text)
            except ValueError:
                raise ValueError('The magnitude value in the XML is the string ' +
                                 magnitude_text +
                                 ' and this cannot converted to a float or int.')

        unit = unit_type_magnitude_XML.get(UnitTypeMagnitude.LOG_UNIT)
        unit_type = unit_type_magnitude_XML.get(UnitTypeMagnitude.LOG_UNIT_TYPE)

        if unit_type == ControlRecord.UNIT_TYPE_DURATION and \
           unit == ControlRecord.UNIT_DURATION:
            return cls(dt.timedelta(seconds=magnitude),
                       unit,
                       unit_type)
        else:
            return cls(magnitude,
                       unit,
                       unit_type)

    def reset_magnitude(self):
        self.magnitude = self.ZERO_VALUE

    def compare_unit(self,
                     comparison,
                     used):

        if self.unit != comparison.unit:
            if used:
                raise ValueError('Mismatch in units ' +
                                 self.unit +
                                 ' and ' +
                                 comparison.unit)
            else:
                comparison.unit = self.unit

        if self.unitType != comparison.unitType:
            raise ValueError('Mismatch in units ' +
                             self.unitType +
                             ' and ' +
                             comparison.unitType)


class ControlRecord:
    BATCH_MASS = 'BATCH_MASS'
    ROLLING_MASS = 'ROLLING_MASS'
    BATCH_WINDOW = 'BATCH_WINDOW'
    ROLLING_WINDOW = 'ROLLING_WINDOW'
    UNIT_DURATION = 'second'
    UNIT_MASS = 'kilogram'
    UNIT_TYPE_MASS = 'mass'
    UNIT_TYPE_DURATION = 'duration'

    def __init__(self,
                 control_method,
                 control_window,
                 control_mass):
        self.method = control_method
        self.window = control_window
        self.mass = control_mass

        if self.method not in [self.BATCH_MASS,
                               self.BATCH_WINDOW,
                               self.ROLLING_MASS,
                               self.ROLLING_WINDOW]:
            raise ValueError('Control type ' +
                             self.method +
                             ' is invalid')

        if self.window is None and self.mass is None:
            raise ValueError('Control has neither a control window nor control mass')

        if self.window is not None:
            if self.window.unit != self.UNIT_DURATION:
                raise ValueError('Control window unit is not ' +
                                 self.UNIT_DURATION +
                                 ', instead ' +
                                 self.window.unit)
            if self.window.unitType != self.UNIT_TYPE_DURATION:
                raise ValueError('Control window unit type is not ' +
                                 self.UNIT_TYPE_DURATION +
                                 ', instead ' +
                                 self.window.unitType)

        if self.mass is not None:
            if self.mass.unit != self.UNIT_MASS:
                raise ValueError('Control window unit is not ' +
                                 self.UNIT_MASS +
                                 ', instead ' +
                                 self.mass.unit)
            if self.mass.unitType != self.UNIT_TYPE_MASS:
                raise ValueError('Control window unit type is not ' +
                                 self.UNIT_TYPE_MASS +
                                 ', instead ' +
                                 self.mass.unitType)


class DestinationBlendCycleInternal:
    LOG_ACTIVE_BLEND = 'activeBlend'
    LOG_ACTIVE_DESTINATION_BLEND = 'activeDestinationBlend'
    LOG_BLEND_OID = 'blendOID'
    LOG_DESTINATION_BLEND_OID = 'oid'
    CYCLE_CYCLE_OID = 'cycleOID'
    CYCLE_END_TIME = 'endTime'
    CYCLE_START_TIME = 'startTime'
    CYCLE_PROCESSOR = 'processor'
    CYCLE_PROCESSOR_OID = 'oid'
    CYCLE_CONTINUOUS_GRADE_PAYLOAD_DTO = 'continuousGradePayloadDTOs'
    CYCLE_CONTINUOUS_GRADE_VALUE = 'gradeValue'
    CYCLE_CONTINUOUS_GRADE_NAME = 'name'
    CYCLE_CONTINUOUS_GRADE_OID = 'oid'
    CYCLE_CONTINUOUS_GRADE_WEIGHTING_QUANTITY = 'weightingQuantity'
    CYCLE_CONTINUOUS_GRADE_GRADE_QUANTITY = 'gradeQuantity'
    CYCLE_MATERIALS_PAYLOAD_DTO = 'materialsPayloadDTO'
    CYCLE_MATERIALS_VALUE = 'gradeValue'
    CYCLE_MATERIALS_NAME = 'name'
    CYCLE_MATERIALS_OID = 'oid'
    CYCLE_MATERIALS_WEIGHTING_QUANTITY = 'weightingQuantity'
    CYCLE_MATERIALS_GRADE_QUANTITY = 'gradeQuantity'
    CYCLE_DISCRETE_GRADE_PAYLOAD_DTO = 'discreteGradePayloadDTOs'
    CYCLE_DISCRETE_GRADE_VALUE = 'gradeValue'
    CYCLE_DISCRETE_GRADE_NAME = 'name'
    CYCLE_DISCRETE_GRADE_OID = 'oid'
    CYCLE_DISCRETE_GRADE_WEIGHTING_QUANTITY = 'weightingQuantity'
    CYCLE_DISCRETE_GRADE_GRADE_QUANTITY = 'gradeQuantity'
    CYCLE_DISCRETE_GRADE_VALUE_NAME = 'value'
    CYCLE_DISCRETE_GRADE = 'weightedDiscreteGradeReference'
    CYCLE_CALCULATION_TIME = 'calculationTime'
    ZERO_VALUE = 0.0
    CYCLE_MASS = 'mass'
    CYCLE_UUID = 'uuid'
    CYCLE_PROCESSOR_NAME = 'name'
    CYCLE_MACHINE = 'primaryMachine'
    CYCLE_MACHINE_OID = 'oid'
    CYCLE_MACHINE_NAME = 'name'
    CYCLE_IS_LHD = 'lhd'
    CYCLE_MATERIAL_COLOUR = 'materialColour'
    CYCLE_MATERIAL_NAME = 'materialName'
    CYCLE_SOURCE_BLOCK = 'sourceBlock'
    CYCLE_SOURCE_DESTINATION = 'sourceDestination'
    CYCLE_ASSIGNED_DESTINATION = 'assignedDestination'
    CYCLE_SINK_DESTINATION = 'sinkDestination'

    def __init__(self,
                 db_cycle_XML,
                 cycle_calculation_time):

        db_cyc = copy.deepcopy(db_cycle_XML)

        active_blend_root = db_cyc.find(".//" +
                                        self.LOG_ACTIVE_BLEND +
                                        "/..")

        active_blend_root.remove(active_blend_root.find(".//" +
                                                        self.LOG_ACTIVE_BLEND))

        self.blendOid = db_cyc.find(".//" +
                                    self.LOG_BLEND_OID).text

        active_destination_blend_root = db_cyc.find(".//" +
                                                    self.LOG_ACTIVE_DESTINATION_BLEND +
                                                    "/..")

        self.dbOid = active_destination_blend_root.find(".//" +
                                                        self.LOG_DESTINATION_BLEND_OID).text

        active_destination_blend_root.remove(active_destination_blend_root.find(".//" +
                                                                                self.LOG_ACTIVE_DESTINATION_BLEND))

        self.oid = db_cyc.find(".//" +
                               self.CYCLE_CYCLE_OID).text

        self.processorOid = db_cyc.find(".//" +
                                        self.CYCLE_PROCESSOR).find(self.CYCLE_PROCESSOR_OID).text

        self.processorName = db_cyc.find(".//" +
                                         self.CYCLE_PROCESSOR).find(self.CYCLE_PROCESSOR_NAME).text

        self.machineOid = db_cyc.find(".//" +
                                      self.CYCLE_MACHINE).find(self.CYCLE_MACHINE_OID).text

        self.machineName = db_cyc.find(".//" +
                                       self.CYCLE_MACHINE).find(self.CYCLE_MACHINE_NAME).text

        self.isLHD = db_cyc.find(".//" +
                                 self.CYCLE_IS_LHD).text

        self.materialColour = db_cyc.find(".//" +
                                          self.CYCLE_MATERIAL_COLOUR).text

        self.materialName = db_cyc.find(".//" +
                                        self.CYCLE_MATERIAL_NAME).text

        self.uuid = db_cyc.find(".//" +
                                self.CYCLE_UUID).text

        self.sourceBlock = db_cyc.find(".//" +
                                       self.CYCLE_SOURCE_BLOCK).text

        self.sourceDestination = db_cyc.find(".//" +
                                             self.CYCLE_SOURCE_DESTINATION).text

        self.assignedDestination = db_cyc.find(".//" +
                                               self.CYCLE_ASSIGNED_DESTINATION).text

        self.sinkDestination = db_cyc.find(".//" +
                                           self.CYCLE_SINK_DESTINATION).text

        self.cycleCalculationTime = cycle_calculation_time

        self.mass = UnitTypeMagnitude.fromXML(db_cyc.find(".//" +
                                                          self.CYCLE_MASS))

        self.cycleStartTimeProrata = dt.datetime.min
        self.cycleDurationProrata = dt.timedelta(seconds=0)
        self.shiftRelevant = False
        self.shiftPercentage = 0.0
        self.controlPercentage = 0.0
        self.controlRelevant = False
        self.controlAlternativeProrataPercentage = 0.0
        self.controlRateProrataPercentage = 0.0

        self.cycleEndTime = MineStarToInternal.to_datetime_from_timestamp_text(
            db_cyc.find(".//" +
                        self.CYCLE_END_TIME).text)
        self.cycleStartTime = MineStarToInternal.to_datetime_from_timestamp_text(
            db_cyc.find(".//" +
                        self.CYCLE_START_TIME).text)
        self.cycleDuration = self.cycleEndTime - self.cycleStartTime

        # Continuous Grades
        self.continuousGrades = {}

        for cg in db_cyc.findall(".//" +
                                 self.CYCLE_CONTINUOUS_GRADE_PAYLOAD_DTO):
            cg_grade_value = UnitTypeMagnitude.fromXML(cg.find(".//" +
                                                               self.CYCLE_CONTINUOUS_GRADE_VALUE))
            cg_weighted = WeightedValue(cg.find(".//" +
                                                self.CYCLE_CONTINUOUS_GRADE_NAME).text,
                                        cg.find(".//" +
                                                self.CYCLE_CONTINUOUS_GRADE_OID).text,
                                        cg_grade_value.magnitude,
                                        cg_grade_value.unit,
                                        cg_grade_value.unitType,
                                        self.mass.magnitude,
                                        self.ZERO_VALUE,
                                        self.ZERO_VALUE,
                                        True,
                                        True)

            if not ValueComparison.standard(cg.find(".//" +
                                                    self.CYCLE_CONTINUOUS_GRADE_WEIGHTING_QUANTITY).text,
                                            self.mass.magnitude):
                raise ValueError('Continuous grade weighting quantity in XML ' +
                                 cg.find(".//" +
                                         self.CYCLE_CONTINUOUS_GRADE_WEIGHTING_QUANTITY).text +
                                 ' does not equal mass in XML ' +
                                 self.mass.magnitude)

            if not ValueComparison.standard(cg.find(".//" +
                                                    self.CYCLE_CONTINUOUS_GRADE_GRADE_QUANTITY).text,
                                            cg_weighted.weightValueMagnitude):
                raise ValueError('Continuous grade grade quantity in XML ' +
                                 cg.find(".//" +
                                         self.CYCLE_CONTINUOUS_GRADE_GRADE_QUANTITY).text +
                                 ' does not equal grade value multiplied by mass in XML ' +
                                 str(cg_weighted.weightValueMagnitude) +
                                 ' derived from mass ' +
                                 str(self.mass.magnitude) +
                                 ' and grade value ' +
                                 str(cg_weighted.value.magnitude))

            self.continuousGrades[cg_weighted.oid] = cg_weighted

        # materials
        self.materials = {}

        for mat in db_cyc.findall(".//" +
                                  self.CYCLE_MATERIALS_PAYLOAD_DTO):
            if mat.find(".//" +
                        self.CYCLE_MATERIALS_VALUE) is not None:

                mat_grade_value = UnitTypeMagnitude.fromXML(mat.find(".//" +
                                                                     self.CYCLE_MATERIALS_VALUE))
                mat_weighted = WeightedValue(mat.find(".//" +
                                                      self.CYCLE_MATERIALS_NAME).text,
                                             mat.find(".//" +
                                                      self.CYCLE_MATERIALS_OID).text,
                                             mat_grade_value.magnitude,
                                             mat_grade_value.unit,
                                             mat_grade_value.unitType,
                                             self.mass.magnitude,
                                             self.ZERO_VALUE,
                                             self.ZERO_VALUE,
                                             True,
                                             True)

                if not ValueComparison.standard(mat.find(".//" +
                                                         self.CYCLE_MATERIALS_WEIGHTING_QUANTITY).text,
                                                self.mass.magnitude):
                    raise ValueError('Material weighting quantity in XML ' +
                                     mat.find(".//" +
                                              self.CYCLE_MATERIALS_WEIGHTING_QUANTITY).text +
                                     ' does not equal mass in XML ' +
                                     str(self.mass.magnitude))

                if not ValueComparison.standard(mat.find(".//" +
                                                         self.CYCLE_MATERIALS_GRADE_QUANTITY).text,
                                                mat_weighted.weightValueMagnitude):
                    raise ValueError('Material grade quantity in XML ' +
                                     mat.find(".//" +
                                              self.CYCLE_MATERIALS_GRADE_QUANTITY).text +
                                     ' does not equal grade value multiplied by mass in XML ' +
                                     str(mat_weighted.weightValueMagnitude) +
                                     ' derived from mass ' +
                                     str(self.mass.magnitude) +
                                     ' and grade value ' +
                                     str(mat_weighted.value.magnitude))

                self.materials[mat_weighted.oid] = mat_weighted

        # discrete grades
        self.discreteGrades = {}

        for dg in db_cyc.findall(".//" +
                                 self.CYCLE_DISCRETE_GRADE_PAYLOAD_DTO):

            dg_weighted = {}

            dg_grade_value = UnitTypeMagnitude.fromXML(dg.find(".//" +
                                                               self.CYCLE_DISCRETE_GRADE_VALUE))
            dg_weighted_key = dg.find(".//" +
                                      self.CYCLE_DISCRETE_GRADE_VALUE_NAME).text

            dg_weighted[dg_weighted_key] = WeightedValue(dg_weighted_key,
                                                         'No Oid Yet',
                                                         dg_grade_value.magnitude,
                                                         dg_grade_value.unit,
                                                         dg_grade_value.unitType,
                                                         self.mass.magnitude,
                                                         self.ZERO_VALUE,
                                                         self.ZERO_VALUE,
                                                         True,
                                                         True)

            dg_non_weighted = NonWeightedValue(dg.find('./' +
                                                       self.CYCLE_DISCRETE_GRADE +
                                                       '/' +
                                                       self.CYCLE_DISCRETE_GRADE_NAME).text,
                                               dg.find('./' +
                                                       self.CYCLE_DISCRETE_GRADE +
                                                       '/' +
                                                       self.CYCLE_DISCRETE_GRADE_OID).text,
                                               dg_grade_value.magnitude,
                                               dg_grade_value.unit,
                                               dg_grade_value.unitType,
                                               self.ZERO_VALUE,
                                               self.ZERO_VALUE,
                                               True,
                                               True)

            if not ValueComparison.standard(dg.find(".//" +
                                                    self.CYCLE_DISCRETE_GRADE_WEIGHTING_QUANTITY).text,
                                            self.mass.magnitude):
                raise ValueError('Discrete grade weighting quantity in XML ' +
                                 dg.find(".//" +
                                         self.CYCLE_DISCRETE_GRADE_WEIGHTING_QUANTITY).text +
                                 ' does not equal mass in XML ' +
                                 str(self.mass.magnitude))

            if not ValueComparison.standard(dg.find(".//" +
                                                    self.CYCLE_DISCRETE_GRADE_GRADE_QUANTITY).text,
                                            dg_weighted[dg_weighted_key].weightValueMagnitude):
                raise ValueError('Discrete grade grade quantity in XML ' +
                                 dg.find(".//" +
                                         self.CYCLE_DISCRETE_GRADE_GRADE_QUANTITY).text +
                                 ' does not equal grade value multiplied by mass in XML ' +
                                 str(dg_weighted[dg_weighted_key].weightValueMagnitude) +
                                 ' derived from mass ' +
                                 str(self.mass.magnitude) +
                                 ' and grade value ' +
                                 str(dg_weighted[dg_weighted_key].value.magnitude))

            self.discreteGrades[dg_non_weighted.oid +
                                '|' +
                                dg_weighted[dg_weighted_key].name] = CompositeWeightedValue(dg_non_weighted,
                                                                                            dg_weighted)


class ValueComparison:
    def __init__(self):
        pass

    @staticmethod
    def percentage_based(value_one,
                         value_two,
                         comparison_percent):

        if isinstance(value_one, basestring):
            number_one = float(value_one)
        elif isinstance(value_one, dt.timedelta):
            number_one = value_one.total_seconds()
        else:
            number_one = value_one

        if isinstance(value_two, basestring):
            number_two = float(value_two)
        elif isinstance(value_two, dt.timedelta):
            number_two = value_two.total_seconds()
        else:
            number_two = value_two

        if abs(number_two) > 0:
            return abs((number_one - number_two) / number_two) < (comparison_percent / 1e2)
        else:
            return number_one == number_two

    @classmethod
    def standard(cls,
                 value_one,
                 value_two):

        comparison_percent = 0.001

        return cls.percentage_based(value_one,
                                    value_two,
                                    comparison_percent)


class DestinationBlendCacheInternal:
    maxWindow = dt.timedelta(hours=8)
    PERCENT_MAX = 1e2
    PERCENT_ZERO = 0.0
    BLEND_TOTAL = 'Blend Total'

    def __init__(self,
                 name,
                 db_oid,
                 db_control):
        self.name = name
        self.dbCycles = []
        self.control = db_control
        self.controlCumulative = copy.deepcopy(db_control)
        self.controlCumulative.mass.magnitude = 0.0
        self.controlCumulative.window.magnitude = dt.timedelta(seconds=0)
        self.controlLastCycleIndex = 0
        self.shiftLastCycleIndex = 0
        self.dbOid = db_oid
        self.cacheBatchStartTime = dt.datetime.max

    def add_cycle_no_delta(self,
                           db_cycle_XML,
                           db_state,
                           is_update,
                           cycle_update_time):

        db_cycle = DestinationBlendCycleInternal(db_cycle_XML,
                                                 cycle_update_time)

        if self.control.method == ControlRecord.BATCH_MASS:
            if self.cacheBatchStartTime < dt.datetime.max:
                if self.cacheBatchStartTime + self.maxWindow < cycle_update_time:
                    self.set_cache_batch_start_time(cycle_update_time - self.maxWindow)

        prorata_end_time = db_cycle.cycleCalculationTime

        if not db_state.blendOid == db_cycle.blendOid:
            raise ValueError('The blend OID for the cycle ' +
                             db_cycle.oid +
                             ' is ' +
                             db_cycle.blendOid +
                             ' and does not match the blend OID ' +
                             db_state.blendOid +
                             '\n' +
                             ' associated with the destination blend ' +
                             db_state.destinationBlendOID +
                             ' (the destination blend for the cycle is ' +
                             db_cycle.dbOid +
                             ')')

        db_cycle.mass.compare_unit(self.control.mass,
                                   db_state.currentMasses[self.BLEND_TOTAL].used)

        db_cycle.controlPercentage = self.PERCENT_ZERO
        db_cycle.controlRelevant = False
        db_cycle.shiftPercentage = self.PERCENT_ZERO
        db_cycle.shiftRelevant = False
        db_cycle.controlAlternativeProrataPercentage = self.PERCENT_ZERO
        db_cycle.controlRateProrataPercentage = self.PERCENT_ZERO

        if db_cycle.oid in self.dbCycles:
            raise ValueError('A blend cycle ' +
                             db_cycle.oid +
                             ' is being added to the cache ' +
                             self.dbOid +
                             ' and it already exists. This should have already been removed.')

        else:
            if self.dbCycles:
                if self.dbCycles[0].cycleEndTime > db_cycle.cycleEndTime:
                    self.dbCycles[0].cycleStartTimeProrata = \
                        db_cycle.cycleEndTime
                    self.dbCycles[0].cycleDurationProrata = \
                        self.dbCycles[0].cycleEndTime - \
                        self.dbCycles[0].cycleStartTimeProrata

                    db_cycle.cycleStartTimeProrata = db_state.controlStartTime
                    db_cycle.cycleDurationProrata = db_cycle.cycleEndTime - \
                                                    db_cycle.cycleStartTimeProrata

                    self.dbCycles.insert(0, db_cycle)

                    if 0 < self.shiftLastCycleIndex:
                        self.shiftLastCycleIndex += 1

                    if 0 < self.controlLastCycleIndex:
                        self.controlLastCycleIndex += 1
                else:
                    for index in range(len(self.dbCycles) - 1, -1, -1):
                        if self.dbCycles[index].cycleEndTime < db_cycle.cycleEndTime:
                            if index < len(self.dbCycles) - 1:
                                # adjust cycle that occurred after this new one
                                self.dbCycles[index + 1].cycleStartTimeProrata = \
                                    db_cycle.cycleEndTime
                                self.dbCycles[index + 1].cycleDurationProrata = \
                                    self.dbCycles[index + 1].cycleEndTime - \
                                    self.dbCycles[index + 1].cycleStartTimeProrata

                            db_cycle.cycleStartTimeProrata = self.dbCycles[index].cycleEndTime

                            db_cycle.cycleDurationProrata = \
                                db_cycle.cycleEndTime - \
                                db_cycle.cycleStartTimeProrata

                            self.dbCycles.insert(index + 1, db_cycle)

                            break

            else:
                db_cycle.cycleStartTimeProrata = db_state.controlStartTime
                db_cycle.cycleDurationProrata = db_cycle.cycleEndTime - \
                                                db_cycle.cycleStartTimeProrata

                self.dbCycles.append(db_cycle)

            # check to see if the
            db_state.shift_values_reset()

            self.controlCumulative.mass.magnitude = 0.0
            if (prorata_end_time - self.dbCycles[len(self.dbCycles) - 1].cycleEndTime).total_seconds() > \
               self.maxWindow.total_seconds():
                self.controlCumulative.window.magnitude = dt.timedelta(seconds=self.maxWindow.total_seconds())
            else:
                self.controlCumulative.window.magnitude = \
                   dt.timedelta(seconds=(prorata_end_time -
                                         self.dbCycles[len(self.dbCycles) - 1].cycleEndTime).total_seconds())

            for index in range(self.shiftLastCycleIndex, len(self.dbCycles), 1):
                if index == self.shiftLastCycleIndex:
                    # if index == 0:
                    if len(self.dbCycles) == 1:
                        self.dbCycles[index].shiftRelevant = True
                        if self.dbCycles[index].cycleStartTimeProrata >= db_state.shiftStartTime:
                            self.dbCycles[index].shiftPercentage = self.PERCENT_MAX
                        else:
                            if self.dbCycles[index].cycleEndTime <= db_state.shiftStartTime:
                                self.dbCycles[index].shiftPercentage = self.PERCENT_ZERO
                                self.dbCycles[index].shiftRelevant = False
                            else:
                                self.dbCycles[index].shiftPercentage = \
                                (self.dbCycles[index].cycleEndTime -
                                 db_state.shiftStartTime).total_seconds() / \
                                self.dbCycles[index].cycleDurationProrata.total_seconds() * \
                                self.PERCENT_MAX
                    elif self.dbCycles[index].cycleEndTime <= db_state.shiftStartTime:
                        self.dbCycles[index].shiftPercentage = self.PERCENT_ZERO
                        self.dbCycles[index].shiftRelevant = False
                    elif self.dbCycles[index].cycleStartTimeProrata < db_state.shiftStartTime < \
                            self.dbCycles[index].cycleEndTime:
                        self.dbCycles[index].shiftPercentage = \
                            (self.dbCycles[index].cycleEndTime -
                             db_state.shiftStartTime).total_seconds() / \
                            self.dbCycles[index].cycleDurationProrata.total_seconds() * \
                            self.PERCENT_MAX
                        self.dbCycles[index].shiftRelevant = True
                    elif self.dbCycles[index].cycleStartTimeProrata >= db_state.shiftStartTime:
                        self.dbCycles[index].shiftPercentage = self.PERCENT_MAX
                        self.dbCycles[index].shiftRelevant = True
                    else:
                        raise ValueError('First cycle in destination blend ' +
                                         self.dbOid +
                                         ' after shift change is doing something weird')
                else:
                    self.dbCycles[index].shiftPercentage = self.PERCENT_MAX
                    self.dbCycles[index].shiftRelevant = True

            db_state.control_values_reset()

            # special case for once off cache processing for first cache cycle
            if self.control.method == ControlRecord.BATCH_MASS or \
               self.control.method == ControlRecord.BATCH_WINDOW:

                if prorata_end_time > self.cacheBatchStartTime:
                    self.controlLastCycleIndex = len(self.dbCycles) - 1
                    db_state.control_set(self.cacheBatchStartTime,
                                         prorata_end_time,
                                         cycle_update_time)
                    self.controlCumulative.window.magnitude = \
                        dt.timedelta(seconds=(prorata_end_time -
                                              max(self.dbCycles[len(self.dbCycles) - 1].cycleEndTime,
                                                  self.cacheBatchStartTime)).total_seconds())
                    self.cacheBatchStartTime = dt.datetime.max

            # window_lower_time = max(prorata_end_time - self.maxWindow, db_state.controlStartTime)
            window_lower_time = max(prorata_end_time - self.maxWindow,
                                    self.dbCycles[self.controlLastCycleIndex].cycleStartTimeProrata)

            if self.control.method == ControlRecord.BATCH_MASS or \
               self.control.method == ControlRecord.ROLLING_MASS:
                if window_lower_time > db_state.controlStartTime:
                    pass

            elif self.control.method == ControlRecord.BATCH_WINDOW:
                window_batch_start = db_state.controlStartTime
                while window_batch_start < (prorata_end_time -
                                            db_state.control.window.magnitude):
                    window_batch_start += db_state.control.window.magnitude
                if window_batch_start >= window_lower_time:
                    window_lower_time = window_batch_start
                    db_state.control_set(window_batch_start,
                                         prorata_end_time,
                                         cycle_update_time)
                    self.controlCumulative.window.magnitude = \
                        dt.timedelta(seconds=(prorata_end_time -
                                              max(self.dbCycles[len(self.dbCycles) - 1].cycleEndTime,
                                                  window_batch_start)).total_seconds())
                else:
                    raise ValueError('The batch window control start ' +
                                     str(window_batch_start) +
                                     'is before the maximum window horizon ' +
                                     str(window_lower_time))
            elif self.control.method == ControlRecord.ROLLING_WINDOW:
                window_rolling_start = prorata_end_time - \
                                        db_state.control.window.magnitude
                if window_rolling_start >= window_lower_time:
                    window_lower_time = window_rolling_start
                    db_state.control_set(window_rolling_start,
                                         prorata_end_time,
                                         cycle_update_time)
            else:
                raise ValueError('Control method ' +
                                 self.control.method +
                                 ' is unrecognised.')

            if self.control.method == ControlRecord.BATCH_MASS or \
                self.control.method == ControlRecord.BATCH_WINDOW:

                for index in range(self.controlLastCycleIndex, len(self.dbCycles), 1):
                    if self.dbCycles[index].cycleEndTime <= window_lower_time:
                        self.dbCycles[index].controlPercentage = self.PERCENT_ZERO
                        self.dbCycles[index].controlRelevant = False
                        self.dbCycles[index].controlRateProrataPercentage = self.PERCENT_ZERO
                        self.dbCycles[index].controlAlternativeProrataPercentage = self.PERCENT_ZERO
                    else:
                        if self.dbCycles[index].cycleStartTimeProrata < window_lower_time < \
                                self.dbCycles[index].cycleEndTime:
                            self.dbCycles[index].controlPercentage = \
                                (self.dbCycles[index].cycleEndTime -
                                  window_lower_time).total_seconds() / \
                                self.dbCycles[index].cycleDurationProrata.total_seconds() * \
                                self.PERCENT_MAX
                            self.dbCycles[index].controlRelevant = True
                        else:
                            self.dbCycles[index].controlPercentage = self.PERCENT_MAX
                            self.dbCycles[index].controlRelevant = True

                        self.controlCumulative.window.magnitude += \
                            dt.timedelta(seconds=(self.dbCycles[index].cycleDurationProrata.total_seconds() *
                                         self.dbCycles[index].controlPercentage /
                                         self.PERCENT_MAX))
                        self.controlCumulative.mass.magnitude += self.dbCycles[index].mass.magnitude * \
                                                                 self.dbCycles[index].controlPercentage / \
                                                                 self.PERCENT_MAX

                        if self.control_cache_exceeded(db_state.control,
                                                       self.controlCumulative.mass,
                                                       self.controlCumulative.window,
                                                       self.dbCycles[index].cycleEndTime,
                                                       db_state.controlEndTime):

                            # remove all of the records apart from the last one
                            for control_clean_index in range(self.controlLastCycleIndex, index, 1):
                                self.dbCycles[control_clean_index].controlPercentage = self.PERCENT_ZERO
                                self.dbCycles[control_clean_index].controlRelevant = False
                                self.dbCycles[index].controlRateProrataPercentage = self.PERCENT_ZERO
                                self.dbCycles[index].controlAlternativeProrataPercentage = self.PERCENT_ZERO

                            self.controlLastCycleIndex = index

                            if self.control.method == ControlRecord.BATCH_WINDOW:

                                control_end_time = db_state.controlStartTime + \
                                                   db_state.control.window.magnitude

                                while control_end_time < (self.dbCycles[index].cycleEndTime -
                                                          db_state.control.window.magnitude):
                                    control_end_time += db_state.control.window.magnitude

                                self.controlCumulative.window.magnitude = 0

                                self.dbCycles[index].controlPercentage = \
                                    (self.dbCycles[index].cycleEndTime -
                                     control_end_time).total_seconds() / \
                                    self.dbCycles[index].cycleDurationProrata.total_seconds() * \
                                    self.PERCENT_MAX
                                self.dbCycles[index].controlRelevant = True

                                self.controlCumulative.mass.magnitude = self.dbCycles[index].mass.magnitude * \
                                                                        self.dbCycles[index].controlPercentage / \
                                                                        self.PERCENT_MAX

                                self.controlCumulative.window.magnitude = \
                                    dt.timedelta(seconds=self.dbCycles[index].cycleDurationProrata.total_seconds() *
                                                 self.dbCycles[index].controlPercentage /
                                                 self.PERCENT_MAX)
                                # this may be unnecessary
                                self.controlCumulative.window.magnitude += \
                                    dt.timedelta(seconds=(prorata_end_time -
                                                          self.dbCycles[
                                                              len(self.dbCycles) - 1].cycleEndTime).total_seconds())

                                db_state.control_set(control_end_time,
                                                     prorata_end_time,
                                                     cycle_update_time)

                            else:

                                self.controlCumulative.mass.magnitude = self.dbCycles[index].mass.magnitude
                                self.controlCumulative.window.magnitude = self.dbCycles[index].cycleDurationProrata
                                self.controlCumulative.window.magnitude += \
                                    dt.timedelta(seconds=(prorata_end_time -
                                                          self.dbCycles[
                                                              len(self.dbCycles) - 1].cycleEndTime).total_seconds())

                                db_state.control_set(self.dbCycles[index].cycleStartTimeProrata,
                                                     prorata_end_time,
                                                     cycle_update_time)

                rate_prorata_percentage_total = 0.0

                # DELETE ONCE WORKING
                # for index in range(min(self.shiftLastCycleIndex, self.controlLastCycleIndex), len(self.dbCycles), 1):
                #     if db_state.controlDuration.total_seconds() > 0.0:
                #         rate_prorata_percentage_total += \
                #             (self.dbCycles[index].cycleEndTime -
                #              db_state.controlStartTime).total_seconds() / \
                #             db_state.controlDuration.total_seconds()

                for index in range(min(self.shiftLastCycleIndex, self.controlLastCycleIndex), len(self.dbCycles), 1):
                    # striping is not used in batch control, so set to control percentage
                    self.dbCycles[index].controlAlternativeProrataPercentage = \
                        self.dbCycles[index].controlPercentage
                    self.dbCycles[index].controlRateProrataPercentage = \
                        self.dbCycles[index].controlPercentage
                    # DELETE ONCE WORKING
                    # if db_state.controlDuration.total_seconds() > 0.0:
                    #     self.dbCycles[index].controlRateProrataPercentage = \
                    #        ((self.dbCycles[index].cycleEndTime -
                    #          db_state.controlStartTime).total_seconds() /
                    #          db_state.controlDuration.total_seconds() /
                    #          rate_prorata_percentage_total) * \
                    #          self.PERCENT_MAX

                    db_state.cycle_quantity_delta(self.dbCycles[index],
                                                  db_state,
                                                  self.dbCycles[index].controlPercentage,
                                                  self.dbCycles[index].shiftPercentage,
                                                  self.dbCycles[index].controlAlternativeProrataPercentage,
                                                  self.dbCycles[index].controlRateProrataPercentage)
            else:
                clean_remainder = False
                control_last_cycle_index = self.controlLastCycleIndex

                for index in range(len(self.dbCycles) - 1, control_last_cycle_index - 1, -1):
                    if self.dbCycles[index].cycleEndTime <= window_lower_time or \
                       clean_remainder:
                        self.dbCycles[index].controlPercentage = self.PERCENT_ZERO
                        self.dbCycles[index].controlRelevant = False
                        self.dbCycles[index].controlRateProrataPercentage = self.PERCENT_ZERO
                        self.dbCycles[index].controlAlternativeProrataPercentage = self.PERCENT_ZERO

                        # special case where all cycles in the cache are out of the control window
                        if index == len(self.dbCycles) - 1:
                            self.controlLastCycleIndex = index
                    else:
                        if self.dbCycles[index].cycleStartTimeProrata < window_lower_time \
                                < self.dbCycles[index].cycleEndTime:
                            if self.control.method == ControlRecord.ROLLING_WINDOW or \
                                  self.control.method == ControlRecord.ROLLING_MASS:
                                self.dbCycles[index].controlPercentage = \
                                    (self.dbCycles[index].cycleEndTime -
                                      window_lower_time).total_seconds() / \
                                     self.dbCycles[index].cycleDurationProrata.total_seconds() * \
                                     self.PERCENT_MAX
                                self.dbCycles[index].controlRelevant = True
                            else:
                                # this path should not get used
                                self.dbCycles[index].controlPercentage = self.PERCENT_MAX
                                self.dbCycles[index].controlRelevant = True
                        else:
                            self.dbCycles[index].controlPercentage = self.PERCENT_MAX
                            self.dbCycles[index].controlRelevant = True

                        if self.control.method == ControlRecord.ROLLING_WINDOW:
                            self.controlCumulative.window.magnitude += \
                                dt.timedelta(seconds=self.dbCycles[index].cycleDurationProrata.total_seconds() *
                                                     self.dbCycles[index].controlPercentage /
                                                     self.PERCENT_MAX)
                        elif self.control.method == ControlRecord.ROLLING_MASS:
                            # cycle_time_prorata = self.dbCycles[index].cycleDurationProrata.total_seconds()
                            # if self.dbCycles[index].cycleStartTimeProrata < window_lower_time:
                            #     cycle_time_prorata = min(self.dbCycles[index].cycleDurationProrata.total_seconds(),
                            #                              (self.dbCycles[index].cycleEndTime -
                            #                               window_lower_time).total_seconds())
                            self.controlCumulative.window.magnitude += \
                                dt.timedelta(seconds=self.dbCycles[index].cycleDurationProrata.total_seconds() *
                                                     self.dbCycles[index].controlPercentage /
                                                     self.PERCENT_MAX)

                        self.controlCumulative.mass.magnitude += self.dbCycles[index].mass.magnitude * \
                                                                 self.dbCycles[index].controlPercentage / \
                                                                 self.PERCENT_MAX

                        if self.control_cache_exceeded(db_state.control,
                                                       self.controlCumulative.mass,
                                                       self.controlCumulative.window,
                                                       self.dbCycles[index].cycleEndTime,
                                                       db_state.controlEndTime):

                            # remove all of the records until the control is back under the limit
                            clean_remainder = True
                            # new_control_last_cycle_index = index
                            exceed_control_percentage = 0.0

                            if self.control.method == ControlRecord.ROLLING_MASS:
                                if self.dbCycles[index].controlPercentage > 0.0:
                                    exceed_control_percentage = (self.controlCumulative.mass.magnitude -
                                                                 db_state.control.mass.magnitude) / \
                                                                self.dbCycles[index].mass.magnitude * \
                                                                self.PERCENT_MAX * \
                                                                (self.PERCENT_MAX /
                                                                 self.dbCycles[index].controlPercentage)
                                else:
                                    exceed_control_percentage = (self.controlCumulative.mass.magnitude -
                                                                 db_state.control.mass.magnitude) / \
                                                                self.dbCycles[index].mass.magnitude * \
                                                                self.PERCENT_MAX

                            else:
                                if self.dbCycles[index].controlPercentage > 0.0:
                                    exceed_control_percentage = \
                                        (self.controlCumulative.window.magnitude -
                                         db_state.control.window.magnitude).total_seconds() / \
                                        self.dbCycles[index].cycleDurationProrata.total_seconds() * \
                                        self.PERCENT_MAX * \
                                        (self.PERCENT_MAX /
                                         self.dbCycles[index].controlPercentage)
                                else:
                                    exceed_control_percentage = \
                                        (self.controlCumulative.window.magnitude -
                                         db_state.control.window.magnitude).total_seconds() / \
                                        self.dbCycles[index].cycleDurationProrata.total_seconds() * \
                                        self.PERCENT_MAX

                            self.dbCycles[index].controlRelevant = True
                            self.dbCycles[index].controlPercentage = self.PERCENT_MAX - exceed_control_percentage

                            if self.controlCumulative.window.magnitude.total_seconds() >= \
                               self.maxWindow.total_seconds():
                                # add on the cycle prorata if the maximum window has already been exceeded
                                self.controlCumulative.window.magnitude += \
                                    dt.timedelta(seconds=(window_lower_time -
                                                          self.dbCycles[index].cycleStartTimeProrata).total_seconds())
                                self.controlCumulative.window.magnitude -= \
                                    dt.timedelta(seconds=(self.dbCycles[index].cycleDurationProrata.total_seconds() *
                                                      (self.PERCENT_MAX -
                                                       self.dbCycles[index].controlPercentage) /
                                                      self.PERCENT_MAX))

                            else:

                                self.controlCumulative.window.magnitude -= \
                                    dt.timedelta(seconds=min(self.dbCycles[index].cycleDurationProrata.total_seconds(),
                                                             (self.dbCycles[index].cycleEndTime -
                                                              window_lower_time).total_seconds()) *
                                                             (self.PERCENT_MAX -
                                                              self.dbCycles[index].controlPercentage) /
                                                              self.PERCENT_MAX)

                            # special case for prorated rolling mass cycle that exceeds max control window
                            if self.controlCumulative.window.magnitude.total_seconds() > \
                                self.maxWindow.total_seconds():
                                # (self.dbCycles[index].cycleEndTime -
                                #  window_lower_time).total_seconds():
                                self.controlCumulative.window.magnitude = \
                                    dt.timedelta(seconds=(self.dbCycles[index].cycleEndTime -
                                                          window_lower_time).total_seconds())
                            # cycle_time_prorata = min(self.dbCycles[index].cycleDurationProrata.total_seconds(),
                            #                          (self.dbCycles[index].cycleEndTime -
                            #                           window_lower_time).total_seconds())
                            self.controlCumulative.mass.magnitude -= self.dbCycles[index].mass.magnitude * \
                                                                     (self.PERCENT_MAX -
                                                                      self.dbCycles[index].controlPercentage) / \
                                                                     self.PERCENT_MAX

                            if exceed_control_percentage < 0.0:
                                raise ValueError('Somehow the exceed control percentage for the cycle ' +
                                                 self.dbCycles[index].oid +
                                                 ' in the destination blend ' +
                                                 self.dbCycles[index].dbOid +
                                                 ' has ended up negative ' +
                                                 str(exceed_control_percentage))

                        elif db_state.control.method == ControlRecord.ROLLING_MASS and \
                                self.controlCumulative.window.magnitude > self.maxWindow:

                            pass

                        self.controlLastCycleIndex = index

                # Special case for rolling mass cycle time being different to mass for prorata
                control_last_cycle_start = \
                   self.dbCycles[self.controlLastCycleIndex].cycleStartTimeProrata + \
                   dt.timedelta(seconds=((self.PERCENT_MAX -
                                          self.dbCycles[self.controlLastCycleIndex].controlPercentage) /
                                          self.PERCENT_MAX *
                                          self.dbCycles[self.controlLastCycleIndex].
                                                cycleDurationProrata.total_seconds()))

                if self.control.method == ControlRecord.ROLLING_MASS and \
                   control_last_cycle_start < window_lower_time:
                    db_state.control_set(window_lower_time,
                                         prorata_end_time,
                                         cycle_update_time)
                else:
                    db_state.control_set(control_last_cycle_start,
                                         prorata_end_time,
                                         cycle_update_time)

                # for index in range(min(self.shiftLastCycleIndex, self.controlLastCycleIndex), len(self.dbCycles), 1):
                #     # calculate the prorata
                #     if db_state.useAlternativeProrata:
                #
                #         if self.control.method == ControlRecord.ROLLING_MASS:
                #
                #             control_mass += self.dbCycles[index].mass.magnitude * \
                #                 self.dbCycles[index].controlPercentage / \
                #                 self.PERCENT_MAX
                #
                #         else:
                #             if db_state.controlDuration.total_seconds() == 0.0 \
                #                     or not self.dbCycles[index].controlRelevant:
                #                 self.dbCycles[index].controlAlternativeProrataPercentage = 0.0
                #             else:
                #                 self.dbCycles[index].controlAlternativeProrataPercentage = \
                #                     ((self.dbCycles[index].cycleEndTime -
                #                      db_state.controlStartTime).total_seconds() /
                #                     db_state.controlDuration.total_seconds()) * self.PERCENT_MAX
                #     else:
                #         self.dbCycles[index].controlAlternativeProrataPercentage = \
                #             self.dbCycles[index].controlPercentage

                control_mass = self.controlCumulative.mass.magnitude

                if self.control.method == ControlRecord.ROLLING_MASS:
                    control_mass_missing = db_state.control.mass.magnitude - control_mass
                else:
                    control_mass_missing = 0

                accumulated_mass = 0.0
                rate_prorata_percentage_total = 0.0
                control_duration_calc = 0.0

                if self.control.method == ControlRecord.ROLLING_MASS:
                    control_duration_calc = self.controlCumulative.window.magnitude.total_seconds()
                else:
                    control_duration_calc = db_state.control.window.magnitude.total_seconds()

                for index in range(min(self.shiftLastCycleIndex, self.controlLastCycleIndex), len(self.dbCycles), 1):
                    if self.dbCycles[index].controlRelevant and \
                       control_duration_calc > 0.0:
                        rate_prorata_percentage_total += \
                            (control_duration_calc -
                             (prorata_end_time -
                              self.dbCycles[index].cycleEndTime).total_seconds()) / \
                             control_duration_calc * \
                             self.dbCycles[index].cycleDurationProrata.total_seconds() / \
                             control_duration_calc * \
                             self.PERCENT_MAX

                for index in range(min(self.shiftLastCycleIndex, self.controlLastCycleIndex), len(self.dbCycles), 1):

                    if self.dbCycles[index].controlRelevant:
                        if db_state.useAlternativeProrata:
                            if self.control.method == ControlRecord.ROLLING_MASS:
                                if control_mass == 0.0 \
                                        or not self.dbCycles[index].controlRelevant:
                                    self.dbCycles[index].controlAlternativeProrataPercentage = 0.0
                                else:
                                    accumulated_mass += self.dbCycles[index].mass.magnitude * \
                                        self.dbCycles[index].controlPercentage / \
                                        self.PERCENT_MAX
                                    self.dbCycles[index].controlAlternativeProrataPercentage = \
                                        (accumulated_mass + control_mass_missing) / \
                                        (control_mass + control_mass_missing) * self.PERCENT_MAX
                            else:
                                if db_state.controlDuration.total_seconds() == 0.0 \
                                        or not self.dbCycles[index].controlRelevant:
                                    self.dbCycles[index].controlAlternativeProrataPercentage = 0.0
                                else:
                                    self.dbCycles[index].controlAlternativeProrataPercentage = \
                                                        ((self.dbCycles[index].cycleEndTime -
                                                        db_state.controlStartTime).total_seconds() /
                                                        db_state.controlDuration.total_seconds()) * \
                                                        self.PERCENT_MAX

                            if rate_prorata_percentage_total > 0.0 and \
                               control_duration_calc > 0.0:
                                    self.dbCycles[index].controlRateProrataPercentage = \
                                        (control_duration_calc -
                                         (prorata_end_time -
                                          self.dbCycles[index].cycleEndTime).total_seconds()) / \
                                         control_duration_calc * \
                                         self.dbCycles[index].cycleDurationProrata.total_seconds() / \
                                        control_duration_calc * \
                                        self.PERCENT_MAX / \
                                         rate_prorata_percentage_total * \
                                         self.PERCENT_MAX
                        else:
                            self.dbCycles[index].controlAlternativeProrataPercentage = \
                                self.dbCycles[index].controlPercentage

                            self.dbCycles[index].controlRateProrataPercentage = \
                                self.dbCycles[index].controlPercentage

                    # calculate the prorata
                    db_state.cycle_quantity_delta(self.dbCycles[index],
                                                  db_state,
                                                  self.dbCycles[index].controlPercentage,
                                                  self.dbCycles[index].shiftPercentage,
                                                  self.dbCycles[index].controlAlternativeProrataPercentage,
                                                  self.dbCycles[index].controlRateProrataPercentage)

        # this is due to the control and shift duration being bookended by the update time
        self.controlCumulative.window.magnitude += \
           (cycle_update_time -
            prorata_end_time)

        db_state.cycle_datetime_update(prorata_end_time,
                                       cycle_update_time)

        if not ValueComparison.standard(db_state.controlDuration,
                                        self.controlCumulative.window.magnitude):
            raise ValueError('For destination blend ' +
                             db_state.destinationBlendOID +
                             ', control duration of the blend state ' +
                             str(db_state.controlDuration) +
                             '\n' +
                             'does not equal the magnitude of the control cumulative window ' +
                             str(self.controlCumulative.window.magnitude))

        # if not db_state.useAlternativeProrata:
        if not ValueComparison.standard(db_state.currentMasses[self.BLEND_TOTAL].value.magnitude,
                                        self.controlCumulative.mass.magnitude):
            raise ValueError('For destination blend ' +
                             db_state.destinationBlendOID +
                             ', current mass of the blend state ' +
                             '\n' +
                             str(db_state.currentMasses[self.BLEND_TOTAL].value.magnitude) +
                             ' does not equal the magnitude of the control cumulative mass ' +
                             str(self.controlCumulative.mass.magnitude))

    def set_max_window(self,
                       max_window):

        self.maxWindow = max_window

    def set_cache_batch_start_time(self,
                                   cache_batch_start_time):

        self.cacheBatchStartTime = cache_batch_start_time

    def control_cache_exceeded(self,
                               control,
                               cumulative_mass,
                               cumulative_window,
                               current_time,
                               next_batch_start_time):

        exceeded = False

        if control.method == ControlRecord.BATCH_MASS or \
           control.method == ControlRecord.ROLLING_MASS:
            if cumulative_mass.magnitude > control.mass.magnitude:
                exceeded = True
            else:
                exceeded = False

        elif control.method == ControlRecord.ROLLING_WINDOW:
            if cumulative_window.magnitude > control.window.magnitude:
                exceeded = True
            else:
                exceeded = False

        elif control.method == ControlRecord.BATCH_WINDOW:
            if current_time > next_batch_start_time:
                exceeded = True
            else:
                exceeded = False

        return exceeded

    def control_cache_synched(self,
                              control,
                              cumulative_mass,
                              cumulative_window,
                              current_time,
                              shift_start_time,
                              control_start_time):

        synched = False

        # special case for once off cache processing for first cache cycle
        if current_time > self.cacheBatchStartTime and \
                (control.method == ControlRecord.BATCH_MASS or
                 control.method == ControlRecord.BATCH_WINDOW):
            synched = False
            self.cacheBatchStartTime = dt.datetime.max
        else:
            if control.method == ControlRecord.BATCH_MASS or \
               control.method == ControlRecord.ROLLING_MASS:
                if cumulative_mass.magnitude > control.mass.magnitude:
                    synched = False
                else:
                    synched = True

            elif control.method == ControlRecord.BATCH_WINDOW or \
                 control.method == ControlRecord.ROLLING_WINDOW:
                if cumulative_window.magnitude > control.window.magnitude:
                    synched = False
                else:
                    synched = True

        return synched

    def remove_cycle(self,
                     cycle_oid,
                     db_state):

        if True:

            pass

        index = [find_index.oid for find_index in self.dbCycles].index(cycle_oid)

        if index < len(self.dbCycles) - 1:

            # adjust cycle that occurred after this new one
            self.dbCycles[index + 1].cycleStartTimeProrata = \
                self.dbCycles[index - 1].cycleEndTime
            self.dbCycles[index + 1].cycleDurationProrata = \
                self.dbCycles[index + 1].cycleEndTime - \
                self.dbCycles[index + 1].cycleStartTimeProrata

        self.dbCycles.pop(index)

        if index < self.shiftLastCycleIndex:
            self.shiftLastCycleIndex -= 1

        if index < self.controlLastCycleIndex:
            self.controlLastCycleIndex -= 1

        db_state.cycle_datetime_update(db_state.controlCurrentTime,
                                       db_state.updateTime)

    def shift_reset(self,
                    shift_reset_time):
        index = 0

        if self.dbCycles:

            for index in range(self.shiftLastCycleIndex, len(self.dbCycles), 1):
                if self.dbCycles[index].cycleEndTime < shift_reset_time:

                    self.dbCycles[index].shiftPercentage = self.PERCENT_ZERO
                    self.dbCycles[index].shiftRelevant = False

                else:
                    raise ValueError('Shift change at time ' +
                                     shift_reset_time +
                                     ' is before the most recent cycle at index ' +
                                     str(index) +
                                     ' and time ' +
                                     self.dbCycles[0].cycleEndtime)

            self.shiftLastCycleIndex = index + 1

        else:

            self.shiftLastCycleIndex = index

    def shift_control_reset(self,
                            control_reset_time):
        index = 0

        for index in range(self.controlLastCycleIndex, len(self.dbCycles), 1):
            if self.dbCycles[index].cycleEndTime < control_reset_time:

                self.dbCycles[index].controlPercentage = self.PERCENT_ZERO
                self.dbCycles[index].controlRelevant = False
                self.dbCycles[index].controlAlternativeProrataPercentage = self.PERCENT_ZERO
                self.dbCycles[index].controlRateProrataPercentage = self.PERCENT_ZERO

            else:
                raise ValueError('Shift change at time ' +
                                 control_reset_time +
                                 ' is before the most recent cycle at index ' +
                                 str(index) +
                                 ' and time ' +
                                 self.dbCycles[0].cycleEndtime)

        self.controlCumulative.mass.magnitude = 0.0
        self.controlCumulative.window.magnitude = dt.timedelta(seconds=0)

        self.controlLastCycleIndex = index


class DestinationBlendState:
    ZERO_VALUE = 0.0
    ZERO_INT = 0
    ZERO_WEIGHT = 0.0
    TIMEDELTA_ZERO = dt.timedelta(seconds=0)
    NO_UNIT = 'No Unit'
    NO_OID = 'No OID'
    BLEND_TOTAL = 'Blend Total'
    LOG_BLENDING_CYCLE = 'blendingCycle'
    LOG_ACTIVE_BLENDS_DTO = 'activeBlendsDTO'
    LOG_CYCLE_CACHE_ENTRY = 'cycleCacheEntry'
    LOG_SHIFT_START_LOOKUP = 'shiftStartLookUp'
    LOG_ENGINE_START_ENTRY = 'engineStartEntry'
    LOG_PROCESS_CYCLE_EVENT_ENTRY = 'processCycleEventEntry'
    LOG_TIME_RANGE_CONFIG_ENTRY = 'timeRangeConfigEntry'
    LOG_BLEND_CALCULATION_ENTRY = 'blendCalculationEntry'
    LOG_DESTINATION_BLEND_REMOVAL_ENTRY = 'destinationBlendRemovalEntry'
    LOG_DESTINATION_BLEND = 'destinationBlend'
    LOG_MASS_UNIT_TYPE = 'mass'
    LOG_START_DATE = 'startDate'
    LOG_END_DATE = 'endDate'
    LOG_BLEND_COMPUTATION_METHOD = 'blendComputationMethod'
    LOG_CONTROL_METHOD_MASS = 'controlMass'
    LOG_CONTROL_METHOD_TIME = 'controlDuration'
    LOG_MINIMUM_RATE = 'minimumRate'
    LOG_MAXIMUM_RATE = 'maximumRate'
    LOG_PROCESSOR_NAMES = 'processorNames'
    LOG_PROCESSOR_NAME = 'processorName'
    LOG_PROCESSOR_OID = 'processorOID'
    LOG_BLEND_MASS = 'blendMass'
    LOG_UNIT = 'unit'
    LOG_WINDOW_UNIT_TYPE = 'duration'
    LOG_CONTINUOUS_GRADE_CRITERIAS = 'continuousGradeCriterias'
    LOG_DISCRETE_GRADE_CRITERIAS = 'discreteGradeCriterias'
    LOG_MATERIAL_CRITERIAS = 'materialCriterias'
    LOG_CONTINUOUS_GRADE = 'grade'
    LOG_SHIFT_MASS = 'shiftMass'
    LOG_BATCH_LAST_START_DATE = 'batchLastStartDate'
    LOG_CRITERIA_LABEL = 'criteriaLabel'
    LOG_CONTINUOUS_GRADE_NAME = 'name'
    LOG_CRITERIA_OID = 'OID'
    LOG_CONTINUOUS_GRADE_OID = 'oid'
    LOG_MIN_VALUE = 'minimumValue'
    LOG_MAX_VALUE = 'maximumValue'
    LOG_LOWER_LIMIT = 'lowerLimit'
    LOG_MATERIAL = 'material'
    LOG_MATERIAL_NAME = 'name'
    LOG_MATERIAL_OID = 'oid'
    LOG_DISCRETE_GRADE = 'grade'
    LOG_DISCRETE_GRADE_NAME = 'name'
    LOG_DISCRETE_GRADE_OID = 'oid'
    LOG_DISCRETE_GRADE_VALUE_LIST = 'valueList'
    LOG_DISCRETE_GRADE_VALUE = 'gradeValue'
    LOG_BLEND_OID = 'blendOID'
    resetOnShiftChange = False
    useAlternativeProrata = True
    BATCH_MASS = 'BATCH_MASS'
    ROLLING_MASS = 'ROLLING_MASS'
    BATCH_WINDOW = 'BATCH_WINDOW'
    ROLLING_WINDOW = 'ROLLING_WINDOW'
    LOG_SECOND = 'second'
    LOG_KILOGRAM = 'kilogram'
    PERCENT_MAX = 100.0
    LOG_UNIT_TYPE = 'unitType'
    LOG_UNIT_NAME = 'unitName'
    RATE_UNIT = 'kilograms per second'
    RATE_UNIT_TYPE = 'rate'
    BLEND_RATE = 'blendRate'

    def __init__(self,
                 name,
                 oid,
                 dbDTO):

        control_method = \
            MineStarToInternal.out_tag_value(self.LOG_BLEND_COMPUTATION_METHOD,
                                             dbDTO.find(".//" +
                                                        self.LOG_BLEND_COMPUTATION_METHOD).text)

        control_window = None
        control_mass = None

        if control_method == ControlRecord.BATCH_MASS or control_method == ControlRecord.ROLLING_MASS:
            control_window = UnitTypeMagnitude(self.TIMEDELTA_ZERO,
                                               self.LOG_SECOND,
                                               self.LOG_WINDOW_UNIT_TYPE)
            control_mass = UnitTypeMagnitude.fromXML(dbDTO.find(".//" +
                                                                self.LOG_CONTROL_METHOD_MASS))

        elif control_method == ControlRecord.BATCH_WINDOW or control_method == ControlRecord.ROLLING_WINDOW:
            control_mass = UnitTypeMagnitude(self.ZERO_VALUE,
                                             self.LOG_KILOGRAM,
                                             self.LOG_MASS_UNIT_TYPE)
            control_window = UnitTypeMagnitude.fromXML(dbDTO.find(".//" +
                                                                  self.LOG_CONTROL_METHOD_TIME))

        else:

            raise ValueError('Unrecognised or missing controlMethod in the destination blend ' +
                             self.name)

        self.control = ControlRecord(control_method,
                                     control_window,
                                     control_mass)

        # Processors
        self.processors = {}
        for processor in dbDTO.findall(".//" +
                                       self.LOG_PROCESSOR_NAMES):

            self.processors[processor.find(".//" +
                                           self.LOG_PROCESSOR_OID).text] = processor.find(".//" +
                                                                                          self.LOG_PROCESSOR_NAME).text

        self.currentMasses = {}
        self.shiftMasses = {}
        self.currentValuesContinuous = {}
        self.currentValuesDiscrete = {}
        self.currentValuesMaterial = {}
        self.shiftValuesContinuous = {}
        self.shiftValuesDiscrete = {}
        self.shiftValuesMaterial = {}
        self.currentRate = {}
        self.shiftRate = {}

        # track all grades, masses by processor
        for processor_oid, processor_name in self.processors.iteritems():

            if self.control.method == ControlRecord.BATCH_MASS or self.control.method == ControlRecord.ROLLING_MASS:
                control_unit = self.control.mass.unit
            else:
                # it can not be assumed that the hit will occur by finding mass that is useful, so put in
                # the standard kilogram
                control_unit = self.LOG_KILOGRAM

            # current and shift mass
            self.currentMasses[processor_oid] = NonWeightedValue(self.LOG_BLEND_MASS,
                                                                 self.NO_OID,
                                                                 self.ZERO_VALUE,
                                                                 control_unit,
                                                                 self.LOG_MASS_UNIT_TYPE,
                                                                 self.ZERO_VALUE,
                                                                 self.ZERO_VALUE,
                                                                 False,
                                                                 True)
            self.shiftMasses[processor_oid] = NonWeightedValue(self.LOG_SHIFT_MASS,
                                                               self.NO_OID,
                                                               self.ZERO_VALUE,
                                                               control_unit,
                                                               self.LOG_MASS_UNIT_TYPE,
                                                               self.ZERO_VALUE,
                                                               self.ZERO_VALUE,
                                                               False,
                                                               True)

            # continuous grade
            dict_cg = {}

            for cg in dbDTO.findall('.//' +
                                    self.LOG_CONTINUOUS_GRADE_CRITERIAS):

                dict_cg[cg.find('./' +
                                self.LOG_CONTINUOUS_GRADE +
                                '/' +
                                self.LOG_CONTINUOUS_GRADE_OID).text] = \
                    WeightedValue(cg.find('./' +
                                          self.LOG_CONTINUOUS_GRADE +
                                          '/' +
                                          self.LOG_CONTINUOUS_GRADE_NAME).text,
                                  cg.find('./' +
                                          self.LOG_CONTINUOUS_GRADE +
                                          '/' +
                                          self.LOG_CONTINUOUS_GRADE_OID).text,
                                  self.ZERO_VALUE,
                                  cg.find('./' +
                                          self.LOG_UNIT_NAME).text,
                                  cg.find('./' +
                                          self.LOG_UNIT_TYPE).text,
                                  self.ZERO_VALUE,
                                  float(cg.find(self.LOG_MIN_VALUE).text),
                                  float(cg.find(self.LOG_MAX_VALUE).text),
                                  False,
                                  True)

            self.currentValuesContinuous[processor_oid] = dict_cg
            self.shiftValuesContinuous[processor_oid] = copy.deepcopy(dict_cg)

            # materials
            dict_mat = {}

            for mat in dbDTO.findall('.//' +
                                     self.LOG_MATERIAL_CRITERIAS):
                example = UnitTypeMagnitude.fromXML(mat.find(self.LOG_MIN_VALUE))

                dict_mat[mat.find('./' +
                                  self.LOG_MATERIAL +
                                  '/' +
                                  self.LOG_MATERIAL_OID).text] = \
                    WeightedValue(mat.find('./' +
                                           self.LOG_MATERIAL +
                                           '/' +
                                           self.LOG_MATERIAL_NAME).text,
                                  mat.find('./' +
                                           self.LOG_MATERIAL +
                                           '/' +
                                           self.LOG_MATERIAL_OID).text,
                                  self.ZERO_VALUE,
                                  example.unit,
                                  example.unitType,
                                  self.ZERO_VALUE,
                                  UnitTypeMagnitude.fromXML(mat.find(self.LOG_MIN_VALUE)).magnitude,
                                  UnitTypeMagnitude.fromXML(mat.find(self.LOG_MAX_VALUE)).magnitude,
                                  False,
                                  True)

            self.currentValuesMaterial[processor_oid] = dict_mat
            self.shiftValuesMaterial[processor_oid] = copy.deepcopy(dict_mat)

            # discrete grade
            dict_dg = {}

            for dg in dbDTO.findall('.//' +
                                    self.LOG_DISCRETE_GRADE_CRITERIAS):
                example = UnitTypeMagnitude.fromXML(dg.find(self.LOG_MIN_VALUE))

                # discrete grade value
                dict_dg_value = {}

                for dg_value in dg.findall('.//' +
                                           self.LOG_DISCRETE_GRADE_VALUE):

                    dict_dg_value[dg_value.text] = \
                        WeightedValue(dg_value.text,
                                      'No OID yet',
                                      self.ZERO_VALUE,
                                      example.unit,
                                      example.unitType,
                                      self.ZERO_VALUE,
                                      UnitTypeMagnitude.fromXML(dg.find(self.LOG_MIN_VALUE)).magnitude,
                                      UnitTypeMagnitude.fromXML(dg.find(self.LOG_MAX_VALUE)).magnitude,
                                      False,
                                      True)

                parent_dg = NonWeightedValue(dg.find('./' +
                                                     self.LOG_DISCRETE_GRADE +
                                                     '/' +
                                                     self.LOG_DISCRETE_GRADE_NAME).text,
                                             dg.find('./' +
                                                     self.LOG_DISCRETE_GRADE +
                                                     '/' +
                                                     self.LOG_DISCRETE_GRADE_OID).text,
                                             self.ZERO_VALUE,
                                             example.unit,
                                             example.unitType,
                                             self.ZERO_VALUE,
                                             self.ZERO_VALUE,
                                             False,
                                             True)

                if parent_dg.oid in dict_dg:
                    # with the introduction of the discrete grade value rather than the discrete grade value
                    # list, there should never be more than one of these
                    for dict_dg_value_key in dict_dg_value:
                        if dict_dg_value_key not in dict_dg[parent_dg.oid].children:

                            dict_dg[parent_dg.oid].children[dict_dg_value_key] = \
                                dict_dg_value[dict_dg_value_key]

                else:

                    dict_dg[parent_dg.oid] = CompositeWeightedValue(parent_dg, dict_dg_value)

            self.currentValuesDiscrete[processor_oid] = dict_dg
            self.shiftValuesDiscrete[processor_oid] = copy.deepcopy(dict_dg)

            # rates
            if dbDTO.find(".//" +
                          self.LOG_MINIMUM_RATE) is None:

                NonWeightedValue(self.BLEND_RATE,
                                 self.NO_OID,
                                 self.ZERO_VALUE,
                                 self.RATE_UNIT,
                                 self.RATE_UNIT_TYPE,
                                 self.ZERO_VALUE,
                                 self.ZERO_VALUE,
                                 False,
                                 True)

                self.currentRate[processor_oid] = NonWeightedValue(self.BLEND_RATE,
                                                                   self.NO_OID,
                                                                   self.ZERO_VALUE,
                                                                   self.RATE_UNIT,
                                                                   self.RATE_UNIT_TYPE,
                                                                   self.ZERO_VALUE,
                                                                   self.ZERO_VALUE,
                                                                   False,
                                                                   True)
            else:

                current_rate_UTM = UnitTypeMagnitude.fromXML(dbDTO.find(".//" +
                                                                        self.LOG_MINIMUM_RATE))

                self.currentRate[processor_oid] = NonWeightedValue(self.BLEND_RATE,
                                                                   self.NO_OID,
                                                                   current_rate_UTM.magnitude,
                                                                   current_rate_UTM.unit,
                                                                   current_rate_UTM.unitType,
                                                                   self.ZERO_VALUE,
                                                                   self.ZERO_VALUE,
                                                                   False,
                                                                   True)

            self.currentRate[processor_oid].value.magnitude = self.ZERO_VALUE

            self.shiftRate[processor_oid] = copy.deepcopy(self.currentRate[processor_oid])

        # create the blend totals for all masses, grades and materials
        if self.currentMasses != {}:
            self.currentMasses[self.BLEND_TOTAL] = \
                copy.deepcopy(self.currentMasses[self.currentMasses.keys()[0]])

        if self.shiftMasses != {}:
            self.shiftMasses[self.BLEND_TOTAL] = \
                copy.deepcopy(self.shiftMasses[self.shiftMasses.keys()[0]])

        if self.currentRate != {}:
            self.currentRate[self.BLEND_TOTAL] = \
                copy.deepcopy(self.currentRate[self.currentRate.keys()[0]])

        if self.shiftRate != {}:
            self.shiftRate[self.BLEND_TOTAL] = \
                copy.deepcopy(self.shiftRate[self.shiftRate.keys()[0]])

        if self.currentValuesContinuous != {}:
            self.currentValuesContinuous[self.BLEND_TOTAL] = \
                copy.deepcopy(self.currentValuesContinuous[self.currentValuesContinuous.keys()[0]])

        if self.currentValuesDiscrete != {}:
            self.currentValuesDiscrete[self.BLEND_TOTAL] = \
                copy.deepcopy(self.currentValuesDiscrete[self.currentValuesDiscrete.keys()[0]])

        if self.currentValuesMaterial != {}:
            self.currentValuesMaterial[self.BLEND_TOTAL] = \
                copy.deepcopy(self.currentValuesMaterial[self.currentValuesMaterial.keys()[0]])

        if self.shiftValuesContinuous != {}:
            self.shiftValuesContinuous[self.BLEND_TOTAL] = \
                copy.deepcopy(self.shiftValuesContinuous[self.shiftValuesContinuous.keys()[0]])

        if self.shiftValuesDiscrete != {}:
            self.shiftValuesDiscrete[self.BLEND_TOTAL] = \
                copy.deepcopy(self.shiftValuesDiscrete[self.shiftValuesDiscrete.keys()[0]])

        if self.shiftValuesMaterial != {}:
            self.shiftValuesMaterial[self.BLEND_TOTAL] = \
                copy.deepcopy(self.shiftValuesMaterial[self.shiftValuesMaterial.keys()[0]])

        self.name = name
        self.destinationBlendOID = oid

        self.blendOid = dbDTO.find(".//" +
                                   self.LOG_BLEND_OID).text

        start_date = dbDTO.find(".//" +
                                self.LOG_START_DATE)
        if start_date is not None:
            self.startDate = MineStarToInternal.to_datetime(start_date.text)
        else:
            self.startDate = None
            raise ValueError('The start date of the blend ' +
                             name +
                             ", " +
                             oid +
                             ' is missing in the iBlend.log')

        end_date = dbDTO.find(".//" +
                              self.LOG_END_DATE)
        if end_date is not None:
            self.endDate = MineStarToInternal.to_datetime(end_date.text)
        else:
            self.endDate = dt.datetime.max

        if self.startDate > self.endDate:
            raise ValueError('The start date ' +
                             self.startDate.strftime("%Y-%m-%d %H:%M:%S") +
                             ' is greater than the end date ' +
                             self.endDate.strftime("%Y-%m-%d %H:%M:%S") +
                             ' in the destination blend ' +
                             self.name)

        self.updateTime = self.startDate

        self.shiftStartTime = self.startDate
        self.shiftCurrentTime = self.startDate
        self.controlStartTime = self.startDate
        self.controlCurrentTime = self.startDate

        if self.control.method == ControlRecord.ROLLING_WINDOW or \
           self.control.method == ControlRecord.ROLLING_MASS or \
           self.control.method == ControlRecord.BATCH_WINDOW or \
           self.control.method == ControlRecord.BATCH_MASS:
            self.controlDuration = self.controlCurrentTime - self.controlStartTime
            if self.controlDuration > DestinationBlendCacheInternal.maxWindow:
                self.controlDuration = DestinationBlendCacheInternal.maxWindow

        self.shiftDuration = self.shiftCurrentTime - self.shiftStartTime

        if self.control.method == ControlRecord.BATCH_WINDOW:

            if self.control.window.unit != self.LOG_SECOND:
                raise ValueError('ControlWindow in the destination blend ' +
                                 self.name +
                                 ' is not in ' +
                                 self.LOG_SECOND)

            else:

                self.controlEndTime = self.controlStartTime + \
                                      self.control.window.magnitude

        else:

            self.controlEndTime = dt.datetime.max

        last_batch_date = dbDTO.find(".//" +
                                     self.LOG_BATCH_LAST_START_DATE)

        if last_batch_date is not None:
            if self.control.method ==  ControlRecord.BATCH_MASS:
                self.lastBatchStartDate = MineStarToInternal.to_datetime(last_batch_date.text)
            else:
                self.lastBatchStartDate = self.startDate
        else:
            self.lastBatchStartDate = self.startDate

    def set_shift_start_time(self,
                             shift_start_time):
        self.shiftStartTime = shift_start_time

    def set_reset_on_shift_change(self,
                                  reset_on_shift_change):
        self.resetOnShiftChange = reset_on_shift_change

    def non_control_continuous_grade(self,
                                     continuous_grade_name,
                                     continuous_grade_oid,
                                     continuous_grade_value):

        for processor_oid, current_masses in self.currentMasses.iteritems():
            cg = WeightedValue(continuous_grade_name,
                               continuous_grade_oid,
                               self.ZERO_VALUE,
                               continuous_grade_value.unit,
                               continuous_grade_value.unitType,
                               self.ZERO_VALUE,
                               self.ZERO_VALUE,
                               self.ZERO_VALUE,
                               True,
                               False)

            self.currentValuesContinuous[processor_oid][continuous_grade_oid] = cg
            self.shiftValuesContinuous[processor_oid][continuous_grade_oid] = copy.deepcopy(cg)

        self.currentValuesContinuous[self.BLEND_TOTAL][continuous_grade_oid] = \
            copy.deepcopy(self.currentValuesContinuous[self.currentValuesContinuous.keys()[0]][continuous_grade_oid])

        self.shiftValuesContinuous[self.BLEND_TOTAL][continuous_grade_oid] = \
            copy.deepcopy(self.shiftValuesContinuous[self.shiftValuesContinuous.keys()[0]][continuous_grade_oid])

    def non_control_discrete_grade(self,
                                   discrete_grade_name,
                                   discrete_grade_oid,
                                   discrete_grade_value_name,
                                   discrete_grade_value,
                                   discrete_grade_value_value):

        first_processor = True

        for processor_oid, current_masses in self.currentMasses.iteritems():

            dg_value = {discrete_grade_value_name: WeightedValue(discrete_grade_value_name,
                                                                 'No OID yet',
                                                                 self.ZERO_VALUE,
                                                                 discrete_grade_value_value.unit,
                                                                 discrete_grade_value_value.unitType,
                                                                 self.ZERO_VALUE,
                                                                 self.ZERO_VALUE,
                                                                 self.ZERO_VALUE,
                                                                 True,
                                                                 False)}

            parent_dg = NonWeightedValue(discrete_grade_name,
                                         discrete_grade_oid,
                                         self.ZERO_VALUE,
                                         discrete_grade_value.unit,
                                         discrete_grade_value.unitType,
                                         self.ZERO_VALUE,
                                         self.ZERO_VALUE,
                                         True,
                                         False)

            if parent_dg.oid in self.currentValuesDiscrete[processor_oid]:
                for dg_value_key, dg_value_value in dg_value.iteritems():
                    if dg_value_key not in self.currentValuesDiscrete[processor_oid][parent_dg.oid].children:
                        dg_value_value.weightMagnitude = \
                            self.currentValuesDiscrete[processor_oid][parent_dg.oid].parent.value.magnitude
                        self.currentValuesDiscrete[processor_oid][parent_dg.oid].children[dg_value_key] = dg_value_value
                        self.shiftValuesDiscrete[processor_oid][parent_dg.oid].children[dg_value_key] = \
                            copy.deepcopy(dg_value_value)

                        if first_processor:
                            self.currentValuesDiscrete[self.BLEND_TOTAL][parent_dg.oid].children[dg_value_key] = \
                                copy.deepcopy(dg_value_value)
                            self.shiftValuesDiscrete[self.BLEND_TOTAL][parent_dg.oid].children[dg_value_key] = \
                                copy.deepcopy(dg_value_value)
                            first_processor = False

            else:

                self.currentValuesDiscrete[processor_oid][parent_dg.oid] = \
                    CompositeWeightedValue(parent_dg, dg_value)
                self.shiftValuesDiscrete[processor_oid][parent_dg.oid] = \
                    CompositeWeightedValue(parent_dg, dg_value)

                if first_processor:
                    self.currentValuesDiscrete[self.BLEND_TOTAL][parent_dg.oid] = \
                        CompositeWeightedValue(parent_dg, dg_value)
                    self.shiftValuesDiscrete[self.BLEND_TOTAL][parent_dg.oid] = \
                        CompositeWeightedValue(parent_dg, dg_value)
                    first_processor = False

    def non_control_material(self,
                             material_name,
                             material_oid,
                             material_value):

        if not self.currentValuesMaterial[self.BLEND_TOTAL]:
            material_weight_magnitude = 0.0
        else:
            material_weight_magnitude = self.currentValuesMaterial[self.BLEND_TOTAL].itervalues().next().weightMagnitude

        for processor_oid, current_masses in self.currentMasses.iteritems():
            mat = WeightedValue(material_name,
                                material_oid,
                                self.ZERO_VALUE,
                                material_value.unit,
                                material_value.unitType,
                                material_weight_magnitude,
                                self.ZERO_VALUE,
                                self.ZERO_VALUE,
                                True,
                                False)

            self.currentValuesMaterial[processor_oid][material_oid] = mat
            self.shiftValuesMaterial[processor_oid][material_oid] = copy.deepcopy(mat)

        self.currentValuesMaterial[self.BLEND_TOTAL][material_oid] = \
            copy.deepcopy(self.currentValuesMaterial[self.currentValuesMaterial.keys()[0]][material_oid])

        self.shiftValuesMaterial[self.BLEND_TOTAL][material_oid] = \
            copy.deepcopy(self.shiftValuesMaterial[self.shiftValuesMaterial.keys()[0]][material_oid])

    def shift_values_reset(self):

        # code to clear the shift state
        for processor_oid, shift_value in self.shiftMasses.iteritems():
            self.shiftMasses[processor_oid].reset_values()
            self.shiftRate[processor_oid].value.magnitude = self.ZERO_VALUE
            for cg_key in self.shiftValuesContinuous[processor_oid]:
                self.shiftValuesContinuous[processor_oid][cg_key].reset_values()
            for dg_key in self.shiftValuesDiscrete[processor_oid]:
                self.shiftValuesDiscrete[processor_oid][dg_key].reset_values()
            for mat_key in self.shiftValuesMaterial[processor_oid]:
                self.shiftValuesMaterial[processor_oid][mat_key].reset_values()

    def shift_change(self,
                     shift_change_time,
                     current_time,
                     update_time):

        if self.resetOnShiftChange:

            # code to clear the control state
            self.control_reset(shift_change_time,
                               current_time,
                               update_time)

        self.shift_values_reset()

        # update times
        self.updateTime = update_time
        self.shiftStartTime = shift_change_time
        self.shiftCurrentTime = update_time

        self.shiftDuration = self.shiftCurrentTime - self.shiftStartTime

        self.cycle_datetime_update(update_time,
                                   update_time)

    def control_values_reset(self):

        for processor_oid, current_value in self.currentMasses.iteritems():
            self.currentMasses[processor_oid].reset_values()
            self.currentRate[processor_oid].value.magnitude = self.ZERO_VALUE
            for cg_key in self.currentValuesContinuous[processor_oid]:
                self.currentValuesContinuous[processor_oid][cg_key].reset_values()
            for dg_key in self.currentValuesDiscrete[processor_oid]:
                self.currentValuesDiscrete[processor_oid][dg_key].reset_values()
            for mat_key in self.currentValuesMaterial[processor_oid]:
                self.currentValuesMaterial[processor_oid][mat_key].reset_values()

    def control_set(self,
                    reset_time,
                    current_time,
                    update_time):

        self.controlStartTime = reset_time

        if self.control.method == self.BATCH_WINDOW:
            self.controlEndTime = self.controlStartTime + \
                                  self.control.window.magnitude

        self.controlCurrentTime = current_time
        self.updateTime = update_time

        self.controlDuration = self.controlCurrentTime - self.controlStartTime

        self.cycle_datetime_update(current_time,
                                   update_time)

    def control_reset(self,
                      reset_time,
                      current_time,
                      update_time):

        self.control_values_reset()

        self.control_set(reset_time,
                         current_time,
                         update_time)

    def cycle_control_rate_delta(self,
                                 db_cycle,
                                 rate_percentage):

        rate_factor = rate_percentage / self.PERCENT_MAX

        if db_cycle.cycleDurationProrata > dt.timedelta(seconds=0):
                self.currentRate[db_cycle.processorOid].value.magnitude += \
                    db_cycle.mass.magnitude / \
                    db_cycle.cycleDurationProrata.total_seconds() * \
                    rate_factor

                self.currentRate[self.BLEND_TOTAL].value.magnitude += \
                    db_cycle.mass.magnitude / \
                    db_cycle.cycleDurationProrata.total_seconds() * \
                    rate_factor

    def cycle_datetime_update(self,
                              current_time,
                              update_time):

        if current_time < self.controlCurrentTime or \
                        update_time < self.updateTime:

            raise ValueError('Current time ' +
                             str(current_time) +
                             ' is less than the previous current time ' +
                             str(self.controlCurrentTime) +
                             '\n' +
                             ' or the update time ' +
                             str(update_time) +
                             ' is less than the previous ' +
                             str(self.updateTime))

        self.controlCurrentTime = current_time
        self.controlDuration = update_time - self.controlStartTime

        self.shiftCurrentTime = current_time
        if self.shiftStartTime < self.startDate:
            self.shiftDuration = update_time - self.startDate
        else:
            self.shiftDuration = update_time - self.shiftStartTime

        for processor_oid in self.currentRate:
            if not self.useAlternativeProrata or \
               self.control.method == ControlRecord.BATCH_MASS or \
               self.control.method == ControlRecord.BATCH_WINDOW:
                if self.controlDuration > self.TIMEDELTA_ZERO:
                    self.currentRate[processor_oid].value.magnitude = \
                        self.currentMasses[processor_oid].value.magnitude / \
                        self.controlDuration.total_seconds()
                else:
                    self.currentRate[processor_oid].value.magnitude = 0.0

            if self.shiftDuration > self.TIMEDELTA_ZERO:
                self.shiftRate[processor_oid].value.magnitude = self.shiftMasses[processor_oid].value.magnitude / \
                                                                self.shiftDuration.total_seconds()
            else:
                self.shiftRate[processor_oid].value.magnitude = 0.0

        self.updateTime = update_time

    def cycle_quantity_delta(self,
                             db_cycle,
                             db_state,
                             control_percentage,
                             shift_percentage,
                             prorata_percentage,
                             rate_percentage):

        control_factor = control_percentage / \
                         self.PERCENT_MAX

        shift_factor = shift_percentage / \
                       self.PERCENT_MAX

        prorata_factor = prorata_percentage / \
                         self.PERCENT_MAX

        if self.useAlternativeProrata and \
            self.control.method != ControlRecord.BATCH_MASS and \
            self.control.method != ControlRecord.BATCH_WINDOW:
                self.cycle_control_rate_delta(db_cycle,
                                              rate_percentage)

        # masses
        db_cycle.mass.compare_unit(db_state.currentMasses[db_cycle.processorOid].value,
                                   db_state.currentMasses[db_cycle.processorOid].used)

        db_state.currentMasses[db_cycle.processorOid].value.magnitude += \
            db_cycle.mass.magnitude * \
            control_factor
        db_state.currentMasses[db_cycle.processorOid].set_is_used()

        db_state.shiftMasses[db_cycle.processorOid].value.magnitude += \
            db_cycle.mass.magnitude * \
            shift_factor
        db_state.shiftMasses[db_cycle.processorOid].set_is_used()

        db_state.currentMasses[self.BLEND_TOTAL].value.magnitude += \
            db_cycle.mass.magnitude * \
            control_factor
        db_state.currentMasses[self.BLEND_TOTAL].set_is_used()

        db_state.shiftMasses[self.BLEND_TOTAL].value.magnitude += \
            db_cycle.mass.magnitude * \
            shift_factor
        db_state.currentMasses[self.BLEND_TOTAL].set_is_used()

        # continuous grade
        for cg_key, cg_value in db_cycle.continuousGrades.iteritems():

            if not db_state.currentValuesContinuous[db_cycle.processorOid]:

                db_state.non_control_continuous_grade(cg_value.name,
                                                      cg_value.oid,
                                                      cg_value.value)

            elif cg_value.oid not in db_state.currentValuesContinuous[db_cycle.processorOid]:

                db_state.non_control_continuous_grade(cg_value.name,
                                                      cg_value.oid,
                                                      cg_value.value)

            cg_value.value.compare_unit(db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].value,
                                        db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].used)

            cg_value.value.compare_unit(db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].value,
                                        db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].used)

            cg_value.value.compare_unit(db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].value,
                                        db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].used)

            cg_value.value.compare_unit(db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].value,
                                        db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].used)

            # magnitude
            db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].weightMagnitude += \
                cg_value.weightMagnitude * \
                prorata_factor
            if prorata_factor > 0:
                db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].set_is_used()

            db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].weightMagnitude += \
                cg_value.weightMagnitude * \
                shift_factor
            if shift_factor > 0:
                db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].set_is_used()

            db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightMagnitude += \
                cg_value.weightMagnitude * \
                prorata_factor
            if prorata_factor > 0:
                db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].set_is_used()

            db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightMagnitude += \
                cg_value.weightMagnitude * \
                shift_factor
            if shift_factor > 0:
                db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].set_is_used()

            # weight magnitude
            db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].weightValueMagnitude += \
                cg_value.weightValueMagnitude * \
                prorata_factor

            db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].weightValueMagnitude += \
                cg_value.weightValueMagnitude * \
                shift_factor

            db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightValueMagnitude += \
                cg_value.weightValueMagnitude * \
                prorata_factor

            db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightValueMagnitude += \
                cg_value.weightValueMagnitude * \
                shift_factor

            # value magnitude
            if db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].weightMagnitude > 0.0:

                db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].value.magnitude = \
                    db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].weightValueMagnitude / \
                    db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].weightMagnitude
            else:
                db_state.currentValuesContinuous[db_cycle.processorOid][cg_value.oid].value.magnitude = 0.0

            if db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].weightMagnitude > 0.0:

                db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].value.magnitude = \
                    db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].weightValueMagnitude / \
                    db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].weightMagnitude
            else:
                db_state.shiftValuesContinuous[db_cycle.processorOid][cg_value.oid].value.magnitude = 0.0

            if db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightMagnitude > 0.0:

                db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].value.magnitude = \
                    db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightValueMagnitude / \
                    db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightMagnitude
            else:
                db_state.currentValuesContinuous[self.BLEND_TOTAL][cg_value.oid].value.magnitude = 0.0

            if db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightMagnitude > 0.0:

                db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].value.magnitude = \
                    db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightValueMagnitude / \
                    db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].weightMagnitude
            else:
                db_state.shiftValuesContinuous[self.BLEND_TOTAL][cg_value.oid].value.magnitude = 0.0

            # materials
        for mat_key, mat_value in db_cycle.materials.iteritems():
            if not db_state.currentValuesMaterial[db_cycle.processorOid]:

                db_state.non_control_material(mat_value.name,
                                              mat_value.oid,
                                              mat_value.value)

            elif mat_value.oid not in db_state.currentValuesMaterial[db_cycle.processorOid]:

                db_state.non_control_material(mat_value.name,
                                              mat_value.oid,
                                              mat_value.value)

            mat_value.value.compare_unit(db_state.currentValuesMaterial[db_cycle.processorOid][mat_value.oid].value,
                                         db_state.currentValuesMaterial[db_cycle.processorOid][mat_value.oid].used)

            mat_value.value.compare_unit(db_state.currentValuesMaterial[self.BLEND_TOTAL][mat_value.oid].value,
                                         db_state.currentValuesMaterial[self.BLEND_TOTAL][mat_value.oid].used)

            mat_value.value.compare_unit(db_state.shiftValuesMaterial[db_cycle.processorOid][mat_value.oid].value,
                                         db_state.shiftValuesMaterial[db_cycle.processorOid][mat_value.oid].used)

            mat_value.value.compare_unit(db_state.shiftValuesMaterial[self.BLEND_TOTAL][mat_value.oid].value,
                                         db_state.shiftValuesMaterial[self.BLEND_TOTAL][mat_value.oid].used)

            # magnitude
            for material_oid in db_state.currentValuesMaterial[self.BLEND_TOTAL]:

                db_state.currentValuesMaterial[db_cycle.processorOid][material_oid].weightMagnitude += \
                    mat_value.weightMagnitude * \
                    prorata_factor

                db_state.shiftValuesMaterial[db_cycle.processorOid][material_oid].weightMagnitude += \
                    mat_value.weightMagnitude * \
                    shift_factor

                db_state.currentValuesMaterial[self.BLEND_TOTAL][material_oid].weightMagnitude += \
                    mat_value.weightMagnitude * \
                    prorata_factor

                db_state.shiftValuesMaterial[self.BLEND_TOTAL][material_oid].weightMagnitude += \
                    mat_value.weightMagnitude * \
                    shift_factor

            if prorata_factor > 0:
                db_state.currentValuesMaterial[db_cycle.processorOid][mat_value.oid].set_is_used()
                db_state.currentValuesMaterial[self.BLEND_TOTAL][mat_value.oid].set_is_used()

            if shift_factor > 0:
                db_state.shiftValuesMaterial[db_cycle.processorOid][mat_value.oid].set_is_used()
                db_state.shiftValuesMaterial[self.BLEND_TOTAL][mat_value.oid].set_is_used()

            # weight magnitude
            db_state.currentValuesMaterial[db_cycle.processorOid][mat_value.oid].weightValueMagnitude += \
                mat_value.weightValueMagnitude * \
                prorata_factor

            db_state.shiftValuesMaterial[db_cycle.processorOid][mat_value.oid].weightValueMagnitude += \
                mat_value.weightValueMagnitude * \
                shift_factor

            db_state.currentValuesMaterial[self.BLEND_TOTAL][mat_value.oid].weightValueMagnitude += \
                mat_value.weightValueMagnitude * \
                prorata_factor

            db_state.shiftValuesMaterial[self.BLEND_TOTAL][mat_value.oid].weightValueMagnitude += \
                mat_value.weightValueMagnitude * \
                shift_factor

            # value magnitude
            for material_oid in db_state.currentValuesMaterial[self.BLEND_TOTAL]:
                if db_state.currentValuesMaterial[db_cycle.processorOid][material_oid].weightMagnitude > 0.0:

                    db_state.currentValuesMaterial[db_cycle.processorOid][material_oid].value.magnitude = \
                        db_state.currentValuesMaterial[db_cycle.processorOid][material_oid].weightValueMagnitude / \
                        db_state.currentValuesMaterial[db_cycle.processorOid][material_oid].weightMagnitude
                else:
                    db_state.currentValuesMaterial[db_cycle.processorOid][material_oid].value.magnitude = 0.0

                if db_state.shiftValuesMaterial[db_cycle.processorOid][material_oid].weightMagnitude > 0.0:

                    db_state.shiftValuesMaterial[db_cycle.processorOid][material_oid].value.magnitude = \
                        db_state.shiftValuesMaterial[db_cycle.processorOid][material_oid].weightValueMagnitude / \
                        db_state.shiftValuesMaterial[db_cycle.processorOid][material_oid].weightMagnitude
                else:
                    db_state.shiftValuesMaterial[db_cycle.processorOid][material_oid].value.magnitude = 0.0

                if db_state.currentValuesMaterial[self.BLEND_TOTAL][material_oid].weightMagnitude > 0.0:

                    db_state.currentValuesMaterial[self.BLEND_TOTAL][material_oid].value.magnitude = \
                        db_state.currentValuesMaterial[self.BLEND_TOTAL][material_oid].weightValueMagnitude / \
                        db_state.currentValuesMaterial[self.BLEND_TOTAL][material_oid].weightMagnitude
                else:
                    db_state.currentValuesMaterial[self.BLEND_TOTAL][material_oid].value.magnitude = 0.0

                if db_state.shiftValuesMaterial[self.BLEND_TOTAL][material_oid].weightMagnitude > 0.0:

                    db_state.shiftValuesMaterial[self.BLEND_TOTAL][material_oid].value.magnitude = \
                        db_state.shiftValuesMaterial[self.BLEND_TOTAL][material_oid].weightValueMagnitude / \
                        db_state.shiftValuesMaterial[self.BLEND_TOTAL][material_oid].weightMagnitude
                else:
                    db_state.shiftValuesMaterial[self.BLEND_TOTAL][material_oid].value.magnitude = 0.0

        # discrete grade
        for dg_key, dg_value in db_cycle.discreteGrades.iteritems():

            if not db_state.currentValuesDiscrete[db_cycle.processorOid]:
                db_state.non_control_discrete_grade(dg_value.parent.name,
                                                    dg_value.parent.oid,
                                                    dg_value.children.itervalues().next().name,
                                                    dg_value.parent.value,
                                                    dg_value.children.itervalues().next().value)

            elif dg_value.parent.oid not in db_state.currentValuesDiscrete[db_cycle.processorOid]:
                db_state.non_control_discrete_grade(dg_value.parent.name,
                                                    dg_value.parent.oid,
                                                    dg_value.children.itervalues().next().name,
                                                    dg_value.parent.value,
                                                    dg_value.children.itervalues().next().value)

            dg_value.parent.value.compare_unit(
                db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].parent.value,
                db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].parent.used)

            dg_value.parent.value.compare_unit(
                db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].parent.value,
                db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].parent.used)

            dg_value.parent.value.compare_unit(
                db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].parent.value,
                db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].parent.used)

            dg_value.parent.value.compare_unit(
                db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].parent.value,
                db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].parent.used)

            db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].parent.value.magnitude += \
                dg_value.parent.value.magnitude * \
                prorata_factor
            db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].parent.set_is_used()

            db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].parent.value.magnitude += \
                dg_value.parent.value.magnitude * \
                shift_factor
            db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].parent.set_is_used()

            db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].parent.value.magnitude += \
                dg_value.parent.value.magnitude * \
                prorata_factor
            db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].parent.set_is_used()

            db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].parent.value.magnitude += \
                dg_value.parent.value.magnitude * \
                shift_factor
            db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].parent.set_is_used()

            for dg_child_key, dg_child_value in dg_value.children.iteritems():

                # if dg_child_value.oid not in \
                if dg_child_value.name not in \
                        db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].children:
                    db_state.non_control_discrete_grade(dg_value.parent.name,
                                                        dg_value.parent.oid,
                                                        dg_child_value.name,
                                                        dg_value.parent.value,
                                                        dg_child_value.value)

                dg_child_value.value.compare_unit(
                    db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].
                    children[dg_child_value.name].value,
                    db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].
                    children[dg_child_value.name].used)

                dg_child_value.value.compare_unit(
                    db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].
                    children[dg_child_value.name].value,
                    db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].
                    children[dg_child_value.name].used)

                dg_child_value.value.compare_unit(
                    db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].
                        children[dg_child_value.name].value,
                    db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid].
                        children[dg_child_value.name].used)

                dg_child_value.value.compare_unit(
                    db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].
                        children[dg_child_value.name].value,
                    db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid].
                        children[dg_child_value.name].used)

                # weight magnitude
                for dg_value_key in db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                        .children:

                    db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                        .children[dg_value_key].weightMagnitude += \
                        dg_child_value.weightMagnitude * \
                        prorata_factor

                    db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                        .children[dg_value_key].weightMagnitude += \
                        dg_child_value.weightMagnitude * \
                        shift_factor

                    db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                        .children[dg_value_key].weightMagnitude += \
                        dg_child_value.weightMagnitude * \
                        prorata_factor

                    db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                        .children[dg_value_key].weightMagnitude += \
                        dg_child_value.weightMagnitude * \
                        shift_factor

                if prorata_factor > 0:
                    db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                        .children[dg_child_value.name].set_is_used()
                    db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                        .children[dg_child_value.name].set_is_used()

                if shift_factor > 0:
                    db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                        .children[dg_child_value.name].set_is_used()
                    db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                        .children[dg_child_value.name].set_is_used()

                # weight value magnitude
                db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                    .children[dg_child_value.name].weightValueMagnitude += \
                    dg_child_value.weightValueMagnitude * \
                    prorata_factor

                db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                    .children[dg_child_value.name].weightValueMagnitude += \
                    dg_child_value.weightValueMagnitude * \
                    shift_factor

                db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                    .children[dg_child_value.name].weightValueMagnitude += \
                    dg_child_value.weightValueMagnitude * \
                    prorata_factor

                db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                    .children[dg_child_value.name].weightValueMagnitude += \
                    dg_child_value.weightValueMagnitude * \
                    shift_factor

                # value magnitude
                for dg_value_key in db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                        .children:

                    if db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                            .children[dg_value_key].weightMagnitude > 0.0:

                        db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                            .children[dg_value_key].value.magnitude = \
                            db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                                .children[dg_value_key].weightValueMagnitude / \
                            db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                                .children[dg_value_key].weightMagnitude
                    else:
                        db_state.currentValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                            .children[dg_value_key].value.magnitude = 0.0

                    if db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                            .children[dg_value_key].weightMagnitude > 0.0:

                        db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                            .children[dg_value_key].value.magnitude = \
                            db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                                .children[dg_value_key].weightValueMagnitude / \
                            db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                                .children[dg_value_key].weightMagnitude
                    else:
                        db_state.shiftValuesDiscrete[db_cycle.processorOid][dg_value.parent.oid] \
                            .children[dg_value_key].value.magnitude = 0.0

                    if db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                            .children[dg_value_key].weightMagnitude > 0.0:

                        db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                            .children[dg_value_key].value.magnitude = \
                            db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                                .children[dg_value_key].weightValueMagnitude / \
                            db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                                .children[dg_value_key].weightMagnitude
                    else:
                        db_state.currentValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                            .children[dg_value_key].value.magnitude = 0.0

                    if db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                            .children[dg_value_key].weightMagnitude > 0.0:

                        db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                            .children[dg_value_key].value.magnitude = \
                            db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                                .children[dg_value_key].weightValueMagnitude / \
                            db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                                .children[dg_value_key].weightMagnitude
                    else:
                        db_state.shiftValuesDiscrete[self.BLEND_TOTAL][dg_value.parent.oid] \
                            .children[dg_value_key].value.magnitude = 0.0


class MineStarToInternal:
    OUT_TAG_VALUE = {DestinationBlendState.LOG_BLEND_COMPUTATION_METHOD:
                         {ControlRecord.ROLLING_WINDOW: ControlRecord.ROLLING_WINDOW,
                          ControlRecord.ROLLING_MASS: ControlRecord.ROLLING_MASS,
                          ControlRecord.BATCH_WINDOW: ControlRecord.BATCH_WINDOW,
                          ControlRecord.BATCH_MASS: ControlRecord.BATCH_MASS},
                     'weighting': {'mass': 'MASS',
                                   'ratio': 'ratio',
                                   'density': 'density'},
                     'weightedBy': {'mass': 'MASS',
                                    'ratio': 'MASS',
                                    'density': 'MASS',
                                    'work': 'WHATEVER',
                                    'force': 'WHATEVER'}}
    OUT_TAG = {'': ''}
    timeZone = None

    def __init__(self):
        pass

    @staticmethod
    def to_datetime_from_timestamp_text(time_stamp):
        return dt.datetime.fromtimestamp(int(time_stamp) / 1e3)

    @staticmethod
    def to_datetime(time_string):
        if time_string.find('+') >= 0:
            l_string, m_string, r_string = time_string.rpartition('+')
        elif time_string.find('-') >= 0:
            l_string, m_string, r_string = time_string.rpartition('-')
        else:
            raise ValueError('Expected timezone UTC prefix + or - but found neither')

        ll_string, lm_string, lr_string = l_string.rpartition('.')

        time_string_filtered = ll_string + lm_string + lr_string

        # if there are no sub seconds
        if ll_string + lm_string == '':
            time_string_filtered += '.000000'
        else:
            for zeros in range(len(lr_string), 6):
                time_string_filtered += '0'

        if MineStarToInternal.timeZone is not None:
            if MineStarToInternal.timeZone != m_string + r_string:
                raise ValueError('Expected timezone' +
                                 MineStarToInternal.timeZone +
                                 ' but found timezone' +
                                 m_string +
                                 r_string +
                                 ' in the iBlend.log')
        else:
            MineStarToInternal.timeZone = m_string + r_string

        try:
            new_date_time = dt.datetime.strptime(time_string_filtered,
                                             "%Y-%m-%dT%H:%M:%S.%f")

        except ValueError as err:
            raise err

        return new_date_time

    @staticmethod
    def out_tag(tag):

        return MineStarToInternal.OUT_TAG[tag]

    @staticmethod
    def out_tag_value(tag,
                      tag_value):

        if tag in MineStarToInternal.OUT_TAG_VALUE:
            if tag_value in MineStarToInternal.OUT_TAG_VALUE[tag]:
                return MineStarToInternal.OUT_TAG_VALUE[tag][tag_value]
            else:
                return 'Whatever'
                # raise ValueError('Mapping of tag ' +
                #                  tag +
                #                  ' was fine but the tag value ' +
                #                  tag_value +
                #                  ' was missing from MineStarToInternal')
        else:
            raise ValueError('Mapping of tag ' +
                             tag +
                             ' did not work.' +
                             '\n' +
                             'No idea if the tag value will work as yet - ' +
                             tag_value +
                             '\n',
                             'This is mapped in MintStarToInternal')


class DestinationBlendInternal:
    LOG_DESTINATION_BLENDS = 'destinationBlends'
    LOG_BLENDS = 'blends'
    LOG_BLEND_NAME = 'blendName'
    LOG_PROCESSORS = 'processors'
    LOG_KEY = 'key'
    LOG_ENTRY = 'entry'
    LOG_VALUE = 'value'
    LOG_CYCLE_CYCLE_OID = 'cycleOID'
    LOG_TIMESTAMP = 'timestamp'
    LOG_CALCULATION_TIME = 'calculationTime'

    def __init__(self,
                 name,
                 active_blends_DTO_root):

        self.name = name
        self.db_states = {}
        self.db_caches = {}
        self.cycle_to_db = {}
        active_blends = []

        for dbs_root in active_blends_DTO_root.findall(".//" +
                                                       self.LOG_DESTINATION_BLENDS):
            for db_root in dbs_root.findall(self.LOG_ENTRY):
                if db_root.find(self.LOG_KEY).text not in self.db_states:
                    self.add_blend(db_root.find(self.LOG_KEY).text,
                                   db_root.find(self.LOG_VALUE))
                    active_blends.append(db_root.find(self.LOG_KEY).text)

        pass

        remove_blends = []

        for existing_blend in self.db_states:
            if existing_blend not in active_blends:
                remove_blends.append(existing_blend)

        for remove_blend in remove_blends:
            remove_blend(remove_blend)

    def add_blend(self,
                  db_oid,
                  db_value_root):

        if db_oid not in self.db_states:
            self.db_states[db_oid] = \
                DestinationBlendState(db_value_root.find(".//" +
                                                         self.LOG_BLEND_NAME).text,
                                      db_oid,
                                      db_value_root)

            self.db_caches[db_oid] = \
                DestinationBlendCacheInternal(db_value_root.find(".//" +
                                                                 self.LOG_BLEND_NAME).text,
                                              db_oid,
                                              self.db_states[db_oid].control)
        else:
            pass
            # raise ValueError('Blend ' +
            #                  db_oid +
            #                  ' already exists and cannot be added.')

    def remove_blend(self,
                     db_oid):

        del self.db_states[db_oid]
        del self.db_caches[db_oid]

    def add_cycle(self,
                  db_cycle_XML,
                  db_oid,
                  cycle_update_time):

        self.add_cycle_from_cache(db_cycle_XML,
                                  db_oid,
                                  cycle_update_time)

    def add_cycle_from_cache(self,
                             db_cycle_XML,
                             db_oid,
                             cycle_update_time):

        cycle_oid = db_cycle_XML.find(".//" +
                                      self.LOG_CYCLE_CYCLE_OID).text

        # check to see if the cycle already exists
        if cycle_oid in self.cycle_to_db:

            if db_oid != self.cycle_to_db[cycle_oid]:

                self.db_caches[self.cycle_to_db[cycle_oid]].remove_cycle(cycle_oid,
                                                                         self.db_states[self.cycle_to_db[cycle_oid]])

                self.db_caches[db_oid].add_cycle_no_delta(db_cycle_XML,
                                                          self.db_states[db_oid],
                                                          True,
                                                          cycle_update_time)

                self.cycle_to_db[cycle_oid] = db_oid

            else:

                self.db_caches[self.cycle_to_db[cycle_oid]].remove_cycle(cycle_oid,
                    self.db_states[self.cycle_to_db[cycle_oid]])

                self.db_caches[db_oid].add_cycle_no_delta(db_cycle_XML,
                                                          self.db_states[db_oid],
                                                          True,
                                                          cycle_update_time)
        else:

            self.db_caches[db_oid].add_cycle_no_delta(db_cycle_XML,
                                                      self.db_states[db_oid],
                                                      False,
                                                      cycle_update_time)

            self.cycle_to_db[cycle_oid] = db_oid


class LogState:
    shiftStartLookUp = DestinationBlendState.LOG_SHIFT_START_LOOKUP
    blendingCycle = DestinationBlendState.LOG_BLENDING_CYCLE
    activeBlendsDTO = DestinationBlendState.LOG_ACTIVE_BLENDS_DTO
    cycleCacheEntry = DestinationBlendState.LOG_CYCLE_CACHE_ENTRY
    engineStartEntry = DestinationBlendState.LOG_ENGINE_START_ENTRY
    timeRangeConfigEntry = DestinationBlendState.LOG_TIME_RANGE_CONFIG_ENTRY
    processCycleEventEntry = DestinationBlendState.LOG_PROCESS_CYCLE_EVENT_ENTRY
    blendCalculationEntry = DestinationBlendState.LOG_BLEND_CALCULATION_ENTRY
    destinationBlendRemovalEntry = DestinationBlendState.LOG_DESTINATION_BLEND_REMOVAL_ENTRY
    destinationBlend = DestinationBlendState.LOG_DESTINATION_BLEND

    def __init__(self,
                 name):
        self.expected = [self.engineStartEntry,
                         self.activeBlendsDTO]
        self.name = name

    def next_state(self,
                   current_state):
        if current_state == self.engineStartEntry:
            self.expected = [self.activeBlendsDTO]

        elif current_state == self.activeBlendsDTO:
            self.expected = [self.cycleCacheEntry,
                             self.activeBlendsDTO,
                             self.blendingCycle,
                             self.destinationBlendRemovalEntry,
                             self.destinationBlend]

        elif current_state == self.cycleCacheEntry:
            self.expected = [self.timeRangeConfigEntry]

        elif current_state == self.blendingCycle:
            self.expected = [self.blendCalculationEntry]

        elif current_state == self.blendCalculationEntry:
            self.expected = [self.blendingCycle,
                             self.activeBlendsDTO,
                             self.destinationBlendRemovalEntry,
                             self.destinationBlend]

        elif current_state == self.timeRangeConfigEntry:
            self.expected = [self.blendingCycle,
                             self.activeBlendsDTO,
                             self.destinationBlendRemovalEntry,
                             self.destinationBlend]

        elif current_state == self.destinationBlend:
            self.expected = [self.blendingCycle,
                             self.activeBlendsDTO,
                             self.destinationBlendRemovalEntry,
                             self.destinationBlend]

        elif current_state == self.destinationBlendRemovalEntry:
            self.expected = [self.blendingCycle,
                             self.activeBlendsDTO,
                             self.destinationBlendRemovalEntry,
                             self.destinationBlend]

        else:
            raise ValueError('Log state ' +
                             current_state +
                             ' is unknown - this should never happen.')


class DestinationBlendStatusUpdateDTO:
    OUT_DESTINATION_BLEND_STATUS_UPDATE_DTO = 'destinationBlendStatusUpdateDTO'
    OUT_BLEND_MASS = 'blendMass'
    OUT_BLEND_VOLUME = 'blendVolume'
    OUT_MAGNITUDE = 'magnitude'
    OUT_UNIT = 'unit'
    OUT_UNIT_PERCENT = 'percent'
    OUT_UNIT_TYPE = 'unitType'
    OUT_CURRENT_VALUES = 'currentValues'
    OUT_GRADE_VALUE = 'gradeValue'
    OUT_MATERIAL_VALUE = 'materialValue'
    OUT_NAME = 'name'
    OUT_DESCRIPTIVE_NAME = 'descriptiveName'
    OUT_REF_OID = 'refOid'
    OUT_WEIGHTING = 'weighting'
    OUT_DESTINATION_BLEND_OID = 'destinationBlendOID'
    OUT_SHIFT_MASS = 'shiftMass'
    OUT_SHIFT_VALUES = 'shiftValues'
    OUT_UPDATE_TIME = 'updateTime'
    TOTAL = DestinationBlendState.BLEND_TOTAL
    OUT_PERCENT = 'percent'
    OUT_CONTROL_RATE = 'controlRate'
    OUT_SHIFT_RATE = 'shiftRate'
    OUT_WEIGHTED_BY = 'weightedBy'
    OUT_NO_IDEA = 'No Idea'
    OUT_NONE = ''
    OUT_SEQUENCE_NO = 'sequenceNo'
    OUT_UUID = 'uuid'
    OUT_CONTROL_WINDOW = 'controlWindow'
    OUT_SHIFT_WINDOW = 'shiftWindow'
    OUT_LOWER = 'lower'
    OUT_LOWER_BOUND_TYPE = 'lowerBoundType'
    OUT_UPPER = 'upper'
    OUT_UPPER_BOUND_TYPE = 'upperBoundType'
    OUT_OPEN = 'OPEN'
    OUT_CLOSED = 'CLOSED'
    OUT_FORMAT_MICRO_SECONDS = 3

    def __init__(self,
                 db_state,
                 uuid):

        # root and header tag
        self.dbuDTORoot = ET.Element(self.OUT_DESTINATION_BLEND_STATUS_UPDATE_DTO)

        # blend mass
        blend_mass = ET.TreeBuilder()

        blend_mass.start(self.OUT_BLEND_MASS,
                         {self.OUT_MAGNITUDE: str(db_state.currentMasses[self.TOTAL].value.magnitude),
                          self.OUT_UNIT: db_state.currentMasses[self.TOTAL].value.unit,
                          self.OUT_UNIT_TYPE: db_state.currentMasses[self.TOTAL].value.unitType})

        blend_mass.end(self.OUT_BLEND_MASS)
        self.dbuDTORoot.append(blend_mass.close())

        # current rate
        control_rate = ET.TreeBuilder()

        control_rate.start(self.OUT_CONTROL_RATE,
                           {self.OUT_MAGNITUDE: str(db_state.currentRate[self.TOTAL].value.magnitude),
                            self.OUT_UNIT: db_state.currentRate[self.TOTAL].value.unit,
                            self.OUT_UNIT_TYPE: db_state.currentRate[self.TOTAL].value.unitType})

        control_rate.end(self.OUT_CONTROL_RATE)
        self.dbuDTORoot.append(control_rate.close())

        # control window
        control_window_root = ET.Element(self.OUT_CONTROL_WINDOW)

        lower = ET.TreeBuilder()
        lower.start(self.OUT_LOWER, {})
        lower.data(str(int(time.mktime(db_state.controlStartTime.timetuple()))) +
            db_state.controlStartTime.strftime("%f")[:self.OUT_FORMAT_MICRO_SECONDS])
        lower.end(self.OUT_LOWER)
        control_window_root.append(lower.close())

        lower_bound = ET.TreeBuilder()
        lower_bound.start(self.OUT_LOWER_BOUND_TYPE, {})
        lower_bound.data(self.OUT_OPEN)
        lower_bound.end(self.OUT_LOWER_BOUND_TYPE)
        control_window_root.append(lower_bound.close())

        upper = ET.TreeBuilder()
        upper.start(self.OUT_UPPER, {})
        upper.data(str(int(time.mktime(db_state.controlCurrentTime.timetuple()))) +
            db_state.updateTime.strftime("%f")[:self.OUT_FORMAT_MICRO_SECONDS])
        upper.end(self.OUT_UPPER)
        control_window_root.append(upper.close())

        upper_bound = ET.TreeBuilder()
        upper_bound.start(self.OUT_UPPER_BOUND_TYPE, {})
        upper_bound.data(self.OUT_CLOSED)
        upper_bound.end(self.OUT_UPPER_BOUND_TYPE)
        control_window_root.append(upper_bound.close())

        self.dbuDTORoot.append(control_window_root)

        # current values

        # materials
        for mat_key, mat_value in db_state.currentValuesMaterial[self.TOTAL].iteritems():

            if mat_value.used:

                # grade value
                mat_root = ET.Element(self.OUT_CURRENT_VALUES)
                material_value = ET.TreeBuilder()

                material_value.start(self.OUT_MATERIAL_VALUE,
                                     {self.OUT_MAGNITUDE: str(mat_value.value.magnitude),
                                      self.OUT_UNIT: mat_value.value.unit,
                                      self.OUT_UNIT_TYPE: mat_value.value.unitType})

                material_value.end(self.OUT_MATERIAL_VALUE)
                mat_root.append(material_value.close())

                # name
                name = ET.TreeBuilder()
                name.start(self.OUT_NAME, {})
                name.data(mat_value.name)
                name.end(self.OUT_NAME)
                mat_root.append(name.close())

                # refOID
                ref_oid = ET.TreeBuilder()
                ref_oid.start(self.OUT_REF_OID, {})
                ref_oid.data(mat_value.oid)
                ref_oid.end(self.OUT_REF_OID)
                mat_root.append(ref_oid.close())

                # weighting
                weighting = ET.TreeBuilder()
                weighting.start(self.OUT_WEIGHTING, {})
                weighting.data(MineStarToInternal.out_tag_value(self.OUT_WEIGHTED_BY,
                                                                mat_value.value.unitType))
                weighting.end(self.OUT_WEIGHTING)
                mat_root.append(weighting.close())

                self.dbuDTORoot.append(mat_root)

        # continuous grades
        for cg_key, cg_value in db_state.currentValuesContinuous[self.TOTAL].iteritems():

            if cg_value.used:

                # grade value
                cg_root = ET.Element(self.OUT_CURRENT_VALUES)
                grade_value = ET.TreeBuilder()

                grade_value.start(self.OUT_GRADE_VALUE,
                                  {self.OUT_MAGNITUDE: str(cg_value.value.magnitude),
                                   self.OUT_UNIT: cg_value.value.unit,
                                   self.OUT_UNIT_TYPE: cg_value.value.unitType})

                grade_value.end(self.OUT_GRADE_VALUE)
                cg_root.append(grade_value.close())

                # name
                name = ET.TreeBuilder()
                name.start(self.OUT_NAME, {})
                name.data(cg_value.name)
                name.end(self.OUT_NAME)
                cg_root.append(name.close())

                # refOID
                ref_oid = ET.TreeBuilder()
                ref_oid.start(self.OUT_REF_OID, {})
                ref_oid.data(cg_value.oid)
                ref_oid.end(self.OUT_REF_OID)
                cg_root.append(ref_oid.close())

                # weighting
                weighting = ET.TreeBuilder()
                weighting.start(self.OUT_WEIGHTING, {})
                weighting.data(MineStarToInternal.out_tag_value(self.OUT_WEIGHTED_BY,
                                                                cg_value.value.unitType))
                weighting.end(self.OUT_WEIGHTING)
                cg_root.append(weighting.close())

                self.dbuDTORoot.append(cg_root)

        # discrete grades

        for dg_key, dg_value in db_state.currentValuesDiscrete[self.TOTAL].iteritems():

            if dg_value.parent.used:

                # grade value

                for dg_value_key, dg_value_value in dg_value.children.iteritems():

                    if dg_value_value.used:

                        dg_root = ET.Element(self.OUT_CURRENT_VALUES)

                        # descriptive name
                        descriptive_name = ET.TreeBuilder()
                        descriptive_name.start(self.OUT_DESCRIPTIVE_NAME, {})
                        descriptive_name.data(dg_value_key)
                        descriptive_name.end(self.OUT_DESCRIPTIVE_NAME)
                        dg_root.append(descriptive_name.close())

                        # grade value
                        grade_value = ET.TreeBuilder()

                        grade_value.start(self.OUT_GRADE_VALUE,
                                          {self.OUT_MAGNITUDE: str(dg_value_value.value.magnitude),
                                           self.OUT_UNIT: dg_value.parent.value.unit,
                                           self.OUT_UNIT_TYPE: dg_value.parent.value.unitType})

                        grade_value.end(self.OUT_GRADE_VALUE)
                        dg_root.append(grade_value.close())

                        # name
                        name = ET.TreeBuilder()
                        name.start(self.OUT_NAME, {})
                        name.data(dg_value.parent.name)
                        name.end(self.OUT_NAME)
                        dg_root.append(name.close())

                        # refOID
                        ref_oid = ET.TreeBuilder()
                        ref_oid.start(self.OUT_REF_OID, {})
                        ref_oid.data(dg_value.parent.oid)
                        ref_oid.end(self.OUT_REF_OID)
                        dg_root.append(ref_oid.close())

                        # weighting
                        weighting = ET.TreeBuilder()
                        weighting.start(self.OUT_WEIGHTING, {})
                        weighting.data(MineStarToInternal.out_tag_value(self.OUT_WEIGHTED_BY,
                                                                        dg_value_value.value.unitType))
                        weighting.end(self.OUT_WEIGHTING)
                        dg_root.append(weighting.close())

                        self.dbuDTORoot.append(dg_root)

        # destination blend oid
        destination_blend = ET.TreeBuilder()

        destination_blend.start(self.OUT_DESTINATION_BLEND_OID, {})
        destination_blend.data(str(db_state.destinationBlendOID))
        destination_blend.end(self.OUT_DESTINATION_BLEND_OID)
        self.dbuDTORoot.append(destination_blend.close())

        # sequence number
        sequence_no = ET.TreeBuilder()

        sequence_no.start(self.OUT_SEQUENCE_NO, {})
        # sequence_no.data(self.OUT_NONE)
        sequence_no.end(self.OUT_SEQUENCE_NO)
        self.dbuDTORoot.append(sequence_no.close())

        # shift mass
        shift_mass = ET.TreeBuilder()

        shift_mass.start(self.OUT_SHIFT_MASS,
                         {self.OUT_MAGNITUDE: str(db_state.shiftMasses[self.TOTAL].value.magnitude),
                          self.OUT_UNIT: db_state.shiftMasses[self.TOTAL].value.unit,
                          self.OUT_UNIT_TYPE: db_state.shiftMasses[self.TOTAL].value.unitType})

        shift_mass.end(self.OUT_SHIFT_MASS)
        self.dbuDTORoot.append(shift_mass.close())

        # shift rate
        shift_rate = ET.TreeBuilder()

        shift_rate.start(self.OUT_SHIFT_RATE,
                           {self.OUT_MAGNITUDE: str(db_state.shiftRate[self.TOTAL].value.magnitude),
                            self.OUT_UNIT: db_state.shiftRate[self.TOTAL].value.unit,
                            self.OUT_UNIT_TYPE: db_state.shiftRate[self.TOTAL].value.unitType})

        shift_rate.end(self.OUT_SHIFT_RATE)
        self.dbuDTORoot.append(shift_rate.close())

        # shift values

        # materials
        for mat_key, mat_value in db_state.shiftValuesMaterial[self.TOTAL].iteritems():

            if mat_value.used:

                # grade value
                mat_root = ET.Element(self.OUT_SHIFT_VALUES)
                material_value = ET.TreeBuilder()

                material_value.start(self.OUT_MATERIAL_VALUE,
                                     {self.OUT_MAGNITUDE: str(mat_value.value.magnitude),
                                      self.OUT_UNIT: mat_value.value.unit,
                                      self.OUT_UNIT_TYPE: mat_value.value.unitType})

                material_value.end(self.OUT_MATERIAL_VALUE)
                mat_root.append(material_value.close())

                # name
                name = ET.TreeBuilder()
                name.start(self.OUT_NAME, {})
                name.data(mat_value.name)
                name.end(self.OUT_NAME)
                mat_root.append(name.close())

                # refOID
                ref_oid = ET.TreeBuilder()
                ref_oid.start(self.OUT_REF_OID, {})
                ref_oid.data(mat_value.oid)
                ref_oid.end(self.OUT_REF_OID)
                mat_root.append(ref_oid.close())

                # weighting
                weighting = ET.TreeBuilder()
                weighting.start(self.OUT_WEIGHTING, {})
                weighting.data(MineStarToInternal.out_tag_value(self.OUT_WEIGHTED_BY,
                                                                mat_value.value.unitType))
                weighting.end(self.OUT_WEIGHTING)
                mat_root.append(weighting.close())

                self.dbuDTORoot.append(mat_root)

        # continuous grades
        for cg_key, cg_value in db_state.shiftValuesContinuous[self.TOTAL].iteritems():

            if cg_value.used:

                # grade value
                cg_root = ET.Element(self.OUT_SHIFT_VALUES)
                grade_value = ET.TreeBuilder()

                grade_value.start(self.OUT_GRADE_VALUE,
                                  {self.OUT_MAGNITUDE: str(cg_value.value.magnitude),
                                   self.OUT_UNIT: cg_value.value.unit,
                                   self.OUT_UNIT_TYPE: cg_value.value.unitType})

                grade_value.end(self.OUT_GRADE_VALUE)
                cg_root.append(grade_value.close())

                # name
                name = ET.TreeBuilder()
                name.start(self.OUT_NAME, {})
                name.data(cg_value.name)
                name.end(self.OUT_NAME)
                cg_root.append(name.close())

                # refOID
                ref_oid = ET.TreeBuilder()
                ref_oid.start(self.OUT_REF_OID, {})
                ref_oid.data(cg_value.oid)
                ref_oid.end(self.OUT_REF_OID)
                cg_root.append(ref_oid.close())

                # weighting
                weighting = ET.TreeBuilder()
                weighting.start(self.OUT_WEIGHTING, {})
                weighting.data(MineStarToInternal.out_tag_value(self.OUT_WEIGHTED_BY,
                                                                cg_value.value.unitType))
                weighting.end(self.OUT_WEIGHTING)
                cg_root.append(weighting.close())

                self.dbuDTORoot.append(cg_root)

        # discrete grades
        for dg_key, dg_value in db_state.shiftValuesDiscrete[self.TOTAL].iteritems():

            if dg_value.parent.used:

                # grade value

                for dg_value_key, dg_value_value in dg_value.children.iteritems():

                    if dg_value_value.used:

                        dg_root = ET.Element(self.OUT_SHIFT_VALUES)

                        # descriptive name
                        descriptive_name = ET.TreeBuilder()
                        descriptive_name.start(self.OUT_DESCRIPTIVE_NAME, {})
                        descriptive_name.data(dg_value_key)
                        descriptive_name.end(self.OUT_DESCRIPTIVE_NAME)
                        dg_root.append(descriptive_name.close())

                        # grade value
                        grade_value = ET.TreeBuilder()

                        grade_value.start(self.OUT_GRADE_VALUE,
                                          {self.OUT_MAGNITUDE: str(dg_value_value.value.magnitude),
                                           self.OUT_UNIT: dg_value.parent.value.unit,
                                           self.OUT_UNIT_TYPE: dg_value.parent.value.unitType})

                        grade_value.end(self.OUT_GRADE_VALUE)
                        dg_root.append(grade_value.close())

                        # name
                        name = ET.TreeBuilder()
                        name.start(self.OUT_NAME, {})
                        name.data(dg_value.parent.name)
                        name.end(self.OUT_NAME)
                        dg_root.append(name.close())

                        # refOID
                        ref_oid = ET.TreeBuilder()
                        ref_oid.start(self.OUT_REF_OID, {})
                        ref_oid.data(dg_value.parent.oid)
                        ref_oid.end(self.OUT_REF_OID)
                        dg_root.append(ref_oid.close())

                        # weighting
                        weighting = ET.TreeBuilder()
                        weighting.start(self.OUT_WEIGHTING, {})
                        weighting.data(MineStarToInternal.out_tag_value(self.OUT_WEIGHTED_BY,
                                                                        dg_value_value.value.unitType))
                        weighting.end(self.OUT_WEIGHTING)
                        dg_root.append(weighting.close())

                        self.dbuDTORoot.append(dg_root)

        # shift window
        shift_window_root = ET.Element(self.OUT_SHIFT_WINDOW)

        lower = ET.TreeBuilder()
        lower.start(self.OUT_LOWER, {})
        lower.data(str(int(time.mktime(db_state.shiftStartTime.timetuple()))) +
            db_state.shiftStartTime.strftime("%f")[:self.OUT_FORMAT_MICRO_SECONDS])
        lower.end(self.OUT_LOWER)
        shift_window_root.append(lower.close())

        lower_bound = ET.TreeBuilder()
        lower_bound.start(self.OUT_LOWER_BOUND_TYPE, {})
        lower_bound.data(self.OUT_OPEN)
        lower_bound.end(self.OUT_LOWER_BOUND_TYPE)
        shift_window_root.append(lower_bound.close())

        upper = ET.TreeBuilder()
        upper.start(self.OUT_UPPER, {})
        upper.data(str(int(time.mktime(db_state.shiftCurrentTime.timetuple()))) +
            db_state.updateTime.strftime("%f")[:self.OUT_FORMAT_MICRO_SECONDS])
        upper.end(self.OUT_UPPER)
        shift_window_root.append(upper.close())

        upper_bound = ET.TreeBuilder()
        upper_bound.start(self.OUT_UPPER_BOUND_TYPE, {})
        upper_bound.data(self.OUT_CLOSED)
        upper_bound.end(self.OUT_UPPER_BOUND_TYPE)
        shift_window_root.append(upper_bound.close())

        self.dbuDTORoot.append(shift_window_root)

        # update time
        update_time = ET.TreeBuilder()

        update_time.start(self.OUT_UPDATE_TIME, {})

        update_time.data(db_state.updateTime.strftime("%Y-%m-%dT%H:%M:%S.") +
                         str(int(int(db_state.updateTime.strftime("%f"))/1000)).zfill(3) +
                         MineStarToInternal.timeZone)

        update_time.end(self.OUT_UPDATE_TIME)
        self.dbuDTORoot.append(update_time.close())

        # uuid
        cycle_uuid = ET.TreeBuilder()

        cycle_uuid.start(self.OUT_UUID, {})
        cycle_uuid.data(uuid)
        cycle_uuid.end(self.OUT_UUID)
        self.dbuDTORoot.append(cycle_uuid.close())

        pass


class DestinationBlendReporting:
    OUT_DESTINATION_BLEND_STATUS_UPDATE_DTO = 'destinationBlendStatusUpdateDTO'
    OUT_BLEND_MASS = 'blendMass'
    OUT_BLEND_VOLUME = 'blendVolume'
    OUT_MAGNITUDE = 'magnitude'
    OUT_UNIT = 'unit'
    OUT_UNIT_PERCENT = 'percent'
    OUT_UNIT_TYPE = 'unitType'
    OUT_CURRENT_VALUES = 'currentValues'
    OUT_GRADE_VALUE = 'gradeValue'
    OUT_MATERIAL_VALUE = 'materialValue'
    OUT_NAME = 'name'
    OUT_DESCRIPTIVE_NAME = 'descriptiveName'
    OUT_REF_OID = 'refOid'
    OUT_WEIGHTING = 'weighting'
    OUT_DESTINATION_BLEND_OID = 'destinationBlendOID'
    OUT_SHIFT_MASS = 'shiftMass'
    OUT_SHIFT_VALUES = 'shiftValues'
    TOTAL = DestinationBlendState.BLEND_TOTAL
    OUT_PERCENT = 'percent'

    OUT_SHIFT_RATE = 'shiftRate'
    OUT_WEIGHTED_BY = 'weightedBy'
    OUT_NO_IDEA = 'No Idea'
    OUT_NONE = ''
    OUT_SEQUENCE_NO = 'sequenceNo'

    OUT_CONTROL_WINDOW = 'controlWindow'
    OUT_SHIFT_WINDOW = 'shiftWindow'
    OUT_LOWER = 'lower'
    OUT_LOWER_BOUND_TYPE = 'lowerBoundType'
    OUT_UPPER = 'upper'
    OUT_UPPER_BOUND_TYPE = 'upperBoundType'
    OUT_OPEN = 'OPEN'
    OUT_CLOSED = 'CLOSED'
    OUT_FORMAT_MICRO_SECONDS = 3

    OUT_CONTROL_RATE = 'controlRate'
    OUT_UUID = 'uuid'
    OUT_CYCLE = 'cycle'
    OUT_BLEND_NAME = 'blendName'
    OUT_BLEND_OID = 'blendOid'
    OUT_OID = 'oid'
    OUT_UPDATE_TIME = 'updateTime'
    OUT_PREVIOUS_END_TIME = 'previousEndTime'
    OUT_END_TIME = 'endTime'
    OUT_START_TIME = 'startTime'
    OUT_SHIFT_START_TIME = 'shiftStart'
    OUT_CONTROL_START_TIME = 'controlStartTime'
    OUT_CONTROL_END_TIME = 'controlEndTime'
    OUT_BATCH_START_TIME = 'batchStartTime'
    OUT_BLEND_START_TIME = 'blendStartTime'
    OUT_UPDATE_TIME_05M = 'updateTime05m'
    OUT_UPDATE_TIME_15M = 'updateTime15m'
    OUT_UPDATE_TIME_30M = 'updateTime30m'
    OUT_UPDATE_TIME_01H = 'updateTime01h'
    OUT_UPDATE_TIME_02H = 'updateTime02h'
    OUT_UPDATE_TIME_04H = 'updateTime04h'
    OUT_PREVIOUS_END_TIME_05M = 'previousEndTime05m'
    OUT_PREVIOUS_END_TIME_15M = 'previousEndTime15m'
    OUT_PREVIOUS_END_TIME_30M = 'previousEndTime30m'
    OUT_PREVIOUS_END_TIME_01H = 'previousEndTime01h'
    OUT_PREVIOUS_END_TIME_02H = 'previousEndTime02h'
    OUT_PREVIOUS_END_TIME_04H = 'previousEndTime04h'
    OUT_END_TIME_05M = 'endTime05m'
    OUT_END_TIME_15M = 'endTime15m'
    OUT_END_TIME_30M = 'endTime30m'
    OUT_END_TIME_01H = 'endTime01h'
    OUT_END_TIME_02H = 'endTime02h'
    OUT_END_TIME_04H = 'endTime04h'
    OUT_START_TIME_05M = 'startTime05m'
    OUT_START_TIME_15M = 'startTime15m'
    OUT_START_TIME_30M = 'startTime30m'
    OUT_START_TIME_01H = 'startTime01h'
    OUT_START_TIME_02H = 'startTime02h'
    OUT_START_TIME_04H = 'startTime04h'
    OUT_ASSIGNED_DESTINATION = 'assignedDestination'
    OUT_IS_LHD = 'isLHD'
    OUT_MACHINE_NAME = 'machineName'
    OUT_MACHINE_OID = 'machineOid'
    OUT_MATERIAL_COLOUR = 'materialColour'
    OUT_MATERIAL_NAME = 'materialName'
    OUT_PROCESSOR_NAME = 'processorName'
    OUT_PROCESSOR_OID = 'processorOid'
    OUT_SINK_DESTINATION = 'sinkDestination'
    OUT_SOURCE_BLOCK = 'sourceBlock'
    OUT_SOURCE_DESTINATION = 'sourceDestination'
    OUT_DURATION_SINCE_PREVIOUS = 'durationSincePrev'
    OUT_DURATION = 'duration'
    OUT_PAYLOAD = 'payload'
    OUT_PAYLOAD_UNIT = 'payloadUnit'
    OUT_DATA = 'data'
    OUT_DATA_NORMALISED = 'dataNormalised'
    OUT_DATA_TYPE = 'dataType'
    OUT_DATA_SCOPE = 'dataScope'
    OUT_DATA_VALUE = 'dataValue'
    OUT_DATA_WEIGHT = 'dataWeight'
    OUT_DATA_WEIGHT_VALUE = 'dataWeightValue'
    OUT_DATA_UNIT = 'dataUnit'
    OUT_DATA_UNIT_TYPE = 'dataUnitType'
    OUT_DATA_NAME = 'dataName'
    OUT_DATA_CATEGORY = 'dataCategory'
    OUT_DATA_NORMALISED_ADJUSTED = 'Adjusted'
    OUT_DATA_NORMALISED_RAW = 'Raw'
    OUT_DATA_TYPE_ACTUAL = 'Actual'
    OUT_DATA_TYPE_LOWER = 'Lower'
    OUT_DATA_TYPE_UPPER = 'Upper'
    OUT_DATA_SCOPE_CYCLE = 'Cycle'
    OUT_DATA_SCOPE_CONTROL = 'Control'
    OUT_DATA_SCOPE_SHIFT = 'Shift'
    OUT_DATA_CATEGORY_MASS = 'Mass'
    OUT_DATA_CATEGORY_DURATION = 'Duration'
    OUT_DATA_CATEGORY_RATE = 'Rate'
    OUT_DATA_CATEGORY_CONTINUOUS = 'Continuous'
    OUT_DATA_CATEGORY_DISCRETE = 'Discrete'
    OUT_DATA_CATEGORY_MATERIAL = 'Material'
    OUT_DATA_PROCESSOR = 'dataProcessor'
    OUT_DATA_OID = 'oid'
    OUT_DISCRETE_TOKEN = '|'
    OUT_DATA_NAME_TYPE = 'dataNameType'
    OUT_DATA_NAME_TYPE_SCOPE = 'dataNameTypeScope'
    OUT_DATA_DURATION_UNIT = 'Seconds'
    OUT_DATA_DURATION_UNIT_TYPE = 'Time'

    def __init__(self,
                 db_state,
                 uuid,
                 db_cycle):

        self.cycleHead = ET.Element(self.OUT_CYCLE)
        self.dataCycleHead = ET.Element(self.OUT_CYCLE)

        # uuid
        cycle_uuid = ET.TreeBuilder()

        cycle_uuid.start(self.OUT_UUID, {})
        cycle_uuid.data(uuid)
        cycle_uuid.end(self.OUT_UUID)
        self.cycleHead.append(cycle_uuid.close())

        # blend name
        blend_name = ET.TreeBuilder()

        blend_name.start(self.OUT_BLEND_NAME, {})
        blend_name.data(db_state.name)
        blend_name.end(self.OUT_BLEND_NAME)
        self.cycleHead.append(blend_name.close())

        # blend oid
        blend_oid = ET.TreeBuilder()

        blend_oid.start(self.OUT_BLEND_OID, {})
        blend_oid.data(db_state.blendOid)
        blend_oid.end(self.OUT_BLEND_OID)
        self.cycleHead.append(blend_oid.close())

        # cycle oid
        oid = ET.TreeBuilder()

        oid.start(self.OUT_OID, {})
        oid.data(db_cycle.oid)
        oid.end(self.OUT_OID)
        self.cycleHead.append(oid.close())

        # assigned destination
        assigned_destination = ET.TreeBuilder()

        assigned_destination.start(self.OUT_ASSIGNED_DESTINATION, {})
        if db_cycle.assignedDestination is None:
            assigned_destination.data('')
        else:
            assigned_destination.data(db_cycle.assignedDestination)
        assigned_destination.end(self.OUT_ASSIGNED_DESTINATION)
        self.cycleHead.append(assigned_destination.close())

        # is lhd
        is_lhd = ET.TreeBuilder()

        is_lhd.start(self.OUT_IS_LHD, {})
        is_lhd.data(db_cycle.isLHD)
        is_lhd.end(self.OUT_IS_LHD)
        self.cycleHead.append(is_lhd.close())

        # machine name
        machine_name = ET.TreeBuilder()

        machine_name.start(self.OUT_MACHINE_NAME, {})
        machine_name.data(db_cycle.machineName)
        machine_name.end(self.OUT_MACHINE_NAME)
        self.cycleHead.append(machine_name.close())

        # machine oid
        machine_oid = ET.TreeBuilder()

        machine_oid.start(self.OUT_MACHINE_OID, {})
        machine_oid.data(db_cycle.machineOid)
        machine_oid.end(self.OUT_MACHINE_OID)
        self.cycleHead.append(machine_oid.close())

        # material colour
        material_colour = ET.TreeBuilder()

        material_colour.start(self.OUT_MATERIAL_COLOUR, {})
        material_colour.data(db_cycle.materialColour)
        material_colour.end(self.OUT_MATERIAL_COLOUR)
        self.cycleHead.append(material_colour.close())

        # material name
        material_name = ET.TreeBuilder()

        material_name.start(self.OUT_MATERIAL_NAME, {})
        material_name.data(db_cycle.materialName)
        material_name.end(self.OUT_MATERIAL_NAME)
        self.cycleHead.append(material_name.close())

        # processor name
        processor_name = ET.TreeBuilder()

        processor_name.start(self.OUT_PROCESSOR_NAME, {})
        processor_name.data(db_cycle.processorName)
        processor_name.end(self.OUT_PROCESSOR_NAME)
        self.cycleHead.append(processor_name.close())

        # processor oid
        processor_oid = ET.TreeBuilder()

        processor_oid.start(self.OUT_PROCESSOR_OID, {})
        processor_oid.data(db_cycle.processorOid)
        processor_oid.end(self.OUT_PROCESSOR_OID)
        self.cycleHead.append(processor_oid.close())

        # sink destination
        sink_destination = ET.TreeBuilder()

        sink_destination.start(self.OUT_SINK_DESTINATION, {})
        sink_destination.data(db_cycle.sinkDestination)
        sink_destination.end(self.OUT_SINK_DESTINATION)
        self.cycleHead.append(sink_destination.close())

        # source block
        source_block = ET.TreeBuilder()

        source_block.start(self.OUT_SOURCE_BLOCK, {})
        source_block.data(db_cycle.sourceBlock)
        source_block.end(self.OUT_SOURCE_BLOCK)
        self.cycleHead.append(source_block.close())

        # source destination
        source_destination = ET.TreeBuilder()

        source_destination.start(self.OUT_SOURCE_DESTINATION, {})
        source_destination.data(db_cycle.sourceDestination)
        source_destination.end(self.OUT_SOURCE_DESTINATION)
        self.cycleHead.append(source_destination.close())

        # update time
        update_time = ET.TreeBuilder()

        update_time.start(self.OUT_UPDATE_TIME, {})
        update_time.data(db_state.updateTime.strftime('%Y-%m-%dT%H:%M:%S.') +
                         str(int(int(db_state.updateTime.strftime('%f')) / 1000)).zfill(3) +
                         MineStarToInternal.timeZone)
        update_time.end(self.OUT_UPDATE_TIME)
        self.cycleHead.append(update_time.close())

        temp_time = db_state.updateTime - dt.timedelta(minutes=db_state.updateTime.minute % 5,
                                                       seconds=db_state.updateTime.second,
                                                       microseconds=db_state.updateTime.microsecond)

        # update time 05m
        update_time_05m = ET.TreeBuilder()

        update_time_05m.start(self.OUT_UPDATE_TIME_05M, {})
        update_time_05m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                             str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                             MineStarToInternal.timeZone)
        update_time_05m.end(self.OUT_UPDATE_TIME_05M)
        self.cycleHead.append(update_time_05m.close())

        temp_time = db_state.updateTime - dt.timedelta(minutes=db_state.updateTime.minute % 15,
                                                       seconds=db_state.updateTime.second,
                                                       microseconds=db_state.updateTime.microsecond)

        # update time 15m
        update_time_15m = ET.TreeBuilder()

        update_time_15m.start(self.OUT_UPDATE_TIME_15M, {})
        update_time_15m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                             str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                             MineStarToInternal.timeZone)
        update_time_15m.end(self.OUT_UPDATE_TIME_15M)
        self.cycleHead.append(update_time_15m.close())

        temp_time = db_state.updateTime - dt.timedelta(minutes=db_state.updateTime.minute % 30,
                                                       seconds=db_state.updateTime.second,
                                                       microseconds=db_state.updateTime.microsecond)

        # update time 30m
        update_time_30m = ET.TreeBuilder()

        update_time_30m.start(self.OUT_UPDATE_TIME_30M, {})
        update_time_30m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                             str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                             MineStarToInternal.timeZone)
        update_time_30m.end(self.OUT_UPDATE_TIME_30M)
        self.cycleHead.append(update_time_30m.close())

        temp_time = db_state.updateTime - dt.timedelta(minutes=db_state.updateTime.minute,
                                                       seconds=db_state.updateTime.second,
                                                       microseconds=db_state.updateTime.microsecond)

        # update time 01h
        update_time_01h = ET.TreeBuilder()

        update_time_01h.start(self.OUT_UPDATE_TIME_01H, {})
        update_time_01h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                             str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                             MineStarToInternal.timeZone)
        update_time_01h.end(self.OUT_UPDATE_TIME_01H)
        self.cycleHead.append(update_time_01h.close())

        temp_time = db_state.updateTime - dt.timedelta(hours=db_state.updateTime.hour % 2,
                                                       minutes=db_state.updateTime.minute,
                                                       seconds=db_state.updateTime.second,
                                                       microseconds=db_state.updateTime.microsecond)

        # update time 02h
        update_time_02h = ET.TreeBuilder()

        update_time_02h.start(self.OUT_UPDATE_TIME_02H, {})
        update_time_02h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                             str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                             MineStarToInternal.timeZone)
        update_time_02h.end(self.OUT_UPDATE_TIME_02H)
        self.cycleHead.append(update_time_02h.close())

        temp_time = db_state.updateTime - dt.timedelta(hours=db_state.updateTime.hour % 4,
                                                       minutes=db_state.updateTime.minute,
                                                       seconds=db_state.updateTime.second,
                                                       microseconds=db_state.updateTime.microsecond)

        # update time 04h
        update_time_04h = ET.TreeBuilder()

        update_time_04h.start(self.OUT_UPDATE_TIME_04H, {})
        update_time_04h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                             str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                             MineStarToInternal.timeZone)
        update_time_04h.end(self.OUT_UPDATE_TIME_04H)
        self.cycleHead.append(update_time_04h.close())

        # previous end time
        previous_end_time = ET.TreeBuilder()

        previous_end_time.start(self.OUT_PREVIOUS_END_TIME, {})
        previous_end_time.data(db_cycle.cycleStartTimeProrata.strftime('%Y-%m-%dT%H:%M:%S.') +
                               str(int(int(db_cycle.cycleStartTimeProrata.strftime('%f')) / 1000)).zfill(3) +
                               MineStarToInternal.timeZone)
        previous_end_time.end(self.OUT_PREVIOUS_END_TIME)
        self.cycleHead.append(previous_end_time.close())

        temp_time = db_cycle.cycleStartTimeProrata - \
                    dt.timedelta(minutes=db_cycle.cycleStartTimeProrata.minute % 5,
                                 seconds=db_cycle.cycleStartTimeProrata.second,
                                 microseconds=db_cycle.cycleStartTimeProrata.microsecond)

        # previous end time 05m
        previous_end_time_05m = ET.TreeBuilder()

        previous_end_time_05m.start(self.OUT_PREVIOUS_END_TIME_05M, {})
        previous_end_time_05m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                                   str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                                   MineStarToInternal.timeZone)
        previous_end_time_05m.end(self.OUT_PREVIOUS_END_TIME_05M)
        self.cycleHead.append(previous_end_time_05m.close())

        temp_time = db_cycle.cycleStartTimeProrata - \
                    dt.timedelta(minutes=db_cycle.cycleStartTimeProrata.minute % 15,
                                 seconds=db_cycle.cycleStartTimeProrata.second,
                                 microseconds=db_cycle.cycleStartTimeProrata.microsecond)

        # previous end time 15m
        previous_end_time_15m = ET.TreeBuilder()

        previous_end_time_15m.start(self.OUT_PREVIOUS_END_TIME_15M, {})
        previous_end_time_15m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                                   str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                                   MineStarToInternal.timeZone)
        previous_end_time_15m.end(self.OUT_PREVIOUS_END_TIME_15M)
        self.cycleHead.append(previous_end_time_15m.close())

        temp_time = db_cycle.cycleStartTimeProrata - \
                    dt.timedelta(minutes=db_cycle.cycleStartTimeProrata.minute % 30,
                                 seconds=db_cycle.cycleStartTimeProrata.second,
                                 microseconds=db_cycle.cycleStartTimeProrata.microsecond)

        # previous end time 30m
        previous_end_time_30m = ET.TreeBuilder()

        previous_end_time_30m.start(self.OUT_PREVIOUS_END_TIME_30M, {})
        previous_end_time_30m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                                   str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                                   MineStarToInternal.timeZone)
        previous_end_time_30m.end(self.OUT_PREVIOUS_END_TIME_30M)
        self.cycleHead.append(previous_end_time_30m.close())

        temp_time = db_cycle.cycleStartTimeProrata - \
                    dt.timedelta(minutes=db_cycle.cycleStartTimeProrata.minute,
                                 seconds=db_cycle.cycleStartTimeProrata.second,
                                 microseconds=db_cycle.cycleStartTimeProrata.microsecond)

        # previous end time 01h
        previous_end_time_01h = ET.TreeBuilder()

        previous_end_time_01h.start(self.OUT_PREVIOUS_END_TIME_01H, {})
        previous_end_time_01h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                                   str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                                   MineStarToInternal.timeZone)
        previous_end_time_01h.end(self.OUT_PREVIOUS_END_TIME_01H)
        self.cycleHead.append(previous_end_time_01h.close())

        temp_time = db_cycle.cycleStartTimeProrata - \
                    dt.timedelta(hours=db_cycle.cycleStartTimeProrata.hour % 2,
                                 minutes=db_cycle.cycleStartTimeProrata.minute,
                                 seconds=db_cycle.cycleStartTimeProrata.second,
                                 microseconds=db_cycle.cycleStartTimeProrata.microsecond)

        # previous end time 02h
        previous_end_time_02h = ET.TreeBuilder()

        previous_end_time_02h.start(self.OUT_PREVIOUS_END_TIME_02H, {})
        previous_end_time_02h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                                   str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                                   MineStarToInternal.timeZone)
        previous_end_time_02h.end(self.OUT_PREVIOUS_END_TIME_02H)
        self.cycleHead.append(previous_end_time_02h.close())

        temp_time = db_cycle.cycleStartTimeProrata - \
                    dt.timedelta(hours=db_cycle.cycleStartTimeProrata.hour % 4,
                                 minutes=db_cycle.cycleStartTimeProrata.minute,
                                 seconds=db_cycle.cycleStartTimeProrata.second,
                                 microseconds=db_cycle.cycleStartTimeProrata.microsecond)

        # previous end time 04h
        previous_end_time_04h = ET.TreeBuilder()

        previous_end_time_04h.start(self.OUT_PREVIOUS_END_TIME_04H, {})
        previous_end_time_04h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                                   str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                                   MineStarToInternal.timeZone)
        previous_end_time_04h.end(self.OUT_PREVIOUS_END_TIME_04H)
        self.cycleHead.append(previous_end_time_04h.close())

        # end time
        end_time = ET.TreeBuilder()

        end_time.start(self.OUT_END_TIME, {})
        end_time.data(db_cycle.cycleEndTime.strftime('%Y-%m-%dT%H:%M:%S.') +
                      str(int(int(db_cycle.cycleEndTime.strftime('%f')) / 1000)).zfill(3) +
                      MineStarToInternal.timeZone)
        end_time.end(self.OUT_END_TIME)
        self.cycleHead.append(end_time.close())

        temp_time = db_cycle.cycleEndTime - \
                    dt.timedelta(minutes=db_cycle.cycleEndTime.minute % 5,
                                 seconds=db_cycle.cycleEndTime.second,
                                 microseconds=db_cycle.cycleEndTime.microsecond)

        # end time 05m
        end_time_05m = ET.TreeBuilder()

        end_time_05m.start(self.OUT_END_TIME_05M, {})
        end_time_05m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                          str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                          MineStarToInternal.timeZone)
        end_time_05m.end(self.OUT_END_TIME_05M)
        self.cycleHead.append(end_time_05m.close())

        temp_time = db_cycle.cycleEndTime - \
                    dt.timedelta(minutes=db_cycle.cycleEndTime.minute % 15,
                                 seconds=db_cycle.cycleEndTime.second,
                                 microseconds=db_cycle.cycleEndTime.microsecond)

        # end time 15m
        end_time_15m = ET.TreeBuilder()

        end_time_15m.start(self.OUT_END_TIME_15M, {})
        end_time_15m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                          str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                          MineStarToInternal.timeZone)
        end_time_15m.end(self.OUT_END_TIME_15M)
        self.cycleHead.append(end_time_15m.close())

        temp_time = db_cycle.cycleEndTime - \
                    dt.timedelta(minutes=db_cycle.cycleEndTime.minute % 30,
                                 seconds=db_cycle.cycleEndTime.second,
                                 microseconds=db_cycle.cycleEndTime.microsecond)

        # end time 30m
        end_time_30m = ET.TreeBuilder()

        end_time_30m.start(self.OUT_END_TIME_30M, {})
        end_time_30m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                          str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                          MineStarToInternal.timeZone)
        end_time_30m.end(self.OUT_END_TIME_30M)
        self.cycleHead.append(end_time_30m.close())

        temp_time = db_cycle.cycleEndTime - \
                    dt.timedelta(minutes=db_cycle.cycleEndTime.minute,
                                 seconds=db_cycle.cycleEndTime.second,
                                 microseconds=db_cycle.cycleEndTime.microsecond)

        # end time 01h
        end_time_01h = ET.TreeBuilder()

        end_time_01h.start(self.OUT_END_TIME_01H, {})
        end_time_01h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                          str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                          MineStarToInternal.timeZone)
        end_time_01h.end(self.OUT_END_TIME_01H)
        self.cycleHead.append(end_time_01h.close())

        temp_time = db_cycle.cycleEndTime - \
                    dt.timedelta(hours=db_cycle.cycleEndTime.hour % 2,
                                 minutes=db_cycle.cycleEndTime.minute,
                                 seconds=db_cycle.cycleEndTime.second,
                                 microseconds=db_cycle.cycleEndTime.microsecond)

        # end time 02h
        end_time_02h = ET.TreeBuilder()

        end_time_02h.start(self.OUT_END_TIME_02H, {})
        end_time_02h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                          str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                          MineStarToInternal.timeZone)
        end_time_02h.end(self.OUT_END_TIME_02H)
        self.cycleHead.append(end_time_02h.close())

        temp_time = db_cycle.cycleEndTime - \
                    dt.timedelta(hours=db_cycle.cycleEndTime.hour % 4,
                                 minutes=db_cycle.cycleEndTime.minute,
                                 seconds=db_cycle.cycleEndTime.second,
                                 microseconds=db_cycle.cycleEndTime.microsecond)

        # end time 04h
        end_time_04h = ET.TreeBuilder()

        end_time_04h.start(self.OUT_END_TIME_04H, {})
        end_time_04h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                          str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                          MineStarToInternal.timeZone)
        end_time_04h.end(self.OUT_END_TIME_04H)
        self.cycleHead.append(end_time_04h.close())

        # start time
        start_time = ET.TreeBuilder()

        start_time.start(self.OUT_START_TIME, {})
        start_time.data(db_cycle.cycleStartTime.strftime('%Y-%m-%dT%H:%M:%S.') +
                        str(int(int(db_cycle.cycleStartTime.strftime('%f')) / 1000)).zfill(3) +
                        MineStarToInternal.timeZone)
        start_time.end(self.OUT_START_TIME)
        self.cycleHead.append(start_time.close())

        temp_time = db_cycle.cycleStartTime - \
                    dt.timedelta(minutes=db_cycle.cycleStartTime.minute % 5,
                                 seconds=db_cycle.cycleStartTime.second,
                                 microseconds=db_cycle.cycleStartTime.microsecond)

        # start time 05m
        start_time_05m = ET.TreeBuilder()

        start_time_05m.start(self.OUT_START_TIME_05M, {})
        start_time_05m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                            str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                            MineStarToInternal.timeZone)
        start_time_05m.end(self.OUT_START_TIME_05M)
        self.cycleHead.append(start_time_05m.close())

        temp_time = db_cycle.cycleStartTime - \
                    dt.timedelta(minutes=db_cycle.cycleStartTime.minute % 15,
                                 seconds=db_cycle.cycleStartTime.second,
                                 microseconds=db_cycle.cycleStartTime.microsecond)

        # start time 15m
        start_time_15m = ET.TreeBuilder()

        start_time_15m.start(self.OUT_START_TIME_15M, {})
        start_time_15m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                            str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                            MineStarToInternal.timeZone)
        start_time_15m.end(self.OUT_START_TIME_15M)
        self.cycleHead.append(start_time_15m.close())

        temp_time = db_cycle.cycleStartTime - \
                    dt.timedelta(minutes=db_cycle.cycleStartTime.minute % 30,
                                 seconds=db_cycle.cycleStartTime.second,
                                 microseconds=db_cycle.cycleStartTime.microsecond)

        # start time 30m
        start_time_30m = ET.TreeBuilder()

        start_time_30m.start(self.OUT_START_TIME_30M, {})
        start_time_30m.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                            str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                            MineStarToInternal.timeZone)
        start_time_30m.end(self.OUT_START_TIME_30M)
        self.cycleHead.append(start_time_30m.close())

        temp_time = db_cycle.cycleStartTime - \
                    dt.timedelta(minutes=db_cycle.cycleStartTime.minute,
                                 seconds=db_cycle.cycleStartTime.second,
                                 microseconds=db_cycle.cycleStartTime.microsecond)

        # start time 01h
        start_time_01h = ET.TreeBuilder()

        start_time_01h.start(self.OUT_START_TIME_01H, {})
        start_time_01h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                            str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                            MineStarToInternal.timeZone)
        start_time_01h.end(self.OUT_START_TIME_01H)
        self.cycleHead.append(start_time_01h.close())

        temp_time = db_cycle.cycleStartTime - \
                    dt.timedelta(hours=db_cycle.cycleStartTime.hour % 2,
                                 minutes=db_cycle.cycleStartTime.minute,
                                 seconds=db_cycle.cycleStartTime.second,
                                 microseconds=db_cycle.cycleStartTime.microsecond)

        # start time 02h
        start_time_02h = ET.TreeBuilder()

        start_time_02h.start(self.OUT_START_TIME_02H, {})
        start_time_02h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                            str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                            MineStarToInternal.timeZone)
        start_time_02h.end(self.OUT_START_TIME_02H)
        self.cycleHead.append(start_time_02h.close())

        temp_time = db_cycle.cycleStartTime - \
                    dt.timedelta(hours=db_cycle.cycleStartTime.hour % 4,
                                 minutes=db_cycle.cycleStartTime.minute,
                                 seconds=db_cycle.cycleStartTime.second,
                                 microseconds=db_cycle.cycleStartTime.microsecond)

        # start time 04h
        start_time_04h = ET.TreeBuilder()

        start_time_04h.start(self.OUT_START_TIME_04H, {})
        start_time_04h.data(temp_time.strftime('%Y-%m-%dT%H:%M:%S.') +
                            str(int(int(temp_time.strftime('%f')) / 1000)).zfill(3) +
                            MineStarToInternal.timeZone)
        start_time_04h.end(self.OUT_START_TIME_04H)
        self.cycleHead.append(start_time_04h.close())

        # shift start time
        shift_start_time = ET.TreeBuilder()

        shift_start_time.start(self.OUT_SHIFT_START_TIME, {})
        shift_start_time.data(db_state.shiftStartTime.strftime('%Y-%m-%dT%H:%M:%S.') +
                              str(int(int(db_state.shiftStartTime.strftime('%f')) / 1000)).zfill(3) +
                              MineStarToInternal.timeZone)
        shift_start_time.end(self.OUT_SHIFT_START_TIME)
        self.cycleHead.append(shift_start_time.close())

        # control start time
        control_start_time = ET.TreeBuilder()

        control_start_time.start(self.OUT_CONTROL_START_TIME, {})
        control_start_time.data(db_state.controlStartTime.strftime('%Y-%m-%dT%H:%M:%S.') +
                                str(int(int(db_state.controlStartTime.strftime('%f')) / 1000)).zfill(3) +
                                MineStarToInternal.timeZone)
        control_start_time.end(self.OUT_CONTROL_START_TIME)
        self.cycleHead.append(control_start_time.close())

        # control end time
        control_end_time = ET.TreeBuilder()

        control_end_time.start(self.OUT_CONTROL_END_TIME, {})
        control_end_time.data(db_state.controlEndTime.strftime('%Y-%m-%dT%H:%M:%S.') +
                              str(int(int(db_state.controlEndTime.strftime('%f')) / 1000)).zfill(3) +
                              MineStarToInternal.timeZone)
        control_end_time.end(self.OUT_CONTROL_END_TIME)
        self.cycleHead.append(control_end_time.close())

        # batch start time
        batch_start_time = ET.TreeBuilder()

        batch_start_time.start(self.OUT_BATCH_START_TIME, {})
        batch_start_time.data(db_state.lastBatchStartDate.strftime('%Y-%m-%dT%H:%M:%S.') +
                              str(int(int(db_state.lastBatchStartDate.strftime('%f')) / 1000)).zfill(3) +
                              MineStarToInternal.timeZone)
        batch_start_time.end(self.OUT_BATCH_START_TIME)
        self.cycleHead.append(batch_start_time.close())

        # blend start time
        blend_start_time = ET.TreeBuilder()

        blend_start_time.start(self.OUT_BLEND_START_TIME, {})
        blend_start_time.data(db_state.startDate.strftime('%Y-%m-%dT%H:%M:%S.') +
                              str(int(int(db_state.startDate.strftime('%f')) / 1000)).zfill(3) +
                              MineStarToInternal.timeZone)
        blend_start_time.end(self.OUT_BLEND_START_TIME)
        self.cycleHead.append(blend_start_time.close())

        # duration since previous
        duration_since_previous = ET.TreeBuilder()

        duration_since_previous.start(self.OUT_DURATION_SINCE_PREVIOUS, {})
        duration_since_previous.data(str(db_cycle.cycleDurationProrata.total_seconds()))
        duration_since_previous.end(self.OUT_DURATION_SINCE_PREVIOUS)
        self.cycleHead.append(duration_since_previous.close())

        # duration since cycle start
        duration_since_start = ET.TreeBuilder()

        duration_since_start.start(self.OUT_DURATION, {})
        duration_since_start.data(str(db_cycle.cycleDuration.total_seconds()))
        duration_since_start.end(self.OUT_DURATION)
        self.cycleHead.append(duration_since_start.close())

        # payload
        data_cycle_payload = ET.TreeBuilder()

        data_cycle_payload.start(self.OUT_PAYLOAD, {})
        data_cycle_payload.data(str(db_cycle.mass.magnitude))
        data_cycle_payload.end(self.OUT_PAYLOAD)
        self.cycleHead.append(data_cycle_payload.close())

        # payload unit
        data_cycle_payload_unit = ET.TreeBuilder()

        data_cycle_payload_unit.start(self.OUT_PAYLOAD_UNIT, {})
        data_cycle_payload_unit.data(db_cycle.mass.unit)
        data_cycle_payload_unit.end(self.OUT_PAYLOAD_UNIT)
        self.cycleHead.append(data_cycle_payload_unit.close())

        # uuid
        data_cycle_uuid = ET.TreeBuilder()

        data_cycle_uuid.start(self.OUT_UUID, {})
        data_cycle_uuid.data(uuid)
        data_cycle_uuid.end(self.OUT_UUID)
        self.dataCycleHead.append(data_cycle_uuid.close())

        # cycle data

        for proc_key, proc_value in db_state.currentMasses.iteritems():

            proc_name = proc_key
            if proc_name != self.TOTAL:
                proc_name = db_state.processors[proc_key]

            # Raw Actual Control Mass
            self.add_data(uuid,
                          self.OUT_DATA_NORMALISED_RAW,
                          self.OUT_DATA_TYPE_ACTUAL,
                          self.OUT_DATA_SCOPE_CONTROL,
                          proc_name,
                          self.OUT_DATA_CATEGORY_MASS,
                          self.OUT_DATA_CATEGORY_MASS,
                          self.OUT_DATA_CATEGORY_MASS,
                          str(db_state.currentMasses[proc_key].value.magnitude),
                          str(db_state.controlDuration.total_seconds()),
                          str(db_state.currentMasses[proc_key].value.magnitude *
                              db_state.controlDuration.total_seconds()),
                          db_state.currentMasses[proc_key].value.unit,
                          db_state.currentMasses[proc_key].value.unitType)

            # Raw Actual Shift Mass
            self.add_data(uuid,
                          self.OUT_DATA_NORMALISED_RAW,
                          self.OUT_DATA_TYPE_ACTUAL,
                          self.OUT_DATA_SCOPE_SHIFT,
                          proc_name,
                          self.OUT_DATA_CATEGORY_MASS,
                          self.OUT_DATA_CATEGORY_MASS,
                          self.OUT_DATA_CATEGORY_MASS,
                          str(db_state.shiftMasses[proc_key].value.magnitude),
                          str(db_state.shiftDuration.total_seconds()),
                          str(db_state.shiftMasses[proc_key].value.magnitude *
                              db_state.shiftDuration.total_seconds()),
                          db_state.shiftMasses[proc_key].value.unit,
                          db_state.shiftMasses[proc_key].value.unitType)

            # Raw Actual Control Rate
            self.add_data(uuid,
                          self.OUT_DATA_NORMALISED_RAW,
                          self.OUT_DATA_TYPE_ACTUAL,
                          self.OUT_DATA_SCOPE_CONTROL,
                          proc_name,
                          self.OUT_DATA_CATEGORY_RATE,
                          self.OUT_DATA_CATEGORY_RATE,
                          self.OUT_DATA_CATEGORY_RATE,
                          str(db_state.currentRate[proc_key].value.magnitude),
                          str(db_state.controlDuration.total_seconds()),
                          str(db_state.currentRate[proc_key].value.magnitude *
                              db_state.controlDuration.total_seconds()),
                          db_state.currentRate[proc_key].value.unit,
                          db_state.currentRate[proc_key].value.unitType)

            # Raw Actual Shift Rate
            self.add_data(uuid,
                          self.OUT_DATA_NORMALISED_RAW,
                          self.OUT_DATA_TYPE_ACTUAL,
                          self.OUT_DATA_SCOPE_SHIFT,
                          proc_name,
                          self.OUT_DATA_CATEGORY_RATE,
                          self.OUT_DATA_CATEGORY_RATE,
                          self.OUT_DATA_CATEGORY_RATE,
                          str(db_state.shiftRate[proc_key].value.magnitude),
                          str(db_state.shiftDuration.total_seconds()),
                          str(db_state.shiftRate[proc_key].value.magnitude *
                              db_state.shiftDuration.total_seconds()),
                          db_state.shiftRate[proc_key].value.unit,
                          db_state.shiftRate[proc_key].value.unitType)

            # Raw Actual Control Duration
            self.add_data(uuid,
                          self.OUT_DATA_NORMALISED_RAW,
                          self.OUT_DATA_TYPE_ACTUAL,
                          self.OUT_DATA_SCOPE_CONTROL,
                          proc_name,
                          self.OUT_DATA_CATEGORY_DURATION,
                          self.OUT_DATA_CATEGORY_DURATION,
                          self.OUT_DATA_CATEGORY_DURATION,
                          str(db_state.controlDuration.total_seconds()),
                          str(db_state.currentRate[proc_key].value.magnitude),
                          str(db_state.currentRate[proc_key].value.magnitude *
                              db_state.controlDuration.total_seconds()),
                          self.OUT_DATA_DURATION_UNIT,
                          self.OUT_DATA_DURATION_UNIT_TYPE)

            # Raw Actual Shift Rate
            self.add_data(uuid,
                          self.OUT_DATA_NORMALISED_RAW,
                          self.OUT_DATA_TYPE_ACTUAL,
                          self.OUT_DATA_SCOPE_SHIFT,
                          proc_name,
                          self.OUT_DATA_CATEGORY_DURATION,
                          self.OUT_DATA_CATEGORY_DURATION,
                          self.OUT_DATA_CATEGORY_DURATION,
                          str(db_state.shiftDuration.total_seconds()),
                          str(db_state.shiftRate[proc_key].value.magnitude),
                          str(db_state.shiftRate[proc_key].value.magnitude *
                              db_state.shiftDuration.total_seconds()),
                          self.OUT_DATA_DURATION_UNIT,
                          self.OUT_DATA_DURATION_UNIT_TYPE)

            # continuous grades
            # Raw Actual Control Continuous
            for cg_key, cg_value in db_state.currentValuesContinuous[proc_key].iteritems():

                self.add_data(uuid,
                              self.OUT_DATA_NORMALISED_RAW,
                              self.OUT_DATA_TYPE_ACTUAL,
                              self.OUT_DATA_SCOPE_CONTROL,
                              proc_name,
                              self.OUT_DATA_CATEGORY_CONTINUOUS,
                              cg_value.name,
                              cg_value.oid,
                              str(cg_value.value.magnitude),
                              str(cg_value.weightMagnitude),
                              str(cg_value.weightValueMagnitude),
                              cg_value.value.unit,
                              cg_value.value.unitType)

                if cg_value.relevantToDb:
                    # Raw Lower Control Continuous
                    self.add_data(uuid,
                                  self.OUT_DATA_NORMALISED_RAW,
                                  self.OUT_DATA_TYPE_LOWER,
                                  self.OUT_DATA_SCOPE_CONTROL,
                                  proc_name,
                                  self.OUT_DATA_CATEGORY_CONTINUOUS,
                                  cg_value.name,
                                  cg_value.oid,
                                  str(cg_value.lowerLimit),
                                  str(cg_value.weightMagnitude),
                                  str(cg_value.weightMagnitude *
                                      cg_value.lowerLimit),
                                  cg_value.value.unit,
                                  cg_value.value.unitType)

                    # Raw Upper Control Continuous
                    self.add_data(uuid,
                                  self.OUT_DATA_NORMALISED_RAW,
                                  self.OUT_DATA_TYPE_UPPER,
                                  self.OUT_DATA_SCOPE_CONTROL,
                                  proc_name,
                                  self.OUT_DATA_CATEGORY_CONTINUOUS,
                                  cg_value.name,
                                  cg_value.oid,
                                  str(cg_value.upperLimit),
                                  str(cg_value.weightMagnitude),
                                  str(cg_value.weightMagnitude *
                                      cg_value.upperLimit),
                                  cg_value.value.unit,
                                  cg_value.value.unitType)

            # Raw Actual Shift Continuous
            for cg_key, cg_value in db_state.shiftValuesContinuous[proc_key].iteritems():

                self.add_data(uuid,
                              self.OUT_DATA_NORMALISED_RAW,
                              self.OUT_DATA_TYPE_ACTUAL,
                              self.OUT_DATA_SCOPE_SHIFT,
                              proc_name,
                              self.OUT_DATA_CATEGORY_CONTINUOUS,
                              cg_value.name,
                              cg_value.oid,
                              str(cg_value.value.magnitude),
                              str(cg_value.weightMagnitude),
                              str(cg_value.weightValueMagnitude),
                              cg_value.value.unit,
                              cg_value.value.unitType)

            # discrete grades
            # Raw Actual Control Discrete
            for dg_key, dg_value in db_state.currentValuesDiscrete[proc_key].iteritems():

                # grade value
                for dg_value_key, dg_value_value in dg_value.children.iteritems():

                    self.add_data(uuid,
                                  self.OUT_DATA_NORMALISED_RAW,
                                  self.OUT_DATA_TYPE_ACTUAL,
                                  self.OUT_DATA_SCOPE_CONTROL,
                                  proc_name,
                                  self.OUT_DATA_CATEGORY_DISCRETE,
                                  dg_value.parent.name +
                                  self.OUT_DISCRETE_TOKEN +
                                  dg_value_value.name,
                                  dg_value.parent.oid +
                                  self.OUT_DISCRETE_TOKEN +
                                  dg_value_value.name,
                                  str(dg_value_value.value.magnitude),
                                  str(dg_value_value.weightMagnitude),
                                  str(dg_value_value.weightValueMagnitude),
                                  dg_value.parent.value.unit,
                                  dg_value.parent.value.unitType)

                    if dg_value_value.relevantToDb:
                        # Raw Lower Control Discrete
                        self.add_data(uuid,
                                      self.OUT_DATA_NORMALISED_RAW,
                                      self.OUT_DATA_TYPE_LOWER,
                                      self.OUT_DATA_SCOPE_CONTROL,
                                      proc_name,
                                      self.OUT_DATA_CATEGORY_DISCRETE,
                                      dg_value.parent.name +
                                      self.OUT_DISCRETE_TOKEN +
                                      dg_value_value.name,
                                      dg_value.parent.oid +
                                      self.OUT_DISCRETE_TOKEN +
                                      dg_value_value.name,
                                      str(dg_value_value.lowerLimit),
                                      str(dg_value_value.weightMagnitude),
                                      str(dg_value_value.weightMagnitude *
                                          dg_value_value.lowerLimit),
                                      dg_value.parent.value.unit,
                                      dg_value.parent.value.unitType)

                        # Raw Upper Control Discrete
                        self.add_data(uuid,
                                      self.OUT_DATA_NORMALISED_RAW,
                                      self.OUT_DATA_TYPE_UPPER,
                                      self.OUT_DATA_SCOPE_CONTROL,
                                      proc_name,
                                      self.OUT_DATA_CATEGORY_DISCRETE,
                                      dg_value.parent.name +
                                      self.OUT_DISCRETE_TOKEN +
                                      dg_value_value.name,
                                      dg_value.parent.oid +
                                      self.OUT_DISCRETE_TOKEN +
                                      dg_value_value.name,
                                      str(dg_value_value.upperLimit),
                                      str(dg_value_value.weightMagnitude),
                                      str(dg_value_value.weightMagnitude *
                                          dg_value_value.upperLimit),
                                      dg_value.parent.value.unit,
                                      dg_value.parent.value.unitType)

            # Raw Actual Shift Discrete
            for dg_key, dg_value in db_state.shiftValuesDiscrete[proc_key].iteritems():

                # grade value
                for dg_value_key, dg_value_value in dg_value.children.iteritems():

                    self.add_data(uuid,
                                  self.OUT_DATA_NORMALISED_RAW,
                                  self.OUT_DATA_TYPE_ACTUAL,
                                  self.OUT_DATA_SCOPE_SHIFT,
                                  proc_name,
                                  self.OUT_DATA_CATEGORY_DISCRETE,
                                  dg_value.parent.name +
                                  self.OUT_DISCRETE_TOKEN +
                                  dg_value_value.name,
                                  dg_value.parent.oid +
                                  self.OUT_DISCRETE_TOKEN +
                                  dg_value_value.name,
                                  str(dg_value_value.value.magnitude),
                                  str(dg_value_value.weightMagnitude),
                                  str(dg_value_value.weightValueMagnitude),
                                  dg_value.parent.value.unit,
                                  dg_value.parent.value.unitType)

            # materials
            # Raw Actual Control Material
            for mat_key, mat_value in db_state.currentValuesMaterial[proc_key].iteritems():

                self.add_data(uuid,
                              self.OUT_DATA_NORMALISED_RAW,
                              self.OUT_DATA_TYPE_ACTUAL,
                              self.OUT_DATA_SCOPE_CONTROL,
                              proc_name,
                              self.OUT_DATA_CATEGORY_MATERIAL,
                              mat_value.name,
                              mat_value.oid,
                              str(mat_value.value.magnitude),
                              str(mat_value.weightMagnitude),
                              str(mat_value.weightValueMagnitude),
                              mat_value.value.unit,
                              mat_value.value.unitType)

                # raw lower control material
                if mat_value.relevantToDb:
                    self.add_data(uuid,
                                  self.OUT_DATA_NORMALISED_RAW,
                                  self.OUT_DATA_TYPE_LOWER,
                                  self.OUT_DATA_SCOPE_CONTROL,
                                  proc_name,
                                  self.OUT_DATA_CATEGORY_MATERIAL,
                                  mat_value.name,
                                  mat_value.oid,
                                  str(mat_value.lowerLimit),
                                  str(mat_value.weightMagnitude),
                                  str(mat_value.weightMagnitude *
                                      mat_value.lowerLimit),
                                  mat_value.value.unit,
                                  mat_value.value.unitType)

                    # raw upper control material
                    self.add_data(uuid,
                                  self.OUT_DATA_NORMALISED_RAW,
                                  self.OUT_DATA_TYPE_UPPER,
                                  self.OUT_DATA_SCOPE_CONTROL,
                                  proc_name,
                                  self.OUT_DATA_CATEGORY_MATERIAL,
                                  mat_value.name,
                                  mat_value.oid,
                                  str(mat_value.upperLimit),
                                  str(mat_value.weightMagnitude),
                                  str(mat_value.weightMagnitude *
                                      mat_value.upperLimit),
                                  mat_value.value.unit,
                                  mat_value.value.unitType)

            # Raw Actual Shift Material
            for mat_key, mat_value in db_state.shiftValuesMaterial[proc_key].iteritems():

                self.add_data(uuid,
                              self.OUT_DATA_NORMALISED_RAW,
                              self.OUT_DATA_TYPE_ACTUAL,
                              self.OUT_DATA_SCOPE_SHIFT,
                              proc_name,
                              self.OUT_DATA_CATEGORY_MATERIAL,
                              mat_value.name,
                              mat_value.oid,
                              str(mat_value.value.magnitude),
                              str(mat_value.weightMagnitude),
                              str(mat_value.weightValueMagnitude),
                              mat_value.value.unit,
                              mat_value.value.unitType)

        # Cycle
        # Raw Actual Cycle Mass
        self.add_data(uuid,
                      self.OUT_DATA_NORMALISED_RAW,
                      self.OUT_DATA_TYPE_ACTUAL,
                      self.OUT_DATA_SCOPE_CYCLE,
                      db_cycle.processorName,
                      self.OUT_DATA_CATEGORY_MASS,
                      self.OUT_DATA_CATEGORY_MASS,
                      self.OUT_DATA_CATEGORY_MASS,
                      str(db_cycle.mass.magnitude),
                      str(db_cycle.cycleDurationProrata.total_seconds()),
                      str(db_cycle.mass.magnitude *
                          db_cycle.cycleDurationProrata.total_seconds()),
                      db_state.currentMasses[db_cycle.processorOid].value.unit,
                      db_state.currentMasses[db_cycle.processorOid].value.unitType)

        # Raw Actual Cycle Rate
        raw_actual_cycle_rate = 0.0
        if db_cycle.cycleDurationProrata.total_seconds() > 0.0:
            raw_actual_cycle_rate = db_cycle.mass.magnitude / db_cycle.cycleDurationProrata.total_seconds()

        self.add_data(uuid,
                      self.OUT_DATA_NORMALISED_RAW,
                      self.OUT_DATA_TYPE_ACTUAL,
                      self.OUT_DATA_SCOPE_CYCLE,
                      db_cycle.processorName,
                      self.OUT_DATA_CATEGORY_RATE,
                      self.OUT_DATA_CATEGORY_RATE,
                      self.OUT_DATA_CATEGORY_RATE,
                      str(raw_actual_cycle_rate),
                      str(db_cycle.cycleDurationProrata.total_seconds()),
                      str(raw_actual_cycle_rate *
                          db_cycle.cycleDurationProrata.total_seconds()),
                      db_state.currentRate[db_cycle.processorOid].value.unit,
                      db_state.currentRate[db_cycle.processorOid].value.unitType)

        # Raw Actual Cycle Duration
        self.add_data(uuid,
                      self.OUT_DATA_NORMALISED_RAW,
                      self.OUT_DATA_TYPE_ACTUAL,
                      self.OUT_DATA_SCOPE_CYCLE,
                      db_cycle.processorName,
                      self.OUT_DATA_CATEGORY_DURATION,
                      self.OUT_DATA_CATEGORY_DURATION,
                      self.OUT_DATA_CATEGORY_DURATION,
                      str(db_cycle.cycleDurationProrata.total_seconds()),
                      str(db_cycle.mass.magnitude),
                      str(db_cycle.mass.magnitude *
                          db_cycle.cycleDurationProrata.total_seconds()),
                      self.OUT_DATA_DURATION_UNIT,
                      self.OUT_DATA_DURATION_UNIT_TYPE)

        # Raw Actual Cycle Continuous
        for cg_key, cg_value in db_cycle.continuousGrades.iteritems():

            self.add_data(uuid,
                          self.OUT_DATA_NORMALISED_RAW,
                          self.OUT_DATA_TYPE_ACTUAL,
                          self.OUT_DATA_SCOPE_CYCLE,
                          db_cycle.processorName,
                          self.OUT_DATA_CATEGORY_CONTINUOUS,
                          cg_value.name,
                          cg_value.oid,
                          str(cg_value.value.magnitude),
                          str(cg_value.weightMagnitude),
                          str(cg_value.weightValueMagnitude),
                          cg_value.value.unit,
                          cg_value.value.unitType)

        # Raw Actual Cycle Discrete
        for dg_key, dg_value in db_cycle.discreteGrades.iteritems():

            # grade value
            for dg_value_key, dg_value_value in dg_value.children.iteritems():

                self.add_data(uuid,
                              self.OUT_DATA_NORMALISED_RAW,
                              self.OUT_DATA_TYPE_ACTUAL,
                              self.OUT_DATA_SCOPE_CYCLE,
                              db_cycle.processorName,
                              self.OUT_DATA_CATEGORY_DISCRETE,
                              dg_value.parent.name +
                              self.OUT_DISCRETE_TOKEN +
                              dg_value_value.name,
                              dg_value.parent.oid +
                              self.OUT_DISCRETE_TOKEN +
                              dg_value_value.name,
                              str(dg_value_value.value.magnitude),
                              str(dg_value_value.weightMagnitude),
                              str(dg_value_value.weightValueMagnitude),
                              dg_value.parent.value.unit,
                              dg_value.parent.value.unitType)

        # Raw Actual Cycle Material
        for mat_key, mat_value in db_cycle.materials.iteritems():

            self.add_data(uuid,
                          self.OUT_DATA_NORMALISED_RAW,
                          self.OUT_DATA_TYPE_ACTUAL,
                          self.OUT_DATA_SCOPE_CYCLE,
                          db_cycle.processorName,
                          self.OUT_DATA_CATEGORY_MATERIAL,
                          mat_value.name,
                          mat_value.oid,
                          str(mat_value.value.magnitude),
                          str(mat_value.weightMagnitude),
                          str(mat_value.weightValueMagnitude),
                          mat_value.value.unit,
                          mat_value.value.unitType)

    def add_data(self,
                 cycle_uuid,
                 text_normalised,
                 text_type,
                 text_scope,
                 text_processor,
                 text_category,
                 text_name,
                 text_oid,
                 text_value,
                 text_weight,
                 text_weight_value,
                 text_unit,
                 text_unit_type):

        data_head_temp = ET.Element(self.OUT_DATA)
        self.dataCycleHead.append(data_head_temp)

        # normalised
        data_normalised = ET.TreeBuilder()

        data_normalised.start(self.OUT_DATA_NORMALISED, {})
        data_normalised.data(text_normalised)
        data_normalised.end(self.OUT_DATA_NORMALISED)
        data_head_temp.append(data_normalised.close())

        # type
        data_type = ET.TreeBuilder()

        data_type.start(self.OUT_DATA_TYPE, {})
        data_type.data(text_type)
        data_type.end(self.OUT_DATA_TYPE)
        data_head_temp.append(data_type.close())

        # scope
        data_scope = ET.TreeBuilder()

        data_scope.start(self.OUT_DATA_SCOPE, {})
        data_scope.data(text_scope)
        data_scope.end(self.OUT_DATA_SCOPE)
        data_head_temp.append(data_scope.close())

        # processor
        data_processor = ET.TreeBuilder()

        data_processor.start(self.OUT_DATA_PROCESSOR, {})
        data_processor.data(text_processor)
        data_processor.end(self.OUT_DATA_PROCESSOR)
        data_head_temp.append(data_processor.close())

        # category
        data_category = ET.TreeBuilder()

        data_category.start(self.OUT_DATA_CATEGORY, {})
        data_category.data(text_category)
        data_category.end(self.OUT_DATA_CATEGORY)
        data_head_temp.append(data_category.close())

        # name
        data_name = ET.TreeBuilder()

        data_name.start(self.OUT_DATA_NAME, {})
        data_name.data(text_name)
        data_name.end(self.OUT_DATA_NAME)
        data_head_temp.append(data_name.close())

        # name type combined
        data_name_type = ET.TreeBuilder()

        data_name_type.start(self.OUT_DATA_NAME_TYPE, {})
        data_name_type.data(text_name + ' ' + text_type)
        data_name_type.end(self.OUT_DATA_NAME_TYPE)
        data_head_temp.append(data_name_type.close())

        # data name type scope
        data_name_type_scope = ET.TreeBuilder()

        data_name_type_scope.start(self.OUT_DATA_NAME_TYPE_SCOPE, {})
        data_name_type_scope.data(text_name + ' ' +
                                  text_type + ' ' +
                                  text_scope)
        data_name_type_scope.end(self.OUT_DATA_NAME_TYPE_SCOPE)
        data_head_temp.append(data_name_type_scope.close())

        # oid
        data_oid = ET.TreeBuilder()

        data_oid.start(self.OUT_DATA_OID, {})
        data_oid.data(text_oid)
        data_oid.end(self.OUT_DATA_OID)
        data_head_temp.append(data_oid.close())

        # value
        data_value = ET.TreeBuilder()

        data_value.start(self.OUT_DATA_VALUE, {})
        data_value.data(text_value)
        data_value.end(self.OUT_DATA_VALUE)
        data_head_temp.append(data_value.close())

        # weight
        data_weight = ET.TreeBuilder()

        data_weight.start(self.OUT_DATA_WEIGHT, {})
        data_weight.data(text_weight)
        data_weight.end(self.OUT_DATA_WEIGHT)
        data_head_temp.append(data_weight.close())

        # weight_value
        data_weight_value = ET.TreeBuilder()

        data_weight_value.start(self.OUT_DATA_WEIGHT_VALUE, {})
        data_weight_value.data(text_weight_value)
        data_weight_value.end(self.OUT_DATA_WEIGHT_VALUE)
        data_head_temp.append(data_weight_value.close())

        # unit
        data_unit = ET.TreeBuilder()

        data_unit.start(self.OUT_DATA_UNIT, {})
        data_unit.data(text_unit)
        data_unit.end(self.OUT_DATA_UNIT)
        data_head_temp.append(data_unit.close())

        # unit_type
        data_unit_type = ET.TreeBuilder()

        data_unit_type.start(self.OUT_DATA_UNIT_TYPE, {})
        data_unit_type.data(text_unit_type)
        data_unit_type.end(self.OUT_DATA_UNIT_TYPE)
        data_head_temp.append(data_unit_type.close())


class TimeRangeConfig:
    LOG_MAX_CONTROL_WINDOW_SIZE = 'maxControlWindowSize'
    LOG_RESET_ON_SHIFT = 'resetOnShift'
    LOG_FALSE = 'false'

    def __init__(self,
                 time_range_XML):

        self.resetOnShift = None

        if time_range_XML.find('.//' +
                               self.LOG_MAX_CONTROL_WINDOW_SIZE).text is None:
            raise ValueError(self.LOG_MAX_CONTROL_WINDOW_SIZE +
                             ' could not be found in iBlend.log')

        self.maxControlWindowSize = dt.timedelta(seconds=int(time_range_XML.find('.//' +
                                                             self.LOG_MAX_CONTROL_WINDOW_SIZE).text))

        if time_range_XML.find('.//' +
                               self.LOG_MAX_CONTROL_WINDOW_SIZE).text is None:

            raise ValueError(self.LOG_RESET_ON_SHIFT +
                             ' could not be found in iBlend.log')

        self.resetOnShift = time_range_XML.find('.//' +
                                                self.LOG_RESET_ON_SHIFT).text != self.LOG_FALSE


def main():
    root = tk.Tk()
    root.withdraw()
    #filePath = askopenfilename()
    #file_path = 'C:/Users/nixont/Box Sync/Cat/Blending to Destination/B2D Check Engine/multipleUpdateRunData.log'
    root_log_active_blends_DTO = None
    root_log_cycle_cache_entry = None
    root_log_shift_start_lookup = None
    root_log_blending_cycle = None
    root_log_blending_cycle_first = None
    root_log_time_range_config_entry = None
    file_dbs = None
    current_shift = None
    file_time_config = None
    LOG_SHIFT_START = 'shiftStart'
    LOG_PROCESSOR = 'processor'
    LOG_PROCESSOR_OID = 'oid'
    LOG_DESTINATION_BLEND_CYCLES = 'destinationBlendCycles'
    LOG_BLENDING_CYCLE_CACHE = 'blendingCycleCache'
    LOG_VALUE = 'value'
    LOG_ENTRY = 'entry'
    LOG_KEY = 'key'
    LOG_CYCLE_END_TIME = 'endTime'
    LOG_SHIFT_START_TIME = 'shiftStartTime'
    LOG_TIMESTAMP = 'timestamp'
    LOG_CALCULATION_TIME = 'calculationTime'
    LOG_CYCLE_UUID = 'uuid'
    LOG_CYCLE_CREATION_TIME = 'cycleCreationTime'
    LOG_DESTINATION_BLEND_OID = 'destinationBlendOid'
    LOG_DESTINATION_BLEND = 'destinationBlend'
    LOG_BLEND_OID = 'blendOID'
    LOG_OID_LOWER = 'oid'
    OUT_REPORT_ROOT = 'DestinationBlendReportingCycles'
    cycle_count = 0
    OUT_REPORT_CYCLE_DATA_ROOT = 'data'
    process_reporting = True

    parser = argparse.ArgumentParser(description="B2D Replay Check Engine",
                                     epilog="Can be used manually and as part of the B2D Replay test harness")
    parser.add_argument('-i', '--i-input', required=True)
    parser.add_argument('-o', '--o-output', required=True)
    parser.add_argument('-c', '--c-cycles', required=False)
    parser.add_argument('-d', '--d-data', required=False)
    parser.add_argument('values', nargs='*')
    args = parser.parse_args()

    file_path = args.i_input

    dbsuDTO_XML_file_path = args.o_output

    if args.c_cycles is not None:
        db_report_cycle_XML_file_path = args.c_cycles
    else:
        process_reporting = False

    if args.d_data is not None:
        db_report_cycle_data_XML_file_path = args.d_data
    else:
        process_reporting = False

    # root and header tag
    db_report_cycle_root = ET.Element(OUT_REPORT_ROOT)
    db_report_cycle_data_root = ET.Element(OUT_REPORT_ROOT)

    with open(file_path, 'r') as f:
        content = f.readlines()

    open_log_state = LogState(file_path)

    for iBlendLine in content:
        line_root = ET.fromstring(iBlendLine)

        for child in line_root:
            found = False
            looking_for = ''
            for expected in open_log_state.expected:
                if child.tag == expected:
                    found = True
                    break
                else:
                    if looking_for == '':
                        looking_for = expected
                    else:
                        looking_for += ', or ' + \
                                       expected
            if not found:
                raise ValueError('Expected ' +
                                 looking_for +
                                 ' but found ' +
                                 child.tag +
                                 ' in the iBlend.log')

        if line_root.find(DestinationBlendState.LOG_ENGINE_START_ENTRY) is not None:
            open_log_state.next_state(DestinationBlendState.LOG_ENGINE_START_ENTRY)

        elif line_root.find(DestinationBlendState.LOG_ACTIVE_BLENDS_DTO) is not None:
            root_log_active_blends_DTO = copy.deepcopy(line_root)
            file_dbs = DestinationBlendInternal(file_path,
                                                root_log_active_blends_DTO)

            # set the last batch start date before the processing of the cache begins
            for db_cache_key, db_cache_value in file_dbs.db_caches.iteritems():
                if file_dbs.db_states[db_cache_key].control.method == ControlRecord.BATCH_MASS or \
                                file_dbs.db_states[db_cache_key].control.method == ControlRecord.BATCH_WINDOW:
                    db_cache_value.set_cache_batch_start_time(file_dbs.db_states[db_cache_key].lastBatchStartDate)

            open_log_state.next_state(DestinationBlendState.LOG_ACTIVE_BLENDS_DTO)

        elif line_root.find(DestinationBlendState.LOG_CYCLE_CACHE_ENTRY) is not None:
            if root_log_cycle_cache_entry is None:
                root_log_cycle_cache_entry = copy.deepcopy(line_root)
            else:
                raise ValueError(DestinationBlendState.LOG_CYCLE_CACHE_ENTRY +
                                 ' has been encountered more than once in the iBlend.log')

            # cache processing is done in the blend cycle state
            open_log_state.next_state(DestinationBlendState.LOG_CYCLE_CACHE_ENTRY)

        elif line_root.find(DestinationBlendState.LOG_TIME_RANGE_CONFIG_ENTRY) is not None:
            if root_log_time_range_config_entry is None:
                root_log_time_range_config_entry = copy.deepcopy(line_root)
            else:
                raise ValueError(DestinationBlendState.LOG_TIME_RANGE_CONFIG_ENTRY +
                                 ' has been encountered more than once in the iBlend.log')

            file_time_config = TimeRangeConfig(root_log_time_range_config_entry)

            for db_cache_key, db_cache_value in file_dbs.db_caches.iteritems():
                db_cache_value.set_max_window(file_time_config.maxControlWindowSize)

            for db_state_key, db_state_value in file_dbs.db_states.iteritems():
                db_state_value.set_reset_on_shift_change(file_time_config.resetOnShift)

            open_log_state.next_state(DestinationBlendState.LOG_TIME_RANGE_CONFIG_ENTRY)

        elif line_root.find(DestinationBlendState.LOG_DESTINATION_BLEND) is not None:

            root_log_destination_blend = copy.deepcopy(line_root)

            file_dbs.add_blend(root_log_destination_blend.find(LOG_DESTINATION_BLEND).find(LOG_OID_LOWER).text,
                               root_log_destination_blend.find(LOG_DESTINATION_BLEND))

            open_log_state.next_state(DestinationBlendState.LOG_DESTINATION_BLEND)

        elif line_root.find(DestinationBlendState.LOG_DESTINATION_BLEND_REMOVAL_ENTRY) is not None:

            root_log_destination_blend_removal_entry = copy.deepcopy(line_root)

            for db_removal_oid in root_log_destination_blend_removal_entry.findall('.//' +
                                                                                   LOG_DESTINATION_BLEND_OID):

                file_dbs.remove_blend(db_removal_oid.text)

            open_log_state.next_state(DestinationBlendState.LOG_DESTINATION_BLEND_REMOVAL_ENTRY)

        elif line_root.find(DestinationBlendState.LOG_BLENDING_CYCLE) is not None:
            root_log_blending_cycle = copy.deepcopy(line_root)

            open_log_state.next_state(DestinationBlendState.LOG_BLENDING_CYCLE)

        elif line_root.find(DestinationBlendState.LOG_BLEND_CALCULATION_ENTRY) is not None:
            root_log_blend_calculation_entry = copy.deepcopy(line_root)

            root_log_shift_start_lookup = root_log_blend_calculation_entry.find('.//' +
                                                                                LOG_SHIFT_START)

            cycle_uuid = root_log_blending_cycle.find('.//' +
                                                      LOG_CYCLE_UUID).text

            if current_shift is None:

                current_shift = root_log_shift_start_lookup.text
            else:
                if current_shift != root_log_shift_start_lookup.text:

                    shift_change_time = MineStarToInternal.to_datetime_from_timestamp_text(
                        root_log_shift_start_lookup.text)
                    update_time = MineStarToInternal.to_datetime_from_timestamp_text(
                        root_log_blend_calculation_entry.find('.//' +
                                                              LOG_CALCULATION_TIME).text)

                    for db in file_dbs.db_states:
                        file_dbs.db_states[db].shift_change(shift_change_time,
                                                            shift_change_time,
                                                            update_time)

                        # handle the reset of the cache
                        if DestinationBlendState.resetOnShiftChange:
                            file_dbs.db_caches[db].shift_control_reset(shift_change_time)

                        file_dbs.db_caches[db].shift_reset(shift_change_time)

                    current_shift = root_log_shift_start_lookup.text

            if cycle_count == 0:
                cycle_count += 1

                # clear the destination blend status DTO XML file upon the first cycle
                open(dbsuDTO_XML_file_path, 'w').close()

                if process_reporting:
                    open(db_report_cycle_XML_file_path, 'w').close()
                    open(db_report_cycle_data_XML_file_path, 'w').close()

                # set the shift time as per the first shift lookup time
                for db_key, db_value in file_dbs.db_states.iteritems():
                    shift_start_time = MineStarToInternal.to_datetime_from_timestamp_text(current_shift)
                    file_dbs.db_states[db_key].set_shift_start_time(shift_start_time)

                # Code to process cache as cycles
                # This includes calling the shift change for the blend at the appropriate point in time
                for db_cache_XML in root_log_cycle_cache_entry.findall('.//' +
                                                                       LOG_BLENDING_CYCLE_CACHE):

                    shift_cleared = False

                    db_cache_cycles_XML = db_cache_XML.find('.//' +
                                                            LOG_DESTINATION_BLEND_CYCLES)
                    data = []
                    for elem in db_cache_cycles_XML:
                        key = elem.findtext('.//' +
                                            LOG_CYCLE_CREATION_TIME)
                        data.append((key, elem))

                    data.sort()

                    # insert the last item from each tuple
                    db_cache_cycles_XML[:] = [item[-1] for item in data]

                    for db_cycle_XML in db_cache_cycles_XML.findall(LOG_ENTRY):

                        cycle_update_time = MineStarToInternal.to_datetime_from_timestamp_text(
                            root_log_blending_cycle.find('.//' +
                                                         LOG_CYCLE_END_TIME).text)

                        for db_key, db_value in file_dbs.db_states.iteritems():

                            # code to update blend cache and
                            processor = db_cycle_XML.find(LOG_VALUE).find('.//' +
                                                                          LOG_PROCESSOR).find(LOG_PROCESSOR_OID)
                            if processor is not None:

                                for db_processor in db_value.processors:

                                    if processor.text == db_processor:

                                        cycle_end_time = MineStarToInternal.to_datetime_from_timestamp_text(
                                            db_cycle_XML.find(".//" +
                                                              LOG_CYCLE_END_TIME).text)

                                        # reset the shift data when required
                                        if not shift_cleared:

                                            if cycle_end_time > file_dbs.db_states[db_key].shiftStartTime:

                                                shift_change_time = MineStarToInternal.to_datetime_from_timestamp_text(
                                                    root_log_shift_start_lookup.text)

                                                for db in file_dbs.db_states:
                                                    file_dbs.db_states[db].shift_change(shift_change_time,
                                                                                        shift_change_time,
                                                                                        cycle_update_time)

                                                    # handle the reset of the cache
                                                    if DestinationBlendState.resetOnShiftChange:
                                                        file_dbs.db_caches[db].shift_control_reset(shift_change_time)

                                                    file_dbs.db_caches[db].shift_reset(shift_change_time)

                                                shift_cleared = True

                                        file_dbs.add_cycle_from_cache(db_cycle_XML.find(LOG_VALUE),
                                                                      db_key,
                                                                      cycle_update_time)

                                        break

                            else:
                                raise ValueError(
                                    'No processor was found in an active destination blend for the blend cycle' +
                                    ' included in the blend cache')

            cycle_update_time = MineStarToInternal.to_datetime_from_timestamp_text(
                root_log_blend_calculation_entry.find('.//' +
                                                      LOG_CALCULATION_TIME).text)

            for db_key, db_value in file_dbs.db_states.iteritems():

                # code to update blend cache and
                processor = root_log_blending_cycle.find('.//' +
                                                         LOG_PROCESSOR).find(LOG_PROCESSOR_OID)
                if processor is not None:

                    for db_processor in db_value.processors:

                        if processor.text == db_processor:

                            file_dbs.add_cycle(root_log_blending_cycle,
                                               db_key,
                                               cycle_update_time)

                            dbsuDTO = DestinationBlendStatusUpdateDTO(db_value,
                                                                      cycle_uuid)

                            with open(dbsuDTO_XML_file_path, "a") as dbsuDTO_XML_file:
                                dbsuDTO_XML_file.write(ET.tostring(dbsuDTO.dbuDTORoot) +
                                '\n')

                            db_cycle = \
                                next((cy for cy in file_dbs.db_caches[db_key].dbCycles if cy.uuid == cycle_uuid), None)

                            if process_reporting:
                                db_report = DestinationBlendReporting(db_value,
                                                                      cycle_uuid,
                                                                      db_cycle)

                                db_report_cycle_root.append(db_report.cycleHead)
                                db_report_cycle_data_root.append(db_report.dataCycleHead)

                            break

                else:
                    raise ValueError('No processor was found in an active destination blend for the blend cycle')

            open_log_state.next_state(DestinationBlendState.LOG_BLEND_CALCULATION_ENTRY)

        else:
            raise ValueError('Unidentified line type was found in the iBlend.log')

    if process_reporting:
        with open(db_report_cycle_XML_file_path, "a") as db_report_cycle_XML_file:
            # db_report_cycle_XML_file.write(ET.tostring(db_report_cycle_root))
            db_report_cycle_tree = ET.ElementTree(db_report_cycle_root)
            db_report_cycle_tree.write(db_report_cycle_XML_file)

        with open(db_report_cycle_data_XML_file_path, "a") as db_report_cycle_data_XML_file:
            # db_report_cycle_data_XML_file.write(ET.tostring(db_report_cycle_data_root))
            db_report_cycle_data_tree = ET.ElementTree(db_report_cycle_data_root)
            db_report_cycle_data_tree.write(db_report_cycle_data_XML_file)

if __name__ == '__main__':
    main()
