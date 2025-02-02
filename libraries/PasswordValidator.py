allPass = 1

for field in formData:
	password = field.getValue()
	if password is None or len(password) < 8:
		allPass = 0

result.setPassed(allPass)
