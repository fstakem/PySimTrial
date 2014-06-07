#!/usr/bin/env python
# encoding: utf-8
"""
trial3.py

Created by Fredrick Stakem on 2010-02-11.
Copyright (c) 2010 __Research__. All rights reserved.
"""

# Libraries
#------------------------------------------------------------------------------
import SimPy.Simulation as simpy
import scipy.signal.signaltools as signal
import pylab 
import numpy.random as numpy
from Queue import *
from copy import *
import sys
import os
import operator

# Folders and external libraries
currentPath = os.path.abspath(sys.path[0])
pyEnumRelative = os.path.join('PyEnum', 'enum-0.4.3-py2.5.egg')
pyEnumPath = os.path.join(currentPath, pyEnumRelative)
sys.path.append(pyEnumPath)
from enum import Enum
sys.path.pop()

# Data structures
#------------------------------------------------------------------------------
class Packet(object):
	
	def __init__(self, seqNumber, data):
		self.txHost = None
		self.rxHost = None
		self.txTime = -1
		self.rxTime = -1
		self.seqNumber = seqNumber
		self.data = data
		
class Link(object):
	
	def __init__(self, hostFrom=None, hostTo=None, delay=100, jitter=10, packetLoss=0):
		self.hostFrom = hostFrom
		self.hostTo = hostTo
		self.delay = delay
		self.jitter = jitter
		self.packetLoss = packetLoss
		
	def simTransmission(self, receiver, packet):
		if not self.simPacketLoss():
			packet.rxTime =  packet.txTime + self.simDelay()
			receivePacket = ReceivePacket(receiver=receiver, packet=packet)
			simpy.activate(receivePacket, receivePacket.run())

	def simDelay(self):
		return int(numpy.normal( self.delay, self.jitter, 1 )[0])

	def simPacketLoss(self):
		if numpy.uniform( 0, 100, 1 )[0] <= self.packetLoss:
			return True
		else:
			return False
	
class Network(object):
	
	def __init__(self):
		self.links = []
		
	def findLink(self, hostFrom, hostTo):
		for link in self.links:
			if link.hostFrom == hostFrom and link.hostTo == hostTo:
				return link
							
		return None
	
class Session(object):
	
	def __init__(self):
		self.transmittedPackets = []

class SimplexConnection(object):
	
	def __init__(self, name):
		self.name = name
		self.localHost = None
		self.remoteHosts = []
		self.transmitter = None
		self.receivers = []
		self.sessions = []
				
class Receiver(object):

	def __init__(self, name):
		self.name = name
		self.seqNumber = 0
		#self.host = None

	def receivePacket(self, packet):
		print "%7.4f Receiving packet %1d: %s -> %s" % \
			  (simpy.now(), packet.seqNumber, packet.txHost.name, packet.rxHost.name)
		#self.reorderPacket(packet)

	def reorderPackets(self, packet):
		link = packet.txHost.findLink(remoteHost=packet.rxHost)
		if link:
			for packet in link.receivedPackets:
				if packet.rxTime > 1:
					pass
		
class Host(object):
	network = None
	
	def __init__(self, name):
		self.name = name
		self.connections = []
		
	def addSimplexConnection(self, names, remoteHost, transmitter, receiver):
		try:
			localConnection = SimplexConnection(names[0])
			localConnection.localHost = self
			localConnection.remoteHosts.append(remoteHost)
			localConnection.transmitter = transmitter
			localConnection.receivers.append(receiver)
			
			remoteConnection = SimplexConnection(names[1])
			remoteConnection.localHost = remoteHost
			remoteConnection.remoteHosts.append(self)
			
			localConnection.sessions.append(Session())
			localConnection.transmitter.connection = localConnection
			localConnection.transmitter.network = Host.network
			
			self.connections.append(localConnection)
			remoteHost.connections.append(remoteConnection)
		except Exception, e:
			print "Error adding a connection to %s" % (self.name)
			print e
		
	def addDuplexConnection(self, names, remoteHost, transmitters, receivers):
		try:
			localConnection = SimplexConnection(names[0])
			localConnection.localHost = self
			localConnection.remoteHosts.append(remoteHost)
			localConnection.transmitter = transmitters[0]
			localConnection.receivers.append(receivers[1])
			
			remoteConnection = SimplexConnection(names[1])
			remoteConnection.localHost = remoteHost
			remoteConnection.remoteHosts.append(self)
			remoteConnection.transmitter = transmitters[1]
			remoteConnection.receivers.append(receivers[0])
			
			localConnection.sessions.append(Session())
			localConnection.transmitter.connection = localConnection
			localConnection.transmitter.network = Host.network
			remoteConnection.sessions.append(Session())
			remoteConnection.transmitter.connection = remoteConnection
			remoteConnection.transmitter.network = Host.network
			
			self.connections.append(localConnection)
			remoteHost.connections.append(remoteConnection)
		except Exception, e:
			print "Error adding a connection to %s" % (self.name)
			print e
			
	def addReceiverToConnection(self, name, remoteHost, receiver):
		for connection in self.connections:
			if name == connection.name:
				connection.remotehosts.append(remoteHost)
				connection.receivers.append(receiver)
				connection.sessions.append(Sessions())
		
# Models
#------------------------------------------------------------------------------
class Transmitter(simpy.Process):
	
	def __init__(self, name):
		simpy.Process.__init__(self, name=name)
		self.connection = None
		self.network = None
		self.seqNumber = 1
		
	def run(self, data, txRate):
		print "%7.4f Starting transmitter: %s" % (simpy.now(), self.name)
		lastTx = -1000
		
		for sample in data:
			time = sample[0]
			date = sample[1]
			
			if time >= lastTx + txRate:
				lastTx = time
				self.transmitPacket(sample)
				yield simpy.hold, self, txRate
				
	def transmitPacket(self, sample):
		packet = Packet(seqNumber=self.seqNumber, data=sample)
		packet.txHost = self.connection.localHost
		packet.txTime = simpy.now()
		self.seqNumber += 1
		for i, remoteHost in enumerate(self.connection.remoteHosts):
			newPacket = copy(packet)
			newPacket.rxHost = remoteHost
			link = self.network.findLink(hostFrom=self.connection.localHost, \
		           						 hostTo=remoteHost)
			link.simTransmission(self.connection.receivers[i], newPacket)
			self.connection.sessions[i].transmittedPackets.append(newPacket)
			print "%7.4f Transmitting packet %1d: %s -> %s" % \
				  (simpy.now(), newPacket.seqNumber, newPacket.txHost.name, newPacket.rxHost.name)
				
class ReceivePacket(simpy.Process):

		def __init__(self, receiver, packet):
			simpy.Process.__init__(self, name='Packet')
			self.receiver = receiver
			self.packet = packet

		def run(self):
			yield simpy.hold, self, self.packet.rxTime - simpy.now()
			self.receiver.receivePacket(self.packet)
		
# Data
#------------------------------------------------------------------------------
numOfSamples = 1000
deviation = 200
time = range(0,numOfSamples)
data = signal.gaussian(numOfSamples, deviation)
stateData = []
for i in range(0,numOfSamples):
	stateData.append([time[i], data[i]])

# Algorithm parameter
#------------------------------------------------------------------------------

# Simulation
maxTime = 2000.0

# Algorithm
txRate = 50

# Simulation
#------------------------------------------------------------------------------
simpy.initialize()

# Create hosts
hostA = Host(name='Local Host')
hostB = Host(name='Remote Host')

# Create network
network = Network()
Host.network = network
a_b_link = Link(hostFrom=hostA, hostTo=hostB, delay=100, jitter=10, packetLoss=0)
b_a_link = Link(hostFrom=hostB, hostTo=hostA, delay=100, jitter=10, packetLoss=0)
network.links.append(a_b_link)
network.links.append(b_a_link)

# Create algorithms
transmitter = Transmitter(name='SynchA')
receiver = Receiver('SnapB')
simpy.activate(transmitter, transmitter.run(stateData, txRate))

# Connect hosts
hostA.addSimplexConnection(names=[hostA.name, hostB.name], remoteHost=hostB, transmitter=transmitter, receiver=receiver)

simpy.simulate(until=maxTime)

