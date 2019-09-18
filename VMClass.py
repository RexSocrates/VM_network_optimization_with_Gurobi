class VMClass :
    def __init__(self, area, provider, instanceType, contractLength, paymentOption, resFee, utilizeFee, onDemandFee, coreReq, memReq, storageReq, networkReq, energyConsumption) :
        self.area = area
        self.provider = provider
        self.instanceType = instanceType
        self.contractLength = contractLength
        self.paymentOption = paymentOption
        self.resFee = resFee
        self.utilizeFee = utilizeFee
        self.onDemandFee = onDemandFee
        self.coreReq = coreReq
        self.memReq = memReq
        self.storageReq = storageReq
        self.networkReq = networkReq
        self.energyConsumption = energyConsumption