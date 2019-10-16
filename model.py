# Build gurobi model
from readData import *
from subFunctions import *
from gurobipy import *
import random
            
# get instance data from csv file, get get the lists of vm types and cloud providers from instance data

instanceData = getVirtualResource()
providerList = getProvidersList(instanceData)
providerAreaDict = getProviderAreaDict(instanceData)
vmTypeList = getVmTypesList(instanceData)
storageAndBandwidthPrice = getCostOfStorageBandBandwidth()
networkTopology = getNetworkTopology()


model = Model('VM_network_and_energy_optimization_model')

timeLength = 3 * 365 * 24
numOfUsers = len(networkTopology['user'])
vmContractLengthList = [1 * 24 * 365, 3 * 24 * 365]

# VM demand at each time stage
vmDemandList = generateVmDemand(timeLength, numOfUsers, vmTypeList)

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
# a list that contains the decision variables of effective VM reservation
effectiveVmResDecVarDict = dict()

# iniitalize the list of effective VM reservation decision variables
for providerIndex in range(0, len(providerList)) :
    provider = providerList[providerIndex]
    userEffectiveVmResDecVarDict = dict()
    for userIndex in range(0, numOfUsers) :
        vmTypeEffectiveVmResDecVarDict = dict()
        for vmTypeIndex in range(0, len(vmTypeList)) :
            vmType = vmTypeList[vmTypeIndex]
            contractEffectiveVmResDecVarDict = dict()
            for contractLength in vmContractLengthList :
                paymentEffectiveVmResDecVarDict = dict()
                for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront'] :
                    effectiveVmResDecVarList = []
                    for timeStage in range(0, timeLength) :
                        effectiveVmResDecVarList.append([])
                    paymentEffectiveVmResDecVarDict[str(payment)] = effectiveVmResDecVarList
                contractEffectiveVmResDecVarDict[str(contractLength)] = paymentEffectiveVmResDecVarDict
            vmTypeEffectiveVmResDecVarDict[str(vmType)] = contractEffectiveVmResDecVarDict
        userEffectiveVmResDecVarDict[str(userIndex)] = vmTypeEffectiveVmResDecVarDict
    effectiveVmResDecVarDict[str(provider)] = userEffectiveVmResDecVarDict
                    

# equation 2 the cost of VMs
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
                
                for contractIndex in range(0, len(vmContractLengthList)) :
                    contractLength = vmContractLengthList[contractIndex]
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
                        
                        # add reservation decision variable to the effective VM reservation list
                        userEffectiveVmResDecVarDict = effectiveVmResDecVarDict[str(provider)]
                        vmTypeEffectiveVmResDecVarDict = userEffectiveVmResDecVarDict[str(userIndex)]
                        contractEffectiveVmResDecVarDict = vmTypeEffectiveVmResDecVarDict[str(vmType)]
                        paymentEffectiveVmResDecVarDict = contractEffectiveVmResDecVarDict[str(contractLength)]
                        effectiveVmResDecVarList = paymentEffectiveVmResDecVarDict[str(paymentOption)]
                        
                        for currentTimeStage in range(timeStage, min(timeStage + contractLength, timeLength)) :
                            effectiveVmDecVarListAtCurrentTimeStage = effectiveVmResDecVarList[currentTimeStage]
                            effectiveVmDecVarListAtCurrentTimeStage.append(reservationVar)
                        
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

# equation 3 the cost of network bandwidth
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
activeVmEnergyConsumptionDecVarList = []
numOfActiveVmsDecVarList = []
turnedOnVmVarList = []
turnedOffVmVarList = []
greenEnergyUsageDecVarList = []
vmChangeStateEnergyDict = dict()

# equation 4 the cost of energy consumption of active VMs
for timeStage in range(0, timeLength) :
    providerActiveVmEnergyConsumptionDecVarDict = dict()
    providerNumOfActiveVmsDecVarDict = dict()
    providerTurnedOnVmDecVarDict = dict()
    providerTurnedOffVmDecVarDict = dict()
    providerGreenEnergyDecVarDict = dict()
    for area in providerAreaDict :
        providerListOfArea = providerAreaDict[area]
        for provider in providerListOfArea :
            userActiveVmEnergyConsumptionDecVarDict = dict()
            userNumOfActiveVmsDecVarDict = dict()
            userTurnedOnVmDecVarDict = dict()
            userTurnedOffVmDecVarDict = dict()
            for userIndex in range(0, numOfUsers) :
                activeVmEnergyConsumptionDecVarDict = dict()
                numOfActiveVmsDecVarDict = dict()
                turnedOnVmDecVarDict = dict()
                turnedOffVmDecVarDict = dict()
                for vmTypeIndex in range(0, len(vmTypeList)) :
                    vmType = vmTypeList[vmTypeIndex]
                    
                    
                    vmDictOfProvider = sortedVmList[str(provider)]
                    contractDictOfVmType = vmDictOfProvider[str(vmType)]
                    paymentDictOfContract = contractDictOfVmType[str(vmContractLengthList[0])]
                    vmData = paymentDictOfContract['NoUpfront']
                    
                    vmEnergyConsumption = vmData.energyConsumption
                    changeStateEnergyConsumption = vmEnergyConsumption * 0.05
                    
                    if str(vmType) not in vmChangeStateEnergyDict :
                        vmChangeStateEnergyDict[str(vmType)] = changeStateEnergyConsumption
                    
                    
                    energyConsumptionOfActiveVm = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
                    numOfActiveVms = model.addVar(lb=0.0, vtype=GRB.INTEGER)
                    numOfTurnedOnVm = model.addVar(lb=0.0, vtype=GRB.INTEGER)
                    numOfTurnedOffVm = model.addVar(lb=0.0, vtype=GRB.INTEGER)
                    
                    # store the decision variables in the dictionaries
                    activeVmEnergyConsumptionDecVarDict[str(vmType)] = energyConsumptionOfActiveVm
                    numOfActiveVmsDecVarDict[str(vmType)] = numOfActiveVms
                    turnedOnVmDecVarDict[str(vmType)] = numOfTurnedOnVm
                    turnedOffVmDecVarDict[str(vmType)] = numOfTurnedOffVm
                    
                userActiveVmEnergyConsumptionDecVarDict[str(userIndex)] = activeVmEnergyConsumptionDecVarDict
                userNumOfActiveVmsDecVarDict[str(userIndex)] = numOfActiveVmsDecVarDict
                userTurnedOnVmDecVarDict[str(userIndex)] = turnedOnVmDecVarDict
                userTurnedOffVmDecVarDict[str(userIndex)] = turnedOffVmDecVarDict
            
            providerGreenEnergyUsage = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            
            providerActiveVmEnergyConsumptionDecVarDict[str(provider)] = userActiveVmEnergyConsumptionDecVarDict
            providerNumOfActiveVmsDecVarDict[str(provider)] = userNumOfActiveVmsDecVarDict
            providerTurnedOnVmDecVarDict[str(provider)] = userTurnedOnVmDecVarDict
            providerTurnedOffVmDecVarDict[str(provider)] = userTurnedOffVmDecVarDict
            providerGreenEnergyDecVarDict[str(provider)] = providerGreenEnergyUsage
    
    activeVmEnergyConsumptionDecVarList.append(providerActiveVmEnergyConsumptionDecVarDict)
    numOfActiveVmsDecVarList.append(providerNumOfActiveVmsDecVarDict)
    turnedOnVmVarList.append(providerTurnedOnVmDecVarDict)
    turnedOffVmVarList.append(providerTurnedOffVmDecVarDict)
    greenEnergyUsageDecVarList.append(providerGreenEnergyDecVarDict)
                    
                    

# Network energy
routerAreaDict = getRouterAreaDict(routerData)

# decision variables
routerEnergyConsumptionDecVarList = []
routerStatusDecVarList = []
routerOnDecVarList = []
routerOffDecVarList = []
routerBandwidthUsageDecVarList = []

# a fully loaded router consume 3.84 KW
fullyLoadedRouterEnergyConsumption = 3840
idleRouterEnergyConsumption = 1000
# assume that switch the state of router is the 5% of fully loaded energy consumption
routerChangeStateEnergyConsumption = fullyLoadedRouterEnergyConsumption * 0.05
# assume that the capacity of each router is 1 Gbps
routerCapacity = 1.0
    
# equation 9 the cost of energy consumption of network flow
for timeStage in range(0, timeLength) :
    routerEnergyConsumptionDecVarDict = dict()
    routerStatusDecVarDict = dict()
    routerOnDecVarDict = dict()
    routerOffDecVarDict = dict()
    routerBandwidthUsageDecVarDict = dict()
    for area in routerAreaDict :
        areaRouterList = routerAreaDict[area]
        for router in areaRouterList :
            routerIndex = router.routerIndex
            
            routerEnergyConsumption = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            
            routerStatus = model.addVar(vtype=GRB.BINARY)
            routerOn = model.addVar(vtype=GRB.BINARY)
            routerOff = model.addVar(vtype=GRB.BINARY)
            
            routerBandwidthUsage = model.addVar(vtype=GRB.CONTINUOUS)
            
            routerEnergyConsumptionDecVarDict[str(routerIndex)] = routerEnergyConsumption
            routerStatusDecVarDict[str(routerIndex)] = routerStatus
            routerOnDecVarDict[str(routerIndex)] = routerOn
            routerOffDecVarDict[str(routerIndex)] = routerOff
            routerBandwidthUsageDecVarDict[str(routerIndex)] = routerBandwidthUsage
            
    routerEnergyConsumptionDecVarList.append(routerEnergyConsumptionDecVarDict)
    routerStatusDecVarList.append(routerStatusDecVarDict)
    routerOnDecVarList.append(routerOnDecVarDict)
    routerOffDecVarList.append(routerOffDecVarDict)
    routerBandwidthUsageDecVarList.append(routerBandwidthUsageDecVarDict)

# network flow decision variables
edgeList = networkTopology['edges']

edgeFlowDecVarList = []

for timeStage in range(0, timeLength) :
    edgeFlowDecVarDict = dict()
    for edgeIndex in range(0, len(edgeList)) :
        flowTypeDecVarDict = dict()
        for flowTypeIndex in range(2) :
            flowTypeList = ['in', 'out']
            flowType = flowTypeList[flowTypeIndex]
            userFlowDecVarDict = dict()
            for userIndex in range(0, numOfUsers) :
                flow = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
                userFlowDecVarDict[str(userIndex)] = flow
            flowTypeDecVarDict[str(flowType)] = userFlowDecVarDict
        edgeFlowDecVarDict[str(edgeIndex)] = flowTypeDecVarDict
    edgeFlowDecVarList.append(edgeFlowDecVarDict)



# update model
model.update()

# equation 1 total cost function
model.setObjective(quicksum([vmCostDecVarList[i] * vmCostParameterList[i] for i in range(0, len(vmCostDecVarList))]) + quicksum(bandwidthCostDecVarList[i] * bandwidthCostParameterList[i] for i in range(0, len(bandwidthCostDecVarList))) + quicksum([sortedEnergyPrice[timeStage][area] * quicksum([valueOfPUE * quicksum([activeVmEnergyConsumptionDecVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] + changeStateEnergyConsumption[str(vmTypeList[vmTypeIndex])] * turnedOnVmVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] + changeStateEnergyConsumption[str(vmTypeList[vmTypeIndex])] * turnedOffVmVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] for userIndex in range(0, numOfUsers) for vmTypeIndex in range(0, len(vmTypeList))]) - greenEnergyUsageDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict]) + quicksum([sortedEnergyPrice[timeStage][area] * quicksum([routerEnergyConsumptionDecVarList[timeStage][router.routerIndex] + routerChangeStateEnergyConsumption * routerOnDecVarList[timeStage][router.routerIndex] + routerChangeStateEnergyConsumption * routerOffDecVarList[timeStage][router.routerIndex] for router in routerAreaDict[area]]) for timeStage in range(0, timeLength) for area in routerAreaDict]), GRB.MINIMIZE)

# VM energy objective function
# quicksum([sortedEnergyPrice[timeStage][area] * quicksum([valueOfPUE * quicksum([activeVmDecVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] + turnedOnVmVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] + turnedOffVmVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] for userIndex in range(0, numOfUsers) for vmTypeIndex in range(0, len(vmTypeList))]) - greenEnergyUsageDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict])

# network energy
# quicksum([sortedEnergyPrice[timeStage][area] * quicksum([routerEnergyConsumptionDecVarList[timeStage][router.routerIndex] + routerChangeStateEnergyConsumption * routerOnDecVarList[timeStage][router.routerIndex] + routerChangeStateEnergyConsumption * routerOffDecVarList[timeStage][router.routerIndex] for router in routerAreaDict[area]]) for timeStage in range(0, timeLength) for area in routerAreaDict])

# add constraints

# constraint 5 : the total energy consumption of active VMs the product of the energy consumption of each VM type and the number of active VMs
for timeStage in range(0, timeLength) :
    # constraint 5
    providerActiveVmEnergyConsumptionDecVarDict = activeVmEnergyConsumptionDecVarList[timeStage]
    providerNumOfActiveVmsDecVarDict = numOfActiveVmsDecVarList[timeStage]
    
    # constraint 6, 7, 8
    providerDecVar_uti = vmUtilizationDecVar[timeStage]
    providerDecVar_onDemand = vmOnDemandDecVar[timeStage]
    
    # constraint 7, 8
    providerTurnedOnVmDecVarDict = turnedOnVmVarList[timeStage]
    providerTurnedOffVmDecVarDict = turnedOffVmVarList[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        userActiveVmEnergyConsumptionDecVarDict = providerActiveVmEnergyConsumptionDecVarDict[str(provider)]
        userNumOfActiveVmsDecVarDict = providerNumOfActiveVmsDecVarDict[str(provider)]
        
        userDecVar_uti = providerDecVar_uti[str(provider)]
        userDecVar_onDemand = providerDecVar_onDemand[str(provider)]
        
        userTurnedOnVmDecVarDict = providerTurnedOnVmDecVarDict[str(provider)]
        userTurnedOffVmDecVarDict = providerTurnedOffVmDecVarDict[str(provider)]
        for userIndex in range(0, numOfUsers) :
            activeVmEnergyConsumptionDecVarDict = userActiveVmEnergyConsumptionDecVarDict[str(userIndex)]
            numOfActiveVmsDecVarDict = userNumOfActiveVmsDecVarDict[str(userIndex)]
            
            vmDecVar_uti = userDecVar_uti[str(userIndex)]
            vmDecVar_onDemand = userDecVar_onDemand[str(userIndex)]
            
            numOfTurnedOnVmTypeDict = userTurnedOnVmDecVarDict[str(userIndex)]
            numOfTurnedOffVmTypeDict = userTurnedOffVmDecVarDict[str(userIndex)]
            for vmTypeIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmTypeIndex]
                
                energyConsumptionOfActiveVms = activeVmEnergyConsumptionDecVarDict[str(vmType)]
                numOfActiveVms = numOfActiveVmsDecVarDict[str(vmType)]
                
                vmDictOfProvider = sortedVmList[str(provider)]
                contractDictOfVmType = vmDictOfProvider[str(vmType)]
                paymentDictOfContract = contractDictOfVmType[str(1)]
                vmData = paymentDictOfContract['NoUpfront']
                
                energyConsumptionOfVmType = vmData.energyConsumption
                
                # constraint 5
                model.addConstr(energyConsumptionOfActiveVms, GRB.EQUAL, numOfActiveVms * energyConsumptionOfVmType)
                
                # constraint 6
                vmUtilizationAndOnDemandDecVarList = [vmDecVar_uti[str(vmType)][str(contract)][payment] for contract in vmContractLengthList for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront']]
                vmUtilizationAndOnDemandDecVarList.append(vmDecVar_onDemand[str(vmType)])
                
                model.addConstr(numOfActiveVms, GRB.EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList))
                
                # constraint 7 and constraint 8
                numOfTurnedOnVm = numOfTurnedOnVmTypeDict[str(vmType)]
                numOfTurnedOffVm = numOfTurnedOffVmTypeDict[str(vmType)]
                
                if timeStage == 0 :
                    previousTimeStageVmUtilizationAndOnDemandDecVarList = []
                    model.addConstr(numOfTurnedOnVm, GRB.GREATER_EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList))
                    model.addConstr(numOfTurnedOffVm, GRB.GREATER_EQUAL, -1 * quicksum(vmUtilizationAndOnDemandDecVarList))
                else :
                    previousTimeStageProviderDecVar_uti = vmUtilizationDecVar[timeStage-1]
                    previousTimeStageProviderDecVar_onDemand = vmOnDemandDecVar[timeStage - 1]
                    
                    previousTimeStageUserDecVar_uti = previousTimeStageProviderDecVar_uti[str(provider)]
                    previousTimeStageUserDecVar_onDemand = previousTimeStageProviderDecVar_onDemand[str(provider)]
                    
                    previousTimeStageVmDecVar_uti = previousTimeStageUserDecVar_uti[str(userIndex)]
                    previousTimeStageVmDecVar_onDemand = previousTimeStageUserDecVar_onDemand[str(userIndex)]
                    
                    previousTimeStageUtilizedVmDecVar = previousTimeStageVmDecVar_uti[str(vmType)]
                    previousTimeStageOnDemandDecVar = previousTimeStageVmDecVar_onDemand[str(vmType)]
                    
                    previousTimeStageVmUtilizationAndOnDemandDecVarList = [previousTimeStageUtilizedVmDecVar[str(contract)][str(payment)] for contract in [1, 3] for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront']]
                    previousTimeStageVmUtilizationAndOnDemandDecVarList.append(previousTimeStageOnDemandDecVar)
                    
                    model.addConstr(numOfTurnedOnVm, GRB.GREATER_EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList) - quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList))
                    model.addConstr(numOfTurnedOffVm, GRB.GREATER_EQUAL, quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList) - quicksum(vmUtilizationAndOnDemandDecVarList))
                    
                
                

# constraint 6 : the number of active VMs is the sum of utlization and on-demand VMs
'''
for timeStage in range(0, timeLength) :
    providerNumOfActiveVmsDecVarDict = numOfActiveVmsDecVarList[timeStage]
    providerDecVar_uti = vmUtilizationDecVar[timeStage]
    providerDecVar_onDemand = vmOnDemandDecVar[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        userNumOfActiveVmsDecVarDict = providerNumOfActiveVmsDecVarDict[str(provider)]
        userDecVar_uti = providerDecVar_uti[str(provider)]
        userDecVar_onDemand = providerDecVar_onDemand[str(provider)]
        for userIndex in range(0, numOfUsers) :
            numOfActiveVmsDecVarDict = userNumOfActiveVmsDecVarDict[str(userIndex)]
            vmDecVar_uti = userDecVar_uti[str(userIndex)]
            vmDecVar_onDemand = userDecVar_onDemand[str(userIndex)]
            for vmTypeIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmTypeIndex]
                
                numOfActiveVms = numOfActiveVmsDecVarDict[str(vmType)]
                
                contractAndPaymentDecVarList = [vmDecVar_uti[str(vmType)][str(contract)][payment] for contract in vmContractLengthList for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront']]
                contractAndPaymentDecVarList.append(vmDecVar_onDemand[str(vmType)])
                
                model.addConstr(numOfActiveVms, GRB.EQUAL, quicksum(contractAndPaymentDecVarList))
'''

# constraint 7 and constraint 8 : VM_On constraint and VM_Off constraint
'''
for timeStage in range(0, timeLength) :
    providerTurnedOnVmDecVarDict = turnedOnVmVarList[timeStage]
    providerTurnedOffVmDecVarDict = turnedOffVmVarList[timeStage]
    
    providerDecVar_uti = vmUtilizationDecVar[timeStage]
    providerDecVar_onDemand = vmOnDemandDecVar[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        userTurnedOnVmDecVarDict = providerTurnedOnVmDecVarDict[str(provider)]
        userTurnedOffVmDecVarDict = providerTurnedOffVmDecVarDict[str(provider)]
        
        userDecVar_uti = providerDecVar_uti[str(provider)]
        userDecVar_onDemand = providerDecVar_onDemand[str(provider)]
        for userIndex in range(0, numOfUsers) :
            numOfTurnedOnVmTypeDict = userTurnedOnVmDecVarDict[str(userIndex)]
            numOfTurnedOffVmTypeDict = userTurnedOffVmDecVarDict[str(userIndex)]
            
            vmDecVar_uti = userDecVar_uti[str(userIndex)]
            vmDecVar_onDemand = userDecVar_onDemand[str(userIndex)]
            
            for vmTypeIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmTypeIndex]
                numOfTurnedOnVm = numOfTurnedOnVmTypeDict[str(vmType)]
                numOfTurnedOffVm = numOfTurnedOffVmTypeDict[str(vmType)]
                
                vmUtilizationAndOnDemandDecVarList = [vmDecVar_uti[str(vmType)][str(contract)][str(payment)] for contract in vmContractLengthList for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront']]
                vmUtilizationAndOnDemandDecVarList.append(vmDecVar_onDemand[str(vmType)])
                
                if timeStage == 0 :
                    previousTimeStageVmUtilizationAndOnDemandDecVarList = []
                    model.addConstr(numOfTurnedOnVm, GRB.GREATER_EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList))
                    model.addConstr(numOfTurnedOffVm, GRB.GREATER_EQUAL, -1 * quicksum(vmUtilizationAndOnDemandDecVarList))
                else :
                    previousTimeStageProviderDecVar_uti = vmUtilizationDecVar[timeStage-1]
                    previousTimeStageProviderDecVar_onDemand = vmOnDemandDecVar[timeStage - 1]
                    
                    previousTimeStageUserDecVar_uti = previousTimeStageProviderDecVar_uti[str(provider)]
                    previousTimeStageUserDecVar_onDemand = previousTimeStageProviderDecVar_onDemand[str(provider)]
                    
                    previousTimeStageVmDecVar_uti = previousTimeStageUserDecVar_uti[str(userIndex)]
                    previousTimeStageVmDecVar_onDemand = previousTimeStageUserDecVar_onDemand[str(userIndex)]
                    
                    previousTimeStageUtilizedVmDecVar = previousTimeStageVmDecVar_uti[str(vmType)]
                    previousTimeStageOnDemandDecVar = previousTimeStageVmDecVar_onDemand[str(vmType)]
                    
                    previousTimeStageVmUtilizationAndOnDemandDecVarList = [previousTimeStageUtilizedVmDecVar[str(contract)][str(payment)] for contract in [1, 3] for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront']]
                    previousTimeStageVmUtilizationAndOnDemandDecVarList.append(previousTimeStageOnDemandDecVar)
                    
                    model.addConstr(numOfTurnedOnVm, GRB.GREATER_EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList) - quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList))
                    model.addConstr(numOfTurnedOffVm, GRB.GREATER_EQUAL, quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList) - quicksum(vmUtilizationAndOnDemandDecVarList))
'''

# constraint 10, 11 : Router_On and Router_Off constraints
for timeStage in range(0, timeLength) :
    # constraint 10, 11, 12
    routerStatusDecVarDict = routerStatusDecVarList[timeStage]
    # constraint 10, 11
    routerOnDecVarDict = routerOnDecVarList[timeStage]
    routerOffDecVarDict = routerOffDecVarList[timeStage]
    
    # constraint 12
    routerEnergyConsumptionDecVarDict = routerEnergyConsumptionDecVarList[timeStage]
    routerBandwidthUsageDecVarDict = routerBandwidthUsageDecVarList[timeStage]
    
    # constraint 13
    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
    for router in routerData :
        routerIndex = router.routerIndex
        
        routerStatus = routerStatusDecVarDict[str(routerIndex)]
        routerOn = routerOnDecVarDict[str(routerIndex)]
        routerOff = routerOffDecVarDict[str(routerIndex)]
        
        routerEnergyConsumption = routerEnergyConsumptionDecVarDict[str(routerIndex)]
        routerBandwidthUsage = routerBandwidthUsageDecVarDict[str(routerIndex)]
        
        # constraint 10, 11
        if timeStage == 0 :
            model.addConstr(routerOn, GRB.GREATER_EQUAL, routerStatus)
            model.addConstr(routerOff, GRB.GREATER_EQUAL, -1 * routerStatus)
        else :
            previousTimeStageRouterStatusDecVarDict = routerStatusDecVarList[timeStage - 1]
            previousTimeStageRouterStatus = previousTimeStageRouterStatusDecVarDict[str(routerIndex)]
            
            model.addConstr(routerOn, GRB.GREATER_EQUAL, routerStatus - previousTimeStageRouterStatus)
            model.addConstr(routerOff, GRB.GREATER_EQUAL, previousTimeStageRouterStatus - routerStatus)
        
        # constraint 12
        model.addConstr(routerEnergyConsumption, GRB.EQUAL, routerStatus * idleRouterEnergyConsumption + routerBandwidthUsage / (2 * routerCapacity) * (fullyLoadedRouterEnergyConsumption - idleRouterEnergyConsumption))
        
        # constraint 13
        routerDirectlyConnectedEdges = router.edges
        
        inFlowEdge = [edgeFlowDecVarDict[str(edgeIndex)]['in'][str(userIndex)] for edgeIndex in routerDirectlyConnectedEdges for userIndex in range(0, numOfUsers)]
        outFlowEdge = [edgeFlowDecVarDict[str(edgeIndex)]['out'][str(userIndex)] for edgeIndex in routerDirectlyConnectedEdges for userIndex in range(0, numOfUsers)]
        
        model.addConstr(routerBandwidthUsage, GRB.EQUAL, quicksum(inFlowEdge) + quicksum(outFlowEdge))
        
# constraint 12 : the energy consumption of a router
'''
for timeStage in range(0, timeLength) :
    routerEnergyConsumptionDecVarDict = routerEnergyConsumptionDecVarList[timeStage]
    routerStatusDecVarDict = routerStatusDecVarList[timeStage]
    routerBandwidthUsageDecVarDict = routerBandwidthUsageDecVarList[timeStage]
    for router in routerData :
        routerIndex = router.routerIndex
        routerEnergyConsumption = routerEnergyConsumptionDecVarDict[str(routerIndex)]
        routerStatus = routerStatusDecVarDict[str(routerIndex)]
        routerBandwidthUsage = routerBandwidthUsageDecVarDict[str(routerIndex)]
        
        model.addConstr(routerEnergyConsumption, GRB.EQUAL, routerStatus * idleRouterEnergyConsumption + routerBandwidthUsage / (2 * routerCapacity) * (fullyLoadedRouterEnergyConsumption - idleRouterEnergyConsumption))
'''
    
# constraint 13 : the bandwidth usage constraint
'''
for timeStage in range(0, timeLength) :
    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
    routerBandwidthUsageDecVarDict = routerBandwidthUsageDecVarList[timeStage]
    for router in routerData :
        routerIndex = router.routerIndex
        routerDirectlyConnectedEdges = router.edges
        routerBandwidthUsage = routerBandwidthUsageDecVarDict[str(routerIndex)]
        
        inFlowEdge = [edgeFlowDecVarDict[str(edgeIndex)]['in'][str(userIndex)] for edgeIndex in routerDirectlyConnectedEdges for userIndex in range(0, numOfUsers)]
        outFlowEdge = [edgeFlowDecVarDict[str(edgeIndex)]['out'][str(userIndex)] for edgeIndex in routerDirectlyConnectedEdges for userIndex in range(0, numOfUsers)]
        
        model.addConstr(routerBandwidthUsage, GRB.EQUAL, quicksum(inFlowEdge) + quicksum(outFlowEdge))
'''

# constraint 14 : effective VM reservation
for timeStage in range(0, timeLength) :
    providerVmDecVar_uti = vmUtilizationDecVar[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        userVmDecVar_uti = providerVmDecVar_uti[str(provider)]
        for userIndex in range(0, numOfUsers) :
            vmTypeDecVar_uti = userVmDecVar_uti[str(userIndex)]
            for vmTypeIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmTypeIndex]
                contractVmDecVar_uti = vmTypeDecVar_uti[str(vmType)]
                for contractLength in vmContractLengthList :
                    paymentVmDecVar_uti = contractVmDecVar_uti[str(contractLength)]
                    for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront'] :
                        vmUtilizationDecVar = paymentVmDecVar_uti[str(payment)]
                        
                        userEffectiveVmResDecVarDict = effectiveVmResDecVarDict[str(provider)]
                        vmTypeEffectiveVmResDecVarDict = userEffectiveVmResDecVarDict[str(userIndex)]
                        contractEffectiveVmResDecVarDict = vmTypeEffectiveVmResDecVarDict[str(vmType)]
                        paymentEffectiveVmResDecVarDict = contractEffectiveVmResDecVarDict[str(contractLength)]
                        effectiveVmResDecVarList = paymentEffectiveVmResDecVarDict[str(payment)]
                        
                        model.addConstr(vmUtilizationDecVar, GRB.LESS_EQUAL, quicksum(effectiveVmResDecVarList[timeStage]))
                        
# constraint 15
vmUtilizationDecVar = []
vmOnDemandDecVar = []
for timeStage in range(0, timeLength) :
    userVmDemandDict = vmDemandList[timeStage]
    for userIndex in range(0, numOfUsers) :
        vmTypeDemandDict = userVmDemandDict[str(userIndex)]
        for vmTypeIndex in range(0, len(vmTypeList)) :
            vmType = vmTypeList[vmTypeIndex]
            vmDemand = vmTypeDemandDict[str(vmType)]
            
            utlizationAndOnDemandVmDecVarList = []
            
            for providerIndex in range(0, len(providerList)) :
                provider = providerList[providerIndex]
                for contractLength in vmContractLengthList :
                    for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront'] :
                        providerVmDecVarDict_uti = vmUtilizationDecVar[timeStage]
                        userVmDecVarDict_uti = providerVmDecVarDict_uti[str(provider)]
                        
                        vmTypeDecVarDict_uti = userVmDecVarDict_uti[str(userIndex)]
                        
                        contractDecVarDict_uti = vmTypeDecVarDict_uti[str(vmType)]
                        
                        paymentDecVarDict_uti = contractDecVarDict_uti[str(contractLength)]
                        
                        utilizationDecVar = paymentDecVarDict_uti[payment]
                        
                        utlizationAndOnDemandVmDecVarList.append(utilizationDecVar)
                
                providerVmDecVarDict_onDemand = vmOnDemandDecVar[timeStage]
                userVmDecVarDict_onDemand = providerVmDecVarDict_onDemand[str(provider)]
                vmTypeDecVarDict_onDemand = userVmDecVarDict_onDemand[str(userIndex)]
                onDemandDecVar = vmTypeDecVarDict_onDemand[str(vmType)]
                utlizationAndOnDemandVmDecVarList.append(onDemandDecVar)
            
            model.addConstr(quicksum(utlizationAndOnDemandVmDecVarList), GRB.GREATER_EQUAL, vmDemand)
            




















