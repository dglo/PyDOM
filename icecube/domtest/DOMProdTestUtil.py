#!/usr/bin/env python
#
# 'domprodtest' database utility methods

import MySQLdb, os, re

###############################################################################

# top-level property name
propTop = 'database'
# default mid-level property name
defaultGroup = 'domprodtest'

# base name for 'driver' property
basenameDriver = 'driver'
# base name for 'url' property
basenameURL = 'url'
# base name for 'user' property
basenameUser = 'user'
# base name for 'url' property
basenamePassword = 'password'
# base name for 'idle seconds' property
basenameIdleSecs = 'idlesecs'
# base name for 'database type' property
basenameType = 'type'
# base name for 'host' property
basenameHost = 'host'
# base name for 'database' property
basenameDatabase = 'database'

# full name for 'driver' property
propDriver = propTop + defaultGroup + '.' + basenameDriver
# full name for 'url' property
propURL = propTop + '.' + defaultGroup + '.' + basenameURL
# full name for 'user' property
propUser = propTop + '.' + defaultGroup + '.' + basenameUser
# full name for 'url' property
propPassword = propTop + '.' + defaultGroup + '.' + basenamePassword
# full name for 'idle seconds' property
propIdleSecs = propTop + '.' + defaultGroup + '.' + basenameIdleSecs
# full name for 'database type' property
propType = propTop + '.' + defaultGroup + '.' + basenameType
# full name for 'host' property
propHost = propTop + '.' + defaultGroup + '.' + basenameHost
# full name for 'database' property
propDatabase = propTop + '.' + defaultGroup + '.' + basenameDatabase

###############################################################################

def connectToDB(props):
    """Connect to MySQL database using the specified properties"""
    return MySQLdb.connect(host=props[propHost],
                           user=props[propUser],
                           passwd=props[propPassword],
                           db=props[propDatabase])

def findFile(dirList, fileList):
    """Return the first file found from the lists of possible directory
    locations and possible filenames."""
    for dir in dirList:
        if dir is None:
            continue
        for file in fileList:
            if file is None:
                continue
            testFile = os.path.join(dir, file)
            if os.path.isfile(testFile):
                return testFile

    return None

def findProperties():
    """Find configuration properties file."""
    configFile = findPropertiesFile()
    if configFile is None:
        raise IOError, "Couldn't find configuration file"

    return readProperties(configFile)

def findPropertiesFile():
    """Find configuration properties file."""
    # list of directories where properties file might live
    propDirs = [os.environ.get('HOME'), '/usr/local/etc', os.getcwd()]

    # list of possible properties file names
    propFiles = ['domprodtest.properties']

    return findFile(propDirs, propFiles)

def getNextId(db, tblName, fldName):
    cursor = db.executeQuery('select max(%s) from %s' % (fldName, tblName))

    list = cursor.fetchone()
    cursor.close()

    if list is None or list[0] is None:
        return 1

    return list[0] + 1

def isDOMSerial(serial):
    """Is the specified string a valid DOM tag serial number?"""
    if serial is None:
        return False

    domPat = re.compile(r'^(...(Ref|Tst|Syn)\d\d|[ATUX][EKPVX][3456789ABCD][PHY]\d\d\d\d)$')

    if not domPat.match(serial):
        return False

    return True

def isMainBoardSerial(serial):
    """Is the specified string a valid main board hardware serial number?"""
    if serial is None:
        return False

    shortLen = 8
    normalLen = 12

    if (len(serial) != shortLen and len(serial) != normalLen):
        return False

    serPat = re.compile(r'^[0123456789abcdefABCDEF]+$')
    if not serPat.match(serial):
        return False

    return True

def isMainBoardTag(serial):
    """Is the specified string a valid main board tag serial number?"""
    if serial is None:
        return False

    tagPat = re.compile(r'^V.*\s\d\d\d\d\d\d$')
    if not tagPat.match(serial):
        return False

    return True

def quoteStr(str):
    if str is None:
        return 'null'
    return '"' + str + '"'

def readProperties(propFile):
    """Read configuration properties file."""
    props = {}

    commentSub = re.compile(r'\s*#.*$')
    propPat = re.compile(r'\s*([^:]+)(:\s*|\s*=\s*)(.*)\s*$')
    urlPat = re.compile(r'jdbc:([^:]+)://([^\/]*)/(.*)$')

    f = open(propFile, 'r')
    for line in f:
        line = commentSub.sub('', line, 1)

        m = propPat.match(line)
        if (m):
            key = m.group(1)
            val = m.group(3)
            props[key] = val

            if key.endswith(basenameURL):
                urlMatch = urlPat.match(val)
                if urlMatch:
                    base = key[:-len(basenameURL)]
                    props[base + basenameType] = urlMatch.group(1)
                    props[base + basenameHost] = urlMatch.group(2)
                    props[base + basenameDatabase] = urlMatch.group(3)

    return props
