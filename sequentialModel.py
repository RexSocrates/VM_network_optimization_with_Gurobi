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
		effectiveVmResDecVarDict[str(provider)] = vmTypeEffectiveVmResDecVarDict

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
								effectiveVmList = effectiveVmResDecVarDict[str(provider)][str(vmType)][str(vmContractLength)][str(vmPayment)][vmResEffectiveTimeStage]
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
							effectiveVmReservationList = effectiveVmResDecVarDict[str(provider)][str(vmType)][str(vmContractLength)][str(vmPayment)][timeStage]
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

	# decision variables used in VM energy cost
	# energy consumption of active VMs
	energyConsumptionDecVarList = []
	# the number of active VMs
	activeVMsDecVarList = []
	# the number of turned on VMs
	turnedOnVMsDecVarList = []
	# the number of turned off VMs
	turnedOffVMsDecVarList = []
	# the usage of green energy
	greenEnergyDecVarList = []

	for timeStage in range(0, timeLength) :
		provider_energyConsumptionDecVarDict = dict()
		provider_activeVMsDecVarDict = dict()
		provider_turnedOnVMsDecVarDict = dict()
		provider_turnedOffVMsDecVarDict = dict()
		provider_greenEnergyDecVarDict = dict()
		for area in providerAreaDict :
			areaProviderList = providerAreaDict[area]
			for provider in areaProviderList :
				user_energyConsumptionDecVarDict = dict()
				user_activeVMsDecVarDict = dict()
				user_turnedOnVMsDecVarDict = dict()
				user_turnedOffVMsDecVarDict = dict()
				for userIndex in range(0, numOfUsers) :
					vmType_energyConsumptionDecVarDict = dict()
					vmType_activeVMsDecVarDict = dict()
					vmType_turnedOnVMsDecVarDict = dict()
					vmType_turnedOffVMsDecVarDict = dict()
					for vmType in vmTypeList :
						decVarIndex = '_t_' + str(timeStage) + '_u_' + str(userIndex) + '_p_' + str(provider) + '_i_' + str(vmType)

						energyConsumptionOfActiveVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='energyConsumption' + decVarIndex)
						activeVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='numOfActiveVms' + decVarIndex)
						turnedOnVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='numOfTurnedOnVms' + decVarIndex)
						turnedOffVMs = vmModel.addVar(vtype=GRB.CONTINUOUS, name='numOfTurnedOffVms' + decVarIndex)

						vmType_energyConsumptionDecVarDict[str(vmType)] = energyConsumptionOfActiveVMs
						vmType_activeVMsDecVarDict[str(vmType)] = activeVMs
						vmType_turnedOnVMsDecVarDict[str(vmType)] = turnedOnVMs
						vmType_turnedOffVMsDecVarDict[str(vmType)] = turnedOffVMs

					user_energyConsumptionDecVarDict[str(userIndex)] = vmType_energyConsumptionDecVarDict 
					user_activeVMsDecVarDict[str(userIndex)] = vmType_activeVMsDecVarDict
					user_turnedOnVMsDecVarDict[str(userIndex)] = vmType_turnedOnVMsDecVarDict
					user_turnedOffVMsDecVarDict[str(userIndex)] = vmType_turnedOffVMsDecVarDict

				provider_energyConsumptionDecVarDict[str(provider)] = user_energyConsumptionDecVarDict
				provider_activeVMsDecVarDict[str(provider)] = user_activeVMsDecVarDict
				provider_turnedOnVMsDecVarDict[str(provider)] = user_turnedOnVMsDecVarDict
				provider_turnedOffVMsDecVarDict[str(provider)] = user_turnedOffVMsDecVarDict

				tpDecVarIndex = '_t_' + str(timeStage) + '_p_' + str(provider)
				greenEnergyUsage = vmModel.addVar(vtype=GRB.CONTINUOUS, name='greenEnergy' + tpDecVarIndex)
				provider_greenEnergyDecVarDict[str(provider)] = greenEnergyUsage

		energyConsumptionDecVarList.append(provider_energyConsumptionDecVarDict)
		activeVMsDecVarList.append(provider_activeVMsDecVarDict)
		turnedOnVMsDecVarList.append(provider_turnedOnVMsDecVarDict)
		turnedOffVMsDecVarList.append(provider_turnedOffVMsDecVarDict)
		greenEnergyDecVarList.append(provider_greenEnergyDecVarDict)

	# VM cost objective function

	# VM energy cost objective function




































