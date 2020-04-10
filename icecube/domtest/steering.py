from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import range
from builtins import object
import sys
import string
from io import StringIO
import MySQLdb
import re

def indent(str):
    return string.join([ "  " + line for line in str.split("\n") ], "\n")
    
def emit_doms(doms, db, trigMode=2, atwd=0, mux=2, led=0, \
          intPulser=0, pulserRate=0, \
          pulserBrightness=4095, localCoinc=None, \
          commonHV=None, samples=(128, 128, 128, 128), \
                sampleSize=(2, 2, 2, 2), fadc=0, domname=None, \
                FBbrightness=None, FBwidth=None, FBmask=None, FBrate=None, \
                site=None, domhub=None, pair=None, spe=None, hvsetting=None):
    c = db.cursor()
    str = StringIO()
    print("<domConfiguration type='specific'>", file=str)
    for (domid, loc) in list(doms.items()):
        q = "SELECT atwd0_trigger_bias,atwd1_trigger_bias," + \
            "atwd0_ramp_rate,atwd1_ramp_rate," + \
            "atwd0_ramp_top,atwd1_ramp_top," + \
            "atwd_analog_ref,fe_pedestal," + \
            "fadc_ref,spe_disc,mpe_disc,hv1,hv2,hv3,hvmax,hvsetting,doms.name,lcmode,domhub,pair,hv0 " + \
            "FROM domtune,doms WHERE " + \
            "domtune.mbid='%s' AND doms.mbid=domtune.mbid;" % (domid)
        c.execute(q)
        r = c.fetchone()
        if r == None:
            print("WARNING: DOM %s not in testing database" % (domid), file=sys.stderr)
        else:
            print("  <dom domId='%s' name='%s' domhub='%s' card='%d' pair='%d' ab='%s'>" % \
                  ((domid, r[16]) + tuple(loc)), file=str)
            if (r[16] == domname):
              print("    <param name='NUM_SAMPLES' atwdChannel='0' value='0'/>", file=str)
              print("    <param name='SAMPLE_SIZE' atwdChannel='0' value='2'/>", file=str)
              print("    <param name='NUM_SAMPLES' atwdChannel='1' value='0'/>", file=str)
              print("    <param name='SAMPLE_SIZE' atwdChannel='1' value='2'/>", file=str)
              print("    <param name='NUM_SAMPLES' atwdChannel='2' value='0'/>", file=str)
              print("    <param name='SAMPLE_SIZE' atwdChannel='2' value='2'/>", file=str)
              print("    <param name='NUM_SAMPLES' atwdChannel='3' value='64'/>", file=str)
              print("    <param name='SAMPLE_SIZE' atwdChannel='3' value='2'/>", file=str)
              print("    <param name='NUM_FADC_SAMPLES' value='0'/>", file=str)
              print("    <param name='TRIG_MODE' value='3'/>", file=str)
              print("    <param name='ANALOG_MUX_SELECT' value='3'/>", file=str)
            else:
              for ch in range(4):
                print("    <param name='NUM_SAMPLES' atwdChannel='%d' value='%d'/>" % (ch, samples[ch]), file=str)
                print("    <param name='SAMPLE_SIZE' atwdChannel='%d' value='%d'/>" % (ch, sampleSize[ch]), file=str)
              print("    <param name='NUM_FADC_SAMPLES' value='%d'/>" % (fadc), file=str)
              print("    <param name='TRIG_MODE' value='%d'/>" % (trigMode), file=str)
#              print >>str, "    <param name='ANALOG_MUX_SELECT' value='%d'/>" % (mux)
            print("    <param name='ATWD_SELECT' value='%d'/>" % (atwd), file=str)
            print("    <param name='DAC_LED_BRIGHTNESS' value='%d'/>" % (led), file=str)
            if intPulser != 1:
                print("    <param name='FE_PULSER_STATE' value='0'/>", file=str)
            else:
                print("    <param name='FE_PULSER_STATE' value='1'/>", file=str)
            print("    <param name='DAC_INTERNAL_PULSER' value='%d'/>" % (intPulser), file=str)
            print("    <param name='FE_PULSER_RATE' value='%d'/>" % (pulserRate), file=str)
            print("    <param name='DAC_ATWD0_TRIGGER_BIAS' value='%d'/>" % (r[0]), file=str)
            print("    <param name='DAC_ATWD1_TRIGGER_BIAS' value='%d'/>" % (r[1]), file=str)
            print("    <param name='DAC_ATWD0_RAMP_RATE' value='%d'/>" % (r[2]), file=str)
            print("    <param name='DAC_ATWD1_RAMP_RATE' value='%d'/>" % (r[3]), file=str)
            print("    <param name='DAC_ATWD0_RAMP_TOP' value='%d'/>" % (r[4]), file=str)
            print("    <param name='DAC_ATWD1_RAMP_TOP' value='%d'/>" % (r[5]), file=str)
            print("    <param name='DAC_ATWD_ANALOG_REF' value='%d'/>" % (r[6]), file=str)
            print("    <param name='DAC_PMT_FE_PEDESTAL' value='%d'/>" % (r[7]), file=str)
            print("    <param name='DAC_FAST_ADC_REF' value='%d'/>" % (r[8]), file=str)
            if spe != None:
              if (re.search('(?<=DOM)', r[16])):
#                print " found a match for %s " % r[16]
                print("    <param name='DAC_SINGLE_SPE_THRESH' value='%d'/>" % (r[9]), file=str)
              else:
                print("    <param name='DAC_SINGLE_SPE_THRESH' value='%d'/>" % (spe), file=str)
	    else:
              print("    <param name='DAC_SINGLE_SPE_THRESH' value='%d'/>" % (r[9]), file=str)
            print("    <param name='DAC_MULTIPLE_SPE_THRESH' value='%d'/>" % (r[10]), file=str)
	    if (r[16] == domname):
              print("    <param name='PMT_HV_LIMIT' value='0'/>", file=str)
            else:
              if (r[14] < 2048):
                print("    <param name='PMT_HV_LIMIT' value='%d'/>" % (r[14]*2), file=str)
              else:
                print("    <param name='PMT_HV_LIMIT' value='4095'/>", file=str)

            voltage = 0
            if commonHV != None:
               voltage = commonHV
               if (r[14] < voltage):
                 voltage = 0
            else:
#               thishub = r[17]
#               thispair = r[18]		
#               icetophub1 = 'sps-ithub-cont01'
#               print >>str, "*%s* *%d*" % (thishub, thispair)
               if hvsetting != None:
                 if (re.search('(?<=DOM)', r[16])):
                   voltage = 0
                 elif ( hvsetting == 0):
                   voltage = r[20]
                 elif ( hvsetting == 1):
                   voltage = r[11]
                 elif ( hvsetting == 2 ):
                   voltage = r[12]
                 elif ( hvsetting == 3 ):
                   voltage = r[13]
                 elif ( hvsetting == 10 ):
                   voltage = r[13] + 0.7*(r[12]-r[13])
                 else:
                   print("the hvsetting for DOM %s is suspect %d" % (r[16], hvsetting))
                   voltage = 0
               else:
                 if (re.search('(?<=DOM)', r[16])):
                   voltage = 0
                 elif ( r[15] == 0 ):
                   voltage = r[20]
                 elif ( r[15] == 1 ): 
                   voltage = r[11]
                 elif ( r[15] == 2 ):
                   voltage = r[12]
                 elif ( r[15] == 3 ):
                   voltage = r[13]
                 else:
                   print("the voltage setting for DOM %s is suspect" % (r[16]))
                   voltage = 0

            if (r[14] < voltage):
              voltage = r[14]
            if (r[16] == domname):
              voltage = 0
#            print " dom= %s   " % (r[16])
#            print " dom= %s   voltage = %s  " % (r[16],voltage*2)
            print("    <param name='PMT_HV_DAC' value='%d'/>" % (voltage*2), file=str)

#            if commonHV != None:
#	      if (r[15] == domname):
#                print >>str, "    <param name='PMT_HV_DAC' value='0'/>"
#              else:
#               if (r[14] < commonHV*2):
#                print >>str, "    <param name='PMT_HV_DAC' value='0'/>"
#               else:
#                print >>str, "    <param name='PMT_HV_DAC' value='%d'/>" % (commonHV*2)
#            else:
#              if (r[15] == domname):
#                print >>str, "    <param name='PMT_HV_DAC' value='0'/>"
#              else:
#                if (r[14] < r[11]):
#                  print >>str, "    <param name='PMT_HV_DAC' value='%d'/>" % (r[14]*2)
#		else:
#                  if ((r[17]=="fathub1") & (r[18]=="0")):
#                    print >>str, "    <param name='PMT_HV_DAC' value='%d'/>" % (r[13]*2)
#                  elif ((r[17]=="fathub1") & (r[18]=="1")):
#                    print >>str, "    <param name='PMT_HV_DAC' value='%d'/>" % (r[12]*2)
#                  else:
#                    print >>str, "    <param name='PMT_HV_DAC' value='%d'/>" % (r[11]*2)

            if (r[16] == domname):
               print("    <param name='LOCAL_COIN_MODE' value='0'/>", file=str)
               print("    <param name='DAC_FL_REF' value='450'/>", file=str)
               print("    <param name='FB_ENABLE' value='1'/>", file=str)
               print("    <param name='FB_BRIGHTNESS' value='%d'/>" % (FBbrightness), file=str)
               print("    <param name='FB_WIDTH' value='%d'/>" % (FBwidth), file=str)
               print("    <param name='FB_DELAY' value='150'/>", file=str)
               print("    <param name='FB_LED_MASK' value='%d'/>" % (FBmask), file=str)
               print("    <param name='FB_RATE' value='%d'/>" % (FBrate), file=str)
            else:
	      print("    <param name='FB_ENABLE' value='0'/>", file=str)
              if localCoinc != None:
                print("    <param name='LOCAL_COIN_MODE' value='%d'/>" %(r[17]), file=str)
	      else:
                print("    <param name='LOCAL_COIN_MODE' value='0'/>", file=str)

              if ((r[17]>0) & (localCoinc != None)):
                print("    <param name='LOCAL_COIN_WIN_UP_PRE' value='0'/>", file=str)
                print("    <param name='LOCAL_COIN_WIN_UP_POST' value='%d'/>" % (localCoinc), file=str)
                print("    <param name='LOCAL_COIN_WIN_DOWN_PRE' value='0'/>", file=str)
                print("    <param name='LOCAL_COIN_WIN_DOWN_POST' value='%d'/>" % (localCoinc), file=str)
#	       else:
#                print >>str, "    <param name='LOCAL_COIN_MODE' value='0'/>"

            print("  </dom>", file=str)


            
    return str.getvalue() + "</domConfiguration>"

class SteeringDeck(object):

    def __init__(self, dbhost='localhost'):
        self.db = MySQLdb.connect(user='penguin', db='fat', host=dbhost)
        self.str = StringIO()
        print("<?xml version='1.0'?>", file=self.str)
        print("""<!--
        This file was autogenerated by the Python module
            icecube.domtest.steering
            $Id: steering.py,v 1.15 2005/11/22 23:14:49 krasberg Exp $
        -->""", file=self.str)
        print("<DOM_Test_Configuration>", file=self.str)

    def addTest(self,
                testName,
                doms,
                executionTime=120,
                samples=(128, 128, 128, 128),
                sampleSize=(2, 2, 2, 2),
                fadc=0,
                hwInterval=2,
                confInterval=60,
                pulserMode=0,
                pulserFreq=1000,
                filterWheel=1,
                monochromatorWavelen=0,
                trigMode=2,
                atwd=0,
                mux=2,
                led=0,
                intPulser=0,
                pulserRate=0,
                pulserBrightness=None,
                commonHV=None,
		localCoinc=None,
		domname=None,
                FBbrightness=None,
                FBwidth=None,
                FBmask=None,
                FBrate=None,
		site=None,
		spe=None,
		hvsetting=None,
                ):

        str = StringIO()
        print("<test>", file=str)
        print("  <testName name='%s'/>" % (testName), file=str)
        print("  <executionTime value='%d'/>" % (executionTime), file=str)
#        for ch in range(4):
#            print >>str, "  <param name='NUM_SAMPLES' atwdChannel='%d' value='%d'/>" % (ch, samples[ch])
#            print >>str, "  <param name='SAMPLE_SIZE' atwdChannel='%d' value='%d'/>" % (ch, sampleSize[ch])
#        print >>str, "  <param name='NUM_FADC_SAMPLES' value='%d'/>" % (fadc)
        print("  <param name='HW_INTERVAL' value='%d'/>" %   (hwInterval), file=str)
        print("  <param name='CONF_INTERVAL' value='%d'/>" % (confInterval), file=str)
        if ((site == "FAT") | (site=="SPTS")):
          print("  <param name='PULSER_MODE' value='%d'/>" % (pulserMode), file=str)
          print("  <param name='PULSER_FREQUENCY' value='%d'/>" % (pulserFreq), file=str)
	  if pulserBrightness != None:
             print("  <param name='PULSER_BRIGHTNESS' value='%d'/>" % (pulserBrightness), file=str)

	if (site == "FAT"):
          print("  <param name='WHEEL_POSITION' value='%d'/>" % (filterWheel), file=str)
          print("  <param name='MONOCHROMATOR_WAVELENGTH' value='%d'/>" % (monochromatorWavelen), file=str)

        print(indent(emit_doms(doms, self.db, trigMode=trigMode, atwd=atwd,
                                      mux=mux, led=led, intPulser=intPulser,
                                      pulserRate=pulserRate,
				      pulserBrightness=pulserBrightness,
				      localCoinc=localCoinc,
                                      commonHV=commonHV,
                                      samples=samples,
                                      sampleSize=sampleSize,
                                      fadc=fadc,
                                      domname=domname,
                                      FBbrightness=FBbrightness,
                 		      FBwidth=FBwidth,
		                      FBmask=FBmask,
                 		      FBrate=FBrate,
				      site=site,
				      spe=spe,
				      hvsetting=hvsetting,
					)), file=str)
        print(indent(str.getvalue()) + "</test>", file=self.str)
        
    def __str__(self):
        return self.str.getvalue() + "</DOM_Test_Configuration>"
