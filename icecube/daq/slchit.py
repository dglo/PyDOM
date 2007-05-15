from struct import unpack
from cStringIO import StringIO

class SLCHit:
    """
    The SLCHit class handles Soft Local Coincidence
    hits - that is, it is the base class for compressed
    hits all of which share the common header.
    """
    
    def __init__(self, buf, mbid=None, utc=None):
        self.buf  = buf[8:]
        self.mbid = mbid
        self.utc  = utc
        self.domclk = unpack('<q', buf[0:8])
        self.words  = unpack('<2i', self.buf[0:8])
        
    def __getattr__(self, name):
        if name == 'trigger':
            return (self.words[0] & 0x7ffe0000) >> 18
        elif name == 'lc':
            return (self.words[0] & 0x30000) >> 16
        elif name == 'fadc_avail':
            return (self.words[0] & 0x8000) != 0
        elif name == 'atwd_avail':
            return (self.words[0] & 0x4000) != 0
        elif name == 'atwd_channels':
            return (self.words[0] & 0x3000) >> 12
        elif name == 'atwd_chip':
            return (self.words[0] & 0x800) >> 11
        elif name == 'hit_size':
            return self.words[0] & 0x7ff
        elif name == 'chargestamp':
            pk_pos = (self.words[1] >> 27) & 0xf
            pk_pre = (self.words[1] >> 18) & 0x1ff
            pk_max = (self.words[1] >> 9)  & 0x1ff
            pk_pst = self.words[1] & 0x1ff
            if self.words[1] & 0x80000000 != 0:
                return (pk_pos, pk_pre << 1, pk_max << 1, pk_pst << 1)
            else:
                return (pk_pos, pk_pre, pk_max, pk_pst)
        else:
            raise AttributeError(name)
            
            
class DeltaCompressedHit(SLCHit):
    
    def __init__(self, buf, mbid=None, utc=None):
        SLCHit.__init__(self, buf, mbid, utc)
        self.decoded = False
        self.fADC = [ ]
        self.atwd = [ [], [], [], [] ]
        
    def decode_waveforms(self):
        if self.decoded: return
        codec = delta_codec(self.buf[8:])
        if self.fadc_avail: self.fADC = codec.decode(256)
        if self.atwd_avail:
            for i in range(self.atwd_channels+1):
                self.atwd[i] = codec.decode(128)
        self.decoded = True
        
class delta_codec:
    def __init__(self, buf):
        self.tape = StringIO(buf)
        self.valid_bits = 0
        self.register = 0
        
    def decode(self, length):
        self.bpw  = 3
        self.bth  = 2
        last = 0
        out  = [ ]
        for i in range(length):
            while True:
                w = self.get_bits()
                if w != (1 << (self.bpw -1)): break
                self.shift_up()
            if abs(w) < self.bth: self.shift_down()
            last += w
            out.append(last)
        return out
        
    def get_bits(self):
        while self.valid_bits < self.bpw:
            next_byte, = unpack('B', self.tape.read(1))
            self.register |= (next_byte << self.valid_bits)
            self.valid_bits += 8
        val = self.register & ((1 << self.bpw) - 1)
        if val > (1 << (self.bpw - 1)): val -= (1 << self.bpw)
        for i in range(self.bpw):
            self.register >>= 1
            self.valid_bits -= 1
            self.register &= ((1 << self.valid_bits) - 1)
        return val
        
    def shift_up(self):
        if self.bpw == 1:
            self.bpw = 2
            self.bth = 1
        elif self.bpw == 2:
            self.bpw = 3
            self.bth = 2
        elif self.bpw == 3:
            self.bpw = 6
            self.bth = 4
        elif self.bpw == 6:
            self.bpw = 11
            self.bth = 32
        else:
            raise ValueError
        
    def shift_down(self):
        if self.bpw == 2:
            self.bpw = 1
            self.bth = 0
        elif self.bpw == 3:
            self.bpw = 2
            self.bth = 1
        elif self.bpw == 6:
            self.bpw = 3
            self.bth = 2
        elif self.bpw == 11:
            self.bpw = 6
            self.bth = 4
        else:
            raise ValueError
