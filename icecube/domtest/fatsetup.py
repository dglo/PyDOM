"""
This module provides functions for the fat setup.

It is used together with the domconfiguration module by the fatsetup script.
See the methods' documentation for details about the functionality.

Author: Bernhard Voigt <bernhard.voigt@desy.de>
"""
from __future__ import print_function

from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import warnings
import time
from icecube.domtest.domconfiguration import *
import icecube.domtest.databaseutil as databaseutil
from xmlrpc.client import ServerProxy

class DOM(object):
    """
    Simple representation of a DOM and the different configuration
    attributes.

    These are:
    prodId - product id of the DOM
    serialNumber - serial number of the DOM
    name - name of the DOM
    nameExplanation - explanation for the name
    nameTheme - the theme the name belongs to
    localCoincidenceMode - integer number defined in domconfiguration module
    maxHV - integer specifying the maximum HV setting for this DOM
    domhub - string the name of the domhub to which the DOM is connected
    dorCard - integer the DOR Card to which the DOM is connected
    wirePair - see above
    wirePosition - A or B
    stationId - the id of the station the DOM sits on
    """

    def __init__(self, prodId, serialNumber, name, nameExplanation, nameTheme):

        self.prodId = prodId
        self.serialNumber = serialNumber
        if not name:
            name=''
        self.name = name
        if not nameExplanation:
            nameExplanation = ''
        self.nameExplanation = nameExplanation
        if not nameTheme:
            nameTheme=''
        self.nameTheme = nameTheme
        self.domhub = None
        self.dorCard = None
        self.wirePair = None
        self.wirePosition = None
        self.localCoincidenceMode = None
        self.maxHV = None
        self.stationId = None


    def __eq__(self, dom):
        """
        Two instances of a DOM object are considered equal, if their prodIds are equal
        """
        return self.prodId == dom.prodId

    def __ne__(self, dom):
        """
        Two instances of a DOM object are considered unequal, if their prodIds are unequal
        """
        return self.prodId != dom.prodId

    def __lt__(self, dom):
        """
        This DOM is less than dom, when it appears earlier on the connection list.
        This is determined by the connection identifiers. The domhub name is sorted alphabetically,
        the cards from 0-7, the wire from 0-3 and the wire postion is B before A.
        """
        if self.domhub < dom.domhub:
            return True
        elif self.domhub == dom.domhub:
            if self.dorCard < dom.dorCard:
                return True
            elif self.dorCard == dom.dorCard:
                if self.wirePair < dom.wirePair:
                    return True
                elif self.wirePair == self.wirePair:
                    # wirePosition is A or B, unfortunately the order is reversed, B is a top
                    # DOM and therefore earlier in the LC chain, ie, the DOM is 'smaller'
                    if self.wirePosition > dom.wirePosition:
                        return True

        return False

    def __gt__(self, dom):
        """
        This DOM is greater than dom, when it appears later on the connection list.
        This is determined by the connection identifiers. The domhub name is sorted alphabetically,
        the cards from 0-7, the wire from 0-3 and the wire postion is B before A.

        """
        if self.domhub > dom.domhub:
            return True
        elif self.domhub == dom.domhub:
            if self.dorCard > dom.dorCard:
                return True
            elif self.dorCard == dom.dorCard:
                if self.wirePair > dom.wirePair:
                    return True
                elif self.wirePair == self.wirePair:
                    # wirePosition is A or B, unfortunately the order is reversed, A is a bottom
                    # DOM and therefore later in the LC chain, ie, the DOM is 'bigger'
                    if self.wirePosition < dom.wirePosition:
                        return True

        return False

    def __str__(self):
        """
        Returns a string represantation of this DOM object
        """
        str = "Product-Id: %s, DOM-Serial: %s, DOM-Name: %s, DOMHub: %s, " % \
        (self.prodId, self.serialNumber, self.name, self.domhub)
        str += "DORCard: %s, WirePair: %s, Position: %s, " % \
        (self.dorCard, self.wirePair, self.wirePosition)
        str += "LCMode: %s, Max-HV: %s, Station-Id: %s" % \
        (self.localCoincidenceMode, self.maxHV, self.stationId)
        return str


def createDOMs(db, domIdentifiers):
    """
    Creates DOM objects from the list of domIdentifiers.
    Looks up the existing DOMs in the database and fetches those which correspond to the list of identifiers

    domIdentifieres is a list of either DOM serial numbers or names
    returns a list of DOM objects
    """

    cursor = db.cursor()
    doms = []

    for identifier in domIdentifiers:
        sql = """
              SELECT p.prod_id, p.tag_serial, pn.name, pn.explanation, pn.theme FROM Product p
              LEFT JOIN ProductName pn USING (prod_id)
              WHERE pn.name = %s OR p.tag_serial = %s
              LIMIT 1;
              """

        if not cursor.execute(sql, (identifier, identifier)):
            warnings.warn("Cannot find a DOM in the database matching the given identifier %s" % identifier)

        result = cursor.fetchone()
        dom = DOM(result[0], result[1], result[2], result[3], result[4])

        # get the current configuration from the database
        # this step needs the mainboard id
        sql = """
              SELECT p.hardware_serial FROM Product p
              INNER JOIN AssemblyProduct USING (prod_id)
              INNER JOIN Assembly a USING (assem_id)
              INNER JOIN Product p2 USING (prod_id)
              WHERE p2.prod_id = %s and p.prodtype_id=5
              ORDER BY a.datetime DESC, a.assem_id DESC
              LIMIT 1
              """
        # hagar: previously this order was
        # ORDER BY a.datetime DESC LIMIT 1

        cursor.execute(sql, result[0])
        mainboardId = cursor.fetchone()[0]

        # try to get an existing configuration
        # if there is none or it can't be read
        # there is no exception handling since
        # the information is not needed
        try:
            conf = DOMConfigurator(db, mainboardId)
        except:
            pass
        try:
            dom.domhub = conf.getDOMHubName()
        except:
            pass
        try:
            dom.dorCard = conf.getDORCard()
        except:
            pass
        try:
            dom.wirePair = conf.getWirePair()
        except:
            pass
        try:
            dom.wirePosition = conf.getWirePairPosition()
        except:
            pass
        try:
            dom.localCoincidenceMode = conf.getLCMode()
        except:
            pass
        try:
            dom.maxHV = conf.getMaximumHV()
        except:
            pass
        try:
            dom.stationId = getStationForDOM(db, dom)
        except:
            pass

        doms.append(dom)

    doms.sort()
    return doms
    
def scanHubs(db, domhubList):
    """
    Scan the given list of domhubs for connected DOMs.

    The DOMs are returned as a sorted list, where the connection
    information defines the sort order. Starting with the DOMs on the
    first hub (alphabetical order), continuing with dor, wire and pair position
    where the number order is used and the pair position is reversed B, before A.
    This is probably the order of the local coincidence chain in the DFL freezer.

    Parameters:
    db - database connection object
    domhubList - a list of domhub names (hostnames which the machine can resolv)

    Return:
    a list of DOM objects
    """

    domhubList.sort()
    for domhub in domhubList:
        # open a rpc connection to the dor drivers
        dorDriver = ServerProxy("http://" + domhub + ":7501")
        dorDriver.scan()
        mainboardAndConnection = dorDriver.discover_doms() # discores the mainboards connected to the hub

        # the list of DOMs that will be returned
        doms = []
        
        for mbId, (dorCard, wirePair, wirePosition) in mainboardAndConnection.items():
            try:
                # use the functions provided by the DOMConfigruator class to get the DOM that integrates the mainboard
                conf = DOMConfigurator(db, mbId)
            except DOMConfigurationException as e:
                # there is no DOM related to the mainboard
                # the function findDOM tries to figure out whether the is a misrelated mainboard
                # that has a typo in the serial number.  Also, the user can enter the DOM Serial number
                # to specify the correct DOM-Mainboard relation
                #prodId = findDOMForOrphanMainboard(mbId)
                #conf = DOMConfigurator(db, mbId)
                print("""Can't find a DOM that contains the mainboard %s
                it is supposed to be on dor %i, pair %i and DOM %s""" % (mbId, dorCard, wirePair, wirePosition))

            prodId = conf.getProductId()
            serialNumber = conf.getSerialNumber()
            # create the DOM from the database information
            dom = createDOMs(db, (serialNumber,))[0]
            # now set the configuration parameters found during scanning
            dom.domhub = domhub
            dom.dorCard = dorCard
            dom.wirePair = wirePair
            dom.wirePosition = wirePosition
            doms.append(dom)

    doms.sort()
    return doms
# end def scanHubs


def autoFatSetup (db, doms, labName):
    """
    Determines the stations the DOMs sits on from the connection defined in the DOM objects

    Sets the station of the DOM objects

    Parameter:
    db - database connection object
    doms - list of DOM Objects
    labName - string
    """
    
    for dom in doms:
        # get the station
        dom.stationId = getStationFromConnection(db, labName, dom.domhub, dom.dorCard,
                                                 dom.wirePair, dom.wirePosition)
# end def autoFatSetup


def getStationFromConnection(db, labName, domhub, dorCard, wirePair, wirePosition):
    """
    Returns the station id of the station the given connection is related to
    A connection is identified by the lab name, domhub, dor card, wire and wire pair (FAT_Connection table)

    db database connection object
    labName string name of the Lab
    domhub string name of the domhub
    card int card number
    wire int wire number
    wirePosition char A or B
    return int fat station id
    """

    cursor = db.cursor()
    # select the latest station to connection relation for the specified connection
    sql = """
          SELECT fs.fat_station_id FROM FAT_Station fs
          INNER JOIN FAT_StationConnection fsc ON fsc.fat_station_id=fs.fat_station_id
          INNER JOIN FAT_Connection fc ON fc.fat_connection_id=fsc.fat_connection_id
          INNER JOIN Laboratory l ON l.lab_id=fc.lab_id
          WHERE l.name=%s AND
          fc.domhub=%s AND
          fc.dor=%s AND
          fc.wire=%s AND
          fc.wire_position=%s
          ORDER BY fsc.date DESC
          LIMIT 1
          """
    if (cursor.execute(sql, (labName, domhub, dorCard, wirePair, wirePosition))):
        return cursor.fetchone()[0]
    else:
        return None

# end getStationFromConnection

def getConnectionId(db, labName, domhub, dorCard, wirePair, wirePosition, breakoutbox=None, breakoutboxConnector=None):
    """
    Returns the fat_connection_id of the connection defined by the given parameters
    """

    cursor = db.cursor()

    sql = """
          SELECT fat_connection_id FROM FAT_Connection
          INNER JOIN Laboratory l USING (lab_id)
          WHERE l.name=%s AND
          domhub=%s AND
          dor=%s AND
          wire=%s AND
          wire_position=%s
          """
    if breakoutbox is not None and breakoutboxConnector is not None:
        sql += " AND breakoutbox=%s AND connector=%s"
        cursor.execute(sql, (labName, domhub, dorCard, wirePair,
                             wirePosition, breakoutbox, breakoutboxConnector))
    else:
        cursor.execute(sql, (labName, domhub, dorCard, wirePair, wirePosition))
    return cursor.fetchone()[0]

# end getConnectionId    

def getStationIdentifier(db, stationId):
    """
    Returns the station identifier of the station specified by the given station id

    Parameter:
    db database connection object
    stationId int id of the station
    """

    cursor = db.cursor()
    sql = """
          SELECT identifier FROM FAT_Station WHERE fat_station_id=%s
          """

    if cursor.execute(sql, (stationId,)):
        return cursor.fetchone()[0]
    else:
        '-'


def getStationId(db, labName, stationIdentifier):
    """
    Returns the station id of the station specified by the given station identifier string

    Parameter:
    db - database connection object
    labName string
    stationIdentifier string
    """

    cursor = db.cursor()
    sql = """
          SELECT fat_station_id FROM FAT_Station
          INNER JOIN Laboratory l USING (lab_id)
          WHERE identifier = %s AND
          l.name = %s
          """
    cursor.execute(sql, (stationIdentifier, labName))
    return cursor.fetchone()[0]


def getStationForDOM(db, dom):
    """
    Returns the station of the given dom from the last FAT setup information

    Parameter:
    dom is a DOM object
    """
    cursor = db.cursor()
    sql = """
          SELECT fat_station_id FROM FAT_Setup WHERE prod_id = %s ORDER BY load_date DESC LIMIT 1
          """
    cursor.execute(sql, (dom.prodId,))
    return cursor.fetchone()[0]
    

def autoconfigure(db, doms, availableDoms, labName):
    """
    Configures the given DOMs (doms) and set the following configuration parameters:
    Connection identifier, ie. dor card, wire, wire position
    Maximum HV setting
    Local coincidence mode

    The maximum HV setting is set to the default value defined in the domconfiguration module.
    The local coincidence mode is determined by looking into the list of availableDoms for
    neighbors of the DOM.

    Parameter:
    db - database connection object
    doms - list of DOM objects (DOM class in fatsetup module)
    availableDoms - list of DOM objects created by the scanHubs method of the fatsetup module
                    it contains all the DOMs connected to the domhubs
    labName - name of the laboratory where the DOMs are hooked up
    """

    # prepare a list of available connections
    # it's easier to check the list of connections than a list of DOM
    # objects in the getLCMode method
    availableConnections = []
    for availableDom in availableDoms:
        availableConnections.append((availableDom.domhub, availableDom.dorCard,
                                     availableDom.wirePair, availableDom.wirePosition))

    for dom in doms:
        # check for lc neighbors and determine the lc mode
        dom.localCoincidenceMode = getLCMode(db, dom, availableConnections, labName)
        # set the maximum HV
        dom.maxHV = DOMCONFIGURATION_MAXIMUM_HV

# end autoconfigure

def getLCMode(db, dom, availableDOMs, labName):
    """
    Looks for the neighboring connections as defined in the databae
    for the given connection identified by labName, dom.domhub, dom.dorCard, dom.wirePair and dom.wirePosition
    On the basis of list of availableDoms and the defined neighboring connections in the database
    the actual lc mode is determined

    Parameter:
    db - database connection object
    dom - DOM object (class in this module)
    availableDOMs - list of available connections, ie. domhub, dorCard, wirePair and wirePosition informations
    labName - name of the laboratory where the DOMs are hooked up
    """

    cursor = db.cursor()

    # get the top neighbor connection which is the previous connector one the same breakoutbox if the connector
    # is not #1, otherwise it is the connector #8 on the previous breakoutbox
    # only connections to the same domhub are selected
    sql = """
          SELECT fc_top.domhub, fc_top.dor, fc_top.wire, fc_top.wire_position
          FROM FAT_Connection fc
          INNER JOIN Laboratory l ON l.lab_id=fc.lab_id
          INNER JOIN FAT_Connection fc_top ON fc_top.breakoutbox=IF(fc.connector=1,fc.breakoutbox-1,fc.breakoutbox) AND
          fc_top.connector=IF(fc.connector=1,8,fc.connector-1) AND
          fc.lab_id=fc_top.lab_id AND
          fc.domhub=fc_top.domhub
          WHERE l.name=%s AND
          fc.domhub=%s AND
          fc.dor=%s AND
          fc.wire=%s AND
          fc.wire_position=%s
          """
    cursor.execute(sql, (labName, dom.domhub, dom.dorCard, dom.wirePair, dom.wirePosition))
    result = cursor.fetchone()

    if result is None:
        noTopNeighbor = True
    elif ((result[0], result[1], result[2], result[3])) not in availableDOMs:
        noTopNeighbor = True
    else:
        noTopNeighbor = False
        
    # get the bottom neighbor connection which is the next connector one the same breakoutbox if the connector
    # is not #8, otherwise it is the connector #1 on the next breakoutbox
    # only connections to the same domhub are selected
    sql = """
          SELECT fc_bottom.domhub, fc_bottom.dor, fc_bottom.wire, fc_bottom.wire_position
          FROM FAT_Connection fc
          INNER JOIN Laboratory l ON l.lab_id=fc.lab_id
          INNER JOIN FAT_Connection fc_bottom ON fc_bottom.breakoutbox=IF(fc.connector=8,fc.breakoutbox+1,fc.breakoutbox) AND
          fc_bottom.connector=IF(fc.connector=8,1,fc.connector+1) AND
          fc.lab_id=fc_bottom.lab_id AND
          fc.domhub=fc_bottom.domhub
          WHERE l.name=%s AND
          fc.domhub=%s AND
          fc.dor=%s AND
          fc.wire=%s AND
          fc.wire_position=%s
          """
    cursor.execute(sql, (labName, dom.domhub, dom.dorCard, dom.wirePair, dom.wirePosition))
    result = cursor.fetchone()
    if result is None:
        noBottomNeighbor = True
    elif ((result[0], result[1], result[2], result[3])) not in availableDOMs:
        noBottomNeighbor = True
    else:
        noBottomNeighbor = False

    if noTopNeighbor and noBottomNeighbor:
        return DOMCONFIGURATION_LC_MODE_NO_NEIGHBOR
    if noTopNeighbor:
        return DOMCONFIGURATION_LC_MODE_NO_TOP_NEIGHBOR
    if noBottomNeighbor:
        return DOMCONFIGURATION_LC_MODE_NO_BOTTOM_NEIGHBOR
    if not (noTopNeighbor and noBottomNeighbor):
        return DOMCONFIGURATION_LC_MODE_BOTH_NEIGHBORS

# end getLCMode        


def storeFatSetup(db, doms, fatName, labName, loadDate=time.strftime('%Y-%m-%d %H:%M')):
    """
    Adds the given doms to the FAT_Setup table and sets the station and load date values

    db is a database connection object
    doms is a list of DOM objects
    fatName is the name of the FAT this product should be added to
    labName is the name of the laboratory
    loadDate is the date the DOM was loaded in the freezer

    throws an Exception with an error message describing the problem that occured
    """

    cursor = db.cursor()
    
    # get the fat id
    sql = """
          SELECT fat_id FROM FAT f
          INNER JOIN Laboratory l USING (lab_id)
          WHERE f.name=%s AND
          l.name=%s 
          """
    if not cursor.execute(sql, (fatName, labName)):
        raise Exception('No FAT named %s found in the database' % fatName)
    
    fatId = cursor.fetchone()[0]

    for dom in doms:
        # replace existing entries with new setup information
        # key is the combination of the fat_id and the prod_id
        sql = """
              REPLACE INTO FAT_Setup SET
              fat_id=%s,
              prod_id=%s,
              fat_station_id=%s,
              load_date=%s
              """
        if not cursor.execute(sql, (fatId, dom.prodId, dom.stationId, loadDate)):
            raise Exception('Could not add DOM %s to FAT %s' % (dom.serialNumber, fatName) )

      
def storeConfiguration(db, doms, labName, date=time.strftime('%Y-%m-%d %H:%M'), overwrite=False):
    """
    Writes the configuration to the FAT_DOM_Configuration tabel of the domprodteset database.
    
    If overwrite is set the latest configuration in the ProductConfiguration table related to
    the DOM of this DOMConfigruator object is replaced by the confifuration settings of this object.
    
    If a date is specified (format has to be sql conform) this date will be used rather than the current
    date.
    """

    cursor = db.cursor()
    for dom in doms:

        # The connection definitions are stored in a separate table (FAT_Connection)
        # Therefor, from the connection settings of this object the connection definition
        # has to be looked up in the connection table. The found id is then linked to the
        # configuration entry. If the connection defined for this object does not exist in the
        # table, a warning is shown.
        connectionId = getConnectionId(db, labName, dom.domhub, dom.dorCard, dom.wirePair, dom.wirePosition)
        if not connectionId:
            warnings.warn('The connection for domhub:%s card:%s wire:%s dom:%s does not exist in the \
            FAT_Connection table. You have to add it before this DOM can be configured!' %
                          (dom.domhub, dom.dorCard, dom.wirePair, dom.wirePosition))
            print(connectionId)

        sql = """
               FAT_DOM_Configuration
               SET fat_config_id=%s,
               prod_id=%s,
               date=%s,
               lc_mode=%s+1,
               max_hv=%s,
               fat_connection_id=%s
               """

        if overwrite:
            # get the latest configuration for this DOM
            getLatestSql = """
                           SELECT fat_config_id
                           FROM FAT_DOM_Configuration
                           WHERE prod_id=%s
                           ORDER BY date DESC
                           LIMIT 1;
                           """
            if cursor.execute( getLatestSql, (dom.prodId)):
                confId = cursor.fetchone()[0]
                sql = "UPDATE " + sql + " WHERE fat_config_id=%s"
                result = cursor.execute(sql, (confId, dom.prodId, date, dom.localCoincidenceMode,
                                               dom.maxHV, connectionId, confId))
            else:
                # no related DOM found in the database add a new instead
                overwrite = False

        if not overwrite:
            sql = "INSERT INTO " + sql
            # generate the next id for the FAT_DOM_Configuration table
            # all affected tables have to be locked for writing because
            # in between the id generation and the insertion no other
            # thread should insert another id to the specified tables
            #
            # this method is defined in the databaseutil module
            # the id has to be in the range of the laboratory id-range
            # the laboratory is identified by the first digit of an existing id
            # because all the IDs within the lab id-range start with the lab id

            cursor.execute('LOCK TABLES Laboratory WRITE, FAT_DOM_Configuration WRITE;')
            confId = databaseutil.getNextId(db, 'fat_config_id', 'FAT_DOM_Configuration', str(dom.prodId)[0])
            result = cursor.execute(sql, (confId, dom.prodId, date, dom.localCoincidenceMode, 
                                               dom.maxHV, connectionId))
            cursor.execute('UNLOCK TABLES;')
        
    return result
#end storeConfiguration

def storeNames(db, doms):
    """
    Stores the names of the given DOMs into the database

    Parameter:
    db database connection object
    doms list of DOM objects
    """

    cursor = db.cursor()

    for dom in doms:
        sql = """
              REPLACE INTO ProductName SET
              prod_id = %s,
              name = %s,
              explanation = %s,
              theme = %s
              """
        cursor.execute(sql, (dom.prodId, dom.name, dom.nameExplanation, dom.nameTheme))
    
              
def printSetupAndConfiguration(db, doms):
    """
    Prints the setup information stored in the DOM objects

    Parameter:
    db database connection object
    doms list of DOM objects
    """

    print("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" \
          % ('Serial #', 'Name'.ljust(20), 'domhub'.ljust(15), 'DOR', 'Wire', 'A|B', 'LC Neighbors', 'Max HV', 'Station')) 
    for dom in doms:
        print("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" \
              % (dom.serialNumber, dom.name.ljust(20), dom.domhub.ljust(15), dom.dorCard,
               dom.wirePair, dom.wirePosition, lcModeToString(dom.localCoincidenceMode).ljust(10),
               dom.maxHV, getStationIdentifier(db, dom.stationId)))

def lcModeToString(number):
    """
    Returns a string represantion for the given LC Mode number
    """

    if number == 0:
        return 'no'
    elif number == 1:
        return 'both'
    elif number == 2:
        return 'no bottom'
    elif number == 3:
        return 'no top'

# end localToString

def insertStation(db, labName, stationIdentifier):
    """
    Inserts the station with the given identifier to the database.

    Paramter:

    db database connection object
    labName the name of the lab this station is related to
    stationIdentifier the station label

    Return:
    the station id
    """

    cursor = db.cursor()

    # get the lab_id from the database
    sql = """
          SELECT lab_id FROM Laboratory WHERE name=%s
          """
    cursor.execute(sql, (labName,))
    labId = cursor.fetchone()[0]

    sql = """
          INSERT INTO FAT_Station SET
          fat_station_id=%s,
          lab_id=%s,
          identifier=%s
          """

    # generate the next id for the FAT_Station table
    # all affected tables have to be locked for writing because
    # in between the id generation and the insertion no other
    # thread should insert another id to the specified tables
    #
    # this method is defined in the databaseutil module
    # the id has to be in the range of the laboratory id-range

    cursor.execute('LOCK TABLES Laboratory WRITE, FAT_Station WRITE;')
    stationId = databaseutil.getNextId(db, 'fat_station_id', 'FAT_Station', labId )
    result = cursor.execute(sql, (stationId, labId, stationIdentifier))
    cursor.execute('UNLOCK TABLES;')

    return stationId
# insertStation

def insertConnection(db, labName, domhub, dorCard, wirePair,
                     wirePosition, breakoutbox, breakoutboxConnector):
    """
    Inserts the connection specified by the given parameters into the database

    If a connection with the given labName, domhub, dorCard, wirePair, wirePosition
    exists in the databse only the breakoutbox and breakoutboxConnector information will
    be updated and no new connection is inserted

    Returns the fat_connection_id of the inserted or updated entry
    """

    cursor = db.cursor()

    # first figure out whether the connection domhub,dorCard, wirePair, wirePosition
    # is already defined
    try:
        connectionId = getConnectionId(db, labName, domhub, dorCard, wirePair, wirePosition)
        print('oi')
        # update the connection and set the breakoutbox and connector values
        sql = """
              UPDATE FAT_Connection SET
              breakoutbox=%s,
              connector=%s
              WHERE fat_connection_id=%s
              """
        cursor.execute(sql, (breakoutbox, breakoutboxConnector, connectionId))
        
    except Exception as e:
        print(e)
        # no connection found, insert a new one

        # get the lab_id from the database
        sql = """
              SELECT lab_id FROM Laboratory WHERE name=%s
              """
        cursor.execute(sql, (labName,))
        labId = cursor.fetchone()[0]

        sql = """
              INSERT INTO FAT_Connection SET
              fat_connection_id=%s,
              lab_id=%s,
              domhub=%s,
              dor=%s,
              wire=%s,
              wire_position=%s,
              breakoutbox=%s,
              connector=%s
              """

        # generate the next id for the FAT_Connection table
        # all affected tables have to be locked for writing because
        # in between the id generation and the insertion no other
        # thread should insert another id to the specified tables
        #
        # this method is defined in the databaseutil module
        # the id has to be in the range of the laboratory id-range

        cursor.execute('LOCK TABLES Laboratory WRITE, FAT_Connection WRITE;')
        connectionId = databaseutil.getNextId(db, 'fat_connection_id', 'FAT_Connection', labId )
        result = cursor.execute(sql, (connectionId, labId, domhub, dorCard, wirePair,
                                      wirePosition, breakoutbox, breakoutboxConnector))
        cursor.execute('UNLOCK TABLES;')

    return connectionId

# end insertConnection
        

def mapStationToConnection(db, stationId, connectionId, date=time.strftime('%Y-%m-%d')):
    """
    Inserts and replaces existing station to connection mappings into the database

    Parameter:
    database station id
    database connection id
    date when this mapping is performed, default the current system date
    """
    
    cursor = db.cursor()

    # with the replace statement already existing mappings only get a new date
    # the primary key of the table is the combination of fat_station_id and fat_connection_id
    sql = """
          REPLACE INTO FAT_StationConnection SET
          fat_station_id=%s,
          fat_connection_id=%s,
          date=%s
          """
    return cursor.execute(sql, (stationId, connectionId, date))
# end mapStationToConnection

def printStationToConnectionMapping(db, labName):
    """
    Prints the station and connection mapping stored in the database
    """

    cursor = db.cursor()
    print("Station\tDOMHub\tDORCard\tWire\tPosition\tBreakoutbox\tConnector")
    sql = """
          SELECT domhub, dor, wire, wire_position, breakoutbox, connector FROM FAT_Connection
          INNER JOIN Laboratory l USING (lab_id)
          WHERE l.name=%s
          """
    cursor.execute(sql, (labName,))
    for (domhub, dor, wire, wirePosition, breakoutbox, connector) in cursor.fetchall():
        stationId = getStationFromConnection(db, labName, domhub, dor, wire, wirePosition)
        if stationId != None:
            stationIdentifier = getStationIdentifier(db, stationId)
            print(("%s\t%s\t%s\t%s\t%s\t%s\t%s") % \
                  (stationIdentifier, domhub, dor, wire, wirePosition, breakoutbox, connector))

# end printStatoinToConnectionMapping
        
