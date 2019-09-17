# Build gurobi model
from readData import *
from gurobipy import *
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
def getProvidersList(instanceData) :
    providerList = []
    for item in instanceData :
        provider = item.provider
        if provider not in providerList :
            providerList.append(provider)
    return providerList

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
            

instanceData = readVirtualResourceFile()
vmList = getVmTypesList(instanceData)
providerList = getProvidersList(instanceData)


model = Model('VM_network_and_energy_optimization_model')

timeLength = 500
numOfUsers = 10

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
            for vmIndex in range(0, len(vmList)) :
                vmType = vmList[vmIndex]
                contractDecVar_res = dict()
                contractDecVar_uti = dict()
                for contractIndex in range(2) :
                    contractLengthList = [1, 3]
                    contractLength = contractLengthList[contractIndex]
                    paymentOptionDecVar_res = dict()
                    paymentOptionDecVar_uti = dict()
                    for paymentOptionIndex in range(3) :
                        paymentOptionsList = ['No', 'Partial', 'All']
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
                        
                    contractDecVar_res[str(contractLength)] = paymentOptionDecVar_res
                    contractDecVar_uti[str(contractLength)] = paymentOptionDecVar_uti
                
                onDemandVar = model.addVar(lb=0.0, vtype=GRB.INFINITY)
                
                vmDecVar_res[vmType] = contractDecVar_res
                vmDecVar_uti[vmType] = contractDecVar_uti
                vmDecVar_onDemand[vmType] = onDemandVar
            providerDecVar_res[provider] = vmDecVar_res
            providerDecVar_uti[provider] = vmDecVar_uti
            providerDecVar_onDemand[provider] = vmDecVar_onDemand
        userDecVar_res.append(providerDecVar_res)
        userDecVar_uti.append(providerDecVar_uti)
        userDecVar_onDemand.append(providerDecVar_onDemand)
    vmResDecVar.append(userDecVar_res)
    vmUtilizationDecVar.append(userDecVar_uti)
    vmOnDemandDecVar.append(userDecVar_onDemand)
    


# Bandwidth decision variables

# VM energy decision variables

# Network energy decision variables



# objective function

# add constraints