from flair_api import make_client

client = make_client('n3pdxfil6RboAIFsFiSx0sTSyxzR06SWvoWEiEm3', '77Dmrd52VI8fLw21ioh77xFMvqcsMP24Z2z5zyFqL1jUZCTQhgkl8QNQhGpd', 'https://api.flair.co/')

# retrieve a list of structures available to this account
structures = client.get('structures')

# get a single room by id
rooms = client.get('rooms')

for room in rooms:
  print (room.attributes['name'])
  try:
    vents = room.get_rel('vents')
    for vent in vents:
      print (vent.attributes['name'])
  except Exception as ex:
    pass
