"""
    Simple Python module to store queried web page localy to retrieve them faster.
     

    The cached files are stored in a given directory and name with their md5 hash. 
    Their creation date is stored in the same directory in a JSON file.
"""

import hashlib,json, getopt, sys
from os import listdir, makedirs
from os.path import isfile, join, isdir, getmtime
from urllib.request import urlopen
from datetime import datetime, timedelta


# Will update the file from the server if the cached file is older than the limit.
timelimit = timedelta (days = 7)

try:
    opts, args = getopt.getopt(sys.argv[1:],"vr",["print"])
except getopt.GetoptError:
    print ('localPageCache.py')
    sys.exit(2)
    
verbose = False
for opt, arg in opts:
    if opt == '-v':
        verbose = True
    if opt == '-r':
        timelimit = timedelta (days = 0)


_cacheDir = "pythonWebCache/"
_cacheDataFilePath = _cacheDir+"cacheData.json"



if isfile(_cacheDataFilePath) : 
    file = open(_cacheDataFilePath,"r")
    s = file.read()
    _cacheData = json.loads(s)
else : 
    _cacheData = dict()


"""
    This is the only public function. Just call it the retrieve the page either from the web or from the cache
    The origin is determined by the module itself.
"""
def getPage(url):
    md5hash = _urlHash(url)

    if not isdir(_cacheDir):
        makedirs(_cacheDir)
    
    filename = _cacheDir+md5hash 

    if isfile(filename) and not _needsUpdate(url) : 
        if verbose:
            print("Loading page",url, "from cache")
        file = open(filename,"r")
        return file.read()

    else:
        if verbose:
            print("Loading page",url, "from the web")
        u = urlopen(url)
        s = u.read().decode('utf-8')

        file = open(filename, "w")
        file.write(s)
        file.close()
        _setUpdateTime(url)
        return s
    return # never reached


"""
    Return a md5 hash for an url (or any other string)
"""
def _urlHash(url) :
    h = hashlib.md5()
    h.update(url.encode('utf-8'))
    return h.hexdigest()
    
"""
    sets the new creation time of a cached url and updates the cacheData json 
"""        
def _setUpdateTime(url): 
    hash = _urlHash(url)
    
    # storing as a string since datetime is not serializable
    _cacheData[hash] = str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) 
    
    # Saving the data 
    jsonData = json.dumps(_cacheData,indent=2,sort_keys=True)
    text_file = open(_cacheDataFilePath, "w")
    text_file.write(jsonData)
    text_file.close()

"""
    retrieves from the cacheData the creation time of the cached url 
"""
def _updateTime(url):
    hash = _urlHash(url)
    if hash in _cacheData:
        # The date is stored as a text, it need to be parsed to be a datetime
        return datetime.strptime(_cacheData[hash],"%Y-%m-%d %H:%M:%S")
    else:
        return None

"""
    Computes if the cache needs to be updated for the given url
"""
def _needsUpdate(url):
    now = datetime.now()
    then = _updateTime(url)
    return (now - then) > timelimit