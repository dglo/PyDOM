
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
    

def multiplet(v):
    """ Count non-zero multiplets in a vector """
    m = [ ]
    i = 0
    j = 0
    while j < len(v):
        if v[i]:
            while j < len(v) and v[j]: 
                j += 1
            k = j-i
            if len(m) < k + 1: 
                m += ([0] * (k+1-len(m)))
            m[k] += 1
            i = j
        else:
            i += 1
            j = i + 1
    return m

def scola_spacca(hits, nick):
    spacca = dict()
    for h in hits:
        chid = nick.lookup(h.mbid)
        if chid is None: return None
        chid = chid[3]
        astrid = int(chid[0:2])
        stomid = int(chid[3:5])
        tijd = h.utc
        if astrid not in spacca: spacca[astrid] = [ ]
        spacca[astrid].append((stomid, tijd))
    return spacca

def string_trigger(hits, mult, clen, twin=15000, topVeto=0, bottomVeto=60):
    """
    Do string triggering on list of hits which must be time-ordered list
    of triplets with hits[i] = (module, utc)
    This function only operates with hits from a single string!
    """

    i = 0
    j = 1

    while j < len(hits):
        while j < len(hits) and hits[j][1] - hits[i][1] < twin: j += 1
        if j - i >= mult:
            clust = [ 0 ] * 60
            for h in hits[i:j]:
                m0 = h[0] - mult / 2
                for k in range(m0, m0 + mult): 
                    if k > topVeto and k < bottomVeto: 
                        clust[k] += 1
                        if clust[k] >= mult: return True
            i = j
            j = i + 1
        else:
            i += 1
    
    return False
