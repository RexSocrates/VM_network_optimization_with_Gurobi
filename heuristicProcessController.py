# control the heuristic process
from readData import *
from subFunctions import *
from relaxAndFixController import *
from model import *

# configure the experiment

instanceData = getVirtualResource()
vmDataConfiguration = getVmDataConfiguration(instanceData)
storageAndBandwidthPrice = getCostOfStorageBandBandwidth()
networkTopology = getNetworkTopology()

# Decomposition-required parameters : windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters

# the number of time periods that are going to be optimized in each iteration
windowSize = 2
# the percentage of the variables that are going to be re-optimized in the next iteration
overlap = 0.5
# the number of time periods
timeLength = 100
# the number of users in the topology
numOfUsers = len(networkTopology['user'])
# the list of the cloud providers in the topology
providerList = vmDataConfiguration['providerList']
# the list of vm type
vmTypeList = vmDataConfiguration['vmTypeList']
# the list of VM contract
vmContractList = vmDataConfiguration['vmContractLengthList']
# the list of VM contrqact payment
vmPaymentList = vmDataConfiguration['vmPaymentList']
# the number of the routers in the topology
numOfRouters = len(networkTopology['router'])



# relax and fix decomposition
# 1. Time Decomposition
# 2. Time and Stage Decomposition 1
# 3. Time and Stage Decomposition 2
relaxAndFixDecomposition = 1

subProblemVarList = []

if relaxAndFixDecomposition == 1 :
    # time decomposition
    subProblemVarList = orderByTimePeriodsAscending(windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters)
elif relaxAndFixDecomposition == 2 :
    # time and stage decomposition 1
    subProblemVarList = orderByTimePeriodsAndStagesAscending(windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters)
elif relaxAndFixDecomposition == 3 :
    # time and stage decomposition 2
    subProblemVarList = orderByTimePeriodsAndStagesAscending_2(windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters)
else :
    print('No decomposition was choosed')

fixedAndOptimizedVarDict = dict()

for subProblemIndex in range(0, len(subProblemVarList)) :
    periodVarDict = subProblemVarList[subProblemIndex]
    currentFixedVarDict = periodVarDict['fix']
    
    # update the values of fixed decision variables
    for key in currentFixedVarDict :
        currentFixedVarDict[key] = fixedAndOptimizedVarDict[key]
    
    currentOptimizedVarDict = periodVarDict['optimize']
    currentRelaxedVarDict = periodVarDict['relax']
    
    # only the variables in optimized set and relaxed set are included in the solution dictionary
    modelVarSolutionDict = solveModel(timeLength, currentFixedVarDict, currentOptimizedVarDict, currentRelaxedVarDict)
    
    for key in currentOptimizedVarDict :
        fixedAndOptimizedVarDict[key] = modelVarSolutionDict[key]

print('Relax and Fix complete')

# output the result of relax and fix
column = ['Variable name', 'Value']
data = [[key, fixedAndOptimizedVarDict[key]] for key in fixedAndOptimizedVarDict]

writeModelResult('relaxAndFixModelResult.csv', column, data)

























