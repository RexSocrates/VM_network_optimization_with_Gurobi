# Build gurobi model
from readData import *
from subFunctions import *
from gurobipy import *
import random
            
# get instance data from csv file, get get the lists of vm types and cloud providers from instance data

instanceData = getVirtualResource()
providerList = getProvidersList(instanceData)
vmTypeList = getVmTypesList(instanceData)
storageAndBandwidthPrice = getCostOfStorageBandBandwidth()


model = Model('VM_network_and_energy_optimization_model')

timeLength = 500
numOfUsers = 10

sortedVmList = sortVM(instanceData, providerList, vmTypeList)
vmCostDecVarList = []
vmCostParameterList = []

# decision variables

# VM decision variables
vmResDecVar = []
vmUtilizationDecVar = []
vmOnDemandDecVar = []

for timeStage in range(0, timeLength) :
    userDecVar_res = []
    userDecVar_uti = []
    userDecVar_onDemand = []
    for userIndex in range(0, numOfUsers) :
        providerDecVar_res = dict()
        providerDecVar_uti = dict()
        providerDecVar_onDemand = dict()
        for providerIndex in range(0, len(providerList)) :
            provider = providerList[providerIndex]
            vmDecVar_res = dict()
            vmDecVar_uti = dict()
            vmDecVar_onDemand = dict()
            for vmIndex in range(0, len(vmTypeList)) :
                vmType = vmTypeList[vmIndex]
                contractDecVar_res = dict()
                contractDecVar_uti = dict()
                
                # on-demand vm data
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
                        instanceTupleData = paymentDictOfContract[paymentOption]
                        
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
                
            providerDecVar_res[provider] = vmDecVar_res
            providerDecVar_uti[provider] = vmDecVar_uti
            providerDecVar_onDemand[provider] = vmDecVar_onDemand
        userDecVar_res.append(providerDecVar_res)
        userDecVar_uti.append(providerDecVar_uti)
        userDecVar_onDemand.append(providerDecVar_onDemand)
    vmResDecVar.append(userDecVar_res)
    vmUtilizationDecVar.append(userDecVar_uti)
    vmOnDemandDecVar.append(userDecVar_onDemand)


# cost of VM




numOfRouters = 50

# Bandwidth decision variables
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
            
            for bandResContractIndex in range(2) :
                bandResContractLengthList = [1, 3]
                bandResContractLength = bandResContractLengthList[bandResContractIndex]
                
                bandPaymentOptionDecVar_res = dict()
                bandPaymentOptionDecVar_uti = dict()
                
                for bandPaymentOptionIndex in range(3) :
                    bandPaymentOptionList = ['No', 'Partial', 'All']
                    bandPaymentOption = bandPaymentOptionList[bandPaymentOptionIndex]
                    
                    bandReservation = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
                    bandUtilization = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
                    
                    bandPaymentOptionDecVar_res[bandPaymentOption] = bandReservation
                    bandPaymentOptionDecVar_uti[bandPaymentOption] = bandUtilization
                    
                bandContractDecVar_res[str(bandResContractLength)] = bandPaymentOptionDecVar_res
                bandContractDecVar_uti[str(bandResContractLength)] = bandPaymentOptionDecVar_uti
            
            bandOnDemand = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS)
            
            bandRouterDecVar_res.append(bandContractDecVar_res)
            bandRouterDecVar_uti.append(bandContractDecVar_uti)
            bandRouterDecVar_onDemand.append(bandOnDemand)
        
        bandUserDecVar_res.append(bandRouterDecVar_res)
        bandUserDecVar_uti.append(bandRouterDecVar_uti)
        bandUserDecVar_onDemand.append(bandRouterDecVar_onDemand)
        
    bandResDecVar.append(bandUserDecVar_res)
    bandUtilizationDecVar.append(bandUserDecVar_uti)
    bandOnDemandDecVar.append(bandUserDecVar_onDemand)

# VM energy decision variables
valueOfPUE = 1.58

for timeStage in range(0, timeLength) :
    userDecVar_uti = vmUtilizationDecVar[timeStage]
    userDecVar_onDemand = vmOnDemandDecVar[timeStage]
    for userIndex in range(0, numOfUsers) :
        providerDecVar_uti = userDecVar_uti[userIndex]
        providerDecVar_onDemand = userDecVar_onDemand[userIndex]
        for providerIndex in range(0, len(providerList)) :
            provider = providerList[providerIndex]
            vmDecVar_uti = providerDecVar_uti[provider]
            vmDecVar_onDemand = providerDecVar_onDemand[provider]
            for vmTypeIndex in range(0, len(vmList)) :
                vmType = vmList[vmTypeIndex]
                contractDecVar_uti = vmDecVar_uti[vmType]
                for contractIndex in range(2) :
                    contractLengthList = [1, 3]
                    contractLength = contractLengthList[contractIndex]
                    paymentOptionDecVar_uti = contractDecVar_uti[str(contractLength)]
                    for paymentOptionIndex in range(3) :
                        paymentOptionList = ['No', 'Partial', 'All']
                        paymentOption = paymentOptionList[paymentOptionIndex]
                        
                        utilizationVar = paymentOptionDecVar_uti[paymentOption]
                        
                    
    

# Network energy decision variables



# objective function

# add constraints