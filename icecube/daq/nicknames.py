"""
This is the DOM nicknames utility module.
DOMs can have many nicknames:
    1. The MBID - the 48-bit ID which electronically identifies it
    2. The DOMID - an 8-character ID assigned at production time
    3. The NICKNAME - an oft-whimsical name assigned by some grad student
    4. The LOCATION - if the DOM is deployed in the IceCube array then
       it gets a location string of the form 'ss-mm' where ss is the
       string number and mm is the position along the string; 01-60 for
       in-ice modules and 61-64 for IceTop.
You should define an environmental variable NICKNAMES which points
to a file with MBID\s+DOMID\s+NICKNAME\s+LOCATION lines.
"""

import re

class Nicknames:
    def __init__(self, filename):
        pattern = re.compile( \
            '([0-9a-f]{12})\s+([ATU][XP][0-9][HPY][0-9]' \
            + '{4})\s+(\w+)\s+([0-9]{2}\-[0-9]{2}).*' \
            )
        f = file(filename)
        self.by_mbid  = dict()
        self.by_domid = dict()
        self.by_name  = dict()
        self.by_loc   = dict()
        self.domdb    = [ ]
        while 1:
            s = f.readline()
            if len(s) == 0: break
            m = pattern.matches(s)
            if m is not None: self.domdb.append(m.groups())
        f.close()
        for index in range(len(self.domdb)):
            mbid, domid, name, loc = self.domdb[index]
            self.by_mbid[mbid] = index
            self.by_domid[domid] = index
            self.by_name[name] = index
            self.by_loc[name] = index
        
    def lookup(self, key):
        """
        Do a smart lookup of a DOM
        """
        if len(key) == 12:
            return self.domdb[self.by_mbid[key]]
        elif len(key) == 8:
            return self.domdb[self.by_domid[key]]
        elif len(key) == 5:
            return self.domdb[self.by_loc[key]]
        else:
            return self.domdb[self.by_name[key]]
        
