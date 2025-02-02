import mstarpaths, sys, string
import minestar

logger = minestar.initApp()

def main(args):
    args = args['args']
    for arg in args:
        print mstarpaths.interpretPath(arg),
    print
