lastValue = None
allPass = 1

for field in formData:
	value = field.getValue()
	if lastValue is None:
		lastValue = value
	else:
		if value == lastValue:
			pass
		else:
			allPass = 0
result.setPassed(allPass)
