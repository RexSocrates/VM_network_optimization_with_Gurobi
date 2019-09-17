from VMClass import *
import csv

def readSampleFile(fileName) :
    rawData = []
    with open(fileName, encoding='utf-8', newline='') as csvfile :
        rows = csv.reader(csvfile)
        
        for row in rows :
            if len(row) > 0 :
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
        
        newInstance = VMClass(area, provider, instanceType, contract, paymentOption, reservationFee, utilizationFee, onDemandFee, hostReq, memoryReq, storageReq, networkReq)
        instanceData.append(newInstance)
    
    return instanceData