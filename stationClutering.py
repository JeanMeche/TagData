#!/usr/bin/env python3

import json
import math
import sys
from pprintpp import pprint
from itertools import groupby
from collections import defaultdict
from math import radians, sin, cos, asin, sqrt
from lxml import etree as ET
from bs4 import BeautifulSoup

stations = None
osmMbtData = None
routes = None

def main():
    global stations, osmMbtData, routes
    with open('stations.json', 'r') as fp:
        stations = json.load(fp)
    with open('osmMbtData.json', 'r') as fp:
        osmMbtData = json.load(fp)

    with open('lineRoutes.kml', 'r') as fp:
        route_data = fp.read()
    bs = BeautifulSoup(route_data)
    placemarks = bs.findAll('placemark')
    routes = list()
    for aPlacemark in placemarks:
        lines = list(aPlacemark.find('description').text)
        route = aPlacemark.find('coordinates').text.split(' ')
        route = [coord.split(',') for coord in route]
        routes.extend(route)


    tramStations = list()
    busStations = list()
    for aStationId in stations:
        lines = linesForStation(aStationId)

        # only tram stations
        lineNames = [x['name'] for x in lines if 'Tram' in x['name']]

        if len(lineNames) > 0:
            tramStations.append(stations[aStationId])
        else:
            busStations.append(stations[aStationId])

    mergedTramStations = mergeTramStations(tramStations)
    mergedBusStations = mergeBusStations(busStations)

    mergedTramStations = computeStationOrientation(mergedTramStations)

    # Merge tram + bus stations when necessary
    for aTramStation in mergedTramStations:
        connections = [aBusStation for aBusStation in mergedBusStations if aBusStation['name'] == aTramStation['name']]
        if len(connections):
            for aConnection in connections:
                if haversine(float(aConnection['lon']), float(aConnection['lat']), float(aTramStation['lon']), float(aTramStation['lat'])) < 20:
                    aTramStation['type'] = 'both'
                    aTramStation['source'].extend(aConnection['source'])
                    mergedBusStations.remove(aConnection)

    allStations = list()
    allStations.extend(mergedTramStations)
    allStations.extend(mergedBusStations)

    # with open('clusteredStations.json', 'w', encoding='utf8') as fp:
    #     json.dump(allStations, fp, indent=2, ensure_ascii=False)
    exportToXml(allStations)


def exportToXml(stations):
    """
        Export subRoutes data to XML
    """

    root = ET.Element("stations")

    for aStation in stations:
        station = ET.SubElement(root, "station")
        station.set('lat', aStation['lat'])
        station.set('lon', aStation['lon'])
        station.set('name', aStation['name'])
        station.set('city', aStation['city'])
        station.set('source', ",".join((str(x) for x in aStation['source'])))
        station.set('type', aStation['type'])
        if 'orientation' in aStation:
            station.set('orientation', aStation['orientation'])
        if 'road' in aStation:
            station.set('road', aStation['road'])

    tree = ET.ElementTree(root)
    # Writing to file XML a valid XML encoded in UTF-8 (because Unicode FTW)
    tree.write("stations.xml", pretty_print=True, encoding="utf-8", xml_declaration=True)


def linesForStation(stationId):
    global stations, osmMbtData
    lines = list()
    for aLine in osmMbtData:
        aLine["sens2"]
        if int(stationId) in [x['osmId'] for x in aLine["sens1"]]:
            lines.append(aLine)
        if int(stationId) in [x['osmId'] for x in aLine["sens2"]]:
            lines.append(aLine)
    return lines

def stationWithTheNearestStation(stationList):
    size = len(stationList)
    #table = [[0 for x in range(size)] for x in range(size)]
    minDistance = sys.float_info.max
    minIndex = None
    for i in range(size):
        for j in range(size):
            distance = haversine(stationList[i]['lon'], stationList[i]['lat'], stationList[j]['lon'], stationList[j]['lat'])
            if distance < minDistance:
                minIndex = i
    return stationList[minIndex]

def clusterStations(stationList):
    maxRange = 40
    clusters = list()

    #
    # if len(stationList) is 2 and haversine(stationList[0]['lon'], stationList[0]['lat'], stationList[1]['lon'], stationList[1]['lat']) < maxRange:
    #     result = list()
    #     result.append(stationList)
    #     return result

    averageLat = sum(station['lat'] for station in stationList)/len(stationList)
    averageLon = sum(station['lon'] for station in stationList)/len(stationList)

    if 'Grand\'Place' in stationList[0]['name'] or 'Neyrpic - Belledonne' in stationList[0]['name'] or 'Flandrin - Valmy' in stationList[0]['name']:
        dd = defaultdict(list)
        for d in stationList:
            dd[(d['road'])].append(d)
        result = list()
        result.append(stationList)
        return dd.values()

    # ??????????????
    elif len(stationList) > 2:
        for station in stationList:
            if haversine(station['lon'], station['lat'], averageLon, averageLat) > maxRange:
                break
        else:
            if len(set([station['road'] for station in stationList])) is 1:  # if every stations are on the same road
                print(stationList[0]['name'] + ' will be merged')
                result = list()
                result.append(stationList)
                return result

    while stationList:
        cluster = list()
        station = stationWithTheNearestStation(stationList)
        if 'La Revir' in stationList[0]['name']:
            print(station)
        stationList.remove(station)
        cluster.append(station)

        for anotherStation in stationList:
            if (haversine(station['lon'], station['lat'], anotherStation['lon'], anotherStation['lat']) < maxRange and
                    anotherStation['road'] == cluster[0]['road']):
                cluster.append(anotherStation)
                stationList.remove(anotherStation)
        clusters.append(cluster)

    return clusters




def mergeTramStations(tramStations):

    sortedTramStationsListByName = sorted(tramStations, key=lambda k: k['name'])

    tramStationsClusters = list()
    for key, group in groupby(sortedTramStationsListByName, lambda x: x['name']):
        cluster = list()
        for a in group:
            cluster.append(a)
        tramStationsClusters.append(cluster)

    # reclustering station within a range
    geoClusters = list()
    for aCluster in tramStationsClusters:
        geoClusters.extend(clusterStations(aCluster))

    mergedTramStations = list()
    for aCluster in geoClusters:

        averageLat = sum(station['lat'] for station in aCluster)/len(aCluster)
        averageLon = sum(station['lon'] for station in aCluster)/len(aCluster)

        newStation = dict()
        newStation['lat'] = "{:.7f}".format(averageLat)
        newStation['lon'] = "{:.7f}".format(averageLon)
        newStation['city'] = aCluster[0]['city']
        newStation['name'] = aCluster[0]['name']
        newStation['source'] = [station['id'] for station in aCluster]
        newStation['type'] = 'tram'
        if 'road' in aCluster[0]:
            newStation['road'] = aCluster[0]['road']

        mergedTramStations.append(newStation)
    # pprint(mergedTramStations)
    return mergedTramStations


def mergeBusStations(busStations):
    sortedBusStationsListByName = sorted(busStations, key=lambda k: k['name'])

    busStationsClusters = list()
    for key, group in groupby(sortedBusStationsListByName, lambda x: x['name']):
        cluster = list()
        for a in group:
            cluster.append(a)
        busStationsClusters.append(cluster)

    geoClusters = list()
    for aCluster in busStationsClusters:
        clusters = clusterStations(aCluster)
        # if len(clusters[0]) > 2:
        #     pprint(clusters[0])
        geoClusters.extend(clusters)

    mergedBusStations = list()
    for aCluster in geoClusters:

        averageLat = sum(station['lat'] for station in aCluster)/len(aCluster)
        averageLon = sum(station['lon'] for station in aCluster)/len(aCluster)

        newStation = dict()
        newStation['lat'] = "{:.7f}".format(averageLat)
        newStation['lon'] = "{:.7f}".format(averageLon)
        newStation['city'] = aCluster[0]['city']
        newStation['name'] = aCluster[0]['name']
        newStation['source'] = [station['id'] for station in aCluster]
        newStation['type'] = 'bus'
        if 'road' in aCluster[0]:
            newStation['road'] = aCluster[0]['road']

        mergedBusStations.append(newStation)

    # pprint(mergedBusStations)
    return mergedBusStations


def computeStationOrientation(tramStations):
    global routes
    for aStation in tramStations:
        p1 = min(routes, key=lambda p: haversine(float(p[1]), float(p[0]), float(aStation['lat']), float(aStation['lon'])))
        routes.remove(p1)
        p2 = min(routes, key=lambda p: haversine(float(p[1]), float(p[0]), float(aStation['lat']), float(aStation['lon'])))

        deltaY = float(p1[0])-float(p2[0])
        deltaX = float(p1[1])-float(p2[1])

        angle = math.atan2(deltaX, deltaY) * 180 / math.pi
        aStation['orientation'] = "{:.7f}".format(angle)

        # print(angle)
        # print(haversine(float(p1[1]), float(p1[0]), float(aStation['lat']), float(aStation['lon'])), p1)
        # print(haversine(float(p2[1]), float(p2[0]), float(aStation['lat']), float(aStation['lon'])), p2)
    return tramStations


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


if __name__ == '__main__':
    main()
