#!/usr/bin/env python

# Scan events for subthreshold hits

import sys
from icecube.daq.payload import decode_payload
from icecube.daq.subthresh import checkMissingReadouts
from getopt import getopt

def isAmandaTrig(triggers):
    for srcid, trig in triggers:
        if srcid == 10000: return True
    return False

maxevt  = 100000
verbose = False
merged  = 0
requireIceTopSMT = False
requireInIceSMT  = False
requireAmanda    = False
requirePhysMBT   = False

opts, args = getopt(sys.argv[1:], 'AIJMPTn:v')
for o, a in opts:
    if o == '-A':
        requireAmanda = True
    elif o == '-I':
        requireInIceSMT = True
    elif o == '-J':
        merged = -1
    elif o == '-M':
        merged = +1
    elif o == '-P':
        requirePhysMBT = True
    elif o == '-T':
        requireIceTopSMT = True
    elif o == '-n':
        maxevt = int(a)
    elif o == '-v':
        verbose = True

totevt = 0
totsub = 0

for filename in args:
    f = open(filename, "rb")
    while totevt < maxevt:
        evt = decode_payload(f)
        if evt is None: break
        trigs = evt.getTriggers()
        if merged == 1 and len(trigs) <= 2: continue
        if merged == -1 and len(trigs) > 2: continue
        if requireAmanda and not isAmandaTrig(trigs): continue
        if requireIceTopSMT and (5000, 0) not in trigs: continue
        if requireInIceSMT and (4000, 0) not in trigs: continue
        if requirePhysMBT and (4000, 13) not in trigs: continue
        totevt += 1
        if checkMissingReadouts(evt):
            totsub += 1
            if verbose: print evt.uid, evt.utime, evt.getTriggers()
    if totevt == maxevt: break

print totevt, totsub, "%.4g" % (float(totsub) / float(totevt))
 
