""" Repository operations. """

# TODO add '_runningFromRepository' variable here.

_repositoryHome = "{MSTAR_HOME}/../../../.."

def repositoryHome():
    """ Get the location of the repository home directory. """
    return _repositoryHome

def repositoryRuntimeTarget():
    """ Get the location of the runtime target directory in the repository. """
    return repositoryHome() + '/runtime/target'

