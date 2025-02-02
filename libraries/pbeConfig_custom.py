from pbeConfig import PBEConfigSPI

def getInstance(config=None):
    return MineStarPBEConfigSPI()

class MineStarPBEConfigSPI(PBEConfigSPI):
    
    # @Override
    def getSalt(self):
        return "MineStar".encode("utf-8")

    # @Override
    def getIterationCount(self):
        return 20

    # @Override
    def getAlgorithm(self):
        return "PBEWithMD5AndTripleDES"

    # @Override
    def getPassword(self):
        return "MineStar"
