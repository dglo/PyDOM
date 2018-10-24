#!/usr/bin/env python
#
# RebootFile unit tests

import time
import unittest
from icecube.domtest.DOMProdTestDB import DOMProdTestDB
from icecube.domtest.RebootFile import DOM, RebootFile
from MockDB import MockDB, MockConnection, MockCursor
import cStringIO

#class FakeData:
#    def __init__(self, baseId):
#        self.mbSerial = '%06x%06x' % (baseId, baseId + 16)
#        self.maxTemp = baseId + 12.34
#        self.minTemp = baseId + 1.234
#        self.avgTemp = baseId + 6.78
#        self.maxHV = baseId + 234
#        self.minHV = baseId + 123
#        self.avgHV = baseId + 178
#        self.maxPT = baseId + 34.56
#        self.minPT = baseId + 3.456
#        self.avgPT = baseId + 18.76
#        self.maxRate = baseId + 456
#        self.minRate = baseId + 321
#        self.avgRate = baseId + 388.888
#        self.width = baseId + 56.7
#        self.const = baseId + 678.9
#        self.numSpikes = baseId + 7
#        self.r2 = baseId + 8.90
#        self.histo = [0, baseId / 10, baseId, baseId / 2, baseId / 5, 0]

class testDOM(unittest.TestCase):
    """Unit tests for DOM class"""

    def addProdIdQueries(self, conn, name, nameId, mbId, prodId):
        cursor = MockCursor('GetIdByName')
        conn.addCursor(cursor)

        qry = "select prod_id from ProductName where name='" + name + "'"
        if nameId is not None:
            cursor.addExpectedExecute(qry, nameId)
        else:
            cursor.addExpectedExecute(qry)

            cursor = MockCursor('GetIdByMBId')
            conn.addCursor(cursor)

            qry = 'select d.prod_id from Product mb,AssemblyProduct ap' + \
                ',Assembly a,Product d where mb.hardware_serial="' + mbId + \
                '" and mb.prod_id=ap.prod_id and ap.assem_id=a.assem_id' + \
                ' and a.prod_id=d.prod_id'
            if prodId is not None:
                cursor.addExpectedExecute(qry, prodId)
            else:
                cursor.addExpectedExecute(qry)

    def addRebootFailure(self, cursor, rebootId, sqlDate, prevTemp, nextTemp):
        if prevTemp is None:
            prevStr = 'null'
        else:
            prevStr = '%f' % prevTemp

        if nextTemp is None:
            nextStr = 'null'
        else:
            nextStr = '%f' % nextTemp

        qry = ('insert into FATRebootFail(fat_reboot_id,datetime,prev_temp' +
               ',next_temp)values(%d,"%s",%s,%s)' %
               (rebootId, sqlDate, prevStr, nextStr))
        cursor.addExpectedExecute(qry)

    def addRebootInsert(self, cursor, fatId, prodId, rebootId,
                        numSuccess, numFailed):
        qry = 'insert into FATReboot(fat_reboot_id,fat_id,prod_id' + \
            ',num_success,num_failed)values(' + str(rebootId) + \
            ',' + str(fatId) + ',' + str(prodId) + ',' + str(numSuccess) + \
            ',' + str(numFailed) + ')'
        cursor.addExpectedExecute(qry)

    def addRebootQuery(self, cursor, fatId, prodId,
                       rebootId=None, numSuccess=None, numFailed=None):
        qry = 'select fat_reboot_id,num_success,num_failed' + \
            ' from FATReboot where fat_id=' + str(fatId) + \
            ' and prod_id=' + str(prodId)
        if rebootId is None:
            cursor.addExpectedExecute(qry)
        else:
            cursor.addExpectedExecute(qry, (rebootId, numSuccess, numFailed))

    def addRebootUpdate(self, cursor, fatId, prodId, rebootId,
                        numSuccess, numFailed):
        qry = 'update FATReboot set num_success=' + str(numSuccess) + \
            ',num_failed=' + str(numFailed) + \
            ' where fat_reboot_id=' + str(rebootId)
        cursor.addExpectedExecute(qry)

    def testProdId(self):
        name = 'foo'
        mbId = '012345fedcba'

        fatId = 123
        rebootId = 456
        prodId = 789

        for i in range(3):
            dom = DOM(name, mbId)

            conn = MockConnection()

            dptDB = DOMProdTestDB(conn)

            if i == 0:
                self.addProdIdQueries(conn, name, None, mbId, None)
            elif i == 1:
                self.addProdIdQueries(conn, name, None, mbId, prodId)
            else:
                self.addProdIdQueries(conn, name, prodId, mbId, prodId)

            if i > 0:
                cursor = MockCursor('MainCursor')
                conn.addCursor(cursor)

                self.addRebootQuery(cursor, fatId, prodId)
                self.addRebootInsert(cursor, fatId, prodId, rebootId, 0, 0)

            try:
                dom.insert(dptDB, rebootId, fatId)
                if i == 0:
                    self.fail('Expected unknown Product to fail')
            except ValueError as data:
                if i > 0:
                    self.fail('Did not expect insert to fail: ' +
                              str(data))

            conn.verify()

    def testNoData(self):
        name = 'foo'
        mbId = '012345fedcba'

        fatId = 123
        rebootId = 456
        prodId = 789

        dom = DOM(name, mbId)

        conn = MockConnection()

        dptDB = DOMProdTestDB(conn)

        self.addProdIdQueries(conn, name, prodId, mbId, prodId)

        for i in range(2):
            cursor = MockCursor('MainCursor')
            conn.addCursor(cursor)

            if i == 0:
                self.addRebootQuery(cursor, fatId, prodId)
                self.addRebootInsert(cursor, fatId, prodId, rebootId, 0, 0)
            else:
                self.addRebootQuery(cursor, fatId, prodId,
                                    rebootId, 0, 0)
                self.addRebootUpdate(cursor, fatId, prodId, rebootId, 0, 0)

            dom.insert(dptDB, rebootId, fatId)

    def testFailures(self):
        name = 'foo'
        mbId = '012345fedcba'

        fatId = 123
        rebootId = 456
        prodId = 789

        dom = DOM(name, mbId)

        conn = MockConnection()

        dptDB = DOMProdTestDB(conn)

        self.addProdIdQueries(conn, name, prodId, mbId, prodId)

        failTime = (2005, 8, 5, 17, 25, 33, 4, 217, -1)
        failDateStr = '%04d-%02d-%02d %02d:%02d:%02d' % \
            (failTime[0], failTime[1], failTime[2],
             failTime[3], failTime[4], failTime[5])

        dom.addFailure(failTime, 'some text')

        for i in range(2):
            newList = []
            for d in failTime:
                newList.append(d)

            if i == 0:
                newList[3] = newList[3] - 3
                utime = time.mktime(newList)
                temp = -12.34
            else:
                newList[3] = newList[3] + 3
                utime = time.mktime(newList)
                temp = -43.21

            dom.addSuccess(newList, utime, temp)

        for i in range(2):
            cursor = MockCursor('MainCursor')
            conn.addCursor(cursor)

            if i == 0:
                self.addRebootQuery(cursor, fatId, prodId)
                self.addRebootInsert(cursor, fatId, prodId, rebootId, 2, 1)
                self.addRebootFailure(cursor, rebootId, failDateStr,
                                      None, None)
            else:
                dom.fillFailures()
                self.addRebootQuery(cursor, fatId, prodId,
                                    rebootId, 0, 0)
                self.addRebootUpdate(cursor, fatId, prodId, rebootId, 2, 1)
                self.addRebootFailure(cursor, rebootId, failDateStr,
                                      -12.34, -43.21)

            dom.insert(dptDB, rebootId, fatId)

        conn.verify()

class testRebootFile(unittest.TestCase):
    """Unit tests for RebootFile class"""

    def fakeSuccess(self, hub, dorAddr, timeList, name, mbId, temp):
        utime = time.mktime(timeList)
        return ('%s %03.3d %d-%02d-%02d %d:%02d:%02d %s' +
                " %11.1f %s %s %7.2f\n") % \
                (hub, dorAddr, timeList[0], timeList[1], timeList[2],
                 timeList[3], timeList[4], timeList[5], 'GMT', utime, name,
                 mbId, temp)

    def fakeFailure(self, hub, dorAddr, timeList):
        return ('%s %03.3d %d-%02d-%02d %d:%02d:%02d %s' +
                " COMMUNICATION FAILURE\n") % \
                (hub, dorAddr, timeList[0], timeList[1], timeList[2],
                 timeList[3], timeList[4], timeList[5], 'CDT')

    def testDeleteOldRows(self):
        conn = MockConnection()

        dptDB = DOMProdTestDB(conn)

        fatId = 123
        rebootId = 456

        cursor = MockCursor('delete')
        conn.addCursor(cursor)

        qry = 'select fat_reboot_id from FATReboot where fat_id=' + str(fatId)
        cursor.addExpectedExecute(qry, rebootId)

        qry = 'delete from FATRebootFail where fat_reboot_id=' + str(rebootId)
        cursor.addExpectedExecute(qry)

        qry = 'delete from FATReboot where fat_id=' + str(fatId)
        cursor.addExpectedExecute(qry)

        RebootFile.deleteOldRows(dptDB, fatId)

        conn.verify()

    def testReadEmpty(self):
        strIO = cStringIO.StringIO('')
        results = RebootFile.read(strIO)
        self.assertEqual(results, None,
                        'Expected no results')

    def testReadOneResult(self):
        hub = 'fakehub'
        dorAddr = 611
        timeList = (2005, 5, 20, 20, 5, 20, 5, 205, -1)
        name = 'foo'
        mbId = '012345fedcba'
        temp = -10.10

        lcStr = self.fakeSuccess(hub, dorAddr, timeList, name, mbId, temp)
        strIO = cStringIO.StringIO(lcStr)
        results = RebootFile.read(strIO)
        self.failUnless(isinstance(results, dict),
                        'Expected RebootFile.read() to return' +
                        ' a dictionary object, not ' + str(type(results)))
        self.assertEqual(len(results), 1,
                        'Expected 1 result, not ' + str(len(results)))
        for k in results.keys():
            self.assertEqual(results[k].name, name,
                             'Expected ' + k + ' name to be ' + name +
                             ', not ' + results[k].name)
            self.assertEqual(results[k].mbId, mbId,
                             'Expected ' + k + ' main board to be ' + mbId +
                             ', not ' + results[k].mbId)
            self.assertEqual(results[k].prodId, None,
                             'Did not expect ' + k + ' product ID to be set')
            self.assertEqual(len(results[k].success), 1,
                             'Expected one success for ' + k + ', not ' +
                             str(len(results[k].success)))
            self.assertEqual(len(results[k].failure), 0,
                             'Expected no failures for ' + k + ', not ' +
                             str(len(results[k].failure)))

    def testReadManyResults(self):
        hub = 'fakehub'
        dorAddr = 611
        baseTime = (2005, 5, 20, 1, 5, 20, 5, 205, -1)
        name = 'foo'
        mbId = '012345fedcba'
        temp = -10.10

        expSuccess = 0
        expFail = 0

        lcStr = ''
        for i in range(5):
            thisTime = []
            for t in baseTime:
                thisTime.append(t)
            thisTime[3] = i

            if i == 2 or i == 4:
                lcStr = lcStr + self.fakeFailure(hub, dorAddr, thisTime)
                expFail = expFail + 1
            else:
                lcStr = lcStr + self.fakeSuccess(hub, dorAddr, thisTime,
                                                 name, mbId, temp)
                expSuccess = expSuccess + 1

        strIO = cStringIO.StringIO(lcStr)
        results = RebootFile.read(strIO)
        self.failUnless(isinstance(results, dict),
                        'Expected RebootFile.read() to return' +
                        ' a dictionary object, not ' + str(type(results)))
        self.assertEqual(len(results), 1,
                        'Expected 1 result, not ' + str(len(results)))
        for k in results.keys():
            self.assertEqual(results[k].name, name,
                             'Expected ' + k + ' name to be ' + name +
                             ', not ' + results[k].name)
            self.assertEqual(results[k].mbId, mbId,
                             'Expected ' + k + ' main board to be ' + mbId +
                             ', not ' + results[k].mbId)
            self.assertEqual(results[k].prodId, None,
                             'Did not expect ' + k + ' product ID to be set')
            self.assertEqual(len(results[k].success), expSuccess,
                             'Expected ' + str(expSuccess) + \
                             ' successes for ' + k + ', not ' +
                             str(len(results[k].success)))
            self.assertEqual(len(results[k].failure), expFail,
                             'Expected ' + str(expFail) + ' failures for ' + \
                             k + ', not ' + str(len(results[k].failure)))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testDOM))
    suite.addTest(unittest.makeSuite(testRebootFile))
    return suite

if __name__ == '__main__':
    unittest.main()
