"""
Supernova entities.
"""

from struct import unpack

class SNData:
    
    def __init__(self, data):
        """
        Create from payload
        """
        pbyt, pfmt, self.utc, mbid, bytes, fmtid, t5, t4, t3, t2, t1, t0 = unpack(
            '>iiqqhh6B', data[0:34])
        self.mbid = '%12.12x' % mbid
        self.scalers = unpack('%dB' % (bytes - 10), data[34:])
        self.domclk  = ((((t5 << 8L | t4) << 8L | t3) << 8L | t2) << 8L | t1) << 8L | t0
        self.utcend  = self.utc + len(self.scalers) * 16384000L
        
def readsn(f):
    d = dict()
    while 1:
        hdr = f.read(24)
        if len(hdr) != 24: break
        bytes, fmtid, utc, mbid = unpack('>iiqq', hdr)
        buf = f.read(bytes-24)
        mbid = "%12.12x" % mbid
        if mbid not in d: d[mbid] = list()
        d[mbid].append(SNData(hdr+buf))
    return d
    
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
   
