# Build gurobi sequential model
from readData import *
from subFunctions import *
from gurobipy import *
import random

gurobiErr = False
resultData = []

try :
	timeLength = 50
	# get instance data from csv file, get get the lists of vm types and cloud providers from instance data
	instanceData = getVirtualResource()
	vmDataConfiguration = getVmDataConfiguration(instanceData)
	providerList = vmDataConfiguration['providerList']
	providerAreaDict = getProviderAreaDict(instanceData)
	vmTypeList = vmDataConfiguration['vmTypeList']
	vmContractLengthList = vmDataConfiguration['vmContractLengthList']
	vmPaymentList = vmDataConfiguration['vmPaymentList']
	networkTopology = getNetworkTopology()

	# create a model for VM placement
	vmModel = Model('VM_placement_model')

	# model parameters : log file, stopping criteria
	# log file for VM optimization model
	vmModel.setParam(GRB.Param.LogFile, 'vm_log.txt')
	vmModel.setParam(GRB.Param.MIPGap, 0.00019)

	# get the number of users from network topology
	numOfUsers = len(networkTopology['user'])

	# get the demand of each instacne type for each user at each time period
	vmDemandList = generateVmDemand(timeLength, numOfUsers, vmTypeList)

	# Virtual Machine decision variables

	# VM reservation decision variables
	vmResDecVar = []
	# VM utilization decision variables
	vmUtilizationDecVar = []
	# On-demand VM decision variables
	vmOnDemandDecVar = []
	
	# a dictionary to record the effective VM reservation
	effectiveVmResDecVarDict = dict()
	# initialize the dictionary to record the effective VM reservation
	for provider in providerList :
		userEffectiveVmResDecVarDict = dict()
		for userIndex in range(0, numOfUsers) :
			vmTypeEffectiveVmResDecVarDict = dict()
			for vmType in vmTypeList :
				contractEffectiveVmResDecVarDict = dict()
				for vmContractLength in vmContractLengthList :
					paymentEffectiveVmResDecVarDict = dict()
					for vmPayment in vmPaymentList :
						effectiveVmReservationList = [[] for _ in range(0, timeLength)]
						paymentEffectiveVmResDecVarDict[str(vmPayment)] = effectiveVmReservationList
					contractEffectiveVmResDecVarDict[str(vmContractLength)] = paymentEffectiveVmResDecVarDict
				vmTypeEffectiveVmResDecVarDict[str(vmType)] = contractEffectiveVmResDecVarDict
			userEffectiveVmResDecVarDict[str(userIndex)] = vmTypeEffectiveVmResDecVarDict
		effectiveVmResDecVarDict[str(provider)] = userEffectiveVmResDecVarDict

	# declare decision variables for equation 2 : VM cost
	for timeStage in range(0, timeLength) :
		providerVmDecVarDict_res = dict()
		providerVmDecVarDict_uti = dict()
		providerVmDecVarDict_onDemand = dict()

		for provider in providerList :
			userVmDecVarDict_res = dict()
			userVmDecVarDict_uti = dict()
			userVmDecVarDict_onDemand = dict()
			for userIndex in range(0, numOfUsers) :
				vmTypeDecVarDict_res = dict()
				vmTypeDecVarDict_uti = dict()
				vmTypeDecVarDict_onDemand = dict()
				for vmType in vmTypeList :
					vmContractDecVarDict_res = dict()
					vmContractDecVarDict_uti = dict()
					
					for vmContractLength in vmContractLengthList :
						vmPaymentDecVarDict_res = dict()
						vmPaymentDecVarDict_uti = dict()
						for vmPayment in vmPaymentList :
							vmResUtiDecVarIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_p_' + str(provider) + '_i_' + str(vmType) + '_k_' + str(vmContractLength) + '_j_' + str(vmPayment)
							decVar_res = vmModel.addVar(vtype=GRB.INTEGER, name='vmRes' + vmResUtiDecVarIndex)
							decVar_uti = vmModel.addVar(vtype=GRB.INTEGER, name='vmUti' + vmResUtiDecVarIndex)

							# store decision variabls
							vmPaymentDecVarDict_res[str(vmPayment)] = decVar_res
							vmPaymentDecVarDict_uti[str(vmPayment)] = decVar_uti

							# store the reservation decision variable in effective reservation dictionary
							for vmResEffectiveTimeStage in range(timeStage, min(timeStage + vmContractLength, timeLength)) :
								effectiveVmList = effectiveVmResDecVarDict[str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)][vmResEffectiveTimeStage]
								effectiveVmList.append(decVar_res)

						vmContractDecVarDict_res[str(vmContractLength)] = vmPaymentDecVarDict_res
						vmContractDecVarDict_uti[str(vmContractLength)] = vmPaymentDecVarDict_uti

					vmOndemandIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_p_' + str(provider) + '_i_' + str(vmType)
					decVar_onDemand = vmModel.addVar(vtype=GRB.INTEGER, name = 'vmOnDemand' + vmOndemandIndex)

					vmTypeDecVarDict_res[str(vmType)] = vmContractDecVarDict_res
					vmTypeDecVarDict_uti[str(vmType)] = vmContractDecVarDict_uti
					vmTypeDecVarDict_onDemand[str(vmType)] = decVar_onDemand

				userVmDecVarDict_res[str(userIndex)] = vmTypeDecVarDict_res
				userVmDecVarDict_uti[str(userIndex)] = vmTypeDecVarDict_uti
				userVmDecVarDict_onDemand[str(userIndex)] = vmTypeDecVarDict_onDemand

			providerVmDecVarDict_res[str(provider)] = userVmDecVarDict_res
			providerVmDecVarDict_uti[str(provider)] = userVmDecVarDict_uti
			providerVmDecVarDict_onDemand[str(provider)] = userVmDecVarDict_onDemand

		vmResDecVar.append(providerVmDecVarDict_res)
		vmUtilizationDecVar.append(providerVmDecVarDict_uti)
		vmOnDemandDecVar.append(providerVmDecVarDict_onDemand)

	# sort the instance data according to provider, vm type, vm contract and vm payment option for calculating the cost of using VM
	sortedVmList = sortVM(instanceData, providerList, vmTypeList, vmContractLengthList, vmPaymentList)

	# get storage and bandwidth price of each provider
	storageAndBandPrice = getCostOfStorageAndBandwidth()

	# build VM cost array
	vmCostDecVarList = []
	vmCostParameterList = []
	for timeStage in range(0, timeLength) :
		for provider in providerList :
			for userIndex in range(0, numOfUsers) :
				for vmType in vmTypeList :
					vmOnDemandCost = 0
					for vmContractLength in vmContractLengthList :
						for vmPayment in vmPaymentList :
							vmDecVar_res = vmResDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]
							vmDecVar_uti = vmUtilizationDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]

							instance = sortedVmList[str(provider)][str(vmType)][str(vmContractLength)][str(vmPayment)]

							vmResFee = instance.resFee
							vmUtiFee = instance.utilizeFee
							vmOnDemandFee = instance.onDemandFee
							storageReq = instance.storageReq
							bandReq = instance.networkReq

							# VM reservation cost
							vmCostDecVarList.append(vmDecVar_res)
							vmCostParameterList.append(vmResFee)

							# VM utilization cost
							effectiveVmReservationList = effectiveVmResDecVarDict[str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)][timeStage]
							vmCostDecVarList.append(quicksum(effectiveVmReservationList))
							vmCostParameterList.append(vmResFee)

							# the cost of storage and bandwidth used by reserved instance
							utilizationStorageAndBandCost = storageReq * storageAndBandPrice[str(provider)]['storage'] + bandReq * storageAndBandPrice[str(provider)]['bandwidth']
							vmCostDecVarList.append(vmDecVar_uti)
							vmCostParameterList.append(utilizationStorageAndBandCost)

							vmOnDemandCost = vmOnDemandFee + storageReq * storageAndBandPrice[str(provider)]['storage'] + bandReq * storageAndBandPrice[str(provider)]['bandwidth']

					vmDecVar_onDemand = vmOnDemandDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)]
					vmCostDecVarList.append(vmDecVar_onDemand)
					vmCostParameterList.append(vmOnDemandCost)
	print('VM decision variables complete')

	# VM energy cost

	# Power Usage Effectiveness
	valueOfPUE = 1.58
	chargingDischargingEffeciency = 0.88
	energyPriceDict = readEnergyPricingFile()
	sortedEnergyPrice = sortEnergyPrice(energyPriceDict, timeLength)

	# parameters used in VM energy cost
	# the energy cnosumption when a VM is turned on or off is 5% of its active energy consumption
	changeStateEnergyPercentage = 0.05
	# record the energy consumption parameter of VM types
	vmEnergyConsumptionDict = dict()
	# record the parameter of energy consumption used to turn on or off a VM
	vmChangeStateEnergyConsumptionDict = dict()	

	# decision variables used in VM energy cost
	# energy consumption of active VMs
	energyConsumptionOfActiveVMsDecVarList = []
	# the number of active VMs
	activeVMsDecVarList = []
	# the number of turned on VMs
	turnedOnVMsDecVarList = []
	# the number of turned off VMs
	turnedOffVMsDecVarList = []
	# the usage of green energy
	greenEnergyDecVarList = []

	for timeStage in range(0, timeLength) :
		provider_energyConsumptionOfActiveVMsDecVarDict = dict()
		provider_activeVMsDecVarDict = dict()
		provider_turnedOnVMsDecVarDict = dict()
		provider_turnedOffVMsDecVarDict = dict()
		provider_greenEnergyDecVarDict = dict()
		for area in providerAreaDict :
			areaProviderList = providerAreaDict[area]
			for provider in areaProviderList :
				user_energyConsumptionOfActiveVMsDecVarDict = dict()
				user_activeVMsDecVarDict = dict()
				user_turnedOnVMsDecVarDict = dict()
				user_turnedOffVMsDecVarDict = dict()
				for userIndex in range(0, numOfUsers) :
					vmType_energyConsumptionOfActiveVMsDecVarDict = dict()
					vmType_activeVMsDecVarDict = dict()
					vmType_turnedOnVMsDecVarDict = dict()
					vmType_turnedOffVMsDecVarDict = dict()
					for vmType in vmTypeList :
						decVarIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_p_' + str(provider) + '_i_' + str(vmType)

						energyConsumptionOfActiveVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='energyConsumption' + decVarIndex)
						activeVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='numOfActiveVms' + decVarIndex)
						turnedOnVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='numOfTurnedOnVms' + decVarIndex)
						turnedOffVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='numOfTurnedOffVms' + decVarIndex)

						vmData = sortedVmList[str(provider)][str(vmType)][str(vmContractLengthList[0][str(vmPaymentList[0])])]
						energyConsumptionOfVM = vmData.energyConsumption
						changeStateEnergyConsumptionOfVM = energyConsumptionOfVM * changeStateEnergyPercentage

						if vmType not in vmEnergyConsumptionDict :
							vmEnergyConsumptionDict[str(vmType)] = energyConsumptionOfVM
							vmChangeStateEnergyConsumptionDict[str(vmType)] = changeStateEnergyConsumptionOfVM

						vmType_energyConsumptionOfActiveVMsDecVarDict[str(vmType)] = energyConsumptionOfActiveVMs
						vmType_activeVMsDecVarDict[str(vmType)] = activeVMs
						vmType_turnedOnVMsDecVarDict[str(vmType)] = turnedOnVMs
						vmType_turnedOffVMsDecVarDict[str(vmType)] = turnedOffVMs

					user_energyConsumptionOfActiveVMsDecVarDict[str(userIndex)] = vmType_energyConsumptionOfActiveVMsDecVarDict 
					user_activeVMsDecVarDict[str(userIndex)] = vmType_activeVMsDecVarDict
					user_turnedOnVMsDecVarDict[str(userIndex)] = vmType_turnedOnVMsDecVarDict
					user_turnedOffVMsDecVarDict[str(userIndex)] = vmType_turnedOffVMsDecVarDict

				provider_energyConsumptionOfActiveVMsDecVarDict[str(provider)] = user_energyConsumptionOfActiveVMsDecVarDict
				provider_activeVMsDecVarDict[str(provider)] = user_activeVMsDecVarDict
				provider_turnedOnVMsDecVarDict[str(provider)] = user_turnedOnVMsDecVarDict
				provider_turnedOffVMsDecVarDict[str(provider)] = user_turnedOffVMsDecVarDict

				tpDecVarIndex = '_t_' + str(timeStage) + '_p_' + str(provider)
				greenEnergyUsage = vmModel.addVar(vtype=GRB.CONTINUOUS, name='greenEnergy' + tpDecVarIndex)
				provider_greenEnergyDecVarDict[str(provider)] = greenEnergyUsage

		energyConsumptionOfActiveVMsDecVarList.append(provider_energyConsumptionOfActiveVMsDecVarDict)
		activeVMsDecVarList.append(provider_activeVMsDecVarDict)
		turnedOnVMsDecVarList.append(provider_turnedOnVMsDecVarDict)
		turnedOffVMsDecVarList.append(provider_turnedOffVMsDecVarDict)
		greenEnergyDecVarList.append(provider_greenEnergyDecVarDict)

	print('VM energy cost decision variables complete')

	vmModel.update()

	vmModel.setObjective(quicksum([vmCostDecVarList[itemIndex] * vmCostParameterList[itemIndex] for itemIndex in range(0, len(vmCostDecVarList))]) + quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([valueOfPUE * quicksum([activeVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOnVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOffVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] for userIndex in range(numOfUsers) for vmType in vmTypeList]) - greenEnergyDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict]), GRB.MINIMIZE)

	# VM cost objective function
	# quicksum([vmCostDecVarList[itemIndex] * vmCostParameterList[itemIndex] for itemIndex in range(0, len(vmCostDecVarList))])

	# VM energy cost objective function
	# quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([valueOfPUE * quicksum([activeVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOnVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOffVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] for userIndex in range(numOfUsers) for vmType in vmTypeList]) - greenEnergyDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict])

	print('Objective function of VM complete')

	# constraint 6 : the energy consumption of active VMs
	for timeStage in range(0, timeLength) :
		for provider in providerList :
			for userIndex in range(0, numOfUsers) :
				for vmType in vmTypeList :
					energyConsumptionOfActiveVMs = energyConsumptionOfActiveVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)]
					activeVMs = activeVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)]
					energyConsumptionOfVM = vmEnergyConsumptionDict[str(vmType)]

					constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider) + '_u_' + str(userIndex) + '_i_' + str(vmType)

					vmModel.addConstr(energyConsumptionOfActiveVMs, GRB.EQUAL, activeVMs * energyConsumptionOfVM, name='c6:' + constrIndex)

	print('Constraint 6 complete')

	# constraint 7 : the number of active VMs
	for timeStage in range(0, timeLength) :
		for provider in providerList :
			for userIndex in range(0, numOfUsers) :
				for vmType in vmTypeList :
					activeVMs = activeVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)]

					vmUtiAndOndemandDecVarList = []

					for vmContractLength in vmContractLengthList :
						for vmPayment in vmPaymentList :
							vmDecVar_uti = vmUtilizationDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]
							vmUtiAndOndemandDecVarList.append(vmDecVar_uti)

					vmDecVar_onDemand = vmOnDemandDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)]
					vmUtiAndOndemandDecVarList.append(vmDecVar_onDemand)

					constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider) + '_u_' + str(userIndex) + '_i_' + str(vmType)

					vmModel.addConstr(activeVMs, GRB.EQUAL, quicksum(vmUtiAndOndemandDecVarList), name='c7:' + constrIndex)
	print('Constraint 7 complete')

	# constraint 8, 9 : turned on / off VMs
	for timeStage in range(1, timeLength) :
		for provider in providerList :
			for userIndex in range(0, numOfUsers) :
				for vmType in vmTypeList :
					# VM decision variables of current time period
					vmUtiAndOndemandDecVarList_currentTimeStage = []
					# VM decision variables of previous time period
					vmUtiAndOndemandDecVarList_previousTimeStage = []

					for vmContractLength in vmContractLengthList :
						for vmPayment in vmPaymentList : 
							vmUtiAndOndemandDecVarList_currentTimeStage.append(vmUtilizationDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)])
							vmUtiAndOndemandDecVarList_previousTimeStage.append(vmUtilizationDecVar[timeStage - 1][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)])

					vmUtiAndOndemandDecVarList_currentTimeStage.append(vmOnDemandDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)])
					vmUtiAndOndemandDecVarList_previousTimeStage.append(vmOnDemandDecVar[timeStage - 1][str(provider)][str(userIndex)][str(vmType)])

					# number of turned on and off VM
					numOfTurnedOnVms = turnedOnVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)]
					numOfTurnedOffVms = turnedOffVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)]

					constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider) + '_u_' + str(userIndex) + '_i_' + str(vmType)

					vmModel.addConstr(numOfTurnedOnVms, GRB.GREATER_EQUAL, quicksum(vmUtiAndOndemandDecVarList_currentTimeStage) - quicksum(vmUtiAndOndemandDecVarList_previousTimeStage), name='c8:' + constrIndex)
					vmModel.addConstr(numOfTurnedOffVms, GRB.GREATER_EQUAL, quicksum(vmUtiAndOndemandDecVarList_previousTimeStage) - quicksum(vmUtiAndOndemandDecVarList_currentTimeStage), name='c9:' + constrIndex)
	print('Constraint 8, 9 complete')

	# constraint 15 : effective VM reservation
	for timeStage in range(0, timeLength) :
		for provider in providerList :
			for userIndex in range(0, numOfUsers) :
				for vmType in vmTypeList :
					for vmContractLength in vmContractLengthList :
						for vmPayment in vmPaymentList :
							vmDecVar_uti = vmUtilizationDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]
							effectiveVmReservationList = effectiveVmResDecVarDict[str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)][timeStage]

							constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider) + '_u_' + str(userIndex) + '_i_' + str(vmType) + '_k_' + str(vmContractLength) + '_j_' + str(vmPayment)

							vmModel.addConstr(vmDecVar_uti, GRB.LESS_EQUAL, quicksum(effectiveVmReservationList), name='c15:' + constrIndex)
	print('Contraint 15 complete')

	# constraint 16 : the demand of instances should be satisfied by reserved and on-demand instances
	# VM demand at each time stage
	vmDemandList = generateVmDemand(timeLength, numOfUsers, vmTypeList)
	for timeStage in range(0, timeLength) :
		for userIndex in range(0, numOfUsers) :
			for vmType in vmTypeList :
				vmDemand = vmDemandList[timeStage][str(userIndex)][str(vmType)]

				vmDecVarListOfUser = []

				for provider in providerList :
					for vmContractLength in vmContractLengthList :
						for vmPayment in vmPaymentList :
							vmDecVar_uti = vmUtilizationDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]
							vmDecVarListOfUser.append(vmDecVar_uti)
					# ondemand
					vmDecVar_onDemand = vmOnDemandDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)]
					vmDecVarListOfUser.append(vmDecVar_onDemand)

				constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_i_' + str(vmType)

				vmModel.addConstr(quicksum(vmDecVarListOfUser), GRB.GREATER_EQUAL, vmDemand, name='c16:' + constrIndex)
	print('Constraint 16 complete')

	# constraint 17, 18, 19 : the constraints of provider capacities
	cloudProvidersDict = getProviderCapacity(networkTopology['provider'])
	for provider in providerList :
		cloudProvider = cloudProvidersDict[str(provider)]
		coreLimit = cloudProvider.coresLimit
		storageLimit = cloudProvider.storageLimit
		networkLimit = cloudProvider.internalBandwidthLimit
		for timeStage in range(0, timeLength) :
			# the VM decision variables (including reserved and on-demand instances) of all users in a provider
			vmDecVarListInProvider = []
			vmCoreReqList = []
			vmStorageReqList = []
			vmNetworkReqList = []
			# resources usage
			for vmType in vmTypeList :
				vm = sortedVmList[str(provider)][str(vmType)][str(vmContractLengthList[0])][str(vmPaymentList[0])]
				vmCoreReq = vm.coreReq
				vmStorageReq = vm.storageReq
				vmNetworkReq = vm.networkReq

				vmDecVarInProvider = []

				for userIndex in range(0, numOfUsers) :
					for vmContractLength in vmContractLengthList :
						for vmPayment in vmPaymentList :
							vmDecVar_uti = vmUtilizationDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]
							vmDecVarInProvider.append(vmDecVar_uti)
					vmDecVar_onDemand = vmOnDemandDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)]
					vmDecVarInProvider.append(vmDecVar_onDemand)

				vmDecVarListInProvider.append(quicksum(vmDecVarInProvider))
				vmCoreReqList.append(vmCoreReq)
				vmStorageReqList.append(vmStorageReq)
				vmNetworkReqList.append(vmNetworkReq)
			
			constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider)
			vmModel.addConstr(quicksum([vmCoreReqList[itemIndex] * vmDecVarListInProvider[itemIndex] for itemIndex in range(0, len(vmDecVarListInProvider))]), GRB.LESS_EQUAL, coreLimit, name='c17:' + constrIndex)
			vmModel.addConstr(quicksum([vmStorageReqList[itemIndex] * vmDecVarListInProvider[itemIndex] for itemIndex in range(0, len(vmDecVarListInProvider))]), GRB.LESS_EQUAL, storageLimit, name='c18:' + constrIndex)
			vmModel.addConstr(quicksum([vmNetworkReqList[itemIndex] * vmDecVarListInProvider[itemIndex] for itemIndex in range(0, len(vmDecVarListInProvider))]), GRB.LESS_EQUAL, networkLimit, name='c19:' + constrIndex)
	print('Constraint 17, 18, 19 complete')

	# constraint 20, 21 : VM initialization
	for provider in providerList :
		for userIndex in range(0, numOfUsers) :
			for vmType in vmTypeList :
				for vmContractLength in vmContractLengthList :
					for vmPayment in vmPaymentList :
						vmDecVar_uti = vmUtilizationDecVar[0][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]
						constrIndex = '_p_' + str(provider) + '_u_' + str(userIndex) + '_i_' + str(vmType) + '_k_' + str(vmContractLength) + '_j_' + str(vmPayment)
						vmModel.addConstr(vmDecVar_uti, GRB.EQUAL, 0, name='c20:' + constrIndex)
				vmDecVar_onDemand = vmOnDemandDecVar[0][str(provider)][str(userIndex)][str(vmType)]
				constrIndex = '_p_' + str(provider) + '_u_' + str(userIndex) + '_i_' + str(vmType)
				vmModel.addConstr(vmDecVar_onDemand, GRB.EQUAL, 0, name='c21:' + constrIndex)
	print('Contraint 20, 21 complete')

	# constraint 22 : VM decision variables integer constraints
	for timeStage in range(0, timeLength) :
		for provider in providerList :
			for userIndex in range(0, numOfUsers) :
				for vmType in vmTypeList :
					for vmContractLength in vmContractLengthList :
						for vmPayment in vmPaymentList :
							vmDecVar_res = vmResDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]
							vmDecVar_uti = vmUtilizationDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]

							constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider) + '_u_' + str(userIndex) + '_i_' + str(vmType) + '_k_' + str(vmContractLength) + '_j_' + str(vmPayment)

							vmModel.addConstr(vmDecVar_res, GRB.GREATER_EQUAL, 0, name='c22_res:' + constrIndex)
							vmModel.addConstr(vmDecVar_uti, GRB.GREATER_EQUAL, 0, name='c22_uti:' + constrIndex)

					vmDecVar_onDemand = vmOnDemandDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)]
					constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider) + '_u_' + str(userIndex) + '_i_' + str(vmType)
					vmModel.addConstr(vmDecVar_onDemand, GRB.GREATER_EQUAL, 0, name='c22_onDemand:' + constrIndex)
	print('Contraint 22 complete')

	



					





































