#!/bin/env python

"""
Local Coincidence test module
(C) 2005 Kael Hanson (kael.hanson@icecube.wisc.edu)

This module tests the LC function of a triplet of DOMs
by setting up LC between them, collecting hits, and
compairing hit times.  The DOMs must be physically
connected so that the 'down' module's LC_UP is
connected to the 'mid' module which is connected
LC up-wise to the 'up' module's LC_DOWN and so forth.

        'up'  dom: 00B
        'mid' dom: 00A
        'dn'  dom: 01B

etc.

"""

import sys, os, time, math
from struct import *
from icecube.daq import domapp
from icecube.daq.hal import *
from icecube.domtest.rapcal import RAPCal
from icecube.domtest.hits import domhit
from icecube.domtest.lightsource import pulser
import signal

dom_up = None
dom_mi = None
dom_dn = None

def int_handler(signum, frame):
    print >>sys.stderr, "terminating run ..."
    dom_up.app.endRun()
    dom_mi.app.endRun()
    dom_dn.app.endRun()
    sys.exit(1)
    
class dom_harness:
    
    def __init__(self, cwd, **opts):
        self.card = int(cwd[0])
        self.pair = int(cwd[1])
        self.dom  = cwd[2]

        self.gpsbuf = None
        self.rapcal = None
        self.rapcal_ok = False
        self.last_tcal_time = 0
        self.tcal_period    = 1
        
        self.app  = domapp.DOMApp(self.card, self.pair, self.dom)
        self.mbid = self.app.getMainboardID()

        # Start configuring
        # HV may be switched off for the middle dom
        self.app.enableHV()
        if 'hv' in opts:
            self.app.setHV(opts['hv'])
        else:
            self.app.setHV(2800)
            
        self.app.writeDAC(DAC_ATWD0_TRIGGER_BIAS, 850)
        self.app.writeDAC(DAC_ATWD1_TRIGGER_BIAS, 850)
        self.app.writeDAC(DAC_ATWD0_RAMP_RATE, 350)
        self.app.writeDAC(DAC_ATWD1_RAMP_RATE, 350)
        self.app.writeDAC(DAC_ATWD0_RAMP_TOP, 2300)
        self.app.writeDAC(DAC_ATWD1_RAMP_TOP, 2300)
        self.app.writeDAC(DAC_ATWD_ANALOG_REF, 2250)
        self.app.writeDAC(DAC_PMT_FE_PEDESTAL, 2130)
        self.app.writeDAC(DAC_SINGLE_SPE_THRESH, 943)
        self.app.writeDAC(DAC_MULTIPLE_SPE_THRESH, 650)
        self.app.writeDAC(DAC_FAST_ADC_REF, 800)
        self.app.writeDAC(DAC_INTERNAL_PULSER, 80)
        self.app.setTriggerMode(2)
        self.app.setPulser(mode=domapp.BEACON, rate=1)
        self.app.selectMUX(255)
        self.app.setEngFormat(0, 4*(2,), (32, 0, 0, 0))

        # Clear out stale data
        #self.app.resetLookbackMemory()
        #while 1:
        #    w = self.app.getWaveformData()
        #    if len(w) == 0: break
            
        # Grab the syncgps data *NOW*
        self.syncgps()
        self.tcal()
        
    def syncgps(self):
        """
        Returns the 22-byte GPS string from the syncgps procfile
        """
        fgps = os.open('/proc/driver/domhub/card%d/syncgps' %
                       self.card,
                       os.O_RDONLY
                       )
        self.gpsbuf = os.read(fgps, 22)
        os.close(fgps)

    def tcal(self):
        t0 = time.time()
        if t0 - self.last_tcal_time < self.tcal_period: return
        self.last_tcal_time = t0
        ft = os.open('/proc/driver/domhub/card%d/pair%d/dom%c/tcalib' %
                     (self.card, self.pair, self.dom),
                     os.O_RDWR
                     )
        os.write(ft, 'single\n')
        time.sleep(0.025)
        buf = os.read(ft, 292)
        os.close(ft)
        if len(buf) != 292:
            print >>sys.stderr, "ERROR: short TCAL read (%d bytes)" % len(buf)
            return
        rc = RAPCal(buf[4:])
        rc.setGPSString(self.gpsbuf)
        if self.rapcal is not None:
            rc.doRAPCal(self.rapcal)
            self.rapcal_ok = True
        self.rapcal = rc
        
    def get_hits(self):
        self.tcal()
        # Retry on empty data replies - this is a big
        # performance killer so take it out if it
        # becomes problematic
        for itry in range(5):
            w = self.app.getWaveformData()
            if len(w) > 0: break
            time.sleep(0.05)
        hits = list()
        while len(w) > 0:
            nb, = unpack('>H', w[0:2])
            h  = domhit(self.mbid)
            h.decode(w[0:nb])
            if self.rapcal_ok:
                h.utclk = self.rapcal.dom2UT(h.domclk)
            else:
                h.utclk = -1
            hits.append(h)
            w = w[nb:]
        return hits


def calc_rate(hits):
    if len(hits) < 2:
        return 0.0
    return len(hits) / (1E-10*(hits[-1].utclk - hits[0].utclk))

def meanstd(list):
    sum = 0.0
    for x in list:
        sum += x
    x0 = sum / len(list)
    sum = 0.0
    for x in list:
        sum += (x - x0)**2
    std = math.sqrt(sum/len(list))
    return x0, std

def collect(dom_up, dom_dn, n=100):
    dom_up.app.startRun()
    dom_dn.app.startRun()
    
    hup = list()
    hdn = list()
    loop_counter = 0
    t0  = time.time()
    while (len(hup) < nacq or len(hdn) < nacq) and time.time() - t0 < 10:
        hup += dom_up.get_hits()
        hdn += dom_dn.get_hits()
        #print len(hup), len(hdn)
        loop_counter += 1
        if (len(hup) == 0 or len(hdn) == 0) and loop_counter > 1000: break

    if len(hup) > 5 and len(hdn) > 2:
    
        print "up rate:", calc_rate(hup)
        print "dn rate:", calc_rate(hdn)
        hits = hup + hdn
        hits.sort(lambda x, y: cmp(x.utclk, y.utclk))
        
        nlc = 0
        
        dtlist = []
        for i in range(1, len(hits)):
            h0 = hits[i-1]
            h1 = hits[i]
            dt = 0.1*(h1.utclk - h0.utclk)
            if dt > 1000: continue
            if h0.domid != dom_up.mbid:
                tmp = h0
                h0 = h1
                h1 = tmp
                dt = -dt
            nlc += 1
            dtlist.append(dt)

        if len(dtlist) > 0:
            print >>sys.stderr, nlc, len(hits), \
                  "frac = %.1f%%" % (100.0*float(nlc)/n), \
                  "mean = %.1f, std = %.1f" % meanstd(dtlist)

    dom_up.app.endRun()
    dom_dn.app.endRun()
    
    
if __name__ == "__main__":

    from getopt import getopt

    nacq = 1000
    opts, args = getopt(sys.argv[1:], 'N:')

    for o, a in opts:
        if o == '-N':
            nacq = int(a)

    cwd_up = args.pop(0)
    cwd_mi = args.pop(0)
    cwd_dn = args.pop(0)

    # Make connections to the domapp for up and down DOMs
    dom_up = dom_harness(cwd_up)
    dom_mi = dom_harness(cwd_mi, hv=0)
    dom_dn = dom_harness(cwd_dn)

    # Wait for HV to settle
    time.sleep(2.0)

    p = pulser('lantronix-spts.icecube.wisc.edu', 3002)
    p.setPulseFrequency(100)
    p.fastOn()

    signal.signal(signal.SIGINT, int_handler)

    for delay in range(1100, 1300, 25):
        print >>sys.stderr, "Setting delay parameter to", delay
        dom_up.app.setLC(mode=2,
                         transmit=1,
                         type=2,
                         window=(100, 100),
                         cablelen=8*(delay,),
                         span=2
                         )
        dom_mi.app.setLC(mode=1,
                         transmit=3,
                         type=2,
                         window=(1000, 1000),
                         cablelen=8*(550,),
                         span=1
                         )
        dom_dn.app.setLC(mode=3,
                         transmit=2,
                         type=2,
                         window=(100, 100),
                         cablelen=8*(delay,),
                         span=2
                         )
        dom_mi.app.startRun()
        collect(dom_up, dom_dn, nacq)
        dom_mi.app.endRun()
        
    p.allOff()
    
