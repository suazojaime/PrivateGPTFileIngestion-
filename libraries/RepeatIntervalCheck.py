from com.mincom.util.unit import Quantity
from com.mincom.util.unit import UnitHelper
from com.mincom.util.unit import UnitType

passFlag = 1
if formData[0].getValue() != None :
 value = Quantity(formData[0].getValue(), UnitHelper.SECOND, UnitType.DURATION )
 if value.isLessThanOrEqualTo(0.0):
    passFlag = 0
# 1-success 0-fails
result.setPassed(passFlag)
