#!/usr/bin/env python
#
# DOMProdTestDB unit tests

import socket
import unittest
from icecube.domtest.DOMProdTestDB import DOMProdTestDB, FATData, FATRun
from MockDB import MockDB, MockConnection, MockCursor

class testDOMProdTestDB(unittest.TestCase):
    """Unit tests for DOMProdTestDB module"""

    def setUp(self):
        self.conn = MockConnection()

    def tearDown(self):
        self.conn.verify()

    def testGetDOMIdNone(self):
        dptDB = DOMProdTestDB(self.conn)

        domTag = 'TEDY1234'
        expId = None

        cursor = MockCursor("NoResult")
        self.conn.addCursor(cursor)

        qry = 'select prod_id from Product where tag_serial="' + domTag + '"'
        cursor.addExpectedExecute(qry, None)

        id = dptDB.getDOMId(domTag)
        self.assertEqual(id, expId, "Expected empty query to return None")

    def testGetDOMIdDirect(self):
        dptDB = DOMProdTestDB(self.conn)

        domTag = 'TEDY1234'
        expId = 12345

        cursor = MockCursor("Direct")
        self.conn.addCursor(cursor)

        qry = 'select prod_id from Product where tag_serial="' + domTag + '"'
        cursor.addExpectedExecute(qry, (expId, ))

        id = dptDB.getDOMId(domTag)
        self.assertEqual(id, expId, "Expected ID#" + str(expId) +
                         ", got ID#" + str(id))

    def testGetDOMIdIndirect(self):
        dptDB = DOMProdTestDB(self.conn)

        mbSerial = 'fedcba543210'
        expId = 12345

        cursor = MockCursor("Indirect")
        self.conn.addCursor(cursor)

        qry = 'select d.prod_id' + \
            ' from Product mb,AssemblyProduct ap,Assembly a,Product d' + \
            ' where mb.hardware_serial="' + mbSerial + '"' + \
            ' and mb.prod_id=ap.prod_id and ap.assem_id=a.assem_id' + \
            ' and a.prod_id=d.prod_id'
        cursor.addExpectedExecute(qry, (expId, ))

        id = dptDB.getDOMId(mbSerial)
        self.assertEqual(id, expId, "Expected ID#" + str(expId) +
                         ", got ID#" + str(id))

    def testGetLabIdByNameNone(self):
        dptDB = DOMProdTestDB(self.conn)

        hostName = 'foo.bar.com'
        expId = None

        cursor = MockCursor("LabNameNone")

        qry = 'select lab_id from Laboratory where name="' + hostName + '"'
        cursor.addExpectedExecute(qry, None)

        id = dptDB.getLabIdByName(cursor, hostName)
        self.assertEqual(id, expId, "Expected getLabIdByName to return " +
                         str(expId) + ", not " + str(id))

        cursor.verify()

    def testGetLabIdByName(self):
        dptDB = DOMProdTestDB(self.conn)

        hostName = 'foo.bar.com'
        expId = 12345

        cursor = MockCursor("LabName")

        qry = 'select lab_id from Laboratory where name="' + hostName + '"'
        cursor.addExpectedExecute(qry, (expId, ))

        id = dptDB.getLabIdByName(cursor, hostName)
        self.assertEqual(id, expId, "Expected getLabIdByName to return " +
                         str(expId) + ", not " + str(id))

        cursor.verify()

    def testGetLabIdByMachNone(self):
        dptDB = DOMProdTestDB(self.conn)

        hostName = 'foo.bar.com'
        expId = None

        cursor = MockCursor("LabMachNone")

        tmpName = hostName
        while True:
            qry = 'select lab_id from LabMachine where machine="' + tmpName + \
                '"'
            cursor.addExpectedExecute(qry, None)

            dot = tmpName.find('.')
            if dot < 0:
                break

            tmpName = tmpName[dot + 1:]

        id = dptDB.getLabIdByMachine(cursor, hostName)
        self.assertEqual(id, expId, "Expected getLabIdByName to return " +
                         str(expId) + ", not " + str(id))

        cursor.verify()

    def testGetLabIdByMach(self):
        dptDB = DOMProdTestDB(self.conn)

        pieces = ['foo', 'bar', 'com']

        hostName = '.'.join(pieces)
        expId = 12345

        for i in range(len(pieces)):
            cursor = MockCursor("LabMach#" + str(i))

            n = 0
            tmpName = hostName
            while True:
                qry = 'select lab_id from LabMachine where machine="' + \
                    tmpName + '"'
                if n < i:
                    cursor.addExpectedExecute(qry, None)
                else:
                    cursor.addExpectedExecute(qry, (expId,))
                    break

                n = n + 1
                
                dot = tmpName.find('.')
                if dot < 0:
                    break

                tmpName = tmpName[dot + 1:]

            id = dptDB.getLabIdByMachine(cursor, hostName)
            self.assertEqual(id, expId,
                             "Expected getLabIdByName to return " +
                             str(expId) + ", not " + str(id))

            cursor.verify()

    def testGetLabIdNone(self):
        dptDB = DOMProdTestDB(self.conn)

        hostName = 'foo.bar.com'
        expId = None

        cursor = MockCursor("SubNameNone")
        self.conn.addCursor(cursor)

        qry = 'select lab_id from Laboratory where name="' + hostName + '"'
        cursor.addExpectedExecute(qry, None)

        cursor = MockCursor("SubMachNone")
        self.conn.addCursor(cursor)

        tmpName = hostName
        while True:
            qry = 'select lab_id from LabMachine where machine="' + tmpName + \
                '"'
            cursor.addExpectedExecute(qry, None)

            dot = tmpName.find('.')
            if dot < 0:
                break

            tmpName = tmpName[dot + 1:]

        try:
            id = dptDB.getLabId(hostName)
            self.fail("Expected getLabId(" + hostName + ") to fail")
        except IOError as msg:
            pass # expect this to fail

    def testGetLabIdRtnMach(self):
        dptDB = DOMProdTestDB(self.conn)

        pieces = ['foo', 'bar', 'com']

        hostName = '.'.join(pieces)
        expId = 12345

        for i in range(len(pieces)):
            cursor = MockCursor("SubNameNone#2x" + str(i))
            self.conn.addCursor(cursor)

            qry = 'select lab_id from Laboratory where name="' + hostName + '"'
            cursor.addExpectedExecute(qry, None)

            cursor = MockCursor("SubMachRtn#" + str(i))
            self.conn.addCursor(cursor)

            n = 0
            tmpName = hostName
            while True:
                qry = 'select lab_id from LabMachine where machine="' + \
                    tmpName + '"'
                if n < i:
                    cursor.addExpectedExecute(qry, None)
                else:
                    cursor.addExpectedExecute(qry, (expId,))
                    break

                n = n + 1
                
                dot = tmpName.find('.')
                if dot < 0:
                    break

                tmpName = tmpName[dot + 1:]

            id = dptDB.getLabId(hostName)
            self.assertEqual(id, expId,
                             "Expected getLabId to return " +
                             str(expId) + ", not " + str(id))

    def testGetLabIdRtnName(self):
        dptDB = DOMProdTestDB(self.conn)

        hostName = 'foo.bar.com'
        expId = 12345

        cursor = MockCursor("SubName")
        self.conn.addCursor(cursor)

        qry = 'select lab_id from Laboratory where name="' + hostName + '"'
        cursor.addExpectedExecute(qry, (expId,))

        id = dptDB.getLabId(hostName)
        self.assertEqual(id, expId, "Expected getLabId to return " +
                         str(expId) + ", not " + str(id))

    def testGetMainBoardIdNone(self):
        dptDB = DOMProdTestDB(self.conn)

        mbSerial = 'fedcba543210'
        expId = None

        cursor = MockCursor("NoResult")
        self.conn.addCursor(cursor)

        qry = 'select prod_id from Product where hardware_serial="' + \
            mbSerial + '"'
        cursor.addExpectedExecute(qry, None)

        id = dptDB.getMainBoardId(mbSerial)
        self.assertEqual(id, expId, "Expected empty query to return None")

    def testGetMainBoardIdDirect(self):
        dptDB = DOMProdTestDB(self.conn)

        mbSerial = 'fedcba543210'
        expId = 12345

        cursor = MockCursor("Direct")
        self.conn.addCursor(cursor)

        qry = 'select prod_id from Product' + \
            ' where hardware_serial="' + mbSerial + '"'
        cursor.addExpectedExecute(qry, (expId, ))

        id = dptDB.getMainBoardId(mbSerial)
        self.assertEqual(id, expId, "Expected ID#" + str(expId) +
                         ", got ID#" + str(id))

    def testGetMainBoardIdIndirect(self):
        dptDB = DOMProdTestDB(self.conn)

        domTag = 'TEDY1234'
        expId = 12345

        cursor = MockCursor("Indirect")
        self.conn.addCursor(cursor)

        qry = 'select mb.prod_id' + \
            ' from Product mb,AssemblyProduct ap,Assembly a,Product d' + \
            ' where d.tag_serial="' + domTag + '" and d.prod_id=a.prod_id' + \
            ' and a.assem_id=ap.assem_id and ap.prod_id=mb.prod_id'
        cursor.addExpectedExecute(qry, (expId, ))

        id = dptDB.getMainBoardId(domTag)
        self.assertEqual(id, expId, "Expected ID#" + str(expId) +
                         ", got ID#" + str(id))

    def testGetProductMB(self):
        dptDB = DOMProdTestDB(self.conn)

        mbSerial = 'fedcba543210'
        expId = 12345

        cursor = MockCursor("Direct")
        self.conn.addCursor(cursor)

        qry = 'select prod_id from Product' + \
            ' where hardware_serial="' + mbSerial + '"'
        cursor.addExpectedExecute(qry, (expId, ))

        id = dptDB.getProductId(mbSerial)
        self.assertEqual(id, expId, "Expected ID#" + str(expId) +
                         ", got ID#" + str(id))

    def testGetProductDOM(self):
        dptDB = DOMProdTestDB(self.conn)

        domTag = 'TEDY1234'
        expId = 12345

        cursor = MockCursor("Indirect")
        self.conn.addCursor(cursor)

        qry = 'select prod_id from Product' + \
            ' where tag_serial="' + domTag + '"'
        cursor.addExpectedExecute(qry, (expId, ))

        id = dptDB.getProductId(domTag)
        self.assertEqual(id, expId, "Expected ID#" + str(expId) +
                         ", got ID#" + str(id))

class testFATData(unittest.TestCase):
    """Unit tests for FATData class"""

    def addMockLabIdQuery(self, id):
        hostName = socket.gethostname()

        cursor = MockCursor("GetLabId")
        self.conn.addCursor(cursor)

        qry = 'select lab_id from Laboratory where name="' + hostName + '"'
        cursor.addExpectedExecute(qry, (id,))

    def setUp(self):
        self.conn = MockConnection()

    def tearDown(self):
        pass #self.conn.verify()

    def testNotExists(self):
        dptDB = DOMProdTestDB(self.conn)

        expLabId = 12345
        self.addMockLabIdQuery(expLabId)

        runName = 'A FAT RUN'
        expId = None

        cursor = MockCursor("NotExists")
        self.conn.addCursor(cursor)

        qry = 'select fat_id from FAT where name="' + runName + \
            '" and lab_id=' + str(expLabId)
        cursor.addExpectedExecute(qry, None)

        self.failIf(FATData.exists(dptDB, runName),
                    'Run ' + runName + ' should not exist')

    def testExists(self):
        dptDB = DOMProdTestDB(self.conn)

        expLabId = 12345
        self.addMockLabIdQuery(expLabId)

        runName = 'A FAT RUN'
        expId = 12345

        cursor = MockCursor("NoResult")
        self.conn.addCursor(cursor)

        qry = 'select fat_id from FAT where name="' + runName + \
            '" and lab_id=' + str(expLabId)
        cursor.addExpectedExecute(qry, (expId, ))

        self.failUnless(FATData.exists(dptDB, runName),
                        'Run ' + runName + ' should exist')

    def testSaveFirst(self):
        dptDB = DOMProdTestDB(self.conn)

        expLabId = 12345
        self.addMockLabIdQuery(expLabId)

        runName = 'A FAT RUN'
        startDate = '2005-08-04'
        expId = 1

        cursor = MockCursor("FirstRun")
        self.conn.addCursor(cursor)

        qry = 'select max(fat_id) from FAT'
        cursor.addExpectedExecute(qry, None)

        cursor = MockCursor("SaveFirst")
        self.conn.addCursor(cursor)

        ins = 'insert into FAT(fat_id,lab_id,name,start_date,end_date' + \
            ',comment)values(' + str(expId) + ',' + str(expLabId) + ',"' + \
            runName + '","' + startDate + '",null,null)'
        cursor.addExpectedExecute(ins)

        data = FATData(runName, startDate, None, None)

        data.save(dptDB)

    def testSave(self):
        dptDB = DOMProdTestDB(self.conn)

        expLabId = 12345
        self.addMockLabIdQuery(expLabId)

        runName = 'A FAT RUN'
        startDate = '2005-08-04'
        expId = 1234

        cursor = MockCursor("GetNextId")
        self.conn.addCursor(cursor)

        qry = 'select max(fat_id) from FAT'
        cursor.addExpectedExecute(qry, (expId - 1, ))

        cursor = MockCursor("Save")
        self.conn.addCursor(cursor)

        ins = 'insert into FAT(fat_id,lab_id,name,start_date,end_date' + \
            ',comment)values(' + str(expId) + ',' + str(expLabId) + ',"' + \
            runName + '","' + startDate + '",null,null)'
        cursor.addExpectedExecute(ins)

        data = FATData(runName, startDate, None, None)

        data.save(dptDB)

class testFATRun(unittest.TestCase):
    """Unit tests for FATRun class"""

    def setUp(self):
        self.conn = MockConnection()

    def tearDown(self):
        self.conn.verify()

    def testNoRuns(self):
        dptDB = DOMProdTestDB(self.conn)

        runName = 'A FAT RUN'

        cursor = MockCursor("Empty")
        self.conn.addCursor(cursor)

        qry = 'select fat_id,name,start_date,end_date,comment' + \
            ' from FAT order by fat_id'
        cursor.addExpectedExecute(qry, None)

        run = FATRun(dptDB)

        self.failIf(run.isName(runName),
                    'Run ' + runName + ' should not exist')
        self.assertEqual(None, run.getId(runName),
                         'Should not have ID for run ' + runName)

    def testOneRun(self):
        dptDB = DOMProdTestDB(self.conn)

        runName = 'A FAT RUN'
        expId = 123
        startDate = '2005-08-04'

        cursor = MockCursor("Empty")
        self.conn.addCursor(cursor)

        qry = 'select fat_id,name,start_date,end_date,comment' + \
            ' from FAT order by fat_id'
        cursor.addExpectedExecute(qry, (expId, runName, startDate, None, None))

        run = FATRun(dptDB)

        self.failUnless(run.isName(runName),
                        'Run ' + runName + ' should exist')
        self.assertEqual(expId, run.getId(runName),
                         'Unexpected ID for run ' + runName)

    def testTwoRuns(self):
        dptDB = DOMProdTestDB(self.conn)

        nameList = ['A FAT RUN', 'ANOTHER']
        idList = [123, 345]

        startDate = '2005-08-04'

        cursor = MockCursor("Empty")
        self.conn.addCursor(cursor)

        qry = 'select fat_id,name,start_date,end_date,comment' + \
            ' from FAT order by fat_id'
        cursor.addExpectedExecute(qry,
                                  (idList[0], nameList[0], startDate,
                                   None, None),
                                  (idList[1], nameList[1], startDate,
                                   '2005-08-05', 'A comment'))

        run = FATRun(dptDB)

        for i in range(len(nameList)):
            self.failUnless(run.isName(nameList[i]),
                            'Run ' + nameList[i] + ' should exist')
            self.assertEqual(idList[i], run.getId(nameList[i]),
                             'Unexpected ID for run ' + nameList[i])

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testDOMProdTestDB))
    suite.addTest(unittest.makeSuite(testFATData))
    suite.addTest(unittest.makeSuite(testFATRun))
    return suite

if __name__ == '__main__':
    unittest.main()
