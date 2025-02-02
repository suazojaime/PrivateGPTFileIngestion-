import os, time, mstarpaths, minestar
logger = minestar.initApp()
OLD_FILE = 3600

class MutexError(IOError):
    """ Default error """


class Mutex(object):
    """A simple mutex, based on creating a locked file, compatible with windows and Linux.
    """

    def __init__(self, name, timeout=5, step=0.1):
        """
        Create a ``Lock`` object on ``name``

        ``timeout`` the time (s) to wait before timing out attempting to acquire the lock.

        ``step`` is the number of seconds to wait between attempts to acquire the lock.

        """
        self.timeout = timeout
        self.step = step
        tempDir = mstarData = mstarpaths.interpretPath("{MSTAR_TEMP}")
        self.filename = os.path.sep.join([tempDir, name])
        self.locked = False
        #logger.info("Mutex created for file %s" % self.filename)
        self.deleteAncientLockFile()


    def deleteAncientLockFile(self):
        if os.path.exists(self.filename):
            #logger.info("deleteAncientLockFile: Mutex file %s already exists - seeing if it is very old" % self.filename)
            try:
                s = os.stat(self.filename)
                ageInSeconds = time.time() - s.st_ctime
                if ageInSeconds >= OLD_FILE:
                    #logger.info("deleteAncientLockFile: Mutex file %s is very old - removing" % self.filename)
                    os.rmdir(self.filename)
            except os.error, err:
                #logger.info("deleteAncientLockFile: Mutex file %s exists, but unable to see if it is very old and remove it: error %s " % (self.filename,str(err)))
                raise MutexError(str(err))

    def lock(self, force=False):
        """
        If ``force`` is ``False`` (the default), then on timeout a ``MutexError`` is raised.
        If ``force`` is ``True``, then on timeout we forcibly acquire the lock.
        """
        #logger.info("Mutex.lock: Locking mutex file %s: locked = %s" % (self.filename,self.locked))
        #(drive,tail) = os.path.splitdrive(os.getcwd())
        #logger.info("Mutex.lock: Current Drive %s and directory %s " % (drive,tail))
        if self.locked:
            #logger.info("Mutex.lock: Unable to lock mutex file %s as it is already locked %s " % (self.filename,e))
            raise MutexError('%s is already locked' % self.filename)
        t = 0
        e = ''
        #logger.info("Mutex.lock: self.timeout = %s: self.step = %s" % (self.timeout,self.step))
        while t < self.timeout:
            t += self.step
            try:
                #logger.info("Mutex.lock: Attempting to create directory %s (t=%s)" % (self.filename,t))
                os.makedirs(self.filename)
                #logger.info("Mutex.lock: Finished creating directory %s (t=%s)" % (self.filename,t))
            except os.error, err:
                #logger.info("Mutex.lock: 2 Exception caught (t=%s)" % t)
                e = str(err)
                #logger.info("Mutex.lock: 2 Exception %s (t=%s)  - sleeping ..." % (e,t))
                time.sleep(self.step)
                #logger.info("Mutex.lock: 2 Exception sleep finished (t=%s)" % t)
            except:
                #logger.info("Mutex.lock: 3 Exception caught (t=%s)" % t)
                time.sleep(self.step)
                #logger.info("Mutex.lock: 3 Exception sleep finished (t=%s)" % t)
            else:
                self.locked = True
                #logger.info("Mutex.lock: Exception else: Finished - returning")
                return
        if force:
            self.locked = True
        else:
            raise MutexError('Failed to acquire lock on %s: %s' % (self.filename, e))

    def isLocked(self):
        return self.locked

    def release(self):
        """
        Release the lock.

        If ``ignore`` is ``True`` and removing the lock directory fails, then
        the error is not used. (could happen if the lock was acquired via a timeout.)
        """
        #logger.info("Mutex.release: Releasing mutex lock file %s: locked = %s " % (self.filename,self.locked))
        if not self.locked:
            #logger.info("Mutex.release: Can't release mutex lock file %s as it is not locked " % self.filename)
            raise MutexError('%s is not locked' % self.filename)
        self.locked = False
        t = 0
        e = ''
        while t < self.timeout and os.path.exists(self.filename):
            t += self.step
            try:
                os.rmdir(self.filename)
            except os.error, err:
                e = str(err)
                time.sleep(self.step)
        if os.path.exists(self.filename):
            #logger.info("Mutex.release: Unable to unlock mutex lock file %s - error is %s " % (self.filename,e))
            raise MutexError("Unable to unlock file %s: %s" % (self.filename, e))

    def getFilename(self):
        return self.filename

    def __del__(self):
        if self.locked:
            self.release()

