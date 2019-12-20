from VMClass import *
from EnergyPriceClass import *
from CloudProviderClass import *
from RouterClass import *
import pandas as pd
import numpy as np
import csv
import random

# read VM pricing and configuration data
def readSampleFile(fileName) :
    rawData = []
    with open(fileName, encoding='utf-8', newline='') as csvfile :
        rows = csv.reader(csvfile)
        
        for row in rows :
            rawData.append(row)
                
    return rawData
    
# read the VM data file and return the list of VM data
def getVirtualResource() :
    rawData = readSampleFile('goldenSample_VM.csv')
    
    rows = rawData[1:]
    
    instanceData = []
    
    for row in rows :
        area = row[0]
        provider = row[1]
        instanceType = row[2]
        contract = int(float(row[3]))
        paymentOption = row[4]
        reservationFee = float(row[5])
        utilizationFee = float(row[6])
        onDemandFee = float(row[7])
        hostReq = float(row[8])
        memoryReq = float(row[9])
        storageReq = float(row[10])
        networkReq = float(row[11])
        energyConsumption = float(row[12])
        '''
        if area == 'us' :
            reservationFee *= testValue
            utilizationFee *= testValue
            onDemandFee *= testValue
        '''
        
        newInstance = VMClass(area, provider, instanceType, contract, paymentOption, reservationFee, utilizationFee, onDemandFee, hostReq, memoryReq, storageReq, networkReq, energyConsumption)
        instanceData.append(newInstance)
    
    return instanceData

# read router bandwidth pricing data
def getRouterBandwidthPrice(networkTopology) :
    random.seed(10)    
    rowData = []
    with open('goldenSample_router_bandwidth_pricing.csv', 'r', newline='', encoding='utf-8') as csvfile :
        rows = csv.reader(csvfile)
        
        for row in rows :
            rowData.append(row)
        
    routerAreaDict = dict()
    
    for row in rowData[1:] :
        routerIndex = int(row[0])
        routerArea = row[1]
        contractLength = int(row[2])
        paymentOption = row[3]
        initialResFee = float(row[4])
        utilizationFee = float(row[5])
        onDemandFee = float(row[6])
        
        if routerArea not in routerAreaDict :
            routerIndexDict = dict()
            routerIndexDict[routerIndex] = [row]
            routerAreaDict[routerArea] = routerIndexDict
        else :
            routerIndexDict = routerAreaDict[routerArea]
            if routerIndex not in routerIndexDict :
                routerList = [row]
                routerIndexDict[routerIndex] = routerList
            else :
                routerList = routerIndexDict[routerIndex]
                routerList.append(row)
    
    routerList = networkTopology['router']
    routerData = []
    # record the router index that has been picked up in the router data list
    selectedRouterIndexList = []
    # print(routerAreaDict['ap'])
    
    for routerIndex in range(0, len(routerList)) :
        router = routerList[routerIndex]
        routerArea = router[0]
        routerEdges = router[1:]
        
        areaRouterDict = routerAreaDict[routerArea]
        newAreaRouterDictKey = list(areaRouterDict.keys())[random.randint(0, len(areaRouterDict))]
        
        while newAreaRouterDictKey in selectedRouterIndexList :
            newAreaRouterDictKey = list(areaRouterDict.keys())[random.randint(0, len(areaRouterDict))]
        
        selectedRouterIndexList.append(newAreaRouterDictKey)
        routerPricingDataList = areaRouterDict[newAreaRouterDictKey]
        
        for router in routerPricingDataList :
            routerArea = router[1]
            contractLength = int(router[2])
            paymentOption = router[3]     
            initialResFee = float(router[4])
            utilizationFee = float(router[5])
            onDemandFee = float(router[6])
            '''
            if routerArea == 'us' :
                initialResFee *= testValue
                utilizationFee *= testValue
                onDemandFee *= testValue
            '''
            
            newRouterData = RouterClass(routerIndex, routerArea, contractLength, paymentOption, initialResFee, utilizationFee, onDemandFee, routerEdges)
            routerData.append(newRouterData)
    return routerData

# read energy pricing data
def readEnergyPricingFile(testValue) :
    areaList = ['us', 'ap', 'eu']
    dataframe = pd.read_csv('goldenSample_energyPrice.csv')
    
    energyPriceDict = dict()
    for areaIndex in range(0, len(areaList)) :
        area = areaList[areaIndex]
        areaPrice = dataframe[area]
        
        if area == 'us' :
            areaPrice *= testValue
        
        
        areaPriceList = []
        for item in areaPrice :
            # transfer the price of each megawatt-hour to the price of each kilowatt-hour
            areaPriceList.append(float(item) / 1000)
        
        newAreaEnergyPricingData = EnergyPrice(area, areaPriceList)
        
        energyPriceDict[area] = newAreaEnergyPricingData
    
    return energyPriceDict        


# read the file of cloud provider capacity
def getProviderCapacity(providerNetworkEdges) :
    cloudProvidersLimitDict = dict()
    with open('goldenSample_provider_capacity.csv', 'r', newline='', encoding='utf-8') as csvfile :
        rows = csv.reader(csvfile)

        rowData = []
        for row in rows :
            rowData.append(row)
        
        column = rowData[0]
        for data in rowData[1:] :
            providerCapacityDict = dict()
            provider = data[0]
            coresLimit = float(data[1])
            memoryLimit = float(data[2])
            storageLimit = float(data[3])
            internalBandwidthLimit = float(data[4])
            
            providerCapacityDict['core'] = coresLimit
            providerCapacityDict['memory'] = memoryLimit
            providerCapacityDict['storage'] = storageLimit
            providerCapacityDict['band'] = internalBandwidthLimit
            
            cloudProvidersLimitDict[provider] = providerCapacityDict
    
    cloudProvidersDict = dict()
    for key in providerNetworkEdges :
        providerName = key
        providerLimitDict = cloudProvidersLimitDict[providerName]
        coresLimit = providerLimitDict['core']
        memoryLimit = providerLimitDict['memory']
        storageLimit = providerLimitDict['storage']
        bandLimit = providerLimitDict['band']
        directlyConnectedEdges = providerNetworkEdges[key]
        
        newProvider = CloudProvider(provider, coresLimit, memoryLimit, storageLimit, bandLimit, directlyConnectedEdges)
        cloudProvidersDict[key] = newProvider
    return cloudProvidersDict

# read the network topology
def getNetworkTopology() :
    with open('goldenSample_network.csv', 'r', newline='', encoding='utf-8') as csvfile :
        rows = csv.reader(csvfile)
        
        rowData = []
        for row in rows :
            rowData.append(row)
        
        networkDict = dict()
        networkDict['user'] = []
        networkDict['provider'] = dict()
        networkDict['router'] = []
        networkDict['edges'] = rowData[0][1:]
        
        for row in rowData[1:] :
            node = row[0]
            edges = row[1:]
            
            directlyConnectedInFlowEdges = [edgeIndex for edgeIndex in range(0, len(edges)) if edges[edgeIndex] == '1']
            directlyConnectedOutFlowEdges = [edgeIndex for edgeIndex in range(0, len(edges)) if edges[edgeIndex] == '2']
            
            directlyConnectedEdges = [edgeIndex for edgeIndex in range(0, len(edges)) if edges[edgeIndex] is not '0']
            
            if node[0] == 'u' :
                networkDict['user'].append(directlyConnectedEdges)
            elif node[0] == 'p' :
                nodeSplitList = node.split('-', 1)
                providerName = nodeSplitList[1]
                networkDict['provider'][str(providerName)] = directlyConnectedEdges
            elif node[0] == 'r' :
                routerNameList = node.split('-')
                routerArea = routerNameList[1]
                networkDict['router'].append([routerArea, directlyConnectedInFlowEdges, directlyConnectedOutFlowEdges])
            else :
                print('Network topology error')
        
        return networkDict

# define a function to return the cost of VM storage and bandwidth
def getCostOfStorageAndBandwidth() :
    outputData = dict()
    with open('goldenSample_VmStoragePrice.csv', newline='', encoding='utf-8') as csvfile :
        rows = csv.reader(csvfile)
        
        rowData = []
        for row in rows :
            rowData.append(row)
        
        for data in rowData[1:] :
            newData = dict()
            region = data[0]
            newData['storage'] = float(data[1])
            newData['bandwidth'] = float(data[2])
            outputData[region] = newData
    return outputData

def getGreenEnergyUsageLimit(timeLength, providerList) :
    greenEnergyUsageLimitList = []
    for timeStage in range(0, timeLength) :
        providerGreenEnergyLimitDict = dict()
        for providerIndex in range(0, len(providerList)) :
            provider = providerList[providerIndex]
            greenEnergyLimit = 20
            providerGreenEnergyLimitDict[str(provider)] = greenEnergyLimit
        greenEnergyUsageLimitList.append(providerGreenEnergyLimitDict)
    return greenEnergyUsageLimitList
            