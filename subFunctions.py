# sub functions
import random

# get the list of instance types 
def getVmTypesList(instanceData) :
    vmList = []
    for item in instanceData :
        instanceType = item.instanceType
        if instanceType not in vmList :
            vmList.append(instanceType)
    return vmList

# get the list of DCs
def getProvidersNameList(instanceData) :
    providerList = []
    for item in instanceData :
        provider = item.provider
        if provider not in providerList :
            providerList.append(provider)
    return providerList

def getProviderAreaDict(instanceData) :
    areaDict = dict()
    for instance in instanceData :
        instanceArea = instance.area
        instanceProvider = instance.provider
        if instanceArea not in areaDict :
            areaDict[str(instanceArea)] = [instanceProvider]
        else :
            providerListOfArea = areaDict[str(instanceArea)]
            if instanceProvider not in providerListOfArea :
                providerListOfArea.append(instanceProvider)
    return areaDict

# generate the demand for each instance type at each time period
def demandGenerator(timeLength, userList, vmTypes) :
    timeList = []
    for time in range(0, timeLength) :
        vmDemandForUsers = []
        for user in userList :
            vmDemandForSingleUser = dict()
            for vm in vmTypes :
                vmDemand = random.randint(10, 30)
                vmDemandForSingleUser[vm] = vmDemand
            vmDemandForUsers.append(vmDemandForSingleUser)
        timeList.append(vmDemandForUsers)
    return timeList

# sort the VM data accroding to the providers, VM types, contracts, payment options
def sortVM(instanceData, providerList, vmTypeList, contractLengthList, paymentList) :
    # store the sorted VM data
    newVmList = dict()
    
    for provider in providerList :
        vmTypesOfProvider = dict()
        for vmType in vmTypeList :
            contractOfVmTypes = dict()
            for contractLength in contractLengthList :
                paymentOptionOfContract = dict()
                for payment in paymentList :
                    # find the instance data with specific configuration
                    for instance in instanceData :
                        instanceProvider = instance.provider
                        instanceType = instance.instanceType
                        instanceContract = instance.contractLength
                        instancePayment = instance.paymentOption
                        
                        
                        if instanceProvider == provider and instanceType == vmType and instanceContract == contractLength and instancePayment == payment :
                            paymentOptionOfContract[str(payment)] = instance
                            break
                contractOfVmTypes[str(contractLength)] = paymentOptionOfContract
            vmTypesOfProvider[str(vmType)] = contractOfVmTypes
        newVmList[str(provider)] = vmTypesOfProvider
    '''
    for pro in providerList :
        for vmType in vmTypeList :
            for contractLength in contractList :
                for payment in paymentOptionList :
                    print(newVmList[pro][vmType][str(contractLength)][payment])
    '''
    return newVmList    

# sort the router accorging to the router, contract length and payment options
def sortRouter(routerData) :
    sortedRouterData = dict()
    for routerIndex in range(len(routerData)) :
        contractsOfRouterDict = dict()
        contractLengthList = [5, 10]
        for contractLengthIndex in range(2) :
            contractLength = contractLengthList[contractLengthIndex]
            
            paymentsOfContractDict = dict()
            
            paymentList = ['No upfront', 'Partial upfront', 'All upfront']
            for paymentIndex in range(3) :
                payment = paymentList[paymentIndex]
                
                for router in routerData :
                    routerSeries = router.routerIndex
                    routerContractLength = router.contractLength
                    routerPayment = router.paymentOption
                    
                    if routerSeries == routerIndex and routerContractLength == contractLength and routerPayment == payment :
                        paymentsOfContractDict[str(payment)] = router
                        break
            contractsOfRouterDict[str(contractLength)] = paymentsOfContractDict
        sortedRouterData[str(routerIndex)] = contractsOfRouterDict
    return sortedRouterData

# sort energy price according to time, area
def sortEnergyPrice(energyPriceDict, timeLength) :
    sortedEnergyPrice = []
    for timeStage in range(0, timeLength) :
        sortedEnergyPrice.append(dict())
    
    for area in energyPriceDict :
        energyPriceObj = energyPriceDict[area]
        priceList = energyPriceObj.priceList
        
        for timeStage in range(0, timeLength) :
            sortedEnergyPrice[timeStage][str(area)] = priceList[timeStage % len(priceList)]
    return sortedEnergyPrice

def getRouterAreaDict(routerData) :
    areaDict = dict()
    
    for router in routerData :
        routerArea = router.routerArea
        
        if str(routerArea) in areaDict :
            areaRouterList = areaDict[str(routerArea)]
            areaRouterList.append(router)
        else :
            areaRouterList = [router]
            areaDict[str(routerArea)] = areaRouterList
    return areaDict

# generate the VM demand data randomly
def generateVmDemand(timeLength, numOfUsers, vmTypeList) :
    vmDemandList = []
    
    for timeStage in range(0, timeLength) :
        userVmDemandDict = dict()
        for userIndex in range(0, numOfUsers) :
            vmTypeDemandDict = dict()
            for vmTypeIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmTypeIndex]
                
                vmDemand = random.randint(15, 30)
                
                vmTypeDemandDict[str(vmType)] = vmDemand
            userVmDemandDict[str(userIndex)] = vmTypeDemandDict
        vmDemandList.append(userVmDemandDict)
    
    return vmDemandList

# get the dictionary containing instance resource requirement
def getInstanceReqDict(instanceData) :
    reqDict = dict()
    
    for vm in instanceData :
        instanceType = vm.instanceType
        
        if instanceType not in reqDict :
            reqDict[str(instanceType)] = vm
    return reqDict
        
# get the outbound bandwidth requirement of each VM type
def getOutboundBandwidthRequirement(instanceData) :
    outboundBandReqDict = dict()
    
    for instance in instanceData :
        instanceType = instance.instanceType
        networkReq = instance.networkReq
        
        if instanceType not in outboundBandReqDict :
            outboundBandReqDict[str(instanceType)] = networkReq
    return outboundBandReqDict

def getVmDataConfiguration(instanceData) :
    providerList = []
    vmTypeList = []
    vmContractLengthList = []
    vmPaymentList = []
    
    for instance in instanceData :
        provider = instance.provider
        vmType = instance.instanceType
        contractLength = instance.contractLength
        payment = instance.paymentOption
        
        if provider not in providerList :
            providerList.append(provider)
        
        if vmType not in vmTypeList :
            vmTypeList.append(vmType)
        
        if contractLength not in vmContractLengthList :
            vmContractLengthList.append(int(contractLength))
        
        if payment not in vmPaymentList :
            vmPaymentList.append(payment)
    configDict = dict()
    configDict['providerList'] = providerList
    configDict['vmTypeList'] = vmTypeList
    configDict['vmContractLengthList'] = vmContractLengthList
    configDict['vmPaymentList'] = vmPaymentList
    
    return configDict
