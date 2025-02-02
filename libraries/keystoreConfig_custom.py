from keystoreConfig import KeyStoreConfigSPI

def getInstance(config=None):
    return MineStarKeyStoreConfigSPI(config)

class MineStarKeyStoreConfigSPI(KeyStoreConfigSPI):
    
    """The keystore configuration used by MineStar."""
    
    def __init__(self, config=None):
        super(MineStarKeyStoreConfigSPI, self).__init__()
        self.config = config

    # @Override
    def getKeyStoreFile(self):
        import mstarpaths
        return mstarpaths.interpretPathOverride("{MSTAR_CREDS}/keystore.jks", self.config)

    # @Override
    def getKeyStorePassword(self):
        return 'MineStar'
