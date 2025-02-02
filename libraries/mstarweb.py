# A module to assist in deploying UFS directories to Jetty
#
# Written by Glen Blanchard
import mstarpaths, ufs, os, re, shutil, minestar, time

def cleanWebDirectories():
	_cleanOldWebdirs()
	_cleanOldWarFiles()

def _cleanContexts():
	# Remove all mstar_*.xml contexts from JETTY_HOME\contexts
	jettyContexts = mstarpaths.interpretPath("{_JETTY_BASE}/webapps");
	if not os.access(jettyContexts, os.F_OK | os.X_OK):
		minestar.initApp().warn("Jetty contexts directory '%s' not found." % jettyContexts)
		return
	files = os.listdir(jettyContexts)
	pattern = re.compile("mstar_.*\.xml")
	for f in files:
		if pattern.match(f):
			path = os.path.join(jettyContexts, f);
			if os.path.isfile(path):
				print "Removing existing context: %s" % f
				os.remove(path)

	# Remove a badly deployed ROOT directory in the webapps context directory
	badroot = os.path.join(jettyContexts, 'ROOT')
	if os.path.exists(badroot):
		print "Removing bad root directory: %s" % badroot
		shutil.rmtree(badroot)

def _cleanOldWarFiles():
	""" Only here to remove the old war files we deployed in 4.0

	Should be removed in about 4.2
	"""
	warHome = mstarpaths.interpretPath("{_JETTY_HOME}/webapps")
	if not os.path.exists(warHome):
		return
	for warFile in os.listdir(warHome):
		if warFile in ["minestar.war", "minestar-rest.war"]:
			try:
				os.remove(os.path.join(warHome, warFile))
			except:
				pass

def _cleanOldWebdirs():
	""" Used to remove old directories used in 4.1-4.3
	"""
	# Remove any old directories
	webHome = mstarpaths.interpretPath("{MSTAR_TEMP}/web")
	if os.path.exists(webHome):
		try:
			print "Removing old directory: %s" % webHome
			shutil.rmtree(webHome)
		except:
			pass

def unpackWebDirectories():
	# for each directory
	#   unpack it

	directories = mstarpaths.interpretVar("_WEB_DIRECTORIES")

	_cleanContexts()

	webServerSrc = mstarpaths.interpretPath("{MSTAR_HOME}/ext/Platform/Platform_Management/webserver")
	if os.path.isdir(webServerSrc):
		webServerBase = mstarpaths.interpretPath("{_JETTY_BASE}")
		if os.path.isdir(webServerBase):
			print "Removing existing web server configuration %s" % webServerBase
			shutil.rmtree(webServerBase)
		print "Copy new web server configuration %s" % webServerBase
		copytree(webServerSrc, webServerBase)

		webhome = mstarpaths.interpretPath("{MSTAR_TEMP}/web")

		print "Unpacking web directories to %s: %s" % (webhome, directories)
		dirs = directories.split(',')
		for directory in dirs:
			_unpackWebDirectory(directory, webhome)

def _unpackWebDirectory(directory, webhome):
	#   find it in the UFS and unpack it to a temporary location
	#   and create a context.xml for jetty
	print "Unpacking web directory: %s" % directory
	ufsroot = ufs.getRoot(mstarpaths.interpretPath("{UFS_PATH}"))
	root = None
	try:
		root = ufsroot.get(directory)
	except ufs.UfsException:
		pass
	if not root:
		minestar.initApp().error("Web directory '%s' not found in UFS." % directory)
		return

	physicalDirectory = os.path.join(webhome, directory)
	zipFile = "%s.zip" % physicalDirectory
	# Remove anything that exists there first
	if os.path.exists(physicalDirectory):
		print "  Removing old ufs copy tmp/web/%s" % directory
		shutil.rmtree(physicalDirectory)
	if os.path.exists(zipFile):
		print "  Removing old zip file %s" % zipFile
		os.remove(zipFile)

	# Copy the current UFS view to this location
	print "  Copy %s from ufs to tmp/web/%s" % (directory, directory)
	_copyUFS(root, physicalDirectory)

	# Restores JARS from Minestar lib listed in removedjars.txt (removed during Runtime compilation)
	_replaceMissingJarFiles(physicalDirectory)

	# Archive the directory to a zip file
	print "  Archive copy to %s" % zipFile
	shutil.make_archive(physicalDirectory, 'zip', physicalDirectory)

	# Clean up after ourselves
	print "  Remove temporary ufs copy %s" % physicalDirectory
	shutil.rmtree(physicalDirectory)

	# Write the context to point to new zip file
	_writeContext(directory, zipFile)

def _replaceMissingJarFiles(physicalDirectory):
	# Replace any jar files that have been removed the WEB-INF/lib directory.
	webLibDirectory = os.path.join(physicalDirectory, "WEB-INF", "lib")
	missingJarFiles = _findMissingJarFiles(webLibDirectory)
	if len(missingJarFiles) > 0:
		print "  Restoring %s removed jar files." % len(missingJarFiles)
		mstarlibs = mstarpaths.interpretPath("{MSTAR_LIB}")
		for missingJarFile in missingJarFiles:
			# Copy missing jar file from mstar/lib directory to web-inf/lib directory.
			shutil.copy2(os.path.join(mstarlibs, missingJarFile), webLibDirectory)

def _findMissingJarFiles(webLibDirectory):
	# Load the set of jar file names contained in the WEB-INF/lib/removedjars.txt file.
	missingJarFiles = []
	removedJarFiles = os.path.join(webLibDirectory, "removedjars.txt")
	if os.path.isfile(removedJarFiles):
		with open(removedJarFiles) as fp:
			for line in fp:
				for jarFile in [x.strip() for x in line.strip().split(";")]:
					if not jarFile in missingJarFiles:
						missingJarFiles.append(jarFile)
	return missingJarFiles

def _writeContext(directory, zipFile):
	# create a mstar_*.xml context in JETTY_HOME\contexts
	jettyContexts = mstarpaths.interpretPath("{_JETTY_BASE}/webapps")
	if not os.access(jettyContexts, os.F_OK | os.X_OK):
		os.mkdir(jettyContexts)

	jettyWorkDir = mstarpaths.interpretPath("{_JETTY_BASE}/work")
	if not os.access(jettyWorkDir, os.F_OK | os.X_OK):
		os.mkdir(jettyWorkDir) # webapp deployments

	print "  Storing jetty contexts: %s" % jettyContexts
	context = _getContextForWebDirectory(directory)
	print "  Context /%s points to war file %s (%s)" % (context, directory, zipFile)
	contextFileName = os.path.join(jettyContexts, "mstar_" + directory + ".xml");
	#print "Found %s context for %s web directory" % (context, directory)
	file = open(contextFileName, "w")
	file.write("""<?xml version="1.0"  encoding="UTF-8"?>
<!DOCTYPE Configure PUBLIC "-//Jetty//Configure//EN" "http://www.eclipse.org/jetty/configure_9_0.dtd">
<Configure class="org.eclipse.jetty.webapp.WebAppContext">
	<Set name="contextPath">/%s</Set>
	<Set name="war">%s</Set>
	<Set name="extractWAR">true</Set>
	<Set name="defaultsDescriptor"><SystemProperty name="jetty.base" default="."/>/etc/webdefault.xml</Set>
</Configure>
""" % (context, zipFile))
	file.close()

def _getContextForWebDirectory(directory):
	loadedExtensions = mstarpaths.config["LOADED_EXTENSIONS"]
	for e in loadedExtensions:
		if e.webdirectory == directory:
			return e.webcontext
	return None

def _copyUFS(root, physicalDirectory):
	dirs = root.getPhysicalDirectories()
	#print "For UFS %s have physicalDirectories %s" % (root, dirs)
	for src in dirs:
		copytree(src, physicalDirectory)

def copytree(src, dst, symlinks=False, ignore=None):
	"""Recursively copy a directory tree using copy2().

	Blatent copy of http://hg.python.org/cpython/file/2.7/Lib/shutil.py#l145
	The difference is that the destination directory can exist.

	If exception(s) occur, an Error is raised with a list of reasons.

	If the optional symlinks flag is true, symbolic links in the
	source tree result in symbolic links in the destination tree; if
	it is false, the contents of the files pointed to by symbolic
	links are copied.

	The optional ignore argument is a callable. If given, it
	is called with the `src` parameter, which is the directory
	being visited by copytree(), and `names` which is the list of
	`src` contents, as returned by os.listdir():

		callable(src, names) -> ignored_names

	Since copytree() is called recursively, the callable will be
	called once for each directory that is copied. It returns a
	list of names relative to the `src` directory that should
	not be copied.

	XXX Consider this example code rather than the ultimate tool.

	"""
	names = os.listdir(src)
	if ignore is not None:
		ignored_names = ignore(src, names)
	else:
		ignored_names = set()

	if not os.path.exists(dst):
		os.makedirs(dst)

	errors = []
	for name in names:
		if name in ignored_names:
			continue
		srcname = os.path.join(src, name)
		dstname = os.path.join(dst, name)
		try:
			if symlinks and os.path.islink(srcname):
				linkto = os.readlink(srcname)
				os.symlink(linkto, dstname)
			elif os.path.isdir(srcname):
				copytree(srcname, dstname, symlinks, ignore)
			else:
				# Will raise a SpecialFileError for unsupported file types
				shutil.copy2(srcname, dstname)
		# catch the Error from the recursive copytree so that we can
		# continue with other files
		except shutil.Error, err:
			errors.extend(err.args[0])
		except EnvironmentError, why:
			errors.append((srcname, dstname, str(why)))
	try:
		shutil.copystat(src, dst)
	except OSError, why:
		if WindowsError is not None and isinstance(why, WindowsError):
			# Copying file access times may fail on Windows
			pass
		else:
			errors.append((src, dst, str(why)))
	if errors:
		raise shutil.Error, errors



## Main program ##

import minestar, mstarapplib

def main(appConfig=None):
	"""entry point when called from mstarrun"""

	mstarpaths.loadMineStarConfig()

	# Get the web directories that are configured
	print "Generating web directories"
	unpackWebDirectories()
	minestar.exit()

if __name__ == "__main__":
	"""entry point when called from python"""
	main()
