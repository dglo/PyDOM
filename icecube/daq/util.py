
from icecube.daq.hits import domhit
from icecube.daq.slchit import DeltaCompressedHit
from struct import unpack

def nextHit(f):
    "Read a TestDAQ hit stream."
    hdr = f.read(32)
    if len(hdr) != 32: return None
    recl, fmt, mbid, utc = unpack('>iiq8xq', hdr)
    buf = f.read(recl-32)
    hit = None
    
    if fmt == 2:
    	hit = domhit('%12.12x' % mbid)
        hit.decode(buf)
        hit.utclk = utc
    elif fmt == 3:
        hit = DeltaCompressedHit(buf[6:], '%12.12x' % mbid, utc, True)
        
    return hit
    
def getHits(f, count=1000, hits=dict()):
    """Read <count> hits from the file stream, return a
    dictionary map keyed by mainboard ID, with lists of
    hits as elements."""
    for i in range(count):
        h = nextHit(f)
        if h is None: return hits
        if h.mbid not in hits:
            hits[h.mbid] = list()
        hits[h.mbid].append(h)
    return hits
