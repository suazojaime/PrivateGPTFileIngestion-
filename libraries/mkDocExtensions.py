import os, sys, makeSystem, mstarpaths

# get mstar build version
mstarpaths.loadMineStarConfig()
mstar_build = makeSystem.getCurrentBuild()
mstar_fields = mstar_build.split("-")
mstar_major = mstar_fields[0]

# get system type for command
if sys.platform == 'win32':
    rmcmd = 'del /q'
else:
    rmcmd = 'rm -f'

# @joehuang pack up
langs = {'en':'English', 'es':'Spanish', 'pt':'Portuguese'}
pkgs = ['Aquila_Drills_Documentation', 'CAES_Documentation', 'MineStar_Documentation', 'Phrase_Books', 'TOPE_Documentation', 'Wireless_Network_Documentation']

for lang in langs.keys():
	for pkg in pkgs:
		sourcefile = '%s/%s' % (langs[lang], pkg)
		targetfile = '%s-%s-%s.zip' % (lang, pkg.replace("_", "-"), mstar_major)
		if os.path.exists(sourcefile):
			cmd = '%s %s' % (rmcmd, targetfile)
 			print cmd + "..."
			os.system(cmd)
			cmd = 'zip -r %s %s' % (targetfile, sourcefile)
			print cmd + "..."
			os.system(cmd)
