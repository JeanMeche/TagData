#!/usr/bin/env python3

# ToDo mettre bout a bout les ways

import sys, getopt, re
import overpass
import itertools, hashlib
from bs4 import BeautifulSoup
from math import sqrt
import localPageCache
import json
from lxml import etree as ET
from simplekml import Kml
import random

nodesDict = dict()
waysDict = dict()
tramRoutes = dict()
subRoutes = dict()

osmTramIds = [('A', 3921492), ('B',3921491), ('C', 3921484), ('D', 3921494) , ('E',3921488)] # A,B,C,D,E


def main(argv) : 
    try:
        opts, args = getopt.getopt(argv,"v",["print"])
    except getopt.GetoptError:
        print ('lineRoute.py')
        sys.exit(2)
    
    verbose = False
    for opt, arg in opts:
        if opt == '-v' :
            verbose = True


    lineWays = list() 

    for aRelationId in osmTramIds :
        directionsGroupedWays = groupWays(str(aRelationId[1]))
        lineWays.append((directionsGroupedWays, aRelationId[0]))

    mergeMiniSplits(lineWays)
    mergeMidLineTerminus(lineWays)

    mergeOppositeRoutes(lineWays)

#    exportToXml()
    exportToKml()



"""
    Export to KML for subRoutes before merging directions 
"""
def exportToKml2() :
    # KML 
    kml = Kml()
    for aGroupedWayKey in subRoutes :
        aGroupedWay = subRoutes[aGroupedWayKey][0]
        lineNames = ','.join(aGroupedWay.lines)

        coords = list() 
        for aNodeKey in aGroupedWay.nodesList : 
            if type(aNodeKey) is str : 
                aNode = nodesDict[aNodeKey]
                lat = aNode.lat
                lon = aNode.lon
            elif type(aNodeKey) is OsmNode:
                lat = aNodeKey.lat
                lon = aNodeKey.lon
            else :
                lat = aNodeKey[0]
                lon = aNodeKey[1]

            coords.append((lon,lat))

        lin = kml.newlinestring(name="Pathway", description='-', coords= coords)

        r = lambda: random.randint(0,255)
        randomColor = '#ff%02X%02X%02X' % (r(),r(),r()) #random ARGB color 
        lin.style.linestyle.color = randomColor
        lin.style.linestyle.width= 10  # 10 pixels

    kml.save("singlestyle.kml")

def longest_common_subroute(s1, s2):
    m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
    longest, x_longest = 0, 0
    for x in range(1, 1 + len(s1)):
        for y in range(1, 1 + len(s2)):
            if s1[x - 1] == s2[y - 1]:
                m[x][y] = m[x - 1][y - 1] + 1
                if m[x][y] > longest:
                    longest = m[x][y]
                    x_longest = x
            else:
                m[x][y] = 0
    return s1[x_longest - longest: x_longest]


"""
    Export to KML for subRoutes after merging directions 
"""
def exportToKml() :
    # KML 
    kml = Kml()

    for aMergedWayTupleKey in tramRoutes :
        aMergedWayTuple = tramRoutes[aMergedWayTupleKey]
        aMergedWay = aMergedWayTuple[1]
        lineNames = ','.join(aMergedWayTuple[0])

        coords = list() 

        for aCoordTuple in aMergedWay :
            lat = aCoordTuple[0]
            lon = aCoordTuple[1]

            coords.append((lon,lat))

        lin = kml.newlinestring(name="Pathway", description='-', coords= coords)

        r = lambda: random.randint(0,255)
        randomColor = '#ff%02X%02X%02X' % (r(),r(),r())

        lin.style.linestyle.color = randomColor
        lin.style.linestyle.width= 10  # 10 pixels

    kml.save("singlestyle.kml")

"""
    Export subRoutes data to XML 
"""
def exportToXml() :
    root = ET.Element("TramRoutes")
    
    for aGroupedWayKey in subRoutes :
        aGroupedWay = subRoutes[aGroupedWayKey][0]
        lineNames = ','.join(aGroupedWay.lines)
        print(len(aGroupedWay.nodesList), lineNames)

        way = ET.SubElement(root,"route")
        way.set("lines", lineNames)

        for aNodeKey in aGroupedWay.nodesList : 
            aNode = nodesDict[aNodeKey]
            lat = aNode.lat
            lon = aNode.lon
            node = ET.SubElement(way, "node")
            node.set("lat", str("{0:.7f}".format(lat)))
            node.set("lon", str("{0:.7f}".format(lon)))
 
    tree = ET.ElementTree(root)   
    # Writing to file XML a valid XML encoded in UTF-8 (because Unicode FTW) 
    tree.write("lineRoutes.xml", pretty_print=True, encoding="utf-8", xml_declaration=True)


"""
Parsing the ways & nodes informations for a particular line 
"""
def groupWays (relationId) :
    
    # Retrieving the directions for a line
    lineId = "http://api.openstreetmap.org/api/0.6/relation/" + relationId
    s = localPageCache.getPage(lineId)
    soup = BeautifulSoup(s)
    members = soup.findAll("member")
    directionId = [x["ref"] for x in members]
    
    query = """
    <osm-script>
      <id-query type="relation" ref=" """ + relationId + """ "/>
      <recurse type="relation-relation"/>   
            
      <recurse type="relation-way" role="forward" />

     <print mode="body"/>
      <recurse type="down" />
      <print mode="skeleton" order="quadtile"/>
    </osm-script>
    """
    
    s = overpass.query(query)
    soup = BeautifulSoup(s)
    
    nodeNodes = soup.findAll("node")

    for aNode in nodeNodes :
        nodeId = aNode["id"] # Is an number but stored as string
        nodesDict[nodeId] = OsmNode(aNode)

    
    # Parsing the ways 
    wayNodes = soup.findAll("way")
    for aWay in wayNodes : 
        wayId = aWay["id"] # Is an number but stored as string
        waysDict[wayId] = OsmWay(aWay)
    

    directionsGroupedWays = list() # ordered groupedWays for each direction

    # For each direction 
    for aRelationId in directionId :
        
        groupedWays = list()  # the global way with every node of the direction 
        osmApiQuery = "http://api.openstreetmap.org/api/0.6/relation/" + aRelationId
    
        s = localPageCache.getPage(osmApiQuery)
        soup = BeautifulSoup(s)

        members = soup.findAll("member", role=re.compile("forward"))
        
        ways = list()
        for aMember in members :
            ways.append(aMember["ref"])

        subWay =  list()
        shared = len(waysDict[ways[0]].lines) > 1 # wheter the lines starts shared or not. 
        previous = None


        # Merging consecutive ways which have same caracteristicts (shared or not shared)
        for index, aWay in enumerate(ways): 
            # Todo : If merging back into the same pair of lines => averaging the section
            if shared != waysDict[aWay].isShared() :

                mySubWay = groupedWay(subWay, waysDict[previous].lines)

                groupedWays.append(mySubWay)
                subRoutes[mySubWay.id] = (mySubWay, )

                subWay = list()
                shared = not shared
            subWay.extend(waysDict[aWay].nodesList)
            previous = aWay

        mySubWay = groupedWay(subWay, waysDict[aWay].lines)

        groupedWays.append(mySubWay)
        subRoutes[mySubWay.id] = (mySubWay, )

        directionsGroupedWays.append(groupedWays)

        # if groupedWays[-1].lines == ['C'] and groupedWays[-2].lines == ['B','C'] : 
        #     del groupedWays[-1]

    return directionsGroupedWays


def mergeMidLineTerminus(lineWays) : 
    for directionsGroupedWaysTuple in lineWays :
        lineName = directionsGroupedWaysTuple[1]
        directionsGroupedWays = directionsGroupedWaysTuple[0]

        for aDirection in range(0, len(directionsGroupedWays)) :

        # Test the first groupedWay it is part of a bigger groupedWay on another line 
            groupedWays = directionsGroupedWays[aDirection]
            if not groupedWays[0].isShared() and (len(groupedWays) > 1 and groupedWays[1].isShared()) : 
                firstGroupedWay = groupedWays[0]
                secondGroupedWay = groupedWays[1]
                otherLine = list(set(secondGroupedWay.lines) - set(firstGroupedWay.lines))[0]

                firstNodeKey = firstGroupedWay.nodesList[0]
                firstNode = nodesDict[firstNodeKey]

                theOtherDirectionGroupedWays = [directionsGroupedWays for directionsGroupedWays in lineWays if directionsGroupedWays[1] == otherLine]

                directionCount = len(theOtherDirectionGroupedWays[0][0]) # List Compregension result, Tuple

                for direction in range(0,  directionCount) :
                    nodes = nodesOfDirection(theOtherDirectionGroupedWays[0][0][direction]) # List Comprehension Result, Tuple

                    closestNodeKey = min(nodes, key=lambda p: nodeDistance(p, firstNode))
                    closestNode = nodesDict[closestNodeKey]


                    distance = haversine(firstNode.lon, firstNode.lat, closestNode.lon, closestNode.lat)
                    if distance < 20 :  # Lets consider that below 20m, the line starts on the same route as another one 
                        print(lineName, 'is candidate with', otherLine, closestNode, 'at ', distance, 'm')
                        # index = nodes.index(closestNodeKey)
                        # toMerge = nodes[index:]
                        # nodesOfDirection(theOtherDirectionGroupedWays[0][0][direction] = nodes[index:]


        # Do the same thing for the last groupedWay 


def mergeMiniSplits(lineWays) : 
    for directionsGroupedWays in lineWays:
        lineName = directionsGroupedWays[1]
        directionsGroupedWays = directionsGroupedWays[0]

        for aDirection in range(0,len(directionsGroupedWays)) : 

            previous = None 
            shared = len(directionsGroupedWays[aDirection][0].lines) > 1

            for index, aGroupedWay in enumerate(directionsGroupedWays[aDirection]):


                if aGroupedWay.isShared() : # Only looking ahead of sharedLines

                    # Foreach groupedWay head 
                    for someWayIndex in range(index+1, len(directionsGroupedWays[aDirection])) : 
                        someWay = directionsGroupedWays[aDirection][someWayIndex]

                        # We don't want to look to much ahead, just the next shared way
                        if someWayIndex > index+1 + 1 : 
                            break

                        # if we found the same pair of lines 
                        if someWay.isShared() and someWay.lines == aGroupedWay.lines : 

                            currentLineStartIndex = index
                            currentLineEndIndex = someWayIndex

                            # find the other line 
                            theOtherLine = list(set(aGroupedWay.lines) - set([lineName]))
                            if(len(theOtherLine) > 1) :
                                print('WOOOPS ERROR FINDING OTHER LINE')
                            # There should be only 1 line name 
                            theOtherLine = theOtherLine[0]

                            # Search for the other line who shares the groupedWay
                            theOtherDirectionGroupedWays = [directionsGroupedWays for directionsGroupedWays in lineWays if directionsGroupedWays[1] == theOtherLine]
                            if len(theOtherDirectionGroupedWays) != 1 and len(theOtherDirectionGroupedWays[1]) <= 0:
                                print('WOOPS ERROR FINDING OTHER LINE')
                            # There should be only one other line
                            # First element is a tuple (groupedWays, lineName) 
                            theOtherDirectionGroupedWays = theOtherDirectionGroupedWays[0][0]

                            # Find the right direction for the line we found 
                            directionGroupedWay = [x for x in theOtherDirectionGroupedWays if aGroupedWay in x]
                            directionGroupedWay = directionGroupedWay[0] # There should be only one item

                            # Indexes 
                            firstGroupedWay = directionGroupedWay.index(aGroupedWay)
                            secondGroupedWay = directionGroupedWay.index(someWay)

                            # Keeping first as lowest index 
                            if(firstGroupedWay > secondGroupedWay) :
                                firstGroupedWay, secondGroupedWay = secondGroupedWay, firstGroupedWay


                            # Listing the nodes that need to be merged of first way
                            mergedNodes1 = list()
                            mergedNodes2 = list()
                            for someWayIndex1 in range(index+1, someWayIndex) :
                                someWay = directionsGroupedWays[aDirection][someWayIndex1] 
                                mergedNodes1.extend(someWay.nodesList)

                            for someWayIndex2 in range(firstGroupedWay+1, secondGroupedWay):
                                someWay = directionGroupedWay[someWayIndex2]
                                mergedNodes2.extend(someWay.nodesList)

                            mergedNodes = list()
                            for aNode in mergedNodes1 : 
                                nodeCoor =  (float(nodesDict[aNode].lat), float(nodesDict[aNode].lon))
                                nearestNode = min(mergedNodes2, key=lambda p: nodeDistance(p, nodeCoor))

                                nearestNodeCoord = (float(nodesDict[nearestNode].lat), float(nodesDict[nearestNode].lon))

                                lat = (float(nearestNodeCoord[0])+float(nodeCoor[0]))/2
                                lon = (float(nearestNodeCoord[1])+float(nodeCoor[1]))/2
                                lat = str("{0:.7f}".format(lat))
                                lon = str("{0:.7f}".format(lon))

                                mergedNodes.append(OsmNode({'lat' : lat, 'lon' : lon}))

                            # Merge the previous, the new and the next groupedWay into one 
                            # directionsGroupedWays[aDirection][currentLineStartIndex].nodesList.extend(mergedNodes)
                            # directionsGroupedWays[aDirection][currentLineStartIndex].nodesList.extend(directionsGroupedWays[aDirection][currentLineEndIndex].nodesList)

                            subRoutes[directionsGroupedWays[aDirection][currentLineStartIndex].id][0].nodesList.extend(mergedNodes)
                            subRoutes[directionsGroupedWays[aDirection][currentLineStartIndex].id][0].nodesList.extend(directionsGroupedWays[aDirection][currentLineEndIndex].nodesList)
                            
                            # Removing from the subRoutes dict the ways that don't exist anymore
                            del subRoutes[directionsGroupedWays[aDirection][currentLineEndIndex].id]
                            del subRoutes[directionsGroupedWays[aDirection][currentLineStartIndex+1].id]

                            #Remove for the current direction the unneeded groupedWays
                            directionsGroupedWays[aDirection].remove(directionsGroupedWays[aDirection][currentLineEndIndex])
                            directionsGroupedWays[aDirection].remove(directionsGroupedWays[aDirection][currentLineStartIndex+1]) # Here we delete the lonely non shared

                            # Remove for the other line the unneeded groupedWays
                            del directionGroupedWay[secondGroupedWay]
                            del directionGroupedWay[firstGroupedWay+1]

                            # Removing from the subRoutes dict the ways that don't exist anymore
                            # del subRoutes[directionGroupedWay[secondGroupedWay].id]
                            # del subRoutes[directionGroupedWay[firstGroupedWay+1].id]

def mergeOppositeRoutes(lineWays) :
    for aLine in lineWays : 

        groupedWays1 = aLine[0][0] # list of groupedWays 
        groupedWays2 = aLine[0][1] # list of groupedWays 

        orderedMergedWays = list()

        print(aLine[1])
        for index in range(0, len(groupedWays1)) : 
            way1 = groupedWays1[index]
            way2 = groupedWays2[len(groupedWays2)-index-1]
            mergedWay = list()
            id1 = int(way1.id,16)
            id2 = int(way2.id,16)
            if id1>id2 : 
                key = way2.id + way1.id  
            else :
                key = way1.id + way2.id 

            for aNodeKey in way1.nodesList: 
                aNode = nodesDict[aNodeKey]
                nodeCoor = (aNode.lat, aNode.lon)

                nearestNodeKey = min(way2.nodesList, key=lambda p: nodeDistance(p, nodeCoor))

                if type(nearestNodeKey) is str :
                    nearestNode = nodesDict[nearestNodeKey]
                    nearestNode = (nearestNode.lat,nearestNode.lon)

                lat = float("{0:.7f}".format((nearestNode[0]+nodeCoor[0])/2))
                lon = float("{0:.7f}".format((nearestNode[1]+nodeCoor[1])/2))

                mergedWay.append((lat, lon))
            tramRoutes[key] = (way1.lines, mergedWay)
            orderedMergedWays.append((key, mergedWay))

        for index in range(0, len(orderedMergedWays)) :
            if index+1 < len(orderedMergedWays) :
                sharedNode = orderedMergedWays[index+1][1][0]
                distance = haversine(orderedMergedWays[index][1][-1][0], orderedMergedWays[index][1][-1][1],sharedNode[0], sharedNode[1])
                print(distance)
                if 0 < distance < 500 : 
                    #print('----sdfds')
                    mergedWay = tramRoutes[orderedMergedWays[index][0]][1]
                    mergedWay.append((sharedNode[0], sharedNode[1]))




def findOpposite() :

    firstDirection = 0
    secondDirection = 1 

    for aGroupedWay in directionsGroupedWays[firstDirection] : # getting a Key 
        nearestWay = (sys.maxsize, None)
        for anotherGroupedWay in directionsGroupedWays[secondDirection] : # getting a Key

            # The first node of a direction should match the last node of the opposite direction
            aNode = directionsGroupedWays[firstDirection][aGroupedWay].nodesList[0] # getting a node Id 
            aNode = nodesDict[aNode]

            anotherNode = directionsGroupedWays[secondDirection][anotherGroupedWay].nodesList[-1] # getting a node Id
            anotherNode = nodesDict[anotherNode]

            distance = haversine(aNode.lon, aNode.lat, anotherNode.lon, anotherNode.lat)
            if distance < nearestWay[0] : # comparing the distance
                nearestWay = (distance, aGroupedWay, anotherGroupedWay)

def nodesOfDirection(aDirectionGroupedWays) : 
    nodes = list()
    for aGroupedWay in aDirectionGroupedWays : 
        nodes.extend(aGroupedWay.nodesList)
    return nodes


"""
    Converting list to list of unique element and still keeping the order 
"""
def f7(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]

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


# For node as (lat,lon)
def nodeDistance(node1, node2) :
    if type(node1) is str : #means its a key for a node 
        node1 = (nodesDict[node1].lat, nodesDict[node1].lon)
    elif type(node1) is OsmNode : 
        node1 = (node1.lat, node1.lon)

    if type(node2) is str :
        node2 = (nodesDict[node2].lat, nodesDict[node2].lon)
    elif type(node2) is OsmNode : 
        node2 = (node2.lat, node2.lon)

    distance = sqrt( (node2[0] - node1[0])**2 + (node2[1] - node1[1])**2 )
    return  distance

class OsmNode : 
    def __init__(self,nodeNode):
        self.lat = float(nodeNode['lat'])
        self.lon = float(nodeNode['lon'])
    def __repr__(self):
        return '('+str("{0:.7f}".format(self.lat))+','+ str("{0:.7f}".format(self.lon))+')'

    def __str__(self) :
        return '('+str("{0:.7f}".format(self.lat))+','+ str("{0:.7f}".format(self.lon))+')'

class OsmWay : 
    def __init__(self, wayNode) :
        self.nodesList = list() # A sorted list of node id 
        ndNodes = wayNode.findAll("nd")
        self.lines= wayNode.find(k="name")["v"]
        self.lines = re.sub(r'^(Ligne|Lignes) (.*)',r'\2', self.lines)
        self.lines = re.findall(r"[\w']+", self.lines)

        for aNdNode in ndNodes : 
            self.nodesList.append(aNdNode["ref"])

        #print(len(self.nodesList), "nodes for relation", wayNode['id']) 

    def __str__(self):
        return str(self.lines) + str(len(self.nodesList))

    def __repr__(self): 
        return str(self.lines) + str(len(self.nodesList))

    def isShared(self): 
        return len(self.lines) > 1 
                
    def head(self) : 
        return self.nodesList[0]
        
    def tail(self) : 
        return self.nodesList[-1]

    def hasNode(self, node) :
        return node in self.nodesList

class groupedWay : 
    def __init__(self, nodesList, lines):
        global nodesDict
        self.nodesList = nodesList # An ordered list of nodes 
        self.lines = lines

        # generating an id with low probability of collision : appending as string lat/lon of first, middle and last node 
        # and converting the string to md5 hash
        boundingNodes = [nodesDict[self.nodesList[0]], nodesDict[self.nodesList[len(self.nodesList)//2]], nodesDict[self.nodesList[-1]]]
        stringCoordList = [str(i.lat) + '-' + str(i.lon) for i in boundingNodes]
        stringCoordList = '-'.join(stringCoordList).encode('utf-8')
        self.id = hashlib.md5(stringCoordList).hexdigest()

    def isShared(self):
        return len(self.lines) > 1

    def __str__(self):
        return self.id + ' ' + str(self.lines)

    def __repr__(self):
        return 'id: '+self.id + ' -- lines: ' + str(self.lines)

    def __eq__(self, other):
        return self.id == other.id    


if __name__ == '__main__' : 
    main(sys.argv[1:])