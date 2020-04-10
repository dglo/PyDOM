#!/usr/bin/env python

from __future__ import print_function
from past.builtins import cmp
from builtins import range
import sys
from icecube.domtest.util import nextHit, softdisc
from icecube.domtest.domcal import calibrator
from numarray import zeros
from getopt import getopt

class SoftwareDiscriminatorException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
    
def read_hits(f):
    hits = list()
    n = 0
    while n < 10000:
        n += 1
        hit = nextHit(f)
        if hit is None: return hits
        hits.append(hit)
    return hits

def fineTime(hit, c, cfd=0.1, ch=0):
    """
    Find the fine time offset of the pulse in the waveform
    """
    w = [ hit.atwd[ch][0] ]*(128 - len(hit.atwd[ch])) + list(hit.atwd[ch])
    v = c.recoATWD(w, ch, 2130./4096.0*5)
    f = 20.0 * c.calcATWDFreq(850, 0)
    x = softdisc(v, cfd*max(v))
    if len(x) < 1 or x[0].slope != 1:
        raise SoftwareDiscriminatorException(len(x))
    return hit.utclk + x[0].x / f * 10000

def usage():
    print("usage: syncole [ opts ] dom-hits sync hits domcal_1.xml ...", file=sys.stderr)

ch   = 0
flog = sys.stdout

opts, args = getopt(sys.argv[1:], 'hC:o:', [])
for o, a in opts:
    if o == '-h':
        usage()
        sys.exit(1)
    elif o == '-C':
        ch = int(a)
    elif o == '-o':
        flog = open(a, 'wt')

# Read DOM hits
hits = read_hits(open(args.pop(0), 'rb'))
# Read reference hits
hits += read_hits(open(args.pop(0), 'rb'))
# Read calibration files
cal = dict()
while len(args) > 0:
    c = calibrator(args.pop(0))
    cal[c.domid] = c
    
hits.sort(cmp = lambda a, b: cmp(a.utclk, b.utclk))

avg_waveform = zeros(250, 'd')
navg = 0
lastHit = None

for h in hits:
    if lastHit is not None:
        delta = h.utclk - lastHit.utclk
        print(h.domid, h.domclk)
        if delta < -5000:
            try:
                deltaf = fineTime(h, cal[h.domid]) - \
                         fineTime(lastHit, cal[lastHit.domid])
                bin_offset = int(cal[h.domid].calcATWDFreq(850, 0) * deltaf / 500.0)
                print(h.domid, lastHit.domid, delta, bin_offset)
                v = c.recoATWD(h.atwd[ch], ch, 2130.0 / 4096.0 * 5)
                for i in range(len(v)):
                    avg_waveform[i + bin_offset] += v[i]
                navg += 1
            except SoftwareDiscriminatorException:
                pass
            except IndexError:
                print(i, bin_offset)
    lastHit = h
    
avg_waveform /= navg
for i in range(len(avg_waveform)):
    print(i, avg_waveform[i], file=flog)

