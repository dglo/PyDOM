#!/bin/env python

"""
A DOM configuration module for DAQ
Author: K. Hanson (kael.hanson@icecube.wisc.edu)
Date: 2006-01-08
"""

import os, sys, math
import xml.sax, xml.dom.minidom
from xml.sax.handler import ContentHandler
import time
import MySQLdb

RCS_ID = "$Id: domconfig.py,v 1.13 2006/04/03 02:10:16 kael Exp $"

db = None
mbid2domid = dict()

# Global variable which selects behavior of LC - prior to DOMApp FPGA 329
# the LC_RX sense was swapped UP <--> DN.  Now LC_TX is swapped but it
# doesn't matter since we are transmitting in both directions at all times
# Set this variable to True if you are using an old FPGA image
lc_rx_swap = False

# Table of default HVs
default_hv = { "2c5bf45ca479": 2604, "308d3f7692fd": 2508, "9ed5742a784d": 2420,
               "d4b05c67ce19": 2410, "d52b66ab6861": 2900, "173ce1549a47": 2800,
               "0b5dc6a92170": 2458, "c80b79e1a8b7": 2870, "06f482883442": 2770,
               "62645a002733": 2640, "69a38b5dc5f8": 2496, "22c1d090b1eb": 2432, 
               "75f1a642df54": 2952, "86355672dcee": 2600, "1ebec6395f96": 2976,
               "eeb299b6639d": 2446 }

lc_exceptions = {
    "31fe50f2c0b4" : 2, # 30-22 is UP_ONLY
    "b821873ff31a" : 3, # 30-24 is DN_ONLY
    "be5843e76a69" : 2, # 29-58 (Nikolassee) is UP_ONLY
    "86438b93c165" : 2, # 59-51 (Medborgarplatsen) is UP_ONLY
    "93728135e247" : 3  # 59-52 (T_Centraalen) is DN_ONLY
    }

lc_span_exceptions = {
    "2a4931d33ab6" : 2, # 38-58 goes to 38-60
    "a2aad9826a9d" : 2  # 38-60 goes to 38-58
    }
    
def db_connect(host, user):
    global db, mbid2domid
    db = MySQLdb.connect(host=host, user=user, db='domprodtest')
    cur = db.cursor()
    cur.execute("""
    SELECT q.tag_serial, p.hardware_serial FROM Product q
    JOIN Assembly a ON a.prod_id = q.prod_id
    JOIN AssemblyProduct ap ON ap.assem_id=a.assem_id
    JOIN Product p ON p.prod_id=ap.prod_id
    WHERE p.prodtype_id=5 and q.prodtype_id=99
    ORDER BY a.datetime""")
    for domid, mbid in cur.fetchall():
        mbid2domid[mbid.lower()] = domid
        
def log(s, level=0):
    if level > 1:
        print >>sys.stderr, "[%s] LOG LEVEL=%d: %s" % \
              (time.strftime("%c"), level, s)
    pass

def calculate_hv(gain, par):
    slope, inter = par
    return int(2*math.pow(10.0, (math.log10(gain)-inter)/slope))
    
def db_lookup_hvpar(mbid):
    cur = db.cursor()
    if mbid not in mbid2domid: log("%s not in DB!" % mbid, 3)
    domid = mbid2domid[mbid]
    # print "%s %s" % (mbid, domid)
    if cur.execute("""
    SELECT
        temperature, slope, intercept
    FROM
        Product p
    JOIN
        DOMCalibration dc ON p.prod_id = dc.prod_id
    JOIN
        DOMCal_HvGain hv ON hv.domcal_id = dc.domcal_id
    WHERE
        p.tag_serial=%s AND temperature < 0 AND regression > 0.99
    ORDER BY dc.date DESC
    LIMIT 1
        """, domid) != 1:
        log("No DB entry for HV: DOM %s" % mbid, 2)
        return None
    t, slope, inter = cur.fetchone()
    return (slope, inter)
        
def generateDOMConfiguration(hvpar, mbid, hubname, streich, 
    module, domname, ab, runtype, **opts):
    """
    Generate an XML string that represents the DOM configuration.
    Arguments are DOM mainboard ID, deployed string, deployed
    module location (1-64) and runtype:
        = 1 --> beacon run without HV
        = 2 --> dark noise run with elevated thresholds
        = 3 --> standard LC run
    """
    
    inice_gain = 1.0E+07
    icetop_gain = { 61: 5.0E+06, 62: 5.0E+04, 63: 5.0E+06, 64: 5.0E+04 }
    
    if 'inice_gain' in opts:
        inice_gain = opts['inice_gain']
    if 'icetop_gain' in opts:
        icetop_gain = opts['icetop_gain']
        
    # LC rules
    if module > 60:
        # IceTop
        cablelen_up = cablelen_dn = (650, 1350, 1350, 1350)
    elif ab == 'A':
        cablelen_up = (550, 1325, 1950, 2725)
        cablelen_dn = (725, 1325, 2125, 2725)
    elif ab == 'B':
        cablelen_up = (725, 1325, 2125, 2725)
        cablelen_dn = (550, 1325, 1950, 2725)
        
    # HV Exceptions
    # The Phenol exceptional case (DOM is noisy if HV too high)
    # Now added Maserati_Bora to the SHDR list
    if mbid in ('57bb7c43b042', '1c871a91050d'):
        hvlimit = 2500
    else:
        hvlimit = 4095
    
    # Dark SPE Exceptions
    if mbid == '57bb7c43b042':
        dark_spe = 625
    elif mbid == 'e53c98680186':
        dark_spe = 943
    else:
        dark_spe = 750
        
    mpe = 560
    
    if runtype == 1:
        # HV OFF - beacons only
        hv = 0
        samples = 4*(128,)
        fadc    = 250
        spe     = 560
        lcmode  = 0
    else:
        # These runs do require HV set to nominal but put in
        # reasonable default (1400 V) if you can't find the DOMCal

        # IceTop special configs is different
        if module > 60:
            samples = (128, 128, 128, 0)
            fadc = 0
            gain = icetop_gain[module]
        else:
            samples = (128, 32, 32, 0)
            fadc = 50
            gain = inice_gain
        
        # Set the PMT high voltage - rules are
        # (1) Use DOMCal fit if available
        # (2) Use default value from table
        # (3) Use default value of 1400 V (2800 DAC)
        hv = 2800
        if mbid in default_hv: hv = default_hv[mbid]
        # hv = calculate_hv(gain, db_lookup_hvpar(mbid))
        if mbid in hvpar: hv = calculate_hv(gain, hvpar[mbid])
        hv = min(hvlimit, hv)
        
        if runtype == 2:
            # Dark run /w/ elevated SPE
            spe  = dark_spe
            lcmode = 0
        elif runtype == 3:
            # Standard LC type run
            # IceTop tanks have higher threshold - muons are 50 pe
            if module > 60:
                spe = 943
                mpe = 943
            else:
                spe = 560
                spe = 560
            # Handle terminal modules - otherwise LC triggers on reflections
            if module == 60:
                if lc_rx_swap:  # No 'dn' module - select RX from UP module only
                    lcmode = 3
                else:
                    lcmode = 2
            elif module == 1:   # No 'up' module - select RX from DN module only
                if lc_rx_swap:
                    lcmode = 2
                else:
                    lcmode = 3
            elif module == 61 or module == 64:
                # (KH) Added special mode for IT - from Serap
                # Fix PY03/PY04 tank A <--> B mixup
                if streich in (21, 29, 30, 39):
                    lcmode = 3
                else:
                    lcmode = 2
            elif module == 62 or module == 63:
                # (KH) Added special mode for IT - from Serap
                # Fix PY03/PY04 tank A <--> B mixup
                if streich in (21, 29, 30, 39):
                    lcmode = 2
                else:
                    lcmode = 3
            elif mbid in lc_exceptions:
                lcmode = lc_exceptions[mbid]
            else:
                lcmode = 1
        else:
            # undefined run type so return ''
            return ''
            
    return '<dom domId="%s" domhub="%s" name="%s" ab="%s">\n' % \
        (mbid, hubname, domname, ab) + \
        '  <param name="NUM_SAMPLES_ch0" value="%d"/>\n' % samples[0] + \
        '  <param name="NUM_SAMPLES_ch1" value="%d"/>\n' % samples[1] + \
        '  <param name="NUM_SAMPLES_ch2" value="%d"/>\n' % samples[2] + \
        '  <param name="NUM_SAMPLES_ch3" value="%d"/>\n' % samples[3] + \
        '  <param name="SAMPLE_SIZE_ch0" value="2"/>\n' + \
        '  <param name="SAMPLE_SIZE_ch1" value="2"/>\n' + \
        '  <param name="SAMPLE_SIZE_ch2" value="2"/>\n' + \
        '  <param name="SAMPLE_SIZE_ch3" value="2"/>\n' + \
        '  <param name="NUM_FADC_SAMPLES" value="%d"/>\n' % fadc + \
        '  <param name="DAC_ATWD0_TRIGGER_BIAS" value="850"/>\n' + \
        '  <param name="DAC_ATWD0_RAMP_RATE" value="350"/>\n' + \
        '  <param name="DAC_ATWD0_RAMP_TOP" value="2300"/>\n' + \
        '  <param name="DAC_ATWD_ANALOG_REF" value="2250"/>\n' + \
        '  <param name="DAC_ATWD1_TRIGGER_BIAS" value="850"/>\n' + \
        '  <param name="DAC_ATWD1_RAMP_RATE" value="350"/>\n' + \
        '  <param name="DAC_ATWD1_RAMP_TOP" value="2300"/>\n' + \
        '  <param name="DAC_PMT_FE_PEDESTAL" value="2130"/>\n' + \
        '  <param name="DAC_MULTIPLE_SPE_THRESH" value="%d"/>\n' % mpe + \
        '  <param name="DAC_SINGLE_SPE_THRESH" value="%d"/>\n' % spe + \
        '  <param name="DAC_FAST_ADC_REF" value="800"/>\n' + \
        '  <param name="DAC_INTERNAL_PULSER" value="0"/>\n' + \
        '  <param name="DAC_LED_BRIGHTNESS" value="1023"/>\n' + \
        '  <param name="ANALOG_MUX_SELECT" value="255"/>\n' + \
        '  <param name="FE_PULSER_STATE" value="0"/>\n' + \
        '  <param name="FE_PULSER_RATE" value="5"/>\n' + \
        '  <param name="PMT_HV_LIMIT" value="%d"/>\n' % hvlimit + \
        '  <param name="PMT_HV_DAC" value="%d"/>\n' % hv + \
        '  <param name="TRIG_MODE" value="2"/>\n' + \
        '  <param name="LOCAL_COIN_MODE" value="%d"/>\n' % lcmode + \
        '  <param name="LOCAL_COIN_WIN_UP_PRE" value="1000"/>\n' + \
        '  <param name="LOCAL_COIN_WIN_UP_POST" value="1000"/>\n' + \
        '  <param name="LOCAL_COIN_CABLELENGTH_UP0" value="%d"/>\n' % cablelen_up[0] + \
        '  <param name="LOCAL_COIN_CABLELENGTH_UP1" value="%d"/>\n' % cablelen_up[1] + \
        '  <param name="LOCAL_COIN_CABLELENGTH_UP2" value="%d"/>\n' % cablelen_up[2] + \
        '  <param name="LOCAL_COIN_CABLELENGTH_UP3" value="%d"/>\n' % cablelen_up[3] + \
        '  <param name="LOCAL_COIN_CABLELENGTH_DN0" value="%d"/>\n' % cablelen_dn[0] + \
        '  <param name="LOCAL_COIN_CABLELENGTH_DN1" value="%d"/>\n' % cablelen_dn[1] + \
        '  <param name="LOCAL_COIN_CABLELENGTH_DN2" value="%d"/>\n' % cablelen_dn[2] + \
        '  <param name="LOCAL_COIN_CABLELENGTH_DN3" value="%d"/>\n' % cablelen_dn[3] + \
        '  <param name="SCALAR_DEADTIME" value="51200"/>' + \
        '</dom>'

class FitGetter(ContentHandler):

    def startDocument(self):
        self.state = 0
        self.slope_string = ''
        self.inter_string = ''
        self.slope = 0.0
        self.intercept = 0.0
        
    def startElement(self, name, attrs):

        if name == 'hvGainCal':
            self.state = 1
            log("set state to 1")
        elif name == 'param' and self.state == 1:
            if attrs['name'] == 'slope':
                self.state = 2
                log("set state to 2")
            elif attrs['name'] == 'intercept':
                self.state = 3
                log("set state to 3")
                
    def endElement(self, name):
        if name == 'hvGainCal':
            self.state = 0
            log("set state to 0")
            self.intercept = float(self.inter_string)
            self.slope = float(self.slope_string)
        if name == 'param' and self.state in (2, 3):
            self.state = 1
            
    def characters(self, content):
        if self.state == 2:
            self.slope_string += content
        elif self.state == 3:
            self.inter_string += content
            
def process_domcals(xmls):
    """
    Parses the gain vs. HV information from the DOMCal XMLs
    """
    fg = FitGetter()
    hv = dict()
    # Parse the HV Gain fits
    for filename in xmls:
        xml.sax.parse(filename, fg)
        mbid = os.path.basename(filename)[7:19]
        if fg.slope > 6 and fg.slope < 10 and \
           fg.intercept > -20 and fg.intercept < -12:
            hv[mbid] = (fg.slope, fg.intercept) 
        else:
            log("Bad fit for mbid %s" % mbid, 3)
    return hv
    
def prologue(hubid, runtype, rundesc):
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + \
           '<!-- generated by domconfig.py ' + RCS_ID + '-->\n' + \
           '<runHeader>\n' + \
           '<steeringFile hubID="%s">\n' % hubid + \
           '<test>\n' + \
           '<domConfiguration configID="%d">\n' % runtype + \
           '<description>\n' + rundesc + '\n</description>'
           
def epilogue(mbids):
    s = '</domConfiguration>\n' + \
        '</test>\n' + \
        '</steeringFile>\n'
    for mbid in mbids:
        s += '<activeDOMs>%s</activeDOMs>\n' % mbid
    return s + '</runHeader>'
    
def mkxml(hvpar, filename, hubname, hubid, runtype, rundesc, doms):
    fxml = file(filename, 'w')
    print >>fxml, prologue(hubid, runtype, rundesc)
    for x in doms:
        string  = int(x[3][0:2])
        module  = int(x[3][3:5])
        if x[1][0] == 'U':
            ab = 'B'
        else:
            ab = 'A'
        # Figure out 1, 2, 3 run type from things like 4,5,6 or 101,102,103
        normalized_runtype = (((runtype-1) % 10) % 3) + 1
        print >>fxml, generateDOMConfiguration(
            hvpar, x[0], hubname,
            string, module, x[2],
            ab, normalized_runtype
            )
    print >>fxml, epilogue([ x[0] for x in doms ])
    fxml.close()
    
