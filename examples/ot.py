#!/usr/bin/env python

###
#
# Author: Kael Hanson (kael.hanson@icecube.wisc.edu)
# 2005.06.06
#
###

"""
SYNOPSIS

    Analyze the pulse risetimes and widths from a data file.

USAGE

    ot.py [ options ] <datafile.hit> <domcal_1.xml> <domcal_2.xml> ...
    
"""
from __future__ import print_function

import sys
from icecube.domtest.domcal import calibrator
from icecube.domtest.util import nextHit, softdisc
from getopt import getopt

correct_baseline = False
n = 1000000000
opts, args = getopt(sys.argv[1:], 'hb', [])
for o, a in opts:
    if o == '-h':
        usage()
        sys.exit(1)
    elif o == '-b':
        correct_baseline = True
    elif o == '-n':
        n = int(a)
        
hitfile = args.pop(0)

# Load / store the DOMCal information in huge dictionary
calibs = dict()
while len(args) > 0:
    calfile = args.pop(0)
    cal = calibrator(calfile)
    print("Loaded calibration for DOM", cal.domid, file=sys.stderr)
    calibs[cal.domid] = cal
    
f = open(hitfile, 'rb')
while n > 0:
    n -= 1
    hit = nextHit(f)
    if hit is None: break
    if hit.domid not in calibs: continue
    cal = calibs[hit.domid]
    atwd_freq = 20.0*cal.calcATWDFreq(850, 0)
    w = hit.atwd[0]
    if len(w) < 128:
        w = [0] * (128 - len(w)) + list(w)
    v = cal.recoATWD(w, 0, 2.6)
    # We may have a slight baseline problem - correct if switched on
    if correct_baseline: v -= v[0]
    e10 = softdisc(v, 0.1*max(v))
    e90 = softdisc(v, 0.9*max(v))
    # Don't process this waveform if things look funny
    if len(e10) != 2 or len(e90) != 2: continue
    risetime = 1000.0 / atwd_freq * (e90[0].x - e10[0].x)
    print(hit.domid, risetime)
