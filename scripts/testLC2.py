#!/bin/env python

"""
Local Coincidence test module
(C) 2005 Kael Hanson (kael.hanson@icecube.wisc.edu)

This module tests the LC function of a pair of DOMs
by setting up LC between them, collecting hits, and
compairing hit times.  The two DOMs must be physically
connected so that the 'down' module's LC_UP is
connected to the 'up' module and the 'up' module's
LC_DOWN is connected to the 'down' module.  Using
a standard breakout box, the configuration would
probably go something like

        'up' dom: 00B
        'dn' dom: 00A

or

        'up' dom: 00A
        'dn' dom: 01B

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
dom_dn = None

def int_handler(signum, frame):
    print >>sys.stderr, "terminating run ..."
    dom_up.app.endRun()
    dom_dn.app.endRun()
    sys.exit(1)
    
class dom_harness:
    
    def __init__(self, cwd):
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
        self.app.enableHV()
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
                h.utclk = -1L
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
        hits.sort(lambda x,y: cmp(x.utclk, y.utclk))
        
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
        
        print >>sys.stderr, nlc, len(hits), \
              "frac = %.1f%%" % (100.0*float(nlc)/n), \
              "mean = %.1f, std = %.1f" % meanstd(dtlist)

    dom_up.app.endRun()
    dom_dn.app.endRun()
    
    
if __name__ == "__main__":

    from getopt import getopt

    nacq = 1000
    up_rx, up_tx = (3, 3)
    dn_rx, dn_tx = (2, 3)
    del0, del1, ddel = (450, 750, 25)
    win  = 100
    pulserInetAddr = None
    opts, args = getopt(sys.argv[1:], 'D:L:N:P:W:U:')

    for o, a in opts:
        if o == '-D':
            dn_rx, dn_tx = a.split(',')
            dn_rx = int(dn_rx)
            dn_tx = int(dn_tx)
        elif o == '-L':
            del0, del1, ddel = a.split(',')
            del0 = int(del0)
            del1 = int(del1)
            ddel = int(ddel)
        elif o == '-N':
            nacq = int(a)
        elif o == '-P':
            pulserInetAddr = a
        elif o == '-U':
            up_rx, up_tx = a.split(',')
            up_rx = int(up_rx)
            up_tx = int(up_tx)
        elif o == '-W':
            win = int(a)
            
    cwd_up = args.pop(0)
    cwd_dn = args.pop(0)

    # Make connections to the domapp for up and down DOMs
    dom_up = dom_harness(cwd_up)
    dom_dn = dom_harness(cwd_dn)

    # Wait for HV to settle
    time.sleep(2.0)

    p = None
    if pulserInetAddr is not None:
        try:
            ps = pulserInetAddr.index(':')
            pulserPort = int(pulserInetAddr[ps+1:])
            pulserInetAddr = pulserInetAddr[0:ps]
            p = pulser(pulserInetAddr, pulserPort)
            p.setPulseFrequency(100)
            p.fastOn()
        except ValueError:
            print >>sys.stderr, "WARNING: pulser addr parameter not " +\
                "host:port format - ignoring pulser"
            

    signal.signal(signal.SIGINT, int_handler)
    
    for delay in range(del0, del1, ddel):
        print >>sys.stderr, "Setting delay parameter to", delay
        dom_up.app.setLC(mode=up_rx,
                         transmit=up_tx,
                         type=2,
                         window=(win,win),
                         cablelen=8*(delay,),
                         span=1
                         )
        dom_dn.app.setLC(mode=dn_rx,
                         transmit=dn_tx,
                         type=2,
                         window=(win,win),
                         cablelen=8*(delay,),
                         span=1
                         )
        collect(dom_up, dom_dn, nacq)
    
    if p is not None: p.allOff()
    
