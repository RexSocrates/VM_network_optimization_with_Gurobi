# relax and fix controller
import math

# initialize the window for time decomposition
def initWindow_TD(windowSize, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters) :
    optimizedVarDict = dict()
    relaxedVarDict = dict()
    
    # VM decision variables
    for timeStage in range(0, timeLength) :
        for providerIndex in range(0, len(providerList)) :
            provider = providerList[providerIndex]
            for userIndex in range(0, numOfUsers) :
                for vmTypeIndex in range(0, len(vmTypeList)):
                    vmType = vmTypeList[vmTypeIndex]
                    for vmContractLength in vmContractList :
                        for vmPayment in vmPaymentList :
                            # VM reservation
                            resDecVarName = 'vmRes_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                            # vm utilization
                            utiDecVarName = 'vmUti_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                            
                            if timeStage < windowSize :
                                # add the variable into the set that is going to be optimized
                                optimizedVarDict[resDecVarName] = 0
                                optimizedVarDict[utiDecVarName] = 0
                            else :
                                # add thevariables into the set that is going to be relaxed
                                relaxedVarDict[resDecVarName] = 0
                                relaxedVarDict[utiDecVarName] = 0
                    # VM on-demand
                    onDemandDecVarName = 'vmOnDemand_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
                    
                    if timeStage < windowSize :
                        # put the on-demand VM decision variables into the optimized set
                        optimizedVarDict[onDemandDecVarName] = 0
                    else :
                        # put the on-demand VM decision variables into the relaxed set
                        relaxedVarDict[onDemandDecVarName] = 0
                    
        for routerIndex in range(0, numOfRouters) :
            timeRouterStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
            routerStatusVarName = 'RS_' + timeRouterStr
            if timeStage < windowSize :
                # put the decision variables into the optimized set
                optimizedVarDict[routerStatusVarName] = 0
            else :
                # put the decision variables into the relaxed set
                relaxedVarDict[routerStatusVarName] = 0
    
    decVarSetsDict = dict()
    decVarSetsDict['optimize'] = optimizedVarDict
    decVarSetsDict['relax'] = relaxedVarDict
    
    return  decVarSetsDict

# initialize the window for time and stage decomposition
def initWindow_TSD(windowSize, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters) :
    optimizedVarDict = dict()
    relaxedVarDict = dict()
    
    for timeStage in range(0, timeLength) :
        for providerIndex in range(0, len(providerList)) :
            provider = providerList[providerIndex]
            for userIndex in range(0, numOfUsers) :
                for vmTypeIndex in range(0, len(vmTypeList)) :
                    vmType = vmTypeList[vmTypeIndex]
                    for vmContractLength in vmContractList :
                        for vmPayment in vmPaymentList :
                            # VM reservation
                            resDecVarName = 'vmRes_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                            # vm utilization
                            utiDecVarName = 'vmUti_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                            
                            if timeStage < windowSize :
                                optimizedVarDict[resDecVarName] = 0
                                optimizedVarDict[utiDecVarName] = 0
                            else :
                                relaxedVarDict[resDecVarName] = 0
                                relaxedVarDict[utiDecVarName] = 0
                    # VM on-demand
                    onDemandDecVarName = 'vmOnDemand_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
                    
                    if timeStage < windowSize :
                        optimizedVarDict[onDemandDecVarName] = 0
                    else :
                        relaxedVarDict[onDemandDecVarName] = 0
        
        for routerIndex in range(0, numOfRouters) :
            timeRouterStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
            routerStatusVarName = 'RS_' + timeRouterStr
            
            relaxedVarDict[routerStatusVarName] = 0

    decVarSetsDict = dict()
    decVarSetsDict['optimize'] = optimizedVarDict
    decVarSetsDict['relax'] = relaxedVarDict
    
    return  decVarSetsDict

# define a function to divide the model into multiple sub-problems
def orderByTimePeriodsAscending(windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters) :
    movingSteps = math.ceil(windowSize * overlap)
    subProblemsList = []
    
    # count how many windows in time decomposition
    windowPeriodList_start = []
    windowPeriodList_end = []
    
    windowPeriod_start = 0
    windowPeriod_end = windowSize
    
    while(windowPeriod_end <= timeLength) :
        print()
        windowPeriodList_start.append(windowPeriod_start)
        windowPeriodList_end.append(windowPeriod_end)
        
        windowPeriod_start = min(windowPeriod_start + movingSteps, timeLength)
        windowPeriod_end = min(windowPeriod_end + movingSteps, timeLength)
    
    for periodIndex in range(0, len(windowPeriodList_start)) :
        windowPeriod_start = windowPeriodList_start[periodIndex]
        windowPeriod_end = windowPeriodList_end[periodIndex]
        
        fixedVarDict = dict()
        optimizedVarDict = dict()
        relaxedVarDict = dict()
        
        for timeStage in range(0, timeLength) :
            for providerIndex in range(0, len(providerList)) :
                provider = providerList[providerIndex]
                for userIndex in range(0, numOfUsers) :
                    for vmTypeIndex in range(0, len(vmTypeList)) :
                        vmType = vmTypeList[vmTypeIndex]
                        for vmContractLength in vmContractList :
                            for vmPayment in vmPaymentList :
                                # VM reservation decision variable name
                                resDecVarName = 'vmRes_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                                # VM utilization decision variable name
                                utiDecVarName = 'vmUti_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                                
                                if timeStage < windowPeriod_start :
                                    # put the variables into the fixed set
                                    fixedVarDict[resDecVarName] = 0
                                    fixedVarDict[utiDecVarName] = 0
                                elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end :
                                    # put the variables into the optimized set
                                    optimizedVarDict[resDecVarName] = 0
                                    optimizedVarDict[utiDecVarName] = 0
                                else :
                                    # put the variables into the relaxed set
                                    relaxedVarDict[resDecVarName] = 0
                                    relaxedVarDict[utiDecVarName] = 0
                                
                        # on-demand VM name
                        onDemandDecVarName = 'vmOnDemand_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
                        
                        if timeStage < windowPeriod_start :
                            # fix to current value
                            fixedVarDict[onDemandDecVarName] = 0
                        elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end :
                            # optimize
                            optimizedVarDict[onDemandDecVarName] = 0
                        else :
                            # relaxed
                            relaxedVarDict[onDemandDecVarName] = 0
            
            for routerIndex in range(0, numOfRouters) :
                # router status decision variable name
                timeRouterStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
                routerStatusVarName = 'RS_' + timeRouterStr
                
                if timeStage < windowPeriod_start :
                    # fix
                    fixedVarDict[routerStatusVarName] = 0
                elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end :
                    # optimize
                    optimizedVarDict[routerStatusVarName] = 0
                else :
                    # relax
                    relaxedVarDict[routerStatusVarName] = 0
        
        # put three sets into a dictionary and add the dictionary at the end of the list
        periodVarDict = dict()
        periodVarDict['fix'] = fixedVarDict
        periodVarDict['optimize'] = optimizedVarDict
        periodVarDict['relax'] = relaxedVarDict
        
        subProblemsList.append(periodVarDict)
    
    return subProblemsList

# a function used to configure the variable sets of fixed, optimized and relaxed for time and stage decomposition_1
def orderByTimePeriodsAndStagesAscending(windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters) :
    movingSteps = math.ceil(windowSize * overlap)
    subProblemsList = []
    
    # count how many windows in time decomposition
    windowPeriodList_start = []
    windowPeriodList_end = []
    
    windowPeriod_start = 0
    windowPeriod_end = windowSize
    
    while(windowPeriod_end <= timeLength) :
        print()
        windowPeriodList_start.append(windowPeriod_start)
        windowPeriodList_end.append(windowPeriod_end)
        
        windowPeriod_start = min(windowPeriod_start + movingSteps, timeLength)
        windowPeriod_end = min(windowPeriod_end + movingSteps, timeLength)
    
    for periodIndex in range(0, len(windowPeriodList_start)) :
        windowPeriod_start = windowPeriodList_start[periodIndex]
        windowPeriod_end = windowPeriodList_end[periodIndex]
        
        for timeStage in range(0, timeLength) :
            for stage in [1, 2] :
                
                fixedVarDict = dict()
                optimizedVarDict = dict()
                relaxedVarDict = dict()
                
                for providerIndex in range(0, len(providerList)) :
                    provider = providerList[providerIndex]
                    for userIndex in range(0, numOfUsers) :
                        for vmTypeIndex in range(0, len(vmTypeList)) :
                            vmType = vmTypeList[vmTypeIndex]
                            for vmContractLength in vmContractList :
                                for vmPayment in vmPaymentList :
                                    # VM reservation
                                    resDecVarName = 'vmRes_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                                    # VM utilization
                                    utiDecVarName = 'vmUti_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                                    
                                    if timeStage < windowPeriod_start :
                                        fixedVarDict[resDecVarName] = 0
                                        fixedVarDict[utiDecVarName] = 0
                                    elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 1 :
                                        optimizedVarDict[resDecVarName] = 0
                                        optimizedVarDict[utiDecVarName] = 0
                                    elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                                        fixedVarDict[resDecVarName] = 0
                                        fixedVarDict[utiDecVarName] = 0
                                    else :
                                        relaxedVarDict[resDecVarName] = 0
                                        relaxedVarDict[utiDecVarName] = 0
                                    
                                    
                            # on-demand variable name
                            onDemandDecVarName = 'vmOnDemand_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
                            
                            if timeStage < windowPeriod_start :
                                fixedVarDict[onDemandDecVarName] = 0
                            elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 1 :
                                optimizedVarDict[onDemandDecVarName] = 0
                            elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                                fixedVarDict[onDemandDecVarName] = 0
                            else :
                                relaxedVarDict[onDemandDecVarName] = 0
                            
                for routerIndex in range(0, numOfRouters) :
                    timeRouterStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
                    routerStatusVarName = 'RS_' + timeRouterStr
                    
                    if timeStage < windowPeriod_start :
                        fixedVarDict[routerStatusVarName] = 0
                    elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 1 :
                        relaxedVarDict[routerStatusVarName] = 0
                    elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                        optimizedVarDict[routerStatusVarName] = 0
                    else :
                        relaxedVarDict[routerStatusVarName] = 0
                # add three variable sets into a dictionary and add it at the end of the list
                periodAndStageVarDict = dict()
                periodAndStageVarDict['fix'] = fixedVarDict
                periodAndStageVarDict['optimize'] = optimizedVarDict
                periodAndStageVarDict['relax'] = relaxedVarDict
            
                subProblemsList.append(periodAndStageVarDict)
    
    return subProblemsList

# a function used to configure the variable sets of fixed, optimized and relaxed for time and stage decomposition_2
# stage 1 VM reservation
# stage 2 VM utilization and router bandwidth reservation, utilization
def orderByTimePeriodsAndStagesAscending_2(windowSize, overlap, timeLength, numOfUsers, providerList, vmTypeList, vmContractList, vmPaymentList, numOfRouters) :
    movingSteps = math.ceil(windowSize * overlap)
    subProblemList = []
    
    # count how many windows in time decomposition
    windowPeriodList_start = []
    windowPeriodList_end = []
    
    windowPeriod_start = 0
    windowPeriod_end = windowSize
    
    while(windowPeriod_end <= timeLength) :
        print()
        windowPeriodList_start.append(windowPeriod_start)
        windowPeriodList_end.append(windowPeriod_end)
        
        windowPeriod_start = min(windowPeriod_start + movingSteps, timeLength)
        windowPeriod_end = min(windowPeriod_end + movingSteps, timeLength)
    
    for periodIndex in range(0, len(windowPeriodList_start)) :
        windowPeriod_start = windowPeriodList_start[periodIndex]
        windowPeriod_end = windowPeriodList_end[periodIndex]        
        for timeStage in range(0, timeLength) :
            for stage in [1, 2] :
                fixedVarDict = dict()
                optimizedVarDict = dict()
                relaxedVarDict = dict()
                
                for providerIndex in range(0, len(providerList)) :
                    provider = providerList[providerIndex]
                    for userIndex in range(0, numOfUsers) :
                        for vmTypeIndex in range(0, len(vmTypeList)) :
                            vmType = vmTypeList[vmTypeIndex]
                            for vmContractLength in vmContractList :
                                for vmPayment in vmPaymentList :
                                    # vm reservation
                                    resDecVarName = 'vmRes_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                                    # vm utilization
                                    utiDecVarName = 'vmUti_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
                                    
                                    if timeStage < windowPeriod_start :
                                        # fix reservation, utilization
                                        fixedVarDict[resDecVarName] = 0
                                        fixedVarDict[utiDecVarName] = 0
                                    elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 1 :
                                        # optimized stage 1 : optimize reservation, relax utilization
                                        optimizedVarDict[resDecVarName] = 0
                                        relaxedVarDict[utiDecVarName] = 0
                                    elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                                        # optimized stage 2 : fix reservation, optimize utilization
                                        fixedVarDict[resDecVarName] = 0
                                        optimizedVarDict[utiDecVarName] = 0
                                    else :
                                        # relax
                                        relaxedVarDict[resDecVarName] = 0
                                        relaxedVarDict[utiDecVarName] = 0
                                    
                                    
                            # on-demand VM
                            onDemandDecVarName = 'vmOnDemand_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
                            
                            if timeStage < windowPeriod_start :
                                # fix on-demand VM
                                fixedVarDict[onDemandDecVarName] = 0
                            elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 1 :
                                # relax on-demand VM
                                relaxedVarDict[onDemandDecVarName] = 0
                            elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                                # optimize on-demand VM
                                optimizedVarDict[onDemandDecVarName] = 0
                            else :
                                # relax on-demand VM
                                relaxedVarDict[onDemandDecVarName] = 0
                
                # router
                for routerIndex in range(0, numOfRouters) :
                    timeRouterStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
                    routerStatusVarName = 'RS_' + timeRouterStr
                    
                    
                    if timeStage < windowPeriod_start :
                        # fix router status
                        fixedVarDict[routerStatusVarName] = 0
                    elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 1 :
                        # relax router status
                        relaxedVarDict[routerStatusVarName] = 0
                    elif timeStage >= windowPeriod_start and timeStage < windowPeriod_end and stage == 2 :
                        # optimize router status
                        optimizedVarDict[routerStatusVarName] = 0
                    else :
                        # relax router status
                        relaxedVarDict[routerStatusVarName] = 0
                
                periodAndStageVarDict = dict()
                periodAndStageVarDict['fix'] = fixedVarDict
                periodAndStageVarDict['optimize'] = optimizedVarDict
                periodAndStageVarDict['relax'] = relaxedVarDict
                
                subProblemList.append(periodAndStageVarDict)
    
    return subProblemList
