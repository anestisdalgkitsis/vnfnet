# VNFnet v6.0.2
# VNF Simulation Laboratory | Fork of VNFnet2018
# Anestis Dalgkitsis ✖️ | Started 29 March 2020
# 23 Jan 2022

# Python Modules

import os
import json
import warnings
import networkx as nx
import matplotlib.pyplot as plt
# Apple ARM Fix
# import matplotlib  
# matplotlib.use('Qt5Agg')
# from matplotlib import pyplot as plt

# Local Modules

from microlog import Microlog

# Suppress Warnings

warnings.filterwarnings("ignore")

# Start Microlog Session

m = Microlog(path=os.path.join('./logs', 'VNFnetLog.log'), date=True)
# e = Microlog(path=os.path.join('./logs', 'VNFnetENERGYLog.log'), date=True)
m.printl(" >>>> New VNFnet Session >>>>")

# Simulation Classes

class Chain:
	def __init__(self, uid, title, chainList, sla):

		self.uid = uid
		self.title = title

		self.sla = sla

		self.chain = chainList # DATA FLOW -> FROM FIRST TO LAST VM!

	def destination(self):
		return self.chain[len(self.chain)-1].host.uid

	def strChain(self):
		text = ""
		for vm in self.chain:
			text += str(vm.uid)
			text += ">"
		text = text[:-1]
		return text

class Service:
	def __init__(self, uid, title="Untitled_Service", cpuCores=1, ram=1, storage=1):

		self.name = title
		self.uid = uid

		self.CPUrequirements = cpuCores
		self.RAMrequirements = ram
		self.StorageRequirements = storage

class VM:
	def __init__(self, uid, name, serviceImage, hostObject):

		self.uid = uid
		self.name = name

		self.service = serviceImage
		self.host = hostObject

class Link:
	def __init__(self, uid, sourceObject, destinationObject, bandwidth=1, latency=1, opticalPowerTX=-2):
		
		# Link Attributes
		
		self.uid = uid

		self.bandwidthCap = bandwidth # Gbps
		self.latency = latency # ms

		self.source = sourceObject
		self.destination = destinationObject

		self.opticalPowerTX = opticalPowerTX # dBm

		# Link Simulation Variables

		self.bandwidthUtil = bandwidth

		self.runningConnections = []

	def establishConnection(self, serviceObject):
		"""return 0 means ok, 1 means can not be hosted"""

		if self.bandwidthCap < (self.bandwidthUtil + serviceObject.bandwidthRequirements):
			m.printl("[linkALERT] full capacity reached on: " + str(self.uid)) # + " | Top: " + str(self.top()))
			return 1

		self.bandwidthUtil += serviceObject.bandwidthRequirements
		self.runningConnections.append(serviceObject)

		return 0

	def closeConnection(self, serviceObject):
		""" return 0 means closed, 1 means the connection does not exist """

		for service in range(len(self.runningConnections)):
			if serviceObject.id == self.runningConnections[service].id:
				self.bandwidthUtil -= self.runningConnections[service].bandwidthRequirements
				del self.runningConnections[service]
				return 0

		m.printl("Connection to kill does not exist") #: " + str(self.top()))
		return 1

	def top(self):
		"""returns a list with the IDs of all running connections"""
		topConnectionsID = []
		for connection in range(len(self.runningConnections)):
			topConnectionsID.append(self.runningConnections[connection].id)
		return topConnectionsID

	# def activity(self):
	# 	return (self.bandwidthUtil/self.bandwidthCap)*100

	def sampleEnergyConsumption(self, datasize): # bits
		linkConsuption = -self.opticalPowerTX * (datasize / self.bandwidthUtil * (10 ** -9))
		# print(self.opticalPowerTX)
		# print(datasize)
		# print(self.bandwidthUtil * (10 ** 9))
		# print(datasize / self.bandwidthUtil * (10 ** 9))
		# print(">> sEC "+str(linkConsuption))
		return linkConsuption

class Host:
	def __init__(self, uid, name="Untitled_host", cpuCores=4, ram=8, storage=128, cpuFrequency=2.6, cpuCyclesPerSampleData=(10 ** 4)):

		# Host Attributes

		self.name = name
		self.uid = uid

		self.CPUcap = cpuCores
		self.RAMcap = ram
		self.StorageCap = storage

		self.cpuFrequency = cpuFrequency ** 9 # GHz to Hz
		self.cpuCyclesPerSampleData = cpuCyclesPerSampleData # CPU Cycles Number
		self.architectureEffectiveSwitchedCapacitance = 10 ** (-28)
		self.bitsOverhead = 8440000 # 1.055 MB

		# Host Simulation Variables

		self.CPUUtil = 0
		self.RAMUtil = 0
		self.StorageUtil = 0

		self.runningServices = []

	def instantiateService(self, serviceObject):
		""" return 0 means hosted ok, return 1 means that it can not be hosted """

		if self.CPUcap < (self.CPUUtil + serviceObject.CPUrequirements):
			m.printl("[Host Alert] Full CPU on host: " + str(self.uid)) # + " | Top: " + str(self.top()))
			return 1
		if self.RAMcap < (self.RAMUtil + serviceObject.RAMrequirements):
			m.printl("[Host Alert] Full RAM on host: " + str(self.uid)) # + " | Top: " + str(self.top()))
			return 1
		if self.StorageCap < (self.StorageUtil + serviceObject.StorageRequirements):
			m.printl("[Host Alert] Full Storage on host: " + str(self.uid)) # + " | Top: " + str(self.top()))
			return 1

		self.CPUUtil += serviceObject.CPUrequirements
		self.RAMUtil += serviceObject.RAMrequirements
		self.StorageUtil += serviceObject.StorageRequirements

		self.runningServices.append(serviceObject)

		return 0

	def killService(self, serviceObject):
		""" return 0 means killed ok, return 1 means that the service does not run in this host """

		for service in range(len(self.runningServices)):
			if serviceObject.uid == self.runningServices[service].uid:

				self.CPUUtil -= self.runningServices[service].CPUrequirements
				self.RAMUtil -= self.runningServices[service].RAMrequirements
				self.StorageUtil -= self.runningServices[service].StorageRequirements

				del self.runningServices[service]

				return 0
		m.printl("[Host Alert] Service to terminate does not exist: ") # + str(self.top()), flairs=["Host"])
		return 1

	def sampleEnergyConsumption(self):
		serverConsuption = self.CPUUtil * self.architectureEffectiveSwitchedCapacitance * self.cpuCyclesPerSampleData * self.bitsOverhead * (self.cpuFrequency ** 2)
		return serverConsuption

class Domain:
	def __init__(self, uid, name, hostList, linkList):

		self.uid = uid
		self.name = name
		self.hostList = hostList
		self.linkList = linkList

class User:
	def __init__(self, uid, name, VMChain, datarate, trafficPattern):

		# User Attributes

		self.uid = uid
		self.name = name

		self.bitsOverhead = 8440000 # 1.055 MB
		self.userChain = VMChain # One Chain for every user
		self.bandwidth = datarate # Gbps. Casual mmWave 5G 0.1 Gbps
		self.trafficPattern = trafficPattern # Default: Reserved, otherwise: Square or Saw

		# self.sla = sla

		# Simulation Variables

		self.runtimeUserDatarate = self.bandwidth
		self.counter = 0

	def trafficPatternGenerator(self):
		
		if self.trafficPattern == "square":
			if self.counter % 2 == 0:
				self.runtimeUserDatarate = 0.3 * self.bandwidth
			else:
				self.runtimeUserDatarate = self.bandwidth

		if self.trafficPattern == "saw":
			self.runtimeUserDatarate = abs(self.counter) % 10 * 0.1 * self.bandwidth

		# if self.trafficPattern == "pulse":
		# 	pass

		# if self.trafficPattern == "reserved":
		# 	self.runtimeUserDatarate = self.bandwidth

		self.counter += 1

		return self.runtimeUserDatarate

class Connection:
	def __init__(self, uid, nodePath, userObject):
		self.uid = uid
		self.nodePath = nodePath
		self.userObject = userObject

class Network:
	def __init__(self, title):

		# Network Graph
		self.topologyGraph = nx.Graph()

		# Network Entities
		self.networkHosts = []
		self.networkUsers = []
		self.networkLinks = []
		self.networkServices = []
		self.networkVMs = []
		self.networkChains = []
		self.networkDomains = []

		# Statistics (Used for ML regularization)

		self.maxNetCPU = -1
		self.maxNetRAM = -1
		self.maxNetStorage = -1
		self.maxNetLatency = -1
		self.maxNetBandwidth = -1
		self.maxNetSLA = -1

		# Internal Variables

		self.guidCounter = -1 # Graph Unique Identifier Counter

		self.suspendedLinks = []
		self.trafficActivityList = []

	# Internal Utilities

	def getGUID(self):
		self.guidCounter += 1
		return self.guidCounter

	# Network Building Commands

	def addHost(self, hostname, cpuCores, ram, storage):

		uid = self.getGUID()
		hostObject = Host(uid, hostname, cpuCores, ram, storage)
		self.networkHosts.append(hostObject)

		self.topologyGraph.add_node(uid, label=hostname, shapes="o")
		m.printl("Host added with uid: " + str(uid) + ", hostname: " + str(hostname) + ".")

		if cpuCores > self.maxNetCPU:
			self.maxNetCPU = cpuCores
		if ram > self.maxNetRAM:
			self.maxNetRAM = ram
		if storage > self.maxNetStorage:
			self.maxNetStorage = storage

		return hostObject

	def addUser(self, name, VMchain, datarate=1, trafficPattern="reserved"): # , sla=10

		uid = self.getGUID()
		userObject = User(uid, name, VMchain, datarate, trafficPattern) # , sla
		self.networkUsers.append(userObject)

		self.topologyGraph.add_node(uid, uid=uid, label=name, shapes="v")
		m.printl("User with uid: " + str(uid) + " added.")

		# if sla > self.maxNetSLA:
		# 	self.maxNetSLA = sla

		return userObject

	def removeUser(self, userObject):

		self.topologyGraph.remove_node(userObject.uid)
		self.networkUsers.remove(userObject)
		del userObject

		return True

	def addLink(self, sourceHostObject, destinationHostObject, bandwidth=10, delay=5, loss=0):

		uid = self.getGUID()
		linkObject = Link(uid, sourceHostObject, destinationHostObject, bandwidth=bandwidth, latency=delay)
		self.networkLinks.append(linkObject)

		if loss > 0:
			self.topologyGraph.add_edge(sourceHostObject.uid, destinationHostObject.uid, uid=uid, color='m', style="dashed", weight=bandwidth/12, length=delay, delay=delay, bandwidth=bandwidth, loss=loss)
		else:
			self.topologyGraph.add_edge(sourceHostObject.uid, destinationHostObject.uid, uid=uid, color='skyblue', style="solid", weight=bandwidth/12, length=delay, delay=delay, bandwidth=bandwidth, loss=loss)
		
		m.printl("Link " + "("+str(sourceHostObject.uid)+")<->("+str(destinationHostObject.uid)+")" + " with bandwidth: " + str(bandwidth) + " added with uid: " + str(uid) + ".")

		if delay > self.maxNetLatency:
			self.maxNetLatency = delay
		if bandwidth > self.maxNetBandwidth:
			self.maxNetBandwidth = bandwidth

		return linkObject

	def removeLink(self, linkObject):

		self.topologyGraph.remove_edge(linkObject.uid)
		self.networkLinks.remove(linkObject)
		del linkObject

		return True

	def addService(self, title, cpuCores=2, ram=3, storage=8):

		uid = self.getGUID()
		serviceObject = Service(uid, title, cpuCores=cpuCores, ram=ram, storage=storage)
		self.networkServices.append(serviceObject)

		m.printl("Service added with uid: " + str(uid) + ".")

		return serviceObject

	def addChain(self, title, serviceObjectList, sla):

		uid = self.getGUID()
		chainObject = Chain(uid=uid, title=title, chainList=serviceObjectList, sla=sla)
		self.networkChains.append(chainObject)
		m.printl("Chain added with uid: " + str(uid) + ".")

		return chainObject

	def removeChain(self, chainObject):

		self.networkChains.remove(chainObject)
		del chainObject

		return True

	def addDomain(self, name, hostList, linkList):

		uid = self.getGUID()
		domainObject = Domain(uid, name, hostList, linkList)
		self.networkDomains.append(domainObject)
		m.printl("Domain " + str(name) + " added with uid: " + str(uid) + ".")

		return domainObject

	# VM Orchestration Operations

	def instantiateVM(self, serviceObject, hostObject):

		uid = self.getGUID()
		title2 = serviceObject.name+str(uid)
		self.VMObject = VM(uid, title2, serviceObject, hostObject)
		self.networkVMs.append(self.VMObject)
		m.printl("Service VM Instantiated with uid: " + str(uid) + ".")
		
		error = hostObject.instantiateService(serviceObject)
		if (error):
			m.printl("Error Instantiating Service VM in Host, check logfile. Err: " + str(error), flairs=["instantiateVM"])
			# exit()

		self.topologyGraph.add_node(uid, uid=uid, label=title2, shapes="^")
		self.topologyGraph.add_edge(uid, hostObject.uid, uid=uid, color='g', style="dashed", weight=1, length=12, delay=99999, bandwidth=0, loss=100)

		return self.VMObject

	def terminateVM(self, VMObject):
		hostObject = VMObject.host
		error = hostObject.killService(VMObject.service)
		if error:
			m.printl("Error while terminating VM in host. Check the class code.", flairs=["terminateVM"])
			return False

		self.topologyGraph.remove_node(VMObject.uid)
		self.topologyGraph.remove_edge(VMObject.uid, hostObject.uid)

		return True

	def migrateVM(self, vm, sourceHostObject, destinationHostObject):

		connectionsWithThisHost = []

		# Discover connections to update

		if sourceHostObject == destinationHostObject:
			m.printl("Source and destination hosts are the same.", flairs=["migrateVM"])
			return True
		for connection in self.trafficActivityList:
			if vm.host in connection.nodePath:
				connectionsWithThisHost.append(connection)
		
		# Stop Traffic in old host (BM)

		for connection in connectionsWithThisHost:
			# self.stopTraffic(connection.userObject)
			er = self.stopTraffic(connection)
			if not er:
				m.printl("Error in vm.stop(): " + str(er), flairs=["migrateVM"])
				return False

		# Start traffic in new host (AM)

		for connection in connectionsWithThisHost:
			# self.startTraffic(connection.userObject)
			error = self.startTraffic(connection)
			if not error:
				m.printl("Error migrating, could not start connection in new host.", flairs=["migrateVM"])
				return False

		# Terminate VM instance in old host (BM)

		# error = self.terminateVM(vm)
		error = sourceHostObject.killService(vm.service)
		if error:
			m.printl("Error while terminating VM with uid "+str(vm.uid)+" in host with uid "+str(sourceHostObject.uid)+". VM not found in host.", flairs=["migrateVM"])
			return False
		else:
			m.printl("VM with uid "+str(vm.uid)+" in host "+str(sourceHostObject.uid)+" terminated successfully.", flairs=["migrateVM"])
			self.topologyGraph.remove_edge(vm.uid, sourceHostObject.uid)
		
		# Instantiate VM instance in new host (AM)

		# self.instantiateVM(vm.service, destinationHostObject)
		error = destinationHostObject.instantiateService(vm.service)
		if (error):
			m.printl("Error Instantiating Service VM in Host, check logfile. Err: " + str(error), flairs=["migrateVM"])
			# exit()
		else:
			m.printl("Service VM Instantiated.", flairs=["migrateVM"])
			self.topologyGraph.add_edge(vm.uid, destinationHostObject.uid, uid=vm.uid, color='g', style="dashed", weight=1, length=12, delay=99999, bandwidth=0, loss=100)

		# Log Action

		vm.host = destinationHostObject
		m.printl("Migration successful. Info: "+str(vm.uid)+" ("+str(sourceHostObject.uid)+")->-("+str(destinationHostObject.uid)+").", flairs=["migrateVM"])
		return True

	# Traffic Flows Management

	def createConnection(self, userObject):

		# Calculate Available Route (Dijkstra)

		chainNodePath = []
		try:
			nodePath = nx.single_source_dijkstra(self.topologyGraph, userObject.uid, userObject.userChain.chain[0].host.uid, weight='delay')
		except nx.NetworkXNoPath:
			m.printl("except NetworkXNoPath")
			return False
		chainNodePath.extend(nodePath[1])
		for n in range(len(userObject.userChain.chain)-1):
			chainNodePath = chainNodePath[:-1]
			try:
				nodePath = nx.single_source_dijkstra(self.topologyGraph, userObject.userChain.chain[n].host.uid, userObject.userChain.chain[n+1].host.uid, weight='delay')
			except nx.NetworkXNoPath:
				return False
			chainNodePath.extend(nodePath[1])
		# m.printl("User with uid "+str(userObject.uid)+" has this host chain path: "+ str(chainNodePath), flairs=["createConnection"])
		m.printl("User uid "+str(userObject.uid)+" has this host chain path: "+str(chainNodePath)+" with this SC:", flairs=["createConnection"])
		for h in range(len(userObject.userChain.chain)):
			m.printl(" |- VM ["+str(userObject.userChain.chain[h].uid)+"] in host ("+str(userObject.userChain.chain[h].host.uid)+")", flairs=["createConnection"])

		# Allocate bandwidth on Links
		
		for edge in range(len(chainNodePath)-1):
			linkAttributesJSON = self.topologyGraph.get_edge_data(chainNodePath[edge],chainNodePath[edge+1])
			linkbandwidth = linkAttributesJSON["bandwidth"]
			linkuid = linkAttributesJSON["uid"]
			bandwidthAfter = linkbandwidth - userObject.bandwidth
			m.printl("Link uid: "+str(linkuid) + " bandwidth_after is "+str(bandwidthAfter)+ " of connection ("+str(chainNodePath[edge])+")-("+str(chainNodePath[edge+1])+").")
			if bandwidthAfter <= 0:
				m.printl("Cannot create connection between nodes: "+str(chainNodePath[edge])+" and "+str(chainNodePath[edge+1])+". ZERO OR NEGATIVE bandwidth AFTER TRAFFIC ASSIGNMENT. Adding link to suspended.")
				self.suspendedLinks.append([chainNodePath[edge],chainNodePath[edge+1],self.topologyGraph[chainNodePath[edge]][chainNodePath[edge+1]]])
				self.topologyGraph.remove_edge(chainNodePath[edge],chainNodePath[edge+1])
				return True
			self.topologyGraph[chainNodePath[edge]][chainNodePath[edge+1]]['bandwidth']=bandwidthAfter
			# m.printl("LNK_UID: "+str(linkuid))
			# m.printl("NETLNK_LST_LEN: "+str(len(self.networkLinks)))
			index = 0
			for link in self.networkLinks:
				# m.printl("LNK_LP_UID: "+str(link.uid))
				# m.printl("LNK_LP_TA: "+str(link.bandwidthUtil))
				# m.printl("-")
				if link.uid == linkuid:
					break
				index += 1
			# m.printl(index)
			# exit()
			self.networkLinks[index].bandwidthUtil = bandwidthAfter

		return chainNodePath

	def unsuspendLinks(self):
		if self.suspendedLinks:
			for link in self.suspendedLinks[:]:
				# print(str(link[0])+","+str(link[1])+","+str(link[2])+"////////")
				attributesList=link[2]
				self.topologyGraph.add_edge(link[0], link[1], uid=attributesList["uid"], color=attributesList["color"], style=attributesList["style"], weight=attributesList["weight"], length=attributesList["length"], delay=attributesList["delay"], bandwidth=attributesList["bandwidth"], loss=attributesList["loss"])
				# self.topologyGraph.add_edge(link[0], link[1], color=attributesList["color"], weight=attributesList["weight"])
				self.suspendedLinks.remove(link)
		return

	def startTraffic(self, userObject):

		while True:
			chainNodePath = self.createConnection(userObject)
			if isinstance(chainNodePath, list):
				m.printl("chainNodePath " + str(chainNodePath) + " defined successfully")
				break
			elif chainNodePath == False:

				m.printl("suspended links <<ffXX>> dump: " + str(self.suspendedLinks))
				# print(self.topologyGraph.number_of_edges())

				self.unsuspendLinks()

				m.printl("suspended links <<rrXX>> dump: " + str(self.suspendedLinks))
				# print(str(self.topologyGraph.number_of_edges())+"<><><2>")

				m.printl("chainNodePath of user "+str(userObject.uid)+" COULD NOT BE DEFINED. No links with available bandwidth are connected to the destination node.")

				return False # Refuse service
			else:
				m.printl("Rerouting. Removed unavailable link from graph.")
				pass

		m.printl("suspended links <<ff>> dump: " + str(self.suspendedLinks))
		# print(str(self.topologyGraph.number_of_edges())+"<><><1>")

		self.unsuspendLinks()

		m.printl("suspended links <<rr>> dump: " + str(self.suspendedLinks))
		# print(str(self.topologyGraph.number_of_edges())+"<><><2>")

		uid = len(self.trafficActivityList)
		connectionObject = Connection(uid, chainNodePath, userObject)
		self.trafficActivityList.append(connectionObject)
		# print(chainNodePath)

		return connectionObject

	def stopTraffic(self, connectionObject):
		if not connectionObject:
			m.printl("Connection does not exist. Service was denied during request.", flairs=["stopTraffic"])
			return False
		m.printl("stopTraffic(@args) >> connectionObject.nodePath: " + str(connectionObject.nodePath), flairs=["stopTraffic"])
		for edge in range(len(connectionObject.nodePath)-1):
			linkAttributesJSON = self.topologyGraph.get_edge_data(connectionObject.nodePath[edge],connectionObject.nodePath[edge+1])
			linkbandwidth = linkAttributesJSON["bandwidth"]
			linkuid = linkAttributesJSON["uid"]
			bandwidthAfter = linkbandwidth + connectionObject.userObject.bandwidth
			self.topologyGraph[connectionObject.nodePath[edge]][connectionObject.nodePath[edge+1]]['bandwidth']=bandwidthAfter
			# self.networkLinks[linkuid].bandwidthUtil = self.networkLinks[linkuid].bandwidthCap - bandwidthAfter
			index = 0
			for link in self.networkLinks:
				# m.printl("LNK_LP_UID: "+str(link.uid))
				# m.printl("LNK_LP_TA: "+str(link.bandwidthUtil))
				# m.printl("-")
				if link.uid == linkuid:
					break
				index += 1
			self.networkLinks[index].bandwidthUtil = bandwidthAfter
			# self.networkLinks[linkuid].bandwidthUtil = bandwidthAfter
			m.printl("Traffic stopped in edge: "+str(connectionObject.nodePath[edge]), flairs=["stopTraffic"])
		self.trafficActivityList.remove(connectionObject)
		m.printl("Traffic connection "+str(connectionObject.nodePath)+" stopped successfully.", flairs=["stopTraffic"])
		return True


	def servicePing(self, connectionObject):
		if connectionObject == False:
			m.printl("DURING SERVICEPING. THIS MESSAGE SHOULD NOT DISPLAY! Connection does not exist. Service was denied during request.", flairs=["ERROR", "servicePing"])
			return 99999 # Denied flag
		m.printl("servicePing(@args) >> connectionObject.nodePath: " + str(connectionObject.nodePath))
		rtt = 0
		for edge in range(len(connectionObject.nodePath)-1):
			linkAttributesJSON = self.topologyGraph.get_edge_data(connectionObject.nodePath[edge],connectionObject.nodePath[edge+1])
			rtt += linkAttributesJSON["delay"]
		m.printl("servicePing for chain " + str(connectionObject.nodePath) + " done with result: " + str(rtt) + "ms.")
		return rtt

	def serviceData(self, connectionObject):
		# e.printl("Link Energy Stats:")
		if connectionObject == False:
			m.printl("DURING SERVICEDATA. THIS MESSAGE SHOULD NOT DISPLAY! Connection does not exist. Service was denied during request.", flairs=["ERROR", "serviceData"])
			return -1 # Denied flag
		m.printl("serviceData(@args) >> connectionObject.nodePath: " + str(connectionObject.nodePath))
		# for edge in range(len(connectionObject.nodePath)-1):
		# 	linkAttributesJSON = self.topologyGraph.get_edge_data(connectionObject.nodePath[edge],connectionObject.nodePath[edge+1])
		# 	bitSum = linkAttributesJSON["bits"]
		linkEnergy = 0
		if len(connectionObject.nodePath)-2 != 0 : # is not
			for i in range(len(connectionObject.nodePath)-2):
				for link in self.networkLinks:
					# sumOverhead = 0
					if link.source.uid == connectionObject.nodePath[i] and link.destination.uid == connectionObject.nodePath[i+1]:
						# sumOverhead += link.source.bitsOverhead
						# linkEnergy += link.sampleEnergyConsumption(sumOverhead)
						linkEnergy += link.sampleEnergyConsumption(link.source.bitsOverhead)
						# e.printl("Luid: " + str(link.uid) + " s: " + str(link.source.uid) + " d: " + str(link.destination.uid) + " E: " + str(link.sampleEnergyConsumption(link.source.bitsOverhead)))
						if linkEnergy == 0:
							print(linkEnergy)
							print(link.source.bitsOverhead)
							print(connectionObject.nodePath)
							print(connectionObject.nodePath[i])
							print(connectionObject.nodePath[i+1])
							exit()
		else:
			# print("ZERO-TWO")
			# print(connectionObject.nodePath)
			for link in self.networkLinks:
				if link.source.uid == connectionObject.nodePath[0] and link.destination.uid == connectionObject.nodePath[1]:
					linkEnergy += link.sampleEnergyConsumption(link.source.bitsOverhead)
					# e.printl("Luid: " + str(link.uid) + " s: " + str(link.source.uid) + " d: " + str(link.destination.uid) + " E: " + str(link.sampleEnergyConsumption(link.source.bitsOverhead)))
					if linkEnergy == 0:
						print(linkEnergy)
						print(link.source.bitsOverhead)
						print(connectionObject.nodePath)
						print(connectionObject.nodePath[0])
						print(connectionObject.nodePath[1])
						exit()
		if linkEnergy == 0:
			linkEnergy = 0.0001
			print("Zero Energy! ERROR! Dump info:")
			print(connectionObject.nodePath)
			exit()
		m.printl("serviceData for chain " + str(connectionObject.nodePath) + " done with result: " + str(linkEnergy) + " bits.")
		return linkEnergy

	def servicePerf(self, connectionObject):
		if connectionObject == False:
			m.printl("DURING SERVICEPERF. THIS MESSAGE SHOULD NOT DISPLAY! Connection does not exist. Service was denied during request.", flairs=["ERROR"])
			return 0 # Denied flag
		m.printl("Starting SERVICE PERF of user " + str(connectionObject.userObject.uid))
		# for edge in range(len(connectionObject.nodePath)-1):
		# 	linkAttributesJSON = self.topologyGraph.get_edge_data(connectionObject.nodePath[edge],connectionObject.nodePath[edge+1])
		# 	m.printl("Measured bandwidth of link "+str(connectionObject.nodePath[edge])+" and "+str(connectionObject.nodePath[edge])+" is "+str(linkAttributesJSON["bandwidth"])+" Gbps")
		# 	if linkAttributesJSON["bandwidth"] < bw:
		# 		bw = linkAttributesJSON["bandwidth"]
		bw = connectionObject.userObject.trafficPatternGenerator()
		# bw = connectionObject.userObject.bandwidth
		m.printl("SERVICE PERF done with result: " + str(bw) + "Gbps.")
		return bw

	def servicePerformanceScore(self, userObject):
		rtt = self.servicePing(userObject)
		bw = self.servicePerf(userObject)
		return bw / rtt

	# Interactive Terminal Commands

	def printTopology(self):

		plt.figure(1)
		plt.clf()

		# Positions for all nodes
		pos = nx.spring_layout(self.topologyGraph)

		# Fetch graph attributes / Calculate graph element attributes
		edges = self.topologyGraph.edges()
		colors = [self.topologyGraph[u][v]['color'] for u,v in edges]
		weights = [self.topologyGraph[u][v]['weight'] for u,v in edges]
		lengths = [self.topologyGraph[u][v]['length'] for u,v in edges]
		styles = [self.topologyGraph[u][v]['style'] for u,v in edges]

		nodes = self.topologyGraph.nodes()
		# shapes = [self.topologyGraph[n]['shapes'] for n in nodes]
		shapes = set((aShape[1]["shapes"] for aShape in nodes(data = True)))
		# labels = [self.topologyGraph[u][v]['bandwidth'] for u,v in edges]

		# Blue nodes: Servers, size = capacity
		# Magenda nodes: Users
		# nodes = self.topologyGraph.nodes()
		# labels = [self.topologyGraph[u][v]['label'] for u,v in nodes]
		# self.topologyGraph
		# nx.draw_networkx_nodes(self.topologyGraph, pos, node_size=700, shapes=shapes)
		for aShape in shapes:
			nx.draw_networkx_nodes(self.topologyGraph, pos, node_size=700, node_shape = aShape, nodelist = [sNode[0] for sNode in filter(lambda x: x[1]["shapes"]==aShape, self.topologyGraph.nodes(data = True))])
		
		# Solid lines: optical links, size = free capacity
		# Magenda dashed lines: wireless links, size = free capacity.
		# nx.draw_networkx_edges(self.topologyGraph, pos, edgelist=self.topologyGraph.edges, edge_color=colors, style=styles, width=6)
		nx.draw_networkx_edges(self.topologyGraph, pos, edgelist=self.topologyGraph.edges, edge_color=colors, style=styles, width=weights) # length=lengths
		# nx.draw_networkx_edge_labels(self.topologyGraph, pos, edge_labels=labels,font_color='red')
		nx.draw_networkx_labels(self.topologyGraph, pos, font_size=20, font_family='sans-serif')

		plt.axis('off')
		plt.savefig("./figures/topology.png", format="PNG")
		# plt.show()
		plt.clf()

	def printHosts(self):
		print("[Hosts in Network: "+str(len(self.networkHosts))+"]")
		for h in range(len(self.networkHosts)):
			print(" |- uid: " + str(self.networkHosts[h].uid) + ", name: " + str(self.networkHosts[h].name))

	def printLinks(self):
		print("[Links in Network: "+str(len(self.networkLinks))+"]")
		for l in range(len(self.networkLinks)):
			print(" |- uid: "+str(self.networkLinks[l].uid)+", src_uid: "+str(self.networkLinks[l].source.uid)+", dst_uid: "+str(self.networkLinks[l].destination.uid)+", bw_u/c: "+str(self.networkLinks[l].bandwidthUtil)+"/"+str(self.networkLinks[l].bandwidthCap)+", lat: "+str(self.networkLinks[l].latency))

	def printServices(self):
		print("[Application Flavors Available: "+str(len(self.networkServices))+"]")
		for s in range(len(self.networkServices)):
			print(" |- uid: "+str(self.networkServices[s].uid)+", name: "+str(self.networkServices[s].name)+", cpu: "+str(self.networkServices[s].CPUrequirements)+", ram: "+str(self.networkServices[s].RAMrequirements)+", storage: "+str(self.networkServices[s].StorageRequirements))

	def printChains(self):
		print("[Defined Chains: "+str(len(self.networkChains))+"]")
		for c in range(len(self.networkChains)):
			print(" |- uid: " + str(self.networkChains[c].uid) + ", flow: " + str(self.networkChains[c].strChain())+", sla: "+str(self.networkChains[c].sla))

	def printVMs(self):
		print("[VMs in Network: "+str(len(self.networkVMs))+"]")
		for v in range(len(self.networkVMs)):
			print(" |- uid: "+str(self.networkVMs[v].uid)+", app: "+str(self.networkVMs[v].name)+", host_uid: "+str(self.networkVMs[v].host.uid))

	def printUsers(self):
		print("[Users in Network: "+str(len(self.networkUsers))+"]")
		for u in range(len(self.networkUsers)):
			print(" |- uid: "+str(self.networkUsers[u].uid)+", name: "+str(self.networkUsers[u].name)+", chain_uid: "+str(self.networkUsers[u].userChain.uid)+", bw: "+str(self.networkUsers[u].bandwidth))

	def printNetTop(self):
		# for all hosts and links visualize the data
		print("[[NetTop]]")
		print("[Hosts]")
		for h in range(len(self.networkHosts)):
			print(" |- host_uid: " + str(self.networkHosts[h].uid) + ", name: " + str(self.networkHosts[h].name))
			print(" |   |- CPU: ", self.networkHosts[h].CPUUtil, "/", self.networkHosts[h].CPUcap)
			print(" |   |- RAM: ", self.networkHosts[h].RAMUtil, "/", self.networkHosts[h].RAMcap)
			print(" |   |- STR: ", self.networkHosts[h].StorageUtil, "/", self.networkHosts[h].StorageCap)
		print("[Links]")
		for l in range(len(self.networkLinks)):
			print(" |- link_uid: "+str(self.networkLinks[l].uid)+", src_uid: "+str(self.networkLinks[l].source.uid)+", dst_uid: "+str(self.networkLinks[l].destination.uid))
			print(" |   |- BWD: ", self.networkLinks[l].bandwidthUtil, "/", self.networkLinks[l].bandwidthCap)
			print(" |   |- LAT: ", self.networkLinks[l].latency)

	def printFlows(self):
		# print active data traffic flows
		pass

	def printUserSnap(self, userObject):
		# a brief with everythong about the user.
		# print("[User "+str(userObject.uid)+" data brief]")
		# print(" |- user_uid: " + str(userObject.uid))
		# print(" |- user_name: " + str(userObject.name))
		# print(" |- user_datarate: " + str(userObject.bandwidth))
		# print(" |- user_max_lat_SLA: " + str(userObject.sla))
		# print(" |- user_userChain: " + userObject.userChain.strChain())
		# print(" |- [userChainHosts_exp]")
		chtext=""
		for h in range(len(userObject.userChain.chain)):
			# print("      |- VM ["+str(userObject.userChain.chain[h].uid)+"] in host ("+str(userObject.userChain.chain[h].host.uid)+")")
			chtext += str(userObject.userChain.chain[h].host.uid)+">"
		chtext = chtext[:-1]
		# return "user_uid: "+str(userObject.uid)+" | max_lat_SLA: " + str(userObject.sla)+" | SC: " + userObject.userChain.strChain()+" | SCHosts: "+chtext
		return "user_uid: "+str(userObject.uid)+" | SC: " + userObject.userChain.strChain()+" | SCHosts: "+chtext