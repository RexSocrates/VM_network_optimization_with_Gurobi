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
    return timeList

# sort the VM data accroding to the providers, VM types, contracts, payment options
def sortVM(instanceData, providerList, vmTypeList) :
    contractList = [1, 3]
    paymentOptionList = ['NoUpfront', 'PartialUpfront', 'AllUpfront']
    
    # store the sorted VM data
    newVmList = dict()
    
    for provider in providerList :
        vmTypesOfProvider = dict()
        for vmType in vmTypeList :
            contractOfVmTypes = dict()
            for contractLength in contractList :
                paymentOptionOfContract = dict()
                for payment in paymentOptionList :
                    # find the instance data with specific configuration
                    for instance in instanceData :
                        instanceProvider = instance.provider
                        instanceType = instance.instanceType
                        instanceContract = instance.contractLength
                        instancePayment = instance.paymentOption
                        
                        if instanceProvider == provider and instanceType == vmType and instanceContract == contractLength and instancePayment == payment :
                            paymentOptionOfContract[str(payment)] == instance
                            break
                contractOfVmTypes[str(contractLength)] = paymentOptionOfContract
            vmTypesOfProvider[str(vmType)] = contractOfVmTypes
        newVmList[str(provider)] = vmTypesOfProvider
    return newVmList

# define a function to return the cost of VM storage and bandwidth
def getCostOfStorageBandBandwidth() :
    storageCost = []
    bandwidthCost = []





                        