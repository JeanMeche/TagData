# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import urllib2
import json
import sys
from urlparse import urlparse, parse_qs
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


def main():
    lines = findTramIDs()
    
    res = list();
    for aLine in lines: 
         sens1 = stationsForLine(aLine["lineID"],1)
         sens2 = stationsForLine(aLine["lineID"],2)

         aDict = dict();
         aDict['name'] = aLine['name']
         aDict['lineID'] = aLine["lineID"]
         
         stationList =list()
         for aStation in sens1['stations']:
             stationDict = dict()
             stationDict['name'] = aStation['name']
             stationDict['sens1']  = aStation['stationID']
                
             for s2Stations in sens2['stations']:
                 if aStation['name'] == s2Stations['name']:
                     stationDict['sens2'] = s2Stations['stationID']             
             stationList.append(stationDict)

         aDict['stations'] = stationList
         res.append(aDict)

    print json.dumps(res,indent=4,sort_keys=True,ensure_ascii=False)


def stationsForLine(lineID, sens):    
    url = "http://tag.mobitrans.fr/horaires/index.asp?rub_code=23&typeSearch=line&lign_id="+str(lineID)+"&sens="+str(sens)
    f = urllib2.urlopen(url)
    s = f.read()

    #Using BeautifulSoup to parse the DOM
    soup = BeautifulSoup(s)
    rubDiv = soup.find("div", class_="rub_content")
    
    ulStops = rubDiv.find("ul", class_="stops")
    stops = ulStops.findAll("li", recursive=False)

    lineStops = list()

    for aStop in stops :
        theStop = dict()
        theStop['name'] = aStop.next.string
        url = aStop.find("a").attrs['href']
        parsed = parse_qs(urlparse(url).query, keep_blank_values=True)
        theStop['stationID'] = int(parsed["pa_id"][0])
        lineStops.append(theStop)
        
    stationDict = dict() 
    stationDict['sens'] = sens
    stationDict['stations'] = lineStops   
    
    return stationDict
    
def findTramIDs(): 
    url = "http://tag.mobitrans.fr/horaires/index.asp?rub_code=23&keywords=e"
    f = urllib2.urlopen(url)
    s = f.read()

    #Using BeautifulSoup to parse the DOM
    soup = BeautifulSoup(s)
    rubDiv = soup.find("div", class_="rub_content")

    ulLignes = rubDiv.find("ul", class_="lig")
    lignes = ulLignes.findAll("li", recursive=False)
    #print lignes
    resultList = list() #setting the list returned

    lines = list()

    for ligne in lignes :
        if(ligne.find("span") is not None):
            name = ligne.find("span").next.string
            if(not name.isdigit() and len(name) == 1):
                aLine = dict()
                aLine['name'] = name      
                url = ligne.find("a").attrs['href']
                parsed = parse_qs(urlparse(url).query, keep_blank_values=True)
                aLine['lineID'] = int(parsed["lign_id"][0])
                lines.append(aLine)
    
    #print json.dumps(lines,indent=4,sort_keys=True)
    return lines
    
if __name__ == '__main__':
    main();

