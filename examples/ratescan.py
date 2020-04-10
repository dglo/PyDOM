#!/usr/bin/env python

from __future__ import print_function
from builtins import range
import sys, time
import icecube.domtest.ibidaq as daq
from getopt import getopt

hv = -1
step = 1
integration = 10
deadtime    = 0

def usage():
    sys.stderr.write("""Usage: ratescan [ options ] <host> <port> <dac-from> <dac-to>
Options are ...
        -V <int>        HV DAC setting
        -s <int>        step
        -a <int>        aperture size (in 0.1 s steps)
        -d <int>        spe scaler deadtime code
        -h              this help
""");
    sys.exit(1)

opts, args = getopt(sys.argv[1:], 'ha:d:s:V:', [ ])
for o, a in opts:
    if o == '-s':
        step = int(a)
    elif o == '-V':
        hv = int(a)
    elif o == '-a':
        integration = int(a)
    elif o == '-h':
        usage()
    elif o == '-d':
        deadtime = int(a)
        
q = daq.ibx(args.pop(0), int(args.pop(0)))

q.setSPEDeadtime(deadtime)

if hv < 0:
    q.disableHV()
else:
    q.enableHV()
    q.setHV(hv)
    time.sleep(1.0)
    
d0 = int(args.pop(0))
d1 = int(args.pop(0))

for dac in range(d0, d1, step):
    q.setDAC(9, dac)
    r = 0
    for i in range(integration):
        time.sleep(0.150)
        r += q.spef()
    mv = 2.44E-02*(0.4*dac - 0.1*q.getDAC(7))*5
    print("%d %.2f %d" % (dac, mv, r))

q.disableHV()
q.s.close()
