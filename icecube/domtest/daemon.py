#!/usr/bin/env python
#
# functions for starting a Unix daemon

import os,signal,sys,time
import traceback

def close_all_files():
    """Close all open files.  Try the system configuration variable,
    SC_OPEN_MAX, for the maximum number of open files to close.  If it
    doesn't exist, use the default value (configurable)."""
    try:
        maxfd = os.sysconf("SC_OPEN_MAX")
    except (AttributeError, ValueError):
        maxfd = 256       # default maximum

    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:   # ERROR (ignore)
            pass

def create(inFile='/dev/null', outFile='/dev/null', errFile='/dev/null',
           pidFile=None):
    """Detach a process from the controlling terminal and run it in the
    background as a daemon.

    Default daemon behaviors (they can be modified):
        1.) Ignore SIGHUP signals.
        2.) Default current working directory to the "/" directory.
        3.) Set the current file creation mode mask to 0.
        4.) Close all open files (0 to [SC_OPEN_MAX or 256]).
        5.) Redirect standard I/O streams to "/dev/null".

    Failed fork() calls will return a tuple: (errno, strerror).  This
    behavior can be modified to meet your program's needs.

    Resources:
        Advanced Programming in the Unix Environment: W. Richard Stevens
        Unix Network Programming (Volume 1): W. Richard Stevens
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
    """

    __author__ = "Chad J. Schroeder"

    try:
        # Fork a child process so the parent can exit.  This will return
        # control to the command line or shell.  This is required so that
        # the new process is guaranteed not to be a process group leader.
        # We have this guarantee because the process GID of the parent is
        # inherited by the child, but the child gets a new PID, making it
        # impossible for its PID to equal its
        # PGID.
        pid = os.fork()
    except OSError as e:
        return((e.errno, e.strerror))     # ERROR (return a tuple)

    if (pid != 0):
        os._exit(0)      # Exit parent of the first child.

    rtnval = start_child(pidFile)
    close_all_files()
    open_special(inFile, outFile, errFile)

    return rtnval

def get_pid(pidFile):
    """Get process ID from the PID file."""
    try:
        pf  = file(pidFile,'r')
        pid = int(pf.read().strip())
        pf.close()
    except IOError:
        pid = None
    return pid

def handle_action(action, inFile='/dev/null', outFile='/dev/null',
                  errFile=None, pidFile='/tmp/daemon.pid',
                  startmsg = 'started with pid %s'):
    """Returns None if daemon was started, '' if there were no problems,
    or any non-empty string for an error message"""
    pid = get_pid(pidFile)
    if 'stop' == action or 'restart' == action:
        if not pid:
            return 'Could not stop, pid file "%s" missing.' % pidFile
        try:
            while True:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
        except OSError as err:
            err = str(err)
            if err.find("No such process") > 0:
                os.remove(pidFile)
                if 'stop' == action:
                    return ''
                action = 'start'
                pid = None
            else:
                return str(err)
    if 'start' == action:
        if pid:
            return 'Start aborted since pid file "%s" exists.' % pidFile
        create(inFile, outFile, errFile, pidFile)
        return None
    return 'usage: %s start|stop|restart' % sys.argv[0]

def run(cmdStr, inFile='/dev/null', outFile='/dev/null', errFile='/dev/null',
        pidFile=None):
    """Run the specified command as a daemon."""
    try:
        pid = os.fork()
    except OSError as e:
        return((e.errno, e.strerror))     # ERROR (return a tuple)

    if pid == 0:
        rtnval = start_child(pidFile)

        close_all_files()

        open_special(inFile, outFile, errFile)

        cmdList = cmdStr.split()
        if (len(cmdList) == 1):
            rtnval = os.execvp(cmdList[0], cmdList)
        else:
            rtnval = os.execvp(cmdList[0], cmdList)
        if rtnval != 0 and pidFile is not None:
            file.remove(pidFile)

def open_special(inFile, outFile, errFile):
    """Open standard input, output, and error file handles."""
    writeFlags = (os.O_WRONLY | os.O_NDELAY | os.O_APPEND | os.O_CREAT)

    os.open(inFile, os.O_RDONLY)            # standard input (0)
    os.open(outFile, writeFlags)            # standard output (1)
    os.open(errFile, writeFlags)            # standard error (2)

def start_child(pidFile=None):
    """Start a daemon child process."""

    # Call os.setsid() to become the session leader of this new
    # session.  The process also becomes the process group leader of the
    # new process group.  Since a controlling terminal is associated with
    # a session, and this new session has not yet acquired a controlling
    # terminal our process now has no controlling terminal.  This
    # shouldn't fail, since we're guaranteed that the child is not a
    # process group leader.
    os.setsid()

    # When the first child terminates, all processes in the second child
    # are sent a SIGHUP, so it's ignored.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    try:
        # Fork a second child to prevent zombies.  Since the first child
        # is a session leader without a controlling terminal, it's
        # possible for it to acquire one by opening a terminal in the
        # future.  This second fork guarantees that the child is no
        # longer a session leader, thus preventing the daemon from ever
        # acquiring a controlling terminal.
        pid = os.fork()
    except OSError as e:
        return((e.errno, e.strerror))

    if (pid != 0):     # The second parent
        if pidFile is not None:
            try:
                open(pidFile,'w').write("%d" % pid)
            except IOError as err:
                sys.stderr.write("Couldn't create PID file \"%s\"\n" % pidFile)

        os._exit(0)    # Exit parent (the first child) of the second child.
    else:
        # Ensure that the daemon doesn't keep any directory in use.
        # Failure to do this could make a filesystem unmountable.
        os.chdir("/")
        # Give the child complete control over permissions.
        os.umask(0)

    return None
