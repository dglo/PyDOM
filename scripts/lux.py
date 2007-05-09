#!/bin/env python

"""
Turn on the light sources and run through the paces
2004-08-27 K. Hanson (kael.hanson@icecube.wisc.edu)
$Id: lux.py,v 1.8 2006/03/27 21:10:53 kael Exp $
"""

import sys, time, os
from icecube.domtest.lightsource import pulser, Digikrom, FilterWheel
from getopt import getopt


def usage():
    print >>sys.stderr, \
"""
USAGE

    lux.py [ options ]

Options are

    -o <output-dir>             direct logfile to <output-dir>/lux.log
    --lantronix=<hostname>      specify lantronix hostname (default='lantronix')
    --pulser-port=<port>        (default=3010)
    --monochromator-port=<port> (default=3011)
    --filter-wheel-port=<port>  (default=3012) specify which ports on lantronix to use
    
"""

luxDir          = os.path.expanduser("~/monitoring")
lantronixHost   = "lantronix"
pulserPort      = 3010
monoPort        = 3011
filterPort      = 3012

opts, args = getopt(
    sys.argv[1:], 
    "ho:",
    [ "lantronix=", "pulser-port=", "monochromator-port=", "filter-wheel-port=", 
        "help" ]
    )
 

for o, a in opts:
    if o == "-o":
        luxDir = a
    elif o == "--lantronix":
        lantronixHost = a
    elif o == "--pulser-port":
        pulserPort = int(a)
    elif o == "--monochromator-port":
        monoPort = int(a)
    elif o == "--filter-wheel-port":
        filterPort = int(a)
    elif o == "-h" or o =="--help":
        usage()
        sys.exit(1)

logf = file(os.path.expanduser(luxDir + "/" + "lux.log"), "a")

p    = pulser(lantronixHost, 3010)
mono = Digikrom(lantronixHost, 3011)
fw   = FilterWheel(lantronixHost, 3012)

pulser_freq = 100000

p.allOff()
fw.reset()
time.sleep(5.0)
mono.reset()
time.sleep(5.0)


print >>logf, "%.1f RUN BEGIN" % (time.time())

for pos in (1, 2, 3):
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

    # Warm up the QTH lamp
    fw.setPosition(6)
    time.sleep(10.0)
    p.relayOn()
    time.sleep(300.0)
    p.allOff()
    fw.setPosition(pos)
    time.sleep(10.0)
    
    for wavelength in range(4000, 3000, -100):
        mono.goto(wavelength)
        time.sleep(10.0)
        t0 = time.time()
        p.relayOn()
        logf.flush()
        time.sleep(180.0)
        t1 = time.time()
        p.allOff()
        print >>logf, "%.1f %.1f MONO ON LAMBDA %d FW %d" % (t0, t1, wavelength, pos)
        logf.flush()

print >>logf, "%.1f RUN END" % (time.time())
