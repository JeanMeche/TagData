#!/usr/bin/python
import sys, os, console
from urllib.request import urlopen
import xml.dom.minidom
import itertools
import pprint
import json
from bs4 import BeautifulSoup

import OsmTagStations as ots

def main() :
    parseOsmTAGRelation(True)

'''
OSM has a list of lines for the TAG network. 
Data can be retrieved using the Overpass API. 
'''
def parseOsmTAGRelation(doPrint) :
    url = "http://overpass-api.de/api/interpreter?data=relation%283300434%29%3Brel%28r%29%3Bout%20body%3B%0A"
    f = urlopen(url)
    s = f.read()

    #Parsing the Overpass API result of TAG relation 3300434
    soup = BeautifulSoup(s)
    lineRelations = soup.findAll("relation")

    #Progress bar is a cool feature. 
    (termWidth, height) = console.getTerminalSize()
    total = len(lineRelations)
    index=0
    
    
    lines = list()
    for aLine in lineRelations : #48 elements
        index = index+1 
        percentage = index/total
        sys.stdout.write("\r")
        for i in range(int(termWidth*percentage)):
            sys.stdout.write("-")
            sys.stdout.flush()
        myLine = OsmLine(aLine) # each objects parse the data related to its line 
        lines.append(myLine)

    jsonOutput = json.dumps(lines,indent=4,sort_keys=True, cls=OsmLineEncoder)
    
    if doPrint : 
        print(jsonOutput)
    
    return jsonOutput


'''
This class represents the data parsed for OSM for a particular line
It has 
* The line name (1,2,3,A,B etc)
* The stations for each directions (lines have 2 directions)
* The ID of the line on OSM 
'''
class OsmLine :
    def __init__(self,node):
        self.name = node.find(k="name")['v']
        self.relationId = int(node["id"])
        directions = node.findAll("member") 
        self.directions = list()
        self.stationsSensA= list() # stationID for a given Sens
        self.stationsSensB= list() # stationID for a given Sens
        
        for aDirection in directions:
            self.directions.append(OsmDirection(aDirection["ref"]))
        
        index = 0
        while not self.dispatchDirections(index): #While It can't dispatch, 
            index = index+1;
        
    def __repr__(self):
        return "OsmLine()"


    def __str__(self):
        return str(self.relationId) + " - ligne : " + self.name + " - " + str(len(self.directions)) + " directions"    
        
    # Splitting the directions in 2 categories 
    # Station at Index must be a station shared by each subDirection
    # Returns false if it could not disptach the station with the index
    def dispatchDirections(self, index) :
                        
        # Using the first direction for the base of the comparaison.         
        baseStations = self.directions[0].stations() 
        
        # First direction is sensA by default
        aId =  baseStations[index]
        
        # Related stations are all the stations at location (== same name)
        relatedStations = ots.relatedStations(aId)
        
        # Search for a station present in every direction 
        for aDirection in self.directions[1:] :         #Since index 0 is the base for this, skipping it every time.
            if not set.intersection(set(aDirection.stations()),set(relatedStations)) :
                return False
         
        # Skipping the station if its present multiple times on a track (ex: dead-end loop in middle of the line)
        if ots.hasDuplicateName(baseStations.stations(), index) :
            return False

        # Skipping when previous and next station == previous station (occures in dead-end loop like above)
        if index-1 >= 0 and index+1 < len(self.directions[0].stations()) :  # bounds checking 
            if ots.stationName(baseStations[index-1]) == ots.stationName(baseStations[index+1]) : 
                return False
        
        # At this point we have to station we need 
        # now comparing the next or the previous station        
                            
        nextStationId = baseStations[index+1] 

        if(index > 0) :
            previousStationId = baseStations[index-1] 
        

        # Lists for where the station will be added 
        sensA = [self.directions[0]] #Already adding stations of the first direction 
        sensB = list() 
        
        # Actally dispatching the directions
        for aDirection in self.directions[1:] : #skipping index 0 

            # Index of the sharedStation for this direction 
            # The intersection should return only one item. 
            # If not there is a problem in selecting the station
            sharedStation = set.intersection(set(aDirection.stations()),set(relatedStations))

            if len(sharedStation) == 1 : 
                # Index of the station for this direction 
                stationIndex = aDirection.stations().index(sharedStation.pop())
                
                # The next Station is the same than for the 1st sub-direction 
                if stationIndex < len(aDirection.stations())-1 and ots.isSameStation(nextStationId, aDirection[stationIndex+1]) :
                    sensA.append(aDirection)
                    
                # The previous Station is the same than for the 1st sub-direction     
                elif index > 0 and ots.isSameStation(previousStationId, aDirection[stationIndex-1]) : 
                    sensA.append(aDirection)
                    
                # Every other case : It's the opposite direction of 1st sub-direction 
                else :
                    sensB.append(aDirection)                         
            else :
                print("ERROR IN SHARED STATION")    
                
        # Making a bigList of the stations for each direction. Always with unique values and ordered
        # Ordered is important for the first direction as it will be use to compare with Mobitrans
        self.stationsSensA[:] = unique(itertools.chain.from_iterable(sensA))
        self.stationsSensB[:] = unique(itertools.chain.from_iterable(sensB))
        return True

    def printNode(self):
        xml2 = xml.dom.minidom.parseString(self.node)
        pretty_xml_as_string = xml2.toprettyxml()

    def testStationSum(self, directionSet) : 
        resultSet = set()  
        for aDirection in directionSet:
            url = "http://api.openstreetmap.org/api/0.6/relation/"+str(aDirection.id)
            f = urlopen(url)
            s = f.read()        
            soup = BeautifulSoup(s)
            orderedStations = soup.findAll(member_role_stop)
        
            for aStation in orderedStations:
                resultSet.add(int(aStation["ref"]))
        #print([x.id for x in directionSet])
        return len(resultSet)    
        


'''
    JSONEncoder for the OSMLine class (and included elements). 
'''
class OsmLineEncoder(json.JSONEncoder):
    def default(self, obj):
       if isinstance(obj, OsmLine) :
         aDict = dict()
         aDict["name"] = obj.name
         aDict["OsmId"] = obj.relationId
         aDict["sensA"] = obj.stationsSensA
         aDict["sensB"] = obj.stationsSensB
         return aDict;
        
        
        
'''
    Every Line has at least 2 sub-direction, sometimes more. 
    This is the representation for each of them
'''
class OsmDirection(object) :
    def __init__(self, id) :
        self.id = int(id)                # OSM reference for the direction
        self.__stations = list()    # ordered list of stations for the direction

    # This class is iterable
    def __iter__(self):
        return iter(self.__stations)
    
    # Also possible to directly access the stations 
    def __getitem__(self, key) :
        return self.__stations[key]

    def stations(self) :
        if( len(self.__stations) == 0 ) :
            self.fetchStations()
        return self.__stations
    
    # Fetch the ordered list of stations 
    def fetchStations(self) :     
        
        # Overpass doesn't provide a ordered detailled list, so it uses the base OSM API. 
        url = "http://api.openstreetmap.org/api/0.6/relation/" + str(self.id)
        f = urlopen(url)
        s = f.read()        
        soup = BeautifulSoup(s)
        orderedStations = soup.findAll(member_role_stop)
        
        for aStation in orderedStations:
            # Only storing the OSM node ID of the station 
            self.__stations.append(int(aStation["ref"]))
            if not ots.hasStation(int(aStation["ref"])):
                print("Error : ", int(aStation["ref"]), "not present") 
#END_DEF class            
            
'''
    fonction called by BeautifulSoup for find XML member nodes where role="stop"
'''
def member_role_stop(tag):
        return tag.name == "member" and tag['role'] == "stop" 

def unique( seq ):
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add( item )
            yield item

def printXML(xmlStr): 
    xml2 = xml.dom.minidom.parseString(xmlStr)
    print(xml2.toprettyxml())

if __name__ == '__main__' :
    main()
