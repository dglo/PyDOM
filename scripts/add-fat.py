#!/usr/bin/env python
#
# Add a FAT run to the database

import email,os,sys
from email.Utils import parsedate
from icecube.domtest.DOMProdTestDB import DOMProdTestDB, FATData

##############################################################################

def sqldate(dateStr):
    parsed = parsedate(dateStr)
    if parsed is None:
        parsed = parsedate(dateStr + ' 00:00:00 -0000')
        if parsed is None:
            return None

    return '%04d-%02d-%02d' % (parsed[0], parsed[1], parsed[2])

def processArgs():
    ARG_COMMENT = 1
    ARG_ENDDATE = 2
    ARG_STARTDATE = 3

    fatName = None
    startDate= None
    endDate = None
    comment = None

    argArg = None
    usage = False
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]

        argStr = None
        if argArg is not None:
            argStr = arg
        elif len(arg) > 1 and arg[0] == '-':
            if arg[1] == 'c':
                argArg = ARG_COMMENT
                if len(arg) > 2:
                    argStr = arg[2:]
            elif arg[1] == 'e':
                argArg = ARG_ENDDATE
                if len(arg) > 2:
                    argStr = arg[2:]
            elif arg[1] == 's':
                argArg = ARG_STARTDATE
                if len(arg) > 2:
                    argStr = arg[2:]
            else:
                sys.stderr.write('Error: Unknown option "' + str(arg) + "\"\n")
                usage = True
        elif fatName is None:
            fatName = arg
        else:
            sys.stderr.write('Error: Unrecognized argument "' + str(arg) +
                             "\"\n")
            usage = True

        if argStr is not None:
            tmpArg = argArg
            argArg = None

            if tmpArg == ARG_COMMENT:
                comment = argStr
            elif tmpArg == ARG_ENDDATE:
                endDate = sqldate(argStr)
                if endDate is None:
                    sys.stderr.write(sys.argv[0] + ": Invalid end date '" +
                                     argStr + "'\n")
                    usage = True
            elif tmpArg == ARG_STARTDATE:
                startDate = sqldate(argStr)
                if startDate is None:
                    sys.stderr.write(sys.argv[0] + ": Invalid start date '" +
                                     argStr + "'\n")
                    usage = True

        if usage:
            break

    if not usage:
        if fatName is None:
            sys.stderr.write(sys.argv[0] + ": FAT name was not specified\n")
            usage = True
        elif startDate is None:
            sys.stderr.write(sys.argv[0] + ": Start date was not specified\n")
            usage = True

    if usage:
        sys.stderr.write('Usage: ' + sys.argv[0] +
                         ' [-c comment]' +
                         ' [-e endDate]' +
                         ' -s startDate' +
                         " fat_name\n")
        sys.exit(1)

    return (fatName, startDate, endDate, comment)

##############################################################################

(fatName, startDate, endDate, comment) = processArgs()

db = DOMProdTestDB()

if FATData.exists(db, fatName):
    sys.stderr.write(sys.argv[0] + ": FAT '" + fatName + "' already exists\n")
    sys.exit(1)

fatData = FATData(fatName, startDate, endDate, comment)

fatData.save(db)

print "Saved " + fatData.name + " as ID#" + str(fatData.id)

db.close()
