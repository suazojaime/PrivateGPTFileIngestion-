import os
import shutil
import stat

class FileOps:
    
    """ Interface for file operations."""

    def __isDirResource(self, resource):
        return os.path.exists(resource) and os.path.isdir(resource)

    def copyResource(self, src, dest, options={}):
        """ 
        Copy a resource (either a file or a directory). 
        
        The following options are supported:
        
        'backup' - indicates if a backup of the resource should be created. Only applies
        to file resources at this time. Defaults to False. The options as specified for
        the backupFile() operation also apply.
        """
        return self.copyDir(src,dest) if self.__isDirResource(src) else self.copyFile(src, dest, options)

    def moveResource(self, src, dest, options={}):
        """ 
        Move a resource, which can be a file or a directory. 
        
        The following options are supported:
        
        'backup' - indicates if a backup of the resource should be created. Only applies
        to file resources at this time. Defaults to False. The options as specified for
        the backupFile() operation also apply.
        """
        return self.moveDir(src, dest) if self.__isDirResource(src) else self.moveFile(src, dest, options)

    def removeResource(self, path, options={}):
        """ 
        Remove a resource (either a file or a directory). 
        
        The following options are supported:
        
        'backup' - indicates if a backup of the resource should be created. Only applies
        to file resources at this time. Defaults to False. The options as specified for
        the backupFile() operation also apply.
        """
        return self.removeDir(path) if self.__isDirResource(path) else self.removeFile(path, options)

    def createFile(self, path, options={}):
        """ 
        Create an empty file at the specified path. Creates any intermediate directories if
        required. Returns True if the file was created, False otherwise. 
        
        The following options are supported:
        
        'backup' - indicates if a backup of the destination file should be created. Defaults
        to False. The options as specified for the backupFile() operation also apply.
        """
        raise NotImplementedError("'createFile' not implemented!")

    def backupFile(self, file, options={}):
        """ 
        Create a backup of the file, returning the path to the backup file, or None if the
        original file does not exist.
        
        The following options are supported:
        
        'backup.file' - the path to the backup file. If not specified on input, then the backup
        file is created in the backup directory (see below) and has the same name as the original
        file, with the backup suffix (see below) appended. On output, contains the fully qualified
        path to the backup file.
        
        'backup.dir'  - the directory for storing backup files. If not specified, then the parent
        directory of the original file is used.               
                   
        'backup.suffix' - the suffix to use when backing up the original file. Defaults to 
        ".original". For example, if the original file has the base name 'foo.txt' then the
         backup file will have the base name 'foo.txt.original'. 
          
        'backup.overwrite' - indicates if the backup file can overwrite an existing file of 
        the same name. Defaults to True. If set to False, backup files will have numbers 
        appended until a unique file name is found.
        
        Examples:
        1. Backup a file: 
        
           backupFile = fileOps.backupFile('/x/y/foo.txt')
           assert os.path.exists(backupFile)
           
        2. Backup the original file to a specific file:
                           
           backupFile = '/x/y/foo.txt.bak'
           assert not os.path.exists(backupFile)
                           
           backupFile = fileOps.backupFile('/x/y/foo.txt', {'backup.file':backupFile})
           assert os.path.exists(backupFile)
           
        4. Backup the original file to a specific directory.
           
           backupFile = fileOps.backupFile('/x/y/foo.txt', {'backup.dir':'/tmp')
           assert os.path.exists(backupFile)
           assert os.path.dirname(backupFile)) == '/tmp'
        
        """
        raise NotImplementedError()
    
    def moveFile(self, src, dest, options={}):
        """ 
        Move a file from 'src' to 'dest', e.g. moveFile('/x/y/foo.txt', '/x/y/bar.txt'). 
        
        The following options are supported:
        
        'backup' - indicates if a backup of the destination file should be created. Defaults
        to False. The options as specified for the backupFile() operation also apply.
        
        'overwrite' - indicates if overwriting destination file is permitted. Defaults to False.

        Returns True if the file was moved from 'src' to 'dest'; False otherwise.
        """
        raise NotImplementedError("'moveFile' not implemented!")

    def copyFile(self, src, dest, options={}):
        """ 
        Copy a file from 'src' to 'dest', e.g copyFile('/x/y/foo.txt', '/x/y/bar.txt'). 
        
        The following options are supported:
        
        'backup' - indicates if a backup of the destination file should be created. Defaults
        to False. The options as specified for the backupFile() operation also apply.
        """
        raise NotImplementedError("'copyFile' not implemented!")

    def removeFile(self, path, options={}):
        """ 
        Remove the file at the specified path. 
        
        The following options are supported:
        
        'backup' - indicates if a backup of the file should be created. Defaults
        to False. The options as specified for the backupFile() operation also apply.
        """
        raise NotImplementedError("'removeFile' not implemented")

    def createDir(self, path, options={}):
        """
         Create a directory at the specified path. Also creates intermediate directories.
         
         Returns True if the directory was created, False otherwise. 
         
        The following options are supported:
        
        'backup' - indicates if a backup of the file should be created. Defaults
        to False. The options as specified for the backupFile() operation also apply.
        """
        raise NotImplementedError("'createDir' not implemented!")

    def moveDir(self, src, dest, options={}):
        """ Move a directory tree from 'src' to 'dest'. No options supported yet. """
        raise NotImplementedError("'moveDir' not implemented!")
    
    def copyDir(self, src, dest, options={}):
        """ 
        Copy a directory tree from 'src' to 'dest' 
        
        The following options are supported:
        
        'symlinks' - Indicates if symbolic links should be copied. Defaults to True.
        'ignore' - A callable that determines which contents of a directory should be ignored.
        """
        raise NotImplementedError("'copyDir' not implemented!")
    
    def removeDir(self, dir, options={}):
        """ Remove a directory tree. No options supported yet. """
        raise NotImplementedError("'removeDir' not implemented!")
    
    def writeLines(self, path, lines):
        """ Write lines to the file at the path. """
        raise NotImplementedError("'writeLines' not implemented!")
    
    def createSymbolicLink(self, link, target, options={}):
        """ Create a symbolic link to the target. No options supported yet. """
        raise NotImplementedError("'createSymbolicLink' not implemented!")

    def removeSymbolicLink(self, link, options={}):
        """ Remove a symbolic link. No options supported yet. """
        raise NotImplementedError("'removeSymbolLink' not implemented!")

    @staticmethod
    def getFileOps(options={}):
        # Use either system ops or faux ops.
        ops = FauxFileOps() if FileOps.__useFauxOps(options) else SystemFileOps()
        # Wrap a logger around the ops, if required.
        if FileOps.__useLogging(options):
            ops = LoggingFileOps(ops)
        return ops

    @staticmethod
    def __useFauxOps(options=None):
        return getBooleanValue('faux', options)

    @staticmethod
    def __useLogging(options=None):
        return getBooleanValue('logging', options)

def getBooleanValue(name, properties):
    if properties is not None:
        if name in properties:
            value = properties[name]
            if value is not None:
                return value is True or value == 'true'
    return False

class LoggingFileOps(FileOps):
    
    """ Implementation of FileOps that logs the operation before delegating to actual FileOps. """

    def __init__(self, delegate):
        self._delegate = delegate
        
    @property
    def delegate(self):
        return self._delegate

    # @Override
    def backupFile(self, file, options={}):
        print "Backing up file '%s' ..." % file
        return self.delegate.backupFile(file, options)
    
    # @Override
    def createFile(self, path, options={}):
        print "Creating file at '%s'" % path
        return self.delegate.createFile(path, options)

    # @Override
    def moveFile(self, src, dest, options={}):
        print "Moving file from '%s' to '%s'" % (src, dest)
        return self.delegate.moveFile(src, dest, options)

    # @Override
    def copyFile(self, src, dest, options={}):
        print "Copying file from '%s' to '%s'" % (src, dest)
        self.delegate.copyFile(src, dest, options)
        
    # @Override
    def removeFile(self, path, options={}):
        print "Removing file '%s'" % path
        self.delegate.removeFile(path, options)

    # @Override
    def createDir(self, path, options={}):
        print "Creating directory at '%s'" % path
        return self.delegate.createDir(path, options)

    # @Override
    def moveDir(self, src, dest, options={}):
        print "Moving directory from '%s' to '%s'" % (src, dest)
        self.delegate.moveDir(src, dest, options)
        
    # @Override
    def copyDir(self, src, dest, options={}):
        print "Copying directory from '%s' to '%s'" % (src, dest)
        self.delegate.copyDir(src, dest, options)

    # @Override
    def removeDir(self, dir, options={}):
        print "Removing directory '%s'" % dir
        self.delegate.removeDir(dir, options)

    # @Override
    def writeLines(self, path, lines):
        print "Writing %s lines to file '%s'" % (len(lines), path)
        self.delegate.writeLines(path, lines)
        
    # @Override
    def createSymbolicLink(self, link, target, options={}):
        print "Creating symbolic link from '%s' to '%s'" % (link, target)
        return self.delegate.createSymbolicLink(link, target, options)

    # @Override
    def removeSymbolicLink(self, link, options={}):
        print "Removing symbolic link '%s'" % link
        return self.delegate.removeSymbolicLink(link, options={})

class FauxFileOps(FileOps):

    """ Faux implementation of FileOps interface that writes what it does to StdOut. """

    # @Override
    def backupFile(self, file, options={}):
        print "  (Pretending to backup file at '%s')" % file
        return file
    
    # @Override
    def createFile(self, path, options={}):
        print "  (Pretending to create file at '%s')" % path
        return True

    # @Override
    def moveFile(self, src, dest, options={}):
        print "  (Pretending to move file from '%s' to '%s')" % (src, dest)
        return True

    # @Override
    def copyFile(self, src, dest, options={}):
        print "  (Pretending to copy file from '%s' to '%s')" % (src, dest)
        return True

    # @Override
    def removeFile(self, path, options={}):
        print "  (Pretending to remove file at '%s')" % path
        return True

    # @Override
    def createDir(self, path, options={}):
        print "Creating directory at '%s'" % path
        return self.delegate.createDir(path)

    # @Override
    def moveDir(self, src, dest, options={}):
        print "  (Pretending to move directory from '%s' to '%s')" % (src, dest)
        return True

    # @Override
    def copyDir(self, src, dest, options={}):
        print "  (Pretending to copy directory from '%s' to '%s')" % (src, dest)
        return True

    # @Override
    def removeDir(self, dir, options={}):
        print "  (Pretending to remove directory '%s')" % dir
        return True

    # @Override
    def writeLines(self, path, lines):
        print "  (Pretending to write %s lines to file: %s)" % (len(lines), path)
        for line in lines:
            print "    -> %s" % line
        return True

    # @Override
    def createSymbolicLink(self, link, target, options={}):
        print "  (Pretending to create symbolic link from '%s' to '%s')" % (link, target)
        return True

    # @Override
    def removeSymbolicLink(self, link, options={}):
        print "  (Pretending to remove symbolic link '%s')" % link
        return True

class Backups(object):
    
    def __init__(self, options={}):
        self._options = options
        self._backupFile = options.get('backup.file')
        self._backupDir = options.get('backup.dir')
        self._backupSuffix = options.get('backup.suffix') or '.original'
        self._required = options.get('backup') or options.get('backup.file') or options.get('backup.dir')
        self._overwrite = options.get('backup.overwrite')
        if self._overwrite is None:
            self._overwrite = True
            
    @property
    def required(self):
        return self._required
    
    def getBackupFile(self, file):
        """ Get the path to the backup file. """
        if self._backupFile is None:
            self._backupFile = self._options.get('backupFile') or self._findBackupFilePath(file)
        return self._backupFile
        
    def getBackupDir(self):
        """ Get the backup directory, if specified. """
        return self._backupDir
    
    def getBackupSuffix(self):
        return self._backupSuffix
    
    def _findBackupFilePath(self, file):
        # Get initial backup file name, in parent directory or backup directory.
        backupDir = self._backupDir or os.path.dirname(file)
        
        # Create the backup directory, if required.
        if not os.path.exists(backupDir):
            try:
                os.makedirs(backupDir)
            except os.error as e:
                if not os.path.exists(backupDir):
                    raise e
                
        # Create the backup file name.    
        backupFile = os.path.join(backupDir, os.path.basename(file) + self._backupSuffix)
        
        # If the backup file exists and cannot overwrite, then find a unique backup file name.    
        if os.path.exists(backupFile) and not self._overwrite:
            counter = 1
            while os.path.exists(backupFile + ".%d" % counter):
                counter = counter + 1
            backupFile = backupFile + ".%d" % counter
        
        return backupFile
    
class SystemFileOps(FileOps):

    """ Default implementation of FileOps interface that delegates to the underlying system. """

    # @Override
    def backupFile(self, file, options={}):
        backupFile = None
        if os.path.exists(file):
            backupFile = self._backupFile(file, Backups(options or {}))
        return backupFile

    def _backupFile(self, file, backups):
        backupFile = backups.getBackupFile(file)
        self.copyFile(src=file, dest=backupFile, options=None)
        return backupFile
    
    def _backupFileIfRequired(self, file, options):
        if os.path.exists(file):
            backups = Backups(options)
            if backups.required:
                return self._backupFile(file, backups)

    # @Override
    def createFile(self, path, options={}):
        # Create the parent directories if required.
        parentDir = os.path.dirname(path)
        if not os.path.exists(parentDir) and not self.createDir(parentDir):
            return False
        # Open new file (or truncate existing file).
        try:
            with open(path, 'w') as f:
                return True
        except:
            return False

    # @Override
    def moveFile(self, src, dest, options={}):
        def exists(p):
            return os.access(p, os.F_OK)
        def isFile(p):
            return exists(p) and os.path.isfile(p)
        def isDirectory(p):
            return exists(p) and os.path.isdir(p)

        # Check that the source exists and is a file.
        if not exists(src):
            raise IOError("Cannot move file: source '%s' does not exist.")
        if not isFile(src):
            raise IOError("Cannot move file: source '%s' is not a file.")

        # If the destination exists and is a directory, convert to file path.
        if isDirectory(dest):
            dest = os.path.join(dest, os.path.basename(src))
            
        # Check if the destination file already exists.
        if isFile(dest):
            # Check if overwriting the file is permitted.
            if not self._overwriteFile(options):
                return False
            
            # Remove the destination file (will create backup if necessary).
            self.removeFile(dest, options)

        # Create backup of the destination file (if required).
        if isFile(dest):
            self._backupFileIfRequired(dest, options or {})

        # Move (or rename) the file.
        shutil.move(src, dest)

        return not exists(src) and exists(dest)

    def _overwriteFile(self, options={}):
        return options.get('overwrite', False)
    
    # @Override
    def copyFile(self, src, dest, options={}):
        self._backupFileIfRequired(dest, options or {})
        shutil.copy2(src,dest)

    # @Override
    def removeFile(self, path, options={}):
        self._backupFileIfRequired(path, options or {})
        os.remove(path)

    # @Override
    def createDir(self, path, options={}):
        try:
            os.makedirs(path)
            return True
        except:
            return False

    # @Override
    def moveDir(self, src, dest, options={}):
        shutil.move(src,dest)

    # @Override
    def copyDir(self, src, dest, options={}):
        symlinks = options.get('symlinks', True)
        ignore = options.get('ignore', None)
        # Check if allowed to overwrite the destination directory.
        overwrite = options.get('overwrite', True)
        if not overwrite and os.path.exists(dest):
            raise IOError("Cannot copy directory %s to %s: destination directory already exists")
        # Copy the source directory over the target directory.
        _copyTree(src=src, dest=dest, symlinks=symlinks, ignore=ignore)
    
    # @Override
    def removeDir(self, dir, options={}):
        if os.access(dir, os.F_OK):
            shutil.rmtree(path=dir, ignore_errors=False)
        
    # @Override    
    def writeLines(self, path, lines):
        with file(path, 'w') as f:
            for line in lines:
                f.write(line + '\n')

    # @Override
    def createSymbolicLink(self, link, target, options={}):
        import symlink
        return symlink.createSymbolicLink(link, target)

    def removeSymbolicLink(self, link, options={}):
        import symlink
        return symlink.removeSymbolicLink(link)

def _copyTree(src, dest, symlinks=True, ignore=None):
    # Create destination directory if required.
    if not os.path.exists(dest):
        os.makedirs(dest)
    
    # Get the list of items in the source directory, and which items to ignore (if any).    
    items = os.listdir(src)
    ignoredItems = [] if ignore is None else ignore(src, items)
    
    errors = []
    
    # Recursively copy each item in the source directory.
    for item in items:
        if item in ignoredItems:
            continue
        s = os.path.join(src, item)
        d = os.path.join(dest, item)
        try:
            if symlinks and os.path.islink(s):
                os.symlink(os.readlink(s), d)
            elif os.path.isdir(s):
                _copyTree(s, d, symlinks, ignore)
            else:
                shutil.copy2(s, d)
        except Exception as e:
            errors.append(e)
            
    # Copy the file stats (if possible).
    try:
        shutil.copystat(src, dest)
    except OSError as why:
        if WindowsError is not None and isinstance(why, WindowsError):
            # Copying file access times may fail on Windows
            pass
        errors.append(e)
    
    if errors:
        raise IOError(error)
