from com.mincom.base.resource import ResourceManager
from com.mincom.util.job import AbstractManagedJob
from com.mincom.util.job import JobState
from com.mincom.util.text import LocalisableString
from java.util import Arrays
import jarray
import java

class PythonCountDownTask(AbstractManagedJob):
    global rp;

    def __init__(self, name, context):
        AbstractManagedJob.__init__(self, name, context)
        self.rp = ResourceManager.getProvider();
        self.nrSteps = self.getContext().getAttribute('nrSteps')
    
    def mainProcess(self):
        for x in range(self.nrSteps):
            if self.checkAbort():
                self.invokeOnAbort()
                return

            progress = x * 100 / self.nrSteps;
            self.getContext().putAttribute(JobState.ATTR_PROGRESS_PERCENT, progress);
            self.invokeOnTaskChange('Task ' + str(x+1))
            self.invokeOnMessage(LocalisableString(self.rp.getResource(None, ("Count down starting... " + str(x)))));
            java.lang.Thread.sleep(1000);
            self.invokeOnMessage(LocalisableString(self.rp.getResource(None, ("Count down finished... " + str(x)))));

    def getSubTasks(self):
        knownSteps = []
        for x in range(self.nrSteps):
            knownSteps.append('Task ' + str(x+1))
        return Arrays.asList(jarray.array(knownSteps, java.lang.String))
