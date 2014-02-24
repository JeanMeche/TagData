import hashlib,json 
from os import listdir, makedirs
from os.path import isfile, join, isdir, getmtime
from urllib.request import urlopen
from datetime import datetime

cacheDataFilePath = "cacheData"

if isfile(cacheDataFilePath) : 
	file = open(cacheDataFilePath,"r")
	s = file.read()
	cacheData = json.loads(s)
else : 
	cacheData = dict()

def urlHash(url) :
    h = hashlib.md5()
    h.update(url.encode('utf-8'))
    return h.hexdigest()

def getPage(url):
	md5hash = urlHash(url)

	if not isdir("pythonWebCache"):
		makedirs("pythonWebCache")
	
	filename = "pythonWebCache/"+md5hash 

	if isfile(filename) and updateTime(url) : 
		print("Loading page",url, "from cache")
		file = open(filename,"r")
		return file.read()

	else:
		print("Loading page",url, "from the web")
		u = urlopen(url)
		s = u.read().decode('utf-8')

		file = open(filename, "w")
		file.write(s)
		file.close()
		setUpdateTime(url)
		return s
	return # never reached
	
	
def setUpdateTime(url): 
	hash = urlHash(url)
	cacheData[hash] = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	
	# Saving the data 
	jsonData = json.dumps(cacheData,indent=2,sort_keys=True)
	text_file = open(cacheDataFilePath, "w")
	text_file.write(jsonData)
	text_file.close()

def updateTime(url):
	hash = urlHash(url)
	if hash in cacheData:
		return datetime.strptime(cacheData[hash],"%Y-%m-%d %H:%M:%S")
	else:
		return None

def needsUpdate(url):
	now = datetime.now()
	then = updateTime(url)
	return (now - then) > timedelta (days = 14)