#!/usr/bin/env python
#
# LCChainFile unit tests

import unittest
from icecube.domtest.DOMProdTestDB import DOMProdTestDB
from icecube.domtest.LCChainFile import TestResult, LCChainFile
from MockDB import MockDB, MockConnection, MockCursor
import cStringIO

class testTestResult(unittest.TestCase):
    """Unit tests for TestResult class"""

    def notChar(self, dir, descr):
        if dir == 0:
            ch = '!'
        else:
            ch = ' '
        return ch + descr

    def setUp(self):
        self.conn = MockConnection()

    def tearDown(self):
        self.conn.verify()

    def testIncomplete(self):
        dptDB = DOMProdTestDB(self.conn)

        fatId = 123

        for lo in range(1):
            if lo == 0:
                loDOM = None
            else:
                loDOM = 'UX3P0123'

            for hi in range(1):
                if lo == 1 and hi == 1:
                    continue

                if hi == 0:
                    hiDOM = None
                else:
                    hiDOM = 'AE3H0001'

                result = TestResult(loDOM, hiDOM)

                for set in range(1):
                    if set == 1:
                        result.setDownNeg(lo == 0)
                        result.setDownPos(hi == 1)
                        result.setUpNeg(lo == 0)
                        result.setUpPos(hi == 1)

                    self.failIf(result.isFilled(), 'Result[' + str(loDOM) +
                                '/' + str(hiDOM) +
                                '] should not claim to be filled')
                    self.failIf(result.isSuccess(), 'Result[' + str(loDOM) +
                                '/' + str(hiDOM) +
                                '] should not be a success')

                    try:
                        result.insert(dptDB, fatId)
                        fail('Result [' + str(loDOM) + '/' + str(hiDOM) +
                             '] insert should not succeed')
                    except ValueError:
                        pass # expect this to fail

    def testInsert(self):
        dptDB = DOMProdTestDB(self.conn)

        fatId = 123

        loDOM = 'UX3P0123'
        loId = 543

        hiDOM = 'AE3H0001'
        hiId = 678

        result = TestResult(loDOM, hiDOM)

        for dn in range(1):
            for dp in range(1):
                for un in range(1):
                    for up in range(1):
                        result.setDownNeg(dn == 1)
                        result.setDownPos(dp == 1)
                        result.setUpNeg(un == 1)
                        result.setUpPos(up == 1)

                        self.failUnless(result.isFilled(),
                                        'Result[' + str(loDOM) + '/' +
                                        str(hiDOM) + '] should be filled')
                        if (dn + dp + un + up) == 4:
                            self.failUnless(result.isSuccess(), 'Result[' +
                                            str(loDOM) + '/' + str(hiDOM) +
                                            '] should be a success')
                        else:
                            self.failIf(result.isSuccess(), 'Result[' +
                                        str(loDOM) + '/' + str(hiDOM) +
                                        '] should not be a success')

                        name = self.notChar(dn, 'D-') + \
                            self.notChar(dp, 'D+') + \
                            self.notChar(un, 'U-') + \
                            self.notChar(up, 'U+')

                        cursor = MockCursor(name + " LoDOM")
                        self.conn.addCursor(cursor)

                        qry = 'select prod_id from Product' + \
                            ' where tag_serial="' + loDOM + '"'
                        cursor.addExpectedExecute(qry, (loId, ))

                        cursor = MockCursor(name + " LoDOM")
                        self.conn.addCursor(cursor)

                        qry = 'select prod_id from Product' + \
                            ' where tag_serial="' + hiDOM + '"'
                        cursor.addExpectedExecute(qry, (hiId, ))

                        cursor = MockCursor(name + " Insert")
                        self.conn.addCursor(cursor)

                        qry = 'insert into FATLCChain(fat_id,hi_prod_id' + \
                            ',lo_prod_id,down_neg,down_pos,up_neg,up_pos)' + \
                            'values(' + str(fatId) + ',' + str(loId) + ',' + \
                            str(hiId) +  ',' + str(dn) + ',' + \
                            str(dp) + ',' + str(un) + ',' + str(up) + ')'
                        cursor.addExpectedExecute(qry)

                        result.insert(dptDB, fatId)

class testLCChainFile(unittest.TestCase):
    """Unit tests for LCChainFile class"""

    def buildLCStr(self, hubName, addr0, addr1, hiDOM, loDOM,
                   downNeg, downPos, upNeg, upPos):
        lcStr = 'Testing ' + hubName + ' ' + addr0 + ' to ' + \
            hubName + ' ' + addr1 + "\n" + \
            'High DOM: ' + hiDOM + "\n" + \
            'Low DOM: ' + loDOM + "\n"

        locNames = ['d_neg', 'd_pos', 'u_neg', 'u_pos']
        locVals = [downNeg, downPos, upNeg, upPos]

        for i in range(len(locNames)):
            if locVals[i]:
                pfStr = "PASSED\n"
            else:
                pfStr = "FAILED\n"

            locStr = 'Sending pulse_' + locNames[i] + "\n" + pfStr
            lcStr = lcStr + locStr

        if downNeg and downPos and upNeg and upPos:
            verdict = 'PASS'
        else:
            verdict = 'FAIL'

        return lcStr + 'LC pair test result: ' + verdict + "\n"

    def testDeleteOldRows(self):
        conn = MockConnection()

        dptDB = DOMProdTestDB(conn)

        fatId = 1234

        cursor = MockCursor('delete')
        conn.addCursor(cursor)

        qry = 'delete from FATLCChain where fat_id=' + str(fatId)
        cursor.addExpectedExecute(qry)

        LCChainFile.deleteOldRows(dptDB, fatId)

        conn.verify()

    def testReadEmpty(self):
        strIO = cStringIO.StringIO('')
        results = LCChainFile.read(strIO)
        self.failUnless(isinstance(results, list),
                        'Expected LCChainFile.read() to return a list')
        self.assertEqual(len(results), 0,
                        'Expected LCChainFile.read() to return an empty list')

    def testReadOneResult(self):
        hiDOM = '0123456789ab'
        loDOM = 'fedcba987654'
        dnNeg = True
        dnPos = False
        upNeg = False
        upPos = True

        lcStr = self.buildLCStr('hub', '01A', '01B', hiDOM, loDOM,
                                dnNeg, dnPos, upNeg, upPos)
        strIO = cStringIO.StringIO(lcStr)
        results = LCChainFile.read(strIO)
        self.failUnless(isinstance(results, list),
                        'Expected LCChainFile.read() to return a list')
        self.assertEqual(len(results), 1, 'Expected LCChainFile.read()' +
                         ' to return a single result')

        result = results[0]
        self.assertEqual(result.highDOM, hiDOM, 'Unexpected high DOM')
        self.assertEqual(result.lowDOM, loDOM, 'Unexpected low DOM')
        self.assertEqual(result.downNeg, dnNeg, 'Unexpected down-')
        self.assertEqual(result.downPos, dnPos, 'Unexpected down+')
        self.assertEqual(result.upNeg, upNeg, 'Unexpected up-')
        self.assertEqual(result.upPos, upPos, 'Unexpected up+')

    def testReadTwoResults(self):
        hiDOM = ['0123456789ab', '02468ace1357']
        loDOM = ['fedcba987654', 'fdb97531eca8']
        dnNeg = [True, True]
        dnPos = [False, True]
        upNeg = [False, True]
        upPos = [True, True]

        lcStr = ''
        for i in range(len(hiDOM)):
            lcStr = lcStr + self.buildLCStr('hub', '01A', '01B',
                                            hiDOM[i], loDOM[i], dnNeg[i],
                                            dnPos[i], upNeg[i], upPos[i])

        strIO = cStringIO.StringIO(lcStr)
        results = LCChainFile.read(strIO)
        self.failUnless(isinstance(results, list),
                        'Expected LCChainFile.read() to return a list')
        self.assertEqual(len(results), len(hiDOM),
                         'Expected LCChainFile.read() to return ' +
                         str(len(hiDOM)) + ' results')

        for i in range(len(hiDOM)):
            result = results[i]
            self.assertEqual(result.highDOM, hiDOM[i], 'Expected high DOM ' +
                             hiDOM[i] + ', not ' + result.highDOM)
            self.assertEqual(result.lowDOM, loDOM[i], 'Unexpected low DOM')
            self.assertEqual(result.downNeg, dnNeg[i], 'Unexpected down-')
            self.assertEqual(result.downPos, dnPos[i], 'Unexpected down+')
            self.assertEqual(result.upNeg, upNeg[i], 'Unexpected up-')
            self.assertEqual(result.upPos, upPos[i], 'Unexpected up+')

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testTestResult))
    suite.addTest(unittest.makeSuite(testLCChainFile))
    return suite

if __name__ == '__main__':
    unittest.main()
