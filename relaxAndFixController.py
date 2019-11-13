# relax and fix controller

def initWindow(windowSize, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList) :
    for timeStage in range(0, timeLength) :
        for providerIndex in range(0, len(providerList)) :
            for userIndex in range(0, numOfUsers) :
                for vmTypeIndex in range(0, len(vmTypeList)):
                    for vmContractLength in vmContractList :
                        for vmPaymentOpti0on in vmPaymentList :
                            if timeStage < windowSize :
                                # add the variable into the set that is going to be optimized
                                print()
                            else :
                                # add thevariables into the set that is going to be relaxed
                                print()