#!/usr/bin/env python3

import OsmTagStations as ots 
import sys

def main(argv):
    #ots.stationsCloserThan(int(argv[0]))
    ots.lowestStationId()


if __name__ == '__main__':
    main(sys.argv[1:])

