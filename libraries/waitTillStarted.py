# An application to wait till a particular object server has started
import mstarpaths, sys, os, time, mstardebug, i18n
import minestar

logger = minestar.initApp()

rightNow = time.time()
tooLate = rightNow + 60
delay = 2
needed = sys.argv[1:]
paths = []
mstarpaths.loadMineStarConfig()
for x in needed:
    print i18n.translate("Waiting for %s to start") % x
    path = mstarpaths.interpretPath("{MSTAR_TEMP}/%s.started" % x)
    paths.append(path)
while len(paths) > 0:
    stillToDo = []
    for p in paths:
        if not os.access(p, os.F_OK):
            stillToDo.append(p)
        else:
            st = os.stat(p)
            if st.st_mtime < rightNow:
                # it's an old one
                stillToDo.append(p)
    if len(stillToDo) > 0:
        if mstardebug.debug or time.time() > tooLate:
            if time.time() > tooLate:
                delay = 10
            print "Waiting for " + `stillToDo`
        time.sleep(delay)
    paths = stillToDo
