#!/usr/bin/env python
#
# Parse histo-clean (monitoring) data

import os, sys
from icecube.domtest.DOMProdTestDB import DOMProdTestDB, FATRun
from icecube.domtest.LCChainFile import LCChainFile
from icecube.domtest.MonitorFile import MonitorFile
from icecube.domtest.RebootFile import RebootFile

##############################################################################

def process(dir, db, fatId, isLCChainDir=False):
    subdir = []
    for entry in os.listdir(dir):
        path = os.path.join(dir, entry)

        if os.path.isdir(path):
            subdir.append(path)
        elif entry.endswith('~'):
            # ignore editted files
            continue
        elif (isLCChainDir or entry.find('lcchain') >= 0):
            LCChainFile.process(path, db, fatId)
        elif entry == 'histo-clean.txt':
            MonitorFile.process(path, db, fatId)
        elif entry.startswith('reboot.dat') or \
                (entry.startswith('reboot') and entry.endswith('.dat')):
            RebootFile.process(path, db, fatId)

    for sd in subdir:
        process(sd, db, fatId, isLCChainDir or (subdir == 'lcchain'))

def processArgs(fatRun):
    deleteOld = False
    dir = None
    fatName = None

    usage = False
    if len(sys.argv) < 3:
        usage = True
    else:
        for i in range(1, len(sys.argv)):
            arg = sys.argv[i]

            if len(arg) > 1 and arg[0] == '-':
                if arg[1] == 'd':
                    deleteOld = True
                else:
                    sys.stderr.write('Error: Unknown option "' + str(arg) +
                                     "\"\n")
                    usage = True
            elif os.path.isdir(arg):
                if dir is None:
                    dir = arg
                elif fatName is not None:
                    sys.stderr.write('Error: Extra argument "' +
                                     str(arg) + "\"\n")
                    usage = True
                elif fatRun.isName(dir):
                    fatName = dir
                    dir = arg
                elif fatRun.isName(arg):
                    fatName = arg
                else:
                    sys.stderr.write('Error: Unrecognized argument "' +
                                     str(arg) + "\"\n")
                    usage = True
            elif fatRun.isName(arg):
                if fatName is None:
                    fatName = arg
                elif dir is not None:
                    sys.stderr.write('Error: Unrecognized argument "' +
                                     str(arg) + "\"\n")
                    usage = True
                elif os.path.isdir(arg):
                    dir = arg
                elif os.path.isdir(fatName):
                    dir = fatName
                    fatName = arg
                else:
                    sys.stderr.write('Error: Unrecognized argument "' +
                                     str(arg) + "\"\n")
                    usage = True
            else:
                sys.stderr.write('Error: Unrecognized argument "' +
                                 str(arg) + "\"\n")
                usage = True

            if usage:
                break

    if usage:
        sys.stderr.write('Usage: ' + sys.argv[0] +
                         ' [-d(eleteOldFAT)' +
                         " fat_name fat_directory\n")
        sys.exit(1)

    return (deleteOld, dir, fatName)

##############################################################################

db = DOMProdTestDB()

fatRun = FATRun(db)

(deleteOld, dir, fatName) = processArgs(fatRun)

fatId = fatRun.getId(fatName)

if deleteOld:
    LCChainFile.deleteOldRows(db, fatId)
    MonitorFile.deleteOldRows(db, fatId)
    RebootFile.deleteOldRows(db, fatId)

process(dir, db, fatId)

db.close()
