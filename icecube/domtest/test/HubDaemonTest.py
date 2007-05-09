#!/usr/bin/env python
#
# HubDaemon unit tests

import unittest
import sys
from icecube.domtest.HubDaemon import HubSysDep, HubDaemon

class MockError(StandardError):
    """Error in MockDriver"""

class MockSysDep(HubSysDep):
    def __init__(self):
        HubSysDep.__init__(self)
        self.expDtsxAll = 0
        self.expJarList = { }
        self.expKillDomProcs = []
        self.expKillProc = {}
        self.expStartDaemon = {}
        self.expDomHubAppPid = None

    def expectDtsxAll(self, num=1):
        self.expDtsxAll = self.expDtsxAll + num

    def expectStartDomHubApp(self, pidFile=None):
        if self.expDomHubAppPid is not None:
            raise MockError, 'domhub-app PID file was already set to "' + \
                self.expDomHubAppPid + '"'
        if pidFile is None:
            self.expDomHubAppPid = self.domhubAppPid
        else:
            self.expDomHubAppPid = pidFile

    def addExpectedJarList(self, workDir, jars):
        if not isinstance(jars, list):
            raise MockError, 'Argument should be a list, not ' + \
                str(type(jars))
        if self.expJarList.has_key(workDir):
            raise MockError, 'Cannot use multiple instances of' + \
                ' working directory "' + workDir + '"'
        self.expJarList[workDir] = jars

    def addKillDomProcessesReturnValue(self, val):
        self.expKillDomProcs.append(val)

    def addKillProcess(self, progName):
        if self.expKillProc.has_key(progName):
            self.expKillProc[progName] = self.expKillProc[progName] + 1
        else:
            self.expKillProc[progName] = 1

    def addStartDaemon(self, progName, pidFile):
        if self.expStartDaemon.has_key(progName):
            raise MockError, 'Cannot kill "' + progName + '" multiple times'
        self.expStartDaemon[progName] = pidFile

    def getJarList(self, workDir):
        if not self.expJarList.has_key(workDir):
            raise MockError, 'No jar list for for "' + workDir + '"'
        list = self.expJarList[workDir]
        del self.expJarList[workDir]
        return list

    def killDomProcesses(self):
        if len(self.expKillDomProcs) == 0:
            raise MockError, 'Unexpected call to killDomProcesses()'
        rtnVal = self.expKillDomProcs[0]
        del self.expKillDomProcs[0]
        return rtnVal

    def killProcess(self, progName):
        if not self.expKillProc.has_key(progName):
            raise MockError, 'Unexpected call to killProcess(' + progName + ')'
        if self.expKillProc[progName] == 1:
            del self.expKillProc[progName]
        else:
            self.expKillProc[progName] = self.expKillProc[progName] - 1

    def runDtsxAll(self):
        if self.expDtsxAll == 0:
            raise MockError, 'Unexpected call to runDtsxAll()'
        self.expDtsxAll = self.expDtsxAll - 1
        return 'Ran dtsxall'

    def startDaemon(self, progName, pidFile):
        if not self.expStartDaemon.has_key(progName):
            raise MockError, 'Did not expect to start "' + progName + \
                '" daemon'

        expPid = self.expStartDaemon[progName]
        del self.expStartDaemon[progName]

        if expPid != pidFile:
            raise MockError, 'Expected "' + progName + '" PID file to be "' + \
                expPid + '", not "' + pidFile + '"'

    def startDomHubApp(self, pidFile):
        if self.expDomHubAppPid != pidFile:
            raise MockError, 'Expected domhub-app PID file to be "' + \
                self.expDomHubAppPid + '", not "' + pidFile + '"'
        self.expDomHubAppPid = None

    def verify(self):
        if self.expDtsxAll > 0:
            raise MockError, 'Expected ' + str(self.expDtsxAll) + \
                ' calls to runDtsxAll()'
        if len(self.expJarList) > 0:
            raise MockError, 'Expected ' + str(len(self.expJarList)) + \
                ' calls to getJarList()'
        if len(self.expKillDomProcs) > 0:
            raise MockError, 'Expected ' + str(len(self.expKillDomProcs)) + \
                ' calls to killDomProcesses()'
        if len(self.expStartDaemon) > 0:
            raise MockError, 'Expected ' + str(len(self.expStartDaemon)) + \
                ' calls to startDaemon()'
        if self.expDomHubAppPid is not None:
            raise MockError, 'Expected call to startDomHubApp()'

class MockDriver:
    def __init__(self):
        self.expActiveDoms = None
        self.expDisableBlocking = 0
        self.expGoToIceBoot = 0
        self.expOffAll = 0
        self.expOnAll = 0

    def disable_blocking(self):
        if self.expDisableBlocking == 0:
            raise MockError, 'Unexpected call to disable_blocking'
        self.expDisableBlocking = self.expDisableBlocking - 1

    def expectDisableBlocking(self, num=1):
        self.expDisableBlocking = self.expDisableBlocking + num

    def expectGoToIceBoot(self, num=1):
        self.expGoToIceBoot = self.expGoToIceBoot + num

    def expectOffAll(self, num=1):
        self.expOffAll = self.expOffAll + num

    def expectOnAll(self, num=1):
        self.expOnAll = self.expOnAll + num

    def get_active_doms(self):
        if self.expActiveDoms is None:
            raise MockError, 'Unexpected call to getActiveDoms()'
        active = self.expActiveDoms
        self.expActiveDoms = None
        return active

    def go_to_iceboot(self):
        if self.expGoToIceBoot == 0:
            raise MockError, 'Unexpected call to disable_blocking'
        self.expGoToIceBoot = self.expGoToIceBoot - 1

    def offAll(self):
        if self.expOffAll == 0:
            raise MockError, 'Unexpected call to offAll'
        self.expOffAll = self.expOffAll - 1

    def onAll(self):
        if self.expOnAll == 0:
            raise MockError, 'Unexpected call to onAll'
        self.expOnAll = self.expOnAll - 1

    def setExpectedActiveDoms(self, doms):
        if not isinstance(doms, dict):
            raise MockError, 'Argument should be a dictionary, not ' + \
                str(type(doms))
        self.expActiveDoms = doms

    def verify(self):
        if self.expActiveDoms is not None:
            raise MockError, 'get_active_doms() was never called'
        if self.expDisableBlocking > 0:
            raise MockError, 'Expected ' + str(self.expDisableBlocking) + \
                ' calls to disable_blocking()'
        if self.expGoToIceBoot > 0:
            raise MockError, 'Expected ' + str(self.expGoToIceBoot) + \
                ' calls to go_to_iceboot()'
        if self.expOffAll > 0:
            raise MockError, 'Expected ' + str(self.expOffAll) + \
                ' calls to offAll()'
        if self.expOnAll > 0:
            raise MockError, 'Expected ' + str(self.expOnAll) + \
                ' calls to offAll()'

class testHubDaemon(unittest.TestCase):
    """Unit tests for HubDaemon class"""

    def setUp(self):
        self.sysDep = MockSysDep()
        self.driver = MockDriver()
        self.daemon = HubDaemon(self.sysDep, self.driver)

    def tearDown(self):
        self.driver.verify()
        self.sysDep.verify()

    def testDisableBlocking(self):
        self.driver.expectDisableBlocking()

        self.daemon.disableBlocking()

    def testDtsxAll(self):
        self.sysDep.expectDtsxAll()

        result = self.daemon.dtsxAll()
        self.assertEqual(result, 'Ran dtsxall', 'Unexpected return string' +
                         ' from dtsxAll(): ' + str(result))

    def testGetActiveDoms(self):
        expList = { 'abc':(0, 1, 'A'), 'def':(2, 3, 'B') }
        self.driver.setExpectedActiveDoms(expList)

        result = self.daemon.getActiveDoms()
        self.failUnless(isinstance(result, dict), 'Expected getActiveDoms()' +
                        ' to return a dictionary, not ' + str(type(result)))
        self.assertEqual(len(result), len(expList), 'Expected ' +
                         str(len(expList)) + ' doms, not ' +
                         str(len(result)))
        for k in expList.keys():
            self.failUnless(result.has_key(k), 'Could not find DOM ' + k)
            self.assertEqual(expList[k], result[k], 'Expected dom ' + str(k) +
                             ' to be "' + str(expList[k]) + '", not "' +
                             str(result[k]))

    def testGoToIceBoot(self):
        self.driver.expectGoToIceBoot()

        result = self.daemon.goToIceBoot()

    def testKillDomProcs(self):
        expRtnVal = 7

        self.sysDep.addKillDomProcessesReturnValue(expRtnVal)

        rtnVal = self.sysDep.killDomProcesses()
        self.assertEquals(expRtnVal, rtnVal, 'Expected return value of ' +
                          str(expRtnVal) + ', not ' + str(rtnVal))

    def testOffAll(self):
        self.driver.expectOffAll()

        self.daemon.offAll()

    def testOnAll(self):
        self.driver.expectOnAll()

        self.daemon.onAll()

    def testReady(self):
        self.sysDep.addExpectedJarList(self.daemon.workDir, ['abc', 'def'])
        self.sysDep.addKillProcess('dtsx')
        self.sysDep.addKillProcess('rmiregistry')
        self.driver.expectDisableBlocking()
        self.driver.expectOffAll()
        self.sysDep.addStartDaemon('rmiregistry', self.sysDep.rmiRegPid)
        self.sysDep.expectStartDomHubApp()

        self.daemon.ready()

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testHubDaemon))
    return suite

if __name__ == '__main__':
    unittest.main()
