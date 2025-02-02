import java.util.Calendar

startDate = formData[0].getValue()
now = java.util.Calendar.getInstance().getTime()
passFlag = 1
if startDate != None and now.after(startDate):
    passFlag = 0
# 1-success 0-fails
result.setPassed(passFlag)
