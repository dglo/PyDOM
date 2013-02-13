
from struct import unpack
from hits import domhit
from slchit import DeltaCompressedHit as DCH
from monitoring import MonitorRecordFactory

def indent(string, n):
    txt = ''
    for line in string.split('\n'):
        txt += ' '*n + line + '\n'
    return txt

def recurse_triggers(tr):
    trig = [ (tr.srcid, tr.trigger_type, tr.trigger_cfg_id) ]
    for st in tr.hits:
        if isinstance(st, TriggerRequestPayload):
            trig += recurse_triggers(st)
    return trig

class PayloadException(Exception):
    pass

class Payload:

    def __init__(self, length, type, utime):
        self.length, self.type, self.utime = length, type, utime

    def __str__(self):
        return "Payload#%d[@%d, %d bytes]" % (self.type, self.utime, self.length)

class EventPayload(Payload):

    def __init__(self, length, type, utime):
        Payload.__init__(self, length, type, utime)
        self.run_number = 0
        self.subrun_number = 0
        self.uid = 0
        self.interval = [0, 0]
        self.trigger_request = None
        self.readout_data = []
        self.trigger_records = None

    def __str__(self):
        txt = "[EventPayload]: Event #"
        if self.subrun_number == 0:
            txt += "%d-%d" % (self.run_number, self.uid)
        else:
            txt += "%d/%d-%d" % (self.run_number, self.subrun_number, self.uid)
        txt += " ival=(%d, %d)\n" % self.interval
        if self.trigger_request is not None:
            txt += indent(str(self.trigger_request),4)
        if self.trigger_records is not None:
            for tr in self.trigger_records:
                txt += indent(str(tr),4)
        return txt

    def getTriggers(self):
        triggers = [ ]
        tr = self.trigger_request
        triggers += recurse_triggers(tr)
        return triggers

    def getTrigHits(tr):
        hits = []
        for hit in tr.hits:
            if isinstance(hit, HitDataPayload):
                hits.append(hit)
            elif isinstance(hit, TriggerRequestPayload):
                hits += getTrigHits(hit)
        return hits

    def getHits(self):
        """
        Return the hits as a flattened list
        """
        hits = list()
        for rd in self.readout_data:
            for d in rd.data:
                if isinstance(d, EngHitDataPayload):
                    mbid = '%12.12x' % d.mbid
                    h = domhit(mbid, d.data)
                    h.utclk = d.utime
                    h.utc   = d.utime
                elif isinstance(d, DeltaCompressedHitPayload):
                    mbid = '%12.12x' % d.mbid
                    h = DCH(d.data, mbid, d.utime)
                hits.append(h)
        return hits

class TriggerRequestPayload(Payload):
    def __str__(self):
        txt = "[TriggerRequestPayload]: source=%s trigtype=%d\n" % \
            (source_str(self.srcid), self.trigger_type)
        for ex in self.readout_request.elements:
            txt += indent(str(ex),4)
        for h in self.hits:
            txt += indent(str(h),4)
        txt += '--'
        return txt

class ReadoutRequest:
    pass

class ReadoutRequestElement:
    def __str__(self):
        return "[ReadoutRequestElement]: source=%s type=%d ival=(%d, %d)" % \
            (source_str(self.srcid), self.readout_type,
            self.interval[0], self.interval[1])

class ReadoutDataPayload(Payload):
    pass

class HitDataPayload(Payload):
    def __str__(self):
        return "[HitDataPayload]: source=%s mbid=%12.12x utime=%d" % \
            (source_str(self.srcid), self.mbid, self.utime)

class DeltaCompressedHitPayload(Payload):
    pass

class EngHitDataPayload(Payload):
    pass

class MonitorRecordPayload(Payload):
    pass

class DeltaSenderHit(object):
    def __init__(self, mbid, utime, version, pedestal, domclk, word0, word2,
                 data):
        self.mbid = mbid
        self.utime = utime
        self.pedestal = pedestal
        self.domclk = domclk
        self.word0 = word0
        self.word2 = word2
        self.data = data

    def __str__(self):
        return "DeltaSenderHit@%d[dom %012x]" % (self.utime, self.mbid)

class HitRecord(object):
    def __init__(self, chanid, utime):
        self.chanid = chanid
        self.utime = utime

class EngHitRecord(HitRecord):
    def __init__(self, flags, chanid, utime, data):
        super(EngHitRecord, self).__init__(chanid, utime)
        self.flags = None
        self.data = data

class DeltaHitRecord(HitRecord):
    def __init__(self, flags, chanid, utime, data):
        super(DeltaHitRecord, self).__init__(chanid, utime)
        self.flags = flags
        self.data = data
    def __str__(self):
        return "DeltaHitRecord@%d[chanid %d]" % (self.utime, self.chanid)

class TriggerRecord(object):
    def __init__(self, ttype, cfgid, srcid, starttime, endtime, hits):
        self.trigger_type = ttype
        self.cfgid = cfgid
        self.srcid = srcid
        self.interval = (starttime, endtime)
        self.hits = hits

    def __str__(self):
        txt = "[TriggerRecord]: source=%s trigtype=%d\n" % \
            (source_str(self.srcid), self.trigger_type)
        for h in self.hits:
            txt += indent(str(h),4)
        txt += '--'
        return txt

def decode_payload(f):
    """
    Read a payload from the stream f
    """
    envelope = f.read(16)
    if len(envelope) == 0: return None
    length, type, utime = unpack(">iiq", envelope)
    if type == 1:
        payload = HitDataPayload(length, type, utime)
        buf = f.read(22)
        hdr = unpack(">3iqh", buf)
        payload.trigger_type    = hdr[0]
        payload.trigger_cfg_id  = hdr[1]
        payload.srcid           = hdr[2]
        payload.mbid            = hdr[3]
        payload.trigger_mode    = hdr[4]
    elif type == 3:
        mbid = utime
        hdr = unpack(">8xQHHHQII", f.read(38))

        if hdr[1] != 1:
            raise PayloadException(("Bad order-check %d for DeltaSenderHit" +
                                    " (should be 1)") % hdr[1])

        data = f.read(length - 54)
        payload = DeltaSenderHit(utime, hdr[0], hdr[2], hdr[3], hdr[4], hdr[5],
                                 hdr[6], data)
    elif type == 5:
        payload = MonitorRecordPayload(length, type, utime)
        payload.mbid, = unpack('>q', f.read(8))
        payload.rec   = MonitorRecordFactory(f.read(length-24),
            '%12.12x' % payload.mbid, payload.utime)
    elif type in (13, 19, 20):
        payload = EventPayload(length, type, utime)
        # 38 bytes of 'header' information
        buf = f.read(38)
        hdr = unpack(">hiiqqiii", buf)
        payload.record_type     = hdr[0]
        payload.uid             = hdr[1]
        payload.srcid           = hdr[2]
        payload.interval        = (hdr[3], hdr[4])
        payload.event_type      = 0
        payload.event_cfg_id    = 0
        payload.year            = 0
        payload.subrun_number   = 0
        if type == 13 or type == 19:
            payload.event_type      = hdr[5]
        elif type == 20:
            payload.year            = (hdr[5] >> 16) & 0xffff
        if type == 13:
            payload.event_cfg_id    = hdr[6]
            payload.run_number      = hdr[7]
        elif type == 19 or type == 20:
            payload.run_number      = hdr[6]
            payload.subrun_number   = hdr[7]
        composites              = decode_composite(f)
        payload.trigger_request = None
        payload.readout_data    = []
        if len(composites) > 0:
            payload.trigger_request = composites.pop(0)
        payload.readout_data = composites
    elif type == 21:
        payload = EventPayload(length, type, utime)
        # 38 bytes of 'header' information
        hdr = unpack(">IHIIII", f.read(22))
        payload.interval        = (utime, utime + hdr[0])
        payload.year            = hdr[1]
        payload.uid             = hdr[2]
        #payload.srcid           = hdr[2]
        payload.run_number      = hdr[3]
        payload.event_cfg_id    = 0
        payload.subrun_number   = hdr[4]

        num_hitrecs             = hdr[5]

        hits = []
        for i in xrange(num_hitrecs):
            hdr = unpack(">HBBHI", f.read(10))

            rlen = hdr[0]
            rtype = hdr[1]
            flags = hdr[2]
            chanID = hdr[3]
            time = utime + hdr[4]

            buf = f.read(rlen - 10)
            if rtype == 0:
                hits.append(EngHitRecord(flags, chanID, time, buf))
            elif rtype == 1:
                hits.append(DeltaHitRecord(flags, chanID, time, buf))

        num_trigrecs = unpack(">I", f.read(4))[0]

        trigrecs = []
        for i in xrange(num_trigrecs):
            hdr = unpack(">ii4I", f.read(24))

            ttype = hdr[0]
            cfgid = hdr[1]
            srcid = hdr[2]
            starttime = utime + hdr[3]
            endtime = utime + hdr[4]
            num_hits = hdr[5]

            fmt = ">%dI" % num_hits

            trighits = []
            for i in unpack(fmt, f.read(num_hits * 4)):
                trighits.append(hits[i])
            trigrecs.append(TriggerRecord(ttype, cfgid, srcid, starttime,
                                          endtime, trighits))

        payload.trigger_records = trigrecs

    elif type == 9:
        payload = TriggerRequestPayload(length, type, utime)
        buf = f.read(34)
        hdr = unpack(">hiiiiqq", buf)
        payload.record_type     = hdr[0]
        payload.uid             = hdr[1]
        payload.trigger_type    = hdr[2]
        payload.trigger_cfg_id  = hdr[3]
        payload.srcid           = hdr[4]
        payload.interval        = (hdr[5], hdr[6])
        # Now there is a readout request record ...
        payload.readout_request = ReadoutRequest()
        buf = f.read(14)
        hdr = unpack(">hiii", buf)
        payload.readout_request.request_type    = hdr[0]
        payload.readout_request.trigger_uid     = hdr[1]
        payload.readout_request.srcid           = hdr[2]
        payload.readout_request.elements        = [ ]
        for elt in range(hdr[3]):
            r2e = ReadoutRequestElement()
            buf = f.read(32)
            hdr = unpack(">2i3q", buf)
            r2e.readout_type    = hdr[0]
            r2e.srcid           = hdr[1]
            r2e.interval        = (hdr[2], hdr[3])
            r2e.mbid            = hdr[4]
            payload.readout_request.elements.append(r2e)
        payload.hits            = decode_composite(f)
    elif type == 10:
        payload = EngHitDataPayload(length, type, utime)
        # The next 8 bytes are trigger config id and source ID - skip for now
        f.read(8)
        # The next 32 bytes are the 'standard TestDAQ wrapped record'
        data_len, fmtid, mbid, utc = unpack(">iiq8xq", f.read(32))
        payload.mbid            = mbid
        payload.data_len        = data_len
        payload.utc             = utc
        payload.data            = f.read(length - 56)
    elif type == 11:
        payload = ReadoutDataPayload(length, type, utime)
        buf = f.read(30)
        hdr = unpack(">hihhiqq", buf)
        payload.record_type     = hdr[0]
        payload.uid             = hdr[1]
        payload.index           = hdr[2]
        payload.is_last         = (hdr[3] != 0)
        payload.srcid           = hdr[4]
        payload.interval        = (hdr[5], hdr[6])
        payload.data            = decode_composite(f)
    elif type == 18:
        payload = DeltaCompressedHitPayload(length, type, utime)
        buf = f.read(length-16)
        mbid, bochk, vers, pwd = unpack('>qhhh', buf[12:26])
        payload.mbid = mbid
        payload.vers = vers
        payload.pwd  = pwd
        payload.data = buf[26:]
    else:
        payload = Payload(length, type, utime)
        payload.data = f.read(length - 16)
    return payload

def decode_composite(f):
    envelope = f.read(8)
    length, type, n = unpack(">ihh", envelope)
    composites = [ ]
    for icl in range(n):
        composites.append(decode_payload(f))
    return composites

def tohitstack(events):
    """
    Return 'standard' hit stack hits[mbid] = <list-of-hits-to-mbid>
    """
    hits = dict()
    for e in events:
        for rd in e.readout_data:
            for d in rd.data:
                mbid = '%12.12x' % d.mbid
                if mbid not in hits: hits[mbid] = list()
                h = domhit(mbid, d.data)
                h.utclk = d.utime
                hits[mbid].append(h)
    return hits

def read_payloads(stream):
    while 1:
        p = decode_payload(stream)
        if p is None:
            return
        yield p

def make21trig(t, t0, hits):
	buf = ""
	hbuf = ""
	for x in t.hits:
		if isinstance(x, TriggerRequestPayload):
			buf += make21trig(x, t0)
		elif isinstance(x, HitDataPayload):
			n += 1
			idx = -1
			for i in range(len(hits)):
				hit = hits[i]
				if ininstance(hit, SLCHit) and x.mbid == hit.mbid and x.utime == hit.utc:
					idx = i
					break
			hbuf += pack(">i", idx)
	buf += pack(">6i", t.trigger_type, t.trigger_cfg_id, t.srcid,
				t.interval[0] - t0, t.interval[1] - t0, n) + hbuf
	return buf

def make21hits(hits, t0):
	return ""

def make21(evt):
	trig_buf = ""
	hits_buf = ""
	ntrig = 0
	t = evt.trigger_request
	buf = pack(">iq2h6i", 21, evt.utime, 1, evt.year, evt.uid,
			   evt.run_number, evt.subrun_number,
			   evt.interval[0] - evt.utime, evt.interval[1] - evt.utime, ntrig) + \
			   make21trig(t, evt.utime, hits) + \
			   make21hits(evt.utime, hits)
	buf = pack(">i", len(buf) + 4) + buf

_srcDict = { 'domHub' : 1000,
             'stringProc' : 2000,
             'iceTopDH' : 3000,
             'inIceTrig' : 4000,
             'iceTopTrig' : 5000,
             'glblTrig' : 6000,
             'evtBldr' : 7000,
             'tcalBldr' : 8000,
             'moniBldr' : 9000,
             'amandaTrig' : 10000,
             'snBldr' : 11000,
             'stringHub' : 12000,
             'simHub' : 13000
}

def source_str(srcid):
    (srcname, srcbase) = (None, None)

    for name in _srcDict:
        base = _srcDict[name]
        if srcid >= base and srcid < (base + 1000):
            srcname = name
            srcbase = base
            break

    if srcname is None:
        if srcid == -1:
            # hack for wildcard trigger requests
            srcname = 'any'
            srcbase = 0
            srcid = 0
        else:
            srcname = 'unknown'
            srcbase = 0

    num = srcid - srcbase
    if num == 0:
        return srcname
    return srcname + '#' + str(num)
