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
        contract = row[3]
        paymentOption = row[4]
        reservationFee = row[5]
        utilizationFee = row[6]
        onDemandFee = row[7]
        hostReq = row[8]
        memoryReq = row[9]
        storageReq = row[10]
        networkReq = row[11]
        energyConsumption = row[12]
        
        newInstance = VMClass(area, provider, instanceType, contract, paymentOption, reservationFee, utilizationFee, onDemandFee, hostReq, memoryReq, storageReq, networkReq, energyConsumption)
        instanceData.append(newInstance)
    
    return instanceData

# read router bandwidth pricing data
def getRouterBandwidthPrice() :
    with open('goldenSample_router_bandwidth_pricing.csv', 'r', newline='', encoding='utf-8') as csvfile :
        rows = csv.reader(csvfile)
        
        rowData = []
        for row in rows :
            rowData.append(row)
        
        routerData = []
        
        for row in row[1:] :
            routerIndex = row[0]
            contractLength = row[1]
            paymentOption = row[2]
            initialResFee = row[3]
            utilizationFee = row[4]
            onDemandFee = row[5]
            
            newRouterData = RouterClass(routerIndex, contractLength, paymentOption, initialResFee, utilizationFee, onDemandFee)
            routerData.append(newRouterData)
        
        return routerData


# read energy pricing data
def readEnergyPricingFile(fileName) :
    areaList = ['us', 'ap', 'eu']
    dataframe = pd.read_csv(fileName)
    
    energyPriceDict = dict()
    for areaIndex in range(0, len(areaList)) :
        area = areaList[areaIndex]
        areaPrice = dataframe[area]
        
        areaPriceList = []
        for item in areaPrice :
            areaPriceList.append(item)
        
        newAreaEnergyPricingData = EnergyPrice(area, areaPriceList)
        
        energyPriceDict[area] = newAreaEnergyPricingData
    
    return energyPriceDict


# read the file of cloud provider capacity
def getProviderCapacity() :
    with open('goldenSample_provider_capacity.csv', 'r', newline='', encoding='utf-8') as csvfile :
        rows = csv.reader(csvfile)

        rowData = []
        for row in rows :
            rowData.append(row)
        
        column = rowData[0]
        cloudProviders = []
        for data in rowData[1:] :
            provider = row[0]
            coresLimit = row[1]
            memoryLimit = row[2]
            storageLimit = row[3]
            internalBandwidthLimit = row[4]
            
            newProvider = CloudProvider(provider, coresLimit, memoryLimit, storageLimit, internalBandwidthLimit)
            cloudProviders.append(newProvider)
        
        return cloudProviders

# read the network topology
def getNetworkTopology() :
    with open('goldenSample_network.csv', 'r', newline='', encoding='utf-8') as csvfile :
        rows = csv.reader(csvfile)
        
        rowData = []
        for row in rows :
            rowData.append(row)
        
        networkDict = dict()
        for row in rowData[1:] :
            node = row[0]
            edges = row[1:]
            
            networkDict[node] = edges
        
        return networkDict