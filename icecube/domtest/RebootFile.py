#!/usr/bin/env python
#
# Read cold-reboot data and save it to the database

import re,sys,time
import DOMProdTestUtil
import _mysql_exceptions

##############################################################################

class RebootBase:
    """Basic reboot data"""

    def __init__(self, time):
        self.time = time

    def __repr__(self):
        return time.strftime('%x %X', self.time)

    def sqlDate(self):
        return time.strftime('%Y-%m-%d %T', self.time)

class RebootFailure(RebootBase):
    """Reboot failure data"""

    def __init__(self, time, text):
        RebootBase.__init__(self, time)
        self.text = text
        self.prevTemp = None
        self.nextTemp = None

    def __repr__(self):
        return time.strftime('%x %X', self.time) + \
            '[' + self.prevTemp + ',' + self.nextTemp + ']'

    def setTemps(self, prevTemp, nextTemp):
        self.prevTemp = prevTemp
        self.nextTemp = nextTemp

class RebootSuccess(RebootBase):
    """Reboot success data"""

    def __init__(self, time, utime, temp):
        RebootBase.__init__(self, time)
        self.utime = utime
        self.temp = temp

    def __cmp__(self, other):
        if not isinstance(other, RebootBase):
            return -1

        r = cmp(self.utime, other.utime)
        if r == 0:
            r = cmp(self.temp, other.temp)

        return r

    def __repr__(self):
        return time.strftime('%x %X', self.time) + '(' + str(self.utime) + \
            ')' + str(self.temp)

##############################################################################

class DOM:
    """DOM info"""

    def __init__(self, name, mbId):
        self.name = name
        self.mbId = mbId

        self.prodId = None
        self.success = []
        self.failure = []

    def __cmp__(self, other):
        if not isinstance(other, DOM):
            return -1

        r = cmp(self.name, other.name)
        if r == 0:
            r = cmp(self.mbId, other.mbId)

        return r

    def __repr__(self):
        return self.name + '(' + self.mbId + ')'

    def addFailure(self, timeList, text):
        self.failure.append(RebootFailure(timeList, text))

    def addSuccess(self, timeList, utime, temp):
        self.success.append(RebootSuccess(timeList, utime, temp))

    def compareTime(self, list0, list1):
        if list0 is None:
            if list1 is None:
                return 0
            return 1
        elif list1 is None:
            return -1

        n = len(list0) - len(list1)
        if n < 0:
            return -1
        elif n > 0:
            return 1

        for i in range(len(list0)):
            n = list0[i] - list1[i]
            if n < 0:
                return -1
            elif n > 0:
                return 1

        return 0

    def fillFailures(self):
        self.success.sort()
        for f in self.failure:
            prevSuccess = None
            for s in self.success:
                if self.compareTime(s.time, f.time) < 0:
                    if prevSuccess is None or prevSuccess.time < s.time:
                        prevSuccess = s
                else:
                    if prevSuccess is None:
                        f.setTemps(None, s.temp)
                    else:
                        f.setTemps(prevSuccess.temp, s.temp)
                    prevSuccess = None
                    break

            # failure happened on last reboot
            if prevSuccess is not None:
                f.setTemps(prevSuccess.temp, None)

    def getProdId(self, db):
        if self.prodId is None:
            cursor = db.executeQuery('select prod_id from ProductName' +
                                     " where name='%s'" % (self.name))
            list = cursor.fetchone()
            if list is not None:
                self.prodId = list[0]
            else:
                self.prodId = db.getDOMId(self.mbId)

            cursor.close()

        return self.prodId

    def insert(self, db, nextId, fatId):
        prodId = self.getProdId(db)
        if prodId is None:
            raise ValueError, 'Could not get Product ID for DOM#' + \
                self.mbId + '(' + self.name + ')'

        cursor = db.executeQuery('select fat_reboot_id,num_success' +
                                 ',num_failed from FATReboot' +
                                 ' where fat_id=%d and prod_id=%d' % \
                                 (fatId, prodId))
        list = cursor.fetchone()

        if list is None:
            id = nextId
            cursor.execute('insert into FATReboot(fat_reboot_id,fat_id' +
                           ',prod_id,num_success,num_failed)' +
                           'values(%d,%d,%d,%d,%d)' %
                           (id, fatId, prodId, len(self.success),
                            len(self.failure)))
        else:
            id = list[0]
            numSuccess = list[1] + len(self.success)
            numFailed = list[2] + len(self.failure)
            fmtStr = 'update FATReboot set num_success=%d,num_failed=%d' + \
                ' where fat_reboot_id=%d'
            cursor.execute(fmtStr % (numSuccess, numFailed, id))

        for f in self.failure:
            if f.prevTemp is None:
                if f.nextTemp is None:
                    valStr = '%d,"%s",null,null' % (id, f.sqlDate())
                else:
                    valStr = '%d,"%s",null,%f' % (id, f.sqlDate(), f.nextTemp)
            elif f.nextTemp is None:
                valStr = '%d,"%s",%f,null' % (id, f.sqlDate(), f.prevTemp)
            else:
                valStr = '%d,"%s",%f,%f' % (id, f.sqlDate(), f.prevTemp,
                                            f.nextTemp)

            try:
                cursor.execute('insert into FATRebootFail(fat_reboot_id' +
                               ',datetime,prev_temp,next_temp)values(' + \
                               valStr + ')')
            except _mysql_exceptions.IntegrityError:
                # ignore duplicate failures
                xxx = 0

        cursor.close()
        return id

    def matches(self, name, mbId):
        return self.name == name and self.mbId == mbId

##############################################################################

class RebootFile:
    def deleteOldRows(self, db, fatId):
        cursor = db.cursor()

        cursor.execute('select fat_reboot_id from FATReboot where fat_id=%d' %
                       fatId)
        idList = cursor.fetchall()

        for rebootId in idList:
            cursor.execute(('delete from FATRebootFail' +
                           ' where fat_reboot_id=%d') %
                           rebootId)

        cursor.execute('delete from FATReboot where fat_id=%d' % fatId)
        cursor.close()

    # declare deleteOldRows() as class method
    deleteOldRows = classmethod(deleteOldRows)

    def process(self, path, db, fatId):
        dorMap = RebootFile.read(path)

        nextId = DOMProdTestUtil.getNextId(db, 'FATReboot', 'fat_reboot_id')

        for k in dorMap.keys():
            try:
                id = dorMap[k].insert(db, nextId, fatId)
            except ValueError:
                continue
            if id == nextId:
                nextId = nextId + 1

    # declare process() as class method
    process = classmethod(process)

    def read(self, arg):
        if not isinstance(arg, str):
            # assume a file descriptor is being passed in

            fd = arg
        else:
            path = arg

            fd = open(path, 'r')

        dorMap = {}

        rebootPatStr = r'^(\S+)\s+(\d\d\d)\s+' + \
            r'(\d+-\d+-\d+\s+\d+:\d+:\d+)\s+(\S+)\s+(.*)$'
        rebootPat = re.compile(rebootPatStr)

        dataPat = re.compile(r'(\d+\.\d+)\s+(\S+)?\s+(\S+)\s+([\-\+]?\d+\.\d+)\s*$')

        for line in fd:
            m = rebootPat.match(line)
            if not m:
                print 'Mismatch: ' + line
                continue

            domhub = m.group(1)
            dorcard = m.group(2)
            dtStr = m.group(3)
            timezone = m.group(4)
            data = m.group(5)

            dtFull = dtStr + ' ' + timezone
            try:
                timeList = time.strptime(dtFull, '%Y-%m-%d %H:%M:%S %Z')
            except ValueError:
                tmpList = time.strptime(dtStr + ' GMT', '%Y-%m-%d %H:%M:%S %Z')

                secsPerHour = 60 * 60
                if timezone == 'CDT':
                    offset = -5 * secsPerHour
                elif timezone == 'CEST':
                    offset = 2 * secsPerHour
                elif timezone == 'CET':
                    offset = 1 * secsPerHour
                elif timezone == 'CST':
                    offset = -6 * secsPerHour
                elif timezone == 'GMT':
                    offset = 0
                else:
                    sys.stderr.write("Unknown timezone '" + timezone +
                                     "' in '" + dtStr + "'\n")
                    offset = 0

                secs = time.mktime(tmpList) + offset
                timeList = time.gmtime(secs)

            key = domhub + ':' + dorcard

            if data.endswith('FAILURE'):
                if key not in dorMap:
                    print 'Failure for unknown DOR entry ' + key
                    continue

                dorMap[key].addFailure(timeList, data)

            else:
                m = dataPat.match(data)
                if not m:
                    print 'Data mismatch: ' + line
                    continue

                utime = m.group(1)
                name = m.group(2)
                mbId = m.group(3)
                temp = float(m.group(4))

                if name is None:
                    name = ''

                if key not in dorMap:
                    dorMap[key] = DOM(name, mbId)

                dom = dorMap[key]
                if not dom.matches(name, mbId):
                    sys.stderr.write('Expected ' + key + \
                                     ' to be DOM ' + str(dom) + \
                                     ', not ' + name + '(' + mbId + ")\n")
                    sys.stderr.write('-- ' + line + "\n");
                else:
                    dom.addSuccess(timeList, utime, temp)

        if len(dorMap) == 0:
            return None

        for k in dorMap.keys():
            dorMap[k].fillFailures()

        return dorMap

    # declare read() as class method
    read = classmethod(read)
