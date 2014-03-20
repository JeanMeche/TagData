#!/usr/bin/env python3

# ToDo mettre bout a bout les ways


import sys, getopt
from bs4 import BeautifulSoup
import localPageCache


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

    relationId = "2418275"        
            
    url = "http://www.overpass-api.de/api/interpreter?data=%5Btimeout%3A25%5D%3Brelation%28"+relationId+"%29%3Bway%28r%29%3Bout%20body%3B%3E%3Bout%20skel%20qt%3B"
    s = localPageCache.getPage(url)

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
        if len(aWay.findAll(k="building")) > 0 :  # Skipping buildings 
            continue
        if len(aWay.findAll(k="public_transport")) > 0 : # skipping platforms 
            continue
            
        wayId = aWay["id"] # Is an number but stored as string
        nodesDict[wayId] = OsmWay(aWay)

class OsmNode : 
    def __init__(self,nodeNode):
        self.lat = nodeNode['lat']
        self.lon = nodeNode['lon']

class OsmWay : 
    def __init__(self, wayNode) :
        self.__nodesList = list()
        ndNodes = wayNode.findAll("nd")

        for aNdNode in ndNodes : 
            self.__nodesList.append(aNdNode["ref"])
        print(len(self.__nodesList), "nodes for relation", wayNode['id']) 
        
if __name__ == '__main__' : 
    main(sys.argv[1:])