#!/usr/bin/env python
#
# 'domprodtest' database class

from __future__ import absolute_import
from builtins import object
from future.utils import raise_
import socket
from . import DOMProdTestUtil

###############################################################################

class BasicDB(object):
    """Basic database object"""

    def __init__(self, db):
        """Constructor which uses a specific instance of a database object"""
        if db is not None:
            self.db = db
        else:
            props = DOMProdTestUtil.findProperties()

            self.db = DOMProdTestUtil.connectToDB(props)

    def close(self):
        self.db.close()

    def cursor(self):
        return self.db.cursor()

    def executeQuery(self, query):
        cursor = self.db.cursor()
        cursor.execute(query)

        return cursor

class DOMProdTestDB(BasicDB):
    """'domprodtest' database object"""

    def __init__(self, db=None):
        """Constructor which uses a specific instance of a database object"""
        BasicDB.__init__(self, db)

    def getLabId(self, hostname=None):
        """
        get the local laboratory ID
        """

        if hostname is None:
            hostname = socket.gethostname()

        labId = self.getLabIdByName(self.cursor(), hostname)
        if labId is None:
            labId = self.getLabIdByMachine(self.cursor(), hostname)
            if labId is None:
                raise_(IOError, "Laboratory " + hostname + " not found")

        return labId

    def getLabIdByMachine(self, cursor, name):
        labId = None
        while labId is None:
            query = 'select lab_id from LabMachine where machine=' + \
                DOMProdTestUtil.quoteStr(name)

            cursor.execute(query)
            if int(cursor.rowcount) == 1:
                labId = cursor.fetchone()[0]
                break

            dot = name.find('.')
            if dot < 0:
                break

            name = name[dot + 1:]

        cursor.close()

        return labId

    def getLabIdByName(self, cursor, name):
        query = 'select lab_id from Laboratory where name=' + \
            DOMProdTestUtil.quoteStr(name)
        cursor.execute(query)
        if int(cursor.rowcount) != 1:
            result = None
        else:
            result = cursor.fetchone()[0]
        cursor.close()

        return result

    def getDOMId(self, serNum):
        """
        get the product ID for the DOM associated with the
        specified serial number
        """

        if DOMProdTestUtil.isMainBoardSerial(serNum):
            query = 'select d.prod_id from Product mb,AssemblyProduct ap' + \
                ',Assembly a,Product d where mb.hardware_serial="' + serNum + \
                '" and mb.prod_id=ap.prod_id and ap.assem_id=a.assem_id' + \
                ' and a.prod_id=d.prod_id'
        elif DOMProdTestUtil.isDOMSerial(serNum):
            query = 'select prod_id from Product where tag_serial="' + \
                serNum + '"'
        else:
            return None

        cursor = self.cursor()
        cursor.execute(query)

        if int(cursor.rowcount) != 1:
            result = None
        else:
            result = cursor.fetchone()[0]
        cursor.close()

        return result

    def getMainBoardId(self, serNum):
        """
        get the product ID for the main board associated with the
        specified serial number
        """

        if DOMProdTestUtil.isMainBoardSerial(serNum):
            query = 'select prod_id from Product where hardware_serial="' + \
                serNum + '"'
        elif DOMProdTestUtil.isDOMSerial(serNum):
            query = 'select mb.prod_id from Product mb,AssemblyProduct ap' + \
                ',Assembly a,Product d where d.tag_serial="' + serNum + \
                '" and d.prod_id=a.prod_id and a.assem_id=ap.assem_id' + \
                ' and ap.prod_id=mb.prod_id'
        else:
            return None

        cursor = self.db.cursor()
        cursor.execute(query)

        if int(cursor.rowcount) != 1:
            result = None
        else:
            result = cursor.fetchone()[0]
        cursor.close()

        return result

    def getProductId(self, serNum):
        """get the product ID for the specified serial number"""
        if DOMProdTestUtil.isMainBoardSerial(serNum):
            query = 'select prod_id from Product where hardware_serial="' + \
                serNum + '"'
        elif DOMProdTestUtil.isDOMSerial(serNum):
            query = 'select prod_id from Product where tag_serial="' + \
                serNum + '"'
        else:
            return None

        cursor = self.db.cursor()
        cursor.execute(query)

        if int(cursor.rowcount) != 1:
            result = None
        else:
            result = cursor.fetchone()[0]
        cursor.close()

        return result

class FATData(object):
    def __init__(self, name, startDate, endDate, comment, id=None):
        self.id = id
        self.labId = None
        self.name = name
        self.startDate = startDate
        self.endDate = endDate
        self.comment = comment

    def exists(self, db, name):
        if name is None:
            return False

        labId = db.getLabId()

        cursor = db.executeQuery(('select fat_id from FAT where name="%s"' +
                                  ' and lab_id=%d') % (name, labId))
        rtnVal = (int(cursor.rowcount) > 0)
        cursor.close()

        return rtnVal

    exists = classmethod(exists)

    def save(self, db):
        if self.id is not None:
            raise_(IOError, "FAT '" + self.name + \
                "' has already been saved")

        if self.labId is None:
            self.labId = db.getLabId()

        self.id = DOMProdTestUtil.getNextId(db, 'FAT', 'fat_id')

        cursor = db.cursor()
        cursor.execute(('insert into FAT(fat_id,lab_id,name,start_date' +
                        ',end_date' +
                        ',comment)values(%d,%d,%s,%s,%s,%s)') %
                       (self.id, self.labId,
                        DOMProdTestUtil.quoteStr(self.name),
                        DOMProdTestUtil.quoteStr(self.startDate),
                        DOMProdTestUtil.quoteStr(self.endDate),
                        DOMProdTestUtil.quoteStr(self.comment)))

        cursor.close()

        return self.id

class FATRun(object):
    """'fat_run' data from 'domprodtest' database"""

    def __init__(self, db):
        self.fatRunCache = {}
        cursor = db.executeQuery('select fat_id,name,start_date,end_date' +
                                 ',comment from FAT order by fat_id')
        while int(cursor.rowcount) > 0:
            row = cursor.fetchone()
            if row is None:
                break

            #print "FETCHED " + str(row) + " (" + str(type(row)) + ")"
            (id, name, startDate, endDate, comment) = row
            self.fatRunCache[name] = FATData(name, startDate, endDate,
                                             comment, id)

        cursor.close()

    def getId(self, name):
        if name not in self.fatRunCache:
            return None
        return self.fatRunCache[name].id

    def isName(self, name):
        return name in self.fatRunCache

