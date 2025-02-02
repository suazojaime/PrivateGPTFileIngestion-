from abstractIni import AbstractIni
from timestamps import Timestamp


class TimestampedConfig(AbstractIni):

    """ A configuration that adds a [Timestamps] section with created/modified timestamps. """

    def __init__(self, source=None):
        super(TimestampedConfig, self).__init__(source)
        self._created = None
        self._modified = None

    @property
    def created(self):
        if self._created is None:
            self._created = self.getOptionWithDefault('Timestamps', 'created', Timestamp.now())
        return self._created

    @created.setter
    def created(self, created):
        self._created = created

    @property
    def modified(self):
        if self._modified is None:
            self._modified = self.getOptionWithDefault('Timestamps', 'modified', self.created)
        return self._modified

    @modified.setter
    def modified(self, modified):
        self._modified = modified

    # @Override
    def writefp(self, fp):
        # Update the modified time before writing the config.
        self.modified = Timestamp.now()
        super(TimestampedConfig, self).writefp(fp)

    # @Override
    def linesToWrite(self):
        return self._getTimestampSectionLines()

    def _getTimestampSectionLines(self):
        return ['[Timestamps]', 'created=%s' % self.created, 'modified=%s' % self.modified]
