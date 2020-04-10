#!/usr/bin/env python
#
# DOMHub XML-RPC daemon

from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import object
import os, re, signal, socket, string, sys, traceback
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer

from . import daemon
from .dor import Driver

# list of valid clients
#accessList=('127.0.0.1')

def jarFilter(file_list, dirname, names):
    """filter program for os.path.walk() which returns only jar files"""
    for name in names:
        if name.endswith('.jar'):
            fullpath = os.path.join(dirname, name)
            if os.path.isopen(fullpath):
                file_list.append(fullpath)

class XMLServer(SimpleXMLRPCServer):
    """Augmented XML-RPC server class"""

    def __init__(self, *args):
        SimpleXMLRPCServer.__init__(self, (args[0], args[1]))

    def server_bind(self):
        """Mark the socket reuseable (for debugging)"""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        SimpleXMLRPCServer.server_bind(self)

    def verify_request(self, request, client_address):
        """
        if access_list is defined,
        only allow hosts in that list to make requests
        """
        try:
            if client_address[0] in accessList:
                return 1
            else:
                return 0
        except:
            return 1

class HubSysDep(object):
    """System-dependent HubDaemon data"""

    def __init__(self):
        # HubDaemon home directory
        self.homeDir = os.environ['HOME']

        # daemon log file
        self.daemonLog = '/tmp/HubDaemon.log'

        # path to DomHub driver
        self.defaultDriverDir = '/proc/driver/domhub'

        # path to TestDAQ jar directory
        self.defaultWorkDir = os.environ.get('HOME') + '/work'

        # path to 'dtsxall' program
        self.dtsxAllBin = '/usr/local/python/dtsxall'

        # server port
        self.port = 5280

        # directory where PID files are stored
        pidDir = "/tmp"

        # name of PID file
        self.daemonPid = os.path.join(pidDir, 'HubDaemon.pid')

        # rmiregistry PID file (None for no PID file)
        self.rmiRegPid = os.path.join(pidDir, 'rmiregistry.pid')

        # domhub-app PID file (None for no PID file)
        self.domhubAppPid = os.path.join(pidDir, 'domhubapp.pid')

    def getJarList(self, workDir):
        """list all jar files in the specified directory"""
        jarList = []
        os.path.walk(workDir, jarFilter, jarList)

        return jarList

    def initLog(self):
        """initialize domhubapp.log"""
        logFile = os.path.join(self.homeDir, 'domhubapp.log')
        f = open(logFile, 'w')
        f.write("\n")
        f.write('STARTING DOMHUBAPP ' + os.popen('date').read() + "\n")
        f.write("\n")
        f.close()
        return logFile

    def isDomProcess(self, procStr):
        """is this a process which might be using one or more DOMs?"""
        try:
            (cmd, args) = procStr.split(None, 1)
        except ValueError:
            cmd = procStr

        if cmd.find('automate') >= 0:
            return True
        if cmd.find('domserv') >= 0:
            return True
        if cmd.find('domterm') >= 0:
            return True
        if cmd.find('dtsx') >= 0:
            return True
        if cmd.find('java') >= 0:
            if args.find('icecube.daq.domhub.DOMHub') > 0:
                return True
            if args.find('icecube.daq.stf.STF') > 0:
                return True
        if cmd.find('rmiregistry') >= 0:
            return True
        if cmd.find('testdaq') >= 0:
            return True

        if procStr.find('watch.pl') >= 0:
            return True

        return False

    def killDomProcesses(self):
        """kill all processes which might be using DOMs"""
        killed = []
        ps = os.popen('ps xww')
        title = ps.readline().rstrip()
        colHdrs = title.split()
        pidCol = colHdrs.index('PID')
        if colHdrs[-1] != 'CMD' and colHdrs[-1] != 'COMMAND':
            sys.stderr.write("Couldn't find command column in '" + title +
                             "'\n")
        else:
            while True:
                l = ps.readline()
                if l == '':
                    break
                pCols = l.rstrip().split(None, len(colHdrs) - 1)
                if self.isDomProcess(pCols[-1]):
                    os.kill(int(pCols[pidCol]), signal.SIGTERM)
                    killed.append(pCols[-1])
        return killed

    def killProcess(self, procName):
        """kill all processes with the specified name"""
        os.system('killall ' + procName + ' >/dev/null 2>&1')

    def makeClassPath(self, jarList):
        """Build a CLASSPATH environment variable from the list of jar files"""
        classPath = None
        for j in jarList:
            if classPath is None:
                classPath = j
            else:
                classPath = classPath + ":" + j

        return classPath

    def runDtsxAll(self):
        """Run the dtsxall program and return its output"""
        return os.popen(self.dtsxAllBin + " 2>&1").read().rstrip()

    def startDaemon(self, progName, pidFile=None):
        """Start a program as a daemon"""
        daemon.run(progName, pidFile)

    def startDomHubApp(self, javaBin='java',
                       domhubClass='icecube.daq.domhub.DOMHub',
                       domhubProperties='/usr/local/etc/dh.properties',
                       pidFile=None):
        """initialize log file and start domhub-app"""
        os.chdir(self.homeDir)
        logFile = self.initLog()
        daemon.run(javaBin + ' ' + domhubClass + ' ' + domhubProperties,
                   outFile=logFile, errFile=logFile, pidFile=pidFile)

class HubDaemon(object):
    """Daemon which runs software on the DOMHub"""

    def __init__(self, sysDep, driver=None):
        self.python_string = string

        self.sysDep = sysDep

        self.driverDir = sysDep.defaultDriverDir
        self.workDir = sysDep.defaultWorkDir

        if driver is not None:
            self.driver = driver
        else:
            try:
                self.driver = Driver(self.driverDir)
            except IOError:
                sys.stderr.write("Couldn't initialize DOR driver\n")
                traceback.print_exc()
                self.driver = None

    def _dispatch(self, method, params):
        """Hack around Linux python bug"""
        return getattr(self, method)(*params)

    def disableBlocking(self):
        """Disable blocking"""
        if not self.driver:
            sys.stderr.write("Not running 'disable_blocking': No driver\n");
        else:
            self.driver.disable_blocking()
        return ''

    def dtsxAll(self):
        """Run dtsxall on domhub"""
        return self.sysDep.runDtsxAll()

    def getActiveDoms(self):
        """list all active DOMs"""
        if not self.driver:
            sys.stderr.write("Not running 'get_active_doms': No driver\n");
            return { }
        else:
            return self.driver.get_active_doms()

    def goToIceBoot(self):
        """Make sure all DOMs are running IceBoot"""
        if not self.driver:
            sys.stderr.write("Not running 'go_to_iceboot': No driver\n");
        else:
            self.driver.go_to_iceboot()
        return ''

    def killDomProcesses(self):
        """kill all processes which might be using DOMs"""
        self.sysDep.killDomProcesses()

    def run(args):
        """Act as a /etc/rc.d script for HubDaemon"""
        sysDep = HubSysDep()

        action=None
        if len(args) > 1:
            action = args[1]

        errMsg = daemon.handle_action(action, outFile=sysDep.daemonLog,
                                      errFile=sysDep.daemonLog,
                                      pidFile=sysDep.daemonPid)
        if errMsg is not None:
            if len(errMsg) > 0:
                sys.stderr.write(errMsg + "\n");
                sys.exit(1)
        else:
            started = False
            while not started:
                try:
                    server = XMLServer('', sysDep.port)
                    started = True
                except:
                    sysDep.port = sysDep.port + 1

            sys.stdout.write("Starting Daemon at " + os.popen('date').read() +
                             "\n")
            sys.stdout.flush()

            server.register_instance(HubDaemon(sysDep))
            server.serve_forever()

    run = staticmethod(run)

    def offAll(self):
        """turn off all DOMs"""
        if not self.driver:
            sys.stderr.write("Not running 'offAll': No driver\n");
        else:
            self.driver.offAll()
        return ''

    def onAll(self):
        """turn on all DOMs"""
        if not self.driver:
            sys.stderr.write("Not running 'onAll': No driver\n");
        else:
            self.driver.onAll()
        return ''

    def ready(self):
        """make the DOM ready for a TestDAQ run"""
        jarList = self.sysDep.getJarList(self.workDir)
        classPath = self.sysDep.makeClassPath(jarList)
        self.sysDep.killProcess('dtsx')
        self.sysDep.killProcess('rmiregistry')
        self.disableBlocking()
        self.offAll()
        if classPath is not None:
            os.environ['CLASSPATH'] = classPath
        self.sysDep.startDaemon('rmiregistry', pidFile=self.sysDep.rmiRegPid)
        self.sysDep.startDomHubApp(pidFile=self.sysDep.domhubAppPid)
        return ''

    def setWorkDir(self, dir):
        """set the working directory on the DOMHub"""
        if not os.path.isdir(dir):
            return 'Bad path "' + dir + '"'

        self.workDir = dir
        return ''

    def setDriverDir(self, dir):
        """Set the root directory of the domhub driver files
        (e.g. '/proc/driver/domhub')
        """
        if not os.path.isdir(dir):
            return 'Bad path "' + dir + '"'

        self.driverDir = dir
        self.driver = Driver(self.driverDir)
        return ''

class HubProxy(ServerProxy):
    """Client proxy for HubDaemon"""
    def __init__(self, host):
        sysDep = HubSysDep()
        ServerProxy.__init__(self, ("http://%s:%d" % (host, sysDep.port)))

if __name__ == "__main__":
    HubDaemon.run(sys.argv)
