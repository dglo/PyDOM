#!/usr/bin/env python
#
# Read lcchain data and save it to the database

import re,sys

STATE_BOGUS = 0
STATE_OUTER = 1
STATE_DOMS = 2
STATE_DATA = 3
STATESTR = ['BOGUS', 'OUTER', 'DOMS', 'DATA']

SEND_UNKNOWN = 0
SEND_PULSE_D_NEG = 1
SEND_PULSE_D_POS = 2
SEND_PULSE_U_NEG = 3
SEND_PULSE_U_POS = 4
SENDSTR = ['UNKNOWN', 'D_NEG', 'D_POS', 'U_NEG', 'U_POS']

##############################################################################

class TestResult:
    """LCChain test results"""

    def __init__(self, highDOM, lowDOM):
        self.highDOM = highDOM
        self.lowDOM = lowDOM
        self.downNeg = None
        self.downPos = None
        self.upNeg = None
        self.upPos = None

    def __repr__(self):
        if self.highDOM is None:
            highStr = "???"
        else:
            highStr = self.highDOM

        if self.lowDOM is None:
            lowStr = "???"
        else:
            lowStr = self.lowDOM

        return highStr + "=>" + lowStr + ': D- ' + str(self.downNeg) + \
            ' D+ ' + str(self.downPos) + ' U- ' + str(self.upNeg) + \
            ' U+ ' + str(self.upPos)

    def boolVal(self, b):
        if b:
            return 1
        else:
            return 0

    def isFilled(self):
        domFilled = (self.highDOM is not None and self.lowDOM is not None)
        dataFilled = (self.downPos is not None and self.downNeg is not None
                      and self.upPos is not None and self.upNeg is not None)
        return (domFilled and dataFilled)

    def isSuccess(self):
        return (self.downNeg and self.downPos and
                self.upNeg and self.upPos) == True

    def insert(self, db, fatId):
        if self.highDOM is None:
            if self.lowDOM is None:
                raise ValueError, "Unknown high and low DOMs"
            else:
                raise ValueError, "Unknown high DOM"
        elif self.lowDOM is None:
            raise ValueError, "Unknown low DOM"

        hiProdId = db.getDOMId(self.highDOM)
        if hiProdId is None:
            raise ValueError, 'Could not get Product ID for high DOM#' + \
                self.highDOM

        loProdId = db.getDOMId(self.lowDOM)
        if loProdId is None:
            raise ValueError, 'Could not get Product ID for low DOM#' + \
                self.lowDOM

        cursor = db.executeQuery(('insert into FATLCChain(fat_id' +
                                 ',hi_prod_id,lo_prod_id' +
                                  ',down_neg,down_pos,up_neg,up_pos)' +
                                 'values(%d,%d,%d,%d,%d,%d,%d)') %
                                 (fatId, hiProdId, loProdId,
                                  self.boolVal(self.downNeg),
                                  self.boolVal(self.downPos),
                                  self.boolVal(self.upNeg),
                                  self.boolVal(self.upPos)))
        cursor.close()

    def setDownNeg(self, val):
        if val:
            self.downNeg = True
        else:
            self.downNeg = False

    def setDownPos(self, val):
        if val:
            self.downPos = True
        else:
            self.downPos = False

    def setUpNeg(self, val):
        if val:
            self.upNeg = True
        else:
            self.upNeg = False

    def setUpPos(self, val):
        if val:
            self.upPos = True
        else:
            self.upPos = False

##############################################################################

class LCChainFile:
    def deleteOldRows(self, db, fatId):
        cursor = db.cursor()

        cursor.execute('delete from FATLCChain where fat_id=%s' % fatId)
        cursor.close()

    # declare deleteOldRows() as class method
    deleteOldRows = classmethod(deleteOldRows)

    def process(self, path, db, fatId):
        resultList = LCChainFile.read(path)
        for r in resultList:
            r.insert(db, fatId)

    # declare process() as class method
    process = classmethod(process)

    def read(self, arg):
        resultList = []
    
        if not isinstance(arg, str):
            # assume a file descriptor is being passed in
            fd = arg
        else:
            fd = open(arg, 'r')

        startMsgPat = re.compile(r'^starting\s+lcchain.py.*$')
        lcchainPyPat = re.compile(r'^\S+\s+\S+\s+lcchain.py\s+\d+\.\d*$')
        dorRevPat = re.compile(r'^\S+\s+DOR\s+Rev\S*\s+.*$')
        testingPat = re.compile(r'^Testing\s+\S+\s+(\d\d[AB])\s+' +
                                r'to\s+\S+\s+(\d\d[AB])$')
        testErrPat = re.compile(r'^Couldn\'t\s+connect\s+to\s+(\S+)\s*:.*$')
        domPat = re.compile(r'^(High|Low)\s+DOM:\s+(\S+)\s*$')
        sendPat = re.compile(r'^Sending\s+(\S+)$')
        respPat = re.compile(r'^(Expected|Actual)\s+response:\s+(\S+)$')
        passFailPat = re.compile(r'^(PASSED|FAILED)$')
        resultPat = re.compile(r'^LC\s+pair\s+test\s+result:\s+(PASS|FAIL)$')
        sumPat = re.compile(r'LC\s+chain\s+result:\s+(\d+)\s+of\s+(\d+)' +
                            r'\s+passed$')
        wrapPat = re.compile(r'^lcchain-wrapper.*$')
    
        state = STATE_BOGUS
    
        for line in fd:
            line = line.rstrip()
            if line == '':
                continue
    
            #sys.stderr.write('STATE[' + STATESTR[state] + "]\n")
            #sys.stderr.write('LINE[' + line + "]\n")
    
            if state == STATE_BOGUS:
                m = testingPat.match(line)
                if m:
                    highDOM = None
                    lowDOM = None
                    state = STATE_DOMS
                    continue
    
                # ignore extra junk
                continue
    
            if state == STATE_OUTER:
                m = testingPat.match(line)
                if m:
                    highDOM = None
                    lowDOM = None
                    state = STATE_DOMS
                    continue
    
                m = sumPat.match(line)
                if m:
                    continue
    
                m = wrapPat.match(line)
                if m:
                    continue
    
                sys.stderr.write("Unknown outer line: " + line + "\n")
                continue
    
            if state == STATE_DOMS:
                m = lcchainPyPat.match(line)
                if m:
                    continue
    
                m = dorRevPat.match(line)
                if m:
                    continue
    
                m = domPat.match(line)
                if m:
                    if m.group(1) == 'High':
                        highDOM = m.group(2)
                    elif m.group(1) == 'Low':
                        lowDOM = m.group(2)
                    else:
                        sys.stderr.write("Unknown middle line: " + line + "\n")
                        state = STATE_OUTER
                        continue
    
                    if highDOM is not None and lowDOM is not None:
                        testResult = TestResult(highDOM, lowDOM)
                        state = STATE_DATA
    
                    continue
    
                m = testErrPat.match(line)
                if m:
                    testResult = TestResult(highDOM, lowDOM)
                    state = STATE_DATA
                    continue
    
                sys.stderr.write("Unknown middle line: " + line + "\n")
                state = STATE_OUTER
                continue
    
            if state == STATE_DATA:
                m = sendPat.match(line)
                if m:
                    if m.group(1) == 'pulse_d_neg':
                        sending = SEND_PULSE_D_NEG
                    elif m.group(1) == 'pulse_d_pos':
                        sending = SEND_PULSE_D_POS
                    elif m.group(1) == 'pulse_u_neg':
                        sending = SEND_PULSE_U_NEG
                    elif m.group(1) == 'pulse_u_pos':
                        sending = SEND_PULSE_U_POS
                    else:
                        sys.stderr.write("Unknown send type: " + m.group(1) +
                                         "\n")
                        sending = SEND_UNKNOWN
                    continue
    
                m = respPat.match(line)
                if m:
                    continue
    
                m = passFailPat.match(line)
                if m:
                    result = (m.group(1) == 'PASSED')
    
                    if sending == SEND_PULSE_D_NEG:
                        testResult.setDownNeg(result)
                    elif sending == SEND_PULSE_D_POS:
                        testResult.setDownPos(result)
                    elif sending == SEND_PULSE_U_NEG:
                        testResult.setUpNeg(result)
                    elif sending == SEND_PULSE_U_POS:
                        testResult.setUpPos(result)
                    continue
    
                m = resultPat.match(line)
                if m:
                    result = (m.group(1) == 'PASS')
                    expResult = testResult.isSuccess()
                    if result != expResult:
                        if expResult:
                            expStr = 'PASS'
                        else:
                            expStr = 'FAIL'
    
                        sys.stderr.write('Expected final ' + expStr + '(' +
                                         str(expResult) + '), got ' +
                                         m.group(1) +
                                         '(' + str(result) + ")\n")
    
                    if testResult.isFilled():
                        resultList.append(testResult)
    
                    state = STATE_OUTER
                    continue
    
                sys.stderr.write("Unknown test line: " + line + "\n")

        return resultList

    # declare read() as class method
    read = classmethod(read)
