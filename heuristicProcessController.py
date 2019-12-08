# control the heuristic process
from readData import *
from subFunctions import *
from relaxAndFixController import *
from fixAndOptimizeController import *
from solveModel import *

# configure the experiment

instanceData = getVirtualResource()
vmDataConfiguration = getVmDataConfiguration(instanceData)
storageAndBandwidthPrice = getCostOfStorageBandBandwidth()
networkTopology = getNetworkTopology()

# Decomposition-required parameters : windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters

# the number of time periods that are going to be optimized in each iteration
windowSize = 4
# the percentage of the variables that are going to be re-optimized in the next iteration
overlap = 0.5
# the number of time periods
timeLength = 50
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

for relaxAndFixDecomposition in [1, 2, 3] :
    for fixAndOptimizeDecomposition in [1, 2, 3] :
        # relax and fix decomposition
        # 1. Time Decomposition
        # 2. Time and Stage Decomposition 1
        # 3. Time and Stage Decomposition 2
        # relaxAndFixDecomposition = 1
        
        subProblemVarList = []
        
        if relaxAndFixDecomposition == 1 :
            # time decomposition
            subProblemVarList = relaxAndFix_orderByTimePeriodsAscending(windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters)
        elif relaxAndFixDecomposition == 2 :
            # time and stage decomposition 1
            subProblemVarList = relaxAndFix_orderByTimePeriodsAndStagesAscending(windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters)
        elif relaxAndFixDecomposition == 3 :
            # time and stage decomposition 2
            subProblemVarList = relaxAndFix_orderByTimePeriodsAndStagesAscending_2(windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters)
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
            
            fixedAndOptimizedVarDict['Cost'] = modelVarSolutionDict['Cost']
        
        print('Relax and Fix complete')
        
        # output the result of relax and fix
        column = ['Variable name', 'Value']
        data = [[key, fixedAndOptimizedVarDict[key]] for key in fixedAndOptimizedVarDict]
        
        writeModelResult('relaxAndFixModelResult_RF' + str(relaxAndFixDecomposition) + '_FO' + str(fixAndOptimizeDecomposition) + '.csv', column, data)
        
        
        # fix and optimize decomposition
        # 1. Time Decomposition
        # 2. Time and Stage Decomposition 1
        # 3. Time and Stage Decomposition 2
        # fixAndOptimizeDecomposition = 1
        
        fixAndOptSubProblemList = []
        
        if fixAndOptimizeDecomposition == 1 :
            # time decomposition
            fixAndOptSubProblemList = fixAndOptimize_orderByTimePeriodAscending(fixedAndOptimizedVarDict, windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters)
        elif fixAndOptimizeDecomposition == 2 :
            # time and stage decomposition 1
            fixAndOptSubProblemList = fixAndOptimize_orderByTimePeriodAndStage_1(fixedAndOptimizedVarDict, windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters)
        elif fixAndOptimizeDecomposition == 3 :
            # time and stage decomposition 2
            fixAndOptSubProblemList = fixAndOptimize_orderByTimePeriodAndStage_2(fixedAndOptimizedVarDict, windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters)
        else :
            print('No decomposition was choosed')
        
        # the dictionary recording the best solution (to which represents the values that the variables should be fixed)
        currentBestSolutionDict = dict()
        for key in fixedAndOptimizedVarDict :
            currentBestSolutionDict[key] = fixedAndOptimizedVarDict[key]
        
        for subProblemIndex in range(0, len(fixAndOptSubProblemList)) :
            subProblemDict = fixAndOptSubProblemList[subProblemIndex]
            fixedVarDict = subProblemDict['fix']
            
            # update the values for the decision variables that are going to be fixed
            for key in fixedVarDict :
                fixedVarDict[key] = currentBestSolutionDict[key]
            
            optimizedVarDict = subProblemDict['optimize']
            # relaxed variable set should be empty
            relaxedVarDict = dict()
            
            modelResultDict = solveModel(timeLength, fixedVarDict, optimizedVarDict, relaxedVarDict)
            
            modelResultTotalCost = modelResultDict['Cost']
            currentBestSolutionTotalCost = currentBestSolutionDict['Cost']
            
            # if the cost of new solution is lower than the current best solution, then  update the best solution
            if modelResultTotalCost < currentBestSolutionTotalCost :
                for key in optimizedVarDict :
                    currentBestSolutionDict[key] = modelResultDict[key]
                currentBestSolutionDict['Cost'] = modelResultDict['Cost']
        
        fixAndOptResult = [[key, currentBestSolutionDict[key]] for key in currentBestSolutionDict]
        
        writeModelResult('fixAndOptModelResult_RF' + str(relaxAndFixDecomposition) + '_FO' + str(fixAndOptimizeDecomposition) + '.csv', column, fixAndOptResult)


















