#!/usr/bin/env python

####
##
#
#  Testing event data structures and analysis
#
#  $Id: hits.py,v 1.10 2006/01/13 21:38:15 kael Exp $
#
##
####

from future import standard_library
standard_library.install_aliases()
from builtins import range
from builtins import object
import struct
from io import StringIO
from array import array

def calc_atwd_fmt(fmt):
    """Returns unpack info for ATWDs."""
    dtab = ( 0, ">32b", 0, ">32h", 
             0, ">64b", 0, ">64h",
             0, ">16b", 0, ">16h",
             0, ">128b", 0, ">128h" )
             
    return ( dtab[fmt[0] & 0x0f], 
        dtab[(fmt[0] & 0xf0) >> 4],
        dtab[fmt[1] & 0x0f],
        dtab[(fmt[1] & 0xf0) >> 4] );

class domhit(object):
    """
    DOM hit data structure - data members
        domhit.domid
        domhit.domclk
        domhit.atwd[i][j] - jth sample of atwd channel i (0..3)
        domhit.atwd_chip  - 0 if atwd-a, 1 if atwd-b
        domhit.fadc[i]    - ith FADC sample
    """
    
    def __init__(self, domid, buf=None):
        """Init the d/s - fill in fields /w/ blanks."""
        self.domid = domid
        self.mbid  = domid
        self.atwd = [ None, None, None, None ]
        if buf is not None:
            self.decode(buf)
            
    def decode(self, buf):
        """Decode the domhit data structure from engineering record."""
        io = StringIO(buf)
        decotup = struct.unpack(">2H6B6s", io.read(16))

        # Decode the time stamp - 6-bit integer a little tricky
        self.domclk = struct.unpack(">q", "\x00\x00" + decotup[8])[0]
        self.atwd_chip = decotup[2] & 1
        self.evt_trig_flag = decotup[6]
        # Next decode the FADC samples, if any
        fadcfmt = ">%dH" % decotup[3:4]
        fadclen = struct.calcsize(fadcfmt)
        self.fadc = array('H', list(struct.unpack(fadcfmt, io.read(fadclen))))
        # Next decode the ATWD samples, if any.
        atwdfmt = calc_atwd_fmt(decotup[4:6])
        for ich in range(4):
            if atwdfmt[ich] is not 0:
                atwdlen = struct.calcsize(atwdfmt[ich])
                self.atwd[ich] = array('H', 
                    list(struct.unpack(atwdfmt[ich], io.read(atwdlen)))
                )
