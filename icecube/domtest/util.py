#
# The DOM utility package
#
# $Id: util.py,v 1.6 2005/12/25 22:46:20 kael Exp $
#

import sys, os, time, math, struct
from icecube.domtest.hits import domhit
from ConfigParser import ConfigParser
from PyBook import Histogram
from numpy import array, arange, zeros, sum, sqrt
from numpy.numarray import matrixmultiply
from numpy.numarray.linear_algebra import linear_least_squares, eigenvalues
from cStringIO import StringIO

debug = 1

def nextHit(f):
    "Read a TestDAQ hit stream."
    hdr = f.read(32)
    if len(hdr) != 32: return None
    recl, fmt, mbid, utc = struct.unpack('>iiq8xq', hdr)
    buf = f.read(recl-32)
    hit = domhit('%12.12x' % mbid)
    hit.decode(buf)
    hit.utclk = utc
    return hit
    
def getHits(f, count=1000, hits=dict()):
    """Read <count> hits from the file stream, return a
    dictionary map keyed by mainboard ID, with lists of
    hits as elements."""
    for i in range(count):
        h = nextHit(f)
        if h is None: return hits
        if h.domid not in hits:
            hits[h.domid] = list()
        hits[h.domid].append(h)
    return hits

def readDHHits(f):
    """
    This little number will read the DOMHub-Prod formatted output data
    """
    
    d = dict()
    while True:
        hdr = f.read(16)
        if len(hdr) != 16: return d
        (length, type, mbid) = struct.unpack('>iiq', hdr)
        buf = f.read(length-16)
        if type == 2:
            mbid = "%12.12x" % mbid
            print length, type, mbid
            if mbid not in d:
                d[mbid] = []

            # There could be multiple engineering records cat'd together
            while len(buf) > 0:
                blen, = struct.unpack('>h', buf[0:2])
                h = domhit(mbid)
                h.decode(buf[0:blen])
                buf = buf[blen:]
                d[mbid].append(h)
                
    return d

def configDefault(q, hvon=0):
    config = ConfigParser()
    config.read(os.path.expanduser('~/.dom-default-config'))
    dacNames = config.options('Rev3-DAC-Channels')
    for name in config.options('Rev3-DAC-Channels'):
        ch = config.getint('Rev3-DAC-Channels', name)
        val = config.getint('Rev3-DAC-Values', name)
        q.setDAC(ch, val)
    if hvon:
        # Enable HV
        q.enableHV()
        try:
            hv = config.getint('Nominal HV', q.getId())
        except:
            print >> sys.stderr, 'WARNING in util.configDefault() - cannot ' \
                  + 'find default HV for DOM ID',q.getId()
            hv = 2800
        q.setHV(hv)
    else:
        # Turn off HV
        q.disableHV()

def ratescan(q, tmin=500, tmax=600, step=5, integration=10, deadtime=0):

    q.setSPEDeadtime(deadtime)

    h = [ ]
    for dac in range(tmin, tmax, step):
        q.setDAC(9, dac)
        r = 0
        for i in range(integration):
            time.sleep(0.12)
            r += q.spef()
        h.append(r)
    return h

def ped_noise(q, nseq=101, ncyc=10):
    # Set the MUXer to LED
    q.mux('ledmux')

    # Init the ped pattern
    pedpat = []
    for i in range(8):
        pedpat.append(zeros(128, 'd'))

    # Acquire ped pattern
    hqx = q.acqX(101, 0x07, 'cpu')
    hqx.pop(0)
    hqy = q.acqX(101, 0x70, 'cpu')
    hqy.pop(0)
    hqx += hqy
    
    for hit in hqx:
        for ich in range(8):
            if hit.atwd[ich]:
                pedpat[ich] += array(hit.atwd[ich], 'd')

    for p in pedpat: p /= 100.0

    mvn = [0] * 8
    mvx = [0] * 8
    var = [0] * 8

    for icyc in range(ncyc):
        hqx = q.acqX(nseq, 0x07, 'cpu')
        hqx.pop(0)
        hqy = q.acqX(nseq, 0x70, 'cpu')
        hqy.pop(0)
        hqx += hqy
        for hit in hqx:
            for ich in range(8):
                if hit.atwd[ich]:
                    w = array(hit.atwd[ich], 'd') - pedpat[ich]
                    mvx[ich] = max(max(w), mvx[ich])
                    mvn[ich] = min(min(w), mvn[ich])
                    var[ich] += sum(w**2)

    chs = [ ]
    for ich in range(8):
        v = math.sqrt(var[ich] / (128*ncyc*(nseq-1)))
        chs.append((mvn[ich], mvx[ich], v))
    return chs

class PMTGainCalibrator:
    """Calibrate the PMT gain using darkcount photons."""
    def __init__(self, q, cal) :
        
        self.q = q
        self.cal = cal
        self.freq = cal.calcATWDFreq(q.getDAC(0), 0)
        self.hv   = (2600, 3000, 3200, 3600, 3800)
        
    def scan(self, nseq=1001, ncyc=20):

        self.q.setDAC(7, 1925)
        self.q.setDAC(9, 515)
        self.q.enableHV()

        self.logHV       = [ ]
        self.logGain     = [ ]
        self.charge_dist = [ ]
        self.dataPoint   = [ ]
        for hv in self.hv:

            print >> sys.stderr, "Gathering SPE distribution for HV = ", hv
            self.q.setHV(hv)
            gmax = math.ceil(pow(10.0, 6.37*math.log10(hv)-21.0))
            print >> sys.stderr, "HV: ", hv, "gmax: ", gmax
            hist = Histogram(
                'Charge Histogram for DOM %s - %d VDC' % (self.q.getId(), hv),
                200, 0.0, gmax)
            
            time.sleep(5.0)
            
            # Test out saturation
            mode = 1
            ch   = 0
            hqx = self.q.acqX(11, 1, 'spe')
            hqx.pop(0)
            for h in hqx:
                if max(h.atwd[0]) > 800:
                    mode = 2
                    ch   = 1
                    break
            for i in range(ncyc):
                try:
                    hqx = self.q.acqX(nseq, mode, 'spe')
                    hqx.pop(0)
                    for h in hqx:
                        w = self.cal.recoATWD(
                            array(h.atwd[ch], 'd'),
                            ch, 1925.0 / 4096.0 * 5)
                        wmx = max(w)
                        for k in range(2, len(w)):
                            if w[k] == wmx:
                                pc = 0.02*sum(w[k-4:k+8])/self.freq*1E+06
                                hist.fill(pc)
                                break
                except IBEX, ibex:
                    print "Caught IBEX error:", ibex, "for DOM",self.q.getId()

            spe = spefit(hist.x(), hist.h)
            self.dataPoint.append((hv, hist, spe))
            g = spe.gain()
            if g:
                self.logHV.append((1, math.log10(hv)))
                self.logGain.append(math.log10(g))

            self.charge_dist.append((hist, spe))
            
        self.c = linear_least_squares(
            array(self.logHV,'d'),
            array(self.logGain,'d')
            )

def tres_fill(hits, cal, offset, threshold, bias, freq, hres, qres=None):
    lastt = 0
    for h in hits:
        w = cal.recoATWD(h.atwd[0], 0, bias)
        e = softdisc(w, threshold)
        # print max(w), len(e), h.clock0
        if len(e) == 2:
            t = h.clock0 / 40E+06 + 1.0E-06 * e[0].x / freq
            if lastt != 0:
                dt = t - lastt
                dt1 = (dt-offset)*1.e+9
                if abs(dt1) < 100.0 or debug > 4:
                    iw0 = max(0, int(e[0].x)-2)
                    iw1 = min(len(w)-1, int(e[1].x)+2)
                    qsum = 1E+06*sum(w[iw0:iw1])/(50*freq)
                    # print "%s: %.1f %.4f" % (id, dt1, qsum)
                    hres.fill(dt1)
                    if qres:
                        qres.fill(qsum)
            lastt = t

def time_resolution(q, cal, pulse_period, threshold=0.0025, nseq=501, ncyc=10):
    
    freq = cal.calcATWDFreq(q.getDAC(0), 0)
    
    s = 0
    v = 0
    n = 0
    bias = q.getDAC(7) / 4096.0 * 5.0
    id   = q.getId()

    # Locate true center
    that = Histogram("Locator - Rough guide", 100, -500.0, 500.0)
    hqx = q.acqX(1001, 1, 'spe')
    hqx.pop(0)
    tres_fill(hqx, cal, pulse_period, threshold, bias, freq, that)

    tmax, bin = that.getMaximum()
    print "TRES Correction:",tmax, bin
    
    hres = Histogram("Time Resolution - DOM %s - Pulse Period %.3g" \
                     % (id, pulse_period), 100, bin-10, bin+10)
    qres = Histogram("Fast Pulse Charge Distribution DOM %s" % (id),
                     100, 0.0, 10.0)
    
    for nc in range(ncyc):
        hqx = q.acqX(nseq, 1, 'spe')
        hqx.pop(0)
        tres_fill(hqx, cal, pulse_period, threshold,
                  bias, freq, hres, qres)

    return hres, qres

class edge:
    def __init__(self, slope, x):
        self.slope = slope
        self.x = x
        
def softdisc(a, thr):
    """Software discriminator."""
    lev = a > thr
    ddi = lev[1:] - lev[:-1]
    edges = [ ]
    for i in range(len(ddi)):
        if ddi[i]:
            fine = (thr - a[i]) / (a[i+1] - a[i]) + i
            edges.append(edge(ddi[i], fine))
    return edges

def roots(c):
    """Find the roots of a polynomial using the eigenvalue method
    (see Numerical Recipes).
    Arguments:
       - c : the polynomial coefficients, the polynomial is
             c[0] * x^n + ... + c[n-1] * x + c[n]
    Returns:
       list of (complex) roots

    K. Hanson 2004-05-15"""

    n = len(c) - 1
    A = zeros((n, n), 'd')
    for i in range(n):
        A[0][i] = -c[i+1] / c[0]
    for i in range(n-1):
        A[i+1][i] = 1.0
    return eigenvalues(A)

def polyval(coeff, x):
    p = 1
    a = 0.0
    for c in coeff:
        a += c*p
        p *= x
    return a

def occupancy(q, p, rate, aperture=10, pulse='fast'):
    """Calculate the occupancy of DOM to pulser pulses.

    occ, err = occupancy(q, p, rate, aperture, pulse)
    
    PARAMETERS
        - q        : ibx object
        - p        : pulser object
        - rate     : pulser rate (Hz)
        - aperture : aperture - scaler counting time in units of 0.1 ms;
                     this parameter must be an integer (DEFAULT=10)
        - pulse    : pulse type, either
                     'marker' - use marker pulse
                     'fast' - use fast pulse (DEFAULT)

    RETURNS
        - occ : occupancy fraction
        - err : (statistical) error in occupancy calculation
        """

    p.setPulseFrequency(rate)
    time.sleep(0.25)
    
    bkg, sig = 0, 0
    for i in range(aperture):
        p.allOff()
        time.sleep(0.1)
        bkg += q.spef()
        if pulse == 'marker':
            p.markerOn()
        elif pulse == 'fast':
            p.fastOn()
        time.sleep(0.2)
        sig += q.spef()

    x    = sig - bkg
    xerr = math.sqrt(bkg + sig)
    dt   = 10.0 / aperture
    return ( x / float(rate), xerr / rate )

class spefit:
    """Fit a PMT P/H and/or charge distribution.  Trick is
    to approximate the distribution to a 5th-order polynomial
    and then the roots of the 4th-order derivative polynomial
    should yield robust estimates of the peak and the valley.

    Returns:
        6-tuple of coefficients of the 5th order fitting polynomial
        and the residual sum of squares.

    TODO:
        Document the data members:
           Y - filtered RHS vector
           A - matrix of overdetermined system of equations
           b - solution vector
           rz - real zeros of the derivative polynomial
           
    2004-05-14 K. Hanson."""

    def __init__(self, x, y, thr=10, order=7):

        self.thr = thr
        self.order = order

        self.peak = None
        self.valley = None
        self.x0 = self.x1 = 0
        
        # First, restrict the range to x-range where the y's are non-zero
        for x0 in range(len(y)):
            if y[x0] > thr:
                break
        for x1 in range(len(y)-1,-1,-1):
            if y[x1] > thr:
                break

        # Additional data condition - remove threshold effect at low end
        # of histogram that makes the steepening dynode-noise shoulder
        # look kind of like a peak to dumb software
        while x[x0+1] > 1.5*x[x0]:
            x0 += 1

        # Require ample points for the fit
        if x1 - x0 < 10:
            return None

        self.x0 = x0
        self.x1 = x1

        # Create coefficient matrix
        matrix = [ ]
        for i in range(x0, x1):
            u = x[i]
            v = [ 1 ]
            for k in range(self.order):
                v.append(u)
                u = u * x[i]
            matrix.append(v)
        self.A = array(matrix, 'd')
        self.X = array(x[x0:x1], 'd')
        self.Y = array(y[x0:x1], 'd')

        # Do lsq fit
        self.Q = linear_least_squares(self.A, self.Y)
        self.b = self.Q[0]

        r = matrixmultiply(self.A, self.b)
        self.fit = r
        self.rss = 0.0
        n = 0
        for i in range(len(self.Y)):
            if self.Y[i] != 0.0:
                self.rss += (r[i] - self.Y[i])**2 / self.Y[i]
                n += 1
        if n > order:
            self.rss = math.sqrt(self.rss/(n - order))
        else:
            self.rss = 0.0

        if debug > 5:
            print >> sys.stderr, "Solution vector: ", self.b, " RSS: ", self.rss
            
        # derivative polynomial - flip around so n-th order polynomial
        # coefficient is in 1st slot
        d = self.b[1:] * (arange(len(self.b)-1)+1)
        
        if debug > 5:
            print >> sys.stderr, "Derivative polynomial coeff: ", d
            
        z = roots(d[-1::-1])

        if z.type() == 'Float64':
            rz = z
        elif z.type() == 'Complex64':
            # ID the real roots
            rz = [ ez.real for ez in z if ez.imag == 0 ]
        else:
            raise TypeError, z.type

        if len(rz) == 0:
            return

        # Then apply various heuristic criteria
        # - first, ensure that the roots are within the
        # specified range of the fit
        rz = sorted(filter(lambda u: u > x[x0] and u < x[x1], rz))
        
        # Ask for concave up followed by concave down that is max
        dd = d[1:] * arange(1, len(d))
        self.xz = [ (z,polyval(self.b, z),polyval(dd, z) > 0) for z in rz ]

        if len(self.xz) == 2:
            # Two real zeros found - easy to ID min and max
            if self.xz[0][1] > self.xz[1][1]:
                self.peak = self.xz[0]
                self.valley = self.xz[1]
            else:
                self.peak = self.xz[1]
                self.valley = self.xz[0]
        elif len(self.xz) == 1 and self.xz[0][2] == 0:
            self.peak = self.xz[0]
        elif len(self.xz)>2 and self.xz[-1][2] == 0 and self.xz[-2][2] == 1:
            self.peak = self.xz[-1]
            self.valley = self.xz[-2]
            
    def peakToValley(self):
        """Returns peak-to-valley ratio."""
        if self.peak and self.valley:
            return self.peak[1] / self.valley[1]
        return None

    def gain(self):
        """Returns gain in units of 1.0E+07 or None if
        a peak was not identified."""
        if self.peak:
            return self.peak[0] / 1.6
        
