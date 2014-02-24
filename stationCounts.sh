#!/bin/bash

#Count of stations for similar directions 

for var in "$@"
do
   url="$url http://api.openstreetmap.org/api/0.6/relation/$var"
done
curl -silent $url | grep stop | awk '{print $3}' | sort | uniq | tr -d 'ref="' | wc -l | tr -d ' '

