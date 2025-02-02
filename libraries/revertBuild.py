import mstaroverrides, mstarrun, os, mstarpaths

mstarpaths.loadMineStarConfig()
buildFile = mstarrun.mstarBuildFile
if os.path.exists(buildFile):
    build = mstarrun.getLocalBuild(buildFile)
    ov = mstaroverrides.Overrides()
    ov.put("/Versions.properties", "CURRENT_BUILD", build)
    ov.save()
else:
    print "No MineStar.ini file found"

