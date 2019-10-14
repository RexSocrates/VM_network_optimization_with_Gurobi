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
turnedOnVmVarList = []
turnedOffVmVarList = []
greenEnergyUsageDecVarList = []


for timeStage in range(0, timeLength) :
    providerActiveVmEnergyConsumptionDecVarDict = dict()
    providerTurnedOnVmDecVarDict = dict()
    providerTurnedOffVmDecVarDict = dict()
    providerGreenEnergyDecVarDict = dict()
    for area in areaDict :
        providerListOfArea = areaDict[area]
        for provider in providerListOfArea :
            userActiveVmEnergyConsumptionDecVarDict = dict()
            userTurnedOnVmDecVarDict = dict()
            userTurnedOffVmDecVarDict = dict()
            for userIndex in range(0, numOfUsers) :
                activeVmEnergyConsumptionDecVarDict = dict()
                turnedOnVmDecVarDict = dict()
                turnedOffVmDecVarDict = dict()
                for vmTypeIndex in range(0, len(vmTypeList)) :
                    vmType = vmTypeList[vmTypeIndex]
                    
                    vmDictOfProvider = sortedVmList[str(provider)]
                    contractDictOfVmType = vmDictOfProvider[str(vmType)]
                    paymentDictOfContract = contractDictOfVmType[str(1)]
                    vmData = paymentDictOfContract['NoUpfront']
                    
                    vmEnergyConsumption = vmData.energyConsumption
                    changeStateEnergyConsumption = vmEnergyConsumption * 0.05
                    
                    energyConsumptionOfActiveVm = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
                    numOfTurnedOnVm = model.addVar(lb=0.0, vtype=GRB.INTEGER)
                    numOfTurnedOffVm = model.addVar(lb=0.0, vtype=GRB.INTEGER)
                    
                    # store the decision variables in the dictionaries
                    activeVmEnergyConsumptionDecVarDict[str(vmType)] = energyConsumptionOfActiveVm
                    turnedOnVmDecVarDict[str(vmType)] = numOfTurnedOnVm
                    turnedOffVmDecVarDict[str(vmType)] = numOfTurnedOffVm
                    
                userActiveVmEnergyConsumptionDecVarDict[str(userIndex)] = activeVmEnergyConsumptionDecVarDict
                userTurnedOnVmDecVarDict[str(userIndex)] = turnedOnVmDecVarDict
                userTurnedOffVmDecVarDict[str(userIndex)] = turnedOffVmDecVarDict
            
            providerGreenEnergyUsage = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            
            providerActiveVmEnergyConsumptionDecVarDict[str(provider)] = userActiveVmEnergyConsumptionDecVarDict
            providerTurnedOnVmDecVarDict[str(provider)] = userTurnedOnVmDecVarDict
            providerTurnedOffVmDecVarDict[str(provider)] = userTurnedOffVmDecVarDict
            providerGreenEnergyDecVarDict[str(provider)] = providerGreenEnergyUsage
    
    activeVmDecVarList.append(providerActiveVmEnergyConsumptionDecVarDict)
    turnedOnVmVarList.append(providerTurnedOnVmDecVarDict)
    turnedOffVmVarList.append(providerTurnedOffVmDecVarDict)
    greenEnergyUsageDecVarList.append(providerGreenEnergyDecVarDict)
                    
                    

# Network energy decision variables



# objective function
model.setObjective(quicksum([vmCostDecVarList[i] * vmCostParameterList[i] for i in range(0, len(vmCostDecVarList))]) + quicksum(bandwidthCostDecVarList[i] * bandwidthCostParameterList[i] for i in range(0, len(bandwidthCostDecVarList))) + quicksum([sortedEnergyPrice[timeStage][area] * quicksum([valueOfPUE * quicksum([activeVmDecVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] + turnedOnVmVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] + turnedOffVmVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] for userIndex in range(0, numOfUsers) for vmTypeIndex in range(0, len(vmTypeList))]) - greenEnergyUsageDecVarList[timeStage][str(provider)] for provider in areaDict[area]]) for timeStage in range(0, timeLength) for area in areaDict]), GRB.MINIMIZE)

# VM energy objective function
# quicksum([sortedEnergyPrice[timeStage][area] * quicksum([valueOfPUE * quicksum([activeVmDecVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] + turnedOnVmVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] + turnedOffVmVarList[timeStage][str(provider)][str(userIndex)][str(vmTypeList[vmTypeIndex])] for userIndex in range(0, numOfUsers) for vmTypeIndex in range(0, len(vmTypeList))]) - greenEnergyUsageDecVarList[timeStage][str(provider)] for provider in areaDict[area]]) for timeStage in range(0, timeLength) for area in areaDict])

# add constraints