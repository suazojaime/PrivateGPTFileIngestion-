# support for kpiSummaries expressions
from com.mincom.base.resource import ResTools
from com.mincom.util.unit import Quantity, QuantityHelper, QuantityUtil, UnitFactory, UnitHelper, UnitType, Units
from java.lang import Math, Number, Double
from minestar.mine.service.material.util import MaterialUtil
from minestar.pitlink.domain.machine import Machine, MachineCapability, Truck, TruckClass
from minestar.pitlink.domain.machine.util import MachineUtil
from minestar.pitlink.service.fleet import MachineSmuService
from minestar.platform.bootstrap import OptionSets

useK1Factor = ResTools.resolveBoolean(OptionSets.getOptionSet("TKPH Parameters"), "useK1Factor")
upperSpeedLimit = UnitHelper.resolveQuantity(OptionSets.getOptionSet("TKPH Parameters"), "upperSpeedLimit",
                                             UnitType.SPEED, UnitHelper.KPH, 16.67)

DURATION_UNIT = UnitFactory.getUnitByType(UnitType.DURATION)
LENGTH_UNIT = UnitFactory.getUnitByType(UnitType.LENGTH)
MASS_DISTANCE_UNIT = UnitFactory.getUnitByType(UnitType.MASS_DIST)
MASS_UNIT = UnitFactory.getUnitByType(UnitType.MASS)
MASS_SPEED_UNIT = UnitFactory.getUnitByType(UnitType.MASS_SPEED)


def isVimsWirelessEnabled(machine):
    return machine is not None and machine.isVimsWirelessEnabled()


def isVimsCapable(machine):
    return machine is not None and machine.hasCapability(MachineCapability.VIMS_CAPABLE)


# return the TKPH Qm factor for the given truck class
def tkphQmForTruckClass(truckClass):
    if truckClass is None:
        return 0.0

    if (not isinstance(truckClass, TruckClass)
            or truckClass.getNominalPayload() is None
            or truckClass.getGrossVehicleWeight() is None
            or truckClass.getFrontDistributionLoaded() is None
            or truckClass.getFrontDistributionEmpty() is None
            or truckClass.getRearDistributionLoaded() is None
            or truckClass.getRearDistributionEmpty() is None):
        return 0.0
    apl = convertToUserPreferredUnits(truckClass.getNominalPayload(), UnitType.MASS)
    gvw = convertToUserPreferredUnits(truckClass.getGrossVehicleWeight(), UnitType.MASS)
    uvw = gvw - apl
    lfd = truckClass.getFrontDistributionLoaded().doubleValue() / 100
    ufd = truckClass.getFrontDistributionEmpty().doubleValue() / 100
    lrd = truckClass.getRearDistributionLoaded().doubleValue() / 100
    urd = truckClass.getRearDistributionEmpty().doubleValue() / 100
    tf = 2
    tr = 4

    qf = (gvw * lfd + uvw * ufd) / (2 * tf)
    qr = (gvw * lrd + uvw * urd) / (2 * tr)
    return Math.max(qf, qr)


def tkphQm(truckOrTruckClass):
    if truckOrTruckClass is None:
        return 0.0

    if isinstance(truckOrTruckClass, TruckClass):
        return tkphQmForTruckClass(truckOrTruckClass)

    # if option is set to use truck class values than
    # ignore truck settings and use truck class settings
    if (isinstance(truckOrTruckClass, Truck)) and truckOrTruckClass.isUseTruckClassPayload():
        return tkphQmForTruckClass(truckOrTruckClass.getMachineClass())

    truck = truckOrTruckClass
    if (not isinstance(truckOrTruckClass, Truck)
            or truck.nominalPayload is None
            or truck.frontDistributionLoaded is None
            or truck.frontDistributionEmpty is None
            or truck.rearDistributionLoaded is None
            or truck.rearDistributionEmpty is None):
        return 0.0
    apl = convertToUserPreferredUnits(truck.nominalPayload, UnitType.MASS)
    gvw = convertToUserPreferredUnits(truck.machineClass.grossVehicleWeight, UnitType.MASS)
    uvw = gvw - apl
    lfd = truck.frontDistributionLoaded.doubleValue() / 100
    ufd = truck.frontDistributionEmpty.doubleValue() / 100
    lrd = truck.rearDistributionLoaded.doubleValue() / 100
    urd = truck.rearDistributionEmpty.doubleValue() / 100
    tf = 2
    tr = 4

    qf = (gvw * lfd + uvw * ufd) / (2 * tf)
    qr = (gvw * lrd + uvw * urd) / (2 * tr)
    return Math.max(qf, qr)


# return the TKPH K1 factor for the given distance (a Quantity)
def tkphK1(distanceQuantity):
    values = [1, 1, 1, 1, 1, 1, 1.04, 1.06, 1.09, 1.1, 1.12, 1.13, 1.14, 1.15, 1.16, 1.16, 1.17, 1.17, 1.18, 1.18, 1.19,
              1.19, 1.19, 1.2, 1.2, 1.2, 1.2, 1.21, 1.21, 1.21, 1.21, 1.21, 1.21, 1.22, 1.22, 1.22, 1.22, 1.22, 1.22,
              1.22, 1.22, 1.23]
    # convert distance to km - note that int() = floor()
    km = int(distanceQuantity.convertTo(Units.KILOMETRE).doubleValue())
    if km < 0:
        return 0
    elif km < len(values):
        return values[km]
    else:
        return values[-1]


# return the tkph value, given the tkphQm, cycle length and cycle time, all in user-preferred units
def tkph(tkphQmValue, cycleLength, cycleDuration):
    if not isinstance(tkphQmValue, (int, float)) \
            or QuantityUtil.isZero(cycleLength) or Double.isNaN(cycleLength) \
            or QuantityUtil.isZero(cycleDuration) or Double.isNaN(cycleDuration):
        return Quantity.createQuantity(0.0, MASS_SPEED_UNIT, UnitType.MASS_SPEED)

    tkphQmQuantity = Quantity.createQuantity(tkphQmValue, MASS_UNIT, UnitType.MASS)
    cycleLengthQuantity = Quantity.createQuantity(cycleLength, LENGTH_UNIT, UnitType.LENGTH)
    cycleDurationQuantity = Quantity.createQuantity(cycleDuration, DURATION_UNIT, UnitType.DURATION)
    return convertToUserPreferredUnits(tkphQmQuantity.multiply(cycleLengthQuantity).divide(cycleDurationQuantity),
                                       UnitType.MASS_SPEED) * tkphK1(cycleLengthQuantity)


# return payload * loaded EFH + vehicle weight * total EFH
def tkphMassDistance(payload, loadedEfhDistance, vehicleWeight, emptyEfhDistance):
    if vehicleWeight is None or vehicleWeight.doubleValue == 0.0:
        return 0.0
    payloadQuantity = Quantity.createQuantity(payload, MASS_UNIT, UnitType.MASS)
    loadedEfhDistanceQuantity = Quantity.createQuantity(loadedEfhDistance, LENGTH_UNIT, UnitType.LENGTH)
    emptyEfhDistanceQuantity = Quantity.createQuantity(emptyEfhDistance, LENGTH_UNIT, UnitType.LENGTH)
    result = payloadQuantity.multiply(loadedEfhDistanceQuantity).add(
        vehicleWeight.multiply(loadedEfhDistanceQuantity.add(emptyEfhDistanceQuantity)))
    return result


# modified tkph algorithm
def calcTkphMassDistanceFront(truckClass, reportingPayload, distanceTravelEmpty, distanceTravelLoaded,
                              vimsDistanceTravelEmpty, vimsDistanceTravelLoaded, cycleDuration):
    if truckClass.objectType.endswith('TruckClass'):
        fdl = truckClass.frontDistributionLoaded.convertTo(Units.PERCENT).doubleValue() / 100.0
        fde = truckClass.frontDistributionEmpty.convertTo(Units.PERCENT).doubleValue() / 100.0
        tf = 2.0
        return calcTkphMassDistance(truckClass, fdl, fde, tf, reportingPayload, distanceTravelEmpty,
                                    distanceTravelLoaded, vimsDistanceTravelEmpty, vimsDistanceTravelLoaded,
                                    cycleDuration)
    return 0.0


def calcTkphMassDistanceRear(truckClass, reportingPayload, distanceTravelEmpty, distanceTravelLoaded,
                             vimsDistanceTravelEmpty, vimsDistanceTravelLoaded, cycleDuration):
    if truckClass.objectType.endswith('TruckClass'):
        rdl = truckClass.rearDistributionLoaded.convertTo(Units.PERCENT).doubleValue() / 100.
        rde = truckClass.rearDistributionEmpty.convertTo(Units.PERCENT).doubleValue() / 100.
        tr = 4.0
        return calcTkphMassDistance(truckClass, rdl, rde, tr, reportingPayload, distanceTravelEmpty,
                                    distanceTravelLoaded, vimsDistanceTravelEmpty, vimsDistanceTravelLoaded,
                                    cycleDuration)
    return 0.0


def calcTkphMassDistance(truckClass, dl, de, nt, reportingPayload, distanceTravelEmpty, distanceTravelLoaded,
                         vimsDistanceTravelEmpty, vimsDistanceTravelLoaded, cycleDuration):
    global useK1Factor
    if truckClass.objectType.endswith('TruckClass'):
        gvw = truckClass.grossVehicleWeight
        npl = truckClass.nominalPayload
        vwe = gvw - npl
        vwl = vwe + Quantity.createQuantity(reportingPayload, MASS_UNIT, UnitType.MASS)
        dtl = validatedDistance(distanceTravelLoaded, vimsDistanceTravelLoaded, distanceTravelEmpty,
                                vimsDistanceTravelEmpty, cycleDuration)
        dte = validatedDistance(distanceTravelEmpty, vimsDistanceTravelEmpty, distanceTravelLoaded,
                                vimsDistanceTravelLoaded, cycleDuration)
        if useK1Factor != 0:
            k1 = tkphK1(dtl + dte)
        else:
            k1 = 1
        result = ((vwe * de * dte + vwl * dl * dtl) * k1) / nt
        return result.convertTo(MASS_DISTANCE_UNIT, UnitType.MASS_DIST)
    return 0.0


def validatedDistance(distanceTravelx, vimsDistanceTravelx, distanceTravely, vimsDistanceTravely, cycleDuration):
    global upperSpeedLimit
    maxDistanceTravelx = Math.max(distanceTravelx, vimsDistanceTravelx)
    maxDistanceTravely = Math.max(distanceTravely, vimsDistanceTravely)
    distance = maxDistanceTravelx + maxDistanceTravely
    result = convertDisplayToQuantity(maxDistanceTravelx, UnitType.LENGTH)
    if cycleDuration > 0:
        cycleDurationQuantity = convertDisplayToQuantity(cycleDuration, UnitType.DURATION)
        speed = convertDisplayToQuantity(distance, UnitType.LENGTH) / cycleDurationQuantity
        if speed.isGreaterThan(upperSpeedLimit):
            result = upperSpeedLimit * cycleDurationQuantity / 2
    return result


# convert a value in the user-preferred(aka display) units to the given unit, given the unit type
def convertDisplayToGivenUnit(value, unitName, unitType):
    return Quantity.createQuantity(value, UnitFactory.getUnitByType(unitType), unitType) \
        .convertTo(UnitFactory.getUnitInstance(unitName), unitType).doubleValue()


# convert a value in the user-preferred(aka display) units to a Quantity of the given unit type
def convertDisplayToQuantity(value, unitType):
    return Quantity.createQuantity(value, UnitFactory.getUnitByType(unitType), unitType)


# convert a Quantity to the user-preferred(aka display) units and return a double
def convertToUserPreferredUnits(quantity, unitType):
    return quantity.convertTo(UnitFactory.getUnitByType(unitType), unitType).doubleValue()


def findGradeBlock(gradeBlockObj):
    """Return the GradeBlock that corresponds to the gradeBlockObj,
       which may be any of GradeBlock, GradeBlockReference or Long (OID)"""
    if gradeBlockObj is None:
        return None
    if isinstance(gradeBlockObj, Number):
        return MaterialUtil.findGradeBlockByOid(gradeBlockObj.longValue)
    else:  # Assume GradeBlock or GradeBlockReference
        return MaterialUtil.findGradeBlockByOid(gradeBlockObj.OID)


def findMaterial(materialObj):
    """Return the Material that corresponds to the materialObj,
       which may be any of Material, MaterialReference or Long (OID)"""
    if materialObj is None:
        return None
    if isinstance(materialObj, Number):
        return MaterialUtil.findMaterialByOid(materialObj.longValue)
    else:  # Assume Material or MaterialReference
        return MaterialUtil.findMaterialByOid(materialObj.OID)


def findMaterialGroupForMaterial(materialObj, level):
    """Return the MaterialGroup  for the given material and level"""

    material = findMaterial(materialObj)
    if material is None:
        return None

    from minestar.mine.service.material.util import MaterialUtil

    return MaterialUtil.findMaterialGroupForMaterial(material.getRef(), level)


def findMaterialGroupNameForMaterial(materialObj, level):
    """Return the MaterialGroup name for the given material and level"""

    materialGroup = findMaterialGroupForMaterial(materialObj, level)
    if materialGroup is None:
        return "unknown"

    return materialGroup.getName()


# return as a double the interpolated smu for a machine and a time
def lookupSmu(machine, time):
    if machine is None:
        return QuantityHelper.ZERO_SECONDS_SMU
    if not isinstance(machine, Machine):
        raise TypeError("Not a machine %s" % type(machine))

    predictedSmu = MachineSmuService.getInstance().predictSmu(machine.getRef(), time)
    if predictedSmu is None:
        predictedSmu = QuantityHelper.ZERO_SECONDS_SMU
    return convertToUserPreferredUnits(predictedSmu, UnitType.DURATION)


# return as a double the interpolated smu duration for a machine and a start and end time
def calcSmuDuration(machine, startTime, endTime):
    if machine is None:
        return QuantityHelper.ZERO_SECONDS_DURATION
    if not isinstance(machine, Machine):
        raise TypeError("Not a machine %s" % type(machine))

    diffSmu = MachineSmuService.getInstance().predictSmuDuration(machine.getRef(), startTime, endTime)
    return convertToUserPreferredUnits(diffSmu, UnitType.DURATION)


def fleetNames(machine):
    if machine is None:
        return ""
    if not isinstance(machine, Machine):
        raise TypeError("Not a machine %s" % type(machine))
    return MachineUtil.fleetNames(machine.getRef())
