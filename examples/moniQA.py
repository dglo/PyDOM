#!/usr/bin/env python

from __future__ import print_function
from builtins import range
import sys
from pickle import load
from icecube.domtest.payload import decode_payload
from icecube.domtest.monitoring import *

def sum(lx):
    s = 0.0
    for x in lx: s += x
    return x

args = sys.argv[1:]
domdb = args.pop(0)
doms = load(open(domdb, 'r'))
db   = dict()
for d in doms: db[d[0]] = d

monitoring = dict()
while len(args) > 0:
    f = open(args.pop(0), 'rb')
    while True:
        mp = decode_payload(f)
        if mp is None: break
        mbid = '%12.12x' % mp.mbid
        domid = db[mbid][3]
        if isinstance(mp.rec, HardwareMonitorRecord): 
            if domid not in monitoring: monitoring[domid] = list()
            monitoring[domid].append(mp.rec)
                
# Summarize stats
domids = list(monitoring.keys())

for string in range(1, 81):
    onstr = [ int(domid[3:5]) for domid in domids if int(domid[0:2]) == string ]
    inice = [ loc for loc in onstr if loc <= 60 ]
    icetop = [ loc for loc in onstr if loc > 60 ]
    missii = [ loc for loc in range(1, 61) if loc not in inice ]
    missit = [ loc for loc in range(61, 65) if loc not in icetop ]
#    if len(onstr) > 0:
#        print "String", string, "in-ice:", len(inice), "icetop:", len(icetop)
#        print missii
#        print missit
        
for domid in sorted(domids):
    mlist = monitoring[domid]
    t0 = mlist[0].timestamp * 1.0E-10
    t2 = mlist[-1].timestamp * 1.0E-10
    n  = len(mlist)
    mx = [ x for x in mlist if x.getSPERate() > 0 ]
    t1 = mx[0].timestamp * 1.0E-10
    t3 = mx[-1].timestamp * 1.0E-10
    if len(mx) > 0:
        avgsperate = sum([ x.getSPERate() for x in mx ]) / len(mx)
        avgmperate = sum([ x.getMPERate() for x in mx ]) / len(mx)
    else:
        avgsperate = 0.0
        avgmperate = 0.0
    print(domid, '%.1f %.1f' % (avgsperate, avgmperate))
    #print domid, n, '%.3f' % t0, '%.3f' % t1, '%.3f' % t2, '%.3f' % t3,\
    #    '%.1f' % (n / (t2 - t0)), '(%.1f:%.1f)' % (avgsperate, avgmperate)
    

