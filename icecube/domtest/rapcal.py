"""
RAPCal data structures and functions
"""

from struct import unpack
import time
from calendar import timegm
from cStringIO import StringIO
from numpy import array, sum
from icecube.domtest.util import softdisc

"""The RAPCal Discriminator threshold."""
DISC_THRESHOLD = 50.0

class RAPCal:
    """
    Data class for TCAL record - fields are ...
        - dorTx         time of pulse transmitted DOR -> DOR
        - dorRx         time of pulse received at DOR <- DOM
        - dorWaveform   64 short samples of waveform recorded by DOR
        - domTx         time of pulse transmitted DOM -> DOR
        - domRx         time of pulse received at DOM <- DOR
        - domWaveform   64 short samples of waveform recorded by DOM
        - dorGPSClock   DOR clock counter as of the last GPS string reading
        - gpsString     gps string, format is %j:%H:%M:%S # j is day of year
    """
    
    def __init__(self, buf, fmtver=0):
        s = StringIO(buf)
        """
        Create from TCAL raw buffer
        fmtver = 1 supports the GPS string deliverd by the DOR Card
        fmtver = 2 is a special format that comes out of the DOMHub-Prod
        """
        
        if fmtver == 2:
            bytes, f0, f1 = unpack("hbb", s.read(4))
            self.dorTx, self.dorRx = unpack("qq", s.read(16))
            self.dorWaveform = unpack("64h", s.read(128))
            self.domRx, self.domTx = unpack("qq", s.read(16))
            self.domWaveform = unpack("64h", s.read(128))
            self.setGPSString(s.read(22))
        else:
            self.dorTx, self.dorRx = unpack("qq", s.read(16))
            self.dorWaveform = []
            for i in range(64):
                self.dorWaveform.append(unpack("h", s.read(2))[0])
            self.domRx, self.domTx = unpack("qq", s.read(16))
            self.domWaveform = []
            for i in range(64):
                self.domWaveform.append(unpack("h", s.read(2))[0])

            if fmtver == 1:
                self.setGPSString(s.read(22))
            else:
                self.gpsString = ""
                self.dorGPSClock = -1
            
        self.clkratio = None
        self.cablelen = None
        self.dorrxc   = None
        self.domrxc   = None

    def setGPSString(self, gpsbuf):
        soh, self.gpsString, self.gpsQuality = unpack("c12sc", gpsbuf[0:14])
        self.dorGPSClock, = unpack('>q', gpsbuf[14:22])
        self.dorGPSClock *= 500
        self.gpsday  = int(self.gpsString[0:3])
        self.gpshour = int(self.gpsString[4:6])
        self.gpsmin  = int(self.gpsString[7:9])
        self.gpssec  = int(self.gpsString[10:12])
        self.gps_offset = 10000000000*long(
            60*(60*(24*(self.gpsday-1) + self.gpshour)+ self.gpsmin) + self.gpssec
            ) - self.dorGPSClock
            
    def getGPSTime(self, year='1970'):
        """
        Return GPS time in seconds in UNIX time (seconds since 1 Jan 1970)

        The GPS string does not contain the year, hence it must be provided by the
        calling program. Otherwise defaults to 1970
        """
        gpsString = "%s:%s" % (year, self.gpsString)
        return timegm(time.strptime(gpsString, '%Y:%j:%H:%M:%S'))
    
    def getDorTx(self):
        """Return in 0.1 ns ticks."""
        return self.dorTx * 500

    def getDomTx(self):
        """Return in 0.1 ns ticks."""
        return self.domTx * 250
    
    def getDorRxC(self):
        """Return corrected time based on algorithm."""
        if self.dorrxc is None:
            a = array(self.dorWaveform[0:48], 'd')
            #a = array('d', self.dorWaveform[0:48])
            baseline = sum(a[0:10])/10.0
            e = softdisc(a, baseline + DISC_THRESHOLD)
            self.dorrxc = 500*self.dorRx + long(500.0*(e[0].x - 48))
        return self.dorrxc
    
    def getDomRxC(self):
        """Return corrected time based on algorithm."""
        if self.domrxc is None:
            a = array(self.domWaveform[0:48], 'd')
            #a = array('d', self.dorWaveform[0:48])
            baseline = sum(a[0:10])/10.0
            e = softdisc(a, baseline + DISC_THRESHOLD)
            self.domrxc = 250*self.domRx + long(500.0*(e[0].x - 48))
        return self.domrxc

    def doRAPCal(self, r0):
        """Perform full RAPCal calibration on two neighbor packets."""
        if self.clkratio is None or self.cablelen is None:
            self.clkratio = float(self.getDorTx() - r0.getDorTx()) / \
                            float(self.getDomRxC() - r0.getDomRxC())
            self.cablelen = (self.getDorRxC() - self.getDorTx() - \
                             long(self.clkratio*(self.getDomTx() - \
                             self.getDomRxC()))) / 2

    def dom2Dor(self, domclk):
        return long(self.clkratio * (250*domclk - self.getDomRxC())) + \
            self.getDorTx() + self.cablelen
            
    def dom2UT(self, domclk):
        dor = self.dom2Dor(domclk)
        return dor + self.gps_offset
    
class TimeCalibrator:
    """
    The IceCube TimeCalibrator class.  Given a .tcal
    stream from TestDAQ, this class reads in the
    tcal records, puts them into a buffer, and provides
    an easy interface for calibration of the DOM clocks
    to surface time.
        (C) 2005 Kael Hanson (kael.hanson@icecube.wisc.edu)
    """
    def __init__(self, f, fmtver=0):
        """
        Construct a TimeCalibrator instance from
        a stream.  fmtver =
            0 : old, pre-2005 format
            1 : New 2005 S. Pole format /w/ GPS
        """
        self.rcd = dict()
        if fmtver == 2:
            while True:
                hdr = f.read(16)
                if len(hdr) != 16: return
                recl, fmtid, mbid = unpack('>iiq', hdr)
                if fmtid != 201: continue
                buf = f.read(recl-16)
                mbid = "%12.12x" % mbid
                if mbid not in self.rcd:
                    self.rcd[mbid] = list()
                self.rcd[mbid].append(RAPCal(buf, fmtver))
            
        if fmtver == 0:
            recl = 300
        elif fmtver == 1:
            recl = 334
        else:
            raise ValueError, "Unknown TCAL format version %d" % fmtver
        while True:
            buf = f.read(recl)
            if len(buf) != recl: break
            mbid = "%12.12x" % unpack("q", buf[0:8])
            if mbid not in self.rcd:
                self.rcd[mbid] = list()
            if fmtver == 0:
                self.rcd[mbid].append(RAPCal(buf[12:]))
            elif fmtver == 1:
                self.rcd[mbid].append(RAPCal(buf[24:], fmtver))
               
            
    def translateDOMtoDOR(self, hit, year='1970'):
        """
        Convenience function to translate a Hit time
        from DOM clock units to DOR units.
        Note that no checks are made for validity of the
        RAPCal stream times wrt hit time.

        If GPS times are required, you have to apply the year
        of the datataking. The GPS string provided by the rapcal
        packats only includes the day of year information
        """
        rcl = self.rcd[hit.domid]
        for ixrc in range(len(rcl)):
            if rcl[ixrc].domRx > hit.domclk: break
        if ixrc == 0:
            ixrc += 1
        if ixrc == len(rcl):
            ixrc -= 1
        rc1 = rcl[ixrc]
        rc0 = rcl[ixrc-1]
        rc1.doRAPCal(rc0)
        hit.utclk = rc1.dom2Dor(hit.domclk)
        # store the counter when the gps string
        # was read the last time.
        # needed to compute the offset of the hit time
        # with respect to the gps time string
        hit.gpsClock = rc1.dorGPSClock

        # I'm not sure about the following:
        #
        # if the DOR GPS clock count is off by more than 10 seconds
        # the entry is wrong, use one of the previous once
        # try the last four
        for previous in range(2, 6):
            previousRcl = rcl[ixrc-previous]
            if abs(hit.utclk - hit.gpsClock) / 10e10 > 10:
                hit.gpsClock = previousRcl.dorGPSClock
            else:
                break
                
        hit.gpsTime = rc1.getGPSTime(year)
# end translateDOMtoDOR

    def getUTC(self, hit):
        """
        Returns a tuple with the UTC time (Y-M-d HH:MM:SS) of the 
        GPS time string after the hit was recorded and the offset
        of the hit time in 0.1 nsec with respect to the GPS time

        The fields of the tuple are accessible via the keys 'utc' and
        'offset'
        """
        utc = dict()
        utc['utc'] = time.strftime('%Y-%m-%d %H:%M:%S',
                                   time.gmtime(hit.gpsTime))
        if hit.gpsClock is not 0:
            utc['offset'] = hit.utclk - hit.gpsClock
        else:
            utc['offset'] = 'invalid'
        
        return utc
        
        
###########################################################
#
# Live RAPCal!
#
###########################################################

DRIVER_ROOT = '/proc/driver/domhub/'

def syncgps(card):
    """
    Returns the 22-byte GPS string from the syncgps procfile
    """
    fgps = os.open(DRIVER_ROOT + 'card%d/syncgps' % card, os.O_RDONLY)
    gpsstr = os.read(fgps, 22)
    os.close(fgps)
    return gpsstr

def tcal(cpd):
    """
    Do the time synchronization stuff
    ARGUMENTS
        - cpd = DOM location (card, pair, ['A' | 'B'])
    """
    
    ft = os.open(DRIVER_ROOT + 'card%d/pair%d/dom%c/tcalib' % cpd, os.O_RDWR)
    os.write(ft, 'single\n')
    time.sleep(0.05)
    buf = os.read(ft, 292)
    os.close(ft)
    if len(buf) != 292:
        print >>sys.stderr, "ERROR: short TCAL read (%d bytes)" % len(buf)
        return
    return RAPCal(buf[4:])
    
