#!/usr/bin/python


"""
Threaded monitoring
2004-07-17 K. Hanson (kael.hanson@icecube.wisc.edu)
Changes 15/11/05: HL
- Update default parameters for inexisting db DOM.
- New parameters - number of lines, HV, disc, dead time
- Check HVMax from table domtune in FAT database
"""

import sys, time, os
import re
from icecube.domtest.ibidaq import ibx
from icecube.domtest.dor import Driver
from xmlrpclib import ServerProxy
from threading import Thread
from getopt import getopt
import signal
import MySQLdb
from threading import Lock

def usage():
    print >>sys.stderr, \
          """usage::multimon.py [ -H <db-server> ] [ -S <site> ] [ -o <output-dir> ] [-d <scaler-Dead time>0..11]  [-c <discriminator setting> 0..1023] [-l 
<Number_of_output_lines>] [-V <High voltage>] [-g <gain in E7 units>5,1,0.5,0.05][ domhub ... ]"""

monitorDir = os.path.expanduser("~/monitoring")
dbhost     = "localhost"
threads    = [ ]
running    = 1
ScalerDeadTime=0
RunTime=-1
HighVoltage=-1
Disc=-1
lines=0
Gain=-1

opts, args = getopt(
    sys.argv[1:], "H:ho:S:l:V:c:d:g:"
    )

Site = "DESY"
ScalerDeadTime=0
RunTime=-1
for o, a in opts:
    if o == "-H":
        dbhost = a
    elif o == "-o":
        monitorDir = a
    elif o == "-S":
        Site = a
    elif o == "-g":
	Gain=float(a)
        if (Gain == 5): 
		Gain = 0 # gain 5e7, use hv0
        elif (Gain == 1):
 		Gain = 1 # gain 1e7, us hv1
        elif (Gain == 0.5): 
		Gain = 3 # gain 5e6, us hv2
        elif (Gain == 0.05):
		Gain = 3 # gain 5e5, us hv3
        else:
            print 'Illegal Gain value, setting can be 5,1,0.5,0.05'
            sys.exit(1)
    elif o == "-d":
        ScalerDeadTime = int(a)
        if int(ScalerDeadTime)>15:
            print 'Dead-time value must be [0..15]', ScalerDeadTime
            sys.exit(1)
        if int(ScalerDeadTime<0):
            print 'Dead-time value must be [0..15]', ScalerDeadTime
            sys.exit(1)
    elif o == "-l":
        RunTime = int(a)
    elif o == "-c":
        Disc = int(a)
        if Disc>1023:
            print 'Discriminator values must be [0..1023]'
            sys.exit(1)
        if Disc<0:
            print 'Discriminator values must be [0..1023]'
            sys.exit(1)
    elif o == "-V":
        if (Gain == -1):
            HighVoltage = int(a)
        else:
            print 'Gain already set, cannot set High voltage as well'
            sys.exit(1)
    elif o == "-h":
        usage()
        sys.exit(1)

def stopper(signum, frame):
    print "Caught signal - stopping threads."
    for t in threads:
        t.running = 0
    for t in threads:
        t.join()

class Monitor(Thread):
    def __init__(self, host, port,  Disc, Gain, RunTime, ScalerDeadTime, HighVoltage):
        Thread.__init__(self)
        self.Disc = Disc
        self.ScalerDeadTime = ScalerDeadTime
        self.RunTime = RunTime
        self.Gain = Gain
	self.HighVoltage = HighVoltage
        self.host = host
        self.port = port
        self.running = 1
    def run(self):
	lines=0
        init_counter = 0
        while init_counter < 4:
            self.q = ibx(self.host, self.port)
            domid = self.q.getId()
            if re.compile("[0-9A-Fa-f]").match(domid): break
            print >> sys.stderr, "***WARNING - DOM at %s:%d got bad ID" \
                  % (self.host, self.port)
            del(self.q)
            init_counter += 1

        if init_counter == 4:
            print >> sys.stderr, "***ERROR - DOM at %s:%d failed to init" \
                  % (self.host, self.port)
            return
        
#        self.f = file(monitorDir + "/" + domid + ".moni", "a")
        
        # Get info from the DB - make sure to surround in locking
        # objects to synchronize access to the db connection
        # (not thread-safe on all systems - Linux included)
        dbLock.acquire()
        c = db.cursor()
        c.execute(
            "SELECT atwd0_trigger_bias,atwd1_trigger_bias," + \
            "atwd0_ramp_rate,atwd1_ramp_rate," + \
            "atwd0_ramp_top,atwd1_ramp_top," + \
            "atwd_analog_ref,fe_pedestal," + \
            "fadc_ref,spe_disc,hv1, doms.name,doms.domid, hvmax, " + \
            "hv0,hv2,hv3 "+\
            "FROM domtune,doms WHERE " + \
            "domtune.mbid='%s' AND doms.mbid=domtune.mbid;" % (domid)
        )

 
        r = c.fetchone()
        dbLock.release()
        
        
        if r == None:
            r = [ 0 ] * 17
            print >>sys.stderr, \
                  "WARNING: DOM %s not in database - " \
                  "set to default values" % (domid)
            r[0]  = 850     #  atwd0_trigger_bias
            r[1]  = 850     # atwd1_trigger_bias
            r[2]  = 350    # atwd0_ramp_rate
            r[3]  = 350    # atwd1_ramp_top
            r[4]  = 2300     # atwd0_ramp_top
            r[5]  = 2300     # atwd1_ramp_top
            r[6]  = 2250    # atwd_analog_ref
            r[7]  = 2130    # fe_pedestal
            r[8]  = 800     # fadc_ref
            r[9]  = 565     # spe_disc
            r[10] = 1300    # hv1
            r[11] = 'Unknown' # doms.name
            r[13] = 2047  # hvmax
            r[14] = 1300    # hv0
            r[15] = 1300    #hv2
            r[16] = 1300    #hv3
            self.f = file(monitorDir + "/" + domid + ".moni", "a")
            
        else:
            print >>sys.stderr, "Found DOM %s (%s)" % (r[11], domid)
            if (Site == "DESY"):
                self.f = file(monitorDir + "/" + domid + ".moni", "a")  
            else:
                self.f = file(monitorDir + "/" + domid + "-" + r[12] + "-" + r[11] + ".moni", "a")

            self.setName("%s:%s" % (r[11], domid))

        del(c)
        
        self.q.setDAC(0, r[0])
        self.q.setDAC(4, r[1])
        self.q.setDAC(1, r[2])
        self.q.setDAC(5, r[3])
        self.q.setDAC(2, r[4])
        self.q.setDAC(6, r[5])
        self.q.setDAC(3, r[6])
        self.q.setDAC(7, r[7])
        if (self.Disc == -1):
            self.Disc=r[9]
        self.q.setDAC(9, self.Disc)
        print  >>sys.stderr, "Debug: Disc set to ", self.Disc

        self.q.setSPEDeadtime(ScalerDeadTime)
        print  >>sys.stderr, "Debug: Dead time set to ", ScalerDeadTime

        # set HV to the set point or to the Max Setting allowed:
        HVSet = r[10]

        if (int(self.Gain)==0):
              HVSet=r[14]
        elif (int(self.Gain)==1):  
		HVSet=r[10];
        elif (int(self.Gain)==2):  
		HVSet=r[15];	                                                                                                                                                  
        elif (int(self.Gain)==3):
		HVSet=r[16];
        elif (self.HighVoltage != -1): 
		HVSet=self.HighVoltage;
        self.q.enableHV()
        self.q.setHV(int(2*min(HVSet, r[13])))
        print  >>sys.stderr, 'Debug: HV set to ', int(2*min(HVSet, r[13]))



            
        time.sleep(5.0)
        
        # Readout the time and the pressure about 1 time a minute
        tpc = 0
        while self.running:
            t = time.time()
            rate = 0
            for i in range(10):
                rate += self.q.spef()
                time.sleep(0.125)
            txt = "%.1f %d" % (t, rate)
	    lines=lines+1
	    if (self.RunTime>0):
            	if (int(lines) > int(self.RunTime)):
                	print >>sys.stderr, "Line limit reached. stopping"
                	sys.exit()

            if tpc == 0:
                temp = self.q.readTemperature()
                if temp > 32768:
                    temp = temp - 65536
                temp = temp / 256.0
                pressure = self.q.readPressure()
                hv = self.q.readHV()
                txt += " %.1f %d %d" % (temp, pressure, hv)
                tpc = 10
            tpc -= 1
            print >>self.f, txt
            self.f.flush()

        self.f.close()

db         = MySQLdb.connect(user='penguin', db='fat', host=dbhost)
dbLock     = Lock()

signal.signal(signal.SIGHUP, stopper)

for h in args:
    d = ServerProxy("http://" + h + ":7501")
    d.scan()
    doms = d.discover_doms()
    for loc in doms.values():
        port = 5000 + int(loc[0])*8 + int(loc[1])*2
        if loc[2] == 'B': port += 1
	mm = Monitor(h, port, Disc, Gain, RunTime, ScalerDeadTime, HighVoltage)
	
        threads.append(mm)
        mm.start()

# time.sleep(10000000)
