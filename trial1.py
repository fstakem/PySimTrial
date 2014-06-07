#!/usr/bin/env python
# encoding: utf-8
"""
trial1.py

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
TransmitterType = Enum( 'Synchronous')
ReceiverType = Enum( 'Snap' )

class Host(object):
	
	def __init__(self, name='unknown host', transmitterType=TransmitterType.Synchronous, \
				 receiverType=ReceiverType.Snap):
		self.name = name
		self.transmitter = self.createTransmitter(transmitterType)
		self.receiver = self.createReceiver(receiverType)
		self.links = []
		
	def createTransmitter(self, type):
		if type == TransmitterType.Synchronous:
			return Transmitter(host=self)
		else:
			return Transmitter(host=self)
		
	def createReceiver(self, type):
		if type == ReceiverType.Snap:
			return Receiver(host=self)
		else:
			return Receiver(host=self)
		
	def addLink(self, remoteHost=None, delay=100, jitter=10, packetLoss=0):
		link = Link(localHost=self, remoteHost=remoteHost, delay=delay, jitter=jitter, packetLoss=packetLoss)
		self.links.append(link)
		
	def findLink(self, remoteHost=None):
		for link in self.links:
			if remoteHost == link.remoteHost:
				return link
				
		return None
				
class Link(object):
	
	def __init__(self, localHost=None, remoteHost=None, delay=100, jitter=10, packetLoss=0):
		self.localHost = localHost
		self.remoteHost = remoteHost
		self.network = Network(self, delay, jitter, packetLoss)
		self.transmittedPackets = []
		
class Network(object):

	def __init__(self, link=None, delay=100, jitter=10, packetLoss=0):
		self.link = link
		self.delay = delay
		self.jitter = jitter
		self.packetLoss = packetLoss

	def simTransmission(self, packet):
		if not self.simPacketLoss():
			delay = self.simDelay()
			print "%7.4f Packet delay-> %1d" % (delay, packet.seqNumber)
			packet.rxTime =  packet.txTime + delay
			#packet.rxTime =  packet.txTime + self.simDelay()
			receivePacket = ReceivePacket(packet=packet)
			simpy.activate(receivePacket, receivePacket.run())
		
		self.link.transmittedPackets.append(packet)

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

	def __init__(self, host=None):
		self.seqNumber = 0
		self.host = host

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
	
	def __init__(self, host=None):
		simpy.Process.__init__(self, name='Transmitter')
		self.transmittedPackets = []
		self.seqNumber = 1
		self.host = host
		
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
		# Do some stuff
		print "%7.4f Transmitting packet-> %1d" % (packet.txTime, packet.seqNumber)
		for link in self.host.links:
			packet.rxHost = link.remoteHost
			link.network.simTransmission(packet)
			
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
hostA.addLink(remoteHost=hostB, delay=100, jitter=10, packetLoss=0)

simpy.activate(hostA.transmitter, hostA.transmitter.run(data=stateData, txRate=txRate))
simpy.simulate(until=maxTime)

# Output
#------------------------------------------------------------------------------
#pylab.plot(time, data,linewidth=2)
#pylab.show()