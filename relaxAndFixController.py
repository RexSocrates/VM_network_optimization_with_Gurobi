# relax and fix controller

fixVarDict = dict()
optimizeVarDict = dict()
relaxVarDict = dict()

# return the set of variables that are going to be optimized
# initialize the window for time decomposition
def initWindow(windowSize, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList) :
    for timeStage in range(0, timeLength) :
        if timeStage < windowSize :
            # var in optimized set
            print()
        else :
            # var in relax set
            print()