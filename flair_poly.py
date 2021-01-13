#!/usr/bin/env python3

"""
This is a NodeServer for Flair Vent Sys/tem written by automationgeek (Jean-Francois Tremblay) 
based on the NodeServer template for Polyglot v2 written in Python2/3 by Einstein.42 (James Milne) milne.james@gmail.com
Using the Flair API Client - https://github.com/flair-systems/flair-api-client-py
"""

import polyinterface
import hashlib
import time
import json
import sys
from copy import deepcopy
from threading import Thread
from flair_api import make_client
from flair_api import ApiError
from flair_api import EmptyBodyException

LOGGER = polyinterface.LOGGER
SERVERDATA = json.load(open('server.json'))
VERSION = SERVERDATA['credits'][0]['version']

def get_profile_info(logger):
    pvf = 'profile/version.txt'
    try:
        with open(pvf) as f:
            pv = f.read().replace('\n', '')
    except Exception as err:
        logger.error('get_profile_info: failed to read  file {0}: {1}'.format(pvf,err), exc_info=True)
        pv = 0
    f.close()
    return { 'version': pv }

class Controller(polyinterface.Controller):

    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Flair'
        self.initialized = False
        self.queryON = True
        self.client_id = ""
        self.client_secret = ""
        self.api_client = None
        self.tries = 0
        self.discovery_thread = None
        self.hb = 0

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
                self.check_profile()
                self.setDriver('ST', 1, True)
                self.reportDrivers()
                
                # Connect to Flair API
                self.discover()
                self.heartbeat()
 
                
        except Exception as ex:
            LOGGER.error('Error starting Flair NodeServer: %s', str(ex))
            

    def shortPoll(self):
        if self.discovery_thread is not None:
            if self.discovery_thread.is_alive():
                LOGGER.debug('Skipping shortPoll() while discovery in progress...')
            else:
                self.discovery_thread = None
        self.query()
            
    def longPoll(self):
        self.heartbeat()
        if self.discovery_thread is not None:
            if self.discovery_thread.is_alive():
                LOGGER.debug('Skipping longPoll() while discovery in progress...')
                return	
        self.discovery_thread = None	
        self.discover()
    
    def check_profile(self):
        self.profile_info = get_profile_info(LOGGER)
        # Set Default profile version if not Found
        cdata = deepcopy(self.polyConfig['customData'])
        LOGGER.info('check_profile: profile_info={0} customData={1}'.format(self.profile_info,cdata))
        if not 'profile_info' in cdata:
            cdata['profile_info'] = { 'version': 0 }
        if self.profile_info['version'] == cdata['profile_info']['version']:
            self.update_profile = False
        else:
            self.update_profile = True
            self.poly.installprofile()
        LOGGER.info('check_profile: update_profile={}'.format(self.update_profile))
        cdata['profile_info'] = self.profile_info
        self.saveCustomData(cdata)

    def install_profile(self,command):
        LOGGER.info("install_profile:")
        self.poly.installprofile()
    
    def heartbeat(self):
        LOGGER.debug('heartbeat hb={}'.format(str(self.hb)))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0
    
    def query(self):
        for node in self.nodes:
            if self.nodes[node].address != self.address and self.nodes[node].queryON == True :
                self.nodes[node].query()
        self.reportDrivers()
    
    def runDiscover(self,command):
        self.discover()
    
    def discover(self, *args, **kwargs):  
        if self.discovery_thread is not None:
            if self.discovery_thread.is_alive():
                LOGGER.info('Discovery is still in progress')
                return
        self.discovery_thread = Thread(target=self._discovery_process)
        self.discovery_thread.start()

    def _discovery_process(self):
        
        try:
            self.api_client = make_client(self.client_id,self.client_secret,'https://api.flair.co/')
            structures = self.api_client.get('structures')
        except ApiError as ex:
            LOGGER.error('Error _discovery_process: %s', str(ex))
            
        for structure in structures:
            strHash = str(int(hashlib.md5(structure.attributes['name'].encode('utf8')).hexdigest(), 16) % (10 ** 8))
            self.addNode(FlairStructure(self, strHash, strHash,structure.attributes['name'],structure))
            #time.sleep(5)
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
    commands = {    'QUERY': query,        
                    'DISCOVERY' : runDiscover
               }
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
    
class FlairStructure(polyinterface.Node):

    SPM = ['Home Evenness For Active Rooms Flair Setpoint','Home Evenness For Active Rooms Follow Third Party']
    HAM = ['Manual','Third Party Home Away','Flair Autohome Autoaway']
    MODE = ['manual','auto']
    
    def __init__(self, controller, primary, address, name, struct):

        super(FlairStructure, self).__init__(controller, primary, address, name)
        self.queryON = True
        self.name = name
        self.objStructure = struct
   
    def start(self):
        #self.query()
        pass
   
    def setMode(self, command):
        try :
            self.objStructure.update(attributes={'mode': self.MODE[int(command.get('value'))]})  
            self.setDriver('GV4', self.MODE.index(self.objStructure.attributes['mode']), True)
        except ApiError as ex:
            LOGGER.error('Error setMode: %s', str(ex))
       
    def setAway(self, command):
        try:
            self.objStructure.update(attributes={'home-away-mode': self.HAM[int(command.get('value'))]})
            self.setDriver('GV5', self.HAM.index(self.objStructure.attributes['home-away-mode']), True)
        except ApiError as ex:
            LOGGER.error('Error setAway: %s', str(ex))
    
    def setEven(self, command):
        try:    
            self.objStructure.update(attributes={'set-point-mode': self.SPM[int(command.get('value'))]})
            self.setDriver('GV6', self.SPM.index(self.objStructure.attributes['set-point-mode']), True)
        except ApiError as ex:
            LOGGER.error('Error setEven: %s', str(ex))
            
    def query(self):
        try:
            if  self.objStructure.attributes['is-active'] is True:
                self.setDriver('GV2', 1, True)
            else:
                self.setDriver('GV2', 0, True)
            
            self.setDriver('CLITEMP', round(self.objStructure.attributes['set-point-temperature-c'],1), True)

            if  self.objStructure.attributes['home'] is True:
                self.setDriver('GV3', 1, True)
            else:
                self.setDriver('GV3', 0, True)

            self.setDriver('GV6', self.SPM.index(self.objStructure.attributes['set-point-mode']), True)
            self.setDriver('GV5', self.HAM.index(self.objStructure.attributes['home-away-mode']), True)
            self.setDriver('GV4', self.MODE.index(self.objStructure.attributes['mode']), True)
            
        except ApiError as ex:
            LOGGER.error('Error query: %s', str(ex))
            
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
        #self.query()
        pass
        
    def setOpen(self, command):
        
        try:
            self.objVent.update(attributes={'percent-open': int(command.get('value'))})
            self.setDriver('GV1', self.objVent.attributes['percent-open'], True)
        except ApiError as ex:
            LOGGER.error('Error setOpen: %s', str(ex))

    def query(self):
        try:
            if  self.objVent.attributes['inactive'] is True:
                self.setDriver('GV2', 1, True)
            else:
                self.setDriver('GV2', 0, True)

            self.setDriver('GV1', self.objVent.attributes['percent-open'], True)
        
        except ApiError as ex:
            LOGGER.error('Error query: %s', str(ex))
             
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
        #self.query()
        pass
            
    def query(self):
        try:
            if  self.objPuck.attributes['inactive'] is True:
                self.setDriver('GV2', 1)
            else:
                self.setDriver('GV2', 0)

            self.setDriver('CLITEMP', round(self.objPuck.attributes['current-temperature-c'],1), True)
            self.setDriver('CLIHUM', self.objPuck.attributes['current-humidity'], True)
            
        except ApiError as ex:
            LOGGER.error('Error query: %s', str(ex))  
            
    drivers = [ {'driver': 'GV2', 'value': 0, 'uom': 2},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 4},
                {'driver': 'CLIHUM', 'value': 0, 'uom': 51}]
    
    id = 'FLAIR_PUCK'
    commands = {  'QUERY': query }

class FlairRoom(polyinterface.Node):

    def __init__(self, controller, primary, address, name,room):

        super(FlairRoom, self).__init__(controller, primary, address, name)
        self.queryON = True
        self.name = name
        self.objRoom = room
        
    def start(self):
        #self.query()
        pass
            
    def query(self):
        try:
            if self.objRoom.attributes['active'] is True:
                self.setDriver('GV2', 0, True)
            else:
                self.setDriver('GV2', 1, True)

            if self.objRoom.attributes['current-temperature-c'] is not None :
                self.setDriver('CLITEMP', round(self.objRoom.attributes['current-temperature-c'],1), True)
            else:
                self.setDriver('CLITEMP',0, True)

            if self.objRoom.attributes['current-humidity'] is None:
                self.setDriver('CLIHUM',0, True)
            else:
                self.setDriver('CLIHUM', self.objRoom.attributes['current-humidity'], True)

            if self.objRoom.attributes['set-point-c'] is not None:
                self.setDriver('CLISPC', round(self.objRoom.attributes['set-point-c'],1), True)
            else:
                self.setDriver('CLISPC', 0, True)
                
        except ApiError as ex:
            LOGGER.error('Error query: %s', str(ex))  
    
    def setTemp(self, command):
        try:
            self.objRoom.update(attributes={'set-point-c': command.get('value')})
            self.setDriver('CLISPC', round(self.objRoom.attributes['set-point-c'],1), True)

        except ApiError as ex:
            LOGGER.error('Error setTemp: %s', str(ex))

    drivers = [ {'driver': 'GV2', 'value': 0, 'uom': 2},
                {'driver': 'CLITEMP', 'value': 0, 'uom': 4},
                {'driver': 'CLIHUM', 'value': 0, 'uom': 51},
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
