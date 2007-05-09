#
# FAT database module
#

"""
This module contains several database utility functions
    - mbid_to_domid() - convert a mainboard ID to a DOM serial #
    
The database connection information is specified in a Python
ConfigParser file (similar to Windows INI file syntax - see
Python documentation on ConfigParser) .fatdb in the user's
home directory.  This file should have the following section
and keys:
    [domprodtest]
    host=<db-host.ip.addr>
    user=<db-user-account>
    passwd=<db-password>

(C) 2005 Kael Hanson (kael.hanson@icecube.wisc.edu)
"""

import MySQLdb
from ConfigParser import ConfigParser
import os

__config = ConfigParser()
__config.read(os.path.expanduser("~/.fatdb"))

def get_db_connection():
    """
    This function obtains a db connection using host, user,
    and password information contained in the user
    configuration file $HOME/.fatdb.
    """
    return MySQLdb.connect(
        host=__config.get("domprodtest", "host", "localhost"),
        user=__config.get("domprodtest", "user", "penguin"),
        passwd=__config.get("domprodtest", "passwd"),
        db="domprodtest"
        )
        
db = get_db_connection()
c  = db.cursor()
c.execute("""
    SELECT 
        mp.hardware_serial,dp.tag_serial 
    FROM 
        ProductType pt,Product mp,Assembly a,
        AssemblyProduct ap,Product dp 
    WHERE 
        pt.name='Main Board' AND 
        pt.prodtype_id=mp.prodtype_id AND 
        mp.prod_id=ap.prod_id AND 
        ap.assem_id=a.assem_id AND 
        a.prod_id=dp.prod_id
    """
    )

__map_mbid_to_domid = dict()
__map_domid_to_mbid = dict()
for (mbid, domid) in c.fetchall():
    __map_mbid_to_domid[mbid] = domid
    __map_domid_to_mbid[domid] = mbid

del(c)
del(db)
del(mbid)
del(domid)

def mbid_to_domid(mbid):
    """
    Return an 8-character DOMID (e.g. TP7Y0851) from the 12-char
    hexadecimal string representation of a DOM mainboard ID.
    """
    return __map_mbid_to_domid[mbid]

def domid_to_mbid(domid):
    """
    Returns 12-character hex mainboard ID from 8-char DOMID
    """
    return __map_domid_to_mbid[domid]