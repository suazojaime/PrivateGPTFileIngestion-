# TODO:
# - Views?
# - values of permissions, not just the permission names?

__version__ = "$Revision: 1.1 $"

import minestar
logger = minestar.initApp()
import os, sys, md5, types, xml
import mstarpaths, ufs, makeBuildManifest, makeCatalogs, ConfigurationFileIO, datastore


# Default skip patterns file
MANIFEST_SKIP_FILE = "{MSTAR_HOME}/COMPONENTS.SKIP"

# List of catalogs to load components from
CATALOGS = ['Tools', 'Permissions', 'Pages', 'OptionSets']

# Separator for id - type goes before this
_ID_SEP = "::"

# The prefix used at the front of value keys to indicate content is actually a filename to load and checksum
_FILE_PREFIX = "file://"

# Categories of components
CATEGORIES = [
    ('General',     ['Tools', 'Permissions', 'UnitSets']), \
    ('Client',      ['Pages', 'PageConfigs', 'Desktops', 'Consoles', 'OptionSets']), \
    ('Server',      ['Services', 'Jobs', 'ObjectClasses', 'ChoiceLists']), \
    ('Information', ['Views', 'Reports', 'ListOfValues', 'Displays']) \
    ]

# Generic services
_GENERIC_SERVICES = ["manager", "object", "gadget", "loadCircuit", "jobController"]

# Special services 
_SPECIAL_SERVICES = [
    "plannedJobDispatcher", \
    "onboardConfig", "mstarrun", "schemaCheck", \
    "TAEServer", "TAE2Server", "AssignmentController", "QueueMonitor", \
    "unitTest", "junit", "MachineController", "CycleEngineLoader", "BlockDetermination", "CycleSynchronizer", \
    "remoteService", "UrgentAlarmForwarder", "KpiForwarder", "PerfAgent", "logging", \
    ]

# The SQL statement for selecting views metadata (thanks to Michael Siemer)
import databaseDifferentiator
dbobject = databaseDifferentiator.returndbObject()
_SELECT_VIEWS_METADATA_STMT = dbobject.selectViewMetadata()


## Component Manifest Routines ##

def makeComponentsManifest(outputFilename, searchPath, skipPatternsFile=None, reportsDir=None, summaryFilename=None):
    # Load the skip patterns, if any
    skipPatterns = []
    if skipPatternsFile is None:
        logger.info("No skip patterns file specified")
    else:
        logger.info("Loading skip patterns from %s ..." % skipPatternsFile)
        skipPatterns = makeBuildManifest.loadSkipPatterns(skipPatternsFile)
        logger.info("Found %d skip patterns" % len(skipPatterns))

    # Adjust the search path to exclude MSTAR_CONFIG
    mstarCfg = mstarpaths.interpretVar("MSTAR_CONFIG")
    if searchPath.endswith(mstarCfg):
        searchPath = searchPath[:-len(mstarCfg) + 1]
        logger.info("removing %s from the search path" % mstarCfg)
        logger.debug("searching %s" % searchPath)
    else:
        logger.warn("unable to find MSTAR_CONFIG on the search path - can't remove it")
    ufsRoot = ufs.getRoot(searchPath)
    
    # Generate the manifest and dump it
    logger.info("Generating manifest for current build ...")
    manifest = getComponentManifest(ufsRoot, searchPath, skipPatterns, reportsDir)
    logger.info("Dumping manifest to %s ..." % outputFilename)
    counts = dumpManifest(manifest, outputFilename)
    logger.info("Saved %d items in the manifest" % len(manifest))
    _showCounts(counts, summaryFilename)

def getComponentManifest(ufsRoot, searchPath, skipPatterns=[], reportsDir=None):
    manifest = {}

    # Check the search path is good
    if searchPath == None or len(searchPath) == 0:
        logger.error("unable to build components manifest as directory search path is empty")
        return {}

    # Process the catalogs
    searchDirs = searchPath.split(os.pathsep)
    for catalog in CATALOGS:
        if catalog == 'Tools':
            (groups,order) = makeCatalogs.buildGroupsForTools()
        elif catalog in ['OptionSets', 'Permissions']:
            ipParams = {'searchPath':searchPath}
            (groups,order,groupInfo) = makeCatalogs.buildGroupsFromCommentsForCatalog(searchPath, catalog,
                                             itemProcessor=makeCatalogs.buildOptionsFormItemProcessor,
                                             itemProcessorParams=ipParams)
        else:
            (groups,order,groupInfo) = makeCatalogs.buildGroupsFromCommentsForCatalog(searchPath, catalog)
        appendCatalogItems(manifest, groups, catalog, skipPatterns)
        
    # Add the general components
    appendUnitSets(manifest, ufsRoot, skipPatterns)

    # Add the client components
    appendPageConfigs(manifest, ufsRoot, skipPatterns)
    appendDesktops(manifest, ufsRoot, skipPatterns)
    appendConsoles(manifest, ufsRoot, skipPatterns)

    # Add the server components    
    appendServices(manifest, ufsRoot, skipPatterns)
    appendJobs(manifest, ufsRoot, skipPatterns)
    appendObjectClasses(manifest, ufsRoot, skipPatterns)
    appendChoiceLists(manifest, searchPath, skipPatterns)

    # add the analysis components    
    appendViews(manifest, ufsRoot, skipPatterns)
    appendReports(manifest, reportsDir, skipPatterns)
    appendListOfValues(manifest, reportsDir, skipPatterns)
    appendDisplays(manifest, ufsRoot, skipPatterns)
    
    return manifest

def makeId(type, name):
    return type + _ID_SEP + name

def splitId(id):
    return id.split(_ID_SEP, 1)

_COUNTS_FORMAT = "%-16s%-16s%s\n"

def _showCounts(counts, outputFilename=None):
    # Get the output stream
    output = sys.stdout
    if not (outputFilename is None):
        try:
            output = open(outputFilename, "w")
            logger.info("Dumping summary statistics to %s ..." % outputFilename)
        except IOError, msg:
            logger.error('Can\'t open %s (%s) - using standard output' % (outputFilename, msg))
    
    # Dump the totals
    total = 0
    output.write(_COUNTS_FORMAT % ("Category","Component","Count"))
    for categoryInfo in CATEGORIES:
        (category,typesInCategory) = categoryInfo
        for type in typesInCategory:
            count = counts.get(type, 0)
            total += count
            output.write(_COUNTS_FORMAT % (category,type,count))
    output.write(_COUNTS_FORMAT % ("TOTAL:","",total))
    if output != sys.stdout:
        output.close()

            
## General Manifest Routines ##

def idMatchesSkipPatterns(id, skipPatterns):
    return makeBuildManifest.idMatchesSkipPatterns(id, skipPatterns)

def checksumText(text):
    m = md5.md5()
    m.update(text)
    return _hexify(m.digest())

def checksumFile(file, title, bufsize=4096, rmode='r', text=0):
    m = md5.md5()
    try:
        fp = open(file, rmode)
    except IOError, msg:
        logger.error('%s: Can\'t open: %s\n' % (title, msg))
        return -1
    try:
        if text:
            pattern = re.compile(r'\$Id\:.*\$')
            for line in fp:
                (line, count) = pattern.subn(r'\$Id\$', line)
                m.update(line)
                if count:
                    logger.debug('matched CVS string in %s' % title)
        else:
            while 1:
                data = fp.read(bufsize)
                if not data: break
                m.update(data)
    except IOError, msg:
        logger.error('%s: I/O error: %s\n' % (title, msg))
        return -2
    try:
        fp.close()
    except IOError, msg:
        logger.error('%s: Can\'t close: %s\n' % (title, msg))
    return _hexify(m.digest())

def _hexify(s):
    res = ''
    for c in s:
        res = res + '%02x' % ord(c)
    return res

def dumpManifest(manifest, outputFilename):
    sortedKeys = manifest.keys()
    sortedKeys.sort()
    counts = {}
    output = open(outputFilename, "w")
    for id in sortedKeys:
        (hash, physName) = manifest[id]
        output.write("%s\t%s\t%s\n" % (hash, id, physName))
        _incrementCounts(counts, splitId(id)[0])
    output.close()
    return counts

def _incrementCounts(counts, key):
    if counts.has_key(key):
        counts[key] += 1
    else:
        counts[key] = 1

def dumpManifestToString(manifest):
    lines = []
    sortedKeys = manifest.keys()
    sortedKeys.sort()
    for ufsName in sortedKeys:
        (hash, physName) = manifest[ufsName]
        lines.append("%s\t%s\t%s" % (hash, ufsName, physName))
    return "\n".join(lines)

def appendDictionary(manifest, dict, type, skipPatterns):    
    for k in dict.keys():
        id = makeId(type, k)
        if idMatchesSkipPatterns(id, skipPatterns):
            continue
        content = dict[k]
        if content.startswith(_FILE_PREFIX):
            file = content[len(_FILE_PREFIX):]
            checksum = checksumFile(file, file)
            # We explicitly do not put the full path in here as doing so will
            # cause basic diff tools to fail comparisons across manifests built on different machines
            content = "(file)"
        else:
            checksum = checksumText(content)
        manifest[id] = (checksum, content)

 
## Catalog Sourced Information ##

def appendCatalogItems(manifest, groups, catalog, skipPatterns):
    dict = {}
    for name in groups.keys():
        for item in groups[name]:
            # If it's a tuple, the 1st element is the name, the 2nd element is a list of parameters and the 3rd element is extra details
            if type(item) == types.TupleType:
                itemName = item[0]
                itemParams = item[1]
                itemDetails = item[2]
                dict[itemName] = repr(itemParams)
            else:
                dict[item] = item
    appendDictionary(manifest, dict, catalog, skipPatterns)

def appendChoiceLists(manifest, searchPath, skipPatterns):
    lines = makeCatalogs.loadCatalogLines(searchPath, 'ChoiceLists')
    (dict, comments) = ConfigurationFileIO.loadDictionaryFromLinesWithComments(lines)
    _trimSpacesFromValues(dict)
    appendDictionary(manifest, dict, 'ChoiceLists', skipPatterns)

def _trimSpacesFromValues(dict):
    for k in dict.keys():
        dict[k] = dict[k].strip()

def appendPageConfigs(manifest, root, skipPatterns):
    dict = {}
    suffixLen = len("Config.properties")
    ufsDir = root.get("/explorer/configs")

    # Loop over subdirectories, one per page
    for ufsSubdir in ufsDir.listSubdirs():
        for ufsFile in ufsSubdir.listFiles():
            name = ufsFile.getName()
            if name.endswith("Config.properties"):
                label = name[0:-suffixLen]
                if len(label) == 0 or label == "Default":
                    continue
                key = ufsSubdir.getName() + "/" + label
                (sources,content) = ufsFile.loadMapAndSources()
                dict[key] = repr(content)
    appendDictionary(manifest, dict, 'PageConfigs', skipPatterns)

def appendDesktops(manifest, root, skipPatterns):
    dict = {}
    suffix = ".eed"
    ufsDir = root.get("/explorer/desktops")
    if ufsDir is None:
        logger.warn("no %s found in build" % 'Desktops')
        return

    # Loop over subdirectories, one per app
    for ufsSubdir in ufsDir.listSubdirs():
        for ufsFile in ufsSubdir.listFiles():
            name = ufsFile.getName()
            if name.endswith(suffix):
                label = name[0:-len(suffix)]
                key = ufsSubdir.getName() + "/" + label
                (sources,content) = ufsFile.loadMapAndSources()
                dict[key] = repr(content)
    appendDictionary(manifest, dict, 'Desktops', skipPatterns)

def appendConsoles(manifest, root, skipPatterns):
    dict = {}
    suffix = "_Console.eed"
    ufsDir = root.get("/explorer/consoles")
    if ufsDir is None:
        logger.warn("no %s found in build" % 'Consoles')
        return

    # Loop over subdirectories, one per role then one per app
    for ufsRole in ufsDir.listSubdirs():
        for ufsApp in ufsRole.listSubdirs():
            for ufsFile in ufsApp.listFiles():
                name = ufsFile.getName()
                if name.endswith(suffix):
                    label = name[0:-len(suffix)]
                    key = ufsApp.getName() + "/" + ufsRole.getName() + "/" + label
                    (sources,content) = ufsFile.loadMapAndSources()
                    dict[key] = repr(content)
    appendDictionary(manifest, dict, 'Consoles', skipPatterns)


## XML Sourced Information ##

def appendUnitSets(manifest, root, skipPatterns):
    dict = {}
    ufsFile = root.get("/xml/units/units.xml")
    text = ufsFile.getTextContent()
    dict = _loadDictionaryFromXml(text, "unitset", "name")
    appendDictionary(manifest, dict, "UnitSets", skipPatterns)

def appendJobs(manifest, root, skipPatterns):
    appendFromXmlCatalog(manifest, root, 'Jobs', skipPatterns)

def appendDisplays(manifest, root, skipPatterns):
    appendFromXmlCatalog(manifest, root, 'Displays', skipPatterns)

def appendObjectClasses(manifest, root, skipPatterns):
    dict = {}
    ufsDir = root.get("/xml/metadata")
    for ufsFile in ufsDir.listFiles():
        filename = ufsFile.getName()
        if not filename.endswith(".xml"):
            continue
        name = filename[0:-len(".xml")]
        logger.debug("Parsing %s ..." % filename)
        text = ufsFile.getTextContent()
        items = _loadDictionaryFromXml(text, "classdef", "name")
        dict.update(items)
    appendDictionary(manifest, dict, "ObjectClasses", skipPatterns)
    
def appendServices(manifest, root, skipPatterns):
    dict = {}
    for special in _SPECIAL_SERVICES:
        dict["special/" + special] = ""
    ufsDir = root.get("/xml/xoc")
    for ufsFile in ufsDir.listFiles():
        filename = ufsFile.getName()
        if not filename.endswith(".xoc"):
            continue
        name = filename[0:-len(".xoc")]
        logger.debug("Parsing %s ..." % filename)
        text = ufsFile.getTextContent()
        dom = xml.dom.minidom.parseString(text)
        for serviceType in _GENERIC_SERVICES:
            dict.update(_getItemsFromDom(dom, serviceType, "name", serviceType + "/"))
    appendDictionary(manifest, dict, "Services", skipPatterns)

def _getItemsFromDom(dom, elementName, nameAttribute, prefix=""):
    items = {}
    for node in dom.getElementsByTagName(elementName):
        key = prefix + node.getAttribute(nameAttribute)
        if key == "gadget/genericService":
            realName = _getRealName(node)
            key = "genericService/" + realName
        items[key] = node.toxml().replace("\n", " ")
    return items

def _getRealName(node):
    for child in node.getElementsByTagName("var"):
        if child.getAttribute("name") == "name":
            return _getTextFromElement(child.childNodes)
    return repr(node)

def _getTextFromElement(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

def appendFromXmlCatalog(manifest, root, type, skipPatterns):
    ufsDir = root.get("/xml/catalogs/%s " % type)
    if ufsDir is None:
        logger.warn("no %s found in build" % type)
        return
    dict = {}
    for ufsFile in ufsDir.listFiles():
        name = ufsFile.getName()[0:-len(".xml")]
        text = ufsFile.getTextContent()
        items = _loadDictionaryFromXml(text, "classdef", "name", name + "/")
        dict.update(items)
    appendDictionary(manifest, dict, type, skipPatterns)

def _loadDictionaryFromXml(text, elementName, nameAttribute, prefix=""):
    dom = xml.dom.minidom.parseString(text)
    dict = {}
    for node in dom.getElementsByTagName(elementName):
        key = prefix + node.getAttribute(nameAttribute)
        dict[key] = node.toxml().replace("\n", " ")
    return dict


## FileSystem Sourced Information ##
    
def appendReports(manifest,dir, skipPatterns):
    appendComponentsInDir(manifest, dir, skipPatterns, "Reports", ".rep")

def appendListOfValues(manifest,dir, skipPatterns):
    appendComponentsInDir(manifest, dir, skipPatterns, "ListOfValues", ".lov")

def appendComponentsInDir(manifest, dirName, skipPatterns, type, suffix):
    if dirName is None:
        logger.warn("No %s included - no directory specified" % type)
        return

    # Extract the files matching the suffix    
    files = _getBasenamesMatchingSuffix(dirName, suffix)
    appendDictionary(manifest, files, type, skipPatterns)

def _getBasenamesMatchingSuffix(dir, suffix):
    names = {}
    for f in os.listdir(dir):
        path = os.path.join(dir, f)
        if os.path.isdir(path):
            names.update(_getBasenamesMatchingSuffix(path, suffix))
        elif f.endswith(suffix):
            name = f[0:-len(suffix)]
            names[name] = _FILE_PREFIX + path
    return names


## Database Sourced Information ##
    
def appendViews(manifest, ufsRoot, skipPatterns):
    # Collect the views metadata
    views = {}
    try:
        hist = datastore.getDataStore("_HISTORICALDB")
        logger.info("Retrieving view metadata from %s ..." % hist._getThinURL())
        selectResult = hist.javaSelect(_SELECT_VIEWS_METADATA_STMT)
    except:
        logger.error("failed to retrieve views metadata")
        return
    for rec in selectResult:
        # Each record is tableName, ColumnName, dataType, Nullable
        viewName = rec[0]
        columnMetadata = rec[1:]
        if views.has_key(viewName):
            metadata = views[viewName]
            metadata.append(columnMetadata)
        else:
            metadata = [columnMetadata]
        views[viewName] = metadata

    # Convert the metadata to strings and update the manifest        
    dict = {}
    for v in views.keys():
        dict[v] = repr(views[v])
    appendDictionary(manifest, dict, 'Views', skipPatterns)
    
    
## Main Program ##

from optparse import make_option

def main(appConfig=None):
    """entry point when called from mstarrun"""

    # Process options and check usage
    optionDefns = [
        make_option("-r", "--reportsDir", help="parent directory of report & list-of-values files"),\
    ]
    argumentsStr = "manifestFilename [summaryFilename]"
    (options,args) = minestar.parseCommandLine(appConfig, __version__, optionDefns, argumentsStr)

    # Generate the component manifest and dump it
    outputFilename = args[0]
    summaryFilename = None
    if len(args) > 1:
        summaryFilename = args[1]
    mstarpaths.loadMineStarConfig()
    skipPatternsFile = mstarpaths.interpretPath(MANIFEST_SKIP_FILE)
    if not os.path.exists(skipPatternsFile):
        skipPatternsFile = None
    makeComponentsManifest(outputFilename, mstarpaths.interpretVar("UFS_PATH"), skipPatternsFile, options.reportsDir, summaryFilename)
    minestar.exit()

if __name__ == "__main__":
    """entry point when called from python"""
    main()
