#!/usr/bin/env python
#
# Tell HubDaemon to get DOMs ready for a TestDAQ run

import os,sys,traceback
from icecube.domtest.HubDaemon import HubProxy
from xmlrpclib import Error

if len(sys.argv) == 1:
    sys.stderr.write("Please specify one or more domhub machine names\n")
    sys.exit(1)

for s in sys.argv[1:]:
    try:
        driver = HubProxy(s)

        print s,"ready"
        driver.ready()
    except Error:
        print "For ",s,traceback.print_exc()
