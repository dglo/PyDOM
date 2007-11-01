
"""
A module to handle IceCube supernova data
"""

from struct import unpack, pack

class SNData:
    
    def __init__(self, data, mbid, utc):
        """
        Create from payload
        """
        bytes, fmtid, t5, t4, t3, t2, t1, t0 = unpack('>hh6B', data[0:10])
        self.mbid = '%12.12x' % mbid
        self.utc  = utc
        self.scalers = unpack('%dB' % (bytes - 10), data[10:])
        self.domclk  = ((((t5 << 8L | t4) << 8L | t3) \
            << 8L | t2) << 8L | t1) << 8L | t0
        self.utcend  = self.utc + len(self.scalers) * 16384000L
        
class SNPayloadReader:
    def __init__(self, f):
        self.f = f
        
    def __iter__(self):
        return self
        
    def next(self):
        while 1:
            hdr = self.f.read(16)
            if len(hdr) == 0: raise StopIteration
            bytes, fmtid, utc = unpack('>iiq', hdr)
            buf = self.f.read(bytes - 16)
            if fmtid == 16:
                mbid, = unpack('>q', buf[0:8])
                return SNData(buf[8:], mbid, utc)
                
def procsn(f, holdoff=10000):
    
    mtim = dict()
    hold = 0
    
    a = [ 0 ] * 1000
    ta = None
    da = 5000000000L
    db = 16384000L
    
    while 1:
        hdr = f.read(24)
        if len(hdr) != 24: break
        bytes, fmtid, utc, mbid = unpack('>iiqq', hdr)
        buf = f.read(bytes-24)
        mbid = "%12.12x" % mbid
        s = SNData(hdr + buf)
        mtim[mbid] = s.utcend
        if ta is None: ta = s.utc / 10000000000L * 10000000000L
        rebin(a, ta, da, s.scalers, s.utc, db)
        hold += 1
    
    return a
    
def rebin(a, ta, da, b, tb, db):
    """
    Rebin s/n scalers into a global array
        - a         global array
        - ta        time of left edge of a[0]
        - da        bin width of array a elements
        - b         s/n scaler array from a DOM
        - tb        time of left edge of b[0]
        - db        bin width for array b elements
    """
    
    ia = (tb - ta) / da
    
    # Compute storage requirements for a
    na = (tb + len(b) * db - ta) / da + 1
    if na > len(a):
        a += ([0] * (na - len(a)))
        
    # Initialize indices to point to correct elements
    s0 = tb
    s1 = s0 + db
    t0 = ta + ia*da
    t1 = t0 + da
    ib = 0
    
    while ib < len(b):
        u0 = max(s0, t0)
        u1 = min(s1, t1)
        a[ia] += float(u1 - u0) / float(s1 - s0) * b[ib]
        if u1 == t1:
            ia += 1
            t0 = t1
            t1 += da
        if u1 == s1:
            ib += 1
            s0 = s1
            s1 += db
            
def gaps(snvec):
    g = [ ]
    for i in range(1, len(snvec)):
        x = snvec[i-1]
        y = snvec[i]
        if (y.domclk - x.domclk) >> 16 != len(x.scalers): g.append(i-1)
    return g
   
class S2Codec:
    """
    A simple encoder/decoder which translates SN vectors into
    a bit-packed representation of symbols where
    0        : 0
    10       : 1
    110      : 2
    1110     : 3
    11110100 : 4
    11110101 : 5
    &c.
    11110000 : STOP
    11110001 - 11110011 : UNDEF
    """
    def encode(self, scalers):
        """
        Transform scalers into packed bits.
        """
        self.bitvector = ""
        self.register = 0
        self.bpos = 0
        for s in scalers:
            if s == 0:
                self.__push(0)
            elif s == 1:
                self.__push(1)
                self.__push(0)
            elif s == 2:
                self.__push(1)
                self.__push(1)
                self.__push(0)
            elif s == 3:
                self.__pushn(14)
            elif s < 16:
                self.__pushn(15)
                self.__pushn(s)
            else:
                raise ValueError, s
                
        # Push the STOP
        self.__pushn(15)
        self.__pushn(0)
        
        # Flush out anything remaining in the register
        if self.bpos > 0:
            self.bitvector += pack('B', self.register)
            self.bpos = 0
        
    def decode(self):
        scalers = [ ]
        state = 0
        self.bpos = 8
        while 1:
            b = self.__pop()
            if state < 4:
                if b == 0:
                    scalers.append(state)
                    state = 0
                else:
                    state += 1
            else:
                n = self.__popn()
                # Check STOP signal
                if n == 0: return scalers
                scalers.append(n)
                state = 0
                
    def __push(self, bit):
        """
        Internal method to append bit to bitvector.
        """
        if bit: self.register |= (1 << self.bpos)
        self.bpos += 1
        if self.bpos == 8:
            self.bitvector += pack('B', self.register)
            self.bpos = 0
            self.register = 0
            
    def __pop(self):
        if self.bpos == 8:
            self.register = unpack('B', self.bitvector[0])[0]
            self.bitvector = self.bitvector[1:]
            self.bpos = 0
        bit = self.register & 1
        self.register >>= 1
        self.bpos += 1
        return bit
        
    def __pushn(self, nybble):
        self.register |= (nybble << self.bpos)
        self.bpos += 4
        if self.bpos > 7:
            self.bitvector += pack('B', self.register & 0xff)
            self.register >>= 8
            self.bpos -= 8
        
    def __popn(self):
        if self.bpos > 4:
            self.register |= (unpack('B', self.bitvector[0])[0] << (8-self.bpos))
            self.bpos -= 8
        nybble = self.register & 0x0f
        self.register >>= 4
        self.bpos += 4
        return nybble

class ScalerComposition:
    """
    The ScalerComposition class allows one to 'merge' arrays of
    unsynchronized scalers to produce a global scaler.  The scalers
    are generic - they have a start time, an exposure time, and the
    number of counts in that exposure time.  The class logic automatically
    rebins the scalers to share the counts in 1 or more bins of the
    global scaler.  It also tracks how many subelements went into a
    bin of the global array.
    """
    def __init__(self, start_time, bin_width):
        self.w = bin_width
        self.st = start_time
        self.ar = [ 0 ] * 1000
        self.ct = [ 0 ] * 1000
        
    def merge(self, t, dt, counts):
        ix = int((t - self.st) / self.w)
        iy = int((t + dt - self.st) / self.w)
        if len(self.ar) < iy + 1:
            dx = 2*(iy + 1 - len(self.ar))
            self.ar += [ 0 ] * dx
            self.ct += [ 0 ] * dx
        for i in range(ix, iy + 1):
            tt0 = max(t, self.st + i * self.w)
            tt1 = min(t + dt, self.st + (i+1) * self.w)
            frac = (tt1 - tt0) / dt
            self.ar[i] += frac * counts
            self.ct[i] += frac
            
    def globalArray(self):
        """
        Access the global scaler array.  Returns an array 
            [ ( s0, c0 ), ( s1, c1 ), ... ]
        of rebinned counts and the occupancy of the bins.
        """
        return zip(self.ar, self.ct)
