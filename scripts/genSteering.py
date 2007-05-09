#!/usr/bin/env python
#
# Tell HubDaemon to get DOMs ready to generate a steering file

import os,sys,traceback
from icecube.domtest.HubDaemon import HubProxy
from xmlrpclib import Error

if len(sys.argv) == 1:
    sys.stderr.write("Please specify one or more domhub machine names\n")
    sys.exit(1)

for s in sys.argv[1:]:
    try:
        driver = HubProxy(s)

        print s,"off all"
        driver.offAll()
        domDict = driver.getActiveDoms()
        if len(domDict) > 0:
            sys.stderr.write("Found %d %s DOMS still on:" % (len(domDict), s))
            for l in domDict.keys():
                sys.stderr.write(" " + l)
            sys.stderr.write("\n")

        print s,"on all"
        driver.onAll()
        domDict = driver.getActiveDoms()
        sys.stderr.write("Turned %d %s DOMS on:" % (len(domDict), s))
        for l in domDict.keys():
            sys.stderr.write(" " + l)
        sys.stderr.write("\n")

        print s,"go to IceBoot"
        driver.goToIceBoot()

        print s,"dtsx all"
        x = driver.dtsxAll()
        print x
    except Error:
        print "For ",s,traceback.print_exc()
