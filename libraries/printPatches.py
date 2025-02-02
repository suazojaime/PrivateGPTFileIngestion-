import mstarext

def main(appConfig=None):
    info = mstarext.patchesActuallyUsed
    for (filename, id) in info:
        print "%-80s %-20s" % (filename, id)

if __name__ == "__main__":
    """entry point when called from python"""
    main()
