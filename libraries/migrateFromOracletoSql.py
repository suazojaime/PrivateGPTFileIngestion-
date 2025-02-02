__author__ = 'viswav3'
import minestar, mstarpaths,mstarrun,sys, os,mstardebug,emptyDataStore, subprocess, traceback, datastore, databaseDifferentiator
from optparse import make_option
from os import listdir
from os.path import isfile, join

__version__ = "$Revision: 1.0 $"

def isValidSQLServerInstanceType() :
    mstarpaths.loadMineStarConfig(forceReload=1)
    currentDbType = mstarpaths.interpretVar("_INSTANCE1_TYPE")
    if currentDbType != 'sqlserver' :
        print "Usage: INSTANCE TYPE and database connection settings should be SQL Server."
        return False
    return True

def isValidOracleInstanceType() :
    mstarpaths.loadMineStarConfig(forceReload=1)
    currentDbType = mstarpaths.interpretVar("_INSTANCE1_TYPE")
    dbAuth = mstarpaths.interpretVar("_DB_SYS_AUTH")
    if currentDbType != 'oracle' :
        print "Could not continue. Expected Oracle INSTANCE TYPE, but found ", currentDbType
        return False
    return True

def printCurrentInstanceType() :
    currentDbType = mstarpaths.interpretVar("_INSTANCE1_TYPE")
    print 'Current DB INSTANCE TYPE',currentDbType

def changeDatabaseInstance(instanceType, dbServerName, sysPassword) :
    mstarrun.run(["minestar.platform.persistence.service.tools.ssma.MigrateFromOracletoSql", "_INSTANCE1_TYPE="+instanceType, "_DB_SERVER_NAME="+dbServerName,"_DB_SYS_AUTH="+sysPassword])
    mstarpaths.loadMineStarConfig(forceReload=1)
    reload(datastore)

def invokeJava(oracleServer,oraclePass,sqlServer,sqlPass,modelFile,pitModelFile,histFile,summFile,preSteps,runPreScripts,migrate,postSteps,runPostScripts,validate) :
    mstarrun.run(["minestar.platform.persistence.service.tools.ssma.MigrateFromOracletoSql",
                  "_ORACLE_SERVER_NAME="+oracleServer,
                  "_ORACLE_PASS="+oraclePass,
                  "_SQL_SERVER_NAME="+sqlServer,
                  "_SQL_PASS="+sqlPass,
                  "_MODEL_DUMP_FILE="+(modelFile if modelFile is not None else 'Empty'),
                  "_PITMODEL_DUMP_FILE="+(pitModelFile if pitModelFile is not None else 'Empty'),
                  "_HIST_DUMP_FILE="+(histFile if histFile is not None else 'Empty'),
                  "_SUMM_DUMP_FILE="+(summFile if summFile is not None else 'Empty'),
                  "_PREMIGRATE_STEPS="+(','.join(preSteps) if preSteps is not None else 'Empty'),
                  "_RUN_PRESCRIPTS="+str(runPreScripts),
                  "_MIGRATE="+str(migrate),
                  "_POSTMIGRATE_STEPS="+(','.join(postSteps) if postSteps is not None else 'Empty'),
                  "_RUN_POSTSCRIPTS="+str(runPostScripts),
                  "_VALIDATE="+str(validate)])

def checkIfSSMAPackageIsInstalled() :
    try:
        os.startfile('SSMAforOracleConsole')
        return True
    except Exception, e:
        return False

def main(appConfig=None):

    try :
        optionDefns = [
            make_option("-a", "--premigrate",\
                help="Do pre-migrate."),
            make_option("-b", "--migrate",action="store_true",\
                help="Migrate options."),
            make_option("-c", "--postmigrate",\
                help="Do post-migrate."),
            make_option("-z", "--validate", action="store_true",\
                help="Do validation."),
            make_option("-m", "--model",\
                help="model dumpfile."),
            make_option("-p", "--pitmodel",\
                help="pitmodel dumpfile."),
            make_option("-s", "--summ",\
                help="summary dumpfile."),
            make_option("-i", "--hist",\
                help="historical dumpfile."),
            make_option("-x", "--password",\
                help="oracle password."),
            make_option("-d", "--server",\
                help="oracle server."),
            make_option("-t", "--prescript", action="store_true",\
                help="run premigrate script"),
            make_option("-u", "--postscript", action="store_true",\
                help="run postmigrate script"),

            ]

        success = True

        if mstardebug.debug:
            print 'DEBUG is on. Please turn off the debug'
            sys.exit(1)

        mstarpaths.loadMineStarConfig()

        dbRole = mstarpaths.interpretVar("_DBROLE")
        if dbRole != 'PRODUCTION':
            print 'Current DB role is not Production. Migration failed'
            sys.exit(1)

        if checkIfSSMAPackageIsInstalled() == False :
            print 'SSMAforOracleConsole Utility is not installed on the system. Please install to continue.'
            sys.exit(1)

        if isValidSQLServerInstanceType() == False :
            sys.exit(1)

        dbAuth = mstarpaths.interpretVar("_DB_SYS_AUTH")

        argumentsStr = "[modeldumpfile] [pitmodeldumpfile] [historicaldumpfile] [summarydumpfile] [--premigrate] [premigratescript] [-b] [--postmigrate] [postmigratescript] [-v] [oracleDatabaseServer] [oracleSysPassword]"
        (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

        hostName = os.environ['COMPUTERNAME']
        oracleServerName = hostName
        sqlServerName = None
        serverRoleSpec = mstarpaths.interpretVar("_DB_SERVER_ROLES")

        if serverRoleSpec is not None and serverRoleSpec != '':
            serverRoles = eval(serverRoleSpec)
            if serverRoles.has_key(dbRole):
                sqlServerName =  serverRoles[dbRole]

        if options.server is not None:
            oracleServerName = options.server
        oracleSysPassword = options.password

        if oracleServerName is None:
            print 'ERROR : Oracle server name is empty. Migration failed'
            sys.exit(1)
        if oracleSysPassword is None:
            print 'ERROR : Oracle password is empty. Migration failed'
            sys.exit(1)

        premigratesteps = options.premigrate
        postmigratesteps = options.postmigrate

        if premigratesteps is not None:
            premigratesteps = premigratesteps.split(',')
        else:
            premigratesteps = []

        if postmigratesteps is not None:
            postmigratesteps = postmigratesteps.split(',')
        else:
            postmigratesteps = []

        filenameModel = options.model
        filenamePitmodel = options.pitmodel
        filenameHist = options.hist
        filenameSumm = options.summ
        doimport = False
        validate = False

        if options.validate is not None:
            validate = options.validate

        #do the import only if any of the .dmp file is provided
        if (filenameModel is not None or filenamePitmodel is not None or filenameHist is not None or filenameSumm is not None):
            doimport = True

        execPreScripts = options.prescript
        execPostScripts = options.postscript

        doMigrate = options.migrate

        doPremigrateOracle = any(x in premigratesteps for x in ('DeleteOracle','CreateOracleSchema','MakeDataStoresOracle'))
        #updatetns = (True if (doPremigrateOracle or execPreScripts or doimport) else False)

        #updating tns names ora
        currentDbType = mstarpaths.interpretVar("_INSTANCE1_TYPE")
        if (currentDbType != 'oracle'):
            changeDatabaseInstance("oracle", oracleServerName, oracleSysPassword)
            dbObject = databaseDifferentiator.returndbObject()
            dbObject.updateTnsNameFile()

        invokeJava(oracleServerName,oracleSysPassword,sqlServerName,dbAuth,filenameModel,filenamePitmodel,filenameHist,filenameSumm,premigratesteps,execPreScripts,doMigrate,
        postmigratesteps,execPostScripts,validate)

    except Exception, ex:
        print "ERROR:", ex
        traceback.print_exc()
    finally:
        # Change to original context of sql server
        if 'dbAuth' in locals():
            changeDatabaseInstance("sqlserver", sqlServerName, dbAuth)

    outputDir = mstarpaths.interpretPath("{MSTAR_TEMP}") + os.sep + "SSMAReports"

    print 'Data Migrated to SQLServer successfully. Migration Reports are generated to ',outputDir

if __name__ == "__main__":
    """entry point when called from python"""
    main()


