# Build gurobi sequential model
from readData import *
from subFunctions import *
from gurobipy import *
import random

gurobiErr = False
vmModelResultData = []

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
	sortedVmDict = sortVM(instanceData, providerList, vmTypeList, vmContractLengthList, vmPaymentList)

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

							instance = sortedVmDict[str(provider)][str(vmType)][str(vmContractLength)][str(vmPayment)]

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
	# the energy that solar panels supply to DC
	solarEnergyToDcDecVarList = []
	# the energy that solar panels charge to the batteries
	solarEnergyToBatteryDecVarList = []
	# the energy that the batteries supply to DC
	batteryEnergyToDcDecVarList = []
	# the energy level of batteries at the beginning of time periods
	batteryEnergyLevelDecVarList_beg = []
	# the energy level of batteries at the end of time periods
	batteryEnergyLevelDecVarList_end = []

	for timeStage in range(0, timeLength) :
		provider_energyConsumptionOfActiveVMsDecVarDict = dict()
		provider_activeVMsDecVarDict = dict()
		provider_turnedOnVMsDecVarDict = dict()
		provider_turnedOffVMsDecVarDict = dict()
		provider_greenEnergyDecVarDict = dict()
		provider_solarEnergyToDcDecVarDict = dict()
		provider_solarEnergyToBatteryDecVarDict = dict()
		provider_batteryEnergyToDcDecVarDict = dict()
		provider_batteryEnergyLevelDecVarDict_beg = dict()
		provider_batteryEnergyLevelDecVarDict_end = dict()
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

						vmData = sortedVmDict[str(provider)][str(vmType)][str(vmContractLengthList[0][str(vmPaymentList[0])])]
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
				solarEnergyToDc = vmModel.addVar(vtype=GRB.CONTINUOUS, name='SED' + tpDecVarIndex)
				solarEnergyToBattery = vmModel.addVar(vtype=GRB.CONTINUOUS, name='SEB' + tpDecVarIndex)
				batteryEnergyToDc = vmModel.addVar(vtype=GRB.CONTINUOUS, name='BED' + tpDecVarIndex)
				batteryEnergyLevelDecVar_beg = vmModel.addVar(vtype=GRB.CONTINUOUS, name='BatteryEnergyLevel_beg' + tpDecVarIndex)
				batteryEnergyLevelDecVar_end = vmModel.addVar(vtype=GRB.CONTINUOUS, name='BatteryEnergyLevel_end' + tpDecVarIndex)

				provider_greenEnergyDecVarDict[str(provider)] = greenEnergyUsage
				provider_solarEnergyToDcDecVarDict[str(provider)] = solarEnergyToDc
				provider_solarEnergyToBatteryDecVarDict[str(provider)] = solarEnergyToBattery
				provider_batteryEnergyToDcDecVarDict[str(provider)] = batteryEnergyToDc
				provider_batteryEnergyLevelDecVarDict_beg[str(provider)] = batteryEnergyLevelDecVar_beg
				provider_batteryEnergyLevelDecVarDict_end[str(provider)] = batteryEnergyLevelDecVar_end

		energyConsumptionOfActiveVMsDecVarList.append(provider_energyConsumptionOfActiveVMsDecVarDict)
		activeVMsDecVarList.append(provider_activeVMsDecVarDict)
		turnedOnVMsDecVarList.append(provider_turnedOnVMsDecVarDict)
		turnedOffVMsDecVarList.append(provider_turnedOffVMsDecVarDict)
		greenEnergyDecVarList.append(provider_greenEnergyDecVarDict)
		solarEnergyToDcDecVarList.append(provider_solarEnergyToDcDecVarDict)
		solarEnergyToBatteryDecVarList.append(provider_solarEnergyToBatteryDecVarDict)
		batteryEnergyToDcDecVarList.append(provider_batteryEnergyToDcDecVarDict)
		batteryEnergyLevelDecVarList_beg.append(provider_batteryEnergyLevelDecVarDict_beg)
		batteryEnergyLevelDecVarList_end.append(provider_batteryEnergyLevelDecVarDict_end)

	print('VM energy cost decision variables complete')

	# Upfront payment budget and monthly payment budget
	vmUpfrontPaymentCostDecVarList = []
	vmMonthlyPaymentCostDecVarList = []
	for timeStage in range(0, timeLength) :
		userUpfrontPaymentCostDecVarDict = dict()
		userMonthlyPaymentCostDecVarDict = dict()
		for userIndex in range(0, numOfUsers) :
			decVarIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex)
			vmUpfrontPaymentCostDecVar = vmModel.addVar(vtype=GRB.CONTINUOUS, name='UC_VM' + decVarIndex)
			vmMonthlyPaymentCostDecVar = vmModel.addVar(vtype=GRB.CONTINUOUS, name='MC_VM' + decVarIndex)

			userUpfrontPaymentCostDecVarDict[str(userIndex)] = vmUpfrontPaymentCostDecVar
			userMonthlyPaymentCostDecVarDict[str(userIndex)] = vmMonthlyPaymentCostDecVar

		vmUpfrontPaymentCostDecVarList.append(userUpfrontPaymentCostDecVarDict)
		vmMonthlyPaymentCostDecVarList.append(userMonthlyPaymentCostDecVarDict)
	print('VM upfront payment and monthly payment cost decision variables complete')


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
				vm = sortedVmDict[str(provider)][str(vmType)][str(vmContractLengthList[0])][str(vmPaymentList[0])]
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

	totalBudgetOfUpfrontPayment = 150
	totalBudgetOfMonthlyPayment = 150

	vmBudgetPercentage = 0.5

	# constraint 28 : upfront payment and monthly payment budget
	for timeStage in range(0, timeLength) :
		for userIndex in range(0, numOfUsers) :
			vmUpfrontPaymentCost = vmUpfrontPaymentCostDecVarList[timeStage][str(userIndex)]
			vmMonthlyPaymentCost = vmMonthlyPaymentCostDecVarList[timeStage][str(userIndex)]

			vmUpfrontPaymentParameterList = []
			vmUpfrontPaymentDecVarList = []

			vmMonthlyPaymentParameterList = []
			vmMonthlyPaymentDecVarList = []

			for provider in providerList :
				for vmType in vmTypeList :
					for vmContractLength in vmContractLengthList :
						for vmPayment in vmPaymentList :
							vm = sortedVmDict[str(provider)][str(vmType)][str(vmContractLength)][str(vmPayment)]
							vmResFee = vm.resFee
							vmDecVar_res = vmResDecVar[timeStage][str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)]

							vmUpfrontPaymentParameterList.append(vmResFee)
							vmUpfrontPaymentDecVarList.append(vmDecVar_res)

							vmUtilizeFee = vm.utilizeFee
							effectiveVmReservationList = effectiveVmResDecVarDict[str(provider)][str(userIndex)][str(vmType)][str(vmContractLength)][str(vmPayment)][timeStage]

							vmMonthlyPaymentParameterList.append(vmUtilizeFee)
							vmMonthlyPaymentDecVarList.append(quicksum(effectiveVmReservationList))

			constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex)
			vmModel.addConstr(vmUpfrontPaymentCost, GRB.EQUAL, quicksum([vmUpfrontPaymentParameterList[itemIndex] * vmUpfrontPaymentDecVarList[itemIndex] for itemIndex in range(0, len(vmUpfrontPaymentDecVarList))]), name='c28_VM:' + constrIndex)
			vmModel.addConstr(vmMonthlyPaymentCost, GRB.EQUAL, quicksum([vmMonthlyPaymentParameterList[itemIndex] * vmMonthlyPaymentDecVarList[itemIndex] for itemIndex in range(0, len(vmMonthlyPaymentDecVarList))]), name='c29_VM:' + constrIndex)
	print('Constraint 28, 29 complete')

	# constraint 30, 31
	for timeStage in range(0, timeLength) :
		for userIndex in range(0, numOfUsers) :
			vmUpfrontPaymentCost = vmUpfrontPaymentCostDecVarList[timeStage][str(userIndex)]
			vmMonthlyPaymentCost = vmMonthlyPaymentCostDecVarList[timeStage][str(userIndex)]

			constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex)

			vmModel.addConstr(vmUpfrontPaymentCost, GRB.LESS_EQUAL, totalBudgetOfUpfrontPayment * vmBudgetPercentage, name='c30_VM:' + constrIndex)
			vmModel.addConstr(vmMonthlyPaymentCost, GRB.LESS_EQUAL, totalBudgetOfMonthlyPayment * vmBudgetPercentage, name='c31_VM:' + constrIndex)
	print('Constraint 30, 31 VM complete')

	# constraint 32 : the usage of green energy
	for timeStage in range(0, timeLength) :
		for provider in providerList :
			greenEnergyUsage = greenEnergyDecVarList[timeStage][str(provider)]

			computingEquipmentsEnergyConsumptionDecVarList = []
			computingEquipmentsEnergyConsumptionParameterList = []

			for userIndex in range(0, numOfUsers) :
				for vmType in vmTypeList :
					energyConsumptionOfActiveVMs = energyConsumptionOfActiveVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)]
					numOfTurnedOnVms = turnedOnVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)]
					numOfTurnedOffVms = turnedOffVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)]

					computingEquipmentsEnergyConsumptionDecVarList.append(energyConsumptionOfActiveVMs)
					computingEquipmentsEnergyConsumptionParameterList.append(1)

					computingEquipmentsEnergyConsumptionDecVarList.append(numOfTurnedOnVms)
					computingEquipmentsEnergyConsumptionParameterList.append(vmChangeStateEnergyConsumptionDict[str(vmType)])

					computingEquipmentsEnergyConsumptionDecVarList.append(numOfTurnedOffVms)
					computingEquipmentsEnergyConsumptionParameterList.append(vmChangeStateEnergyConsumptionDict[str(vmType)])

			constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider)
			vmModel.addConstr(greenEnergyUsage, GRB.LESS_EQUAL, quicksum([computingEquipmentsEnergyConsumptionParameterList[itemIndex] * computingEquipmentsEnergyConsumptionDecVarList[itemIndex] for itemIndex in range(0, len(computingEquipmentsEnergyConsumptionDecVarList))]), name='c32:' + constrIndex)
	print('Constraint 32 complete')

	# the green energy usage limit of each provider at each time period
	greenEnergyUsageLimitList = getGreenEnergyUsageLimit(timeLength, providerList)
	# the charging and discharging effeciency of the betteries
	chargingDischargingEffeciency = 0.88
	# constraint 33, 34 : the calculation of green energy usage and the limit of energy that is generated by solar panels
	for timeStage in range(0, timeLength) :
		for provider in providerList :
			greenEnergyUsage = greenEnergyDecVarList[timeStage][str(provider)]
			solarEnergyToDc = solarEnergyToDcDecVarList[timeStage][str(provider)]
			solarEnergyToBattery = solarEnergyToBatteryDecVarList[timeStage][str(provider)]
			batteryEnergyToDc = batteryEnergyToDcDecVarList[timeStage][str(provider)]
			greenEnergyUsageLimit = greenEnergyUsageLimitList[timeStage][str(provider)]

			constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider)

			vmModel.addConstr(greenEnergyUsage, GRB.EQUAL, solarEnergyToDc + chargingDischargingEffeciency * batteryEnergyToDc, name='c33:' + constrIndex)
			vmModel.addConstr(solarEnergyToBattery + solarEnergyToDc, GRB.LESS_EQUAL, greenEnergyUsageLimit, name='c34:' + constrIndex)
	print('Constraint 33, 34 complete')

	# constraint 35 : green energy usage limit
	for provider in providerList :
		totalGreenEnergyUsageList = []
		totalGreenEnergyUsageLimitList = []
		for timeStage in range(0, timeLength) :
			greenEnergyUsage = greenEnergyDecVarList[timeStage][str(provider)]
			greenEnergyUsageLimit = greenEnergyUsageLimitList[timeStage][str(provider)]
			
			totalGreenEnergyUsageList.append(greenEnergyUsage)
			totalGreenEnergyUsageLimitList.append(greenEnergyUsageLimit)

		constrIndex = '_p_' + str(provider)
		vmModel.addConstr(quicksum(totalGreenEnergyUsageList), GRB.LESS_EQUAL, quicksum(totalGreenEnergyUsageLimitList), name='c35:' + constrIndex)
	print('Constraint 35 complete')

	# constraint 36 : the battery energy level calculation
	for timeStage in range(1, timeLength) :
		for provider in providerList :
			currentTimePeriodBatteryEnergyLevelDecVar_beg = batteryEnergyLevelDecVarList_beg[timeStage][str(provider)]
			previousTimePeriodBatteryEnergyLevelDecVar_end = batteryEnergyLevelDecVarList_end[timeStage - 1][str(provider)]
			solarEnergyToBattery = solarEnergyToBatteryDecVarList[timeStage][str(provider)]

			constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider)

			vmModel.addConstr(currentTimePeriodBatteryEnergyLevelDecVar_beg, GRB.EQUAL, previousTimePeriodBatteryEnergyLevelDecVar_end + chargingDischargingEffeciency * solarEnergyToBattery, name='c36:' + constrIndex)
	print('Constraint 36 complete')

	# constraint 37, 38, 39, 40 : the calculation of the energy
	batteryEnergyCapacity = 1486
	chargingDischargingLimit = 73 * 5
	for timeStage in range(0, timeLength) :
		for provider in providerList :
			batteryEnergyToDc = batteryEnergyToDcDecVarList[timeStage][str(provider)]
			solarEnergyToBattery = solarEnergyToBatteryDecVarList[timeStage][str(provider)]
			batteryEnergyLevelDecVar_beg = batteryEnergyLevelDecVarList_beg[timeStage][str(provider)]
			batteryEnergyLevelDecVar_end = batteryEnergyLevelDecVarList_end[timeStage][str(provider)]

			constrIndex = '_t_' + str(timeStage) + '_p_' + str(provider)

			vmModel.addConstr(batteryEnergyToDc, GRB.EQUAL, batteryEnergyLevelDecVar_beg - batteryEnergyLevelDecVar_end, name='c37:' + constrIndex)
			vmModel.addConstr(batteryEnergyToDc, GRB.LESS_EQUAL, batteryEnergyLevelDecVar_beg, name='c38:' + constrIndex)
			vmModel.addConstr(batteryEnergyLevelDecVar_beg, GRB.LESS_EQUAL, batteryEnergyCapacity, name='c39:' + constrIndex)
			vmModel.addConstr(batteryEnergyLevelDecVar_end, GRB.LESS_EQUAL, batteryEnergyCapacity, name='c40:' + constrIndex)
			vmModel.addConstr(solarEnergyToBattery, GRB.LESS_EQUAL, chargingDischargingLimit, name='c41:' + constrIndex)
			vmModel.addConstr(batteryEnergyToDc, GRB.LESS_EQUAL, chargingDischargingLimit, name='c42:' + constrIndex)
	print('Constraint 37, 38, 39, 40, 41, 42 complete')

	# constraint 43, 44, 45
	for provider in providerList :
		batteryEnergyToDc = batteryEnergyToDcDecVarList[0][str(provider)]
		batteryEnergyLevelDecVar_beg = batteryEnergyLevelDecVarList_beg[0][str(provider)]
		batteryEnergyLevelDecVar_end = batteryEnergyLevelDecVarList_end[0][str(provider)]

		constrIndex = '_p_' + str(provider)

		vmModel.addConstr(batteryEnergyToDc, GRB.EQUAL, 0, name='c43:' + constrIndex)
		vmModel.addConstr(batteryEnergyLevelDecVar_beg, GRB.EQUAL, 0, name='c44:' + constrIndex)
		vmModel.addConstr(batteryEnergyLevelDecVar_end, GRB.EQUAL, 0, name='c45:' + constrIndex)
	print('Constraint 43, 44, 45 complete')

	vmModel.write("vmModel.lp")

	model.optimize()
except GurobiError as e :
	gurobiErr = True
	print('Gurobi error')
	for v in vmModel.getVars() :
		varName = v.varName
		varValue = v.x
		vmModelResultData.append([varName, varValue])
finally :
	vmModelTotalCost = vmModel.ObjVal
	print("VM model Objective function value : ", vmModelTotalCost)
	vmModelRuntime = vmModel.Runtime
	print('Gurobi run time : ', vmModelRuntime)
	vmModelMipGap = vmModel.MIPGap

	if gurobiErr == False :
		for v in vmModel.getVars() :
			varName = v.varName
			varValue = v.x
			vmModelResultData.append([varName, varValue])
	vmModelResultData.append(['Cost', vmModelTotalCost])
	vmModelResultData.append(['Runtime', vmModelRuntime])
	vmModelResultData.append(['MIPGap', vmModelMipGap])

	resultColumn = ['Variable Name', 'Value']

	writeModelResult('modelResult.csv', resultColumn, vmModelResultData)







					





































