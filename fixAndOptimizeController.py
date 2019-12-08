# configure the variable sets for fix and optimize
import math

# fix and optimize - time decomposition
def fixAndOptimize_orderByTimePeriodAscending(initialSolutionDecVarDict, windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters) :
    movingSteps = math.ceil(windowSize * overlap)
    subProblemsList = []
    
    # count how many windows in time decomposition
    windowPeriodList_start = []
    windowPeriodList_end = []
    
    windowPeriod_start = 0
    windowPeriod_end = windowSize
    
    while(windowPeriod_end <= timeLength) :
        windowPeriodList_start.append(windowPeriod_start)
        windowPeriodList_end.append(windowPeriod_end)
        
        if windowPeriod_end >= timeLength :
            break
        
        windowPeriod_start = min(windowPeriod_start + movingSteps, timeLength)
        windowPeriod_end = min(windowPeriod_end + movingSteps, timeLength)
    
    for periodIndex in range(0, len(windowPeriodList_start)) :
        windowPeriod_start = windowPeriodList_start[periodIndex]
        windowPeriod_end = windowPeriodList_end[periodIndex]
        
        fixedVarDict = dict()
        optimizedVarDict = dict()
        
        for timeStage in range(0, timeLength) :
            for providerIndex in range(0, len(providerList)) :
                provider = providerList[providerIndex]
                for userIndex in range(0, numOfUsers) :
                    for vmTypeIndex in range(0, len(vmTypeList)) :
                        vmType = vmTypeList[vmTypeIndex]
                        for vmContract in vmContractList :
                            for vmPayment in vmPaymentList :
                                # decision variable name
                                resDecVarName = 'vmRes_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContract) + 'j_' + str(vmPayment)
                                utiDecVarName = 'vmUti_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContract) + 'j_' + str(vmPayment)
                                
                                if timeStage >= windowPeriod_start and timeStage < windowPeriod_end :
                                    optimizedVarDict[resDecVarName] = 0
                                    optimizedVarDict[utiDecVarName] = 0
                                else :
                                    fixedVarDict[resDecVarName] = initialSolutionDecVarDict[resDecVarName]
                                    fixedVarDict[utiDecVarName] = initialSolutionDecVarDict[utiDecVarName]
                        
                        # on-demand VM
                        onDemandDecVarName = 'vmOnDemand_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
                        
                        if timeStage >= windowPeriod_start and timeStage < windowPeriod_end :
                            optimizedVarDict[onDemandDecVarName] = 0
                        else :
                            fixedVarDict[onDemandDecVarName] = initialSolutionDecVarDict[onDemandDecVarName]
                        
            for routerIndex in range(0, numOfRouters) :
                timeRouterStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
                routerStatusVarName = 'RS_' + timeRouterStr
                
                if timeStage >= windowPeriod_start and timeStage < windowPeriod_end :
                    optimizedVarDict[routerStatusVarName] = 0
                else :
                    fixedVarDict[routerStatusVarName] = initialSolutionDecVarDict[routerStatusVarName]
        
        periodVarDict = dict()
        periodVarDict['fix'] = fixedVarDict
        periodVarDict['optimize'] = optimizedVarDict
        
        subProblemsList.append(periodVarDict)
    
    return subProblemsList

# set the fixed and optimized variable set for fix and optimize time and stage decomposition_1
def fixAndOptimize_orderByTimePeriodAndStage_1(initialSolutionDecVarDict, windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters) :
    movingSteps = math.ceil(windowSize * overlap)
    subProblemsList = []
    
    # count how many windows in time decomposition
    windowPeriodList_start = []
    windowPeriodList_end = []
    
    windowPeriod_start = 0
    windowPeriod_end = windowSize
    
    while(windowPeriod_end <= timeLength) :
        windowPeriodList_start.append(windowPeriod_start)
        windowPeriodList_end.append(windowPeriod_end)
        
        if windowPeriod_end >= timeLength :
            break
        
        windowPeriod_start = min(windowPeriod_start + movingSteps, timeLength)
        windowPeriod_end = min(windowPeriod_end + movingSteps, timeLength)
    
    for periodIndex in range(0, len(windowPeriodList_start)) :
        windowPeriod_start = windowPeriodList_start[periodIndex]
        windowPeriod_end = windowPeriodList_end[periodIndex]
        
        for timeStage in range(0, timeLength) :
            for stage in [1, 2] :
                fixedVarDict = dict()
                optimizedVarDict = dict()
                
                for providerIndex in range(0, len(providerList)) :
                    provider = providerList[providerIndex]
                    for userIndex in range(0, numOfUsers) :
                        for vmTypeIndex in range(0, len(vmTypeList)) :
                            vmType = vmTypeList[vmTypeIndex]
                            for vmContract in vmContractList :
                                for vmPayment in vmPaymentList :
                                    # VM reservation and utilization
                                    resDecVarName = 'vmRes_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContract) + 'j_' + str(vmPayment)
                                    utiDecVarName = 'vmUti_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContract) + 'j_' + str(vmPayment)
                                    
                                    if timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 1 :
                                        optimizedVarDict[resDecVarName] = 0
                                        optimizedVarDict[utiDecVarName] = 0
                                    else :
                                        fixedVarDict[resDecVarName] = initialSolutionDecVarDict[resDecVarName]
                                        fixedVarDict[utiDecVarName] = initialSolutionDecVarDict[utiDecVarName]
                                    
                            # on-demand VM
                            onDemandDecVarName = 'vmOnDemand_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
                            
                            if timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 1 :
                                optimizedVarDict[onDemandDecVarName] = 0
                            else :
                                fixedVarDict[onDemandDecVarName] = initialSolutionDecVarDict[onDemandDecVarName]
                
                for routerIndex in range(0, numOfRouters) :
                    # router status
                    timeRouterStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
                    routerStatusVarName = 'RS_' + timeRouterStr
                    
                    if timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                        optimizedVarDict[routerStatusVarName] = 0
                    else :
                        fixedVarDict[routerStatusVarName] = initialSolutionDecVarDict[routerStatusVarName]
                
                periodAndStageVarDict = dict()
                periodAndStageVarDict['fix'] = fixedVarDict
                periodAndStageVarDict['optimize'] = optimizedVarDict
                subProblemsList.append(periodAndStageVarDict)
    
    return subProblemsList

# set the fixed and optimized variable set for fix and optimize time and stage decomposition_2
def fixAndOptimize_orderByTimePeriodAndStage_2(initialSolutionDecVarDict, windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters) :
    movingSteps = math.ceil(windowSize * overlap)
    subProblemsList = []
    
    # count how many windows in time decomposition
    windowPeriodList_start = []
    windowPeriodList_end = []
    
    windowPeriod_start = 0
    windowPeriod_end = windowSize
    
    while(windowPeriod_end <= timeLength) :
        windowPeriodList_start.append(windowPeriod_start)
        windowPeriodList_end.append(windowPeriod_end)
        
        if windowPeriod_end >= timeLength :
            break
        
        windowPeriod_start = min(windowPeriod_start + movingSteps, timeLength)
        windowPeriod_end = min(windowPeriod_end + movingSteps, timeLength)
    
    for periodIndex in range(0, len(windowPeriodList_start)) :
        windowPeriod_start = windowPeriodList_start[periodIndex]
        windowPeriod_end = windowPeriodList_end[periodIndex]
        
        for timeStage in range(0, timeLength) :
            for stage in [1, 2] :
                fixedVarDict = dict()
                optimizedVarDict = dict()
                
                for providerIndex in range(0, len(providerList)) :
                    provider = providerList[providerIndex]
                    for userIndex in range(0, numOfUsers) :
                        for vmTypeIndex in range(0, len(vmTypeList)) :
                            vmType = vmTypeList[vmTypeIndex]
                            for vmContract in vmContractList :
                                for vmPayment in vmPaymentList :
                                    # VM reservation and utilization
                                    resDecVarName = 'vmRes_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContract) + 'j_' + str(vmPayment)
                                    utiDecVarName = 'vmUti_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContract) + 'j_' + str(vmPayment)
                                    
                                    if timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 1 :
                                        optimizedVarDict[resDecVarName] = 0
                                    else :
                                        fixedVarDict[resDecVarName] = initialSolutionDecVarDict[resDecVarName]
                                    
                                    if timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                                        optimizedVarDict[utiDecVarName] = 0
                                    else :
                                        fixedVarDict[utiDecVarName] = initialSolutionDecVarDict[utiDecVarName]
                                    
                            # on-demand VM
                            onDemandDecVarName = 'vmOnDemand_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
                            
                            if timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                                optimizedVarDict[onDemandDecVarName] = 0
                            else :
                                fixedVarDict[onDemandDecVarName] = initialSolutionDecVarDict[onDemandDecVarName]
                
                for routerIndex in range(0, numOfRouters) :
                    # router status
                    timeRouterStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
                    routerStatusVarName = 'RS_' + timeRouterStr
                    
                    if timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                        optimizedVarDict[routerStatusVarName] = 0
                    else :
                        fixedVarDict[routerStatusVarName] = initialSolutionDecVarDict[routerStatusVarName]
                
                periodAndStageVarDict = dict()
                periodAndStageVarDict['fix'] = fixedVarDict
                periodAndStageVarDict['optimize'] = optimizedVarDict
                subProblemsList.append(periodAndStageVarDict)
    
    return subProblemsList