#!/usr/bin/python
"""
Basicly what this script does :

* First it retrieve from the Overpass API every line of the TAG network (id 3300434)

* Each line has 2 to 6 directions (also known as mutliple banches).

* Each direction has a sorted list of station. Some of them are shared (main trunk)

* By comparing each directions there are merged into 2.

* Returns a list of each lines with osmID, line Nane, list of stations for each direction.

"""


import sys
import console
import xml.dom.minidom
import itertools
from pprint import pprint
import json
import getopt
from bs4 import BeautifulSoup

import OsmTagStations as ots
import localPageCache

try:
    opts, args = getopt.getopt(sys.argv[1:], "v", ["print"])
except getopt.GetoptError:
    print('getopt error in osmAPI.py')
    sys.exit(2)

verbose = False
for opt, arg in opts:
    if opt == '-v':
        verbose = True


def main():
    parseOsmTAGRelation()

'''
OSM has a list of lines for the TAG network.
Data can be retrieved using the Overpass API.
'''
def parseOsmTAGRelation() :
    networkId = '3921495'
    url = "http://overpass-api.de/api/interpreter?data=relation%28"+networkId+"%29%3Brel%28r%29%3Bout%20body%3B%0A"
    s = localPageCache.getPage(url)

    # Parsing the Overpass API result of TAG relation 3300434
    soup = BeautifulSoup(s)
    lineRelations = soup.findAll("relation")

    # Progress bar is a cool feature.
    (termWidth, height) = console.getTerminalSize()
    #total = len(lineRelations)
    #index = 0

    lines = list()

    for aLine in lineRelations :  # 48 elements
        # index = index+1
        # percentage = index / total
        # sys.stdout.write("\r")
        # for i in range(int(termWidth*percentage)):
        #     sys.stdout.write("-")
        #     sys.stdout.flush()
        myLine = OsmLine(aLine)  # each objects parse the data related to its line
        lines.append(myLine)

    jsonOutput = json.dumps(lines, indent=4, sort_keys=True, cls=OsmLineEncoder)

    if verbose:
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
        self.terminusA = list() 
        self.terminusB = list()
        
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
    def dispatchDirections(self, index):

        # Using the first direction for the base of the comparison.
        baseStations = self.directions[0].stations()

        # First direction is sensA by default
        if index < len(baseStations):
            aId =  baseStations[index]
        else:
            print ("   ", len(baseStations), self.name)
            quit()

        # Related stations are all the stations at location (== same name)
        relatedStations = ots.relatedStations(aId)

        # Search for a station present in every direction
        for aDirection in self.directions[1:]:  # Since index 0 is the base for this, skipping it every time.
            if ots.isSoloStation(aId):
                if aId not in aDirection.stations():
                    return
            else:
                if not set.intersection(set(aDirection.stations()),set(relatedStations)):
                    return False

        # Skipping the station if its present multiple times on a track (ex: dead-end loop in middle of the line)
        if ots.hasDuplicateName(baseStations, index):
            return False

        # Skipping when previous and next station == previous station (occurs in dead-end loop like above)
        if index-1 >= 0 and index+1 < len(self.directions[0].stations()):  # bounds checking
            if ots.stationName(baseStations[index-1]) == ots.stationName(baseStations[index+1]):
                return False

        # At this point we have to station we need
        # now comparing the next or the previous station

        nextStationId = baseStations[index+1]

        if(index > 0):
            previousStationId = baseStations[index-1]

        # Lists for where the station will be added
        sensA = [self.directions[0]]  # Already adding stations of the first direction
        sensB = list()
        self.terminusA.append(self.directions[0][-1])

        # Actually dispatching the directions
        for aDirection in self.directions[1:]:  # skipping index 0
            # Index of the sharedStation for this direction
            # The intersection should return only one item.
            # If not there is a problem in selecting the station
            if ots.isSoloStation(aId):
                sharedStation = [aId]
            else:
                sharedStation = set.intersection(set(aDirection.stations()), set(relatedStations))

            if len(sharedStation) == 1:
                # Index of the station for this direction
                stationIndex = aDirection.stations().index(sharedStation.pop())

                # The next Station is the same than for the 1st sub-direction
                if stationIndex < len(aDirection.stations())-1 and ots.isSameStation(nextStationId, aDirection[stationIndex+1]):
                    sensA.append(aDirection)
                    self.terminusA.append(aDirection[-1])

                    # The previous Station is the same than for the 1st sub-direction
                elif index > 0 and ots.isSameStation(previousStationId, aDirection[stationIndex-1]):
                    sensA.append(aDirection)
                    self.terminusA.append(aDirection[-1])

                # Every other case : It's the opposite direction of 1st sub-direction
                else:
                    self.terminusB.append(aDirection[-1])
                    sensB.append(aDirection)

            else:
                print("ERROR IN SHARED STATION")

        mergedDirectionA = list(itertools.chain.from_iterable(sensA))
        mergedDirectionB = list(itertools.chain.from_iterable(sensB))

        # Removing partial terminus, only keeping branch terminus & trunk terminus
        for aTerminus in self.terminusA:
            # sensA is a list of osmDirection objet, can't iterate directly therefore using itertools
            if mergedDirectionA.count(aTerminus) > 1:
                if(aTerminus == 1804374990):
                    print("coucou", mergedDirectionA.count(aTerminus))
                self.terminusA.remove(aTerminus)
                mergedDirectionA.remove(aTerminus)

        for aTerminus in self.terminusB:
            # sensB is a list of osmDirection objet, can't iterate directly therefore using itertools
            if mergedDirectionB.count(aTerminus) > 1:
                self.terminusB.remove(aTerminus)
                mergedDirectionB.remove(aTerminus)

        # Making a bigList of the stations for each direction. Always with unique values and ordered
        # Ordered is important for the first direction as it will be use to compare with Mobitrans
        self.stationsSensA[:] = unique(itertools.chain.from_iterable(sensA))
        self.stationsSensB[:] = unique(itertools.chain.from_iterable(sensB))
        return True

    def testStationSum(self, directionSet):
        resultSet = set()
        for aDirection in directionSet:
            url = "http://api.openstreetmap.org/api/0.6/relation/"+str(aDirection.id)

            s = localPageCache.getPage(url)
            soup = BeautifulSoup(s)
            orderedStations = soup.findAll(member_role_stop)

            for aStation in orderedStations:
                resultSet.add(int(aStation["ref"]))
        #print([x.id for x in directionSet])
        return len(resultSet)


class OsmLineEncoder(json.JSONEncoder):
    '''
    JSONEncoder for the OSMLine class (and included elements).
    '''
    def default(self, obj):
        if isinstance(obj, OsmLine):
            aDict = dict()
            aDict["name"] = obj.name
            aDict["OsmId"] = obj.relationId
            aDict["sensA"] = obj.stationsSensA
            aDict["sensB"] = obj.stationsSensB
            aDict["terminusA"] = obj.terminusA
            aDict["terminusB"] = obj.terminusB
            return aDict


class OsmDirection(object):
    '''
    Every Line has at least 2 sub-direction, sometimes more.
    This is the representation for each of them
    '''
    def __init__(self, id):
        self.id = int(id)                # OSM reference for the direction
        self.__stations = list()    # ordered list of stations for the direction

    # This class is iterable
    def __iter__(self):
        return iter(self.__stations)

    # Also possible to directly access the stations
    def __getitem__(self, key):
        return self.__stations[key]

    def stations(self):
        if len(self.__stations) == 0:
            self.fetchStations()
        return self.__stations

    # Fetch the ordered list of stations
    def fetchStations(self):

        # Overpass doesn't provide a ordered detailled list, so it uses the base OSM API.
        url = "http://api.openstreetmap.org/api/0.6/relation/" + str(self.id)
        #f = urlopen(url)
        #s = f.read()
        s = localPageCache.getPage(url)
        soup = BeautifulSoup(s)
        orderedStations = soup.findAll(member_role_stop)

        for aStation in orderedStations:
            # Only storing the OSM node ID of the station
            self.__stations.append(int(aStation["ref"]))
            if not ots.hasStation(int(aStation["ref"])):
                print("Error : ", int(aStation["ref"]), "not present")


def member_role_stop(tag):
    '''
    fonction called by BeautifulSoup for find XML member nodes where role="stop"
    '''
    return tag.name == "member" and tag['role'] == "stop"


def unique(seq):
    """
    Return a list with unique elements and with the same order as the one given in parameters
    """
    seen = set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            yield item


def printXML(xmlStr):
    xml2 = xml.dom.minidom.parseString(xmlStr)
    print(xml2.toprettyxml())


if __name__ == '__main__':
    main()
