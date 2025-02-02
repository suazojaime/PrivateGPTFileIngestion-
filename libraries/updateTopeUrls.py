# select MACHINE.NAME, PROP_VAL_STRING_DIM_1.VAL from PROP_VAL_STRING_DIM_1, MACHINE where PROP_VAL_STRING_DIM_1.ID =
# 'Assignment' and MACHINE.MACHINE_OID = PROP_VAL_STRING_DIM_1.OID;
 
import sys
import minestar

logger = minestar.initApp()

UPDATE = "update PROP_VAL_STRING_DIM_1 set VAL = '%s' where ID = 'Assignment' and OID = (select MACHINE_OID from MACHINE where NAME = '%s');\n"

args = sys.argv[1:]
inputFile = args[0]
outputFile = args[1]
out = file(outputFile, "w")
for line in file(inputFile):
    if line[-1] == "\n":
        line = line[:-1]
    fields = line.split()
    if len(fields) != 3:
        continue
    url = "tmac://%s:%s" % (fields[1], fields[2])
    out.write(UPDATE % (url, fields[0]))
