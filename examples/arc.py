#!/usr/bin/env python

from __future__ import print_function
import os, sys
import struct
from icecube.domtest import rapcal, hits, domcal
from getopt import getopt

def usage():
    print("usage: arc [ -h | -n <#> | -T ] <basename>", file=sys.stderr)
    
maxrec = 1000000000
do_tcal = False

opts, args = getopt(sys.argv[1:], 'hn:T', [ ])
for o, a in opts:
    if o == '-h':
        usage()
        sys.exit(1)
    elif o == '-n':
        maxrec = int(a)
    elif o == '-T':
        do_tcal = True
        
basename = args.pop(0)

fhit = open(basename + '.hit', 'rb')
tcal = rapcal.TimeCalibrator(open(basename + '.tcal', 'rb'))
fout = dict()

nrec = 0

while nrec < maxrec:
    nrec += 1
    # Read the header
    hdr = fhit.read(32)
    if len(hdr) != 32: break
    recl, fmt, mbid, utc = struct.unpack('>iiq8xq', hdr)
    buf = fhit.read(recl-32)
    if do_tcal:
        hit = hits.domhit("%12.12x" % mbid)
        hit.decode(buf)
        tcal.translateDOMtoDOR(hit)
        utc = hit.utclk
    if mbid not in fout:
        fout[mbid] = open(("%12.12x" % mbid) + '.hit', 'wb')
    fout[mbid].write(
        struct.pack(
            '>iiqiiq', recl, fmt, mbid, 0, 0, utc
            )
        )
    fout[mbid].write(buf)
    
