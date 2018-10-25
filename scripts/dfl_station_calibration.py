#!/usr/bin/env python
"""
This script sets up mapping from stations to connections in the database

Author: Bernhard Voigt <bernhard.voigt@desy.de>
"""
import time
import sys
from getopt import *
import MySQLdb

######################################
#    Function definitions            #
######################################

def usage():
    print >>sys.stderr, \
          """
          Usage:
          dfl_station_calibration.py -H db-server -u db-user -p db-user-passwd -s site-name
                                     [-d date] calibration.txt
                                      

          Mandatory options:

          -H database-host
          -u database user name
          -p password for the given database user name
          -s name of the production site (DESY, PSL or Uppsala)

          Options

          -h schow this help message
          -d date Sets the date of the calibration in the database table. Format is dd.mm.yyyy
                  The date can also be specified in the file. If no date is given, the current system
                  date is used.

          Arguments:

          calbration.txt is the file containing the calibration information. The format of the file is
          an ASCII comma-separated-variable (csv) file with the first row giving the field names.
          The fields should be separated by tab, space or comma.
          The following rows contain the values, again separated by tab, space or comma.
          There are three fields available: STATION, RATIO, DATE. Ratio is the calibration
          information and date the date of the calibration.
          Example:

          STATION    RATIO    DATE
          1          0.78     28-06-2005
          2          0.56     28-06-2005
          

          Here is an example command line
          $ dfl_station_calibration.py -H databasehost -u dbuser -p somepasswd -s PSL calibration.txt

          Inserted 58 station calibration entries

          $
          
          """


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
verbose = False
date = None

# read the options from the command line
try:
    options, arguments = getopt(sys.argv[1:],
                                "H:u:p:s:d:vh")

except GetoptError as e:
    print e
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
        labName = value.upper()
    elif option == '-v':
        verbose = True
    elif option == '-d':
        date = value

# get the name of the file with the calibration information
# and try to read it
try:
    filename = arguments.pop()
    f = file(filename, 'r')
except Exception as e:
    print >>sys.stderr, "Cannot open file %s" % filename
    sys.exit(1)

# create the database connection
db = MySQLdb.connect(user=dbUser, passwd=dbUserPasswd, db='domprodtest', host=dbHost)
cursor = db.cursor()

# read the whole file, loop through the lines, split them
# and store the values to the database
lines = f.readlines()
fields = [x.upper() for x in lines.pop(0).split()]
counter = 0
for line in lines:
    values = line.split()
    # use a date if available, but only when not specified on the command line
    if not date:
        try:
            date = values[fields.index('DATE')]
        except Exception:
            date = time.strftime('%Y-%m-%d')
            
    # get the fat_station_id from
    sql = """
          SELECT fat_station_id FROM FAT_Station fs
          INNER JOIN Laboratory l USING (lab_id)
          WHERE fs.identifier=%s AND l.name=%s
          """
    if not cursor.execute(sql, (values[fields.index('STATION')], labName)):
        print >>sys.stderr, "Cannot find the fat_station_id for station %s" % values[fields.index('STATION')]
    else:    
        stationId = cursor.fetchone()[0]
    
        sql = "INSERT INTO FAT_Station_Calibration VALUES (%s,%s,%s)"
        if verbose:
            print >>sys.stderr, "Station %s: %s" % (values[fields.index('STATION')],
                                                    (sql % (stationId, values[fields.index('RATIO')], date)))
        if cursor.execute(sql, (stationId, values[fields.index('RATIO')], date)):
            counter += 1

# done with looping and insertion        

print "Inserted %d station calibration entries" % counter

sys.exit(0)
