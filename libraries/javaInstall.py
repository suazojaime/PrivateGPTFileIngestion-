import i18n
import minestar
import os

from pathOps import dotExe


class JavaConfigError(RuntimeError):

    """ Class representing java configuration errors. """

    def __init__(self, msg):
        msg = i18n.translate("Java configuration error: ") + msg
        super(JavaConfigError, self).__init__(msg)

def isLinux():
    import sys
    return sys.platform.startswith('linux')


class JavaInstall(object):

    """ Class representing a Java install. """

    def __init__(self, home, homeSource):
        if home is None:
            raise ValueError("No value specified for 'home'")
        self._home = home
        self._homeSource = homeSource or '(unspecified)'
        self._version = None
        self._versionSource = None
        self._javaBinary = None
        self._javawBinary = None

    @property
    def home(self):
        return self._home

    @property
    def homeSource(self):
        return self._homeSource

    @property
    def version(self):
        if self._version is None:
            (self._version, self._versionSource) = self._lookupVersionAndSource()
        return self._version

    @property
    def versionSource(self):
        if self._versionSource is None:
            (self._version, self._versionSource) = self._lookupVersionAndSource()
        return self._versionSource

    @property
    def javaBinary(self):
        if self._javaBinary is None:
            self._javaBinary = self._lookupJavaBinary()
        return self._javaBinary

    @property
    def javawBinary(self):
        if self._javawBinary is None:
            self._javawBinary = self._lookupJavawBinary()
        return self._javawBinary

    def _lookupVersionAndSource(self):
        # Execute java with '-version' option, which should generate output such as:
        #
        #   java version "1.8.0_121"
        #   Java(TM) SE Runtime Environment (build 1.8.0_121-b13)
        #   Java HotSpot(TM) 64-Bit Server VM (build 25.121-b13, mixed mode)
        #
        versionCommandLine = '"%s" -version' % self.javaBinary
        output = minestar.systemEvalErr(versionCommandLine)
        fields = output.split()
        if len(fields) < 3:
            raise JavaConfigError("Cannot determine java version from output '%s'" % output)
        version = fields[2][1:-1]
        versionSource = "(%s)" % versionCommandLine
        return (version, versionSource)

    def _lookupJavaBinary(self):
        # Find java binary in [${jdk}/jre/bin/java${exe}, ${jdk}/bin/java${exe}, ${jdk}/java${exe}].
        javaExe = 'java%s' % dotExe()
        java = os.path.join(self.home, 'jre', 'bin', javaExe)
        if not os.access(java, os.X_OK):
            java = os.path.join(self.home, 'bin', javaExe)
            if not os.access(java, os.X_OK):
                java = os.path.join(self.home, javaExe)
                if not os.access(java, os.X_OK):
                    raise JavaConfigError(i18n.translate("Cannot find '%s'.") % javaExe)
        return java

    def _lookupJavawBinary(self):
        # Find javaw binary in [${jdk}/jre/bin/javaw${exe}, ${jdk}/bin/javaw${exe}],
        # with fallback to java binary.
        javawExe = 'javaw%s' % dotExe()
        javaw = os.path.join(self.home, 'jre', 'bin', javawExe)
        if not os.access(javaw, os.X_OK):
            javaw = os.path.join(self.home, 'bin', javawExe)
            if not os.access(javaw, os.X_OK):
                javaw = self.javaBinary
        return javaw

    @classmethod
    def fromConfig(cls, config):
        """ Get a Java install using the specified config. The config must contain values for MSTAR_INSTALL and EXE. """
        return ConfigJavaInstallFactory(config=config).getJavaInstall()

    @classmethod
    def fromDirectory(cls, directory):
        """ Get a Java install using the specified directory, e.g. 'C:\\Java8'. """
        return JavaInstall(home=directory, homeSource="(configured directory)")


class ConfigJavaInstallFactory:

    """
    Creates a java install object using a M* config. The config should contain
    values for MSTAR_HOME and MSTAR_INSTALL. 

    The following algorithm is used to determine the location of the java install:

    1. JDK derived from the OS:
       - os.environ['JAVA_HOME']

    2. If running within a source repository:
       - ${project.base}/runtime/target/jdk

    3. JDK derived from MSTAR_HOME:
       - ${MSTAR_HOME}/jdk                            (if it exists)
       - ${MSTAR_HOME}/jre                            (if it exists)
       - ${MSTAR_INSTALL}/packages/jdk/${jdk.version} (if MSTAR_HOME is a package)
       - ${MSTAR_INSTALL}/packages/jre/${jre.version} (if MSTAR_HOME is a package)

    4. JDK derived from MSTAR_INSTALL: 
       - ${MSTAR_INSTALL}/jdk
       - ${MSTAR_INSTALL}/jre

    5. JDK derived from finding 'java' on the path.
    
    Note that options (2,3,4) are skipped on linux (since M* only bundles Windows JDK)
    """

    logging = False
    
    def __init__(self, config):
        self.config = config
        from interpreter import Interpreter
        self.interpreter = Interpreter(config)
        self._mstarInstall = None
        self._mstarHome = None
        
    @property    
    def mstarInstall(self):
        if self._mstarInstall is None:
            self._mstarInstall = self.interpretVar('MSTAR_INSTALL')
        return self._mstarInstall
    
    @property
    def mstarHome(self):
        if self._mstarHome is None:
            self._mstarHome = self.interpretVar('MSTAR_HOME')
        return self._mstarHome
    
    def log(self, msg):
        if self.logging:
            print "[JavaInstall] %s" % msg
        
    def getJavaInstall(self):
        (home, homeSource) = self._getJavaHomeAndSource()
        # Cache source of JAVA_HOME for later.
        if 'JAVA_HOME_SOURCE' not in self.config:
            self.config['JAVA_HOME_SOURCE'] = homeSource
        return JavaInstall(home=home, homeSource=homeSource)
    
    def _getJavaHomeAndSource(self):
        # Check OS first.
        (javaHome, javaHomeSource) = self._getJavaFromOS()
        
        # Check source repository, if required.
        if javaHome is None and not isLinux():
            self.log("no JDK from previous process; trying source repository ...")
            (javaHome, javaHomeSource) = self._getJavaFromSourceRepository()
        
        # Check under MSTAR_HOME, if required.
        if javaHome is None and not isLinux():
            self.log("no JDK from source repository; trying MSTAR_HOME ...")
            (javaHome, javaHomeSource) = self._getJavaFromMStarHome()

        # Check the release packages, if required.
        if javaHome is None and not isLinux():
            self.log("no JDK from MSTAR_HOME; trying release packages ...")
            (javaHome, javaHomeSource) = self._getJavaFromReleasePackages()

        # TODO try most recently installed JDK? Unless a newer JDK can be installed?
        
        # Check under MSTAR_INSTALL, if required.
        if javaHome is None and not isLinux():
            self.log("no JDK from release packages; trying MSTAR_INSTALL ...")
            (javaHome, javaHomeSource) = self._getJavaFromMStarInstall()

        # Check the path, if required.
        if javaHome is None:
            self.log("no JDK from MSTAR_INSTALL; trying path ...")
            (javaHome, javaHomeSource) = self._getJavaFromPath()
            
        # Verify that JDK home is defined.
        if javaHome is None:
            msg = i18n.translate("Cannot find Java distribution")
            raise JavaConfigError(msg)

        # Normalize the java home path.
        javaHome = os.path.abspath(javaHome)
        
        # Verify that JDK home exists.
        if not os.access(javaHome, os.F_OK):
            msg = i18n.translate("Java distribution '%s' %s does not exist") % (javaHome, javaHomeSource)
            raise JavaConfigError(msg)

        self.log("home=%s, source=%s" % (javaHome, javaHomeSource))
        
        return (javaHome, javaHomeSource)

    def _getJavaFromOS(self):
        (javaHome, javaHomeSource) = (None, None)
        if 'JAVA_HOME' in os.environ:
            javaHome = os.environ["JAVA_HOME"]
            self.log("found os.environ[JAVA_HOME]=%s" % javaHome)
            # Check if source of JAVA_HOME is from M*, otherwise emit a warning.
            if 'JAVA_HOME_SOURCE' in os.environ:
                javaHomeSource = os.environ['JAVA_HOME_SOURCE']
            else:
                javaHomeSource = "(operating system environment: JAVA_HOME)"
                # Show a warning if java is external to MSTAR_INSTALL.
                if not self._isInternalDirectory(javaHome):
                    print i18n.translate("Warning: Using external JDK (at %s) instead of bundled JDK") % javaHome
                    print i18n.translate("Warning: Recommend unsetting 'JAVA_HOME' environment variable.")
        return (javaHome, javaHomeSource)

    def _isInternalDirectory(self, directory):
        from pathOps import isSubdirectory
        return isSubdirectory(directory, self.mstarInstall)

    def _getJavaFromSourceRepository(self):
        (javaHome, javaHomeSource) = (None, None)
        from sourceRepository import SourceRepository
        sourceRepository = SourceRepository.getInstance(mstarHome=self.mstarHome)
        if sourceRepository.running:
            javaHome = os.path.join(sourceRepository.runtimeDir, 'jdk')
            if not os.path.exists(javaHome):
                raise JavaConfigError("No bundled JDK found at %s" % javaHome)
            javaHomeSource = "(bundled JDK under REPOSITORY_RUNTIME)"
        return (javaHome, javaHomeSource)

    def _getJavaFromMStarHome(self):
        if os.path.exists(self.mstarHome):
            # Check for ${MSTAR_HOME}/jdk
            javaHome = os.path.join(self.mstarHome, 'jdk')
            if os.path.exists(javaHome):
                return (javaHome, '(bundled JDK under MSTAR_HOME)')

            # Check for ${MSTAR_HOME}/jre
            javaHome = os.path.join(self.mstarHome, 'jre')
            if os.path.exists(javaHome):
                return (javaHome, '(bundled JRE under MSTAR_HOME)')
        return (None,None)

    def _getJavaFromReleasePackages(self):
        # Get the mstar instance.
        from install.mstarInstall import MStarInstall
        mstar = MStarInstall.getInstance(self.mstarInstall)
        
        # Check that packages are available.
        if not os.path.exists(mstar.packagesDir):
            return (None, None)

        # Create an mstar release.
        from mstarRelease import MStarRelease
        release = MStarRelease(mstarInstall=self.mstarInstall, mstarHome=self.mstarHome, overrides=self.config)

        # The release may not be fully installed yet.
        if not release.installed:
            return (None, None)
        
        # Check for JDK package, then JRE package.
        for packageName in ['jdk', 'jre', 'openjdk']:
            package = release.getPackage(packageName)
            if package is not None:
                packageDir = mstar.getPackagePath(package)
                if os.path.exists(packageDir):
                    return (packageDir, "(package %s:%s for release %s)" % (package.name, package.version, release.version))
  
        # No jdk/jre packages found for the release.
        return (None, None)

    def _getJavaFromMStarInstall(self):
        javaHome = self.interpretPath('{MSTAR_INSTALL}/jdk')
        if os.path.exists(javaHome):
            return (javaHome, '(bundled JDK under MSTAR_INSTALL)')
        javaHome = self.interpretPath('{MSTAR_INSTALL}/jre')
        if os.path.exists(javaHome):
            return (javaHome, '(bundled JRE under MSTAR_INSTALL)')
        return (None, None)

    def _getJavaFromPath(self):
        import pathOps
        java = pathOps.which('java')
        if java is not None:
            return (os.path.dirname(java), '(on path)')
        return (None, None)
    
    def interpretPath(self, path):
        return self.interpreter.interpretPath(path, self.config)

    def interpretVar(self, var):
        return self.interpreter.interpretVar(var, self.config)
