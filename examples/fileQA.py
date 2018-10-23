#! /bin/env python

import sys
from pickle import load
from icecube.domtest.payload import decode_payload, tohitstack
from getopt import getopt

triggerHisto = dict()

nevent = 2000000000

def triggerStats(trig):
    if trig.srcid / 1000 == 6:
        # GlobalTrigger
        for t in trig.hits:
            triggerStats(t)
    else:
        if trig.trigger_type not in triggerHisto: triggerHisto[trig.trigger_type] = 0
        triggerHisto[trig.trigger_type] += 1

opts, args = getopt(sys.argv[1:], 'n:')
for o, a in opts:
    if o == '-n':
        nevent = int(a)
        
domdb = args.pop(0)
doms = load(file(domdb, 'r'))

db   = dict()
for d in doms: db[d[0]] = d

events = list()
nev    = 0

while len(args) > 0:
    f = file(args.pop(0), 'rb')
    while nev < nevent:
        evt = decode_payload(f)
        nev += 1
        if evt is None: break
        events.append(evt)

hits = tohitstack(events)

print "DAQ thinks this is run #", events[0].run_number
print "Found", len(events), "events,", len(hits.keys()), "DOMs."
runlength = 1.0E-10*(events[-1].utime - events[0].utime)
print "Run length is %.1f" % runlength
print "Event rate is %.3f Hz" % (len(events)/runlength)

for evt in events:
    triggerStats(evt.trigger_request)
    
for trig_id, num in triggerHisto.items():
    print "Trigger ID:", trig_id, "-", num, " - rate %.2f" % (num / runlength) 
    
rates = dict()
nhits = 0
for mbid, hlist in hits.items():
    nhits += len(hlist)
    t0 = 1.0E-10 * hlist[0].utclk
    t1 = 1.0E-10 * hlist[-1].utclk
    beacons = [ x for x in hlist if x.evt_trig_flag == 1 ]
    hrate = brate = 0.0
    if t1 > t0:
        hrate = 1000.0 * len(hlist) / (t1-t0)
        brate = 1000.0 * len(beacons) / (t1-t0)
    rates[db[mbid][3]] = (len(hlist), len(beacons), t0, t1, hrate, brate)

print 'DOM hit summary information for all discovered DOMs follows'
print 'Total # of hits:', nhits
print '        # of  # of                            Hit     Beacon'
print ' DOM    Hits Beacon     T0          T0        Rate     Rate'
print '                                              [mHz]    [mHz]'
print '-------------------------------------------------------------'
for x in sorted(rates.keys()):
    print '%s %6d %6d %11.3f %11.3f %8.3f %8.3f ' % ((x,) + rates[x])
