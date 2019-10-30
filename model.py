# Build gurobi model
from readData import *
from subFunctions import *
from gurobipy import *
import random
            
# get instance data from csv file, get get the lists of vm types and cloud providers from instance data

instanceData = getVirtualResource()
providerList = getProvidersNameList(instanceData)
providerAreaDict = getProviderAreaDict(instanceData)
vmTypeList = getVmTypesList(instanceData)
storageAndBandwidthPrice = getCostOfStorageBandBandwidth()
networkTopology = getNetworkTopology()


model = Model('VM_network_and_energy_optimization_model')

timeLength = 500
numOfUsers = len(networkTopology['user'])
vmContractLengthList = [10, 30]
# vmContractLengthList = [1, 3]

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

print('VM Cost decision variable complete')

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

# a list containing the effective bandwidth
effectiveBandDecVarDict = dict()

# initialize the bandwidth dictionary
for userIndex in range(0, numOfUsers) :
    routerEffectiveBandDecVarDict = dict()
    for routerIndex in range(0, numOfRouters) :
        contractEffectiveBandDecVarDict = dict()
        for bandResContractLength in [5, 10] :
            paymentEffectiveBandDecVarDict = dict()
            for bandResPayment in ['No upfront', 'Partial upfront', 'All upfront'] :
                effectiveBandDecVarList = []
                for timeStage in range(0, timeLength) :
                    effectiveBandDecVarList.append([])
                paymentEffectiveBandDecVarDict[str(bandResPayment)] = effectiveBandDecVarList
            contractEffectiveBandDecVarDict[str(bandResContractLength)] = paymentEffectiveBandDecVarDict
        routerEffectiveBandDecVarDict[str(routerIndex)] = contractEffectiveBandDecVarDict
    effectiveBandDecVarDict[str(userIndex)] = routerEffectiveBandDecVarDict

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
                    
                    # add the decision variables to the effective bandiwdth list
                    routerEffectiveBandDecVarDict = effectiveBandDecVarDict[str(userIndex)]
                    contractEffectiveBandDecVarDict = routerEffectiveBandDecVarDict[str(routerIndex)]
                    paymentEffectiveBandDecVarDict = contractEffectiveBandDecVarDict[str(bandResContractLength)]
                    effectiveBandDecVarList = paymentEffectiveBandDecVarDict[str(bandPaymentOption)]
                    
                    for currentTimeStage in range(timeStage, min(timeLength, timeStage + bandResContractLength)) :
                        effectiveBandDecVarAtCurrentTimeStage = effectiveBandDecVarList[currentTimeStage]
                        effectiveBandDecVarAtCurrentTimeStage.append(bandReservation)
                    
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

print('Bandwidth Cost decision variable complete')

# VM energy

# Power Usage Effectiveness
valueOfPUE = 1.58
chargingDischargingEffeciency = 0.88
energyPriceDict = readEnergyPricingFile()
sortedEnergyPrice = sortEnergyPrice(energyPriceDict, timeLength)

# the list used to calculate the VM energy consumption
# the energy consumption of active VMs
activeVmEnergyConsumptionDecVarList = []
# the number of active VMs owned by each user
numOfActiveVmsDecVarList = []
# the number of VMs turned by each user
turnedOnVmVarList = []
# the number of VMs turned off by each user
turnedOffVmVarList = []
# the green energy usage of each provider
greenEnergyUsageDecVarList = []
# record the energy consumption when a VM is turned on or off
vmChangeStateEnergyDict = dict()
# the amount of energy that solar panals supply DC
solarEnergyToDcDecVarList = []
# the amount of energy that solar panals charge the battery
solarEnergyToBatteryDecVarList = []
# the amount of energy that battery supplies DC
batteryEnergyToDcDecVarList = []
# the energy level of a battery at the beginning of each time period
batteryEnergyLevelDecVarList_beg = []
# the energy level of a battery at the end of each time period
batteryEnergyLevelDecVarList_end = []

# equation 4 the cost of energy consumption of active VMs
for timeStage in range(0, timeLength) :
    providerActiveVmEnergyConsumptionDecVarDict = dict()
    providerNumOfActiveVmsDecVarDict = dict()
    providerTurnedOnVmDecVarDict = dict()
    providerTurnedOffVmDecVarDict = dict()
    providerGreenEnergyDecVarDict = dict()
    providerSolarToDcDecVarDict = dict()
    providerSolarToBatteryDecVarDict = dict()
    providerBatteryToDcDecVarDict = dict()
    providerBatteryEnergyLevelDecVarDict_beg = dict()
    providerBatteryEnergyLevelDecVarDict_end = dict()
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
            solarToDc = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            solarToBattery = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            batteryToDc = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            battegyEnergyLevel_beg = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            batteryEnergyLevel_end = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            
            providerActiveVmEnergyConsumptionDecVarDict[str(provider)] = userActiveVmEnergyConsumptionDecVarDict
            providerNumOfActiveVmsDecVarDict[str(provider)] = userNumOfActiveVmsDecVarDict
            providerTurnedOnVmDecVarDict[str(provider)] = userTurnedOnVmDecVarDict
            providerTurnedOffVmDecVarDict[str(provider)] = userTurnedOffVmDecVarDict
            providerGreenEnergyDecVarDict[str(provider)] = providerGreenEnergyUsage
            providerSolarToDcDecVarDict[str(provider)] = solarToDc
            providerSolarToBatteryDecVarDict[str(provider)] = solarToBattery
            providerBatteryToDcDecVarDict[str(provider)] = batteryToDc
            providerBatteryEnergyLevelDecVarDict_beg[str(provider)] = battegyEnergyLevel_beg
            providerBatteryEnergyLevelDecVarDict_end[str(provider)] = batteryEnergyLevel_end
    
    activeVmEnergyConsumptionDecVarList.append(providerActiveVmEnergyConsumptionDecVarDict)
    numOfActiveVmsDecVarList.append(providerNumOfActiveVmsDecVarDict)
    turnedOnVmVarList.append(providerTurnedOnVmDecVarDict)
    turnedOffVmVarList.append(providerTurnedOffVmDecVarDict)
    greenEnergyUsageDecVarList.append(providerGreenEnergyDecVarDict)
    solarEnergyToDcDecVarList.append(providerSolarToDcDecVarDict)
    solarEnergyToBatteryDecVarList.append(providerSolarToBatteryDecVarDict)
    batteryEnergyToDcDecVarList.append(providerBatteryToDcDecVarDict)
    batteryEnergyLevelDecVarList_beg.append(providerBatteryEnergyLevelDecVarDict_beg)
    batteryEnergyLevelDecVarList_end.append(providerBatteryEnergyLevelDecVarDict_end)
                    
print('VM Energy decision variable complete')

# Network energy
routerAreaDict = getRouterAreaDict(routerData)

# decision variables
# the energy consumption of each router
routerEnergyConsumptionDecVarList = []
# the statement of each router which is represented as binary bariables
routerStatusDecVarList = []
# if a router is turned on in current time period, the value of this variable is gonna be 1
routerOnDecVarList = []
# if a router is turned off in current time period, the value of this variable is gonna be 1
routerOffDecVarList = []
# the bandwidth usage, which is calculated by the sum of flow of edges directly connected to the router
routerBandwidthUsageDecVarList = []

# a fully loaded router consume 3.84 KW
fullyLoadedRouterEnergyConsumption = 3840
idleRouterEnergyConsumption = 1000
# assume that switch the state of router is the 5% of fully loaded energy consumption
routerChangeStateEnergyConsumption = fullyLoadedRouterEnergyConsumption * 0.05
# assume that the capacity of each router is 1,000 Gbps
routerCapacity = 1000.0
    
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

print('Network Energy decision variable complete')

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

print('Edge flow decision variable complete')

# update model
model.update()

# equation 1 total cost function
model.setObjective(quicksum([vmCostDecVarList[index] * vmCostParameterList[index] for index in range(0, len(vmCostDecVarList))]) + quicksum([bandwidthCostDecVarList[index] * bandwidthCostParameterList[index] for index in range(0, len(bandwidthCostDecVarList))]) + quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([valueOfPUE * quicksum([activeVmEnergyConsumptionDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyDict[str(vmType)] * turnedOnVmVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyDict[str(vmType)] * turnedOffVmVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] for userIndex in range(0, numOfUsers) for vmType in vmTypeList]) - greenEnergyUsageDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict]) + quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([routerEnergyConsumptionDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOnDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOffDecVarList[timeStage][str(router.routerIndex)] for router in routerAreaDict[area]]) for timeStage in range(0, timeLength) for area in routerAreaDict]), GRB.MINIMIZE)

# The cost of VM usage objective function
# quicksum([vmCostDecVarList[index] * vmCostParameterList[index] for index in range(0, len(vmCostDecVarList))])

# The cost of bandwidth usage objective function
# quicksum([bandwidthCostDecVarList[index] * bandwidthCostParameterList[index] for index in range(0, len(bandwidthCostDecVarList))])

# VM energy objective function
# quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([valueOfPUE * quicksum([activeVmEnergyConsumptionDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyDict[str(vmType)] * turnedOnVmVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyDict[str(vmType)] * turnedOffVmVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] for userIndex in range(0, numOfUsers) for vmType in vmTypeList]) - greenEnergyUsageDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict])

# network energy objective function
# quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([routerEnergyConsumptionDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOnDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOffDecVarList[timeStage][str(router.routerIndex)] for router in routerAreaDict[area]]) for timeStage in range(0, timeLength) for area in routerAreaDict])

print('Total cost objective function complete')

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
                paymentDictOfContract = contractDictOfVmType[str(vmContractLengthList[0])]
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
                    
                    previousTimeStageVmUtilizationAndOnDemandDecVarList = [previousTimeStageUtilizedVmDecVar[str(contract)][str(payment)] for contract in vmContractLengthList for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront']]
                    previousTimeStageVmUtilizationAndOnDemandDecVarList.append(previousTimeStageOnDemandDecVar)
                    
                    model.addConstr(numOfTurnedOnVm, GRB.GREATER_EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList) - quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList))
                    model.addConstr(numOfTurnedOffVm, GRB.GREATER_EQUAL, quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList) - quicksum(vmUtilizationAndOnDemandDecVarList))
                    
print('Constraint 5, 6, 7, 8 complete')
                

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
        
        edgeInFlow = []
        edgeOutFlow = []
        
        for edgeIndex in routerDirectlyConnectedEdges :
            flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
            
            flowInDecVarDict = flowTypeDecVarDict['in']
            flowOutDecVarDict = flowTypeDecVarDict['out']
            
            for userIndex in range(0, numOfUsers) :
                userFlowIn = flowInDecVarDict[str(userIndex)]
                userFlowOut = flowOutDecVarDict[str(userIndex)]
                
                edgeInFlow.append(userFlowIn)
                edgeOutFlow.append(userFlowOut)
        
        
        model.addConstr(routerBandwidthUsage, GRB.EQUAL, quicksum(edgeInFlow) + quicksum(edgeOutFlow))
        
print('Constraint 10, 11, 12, 13 complete')

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
        
        edgeInFlow = []
        edgeOutFlow = []
        
        for edgeIndex in routerDirectlyConnectedEdges :
            flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
            
            flowInDecVarDict = flowTypeDecVarDict['in']
            flowOutDecVarDict = flowTypeDecVarDict['out']
            
            for userIndex in range(0, numOfUsers) :
                userFlowIn = flowInDecVarDict[str(userIndex)]
                userFlowOut = flowOutDecVarDict[str(userIndex)]
                
                edgeInFlow.append(userFlowIn)
                edgeOutFlow.append(userFlowOut)
        
        model.addConstr(routerBandwidthUsage, GRB.EQUAL, quicksum(edgeInFlow) + quicksum(edgeOutFlow))
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
                        vmUtilization = paymentVmDecVar_uti[str(payment)]
                        
                        userEffectiveVmResDecVarDict = effectiveVmResDecVarDict[str(provider)]
                        vmTypeEffectiveVmResDecVarDict = userEffectiveVmResDecVarDict[str(userIndex)]
                        contractEffectiveVmResDecVarDict = vmTypeEffectiveVmResDecVarDict[str(vmType)]
                        paymentEffectiveVmResDecVarDict = contractEffectiveVmResDecVarDict[str(contractLength)]
                        effectiveVmResDecVarList = paymentEffectiveVmResDecVarDict[str(payment)]
                        
                        model.addConstr(vmUtilization, GRB.LESS_EQUAL, quicksum(effectiveVmResDecVarList[timeStage]))

print('Constraint 14 complete')

# constraint 15 : demand constraint
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

print('Constraint 15 complete')
            
# constraint 16, 17, 18 : cloud provider resource upper bound limit
cloudProvidersDict = getProviderCapacity(networkTopology['provider'])
instanceReqDict = getInstanceReqDict(instanceData)
for timeStage in range(0, timeLength) :
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        cloudProviderObj = cloudProvidersDict[str(provider)]
        
        coreLimit = cloudProviderObj.coresLimit
        storageLimit = cloudProviderObj.storageLimit
        internalBandLimit = cloudProviderObj.internalBandwidthLimit
        
        vmCoreReqList = []
        vmStorageReqList = []
        vmInternalBandReqList = []
        
        vmTypeUtilizedAndOnDemandDecVarList = []
        
        for vmTypeIndex in range(0, len(vmTypeList)) :
            vmType = vmTypeList[vmTypeIndex]
            vmObj = instanceReqDict[str(vmType)]
            
            vmCoreReq = vmObj.coreReq
            vmStorageReq = vmObj.storageReq
            vmInternalBandReq = vmObj.networkReq
            
            currentVmTypeUtilizedAndOnDemandDecVarList = []
            for userIndex in range(0, numOfUsers) :
                for contractLength in vmContractLengthList :
                    for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront'] :
                        providerVmDecVarDict_uti = vmUtilizationDecVar[timeStage]
                        userVmDecVarDict_uti = providerVmDecVarDict_uti[str(provider)]
                        vmTypeDecVarDict_uti = userVmDecVarDict_uti[str(userIndex)]
                        contractDecVarDict_uti = vmTypeDecVarDict_uti[str(vmType)]
                        paymentDecVarDict_uti = contractDecVarDict_uti[str(contractLength)]
                        utilizationDecVar = paymentDecVarDict_uti[payment]
                        
                        currentVmTypeUtilizedAndOnDemandDecVarList.append(utilizationDecVar)
                        
                providerVmDecVarDict_onDemand = vmOnDemandDecVar[timeStage]
                userVmDecVarDict_onDemand = providerVmDecVarDict_onDemand[str(provider)]
                vmTypeDecVarDict_onDemand = userVmDecVarDict_onDemand[str(userIndex)]
                onDemandDecVar = vmTypeDecVarDict_onDemand[str(vmType)]
                
                currentVmTypeUtilizedAndOnDemandDecVarList.append(onDemandDecVar)
            
            vmCoreReqList.append(vmCoreReq)
            vmStorageReqList.append(vmStorageReq)
            vmInternalBandReqList.append(vmInternalBandReq)
            vmTypeUtilizedAndOnDemandDecVarList.append(currentVmTypeUtilizedAndOnDemandDecVarList)
        
        # constraint 16 : host constraint
        model.addConstr(quicksum([vmCoreReqList[vmIndex] * quicksum(vmTypeUtilizedAndOnDemandDecVarList[vmIndex]) for vmIndex in range(0, len(vmCoreReqList))]), GRB.LESS_EQUAL, coreLimit)
        
        # constraint 17 : storage constraint
        model.addConstr(quicksum([vmStorageReqList[vmIndex] * quicksum(vmTypeUtilizedAndOnDemandDecVarList[vmIndex]) for vmIndex in range(0, len(vmStorageReqList))]), GRB.LESS_EQUAL, storageLimit)
        
        # constraint 18 : internal bandwidth constraint
        model.addConstr(quicksum([vmInternalBandReqList[vmIndex] * quicksum(vmTypeUtilizedAndOnDemandDecVarList[vmIndex]) for vmIndex in range(0, len(vmInternalBandReqList))]), GRB.LESS_EQUAL, internalBandLimit)

print('Constraint 16, 17, 18 complete')

# constraint 19 : VM decision variables integer constraint
for timeStage in range(0, timeLength) :
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        for userIndex in range(0, numOfUsers) :
            for vmTypeIndex in range(0, len(vmTypeList)) :
                for contractLength in vmContractLengthList :
                    for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront'] :
                        providerVmDecVarDict_uti = vmUtilizationDecVar[timeStage]
                        userVmDecVarDict_uti = providerVmDecVarDict_uti[str(provider)]
                        vmTypeDecVarDict_uti = userVmDecVarDict_uti[str(userIndex)]
                        contractDecVarDict_uti = vmTypeDecVarDict_uti[str(vmType)]
                        paymentDecVarDict_uti = contractDecVarDict_uti[str(contractLength)]
                        utilizationDecVar = paymentDecVarDict_uti[payment]
                        
                        model.addConstr(utilizationDecVar, GRB.GREATER_EQUAL, 0)
                        
                providerVmDecVarDict_onDemand = vmOnDemandDecVar[timeStage]
                userVmDecVarDict_onDemand = providerVmDecVarDict_onDemand[str(provider)]
                vmTypeDecVarDict_onDemand = userVmDecVarDict_onDemand[str(userIndex)]
                onDemandDecVar = vmTypeDecVarDict_onDemand[str(vmType)]
                
                model.addConstr(onDemandDecVar, GRB.GREATER_EQUAL, 0)

print('Constraint 19 complete')
                        
# constraint 20 : effective bandiwdth
for userIndex in range(0, numOfUsers) :
    for router in routerData :
        routerIndex = router.routerIndex
        for bandContractLength in [5, 10] :
            for bandPayment in ['No upfront', 'Partial upfront', 'All upfront'] :
                for timeStage in range(0, timeLength) :
                    # effective bandwidth
                    routerEffectiveBandDecVarDict = effectiveBandDecVarDict[timeStage]
                    contractEffectiveDecVarDict = routerEffectiveBandDecVarDict[str(routerIndex)]
                    paymentEffectiveDecVarDict = contractEffectiveDecVarDict[str(bandContractLength)]
                    effectiveBandDecVarList = paymentEffectiveDecVarDict[str(bandPayment)]
                    
                    effectiveBandDecVarAtCurrentTimeStage = effectiveBandDecVarList[timeStage]
                    
                    # bandwidth utilization
                    userBandUtilization = bandUtilizationDecVar[timeStage]
                    routerBandUtilization = userBandUtilization[str(userIndex)]
                    contractBandUtilization = routerBandUtilization[str(routerIndex)]
                    paymentBandUtilization = contractBandUtilization[str(bandContractLength)]
                    bandUtilization = paymentBandUtilization[str(bandPayment)]
                    
                    model.addConstr(bandUtilization, GRB.LESS_EQUAL, quicksum(effectiveBandDecVarAtCurrentTimeStage))

print('Constraint 20 complete')

# constraint 21 : router's bandwidth limit
for timeStage in range(0, timeLength) :
    for router in routerData :
        routerIndex = router.routerIndex
        bandUtilizationAndOnDemandDecVarList = []
        
        routerStatusDecVarDict = routerStatusDecVarList[timeStage]
        routerStatus = routerStatusDecVarDict[str(routerIndex)]
        
        for userIndex in range(0, numOfUsers) :
            for bandContractLength in [5, 10] :
                for bandPayment in ['No upfront', 'Partial upfront', 'All upfront'] :
                    userBandUtilization = bandUtilizationDecVar[timeStage]
                    
                    routerBandUtilization = userBandUtilization[str(userIndex)]
                    
                    contractBandUtilization = routerBandUtilization[str(routerIndex)]
                    
                    paymentBandUtilization = contractBandUtilization[str(bandContractLength)]
                    
                    bandUtilization = paymentBandUtilization[str(bandPayment)]
                    
                    bandUtilizationAndOnDemandDecVarList.append(bandUtilization)
                    
            userBandOnDemand = bandOnDemandDecVar[timeStage]
            routerBandOnDemand = userBandOnDemand[str(userIndex)]
            bandOnDemand = routerBandOnDemand[str(routerIndex)]
            bandUtilizationAndOnDemandDecVarList.append(bandOnDemand)
            
        model.addConstr(quicksum(bandUtilizationAndOnDemandDecVarList), GRB.LESS_EQUAL, routerStatus * 1.0)

print('Constraint 21 complete')

# constraint 22 : router status initialization
for router in routerData :
    routerIndex = router.routerIndex
    routerStatusDecVarDict = routerStatusDecVarList[0]
    routerStatus = routerStatusDecVarDict[str(routerIndex)]
    
    model.addConstr(routerStatus, GRB.EQUAL, 0)

print('Constraint 22 complete')

# constraint 23 : the non-negative constraint for bandwidth decision variables
for timeStage in range(0, timeLength) :
    userBandDecVarDict_res = bandResDecVar[timeStage]
    userBandDecVarDict_uti = bandUtilizationDecVar[timeStage]
    userBandDecVarDict_onDemand = bandOnDemandDecVar[timeStage]
    for userIndex in range(0, numOfUsers) :
        routerBandDecVarDict_res = userBandDecVarDict_res[str(userIndex)]
        routerBandDecVarDict_uti = userBandDecVarDict_uti[str(userIndex)]
        routerBandDecVarDict_onDemand = userBandDecVarDict_onDemand[str(userIndex)]
        for router in routerData :
            routerIndex = router.routerIndex
            
            contractBandDecVarDict_res = routerBandDecVarDict_res[str(routerIndex)]
            contractBandDecVarDict_uti = routerBandDecVarDict_uti[str(routerIndex)]
            bandDecVar_onDemand = routerBandDecVarDict_onDemand[str(routerIndex)]
            for bandContractLength in [5, 10] :
                paymentBandDecVarDict_res = contractBandDecVarDict_res[str(bandContractLength)]
                paymentBandDecVarDict_uti = contractBandDecVarDict_uti[str(bandContractLength)]
                for bandPayment in ['No upfront', 'Partial upfront', 'All upfront'] :
                    bandDecVar_res = contractBandDecVarDict_res[str(bandPayment)]
                    bandDecVar_uti = contractBandDecVarDict_uti[str(bandPayment)]
                    
                    model.addConstr(bandDecVar_res, GRB.GREATER_EQUAL, 0)
                    model.addConstr(bandDecVar_uti, GRB.GREATER_EQUAL, 0)
            model.addConstr(bandDecVar_onDemand, GRB.GREATER_EQUAL, 0)

print('Constraint 23 complete')

# constraint 24 : the relationship between the number of active VMs, turned on / off VMs
for timeStage in range(0, timeLength) :
    providerNumOfActiveVmsDecVarDict = numOfActiveVmsDecVarList[timeStage]
    providerNumOfTurnedOnVmsDecVarDict = turnedOnVmVarList[timeStage]
    providerNumOfTurnedOffVmsDecVarDict = turnedOffVmVarList[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        userNumOfActiveVmsDecVarDict = providerNumOfActiveVmsDecVarDict[str(provider)]
        userNumOfTurnedOnVmsDecVarDict = providerNumOfTurnedOnVmsDecVarDict[str(provider)]
        userNumOfTurnedOffVmsDecVarDict = providerNumOfTurnedOffVmsDecVarDict[str(provider)]
        for userIndex in range(0, numOfUsers) :
            numOfActiveVmsDecVarDict = userNumOfActiveVmsDecVarDict[str(userIndex)]
            numOfTurnedOnVmsDecVarDict = userNumOfTurnedOnVmsDecVarDict[str(userIndex)]
            numOfTurnedOffVmsDecVarDict = userNumOfTurnedOffVmsDecVarDict[str(userIndex)]
            for vmTypeIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmTypeIndex]
                numOfActiveVms = numOfActiveVmsDecVarDict[str(vmType)]
                numOfTurnedOnVms = numOfTurnedOnVmsDecVarDict[str(vmType)]
                numOfTurnedOffVms = numOfTurnedOffVmsDecVarDict[str(vmType)]
                
                if timeStage > 0 :
                    previousTimeStageProviderNumOfActiveVmsDecVarDict = numOfActiveVmsDecVarList[timeStage - 1]
                    previousTimeStageUserNumOfActiveVmsDecVarDict = previousTimeStageProviderNumOfActiveVmsDecVarDict[str(provider)]
                    previousTimeStageNumOfActiveVmsDecVarDict = previousTimeStageUserNumOfActiveVmsDecVarDict[str(userIndex)]
                    previousTimeStageNumOfActiveVms = previousTimeStageNumOfActiveVmsDecVarDict[str(vmType)]
                    
                    model.addConstr(numOfActiveVms, GRB.EQUAL, previousTimeStageNumOfActiveVms + numOfTurnedOnVms - numOfTurnedOffVms)

print('Constraint 24 complete')

# constraint 25, 26
# constraint 25 : the amount of produced green energy do not exceed the usage of energy
for timeStage in range(0, timeLength) :
    # constraint 25, 26
    providerGreenEnergyDecVarDict = greenEnergyUsageDecVarList[timeStage]
    
    # constraint 26
    providerSolarEnergyToDcDecVarDict = solarEnergyToDcDecVarList[timeStage]
    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
    
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        greenEnergyUsage = providerGreenEnergyDecVarDict[str(provider)]
        solarEnergyToDc = providerSolarEnergyToDcDecVarDict[str(provider)]
        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
        
        energyConsumptionDecVarList = []
        energyConsumptionParameterList = []
        
        for userIndex in range(0, numOfUsers) :
            for vmTypeIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmTypeIndex]
                
                providerActiveVmEnergyConsumptionDecVarDict = activeVmEnergyConsumptionDecVarList[timeStage]
                providerTurnedOnVmDecVarDict = turnedOnVmVarList[timeStage]
                providerTurnedOffVmDecVarDict = turnedOffVmVarList[timeStage]
                
                userActiveVmEnergyConsumptionDecVarDict = providerActiveVmEnergyConsumptionDecVarDict[str(provider)]
                userTurnedOnVmDecVarDict = providerTurnedOnVmDecVarDict[str(provider)]
                userTurnedOffVmDecVarDict = providerTurnedOffVmDecVarDict[str(provider)]
                
                vmTypeActiveVmEnergyConsumptionDecVarDict = userActiveVmEnergyConsumptionDecVarDict[str(userIndex)]
                vmTypeTurnedOnVmDecVarDict = userTurnedOnVmDecVarDict[str(userIndex)]
                vmTypeTurnedOffVmDecVarDict = userTurnedOffVmDecVarDict[str(userIndex)]
                
                activeVmEnergyConsumptionDecVar = vmTypeActiveVmEnergyConsumptionDecVarDict[str(vmType)]
                turnedOnVmDecVar = vmTypeTurnedOnVmDecVarDict[str(vmType)]
                turnedOffVmDecVar = vmTypeTurnedOffVmDecVarDict[str(vmType)]
                
                changeStateEnergyConsumption = vmChangeStateEnergyDict[str(vmType)]
                
                energyConsumptionDecVarList.extend([activeVmEnergyConsumptionDecVar, turnedOnVmDecVar, turnedOffVmDecVar])
                energyConsumptionParameterList.extend([1, changeStateEnergyConsumption, changeStateEnergyConsumption])
        
        # constraint 25
        model.addConstr(greenEnergyUsage, GRB.LESS_EQUAL, valueOfPUE * quicksum([energyConsumptionDecVarList[index] * energyConsumptionParameterList[index] for index in range(0, len(energyConsumptionDecVarList))]))
        # constraint 26
        model.addConstr(greenEnergyUsage, GRB.EQUAL, solarEnergyToDc + chargingDischargingEffeciency * batteryEnergyToDc)

print('Constraint 25, 26 complete')

# constraint 26 : the amount of green energy is the sum of solar panel energy and the battery energy
'''
for timeStage in range(0, timeLength) :
    providerGreenEnergyDecVarDict = greenEnergyUsageDecVarList[timeStage]
    providerSolarEnergyToDcDecVarDict = solarEnergyToDcDecVarList[timeStage]
    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
    
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        greenEnergyUsage = providerGreenEnergyDecVarDict[str(provider)]
        solarEnergyToDc = providerSolarEnergyToDcDecVarDict[str(provider)]
        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
        
        model.addConstr(greenEnergyUsage, GRB.EQUAL, solarEnergyToDc + chargingDischargingEffeciency * batteryEnergyToDc)
'''
        
# constraint 27 : the sum of energy used to charge the battery and energy directly supply to DC do not exceed the amount of green energy production
# this is the limit of renewable energy production
greenEnergyDecVarLimitList = []
for timeStage in range(0, timeLength) :
    providerSolarEnergyToDcDecVarDict = solarEnergyToDcDecVarList[timeStage]
    providerSolarEnergyToBatteryDecVarDict = solarEnergyToBatteryDecVarList[timeStage]
    providerGreenEnergyLimitDict = greenEnergyDecVarLimitList[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        solarEnergyToDc = providerSolarEnergyToDcDecVarDict[str(provider)]
        solarEnergyToBattery = providerSolarEnergyToBatteryDecVarDict[str(provider)]
        greenEnergyLimit = providerGreenEnergyLimitDict[str(provider)]
        
        model.addConstr(solarEnergyToBattery + solarEnergyToDc, GRB.LESS_EQUAL, greenEnergyLimit)

print('Constraint 27 complete')

# constraint 28 : the usage of green energy do not exceed the amount of produced renewable energy
for providerIndex in range(0, len(providerList)) :
    provider = providerList[providerIndex]
    greenEnergyUsageList = []
    greenEnergyLimitList = []
    for timeStage in range(0, timeLength) :
        providerGreenEnergyUsageDecVarDict = greenEnergyUsageDecVarList[timeStage]
        providerGreenEnergyLimitDict = greenEnergyDecVarLimitList[timeStage]
        
        greenEnergyUsage = providerGreenEnergyUsage[str(provider)]
        greenEnergyLimit = providerGreenEnergyLimitDict[str(provider)]
        
        greenEnergyUsageList.append(greenEnergyUsage)
        greenEnergyLimitList.append(greenEnergyLimit)
    
    model.addConstr(quicksum(greenEnergyUsageList), GRB.LESS_EQUAL, quicksum(greenEnergyLimitList))

print('Constraint 28 complete')

# constraint 29 : the energy level at the beginning of next time period is the energy level at the end of this time period plus the energy charged to the battery
for timeStage in range(1, timeLength) :
    providerBatteryEnergyLevelDecVarDict_beg = batteryEnergyLevelDecVarList_beg[timeStage]
    providerPreviousTimeBatteryEnergyLevelDecVarDict_end = batteryEnergyLevelDecVarList_end[timeStage - 1]
    providerPreviousTimeSolarEnergyToBatteryDecVarDict = solarEnergyToBatteryDecVarList[timeStage - 1]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        
        batteryEnergyLevel_beg = providerBatteryEnergyLevelDecVarDict_beg[str(provider)]
        previousTimeBatteryEnergyLevel_end = providerPreviousTimeBatteryEnergyLevelDecVarDict_end[str(provider)]
        previousTimeSolarEnergyToBattery = providerPreviousTimeSolarEnergyToBatteryDecVarDict[str(provider)]
        
        model.addConstr(batteryEnergyLevel_beg, GRB.EQUAL, previousTimeBatteryEnergyLevel_end + chargingDischargingEffeciency * previousTimeSolarEnergyToBattery)

print('Constraint 29 complete')

# constraint 30 : the energy supplied from battery to DC is the gap between the energy level at the beginning and the end
for timeStage in range(0, timeLength) :
    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
    providerBatteryEnergyLevelDecVarDict_beg = batteryEnergyLevelDecVarList_beg[timeStage]
    providerBatteryEnergyLevelDecVarDict_end = batteryEnergyLevelDecVarList_end[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        
        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
        batteryEnergyLevel_beg = providerBatteryEnergyLevelDecVarDict_beg[str(provider)]
        batteryEnergyLevel_end = providerBatteryEnergyLevelDecVarDict_end[str(provider)]
        
        model.addConstr(batteryEnergyToDc, GRB.EQUAL, batteryEnergyLevel_beg - batteryEnergyLevel_end)

print('Constraint 30 complete')

# constraint 31 : the energy that the battery can supply do not exceed the energy level of this battery at the beginning
for timeStage in range(0, timeLength) :
    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
    providerBatteryEnergyLevelDecVarDict_beg = batteryEnergyLevelDecVarList_beg[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        
        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
        batteryEnergyLevel_beg = providerBatteryEnergyLevelDecVarDict_beg[str(provider)]
        
        model.addConstr(batteryEnergyToDc, GRB.LESS_EQUAL, batteryEnergyLevel_beg)

print('Constraint 31 complete')

# constraint 32, 33 : bettery energy level limit
batteryEnergyCapacity = 1486
for timeStage in range(0, timeLength) :
    providerBatteryEnergyLevelDecVarDict_beg = batteryEnergyLevelDecVarList_beg[timeStage]
    providerBatteryEnergyLevelDecVarDict_end = batteryEnergyLevelDecVarList_end[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        
        batteryEnergyLevel_beg = providerBatteryEnergyLevelDecVarDict_beg[str(provider)]
        batteryEnergyLevel_end = providerBatteryEnergyLevelDecVarDict_end[str(provider)]
        
        model.addConstr(batteryEnergyLevel_beg, GRB.LESS_EQUAL, batteryEnergyCapacity)
        model.addConstr(batteryEnergyLevel_end, GRB.LESS_EQUAL, batteryEnergyCapacity)

print('Constraint 32, 33 complete')

# constraint 34, 35 : the limit of battery charging and discharging
# assume that the c rate of the battery is 73 Ah permodule and there are 5 modules in a battery
chargingDischargingLimit = 73 * 5
for timeStage in range(0, timeLength) :
    providerSolarEnergyToBatteryDecVarDict = solarEnergyToBatteryDecVarList[timeStage]
    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        
        solarEnergyToBattery = providerSolarEnergyToBatteryDecVarDict[str(provider)]
        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
        
        # constraint 34
        model.addConstr(solarEnergyToBattery, GRB.LESS_EQUAL, chargingDischargingLimit)
        # constraint 35
        model.addConstr(batteryEnergyToDc, GRB.LESS_EQUAL, chargingDischargingLimit)

print('Constraint 34, 35 complete')

# constraint 36, 37, 38 : initialize the battery energy level and theenergy that can supplied by the battery
for providerIndex in range(0, len(providerList)) :
    provider = providerList[providerIndex]
    
    batteryEnergyToDc = batteryEnergyToDcDecVarList[0][str(provider)]
    batteryEnergyLevel_beg = batteryEnergyLevelDecVarList_beg[0][str(provider)]
    batteryEnergyLevel_end = batteryEnergyLevelDecVarList_end[0][str(provider)]
    
    # constraint 36
    model.addConstr(batteryEnergyToDc, GRB.EQUAL, 0)
    # constraint 37
    model.addConstr(batteryEnergyLevel_beg, GRB.EQUAL, 0)
    # constraint 38
    model.addConstr(batteryEnergyLevel_end, GRB.EQUAL, 0)

print('Constraint 36, 37, 38 complete')

# constraint 39 : the flow entering a router is equal to the flow leaving a router
for timeStage in range(0, timeLength) :
    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
    for router in routerData :
        routerIndex = router.routerIndex
        routerDirectlyConnectedEdges = router.edges
        
        flowInDecVarList = []
        flowOutDecVarList = []
        
        for edgeIndex in routerDirectlyConnectedEdges :
            flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
            for flowTypeIndex in range(2) :
                flowTypeList = ['in', 'out']
                flowType = flowTypeList[flowTypeIndex]
                userFlowDecVarDict = flowTypeDecVarDict[str(flowType)]
                for userIndex in range(0, numOfUsers) :
                    flowDecVar = userFlowDecVarDict[str(userIndex)]
                    
                    if flowType == 'in' :
                        flowInDecVarList.append(flowDecVar)
                    else :
                        flowOutDecVarList.append(flowDecVar)
        
        model.addConstr(quicksum(flowInDecVarList), GRB.EQUAL, quicksum(flowOutDecVarList))

print('Constraint 39 complete')

# constraint 40 : the sum of flow leaving a router is the sum of utilization and on-demand bandwidth
for timeStage in range(0, timeLength) :
    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
    for router in routerData :
        routerIndex = router.routerIndex
        routerDirectlyConnectedEdges = router.edges
        
        for userIndex in range(0, numOfUsers) :
            outFlowDecVarList = []
            
            for edgeIndex in routerDirectlyConnectedEdges :
                edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
                flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
                flowDecVar = flowTypeDecVarDict['out'][str(userIndex)]
                outFlowDecVarList.append(flowDecVar)
            
            utilizationAndOnDemandBandDecVarList = []
            for bandContractLength in [5, 10] :
                for bandPayment in ['No upfront', 'Partial upfront', 'All upfront'] :
                    userBandUtilizationDecVarDict = bandUtilizationDecVar[timeStage]
                    routerBandUtilizationDecVarDict = userBandUtilizationDecVarDict[str(userIndex)]
                    contractBandUtilizationDecVarDict = routerBandUtilizationDecVarDict[str(routerIndex)]
                    paymentBandUtilizationDecVarDict = contractBandUtilizationDecVarDict[str(bandContractLength)]
                    bandUtilization = paymentBandUtilizationDecVarDict[str(bandPayment)]
                    
                    utilizationAndOnDemandBandDecVarList.append(bandUtilization)
                
            userBandOnDemandDecVarDict = bandOnDemandDecVar[timeStage]
            routerBandOnDemandDecVarDict = userBandOnDemandDecVarDict[str(userIndex)]
            onDemandBand = routerBandOnDemandDecVarDict[str(routerIndex)]
            utilizationAndOnDemandBandDecVarList.append(onDemandBand)
            
            model.addConstr(quicksum(outFlowDecVarList), GRB.LESS_EQUAL, quicksum(utilizationAndOnDemandBandDecVarList))

print('Constraint 40 complete')

# constraint 41 : the bandwidth requirement of VMs in a provider should be satisfied
outboundBandReqDict = getOutboundBandwidthRequirement(instanceData)
for timeStage in range(0, timeLength) :
    providerVmDecVarDict_uti = vmUtilizationDecVar[timeStage]
    providerVmDecVarDict_onDemand = vmOnDemandDecVar[timeStage]
    for providerIndex in range(0, len(providerList)) :
        provider = providerList[providerIndex]
        cloudProviderObj = cloudProvidersDict[str(provider)]
        providerDirectlyConnectedEdges = cloudProviderObj.directlyConnectedEdges
        
        userVmDecVarDict_uti = providerVmDecVarDict_uti[str(provider)]
        userVmDecVarDict_onDemand = providerVmDecVarDict_onDemand[str(provider)]
        for userIndex in range(0, numOfUsers) :
            vmTypeVmDecVarDict_uti = userVmDecVarDict_uti[str(userIndex)]
            vmTypeVmDecVarDict_onDemand = userVmDecVarDict_onDemand[str(userIndex)]
            
            vmTypeUtilizationAndOnDemandDict = dict()
            
            
            for vmTypeIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmTypeIndex]
                contractVmDecVarDict_uti = vmTypeVmDecVarDict_uti[str(vmType)]
                onDemandVm = vmTypeVmDecVarDict_onDemand[str(vmType)]
                
                utilizationAndOnDemandDecVarList = []
                
                for contractIndex in range(0, len(vmContractLengthList)) :
                    contractLength = vmContractLengthList[contractIndex]
                    paymentVmDecVarDict = contractVmDecVarDict_uti[str(contractLength)]
                    for payment in ['NoUpfront', 'PartialUpfront', 'AllUpfront'] :
                        utilizationVm = paymentVmDecVarDict[str(payment)]
                        utilizationAndOnDemandDecVarList.append(utilizationVm)
                utilizationAndOnDemandDecVarList.append(onDemandVm)
                
                vmTypeUtilizationAndOnDemandDict[str(vmType)] = utilizationAndOnDemandDecVarList
            
            userEdgeFlowDecVarList = []
            for edgeIndex in providerDirectlyConnectedEdges :
                edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
                flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
                userFlowDecVarDict = flowTypeDecVarDict['out']
                flowDecVar = userFlowDecVarDict[str(userIndex)]
                
                userEdgeFlowDecVarList.append(flowDecVar)
            
            model.addConstr(quicksum(userEdgeFlowDecVarList), GRB.GREATER_EQUAL, quicksum([vmTypeUtilizationAndOnDemandDict[str(vmType)] * outboundBandReqDict[str(vmType)] for vmType in vmTypeList]))

print('Constraint 41 complete')

# constraint 42 : the bandwidth required by the flow entering a user should be satistied
userEdgeList = networkTopology['user']
for timeStage in range(0, timeLength) :
    for userIndex in range(0, numOfUsers) :
        userDirectlyConnectedEdges = userEdgeList[userIndex]
        
        userFlowInEdgeDecVarList = []
        
        for edgeIndex in userDirectlyConnectedEdges :
            edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
            flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
            userFlowDecVarDict = flowTypeDecVarDict['in']
            flowDecVar = userFlowDecVarDict[str(userIndex)]
            userFlowInEdgeDecVarList.append(flowDecVar)
        
        flowOutDecVarListOfProviders = []
        
        for providerIndex in range(0, len(providerList)) :
            provider = providerList[providerIndex]
            cloudProviderObj = cloudProvidersDict[str(provider)]
            providerDirectlyConnectedEdges = cloudProviderObj.directlyConnectedEdges
            
            for edgeIndex in providerDirectlyConnectedEdges :
                edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
                flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
                userFlowDecVarDict = flowTypeDecVarDict['out']
                flowDecVar = userFlowDecVarDict[str(userIndex)]
                
                flowOutDecVarListOfProviders.append(flowDecVar)
        
        model.addConstr(quicksum(userFlowInEdgeDecVarList), GRB.GREATER_EQUAL, quicksum(flowOutDecVarListOfProviders))

print('Constraint 42 complete')

# constraint 43 : the decision variables of flow should greater than 0
for timeStage in range(0, timeLength) :
    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
    for edgeIndex in range(0, len(edgeList)) :
        flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
        for flowType in ['in', 'out'] :
            userFlowDecVarDict = flowTypeDecVarDict[str(flowType)]
            for userIndex in range(0, numOfUsers) :
                flow = [str(userIndex)]
                
                model.addConstr(flow, GRB.GREATER_EQUAL, 0)

print('Constraint 43 complete')

model.write("thesis.lp")


# model.optimize()
print("Objective function value : ", model.objVal)
