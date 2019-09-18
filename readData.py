from VMClass import *
from EnergyPriceClass import *
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
    
    
def readVirtualResourceFile() :
    rawData = readSampleFile('smallSample.csv')
    
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
    
        