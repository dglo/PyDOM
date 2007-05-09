#!/bin/env python

import sys, time, math
from icecube.domtest import pulser, ibidaq as daq
from getopt import getopt

##
# $Id: occupancy.py,v 1.1 2004/05/25 14:46:38 kaeld Exp $
##

pulser_host = 'lantronix'
pulser_port = 3010
integration = 25
pulse_freq  = 10000
n           = 1
verbose     = 1
marker      = 0
hv          = 3000
disc        = 535

def help():
    sys.stdout.write("""
Python occupancy calculation script
$Id: occupancy.py,v 1.1 2004/05/25 14:46:38 kaeld Exp $
usage :: occupancy.py [ options ] <host> <port>
options are:
        -h                help
        -a <int>          integration time
        -f <float>        pulser frequency
        -n <int>          repetition count
        -v <int>          set verboseness
        -k                use marker - not fast pulse
        --hv=<int>        set HV
        --spe-disc=<int>  set discriminator threshold
"""
                     )

def rate(q, p, n):
    """Calculate rate off vs. on."""
    global marker
    bkg = 0
    sig = 0
    
    for i in range(n):
        p.allOff()
        time.sleep(0.25)
        bkg += q.spef()
        if marker:
            p.markerOn()
        else:
            p.fastOn()
        time.sleep(0.25)
        sig += q.spef()

    p.allOff()
    
    return (bkg, sig)

opts, args = getopt(sys.argv[1:], 'hkn:f:a:-v:', [ 'hv=', 'spe-disc=' ])

for o, a in opts:
    if o == '-h':
        help()
        sys.exit(1)
    elif o == '-k':
        marker = 1
    elif o == '-f':
        pulse_freq = float(a)
    elif o == '-n':
        n = int(a)
    elif o == '-a':
        integration = int(a)
    elif o == '-v':
        verbose = int(a)
    elif o == '--hv':
        hv = int(a)
    elif o == '--spe-disc':
        disc = int(a)

# Calibrate the occupancy of the pulse
p = pulser.pulser(pulser_host, pulser_port)
p.setPulseFrequency(pulse_freq)
p.allOff()

host = args.pop(0)
port = int(args.pop(0))

q = daq.ibx(host, port)
# print "Connected to DOM: ", q.getId()

q.setDAC(9, disc)
q.enableHV()
q.setHV(hv)
q.setSPEDeadtime(4)
time.sleep(5.0)

s = 10.0 / integration
for i in range(n):
    (bkg, sig) = rate(q, p, integration)
    if verbose > 2: print bkg, sig
    xs = sig - bkg
    xs_err = math.sqrt(bkg + sig)
    xs *= s
    xs_err *= s
    print "%.3f +/- %.3f" % (xs / pulse_freq, xs_err / pulse_freq)

p.allOff()
q.setHV(0)
q.disableHV()

