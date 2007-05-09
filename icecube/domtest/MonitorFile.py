#!/usr/bin/env python
#
# Read monitor data and save it to the database

import os,re,sys
import DOMProdTestUtil
from DOMProdTestDB import DOMProdTestDB, FATRun

##############################################################################

class Monitor:
    """Monitor file metadata"""
    def __init__(self, temp):
        self.temp = temp
        self.binSize = 0
        self.dataList = []
        self.nextMonId = None
        self.nextDataId = None

    def append(self, monData):
        self.dataList.append(monData)

    def setBinSize(self, binSize):
        if self.binSize == 0:
            self.binSize = binSize
        elif self.binSize != binSize:
            raise ValueError, "Expected binSize of " + str(self.binSize) + \
                ", not " + str(binSize)

    def insert(self, db, fatId):
        if self.binSize == 0:
            sys.stderr.write("Warning: bin size was not set\n")

        if self.nextMonId is None:
            self.nextMonId = DOMProdTestUtil.getNextId(db, 'FATMonitor',
                                                       'fat_mon_id')

        monId = self.nextMonId
        self.nextMonId = self.nextMonId + 1

        cursor = db.cursor()

        cursor.execute('insert into FATMonitor(fat_mon_id,fat_id' +
                       ',temp,binsize)values(%d,%d,"%s",%d)' %
                       (monId, fatId, self.temp, self.binSize))

        for d in self.dataList:
            if self.nextDataId is None:
                self.nextDataId = DOMProdTestUtil.getNextId(db, 'FATMonData',
                                                            'fat_mondata_id')

            dataId = self.nextDataId
            self.nextDataId = self.nextDataId + 1

            d.insert(db, monId, dataId)

        cursor.close()

class MonData:
    """Monitor data"""

    def __init__(self, mbId, maxTemp, minTemp, avgTemp, maxHV, minHV, avgHV,
                 maxPT, minPT, avgPT, maxRate, minRate, avgRate,
                 width, const, numSpikes, r2, histo):
        self.mbId = mbId
        self.maxTemp = maxTemp
        self.minTemp = minTemp
        self.avgTemp = avgTemp
        self.maxHV = maxHV
        self.minHV = minHV
        self.avgHV = avgHV
        self.maxPT = maxPT
        self.minPT = minPT
        self.avgPT = avgPT
        self.maxRate = maxRate
        self.minRate = minRate
        self.avgRate = avgRate
        self.width = width
        self.const = const
        self.numSpikes = numSpikes
        self.r2 = r2
        self.histo = histo

    def __repr__(self):
        return self.mbId + \
            ' | ' + self.maxTemp + ' ' + self.minTemp + ' ' + self.avgTemp + \
            ' | ' + self.maxHV + ' ' + self.minHV + ' ' + self.avgHV + \
            ' | ' + self.maxPT + ' ' + self.minPT + ' ' + self.avgPT + \
            ' | ' + self.maxRate + ' ' + self.minRate + ' ' + self.avgRate + \
            ' | ' + self.width + ' ' + self.const + ' ' + \
            self.numSpikes + ' ' + self.r2 + \
            ' # ' + str(self.histo)

    def insert(self, db, monId, dataId):
        prodId = db.getDOMId(self.mbId)
        if prodId is None:
            sys.stderr.write('Could not get Product ID for DOM#' + self.mbId +
                             "; not inserting data\n")
            return None

        cursor = db.cursor()

        if False:
            print 'di int => ' + str(type(dataId))
            print 'mi int => ' + str(type(monId))
            print 'pi int => ' + str(type(prodId))
            print 'xt flt => ' + str(type(self.maxTemp))
            print 'nt flt => ' + str(type(self.minTemp))
            print 'at flt => ' + str(type(self.avgTemp))
            print 'xv int => ' + str(type(self.maxHV))
            print 'nv int => ' + str(type(self.minHV))
            print 'av int => ' + str(type(self.avgHV))
            print 'xp flt => ' + str(type(self.maxPT))
            print 'np flt => ' + str(type(self.minPT))
            print 'ap flt => ' + str(type(self.avgPT))
            print 'xr int => ' + str(type(self.maxRate))
            print 'nr int => ' + str(type(self.minRate))
            print 'ar flt => ' + str(type(self.avgRate))
            print 'wi flt => ' + str(type(self.width))
            print 'co flt => ' + str(type(self.const))
            print 'ns int => ' + str(type(self.numSpikes))
            print 'r2 flt => ' + str(type(self.r2))

        cursor.execute(('insert into FATMonData(' +
                        'fat_mondata_id,fat_mon_id,prod_id' +
                        ',temp_max,temp_min,temp_avg' +
                        ',hv_max,hv_min,hv_avg' +
                        ',pt_max,pt_min,pt_avg' +
                        ',rate_max,rate_min,rate_avg' +
                        ',width,constant,num_spikes,r2' +
                        ')values(%d,%d,%d' +
                        ',%f,%f,%f' +
                        ',%d,%d,%d' +
                        ',%f,%f,%f' +
                        ',%d,%d,%f' +
                        ',%f,%f,%d,%f' +
                        ')') %
                       (dataId, monId, prodId,
                        self.maxTemp, self.minTemp, self.avgTemp,
                        self.maxHV, self.minHV, self.avgHV,
                        self.maxPT, self.minPT, self.avgPT,
                        self.maxRate, self.minRate, self.avgRate,
                        self.width, self.const, self.numSpikes, self.r2))

        bin = 0
        for val in self.histo:
            cursor.execute('insert into FATMonHisto(' +
                           'fat_mondata_id,bin,value)values(%d,%d,%d)' %
                           (dataId,bin,val))
            bin = bin + 1

        cursor.close()

##############################################################################

class MonitorFile:
    def deleteOldRows(self, db, fatId):
        cursor = db.cursor()

        cursor.execute('select fat_mon_id from FATMonitor where fat_id=%d' %
                       (fatId))
        idList = cursor.fetchall()

        for monId, in idList:
            cursor.execute('select fat_mondata_id from FATMonData' +
                           ' where fat_mon_id=%d' % int(monId))
            dataList = cursor.fetchall()

            for dataId in dataList:
                cursor.execute('delete from FATMonHisto' +
                               ' where fat_mondata_id=%d' % (dataId))

            cursor.execute('delete from FATMonData where fat_mon_id=%d' %
                           (monId))

        cursor.execute('delete from FATMonitor where fat_id=%d' % (fatId))
        cursor.close()

    # declare deleteOldRows() as class method
    deleteOldRows = classmethod(deleteOldRows)

    def process(self, path, db, fatId):
        mon = MonitorFile.read(path)

        mon.insert(db, fatId)

    # declare process() as class method
    process = classmethod(process)

    def read(self, arg, temp=None):
        if not isinstance(arg, str):
            # assume a file descriptor is being passed in

            if not temp:
                raise ValueError, 'Temperature parameter was not specified'

            fd = arg
        else:
            path = arg

            for p in path.split(os.sep):
                if p.startswith('mon'):
                    temp = p[3:]

            if not temp:
                raise ValueError, "Couldn't find temperature in path '" + \
                      p + "'"

            fd = open(path, 'r')

        mon = Monitor(temp)

        intPatStr = r'\s+(\d+)'
        fltPatStr = r'\s+(-?\d+\.?\d*)'

        tempPatStr = fltPatStr + fltPatStr + fltPatStr
        #            maxTemp     minTemp     avgTemp
        hvPatStr = intPatStr + intPatStr + intPatStr
        #          maxHV       minHV       avgHV
        ptPatStr = fltPatStr + fltPatStr + fltPatStr
        #          maxP/T      minP/T      avgP/T
        ratePatStr = intPatStr + intPatStr + fltPatStr
        #            maxRate     minRate     avgRate
        miscPatStr = fltPatStr + fltPatStr + intPatStr + fltPatStr + intPatStr
        #            width(std.) const(ampl) numSpikes   r2          binSize

        frontPat = re.compile(r'^\s*(\S+)' + tempPatStr + hvPatStr +
                              ptPatStr + ratePatStr + miscPatStr + r'\s+:')

        for line in fd:
            line = line.rstrip()
            if line == '':
                continue

            #sys.stderr.write('STATE[' + STATESTR[state] + "]\n")
            #sys.stderr.write('LINE[' + line + "]\n")

            m = frontPat.match(line)
            if not m:
                sys.stderr.write("Unknown monitor line: " + line + "\n")
                continue

            (mbId, maxTemp, minTemp, avgTemp, maxHV, minHV, avgHV,
             maxPT, minPT, avgPT, maxRate, minRate, avgRate,
             width, const, numSpikes, r2, binSize) = m.groups()

            histo = []
            for hStr in m.string[m.end():].split():
                histo.append(int(hStr))

            mon.setBinSize(int(binSize))
            mon.append(MonData(mbId,
                               float(maxTemp), float(minTemp),
                               float(avgTemp),
                               int(maxHV), int(minHV), int(avgHV),
                               float(maxPT), float(minPT), float(avgPT),
                               int(maxRate), int(minRate), float(avgRate),
                               float(width), float(const), int(numSpikes),
                               float(r2), histo))

        return mon

    # declare read() as class method
    read = classmethod(read)
