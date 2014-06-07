#!/usr/bin/env python
# encoding: utf-8
"""
trial4.py

Created by Fredrick Stakem on 2010-02-11.
Copyright (c) 2010 __Research__. All rights reserved.
"""

realTimeMode = True

# Libraries
#------------------------------------------------------------------------------
if realTimeMode:
	import SimPy.SimulationRT as simpy
else:
	import SimPy.Simulation as simpy

import scipy.signal.signaltools as signal
import pylab 
import numpy
import numpy.random
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
class Network(object):
	
	def __init__(self):
		self.links = []
		
	def findLink(self, hostFrom, hostTo):
		for link in self.links:
			if link.hostFrom == hostFrom and link.hostTo == hostTo:
				return link
							
		return None
		
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
		return int(numpy.random.normal( self.delay, self.jitter, 1 )[0])

	def simPacketLoss(self):
		if numpy.random.uniform( 0, 100, 1 )[0] <= self.packetLoss:
			return True
		else:
			return False
			
class Packet(object):

	def __init__(self, seqNumber, data, txHost=None, rxHost=None, txTime=-1, rxTime=-1):
		self.txHost = txHost
		self.rxHost = rxHost
		self.txTime = txTime
		self.rxTime = rxTime
		self.seqNumber = seqNumber
		self.data = data
		
	def __str__(self):
		return "%s(%7.4f) -> %s(%7.4f) : Packet %d" % (self.txHost.name, self.txTime, \
													   self.rxHost.name, self.rxTime, \
													   self.seqNumber) 
		
class MulticastSource(object):
	
	def __init__(self, name, host=None, transmitter=None):
		self.name = name
		self.host = host
		self.transmitter = transmitter
		self.sinks = []
		
class Sink(object):
	
	def __init__(self, host=None, receiver=None):
		self.host = host
		self.receiver = receiver
		self.session = Session()
		
class Session(object):

	def __init__(self):
		self.transmittedPackets = []
				
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
		self.sources = []
		
	def addSimplexPath(self, name, remoteHost, transmitter, receiver):
		try:
			source = MulticastSource(name)
			source.host = self
			source.transmitter = transmitter
			sink = Sink(host=remoteHost, receiver=receiver)
			source.sinks.append(sink)
			transmitter.source = source
			
			self.sources.append(source)
		except Exception, e:
			print "Error adding a connection to %s" % (self.name)
			print e
		
	def addDuplexPath(self, names, remoteHost, transmitters, receivers):
		try:
			localSource = MulticastSource(names[0])
			localSource.host = self
			localSource.transmitter = transmitters[0]
			sink = Sink(host=remoteHost, receiver=receivers[1])
			localSource.sinks.append(sink)
			transmitters[0].source = localSource
			
			remoteSource = MulticastSource(names[1])
			remoteSource.host = remoteHost
			remoteSource.transmitter = transmitters[1]
			sink = Sink(host=self, receiver=receivers[0])
			remoteSource.sinks.append(sink)
			transmitters[1].source = remoteSource
			
			self.sources.append(localSource)
			remoteHost.sources.append(remoteSource)
		except Exception, e:
			print "Error adding a connection to %s" % (self.name)
			print e
			
	def addSink(self, sourceName, sink):
		for source in self.sources:
			if sourceName == source.name:
				source.sinks.append(sink)
				return
				
# Models
#------------------------------------------------------------------------------
class Transmitter(simpy.Process):
	network = None
	
	def __init__(self, name):
		simpy.Process.__init__(self, name=name)
		self.source = None
		self.seqNumber = 1
		
	def run(self, data, txRate):
		print "%7.4f Starting transmitter: %s" % (simpy.now(), self.name)
		lastTx = -1000
		
		for sample in data:
			time = sample[0]
			if time >= lastTx + txRate:
				lastTx = time
				self.transmitPacket(sample)
				yield simpy.hold, self, txRate
				
	def transmitPacket(self, sample):
		packet = Packet(txHost=self.source.host, txTime=simpy.now(), \
					    seqNumber=self.seqNumber, data=sample)
		self.seqNumber += 1
		for i, sink in enumerate(self.source.sinks):
			newPacket = copy(packet)
			newPacket.rxHost = sink.host
			link = self.network.findLink(hostFrom=self.source.host, \
		           						 hostTo=sink.host)
			link.simTransmission(sink.receiver, newPacket)
			sink.session.transmittedPackets.append(newPacket)
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
			
class ReceiverRT(simpy.Process):
	
	def __init__(self, name):
		simpy.Process.__init__(self, name=name)
		self.seqNumber = 0
		self.receiveBuffer = []
		self.plotter = None
		
	def run(self, samplingInterval, plotter):
		self.plotter = plotter
		while True:
			yield simpy.hold, self, samplingInterval
		
	def receivePacket(self, packet):
		print "%7.4f Receiving packet %1d: %s -> %s" % \
			  (simpy.now(), packet.seqNumber, packet.txHost.name, packet.rxHost.name)
		self.plotter.time.append(simpy.now())
		#self.plotter.data.append(simpy.now())
		self.plotter.data.append(packet.data[1])

class Plotter(simpy.Process):
	
	def __init__(self, name):
		simpy.Process.__init__(self, name=name)
		self.time = []
		self.data = []
		
	def run(self, timeStep):
		pylab.ion()
		yield simpy.hold, self, 200
		
		while True:
			yield simpy.hold, self, timeStep
			pylab.plot(self.time, self.data)
			pylab.draw()

# Data
#------------------------------------------------------------------------------
numOfSamples = 1000
samplingInterval = 10
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
hostA = Host(name='HostA')
hostB = Host(name='HostB')

# Create network
network = Network()
Host.network = network
Transmitter.network = network
a_b_link = Link(hostFrom=hostA, hostTo=hostB, delay=100, jitter=10, packetLoss=0)
b_a_link = Link(hostFrom=hostB, hostTo=hostA, delay=100, jitter=10, packetLoss=0)
network.links.append(a_b_link)
network.links.append(b_a_link)

# Create algorithms
transmitter = Transmitter(name='SynchA')
simpy.activate(transmitter, transmitter.run(stateData, txRate))
if realTimeMode:
	receiver = ReceiverRT(name='SnapB')
	plotter = Plotter(name='ReceivedData')
	simpy.activate(receiver, receiver.run(samplingInterval=samplingInterval, plotter=plotter))
	simpy.activate(plotter, plotter.run(timeStep=1000))
else:
	receiver = Receiver('SnapB')

# Connect hosts
hostA.addSimplexPath(name='SimplePath', remoteHost=hostB, transmitter=transmitter, receiver=receiver)

if realTimeMode:
	simpy.simulate(real_time=True,rel_speed=12, until=maxTime)
else:
	simpy.simulate(until=maxTime)


# Analysis
#------------------------------------------------------------------------------
source = hostA.sources[0]
session = source.sinks[0].session
packets = session.transmittedPackets

print "\n"
for packet in packets:
	print str(packet)
