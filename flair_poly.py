#!/usr/bin/env python3

"""
This is a NodeServer for Flair Vent System written by automationgeek (Jean-Francois Tremblay) 
based on the NodeServer template for Polyglot v2 written in Python2/3 by Einstein.42 (James Milne) milne.james@gmail.com
Using the Flair API Client - https://github.com/flair-systems/flair-api-client-py
"""

import polyinterface
import hashlib
import time
import json
import sys
from threading import Thread
from flair_api import make_client
from flair_api import ApiError
from flair_api import EmptyBodyException

LOGGER = polyinterface.LOGGER
SERVERDATA = json.load(open('server.json'))
VERSION = SERVERDATA['credits'][0]['version']

class Controller(polyinterface.Controller):

    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Flair'
        self.initialized = False
        self.queryON = False
        self.client_id = ""
        self.client_secret = ""
        self.api_client = None
        self.tries = 0
        self.discovery_thread = None

    def start(self):
        LOGGER.info('Started Flair for v2 NodeServer version %s', str(VERSION))
        self.setDriver('ST', 0)
        try:
            if 'client_id' in self.polyConfig['customParams']:
                self.client_id = self.polyConfig['customParams']['client_id']

            if 'client_secret' in self.polyConfig['customParams']:
                self.client_secret = self.polyConfig['customParams']['client_secret']

            if self.client_id == "" or self.client_secret == "" :
                LOGGER.error('Flair requires \'client_id\' \'client_secret\' parameters to be specified in custom configuration.')
                return False
            else:
                self.setDriver('ST', 1)
                
                # Connect to Flair API
                self.discover()
                
        except Exception as ex:
            LOGGER.error('Error starting Flair NodeServer: %s', str(ex))

    def shortPoll(self):
        pass

    def longPoll(self):
        if self.discovery_thread is not None:
            if self.discovery_thread.isAlive():
                LOGGER.debug('Skipping longPoll() while discovery in progress...')
                return
            else:
                self.discovery_thread = None
                self.api_client = make_client(self.client_id,self.client_secret,'https://api.flair.co/')
                self.discover()
        else:
            self.api_client = make_client(self.client_id,self.client_secret,'https://api.flair.co/')
            self.discover()
     
    def query(self):
        for node in self.nodes:
            if self.nodes[node].queryON == True :
                self.nodes[node].query()
    
    def runDiscover(self,command):
        self.discover()
    
    def discover(self, *args, **kwargs):  
        if self.discovery_thread is not None:
            if self.discovery_thread.isAlive():
                LOGGER.info('Discovery is still in progress')
                return
        self.discovery_thread = Thread(target=self._discovery_process)
        self.discovery_thread.start()

    def _discovery_process(self):
        time.sleep(1)
        structures = self.api_client.get('structures')
        for structure in structures:
            strHash = str(int(hashlib.md5(structure.attributes['name'].encode('utf8')).hexdigest(), 16) % (10 ** 8))
            self.addNode(FlairStructure(self, strHash, strHash,structure.attributes['name'],structure))
            time.sleep(5)
            rooms = structure.get_rel('rooms')
            roomNumber = 1
            for room in rooms:
                strHashRoom = str(int(hashlib.md5(room.attributes['name'].encode('utf8')).hexdigest(), 16) % (10 ** 8))
                self.addNode(FlairRoom(self, strHash,strHashRoom,'R' + str(roomNumber) + '_' + room.attributes['name'],room))
                
                try:
                    pucks = room.get_rel('pucks')
                    for puck in pucks:
                        strHashPucks = str(int(hashlib.md5(puck.attributes['name'].encode('utf8')).hexdigest(), 16) % (10 ** 8))
                        self.addNode(FlairPuck(self, strHash,strHashRoom[:4]+strHashPucks,'R' + str(roomNumber) + '_' + puck.attributes['name'],puck,room))
                except EmptyBodyException as ex:
                    pass
            
                try:
                    vents = room.get_rel('vents')
                    for vent in vents :
                        strHashVents = str(int(hashlib.md5(vent.attributes['name'].encode('utf8')).hexdigest(), 16) % (10 ** 8))
                        self.addNode(FlairVent(self, strHash, strHashRoom[:4]+strHashVents ,'R' + str(roomNumber) + '_' + vent.attributes['name'],vent,room))
                except EmptyBodyException as ex:
                    pass
                
                roomNumber = roomNumber + 1
                           
    def delete(self):
        LOGGER.info('Deleting Flair')
        
    id = 'controller'
    commands = {'DISCOVERY' : runDiscover}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
    
class FlairStructure(polyinterface.Node):

    SPM = ['Home Evenness Flair SetPoint','Home Evenness Follow Third Party','Home Evenness For Active Rooms Follow Third Party']
    HAM = ['Manual','Third Party Home Away','Flair Autohome Autoaway']
    MODE = ['manual','auto']
    
    def __init__(self, controller, primary, address, name, struct):

        super(FlairStructure, self).__init__(controller, primary, address, name)
        self.queryON = True
        self.name = name
        self.objStructure = struct
   
    def start(self):
        self.query()
   
    def setMode(self, command):
        try :
            self.objStructure.update(attributes={'mode': self.MODE[int(command.get('value'))]})        
        except ApiError as ex:
            pass
       
        self.setDriver('GV4', self.MODE.index(self.objStructure.attributes['mode']))

    def setAway(self, command):
        try:
            self.objStructure.update(attributes={'home-away-mode': self.HAM[int(command.get('value'))]})
        except ApiError as ex:
            pass

        self.setDriver('GV5', self.HAM.index(self.objStructure.attributes['home-away-mode']))
    
    def setEven(self, command):
        try:    
            self.objStructure.update(attributes={'set-point-mode': self.SPM[int(command.get('value'))]})
        except ApiError as ex:
            pass
        
        self.setDriver('GV6', self.SPM.index(self.objStructure.attributes['set-point-mode']))

    def query(self):
        if  self.objStructure.attributes['is-active'] is True:
            self.setDriver('GV2', 1)
        else:
            self.setDriver('GV2', 0)
        
        self.setDriver('CLITEMP', round(self.objStructure.attributes['set-point-temperature-c'],1))
        
        if  self.objStructure.attributes['home'] is True:
            self.setDriver('GV3', 1)
        else:
            self.setDriver('GV3', 0)
                
        self.setDriver('GV6', self.SPM.index(self.objStructure.attributes['set-point-mode']))
        self.setDriver('GV5', self.HAM.index(self.objStructure.attributes['home-away-mode']))
        self.setDriver('GV4', self.MODE.index(self.objStructure.attributes['mode']))
                
    drivers = [{'driver': 'GV2', 'value': 0, 'uom': 2},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 4},
                {'driver': 'GV3', 'value': 0, 'uom': 2},
                {'driver': 'GV4', 'value': 0, 'uom': 25},
                {'driver': 'GV5', 'value': 0, 'uom': 25},
                {'driver': 'GV6', 'value': 0, 'uom': 25}]
    
    id = 'FLAIR_STRUCT'
    commands = {'SET_MODE' : setMode, 
                'SET_AWAY' : setAway, 
                'SET_EVENESS' : setEven,
                'QUERY': query }
   
class FlairVent(polyinterface.Node):

    def __init__(self, controller, primary, address, name, vent,room):

        super(FlairVent, self).__init__(controller, primary, address, name)
        self.queryON = True
        self.name = name
        self.objVent = vent
        self.objRoom = room
        
    def start(self):
        self.query()
        
    def setOpen(self, command):
        
        try:
            self.objVent.update(attributes={'percent-open': int(command.get('value'))})
        except ApiError as ex:
            pass
        
        self.setDriver('GV1', self.objVent.attributes['percent-open'])
        
    def query(self):
        if  self.objVent.attributes['inactive'] is True:
            self.setDriver('GV2', 1)
        else:
            self.setDriver('GV2', 0)
            
        self.setDriver('GV1', self.objVent.attributes['percent-open'])
             
    drivers = [{'driver': 'GV2', 'value': 0, 'uom': 2},
              {'driver': 'GV1', 'value': 0, 'uom': 51}]
    
    id = 'FLAIR_VENT'
    commands = { 'SET_OPEN' : setOpen,
                 'QUERY': query}
    
class FlairPuck(polyinterface.Node):

    def __init__(self, controller, primary, address, name, puck,room):

        super(FlairPuck, self).__init__(controller, primary, address, name)
        self.queryON = True
        self.name = name
        self.objPuck = puck
        self.objRoom = room
        
    def start(self):
        self.query()
            
    def query(self):
        if  self.objPuck.attributes['inactive'] is True:
            self.setDriver('GV2', 1)
        else:
            self.setDriver('GV2', 0)
            
        self.setDriver('CLITEMP', round(self.objPuck.attributes['current-temperature-c'],1))
        self.setDriver('CLIHUM', self.objPuck.attributes['current-humidity'])
             
    drivers = [ {'driver': 'GV2', 'value': 0, 'uom': 2},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 4},
                {'driver': 'CLIHUM', 'value': 0, 'uom': 22}]
    
    id = 'FLAIR_PUCK'
    commands = {  'QUERY': query }

class FlairRoom(polyinterface.Node):

    def __init__(self, controller, primary, address, name,room):

        super(FlairRoom, self).__init__(controller, primary, address, name)
        self.queryON = True
        self.name = name
        self.objRoom = room
        
    def start(self):
        self.query()
            
    def query(self):
        if  self.objRoom.attributes['active'] is True:
            self.setDriver('GV2', 0)
        else:
            self.setDriver('GV2', 1)
            
        self.setDriver('CLITEMP', round(self.objRoom.attributes['current-temperature-c'],1))
        
        if self.objRoom.attributes['current-humidity'] is None:
            self.setDriver('CLIHUM',0)
        else:
            self.setDriver('CLIHUM', self.objRoom.attributes['current-humidity'])
        
        self.setDriver('CLISPC', round(self.objRoom.attributes['set-point-c'],1))
    
    def setTemp(self, command):
        try:
            self.objRoom.update(attributes={'set-point-c': command.get('value')})
        except ApiError as ex:
            pass
        
        self.setDriver('CLISPC', round(self.objRoom.attributes['set-point-c'],1))
            
    drivers = [ {'driver': 'GV2', 'value': 0, 'uom': 2},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 4},
                {'driver': 'CLIHUM', 'value': 0, 'uom': 22},
                {'driver': 'CLISPC', 'value': 0, 'uom': 4}]
    
    id = 'FLAIR_ROOM'
    commands = { 'QUERY': query, 
                 'SET_TEMP': setTemp }    
    
if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('FlairNodeServer')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
