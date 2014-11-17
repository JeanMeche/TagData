#!/usr/bin/env python3

'''
Merging Data retrieved from Mobitrans and OSM

1. osmApi.py returns a list of all Lines with every station for 2 different directions

2. MergingData() Associated the osmDirection with the directions retrieved from Mobitrans

'''

import sys
import os
import json
import difflib
import pprint
import getopt

import console
import osmAPI
import mobitrans as mbt
import OsmTagStations as ots
from lxml import etree as ET
import unicodedata

verbose = False


def main(argv):

    # If the json file does not exist, we create it

    try:
        opts, args = getopt.getopt(argv, "hmrv", ["print"])
    except getopt.GetoptError:
        print('TagData.py -hmv')
        sys.exit(2)

    global verbose
    doMerge = False
    for opt, arg in opts:
        print("mm", opt)
        if opt == '-h':
            print('TagData.py')
            print('-v for a verbose output')
            print('-r to refresh the file cache')
            quit()
        if opt == '-m':
            doMerge = True
        if opt == '-v':
            verbose = True

    if doMerge or not os.path.isfile('MergedData.json'):
        linesDict = mergingData()
    else:
        file = open("MergedData.json", "r")
        s = file.read()
        linesDict = json.loads(s)

    osmMbtData = associateOppositeStations(linesDict)
    with open('osmMbtData.json', 'w') as fp:
        json.dump(osmMbtData, fp, indent=2, sort_keys=True)


    print("\n\n -- Processing successful !")


'''
   ??????????
'''


def associateOppositeStations(linesDict):

    resultList = list()

    for aLine in linesDict:

        if "MbtId" not in aLine:
            continue

        aLineDict = dict()

        lineName = aLine["name"]
        lineId = aLine["MbtId"]

        if "OsmId" in aLine:
            aLineDict["osmId"] = aLine["OsmId"]

        aLineDict["mbtId"] = lineId
        aLineDict["name"] = lineName
        aLineDict["sens1"] = list()
        aLineDict["sens2"] = list()

        if not "sens1" in aLine:
            print(aLine)

        for osmStationId in aLine["sens1"]:
            aDict = dict()
            aDict["name"] = ots.stationName(osmStationId)
            aDict["osmId"] = osmStationId
            aDict["mbtId"] = mbt.stationIdForLine(aDict["name"], lineId, 1)
            aDict["terminus"] = osmStationId in aLine["terminus1"]

            # If there is no mobitrans id for this station on the line with sens1, not adding it
            # /!\ Data should probably be changed on OSM to match with the one from Mobitrans
            if aDict["mbtId"] is None:
                continue

            aLineDict["sens1"].append(aDict)

        for osmStationId in aLine["sens2"]:
            aDict = dict()
            aDict["name"] = ots.stationName(osmStationId)
            aDict["osmId"] = osmStationId
            aDict["mbtId"] = mbt.stationIdForLine(aDict["name"], lineId, 2)
            aDict["terminus"] = osmStationId in aLine["terminus2"]

            # If there is no mobitrans id for this station on the line with sens2, not adding it
            # /!\ Data should probably be changed on OSM to match with the one from Mobitrans
            if aDict["mbtId"] is None:
                continue

            aLineDict["sens2"].append(aDict)
        resultList.append(aLineDict)

    if verbose:
        (termWidth, height) = console.getTerminalSize()
        pprint.pprint(resultList, width=termWidth)

    #  jsonData = json.dumps(resultList, indent=2, sort_keys=True)
    exportToXml(resultList)

    return resultList


def exportToXml (resultList):

    # Data To XML

    root = ET.Element("NetworkData")

    for aLine in resultList:
        line = ET.SubElement(root, "line")

        line.set("name", aLine["name"])
        line.set("osmId", str(aLine["osmId"]))
        line.set("mbtId", str(aLine["mbtId"]))

        altName = mbt.alternateName(aLine["name"])
        if altName:
            line.set("picto", altName)

        sens1field = ET.SubElement(line, "sens1")
        sens2field = ET.SubElement(line, "sens2")
        for aDict in aLine["sens1"]:
            stationField = ET.SubElement(sens1field, "station")
            stationField.text = aDict["name"]
            stationField.set("osmId", str(aDict["osmId"]))
            stationField.set("mbtId", str(aDict["mbtId"]))
            if(aDict["terminus"]):
                stationField.set("terminus", "true")

        for aDict in aLine["sens2"]:
            stationField = ET.SubElement(sens2field, "station")
            stationField.text = aDict["name"]
            stationField.set("osmId", str(aDict["osmId"]))
            stationField.set("mbtId", str(aDict["mbtId"]))
            if(aDict["terminus"]):
                stationField.set("terminus", "true")

    tree = ET.ElementTree(root)

    # Writing to file XML a valid XML encoded in UTF-8 (because Unicode FTW)
    tree.write("OsmMbtData.xml", pretty_print=True, encoding="utf-8", xml_declaration=True)


def mergingData() :
    if not os.path.isfile('osmDirections.json'):
        print("Recreating OSM relations file")
        OSMjson = osmAPI.parseOsmTAGRelation()
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
        if not verbose:
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
            sens = matchingSens(osmLine)
            osmLine["MbtId"] = MbtLineId
            if sens == 1:
                osmLine["sens1"] = osmLine["sensA"]
                osmLine["sens2"] = osmLine["sensB"]
                osmLine["terminus1"] = osmLine["terminusA"]
                osmLine["terminus2"] = osmLine["terminusB"]
                osmLine.pop("sensA", None)
                osmLine.pop("sensB", None)
                osmLine.pop("terminusA", None)
                osmLine.pop("terminusB", None)
            elif sens == 2:
                osmLine["sens2"] = osmLine["sensA"]
                osmLine["sens1"] = osmLine["sensB"]
                osmLine["terminus2"] = osmLine["terminusA"]
                osmLine["terminus1"] = osmLine["terminusB"]
                osmLine.pop("sensA", None)
                osmLine.pop("sensB", None)
                osmLine.pop("terminusA", None)
                osmLine.pop("terminusB", None)
            else:
                osmLine.pop("MbtId", None)
                osmLine.pop("sensA", None)
                osmLine.pop("sensB", None)

        #In case the line ain't present on Mobitrans
        else:
            osmLine.pop("sensA", None)
            osmLine.pop("sensB", None)

    if verbose:
        pprint.pprint(linesDict)

    jsonData = json.dumps(linesDict, indent=4, sort_keys=True)
    text_file = open("MergedData.json", "w")
    text_file.write(jsonData)
    text_file.close()
    return linesDict


'''
    For a line dictionary it returns whether sensA correspond to Sens1 or Sens2 in Mobitrans
'''


def matchingSens(osmLine):

    index = 0

    # Looping over the stations because sometimes some of them
    # are not the same depending of the direction
    while index+2 < len(osmLine["sensA"])-1:
        firstStationName = ots.stationName(osmLine["sensA"][index+0])
        secondStationName = ots.stationName(osmLine["sensA"][index+1])

        if secondStationName == firstStationName:
            secondStationName = ots.stationName(osmLine["sensA"][index+2])

        lineId = mbt.idForLine(osmLine["name"])

        #ordered Stations list from mobitrans
        lineStations = mbt.stationsForLine(lineId, 1)
        stationList = [x["name"] for x in lineStations]

        result1 = difflib.get_close_matches(firstStationName, stationList)
        result2 = difflib.get_close_matches(secondStationName, stationList)

        #second chance, looking for substrings:
        if not result1:
            result1 = [s for s in stationList if s in firstStationName]
        if not result2:
            result2 = [s for s in stationList if s in secondStationName]

        # third change, doing the same but with no accent nor diacritics
        if not result1:
            asciiName = ''.join(c for c in unicodedata.normalize('NFD', firstStationName) if unicodedata.category(c) != 'Mn')
            result1 = [s for s in stationList if s in asciiName]
        if not result2:
            asciiName = ''.join(c for c in unicodedata.normalize('NFD', secondStationName) if unicodedata.category(c) != 'Mn')
            result2 = [s for s in stationList if s in asciiName]

        if result1 and result2:
            break
        else:
            index += 1

    if not result1 or not result2:
        #print(firstStationName, secondStationName, stationList)
        print("\n*No match found while calculating directions for line", osmLine["name"], firstStationName, secondStationName, "")
        print(stationList)
        return

    index1 = stationList.index(result1[0])
    index2 = stationList.index(result2[0])

    if index1 < index2:
        sens = 1
    else:
        sens = 2

    return sens


if __name__ == "__main__":
	main(sys.argv[1:]) 