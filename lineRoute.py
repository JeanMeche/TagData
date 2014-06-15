#!/usr/bin/env python3

# ToDo mettre bout a bout les ways

import sys, getopt, re
import overpass
from bs4 import BeautifulSoup
from math import sqrt
import localPageCache
import json
from lxml import etree as ET
from simplekml import Kml 
import random

tramRoutes = list()
subRoutes = list()
osmTramIds = [('A', 2907314), ('B',2422329), ('C', 2427813), ('D', 2438215) , ('E',3785739)] # A,B,C,D,E
lineName = 'A'

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


    global subRoutes
    for aRelationId in osmTramIds :         
        parse(str(aRelationId[1]))

    for index1, route1 in enumerate(tramRoutes):
        for index2, route2 in enumerate(tramRoutes):
            if index1 == index2 : 
                continue
            subRoute = longest_common_subroute(route1,route2)
            if len(subRoute) > 1:
                found = [route for route in subRoutes if (route[0], route[-1]) == (subRoute[0],subRoute[-1])]
                if len(found) == 0 :
                    subRoutes.append(subRoute)
                    print(osmTramIds[index1][0],osmTramIds[index2][0],subRoute[0], subRoute[-1], len(subRoute))


            subRoute = longest_common_subroute(route1, route2[::-1])
            if len(subRoute) > 1:
                found = [route for route in subRoutes if (route[0], route[-1]) == (subRoute[0],subRoute[-1])]
                if len(found) == 0 :
                    subRoutes.append(subRoute)
                    print(osmTramIds[index1][0],osmTramIds[index2][0],subRoute[0], subRoute[-1], len(subRoute))

    print(len(subRoutes))

    exportToXml()



    # KML 
    kml = Kml()
    for index, aRoute in enumerate(subRoutes) :

        coords = [(float(x[1]),float(x[0])) for x in aRoute]


        lin = kml.newlinestring(name="Pathway", description='-', coords= coords)

        r = lambda: random.randint(0,255)
        randomColor = '#%02X%02X%02Xff' % (r(),r(),r())

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
    
def exportToXml() :
    global lineName
    root = ET.Element("TramRoutes")
    
    for  index, aLine in enumerate(tramRoutes) :
        line = ET.SubElement(root, "line")
        line.set("name", lineName)
        line.set("osmId", str(osmTramIds[index][1]))
        lineName = str(osmTramIds[index][0])
        for aCoord in aLine : 
            lat = aCoord[0]
            lon = aCoord[1]
            node = ET.SubElement(line, "node")
            node.set("lat", lat)
            node.set("lon", lon)
 
    tree = ET.ElementTree(root)   
    # Writing to file XML a valid XML encoded in UTF-8 (because Unicode FTW) 
    tree.write("lineRoutes.xml", pretty_print=True, encoding="utf-8", xml_declaration=True)


"""
Parsing the ways & nodes informations for a particular line 
"""
def parse(relationId) :
    
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
    nodesDict = dict()
    for aNode in nodeNodes :
        nodeId = aNode["id"] # Is an number but stored as string
        nodesDict[nodeId] = OsmNode(aNode)
        
    
    # Parsing the ways 
    wayNodes = soup.findAll("way")
    waysDict = dict() 
    for aWay in wayNodes : 
        wayId = aWay["id"] # Is an number but stored as string
        waysDict[wayId] = OsmWay(aWay)
    
    allWays = list()
    
    # For each direction 
    for aRelationId in directionId :
        masterWay = list()  # the global way with every node of the direction 
        osmApiQuery = "http://api.openstreetmap.org/api/0.6/relation/" + aRelationId
    
        s = localPageCache.getPage(osmApiQuery)
        soup = BeautifulSoup(s)

        members = soup.findAll("member", role=re.compile("forward"))
        
        ways = list()
        for aMember in members :
            ways.append(aMember["ref"])

        for aWay in ways: 


            masterWay.extend(waysDict[aWay].nodesList)

        allNodes = list()
        for aWay in masterWay :
            allNodes.append((float(nodesDict[aWay].lat),float(nodesDict[aWay].lon)))
        print(len(allNodes), " nodes for rel", aRelationId);
        allWays.append(allNodes)



    # Merging the 2 directions by averaging every closest nodes
    mergedWay = list() 
    maxDist = 0; 
    for aNode in allWays[0] : 
        theOtherWay = allWays[1]
        
        nearestNode = min(theOtherWay, key=lambda p: nodeDistance(p, aNode))
        
        dist = haversine(nearestNode[1], nearestNode[0], aNode[1], aNode[0])
        
        if(maxDist < dist):
            maxDist = dist
        
        #Problème en cas de terminus à 1 voie
        
        lat = (nearestNode[0]+aNode[0])/2
        lon = (nearestNode[1]+aNode[1])/2

        lat = str("{0:.7f}".format(lat))
        lon = str("{0:.7f}".format(lon))

        mergedWay.append((lat, lon))

    mergedWay = f7(mergedWay)

    tramRoutes.append(mergedWay)
    print(maxDist, "m");



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



def nodeDistance(node1, node2) :
    return sqrt( (node2[0] - node1[0])**2 + (node2[1] - node1[1])**2 )
    

class OsmNode : 
    def __init__(self,nodeNode):
        self.lat = nodeNode['lat']
        self.lon = nodeNode['lon']

class OsmWay : 
    def __init__(self, wayNode) :
        self.nodesList = list() # A sorted list of node id 
        ndNodes = wayNode.findAll("nd")
        name = wayNode.find(k="name")["v"]
        # shared = '&' in name
        # print(name, shared) 

        for aNdNode in ndNodes : 
            self.nodesList.append(aNdNode["ref"])

        #print(len(self.nodesList), "nodes for relation", wayNode['id']) 

    def isShared(): 
        return '&' in name
                
    def head(self) : 
        return self.nodesList[0]
        
    def tail(self) : 
        return self.nodesList[-1]

    def hasNode(self, node) :
        return node in self.nodesList
            






if __name__ == '__main__' : 
    main(sys.argv[1:])