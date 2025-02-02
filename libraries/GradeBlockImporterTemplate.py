from minestar.mine.service.material.imports import CSVGradeBlockImporter
import jarray

class GradeBlockImporterTemplate(CSVGradeBlockImporter):
    def __init__(self, name, context):
        CSVGradeBlockImporter.__init__(self, name, context)

    # gbd is of type GradeBlockData
    def preprocessGradeBlockData(self, gbd):
        # insert code here
        return gbd

    # gbd is of type GradeBlockData
    # return a map of name,value pairs corresponding to GradeBlock entity properties
    def getGradeBlockProperties(self, gbd):
        # insert code here
        return CSVGradeBlockImporter.getGradeBlockProperties(self, gbd)
