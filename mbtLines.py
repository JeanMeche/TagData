#!/usr/bin/env python3

import json, sys
import localPageCache
from bs4 import BeautifulSoup

def main(argv) :
    

    # mbtLinesUrl = "http://tag.mobitrans.fr/horaires/index.asp?rub_code=23&typeSearch=line&monitoring=1&keywords=e"
    # s = localPageCache.getPage(mbtLinesUrl)
    # soup = BeautifulSoup(s)
    # 
    # 
    # 
    # file = open("lines.json", "r")
    # s = file.read()
    # linesDict = json.loads(s)
    
    parseFichesHoraire()

def parseFichesHoraire() : 
    
    urlFicheHoraire = "http://www.tag.fr/180-fiches-horaires.htm"
    s = localPageCache.getPage(urlFicheHoraire)
    soup = BeautifulSoup(s)
    
    liste = soup.find("ul", "liste")
    items = liste.findAll("li", "item")
    
    print(len(items))
        
if __name__ == "__main__": 
	main(sys.argv[1:])
        