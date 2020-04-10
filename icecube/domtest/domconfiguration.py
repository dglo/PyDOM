#!/usr/bin/env python
"""
DOM Configuration module

$Id: domconfiguration.py,v 1.7 2006/06/16 15:06:19 bvoigt Exp $
"""
from __future__ import print_function
from __future__ import absolute_import

####################################################
# Import section                                   #
####################################################

from builtins import str
from builtins import range
from builtins import object
import sys
import math
import warnings
from . import databaseutil
import time

####################################################
# Definition of constants                          #
####################################################

# Channel numbers for DOM Mainboard DACs and ADCs
# taken from the DOM User's Guide
DOMCONFIGURATION_ATWD0_TRIGGER_BIAS_DAC = 0
DOMCONFIGURATION_ATWD0_RAMP_TOP_DAC = 1     
DOMCONFIGURATION_ATWD0_RAMP_RATE_DAC = 2
DOMCONFIGURATION_ATWD_ANALOG_RATE_DAC = 3   
DOMCONFIGURATION_ATWD1_TRIGGER_BIAS_DAC = 4
DOMCONFIGURATION_ATWD1_RAMP_TOP_DAC = 5    
DOMCONFIGURATION_ATWD1_RAMP_RATE_DAC = 6
DOMCONFIGURATION_PMT_FE_PEDESTAL_DAC = 7        
DOMCONFIGURATION_MPE_DISC_DAC = 8
DOMCONFIGURATION_SPE_DISC_DAC = 9          
DOMCONFIGURATION_FADC_REF_DAC = 10
DOMCONFIGURATION_INTERNAL_PULSER_DAC = 11
DOMCONFIGURATION_LED_BRIGHTNESS_DAC = 12
DOMCONFIGURATION_FE_AMP_LOWER_CLAMP_DAC = 13

# Default DAC settings
DOMCONFIGURATION_ATWD0_TRIGGER_BIAS = 850
DOMCONFIGURATION_ATWD0_RAMP_TOP = 2300
DOMCONFIGURATION_ATWD0_RAMP_RATE = 350
DOMCONFIGURATION_ATWD_ANALOG_RATE = 2250
DOMCONFIGURATION_ATWD1_TRIGGER_BIAS = 850
DOMCONFIGURATION_ATWD1_RAMP_TOP = 2300   
DOMCONFIGURATION_ATWD1_RAMP_RATE = 350
DOMCONFIGURATION_PMT_FE_PEDESTAL = 2130        
DOMCONFIGURATION_MPE_DISC = 650
DOMCONFIGURATION_SPE_DISC = 565         
DOMCONFIGURATION_FADC_REF = 800
DOMCONFIGURATION_INTERNAL_PULSER = 0
DOMCONFIGURATION_LED_BRIGHTNESS = 0
DOMCONFIGURATION_FE_AMP_LOWER_CLAMP = 800

# default HV in Volts
DOMCONFIGURATION_HV = 1500

# default maximum HV in Volts
DOMCONFIGURATION_MAXIMUM_HV = 2047

# Local Coincident configurations
DOMCONFIGURATION_LC_MODE_NO_NEIGHBOR = 0 # A DOM has no lc connections
DOMCONFIGURATION_LC_MODE_BOTH_NEIGHBORS= 1 # normal mode the DOM has both lc connections
DOMCONFIGURATION_LC_MODE_NO_BOTTOM_NEIGHBOR = 2 # DOM has only a lc connection to the top
DOMCONFIGURATION_LC_MODE_NO_TOP_NEIGHBOR = 3 # DOM has only a lc connection to the bottom

# DOM Types
DOMCONFIGURATION_TYPE_UNSPECIFIC = 0 # DOMs not qualified for one of the following types
DOMCONFIGURATION_TYPE_IN_ICE = 1
DOMCONFIGURATION_TYPE_ICE_TOP = 2

###################################################
# Module Method section                           #
# Definition of methods that are not related to   #
# classes of this module                          #
###################################################

def getDefaultDACSettings():
    """
    Returns a list of all default DAC settings ordered by the DAC number
    The default values are defined in the domconfiguration module
    """
    settings = []
    for i in range(16):
        settings.insert(i, getDefaultDACSetting(i))

    return settings
#end getDefaultDACSettings

def getDefaultDACSetting(channel):
    """
    Returns the default setting for the DAC specified by channel.
    """

    if channel == DOMCONFIGURATION_ATWD0_TRIGGER_BIAS_DAC:
        return DOMCONFIGURATION_ATWD0_TRIGGER_BIAS
    elif channel == DOMCONFIGURATION_ATWD0_RAMP_TOP_DAC:
        return DOMCONFIGURATION_ATWD0_RAMP_TOP
    elif channel == DOMCONFIGURATION_ATWD0_RAMP_RATE_DAC:
        return DOMCONFIGURATION_ATWD0_RAMP_RATE
    elif channel == DOMCONFIGURATION_ATWD_ANALOG_RATE_DAC:
        return DOMCONFIGURATION_ATWD_ANALOG_RATE
    elif channel == DOMCONFIGURATION_ATWD1_TRIGGER_BIAS_DAC:
        return DOMCONFIGURATION_ATWD1_TRIGGER_BIAS
    elif channel == DOMCONFIGURATION_ATWD1_RAMP_TOP_DAC:
        return DOMCONFIGURATION_ATWD1_RAMP_TOP
    elif channel == DOMCONFIGURATION_ATWD1_RAMP_RATE_DAC:
        return DOMCONFIGURATION_ATWD1_RAMP_RATE
    elif channel == DOMCONFIGURATION_PMT_FE_PEDESTAL_DAC:
        return DOMCONFIGURATION_PMT_FE_PEDESTAL
    elif channel == DOMCONFIGURATION_MPE_DISC_DAC:
        return DOMCONFIGURATION_MPE_DISC
    elif channel == DOMCONFIGURATION_SPE_DISC_DAC:
        return DOMCONFIGURATION_SPE_DISC
    elif channel == DOMCONFIGURATION_FADC_REF_DAC:
        return DOMCONFIGURATION_FADC_REF
    elif channel == DOMCONFIGURATION_INTERNAL_PULSER_DAC:
        return DOMCONFIGURATION_INTERNAL_PULSER
    elif channel == DOMCONFIGURATION_LED_BRIGHTNESS_DAC:
        return DOMCONFIGURATION_LED_BRIGHTNESS
    elif channel == DOMCONFIGURATION_FE_AMP_LOWER_CLAMP_DAC:
        return DOMCONFIGURATION_FE_AMP_LOWER_CLAMP
    elif channel == 14 or channel == 15:
        # these DACS are not used at the moment, just return 0 without notification
        return 0
    else:
        # raise a warning that the value is set to zero
        warnings.warn("Warning: No default value defined for DAC #%d. Set to 0" % channel)
        return 0
#end getDefaultDACSetting

def getDefaultHV():
    """
    Returns the default HV setting in Volts.
    The default value is defined in this module
    """
    return DOMCONFIGURATION_HV
#end getDefaultHV

###################################################
# Class definition section                        #
###################################################

class DOMConfigurator(object):

    """
    Digitial Optical Module configuration

    This class provides methods to get the DOM configuration from the
    domprodtest datebase. The configuration includes the DAC settings, the HV setting
    for a particular gain and various additional parameters used during a
    Final Accept Test.
    The configuration and calibration entries in the database are date stamped. This class
    only fetches the latest settings from the tables.

    A DOM is identified by a mainboard id. The relation between the mainboard and the DOM
    housing this particular mainboard is stored in the database.

    Usage:
    mbid = '1234567890abcdefg'
    db = MySQLdb(user=user,host=host,db=db)
    conf = DOMConfigurator(db,mbid)
    print conf.getName()
    print conf.getSerialNumber()
    print conf.getDACSettings(20) # DAC settings for temperature 20 C
    """

    verbose = 0
    veryverbose = 0

    # serial number of the DOM
    serialNumber = None
    
    def __init__(self, db, mainboardId):
        """
        DOM configuration constructor

        Requires a database conncection to the domprodtest database
        A mainboard id specifies the DOM the configuration is related to
        Throws a DOMConfigurationExceptoin if no related DOM can be found in the database
        """
        self.db = db
        self.cursor = db.cursor()
        self.mainboardId = mainboardId

        # fetch the product id related to the DOM which houses the given mainboard
        # in order to avoid multiple product ids select the information from the
        # latest assembly (the one with the largest assem_id) and limit the result to 1
        sql = """
              SELECT p1.prod_id
              FROM Product p1
              INNER JOIN Assembly a ON a.prod_id = p1.prod_id
              INNER JOIN AssemblyProduct ap ON ap.assem_id = a.assem_id
              INNER JOIN Product p2 ON p2.prod_id = ap.prod_id
              WHERE p2.hardware_serial = %s
              ORDER BY a.datetime DESC, a.assem_id DESC
              LIMIT 1;
              """
        if not (self.cursor.execute(sql, (self.mainboardId))):
            # no related DOM found in the database
            raise DOMConfigurationException(\
                self,\
                "Couldn't find a DOM which is related to the given mainboard id %s" % self.mainboardId)
            
        self.prodId = (self.cursor.fetchone())[0]

        # All data attributes which may be set with setter function
        # and then stored by the save function (definitions of the function below)
        self.domhubName = ''
        self.dorCard = ''
        self.wirePair = ''
        self.wirePairPosition = ''
        self.quadCableNumber = ''
        self.localCoincidenceMode = ''
        self.maxHV = ''
    # end __init__

    def getProductId(self):
        """Returns the id of the database entry in the Product table of this DOM"""
        return self.prodId
    # end getProductId
    
    def getMainboardId(self):
        """
        Returns the mainboard id of the DOM
        """
        return self.mainboardId
    # end getMainboardId
    
    def getSerialNumber(self):
        """
        Returns the DOM serial number
        Throws a DOMConfigurationException if no serial number can be found
        """
        if self.serialNumber is None:
            sql = """
                  SELECT tag_serial
                  FROM Product
                  WHERE prod_id = %s;
                  """
            if not self.cursor.execute(sql, (self.prodId)):
                # no related product found in the database
                raise DOMConfigurationException(\
                      self,\
                      "Couldn't find the serial for the given product id %s" % self.prodId)
        
            return (self.cursor.fetchone())[0]
        else:
            return self.serialNumber
    # end getSerialNumber
        
    def getName(self):
        """
        Returns the name of of the DOM
        Throws a DOMConfigurationException if no name can be found
        """
        sql = """
              SELECT name
              FROM ProductName
              WHERE prod_id = %s;
              """
        if not self.cursor.execute(sql, (self.prodId)):
            # return the DOM serial number
            return self.getSerialNumber()

        return (self.cursor.fetchone())[0]
    # end getName

    def getDACSettings(self,temp=None):
        """
        Returns an array with the latest DAC setting for the given temperature temp
        If temp is not set, the latest DAC settings are returned without respect to the
        temperature.
        The DAC settings are perviously computed by the DOMCal application.
        Throws a DOMConfigurationException if no DOMCalibration results can found.
        """

        # if a temperature is given try at first
        # to figure out which calibration set is the best for the given temp
        if isinstance(temp, int) \
        or isinstance(temp, int) \
        or isinstance(temp, float):

            sql = """
                  SELECT
                  dd.channel,
                  dd.value,
                  d.date,
                  d.temperature,
                  ABS(d.temperature - %s) as tempDifference
                  FROM DOMCal_DAC dd
                  INNER JOIN DOMCalibration d ON dd.domcal_id = d.domcal_id
                  WHERE d.prod_id = %s
                  ORDER BY d.date DESC, tempDifference ASC, dd.channel
                  LIMIT 0,16;
                  """
            if not self.cursor.execute(sql % (temp, self.prodId)): 
                # no related DOM found in the database
                raise DOMConfigurationException(\
                    self,\
                    "Couldn't find DOMCalibartion results for DOM %s" % self.getSerialNumber())
            
        else:
            sql = """
                  SELECT
                  dd.channel,
                  dd.value,
                  d.date,
                  d.temperature
                  FROM DOMCal_DAC dd
                  INNER JOIN DOMCalibration d ON dd.domcal_id = d.domcal_id
                  WHERE d.prod_id = %s
                  ORDER BY d.date DESC, dd.channel
                  LIMIT 0,16;
                  """
            if not self.cursor.execute(sql % self.prodId): 
                # no related DOM found in the database
                raise DOMConfigurationException(\
                    self,\
                    "Couldn't find DOMCalibartion results fpr DOM %s" % self.getSerialNumber())

        result = self.cursor.fetchall()

        if self.verbose:
            print("%s: DAC settings taken from DOMCal run on %s at %.2f C" \
                  % (self.getSerialNumber(), result[0][2], result[0][3]), file=sys.stdout)
        if self.veryverbose:
            print("DAC settings are: ", file=sys.stdout)
            for row in result:
                print("Channel %d: %d" % (row[0], row[1]), file=sys.stdout)
            
        settings = []
        for row in result:
            if row[1] == 0:
                settings.insert(row[0], getDefaultDACSetting(row[0]))
            else:
                settings.insert(int(row[0]), int(row[1]))
        return settings
    # end getDACSettings
                            
    def getHV(self, temp=None, gain=1e7):
        """
        Returns the HV in Volts (as integer) for the given temperature temp and
        the given amplification gain.
        The HV is computed from the latest calibration results from the DOMCal application.
        If no gain is given, the usual working point of 1e7 is used.
        If no temperature is given, the latest calibration is used
        without respect to the temperature.
        Throws a DOMConfigurationException if no DOMCalibration results can be found.
        """

        # if a temperature is given try at first
        # to figure out which calibration set is the best for the given temp
        if isinstance(temp, int) \
        or isinstance(temp, int) \
        or isinstance(temp, float):

            sql = """
                  SELECT
                  dhv.intercept,
                  dhv.slope,
                  d.date,
                  d.temperature,
                  ABS(d.temperature - %s) as tempDifference
                  FROM DOMCal_HvGain dhv
                  INNER JOIN DOMCalibration d ON dhv.domcal_id = d.domcal_id
                  WHERE d.prod_id = %s
                  ORDER BY d.date DESC, tempDifference ASC
                  LIMIT 1;
                  """
            if not self.cursor.execute(sql % (temp, self.prodId)): 
                # no related DOM found in the database
                raise DOMConfigurationException(self,\
                      "Couldn't find DOMCalibartion results for DOM %s"\
                      % self.getSerialNumber())

        else:
            sql = """
                  SELECT
                  dhv.intercept,
                  dhv.slope,
                  d.date,
                  d.temperature
                  FROM DOMCal_HvGain dhv
                  INNER JOIN DOMCalibration d ON dhv.domcal_id = d.domcal_id
                  WHERE d.prod_id = %s
                  ORDER BY d.date DESC
                  LIMIT 1;
                  """
            if not self.cursor.execute(sql % self.prodId): 
                # no related DOM found in the database
                raise DOMConfigurationException(self,\
                      "Couldn't find DOMCalibartion results for DOM %s"\
                      % self.getSerialNumber())

        result = self.cursor.fetchone()
        intercept = result[0]
        slope = result[1]

        if self.verbose:
            print(("%s: HV calibration settings taken from " + \
                  "DOMCal run on %s at %.2f C") \
                  % (self.getSerialNumber(), result[2], result[3]), file=sys.stdout)

        # DOMCal calculates the function log(gain) = intercept + slope * log(hv[V])
        # to get the HV in Volts the function has to be inverted and the result has
        # to be taken as the power of 10 i.e. hv[V] = 10^((log(gain) - intercept)/slope)
        return int(round(math.pow(10, ( (math.log10(gain)-intercept) / slope ))))
    #end getHV

    def getConfigurationDates(self):
        """Returns a list of dates of configurations stored in the database related to this DOM"""

        sql= """
             SELECT
             date
             FROM FAT_DOM_Configuration
             WHERE prod_id = %s
             ORDER BY date DESC;
             """
        if not self.cursor.execute(sql % self.prodId):
            #no related DOM configuration found in the database
            raise DOMConfigurationException(self,\
                                            "Couldn't find configuraiton for DOM %s"\
                                            % self.getSerialNumber())
        return self.cursor.fetchAll()
    #end getConfigurationDates
        
    def getDOMHubName(self):
        """Returns the name of the host to which the DOM is connected"""

        sql = """
              SELECT
              fc.domhub
              FROM FAT_Connection fc
              INNER JOIN FAT_DOM_Configuration fdc ON fdc.fat_connection_id=fc.fat_connection_id
              WHERE fdc.prod_id = %s
              ORDER BY date DESC
              LIMIT 1;
              """
        if not self.cursor.execute(sql % self.prodId): 
            # no related DOM configuration found in the database
            raise DOMConfigurationException(self,\
                                            "Couldn't find configuration for DOM %s"\
                                            % self.getSerialNumber())

        return (self.cursor.fetchone())[0]
    #end getDomHubName

    def getDORCard(self):
        """Returns the DOR Card (int number) to which the DOM is connected"""
        sql = """
              SELECT
              fc.dor
              FROM FAT_Connection fc
              INNER JOIN FAT_DOM_Configuration fdc ON fdc.fat_connection_id=fc.fat_connection_id
              WHERE fdc.prod_id = %s
              ORDER BY date DESC
              LIMIT 1;
              """
        if not self.cursor.execute(sql % self.prodId): 
            # no related DOM configuration found in the database
            raise DOMConfigurationException(self,\
                                            "Couldn't find configuration for DOM %s"\
                                            % self.getSerialNumber())

        return (self.cursor.fetchone())[0]
    #end getDorCard

    def getWirePair(self):
        """Returns the number of the wire pair to which the DOM is connected"""

        sql = """
              SELECT
              fc.wire
              FROM FAT_Connection fc
              INNER JOIN FAT_DOM_Configuration fdc ON fdc.fat_connection_id=fc.fat_connection_id
              WHERE fdc.prod_id = %s
              ORDER BY date DESC
              LIMIT 1;
              """
        if not self.cursor.execute(sql % self.prodId): 
            # no related DOM configuration found in the database
            raise DOMConfigurationException(self,\
                                            "Couldn't find configuration for DOM %s"\
                                            % self.getSerialNumber())

        return (self.cursor.fetchone())[0]
    #end getWirePair

    def getWirePairPosition(self):
        """Returns the position of the DOM on the wire pair, this is 'A' or 'B'"""

        sql = """
              SELECT
              fc.wire_position
              FROM FAT_Connection fc
              INNER JOIN FAT_DOM_Configuration fdc ON fdc.fat_connection_id=fc.fat_connection_id
              WHERE fdc.prod_id = %s
              ORDER BY date DESC
              LIMIT 1;
              """
        if not self.cursor.execute(sql % self.prodId): 
            # no related DOM configuration found in the database
            raise DOMConfigurationException(self,\
                                            "Couldn't find configuration for DOM %s"\
                                            % self.getSerialNumber())

        return (self.cursor.fetchone())[0]
    #end getWirePairPosition

    def getConnectionIdentifier(self):
        """
        Returns a string concatenation of the form:
        DOMhub.DOR-CardWire-PairWire-Pair-Position
        """

        return self.getDOMHubName() + self.getDORCard() \
               + self.getWirePair() + self.getWirePairType()
    #end getConnectionIdentifier

    def getQuadCableNumber(self):
        """
        Returns the quad cable number to which the DOM is connected to.
        This information is not related to the DOR - DOM connection, it is only
        a matter of cable labeling. Cable may be changed and therefor, it can be
        important to have the cable labeled.
        """

        sql = """
              SELECT
              fc.quad
              FROM FAT_Connection fc
              INNER JOIN FAT_DOM_Configuration fdc ON fdc.fat_connection_id=fc.fat_connection_id
              WHERE fdc.prod_id = %s
              ORDER BY date DESC
              LIMIT 1;
              """
        if not self.cursor.execute(sql % self.prodId): 
            # no related DOM configuration found in the database
            raise DOMConfigurationException(self,\
                                            "Couldn't find configuration for DOM %s"\
                                            % self.getSerialNumber())

        return (self.cursor.fetchone())[0]
    #end getQuadCableNumber

    def getLCMode(self):
        """
        Returns the local coincidence configuration of this DOM.
        A DOM may have both neighbor connections, only one (top or bottom neighbor)
        or no neighbor connection at all.
        An integer constant is returned. The values are defined in domconfiguration.py
        """

        # the enumeration field can be used with indexing, but remember that
        # the index starts at 1, 0 means no entry.
        # Since the constants are defined starting with zero, the index of the enumeration
        # field is decreased by one, except no value is present, than 0 is returned
        sql = """
              SELECT
              IF(lc_mode=0, 0, lc_mode-1)
              FROM FAT_DOM_Configuration
              WHERE prod_id = %s
              ORDER BY date DESC
              LIMIT 1;
              """
        if not self.cursor.execute(sql % self.prodId): 
            # no related DOM configuration found in the database
            raise DOMConfigurationException(self,\
                                            "Couldn't find configuration for DOM %s"\
                                            % self.getSerialNumber())
        return int(self.cursor.fetchone()[0])
    #end getLCMode

    def getMaximumHV(self):
        """Returns the maximum HV to which the DOM can be set"""

        sql = """
              SELECT
              max_hv
              FROM FAT_DOM_Configuration
              WHERE prod_id = %s
              ORDER BY date DESC
              LIMIT 1;
              """
        if not self.cursor.execute(sql % self.prodId): 
            # no related DOM configuration found in the database
            raise DOMConfigurationException(self,\
                                            "Couldn't find configuration for DOM %s"\
                                            % self.getSerialNumber())

        return (self.cursor.fetchone())[0]
    #end getMaximumHV

#end class DOMConfigurator

class DOMConfigurationException(Exception):
    """
    Exception class for any error that occurs during the DOM configuration.
    Typically these errors are raised, if a configuration item could not be found
    in the database
    """

    def __init__(self, object, message=''):
        """
        Creates a DOMConfigurationException
        and set the exception message (string)
        """
        self.message = object.__class__.__name__ + ": "
        self.message += message

    def setMessage(self, message):
        """
        Sets the excpetion message
        """
        self.message += message

    def getMessage(self):
        """
        Returns the exception message (string)
        """
        return str(self.message)
#end class DOMConfigurationException
