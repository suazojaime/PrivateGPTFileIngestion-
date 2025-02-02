import os
import zipfile

from abc import ABCMeta, abstractmethod


class AbstractConfig(object):

    """ Base class for configurations. """

    __metaclass__ = ABCMeta
    
    def __init__(self):
        self.path = None

    @classmethod
    def filename(cls):
        """ Get the filename used by the configuration. """
        raise NotImplementedError("No 'filename' implemented.")

    @classmethod
    def filedesc(cls):
        """ Get the description used by the configuration, e.g. 'MineStar Config', etc. """
        raise NotImplementedError("No 'filedesc' implemented.")

    @abstractmethod
    def dump(self):
        """ Dumps the config to a string. """
        raise NotImplementedError()

    def store(self, path=None):
        """
        Store the configuration to the path.

        :param path the path for storing the configuration. If the path is a directory,
        the configuration is stored to the default file name in that directory.

        :return the path to the file that was used for storing the configuration.
        """
        # Check that a path is specified.
        if path is None:
            if self.path is None:
                raise ValueError("Cannot store %s: no path specified." % self.filedesc())
            path = self.path
        # If the path is a directory, use the default file name.
        if os.path.isdir(path):
            path = os.path.join(path, self.filename())
        # Check that the parent directory is accessible.
        parent = os.path.dirname(path)
        if not os.access(parent, os.F_OK):
            raise IOError("Cannot store %s: cannot access directory '%s'." % (self.filedesc(), parent))
        # Open the file and delegate to the implementation.
        with open(path, 'wt') as f:
            self.writefp(f)
        # Cache the path for later. 
        self.path = path
        return path

    @abstractmethod
    def writefp(self, f):
        """ Store the configuration to the specified file object. """
        raise NotImplementedError()

    @classmethod
    def load(cls, path, create=False):
        """
        Load the configuration from the path. The 'path' attribute of the configuration
        is updated to the actual path from which the configuration was loaded, so that
        a store() operation (without specifying the path) may succeed.

        :param path the path for loading the configuration. If the path is a directory,
        the configuration is loaded from the default file name in that directory. If
        the path is an archive (e.g. a zip file), the configuration is loaded from the
        default file name in the top-level directory of the archive.

        :param create create the config if it does not exist. This does not create the
        config file; the config.store() operation must still be used. Defaults to False.

        :return the configuration object loaded from the path.
        """
        # Check that a path is specified.
        if path is None:
            raise ValueError("Cannot load %s: no path specified." % cls.filedesc())
        # If the path is a zipfile, load the embedded configuration file.
        if zipfile.is_zipfile(path):
            return cls._loadFromZipFile(path)
        # If the path is a directory, use the default file name.
        if os.path.isdir(path):
            path = os.path.join(path, cls.filename())
        # Check if loading an existing config or creating a new config.
        if os.access(path, os.F_OK):
            with open(path, 'rt') as f:
                config = cls.readfp(f)
        elif create:
            config = cls()
        else:
            raise IOError("Cannot load %s: cannot access path '%s'." % (cls.filedesc(), path))
        # Cache the path for future store() operations.
        config.path = path
        return config

    @classmethod
    def loadOrCreate(cls, path):
        """ Loads a config from the path (if it exists), otherwise creates a new config. """
        return cls.load(path=path, create=True)

    @classmethod
    def _loadFromZipFile(cls, path):
        z = None
        try:
            z = zipfile.ZipFile(path)
            try:
                f = z.open(cls.filename(), 'r')
            except KeyError:
                raise IOError("Cannot find '%s' in archive '%s'." % (cls.filename(), path))
            try:
                return cls.readfp(f)
            finally:
                f.close()
        finally:
            if z is not None:
                z.close()

    @classmethod
    def readfp(cls, f):
        """ Load the configuration from the specified file object. """
        raise NotImplementedError()

    @classmethod
    def containsConfig(cls, directory):
        """ Determines if the directory contains the configuration. """
        if directory is None:
            raise ValueError("Cannot find %s: no directory specified." % cls.filedesc())
        # Verify that ${directory}/${filename} can be accessed.
        path = os.path.join(directory, cls.filename())
        return os.access(path, os.F_OK)
