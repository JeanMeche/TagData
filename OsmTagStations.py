'''
Module to read station information from a XML file

File comesfrom : http://overpass-api.de/api/interpreter?data=relation%283300434%29%3Brel%28r%29%3Brel%28r%29%3Bnode%28r%29%3Bout%3B

'''

from bs4 import BeautifulSoup
import pprint

         
def hasStation(intId):
    return str(intId) in _stations 
         
def stationById(id):
    return _stations.get(id)                        

def loadAllNodes() :
    aList = list()
    for aNode in _xml.findAll("node"):
        station = dict()
        station["id"] = int(aNode["id"])
        station["lat"] = float(aNode["lat"])
        station["lon"] = float(aNode["lon"])
        station["name"] = aNode.find(k="name")["v"]
        aList.append(station)
    print ("Loaded",len(aList),"stations")
    return aList
        
def stationName(intId):
    return _stations[str(intId)]["name"]        
        
        
"""
It will return if the station is solo
"""        
def isSoloStation(aId):
    return relatedStations(aId) == None
    
"""
This function will return the list of related stations of a station + the station given as input 
If there is none, if will return None
"""    
def relatedStations(aId):
    res = _relatedStations.get(aId)
    if res is None :
        return None
    else :
        return _relatedStations.get(aId).append(aID)
        
def isSameStation(id1, id2) :
    if id1 == id2 :
        return True 
    if not isSoloStation(id1) :  
        return id2 in _relatedStations.get(id1)
    else :
        return False
            
"""
Looks if the station at Index is present multiple times in the given direction
"""        
def hasDuplicateName(dirList, index) :
    theId = dirList[index]
    theName = stationName(theId)    
    for i in range(len(dirList)) : 
        if i != index :
            if stationName(dirList[i]) == theName :
                return True
    return False
    
def distanceBetween(id1, id2): 
    station1 = stationById(id1)
    station2 = stationById(id2)
    return(haversine(station1["lon"], station1["lat"], station2["lon"], station2["lat"]))
        
def parseStations():
    aList = loadAllNodes()
    for aStation in aList:
        found = [x for x in aList if x["name"] == aStation["name"]]
        if(len(found) == 1 ): # this meens there is a unique coordinate for potentially multiple (near) stations  
            _soloStations.append(found[0]["id"])
        else : 
            _relatedStations[aStation["id"]] =  [x["id"] for x in found if x["id"] != aStation["id"]]
                
        _stations[str(aStation["id"])] = aStation


from math import radians, cos, sin, asin, sqrt        
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 

    # 6367 km is the radius of the Earth
    km = 6367 * c 
    meters = "%.2f" % (km * 1000)
    return float(meters)        
        
        
# MISC TEST FUNCTIONS        
        
        
def closestStation() : 

    minDistance = 1000
    
    for station1 in _stations: 
        for station2 in _stations: 
            if station2 is not station1:
                dist = distanceBetween(station1, station2) 
                if dist < minDistance : 
                    s1 = station1
                    s2 = station2
                    minDistance = dist
    print(str(minDistance)+"m", stationById(s1), stationById(s2))                
        



        
print("Loading OSM stations")
file = open("stations.xml", "r")
_s = file.read()
_xml = BeautifulSoup(_s)
_stations=dict()
_relatedStations = dict()
_soloStations = list()
parseStations() # inits soloStations & relatedStations    


