
import re
import MySQLdb
from icecube.domtest.db import get_db_connection
from icecube.domtest.domconfiguration import DOMConfigurator
from datetime import datetime, timedelta, tzinfo

comment = re.compile("^\s*#")
runbe   = re.compile("^(\S+) RUN (BEGIN|END)")
laser   = re.compile("^(\S+) (\S+) LASER FREQ (\S+) FW (\d)")
mono    = re.compile("^(\S+) (\S+) MONO ON LAMBDA (\S+) FW (\d)")

__m2p_map = dict()

db = get_db_connection()

def mbid2prodid(mbid):
    if mbid not in __m2p_map:
        __m2p_map[mbid] = DOMConfigurator(db, mbid)
    return __m2p_map[mbid].prodId
        
class MonitorEOFException:
    pass
 
class UTC(tzinfo):
    """UTC timezone class - see Python Library Reference"""
    def utcoffset(self, dt):
        return timedelta(0)
    
    def tzname(self, dt):
        return "UTC"
    
    def dst(self, dt):
        return timedelta(0)

utc = UTC()
          
class MoniFile:
    """
    Does moni file things
    """
    def __init__(self, f, mbid):
        self.f = f
        self.t = 0
        self.temp     = None
        self.pressure = None
        self.hv       = None
        self.mbid = mbid
        
    def nextRecord(self):
        """
        Gets next line of file returns
            (time, rate, temp, pressure, hv)
        tuple if a line was read or
            None
        at end-of-file
        """
        s = self.f.readline()
        if len(s) == 0: return False
        v = s.split()
        self.t = float(v[0])
        self.rate = float(v[1])
        if len(v) > 2:
            self.temp = float(v[2])
            self.pressure = float(v[3])
            self.hv   = float(v[4])
        return True
        
    def seekTo(self, tseek):
        """
        Find quickly the first time beyond tseek.
        """
        while self.nextRecord() and self.t < tseek: pass
        return self.t >= tseek
        
class LUXFile:
    """
    This class encapsulates a LUX run.  This class has the
    following public fields:
        - runs : list of LUXIlluminator or derived classes
          that holds the actual light source illumination
          interval data
    (C) 2005 - K. Hanson
    """
    def __init__(self, f):
        """
        Load in the LUX lightsource data from a file stream.  
        """
        self.runs = list()
        while True:
            s = f.readline()
            if len(s) == 0: break
            if comment.match(s): continue
            m = runbe.search(s)
            if m:
                if m.group(2) == "BEGIN":
                    self.runs.append(LUXRun())
                    self.runs[-1].begin(float(m.group(1)))
                else:
                    self.runs[-1].end(float(m.group(1)))
                continue
            m = laser.search(s)
            if m:
                t0 = float(m.group(1))
                t1 = float(m.group(2))
                freq = float(m.group(3))
                fw = int(m.group(4))
                self.runs[-1].addLaser(t0, t1, fw, freq)
                continue
            m = mono.search(s)
            if m:
                t0 = float(m.group(1))
                t1 = float(m.group(2))
                wavelength = float(m.group(3))
                fw = int(m.group(4))
                self.runs[-1].addMono(t0, t1, fw, wavelength)
        
    def processMonitorFile(self, f):
        """
        Process moni file over all runs in this LUX file.
        """
        for run in self.runs:
            run.processMonitorFile(f)

class LUXIlluminator:
    """
    Generic illuminator activity descriptor.  Fields are
        .t0 : illuminator start time
        .t1 : illuminator end time
        .fw : filter wheel setting
    """
    def __init__(self, run, t0, t1, fw):
        self.run = run
        self.t0 = t0
        self.t1 = t1
        self.fw = fw
        self.avg_rate = dict()
        
    def processMonitorFile(self, f):
        f.seekTo(self.t0 + 15)
        nrate = 0
        avg_rate = 0.0
        while f.nextRecord() and f.t < self.t1 - 15:
            nrate += 1
            avg_rate += f.rate
        self.avg_rate[f.mbid] = avg_rate / nrate
        
class LUXLaser(LUXIlluminator):
    """
    Derived class - adds .freq field.
    """
    def __init__(self, run, t0, t1, fw, freq):
        LUXIlluminator.__init__(self, run, t0, t1, fw)
        self.freq = freq
        
    def todb(self, c):
        for mbid, rate in self.avg_rate.items():
            if mbid in self.run.baseline:
                prod_id = mbid2prodid(mbid)
                bkg = self.run.baseline[mbid][1]
                c.execute(
                    """
                    INSERT INTO LUXLaser
                    VALUES(%s,%s,%s,%s,%s)
                    """, 
                    (
                        self.run.luxrun_id, 
                        prod_id, 
                        self.freq, 
                        self.fw,
                        rate-bkg
                    )
                )
                    
        
class LUXMono(LUXIlluminator):
    """
    Derived class - adds .wavelength field.
    """
    def __init__(self, run, t0, t1, fw, wavelength):
        LUXIlluminator.__init__(self, run, t0, t1, fw)
        self.wavelength = wavelength
        
    def todb(self, c):
        for mbid, rate in self.avg_rate.items():
            if mbid in self.run.baseline:
                prod_id = mbid2prodid(mbid)
                bkg = self.run.baseline[mbid][1]
                c.execute(
                    """
                    INSERT INTO LUXMono
                    VALUES(%s,%s,%s,%s,%s)
                    """, 
                    (
                        self.run.luxrun_id, 
                        prod_id, 
                        self.wavelength,
                        self.fw,
                        rate-bkg
                    )
                )
        
class LUXRun:
    """
    Class holding LUX run information:
        - begin_time  beginning of run
        - end_time    end of run
        - baseline    pre-run and post-run noise baseline
        - ill:        list of illuminator blocks
    """
    def __init__(self):
        self.ill = list()
        
    def begin(self, begin_time):
        self.begin_time = begin_time
        self.end_time   = begin_time
        self.baseline   = dict()
        
    def end(self, end_time):
        self.end_time = end_time
    
    def addLaser(self, t0, t1, fw, freq):
        """
        Append laser run to list of runs for this LUXRun.
        """
        self.ill.append(LUXLaser(self, t0, t1, fw, freq))
        
    def addMono(self, t0, t1, fw, wavelength):
        """
        Append monochromator run.
        """
        self.ill.append(LUXMono(self, t0, t1, fw, wavelength))
        
    def processMonitorFile(self, f):
        """
        Process a *.moni file.  Pass in an open file object to this file.
        """
        self.baseline[f.mbid] = [ None, None ]
        f.seekTo(self.begin_time - 30)
        self.temp = f.temp
        nrate = 0
        avg_rate = 0.0
        while f.t < self.begin_time:
            nrate += 1
            avg_rate += f.rate
            f.nextRecord()
        if nrate > 0: 
            self.baseline[f.mbid][0] = avg_rate / nrate
        for x in self.ill:
            x.processMonitorFile(f)
        f.seekTo(self.end_time + 10)
        nrate = 0
        avg_rate = 0.0
        for i in range(10):
            nrate += 1
            avg_rate += f.rate
            if not f.nextRecord(): break
        self.baseline[f.mbid][1] = avg_rate / nrate
        
    def todb(self, c):
        """
        Insert run information into database
        """
        begin_dt = datetime.fromtimestamp(self.begin_time, utc)
        c.execute(
            """
            INSERT INTO LUXRun(begin_time, temperature) 
            VALUES(%s,%s)
            """, (begin_dt, self.temp)
        )
        self.luxrun_id = c.lastrowid
        for x in self.ill:
            x.todb(c)
        