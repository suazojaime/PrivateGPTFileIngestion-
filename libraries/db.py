# Jython database functionality

from com.mincom.env.ecf.persistence import ECFDataStoreManager
from com.mincom.env.base.persistence import SqlStatement

class Table:
    def __init__(self, table):
        self.data = []
        self.columns = []
        for rowNum in range(table.size()):
            rowMap = table.getRowAsMap(rowNum)
            if len(self.columns) == 0:
                cols = []
                it = rowMap.keySet().iterator()
                while it.hasNext():
                    cols.append(it.next())
                cols.sort()
                self.columns = cols
            row = []
            for col in self.columns:
                row.append(table.getValue(rowNum, col))
            self.data.append(row)

    def __str__(self):
        return `(self.columns, self.data)`

    def getColumn(self, name):
        if name not in self.columns:
            return None
        i = self.columns.index(name)
        return [ row[i] for row in self.data ]

    def getValue(self, row, columnName):
        if columnName not in self.columns:
            return None
        i = self.columns.index(columnName)
        return self.data[row][i]

class DataStore:
    def __init__(self, ds):
        self.ds = ds

    def query(self, stmt):
        table = self.ds.query(SqlStatement(stmt), 0)
        return Table(table)

    def getOIDsForClass(self, fullClassName):
        table = self.query("select OID from ECF_ENTITY where ECF_CLASS_ID = 'XA%s'" % fullClassName)
        if table is None:
            return None
        return table.getColumn('OID')

class ECFMetadata:
    def __init__(self, datastore):
        ecfClass = datastore.query("select * from ecf_class")
        tableDef = datastore.query("select * from table_def")
        fullNames = ecfClass.getColumn("FULL_NAME")
        names = ecfClass.getColumn("NAME")
        tableIds = ecfClass.getColumn("TABLE_ID")
        self.namesToFullNames = {}
        self.classesToTables = {}
        self.ecfClasses = names[:]
        self.ecfClasses.sort()
        tableIdsToNames = {}
        for i in range(len(tableDef.data)):
            tableIdsToNames[tableDef.getValue(i, 'TABLE_ID')] = tableDef.getValue(i, 'NAME')
        for i in range(len(names)):
            self.namesToFullNames[names[i]] = fullNames[i]
            tableId = tableIds[i]
            self.classesToTables[fullNames[i]] = tableIdsToNames.get(tableId)

    def getFullClassName(self, name):
        return self.namesToFullNames.get(name)

    def getTableForClass(self, fullClassName):
        return self.classesToTables.get(fullClassName)

def getDataStore(name):
    ds = ECFDataStoreManager.getEcfByLogicalName(name)
    if ds is None:
        raise "No such data store as '%s'" % name
    return DataStore(ds)
