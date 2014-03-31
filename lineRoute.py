#!/usr/bin/env python3

# ToDo mettre bout a bout les ways

import sys, getopt, re
import overpass
from bs4 import BeautifulSoup
from math import sqrt
import localPageCache
import json
from lxml import etree as ET

tramRoutes = list()
osmTramIds = [2907314,2422329,2427813,2438215]
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


    for aRelationId in osmTramIds :         
        parse(str(aRelationId))
    
    # jsonData = json.dumps(tramRoutes,indent=2,sort_keys=True)
    # text_file = open("tramRoutes.json", "w")
    # text_file.write(jsonData)
    # text_file.close()
    exportToXml()

    
def exportToXml() :
    global lineName
    root = ET.Element("TramRoutes")
    
    for  index, aLine in enumerate(tramRoutes) :
        line = ET.SubElement(root, "line")
        line.set("name", lineName)
        line.set("osmId", str(osmTramIds[index]))
        lineName = chr(ord(lineName)+1)
        for aCoord in aLine : 
            lat = aCoord[0]
            lon = aCoord[1]
            node = ET.SubElement(line, "node")
            node.set("lat", str("{0:.7f}".format(lat)))
            node.set("lon", str("{0:.7f}".format(lon)))
 
    tree = ET.ElementTree(root)   
    # Writing to file XML a valid XML encoded in UTF-8 (because Unicode FTW) 
    tree.write("lineRoutes.xml", pretty_print=True, encoding="utf-8", xml_declaration=True)

def parse(relationId) :
    lineId = "http://api.openstreetmap.org/api/0.6/relation/" + relationId
    s = localPageCache.getPage(lineId)
    soup = BeautifulSoup(s)

    members = soup.findAll("member")
    directionId = [x["ref"] for x in members]
    print(directionId)
    
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
    
    # Parsing Nodes 
    nodeNodes = soup.findAll("node")
    nodesDict = dict()
    for aNode in nodeNodes :
        nodeId = aNode["id"] # Is an number but stored as string
        nodesDict[nodeId] = OsmNode(aNode)
    
    print(len(nodesDict), "Nodes")
    
    
    # Parsing the ways 
    wayNodes = soup.findAll("way")
    waysDict = dict() 
    for aWay in wayNodes : 
        wayId = aWay["id"] # Is an number but stored as string
        waysDict[wayId] = OsmWay(aWay)
    
    allWays = list()
    
    for aRelationId in directionId :
        masterWay = list()
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

    mergedWay = list()
    
    for aNode in allWays[0] : 
        theOtherWay = allWays[1]
        
        nearestNode = min(theOtherWay, key=lambda p: nodeDistance(p, aNode))

        lat = (nearestNode[0]+aNode[0])/2
        lon = (nearestNode[1]+aNode[1])/2

        mergedWay.append((lat, lon))

    tramRoutes.append(mergedWay)



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

        for aNdNode in ndNodes : 
            self.nodesList.append(aNdNode["ref"])
        print(len(self.nodesList), "nodes for relation", wayNode['id']) 
        
                
    def head(self) : 
        return self.nodesList[0]
        
    def tail(self) : 
        return self.nodesList[-1]

    def hasNode(self, node) :
        return node in self.nodesList
            
if __name__ == '__main__' : 
    main(sys.argv[1:])