#!/usr/bin/env python
"""
This script sets up mapping from stations to connections in the database

Author: Bernhard Voigt <bernhard.voigt@desy.de>
"""
from __future__ import print_function

from builtins import str
import icecube.domtest.fatsetup as fatsetup
import re
import sys
from getopt import *
import MySQLdb


# Python 2/3 compatibility hack
if sys.version_info >= (3, 0):
    read_input = input
else:
    read_input = raw_input


######################################
#    Function definitions            #
######################################

def usage():
    print("""
          Usage:
          dfl_station_connection_setup.py -H db-server -u db-user -p db-user-passwd -s site-name
                                          --breakoutbox BREAKOUTBOX.CONNECTER DOMHUB.CARDWIREDOM STATION_IDENTIFIER

          Mandatory options:

          -H database-host
          -u database user name
          -p password for the given database user name
          -s name of the production site (DESY, PSL or Uppsala)
          --breakoutbox   Specify also the breakout box connection definition.
                          For example -bb 1.1 domhub1.11A means the first breakout box in the
                          DFL and connector number 1 is bound to the card 1, wire 1 DOM A on domhub1.
                          The breakoutbox and connector definition has to be numeric.


          Options:

          -v             The current mapping is printed on the screen

          -f             Do not ask the user if a not existing station or a connection should be
                         inserted into the database

          Arguments:

          DOMHUB.CARDWIREDOM is for example domhub1.11B the connection to DOM B on card 1, wire 1 on
          domhub1.

          STATION_IDENTIFIER is the label of the station

          Example:

          Define the connection for station #6, which takes the A-DOM on card2 wire0, the card is located
          in domhub3. The breakout box 2 and connector 4 is used.

          dfl_station_connection_setup.py -H dbsever -u user -p passwd -s DESY --breakoutbox 4.2 domhub3.20A 6

          """, file=sys.stderr)

def prompt(string, validItems=None):
    """
    Prompts the user with the given string and returns the input, if it is
    in the list of validItems, otherwise the prompt is repeated.

    If validItems is empty any input is returned
    """

    while True:
        response = str(read_input(string))
        if validItems is None:
            return response
        elif response in validItems:
            return response
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
labName = None
breakoutbox = None
breakoutboxConnector = None
domhub = None
dorCard = None
wirePair = None
wirePosition = None
stationIdentifier = None
printMapping = False
confirm = True


# read the options from the command line
try:
    options, arguments = getopt(sys.argv[1:],
                                "H:u:p:s:hvf",
                                ['breakoutbox='])

except GetoptError as e:
    print(e)
    usage()
    sys.exit(1)

# parse the options
for option, value in options:
    if option == '-h':
        usage()
        sys.exit(0)
    if option == "-H":
        dbHost = value
    elif option == '-u':
        dbUser = value
    elif option == '-p':
        dbUserPasswd = value
    elif option == '-s':
        labName = value
    elif option == '-v':
        printMapping = True
    elif option == '-f':
        confirm = False
    elif option == '--breakoutbox':
        (breakoutbox, breakoutboxConnector) = value.split('.')


# get the stationidentifier
try:
    stationIdentifier = arguments.pop()
except Exception as e:
    if not printMapping:
        raise e

# get the connection definition from the command line
try:
    (domhub, rest) = arguments.pop().split('.')
    (dorCard, wirePair, wirePosition) = list(rest)
    wirePosition = wirePosition.upper()
except Exception as e:
    if not printMapping:
        raise e

# create the database connection
db = MySQLdb.connect(user=dbUser, passwd=dbUserPasswd, db='domprodtest', host=dbHost)

# run the mapping action only if arguments are given
if stationIdentifier is not None and domhub is not None:

    # get the station id
    try:
        stationId = fatsetup.getStationId(db, labName, stationIdentifier)
    except Exception as e:
        if not confirm:
            userInput = 'y'
        else:
            userInput = str()
            userInput = prompt("No station %s found in the database! Do you want to insert it [y|n]?" % stationIdentifier,
                       ('y', 'n'))

        if userInput == 'y':
            try:
                stationId = fatsetup.insertStation(db, labName, stationIdentifier)
                print("Station %s created!" % stationIdentifier)
            except Exception as e:
                print(e)
                print("Could not insert the Station into the database!", file=sys.stderr)
                sys.exit(1)


    # get the connection id
    try:

        connectionId = fatsetup.getConnectionId(db, labName, domhub, dorCard, wirePair,
                                                wirePosition, breakoutbox, breakoutboxConnector)
    except Exception as e:
        if not confirm:
            userInput = 'y'
        else:
            userInput = str()
            userInput = prompt("No connection %s.%s%s%s found in the database! Do you want to insert it [y|n]?" % \
                               (domhub, dorCard, wirePair, wirePosition), ('y', 'n'))

        if userInput == 'y':
            try:
                connectionId = fatsetup.insertConnection(db, labName, domhub, dorCard, wirePair,
                                                         wirePosition, breakoutbox, breakoutboxConnector)
                print("Connection %s.%s%s%s created!" % (domhub, dorCard, wirePair, wirePosition))
            except Exception as e:
                print(e)
                print("Could not insert the connection into the database!", file=sys.stderr)
                sys.exit(1)

    try:
        fatsetup.mapStationToConnection(db, stationId, connectionId)
        print("Mapped station %s to connection %s.%s%s%s" % (stationIdentifier, domhub, dorCard, wirePair, wirePosition))

    except Exception as e:
        print(e)
        print("Could not map station %s to connection %s.%s%s%s" % \
              (stationIdentifier, domhub, dorCard, wirePair, wirePosition), file=sys.stderr)
        sys.exit(1)

if printMapping:
    fatsetup.printStationToConnectionMapping(db, labName)

sys.exit(0)
