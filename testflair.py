from flair_api import make_client

client = make_client('n3pdxfil6RboAIFsFiSx0sTSyxzR06SWvoWEiEm3', '77Dmrd52VI8fLw21ioh77xFMvqcsMP24Z2z5zyFqL1jUZCTQhgkl8QNQhGpd', 'https://api.flair.co/')

# retrieve a list of structures available to this account
structures = client.get('structures')

# get a single room by id
room = client.get('rooms', id="2")

# fetch vents in a room
# vents = structures.get_rel('vents')

#print (room)

print (structures)
#print (vents)
