from VMClass import *
from EnergyPriceClass import *
from CloudProviderClass import *
import pandas as pd
import numpy as np
import csv

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
        contract = int(row[3]) * 24 * 365
        paymentOption = row[4]
        reservationFee = float(row[5])
        utilizationFee = float(row[6])
        onDemandFee = float(row[7])
        hostReq = float(row[8])
        memoryReq = float(row[9])
        storageReq = float(row[10])
        networkReq = float(row[11])
        energyConsumption = float(row[12])
        
        newInstance = VMClass(area, provider, instanceType, contract, paymentOption, reservationFee, utilizationFee, onDemandFee, hostReq, memoryReq, storageReq, networkReq, energyConsumption)
        instanceData.append(newInstance)
    
    return instanceData

# read router bandwidth pricing data
def getRouterBandwidthPrice(networkTopology) :
    with open('goldenSample_router_bandwidth_pricing.csv', 'r', newline='', encoding='utf-8') as csvfile :
        routerEdgesList = networkTopology['router']
        
        rows = csv.reader(csvfile)
        
        rowData = []
        for row in rows :
            rowData.append(row)
        
        routerData = []
        
        for row in row[1:] :
            routerIndex = int(row[0])
            routerArea = row[1]
            contractLength = int(row[2])
            paymentOption = row[3]
            initialResFee = float(row[4])
            utilizationFee = float(row[5])
            onDemandFee = float(row[6])
            
            edges = routerEdgesList[routerIndex]
            
            if routerIndex >= len(routerEdgesList) :
                break
            else :
                newRouterData = RouterClass(routerIndex, routerArea, contractLength, paymentOption, initialResFee, utilizationFee, onDemandFee, edges)
                routerData.append(newRouterData)
        
        return routerData


# read energy pricing data
def readEnergyPricingFile() :
    areaList = ['us', 'ap', 'eu']
    dataframe = pd.read_csv('goldenSample_energyPrice.csv')
    
    energyPriceDict = dict()
    for areaIndex in range(0, len(areaList)) :
        area = areaList[areaIndex]
        areaPrice = dataframe[area]
        
        areaPriceList = []
        for item in areaPrice :
            areaPriceList.append(float(item))
        
        newAreaEnergyPricingData = EnergyPrice(area, areaPriceList)
        
        energyPriceDict[area] = newAreaEnergyPricingData
    
    return energyPriceDict        


# read the file of cloud provider capacity
def getProviderCapacity(providerNetworkEdges) :
    with open('goldenSample_provider_capacity.csv', 'r', newline='', encoding='utf-8') as csvfile :
        rows = csv.reader(csvfile)

        rowData = []
        for row in rows :
            rowData.append(row)
        
        column = rowData[0]
        cloudProvidersDict = dict()
        for data in rowData[1:] :
            provider = row[0]
            coresLimit = float(row[1])
            memoryLimit = float(row[2])
            storageLimit = float(row[3])
            internalBandwidthLimit = float(row[4])
            
            directlyConnectedEdges = providerNetworkEdges[str(provider)]
            
            newProvider = CloudProvider(provider, coresLimit, memoryLimit, storageLimit, internalBandwidthLimit, directlyConnectedEdges)
            cloudProvidersDict[str(provider)] = newProvider
        
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
        networkDict['edges'] = [rowData[0][1:]]
        
        for row in rowData[1:] :
            node = row[0]
            edges = row[1:]
            
            directlyConnectedEdges = [edgeIndex for edgeIndex in range(0, len(edges)) if edges[edgeIndex] == '1']
            
            if node[0] == 'u' :
                networkDict['user'].append(directlyConnectedEdges)
            elif node[0] == 'p' :
                nodeSplitList = node.split('-')
                providerName = nodeSplitList[1]
                networkDict['provider'][str(providerName)] = directlyConnectedEdges
            else :
                networkDict['router'].append(directlyConnectedEdges)
        
        return networkDict

# define a function to return the cost of VM storage and bandwidth
def getCostOfStorageBandBandwidth() :
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