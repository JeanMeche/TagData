#!/usr/bin/env python3

import json
import sys, os
from pprintpp import pprint
import localPageCache
import functools
from collections import namedtuple, defaultdict
from itertools import groupby
from math import radians, sin, cos, asin, sqrt
from json import encoder
import difflib

encoder.FLOAT_REPR = lambda o: format(o, '.5f')

lines = None
stations = None
groups = list()

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
                    aTramStation['type'] = 'Mixte'
                    aTramStation['source'].extend(aConnection['source'])
                    aTramStation['zones'].extend(aConnection['zones'])
                    mergedBusStations.remove(aConnection)
        aTramStation['zones'] = list(set(aTramStation['zones']))
    allStations = list()
    allStations.extend(mergedTramStations)
    allStations.extend(mergedBusStations)

    toRemove = list()
    for aStation in allStations:
        # allStationstion.pop("road", None)
        aStation.pop("city", None)
        aStation["id"] = "".join([x.split("_")[1] for x in aStation["source"]])

        stationsToMerge = [x for x in allStations if aStation is not x and distanceBetweenStations(x, aStation) < 20]
        lat=aStation["lat"]
        lon=aStation["lon"]

        for i, x in enumerate(stationsToMerge):
            lat = lat + x["lat"]
            lon = lon + x["lon"]
            aStation["zones"].extend(x["zones"])
            aStation["zones"] = list(set(aStation["zones"]))
            aStation["type"] = mergeTypes(aStation["type"], x["type"])
            aStation["source"].extend(x["source"])
            allStations.remove(x)

        aStation["lat"] = lat/(len(stationsToMerge)+1)
        aStation["lon"] = lon/(len(stationsToMerge)+1)

    # grouping
    groups = dict()
    for aStation in allStations: 
        nearStations = [x for x in allStations if distanceBetweenStations(x, aStation) < 200]
        matchingStations = difflib.get_close_matches(aStation["name"], [x["name"] for x in nearStations], n=len(nearStations), cutoff=0.8)
        for aNearStation in nearStations:
            if aNearStation["name"] in matchingStations:
                if "group" not in aNearStation:
                    aNearStation["group"] = aStation["name"]
        # print(aStation["name"])
        # print("\033[92m"+str(matchingStations) +"\033[0m")
        # print("\033[91m"+str([x for x in nearStations if x not in matchingStations])+"\033[0m")
        # print("-------------")

    with open('MapPoints.json', 'w') as fp:
        json.dump(allStations, fp, sort_keys=True, indent=2)


def mergeTypes(type1, type2):
    if type1 == type2:
        return type1
    elif type1 == "Tram" or type2 == "Tram":
        return "Mixte"
    else:
        return "Bus"

def stationWithTheNearestStation(stationList):
    size = len(stationList)
    minDistance = sys.float_info.max
    minIndex = 0
    for i in range(size):
        for j in range(size):
            if i != j:
                distance = haversine(stationList[i].location.longitude, stationList[i].location.latitude, stationList[j].location.longitude, stationList[j].location.latitude)
                if distance < minDistance:
                    minIndex = i
                    minDistance = distance
    return stationList[minIndex]

def clusterStations(stationList):
    maxRange = 60 
    clusters = list()

    averageLat = sum(station.location.latitude for station in stationList)/len(stationList)
    averageLon = sum(station.location.longitude for station in stationList)/len(stationList)

    if 'GRAND\'PLACE' in stationList[0].name or 'NEYRPIC' in stationList[0].name or 'FLANDRIN - VALMY' in stationList[0].name:
        dd = defaultdict(list)
        for d in stationList:
            dd[(d.road)].append(d)
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
                result = list()
                result.append(stationList)
                return result

    bb = False
    # if "LA TRONCHE, CIMETIERE" in stationList[0].name and list(stationList[0].lines)[0].mode == "BUS":
    #     bb = True

    while stationList:
        cluster = list()
        station = stationWithTheNearestStation(stationList)
        stationList.remove(station)
        cluster.append(station)
        if bb:
            print("-- ", station)

        stationList.sort(key = lambda p: haversine(station.location.longitude, station.location.latitude, p.location.longitude, p.location.latitude))
        if bb: 
            pprint(stationList)

        for anotherStation in stationList:
            averageLoc = averageLocation(cluster)
            if bb:
                print(haversine(averageLoc["lon"], averageLoc["lat"], anotherStation.location.longitude, anotherStation.location.latitude), anotherStation)
                print((anotherStation.road == cluster[0].road or anotherStation.road == "" or cluster[0].road == ""), cluster[0].road, anotherStation.road)
            if (haversine(averageLoc["lon"], averageLoc["lat"], anotherStation.location.longitude, anotherStation.location.latitude) < maxRange and
                    (anotherStation.road == cluster[0].road or anotherStation.road == "" or cluster[0].road == "")) or haversine(averageLoc["lon"], averageLoc["lat"], anotherStation.location.longitude, anotherStation.location.latitude) < 15:
                cluster.append(anotherStation)

        stationList = [x for x in stationList if x not in cluster]
        clusters.append(cluster)
        if bb:
            print("Cluster :", cluster ,"\n\n")
    return clusters

def averageLocation(stationList):
    averageLat = sum(station.location.latitude for station in stationList)/len(stationList)
    averageLon = sum(station.location.longitude for station in stationList)/len(stationList)
    return {"lon":averageLon, "lat":averageLat}


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
        newStation['lat'] = averageLat
        newStation['lon'] = averageLon
        newStation['city'] = aCluster[0].city
        newStation['name'] = aCluster[0].name
        newStation['source'] = [station.id for station in aCluster]
        newStation['type'] = 'Tram'
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

    # pprint(geoClusters)

    mergedBusStations = list()
    for aCluster in geoClusters:
        averageLat = sum(station.location.latitude for station in aCluster)/len(aCluster)
        averageLon = sum(station.location.longitude for station in aCluster)/len(aCluster)

        newStation = dict()
        newStation['lat'] = averageLat
        newStation['lon'] = averageLon
        newStation['city'] = aCluster[0].city
        newStation['name'] = aCluster[0].name
        newStation['source'] = [station.id for station in aCluster]
        newStation["zones"] = list(set([station.zone for station in aCluster]))
        
        types = set([x.type for x in aCluster])
        if len(types) == 1:
            newStation["type"] = types.pop()
        else:
            if "Tram" in types:
                newStation["type"] = "Mixte"
            else:
                newStation["type"] = "Bus"

        newStation['road'] = aCluster[0].road
        mergedBusStations.append(newStation)

    # pprint(mergedBusStations)
    return mergedBusStations


def distanceBetweenStations(station1, station2):
    return haversine(station1["lon"], station1["lat"], station2["lon"], station2["lat"])


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
    url = "http://data.metromobilite.fr/api/routers/default/index/routes" #"http://data.metromobilite.fr/otp/routers/default/index/routes"
    s = localPageCache.getPage(url)
    linesJson = json.loads(s)
    lines = {x["id"].replace(":", "_"): Line(x) for x in linesJson}


class Station:
    def __init__(self, jsonObject, lines):
        if "geometry" in jsonObject:
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
            self.lines = {lines[x] for x in jsonObject["lines"] if x in lines}
            self.zone = jsonObject["zone"]
            self.pmr = jsonObject["pmr"]
            self.name = jsonObject["name"]
            self.id = jsonObject["id"]
            self.city = jsonObject["city"]
            self.road = jsonObject["road"]
            coords = jsonObject["location"]
            Location = namedtuple('Location', 'latitude longitude')
            self.location = Location(latitude=coords["latitude"], longitude=coords["longitude"])
            types = set([x.type for x in self.lines])
            if len(types) == 0:
                types = set(["Bus"])
            
            if len(types) == 1:
                self.type = types.pop()
            else:
                if "Tram" in types:
                    self.type = "Mixte"
                else:
                    self.type = "Bus"

    def __str__(self):
        return self.name + str([(x.name, x.mode) for x in self.lines])

    def __repr__(self):
        return self.name + " " + self.zone + " " + str([(x.name, x.mode) for x in self.lines])

    def distanceFromStation(station):
        return haversine(station.location.lon, station.location.lat, self.location.lon, self.location.lat)

    def hasTrams(self):
        if len(self.lines) == 0:
            return False 
        for aLine in self.lines:
            if not aLine.isTram():
                return False
        return True

    def locateStation(self):
        nominatimUrl = "http://open.mapquestapi.com/nominatim/v1/reverse.php?key=NpfVO4ocnBw3PfHSrVCqpGeLzyy4F515&osm_type=N&accept-language=fr&format=json&&lat=" + str(self.location.latitude) + "&lon=" + str(self.location.longitude)
        # nominatimUrl = "http://nominatim.openstreetmap.org/reverse?format=json&osm_type=N&accept-language=fr&lat=" + str(self.location.latitude) + "&lon=" + str(self.location.longitude)
        nominatimData = localPageCache.getPage(nominatimUrl, True)
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
        self.type = jsonObject["type"]

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

    def isScolaire(self):
        return 

    def isNavette(self):
        return self.name.isdigit() and int(self.name) > 80 and int(self.name) < 90

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
