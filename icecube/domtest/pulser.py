
import socket
import time
import math
import random

version = "$Revision: 1.7 $"

class PulserException(Exception):
    """Pulser exception class."""
    def __init__(self, txt):
        self.message = txt
    def __str__(self):
        return self.message

class LockInSyncFailure(Exception):
    """Exception class indicating failure of LockIn class to
    acquire a synchronization between DOM and pulser clocks."""

    def __init__(self, iter):
        self.iter = iter
    def __str__(self):
        return "LockIn failed to sync after %d iterations." % (self.iter)
    
        
class pulser:
    """Pythonic interface to Chris W's uC pulser circuit.
    The pulser delivers up to 3 optical signals:
        - Marker pulse   a 26 dB pulse that is used to
                         mark the presence of the following
                         fast pulse.  This pulse is approx.
                         20 nsec wide.
        - Fast pulse     a small, narrow (2-5 nsec) pulse
                         useful for single photon counting.
                         It follows the marker pulse by
                         approximately 116 nsec.
        - Big pulse      a XX dB pulse - broad and huge for
                         non-linearity, afterpulsing.
    The pulse amplitude is given relative to the fast pulse.

    The class objects will have the following public data
    members:
        - p.marker      0 if marker off, 1 if on
        - p.fast        ibid. for fast pulse
        - p.big         ibid. for big pulse
        - p.freq        set to last successful frequency setting

    Author:
        Kael Hanson
        IceCube Project
        (C) 2004 K. Hanson
    """

    def __init__(self, host, port):
        """Construct object, connecting to the pulser server."""
        self.host = host
        self.port = port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((host, port))
        self.allOff()
        self.setPulseFrequency(1000.0)
        self.setBrightness(2000)
        
    def __dispatch(self, command):
        """Internal function for handling message send and retrieval."""
        self.s.send(command + "\n")
        # Delay to give the processor time to digest and respond.
        time.sleep(0.1)
        ans = self.s.recv(100).strip()
        # Error handling
        if ans.find('?') >= 0: raise PulserException, ans
            
    def setPulseFrequency(self, f):
        """Set the frequency in Hz."""
        self.__dispatch("FREQ %.2f" % (int(f)))
        self.freq = f

    def markerOn(self):
        """Turn on marker pulse."""
        self.__dispatch("MARKER_PULSE ON")
        self.marker = 1

    def setBrightness(self, br):
        self.__dispatch("BRIGHTNESS %d" % (int(br)))
        self.brightness = br
        
    def fastOn(self):
        """Turn on fast pulse."""
        self.__dispatch("FAST_PULSE ON")
        self.fast = 1

    def bigOn(self):
        """Turn on big pulse."""
        self.__dispatch("BIG_PULSE ON")
        self.big = 1

    def syncOn(self):
        """Turn on sync pulse (TTL trigger)."""
        self.__dispatch("SYNC_OUTPUT ON")
        self.sync = 1

    def trigOn(self):
        self.__dispatch("TRIG_OUTPUT ON")
        self.trig = 1

    def relayOn(self):
        self.__dispatch("RELAY ON")
        self.relay = 1
        
    def allOff(self):
        """Turn off all LED pulses."""
        self.__dispatch("ALL OFF")
        self.marker = self.fast = self.big = self.trig = self.sync = self.relay = 0

    def __str__(self):
        return "pulser@%s:%d M:%d F:%d B:%d S: %d R: %d Freq: %.6g" \
               % (self.host,
                  self.port,
                  self.marker,
                  self.fast,
                  self.big,
                  self.sync,
                  self.relay,
                  self.freq)

def sync(clx, clk0, err, tol=1E-08, bin_width=1.0):
    """The DOM to pulser synchronization routine."""
    brk = [clk0 - err, clk0, clk0 + err]
    hist = perhist(clx, bin_width)
    for i in range(500):
        vals = map(hist.fill, brk)

        # Harbinger of bad things to come
        if brk[2]==brk[1] or brk[1]==brk[0]:
            brk[2] = brk[1] + random.random()
            brk[0] = brk[1] - random.random()
            
        if vals[1]-vals[0] < vals[1]-vals[2]:
            # Move up point between 0 and 1
            trp = brk[0] + 0.5*(brk[1] - brk[0])
            tva = hist.fill(trp)
            m = tva < vals[1]
            # print "Move -"
        else:
            # Test point between 1 and 2
            trp = brk[1] + 0.5*(brk[2] - brk[1])
            tva = hist.fill(trp)
            m = 2 - (tva < vals[1])
            # print "Move +"
        brk[m] = trp
        vals[m] = tva
        #print i, brk, vals
        if (brk[2] - brk[0]) / brk[0] < tol:
            hist.fill(brk[1])
            return (hist.mode(), brk[1])

    # Fail
    raise LockInSyncFailure, i

class perhist:
    def __init__(self, clk, w):
        self.clk = clk
        self.bin_width = w
        self.hist = { }
        
    def fill(self, period):
        self.hist = { }
        self.mean = 0.0
        self.var  = 0.0
        self.nent = 0
        for clk in self.clk:
            clkmod = clk % period
            self.mean += clkmod
            self.var  += clkmod**2
            self.nent += 1
            bin = int(clkmod / self.bin_width)
            if self.hist.has_key(bin) == 0:
                self.hist[bin] = 1
            else:
                self.hist[bin] += 1
        self.max = max(self.hist.values())
        return -self.max

    def mode(self):
        self.max = max(self.hist.values())
        for bin in self.hist.keys():
            if self.hist[bin] == self.max:
                return bin*self.bin_width
