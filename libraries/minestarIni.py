from abstractIni import AbstractIni


class MineStarIni(AbstractIni):

    """ Operations on the MineStar configuration file """

    def __init__(self, source=None, build=None, builds=None):
        super(MineStarIni, self).__init__(source)
        self._builds = builds
        if build is not None:
            self.build = build
            
    @classmethod
    def filedesc(cls):
        return "MineStar Config"
    
    @classmethod
    def filename(cls):
        return "MineStar.ini"

    @property
    def build(self):
        """ Get the build associated with the default system 'main'. """
        return self.getBuild('main')
    
    @build.setter
    def build(self, build):
        """ Set the build associated with the default system 'main'. """
        self.setBuild(systemName='main', buildName=build)
        
    @property
    def builds(self):
        """ Get the builds (including 'main', if specified). """
        if self._builds is None:
            self._builds = self.__loadBuilds()
        return self._builds
    
    def __loadBuilds(self):
        builds = {}
        for option in self.getOptions('MineStar'):
            if option == 'build':
                builds['main'] = self.getOption('MineStar', option)
            elif option.startswith('build.'):
                system = option[len('build.'):]
                version = self.getOption('MineStar', option)
                builds[system] = version
        return builds
    
    def setBuild(self, *args, **kwargs):
        """ Set the build name for a system name. The system name defaults to 'main' if not specified. """
        # Check that both keywords are specified, or neither.
        if ('systemName' in kwargs) != ('buildName' in kwargs):
            raise RuntimeError("Must specify both systemName and buildName, or neither.")
        # Get the system name and build name (with appropriate defaults).
        systemName = kwargs.get('systemName') or 'main'
        buildName = kwargs.get('buildName') 
        # Check for a call such as setBuild('foo'), which translates to systemName='main' and buildName='foo'.
        if 'systemName' not in kwargs and 'buildName' not in kwargs:
            if len(args) == 1:
                systemName = 'main'
                buildName = args[0]
        # Update or delete entry for the system name.
        if buildName is None:
            if systemName in self.builds:
                del self.builds[systemName]
        else:
            self.builds[systemName] = buildName
        return self
    
    def getBuild(self, systemName=None):
        """ Get the build for the system name. System name defaults to 'main' if not specified. """
        return self.builds.get(systemName or 'main')
    
    # @Override
    def linesToWrite(self):
        lines = ['[MineStar]']
        for (system, build) in self.builds.items():
            if system == 'main':
                lines.append('build=%s' % build)
            else:
                lines.append('build.%s=%s' % (system, build))
        return lines
