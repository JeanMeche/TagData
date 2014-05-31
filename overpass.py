import http.client, urllib.parse


def query(xml) :


    # url = "api.openstreetmap.fr" #OSM FR
    url = "overpass-api.de"
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/html,application/xhtml+xml,application/xml"}

    params = urllib.parse.urlencode({'@data': xml}) 
  
    conn = http.client.HTTPConnection(url, "80")
    # conn.request("POST", "/oapi/interpreter", params, headers) # OSMFR
    conn.request("POST", "/api/interpreter", params, headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return data.decode("unicode_escape");