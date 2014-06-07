#!/usr/bin/env python
# encoding: utf-8
"""
trial2.py

Created by Fredrick Stakem on 2010-02-08.
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

# Ex -> MovementType = Enum( 'Stacking', 'Catching', 'TieShoes' )

# Data structures
#------------------------------------------------------------------------------
class Host(object):
	
	def __init__(self, name):
		self.name = name
		self.transmitter = None
		self.receiver = None
		
	def addTransmitter(self, transmitter):
		self.transmitter = transmitter
		self.transmitter.host = self
		
	def addReceiver(self, receiver):
		self.receiver = receiver
		self.receiver.host = self
		
	def addLink(self, remoteHost=None, delay=100, jitter=10, packetLoss=0):
		link = Link(localHost=self, remoteHost=remoteHost, delay=delay, jitter=jitter, packetLoss=packetLoss)
		self.transmitter.links.append(link)
		
	def addLink2(self, remoteHost, transmitter, receiver, network):
		pass
		
	def addConnection(self, remoteHost, transmitters, receivers, networks):
		pass
								
class Link(object):
	
	def __init__(self, localHost=None, remoteHost=None, delay=100, jitter=10, packetLoss=0):
		self.localHost = localHost
		self.remoteHost = remoteHost
		self.network = Network(delay, jitter, packetLoss)
		self.session = Session()
		
class Session(object):
	
	def __init__(self):
		self.transmittedPackets = []
		
class Network(object):

	def __init__(self, delay=100, jitter=10, packetLoss=0):
		self.delay = delay
		self.jitter = jitter
		self.packetLoss = packetLoss

	def simTransmission(self, packet):
		if not self.simPacketLoss():
			packet.rxTime =  packet.txTime + self.simDelay()
			receivePacket = ReceivePacket(packet=packet)
			simpy.activate(receivePacket, receivePacket.run())
		
		link = packet.txHost.transmitter.findLink(packet.rxHost)
		link.session.transmittedPackets.append(packet)

	def simDelay(self):
		return int(numpy.normal( self.delay, self.jitter, 1 )[0])

	def simPacketLoss(self):
		if numpy.uniform( 0, 100, 1 )[0] <= self.packetLoss:
			return True
		else:
			return False
			
class Packet(object):

	def __init__(self, seqNumber, time, data):
		self.txHost= None
		self.rxHost = None
		self.txTime = -1
		self.rxTime = -1
		self.seqNumber = seqNumber
		self.time = time
		self.data = data
		
class Receiver(object):

	def __init__(self):
		self.seqNumber = 0
		self.host = None

	def receivePacket(self, packet):
		print "%7.4f Receiving packet-> %1d" % (simpy.now(), packet.seqNumber)
		#self.reorderPacket(packet)

	def reorderPackets(self, packet):
		link = packet.txHost.findLink(remoteHost=packet.rxHost)
		if link:
			for packet in link.receivedPackets:
				if packet.rxTime > 1:
					pass
										
# Events
#------------------------------------------------------------------------------
#transmitPacketEvt = simpy.SimEvent("Transmit Packet")
#receivePacketEvt = simpy.SimEvent("Receive Packet")
		
# Models
#------------------------------------------------------------------------------
		
class Transmitter(simpy.Process):
	
	def __init__(self):
		simpy.Process.__init__(self, name='Transmitter')
		self.seqNumber = 1
		self.host = None
		self.links = []
		
	def run(self, data, txRate):
		print "%7.4f Starting transmitter" % (simpy.now())
		lastTx = -1000
		
		for sample in data:
			time = sample[0]
			date = sample[1]
			
			if time >= lastTx + txRate:
				lastTx = time
				self.transmitPacket(time, data)
				yield simpy.hold, self, txRate
				
	def transmitPacket(self, time, data):
		packet = Packet(seqNumber=self.seqNumber, time=time, data=data)
		packet.txHost = self.host
		packet.txTime = simpy.now()
		self.seqNumber += 1
		print "%7.4f Transmitting packet-> %1d" % (packet.txTime, packet.seqNumber)
		for link in self.links:
			packet.rxHost = link.remoteHost
			link.network.simTransmission(packet)
		
	def findLink(self, remoteHost=None):
		for link in self.links:
			if remoteHost == link.remoteHost:
				return link

		return None
			
class ReceivePacket(simpy.Process):
	
	def __init__(self, packet):
		simpy.Process.__init__(self, name='Packet')
		self.packet = packet
		
	def run(self):
		yield simpy.hold, self, self.packet.rxTime - simpy.now()
		self.packet.rxHost.receiver.receivePacket(self.packet)
															
# Resources
#------------------------------------------------------------------------------
#transmissionCh = simpy.Resource(capacity=100, name="TxChannels", unitName="TxChannel")
#receptionCh = simpy.Resource(capacity=100, name="RxChannels", unitName="RxChannel")

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
txRate = 50
maxTime = 2000.0

# Simulation
#------------------------------------------------------------------------------
simpy.initialize()
hostA = Host(name='Local Host')
hostB = Host(name='Remote Host')
transmitter = Transmitter()
receiver = Receiver()
hostA.addTransmitter(transmitter)
hostB.addReceiver(receiver)
hostA.addLink(remoteHost=hostB, delay=100, jitter=10, packetLoss=0)

simpy.activate(transmitter, transmitter.run(data=stateData, txRate=txRate))
simpy.simulate(until=maxTime)

# Output
#------------------------------------------------------------------------------
#pylab.plot(time, data,linewidth=2)
#pylab.show()