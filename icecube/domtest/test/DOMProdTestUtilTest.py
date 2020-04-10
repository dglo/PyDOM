#!/usr/bin/env python
#
# DOMProdTestUtil unit tests

from builtins import str
from builtins import range
import unittest
from icecube.domtest.DOMProdTestUtil import getNextId, isDOMSerial, quoteStr
from icecube.domtest.DOMProdTestDB import DOMProdTestDB
from MockDB import MockDB, MockConnection, MockCursor

class testDOMProdTestUtil(unittest.TestCase):
    """Unit tests for DOMProdTestUtil module"""

    def testGetNextIdFirst(self):
        conn = MockConnection()

        dptDB = DOMProdTestDB(conn)

        tblName = "Table"
        colName = "Column"
        expId = 1

        cursor = MockCursor("NoNextId")
        conn.addCursor(cursor)

        qry = 'select max(' + colName + ') from ' + tblName
        cursor.addExpectedExecute(qry, None)

        id = getNextId(dptDB, tblName, colName)
        self.assertEqual(id, expId, "Expected empty query to return 1")

        conn.verify()

    def testGetNextId(self):
        conn = MockConnection()

        dptDB = DOMProdTestDB(conn)

        tblName = "Table"
        colName = "Column"
        expId = 123

        cursor = MockCursor("NoNextId")
        conn.addCursor(cursor)

        qry = 'select max(' + colName + ') from ' + tblName
        cursor.addExpectedExecute(qry, (expId - 1, ))

        id = getNextId(dptDB, tblName, colName)
        self.assertEqual(id, expId, "Unexpected next ID")

        conn.verify()

    def testIsDOMSerialFalse(self):
        bad = [
            None,
            "",
            "XXXXXXXX",
            "XXXX0000",
            "XX3X0000",
            "XX3P000X",
            "XX300P0000",
            "XX313P0000",
            "XX312X0000",
            "DFLRefXX",
            "TSLRefXX",
            "DSYRefXX",
            "DFLSynXX",
            "ABCTstXX",
            ]

        for badStr in bad:
            self.assert_(not isDOMSerial(badStr),
                         "Shouldn't have recognized " + str(badStr))

    def testIsDOMSerialTrue(self):
        serial = "          "

        for c in "ATUX":
            for u in "EKPVX":
                for y in "3456789ABCD":
                    for l in "PHY":
                        for n in range(1, 10000, 666):
                            serial = '%c%c%c%c%04d' % (c, u, y, l, n)
                            self.assert_(isDOMSerial(serial),
                                         "Should have recognized " + serial)

    def testQuoteStr(self):
        tstVal = [
            [ None, 'null' ],
            [ 'xyz', '"xyz"' ],
            ]

        for val, expected in tstVal:
            quoted = quoteStr(val)
            self.assertEquals(expected, quoted,
                              "Expected [" + str(val) + "] to be quoted as [" +
                              expected + "], not [" + quoted + "]")

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testDOMProdTestUtil))
    return suite

if __name__ == '__main__':
    unittest.main()
