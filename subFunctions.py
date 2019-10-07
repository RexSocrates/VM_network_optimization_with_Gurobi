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
def sortVM(instanceData) :
    providerList = getProvidersList(instanceData)
    vmTypeList = getVmTypesList(instanceData)
    contractList = [1, 3]
    paymentOptionList = ['NoUpfront', 'PartialUpfront', 'AllUpfront']
    
    newVmList = []
    
    for provider in providerList :
        for vmType in vmTypeList :
            for contractLength in contractList :
                for payment in paymentOptionList :
                    # find the instance data with specific configuration
                    for instance in instanceData :
                        print()