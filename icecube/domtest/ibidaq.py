#!/usr/bin/env python
"""
IBI-DAQ is a Python class that talks to IceBoot
and packages returned data in a convenient way.
$Id: ibidaq.py,v 1.40 2006/01/24 20:34:08 kael Exp $
"""
from __future__ import print_function
 
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object
from future.utils import raise_
import socket
import string
import io                 # Needed to unpack the acq dump strings
import struct                   # Ibid.
import re
import time
import os
import zlib                     # New zlib decompress of acq dumps (ver >= 2.2)
from select import select

version     = "3.4"

CPLD_BASE   = 0x50000000
FPGA_BASE   = 0x90080000

# FPGA triggering register & bitmasks ('SIGNAL' in LBNL docs)  
FPGA_TRIGGER_MASK_REGISTER  = FPGA_BASE + 0x1000
FPGA_TRIGGER_ATWD0_CPU  = 0x0001
FPGA_TRIGGER_ATWD0_SPE  = 0x0002
FPGA_TRIGGER_ATWD1_CPU  = 0x0100
FPGA_TRIGGER_ATWD1_SPE  = 0x0200
FPGA_TRIGGER_FADC_CPU   = 0x00010000
FPGA_TRIGGER_FADC_SPE   = 0x00020000
FPGA_TRIGGER_FE_PULSER  = 0x01000000
FPGA_TRIGGER_LED_PULSER = 0x04000000
TRIGMODE_ATWD_CPU       = FPGA_TRIGGER_ATWD0_CPU + FPGA_TRIGGER_ATWD1_CPU
TRIGMODE_ATWD_SPE       = FPGA_TRIGGER_ATWD0_SPE + FPGA_TRIGGER_ATWD1_SPE
TRIGMODE_CPU            = TRIGMODE_ATWD_CPU + FPGA_TRIGGER_FADC_CPU
TRIGMODE_ATWD_CPU_FE    = FPGA_TRIGGER_FE_PULSER + TRIGMODE_ATWD_CPU

# FPGA acquisition complete bitmask register and bits
FPGA_ACQ_COMPLETE_REGISTER  = FPGA_BASE + 0x1004
FPGA_ACQ_ATWD0_DONE         = 0x0001
FPGA_ACQ_ATWD1_DONE         = 0x0100
FPGA_ACQ_FADC_DONE          = 0x00010000

# 16-bit read-only rate scalers
FPGA_SCALER_SPE             = FPGA_BASE + 0x1010
FPGA_SCALER_MPE             = FPGA_BASE + 0x1014
FPGA_SCALER_SPE_FPGA        = FPGA_BASE + 0x1020
FPGA_SCALER_MPE_FPGA        = FPGA_BASE + 0x1024

# DOM Local Clock
FPGA_LCLK_LOW   = FPGA_BASE + 0x1040
FPGA_LCLK_HI    = FPGA_BASE + 0x1044

# FADC and ATWDs
FPGA_FADC       = FPGA_BASE + 0x3000
FPGA_ATWD0      = FPGA_BASE + 0x4000
FPGA_ATWD1      = FPGA_BASE + 0x5000

# DOM Clock register
FPGA_CLOCK_LOW  = FPGA_BASE + 0x1040
FPGA_CLOCK_HI   = FPGA_BASE + 0x1044

# Scaler deadtime
FPGA_DEADTIME   = FPGA_BASE + 0x1060

# Socket timeout, in seconds - this prevents hangs
# when the DOM or network dies in medias res
_TIMEOUT    = 60.0

# For DOR driver - must currently be 400
_CHUNKSIZE     = 1000

DEBUG_LEVEL = 1

class IBEX(Exception):
    """A generic module exception class."""
    def __init__(self, hermes):
        self.hermes = hermes
    def __str__(self):
        print(self.hermes)
        
class hit(object):
    """Waveform hit class.
    
    This class contains data members that hold information
    about a 'hit' or waveform capture in the ATWD and/or FADC.
    There are also slots for the DOM clock information.
      - hit.atwa[i][j] : holds j-th sample of ATWD-A channel i
      - hit.atwb[i][j] : ibid. but for ATWD-B
      - hit.fadc[j]    : only one FADC
      - hit.clock0     : ATWD hit time - latched DOM clock
    """
    def __init__(self, zbuf, format, tmod):
        """Unpack from acqX memory dump"""
        self.format = format
        self.trigmode = tmod
        self.atwa = [ None ] * 4
        self.atwb = [ None ] * 4
        # New code should use atwd field - atwa, atwb are deprecated
        self.atwd = [ None ] * 8 
        self.fadc = [ ]
        if format & 1:
            self.atwa[0] = self.atwd[0] = struct.unpack('128h', zbuf.read(256))
        if format & 2:
            self.atwa[1] = self.atwd[1] = struct.unpack('128h', zbuf.read(256))
        if format & 4:
            self.atwa[2] = self.atwd[2] = struct.unpack('128h', zbuf.read(256))
        if format & 8:
            self.atwa[3] = self.atwd[3] = struct.unpack('128h', zbuf.read(256))
        if format & 16:
            self.atwb[0] = self.atwd[4] = struct.unpack('128h', zbuf.read(256))
        if format & 32:
            self.atwb[1] = self.atwd[5] = struct.unpack('128h', zbuf.read(256))
        if format & 64:
            self.atwb[2] = self.atwd[6] = struct.unpack('128h', zbuf.read(256))
        if format & 128:
            self.atwb[3] = self.atwd[7] = struct.unpack('128h', zbuf.read(256))
        if format & 256:
            self.fadc = struct.unpack('256h', zbuf.read(512))
        self.clock0, self.clock1 = struct.unpack('2Q', zbuf.read(16))
        
    def toeng(self):
        """Write self out as engineering event"""
        afmt = self.format & 0x0f
        bfmt = (self.format & 0xf0) >> 4
        a = (afmt != 0)
        b = (bfmt != 0)
        # Consolidate formats 
        if (not a) and b:
            fmt = bfmt
        elif (not b) and a:
            fmt = afmt
        # Check the unsupported case that A and B readout but different format
        # If this is the case then revert to the least common denominator
        elif a and b:
            fmt = afmt & bfmt
            afmt = fmt
            bfmt = fmt
        else:
            fmt  = 0
        abfmt = ((not a) and b) + ((a and b)<<1)
        nfadc = len(self.fadc) >> 4
        if nfadc > 255: nfadc = 255
        # Format 63 - non-compliant with LBNL engineering V0!
        #             buffer length field included itself.
        # Format 62 - buffer length does not include the 2-byte
        #             length - compliant now.  KDH 4/25/2004
        eng = struct.pack('>H8BI', 62, abfmt, nfadc,
            ((fmt & 1 != 0) * 0x0f) + ((fmt & 2 != 0) * 0xf0),
            ((fmt & 4 != 0) * 0x0f) + ((fmt & 8 != 0) * 0xf0),
            self.trigmode, 0, 
            (self.clock0 & 0xff0000000000) >> 40,
            (self.clock0 & 0x00ff00000000) >> 32,
            self.clock0 & 0xffffffff)
        # Write FADC
        for i in range(nfadc << 4):
            eng = eng + struct.pack('>H', self.fadc[i])
        # Write ATWD-A
        for i in range(4):
            if afmt & (1 << i):
                for j in range(0, len(self.atwa[i])):
                    eng = eng + struct.pack('>H', self.atwa[i][j])
        # Write ATWD-B
        for i in range(4):
            if bfmt & (1 << i):
                for j in range(0, len(self.atwb[i])):
                    eng = eng + struct.pack('>H', self.atwb[i][j])
        return struct.pack('>H', len(eng)) + eng

class dorint(object):
    def __init__(self, device):
        """New create routine with driver buffersize discovery."""
        try:
            f = open("/proc/driver/domhub/bufsiz", "rt")
            self.bsiz = int(f.read(20))
            f.close()
        except IOError:
            # Oops - no file - well, try the old pre-procfile size!
            self.bsiz = 500
        self.fd = os.open(device, os.O_RDWR)
        self.buffer = ""
            
    def fileno(self):
        """Returns the  file descriptor - required for some ops"""
        return self.fd
    
    def recv(self, size):
        if len(self.buffer) < size:
            # Protect the reads - never read unless driver
            # says it's ready - otw it returns an error
            si, so, sx = select( [ self ], [], [], 30 )
            if not len(si):
                raise IBEX('Timeout error.')
            self.buffer += os.read(self.fd, self.bsiz)
        if len(self.buffer) <= size:
            ret = self.buffer
            self.buffer = ""
        else:
            ret = self.buffer[0:size]
            self.buffer = self.buffer[size:]
        return ret

    def send(self, buf):
        return os.write(self.fd, buf)

    def close(self):
        os.close(self.fd)
        
class ibx(object):
    """IceBoot connection class"""
    eol = re.compile('\s*\r\n\s*')
    SPEF_DELAY = 150000

    def __init__(self, host, *args):
        if len(args) == 0:
            self.port = None
        elif len(args) == 1:
            self.port = args[0]
        elif len(args) == 3:
            self.port = self.encodePort(args[0], args[1], args[2])
        else:
            raise_(AttributeError, "Illegal argument list " + str(args))

        if self.port is None:
            # interpret 'host' as device filename
            self.s = dorint(host)
        else:
            # try opening socket
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((host, self.port))

        # Call to flush input FIFO in case there is junk lying around
        self.recv(timeout=0.25)
            
        self._timeout = _TIMEOUT

        # This next section has gotten ugly with iceboot and configboot
        # support - the idea is you first must figure out your state,
        # then you get out of configboot if necessary.
        
        # Figure out - are you in configboot or iceboot?
        self.s.send('\r\n')
        prompt = self.recv(timeout=0.1)
        
        #print "PROMPT:", prompt
        if prompt.find('#') >= 0:
            # send 'r' to get out of configboot, if you are there
            self.s.send('r\r\n')
            while True:
                si, so, sx = select([ self.s ], [], [], 5.0)
                if len(si) > 0:
                    try:
                        prompt = self.s.recv(_CHUNKSIZE)
                    except socket.error as msg:
                        raise_(socket.error, 'Socket Error for ' + \
                            self.portString() + ': ' + str(msg))
                    #print "PROMPT[I]:",prompt
                    if prompt.find('>') >= 0:
                        break
                else:
                    break

        # More junk flushing
        while True:
            si, so, sx = select([ self.s ], [], [], 0.1)
            if len(si) == 0: break
            self.recv(timeout=0.1)
        
        # Some old boards respond differently
        txt = self.send('domid')
        if txt.find('unknown') < 0:
            self.boardId = self.send('type')
        else:
            self.boardId = self.send('boardID type')

    def recv(self, timeout=1.0):
        """Read bytes until iceboot starts blocking."""
        msg = ''
        while True:
            si, so, sx = select([ self.s ], [], [], 0.1)
            if len(si) > 0:
                try:
                    msg += self.s.recv(_CHUNKSIZE)
                except socket.error as msg:
                    raise_(socket.error, 'Socket Error for ' + \
                        self.portString() + ': ' + str(msg))
            else:
                break
        return msg
        
    def send(self, command):
        """Send a command to IceBoot.
        The command is any string recognized (or not) by the
        IceBoot command interpreter.
        """
        if DEBUG_LEVEL > 1:
            print("Sending: " + command)
        self.s.send(command + '\r\n')
        reply = ''
        while reply[-3:] != '> \n':
            si, so, sx = select([ self.s ], [], [], self._timeout)
            if len(si) == 0:
                raise_(IBEX, 'Timeout Error for ' + self.portString())
            try:
                rmadd = self.s.recv(_CHUNKSIZE)
            except socket.error as msg:
                raise_(socket.error, 'Socket Error for ' + \
                    self.portString() + ': ' + str(msg))
            if DEBUG_LEVEL > 5:
                print(rmadd)
            reply = reply + rmadd
        if DEBUG_LEVEL > 4:
            print("Reply: " + reply)
        
        # Hunt the first CR+LF - echo separator
        sep = reply.find('\r\n')
        echo = reply[0:sep]
        text = self.eol.sub(' ', reply[sep:])
        text = text[0:-3]
        
        if DEBUG_LEVEL > 2:
            print('Echoed:  ' + echo)
            print('Message: ' + text) 
        
        return text.strip()

    def encodePort(cls, card, pair, domAB):
        """Encode card/pair/domAB into dtsx port"""
        if int(domAB) < 0 or int(domAB) > 1:
            raise_(AttributeError, 'Illegal domAB value ' + str(domAB))
        elif int(pair) < 0 or int(pair) > 3:
            raise_(AttributeError, 'Illegal pair value ' + str(pair))
        elif int(card) < 0 or int(card) > 31:
            raise_(AttributeError, 'Illegal card value ' + str(card))

        return 5000 + (int(card) * 8) + (int(pair) * 2) + int(domAB)

    encodePort = classmethod(encodePort)

    def decodePort(cls, port):
        """Decode dtsx port into card/pair/domAB"""
        if port is None:
            return (None, None, None)

        port = int(port)
        if port < 5000 or port > 5256:
            return (None, None, None)

        port = port - 5000
        domAB = port % 2
        port = port // 2
        pair = port % 4
        port = port // 4
        card = port
        return (card, pair, domAB)

    decodePort = classmethod(decodePort)

    def portString(self):
        """Return string description of port"""
        if self.port is None:
            return self.host

        (card, pair, domAB) = self.decodePort(self.port)
        if card is None or pair is None or domAB is None:
            return 'port ' + str(self.port)

        if domAB == 0:
            dom = 'A'
        else:
            dom = 'B'

        return 'card ' + str(card) + ' pair ' + str(pair) + ' dom ' + dom

    def zdump(self, count, address):
        """Capture binary dump of the 'zdump' command.  Returns
        a string buffer object containing the raw byte stream."""
        zdcmd = "%d %d zd\r\n" % (address, count)
        self.s.send(zdcmd)
        # Allow extra time for acquisition to complete
        self.s.recv(len(zdcmd))
        words = struct.unpack('i', self.s.recv(4))
        #print "Uncompressed size: " + str(words[0]*4)
        deco = zlib.decompressobj()
        data = ''
        nzb  = 0
        while len(data) < 4*count:
            si, so, sx = select([ self.s ], [], [], self._timeout)
            if len(si) == 0:
                raise IBEX('Timeout Error')
            buf = self.s.recv(_CHUNKSIZE)
            nzb += len(buf)
            data += deco.decompress(buf)
            while len(deco.unconsumed_tail) > 0:
                data += deco.decompress(deco.unconsumed_tail)
        terminator = deco.unused_data
        try:
            while terminator[-3:] != '> \n':
                terminator += self.s.recv(3)
        except IBEX:
            # Allow timeouts here - TODO fix this bug
            pass
        #print "Compressed size: " + str(nzb)
        return data
        
    def getId(self):
        """Returns the DOM mainboard identification string."""
        return self.boardId
        
    def setDAC(self, dac, value):
        """Sets DAC dac to value"""
        self.send('%d %d writeDAC' % (dac, value))

    def getDAC(self, dac):
        """Reads the readback of a DAC stored in FPGA memory"""
        return int(self.send(str(dac) + ' readDAC . drop'))
        
    def readADC(self, adc):
        """Get current value of ADC adc - returns ADC counts."""
        return int(self.send(str(adc) + ' readADC . drop'))
        
    def readHV(self):
        """Read the PMT HV base readback voltage"""
        return int(self.send('readBaseADC . drop'))
        
    def setHV(self, value):
        self.send(str(value) + ' writeActiveBaseDAC')
        
    def enableHV(self):
        """Turn on HV - returns HV readback DAC"""
        self.send('enableHV')
        return self.readHV()
        
    def disableHV(self):
        """Disable HV"""
        self.send('disableHV')
        
    def mux(self, which):
        """Set the MUX input to ATWD ch3"""
        msel = { 'clock1x': '0', 'clock2x': '1', 'ledmux': '2',
                 'flashermux': '3', 'commin': '6' }
        m = msel[which]
        if m == None:
            return
        self.send(m + ' analogMuxInput')
        
    def pulserOn(self):
        """Turn on pulser."""
        self.send("0 %s ! %s %s !" % (forthHex(FPGA_TRIGGER_MASK_REGISTER),
                                      forthHex(FPGA_TRIGGER_FE_PULSER),
                                      forthHex(FPGA_TRIGGER_MASK_REGISTER)))
    def pulserOff(self):
        """Turn off pulser"""
        self.send("0 %s !" % (forthHex(FPGA_TRIGGER_MASK_REGISTER)))
        
    def readTemperature(self):
        """Get current temperature"""
        return int(self.send('readTemp . drop'))

    def readPressure(self):
        """Get pressure - use IceBoot command 'readPressure'"""
        return int(self.send('readPressure . drop'))
    
    def acqStatus(self):
        """Read the ACQ stat register"""
        return int(self.send(forthHex(FPGA_ACQ_COMPLETE_REGISTER) + ' @ . drop'))
        
    def spef(self):
        """Does a SPEF to get discriminator crossing rate"""
        return int(self.send('%s @ . drop' % (forthHex(FPGA_SCALER_SPE_FPGA))))
        
    def discriminatorScan(self, low, high):
        """Scans over SPEFs"""
        hist = []
        scan = self.send('%d %d ?DO 9 i writeDAC %d usleep %s @ . drop LOOP' 
            % (high, low, 125000, forthHex(FPGA_SCALER_SPE_FPGA))
            ).split()
        thr = low
        for x in scan:
            hist.append( (thr, int(x)) )
            thr += 1
        return hist
    
    def acq(self, trigmode):
        """Acquire ATWD A, B, FADC"""
        reset = trigmode & 0xff000000
        x = self.send('%s %s ! %s %s ! %d usleep %s 512 od %s 512 od %s %s !'
            % (
                forthHex(reset), forthHex(FPGA_TRIGGER_MASK_REGISTER), 
                forthHex(trigmode), forthHex(FPGA_TRIGGER_MASK_REGISTER), 25000,
                forthHex(FPGA_ATWD0), forthHex(FPGA_ATWD1),
                forthHex(reset), forthHex(FPGA_TRIGGER_MASK_REGISTER))
            )
        status  = self.acqStatus()
        z = x.split()
        atwda = unpack_octal_dump(z)
        atwdb = unpack_octal_dump(z)
        #fadc = unpack_octal_dump(z)
        return (atwda, atwdb, status)
        
    def acqX(self, nsample, format, mode):
        """This is the eXtended acqusition mode
        nsample - # / samples to batch acquire
        format  - ATWD / FADC readout format bitmask
        mode    = 'cpu' or 'spe'.
        Returns a list of hit class objects from
        which you may extract hit data."""
        # Compute the number of readout points
        #  . 64  32-bit ints per ATWD channel readout
        #  . 128 32-bit ints if the FADC is readout
        #  . 4   32-bit ints for the clock and spare
        natwd = 0
        nfadc = 0
        for i in range(0, 8):
            fmsk = 1 << i
            if format & fmsk:
                natwd += 1
        natwd <<= 6
        if format & 0x100:
            nfadc = 128
        node = (natwd + nfadc + 4) * nsample
        if mode == 'cpu':
            mstr = 'forced'
            mxde = 0x10
        elif mode == 'spe':
            mstr = 'disc'
            mxde = 0x01
        else:
            raise IBEX('Unknown trigger mode ' + mode)
        self.send('%s %s acq-%s' % (nsample, format, mstr))
        z = io.StringIO(self.zdump(node, 0x1000000))
        # now - parse the zdump into a managable data structure
        acqlist = [ ]
        while z.pos < z.len:
            acqlist.append( hit(z, format, mxde) )
        return acqlist

    def setSPEDeadtime(self, deadtime):
        """Set deadtime on FPGA 'spef' scaler.
        ARGUMENTS
            - deadtime  deadtime value expressed as 2^N * 100 ns,
                        e.g., for a deadtime of 12.8 usec use a
                        deadtime word of 7:
                             2^7 = 128 * 100ns = 12.8 usec
        """
        self.send('%s %s !' % (forthHex((deadtime & 15) <<12),
                               forthHex(FPGA_DEADTIME)))
        
    def dumpAddresses(self, addr, nwords):
        """This function dumps the address range
        from addr to addr + 4*nwords and returns
        nwords 32-bit numbers"""
        response = self.send('%s %s od' % (forthHex(addr), forthHex(nwords)))
        olist = response.split()
        vlist = [ ]
        for iaddr in range(len(olist)):
            if iaddr % 5 != 0:
                vlist.append(int(olist[iaddr], 16))
        return vlist

    def readClock(self):
        """Readout the 48-bit free-running DOM clock.  Return a long."""
        clk = self.send('%s @ . drop %s @ . drop' % (
            forthHex(FPGA_CLOCK_LOW),
            forthHex(FPGA_CLOCK_HI))).split()
        return int(clk[0]) + pow(2, 32) * int(clk[1])
        
def unpack_octal_dump(zlist):
    qlist = []
    for k in range(0, 640):
        z = zlist.pop(0)
        if DEBUG_LEVEL > 4:
            print('unpack_octal_dump(): %d %s' % (k, z)) 
        if k % 5:
            qlist.append(int(z, 16))
    return qlist

def unpack_odx(zlist, n):
    """Pick out next n items from the list - cut shortwords"""
    # print 'unpack_odx(): zlist[0] = %s len= %d' % (zlist[0], len(zlist))
    qlist = []
    while len(qlist) < 2*n:
        m = len(zlist)
        z = zlist.pop(0)
        if m % 5:
            qlist.append(int(z[4:8], 16))
            qlist.append(int(z[0:4], 16))
    return qlist
    
def unpack_odx_clock(zlist):
    addr = zlist.pop(0)
    clkl = zlist.pop(0)
    clkh = zlist.pop(0)
    res0 = zlist.pop(0)
    res1 = zlist.pop(0)
    return (int(clkh + clkl, 16), int(res1 + res0, 16))
    
def forthHex(anum):
    return '$%x' % anum
    
def repTriggerMode(mode):
    return '%x' % mode
