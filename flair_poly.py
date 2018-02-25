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
from flair_api import make_client

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
                self.api_client = make_client(self.client_id,self.client_secret,'https://api.flair.co/')
                
                self.discover()
                # self.query()
                
        except Exception as ex:
            LOGGER.error('Error starting Flair NodeServer: %s', str(ex))

    def shortPoll(self):
        pass

    def longPoll(self):
        pass

    def query(self):
        for node in self.nodes:
            if self.nodes[node].queryON == True :
                self.nodes[node].query()
        
    def discover(self, *args, **kwargs):
        time.sleep(1)
        
        structures = self.api_client.get('structures')
        for structure in structures:
            strHash = str(int(hashlib.md5(structure.attributes['name'].encode('utf8')).hexdigest(), 16) % (10 ** 8))
            self.addNode(FlairStructure(self, strHash, strHash,structure.attributes['name'],structure))
            time.sleep(1)
            rooms = structure.get_rel('rooms')
            roomNumber = 1
            for room in rooms:
                strHashRoom = str(int(hashlib.md5(room.attributes['name'].encode('utf8')).hexdigest(), 16) % (10 ** 8))
                try:
                    vents = room.get_rel('vents')
                    for vent in vents :
                        strHashVents = str(int(hashlib.md5(vent.attributes['name'].encode('utf8')).hexdigest(), 16) % (10 ** 8))
                        self.addNode(FlairStructure(self, strHash, strHashRoom + strHashVents,'R' + str(roomNumber) + '_' + vent.attributes['id'],vent))
                except Exception as ex:
                    pass
                
                try:
                    pucks = room.get_rel('pucks')
                    for puck in pucks :
                        strHashPucks = str(int(hashlib.md5(puck.attributes['name'].encode('utf8')).hexdigest(), 16) % (10 ** 8))
                        self.addNode(FlairStructure(self, strHash, strHashRoom + strHashPucks,'R' + str(roomNumber) + '_' + puck.attributes['name'],puck))
                except Exception as ex2:
                    pass
                
                roomNumber = roomNumber + 1
    def delete(self):
        LOGGER.info('Deleting Flair')
        
    id = 'controller'
    commands = {}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
    
class FlairStructure(polyinterface.Node):

    def __init__(self, controller, primary, address, name, struct):

        super(FlairStructure, self).__init__(controller, primary, address, name)
        self.queryON = True
        self.name = name
        self.objStructure = struct
   
    def start(self):
        self.setDriver('ST', 1)
        
    def query(self):
        pass
             
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]
    
    id = 'FLAIR_STRUCT'
    commands = {
                }
    
if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('FlairNodeServer')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
