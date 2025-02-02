import sys, os, os.path, whrandom

COPY_COMMAND = "copy %s %s"

files = os.listdir(os.getcwd() + "\\backgrounds")
jpgs = []
for file in files:
    if file[-4:] == ".jpg":
        jpgs.append(file)
if len(jpgs) > 0:
    filename = whrandom.choice(jpgs)
    cp = COPY_COMMAND % ("backgrounds\\" + filename, "minestar2.jpg")
    print cp
    os.system(cp)

