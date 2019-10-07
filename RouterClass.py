# Router class

class RouterClass :
    def __init__(self, routerIndex, contractLength, paymentOption, reservationFee, utilizationFee, onDemandFee, edges) :
        self.routerIndex = routerIndex
        self.contractLength = contractLength
        self.paymentOption = paymentOption
        self.reservationFee = reservationFee
        self.utilizationFee = utilizationFee
        self.onDemandFee = onDemandFee
        self.edges = edges