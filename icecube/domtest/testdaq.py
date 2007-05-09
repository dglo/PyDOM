import zlib
from zipfile import ZipFile

HITS    = 1
MONITOR = 2
TIMECAL = 3

class datafile:
    """Class datafile encapsulates the TestDAQ ZIP datafile"""
    def __init__(self, filename):
        self.filename = filename
        self.zip = ZipFile(filename, "r")

    def getstream(self, type):
        """Obtain a handle to a data stream - currently supported are
        the types
            - HITS to get the hit stream
            - MONITOR to get the monitor stream
            - TIMECAL to get the rapcal stream
        """
        if type == TIMECAL:
            entry = [ n for n in self.zip.namelist() if n[-4:] == "tcal" ][0]
        elif type == MONITOR:
            entry = [ n for n in self.zip.namelist() if n[-4:] == "moni" ][0]
        elif type == HITS:
            entry = [ n for n in self.zip.namelist() if n[-3:] == "hit" ][0]
        zinf  = self.zip.getinfo(entry)
        return decostream(file(self.filename, "r"),
                          zinf.file_offset,
                          zinf.file_offset + zinf.compress_size
                          )

class decostream:
    """Class decostream allows for decompression of ZIP entries
    without needing to read entire image into memory.  It supports
    reading arbitrary length fragments using the read() method."""
    def __init__(self, f, offset, limit, blocksize=4096):
        self.f = f
        self.offset = offset
        self.limit  = limit
        self.f.seek(offset, 0)
        self.deco = zlib.decompressobj(-15)
        self.blocksize = blocksize
        self.buf  = ""
        
    def read(self, bytes):
        while len(self.buf) < bytes:
            nr  = min(self.blocksize, self.limit - self.f.tell())
            if nr == 0: break
            tmp = self.f.read(nr)
            self.buf += self.deco.decompress(tmp)
        r = self.buf[0:bytes]
        self.buf = self.buf[bytes:]
        return r
    
