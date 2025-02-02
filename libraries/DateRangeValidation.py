import java.util.Calendar
startDate = formData[0].getValue()
endDate = formData[1].getValue()

passFlag = 0
if endDate is None:
    passFlag = 1

if endDate != None:
    if startDate is None:
        startDate = java.util.Calendar.getInstance().getTime()
    if endDate.after(startDate):
        passFlag = 1
# 1-success 0-fails
result.setPassed(passFlag)
