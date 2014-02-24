#!/usr/bin/python

'''

Merging Data retrieved from Mobitrans and OSM 

'''
import sys, os, time, json, difflib, pprint, getopt

import console
import osmAPI
import mobitrans as mbt
import OsmTagStations as ots 
from lxml import etree as ET

def main(argv) :
    
    # If the json file does not exist, we create it 
    
    try:
        opts, args = getopt.getopt(argv,"hpm",["print"])
    except getopt.GetoptError:
        print ('TagData.py')
        sys.exit(2)
    
    doPrint = False
    doMerge = False
    for opt, arg in opts:
        if opt == '-h':
            print ('TagData.py')
            print ('-p to print output')
        if opt == '-m' :   
            doMerge = True
        if opt == '-p':
            doPrint = True
    
    if doMerge :
        linesDict = mergingData(doPrint)
    else :
        file = open("MergedData.json", "r")
        s = file.read()
        linesDict = json.loads(s)
        
    associateOppositeStations(linesDict,doPrint)
#END_DEF


def associateOppositeStations(linesDict, doPrint):

    resultList = list()
    
    for aLine in linesDict: 
        if "MbtId" not in aLine:
            continue 
        
        aLineDict = dict()
        
        lineName = aLine["name"]
        lineId = aLine["MbtId"]
        
        if "OsmId" in aLine :
            aLineDict["osmId"] = aLine["OsmId"]
        
        aLineDict["mbtId"] = lineId
        aLineDict["name"] = lineName
        aLineDict["sens1"] = list()
        aLineDict["sens2"] = list()
        
        
        for osmStationId in aLine["sens1"]:
            aDict = dict()
            aDict["name"] = ots.stationName(osmStationId)
            aDict["osmId"] = osmStationId
            aDict["mbtId"] = mbt.stationIdForLine(aDict["name"], lineId, 1)
            aLineDict["sens1"].append(aDict)
            #print(osmStationId,mbt.stationIdForLine(name, lineId, 1))
        for osmStationId in aLine["sens2"]:
            aDict = dict()
            aDict["name"] = ots.stationName(osmStationId)
            aDict["osmId"] = osmStationId
            aDict["mbtId"] = mbt.stationIdForLine(aDict["name"], lineId, 2)
            aLineDict["sens2"].append(aDict)
            #print(osmStationId,mbt.stationIdForLine(name, lineId, 2))
        resultList.append(aLineDict)
    
    if doPrint:        
        (termWidth, height) = console.getTerminalSize()
        pprint.pprint(resultList, width=termWidth)
    
    jsonData = json.dumps(resultList,indent=2,sort_keys=True)
    
    
    # Data To XML 
    
    root = ET.Element("NetworkData")
    
    for aLine in resultList : 
        line = ET.SubElement(root, "line")
        
        line.set("name", aLine["name"])
        line.set("osmId", str(aLine["osmId"]))
        line.set("mbtId", str(aLine["mbtId"]))
        
        altName = mbt.alternateName(aLine["name"])
        if altName:
            line.set("picto", altName)
        
        sens1field = ET.SubElement(line,"sens1")
        sens2field = ET.SubElement(line,"sens2")
        for aDict in aLine["sens1"]:
            stationField = ET.SubElement(sens1field, "station")
            stationField.text = aDict["name"]
            stationField.set("osmId", str(aDict["osmId"]))
            stationField.set("mbtId", str(aDict["mbtId"]))
        for aDict in aLine["sens2"]:
            stationField = ET.SubElement(sens2field, "station")
            stationField.text = aDict["name"]
            stationField.set("osmId", str(aDict["osmId"]))
            stationField.set("mbtId", str(aDict["mbtId"]))

    tree = ET.ElementTree(root)
    tree.write("OsmMbtData.xml", pretty_print=True)
    
    
    text_file = open("OsmMbtData.json", "w")
    text_file.write(jsonData)
    text_file.close()
    return linesDict



def mergingData(doPrint) :       
    if not os.path.isfile('osmDirections.json'):
        print("Recreating OSM relations file")
        OSMjson = osmAPI.parseOsmTAGRelation(False)
        text_file = open("osmDirections.json", "w")
        text_file.write(OSMjson)
        text_file.close()
    
    print("Loading OSM relations file")
    file = open("osmDirections.json", "r")
    s = file.read()
    linesDict = json.loads(s)


    (termWidth, height) = console.getTerminalSize()
    total = len(linesDict)
    index=0
    print ("Merging the data...")
    for osmLine in linesDict:
        
        # Progressbar stuff
        index = index+1 
        percentage = index/total
        sys.stdout.write("\r")
        for i in range(int(termWidth*percentage)):
            sys.stdout.write("-")
            sys.stdout.flush()

        # Assign directions retrived from from OSM to the direction in Mobitrans 
        
        # Testing if the line is available on Mobitrans
        MbtLineId = mbt.idForLine(osmLine["name"])
        if MbtLineId: 
            sens = doTheStuff(osmLine, MbtLineId)
            osmLine["MbtId"] = MbtLineId   
            if sens == 1 :
                osmLine["sens1"] = osmLine["sensA"]
                osmLine["sens2"] = osmLine["sensB"]
                osmLine.pop("sensA", None) 
                osmLine.pop("sensB", None) 
            elif sens == 2 :
                osmLine["sens2"] = osmLine["sensA"]
                osmLine["sens1"] = osmLine["sensB"]
                osmLine.pop("sensA", None) 
                osmLine.pop("sensB", None)
        
        #In case the line ain't present on Mobitrans
        else : 
            osmLine.pop("sensA", None) 
            osmLine.pop("sensB", None)
        
    if doPrint:        
        pprint.pprint(linesDict)
        
    
    jsonData = json.dumps(linesDict,indent=4,sort_keys=True)
    text_file = open("MergedData.json", "w")
    text_file.write(jsonData)
    text_file.close()
    return linesDict
#END_DEF    
        
'''
    The parameter if the MobitransID of the line
'''      
def doTheStuff(osmLine,MbtLineId) :    
    stationsOfFirstDirection =  osmLine["sensA"]
    
    firstStationName = ots.stationName(osmLine["sensA"][0])
    secondStationName = ots.stationName(osmLine["sensA"][1])
    
    if secondStationName == firstStationName:
        secondStationName = ots.stationName(osmLine["sensA"][2])
    
    lineId = mbt.idForLine(osmLine["name"])
    
    #ordered Stations list from mobitrans   
    lineStations = mbt.stationsForLine(lineId,1)
    stationList = [x["name"] for x in lineStations]
        
    result1 = difflib.get_close_matches(firstStationName, stationList)
    result2 = difflib.get_close_matches(secondStationName, stationList)
   
   #second change, looking for substrings : 
    if not result1 :
        result1 = [s for s in stationList if s in firstStationName]
    if not result2 :    
        result2 = [s for s in stationList if s in secondStationName]
        
    if not result1 or not result2 :     
        print(firstStationName, secondStationName, stationList)
        print("No match found while calculating directions")
        return 
   
    index1 = stationList.index(result1[0]);
    index2 = stationList.index(result2[0]);
      
    if index1 < index2 :
        sens = 1
    else:
        sens = 2
   
    return sens
    #print("For line "+ osmLine["name"] +" A is sens " + str(sens))
#END_DEF        
        
        
if __name__ == "__main__": 
	main(sys.argv[1:])
	if os.name == "nt":
		input() #Not closing the term on windows