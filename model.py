# Build gurobi model
from readData import *
from subFunctions import *
from gurobipy import *
import random
            
# get instance data from csv file, get get the lists of vm types and cloud providers from instance data

instanceData = getVirtualResource()
vmDataConfiguration = getVmDataConfiguration(instanceData)
providerList = vmDataConfiguration['providerList']
providerAreaDict = getProviderAreaDict(instanceData)
vmTypeList = vmDataConfiguration['vmTypeList']
storageAndBandwidthPrice = getCostOfStorageAndBandwidth()
networkTopology = getNetworkTopology()

modelRunTimeList = ['Runtime']

testValueList = [0]
testValueList.extend([val for val in range(10, 151, 10)])
testValueList.reverse()

for testValue in testValueList :
	print()

	model = Model('VM_network_and_energy_optimization_model')
	
	# setting model parameters
	# log file of gurobi optimizer
	model.setParam(GRB.Param.LogFile, 'log.txt')
	# set the stopping criteria for gurobi optimizer, which is the gap less than 0.01
	# model.setParam(GRB.Param.MIPGapAbs, 0.02)
	model.setParam(GRB.Param.MIPGap, 0.00019)
	
	timeLength = 50
	numOfUsers = len(networkTopology['user'])
	# vmContractLengthList = [10, 30]
	vmContractLengthList = vmDataConfiguration['vmContractLengthList']
	vmPaymentList = vmDataConfiguration['vmPaymentList']
	
	# VM demand at each time stage
	vmDemandList = generateVmDemand(timeLength, numOfUsers, vmTypeList)
	
	# Virtual Machines
	
	# sort the instance data for calculating the cost of using VM
	sortedVmList = sortVM(instanceData, providerList, vmTypeList, vmContractLengthList, vmPaymentList)
	
	# VM  reservation decision variables
	vmResDecVar = []
	# VM utilization decision variables
	vmUtilizationDecVar = []
	# VM on-demand decision variables
	vmOnDemandDecVar = []
	# a list that contains the decision variables of effective VM reservation
	effectiveVmResDecVarDict = dict()
	
	# iniitalize the list of effective VM reservation decision variables
	for providerIndex in range(0, len(providerList)) :
	    provider = providerList[providerIndex]
	    userEffectiveVmResDecVarDict = dict()
	    for userIndex in range(0, numOfUsers) :
	        vmTypeEffectiveVmResDecVarDict = dict()
	        for vmTypeIndex in range(0, len(vmTypeList)) :
	            vmType = vmTypeList[vmTypeIndex]
	            contractEffectiveVmResDecVarDict = dict()
	            for contractLength in vmContractLengthList :
	                paymentEffectiveVmResDecVarDict = dict()
	                for payment in vmPaymentList :
	                    effectiveVmResDecVarList = []
	                    for timeStage in range(0, timeLength) :
	                        effectiveVmResDecVarList.append([])
	                    paymentEffectiveVmResDecVarDict[str(payment)] = effectiveVmResDecVarList
	                contractEffectiveVmResDecVarDict[str(contractLength)] = paymentEffectiveVmResDecVarDict
	            vmTypeEffectiveVmResDecVarDict[str(vmType)] = contractEffectiveVmResDecVarDict
	        userEffectiveVmResDecVarDict[str(userIndex)] = vmTypeEffectiveVmResDecVarDict
	    effectiveVmResDecVarDict[str(provider)] = userEffectiveVmResDecVarDict
	                    
	# the dictionary recording the reservation fee
	vmReservationFeeDict = dict()
	# the dictionary recording the utilization fee of reserved VMs
	vmUtilizationFeeDict = dict()
	
	
	# equation 2 the cost of VMs
	for timeStage in range(0, timeLength) :
	    providerDecVar_res = dict()
	    providerDecVar_uti = dict()
	    providerDecVar_onDemand = dict()
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        userDecVar_res = dict()
	        userDecVar_uti = dict()
	        userDecVar_onDemand = dict()
	        for userIndex in range(0, numOfUsers) :
	            vmDecVar_res = dict()
	            vmDecVar_uti = dict()
	            vmDecVar_onDemand = dict()
	            
	            vmTypeReservationFeeDict = dict()
	            vmTypeUtilizationFeeDict = dict()
	            for vmIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmIndex]
	                contractDecVar_res = dict()
	                contractDecVar_uti = dict()
	                
	                contractReservationFeeDict = dict()
	                contractUtilizationFeeDict = dict()
	                
	                # on-demand vm data (cost of using on-demand instance)
	                onDemandParameter = 0
	                
	                for contractIndex in range(0, len(vmContractLengthList)) :
	                    contractLength = vmContractLengthList[contractIndex]
	                    paymentOptionDecVar_res = dict()
	                    paymentOptionDecVar_uti = dict()
	                    
	                    paymentReservationFeeDict = dict()
	                    paymentUtilizationFeeDict = dict()
	                    for paymentOptionIndex in range(len(vmPaymentList)) :
	                        paymentOptionsList = vmPaymentList
	                        paymentOption = paymentOptionsList[paymentOptionIndex]
	                        
	                        resDecVarName = 'vmRes_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(contractLength) + 'j_' + str(paymentOption)
	                        utiDecVarName = 'vmUti_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(contractLength) + 'j_' + str(paymentOption)
	                        
	                        # create a decision variable that represent the number of instance whose instance type is i
	                        # reserved from provider p
	                        # at time stage t
	                        # by user u
	                        # adopted contract k and payment option j
	                        reservationVar = model.addVar(lb=0.0, vtype=GRB.INTEGER, name=resDecVarName)
	                        utilizationVar = model.addVar(lb=0.0, vtype=GRB.INTEGER, name=utiDecVarName)
	                        
	                        paymentOptionDecVar_res[paymentOption] = reservationVar
	                        paymentOptionDecVar_uti[paymentOption] = utilizationVar
	                        
	                        # add decision variables to the list for computing the cost of using VM
	                        # vmCostDecVarList.append(reservationVar)
	                        # vmCostDecVarList.append(utilizationVar)
	                        
	                        # vm data
	                        vmDictOfProvider = sortedVmList[str(provider)]
	                        contractDictOfVM = vmDictOfProvider[str(vmType)]
	                        paymentDictOfContract = contractDictOfVM[str(contractLength)]
	                        instanceTupleData = paymentDictOfContract[str(paymentOption)]
	                        
	                        # get the initial reservation price and utilization price
	                        initialResFee = instanceTupleData.resFee
	                        utilizationFee = instanceTupleData.utilizeFee
	                        onDemandFee = instanceTupleData.onDemandFee
	                        
	                        # store the reservation fee of vm
	                        paymentReservationFeeDict[str(paymentOption)] = initialResFee
	                        # store the utilization fee of reserved VM
	                        paymentUtilizationFeeDict[str(paymentOption)] = utilizationFee
	                        
	                        # get the cost of storage and bandwidth of VM
	                        instanceStorageReq = instanceTupleData.storageReq
	                        instanceOutboundBandwidthReq = instanceTupleData.networkReq
	                        
	                        storageAndBandwidthPriceDict = storageAndBandwidthPrice[str(provider)]
	                        storagePrice = storageAndBandwidthPriceDict['storage']
	                        bandwidthPrice = storageAndBandwidthPriceDict['bandwidth']
	                        
	                        utilizationParameter = storagePrice * instanceStorageReq + bandwidthPrice * instanceOutboundBandwidthReq
	                        onDemandParameter = onDemandFee + storagePrice * instanceStorageReq + bandwidthPrice * instanceOutboundBandwidthReq
	                        
	                        # add parameters of decision variables to the list
	                        # vmCostParameterList.append(initialResFee)
	                        # vmCostParameterList.append(utilizationParameter)
	                        
	                        # add reservation decision variable to the effective VM reservation list
	                        userEffectiveVmResDecVarDict = effectiveVmResDecVarDict[str(provider)]
	                        vmTypeEffectiveVmResDecVarDict = userEffectiveVmResDecVarDict[str(userIndex)]
	                        contractEffectiveVmResDecVarDict = vmTypeEffectiveVmResDecVarDict[str(vmType)]
	                        paymentEffectiveVmResDecVarDict = contractEffectiveVmResDecVarDict[str(contractLength)]
	                        effectiveVmResDecVarList = paymentEffectiveVmResDecVarDict[str(paymentOption)]
	                        
	                        for currentTimeStage in range(timeStage, min(timeStage + contractLength, timeLength)) :
	                            effectiveVmDecVarListAtCurrentTimeStage = effectiveVmResDecVarList[currentTimeStage]
	                            effectiveVmDecVarListAtCurrentTimeStage.append(reservationVar)
	                        
	                    contractDecVar_res[str(contractLength)] = paymentOptionDecVar_res
	                    contractDecVar_uti[str(contractLength)] = paymentOptionDecVar_uti
	                    contractReservationFeeDict[str(contractLength)] = paymentReservationFeeDict
	                    contractUtilizationFeeDict[str(contractLength)] = paymentUtilizationFeeDict
	                
	                onDemandDecVarName = 'vmOnDemand_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
	                onDemandVmVar = model.addVar(lb=0.0, vtype=GRB.INTEGER, name=onDemandDecVarName)
	                
	                vmDecVar_res[vmType] = contractDecVar_res
	                vmDecVar_uti[vmType] = contractDecVar_uti
	                vmDecVar_onDemand[vmType] = onDemandVmVar
	                vmTypeReservationFeeDict[str(vmType)] = contractReservationFeeDict
	                vmTypeUtilizationFeeDict[str(vmType)] = contractUtilizationFeeDict
	                
	                # vmCostDecVarList.append(onDemandVmVar)
	                # vmCostParameterList.append(onDemandParameter)
	                
	            userDecVar_res[str(userIndex)] = vmDecVar_res
	            userDecVar_uti[str(userIndex)] = vmDecVar_uti
	            userDecVar_onDemand[str(userIndex)] = vmDecVar_onDemand
	        providerDecVar_res[str(provider)] = userDecVar_res
	        providerDecVar_uti[str(provider)] = userDecVar_uti
	        providerDecVar_onDemand[str(provider)] = userDecVar_onDemand
	        vmReservationFeeDict[str(provider)] = vmTypeReservationFeeDict
	        vmUtilizationFeeDict[str(provider)] = vmTypeUtilizationFeeDict
	    vmResDecVar.append(providerDecVar_res)
	    vmUtilizationDecVar.append(providerDecVar_uti)
	    vmOnDemandDecVar.append(providerDecVar_onDemand)
	
	# set up the cost of VM usage
	vmCostDecVarList = []
	vmCostParameterList = []
	
	for timeStage in range(0, timeLength) :
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        for userIndex in range(0, numOfUsers) :
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmTypeIndex]
	                onDemandVmParameter = 0
	                for vmContractLength in vmContractLengthList :
	                    for vmPayment in vmPaymentList :
	                        # reservation and utilization
	                        vmRes = vmResDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]
	                        vmUti = vmUtilizationDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]
	                        
	                        # effective VM decision variable list
	                        effectiveVmList = effectiveVmResDecVarDict[str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)][timeStage]
	                        
	                        effectiveVmLinExpr = quicksum(effectiveVmList)
	                        
	                        # vm data
	                        insTupleData = sortedVmList[str(provider)][str(vmType)][str(vmContractLength)][str(vmPayment)]
	                        
	                        vmResFee = insTupleData.resFee
	                        vmUtiFee = insTupleData.utilizeFee
	                        
	                        
	                        # storage fee and bandwidth fee
	                        storageAndBandCostDict = storageAndBandwidthPrice[str(provider)]
	                        storagePrice = storageAndBandCostDict['storage']
	                        bandwidthPrice = storageAndBandCostDict['bandwidth']
	                        utilizationStorageAndBandFee = insTupleData.storageReq * storagePrice + insTupleData.networkReq * bandwidthPrice
	                        onDemandVmParameter = insTupleData.onDemandFee + insTupleData.storageReq * storagePrice + insTupleData.networkReq * bandwidthPrice
	                        
	                        # initial reservation fee
	                        vmCostParameterList.append(vmResFee)
	                        vmCostDecVarList.append(vmRes)
	                        
	                        # reserved instances monthly payment
	                        vmCostParameterList.append(vmUtiFee)
	                        vmCostDecVarList.append(effectiveVmLinExpr)
	                        
	                        # the storage and bandwidth fee of reserved instances
	                        vmCostParameterList.append(utilizationStorageAndBandFee)
	                        vmCostDecVarList.append(vmUti)
	                
	                # on-demand variable
	                vmOnDemand = vmOnDemandDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)]
	                
	                vmCostParameterList.append(onDemandVmParameter)
	                vmCostDecVarList.append(vmOnDemand)
	                
	print('VM Cost decision variable complete')
	
	# Bandwidth
	numOfRouters = len(networkTopology['router'])
	routerData = getRouterBandwidthPrice(networkTopology)
	routerDataConfig = getRouterDataConfiguration(routerData)
	routerContractList = routerDataConfig['contractList']
	routerPaymentList = routerDataConfig['payment']
	sortedRouter = sortRouter(routerData, numOfRouters, routerContractList, routerPaymentList)
	routerList = getRouterList(routerData)
	
	# decision variables
	bandResDecVar = []
	bandUtilizationDecVar = []
	bandOnDemandDecVar = []
	
	# a list containing the effective bandwidth
	effectiveBandDecVarDict = dict()
	
	# initialize the bandwidth dictionary
	for userIndex in range(0, numOfUsers) :
	    routerEffectiveBandDecVarDict = dict()
	    for routerIndex in range(0, numOfRouters) :
	        contractEffectiveBandDecVarDict = dict()
	        for bandResContractLength in routerContractList :
	            paymentEffectiveBandDecVarDict = dict()
	            for bandResPayment in routerPaymentList :
	                effectiveBandDecVarList = []
	                for timeStage in range(0, timeLength) :
	                    effectiveBandDecVarList.append([])
	                paymentEffectiveBandDecVarDict[str(bandResPayment)] = effectiveBandDecVarList
	            contractEffectiveBandDecVarDict[str(bandResContractLength)] = paymentEffectiveBandDecVarDict
	        routerEffectiveBandDecVarDict[str(routerIndex)] = contractEffectiveBandDecVarDict
	    effectiveBandDecVarDict[str(userIndex)] = routerEffectiveBandDecVarDict
	
	# a dictionary recording the reservation fee of routers
	bandReservationFeeDict = dict()
	# a dictionary recording the utilization fee of reserved bandwidth
	bandUtilizationFeeDict = dict()
	
	
	# equation 3 the cost of network bandwidth
	for timeStage in range(0, timeLength) :
	    bandUserDecVar_res = dict()
	    bandUserDecVar_uti = dict()
	    bandUserDecVar_onDemand = dict()
	    
	    for userIndex in range(0, numOfUsers) :
	        bandRouterDecVar_res = dict()
	        bandRouterDecVar_uti = dict()
	        bandRouterDecVar_onDemand = dict()
	        
	        for routerIndex in range(0, numOfRouters) :
	            bandContractDecVar_res = dict()
	            bandContractDecVar_uti = dict()
	            
	            bandContractReservationFeeDict = dict()
	            bandContractUtilizationFeeDict = dict()
	            
	            # record the price of on-demand bandwidth price
	            routerOnDemandFee = 0
	            
	            for bandResContractIndex in range(0, len(routerContractList)) :
	                bandResContractLength = routerContractList[bandResContractIndex]
	                
	                bandPaymentOptionDecVar_res = dict()
	                bandPaymentOptionDecVar_uti = dict()
	                
	                bandPaymentReservationFee = dict()
	                bandPaymentUtilizationFee = dict()
	                
	                for bandPaymentOptionIndex in range(0, len(routerPaymentList)) :
	                    bandPaymentOption = routerPaymentList[bandPaymentOptionIndex]
	                    
	                    bandResDecVarName = 'bandRes_t_' + str(timeStage) + 'u_' + str(userIndex) + 'r_' + str(routerIndex) + 'l_' + str(bandResContractLength) + 'm_' + str(bandPaymentOption)
	                    bandUtiDecVarName = 'bandUti_t_' + str(timeStage) + 'u_' + str(userIndex) + 'r_' + str(routerIndex) + 'l_' + str(bandResContractLength) + 'm_' + str(bandPaymentOption)
	                    
	                    bandReservation = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=bandResDecVarName)
	                    bandUtilization = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=bandUtiDecVarName)
	                    
	                    bandPaymentOptionDecVar_res[bandPaymentOption] = bandReservation
	                    bandPaymentOptionDecVar_uti[bandPaymentOption] = bandUtilization
	                    
	                    # add decision variables to the list
	                    # bandwidthCostDecVarList.append(bandReservation)
	                    # bandwidthCostDecVarList.append(bandUtilization)
	                    
	                    # add parameter to the list
	                    contractsOfRouter = sortedRouter[str(routerIndex)]
	                    paymentsOfContract = contractsOfRouter[str(bandResContractLength)]
	                    routerTupleData = paymentsOfContract[str(bandPaymentOption)]
	                    
	                    routerInitialResFee = routerTupleData.reservationFee
	                    routerUtilizationFee = routerTupleData.utilizationFee
	                    # update the price of on-demand bandwidth
	                    routerOnDemandFee = routerTupleData.onDemandFee
	                    
	                    # store the reservation fee in the dictionary to configure the upfront cost constraint
	                    bandPaymentReservationFee[str(bandPaymentOption)] = routerInitialResFee
	                    # store the utilization fee in the dictionary to calculate the monthly payment
	                    bandPaymentUtilizationFee[str(bandPaymentOption)] = routerUtilizationFee                    
	                    
	                    # bandwidthCostParameterList.append(routerInitialResFee)
	                    # bandwidthCostParameterList.append(routerUtilizationFee)
	                    
	                    # add the decision variables to the effective bandiwdth list
	                    routerEffectiveBandDecVarDict = effectiveBandDecVarDict[str(userIndex)]
	                    contractEffectiveBandDecVarDict = routerEffectiveBandDecVarDict[str(routerIndex)]
	                    paymentEffectiveBandDecVarDict = contractEffectiveBandDecVarDict[str(bandResContractLength)]
	                    effectiveBandDecVarList = paymentEffectiveBandDecVarDict[str(bandPaymentOption)]
	                    
	                    for currentTimeStage in range(timeStage, min(timeLength, timeStage + bandResContractLength)) :
	                        effectiveBandDecVarAtCurrentTimeStage = effectiveBandDecVarList[currentTimeStage]
	                        effectiveBandDecVarAtCurrentTimeStage.append(bandReservation)
	                    
	                bandContractDecVar_res[str(bandResContractLength)] = bandPaymentOptionDecVar_res
	                bandContractDecVar_uti[str(bandResContractLength)] = bandPaymentOptionDecVar_uti
	                bandContractReservationFeeDict[str(bandResContractLength)] = bandPaymentReservationFee
	                bandContractUtilizationFeeDict[str(bandResContractLength)] = bandPaymentUtilizationFee
	            
	            bandOnDemandDecVarName = 'bandOnDemand_t_' + str(timeStage) + 'u_' + str(userIndex) + 'r_' + str(routerIndex)
	            bandOnDemand = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=bandOnDemandDecVarName)
	            
	            bandRouterDecVar_res[str(routerIndex)] = bandContractDecVar_res
	            bandRouterDecVar_uti[str(routerIndex)] = bandContractDecVar_uti
	            bandRouterDecVar_onDemand[str(routerIndex)] = bandOnDemand
	            bandReservationFeeDict[str(routerIndex)] = bandContractReservationFeeDict
	            bandUtilizationFeeDict[str(routerIndex)] = bandContractUtilizationFeeDict
	            
	            # add on demand decision to the list
	            # bandwidthCostDecVarList.append(bandOnDemand)
	            
	            # add on-demand price to the list
	            # bandwidthCostParameterList.append(routerOnDemandFee)
	            
	        
	        bandUserDecVar_res[str(userIndex)] = bandRouterDecVar_res
	        bandUserDecVar_uti[str(userIndex)] = bandRouterDecVar_uti
	        bandUserDecVar_onDemand[str(userIndex)] = bandRouterDecVar_onDemand
	        
	    bandResDecVar.append(bandUserDecVar_res)
	    bandUtilizationDecVar.append(bandUserDecVar_uti)
	    bandOnDemandDecVar.append(bandUserDecVar_onDemand)
	
	# record the cost of using network bandwidth
	bandwidthCostDecVarList = []
	bandwidthCostParameterList = []
	
	for timeStage in range(0, timeLength) :
	    for userIndex in range(0, numOfUsers) :
	        for routerIndex in range(0, numOfRouters) :
	            onDemandRouterPrice = 0
	            for routerContractLength in routerContractList :
	                for routerPayment in routerPaymentList :
	                    # router reservatiuon
	                    bandRes = bandResDecVar[timeStage][str(userIndex)][str(routerIndex)][str(routerContractLength)][str(routerPayment)]
	                    
	                    # effective bandwidth
	                    effectiveBandResList = quicksum(effectiveBandDecVarDict[str(userIndex)][str(routerIndex)][str(routerContractLength)][str(routerPayment)][timeStage])
	                    
	                    # router data
	                    routerTupleData = sortedRouter[str(routerIndex)][str(routerContractLength)][str(routerPayment)]
	                    
	                    # router reservation and utilization fee
	                    routerResFee = routerTupleData.reservationFee
	                    routerUtiFee = routerTupleData.utilizationFee
	                    onDemandRouterPrice = routerTupleData.onDemandFee
	                    
	                    # bandwidth reservation cost
	                    bandwidthCostDecVarList.append(bandRes)
	                    bandwidthCostParameterList.append(routerResFee)
	                    
	                    # bandwidth monthly payment
	                    bandwidthCostDecVarList.append(effectiveBandResList)
	                    bandwidthCostParameterList.append(routerUtiFee)
	                    
	            # router on-demand
	            bandOnDemand = bandOnDemandDecVar[timeStage][str(userIndex)][str(routerIndex)]
	            bandwidthCostDecVarList.append(bandOnDemand)
	            bandwidthCostParameterList.append(onDemandRouterPrice)
	
	print('Bandwidth Cost decision variable complete')
	
	# VM energy
	
	# Power Usage Effectiveness
	valueOfPUE = 1.58
	chargingDischargingEffeciency = 0.88
	energyPriceDict = readEnergyPricingFile()
	sortedEnergyPrice = sortEnergyPrice(energyPriceDict, timeLength)
	
	# the list used to calculate the VM energy consumption
	# the energy consumption of active VMs
	activeVmEnergyConsumptionDecVarList = []
	# the number of active VMs owned by each user
	numOfActiveVmsDecVarList = []
	# the number of VMs turned by each user
	turnedOnVmVarList = []
	# the number of VMs turned off by each user
	turnedOffVmVarList = []
	# the green energy usage of each provider
	greenEnergyUsageDecVarList = []
	# record the energy consumption when a VM is turned on or off
	vmChangeStateEnergyDict = dict()
	# the amount of energy that solar panals supply DC
	solarEnergyToDcDecVarList = []
	# the amount of energy that solar panals charge the battery
	solarEnergyToBatteryDecVarList = []
	# the amount of energy that battery supplies DC
	batteryEnergyToDcDecVarList = []
	# the energy level of a battery at the beginning of each time period
	batteryEnergyLevelDecVarList_beg = []
	# the energy level of a battery at the end of each time period
	batteryEnergyLevelDecVarList_end = []
	
	# equation 4 the cost of energy consumption of active VMs
	for timeStage in range(0, timeLength) :
	    providerActiveVmEnergyConsumptionDecVarDict = dict()
	    providerNumOfActiveVmsDecVarDict = dict()
	    providerTurnedOnVmDecVarDict = dict()
	    providerTurnedOffVmDecVarDict = dict()
	    providerGreenEnergyDecVarDict = dict()
	    providerSolarToDcDecVarDict = dict()
	    providerSolarToBatteryDecVarDict = dict()
	    providerBatteryToDcDecVarDict = dict()
	    providerBatteryEnergyLevelDecVarDict_beg = dict()
	    providerBatteryEnergyLevelDecVarDict_end = dict()
	    for area in providerAreaDict :
	        providerListOfArea = providerAreaDict[area]
	        for provider in providerListOfArea :
	            userActiveVmEnergyConsumptionDecVarDict = dict()
	            userNumOfActiveVmsDecVarDict = dict()
	            userTurnedOnVmDecVarDict = dict()
	            userTurnedOffVmDecVarDict = dict()
	            for userIndex in range(0, numOfUsers) :
	                activeVmEnergyConsumptionDecVarDict = dict()
	                numOfActiveVmsDecVarDict = dict()
	                turnedOnVmDecVarDict = dict()
	                turnedOffVmDecVarDict = dict()
	                for vmTypeIndex in range(0, len(vmTypeList)) :
	                    vmType = vmTypeList[vmTypeIndex]
	                    
	                    
	                    vmDictOfProvider = sortedVmList[str(provider)]
	                    contractDictOfVmType = vmDictOfProvider[str(vmType)]
	                    paymentDictOfContract = contractDictOfVmType[str(vmContractLengthList[0])]
	                    vmData = paymentDictOfContract['NoUpfront']
	                    
	                    vmEnergyConsumption = vmData.energyConsumption
	                    changeStateEnergyConsumption = vmEnergyConsumption * 0.05
	                    
	                    if str(vmType) not in vmChangeStateEnergyDict :
	                        vmChangeStateEnergyDict[str(vmType)] = changeStateEnergyConsumption
	                    
	                    timeProviderUserVmTypeStr = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
	                    
	                    energyConsumptionOfActiveVm = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='energyConsumption_' + timeProviderUserVmTypeStr)
	                    numOfActiveVms = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='numOfActiveVms_' + timeProviderUserVmTypeStr)
	                    numOfTurnedOnVm = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='numOfTurnedOnVms_' + timeProviderUserVmTypeStr)
	                    numOfTurnedOffVm = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='numOfTurnedOffVms_' + timeProviderUserVmTypeStr)
	                    
	                    # store the decision variables in the dictionaries
	                    activeVmEnergyConsumptionDecVarDict[str(vmType)] = energyConsumptionOfActiveVm
	                    numOfActiveVmsDecVarDict[str(vmType)] = numOfActiveVms
	                    turnedOnVmDecVarDict[str(vmType)] = numOfTurnedOnVm
	                    turnedOffVmDecVarDict[str(vmType)] = numOfTurnedOffVm
	                    
	                userActiveVmEnergyConsumptionDecVarDict[str(userIndex)] = activeVmEnergyConsumptionDecVarDict
	                userNumOfActiveVmsDecVarDict[str(userIndex)] = numOfActiveVmsDecVarDict
	                userTurnedOnVmDecVarDict[str(userIndex)] = turnedOnVmDecVarDict
	                userTurnedOffVmDecVarDict[str(userIndex)] = turnedOffVmDecVarDict
	            
	            timeProviderStr = 't_' + str(timeStage) + 'p_' + str(provider)
	            
	            providerGreenEnergyUsage = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='greenEnergyUsage_' + timeProviderStr)
	            solarToDc = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='solarToDc_' + timeProviderStr)
	            solarToBattery = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='solarToBattery_' + timeProviderStr)
	            batteryToDc = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='batteryToDc_' + timeProviderStr)
	            battegyEnergyLevel_beg = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='batteryEnergyLevel_beg_' + timeProviderStr)
	            batteryEnergyLevel_end = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='batteryEnergyLevel_end_' + timeProviderStr)
	            
	            providerActiveVmEnergyConsumptionDecVarDict[str(provider)] = userActiveVmEnergyConsumptionDecVarDict
	            providerNumOfActiveVmsDecVarDict[str(provider)] = userNumOfActiveVmsDecVarDict
	            providerTurnedOnVmDecVarDict[str(provider)] = userTurnedOnVmDecVarDict
	            providerTurnedOffVmDecVarDict[str(provider)] = userTurnedOffVmDecVarDict
	            providerGreenEnergyDecVarDict[str(provider)] = providerGreenEnergyUsage
	            providerSolarToDcDecVarDict[str(provider)] = solarToDc
	            providerSolarToBatteryDecVarDict[str(provider)] = solarToBattery
	            providerBatteryToDcDecVarDict[str(provider)] = batteryToDc
	            providerBatteryEnergyLevelDecVarDict_beg[str(provider)] = battegyEnergyLevel_beg
	            providerBatteryEnergyLevelDecVarDict_end[str(provider)] = batteryEnergyLevel_end
	    
	    activeVmEnergyConsumptionDecVarList.append(providerActiveVmEnergyConsumptionDecVarDict)
	    numOfActiveVmsDecVarList.append(providerNumOfActiveVmsDecVarDict)
	    turnedOnVmVarList.append(providerTurnedOnVmDecVarDict)
	    turnedOffVmVarList.append(providerTurnedOffVmDecVarDict)
	    greenEnergyUsageDecVarList.append(providerGreenEnergyDecVarDict)
	    solarEnergyToDcDecVarList.append(providerSolarToDcDecVarDict)
	    solarEnergyToBatteryDecVarList.append(providerSolarToBatteryDecVarDict)
	    batteryEnergyToDcDecVarList.append(providerBatteryToDcDecVarDict)
	    batteryEnergyLevelDecVarList_beg.append(providerBatteryEnergyLevelDecVarDict_beg)
	    batteryEnergyLevelDecVarList_end.append(providerBatteryEnergyLevelDecVarDict_end)
	                    
	print('VM Energy decision variable complete')
	
	# Network energy
	routerAreaDict = getRouterAreaDict(routerList)
	
	# decision variables
	# the energy consumption of each router
	routerEnergyConsumptionDecVarList = []
	# the statement of each router which is represented as binary bariables
	routerStatusDecVarList = []
	# if a router is turned on in current time period, the value of this variable is gonna be 1
	routerOnDecVarList = []
	# if a router is turned off in current time period, the value of this variable is gonna be 1
	routerOffDecVarList = []
	# the bandwidth usage, which is calculated by the sum of flow of edges directly connected to the router
	routerBandwidthUsageDecVarList = []
	
	# a fully loaded router consume 3.84 KW
	fullyLoadedRouterEnergyConsumption = 3840
	idleRouterEnergyConsumption = 1000
	# assume that switch the state of router is the 5% of fully loaded energy consumption
	routerChangeStateEnergyConsumption = fullyLoadedRouterEnergyConsumption * 0.05
	# assume that the capacity of each router is 1,000 Gbps
	routerCapacity = 100000.0
	    
	# equation 9 the cost of energy consumption of network flow
	for timeStage in range(0, timeLength) :
	    routerEnergyConsumptionDecVarDict = dict()
	    routerStatusDecVarDict = dict()
	    routerOnDecVarDict = dict()
	    routerOffDecVarDict = dict()
	    routerBandwidthUsageDecVarDict = dict()
	    for area in routerAreaDict :
	        areaRouterList = routerAreaDict[area]
	        for router in areaRouterList :
	            routerIndex = router.routerIndex
	            
	            timeRouterStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
	            
	            routerEnergyConsumption = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='routerEnergyConsumption_' + timeRouterStr)
	            
	            routerStatus = model.addVar(vtype=GRB.BINARY, name='RS_' + timeRouterStr)
	            routerOn = model.addVar(vtype=GRB.CONTINUOUS, name='RO_' + timeRouterStr)
	            routerOff = model.addVar(vtype=GRB.CONTINUOUS, name='RF_' + timeRouterStr)
	            
	            routerBandwidthUsage = model.addVar(vtype=GRB.CONTINUOUS, name='routerBandUsage_' + timeRouterStr)
	            
	            routerEnergyConsumptionDecVarDict[str(routerIndex)] = routerEnergyConsumption
	            routerStatusDecVarDict[str(routerIndex)] = routerStatus
	            routerOnDecVarDict[str(routerIndex)] = routerOn
	            routerOffDecVarDict[str(routerIndex)] = routerOff
	            routerBandwidthUsageDecVarDict[str(routerIndex)] = routerBandwidthUsage
	            
	    routerEnergyConsumptionDecVarList.append(routerEnergyConsumptionDecVarDict)
	    routerStatusDecVarList.append(routerStatusDecVarDict)
	    routerOnDecVarList.append(routerOnDecVarDict)
	    routerOffDecVarList.append(routerOffDecVarDict)
	    routerBandwidthUsageDecVarList.append(routerBandwidthUsageDecVarDict)
	
	print('Network Energy decision variable complete')
	
	# network flow decision variables
	edgeList = networkTopology['edges']
	
	edgeFlowDecVarList = []
	
	for timeStage in range(0, timeLength) :
	    edgeFlowDecVarDict = dict()
	    for edgeIndex in range(0, len(edgeList)) :
	        userFlowDecVarDict = dict()
	        for userIndex in range(0, numOfUsers) :
	            timeEdgeUserStr = 't_' + str(timeStage) + 'e_' + str(edgeIndex) + 'u_' + str(userIndex)
	            flow = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='flow_' + timeEdgeUserStr)
	            userFlowDecVarDict[str(userIndex)] = flow
	        edgeFlowDecVarDict[str(edgeIndex)] = userFlowDecVarDict
	    edgeFlowDecVarList.append(edgeFlowDecVarDict)
	
	print('Edge flow decision variable complete')
	
	upfrontCostDecVarList = []
	monthlyCostDecVarList = []
	
	# Upfront cost and monthly payment cost
	for timeStage in range(0, timeLength) :
	    userUpfrontCostDict = dict()
	    userMonthlyCostDict = dict()
	    for userIndex in range(0, numOfUsers) :
	        tuStr = 't_' + str(timeStage) + 'u_' + str(userIndex)
	        
	        upfrontCostDecVar = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="UC_" + tuStr)
	        monthlyCostDecVar = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name='MC_' + tuStr)
	        
	        userUpfrontCostDict[str(userIndex)] = upfrontCostDecVar
	        userMonthlyCostDict[str(userIndex)] = monthlyCostDecVar
	    
	    upfrontCostDecVarList.append(userUpfrontCostDict)
	    monthlyCostDecVarList.append(userMonthlyCostDict)
	
	print('Upfront cost and monthly payment decision variables complete')
	
	# update model
	model.update()
	
	# equation 1 total cost function
	model.setObjective(quicksum([vmCostParameterList[vmCostIndex] * vmCostDecVarList[vmCostIndex] for vmCostIndex in range(0, len(vmCostDecVarList))]) + quicksum([bandwidthCostDecVarList[bandCostItemIndex] * bandwidthCostParameterList[bandCostItemIndex] for bandCostItemIndex in range(0, len(bandwidthCostDecVarList))]) + quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([valueOfPUE * quicksum([activeVmEnergyConsumptionDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyDict[str(vmType)] * turnedOnVmVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyDict[str(vmType)] * turnedOffVmVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] for userIndex in range(0, numOfUsers) for vmType in vmTypeList]) - greenEnergyUsageDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict]) + quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([routerEnergyConsumptionDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOnDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOffDecVarList[timeStage][str(router.routerIndex)] for router in routerAreaDict[area]]) for timeStage in range(0, timeLength) for area in routerAreaDict]), GRB.MINIMIZE)
	
	# The cost of VM usage objective function
	# quicksum([vmCostParameterList[vmCostIndex] * vmCostDecVarList[vmCostIndex] for vmCostIndex in range(0, len(vmCostDecVarList))])
	
	# The cost of bandwidth usage objective function v1
	# quicksum([bandwidthCostDecVarList[index] * bandwidthCostParameterList[index] for index in range(0, len(bandwidthCostDecVarList))]) + quicksum([bandUtilizationFeeDict[str(routerIndex)][str(routerContract)][str(routerPayment)] * effectiveBandDecVarDict[str(userIndex)][str(routerIndex)][str(routerContract)][str(routerPayment)][timeStage] for timeStage in range(0, timeLength) for userIndex in range(0, numOfUsers) for routerIndex in range(0, numOfRouters) for routerContract in routerContractList for routerPayment in routerPaymentList])
	
	# The cost of bandwidth usage objective function v2
	# quicksum([bandwidthCostDecVarList[bandCostItemIndex] * bandwidthCostParameterList[bandCostItemIndex] for bandCostItemIndex in range(0, len(bandwidthCostDecVarList))])
	
	# VM energy objective function
	# quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([valueOfPUE * quicksum([activeVmEnergyConsumptionDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyDict[str(vmType)] * turnedOnVmVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyDict[str(vmType)] * turnedOffVmVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] for userIndex in range(0, numOfUsers) for vmType in vmTypeList]) - greenEnergyUsageDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict])
	
	# network energy objective function
	# quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([routerEnergyConsumptionDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOnDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOffDecVarList[timeStage][str(router.routerIndex)] for router in routerAreaDict[area]]) for timeStage in range(0, timeLength) for area in routerAreaDict])
	
	print('Total cost objective function complete')
	
	# add constraints
	
	# constraint 6 : the total energy consumption of active VMs the product of the energy consumption of each VM type and the number of active VMs
	for timeStage in range(0, timeLength) :
	    # constraint 6
	    providerActiveVmEnergyConsumptionDecVarDict = activeVmEnergyConsumptionDecVarList[timeStage]
	    providerNumOfActiveVmsDecVarDict = numOfActiveVmsDecVarList[timeStage]
	    
	    # constraint 7, 8, 9
	    providerDecVar_uti = vmUtilizationDecVar[timeStage]
	    providerDecVar_onDemand = vmOnDemandDecVar[timeStage]
	    
	    # constraint 8, 9
	    providerTurnedOnVmDecVarDict = turnedOnVmVarList[timeStage]
	    providerTurnedOffVmDecVarDict = turnedOffVmVarList[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        userActiveVmEnergyConsumptionDecVarDict = providerActiveVmEnergyConsumptionDecVarDict[str(provider)]
	        userNumOfActiveVmsDecVarDict = providerNumOfActiveVmsDecVarDict[str(provider)]
	        
	        userDecVar_uti = providerDecVar_uti[str(provider)]
	        userDecVar_onDemand = providerDecVar_onDemand[str(provider)]
	        
	        userTurnedOnVmDecVarDict = providerTurnedOnVmDecVarDict[str(provider)]
	        userTurnedOffVmDecVarDict = providerTurnedOffVmDecVarDict[str(provider)]
	        for userIndex in range(0, numOfUsers) :
	            activeVmEnergyConsumptionDecVarDict = userActiveVmEnergyConsumptionDecVarDict[str(userIndex)]
	            numOfActiveVmsDecVarDict = userNumOfActiveVmsDecVarDict[str(userIndex)]
	            
	            vmDecVar_uti = userDecVar_uti[str(userIndex)]
	            vmDecVar_onDemand = userDecVar_onDemand[str(userIndex)]
	            
	            numOfTurnedOnVmTypeDict = userTurnedOnVmDecVarDict[str(userIndex)]
	            numOfTurnedOffVmTypeDict = userTurnedOffVmDecVarDict[str(userIndex)]
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmTypeIndex]
	                
	                energyConsumptionOfActiveVms = activeVmEnergyConsumptionDecVarDict[str(vmType)]
	                numOfActiveVms = numOfActiveVmsDecVarDict[str(vmType)]
	                
	                vmDictOfProvider = sortedVmList[str(provider)]
	                contractDictOfVmType = vmDictOfProvider[str(vmType)]
	                paymentDictOfContract = contractDictOfVmType[str(vmContractLengthList[0])]
	                vmData = paymentDictOfContract['NoUpfront']
	                
	                energyConsumptionOfVmType = vmData.energyConsumption
	                
	                tpuiStr = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
	                
	                # constraint 6
	                model.addConstr(energyConsumptionOfActiveVms, GRB.EQUAL, numOfActiveVms * energyConsumptionOfVmType, name='c6:' + tpuiStr)
	                
	                # constraint 7
	                vmUtilizationAndOnDemandDecVarList = [vmDecVar_uti[str(vmType)][str(contract)][payment] for contract in vmContractLengthList for payment in vmPaymentList]
	                vmUtilizationAndOnDemandDecVarList.append(vmDecVar_onDemand[str(vmType)])
	                
	                model.addConstr(numOfActiveVms, GRB.EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList), name='c7:' + tpuiStr)
	                
	                # constraint 8 and constraint 9
	                numOfTurnedOnVm = numOfTurnedOnVmTypeDict[str(vmType)]
	                numOfTurnedOffVm = numOfTurnedOffVmTypeDict[str(vmType)]
	                
	                if timeStage == 0 :
	                    previousTimeStageVmUtilizationAndOnDemandDecVarList = []
	                    model.addConstr(numOfTurnedOnVm, GRB.GREATER_EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList), name='c8:' + tpuiStr)
	                    model.addConstr(numOfTurnedOffVm, GRB.GREATER_EQUAL, -1 * quicksum(vmUtilizationAndOnDemandDecVarList), name='c9:' + tpuiStr)
	                else :
	                    previousTimeStageProviderDecVar_uti = vmUtilizationDecVar[timeStage-1]
	                    previousTimeStageProviderDecVar_onDemand = vmOnDemandDecVar[timeStage - 1]
	                    
	                    previousTimeStageUserDecVar_uti = previousTimeStageProviderDecVar_uti[str(provider)]
	                    previousTimeStageUserDecVar_onDemand = previousTimeStageProviderDecVar_onDemand[str(provider)]
	                    
	                    previousTimeStageVmDecVar_uti = previousTimeStageUserDecVar_uti[str(userIndex)]
	                    previousTimeStageVmDecVar_onDemand = previousTimeStageUserDecVar_onDemand[str(userIndex)]
	                    
	                    previousTimeStageUtilizedVmDecVar = previousTimeStageVmDecVar_uti[str(vmType)]
	                    previousTimeStageOnDemandDecVar = previousTimeStageVmDecVar_onDemand[str(vmType)]
	                    
	                    previousTimeStageVmUtilizationAndOnDemandDecVarList = [previousTimeStageUtilizedVmDecVar[str(contract)][str(payment)] for contract in vmContractLengthList for payment in vmPaymentList]
	                    previousTimeStageVmUtilizationAndOnDemandDecVarList.append(previousTimeStageOnDemandDecVar)
	                    
	                    model.addConstr(numOfTurnedOnVm, GRB.GREATER_EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList) - quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList), name='c8:' + tpuiStr)
	                    model.addConstr(numOfTurnedOffVm, GRB.GREATER_EQUAL, quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList) - quicksum(vmUtilizationAndOnDemandDecVarList), name='c9:' + tpuiStr)
	                    
	print('Constraint 6, 7, 8, 9 complete')
	                
	
	# constraint 7 : the number of active VMs is the sum of utlization and on-demand VMs
	'''
	for timeStage in range(0, timeLength) :
	    providerNumOfActiveVmsDecVarDict = numOfActiveVmsDecVarList[timeStage]
	    providerDecVar_uti = vmUtilizationDecVar[timeStage]
	    providerDecVar_onDemand = vmOnDemandDecVar[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        userNumOfActiveVmsDecVarDict = providerNumOfActiveVmsDecVarDict[str(provider)]
	        userDecVar_uti = providerDecVar_uti[str(provider)]
	        userDecVar_onDemand = providerDecVar_onDemand[str(provider)]
	        for userIndex in range(0, numOfUsers) :
	            numOfActiveVmsDecVarDict = userNumOfActiveVmsDecVarDict[str(userIndex)]
	            vmDecVar_uti = userDecVar_uti[str(userIndex)]
	            vmDecVar_onDemand = userDecVar_onDemand[str(userIndex)]
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmTypeIndex]
	                
	                numOfActiveVms = numOfActiveVmsDecVarDict[str(vmType)]
	                
	                contractAndPaymentDecVarList = [vmDecVar_uti[str(vmType)][str(contract)][payment] for contract in vmContractLengthList for payment in vmPaymentList]
	                contractAndPaymentDecVarList.append(vmDecVar_onDemand[str(vmType)])
	                
	                model.addConstr(numOfActiveVms, GRB.EQUAL, quicksum(contractAndPaymentDecVarList))
	'''
	
	# constraint 8 and constraint 9 : VM_On constraint and VM_Off constraint
	'''
	for timeStage in range(0, timeLength) :
	    providerTurnedOnVmDecVarDict = turnedOnVmVarList[timeStage]
	    providerTurnedOffVmDecVarDict = turnedOffVmVarList[timeStage]
	    
	    providerDecVar_uti = vmUtilizationDecVar[timeStage]
	    providerDecVar_onDemand = vmOnDemandDecVar[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        userTurnedOnVmDecVarDict = providerTurnedOnVmDecVarDict[str(provider)]
	        userTurnedOffVmDecVarDict = providerTurnedOffVmDecVarDict[str(provider)]
	        
	        userDecVar_uti = providerDecVar_uti[str(provider)]
	        userDecVar_onDemand = providerDecVar_onDemand[str(provider)]
	        for userIndex in range(0, numOfUsers) :
	            numOfTurnedOnVmTypeDict = userTurnedOnVmDecVarDict[str(userIndex)]
	            numOfTurnedOffVmTypeDict = userTurnedOffVmDecVarDict[str(userIndex)]
	            
	            vmDecVar_uti = userDecVar_uti[str(userIndex)]
	            vmDecVar_onDemand = userDecVar_onDemand[str(userIndex)]
	            
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmTypeIndex]
	                numOfTurnedOnVm = numOfTurnedOnVmTypeDict[str(vmType)]
	                numOfTurnedOffVm = numOfTurnedOffVmTypeDict[str(vmType)]
	                
	                vmUtilizationAndOnDemandDecVarList = [vmDecVar_uti[str(vmType)][str(contract)][str(payment)] for contract in vmContractLengthList for payment in vmPaymentList]
	                vmUtilizationAndOnDemandDecVarList.append(vmDecVar_onDemand[str(vmType)])
	                
	                if timeStage == 0 :
	                    previousTimeStageVmUtilizationAndOnDemandDecVarList = []
	                    model.addConstr(numOfTurnedOnVm, GRB.GREATER_EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList))
	                    model.addConstr(numOfTurnedOffVm, GRB.GREATER_EQUAL, -1 * quicksum(vmUtilizationAndOnDemandDecVarList))
	                else :
	                    previousTimeStageProviderDecVar_uti = vmUtilizationDecVar[timeStage-1]
	                    previousTimeStageProviderDecVar_onDemand = vmOnDemandDecVar[timeStage - 1]
	                    
	                    previousTimeStageUserDecVar_uti = previousTimeStageProviderDecVar_uti[str(provider)]
	                    previousTimeStageUserDecVar_onDemand = previousTimeStageProviderDecVar_onDemand[str(provider)]
	                    
	                    previousTimeStageVmDecVar_uti = previousTimeStageUserDecVar_uti[str(userIndex)]
	                    previousTimeStageVmDecVar_onDemand = previousTimeStageUserDecVar_onDemand[str(userIndex)]
	                    
	                    previousTimeStageUtilizedVmDecVar = previousTimeStageVmDecVar_uti[str(vmType)]
	                    previousTimeStageOnDemandDecVar = previousTimeStageVmDecVar_onDemand[str(vmType)]
	                    
	                    previousTimeStageVmUtilizationAndOnDemandDecVarList = [previousTimeStageUtilizedVmDecVar[str(contract)][str(payment)] for contract in [1, 3] for payment in vmPaymentList]
	                    previousTimeStageVmUtilizationAndOnDemandDecVarList.append(previousTimeStageOnDemandDecVar)
	                    
	                    model.addConstr(numOfTurnedOnVm, GRB.GREATER_EQUAL, quicksum(vmUtilizationAndOnDemandDecVarList) - quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList))
	                    model.addConstr(numOfTurnedOffVm, GRB.GREATER_EQUAL, quicksum(previousTimeStageVmUtilizationAndOnDemandDecVarList) - quicksum(vmUtilizationAndOnDemandDecVarList))
	'''
	
	# constraint 11, 12 : Router_On and Router_Off constraints
	for timeStage in range(0, timeLength) :
	    # constraint 11, 12, 13
	    routerStatusDecVarDict = routerStatusDecVarList[timeStage]
	    # constraint 11, 12
	    routerOnDecVarDict = routerOnDecVarList[timeStage]
	    routerOffDecVarDict = routerOffDecVarList[timeStage]
	    
	    # constraint 13
	    routerEnergyConsumptionDecVarDict = routerEnergyConsumptionDecVarList[timeStage]
	    routerBandwidthUsageDecVarDict = routerBandwidthUsageDecVarList[timeStage]
	    
	    # constraint 14
	    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
	    for router in routerList :
	        routerIndex = router.routerIndex
	        
	        routerStatus = routerStatusDecVarDict[str(routerIndex)]
	        routerOn = routerOnDecVarDict[str(routerIndex)]
	        routerOff = routerOffDecVarDict[str(routerIndex)]
	        
	        routerEnergyConsumption = routerEnergyConsumptionDecVarDict[str(routerIndex)]
	        routerBandwidthUsage = routerBandwidthUsageDecVarDict[str(routerIndex)]
	        
	        trStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
	        
	        # constraint 11, 12
	        if timeStage == 0 :
	            model.addConstr(routerOn, GRB.GREATER_EQUAL, routerStatus, name='c11:' + trStr)
	            model.addConstr(routerOff, GRB.GREATER_EQUAL, -1 * routerStatus, name='c12:' + trStr)
	        else :
	            previousTimeStageRouterStatusDecVarDict = routerStatusDecVarList[timeStage - 1]
	            previousTimeStageRouterStatus = previousTimeStageRouterStatusDecVarDict[str(routerIndex)]
	            
	            model.addConstr(routerOn, GRB.GREATER_EQUAL, routerStatus - previousTimeStageRouterStatus, name='c11:' + trStr)
	            model.addConstr(routerOff, GRB.GREATER_EQUAL, previousTimeStageRouterStatus - routerStatus, name='c12:' + trStr)
	        
	        # constraint 13
	        model.addConstr(routerEnergyConsumption, GRB.EQUAL, routerStatus * idleRouterEnergyConsumption + routerBandwidthUsage / (2 * routerCapacity) * (fullyLoadedRouterEnergyConsumption - idleRouterEnergyConsumption), name='c13:' + trStr)
	        
	        # constraint 14
	        routerDirectlyConnectedInFlowEdges = router.inFlowEdges
	        routerDirectlyConnectedOutFlowEdges = router.outFlowEdges
	        
	        edgeInFlow = []
	        edgeOutFlow = []
	        
	        for edgeIndex in routerDirectlyConnectedInFlowEdges :
	            userFlowDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	            
	            for userIndex in range(0, numOfUsers) :
	                userInFlow = userFlowDecVarDict[str(userIndex)]
	                edgeInFlow.append(userInFlow)
	            
	        for edgeIndex in routerDirectlyConnectedOutFlowEdges :
	            userFlowDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	            
	            for userIndex in range(0, numOfUsers) :
	                userOutFlow = userFlowDecVarDict[str(userIndex)]
	                edgeOutFlow.append(userOutFlow)
	        
	        
	        model.addConstr(routerBandwidthUsage, GRB.EQUAL, quicksum(edgeInFlow) + quicksum(edgeOutFlow), name='c14:' + trStr)
	        
	print('Constraint 11, 12, 13, 14 complete')
	
	# constraint 13 : the energy consumption of a router
	'''
	for timeStage in range(0, timeLength) :
	    routerEnergyConsumptionDecVarDict = routerEnergyConsumptionDecVarList[timeStage]
	    routerStatusDecVarDict = routerStatusDecVarList[timeStage]
	    routerBandwidthUsageDecVarDict = routerBandwidthUsageDecVarList[timeStage]
	    for router in routerList :
	        routerIndex = router.routerIndex
	        routerEnergyConsumption = routerEnergyConsumptionDecVarDict[str(routerIndex)]
	        routerStatus = routerStatusDecVarDict[str(routerIndex)]
	        routerBandwidthUsage = routerBandwidthUsageDecVarDict[str(routerIndex)]
	        
	        model.addConstr(routerEnergyConsumption, GRB.EQUAL, routerStatus * idleRouterEnergyConsumption + routerBandwidthUsage / (2 * routerCapacity) * (fullyLoadedRouterEnergyConsumption - idleRouterEnergyConsumption))
	'''
	    
	# constraint 14 : the bandwidth usage constraint
	'''
	for timeStage in range(0, timeLength) :
	    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
	    routerBandwidthUsageDecVarDict = routerBandwidthUsageDecVarList[timeStage]
	    for router in routerList :
	        routerIndex = router.routerIndex
	        routerDirectlyConnectedEdges = router.edges
	        routerBandwidthUsage = routerBandwidthUsageDecVarDict[str(routerIndex)]
	        
	        edgeInFlow = []
	        edgeOutFlow = []
	        
	        for edgeIndex in routerDirectlyConnectedEdges :
	            flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	            
	            flowInDecVarDict = flowTypeDecVarDict['in']
	            flowOutDecVarDict = flowTypeDecVarDict['out']
	            
	            for userIndex in range(0, numOfUsers) :
	                userFlowIn = flowInDecVarDict[str(userIndex)]
	                userFlowOut = flowOutDecVarDict[str(userIndex)]
	                
	                edgeInFlow.append(userFlowIn)
	                edgeOutFlow.append(userFlowOut)
	        
	        model.addConstr(routerBandwidthUsage, GRB.EQUAL, quicksum(edgeInFlow) + quicksum(edgeOutFlow))
	'''
	
	# constraint 15 : effective VM reservation
	for timeStage in range(0, timeLength) :
	    providerVmDecVar_uti = vmUtilizationDecVar[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        userVmDecVar_uti = providerVmDecVar_uti[str(provider)]
	        for userIndex in range(0, numOfUsers) :
	            vmTypeDecVar_uti = userVmDecVar_uti[str(userIndex)]
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmTypeIndex]
	                contractVmDecVar_uti = vmTypeDecVar_uti[str(vmType)]
	                for contractLength in vmContractLengthList :
	                    paymentVmDecVar_uti = contractVmDecVar_uti[str(contractLength)]
	                    for payment in vmPaymentList :
	                        vmUtilization = paymentVmDecVar_uti[str(payment)]
	                        
	                        userEffectiveVmResDecVarDict = effectiveVmResDecVarDict[str(provider)]
	                        vmTypeEffectiveVmResDecVarDict = userEffectiveVmResDecVarDict[str(userIndex)]
	                        contractEffectiveVmResDecVarDict = vmTypeEffectiveVmResDecVarDict[str(vmType)]
	                        paymentEffectiveVmResDecVarDict = contractEffectiveVmResDecVarDict[str(contractLength)]
	                        effectiveVmResDecVarList = paymentEffectiveVmResDecVarDict[str(payment)]
	                        
	                        tupikjStr = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(contractLength) + 'j_' + str(payment)
	                        
	                        model.addConstr(vmUtilization, GRB.LESS_EQUAL, quicksum(effectiveVmResDecVarList[timeStage]), name='c15:' + tupikjStr)
	
	print('Constraint 15 complete')
	
	# constraint 16 : demand constraint
	for timeStage in range(0, timeLength) :
	    userVmDemandDict = vmDemandList[timeStage]
	    for userIndex in range(0, numOfUsers) :
	        vmTypeDemandDict = userVmDemandDict[str(userIndex)]
	        for vmTypeIndex in range(0, len(vmTypeList)) :
	            vmType = vmTypeList[vmTypeIndex]
	            vmDemand = vmTypeDemandDict[str(vmType)]
	            
	            utlizationAndOnDemandVmDecVarList = []
	            
	            for providerIndex in range(0, len(providerList)) :
	                provider = providerList[providerIndex]
	                for contractLength in vmContractLengthList :
	                    for payment in vmPaymentList :
	                        providerVmDecVarDict_uti = vmUtilizationDecVar[timeStage]
	                        userVmDecVarDict_uti = providerVmDecVarDict_uti[str(provider)]
	                        
	                        vmTypeDecVarDict_uti = userVmDecVarDict_uti[str(userIndex)]
	                        
	                        contractDecVarDict_uti = vmTypeDecVarDict_uti[str(vmType)]
	                        
	                        paymentDecVarDict_uti = contractDecVarDict_uti[str(contractLength)]
	                        
	                        utilizationDecVar = paymentDecVarDict_uti[payment]
	                        
	                        utlizationAndOnDemandVmDecVarList.append(utilizationDecVar)
	                
	                providerVmDecVarDict_onDemand = vmOnDemandDecVar[timeStage]
	                userVmDecVarDict_onDemand = providerVmDecVarDict_onDemand[str(provider)]
	                vmTypeDecVarDict_onDemand = userVmDecVarDict_onDemand[str(userIndex)]
	                onDemandDecVar = vmTypeDecVarDict_onDemand[str(vmType)]
	                utlizationAndOnDemandVmDecVarList.append(onDemandDecVar)
	            
	            tuiStr = 't_' + str(timeStage) + 'u_' + str(userIndex) + 'i_' + str(vmType)
	            model.addConstr(quicksum(utlizationAndOnDemandVmDecVarList), GRB.GREATER_EQUAL, vmDemand, name='c16:' + tuiStr)
	
	print('Constraint 16 complete')
	            
	# constraint 17, 18, 19 : cloud provider resource upper bound limit
	cloudProvidersDict = getProviderCapacity(networkTopology['provider'])
	instanceReqDict = getInstanceReqDict(instanceData)
	for timeStage in range(0, timeLength) :
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        cloudProviderObj = cloudProvidersDict[str(provider)]
	        
	        coreLimit = cloudProviderObj.coresLimit
	        storageLimit = cloudProviderObj.storageLimit
	        internalBandLimit = cloudProviderObj.internalBandwidthLimit
	        
	        vmCoreReqList = []
	        vmStorageReqList = []
	        vmInternalBandReqList = []
	        
	        vmTypeUtilizedAndOnDemandDecVarList = []
	        
	        for vmTypeIndex in range(0, len(vmTypeList)) :
	            vmType = vmTypeList[vmTypeIndex]
	            vmObj = instanceReqDict[str(vmType)]
	            
	            vmCoreReq = vmObj.coreReq
	            vmStorageReq = vmObj.storageReq
	            vmInternalBandReq = vmObj.networkReq
	            
	            currentVmTypeUtilizedAndOnDemandDecVarList = []
	            for userIndex in range(0, numOfUsers) :
	                for contractLength in vmContractLengthList :
	                    for payment in vmPaymentList :
	                        providerVmDecVarDict_uti = vmUtilizationDecVar[timeStage]
	                        userVmDecVarDict_uti = providerVmDecVarDict_uti[str(provider)]
	                        vmTypeDecVarDict_uti = userVmDecVarDict_uti[str(userIndex)]
	                        contractDecVarDict_uti = vmTypeDecVarDict_uti[str(vmType)]
	                        paymentDecVarDict_uti = contractDecVarDict_uti[str(contractLength)]
	                        utilizationDecVar = paymentDecVarDict_uti[payment]
	                        
	                        currentVmTypeUtilizedAndOnDemandDecVarList.append(utilizationDecVar)
	                        
	                providerVmDecVarDict_onDemand = vmOnDemandDecVar[timeStage]
	                userVmDecVarDict_onDemand = providerVmDecVarDict_onDemand[str(provider)]
	                vmTypeDecVarDict_onDemand = userVmDecVarDict_onDemand[str(userIndex)]
	                onDemandDecVar = vmTypeDecVarDict_onDemand[str(vmType)]
	                
	                currentVmTypeUtilizedAndOnDemandDecVarList.append(onDemandDecVar)
	            
	            vmCoreReqList.append(vmCoreReq)
	            vmStorageReqList.append(vmStorageReq)
	            vmInternalBandReqList.append(vmInternalBandReq)
	            vmTypeUtilizedAndOnDemandDecVarList.append(currentVmTypeUtilizedAndOnDemandDecVarList)
	        
	        tpStr = 't_' + str(timeStage) + 'p_' + str(provider)
	        
	        # constraint 17 : host constraint
	        model.addConstr(quicksum([vmCoreReqList[vmIndex] * quicksum(vmTypeUtilizedAndOnDemandDecVarList[vmIndex]) for vmIndex in range(0, len(vmCoreReqList))]), GRB.LESS_EQUAL, coreLimit, name='c17:' + tpStr)
	        
	        # constraint 18 : storage constraint
	        model.addConstr(quicksum([vmStorageReqList[vmIndex] * quicksum(vmTypeUtilizedAndOnDemandDecVarList[vmIndex]) for vmIndex in range(0, len(vmStorageReqList))]), GRB.LESS_EQUAL, storageLimit, name='c18:' + tpStr)
	        
	        # constraint 19 : internal bandwidth constraint
	        model.addConstr(quicksum([vmInternalBandReqList[vmIndex] * quicksum(vmTypeUtilizedAndOnDemandDecVarList[vmIndex]) for vmIndex in range(0, len(vmInternalBandReqList))]), GRB.LESS_EQUAL, internalBandLimit, name='c19:' + tpStr)
	
	print('Constraint 17, 18, 19 complete')
	
	# constraint 20, 21 : the number of utilization and on-demand VM are 0 when it is the first time stage
	for providerIndex in range(0, len(providerList)) :
	    provider = providerList[providerIndex]
	    for userIndex in range(0, numOfUsers) :
	        for vmTypeIndex in range(0, len(vmTypeList)) :
	            vmType = vmTypeList[vmTypeIndex]
	            for vmContract in vmContractLengthList :
	                for vmPayment in vmPaymentList :
	                    # utilization
	                    upikjStr = 't_0_p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContract) + 'j_' + str(vmPayment)
	                    
	                    vmUtiDecVar = vmUtilizationDecVar[0][str(provider)][str(userIndex)][str(vmType)][str(vmContract)][str(vmPayment)]
	                    
	                    model.addConstr(vmUtiDecVar, GRB.EQUAL, 0, name='c20:' + upikjStr)
	            # on-demand Vm
	            vmOnDemand = vmOnDemandDecVar[0][str(provider)][str(userIndex)][str(vmType)]
	            upiStr = 't_0_p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
	            model.addConstr(vmOnDemand, GRB.EQUAL, 0, name='c21:' + upiStr)
	
	print('Constraint 20, 21 complete')
	
	# constraint 22 : VM decision variables integer constraint
	for timeStage in range(0, timeLength) :
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        for userIndex in range(0, numOfUsers) :
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                for contractLength in vmContractLengthList :
	                    for payment in vmPaymentList :
	                        providerVmDecVarDict_res = vmResDecVar[timeStage]
	                        providerVmDecVarDict_uti = vmUtilizationDecVar[timeStage]
	                        userVmDecVarDict_res = providerVmDecVarDict_res[str(provider)]
	                        userVmDecVarDict_uti = providerVmDecVarDict_uti[str(provider)]
	                        vmTypeDecVarDict_res = userVmDecVarDict_res[str(userIndex)]
	                        vmTypeDecVarDict_uti = userVmDecVarDict_uti[str(userIndex)]
	                        contractDecVarDict_res = vmTypeDecVarDict_res[str(vmType)]
	                        contractDecVarDict_uti = vmTypeDecVarDict_uti[str(vmType)]
	                        paymentDecVarDict_res = contractDecVarDict_res[str(contractLength)]
	                        paymentDecVarDict_uti = contractDecVarDict_uti[str(contractLength)]
	                        reservationDecVar = paymentDecVarDict_res[str(payment)]
	                        utilizationDecVar = paymentDecVarDict_uti[str(payment)]
	                        
	                        tupikjStr = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(contractLength) + 'j_' + str(payment)
	                        
	                        # constraint 22
	                        model.addConstr(reservationDecVar, GRB.GREATER_EQUAL, 0, name='c22_res:' + tupikjStr)
	                        model.addConstr(utilizationDecVar, GRB.GREATER_EQUAL, 0, name='c22_uti:' + tupikjStr)
	                        
	                providerVmDecVarDict_onDemand = vmOnDemandDecVar[timeStage]
	                userVmDecVarDict_onDemand = providerVmDecVarDict_onDemand[str(provider)]
	                vmTypeDecVarDict_onDemand = userVmDecVarDict_onDemand[str(userIndex)]
	                onDemandDecVar = vmTypeDecVarDict_onDemand[str(vmType)]
	                
	                tupiStr = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
	                model.addConstr(onDemandDecVar, GRB.GREATER_EQUAL, 0, name='c22_on:' + tupiStr)
	
	print('Constraint 22 complete')
	                        
	# constraint 23 : effective bandiwdth
	for userIndex in range(0, numOfUsers) :
	    for router in routerList :
	        routerIndex = router.routerIndex
	        for bandContractLength in routerContractList :
	            for bandPayment in routerPaymentList :
	                for timeStage in range(0, timeLength) :
	                    # effective bandwidth
	                    routerEffectiveBandDecVarDict = effectiveBandDecVarDict[str(userIndex)]
	                    contractEffectiveDecVarDict = routerEffectiveBandDecVarDict[str(routerIndex)]
	                    paymentEffectiveDecVarDict = contractEffectiveDecVarDict[str(bandContractLength)]
	                    effectiveBandDecVarList = paymentEffectiveDecVarDict[str(bandPayment)]
	                    
	                    effectiveBandDecVarAtCurrentTimeStage = effectiveBandDecVarList[timeStage]
	                    
	                    # bandwidth utilization
	                    userBandUtilization = bandUtilizationDecVar[timeStage]
	                    routerBandUtilization = userBandUtilization[str(userIndex)]
	                    contractBandUtilization = routerBandUtilization[str(routerIndex)]
	                    paymentBandUtilization = contractBandUtilization[str(bandContractLength)]
	                    bandUtilization = paymentBandUtilization[str(bandPayment)]
	                    
	                    turlmStr = 't_' + str(timeStage) + 'r_' + str(routerIndex) + 'u_' + str(userIndex) + 'l_' + str(bandContractLength) + 'm_' + str(bandPayment)
	                    
	                    model.addConstr(bandUtilization, GRB.LESS_EQUAL, quicksum(effectiveBandDecVarAtCurrentTimeStage), name='c23:' + turlmStr)
	
	print('Constraint 23 complete')
	
	# constraint 24 : router's bandwidth limit
	for timeStage in range(0, timeLength) :
	    for router in routerList :
	        routerIndex = router.routerIndex
	        bandUtilizationAndOnDemandDecVarList = []
	        
	        routerStatusDecVarDict = routerStatusDecVarList[timeStage]
	        routerStatus = routerStatusDecVarDict[str(routerIndex)]
	        
	        for userIndex in range(0, numOfUsers) :
	            for bandContractLength in routerContractList :
	                for bandPayment in routerPaymentList :
	                    userBandUtilization = bandUtilizationDecVar[timeStage]
	                    
	                    routerBandUtilization = userBandUtilization[str(userIndex)]
	                    
	                    contractBandUtilization = routerBandUtilization[str(routerIndex)]
	                    
	                    paymentBandUtilization = contractBandUtilization[str(bandContractLength)]
	                    
	                    bandUtilization = paymentBandUtilization[str(bandPayment)]
	                    
	                    bandUtilizationAndOnDemandDecVarList.append(bandUtilization)
	                    
	            userBandOnDemand = bandOnDemandDecVar[timeStage]
	            routerBandOnDemand = userBandOnDemand[str(userIndex)]
	            bandOnDemand = routerBandOnDemand[str(routerIndex)]
	            bandUtilizationAndOnDemandDecVarList.append(bandOnDemand)
	        
	        trStr = 't_' + str(timeStage) + 'r_' + str(routerIndex)
	        
	        model.addConstr(quicksum(bandUtilizationAndOnDemandDecVarList), GRB.LESS_EQUAL, routerStatus * routerCapacity, name='c24:' + trStr)
	
	print('Constraint 24 complete')
	
	# constraint 25 : router status initialization
	for router in routerList :
	    routerIndex = router.routerIndex
	    routerStatusDecVarDict = routerStatusDecVarList[0]
	    routerStatus = routerStatusDecVarDict[str(routerIndex)]
	    
	    rStr = 't_0_r' + str(routerIndex)
	    
	    model.addConstr(routerStatus, GRB.EQUAL, 0, name='c25:' + rStr)
	
	print('Constraint 25 complete')
	
	# constraint 26 : the non-negative constraint for bandwidth decision variables
	for timeStage in range(0, timeLength) :
	    userBandDecVarDict_res = bandResDecVar[timeStage]
	    userBandDecVarDict_uti = bandUtilizationDecVar[timeStage]
	    userBandDecVarDict_onDemand = bandOnDemandDecVar[timeStage]
	    for userIndex in range(0, numOfUsers) :
	        routerBandDecVarDict_res = userBandDecVarDict_res[str(userIndex)]
	        routerBandDecVarDict_uti = userBandDecVarDict_uti[str(userIndex)]
	        routerBandDecVarDict_onDemand = userBandDecVarDict_onDemand[str(userIndex)]
	        for router in routerList :
	            routerIndex = router.routerIndex
	            
	            contractBandDecVarDict_res = routerBandDecVarDict_res[str(routerIndex)]
	            contractBandDecVarDict_uti = routerBandDecVarDict_uti[str(routerIndex)]
	            bandDecVar_onDemand = routerBandDecVarDict_onDemand[str(routerIndex)]
	            for bandContractLength in routerContractList :
	                paymentBandDecVarDict_res = contractBandDecVarDict_res[str(bandContractLength)]
	                paymentBandDecVarDict_uti = contractBandDecVarDict_uti[str(bandContractLength)]
	                for bandPayment in routerPaymentList :
	                    bandDecVar_res = paymentBandDecVarDict_res[str(bandPayment)]
	                    bandDecVar_uti = paymentBandDecVarDict_uti[str(bandPayment)]
	                    
	                    turlmStr = 't_' + str(timeStage) + 'r_' + str(routerIndex) + 'u_' + str(userIndex) + 'l_' + str(bandContractLength) + 'm_' + str(bandPayment)
	                    
	                    model.addConstr(bandDecVar_res, GRB.GREATER_EQUAL, 0, name='c26_res:' + turlmStr)
	                    model.addConstr(bandDecVar_uti, GRB.GREATER_EQUAL, 0, name='c26_uti:' + turlmStr)
	            
	            turStr = 't_' + str(timeStage) + 'r_' + str(routerIndex) + 'u_' + str(userIndex)
	            model.addConstr(bandDecVar_onDemand, GRB.GREATER_EQUAL, 0, name='c26_on:' + turStr)
	
	print('Constraint 26 complete')
	
	# constraint 27 : RS is binary
	
	# constraint 26 : the relationship between the number of active VMs, turned on / off VMs (this constraint has been deleted)
	'''
	for timeStage in range(0, timeLength) :
	    providerNumOfActiveVmsDecVarDict = numOfActiveVmsDecVarList[timeStage]
	    providerNumOfTurnedOnVmsDecVarDict = turnedOnVmVarList[timeStage]
	    providerNumOfTurnedOffVmsDecVarDict = turnedOffVmVarList[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        userNumOfActiveVmsDecVarDict = providerNumOfActiveVmsDecVarDict[str(provider)]
	        userNumOfTurnedOnVmsDecVarDict = providerNumOfTurnedOnVmsDecVarDict[str(provider)]
	        userNumOfTurnedOffVmsDecVarDict = providerNumOfTurnedOffVmsDecVarDict[str(provider)]
	        for userIndex in range(0, numOfUsers) :
	            numOfActiveVmsDecVarDict = userNumOfActiveVmsDecVarDict[str(userIndex)]
	            numOfTurnedOnVmsDecVarDict = userNumOfTurnedOnVmsDecVarDict[str(userIndex)]
	            numOfTurnedOffVmsDecVarDict = userNumOfTurnedOffVmsDecVarDict[str(userIndex)]
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmTypeIndex]
	                numOfActiveVms = numOfActiveVmsDecVarDict[str(vmType)]
	                numOfTurnedOnVms = numOfTurnedOnVmsDecVarDict[str(vmType)]
	                numOfTurnedOffVms = numOfTurnedOffVmsDecVarDict[str(vmType)]
	                
	                if timeStage > 0 :
	                    previousTimeStageProviderNumOfActiveVmsDecVarDict = numOfActiveVmsDecVarList[timeStage - 1]
	                    previousTimeStageUserNumOfActiveVmsDecVarDict = previousTimeStageProviderNumOfActiveVmsDecVarDict[str(provider)]
	                    previousTimeStageNumOfActiveVmsDecVarDict = previousTimeStageUserNumOfActiveVmsDecVarDict[str(userIndex)]
	                    previousTimeStageNumOfActiveVms = previousTimeStageNumOfActiveVmsDecVarDict[str(vmType)]
	                    
	                    tupiStr = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
	                    
	                    model.addConstr(numOfActiveVms, GRB.EQUAL, previousTimeStageNumOfActiveVms + numOfTurnedOnVms - numOfTurnedOffVms, name='c26:' + tupiStr)
	
	print('Constraint 26 complete')
	'''
	
	# Upfront budget
	upfrontBudget = testValue
	monthlyPaymentBudget = testValue
	
	# constraint 28 : the initial reservation budget calculation of each user at each time period
	# constraint 29 : the resource utilization budget calculation of each user at each time period
	# constraint 30 : upfront cost budget
	# constraint 31 : monthly payment cost budget
	for timeStage in range(0, timeLength) :
	    for userIndex in range(0, numOfUsers) :
	        upfrontCost = upfrontCostDecVarList[timeStage][str(userIndex)]
	        monthlyCost = monthlyCostDecVarList[timeStage][str(userIndex)]
	        
	        # VM
	        vmResList = []
	        vmResFeeList = []
	        # list contains list
	        vmEffectiveResList = []
	        vmUtiFeeList = []
	        
	        for providerIndex in range(0, len(providerList)) :
	            provider = providerList[providerIndex]
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmTypeIndex]
	                for vmContract in vmContractLengthList :
	                    for vmPayment in vmPaymentList :
	                        vmRes = vmResDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContract)][str(vmPayment)]
	                        vmResList.append(vmRes)
	                        
	                        vmResFee = vmReservationFeeDict[str(provider)][str(vmType)][str(vmContract)][str(vmPayment)]
	                        vmResFeeList.append(vmResFee)
	                        
	                        effectiveResList = effectiveVmResDecVarDict[str(provider)][str(userIndex)][str(vmType)][str(vmContract)][str(vmPayment)][timeStage]
	                        vmEffectiveResList.append(effectiveResList)
	                        
	                        vmUtiFee = vmUtilizationFeeDict[str(provider)][str(vmType)][str(vmContract)][str(vmPayment)]
	                        vmUtiFeeList.append(vmUtiFee)
	        
	        # router
	        routerResList = []
	        routerResFeeList = []
	        #list contains list
	        routerEffectiveResList = []
	        routerUtiFeeList = []
	        
	        for routerIndex in range(0, numOfRouters) :
	            for routerContract in routerContractList :
	                for routerPayment in routerPaymentList :
	                    bandRes = bandResDecVar[timeStage][str(userIndex)][str(routerIndex)][str(routerContract)][str(routerPayment)]
	                    routerResList.append(bandRes)
	                    
	                    bandResFee = bandReservationFeeDict[str(routerIndex)][str(routerContract)][str(routerPayment)]
	                    routerResFeeList.append(bandResFee)
	                    
	                    effectiveBandResList = effectiveBandDecVarDict[str(userIndex)][str(routerIndex)][str(routerContract)][str(routerPayment)][timeStage]
	                    routerEffectiveResList.append(effectiveBandResList)
	                    
	                    routerUtiFee = bandUtilizationFeeDict[str(routerIndex)][str(routerContract)][str(routerPayment)]
	                    routerUtiFeeList.append(routerUtiFee)
	        
	        # constraint 28
	        tuStr = 't_' + str(timeStage) + 'u_' + str(userIndex)
	        model.addConstr(upfrontCost, GRB.EQUAL, quicksum([vmResList[vmResIndex] * vmResFeeList[vmResIndex] for vmResIndex in range(0, len(vmResList))]) + quicksum([routerResList[routerResIndex] * routerResFeeList[routerResIndex] for routerResIndex in range(0, len(routerResList))]), name='c28:' + tuStr)
	        
	        # constraint 29
	        model.addConstr(monthlyCost, GRB.EQUAL, quicksum(vmUtiFeeList[vmUtiIndex] * quicksum(vmEffectiveResList[vmUtiIndex]) for vmUtiIndex in range(0, len(vmEffectiveResList))) + quicksum([routerUtiFeeList[routerUtiIndex] * quicksum(routerEffectiveResList[routerUtiIndex]) for routerUtiIndex in range(0, len(routerEffectiveResList))]), name='c29:' + tuStr)
	        
	        # constraint 30
	        model.addConstr(upfrontCost, GRB.LESS_EQUAL, upfrontBudget, name='c30:' + tuStr)
	        
	        # constraint 31
	        model.addConstr(monthlyCost, GRB.LESS_EQUAL, monthlyPaymentBudget, name='c31:' + tuStr)
	
	# constraint 32, 33
	# constraint 32 : the amount of produced green energy do not exceed the usage of energy
	for timeStage in range(0, timeLength) :
	    # constraint 32, 33
	    providerGreenEnergyDecVarDict = greenEnergyUsageDecVarList[timeStage]
	    
	    # constraint 33
	    providerSolarEnergyToDcDecVarDict = solarEnergyToDcDecVarList[timeStage]
	    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
	    
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        greenEnergyUsage = providerGreenEnergyDecVarDict[str(provider)]
	        solarEnergyToDc = providerSolarEnergyToDcDecVarDict[str(provider)]
	        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
	        
	        energyConsumptionDecVarList = []
	        energyConsumptionParameterList = []
	        
	        for userIndex in range(0, numOfUsers) :
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmTypeIndex]
	                
	                providerActiveVmEnergyConsumptionDecVarDict = activeVmEnergyConsumptionDecVarList[timeStage]
	                providerTurnedOnVmDecVarDict = turnedOnVmVarList[timeStage]
	                providerTurnedOffVmDecVarDict = turnedOffVmVarList[timeStage]
	                
	                userActiveVmEnergyConsumptionDecVarDict = providerActiveVmEnergyConsumptionDecVarDict[str(provider)]
	                userTurnedOnVmDecVarDict = providerTurnedOnVmDecVarDict[str(provider)]
	                userTurnedOffVmDecVarDict = providerTurnedOffVmDecVarDict[str(provider)]
	                
	                vmTypeActiveVmEnergyConsumptionDecVarDict = userActiveVmEnergyConsumptionDecVarDict[str(userIndex)]
	                vmTypeTurnedOnVmDecVarDict = userTurnedOnVmDecVarDict[str(userIndex)]
	                vmTypeTurnedOffVmDecVarDict = userTurnedOffVmDecVarDict[str(userIndex)]
	                
	                activeVmEnergyConsumptionDecVar = vmTypeActiveVmEnergyConsumptionDecVarDict[str(vmType)]
	                turnedOnVmDecVar = vmTypeTurnedOnVmDecVarDict[str(vmType)]
	                turnedOffVmDecVar = vmTypeTurnedOffVmDecVarDict[str(vmType)]
	                
	                changeStateEnergyConsumption = vmChangeStateEnergyDict[str(vmType)]
	                
	                energyConsumptionDecVarList.extend([activeVmEnergyConsumptionDecVar, turnedOnVmDecVar, turnedOffVmDecVar])
	                energyConsumptionParameterList.extend([1, changeStateEnergyConsumption, changeStateEnergyConsumption])
	        
	        tpStr = 't_' + str(timeStage) + 'p_' + str(provider)
	        
	        # constraint 32
	        model.addConstr(greenEnergyUsage, GRB.LESS_EQUAL, valueOfPUE * quicksum([energyConsumptionDecVarList[index] * energyConsumptionParameterList[index] for index in range(0, len(energyConsumptionDecVarList))]), name='c32:' + tpStr)
	        # constraint 33
	        model.addConstr(greenEnergyUsage, GRB.EQUAL, solarEnergyToDc + chargingDischargingEffeciency * batteryEnergyToDc, name='c33:' + tpStr)
	
	print('Constraint 32, 33 complete')
	
	# constraint 33 : the amount of green energy is the sum of solar panel energy and the battery energy
	'''
	for timeStage in range(0, timeLength) :
	    providerGreenEnergyDecVarDict = greenEnergyUsageDecVarList[timeStage]
	    providerSolarEnergyToDcDecVarDict = solarEnergyToDcDecVarList[timeStage]
	    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
	    
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        greenEnergyUsage = providerGreenEnergyDecVarDict[str(provider)]
	        solarEnergyToDc = providerSolarEnergyToDcDecVarDict[str(provider)]
	        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
	        
	        model.addConstr(greenEnergyUsage, GRB.EQUAL, solarEnergyToDc + chargingDischargingEffeciency * batteryEnergyToDc)
	'''
	        
	# constraint 34 : the sum of energy used to charge the battery and energy directly supply to DC do not exceed the amount of green energy production
	# this is the limit of renewable energy production
	greenEnergyUsageLimitList = getGreenEnergyUsageLimit(timeLength, providerList)
	for timeStage in range(0, timeLength) :
	    providerSolarEnergyToDcDecVarDict = solarEnergyToDcDecVarList[timeStage]
	    providerSolarEnergyToBatteryDecVarDict = solarEnergyToBatteryDecVarList[timeStage]
	    providerGreenEnergyLimitDict = greenEnergyUsageLimitList[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        solarEnergyToDc = providerSolarEnergyToDcDecVarDict[str(provider)]
	        solarEnergyToBattery = providerSolarEnergyToBatteryDecVarDict[str(provider)]
	        greenEnergyLimit = providerGreenEnergyLimitDict[str(provider)]
	        
	        tpStr = 't_' + str(timeStage) + 'p_' + str(provider)
	        
	        model.addConstr(solarEnergyToBattery + solarEnergyToDc, GRB.LESS_EQUAL, greenEnergyLimit, name='c34:' + tpStr)
	
	print('Constraint 34 complete')
	
	# constraint 35 : the usage of green energy do not exceed the amount of produced renewable energy
	for providerIndex in range(0, len(providerList)) :
	    provider = providerList[providerIndex]
	    greenEnergyUsageList = []
	    greenEnergyLimitList = []
	    for timeStage in range(0, timeLength) :
	        providerGreenEnergyUsageDecVarDict = greenEnergyUsageDecVarList[timeStage]
	        providerGreenEnergyLimitDict = greenEnergyUsageLimitList[timeStage]
	        
	        greenEnergyUsage = providerGreenEnergyUsageDecVarDict[str(provider)]
	        greenEnergyLimit = providerGreenEnergyLimitDict[str(provider)]
	        
	        greenEnergyUsageList.append(greenEnergyUsage)
	        greenEnergyLimitList.append(greenEnergyLimit)
	    
	    pStr = 'p_' + str(provider)
	    
	    model.addConstr(quicksum(greenEnergyUsageList), GRB.LESS_EQUAL, quicksum(greenEnergyLimitList), name='c35:' + pStr)
	
	print('Constraint 35 complete')
	
	# constraint 36 : the energy level at the beginning of next time period is the energy level at the end of this time period plus the energy charged to the battery
	for timeStage in range(1, timeLength) :
	    providerBatteryEnergyLevelDecVarDict_beg = batteryEnergyLevelDecVarList_beg[timeStage]
	    providerPreviousTimeBatteryEnergyLevelDecVarDict_end = batteryEnergyLevelDecVarList_end[timeStage - 1]
	    providerPreviousTimeSolarEnergyToBatteryDecVarDict = solarEnergyToBatteryDecVarList[timeStage - 1]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        
	        batteryEnergyLevel_beg = providerBatteryEnergyLevelDecVarDict_beg[str(provider)]
	        previousTimeBatteryEnergyLevel_end = providerPreviousTimeBatteryEnergyLevelDecVarDict_end[str(provider)]
	        previousTimeSolarEnergyToBattery = providerPreviousTimeSolarEnergyToBatteryDecVarDict[str(provider)]
	        
	        tpStr = 't_' + str(timeStage) + 'p_' + str(provider)
	        
	        model.addConstr(batteryEnergyLevel_beg, GRB.EQUAL, previousTimeBatteryEnergyLevel_end + chargingDischargingEffeciency * previousTimeSolarEnergyToBattery, name='c36:' + tpStr)
	
	print('Constraint 36 complete')
	
	# constraint 37 : the energy supplied from battery to DC is the gap between the energy level at the beginning and the end
	for timeStage in range(0, timeLength) :
	    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
	    providerBatteryEnergyLevelDecVarDict_beg = batteryEnergyLevelDecVarList_beg[timeStage]
	    providerBatteryEnergyLevelDecVarDict_end = batteryEnergyLevelDecVarList_end[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        
	        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
	        batteryEnergyLevel_beg = providerBatteryEnergyLevelDecVarDict_beg[str(provider)]
	        batteryEnergyLevel_end = providerBatteryEnergyLevelDecVarDict_end[str(provider)]
	        
	        tpStr = 't_' + str(timeStage) + 'p_' + str(provider)
	        
	        model.addConstr(batteryEnergyToDc, GRB.EQUAL, batteryEnergyLevel_beg - batteryEnergyLevel_end, name='c37:' + tpStr)
	
	print('Constraint 37 complete')
	
	# constraint 38 : the energy that the battery can supply do not exceed the energy level of this battery at the beginning
	for timeStage in range(0, timeLength) :
	    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
	    providerBatteryEnergyLevelDecVarDict_beg = batteryEnergyLevelDecVarList_beg[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        
	        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
	        batteryEnergyLevel_beg = providerBatteryEnergyLevelDecVarDict_beg[str(provider)]
	        
	        tpStr = 't_' + str(timeStage) + 'p_' + str(provider)
	        
	        model.addConstr(batteryEnergyToDc, GRB.LESS_EQUAL, batteryEnergyLevel_beg, name='c38:' + tpStr)
	
	print('Constraint 38 complete')
	
	# constraint 39, 40 : bettery energy level limit
	batteryEnergyCapacity = 1486
	for timeStage in range(0, timeLength) :
	    providerBatteryEnergyLevelDecVarDict_beg = batteryEnergyLevelDecVarList_beg[timeStage]
	    providerBatteryEnergyLevelDecVarDict_end = batteryEnergyLevelDecVarList_end[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        
	        batteryEnergyLevel_beg = providerBatteryEnergyLevelDecVarDict_beg[str(provider)]
	        batteryEnergyLevel_end = providerBatteryEnergyLevelDecVarDict_end[str(provider)]
	        
	        tpStr = 't_' + str(timeStage) + 'p_' + str(provider)
	        
	        model.addConstr(batteryEnergyLevel_beg, GRB.LESS_EQUAL, batteryEnergyCapacity, name='c39:' + tpStr)
	        model.addConstr(batteryEnergyLevel_end, GRB.LESS_EQUAL, batteryEnergyCapacity, name='c40:' + tpStr)
	
	print('Constraint 39, 40 complete')
	
	# constraint 41, 42 : the limit of battery charging and discharging
	# assume that the c rate of the battery is 73 Ah permodule and there are 5 modules in a battery
	chargingDischargingLimit = 73 * 5
	for timeStage in range(0, timeLength) :
	    providerSolarEnergyToBatteryDecVarDict = solarEnergyToBatteryDecVarList[timeStage]
	    providerBatteryEnergyToDcDecVarDict = batteryEnergyToDcDecVarList[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        
	        solarEnergyToBattery = providerSolarEnergyToBatteryDecVarDict[str(provider)]
	        batteryEnergyToDc = providerBatteryEnergyToDcDecVarDict[str(provider)]
	        
	        tpStr = 't_' + str(timeStage) + 'p_' + str(provider)
	        
	        # constraint 36
	        model.addConstr(solarEnergyToBattery, GRB.LESS_EQUAL, chargingDischargingLimit, name='c41:' + tpStr)
	        # constraint 37
	        model.addConstr(batteryEnergyToDc, GRB.LESS_EQUAL, chargingDischargingLimit, name='c42:' + tpStr)
	
	print('Constraint 41, 42 complete')
	
	# constraint 43, 44, 45 : initialize the battery energy level and theenergy that can supplied by the battery
	for providerIndex in range(0, len(providerList)) :
	    provider = providerList[providerIndex]
	    
	    batteryEnergyToDc = batteryEnergyToDcDecVarList[0][str(provider)]
	    batteryEnergyLevel_beg = batteryEnergyLevelDecVarList_beg[0][str(provider)]
	    batteryEnergyLevel_end = batteryEnergyLevelDecVarList_end[0][str(provider)]
	    
	    pStr = 't_0p_' + str(provider)
	    
	    # constraint 43
	    model.addConstr(batteryEnergyToDc, GRB.EQUAL, 0, name='c43:' + pStr)
	    # constraint 44
	    model.addConstr(batteryEnergyLevel_beg, GRB.EQUAL, 0, name='c44:' + pStr)
	    # constraint 45
	    model.addConstr(batteryEnergyLevel_end, GRB.EQUAL, 0, name='c45:' + pStr)
	
	print('Constraint 43, 44, 45 complete')
	
	# constraint 46 : the flow entering a router is equal to the flow leaving a router
	for timeStage in range(0, timeLength) :
	    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
	    for router in routerList :
	        routerIndex = router.routerIndex
	        routerDirectlyConnectedInFlowEdges = router.inFlowEdges
	        routerDirectlyConnectedOutFlowEdges = router.outFlowEdges        
	        
	        for userIndex in range(0, numOfUsers) :
	            flowInDecVarList = []
	            flowOutDecVarList = []
	            
	            for edgeIndex in routerDirectlyConnectedInFlowEdges :
	                userFlowDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	                inFlow = userFlowDecVarDict[str(userIndex)]
	                flowInDecVarList.append(inFlow)
	            
	            for edgeIndex in routerDirectlyConnectedOutFlowEdges :
	                userFlowDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	                outFlow = userFlowDecVarDict[str(userIndex)]
	                flowOutDecVarList.append(outFlow)
	            
	            turStr = 't_' + str(timeStage) + 'r_' + str(routerIndex) + 'u_' + str(userIndex)
	            model.addConstr(quicksum(flowInDecVarList), GRB.EQUAL, quicksum(flowOutDecVarList), name='c46:' + turStr)
	
	print('Constraint 46 complete')
	
	# constraint 47 : the sum of flow leaving a router is the sum of utilization and on-demand bandwidth
	for timeStage in range(0, timeLength) :
	    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
	    for router in routerList :
	        routerIndex = router.routerIndex
	        routerDirectlyConnectedOutFlowEdges = router.outFlowEdges
	        
	        for userIndex in range(0, numOfUsers) :
	            outFlowDecVarList = []
	            
	            for edgeIndex in routerDirectlyConnectedOutFlowEdges :
	                edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
	                flowTypeDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	                flowDecVar = flowTypeDecVarDict[str(userIndex)]
	                outFlowDecVarList.append(flowDecVar)
	            
	            utilizationAndOnDemandBandDecVarList = []
	            for bandContractLength in routerContractList :
	                for bandPayment in routerPaymentList :
	                    userBandUtilizationDecVarDict = bandUtilizationDecVar[timeStage]
	                    routerBandUtilizationDecVarDict = userBandUtilizationDecVarDict[str(userIndex)]
	                    contractBandUtilizationDecVarDict = routerBandUtilizationDecVarDict[str(routerIndex)]
	                    paymentBandUtilizationDecVarDict = contractBandUtilizationDecVarDict[str(bandContractLength)]
	                    bandUtilization = paymentBandUtilizationDecVarDict[str(bandPayment)]
	                    
	                    utilizationAndOnDemandBandDecVarList.append(bandUtilization)
	                
	            userBandOnDemandDecVarDict = bandOnDemandDecVar[timeStage]
	            routerBandOnDemandDecVarDict = userBandOnDemandDecVarDict[str(userIndex)]
	            onDemandBand = routerBandOnDemandDecVarDict[str(routerIndex)]
	            utilizationAndOnDemandBandDecVarList.append(onDemandBand)
	            
	            turStr = 't_' + str(timeStage) + 'r_' + str(routerIndex) + 'u_' + str(userIndex)
	            
	            model.addConstr(quicksum(outFlowDecVarList), GRB.EQUAL, quicksum(utilizationAndOnDemandBandDecVarList), name='c47:' + turStr)
	
	print('Constraint 47 complete')
	
	# constraint 48 : the bandwidth requirement of VMs in a provider should be satisfied
	outboundBandReqDict = getOutboundBandwidthRequirement(instanceData)
	for timeStage in range(0, timeLength) :
	    providerVmDecVarDict_uti = vmUtilizationDecVar[timeStage]
	    providerVmDecVarDict_onDemand = vmOnDemandDecVar[timeStage]
	    for providerIndex in range(0, len(providerList)) :
	        provider = providerList[providerIndex]
	        cloudProviderObj = cloudProvidersDict[str(provider)]
	        providerDirectlyConnectedEdges = cloudProviderObj.directlyConnectedEdges
	        
	        userVmDecVarDict_uti = providerVmDecVarDict_uti[str(provider)]
	        userVmDecVarDict_onDemand = providerVmDecVarDict_onDemand[str(provider)]
	        for userIndex in range(0, numOfUsers) :
	            vmTypeVmDecVarDict_uti = userVmDecVarDict_uti[str(userIndex)]
	            vmTypeVmDecVarDict_onDemand = userVmDecVarDict_onDemand[str(userIndex)]
	            
	            vmTypeUtilizationAndOnDemandDict = dict()
	            
	            
	            for vmTypeIndex in range(0, len(vmTypeList)) :
	                vmType = vmTypeList[vmTypeIndex]
	                contractVmDecVarDict_uti = vmTypeVmDecVarDict_uti[str(vmType)]
	                onDemandVm = vmTypeVmDecVarDict_onDemand[str(vmType)]
	                
	                utilizationAndOnDemandDecVarList = []
	                
	                for contractIndex in range(0, len(vmContractLengthList)) :
	                    contractLength = vmContractLengthList[contractIndex]
	                    paymentVmDecVarDict = contractVmDecVarDict_uti[str(contractLength)]
	                    for payment in vmPaymentList :
	                        utilizationVm = paymentVmDecVarDict[str(payment)]
	                        utilizationAndOnDemandDecVarList.append(utilizationVm)
	                utilizationAndOnDemandDecVarList.append(onDemandVm)
	                
	                vmTypeUtilizationAndOnDemandDict[str(vmType)] = utilizationAndOnDemandDecVarList
	            
	            providerOutFlowEdgeDecVarList = []
	            for edgeIndex in providerDirectlyConnectedEdges :
	                edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
	                userFlowDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	                flowDecVar = userFlowDecVarDict[str(userIndex)]
	                
	                providerOutFlowEdgeDecVarList.append(flowDecVar)
	            
	            tpuStr = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex)
	            
	            model.addConstr(quicksum(providerOutFlowEdgeDecVarList), GRB.GREATER_EQUAL, quicksum([outboundBandReqDict[str(vmType)] * quicksum(vmTypeUtilizationAndOnDemandDict[str(vmType)]) for vmType in vmTypeList]), name='c48:' + tpuStr)
	
	print('Constraint 48 complete')
	
	# constraint 49 : the bandwidth required by the flow entering a user should be satistied
	userEdgeList = networkTopology['user']
	for timeStage in range(0, timeLength) :
	    for userIndex in range(0, numOfUsers) :
	        userDirectlyConnectedEdges = userEdgeList[userIndex]
	        
	        userFlowInEdgeDecVarList = []
	        
	        for edgeIndex in userDirectlyConnectedEdges :
	            edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
	            userFlowDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	            flowDecVar = userFlowDecVarDict[str(userIndex)]
	            userFlowInEdgeDecVarList.append(flowDecVar)
	        
	        flowOutDecVarListOfProviders = []
	        
	        for providerIndex in range(0, len(providerList)) :
	            provider = providerList[providerIndex]
	            cloudProviderObj = cloudProvidersDict[str(provider)]
	            providerDirectlyConnectedEdges = cloudProviderObj.directlyConnectedEdges
	            
	            for edgeIndex in providerDirectlyConnectedEdges :
	                edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
	                userFlowDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	                flowDecVar = userFlowDecVarDict[str(userIndex)]
	                
	                flowOutDecVarListOfProviders.append(flowDecVar)
	        
	        tuStr = 't_' + str(timeStage) + 'u_' + str(userIndex)
	        
	        model.addConstr(quicksum(userFlowInEdgeDecVarList), GRB.GREATER_EQUAL, quicksum(flowOutDecVarListOfProviders), name='c49:' + tuStr)
	
	print('Constraint 49 complete')
	
	# constraint 50 : the decision variables of flow should greater than 0
	for timeStage in range(0, timeLength) :
	    edgeFlowDecVarDict = edgeFlowDecVarList[timeStage]
	    for edgeIndex in range(0, len(edgeList)) :
	        userFlowDecVarDict = edgeFlowDecVarDict[str(edgeIndex)]
	        for userIndex in range(0, numOfUsers) :
	            flow = userFlowDecVarDict[str(userIndex)]
	            tueStr = 't_' + str(timeStage) + 'e_' + str(edgeIndex) + 'u_' + str(userIndex)
	            model.addConstr(flow, GRB.GREATER_EQUAL, 0, name='c50:' + tueStr)
	print('Constraint 50 complete')
	
	model.write("thesis.lp")
	
	
	model.optimize()
	# model.write('result.sol')
	modelTotalCost = model.ObjVal
	print("Objective function value : ", modelTotalCost)
	modelRuntime = model.Runtime
	print('Gurobi run time : ', str(modelRuntime) + ' (s)')

	modelRunTimeList.append(modelRuntime)
	
	resultColumn = ['Variable Name', 'Value']
	resultData = []
	
	for v in model.getVars() :
	    varName = v.varName
	    varValue = v.x
	    resultData.append([varName, varValue])
	resultData.append(['Cost', modelTotalCost])
	
	writeModelResult('modelResult.csv', resultColumn, resultData)
	# print(GRB.OPTIMAL)

runTimeResultColumn = ['Budget']
runTimeResultColumn.extend([testValue for testValue in testValueList])
writeModelResult('Runtime.csv', runTimeResultColumn, modelRunTimeList)