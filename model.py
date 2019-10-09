# Build gurobi model
from readData import *
from subFunctions import *
from gurobipy import *
import random
            
# get instance data from csv file, get get the lists of vm types and cloud providers from instance data

instanceData = getVirtualResource()
providerList = getProvidersList(instanceData)
areaDict = getProviderAreaDict(instanceData)
vmTypeList = getVmTypesList(instanceData)
storageAndBandwidthPrice = getCostOfStorageBandBandwidth()
networkTopology = getNetworkTopology()


model = Model('VM_network_and_energy_optimization_model')

timeLength = 3 * 365 * 24
numOfUsers = len(networkTopology['user'])

# Virtual Machines

# sort the instance data for calculating the cost of using VM
sortedVmList = sortVM(instanceData, providerList, vmTypeList)
vmCostDecVarList = []
vmCostParameterList = []

# VM  reservation decision variables
vmResDecVar = []
# VM utilization decision variables
vmUtilizationDecVar = []
# VM on-demand decision variables
vmOnDemandDecVar = []

for timeStage in range(0, timeLength) :
    providerDecVar_res = dict()
    providerDecVar_uti = dict()
    providerDecVar_onDemand = dict()
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        userDecVar_res = dict()
        userDecVar_uti = dict()
        userDecVar_onDemand = dict()
        for userIndex in range(0, numOfUsers) :
            vmDecVar_res = dict()
            vmDecVar_uti = dict()
            vmDecVar_onDemand = dict()
            for vmIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmIndex]
                contractDecVar_res = dict()
                contractDecVar_uti = dict()
                
                # on-demand vm data (cost of using on-demand instance)
                onDemandParameter = 0
                
                for contractIndex in range(2) :
                    contractLengthList = [1, 3]
                    contractLength = contractLengthList[contractIndex]
                    paymentOptionDecVar_res = dict()
                    paymentOptionDecVar_uti = dict()
                    for paymentOptionIndex in range(3) :
                        paymentOptionsList = ['NoUpfront', 'PartialUpfront', 'AllUpfront']
                        paymentOption = paymentOptionsList[paymentOptionIndex]
                        
                        # create a decision variable that represent the number of instance whose instance type is i
                        # reserved from provider p
                        # at time stage t
                        # by user u
                        # adopted contract k and payment option j
                        reservationVar = model.addVar(lb=0.0, ub=GRB.INFINITY, vtype=GRB.INTEGER)
                        utilizationVar = model.addVar(lb=0.0, vtype=GRB.INTEGER)
                        
                        paymentOptionDecVar_res[paymentOption] = reservationVar
                        paymentOptionDecVar_uti[paymentOption] = utilizationVar
                        
                        # add decision variables to the list for computing the cost of using VM
                        vmCostDecVarList.append(reservationVar)
                        vmCostDecVarList.append(utilizationVar)
                        
                        # vm data
                        vmDictOfProvider = sortedVmList[str(provider)]
                        contractDictOfVM = vmDictOfProvider[str(vmType)]
                        paymentDictOfContract = contractDictOfVM[str(contractLength)]
                        instanceTupleData = paymentDictOfContract[str(paymentOption)]
                        
                        # get the initial reservation price and utilization price
                        initialResFee = instanceTupleData.resFee
                        utilizationFee = instanceTupleData.utilizeFee
                        onDemandFee = instanceTupleData.onDemandFee
                        
                        # get the cost of storage and bandwidth of VM
                        instanceStorageReq = instanceTupleData.storageReq
                        instanceOutboundBandwidthReq = instanceTupleData.networkReq
                        
                        storageAndBandwidthPriceDict = storageAndBandwidthPrice[str(provider)]
                        storagePrice = storageAndBandwidthPriceDict['storage']
                        bandwidthPrice = storageAndBandwidthPriceDict['bandwidth']
                        
                        utilizationParameter = utilizationFee + storagePrice * instanceStorageReq + bandwidthPrice * instanceOutboundBandwidthReq
                        onDemandParameter = onDemandFee + storagePrice * instanceStorageReq + bandwidthPrice * instanceOutboundBandwidthReq
                        
                        # add parameters of decision variables to the list
                        vmCostParameterList.append(initialResFee)
                        vmCostParameterList.append(utilizationParameter)
                        
                    contractDecVar_res[str(contractLength)] = paymentOptionDecVar_res
                    contractDecVar_uti[str(contractLength)] = paymentOptionDecVar_uti
                
                onDemandVmVar = model.addVar(lb=0.0, vtype=GRB.INTEGER)
                
                vmDecVar_res[vmType] = contractDecVar_res
                vmDecVar_uti[vmType] = contractDecVar_uti
                vmDecVar_onDemand[vmType] = onDemandVmVar
                
                vmCostDecVarList.append(onDemandVmVar)
                vmCostParameterList.append(onDemandParameter)
                
            userDecVar_res[str(userIndex)] = vmDecVar_res
            userDecVar_uti[str(userIndex)] = vmDecVar_uti
            userDecVar_onDemand[str(userIndex)] = vmDecVar_onDemand
        providerDecVar_res[str(provider)] = userDecVar_res
        providerDecVar_uti[str(provider)] = userDecVar_uti
        providerDecVar_onDemand[str(provider)] = userDecVar_onDemand
    vmResDecVar.append(providerDecVar_res)
    vmUtilizationDecVar.append(providerDecVar_uti)
    vmOnDemandDecVar.append(providerDecVar_onDemand)


# Bandwidth
numOfRouters = len(networkTopology['router'])
routerData = getRouterBandwidthPrice(networkTopology)
sortedRouter = sortRouter(routerData)

# record the cost of using network bandwidth
bandwidthCostDecVarList = []
bandwidthCostParameterList = []

# decision variables
bandResDecVar = []
bandUtilizationDecVar = []
bandOnDemandDecVar = []

for timeStage in range(0, timeLength) :
    bandUserDecVar_res = []
    bandUserDecVar_uti = []
    bandUserDecVar_onDemand = []
    
    for userIndex in range(0, numOfUsers) :
        bandRouterDecVar_res = []
        bandRouterDecVar_uti = []
        bandRouterDecVar_onDemand = []
        
        for routerIndex in range(0, numOfRouters) :
            bandContractDecVar_res = dict()
            bandContractDecVar_uti = dict()
            
            # record the price of on-demand bandwidth price
            routerOnDemandFee = 0
            
            for bandResContractIndex in range(2) :
                bandResContractLengthList = [5, 10]
                bandResContractLength = bandResContractLengthList[bandResContractIndex]
                
                bandPaymentOptionDecVar_res = dict()
                bandPaymentOptionDecVar_uti = dict()
                
                for bandPaymentOptionIndex in range(3) :
                    bandPaymentOptionList = ['No upfront', 'Partial upfront', 'All upfront']
                    bandPaymentOption = bandPaymentOptionList[bandPaymentOptionIndex]
                    
                    bandReservation = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
                    bandUtilization = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
                    
                    bandPaymentOptionDecVar_res[bandPaymentOption] = bandReservation
                    bandPaymentOptionDecVar_uti[bandPaymentOption] = bandUtilization
                    
                    # add decision variables to the list
                    bandwidthCostDecVarList.append(bandReservation)
                    bandwidthCostDecVarList.append(bandUtilization)
                    
                    # add parameter to the list
                    contractsOfRouter = sortedRouter[str(routerIndex)]
                    paymentsOfContract = contractsOfRouter[str(bandResContractLength)]
                    routerTupleData = paymentsOfContract[str(bandPaymentOption)]
                    
                    routerInitialResFee = routerTupleData.reservationFee
                    routerUtilizationFee = routerTupleData.utilizationFee
                    # update the price of on-demand bandwidth
                    routerOnDemandFee = routerTupleData.onDemandFee
                    
                    bandwidthCostParameterList.append(routerInitialResFee)
                    bandwidthCostParameterList.append(routerUtilizationFee)
                    
                bandContractDecVar_res[str(bandResContractLength)] = bandPaymentOptionDecVar_res
                bandContractDecVar_uti[str(bandResContractLength)] = bandPaymentOptionDecVar_uti
            
            bandOnDemand = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            
            bandRouterDecVar_res.append(bandContractDecVar_res)
            bandRouterDecVar_uti.append(bandContractDecVar_uti)
            bandRouterDecVar_onDemand.append(bandOnDemand)
            
            # add on demand decision to the list
            bandwidthCostDecVarList.append(bandOnDemand)
            
            # add on-demand price to the list
            bandwidthCostParameterList.append(routerOnDemandFee)
            
        
        bandUserDecVar_res.append(bandRouterDecVar_res)
        bandUserDecVar_uti.append(bandRouterDecVar_uti)
        bandUserDecVar_onDemand.append(bandRouterDecVar_onDemand)
        
    bandResDecVar.append(bandUserDecVar_res)
    bandUtilizationDecVar.append(bandUserDecVar_uti)
    bandOnDemandDecVar.append(bandUserDecVar_onDemand)

# VM energy

# Power Usage Effectiveness
valueOfPUE = 1.58
energyPriceDict = readEnergyPricingFile()
sortedEnergyPrice = sortEnergyPrice(energyPriceDict, timeLength)

# the list used to calculate the VM energy consumption
activeVmDecVarList = []
energyConsumptionList = []
greenEnergyUsageDecVarDict = dict()

# store the formula used to calculate the number of turned on VM
turnedOnVmDecVarFormula = []
# store the energy consumption used to turn on VM
turnedOnVmParameterList = []
# store the formula used to calculate the number of turned off VM
turnedOffVmDecVarFormula = []
# store the energy cunsumption used to turn off VM
turnedOffVmParameterList = []

# the list that is used to store the decision variables of previous time stage
previousTimeStageDecVarDict = dict()


for timeStage in range(0, timeLength) :
    providerDecVar_uti = vmUtilizationDecVar[timeStage]
    providerDecVar_onDemand = vmOnDemandDecVar[timeStage]
    for area in areaDict :
        providerListOfArea = areaDict[area]
        for provider in providerListOfArea :
            userDecVar_uti = providerDecVar_uti[str(provider)]
            userDecVar_onDemand = providerDecVar_onDemand[str(provider)]    
            for userIndex in range(0, numOfUsers) :
                vmDecVar_uti = providerDecVar_uti[str(userIndex)]
                vmDecVar_onDemand = providerDecVar_onDemand[str(userIndex)]
                for vmTypeIndex in range(0, len(vmTypeList)) :
                    vmType = vmTypeList[vmTypeIndex]
                    contractDecVar_uti = vmDecVar_uti[vmType]
                    onDemandVmDecVar = vmDecVar_onDemand[vmType]
                    
                    energyConsumption = 0
                    utilizationAndOnDemandDecVarList = []
                    for contractIndex in range(2) :
                        contractLengthList = [1, 3]
                        contractLength = contractLengthList[contractIndex]
                        paymentOptionDecVar_uti = contractDecVar_uti[str(contractLength)]
                        for paymentOptionIndex in range(3) :
                            paymentOptionList = ['NoUpfront', 'PartialUpfront', 'AllUpfront']
                            paymentOption = paymentOptionList[paymentOptionIndex]
                            
                            utilizationVar = paymentOptionDecVar_uti[paymentOption]
                            utilizationAndOnDemandDecVarList.append(utilizationVar)
                            
                            # VM data
                            vmTypeDictOfProvider = sortedVmList[str(provider)]
                            contractsDictOfVM = vmTypeDictOfProvider[str(vmType)]
                            paymentDictOfContract = contractDictOfVM[str(contractLength)]
                            instanceTupleData = paymentDictOfContract[str(paymentOption)]
                            
                            energyConsumption = instanceTupleData.energyConsumption
                    
                    # sum the utilization and on-demand decision variables to get the number of active VMs
                    utilizationAndOnDemandDecVarList.append(onDemandVmDecVar)
                    activeVmDecVarList.append(utilizationAndOnDemandDecVarList)
                    energyConsumptionList.append(energyConsumption)
                    
                    
                    # compute the number of VMs turned on at current time period
                    # assume that the energy used to turn on / off a virtual machine is 5 % of the energy     consumption of active VMs
                    turnedOnVmVarList = []
                    turnedOffVmVarList = []
                    if timeStage == 0 :
                        # time stage is 0
                        
                        # store the decision variables of previous time stage in the dictionary
                        if str(timeStage) in previousTimeStageDecVarDict :
                            userDict = previousTimeStageDecVarDict[str(timeStage)]
                            if str(userIndex) in userDict :
                                providerDict = userDict[str(userIndex)]
                                if str(provider) in providerDict :
                                    vmTypeDict = providerDict[str(provider)]
                                    vmTypeDict[str(vmType)] = utilizationAndOnDemandDecVarList
                                else :
                                    vmTypeDict = dict()
                                    vmTypeDict[str(vmType)] = utilizationAndOnDemandDecVarList
                                    
                                    providerDict[str(provider)] = vmTypeDict
                            else :
                                vmTypeDict = dict()
                                vmTypeDict[str(vmType)] = utilizationAndOnDemandDecVarList
                                
                                providerDict = dict()
                                providerDict[str(provider)] = vmTypeDict
                                
                                userDict[str(userIndex)] = providerDict
                        else :
                            vmTypeDict = dict()
                            vmTypeDict[str(vmType)] = utilizationAndOnDemandDecVarList
                            
                            providerDict = dict()
                            providerDict[str(provider)] = vmTypeDict
                            
                            userDict = dict()
                            userDict[str(userIndex)] = providerDict
                            
                            previousTimeStageDecVarDict[str(timeStage)] = userDict
                        
                        # calculate the number of VMs turned on at this time period
                        for decVar in utilizationAndOnDemandDecVarList :
                            turnedOnVmVarList.append(decVar)
                        
                        
                    else :
                        # time stage > 0
                        # get the decision variable of previous time stage
                        userDict = previousTimeStageDecVarDict[str(timeStage - 1)]
                        providerDict = userDict[str(userIndex)]
                        vmTypeDict = providerDict[str(provider)]
                        
                        utilizationAndOnDemandDecVarOfPreviousTimeStage = vmTypeDict[str(vmType)]
                        
                        
                        for decVar in utilizationAndOnDemandDecVarList :
                            turnedOnVmVarList.append(decVar)
                            turnedOffVmVarList.append(-1 * decVar)
                        
                        for decVar in utilizationAndOnDemandDecVarOfPreviousTimeStage :
                            turnedOnVmVarList.append(-1 * decVar)
                            turnedOffVmVarList.append(decVar)
            providerGreenEnergy = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            greenEnergyUsageDecVarDict[str(provider)] = providerGreenEnergy
                    
                

                    
    

# Network energy decision variables



# objective function
model.setObjective(quicksum([vmCostDecVarList[i] * vmCostParameterList[i] for i in range(0, len(vmCostDecVarList))]) + quicksum(bandwidthCostDecVarList[i] * bandwidthCostParameterList[i] for i in range(0, len(bandwidthCostDecVarList))), GRB.MINIMIZE)

quicksum([sortedEnergyPrice[timeStage][area] for timeStage in range(0, timeLength) for area in areaDict])

# add constraints