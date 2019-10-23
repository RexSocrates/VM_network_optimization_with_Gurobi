# cloud provider class

class CloudProvider :
    def __init__(self, provider, coresLimit, memoryLimit, storageLimit, internalBandwidthLimit, directlyConnectedEdges) :
        self.provider = provider
        self.coresLimit = coresLimit
        self.memoryLimit = memoryLimit
        self.storageLimit = storageLimit
        self.internalBandwidthLimit = internalBandwidthLimit
        self.directlyConnectedEdges = directlyConnectedEdges