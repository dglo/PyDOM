#!/bin/env python

"""
Turn on the light sources and run through the paces
2004-08-27 K. Hanson (kael.hanson@icecube.wisc.edu)
$Id: luxfw.py,v 1.1 2004/09/15 13:01:08 kaeld Exp $
"""

import sys, time, os
from icecube.domtest.lightsource import pulser, Digikrom, FilterWheel

p    = pulser('lantronix', 3010)
mono = Digikrom('lantronix', 3011)
fw   = FilterWheel('lantronix', 3012)

pulser_freq = 100000

p.allOff()
fw.reset()
time.sleep(5.0)
mono.reset()
time.sleep(5.0)

logf = file(os.path.expanduser("~/monitoring/lux.log"), "a")
print >>logf, "%.1f RUN BEGIN" % (time.time())

for pos in range(1,5):
    fw.setPosition(pos)
    time.sleep(5.0)
    
    # Turn on laser
    t0 = time.time()
    p.syncOn()
    p.triggerOn()
    p.setPulseFrequency(pulser_freq)
    logf.flush()
    time.sleep(60.0)
    p.allOff()
    t1 = time.time()
    print >>logf, "%.1f %.1f LASER FREQ %.1f FW %d" % (t0, t1, pulser_freq, pos)
    logf.flush()

    for wavelength in (4000, 3500, 3300, 3000):
        mono.goto(wavelength)
        time.sleep(2.0)
        t0 = time.time()
        p.relayOn()
        logf.flush()
        time.sleep(60.0)
        t1 = time.time()
        p.allOff()
        print >>logf, "%.1f %.1f MONO ON LAMBDA %d FW %d" % (t0, t1, wavelength, pos)
        logf.flush()

print >>logf, "%.1f RUN END" % (time.time())
