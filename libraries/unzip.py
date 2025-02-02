import zipfile,minestar

logger = minestar.initApp()

def unzip(zip_file, outdir):
    """
    Unzip a given 'zip_file' into the output directory 'outdir'.
    """
    try:
        zf = zipfile.ZipFile(zip_file, "r")
        zf.extractall(outdir)
    except IOError, msg:
        logger.error('%s: I/O error: %s\n' % (zip_file, msg))
        pass
