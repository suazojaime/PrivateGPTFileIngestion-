#  Copyright (c) 2023 Caterpillar

import datetime

import ConfigurationFileIO
import databaseDifferentiator
import minestar
import mstarpaths

logger = minestar.initApp()
# Upper limit to set for either deleting or archiving of records.
UPPER_LIMIT = int(mstarpaths.interpretVar("_ADMINDATA_BATCHSIZE"))
if (UPPER_LIMIT > 100000):
    UPPER_LIMIT = 100000

dbobject = databaseDifferentiator.returndbObject()
dbPrefix = mstarpaths.interpretVar("_DBPREFIX")

DBDATAMAN_DELETE_GISEDGE_DATA = """DATASTORE=%s CLASS=%s RETAIN=%d LIMIT=%d;"""
DBDATAMAN_ARCHIVE_GISEDGE_DATA = """DATASTORE=%s CLASS=%s RETAIN=%d LIMIT=%d;"""

DBDATAMAN_DELETE_GIS_OBSTACLE = """DATASTORE=%s CLASS=%s RETAIN=%d LIMIT=%d;"""
DBDATAMAN_ARCHIVE_GIS_OBSTACLE = """DATASTORE=%s CLASS=%s RETAIN=%d LIMIT=%d;"""

if dbobject.getDBString() == "Oracle":
    DBDATAMAN_DELETE_ALARM = """CLASS=%s OPERATION=Delete WHERE=\"END_TIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_ALARM = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"END_TIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_CYCLE = """CLASS=%s OPERATION=Delete WHERE=\"ENDTIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_CYCLE = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"ENDTIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_EVENT = """CLASS=%s OPERATION=Delete WHERE=\"MACHINE_OID != 0 and TIMESTAMP_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_EVENT = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"MACHINE_OID != 0 and TIMESTAMP_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_EVENT_LOG = """CLASS=HealthLog OPERATION=Delete WHERE=\"LOG_CATEGORY = 'HealthEventSummary' AND ENDTIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_EVENT_LOG = """CLASS=HealthLog OPERATION=WriteThenDelete WHERE=\"LOG_CATEGORY = 'HealthEventSummary' AND ENDTIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_PRODUCTION_EVENT_LOG = """CLASS=HealthLog OPERATION=Delete WHERE=\"(LOG_CATEGORY = 'TruckPayloadEvent' OR LOG_CATEGORY = 'LoaderPayloadEvent' OR LOG_CATEGORY = 'PleLoaderPayLoadEvent') AND ENDTIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_PRODUCTION_EVENT_LOG = """CLASS=HealthLog OPERATION=WriteThenDelete WHERE=\"(LOG_CATEGORY = 'TruckPayloadEvent' OR LOG_CATEGORY = 'LoaderPayloadEvent' OR LOG_CATEGORY = 'PleLoaderPayLoadEvent') AND ENDTIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_OFFICEMESSAGE = """CLASS=%s OPERATION=Delete WHERE=\"TOTIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_OFFICEMESSAGE = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"TOTIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_SCHEDULED_BREAK = """CLASS=%s OPERATION=Delete WHERE=\"BREAKTIME_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_SCHEDULED_BREAK = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"BREAKTIME_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_SHIFT_CHANGE = """CLASS=%s OPERATION=Delete WHERE=\"SHIFTDATE_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_SHIFT_CHANGE = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"SHIFTDATE_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_GWMDUPLICATES = """CLASS=%s OPERATION=Delete WHERE=\"SHIFT_START_TIME_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_GWMDUPLICATES = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"SHIFT_START_TIME_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_SYSTEM_RESTART_INFO = """CLASS=%s OPERATION=Delete WHERE=\"JOBEXECUTIONTIME_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_SYSTEM_RESTART_INFO = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"JOBEXECUTIONTIME_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_DELETE_TKPH_READING = """CLASS=%s OPERATION=Delete WHERE=\"READING_TIME_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_TKPH_READING = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"READING_TIME_UTC <= to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_SAFETY_CHECK_RECORD = """CLASS=%s OPERATION=Delete WHERE=\"MACHINE_OID!= 0 and TIMESTAMP_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_SAFETY_CHECK_RECORD = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"MACHINE_OID!= 0 and TIMESTAMP_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_INCIDENT_MESSAGE = """CLASS=%s OPERATION=Delete WHERE=\"EVENT_TIMESTAMP_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_INCIDENT_MESSAGE = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"EVENT_TIMESTAMP_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_HISTORIC_REALTIME_KPI = """CLASS=%s OPERATION=Delete WHERE=\"UPDATED_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_HISTORIC_REALTIME_KPI = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"UPDATED_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_TRACTION_EVENT = """CLASS=%s OPERATION=Delete WHERE=\"START_TIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_TRACTION_EVENT = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"START_TIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_OBSTACLE_CLEAR = """CLASS=%s OPERATION=Delete WHERE=\"TIME_CLEARED_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_OBSTACLE_CLEAR = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"TIME_CLEARED_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""

    DBDATAMAN_DELETE_PROD_PLAN_TASK_HIST = """CLASS=%s OPERATION=Delete WHERE=\"CREATED_TIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
    DBDATAMAN_ARCHIVE_PROD_PLAN_TASK_HIST = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"CREATED_TIME_UTC < to_timestamp('%s','YY-MM-DD hh24:mi:ss.FF') and ROWNUM <= %d\";"""
else:
    DBDATAMAN_DELETE_ALARM = """CLASS=%s OPERATION=Delete WHERE=\"END_TIME_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_ALARM = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"END_TIME_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_CYCLE = """CLASS=%s OPERATION=Delete WHERE=\"ENDTIME_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_CYCLE = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"ENDTIME_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_EVENT = """CLASS=%s OPERATION=Delete WHERE=\"MACHINE_OID != 0 and TIMESTAMP_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_EVENT = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"MACHINE_OID != 0 and TIMESTAMP_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_EVENT_LOG = """CLASS=HealthLog OPERATION=Delete WHERE=\"LOG_CATEGORY = 'HealthEventSummary' AND ENDTIME_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_EVENT_LOG = """CLASS=HealthLog OPERATION=WriteThenDelete WHERE=\"LOG_CATEGORY = 'HealthEventSummary' AND ENDTIME_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_PRODUCTION_EVENT_LOG = """CLASS=HealthLog OPERATION=Delete WHERE=\"(LOG_CATEGORY = 'TruckPayloadEvent' OR LOG_CATEGORY = 'LoaderPayloadEvent' OR LOG_CATEGORY = 'PleLoaderPayLoadEvent') AND ENDTIME_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_PRODUCTION_EVENT_LOG = """CLASS=HealthLog OPERATION=WriteThenDelete WHERE=\"(LOG_CATEGORY = 'TruckPayloadEvent' OR LOG_CATEGORY = 'LoaderPayloadEvent' OR LOG_CATEGORY = 'PleLoaderPayLoadEvent') AND ENDTIME_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_OFFICEMESSAGE = """CLASS=%s OPERATION=Delete WHERE=\"TOTIME_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_OFFICEMESSAGE = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"TOTIME_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_SCHEDULED_BREAK = """CLASS=%s OPERATION=Delete WHERE=\"BREAKTIME_UTC <= '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_SCHEDULED_BREAK = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"BREAKTIME_UTC <= '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_SHIFT_CHANGE = """CLASS=%s OPERATION=Delete WHERE=\"SHIFTDATE_UTC <= '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_SHIFT_CHANGE = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"SHIFTDATE_UTC <= '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_GWMDUPLICATES = """CLASS=%s OPERATION=Delete WHERE=\"SHIFT_START_TIME_UTC <= '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_GWMDUPLICATES = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"SHIFT_START_TIME_UTC <= '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_SYSTEM_RESTART_INFO = """CLASS=%s OPERATION=Delete WHERE=\"JOBEXECUTIONTIME_UTC <= '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_SYSTEM_RESTART_INFO = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"JOBEXECUTIONTIME_UTC <= '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_TKPH_READING = """CLASS=%s OPERATION=Delete WHERE=\"READING_TIME_UTC <= '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_TKPH_READING = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"READING_TIME_UTC <= '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_SAFETY_CHECK_RECORD = """CLASS=%s OPERATION=Delete WHERE=\"MACHINE_OID != 0 and TIMESTAMP_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_SAFETY_CHECK_RECORD = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"MACHINE_OID != 0 and TIMESTAMP_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_INCIDENT_MESSAGE = "CLASS=%s OPERATION=Delete WHERE=\"EVENT_TIMESTAMP_UTC < '%s' \" TOP=top(%d);"
    DBDATAMAN_ARCHIVE_INCIDENT_MESSAGE = "CLASS=%s OPERATION=WriteThenDelete WHERE=\"EVENT_TIMESTAMP_UTC < '%s' \" TOP=top(%d);"

    DBDATAMAN_DELETE_HISTORIC_REALTIME_KPI = """CLASS=%s OPERATION=Delete WHERE=\"UPDATED_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_HISTORIC_REALTIME_KPI = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"UPDATED_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_TRACTION_EVENT = """CLASS=%s OPERATION=Delete WHERE=\"START_TIME_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_TRACTION_EVENT = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"START_TIME_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_OBSTACLE_CLEAR = """CLASS=%s OPERATION=Delete WHERE=\"TIME_CLEARED_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_OBSTACLE_CLEAR = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"TIME_CLEARED_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_REFILL_EVENT = """CLASS=WaterTruckRefillEvent OPERATION=Delete WHERE=\"TIMESTAMP_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_REFILL_EVENT = """CLASS=WaterTruckRefillEvent OPERATION=WriteThenDelete WHERE=\"TIMESTAMP_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_WATERTRUCK_METRICS = """CLASS=WaterTruckMetricsEvent OPERATION=Delete WHERE=\"TIMESTAMP_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_WATERTRUCK_METRICS = """CLASS=WaterTruckMetricsEvent OPERATION=WriteThenDelete WHERE=\"TIMESTAMP_UTC < '%s' \" TOP=top(%d);"""

    DBDATAMAN_DELETE_PROD_PLAN_TASK_HIST = """CLASS=%s OPERATION=Delete WHERE=\"CREATED_TIME_UTC < '%s' \" TOP=top(%d);"""
    DBDATAMAN_ARCHIVE_PROD_PLAN_TASK_HIST = """CLASS=%s OPERATION=WriteThenDelete WHERE=\"CREATED_TIME_UTC < '%s' \" TOP=top(%d);"""

def ufsInterpret(path):
    import ufs
    ufsRoot = ufs.getRoot(mstarpaths.interpretVar("UFS_PATH"))
    ufsFile = ufsRoot.get(path)
    if ufsFile is None:
        logger.error("Unable to find %s on the UFS path", path)
        return None
    return ufsFile.getPhysicalFile()


def makeDBDataManTemplate(dataStoreName=None,doCycles=False):
    if (dataStoreName is None):
        logger.error("No data store name provided")
        return
    # Set up DbDataMan temp file name to be created:
    timestamp = mstarpaths.interpretFormat("{YYYY}{MM}{DD}_{HH}{NN}")
    templateFileName = mstarpaths.interpretPath("{MSTAR_DATA}/dbdataman_deletion%s_%s.txt" % (dataStoreName, timestamp))
    print "makeDBDataManTemplate: making file %s." % (templateFileName)
    templateFile = open(templateFileName, "w")

    # Load DataSets.properties file using UFS:
    dataSetFile = ufsInterpret("/catalogs/DataSets.properties")
    if dataSetFile is None:
        return False

    dataset = ConfigurationFileIO.loadDictionaryFromFile(dataSetFile)

    # remove Cycle from list if needed
    if ('Cycle' in dataset.keys()) and (not doCycles):
        print "Ignoring cycle deletion since --includeCycleData was not specified."
        del dataset['Cycle']

    # Get Retention period values
    retainShort = int(mstarpaths.interpretVar("_ADMINDATA_AGE_SHORT"))
    retainMedium = int(mstarpaths.interpretVar("_ADMINDATA_AGE_MEDIUM"))
    retainLong = int(mstarpaths.interpretVar("_ADMINDATA_AGE_LONG"))
    retainVeryLong = int(mstarpaths.interpretVar("_ADMINDATA_AGE_VERY_LONG"))

    retainLookup = {"Short":retainShort, "Medium":retainMedium, "Long":retainLong, "Very Long":retainVeryLong}

    # Process the data retention policy
    dataRetentionSpec = mstarpaths.interpretVar("_DATA_RETENTION_POLICY")

    dataRetention = {}
    dataRetentionWithoutGroup = {}
    if dataRetentionSpec is not None and dataRetentionSpec != '':
        dataRetention = eval(dataRetentionSpec)
        for key in dataRetention.iterkeys():
            keyStart=key.find(".")+1
            keyVal = dataRetention[key]
            key=key[keyStart:].strip()
            dataRetentionWithoutGroup[key] = keyVal

    for key in dataset.keys():
        value = eval(dataset[key])
        itemClass = value["class"]

        RetainPolicy = 'Delete'
        RetainPeriod = 'Short'
        valLimit = ''
        if dataRetention.has_key(key):
            RetainInfo = dataRetention[key]
        elif dataRetentionWithoutGroup.has_key(key):
            RetainInfo = dataRetentionWithoutGroup[key]
        else:
            RetainInfo = None

        if RetainInfo is not None:
            val = RetainInfo[0]
            if val != 'Default':
                RetainPolicy = val
            val = RetainInfo[1]
            if val != 'Default':
                RetainPeriod = val
            val = RetainInfo[2]
            if val != 'Default':
                valLimit = val
       
        valLimit = valLimit.strip()
        # If Limit is set to 0 or empty, It will set the Limit to max upper limit to delete the records.
        if valLimit == '0' or valLimit == '':
            Limit = UPPER_LIMIT
        else:
            Limit = int(valLimit)
            if (Limit > UPPER_LIMIT):
                Limit = UPPER_LIMIT

        if RetainPeriod == "Retain":
            print "Data Set <%s> will never be archived or deleted" % key
            continue

        Retain = retainLookup[RetainPeriod]
        RetainStr =str(datetime.datetime.now() + datetime.timedelta(days=-Retain))

        dbdataman_line = None

        if dataStoreName == '_HISTORICALDB':
            if itemClass.endswith("Event"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_EVENT % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_EVENT % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("Alarm"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_ALARM % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_ALARM % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("Cycle"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_CYCLE % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_CYCLE % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("FluidAndSmuRecord"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_EVENT % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_EVENT % (itemClass, RetainStr, Limit)
            elif itemClass.startswith("Office"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_OFFICEMESSAGE % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_OFFICEMESSAGE % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("ScheduledBreak"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_SCHEDULED_BREAK % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_SCHEDULED_BREAK % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("ShiftChange"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_SHIFT_CHANGE % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_SHIFT_CHANGE % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("GwmDuplicatesInfoImpl"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_GWMDUPLICATES % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_GWMDUPLICATES % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("StartInfoImpl"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_SYSTEM_RESTART_INFO % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_SYSTEM_RESTART_INFO % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("TkphReading"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_TKPH_READING % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_TKPH_READING % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("SafetyCheckRecord"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_SAFETY_CHECK_RECORD % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_SAFETY_CHECK_RECORD % (itemClass, RetainStr, Limit)
            elif itemClass.startswith("Abstract"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_INCIDENT_MESSAGE % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_INCIDENT_MESSAGE % (itemClass, RetainStr, Limit)
            elif itemClass.endswith("HistoricRealTimeKpi"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_HISTORIC_REALTIME_KPI % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_HISTORIC_REALTIME_KPI % (itemClass, RetainStr, Limit)
            elif itemClass == "HealthEvent":
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_EVENT_LOG % (RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_EVENT_LOG % (RetainStr, Limit)
            elif itemClass == "ProductionEvent":
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_PRODUCTION_EVENT_LOG % (RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_PRODUCTION_EVENT_LOG % (RetainStr, Limit)
            elif itemClass == "TractionEventEntity":
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_TRACTION_EVENT % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_TRACTION_EVENT % (itemClass, RetainStr, Limit)
            elif itemClass == "ObstacleClear":
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_OBSTACLE_CLEAR % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_OBSTACLE_CLEAR % (itemClass, RetainStr, Limit)
            elif itemClass == "WaterTruckMetrics":
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_REFILL_EVENT % (RetainStr, Limit) + "\n" \
                                     + DBDATAMAN_DELETE_WATERTRUCK_METRICS % (RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_REFILL_EVENT % (RetainStr, Limit) + "\n" \
                                     + DBDATAMAN_ARCHIVE_WATERTRUCK_METRICS % (RetainStr, Limit)
            elif itemClass == "ProdPlanTaskHistDO":
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_PROD_PLAN_TASK_HIST % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_PROD_PLAN_TASK_HIST % (itemClass, RetainStr, Limit)
            elif itemClass == "ProdPlanHistDO":
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_PROD_PLAN_TASK_HIST % (itemClass, RetainStr, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_PROD_PLAN_TASK_HIST % (itemClass, RetainStr, Limit)
        elif dataStoreName == '_GISDB':
            if itemClass.startswith("GISEdge"):
                if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_GISEDGE_DATA % (dataStoreName, itemClass, Retain, Limit)
                else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_GISEDGE_DATA % (dataStoreName, itemClass, Retain, Limit)
            elif itemClass == "Obstacles":
               if RetainPolicy == 'Delete':
                    dbdataman_line = DBDATAMAN_DELETE_GIS_OBSTACLE % (dataStoreName, itemClass, Retain, Limit)
               else:
                    dbdataman_line = DBDATAMAN_ARCHIVE_GIS_OBSTACLE % (dataStoreName, itemClass, Retain, Limit)
        elif dataStoreName == '_PITMODELDB' and itemClass == "VehicleData":
            dbdataman_line = DBDATAMAN_DELETE_VEHICLE_DATA % (itemClass, Retain, Retain, Retain, Limit)


        if dbdataman_line is not None:
            print "Data Set <%s> has policy %s with retention period %s and Limit set to %s" % \
                  (key, RetainPolicy, RetainPeriod, Limit)
            templateFile.write(dbdataman_line + "\n")

        if dataStoreName == "_HISTORICALDB" and itemClass == "HealthEvent":
            if RetainPolicy == 'Delete':
                dbdataman_line = DBDATAMAN_DELETE_EVENT_LOG % (RetainStr, Limit)
                templateFile.write(dbdataman_line + "\n")
            else:
                dbdataman_line = DBDATAMAN_ARCHIVE_EVENT_LOG % (RetainStr, Limit)
                templateFile.write(dbdataman_line + "\n")

        if dataStoreName == "_HISTORICALDB" and itemClass == "ProductionEvent":
            if RetainPolicy == 'Delete':
                dbdataman_line = DBDATAMAN_DELETE_PRODUCTION_EVENT_LOG % (RetainStr, Limit)
                templateFile.write(dbdataman_line + "\n")
            else:
                dbdataman_line = DBDATAMAN_ARCHIVE_PRODUCTION_EVENT_LOG % (RetainStr, Limit)
                templateFile.write(dbdataman_line + "\n")

    templateFile.close()
    return templateFileName

# Main program #
if __name__ == '__main__':

    # Set up args and Call top level method to make shortcuts
    mstarpaths.loadMineStarConfig()
    makeDBDataManTemplate('_HISTORICALDB',False)
    makeDBDataManTemplate('_PITMODELDB',False)
