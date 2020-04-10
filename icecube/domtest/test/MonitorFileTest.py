#!/usr/bin/env python
#
# MonitorFile unit tests

from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object
import unittest
from icecube.domtest.DOMProdTestDB import DOMProdTestDB
from icecube.domtest.MonitorFile import Monitor, MonData, MonitorFile
from MockDB import MockDB, MockConnection, MockCursor
import io

class testMonitor(unittest.TestCase):
    """Unit tests for Monitor class"""

    def setUp(self):
        self.conn = MockConnection()

    def tearDown(self):
        self.conn.verify()

    def fakeData(self, baseId):
        mbSerial = '%06x%06x' % (baseId, baseId + 16)
        maxTemp = baseId + 12.34
        minTemp = baseId + 1.234
        avgTemp = baseId + 6.78
        maxHV = baseId + 234
        minHV = baseId + 123
        avgHV = baseId + 178
        maxPT = baseId + 34.56
        minPT = baseId + 3.456
        avgPT = baseId + 18.76
        maxRate = baseId + 456
        minRate = baseId + 321
        avgRate = baseId + 388.888
        width = baseId + 56.7
        const = baseId + 678.9
        numSpikes = baseId + 7
        r2 = baseId + 8.90
        histo = [0, baseId / 10, baseId, baseId / 2, baseId / 5, 0]

        return MonData(mbSerial, maxTemp, minTemp, avgTemp,
                       maxHV, minHV, avgHV, maxPT, minPT, avgPT,
                       maxRate, minRate, avgRate, width, const, numSpikes, r2,
                       histo)

    def testBasic(self):
        dptDB = DOMProdTestDB(self.conn)

        mon = Monitor(12.34)

        mon.setBinSize(11)
        try:
            mon.setBinSize(12)
            fail('Should not be able to set binSize to different size')
        except ValueError:
            pass # expect this to fail

    def testInsertNoData(self):
        dptDB = DOMProdTestDB(self.conn)

        temp = 12.34
        binSize = 17

        mon = Monitor(temp)

        mon.setBinSize(binSize)

        monId = 123
        fatId = 456

        cursor = MockCursor("GetMonId")
        self.conn.addCursor(cursor)

        qry = 'select max(fat_mon_id) from FATMonitor'
        cursor.addExpectedExecute(qry, (monId - 1, ))

        cursor = MockCursor("InsMon")
        self.conn.addCursor(cursor)

        qry = 'insert into FATMonitor(fat_mon_id,fat_id,temp,binsize)' + \
              'values(' + str(monId) + ',' + str(fatId) + ',"' + \
              str(temp) + '",' + str(binSize) + ')'
        cursor.addExpectedExecute(qry, None)

        mon.insert(dptDB, fatId)

    def testInsert(self):
        dptDB = DOMProdTestDB(self.conn)

        temp = 12.34
        binSize = 17

        mon = Monitor(temp)

        mon.setBinSize(binSize)

        data = [self.fakeData(111111), self.fakeData(24680),
                self.fakeData(3691224)]
        for d in data:
            mon.append(d)

        monId = 123
        fatId = 456
        nextDataId = 789

        cursor = MockCursor("GetMonId")
        self.conn.addCursor(cursor)

        qry = 'select max(fat_mon_id) from FATMonitor'
        cursor.addExpectedExecute(qry, (monId - 1, ))

        cursor = MockCursor("InsMon")
        self.conn.addCursor(cursor)

        qry = 'insert into FATMonitor(fat_mon_id,fat_id,temp,binsize)' + \
              'values(' + str(monId) + ',' + str(fatId) + ',"' + \
              str(temp) + '",' + str(binSize) + ')'
        cursor.addExpectedExecute(qry, None)

        cursor = MockCursor("GetDataId")
        self.conn.addCursor(cursor)

        qry = 'select max(fat_mondata_id) from FATMonData'
        cursor.addExpectedExecute(qry, (nextDataId - 1, ))

        nextProdId = 333
        
        for i in range(len(data)):
            d = data[i]

            cursor = MockCursor("GetProdId#" + str(i))
            self.conn.addCursor(cursor)

            qry = 'select d.prod_id from Product mb,AssemblyProduct ap' + \
                  ',Assembly a,Product d' + \
              ' where mb.hardware_serial="' + d.mbId + \
              '" and mb.prod_id=ap.prod_id' + \
              ' and ap.assem_id=a.assem_id and a.prod_id=d.prod_id'
            cursor.addExpectedExecute(qry, (nextProdId, ))

            cursor = MockCursor("InsMonData#" + str(i))
            self.conn.addCursor(cursor)

            qry = ('insert into FATMonData(fat_mondata_id,fat_mon_id' +
                   ',prod_id,temp_max,temp_min,temp_avg' +
                   ',hv_max,hv_min,hv_avg,pt_max,pt_min,pt_avg' +
                   ',rate_max,rate_min,rate_avg' +
                   ',width,constant,num_spikes,r2)' +
                   'values(%d,%d' +
                   ',%d,%f,%f,%f' +
                   ',%d,%d,%d,%f,%f,%f' +
                   ',%d,%d,%f' +
                   ',%f,%f,%d,%f)') % \
                   (nextDataId, monId, nextProdId,
                    d.maxTemp, d.minTemp, d.avgTemp,
                    d.maxHV, d.minHV, d.avgHV,
                    d.maxPT, d.minPT, d.avgPT,
                    d.maxRate, d.minRate, d.avgRate,
                    d.width, d.const, d.numSpikes, d.r2)
            cursor.addExpectedExecute(qry)

            for bin in range(len(d.histo)):
                qry = 'insert into FATMonHisto(fat_mondata_id,bin,value)' + \
                      'values(%d,%d,%d)' % (nextDataId, bin, d.histo[bin])
                cursor.addExpectedExecute(qry)

            nextDataId = nextDataId + 1
            nextProdId = nextProdId + 1

        mon.insert(dptDB, fatId)

class testMonData(unittest.TestCase):
    """Unit tests for MonData class"""

    def setUp(self):
        self.conn = MockConnection()

    def tearDown(self):
        self.conn.verify()

    def testInit(self):
        dptDB = DOMProdTestDB(self.conn)

        mbSerial = '123fed456cba'
        maxTemp = 12.34
        minTemp = 1.234
        avgTemp = 6.78
        maxHV = 234
        minHV = 123
        avgHV = 178
        maxPT = 34.56
        minPT = 3.456
        avgPT = 18.76
        maxRate = 456
        minRate = 321
        avgRate = 388.888
        width = 56.7
        const = 678.9
        numSpikes = 7
        r2 = 8.90
        histo = [0, 0, 1, 5, 10, 7, 4, 1, 1, 1, 0, 0]

        mon = MonData(mbSerial, maxTemp, minTemp, avgTemp,
                      maxHV, minHV, avgHV, maxPT, minPT, avgPT,
                      maxRate, minRate, avgRate, width, const, numSpikes, r2,
                      histo)

        prodId = 777
        monId = 666
        dataId = 600

        cursor = MockCursor("GetProdId")
        self.conn.addCursor(cursor)

        qry = 'select d.prod_id from Product mb,AssemblyProduct ap' + \
              ',Assembly a,Product d' + \
              ' where mb.hardware_serial="' + mbSerial + \
              '" and mb.prod_id=ap.prod_id' + \
              ' and ap.assem_id=a.assem_id and a.prod_id=d.prod_id'
        cursor.addExpectedExecute(qry, (prodId, ))

        cursor = MockCursor("InsMonData")
        self.conn.addCursor(cursor)

        qry = ('insert into FATMonData(fat_mondata_id,fat_mon_id' +
                   ',prod_id,temp_max,temp_min,temp_avg' +
                   ',hv_max,hv_min,hv_avg,pt_max,pt_min,pt_avg' +
                   ',rate_max,rate_min,rate_avg' +
                   ',width,constant,num_spikes,r2)' +
                   'values(%d,%d' +
                   ',%d,%f,%f,%f' +
                   ',%d,%d,%d,%f,%f,%f' +
                   ',%d,%d,%f' +
                   ',%f,%f,%d,%f)') % \
                   (dataId, monId, prodId, maxTemp, minTemp, avgTemp,
                    maxHV, minHV, avgHV, maxPT, minPT, avgPT,
                    maxRate, minRate, avgRate, width, const, numSpikes, r2)
        cursor.addExpectedExecute(qry)

        for bin in range(len(histo)):
            qry = 'insert into FATMonHisto(fat_mondata_id,bin,value)' + \
                  'values(%d,%d,%d)' % (dataId, bin, histo[bin])
            cursor.addExpectedExecute(qry)

        mon.insert(dptDB, monId, dataId)

class FakeData(object):
    def __init__(self, baseId):
        self.mbSerial = '%06x%06x' % (baseId, baseId + 16)
        self.maxTemp = baseId + 12.34
        self.minTemp = baseId + 1.234
        self.avgTemp = baseId + 6.78
        self.maxHV = baseId + 234
        self.minHV = baseId + 123
        self.avgHV = baseId + 178
        self.maxPT = baseId + 34.56
        self.minPT = baseId + 3.456
        self.avgPT = baseId + 18.76
        self.maxRate = baseId + 456
        self.minRate = baseId + 321
        self.avgRate = baseId + 388.888
        self.width = baseId + 56.7
        self.const = baseId + 678.9
        self.numSpikes = baseId + 7
        self.r2 = baseId + 8.90
        self.histo = [0, baseId / 10, baseId, baseId / 2, baseId / 5, 0]

class testMonitorFile(unittest.TestCase):
    """Unit tests for MonitorFile class"""

    def buildMonStr(self, binSize, baseIdList):
        monStr = None
        for i in baseIdList:
            line = self.fakeLine(binSize, i)
            if monStr is None:
                monStr = line
            else:
                monStr = monStr + line

        return monStr

    def checkFakeData(self, md, baseId):
        f = FakeData(baseId)

        self.assertEqual(md.mbId, f.mbSerial, 'Bad mainboard serial')
        self.assertEqual(md.maxTemp, f.maxTemp, 'Bad max temperature')
        self.assertEqual(md.minTemp, f.minTemp, 'Bad min temperature')
        self.assertEqual(md.avgTemp, f.avgTemp, 'Bad avg temperature')
        self.assertEqual(md.maxHV, f.maxHV, 'Bad max high voltage')
        self.assertEqual(md.minHV, f.minHV, 'Bad min high voltage')
        self.assertEqual(md.avgHV, f.avgHV, 'Bad avg high voltage')
        self.assertEqual(md.maxPT, f.maxPT, 'Bad max P/T')
        self.assertEqual(md.minPT, f.minPT, 'Bad min P/T')
        self.assertEqual(md.avgPT, f.avgPT, 'Bad avg P/T')
        self.assertEqual(md.maxRate, f.maxRate, 'Bad max rate')
        self.assertEqual(md.minRate, f.minRate, 'Bad min rate')
        self.assertEqual(md.avgRate, f.avgRate, 'Bad avg rate')
        self.assertEqual(md.width, f.width, 'Bad width')
        self.assertEqual(md.const, f.const, 'Bad const')
        self.assertEqual(md.numSpikes, f.numSpikes, 'Bad num spikes')
        self.assertEqual(md.r2, f.r2, 'Bad R squared')

        for i in range(len(md.histo)):
            self.assertEquals(md.histo[i], f.histo[i],
                              'Bad histogram value#' + str(i))

    def fakeLine(self, binSize, baseId):
        f = FakeData(baseId)

        histoStr = None
        for h in f.histo:
            if histoStr is None:
                histoStr = str(h)
            else:
                histoStr = histoStr + ' ' + str(h)

        fmtStr = '%s %f %f %f %d %d %d %f %f %f %d %d %f %f %f %d %f %d' + \
                 ' : %s\n'
        return fmtStr % (f.mbSerial, f.maxTemp, f.minTemp, f.avgTemp,
                         f.maxHV, f.minHV, f.avgHV, f.maxPT, f.minPT, f.avgPT,
                         f.maxRate, f.minRate, f.avgRate, f.width, f.const,
                         f.numSpikes, f.r2, binSize, histoStr)

    def testDeleteOldRows(self):
        conn = MockConnection()

        dptDB = DOMProdTestDB(conn)

        fatId = 123
        monId = 456
        monDataId = 789

        cursor = MockCursor('delete')
        conn.addCursor(cursor)

        qry = 'select fat_mon_id from FATMonitor where fat_id=' + str(fatId)
        cursor.addExpectedExecute(qry, monId)

        qry = 'select fat_mondata_id from FATMonData where fat_mon_id=' + \
            str(monId)
        cursor.addExpectedExecute(qry, monDataId)

        qry = 'delete from FATMonHisto where fat_mondata_id=' + str(monDataId)
        cursor.addExpectedExecute(qry)

        qry = 'delete from FATMonData where fat_mon_id=' + str(monId)
        cursor.addExpectedExecute(qry)

        qry = 'delete from FATMonitor where fat_id=' + str(fatId)
        cursor.addExpectedExecute(qry)

        MonitorFile.deleteOldRows(dptDB, fatId)

        conn.verify()

    def testReadEmpty(self):
        strIO = io.StringIO('')
        results = MonitorFile.read(strIO, -12.3)
        self.failUnless(isinstance(results, Monitor),
                        'Expected MonitorFile.read() to return' +
                        ' a Monitor object')
        self.assertEqual(results.binSize, 0,
                        'Expected Monitor binSize to be zero')
        self.assertEqual(len(results.dataList), 0,
                        'Expected Monitor dataList to be empty')

    def testReadOneResult(self):
        binSize = 137
        baseId = 123456
        temp = -2.46

        lcStr = self.buildMonStr(binSize, [baseId])
        strIO = io.StringIO(lcStr)
        results = MonitorFile.read(strIO, temp)
        self.failUnless(isinstance(results, Monitor),
                        'Expected MonitorFile.read() to return' +
                        ' a Monitor object')
        self.assertEqual(results.binSize, binSize,
                        'Expected Monitor binSize to be ' + str(binSize))
        self.assertEqual(len(results.dataList), 1,
                        'Expected 1 MonData entry, not ' +
                         str(len(results.dataList)))

        self.checkFakeData(results.dataList[0], baseId)

    def testReadTwoResults(self):
        binSize = 137
        idList = [12345, 67890]
        temp = -2.46

        lcStr = self.buildMonStr(binSize, idList)
        strIO = io.StringIO(lcStr)
        results = MonitorFile.read(strIO, temp)
        self.failUnless(isinstance(results, Monitor),
                        'Expected MonitorFile.read() to return' +
                        ' a Monitor object')
        self.assertEqual(results.binSize, binSize,
                        'Expected Monitor binSize to be ' + str(binSize))
        self.assertEqual(len(results.dataList), len(idList),
                        'Expected ' + str(len(idList)) +
                         ' MonData entries, not ' + str(len(results.dataList)))

        self.checkFakeData(results.dataList[0], idList[0])
        self.checkFakeData(results.dataList[1], idList[1])

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testMonitor))
    suite.addTest(unittest.makeSuite(testMonData))
    suite.addTest(unittest.makeSuite(testMonitorFile))
    return suite

if __name__ == '__main__':
    unittest.main()
