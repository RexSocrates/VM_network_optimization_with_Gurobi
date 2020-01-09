# Build gurobi sequential model
from readData import *
from subFunctions import *
from gurobipy import *
import random

gurobiErr = False
vmModelResultData = []
vmModelResultDict = dict()
bandModelResultData = []

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
costOfVmUsage = vmModel.addVar(vtype=GRB.CONTINUOUS, name='Cost_VM')

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
						vmResUtiDecVarIndex = '_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
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

				vmOndemandIndex = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
				decVar_onDemand = vmModel.addVar(vtype=GRB.INTEGER, name = 'vmOnDemand_' + vmOndemandIndex)

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
						vmCostParameterList.append(vmUtiFee)

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
costOfVMsEnergyConsumption = vmModel.addVar(vtype=GRB.CONTINUOUS, name='Cost_VE')

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
					decVarIndex = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)

					energyConsumptionOfActiveVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='energyConsumption_' + decVarIndex)
					activeVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='numOfActiveVms_' + decVarIndex)
					turnedOnVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='numOfTurnedOnVms_' + decVarIndex)
					turnedOffVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='numOfTurnedOffVms_' + decVarIndex)

					vmData = sortedVmDict[str(provider)][str(vmType)][str(vmContractLengthList[0])][str(vmPaymentList[0])]
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

			tpDecVarIndex = 't_' + str(timeStage) + 'p_' + str(provider)
			greenEnergyUsage = vmModel.addVar(vtype=GRB.CONTINUOUS, name='greenEnergyUsage_' + tpDecVarIndex)
			solarEnergyToDc = vmModel.addVar(vtype=GRB.CONTINUOUS, name='SED_' + tpDecVarIndex)
			solarEnergyToBattery = vmModel.addVar(vtype=GRB.CONTINUOUS, name='SEB_' + tpDecVarIndex)
			batteryEnergyToDc = vmModel.addVar(vtype=GRB.CONTINUOUS, name='BED_' + tpDecVarIndex)
			batteryEnergyLevelDecVar_beg = vmModel.addVar(vtype=GRB.CONTINUOUS, name='batteryEnergyLevel_beg_' + tpDecVarIndex)
			batteryEnergyLevelDecVar_end = vmModel.addVar(vtype=GRB.CONTINUOUS, name='batteryEnergyLevel_end_' + tpDecVarIndex)

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
		vmUpfrontPaymentCostDecVar = vmModel.addVar(vtype=GRB.CONTINUOUS, name='UC_VM_' + decVarIndex)
		vmMonthlyPaymentCostDecVar = vmModel.addVar(vtype=GRB.CONTINUOUS, name='MC_VM_' + decVarIndex)

		userUpfrontPaymentCostDecVarDict[str(userIndex)] = vmUpfrontPaymentCostDecVar
		userMonthlyPaymentCostDecVarDict[str(userIndex)] = vmMonthlyPaymentCostDecVar

	vmUpfrontPaymentCostDecVarList.append(userUpfrontPaymentCostDecVarDict)
	vmMonthlyPaymentCostDecVarList.append(userMonthlyPaymentCostDecVarDict)
print('VM upfront payment and monthly payment cost decision variables complete')


vmModel.update()

vmModel.setObjective(costOfVmUsage + costOfVMsEnergyConsumption, GRB.MINIMIZE)
# vmModel.setObjective(quicksum([vmCostDecVarList[itemIndex] * vmCostParameterList[itemIndex] for itemIndex in range(0, len(vmCostDecVarList))]) + quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([valueOfPUE * quicksum([activeVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOnVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOffVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] for userIndex in range(numOfUsers) for vmType in vmTypeList]) - greenEnergyDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict]), GRB.MINIMIZE)

# VM cost objective function
# quicksum([vmCostDecVarList[itemIndex] * vmCostParameterList[itemIndex] for itemIndex in range(0, len(vmCostDecVarList))])

# VM energy cost objective function
# quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([valueOfPUE * quicksum([activeVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOnVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOffVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] for userIndex in range(numOfUsers) for vmType in vmTypeList]) - greenEnergyDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict])

print('Objective function of VM complete')

# constraint 2 : the cost of VM usage
vmModel.addConstr(costOfVmUsage, GRB.EQUAL, quicksum([vmCostDecVarList[itemIndex] * vmCostParameterList[itemIndex] for itemIndex in range(0, len(vmCostDecVarList))]), name='c2')

# constraint 5 : VM energy consumption
vmModel.addConstr(costOfVMsEnergyConsumption, GRB.EQUAL, quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([valueOfPUE * quicksum([activeVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOnVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] + vmChangeStateEnergyConsumptionDict[str(vmType)] * turnedOffVMsDecVarList[timeStage][str(provider)][str(userIndex)][str(vmType)] for userIndex in range(numOfUsers) for vmType in vmTypeList]) - greenEnergyDecVarList[timeStage][str(provider)] for provider in providerAreaDict[area]]) for timeStage in range(0, timeLength) for area in providerAreaDict]), name='c5')

print('Cost constraint complete')


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

try :
	vmModel.optimize()
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

	for item in vmModelResultData :
		vmModelResultDict[item[0]] = float(item[1])

	resultColumn = ['Variable Name', 'Value']

	writeModelResult('modelResult_VM.csv', resultColumn, vmModelResultData)

# Bandwidth

# create a model for VM placement
bandModel = Model('Bandwidth_placement_model')

# model parameters : log file, stopping criteria
# log file for VM optimization model
bandModel.setParam(GRB.Param.LogFile, 'bandwidth_log.txt')
bandModel.setParam(GRB.Param.MIPGap, 0.00019)

# get router and bandwidth data
numOfRouters = len(networkTopology['router'])
routerData = getRouterBandwidthPrice(networkTopology)
routerDataConfig = getRouterDataConfiguration(routerData)
bandContractList = routerDataConfig['contractList']
bandPaymentList = routerDataConfig['payment']
sortedRouter = sortRouter(routerData, numOfRouters, bandContractList, bandPaymentList)
routerList = getRouterList(routerData)

# Bandwidth cost decision variables
bandResDecVarList = []
bandUtilizationDecVarList = []
bandOnDemandDecVarList = []

# a dictionary recording the effective bandwidth reservation
effectiveBandDecVarDict = dict()

# initialize the dictionary of effective bandwidth reservation
for userIndex in range(0, numOfUsers) :
	routerEffectiveBandDecVarDict = dict()
	for routerIndex in range(0, numOfRouters) :
		bandContractEffectiveBandDecVarDict = dict()
		for bandContract in bandContractList :
			bandPaymentEffectiveBandDecVarDict = dict()
			for bandPayment in bandPaymentList :
				effectiveBandwidthReservationList = [[] for _ in range(0, timeLength)]
				bandPaymentEffectiveBandDecVarDict[str(bandPayment)] = effectiveBandwidthReservationList
			bandContractEffectiveBandDecVarDict[str(bandContract)] = bandPaymentEffectiveBandDecVarDict
		routerEffectiveBandDecVarDict[str(routerIndex)] = bandContractEffectiveBandDecVarDict
	effectiveBandDecVarDict[str(userIndex)] = routerEffectiveBandDecVarDict

# create bandwidth cost decision variables
costOfBandwidthUsage = bandModel.addVar(vtype=GRB.CONTINUOUS, name='Cost_BW')

for timeStage in range(0, timeLength) :
	userBandDecVarDict_res = dict()
	userBandDecVarDict_uti = dict()
	userBandDecVarDict_onDemand = dict()
	for userIndex in range(0, numOfUsers) :
		routerBandDecVarDict_res = dict()
		routerBandDecVarDict_uti = dict()
		routerBandDecVarDict_onDemand = dict()
		for routerIndex in range(0, numOfRouters) :
			contractBandDecVarDict_res = dict()
			contractBandDecVarDict_uti = dict()

			bandwidthOnDemandFee = 0

			for bandContract in bandContractList :
				paymentBandDecVarDict_res = dict()
				paymentBandDecVarDict_uti = dict()
				for bandPayment in bandPaymentList :
					decVarIndex = str(timeStage) + 'u_' + str(userIndex) + 'r_' + str(routerIndex) + 'l_' + str(bandContract) + 'm_' + str(bandPayment)

					bandDecVar_res = bandModel.addVar(vtype=GRB.CONTINUOUS, name='bandRes_t_' + decVarIndex)
					bandDecVar_uti = bandModel.addVar(vtype=GRB.CONTINUOUS, name='bandUti_t_' + decVarIndex)

					paymentBandDecVarDict_res[str(bandPayment)] = bandDecVar_res
					paymentBandDecVarDict_uti[str(bandPayment)] = bandDecVar_uti

					# add the decision variables to effective bandwidth reservation list
					effectiveBandwidthReservationList = effectiveBandDecVarDict[str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)]

					for effectiveBandwidthReservationTimeStage in range(timeStage, min(timeLength, (timeStage + bandContract))) :
						effectiveBandwidthReservationList[effectiveBandwidthReservationTimeStage].append(bandDecVar_res)

					# add decision variables and parameters to bandwidth cost list
					router = sortedRouter[str(routerIndex)][str(bandContract)][str(bandPayment)]
					bandwidthResFee = router.reservationFee
					bandwidthUtiFee = router.utilizationFee
					bandwidthOnDemandFee = router.onDemandFee

				contractBandDecVarDict_res[str(bandContract)] = paymentBandDecVarDict_res
				contractBandDecVarDict_uti[str(bandContract)] = paymentBandDecVarDict_uti

			decVarIndex = 't_' + str(timeStage) + 'u_' + str(userIndex) + 'r_' + str(routerIndex)
			bandDecVar_onDemand = bandModel.addVar(vtype=GRB.CONTINUOUS, name = 'bandOnDemand_' + decVarIndex)

			routerBandDecVarDict_res[str(routerIndex)] = contractBandDecVarDict_res
			routerBandDecVarDict_uti[str(routerIndex)] = contractBandDecVarDict_uti
			routerBandDecVarDict_onDemand[str(routerIndex)] = bandDecVar_onDemand

		userBandDecVarDict_res[str(userIndex)] = routerBandDecVarDict_res
		userBandDecVarDict_uti[str(userIndex)] = routerBandDecVarDict_uti
		userBandDecVarDict_onDemand[str(userIndex)] = routerBandDecVarDict_onDemand

	bandResDecVarList.append(userBandDecVarDict_res)
	bandUtilizationDecVarList.append(userBandDecVarDict_uti)
	bandOnDemandDecVarList.append(userBandDecVarDict_onDemand)

# calculate the cost of bandwidth usage
bandwidthCostParameterList = []
bandwidthCostDecVarList = []
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		for routerIndex in range(0, numOfRouters) :
			onDemandBandwidthFee = 0
			for bandContract in bandContractList :
				for bancPayment in bandPaymentList :
					bandDecVar_res = bandResDecVarList[timeStage][str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)]
					bandDecVar_uti = bandUtilizationDecVarList[timeStage][str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)]

					router = sortedRouter[str(routerIndex)][str(bandContract)][str(bandPayment)]
					bandReservationFee = router.reservationFee
					bandUtilizationFee = router.utilizationFee
					onDemandBandwidthFee = router.onDemandFee

					effectiveBandwidthReservationDecVarList = effectiveBandDecVarDict[str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)][timeStage]

					bandwidthCostParameterList.append(bandReservationFee)
					bandwidthCostDecVarList.append(bandDecVar_res)

					bandwidthCostParameterList.append(bandUtilizationFee)
					bandwidthCostDecVarList.append(quicksum(effectiveBandwidthReservationDecVarList))

			bandDecVar_onDemand = bandOnDemandDecVarList[timeStage][str(userIndex)][str(routerIndex)]

			bandwidthCostParameterList.append(onDemandBandwidthFee)
			bandwidthCostDecVarList.append(bandDecVar_onDemand)

# Network energy
routerAreaDict = getRouterAreaDict(routerList)
# a fully loaded router consume 3.84 KW
fullyLoadedRouterEnergyConsumption = 3840
idleRouterEnergyConsumption = 1000
# assume that switch the state of router is the 5% of fully loaded energy consumption
routerChangeStateEnergyConsumptionPercentage = 0.05
routerChangeStateEnergyConsumption = fullyLoadedRouterEnergyConsumption * routerChangeStateEnergyConsumptionPercentage
# assume that the capacity of each router is 1,000 Gbps
routerCapacity = 100000.0

# router energy consumption
routerEnergyConsumptionDecVarList = []
# the decision variables indicate the status of a router
routerStatusDecVarList = []
# the decision variables indicate turning on a router if the value is 1
routerOnDecVarList = []
# the decision variables indicate turning off a router if the value is 1
routerOffDecVarList = []
# bandwidth usage of each router at each time period
routerBandwidthUsageDecVarList = []

# equation 10 : the cost of network energy consumption
costOfNetworkEnergyConsumption = bandModel.addVar(vtype=GRB.CONTINUOUS, name='Cost_NE')

for timeStage in range(0, timeLength) :
	routerEnergyConsumptionDecVarDict = dict()
	routerStatusDecVarDict = dict()
	routerOnDecVarDict = dict()
	routerOffDecVarDict = dict()
	routerBandwidthUsageDecVarDict = dict()
	for area in routerAreaDict :
		for router in routerAreaDict[area] :
			routerIndex = router.routerIndex
			decVarIndex = 't_' + str(timeStage) + 'r_' + str(routerIndex)
			
			decVar_routerEnergyConsumption = bandModel.addVar(vtype=GRB.CONTINUOUS, name='routerEnergyConsumption_' + decVarIndex)
			decVar_routerStatus = bandModel.addVar(vtype=GRB.BINARY, name='RS_' + decVarIndex)
			decVar_routerOn = bandModel.addVar(vtype=GRB.BINARY, name='RO_' + decVarIndex)
			decVar_routerOff = bandModel.addVar(vtype=GRB.BINARY, name='RF_' + decVarIndex)
			decVar_routerBandwidthUsage = bandModel.addVar(vtype=GRB.CONTINUOUS, name='routerBandUsage_' + decVarIndex)

			routerEnergyConsumptionDecVarDict[str(routerIndex)] = decVar_routerEnergyConsumption
			routerStatusDecVarDict[str(routerIndex)] = decVar_routerStatus
			routerOnDecVarDict[str(routerIndex)] = decVar_routerOn
			routerOffDecVarDict[str(routerIndex)] = decVar_routerOff
			routerBandwidthUsageDecVarDict[str(routerIndex)] = decVar_routerBandwidthUsage

	routerEnergyConsumptionDecVarList.append(routerEnergyConsumptionDecVarDict)
	routerStatusDecVarList.append(routerStatusDecVarDict)
	routerOnDecVarList.append(routerOnDecVarDict)
	routerOffDecVarList.append(routerOffDecVarDict)
	routerBandwidthUsageDecVarList.append(routerBandwidthUsageDecVarDict)

# network edge flow decision variables
edgeList = networkTopology['edges']

edgeFlowDecVarList = []

for timeStage in range(0, timeLength) :
	edgeFlowDecVarDict = dict()
	for edgeIndex in range(0, len(edgeList)) :
		userEdgeFlowDecVarDict = dict()
		for userIndex in range(0, numOfUsers) :
			decVarIndex = 't_' + str(timeStage) + 'e_' + str(edgeIndex) + 'u_' + str(userIndex)
			decVar_edgeFlow = bandModel.addVar(vtype=GRB.CONTINUOUS, name='flow_' + decVarIndex)
			userEdgeFlowDecVarDict[str(userIndex)] = decVar_edgeFlow
		edgeFlowDecVarDict[str(edgeIndex)] = userEdgeFlowDecVarDict
	edgeFlowDecVarList.append(edgeFlowDecVarDict)

bandwidthUpfrontPaymentCostDecVarList = []
bandwidthMonthlyPaymentCostDecVarList = []

for timeStage in range(0, timeLength) :
	userBandwidthUpfrontPaymentCostDecVarDict = dict()
	userBandwidthMonthlyPaymentCostDecVarDict = dict()
	for userIndex in range(0, numOfUsers) :
		decVarIndex = 't_' + str(timeStage) + 'u_' + str(userIndex)

		bandwidthUpfrontPaymentCost = bandModel.addVar(vtype=GRB.CONTINUOUS, name='UC_Bandwidth_' + decVarIndex)
		bandwidthMonthlyPaymentCost = bandModel.addVar(vtype=GRB.CONTINUOUS, name='MC_Bandwidth_' + decVarIndex)

		userBandwidthUpfrontPaymentCostDecVarDict[str(userIndex)] = bandwidthUpfrontPaymentCost
		userBandwidthMonthlyPaymentCostDecVarDict[str(userIndex)] = bandwidthMonthlyPaymentCost
	
	bandwidthUpfrontPaymentCostDecVarList.append(userBandwidthUpfrontPaymentCostDecVarDict)
	bandwidthMonthlyPaymentCostDecVarList.append(userBandwidthMonthlyPaymentCostDecVarDict)

bandModel.update()

bandModel.setObjective(costOfBandwidthUsage + costOfNetworkEnergyConsumption, GRB.MINIMIZE)
# bandModel.setObjective(quicksum([bandwidthCostParameterList[itemIndex] * bandwidthCostDecVarList[itemIndex] for itemIndex in range(0, len(bandwidthCostParameterList))]) + quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([routerEnergyConsumptionDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOnDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOffDecVarList[timeStage][str(router.routerIndex)] for router in routerAreaDict[area]]) for timeStage in range(0, timeLength) for area in routerAreaDict]), GRB.MINIMIZE)

# Bandwidth cost
# quicksum([bandwidthCostParameterList[itemIndex] * bandwidthCostDecVarList[itemIndex] for itemIndex in range(0, len(bandwidthCostParameterList))])

# Network energy
# quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([routerEnergyConsumptionDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOnDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOffDecVarList[timeStage][str(router.routerIndex)] for router in routerAreaDict[area]]) for timeStage in range(0, timeLength) for area in routerAreaDict])

# constraint 4 : the cost of bandwidth usage
bandModel.addConstr(costOfBandwidthUsage, GRB.EQUAL, quicksum([bandwidthCostParameterList[itemIndex] * bandwidthCostDecVarList[itemIndex] for itemIndex in range(0, len(bandwidthCostParameterList))]), name='c4')

# constraint 10 : the cost of network energy consumption
bandModel.addConstr(costOfNetworkEnergyConsumption, GRB.EQUAL, quicksum([sortedEnergyPrice[timeStage][str(area)] * quicksum([routerEnergyConsumptionDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOnDecVarList[timeStage][str(router.routerIndex)] + routerChangeStateEnergyConsumption * routerOffDecVarList[timeStage][str(router.routerIndex)] for router in routerAreaDict[area]]) for timeStage in range(0, timeLength) for area in routerAreaDict]), name='c10')

# constraint 11, 12 : router on / off indicators
for timeStage in range(1, timeLength) :
	for routerIndex in range(0, numOfRouters) :
		decVar_routerOn = routerOnDecVarList[timeStage][str(routerIndex)]
		decVar_routerOff = routerOffDecVarList[timeStage][str(routerIndex)]
		decVar_routerStatus = routerStatusDecVarList[timeStage][str(routerIndex)]
		decVar_previousTimeStageRouterStatus = routerStatusDecVarList[timeStage - 1][str(routerIndex)]

		constrIndex = '_t_' + str(timeStage) + '_r_' + str(routerIndex)

		bandModel.addConstr(decVar_routerOn, GRB.GREATER_EQUAL, decVar_routerStatus - decVar_previousTimeStageRouterStatus, name='c11:' + constrIndex)
		bandModel.addConstr(decVar_routerOff, GRB.GREATER_EQUAL, decVar_previousTimeStageRouterStatus - decVar_routerStatus, name='c12:' + constrIndex)
print('Constraint 11, 12 complete')

# constraint 13, 14 : the energy consumption and bandwidth usage of each router
for timeStage in range(0, timeLength) :
	for router in routerList :
		routerIndex = router.routerIndex
		decVar_routerEnergyConsumption = routerEnergyConsumptionDecVarList[timeStage][str(routerIndex)]
		decVar_routerStatus = routerStatusDecVarList[timeStage][str(routerIndex)]
		decVar_routerBandwidthUsage = routerBandwidthUsageDecVarList[timeStage][str(routerIndex)]

		constrIndex = '_t_' + str(timeStage) + '_r_' + str(routerIndex)

		bandModel.addConstr(decVar_routerEnergyConsumption, GRB.EQUAL, decVar_routerStatus * idleRouterEnergyConsumption + (decVar_routerBandwidthUsage / (2 * routerCapacity)) * (fullyLoadedRouterEnergyConsumption - idleRouterEnergyConsumption), name='c13:' + constrIndex)

		routerInFlowEdges = router.inFlowEdges
		routerOutFlowEdges = router.outFlowEdges

		routerInFlowEdgesDecVarList = []
		routerOutFlowEdgesDecVarList = []

		for edgeIndex in routerInFlowEdges :
			for userIndex in range(0, numOfUsers) :
				decVar_edgeFlow = edgeFlowDecVarList[timeStage][str(edgeIndex)][str(userIndex)]
				routerInFlowEdgesDecVarList.append(decVar_edgeFlow)

		for edgeIndex in routerOutFlowEdges :
			for userIndex in range(0, numOfUsers) :
				decVar_edgeFlow = edgeFlowDecVarList[timeStage][str(edgeIndex)][str(userIndex)]
				routerOutFlowEdgesDecVarList.append(decVar_edgeFlow)

		bandModel.addConstr(decVar_routerBandwidthUsage, GRB.EQUAL, quicksum(routerInFlowEdgesDecVarList) + quicksum(routerOutFlowEdgesDecVarList), name='c14:' + constrIndex)
print('Constraint 13, 14 complete')

# constraint 23 : the amounf of bandwidth utilization cannot exceed the amount of effective bandwidth reservation
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		for routerIndex in range(0, numOfRouters) :
			for bandContract in bandContractList :
				for bandPayment in bandPaymentList :
					bandDecVar_uti = bandUtilizationDecVarList[timeStage][str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)]
					effectiveBandwidthReservationDecVarList = effectiveBandDecVarDict[str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)][timeStage]

					constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_r_' + str(routerIndex) + '_l_' + str(bandContract) + '_m_' + str(bandPayment)

					bandModel.addConstr(bandDecVar_uti, GRB.LESS_EQUAL, quicksum(effectiveBandwidthReservationDecVarList), name='c23:' + constrIndex)
print('Constraint 23 complete')

# constraint 24 : bandwidth usage cannot exceed the limit
for timeStage in range(0, timeLength) :
	for routerIndex in range(0, numOfRouters) :

		bandwidthUsageDecVarList = []

		for userIndex in range(0, numOfUsers) :
			for bandContract in bandContractList :
				for bandPayment in bandPaymentList :
					bandDecVar_uti = bandUtilizationDecVarList[timeStage][str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)]
					bandwidthUsageDecVarList.append(bandDecVar_uti)
			bandDecVar_onDemand = bandOnDemandDecVarList[timeStage][str(userIndex)][str(routerIndex)]
			bandwidthUsageDecVarList.append(bandDecVar_onDemand)

		decVar_routerStatus = routerStatusDecVarList[timeStage][str(routerIndex)]

		constrIndex = '_t_' + str(timeStage) + '_r_' + str(routerIndex)

		bandModel.addConstr(quicksum(bandwidthUsageDecVarList), GRB.LESS_EQUAL, decVar_routerStatus * routerCapacity, name='c24:' + constrIndex)
print('Constraint 24 complete')

# constraint 25 : the initialization of router status
for routerIndex in range(0, numOfRouters) :
	decVar_routerStatus = routerStatusDecVarList[0][str(routerIndex)]

	constrIndex = '_t_' + str(0) + '_r_' + str(routerIndex)

	bandModel.addConstr(decVar_routerStatus, GRB.EQUAL, 0, name='c25:' + constrIndex)
print('Constraint 25 complete')

# constraint 26 : the decision variables of bandwidth must greater than 0
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		for routerIndex in range(0, numOfRouters) :
			for bandContract in bandContractList :
				for bandPayment in bandPaymentList :
					bandDecVar_res = bandResDecVarList[timeStage][str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)]
					bandDecVar_uti = bandUtilizationDecVarList[timeStage][str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)]

					constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_r_' + str(routerIndex) + '_l_' + str(bandContract) + '_m_' + str(bandPayment)

					bandModel.addConstr(bandDecVar_res, GRB.GREATER_EQUAL, 0, name='c26_res:' + constrIndex)
					bandModel.addConstr(bandDecVar_uti, GRB.GREATER_EQUAL, 0, name='c26_uti:' + constrIndex)

			constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_r_' + str(routerIndex)
			bandDecVar_onDemand = bandOnDemandDecVarList[timeStage][str(userIndex)][str(routerIndex)]

			bandModel.addConstr(bandDecVar_onDemand, GRB.GREATER_EQUAL, 0, name='c26_onDemand:' + constrIndex)
print('Constraint 26 complete')

# constraint 28 : upfront payment budget 
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		bandwidthUpfrontPaymentCostDecVar = bandwidthUpfrontPaymentCostDecVarList[timeStage][str(userIndex)]

		upfrontCostDecVarList = []
		upfrontCostParameterList = []

		for routerIndex in range(0, numOfRouters) :
			for bandContract in bandContractList :
				for bandPayment in bandPaymentList :
					bandDecVar_res = bandResDecVarList[timeStage][str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)]
					bandwidthResFee = sortedRouter[str(routerIndex)][str(bandContract)][str(bandPayment)].reservationFee

					upfrontCostDecVarList.append(bandDecVar_res)
					upfrontCostParameterList.append(bandwidthResFee)

		constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex)

		bandModel.addConstr(bandwidthUpfrontPaymentCostDecVar, GRB.EQUAL, quicksum([upfrontCostDecVarList[itemIndex] * upfrontCostParameterList[itemIndex] for itemIndex in range(0, len(upfrontCostDecVarList))]), name='c28_bandwidth:' + constrIndex)
print('Constraint 28 bandwidth complete')

# constraint 29 : monthly payment budget
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		bandwidthMonthlyPaymentCostDecVar = bandwidthMonthlyPaymentCostDecVarList[timeStage][str(userIndex)]

		monthlyCostDecVarList = []
		monthlyCostParameterList = []

		for routerIndex in range(0, numOfRouters) :
			for bandContract in bandContractList :
				for bandPayment in bandPaymentList :
					effectiveBandwidthReservationList = effectiveBandDecVarDict[str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)][timeStage]
					bandwidthUtiFee = sortedRouter[str(routerIndex)][str(bandContract)][str(bandPayment)].utilizationFee

					monthlyCostDecVarList.append(quicksum(effectiveBandwidthReservationList))
					monthlyCostParameterList.append(bandwidthUtiFee)

		constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex)

		bandModel.addConstr(bandwidthMonthlyPaymentCostDecVar, GRB.EQUAL, quicksum([monthlyCostDecVarList[itemIndex] * monthlyCostParameterList[itemIndex] for itemIndex in range(0, len(monthlyCostDecVarList))]), name='c29:bandwidth:' + constrIndex)
print('Constraint 29 bandwidth complete')


# constraint 30, 31 : the budget limit of bandwidth upfront payment cost and monthly payment cost
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		bandwidthUpfrontPaymentCostDecVar = bandwidthUpfrontPaymentCostDecVarList[timeStage][str(userIndex)]
		bandwidthMonthlyPaymentCostDecVar = bandwidthMonthlyPaymentCostDecVarList[timeStage][str(userIndex)]

		constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex)

		bandModel.addConstr(bandwidthUpfrontPaymentCostDecVar, GRB.LESS_EQUAL, totalBudgetOfUpfrontPayment * (1 - vmBudgetPercentage), name='c30_bandwidth:' + constrIndex)
		bandModel.addConstr(bandwidthMonthlyPaymentCostDecVar, GRB.LESS_EQUAL, totalBudgetOfMonthlyPayment * (1 - vmBudgetPercentage), name='c31_bandwidth:' + constrIndex)
print('Constraint 30, 31 bandwidth complete')

# constraint 46 : flow in = flow out
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		for routerIndex in range(0, numOfRouters) : 
			inFlowDecVarList = []
			outFlowDecVarList = []

			router = sortedRouter[str(routerIndex)][str(bandContractList[0])][str(bandPaymentList[0])]
			inFlowEdges = router.inFlowEdges
			outFlowEdges = router.outFlowEdges

			for edgeIndex in inFlowEdges :
				decVar_edgeFlow = edgeFlowDecVarList[timeStage][str(edgeIndex)][str(userIndex)]
				inFlowDecVarList.append(decVar_edgeFlow)

			for edgeIndex in outFlowEdges :
				decVar_edgeFlow = edgeFlowDecVarList[timeStage][str(edgeIndex)][str(userIndex)]
				outFlowDecVarList.append(decVar_edgeFlow)

			constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_r_' + str(routerIndex)

			bandModel.addConstr(quicksum(outFlowDecVarList), GRB.EQUAL, quicksum(inFlowDecVarList), name='c46:' + constrIndex)
print('Constraint 46 complete')

# constraint 47 : the sum of flow equals the sum of bandwidth utilization and on-demand bandwidth
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		for routerIndex in range(0, numOfRouters) :
			router = sortedRouter[str(routerIndex)][str(bandContractList[0])][str(bandPaymentList[0])]
			outFlowEdges = router.outFlowEdges

			bandwidthUtilizationAndOndemandDecVarList = []

			for bandContract in bandContractList :
				for bandPayment in bandPaymentList :
					bandDecVar_uti = bandUtilizationDecVarList[timeStage][str(userIndex)][str(routerIndex)][str(bandContract)][str(bandPayment)]
					bandwidthUtilizationAndOndemandDecVarList.append(bandDecVar_uti)

			bandDecVar_onDemand = bandOnDemandDecVarList[timeStage][str(userIndex)][str(routerIndex)]

			bandwidthUtilizationAndOndemandDecVarList.append(bandDecVar_onDemand)

			outFlowDecVarList = []

			for edgeIndex in outFlowEdges :
				decVar_edgeFlow = edgeFlowDecVarList[timeStage][str(edgeIndex)][str(userIndex)]
				outFlowDecVarList.append(decVar_edgeFlow)

			constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_r_' + str(routerIndex)

			bandModel.addConstr(quicksum(outFlowDecVarList), GRB.EQUAL, quicksum(bandwidthUtilizationAndOndemandDecVarList), name='c47:' + constrIndex)
print('Constraint 47 complete')

# constraint 48 : the bandwidth usage should satisfy the sum of outbound bandwidth of VM in each provider
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		for provider in providerList :
			outboundBandwidthVarList = []
			outboundBandwidthParameterList = []
			for vmType in vmTypeList :
				utilizationAndOndemandVM = 0
				outboundBandwidthRequirement = 0
				for vmContractLength in vmContractLengthList :
					for vmPayment in vmPaymentList :
						vmResUtiDecVarIndex = '_t_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType) + 'k_' + str(vmContractLength) + 'j_' + str(vmPayment)
						vmDecVarName_uti = 'vmUti' + vmResUtiDecVarIndex

						vm_uti = float(vmModelResultDict[vmDecVarName_uti])
						utilizationAndOndemandVM += vm_uti

						vm = sortedVmDict[str(provider)][str(vmType)][str(vmContractLength)][str(vmPayment)]
						outboundBandwidthRequirement = vm.networkReq
				
				vmOndemandIndex = 't_' + str(timeStage) + 'p_' + str(provider) + 'u_' + str(userIndex) + 'i_' + str(vmType)
				vmDecVarName_onDemand = 'vmOnDemand_' + vmOndemandIndex
				vm_onDemand = float(vmModelResultDict[vmDecVarName_onDemand])
				utilizationAndOndemandVM += vm_onDemand

				outboundBandwidthVarList.append(utilizationAndOndemandVM)
				outboundBandwidthParameterList.append(outboundBandwidthRequirement)

			providerDirectlyConnectedEdges = networkTopology['provider'][str(provider)]

			outFlowDecVarList = []
			for edgeIndex in providerDirectlyConnectedEdges :
				decVar_edgeFlow = edgeFlowDecVarList[timeStage][str(edgeIndex)][str(userIndex)]
				outFlowDecVarList.append(decVar_edgeFlow)

			constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_p_' + str(provider)
			bandModel.addConstr(quicksum(outFlowDecVarList), GRB.GREATER_EQUAL, sum([outboundBandwidthVarList[itemIndex] * outboundBandwidthParameterList[itemIndex] for itemIndex in range(0, len(outboundBandwidthVarList))]), name='c48:' + constrIndex)
print('Constraint 48 complete')

# constraint 49
for timeStage in range(0, timeLength) :
	for userIndex in range(0, numOfUsers) :
		userDirectlyConnectedEdges = networkTopology['user'][userIndex]

		userFlowInDecVarList = []
		for edgeIndex in userDirectlyConnectedEdges :
			decVar_edgeFlow = edgeFlowDecVarList[timeStage][str(edgeIndex)][str(userIndex)]
			userFlowInDecVarList.append(decVar_edgeFlow)

		providerFlowOutDecVarList = []
		for provider in providerList :
			providerDirectlyConnectedEdges = networkTopology['provider'][str(provider)]

			for edgeIndex in providerDirectlyConnectedEdges :
				decVar_edgeFlow = edgeFlowDecVarList[timeStage][str(edgeIndex)][str(userIndex)]
				providerFlowOutDecVarList.append(decVar_edgeFlow)
		constrIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex)

		bandModel.addConstr(quicksum(userFlowInDecVarList), GRB.GREATER_EQUAL, quicksum(providerFlowOutDecVarList), name='c49:' + constrIndex)
print('Constraint 49 complete')

# constraint 50 : edge flow >= 0
for timeStage in range(0, timeLength) :
	for edgeIndex in range(0, len(edgeList)) :
		for userIndex in range(0, numOfUsers) :
			decVar_edgeFlow = edgeFlowDecVarList[timeStage][str(edgeIndex)][str(userIndex)]

			constrIndex = '_t_' + str(timeStage) + '_e_' + str(edgeIndex) + '_u_' + str(userIndex)
			bandModel.addConstr(decVar_edgeFlow, GRB.GREATER_EQUAL, 0, name='c50:' + constrIndex)
print('Constraint 50 complete')

bandModel.write("bandModel.lp")

try :
	bandModel.optimize()
except GurobiError as e :
	gurobiErr = True
	print('Gurobi error')
	for v in bandModel.getVars() :
		varName = v.varName
		varValue = v.x
		bandModelResultData.append([varName, varValue])
finally :
	bandModelTotalCost = bandModel.ObjVal
	print("Bandwidth model Objective function value : ", bandModelTotalCost)
	bandModelRuntime = bandModel.Runtime
	print('Gurobi run time : ', bandModelRuntime)
	bandModelMipGap = bandModel.MIPGap

	if gurobiErr == False :
		for v in bandModel.getVars() :
			varName = v.varName
			varValue = v.x
			bandModelResultData.append([varName, varValue])
	bandModelResultData.append(['Cost', bandModelTotalCost])
	bandModelResultData.append(['Runtime', bandModelRuntime])
	bandModelResultData.append(['MIPGap', bandModelMipGap])

	resultColumn = ['Variable Name', 'Value']

	writeModelResult('modelResult_Bandwidth.csv', resultColumn, bandModelResultData)





























