#!/bin/env python
"""
Digitial Optical Module mainboard analog front-end calibration script.
$Id: domcal.py,v 1.11 2006/02/15 21:13:13 kael Exp $
"""

import ibidaq as daq
import time
import getopt
import os
import sys
from urllib import urlopen
from xml.dom.minidom import parse
from numpy import array, zeros, sum, concatenate
from math import sqrt
#from numarray.fft import fft

revision = "$Rev$"
debug_level = 1                 # 1: normal output level - warnings / errors
                                # 3: fair amount of info/debug
                                # 4: a lot of debug messages
PULSER_DAC  = 11

def regression(x, y):
    xm = sum(x)/len(x)
    ym = sum(y)/len(y)
    x0 = x - xm
    y0 = y - ym
    xx = sum(x0*x0)
    yy = sum(y0*y0)
    xy = sum(x0*y0)
    slope = xy / xx
    yint  = ym - slope * xm
    r     = xy / sqrt(xx*yy)
    return slope, yint, r

def hunt(q, alo, ahi):
    while ahi - alo > 1:
        amp = (alo + ahi) / 2
        q.setDAC(PULSER_DAC, amp)
        time.sleep(0.25)
        rate = q.spef()
        if debug_level > 3:
            print "hunt(): %d %d %d %d %d" % (q.getDAC(9), alo, ahi, amp, rate)
        if rate > 3900:
            ahi = amp
        else:
            alo = amp
    return alo, ahi

def meanvar(x):
    mean = 0
    var  = 0
    for i in x:
        mean += i
    mean /= len(x)
    for i in x:
        var += (i - mean)**2
    var /= len(x)
    return mean, var

class atwd_calconst:
    """ATWD Calibration DataStructure."""
    def __init__(self, slope_array, int_array, r_array):
        self.slope = slope_array
        self.inter = int_array
        self.r     = r_array

    def cal(self, raw):
        """Transform raw ATWD to calibrated."""
        return raw * self.slope + self.inter

def _getNodeText(nodes):
    txt = ""
    for n in nodes:
        if n.nodeType == n.TEXT_NODE:
            txt += n.data
    return txt

def _parseADCDAC(node):
    return int(node.getAttribute("channel")), int(_getNodeText(node.childNodes))

class Fit:
    """
    Fit data class.
    """
    def __init__(self, swi, args=None):
        if type(swi) is str:
            self.model = swi
            self.param = { "slope" : args[0], "intercept" : args[1] }
            self.r = args[2]
        else:
            node = swi
            self.model = node.getAttribute("model")
            self.param = { }
            for par in node.getElementsByTagName("param"):
                key = par.getAttribute("name")
                val = float(_getNodeText(par.childNodes))
                self.param[key] = val
                self.r = float(_getNodeText(
                    node.getElementsByTagName(
                    "regression-coeff")[0].childNodes))
    
    def getParam(self, name):
        return self.param[name]
        
    def getR(self):
        """Returns the regression coefficient goodness-of-fit param."""
        return self.r

    def toXML(self, f):
        f.write(' '*8 + '<fit model="%s">\n' % (self.model))
        for p in self.param.items():
            f.write(' '*12 + '<param name="%s">%.6g</param>\n' % p)
        f.write(' '*12 + '<regression-coeff>%.6g</regression-coeff>\n' % (self.r))
        f.write(' '*8 + '</fit>\n')
    
class calibrator:
    """
    DOM Analog FE Calibration class.
    Class public data:
        - atwd_slope[ch][bin] ......... ATWD slopes
        - atwd_intercept[ch][bin] ..... ATWD intercepts
        - ampgain[ch] ................. amplifier gain constants
        - ampgain_error[ch] ........... amplifier gain error estimates
        - fadcpar[key] ................ hash of constants for FADC
                                        key      description
                                        bias     bias DAC setting
                                        fadc_ref reference voltage setting
                                        pedestal FADC pedestal
                                        gain     FADC gain (mV / tick)
        - pulser ...................... Fit of pulser constants
    """
    
    def __init__(self, arg):

        # Can be constructed either by
        #   (1) passing a daq.ibx - do a live cal
        #   (2) passing a uri object - grab from prerecorded xml file
        
        if isinstance(arg, daq.ibx):
            self.inVitroCalibration(arg)
        else:
            self.fromXML(arg)

    def setup_atwd_fits(self):
        self.atwd_intercept = [ None ] * 8
        self.atwd_slope     = [ None ] * 8
        for ch in (0, 1, 2, 4, 5, 6):
            self.atwd_intercept[ch] = zeros(128,'d')
            self.atwd_slope[ch]     = zeros(128,'d')
            for bin in range(128):
                self.atwd_intercept[ch][bin] = self.atwd_fit[ch][bin].getParam("intercept")
                self.atwd_slope[ch][bin] = self.atwd_fit[ch][bin].getParam("slope")

    def recoATWD(self, w, ch, bias):
        """Returns amplitude calibrated vector from raw ATWD waveform."""
        lenw = len(w)
        u = array(w, 'd')
        if lenw < 128: u = concatenate((zeros(128-lenw, 'd'), u))
        v = self.atwd_intercept[ch] + self.atwd_slope[ch]*u - bias
        # Trim v to correct length
        v = v[128-lenw:] / self.ampgain[ch%4]
        return v[::-1]

    def calcATWDFreq(self, dac, atwd):
        return self.freq[atwd].getParam("intercept") + dac * self.freq[atwd].getParam("slope")
        
    def inVitroCalibration(self, q):
        """Does what it says - gets a live calibration from a daq objekt."""
        self.domid = q.getId()
        self.date = time.strftime("%c")
        self.temperature = q.readTemperature()
        self.dac = [ None ] * 16
        self.adc = [ None ] * 24
        for dac in range(16):
            self.dac[dac] = q.getDAC(dac)
        for adc in range(24):
            self.adc[adc] = q.readADC(adc)
        self.pulsercal(q)
        self.atwdcal(q)
        self.setup_atwd_fits()
        self.fadccal(q)
        self.amplifiercal(q)
        self.clockcal(q)
        
    def fromXML(self, uri):
        """Fetch calibration data from specified URL."""
        f = urlopen(uri)
        self.uri = uri
        doc = parse(f)
        # Look for the <domcal> tag
        root = doc.firstChild
        
        # Get the DOM id
        self.domid = _getNodeText(root.getElementsByTagName("domid")[0].childNodes)
        
        # Get the date
        self.date = _getNodeText(root.getElementsByTagName("date")[0].childNodes)
        
        # Convert the temperature from <temperature> node
        tempnode = root.getElementsByTagName("temperature")[0]
        temperature = float(_getNodeText(tempnode.childNodes))
        if tempnode.getAttribute("format") == "raw":
            if temperature > 32767.0:
                temperature -= 65536
            temperature /= 256.0;
        self.temperature = temperature
        
        self.dac = [ None ] * 16
        self.adc = [ None ] * 24
        
        # Get the DAC and ADC channels
        for e in root.getElementsByTagName("dac"):
            ch, val = _parseADCDAC(e)
            self.dac[ch] = val
        for e in root.getElementsByTagName("adc"):
            ch, val = _parseADCDAC(e)
            self.adc[ch] = val
            
        # Read in pulser calibration info
        self.pulser = None
        pulser = root.getElementsByTagName("pulser")
        if len(pulser) > 0:
            self.pulser = Fit(pulser[0].getElementsByTagName("fit")[0])
            
        # Read in discriminator cal
        self.disc = dict()
        disc   = root.getElementsByTagName("discriminator")
        for disc in root.getElementsByTagName("discriminator"):
            self.disc[disc.getAttribute("id")] = \
                Fit(disc.getElementsByTagName("fit")[0])
            
        self.atwd_fit = [ ]
        for ch in range(8):
            self.atwd_fit.append( [ None ] * 128 )
        self.ampgain = [ -16.0, -2.0, -0.25 ]
        self.ampgain_error = [ 0.0, 0.0, 0.0 ]
        
        for atwd in root.getElementsByTagName("atwd"):
            ch = int(atwd.getAttribute("channel"))
            bin = int(atwd.getAttribute("bin"))
            atwd_id = atwd.getAttribute("id")
            if len(atwd_id) and int(atwd_id) == 1: ch += 4
            fit = Fit(atwd.getElementsByTagName("fit")[0])
            self.atwd_fit[ch][bin] = fit
            
        for amp in root.getElementsByTagName("amplifier"):
            ch = int (amp.getAttribute("channel"))
            gn = amp.getElementsByTagName("gain")[0]
            self.ampgain[ch] = float(_getNodeText(gn.childNodes))
            self.ampgain_error[ch] = float(gn.getAttribute("error"))

        # Readback the fit information
        self.freq = [ None, None ]
        for fnod in root.getElementsByTagName("atwdfreq"):
            if fnod.hasAttribute("atwd"):
                ch = int(fnod.getAttribute("atwd"))
            else:
                ch = int(fnod.getAttribute("chip"))
            self.freq[ch] = Fit(fnod.getElementsByTagName("fit")[0])
            
        # Vectorize the ATWD fit for fast reconstruction
        self.setup_atwd_fits()

        # Read in the HV gain calibration information, if available
        gainCal = root.getElementsByTagName("hvGainCal")
        self.pmt_gain_fit = None
        if len(gainCal):
            self.pmt_gain_fit = Fit(gainCal[0].getElementsByTagName("fit")[0])

    def toXML(self, fxml):
        fxml.write("""<?xml version="1.0" encoding="iso-8859-1"?>\n""")
        fxml.write("""<domcal>
    <date>%s</date>
    <domid>%s</domid>
    <temperature format="raw">%d</temperature>\n""" %
                   (self.date, self.domid, self.temperature)
                   )
        for idac in range(16):
            fxml.write("""    <dac channel="%d">%d</dac>\n""" %
                       (idac, self.dac[idac]))
        for iadc in range(24):
            fxml.write("""    <adc channel="%d">%d</adc>\n""" %
                       (iadc, self.adc[iadc]))
            
        fxml.write("    <pulser>\n")
        self.pulser.toXML(fxml)
        fxml.write("    </pulser>\n")

        for ch in (0, 1, 2, 4, 5, 6):
            for bin in range(128):
                fxml.write('    <atwd channel="%d" bin="%d">\n' % (ch, bin))
                self.atwd_fit[ch][bin].toXML(fxml)
                fxml.write('    </atwd>\n')

        for fpr in self.fadcpar.items():
            fxml.write("    <fadc parname='%s' value='%.6g'/>\n" % fpr)
            
        for ch in range(3):
            fxml.write("""    <amplifier channel="%d">
        <gain error="%.6g">%.6g</gain>
    </amplifier>\n""" % (ch, self.ampgain_error[ch], self.ampgain[ch]))

        for ch in range(2):
            fxml.write("""    <atwdfreq chip="%d">\n""" % (ch))
            self.freq[ch].toXML(fxml)
            fxml.write("""    </atwdfreq>\n""")
            
        fxml.write("</domcal>\n")

    def fadccal(self, q):
        bias = q.getDAC(7)
        fadcref = q.getDAC(10)
        q.disableHV()
        time.sleep(5.0)
        hqx = q.acqX(11, 0x100, 'cpu')
        hqx.pop(0)
        fadcped = 0
        n = 0
        for h in hqx:
            fadcped += sum(array(h.fadc,'d'))
            n += len(h.fadc)
        fadcped /= n

        q.pulserOn()
        pulser_amp = 300
        q.setDAC(PULSER_DAC, pulser_amp)
        vmax = self.pulser.getParam("slope")*pulser_amp + self.pulser.getParam("intercept")
        hqx = q.acqX(101, 0x100, 'spe')
        hqx.pop(0)
        wmax = 0
        for h in hqx:
            # Convert to Volts at FADC input
            w = 2.00/1024*(array(h.fadc, 'd') - fadcped)
            wmax += max(w)
        wmax /= 100
        self.fadcpar = { 'bias': bias, 'fadc_ref': fadcref, 'pedestal': fadcped,
                         'gain' : wmax / vmax }
        q.pulserOff()
        
    def pulsercal(self, q):
        """FE Pulser Calibration.
        Calibrates the FE DAC-> Volts relationship."""
        q.setDAC(7, 1925)
        bias = q.getDAC(7)
        
        q.pulserOn()
        
        thresh = []
        pulse  = []
        for disc in (525, 550, 575, 600, 625, 650, 675, 700, 750, 800, 900, 1000):
            q.setDAC(9, disc)
            time.sleep(0.25)
            a, b = hunt(q, 0, 1000)
            q.setDAC(PULSER_DAC, a)
            time.sleep(0.25)
            c = q.spef()
            q.setDAC(PULSER_DAC, b)
            time.sleep(0.25)
            d = q.spef()
            if debug_level > 2:
                print "calibrator::pulsercal()%d %d %d %d %d" % (disc, a, b, c, d)
            if c < 3900 and d > 3900:
                x = (b - a) / float(d - c) * float(3900 - c) + a
                if debug_level > 2:
                    print "%d %d %d %d %d %.2f" % (disc, a, b, c, d, x)
                mv = 2.44E-05*(0.4*disc-0.1*bias)*5
                thresh.append(mv)
                pulse.append(x)
    
        q.pulserOff()
            
        thv = array(thresh, 'd')
        psv = array(pulse, 'd')
        self.pulser = Fit("linear", regression(psv, thv))

    def atwdcal(self, q):

        q.setDAC(12, 0)
        q.setDAC(13, 0)
        q.disableHV()
        time.sleep(5.0)
        
        scan = { }
        for bias in range(1000, 2000, 100):
            q.setDAC(7, bias)
            time.sleep(5.0)
            ped = [ zeros(128,'d') for ch in range(8) ]
            hqx = q.acqX(101, 0x07, 'cpu')
            hqx.pop(0)
            hqy = q.acqX(101, 0x70, 'cpu')
            hqy.pop(0)
            hqx += hqy
            for h in hqx:
                for ch in (0, 1, 2, 4, 5, 6):
                    if h.atwd[ch]:
                        ped[ch] += array(h.atwd[ch], 'd')
            for ch in (0, 1, 2, 4, 5, 6):
                ped[ch] /= 100.0
                # print "ATWD A ch%d: %.2f" % (ch, sum(ped[ch])/128)
            scan[bias] = ped

        # Loop on channel and bin - do regression fit
        self.atwd_fit = [ None ] * 8
        for ch in (0, 1, 2, 4, 5, 6):
            self.atwd_fit[ch] = [ None ] * 128
            for bin in range(128):
                v = []
                a = []
                for bias, vec in scan.items():
                    v.append(bias * 5.0 / 4096.0)
                    a.append(vec[ch][bin])
                    # f = file('debug/atwd-a-%d-%d.vec' % (ch, bin), 'wt')
                    # for pair in zip(a,v):
                    #    f.write("%.2f %.2f\n" % pair)
                    # f.close()
                self.atwd_fit[ch][bin] = Fit(
                    "linear", regression(array(a,'d'), array(v,'d')))
                
    def amplifiercal(self, q):

        # Enable pulser
        q.pulserOn()
        q.setDAC(9, 535)
        
        pulseramp = ( 50, 200, 1000, 0, 50, 200, 1000, 0)
        bias = q.getDAC(7)
        biasvolts = bias * 5.0 / 4096.0

        self.ampgain       = [ None ] * 3
        self.ampgain_error = [ None ] * 3
        # Capture pulser triggers
        for ch in range(4, 7):
            p = pulseramp[ch]
            q.setDAC(PULSER_DAC, p)
            v = self.pulser.getParam("slope")*p + self.pulser.getParam("intercept")
            # print "Set pulser to %d DAC (%.3g V)" % (p, v)
            time.sleep(0.5)
            hqx = q.acqX(251, 1 << ch, 'spe')
            hqx.pop(0)
            wmin = []
            for h in hqx:
                w = array(h.atwd[ch], 'd')
                x = self.atwd_intercept[ch] + self.atwd_slope[ch]*w - biasvolts
                wmin.append(min(x))
            u, var = meanvar(wmin)
            std = sqrt(var)
            self.ampgain[ch%4], self.ampgain_error[ch%4] = u/v, std/(v*sqrt(250))

        q.pulserOff()

    def clockcal(self, q):
        q.mux('clock2x')
        self.freq = [ None, None ]
        speed = [750, 1000, 1250, 1500, 1750, 2000]
        for chip in range(2):
            freq  = [ ]
            old_dac = q.getDAC(4*chip)
            for s in speed:
                q.setDAC(4*chip, s)
                time.sleep(0.5)
                hqx = q.acqX(3, 0x08 << (chip*4), 'cpu')
                w   = array(hqx[2].atwd[chip*4+3], 'd')
                # Remove DC
                wx  = w - sum(w) / len(w)
                # Should put a window here but I forgot Hamming
                psd = abs(fft(wx))
                psd = psd[0:64]
                imx = 0
                for i in range(len(psd)):
                    if psd[i] > psd[imx]: imx = i
                # print imx
                freq.append(2.0*40.0*65.0 / imx)
            #print speed, freq
            self.freq[chip] = Fit("linear", regression(array(speed, 'd'),
                                                       array(freq, 'd')))

if __name__ == "__main__":

    if len(sys.argv) < 3:
        print """usage: domcal <host> <port> <dir>"""
        sys.exit(1)
        
    host = sys.argv[1]
    port = int(sys.argv[2])
    dir  = sys.argv[3]

    if os.access(dir, os.F_OK) == 0: os.mkdir(dir)
    q = daq.ibx(host, port)
    dir = os.path.join(dir, q.getId())
    if os.access(dir, os.F_OK) == 0: os.mkdir(dir)

    # Kill the HV
    q.setHV(0)
    q.disableHV()

    calfile = os.path.join(dir,time.strftime("%Y%m%d%H%M")) + ".xdc"
    
    # Do the live calibration
    cal = calibrator(q)

    del(q)

    fxml = file(calfile, "wt")
    cal.toXML(fxml)
    fxml.close()

    # Write out filename to communicate back to parent process
    print calfile



