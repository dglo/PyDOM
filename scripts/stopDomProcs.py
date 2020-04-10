#!/usr/bin/env python
#
# Tell HubDaemon to stop all processes which may be using a DOM

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import os, sys, traceback
from icecube.domtest.HubDaemon import HubProxy
from xmlrpc.client import Error

if len(sys.argv) == 1:
    sys.stderr.write("Please specify one or more domhub machine names\n")
    sys.exit(1)

for s in sys.argv[1:]:
    try:
        driver = HubProxy(s)

        print(s, "kill dom processes")
        l = driver.killDomProcesses()
        print(l)

    except Error:
        print("For ", s, traceback.print_exc())
