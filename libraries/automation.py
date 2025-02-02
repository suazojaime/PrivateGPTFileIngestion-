class DateChooser:
    def __init__(self, java):
        self.java = java
        self.top = java.getComponents()[0]
        self.left = self.top.getComponents()[0].getComponents()[0]
        self.right = self.top.getComponents()[1].getComponents()[0]
        self.monthLabel = self.top.getComponents()[2].getComponents()[0]
        self.yearLabel = self.top.getComponents()[2].getComponents()[1]

    def getMonth(self):
        return self.monthLabel.getText()

    def getYear(self):
        return self.yearLabel.getText()

    def getMonthYear(self):
        return "%s %s" % (self.getMonth(), self.getYear())

    def getDatesPanel(self):
        return self.java.getComponents()[1].getComponents()[2]

    def click(self, n):
        if type(n) != type(""):
            n = str(n)
        dates = self.getDatesPanel().getComponents()
        for date in dates:
            if n == date.getText():
                fg = date.getForeground()
                if fg.red == fg.blue and fg.blue == fg.green:
                    click(date)
                    return
        fail("Could not find date %s" % n)

from java.lang import Runnable

class SliderSetter(Runnable):
    def __init__(self, component, n):
        self.component = component
        self.n = n

    def run(self):
        # TODO - use mouse stuff to do this
        self.component.setValue(self.n)

from com.mincom.jive.automation import AutomationAccess
from minestar.platform.ufs import UFS
from javax.swing import SwingUtilities
from java.lang import System
import time

java = AutomationAccess.getInstance()
languageCode = System.getProperty("user.language")

windows = []
WINDOW_CLASS = "java.awt.Window"
DIALOG_CLASS = "javax.swing.JDialog"
languages = {"en": {}}

def tr(phrase):
    """Translates a given phrase for internationalisation testing."""
    if phrase is None:
        return None
    joinPhrase = ".*"
    # don't translate wildcards
    if not (phrase.startswith('{') and phrase.endswith('}')):
        return ".*".join([trans(s) for s in phrase.split(".*")])
    else:
        for tmpPhrase in phrase.split('/'):
            for chr in tmpPhrase.split(".*"):
                if not chr=='{' or chr=='}':
                    joinPhrase.join(trans(chr))
    return joinPhrase

def trans(phrase):
    if phrase is not None and (phrase != ''):
        if type(phrase) == type(''):
            if languageCode == 'en':
                return phrase
            elif languageCode in ['xx', 'zz']:
                return languageCode+phrase
            else:
                return translate(phrase, languageCode)
        else:
            fail("Type for phrase: '"+str(phrase)+"' must be 'string' not '"+str(type(phrase))+"'.")
    else:
        return phrase

def loadLanguage(lang):
    if languages.get(lang) is not None:
        return
    ufsRoot = UFS.getRoot()
    pbDir = ufsRoot.getSubdir("phrasebooks")
    dict = {}
    if pbDir is not None:
        pbFiles = pbDir.listFiles()
        for phbk in pbFiles:
            if not phbk.getName().endswith(("%s.txt"%lang)):
                continue
            for line in phbk.getTextContent().split("\n"):
                fields = line.split("\t")
                if len(fields) != 3:
                    continue
                dict[fields[1]] = fields[2]
    languages[lang] = dict

def translate(key, lang):
    loadLanguage(lang)
    if not languages.has_key(lang):
        return key
    before = ""
    after = ""
    while key.startswith(' '):
        key = key[1:]
        before = before + ' '
    while key.endswith(' '):
        key = key[:-1]
        after = after + ' '
    if languages[lang].has_key(key):
        result = languages[lang][key]
        if result is None or result == "":
            return "[%s]" % key
        return before + result + after
    else:
        return before + key + after

def isTranslated(key, lang):
    loadLanguage(lang)
    if not languages.has_key(lang):
        return 0
    if languages[lang].has_key(key):
        return 1
    else:
        return

def flushEventQueue():
    java.flushEventQueue()

def setSliderPercentage(slider, percent):
    c = getComponent(slider)
    if c is None:
        fail("Can't find slider " + slider)
    min = c.getMinimum()
    max = c.getMaximum()
    wanted = min + (max - min) * percent / 100
    SwingUtilities.invokeLater(SliderSetter(c, wanted))
    flushEventQueue()

def screenshot(filename):
    java.screenshot(windows[-1], filename)

def fail(message):
    print message
    java.fail(message)

def show():
    """Pop-up component name window"""
    java.show()

def findWindow(pattern, timeout=1):
    return java.findWindow(pattern, timeout, WINDOW_CLASS)

def findWindows(pattern, javaClass=WINDOW_CLASS):
    return java.findWindows(pattern, javaClass)

def findDialog(pattern, timeout=1):
    return java.findWindow(pattern, timeout, DIALOG_CLASS)

def window(pattern, timeout=20, javaClass=WINDOW_CLASS):
    if type(pattern) == type(""):
        w = java.findWindow(pattern, timeout, javaClass)
        if w is None:
            fail("Can't find window " + pattern + " only " + `[w.getTitle() for w in java.getAllWindows(".*", javaClass)]`)
    else:
        w = pattern
    global windows
    windows.append(w)
    assertTrue('FATNESSE: Found Window with Pattern: '+str(pattern),True)
    return w

def allWindows(pattern=".*", javaClass=WINDOW_CLASS):
    list = java.getAllWindows(pattern, javaClass)
    result = []
    for i in range(list.size()):
        result.append(list.get(i))
    return result

def dialog(pattern, timeout=5, javaClass=DIALOG_CLASS):
    w = java.findWindow(pattern, timeout, javaClass)
    if w is None:
        fail("Can't find dialog " + pattern)
    global windows
    windows.append(w)
    return w

def windowExist(pattern, timeout=5):
    """Checks if a window exists given a pattern, returns True or False."""
    w = findWindow(pattern, timeout)
    if w is None:
        return False
    else:
        window(pattern, timeout)
        return True

def dialogExist(pattern, timeout=5):
    d = findDialog(pattern, timeout)
    if d is None:
        return False
    else:
        dialog(pattern, timeout)
        return True

def componentExist(componentName):
    c = getComponent(componentName)
    if c is None:
        return False
    else:
        return True

def checkExist(*componentName):
    """Checks that one or more component(s) exists on screen"""
    flushEventQueue()
    for name in componentName:
        if getComponent(name) is not None:
            assertTrue("Component '"+name+"'  cannot IS visible.",True)
        else:
            assertTrue("Component '"+name+"'  cannot IS NOT visible.",False)
    return True


def checkEnabled(*componentName):
    flushEventQueue()
    result = False
    timeout = 4
    for name in componentName:
        assertTrue("Component name is None", name is not None)
        n = name
        if type(n) != type(""):
            if n.getName() is not None:
                n = n.getName()
            else:
                n = str(n.getClass())
        if getComponent(name) is not None:
            if getComponent(name).isEnabled():
                result = True
            else:
                while timeout > 0:
                    timeout -= 1
                    time.sleep(1)
                    if getComponent(name).isEnabled():
                        result = True
                        break
            if result:
                assertTrue('Component ' + n + ' is enabled')
            else:
                assertTrue('Component ' + n + ' is not enabled',False)

        else:
            assertTrue("Can not locate component '"+n+"'  to check if enabled.",False)
    return result

def checkDisabled(*componentName):
    flushEventQueue()
    for name in componentName:
        n = name
        if type(n) != type(""):
            n = n.getName()
        if getComponent(name) is not None:
            if not getComponent(name).isEnabled():
                assertTrue('Component '+n+ ' is disabled')
            else:
                assertTrue('Component '+n+ ' is not disabled',False)
        else:
            assertTrue("Can not locate component '"+n+"'  to check if disabled.",False)
    return True

def clicks(*components):
    for c in components:
        click(c)
        sleep(1)

def click(componentName, count=1, shift=0, control=0):
    c = getComponent(componentName)
    if c is None:
        fail("Can't find component " + componentName)
    java.click(c, count, shift, control, 0)

def clickComponent(component, count=1, shift=0, control=0):
    java.click(component, count, shift, control, 0)

def treeclick(componentName, path, count=1, shift=0, control=0, right=0):
    c = getComponent(componentName)
    if c is None:
        fail("Can't find component " + componentName)
    java.treeClick(c, path, count, shift, control, right)

def tableclick(componentName, colName, rowNum, count=1, shift=0, control=0, right=0):
    c = getComponent(componentName)
    colName = findColumnName(componentName, colName)
    if c is None:
        fail("Can't find component " + componentName)
    java.tableClick(c, findColumnName(componentName, colName), rowNum, count, shift, control, right)

def pvtableclick(componentName, colName, rowNum, count=1, shift=0, control=0, right=0):
    c = getComponent(componentName)
    if c is None:
        fail("Can't find component " + componentName)
    java.pvtableClick(c, findColumnName(componentName, colName), rowNum, count, shift, control, right)

def listclick(componentName, rowNum, count=1, shift=0, control=0, right=0):
    c = getComponent(componentName)
    if c is None:
        fail("Can't find component " + componentName)
    java.listClick(c, rowNum, count, shift, control, right)

def rightclick(componentName):
    c = getComponent(componentName)
    if c is None:
        fail("Can't find component " + componentName)
    java.click(c, 1, 0, 0, 1)

def comboboxclick(componentName, entry):
    c = getComponent(componentName)
    if c is None:
        fail("Can't find component " + componentName)
    java.comboboxClick(c, entry)

def close():
    global windows
    del windows[-1]

def getComponent(*names):
    if not len(windows):
        print "No windows"
        return None
    current = windows[-1]
    origName = "/".join([str(name) for name in names])
    for name in names:
        if type(name) == type(""):
            current = java.getComponent(current, name, 3)
        else:
            c = name
            while c is not None:
                if c == current:
                    break
                c = c.getParent()
            if c is None:
                fail("Component " + origName + " is not a descendant of " + `current`)
            current = name
    return current

def matchComponent(*names, **args):
    from java.lang import Class
    javaClass = args.get("javaClass")
    if javaClass is None:
        javaClass = "java.lang.Object"
    if not len(windows):
        print "No windows"
        return None
    current = windows[-1]
    origName = "/".join([str(name) for name in names])
    for name in names:
        if type(name) == type(""):
            current = java.matchComponent(current, name, Class.forName(javaClass), 3)
        else:
            c = name
            while c is not None:
                if c == current:
                    break
                c = c.getParent()
            if c is None:
                fail("Component " + origName + " is not a descendant of " + `current`)
            current = name
    return current

def getComponentByClass(name, javaClass, timeout=3):
    from java.lang import Class
    if type(name) == type(""):
        return java.getComponent(windows[-1], name, Class.forName(javaClass), timeout)
    return name

def assertDescendant(low, high):
    l = getComponent(low)
    h = getComponent(high)
    if l is None:
        fail("Can't find component " + `low`)
    if h is None:
        fail("Can't find component " + `high`)
    java.assertDescendant(l, h)

def assertChild(low, high):
    l = getComponent(low)
    h = getComponent(high)
    if l is None:
        fail("Can't find component " + low)
    if h is None:
        fail("Can't find component " + high)
    java.assertChild(l, h)

def assertNoComponent(c, timeout=2):
    count = 0
    while getComponent(c) is None:
        count += 1
        sleep(1)
        if count == timeout:
            return
    fail("There's not supposed to be a component called " + c)

def sleep(secs):
    import time
    time.sleep(secs)

def waitTillComponentReady(componentName, timeout = 30):
    count = 0
    while getComponent(componentName) is None:
        count += 1
        sleep(1)
        if count == timeout:
            global java
            java.show()
            fail("Timed out waiting for component '%s' to be ready" % componentName)
    return getComponent(componentName)

def waitTillComponentReadyByClass(componentName, clazz, timeout = 30):
    count = 0
    while getComponentByClass(componentName, clazz) is None:
        count += 1
        sleep(1)
        if count == timeout:
            fail("Timed out waiting for component '%s' to be ready" % componentName)
    return getComponentByClass(componentName, clazz)

class TextSetter(Runnable):
    def __init__(self, component, text):
        self.component = component
        self.text = text

    def run(self):
        from java.lang import Class
        jcombo = Class.forName("javax.swing.JComboBox")
        if jcombo.isInstance(self.component):
            if self.component.isEditable():
                self.component.setSelectedItem(str(self.text))
            else:
                fail("Cannot enter text into a non-editable combo box: " + str(self.component))
        else:
            try:
                self.component.setText(str(self.text))
            except AttributeError:
                fail("Component %s (%s) has no setText method" % (str(self.component), str(self.component.getClass())))

def enterText(componentName, text):
    # TODO - rewrite this to use keystrokes
    c = getComponent(componentName)
    if c is None:
        fail("Can't find component " + componentName)
    SwingUtilities.invokeLater(TextSetter(c, text))

def appendText(componentName, text):
    # TODO - rewrite this to use clicks and keystrokes
    c = getComponent(componentName)
    if c is None:
        fail("Can't find component " + componentName)
    SwingUtilities.invokeLater(TextSetter(c, getText(c) + text))

def selectTab(componentName, name):
    # TODO - rewrite this to use a click
    tabs = getComponent(componentName)
    if tabs is None:
        fail("Can't find tab component " + componentName)
        return 0
    for i in range(tabs.getTabCount()):
        if tabs.getTitleAt(i) == name:
            tabs.setSelectedIndex(i)
            return 1
    return 0

def getText(componentName):
    c = getComponent(componentName)
    if c is None:
        fail("Can't find component " + componentName)
    return c.getText()

def waitTill(condition, timeout, error, globals, locals):
    i = 0
    while i < timeout:
        if eval(condition, globals, locals):
            break
        sleep(1)
        i += 1
    if i == timeout:
        fail(error)

def findRow(table, column, value):
    table = getComponent(table)
    if table is None:
        fail("Can't find component " + table)
    return java.findRow(table, column, value)

def findRowInList(list, value):
    from java.lang import String
    list = getComponent(list)
    if list is None:
        fail("Can't find component " + list)
    model = list.getModel()
    for r in range(model.getSize()):
        if String.valueOf(model.getElementAt(r)) == value:
            return r
    return -1

def findColumnIndex(table,columnName):
    """Finds a columnName in a table, and returns the index"""
    component = getComponent(table)
    result = None
    if component is None:
        fail("Can't find component " + component)


    try:
        colModel = component.getColumnModel()
        for i in range(0,colModel.getColumnCount()):
            title = colModel.getColumn(i).getHeaderValue()
            if title == columnName:
                result = i
                break
    except Exception, ex:
        print "Error trying to get column model", columnName, ex

    if result is None:
        for i in range(0,component.getColumnCount()):
            name = component.getColumnName(i)
            if name == columnName:
                result = i
                break

    # DEBUG print "Column Name: '%s', found at idx: %s" % (columnName, str(result))

    return result


def findColumnName(table, columnTitleOrName):
    """Finds a columnName in a table from a column title or name,
       and returns the index"""
    result = columnTitleOrName
    component = getComponent(table)
    if component is None:
        fail("Can't find component " + component)
    try:
        tableDef = component.getModel().getTableDefinition()
        if tableDef is not None:
            columnIndex = tableDef.indexOfTitle(columnTitleOrName)
            if result > -1:
                result = tableDef.getName(columnIndex)

    except:
        pass

    return result

    for i in range(0,component.getColumnCount()):
        name = component.getColumnName(i)
        if name == columnName:
            return i

    return -1


def assertEnabled(component):
    component = getComponent(component)
    if component is None:
        fail("Can't find component " + component)
    java.assertTrue("Component should be enabled", component.isEnabled())

def assertDisabled(component):
    component = getComponent(component)
    if component is None:
        fail("Can't find component " + component)
    java.assertTrue("Component should be disabled", not component.isEnabled())

def assertTrue(message, result=True):
    java.assertTrue(message, result)

def waitForTreePath(tree, path, timeout=30):
    t = 0
    while t < timeout:
        if treePathExists(tree, path):
            return 1
        sleep(1)
        t += 1
    return 0

def waitForTreePathNotVisible(tree, path, timeout=30):
    """ Waits until a tree path is not visible.
    This is for when deleting an item from a tree, and you want to check to make sure it is deleted."""
    t = 0
    while t < timeout:
        if not treePathExists(tree, path):
            return 1
        sleep(1)
        t += 1
    return 0

def treePathExists(tree, path):
    tree = getComponent(tree)
    if tree is None:
        fail("Can't find component: '"+str(tree)+"' to check that tree path exists.")
    if path.startswith("/"):
        path = path[1:]
    path = path.split("/")
    model = tree.getModel()
    root = model.getRoot()
    current = None
    for part in path:
        if current is None and str(root) == part:
            current = root
        elif current is None:
            return 0
        else:
            found = 0
            for i in range(model.getChildCount(current)):
                o = model.getChild(current, i)
                if o is None:
                    # something was deleted from the tree
                    return 0
                try:
                    if str(o) == part:
                        current = o
                        found = 1
                        break
                except Exception, ex:
                    raise Exception("Error converting 'o' to string for part:" + part)
            if not found:
                return 0
    return 1

def makeTreePathVisible(tree, path):
    from javax.swing.tree import TreePath
    tree = getComponent(tree)
    if tree is None:
        fail("Can't find component " + tree)
    if path.startswith("/"):
        path = path[1:]
    path = path.split("/")
    model = tree.getModel()
    root = model.getRoot()
    current = None
    pathSoFar = None
    for part in path:
        if current is None and str(root) == part:
            current = root
            treepath = TreePath(current)
            pathSoFar = part
        elif current is None:
            return 0
        else:
            found = 0
            for i in range(model.getChildCount(current)):
                o = model.getChild(current, i)
                if str(o) == part:
                    current = o
                    found = 1
                    treepath = treepath.pathByAddingChild(current)
                    pathSoFar = pathSoFar + "/" + part
                    break
            if not found:
                return 0
        if not tree.isExpanded(treepath):
            treeclick(tree, pathSoFar, 2)
    return 1

def keystroke(component, stroke, shift=0, control=0):
    component = getComponent(component)
    if component is None:
        fail("Can't find component " + component)
    java.keystroke(component, stroke, shift, control)

def keypress(component, stroke, shift=0, control=0):
    component = getComponent(component)
    if component is None:
        fail("Can't find component " + component)
    java.keypress(component, stroke, shift, control)

def getContent(component):
    """
        For a tree the root node is returned, where a node is a (object, children) tuple. The object is the user
        object for the node and children is a list of nodes.
    """
    from java.lang import Class
    component = getComponent(component)
    if component is None:
        fail("Can't find component " + component)
    jtree = Class.forName("javax.swing.JTree")
    jtable = Class.forName("javax.swing.JTable")
    jlist = Class.forName("javax.swing.JList")
    jcombo = Class.forName("javax.swing.JComboBox")
    if jtree.isInstance(component):
        if component.getModel() is not None:
            root = component.getModel().getRoot()
            if root is not None:
                return getTreeContent(component, root)
    elif jtable.isInstance(component):
        model = component.getModel()
        result = []
        for r in range(model.getRowCount()):
            row = []
            for c in range(model.getColumnCount()):
                row.append(model.getValueAt(r, c))
            result.append(row)
        return result
    elif jlist.isInstance(component) or jcombo.isInstance(component):
        model = component.getModel()
        result = [ model.getElementAt(i) for i in range(model.getSize()) ]
        return result
    return None

def getTreeContent(tree, node):
    model = tree.getModel()
    count = model.getChildCount(node)
    children = [ model.getChild(node, i) for i in range(count) ]
    return node, [ getTreeContent(tree, child) for child in children ]

def getTreePaths(component, node=None):
    component = getComponent(component)
    if component is None:
        fail("Can't find tree " + component)
    model = component.getModel()
    if node is None:
        node = model.getRoot()
    count = model.getChildCount(node)
    children = [ model.getChild(node, i) for i in range(count) ]
    paths = []
    for p in [getTreePaths(component, ch) for ch in children]:
        paths = paths + p
    thisNode = "/" + str(node.getUserObject())
    return [thisNode] + [ thisNode + path for path in paths ]

def getLabels(component):
    component = getComponent(component)
    if component is None:
        fail("Can't find component " + component)
    jl = java.getLabels(component)
    i = 0
    result = []
    while i < jl.size():
        result.append(jl.get(i))
        i += 1
    return result

def getTitlesFromBorder(border):
    from javax.swing.border import TitledBorder
    from javax.swing.border import CompoundBorder
    titles = []
    if isinstance(border, TitledBorder):
        titles.append(border.getTitle())
    elif isinstance(border, CompoundBorder):
        titles += getTitlesFromBorder(border.getInsideBorder())
        titles += getTitlesFromBorder(border.getOutsideBorder())
    return titles

def getBorderTitles(component):
    from javax.swing import JComponent
    component = getComponent(component)
    if component is None:
        fail("Can't find component " + component)
    titles = []
    if isinstance(component, JComponent):
        border = component.getBorder()
        titles += getTitlesFromBorder(border)
    for c in component.getComponents():
        titles += getBorderTitles(c)
    return titles

def isEnabled(componentName):
    return getComponent(componentName).isEnabled()

def isEditable(componentName):
    try:
        return getComponent(componentName).isEditable()
    except AttributeError:
        print "ERROR: Unable to determine if " + componentName + " is editable"
        return False

def searchForComponent(component, func):
    component = getComponent(component)
    if component is None:
        fail("Can't find search root " + `component`)
    return java.searchForComponent(component, func)

def waitForWindowToClose(timeout=5):
    global windows
    w = windows[-1]
    title = w.getTitle()
    print "Title of closing window is %s" % title
    while findWindow(title):
        if not timeout:
            fail("Timed out waiting for %s to close" % title)
        sleep(1)
        timeout -= 1
    close()

def startTimer():
    return time.clock()

def stopTimer(start):
    # return seconds since start (decimal)
    stop = time.clock()
    return stop-start

def getTreePath(component, nodeName):
    component = getComponent(component)
    if component is None:
        fail("Can't find tree " + component)
    if nodeName is None:
        fail("Can't find node " + nodeName)
    model = component.getModel()
    node = model.getRoot()
    for tempName in nodeName.split('/'):
        if tempName != '**' and tempName!= '*':
            searchNode = tempName
    path = "/" + str(node.getUserObject())
    paths = []
    pathsList = []
    for tempName in nodeName.split('/'):
        if tempName =='**':
            path += multiTraverse(model, node, searchNode, path)
        if tempName =='*' and len(paths) > 0:
            for tempPath in paths:
                nodeTreeLength = len(tempPath.split('/'))
                searchNode =  (tempPath.split('/'))[nodeTreeLength-1]
                searchNodeObj =  getNode(model, node, searchNode)
                pathsList += (singleTraverse(model, searchNodeObj, tempPath))
            paths = pathsList
        if tempName =='*' and len(paths) == 0:
            searchNodeObj = getNode(model, node, searchNode)
            paths = singleTraverse(model, searchNodeObj, path)
    if  len(paths) >0:
        return paths
    else:
        return path

def getNode(model, node, searchNode):
    count = model.getChildCount(node)
    child = node
    for i in range(count):
        child = model.getChild(node, i)
        if str(child) == searchNode:
            return child
        else:
            child = getNode(model, child, searchNode)
        if child.toString() == searchNode:
            break
    return child

def singleTraverse(model, searchNodeObj, paths):
    count = model.getChildCount(searchNodeObj)
    tempPaths = []
    for j in range(count):
        child = model.getChild(searchNodeObj, j)
        tempPaths.append(paths + "/" + child.toString())
    return tempPaths

def multiTraverse(model, node, searchNode, paths):
    count = model.getChildCount(node)
    tempPath =''
    if not count:
        paths = ''
    for i in range(count):
        if tempPath != '':
            return paths
        child = model.getChild(node, i)
        if str(child) != searchNode:
            if model.isLeaf(child):
                return ''
            tempPath = multiTraverse(model, child, searchNode, paths)
            if tempPath =='':
                paths = ''
            else:
                if not model.getChildCount(child):
                    paths = tempPath
                else:
                    paths = "/" + child.toString() + tempPath
        else:
            return "/" + child.toString()
    return paths

