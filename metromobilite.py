#!/usr/bin/env python3

import json
import sys, os
from pprintpp import pprint
import localPageCache
import functools
from collections import namedtuple, defaultdict
from itertools import groupby
from math import radians, sin, cos, asin, sqrt

lines = None
stations = None

def main(argv):
    print(sys.version)
    getLines()
    getPointArrets()

    tramStations = list()
    busStations = list()

    for aStation in stations.values():
        if aStation.hasTrams():
            tramStations.append(aStation)
        else:
            busStations.append(aStation)

    mergedTramStations = mergeTramStations(tramStations)
    mergedBusStations = mergeBusStations(busStations)

    for aTramStation in mergedTramStations:
        connections = [aBusStation for aBusStation in mergedBusStations if aBusStation['name'] == aTramStation['name']]
        if len(connections):
            for aConnection in connections:
                if haversine(float(aConnection['lon']), float(aConnection['lat']), float(aTramStation['lon']), float(aTramStation['lat'])) < 20:
                    aTramStation['type'] = 'both'
                    aTramStation['source'].extend(aConnection['source'])
                    aTramStation['zones'].extend(aConnection['zones'])
                    mergedBusStations.remove(aConnection)
        aTramStation['zones'] = list(set(aTramStation['zones']))
    allStations = list()
    allStations.extend(mergedTramStations)
    allStations.extend(mergedBusStations)

    for aStation in allStations:
        aStation.pop("road", None)
        aStation.pop("city", None)

    with open('MergedStations.json', 'w') as fp:
        json.dump(allStations, fp, sort_keys=True)

def stationWithTheNearestStation(stationList):
    size = len(stationList)
    #table = [[0 for x in range(size)] for x in range(size)]
    minDistance = sys.float_info.max
    minIndex = None
    for i in range(size):
        for j in range(size):
            distance = haversine(stationList[i].location.longitude, stationList[i].location.latitude, stationList[j].location.longitude, stationList[j].location.latitude)
            if distance < minDistance:
                minIndex = i
    return stationList[minIndex]


def clusterStations(stationList):
    maxRange = 40
    clusters = list()

    averageLat = sum(station.location.latitude for station in stationList)/len(stationList)
    averageLon = sum(station.location.longitude for station in stationList)/len(stationList)

    if 'Grand\'Place' in stationList[0].name or 'Neyrpic - Belledonne' in stationList[0].name or 'Flandrin - Valmy' in stationList[0].name:
        dd = defaultdict(list)
        for d in stationList:
            dd[(d['road'])].append(d)
        result = list()
        result.append(stationList)
        return dd.values()

    # ??????????????
    elif len(stationList) > 2:
        for station in stationList:
            if haversine(station.location.longitude, station.location.latitude, averageLon, averageLat) > maxRange:
                break
        else:
            if len(set([station.road for station in stationList])) is 1:  # if every stations are on the same road
                print(stationList[0].name + ' will be merged')
                result = list()
                result.append(stationList)
                return result

    while stationList:
        cluster = list()
        station = stationWithTheNearestStation(stationList)
        if 'La Revir' in stationList[0].name:
            print(station)
        stationList.remove(station)
        cluster.append(station)

        for anotherStation in stationList:
            if (haversine(station.location.longitude, station.location.latitude, anotherStation.location.longitude, anotherStation.location.latitude) < maxRange and
                    anotherStation.road == cluster[0].road):
                cluster.append(anotherStation)
                stationList.remove(anotherStation)
        clusters.append(cluster)

    return clusters


def mergeTramStations(tramStations):
    sortedTramStationsListByName = sorted(tramStations, key=lambda k: k.name)

    tramStationsClusters = list()
    for key, group in groupby(sortedTramStationsListByName, lambda x: x.name):
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

        averageLat = sum(station.location.latitude for station in aCluster)/len(aCluster)
        averageLon = sum(station.location.longitude for station in aCluster)/len(aCluster)

        newStation = dict()
        newStation['lat'] = "{:.7f}".format(averageLat)
        newStation['lon'] = "{:.7f}".format(averageLon)
        newStation['city'] = aCluster[0].city
        newStation['name'] = aCluster[0].name
        newStation['source'] = [station.id for station in aCluster]
        newStation['type'] = 'tram'
        newStation["zones"] = list(set([station.zone for station in aCluster]))
        newStation['road'] = aCluster[0].road

        mergedTramStations.append(newStation)
    return mergedTramStations


def mergeBusStations(busStations):
    sortedBusStationsListByName = sorted(busStations, key=lambda k: k.name)

    busStationsClusters = list()
    for key, group in groupby(sortedBusStationsListByName, lambda x: x.name):
        cluster = list()
        for a in group:
            cluster.append(a)
        busStationsClusters.append(cluster)

    geoClusters = list()
    for aCluster in busStationsClusters:
        clusters = clusterStations(aCluster)
        geoClusters.extend(clusters)

    mergedBusStations = list()
    for aCluster in geoClusters:

        averageLat = sum(station.location.latitude for station in aCluster)/len(aCluster)
        averageLon = sum(station.location.longitude for station in aCluster)/len(aCluster)

        newStation = dict()
        newStation['lat'] = "{:.7f}".format(averageLat)
        newStation['lon'] = "{:.7f}".format(averageLon)
        newStation['city'] = aCluster[0].city
        newStation['name'] = aCluster[0].name
        newStation['source'] = [station.id for station in aCluster]
        newStation["zones"] = list(set([station.zone for station in aCluster]))
        newStation['type'] = 'bus'
        newStation['road'] = aCluster[0].road

        mergedBusStations.append(newStation)

    # pprint(mergedBusStations)
    return mergedBusStations


def getPointArrets():
    global lines, stations
    if os.path.isfile('MMStations.json'):
        with open('MMStations.json', 'r') as fp:
            _json = json.load(fp)
            stations = {x["id"]: Station(x, lines) for x in _json.values()}
    else:
        url = "http://data.metromobilite.fr/api/bbox/json?types=pointArret"
        s = localPageCache.getPage(url)
        pointArretsJson = json.loads(s)
        _json = pointArretsJson["features"]
        stations = {x["properties"]["id"]: Station(x, lines) for x in _json}
        with open('MMStations.json', 'w') as fp:
            json.dump(stations, fp, indent=2, sort_keys=True, cls=StationJSONEncoder)


def getLines():
    global lines
    url = "http://data.metromobilite.fr/otp/routers/default/index/routes"
    s = localPageCache.getPage(url)
    linesJson = json.loads(s)
    lines = {x["id"].replace(":", "_"): Line(x) for x in linesJson}


class Station:
    def __init__(self, jsonObject, lines):
        if "city" not in jsonObject:
            coords = jsonObject["geometry"]["coordinates"]
            properties = jsonObject["properties"]
            Location = namedtuple('Location', 'latitude longitude')
            self.location = Location(latitude=coords[1], longitude=coords[0])
            self.lines = {lines[x] for x in properties["lgn"].split(',')}
            self.zone = properties["ZONE"]
            self.pmr = properties["PMR"]
            self.id = properties["id"]
            self.name = properties["LIBELLE"]
            self.locateStation()
        else:
            self.lines = {lines[x] for x in jsonObject["lines"]}
            self.zone = jsonObject["zone"]
            self.pmr = jsonObject["pmr"]
            self.name = jsonObject["name"]
            self.id = jsonObject["id"]
            self.city = jsonObject["city"]
            self.road = jsonObject["road"]
            coords = jsonObject["location"]
            Location = namedtuple('Location', 'latitude longitude')
            self.location = Location(latitude=coords["latitude"], longitude=coords["longitude"])

    def __str__(self):
        return self.name + str([(x.name, x.mode) for x in self.lines])

    def __repr__(self):
        return self.name + str([(x.name, x.mode) for x in self.lines])

    def hasTrams(self):
        for aLine in self.lines:
            if not aLine.isTram():
                return False
        return True

    def locateStation(self):
        sys.stdout.write('.')
        sys.stdout.flush()
        nominatimUrl = "http://open.mapquestapi.com/nominatim/v1/reverse.php?key=NpfVO4ocnBw3PfHSrVCqpGeLzyy4F515&osm_type=N&accept-language=fr&format=json&&lat=" + str(self.location.latitude) + "&lon=" + str(self.location.longitude)
        # nominatimUrl = "http://nominatim.openstreetmap.org/reverse?format=json&osm_type=N&accept-language=fr&lat=" + str(self.location.latitude) + "&lon=" + str(self.location.longitude)
        nominatimData = localPageCache.getPage(nominatimUrl, true)
        print(".", end="")
        nominatimJson = None
        try:
            nominatimJson = json.loads(nominatimData)
        except ValueError:
            print('----------------- ', nominatimUrl)

        if "address" in nominatimJson:
            if "city" in nominatimJson["address"]:
                self.city = nominatimJson["address"]["city"]
            elif "village" in nominatimJson["address"]:
                self.city = nominatimJson["address"]["village"]
            elif "town" in nominatimJson["address"]:
                self.city = nominatimJson["address"]["town"]
            elif "hamlet" in nominatimJson["address"]:
                self.city = nominatimJson["address"]["hamlet"]
            else:
                print(nominatimUrl, " :// ")
                self.city = "HORRIBLE ERROR2"

            if "road" in nominatimJson['address']:
                self.road = nominatimJson['address']['road']
            elif "pedestrian" in nominatimJson['address']:
                self.road = nominatimJson['address']['pedestrian']
            elif "footway" in nominatimJson['address']:
                self.road = nominatimJson['address']['footway']
            else:
                self.road = ""
        else:
            self.city = "HORRIBLE ERROR"
            print(nominatimUrl, " :/ ")


class StationJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        aDict = dict()
        aDict["name"] = obj.name
        aDict["id"] = obj.id
        aDict["pmr"] = obj.pmr
        aDict["city"] = obj.city
        aDict["road"] = obj.road
        aDict["location"] = {"latitude": obj.location.latitude, "longitude": obj.location.longitude}
        aDict["lines"] = [x.id for x in obj.lines]
        aDict["zone"] = obj.zone
        return aDict

class Line:
    def __init__(self, jsonObject):
        self.id = jsonObject["id"].replace(":", "_")
        self.color = jsonObject["color"]
        self.longName = jsonObject["longName"]
        self.mode = jsonObject["mode"]
        self.name = jsonObject["shortName"]

    def __repr__(self):
        return str(self.name + " - " + self.mode)

    def __str__(self):
        return str(self.name + " - " + self.mode)

    def isTram(self):
        return self.mode == "TRAM"

    def isSNCF(self):
        return self.mode == "RAIL"

    def isC38(self):
        return "C38" in self.id

    def isCableCar(self):
        return self.Mode == "CABLE_CAR"


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


if __name__ == "__main__":
    main(sys.argv[1:])
