startDate = formData[0].getValue()
endDate = formData[1].getValue()

passFlag = 1
if startDate != None and endDate != None and startDate.after(endDate):
    passFlag = 0
#
result.setPassed(passFlag)
