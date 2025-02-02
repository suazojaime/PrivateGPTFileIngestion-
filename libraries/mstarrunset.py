# An application to tell you what the mstarrun settings are
import mstarpaths, minestar

logger = minestar.initApp()


def main(args):
    mstarpaths.loadMineStarConfig(args.get('system'))
    mstarpaths.dumpConfig(options=_getConfigOptions(args))

def _getSystem(options={}):
    return options.get('system')

def _getConfigOptions(args={}):
    options = {}
    if _resolveVars(args):
        options['resolve'] = True
    return options

def _resolveVars(options={}):
    args = options.get('args')
    return args is not None and 'resolve' in args


