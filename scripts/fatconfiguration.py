#!/usr/bin/env python
"""
This script provides a configuration dialog
for the DOM configuration. See the documentation of the
script, which you can get by calling it with the -h option

Author: Bernhard Voigt <bernhard.voigt@desy.de>
"""

import sys
import warnings
import readline # improved command line editing, raw_input method is overwritten
from icecube.domtest.domconfiguration import DOMConfigurator
import icecube.domtest.fatsetup as fatsetup
import re
from getopt import *
import MySQLdb

######################################
#    Constant definitions            #
######################################
CONFIGURATION_DIALOG = 1
FAT_SETUP_DIALOG = 2

######################################
#    Function definitions            #
######################################

def usage():
    print >>sys.stderr, \
          """
          Usage:
          fatconfiguration.py -H db-server -u db-user -p db-user-passwd -s site-name
                              [-t] [-v] [-f] [--no-configuration] [--add-to-fat=fat-name]
                              [--set-names=file] [--rename] [--only-doms=DOM_LIST] DOMHUB_LIST
          fatconfiguration.py -H db-server -u db-user -p db-user-passwd -s site-name
                              [-t] [-v] [-f] [--no-configuration] [--add-to-fat=fat-name]
                              [--set-names=file] [--rename] --no-scan DOM_LIST

          This scripts is used for the configuration of DOMs and in particular for the FAT DFL load configuration.
          The configuration and setup information is written to the database. The configuration includes the definition of
          local coincidence modes, maximum high voltage settings and the connection specification (hub, dor, wire etc.). The
          setup information includes the position of the DOM in the freezer, ie. the station and the assignment to a FAT load.
          For the database connection the database host, the database user and the corresponding password have to be supplied
          as command line parameters, as well as the name of the site of the production site.

          If a list of DOMHubs should be scanned for connected DOMs, it is important that the proxy server domhub-services
          is running, the DOMs are in iceboot mode and a terminal connection is opened via the dtsx util.

          Mandatory options:

          -H database-host
          -u database user name
          -p password for the given database user name
          -s name of the production site (DESY, PSL or Uppsala)

          Options:

          -h                    Prints this help

          -f                    The automatic derived setup and configuration is stored without confirmation

          -t                    Test only, the configuration is not saved to the database.

          -v                    Print the configuration after it has been configured. Usefull in combination with
                                the -f and -t option

          --no-configuration    The DOMs will not be configured. This option only makes sense, if you have the
                                --add-to-FAT option specified.

          --add-to-FAT=fat-name The DOMs that are configured will be added to a FAT. The FAT identified by the given
                                name has to be defined in the database beforehand. If no autmatic configuration is
                                used (--no-scan option), the user will be asked for the station of the DOM.
                                The load data written to the database is the current system date

          --set-names=file      The DOMs will be named during the configuration. A file is given as an argument,
                                the names are taken from that file. The file should be a tab separated list of
                                names. The first field is the name, the second the explanation of the name and the
                                third field the corresponding name theme.
                                In the case that a DOM has been named already, the name will not be changed,
                                except the --rename flag is given.
                                If you want to specify the names on in the configuration dialog manually use
                                an empty string '' as the file argument

          --rename              DOM names are overwritten with the new names from the file

          --only-DOMs=DOM_LIST  Only the DOMs in the DOM_LIST will be configured. The list is a string of DOM Serial numbers
                                or DOM names separated by whitespace, e.g. 'TP5Y0001 UP5Y0002' or 'Washington Chicago Atlanta'

          --no-scan             With this option the DOMs to configure are specified explicitly rather than scanning a list
                                of given domhubs for connected DOMs. The command argument has to be the list of DOMs that will
                                be configured. The user will be prompted for the configuration settings and no automatic
                                configuration is performed.

          Arguments:

          DOMHUB_LIST and DOM_LIST are whitespace separated names of domhub or DOMs, respectively. DOM names are either the serial
          numbers or the names that have been assigned to DOMs beforehand.

          Examples:

          There are two different ways how to determine the DOMs that will be configured:
          Scanning for the DOMs hooked up to the given list of domhubs:

          fatconfiguration.py -H db-server -u db-user -p db-user-password domhub1 domhub2

          This will result in the autmatic configuration of all DOMs that are hooked up to domhub1 and domhub2.
          The configuration parameters are determined from the connection to the domhub and the setup information
          defined in the database. The user can save the information directly or modify the configuration parameters
          with the help of a configuration prompt and save them afterwards.

          If you use the command line switch --no-scan the list of DOMs that will be configured has to be passed as
          an argument list:

          fatconfiguration.py -H db-server -u db-user -p db-user-passwd TP5Y0001 UP5Y0002 TP5Y0003

          This will prompt the user with the configuration dialog where the user has to set the configuration parameters
          of each DOM that was given in the command argument list. No automatic configuration is performed. In the example
          the DOMs TP5Y001, UP5Y002 and TP5Y003 will be configured.

          A typical FAT initialization is performed with this command line (use -t to test this procedure):

          fatconfiguration.py -H db-server -u db-user -p db-user-passwd -f -v --add-to-fat='FAT 7' \\
          --set-names='domnames.txt' domhub1


          Author information: Bernhard Voigt <bernhard.voigt@desy.de>

          See also:
          dfl_station_connection_setup.py to define the DFL station connection mapping
          """

# end def usage


def setName(doms, names):
    """
    Sets the names of the given doms, but only if they do not have a name yet
    The name is not only the name of the DOM, but also the explanation and the theme
    of the name.
    Raises an Exception if there are not enough names for all the given DOMs

    Parameter:
    list of DOM objects
    list of names (see getName
    """

    if len(doms) > len(names):
        raise Exception("There are not enough names for all the DOMs which will be configured")

    for (dom, name) in zip(doms, names):
        # only name a DOM if it has no name or the user forced renaming (command line switch)
        if dom.name is '' or rename:
            dom.name = name['name']
            dom.nameExplanation = name['explanation']
            dom.nameTheme = name['theme']
#end setNames


def getNamesFromFile(filename):
    """
    Reads the given file and stores the content into a list of dictionaries entries with fields
    'name', 'explanation' and 'theme'
    """

    names = []

    try:
        file = open(filename, 'r')
    except IOError, error:
        print "Could not open %s for reading the DOM names" % filename
        return

    for line in file:
        line = [item.strip() for item in line.split("\t")]
        entry = {'name':str(), 'explanation':str(), 'theme':str()}
        if len(line) < 2:
            warnings.warn("The names file %s is not in the valid format" % filename)
        else:
            entry['name'] = line[0]
            entry['explanation'] = line[1]
            entry['theme'] = ''
        if len(line) > 2:
            entry['theme'] = line[2]

        names.append(entry)
    return names

def configurationDialog(doms, DIALOG_SELECT):
    """
    """

    currentDOM = 0
    totalNumberOfDOMs = len(doms)
    for dom in doms:
        currentDOM += 1
        while True:
            fields = {}
            # print the current configuration
            if dom.name is None:
                print "- # %i of %i ------- %s ---------" % (currentDOM, totalNumberOfDOMs, dom.serialNumber)
            else:
                print "- # %i of %i --- %s - %s --------" % (currentDOM, totalNumberOfDOMs, dom.serialNumber, dom.name)

            # test the given bitmask for the selection of the configuration dialog
            if DIALOG_SELECT & CONFIGURATION_DIALOG:
                fields = printConfiguration(dom, fields)
            # print the fat setup information
            # test the given bitmask for the selection of the setup dialog
            if DIALOG_SELECT & FAT_SETUP_DIALOG:
                fields = printFatSetup(dom, fields)

            # prompt the user whether something should be changed
            # valid input is a list of numbers for the fields to select and 'c' and 'q'
            validInput = [str(i) for i in range(1,len(fields)+1)]
            validInput.append('c')
            validInput.append('q')
            validInput.append('s')
            if currentDOM < totalNumberOfDOMs:
                userInput = prompt("\nType the number of the field you want to change or\n" +
                                   "c to continue with the next DOM\n" +
                                   "q to leave the program without saving\n> ", validInput)
            else:
                userInput = prompt("\nType the number of the field you want to change or\n" +
                                   "s to save the configuration of all DOMs\n" +
                                   "q to leave the program without saving\n> ", validInput)
            # for a numeric input prompt the user to change the corresponding field
            try:
                userInput = int(userInput)
                changeField(dom, fields[userInput]) # hereafter show the configuration again (while loop continues)
            except ValueError, exception:
                break # stop the loop for this DOM, we have either c or q as input

        if userInput == 'c':
            continue
        elif userInput == 's':
            return
        elif userInput == 'q':
            sys.exit(0)


def printConfiguration(dom, fields):
    """
    Prints the list of configuration fields and settings of the given dom to the screen
    Returns a list of field number to field name mappings

    Parameters:
    dom is a DOM object
    fields is a list

    Return:
    list with field names
    """

    fieldCounter = len(fields)
    # setNames is a command line parameter switch
    if setNames:
        # starting at position 1
        fieldCounter += 1
        print "%i DOM Name: %s " % (fieldCounter, dom.name)
        fields[fieldCounter]='DOM Name'

        fieldCounter += 1
        print "%i Name Explanation: %s " % (fieldCounter, dom.nameExplanation)
        fields[fieldCounter]='Name Explanation'

        fieldCounter += 1
        print "%i Name Theme: %s " % (fieldCounter, dom.nameTheme)
        fields[fieldCounter]='Name Theme'

    fieldCounter += 1
    print "%i DOMHub: %s " % (fieldCounter, dom.domhub)
    fields[fieldCounter] = 'DOMHub Name'

    fieldCounter += 1
    print "%i DORCard: %s " % (fieldCounter, dom.dorCard)
    fields[fieldCounter] = 'DOR-Card #'

    fieldCounter += 1
    print "%i Wire: %s " % ( fieldCounter, dom.wirePair)
    fields[fieldCounter] = 'Wire Pair #'

    fieldCounter += 1
    print "%i Position[A|B]: %s " % (fieldCounter, dom.wirePosition)
    fields[fieldCounter] = 'Position [A|B]'

    fieldCounter += 1
    print "%i Local Coincidence Mode [0 = no neighbor|1 = both|2 = no bottom|3 = no top]': %s " % \
          (fieldCounter, dom.localCoincidenceMode)
    fields[fieldCounter] = 'Local Coincidence Mode [0 = no neighbor|1 = both|2 = no bottom|3 = no top]'

    fieldCounter += 1
    print "%i Maximum allowed HV: %s " % (fieldCounter, dom.maxHV)
    fields[fieldCounter] = 'Maximum HV'

    return fields
# end printConfiguration


def printFatSetup(dom, fields):
    """
    Prints the configuration fields of the FAT setup
    Returns the given list of field number to name mappings appended by the new fields

    Parameters:
    dom is a DOM object
    fields is a list of field number to name mappings

    Return:
    a list with field names
    """

    fieldCounter = len(fields)
    fieldCounter += 1 # starting at position 1
    print "%i Station: %s " % (fieldCounter, fatsetup.getStationIdentifier(db, dom.stationId))
    fields[fieldCounter] = 'Station Identifier'
    return fields
# end printFatSetup


def changeField(dom, field):
    """
    Prompts the user for the value of field and sets the corresponding field of the dom object
    to the given value.
    """

    value =  prompt ("Please enter the %s: " % field )
    if field =='DOM Name':
        dom.name = value
    elif field == 'Name Explanation':
        dom.nameExplanation = value
    elif field == 'Name Theme':
        dom.nameTheme = value
    elif field == 'DOMHub Name':
        dom.domhub = value
    elif field == 'DOMHub Name':
        dom.domhub = value
    elif field == 'DOR-Card #':
        dom.dorCard = int(value)
    elif field == 'Wire Pair #':
        dom.wirePair = int(value)
    elif field == 'Position [A|B]':
        dom.wirePosition == value
    elif field == 'Local Coincidence Mode [0 = no neighbor|1 = both|2 = no bottom|3 = no top]':
        dom.localCoincidenceMode = int(value)
    elif field == 'Maximum HV':
        dom.maxHV = int(value)
    elif field == 'Station Identifier':
        # store the id of the station rather than the given identifier
        # labName is a command line argument
        dom.stationId = fatsetup.getStationId(db, labName, value)
# end changeField


def prompt(string, validItems=None):
    """
    Prompts the user with the given string and returns the input, if it is
    in the list of validItems, otherwise the prompt is repeated.

    If validItems is empty any input is returned
    """

    while True:
        input = str(raw_input(string))
        if validItems is None:
            return input
        elif input in validItems:
            return input
#end prompt


########################################
#          Script execution            #
########################################

# default values for the command line switches
# for documentation read the help print out above and
# compare to the command line switches below
dbHost = None
dbUser = None
dbUserPasswd = None
doScanning = True
doConfirmation = True
doConfiguration = True
noSave = False
doFatSetup = False
setNames = False
domNames = None
rename = False
domList = None
printSetupAndConfiguration = False
labName = None

# read the options from the command line
try:
    options, arguments = getopt(sys.argv[1:],
                                "H:u:p:s:hvft",
                                ['add-to-fat=', 'only-doms=', 'set-names=',
                                 'no-configuration', 'no-scan', 'rename'])

except GetoptError, e:
    print e
    usage()
    sys.exit(1)

# parse the options
for option, value in options:
    if option == "-H":
        dbHost = value
    elif option == '-u':
        dbUser = value
    elif option == '-p':
        dbUserPasswd = value
    elif option == '-s':
        labName = value
    elif option == '-f':
        doConfirmation = False
    elif option == '-v':
        printSetupAndConfiguration = True
    elif option == '-t':
        noSave = True
    elif option == "-h":
        usage()
        sys.exit(1)
    elif option == "--add-to-fat":
        doFatSetup = True
        fatName = value
    elif option == "--only-doms":
        domList = value
    elif option == "--set-names":
        setNames = True
        if value is not "":
            domNames = getNamesFromFile(value)
    elif option == "--rename":
        rename = True
    elif option == "--no-configuration":
        doConfiguration = False
    elif option == "--no-scan":
        doScanning = False

# print an empty line to separate the output from the command line
print

# check whether the manadatory options are set
mandatoryOptions = True
if labName is None:
    print >>sys.stderr, "Command line option -s SiteName has to be specified"
    mandatoryOptions = False
if dbHost is None:
    print >>sys.stderr, "Command line option -H DatabaseHost has to be specified"
    mandatoryOptions = False
if dbUser is None:
    print >>sys.stderr, "Command line option -u DatabaseUser has to be specified"
    mandatoryOptions = False
if dbUserPasswd is None:
    print >>sys.stderr, "Command line option -p DatabasePassword has to be specified"
    mandatoryOptions = False

if not mandatoryOptions:
    print
    sys.exit(1)


# create the database connection
db = MySQLdb.connect(user=dbUser, passwd=dbUserPasswd, db='domprodtest', host=dbHost)

# get the DOMs for the setup and configuration

if not doScanning:
    # if no scanning is demanded, use the DOMs specified as the script's argument list (DOM names or serials)
    availableDoms = fatsetup.createDOMs(db, arguments)
else:
    # scan for the DOMs connected to the hubs given to the script in the argument list
    try:
        availableDoms = fatsetup.scanHubs(db, arguments)
    except Exception, e:
        print >>sys.stderr, "Could not connect to one of the given domhubs: %s" % arguments
        print >>sys.stderr, e
        sys.exit(1)

# the list of DOMs that should be configured is the intersection of the only-doms list and the
# list of DOMs found on the hubs or given as argument
if domList is not None:
    # build the list of DOM objects from the string given as an command option parameter
    domList = fatsetup.createDOMs(db, domList.split())
    # build the list of DOMs to configure
    doms = []
    for dom in domList:
        if dom in availableDoms:
            doms.append(dom)
else:
    doms = availableDoms

# set the names according to the command line argument
if setNames and domNames is not None:
    try:
        setName(doms, domNames)
    except Exception, e:
        print e
        userInput = prompt("Continue (c) Abort(q): ")
        if userInput == 'c':
            pass
        else:
            sys.exit(0)

# depending on the command line switches, perform configuration and fat setup settings
if doScanning:
    # determine the setup and configuration automatically
    if doConfiguration and doFatSetup:
        fatsetup.autoconfigure(db, doms, availableDoms, labName)
        fatsetup.autoFatSetup(db, doms, labName)

        if doConfirmation:
            # applied bitmask to the configurationDialog method selects both dialogs:
            # configuration and setup
            configurationDialog(doms, CONFIGURATION_DIALOG | FAT_SETUP_DIALOG)

    elif doFatSetup:
        fatsetup.autoFatSetup(db, doms, labName)
        if doConfirmation:
            configurationDialog(doms, FAT_SETUP_DIALOG)
    elif doConfiguration:
        fatsetup.autoconfigure(db, doms, availableDoms, labName)
        if doConfirmation:
            configurationDialog(doms, CONFIGURATION_DIALOG)
else:
    # the user has to go through the configuration dialog
    if doConfiguration and doFatSetup:
        # applied bitmask to the configurationDialog method selects both dialogs:
        # configuration and setup
        configurationDialog(doms, CONFIGURATION_DIALOG | FAT_SETUP_DIALOG)
    elif doFatSetup:
        configurationDialog(doms, FAT_SETUP_DIALOG)
    elif doConfiguration:
        configurationDialog(doms, CONFIGURATION_DIALOG)


# store the setup and configuration
if doFatSetup and not noSave:
    fatsetup.storeFatSetup(db, doms, fatName, labName)
if doConfiguration and not noSave:
    fatsetup.storeConfiguration(db, doms, labName)
if setNames and not noSave:
    fatsetup.storeNames(db, doms)

if printSetupAndConfiguration:
    fatsetup.printSetupAndConfiguration(db, doms)
    print
