#!/usr/bin/env python
#
# DOMHub XML-RPC daemon

import sys

from icecube.domtest.HubDaemon import HubDaemon

if __name__ == "__main__":
    HubDaemon.run(sys.argv)
