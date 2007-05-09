#!/usr/bin/env python
#
# Look up a DOM/main board by various identifiers

import MySQLdb
import re,sys
import icecube.domtest.DOMProdTestUtil as DOMProdTestUtil
from icecube.domtest.DOMProdTestDB import DOMProdTestDB

###############################################################################

TYPEKEY_DOM = 'Dom'
TYPEKEY_MB = 'Main'

def dumpAssembly(row, spaces, showIds):
    """Dump Assembly row"""
    (assemId,prodId,techId,dateTime) = row

    if not showIds:
        idStr = ''
    else:
        idStr = ' (assem#' + str(assemId) + ')'

    print '  Created ' + str(dateTime) + idStr

def dumpDOM(db, hardSerial, tagSerial, showIds):
    """Dump DOM data"""
    domList = fetchProdByTypeSerial(db, TYPEKEY_DOM, hardSerial, tagSerial)
    for row in domList:
        (prodId,hardSerial,newTag,type) = row
        dumpProduct(row, '', showIds)

        name = fetchDOMNameByProdId(db, prodId)
        if name is not None:
            print '  Name ' + name

        assemList = fetchAssemByProdId(db, prodId)
        if len(assemList) == 0:
            print '  No Assembly rows' 
        else:
            for row in assemList:
                (assemId,aProdId,techId,datetime) = row
                dumpAssembly(row, '  ', showIds)
                apList = fetchAssemProdByAssemId(db, assemId)
                if len(apList) == 0:
                    print '    No AssemblyProduct rows'
                else:
                    for subProdId in apList:
                        subList = fetchProdByProdId(db, subProdId)
                        if len(subList) == 0:
                            if not showIds:
                                idStr = ''
                            else:
                                idStr = ' for Prod#' + str(subProdId)
                            print 'No Product data' + idStr
                        else:
                            for row in subList:
                                dumpProduct(row, '    ', showIds)

def dumpMB(db, hardSerial, tagSerial, showIds):
    """Dump Main Board data"""
    mbList = fetchProdByTypeSerial(db, TYPEKEY_MB, hardSerial, tagSerial)
    for row in mbList:
        (prodId,newHard,newTag,type) = row
        dumpProduct(row, '', showIds)

        apList = fetchAssemProdByProdId(db, prodId)
        if len(apList) == 0:
            print '  No AssemblyProduct rows'
        else:
            for assemId in apList:
                list = fetchAssemByAssemId(db, assemId)
                if len(list) == 0:
                    if not showIds:
                        idStr = ''
                    else:
                        idStr = ' for Assem#' + str(assemId)
                    print '  No Assembly rows'
                else:
                    for row in list:
                        (xAssemId,xProdId,xTechId,xDateTime) = row
                        dumpAssembly(row, '  ', showIds)
                        subList = fetchProdByProdId(db, xProdId)
                        for row in subList:
                            dumpProduct(row, '    ', showIds)

                            (domProdId,domHard,domTag,domType) = row
                            name = fetchDOMNameByProdId(db, domProdId)
                            if name is not None:
                                print '    Name ' + name

def dumpProduct(row, spaces, showIds):
    """Dump Product row"""
    (prodId,hardSerial,tagSerial,typeName) = row

    if hardSerial is None or hardSerial == '':
        hardStr = ''
    else:
        hardStr = ' hard "' + hardSerial + '"'

    if tagSerial is None or tagSerial == '':
        tagStr = ''
    else:
        tagStr = ' tag "' + tagSerial + '"'

    if not showIds:
        idStr = ''
    else:
        idStr = ' (prod#' + str(prodId) + ')'
    print spaces + str(typeName) + hardStr + tagStr + idStr

def fetchAssemByAssemId(db, assemId):
    """Fetch a row from the Assembly table using an 'assem_id' key"""
    cursor = db.cursor()
    cursor.execute('select prod_id,tech_id,datetime from Assembly' +
                   ' where assem_id=' + str(assemId))

    list = []
    while int(cursor.rowcount) > 0:
        row = cursor.fetchone()
        if row is None:
            break

        (prodId,techId,datetime) = row
        list.append((assemId,prodId,techId,datetime))

    cursor.close()

    return list

def fetchAssemByProdId(db, prodId):
    """Fetch a row from the Assembly table using a 'prod_id' key"""
    cursor = db.cursor()
    cursor.execute('select assem_id,tech_id,datetime from Assembly' +
                   ' where prod_id=' + str(prodId))

    list = []

    while int(cursor.rowcount) > 0:
        row = cursor.fetchone()
        if row is None:
            break

        (assemId,techId,datetime) = row
        list.append((assemId,prodId,techId,datetime))

    cursor.close()

    return list

def fetchAssemProdByAssemId(db, assemId):
    """Fetch a row from the AssemblyProduct table using an 'assem_id' key"""
    cursor = db.cursor()
    cursor.execute('select prod_id from AssemblyProduct' +
                   ' where assem_id=' + str(assemId))

    list = []

    while int(cursor.rowcount) > 0:
        row = cursor.fetchone()
        if row is None:
            break

        (prodId,) = row
        list.append(prodId)

    cursor.close()

    return list

def fetchAssemProdByProdId(db, prodId):
    """Fetch a row from the AssemblyProduct table using a 'prod_id' key"""
    cursor = db.cursor()
    cursor.execute('select assem_id from AssemblyProduct' +
                   ' where prod_id=' + str(prodId))

    list = []
    while int(cursor.rowcount) > 0:
        row = cursor.fetchone()
        if row is None:
            break

        (assemId,) = row
        list.append(assemId)

    cursor.close()

    return list

def fetchDOMTagByName(db, name):
    """Fetch a DOM tag serial number using the DOM name"""
    cursor = db.cursor()
    cursor.execute('select p.tag_serial from Product p,ProductName n' +
                   ' where p.prod_id=n.prod_id and n.name="' + name + '"')

    domTag = None
    if int(cursor.rowcount) > 0:
        row = cursor.fetchone()
        if row is not None:
            (domTag,) = row

    cursor.close()

    return domTag

def fetchDOMNameByProdId(db, prodId):
    """Fetch a DOM name using a 'prod_id' key"""
    cursor = db.cursor()
    cursor.execute('select name from ProductName where prod_id=' + str(prodId))

    name = None
    if int(cursor.rowcount) > 0:
        row = cursor.fetchone()
        if row is not None:
            (name,) = row

    cursor.close()

    return name

def fetchProdByProdId(db, prodId):
    """Fetch a row from the Product table using a 'prod_id' key"""
    cursor = db.cursor()
    cursor.execute('select p.hardware_serial,p.tag_serial,pt.name' +
                   ' from Product p, ProductType pt' +
                   ' where p.prod_id=' + str(prodId) +
                   ' and p.prodtype_id=pt.prodtype_id')

    list = []

    while int(cursor.rowcount) > 0:
        row = cursor.fetchone()
        if row is None:
            break

        (hardSerial,tagSerial,typeName) = row
        list.append((prodId,hardSerial,tagSerial,typeName))

    cursor.close()

    return list

def fetchProdByTypeSerial(db, typeName, hardSerial, tagSerial):
    """
    Fetch a row from the Product table using the product type keyname
    and/or the hardware serial number and/or the tag serial number
    """
    if typeName is None:
        typeStr = ''
    else:
        typeStr = ' and pt.keyname="' + typeName + '"'

    if hardSerial is None:
        hardStr = ''
    else:
        hardStr = ' and hardware_serial="' + hardSerial + '"'

    if tagSerial is None:
        tagStr = ''
    else:
        tagStr = ' and tag_serial="' + tagSerial + '"'

    cursor = db.cursor()
    cursor.execute('select p.prod_id,p.hardware_serial,p.tag_serial,pt.name' +
                   ' from Product p, ProductType pt' +
                   ' where p.prodtype_id=pt.prodtype_id' +
                   typeStr + hardStr + tagStr)

    list = []

    while int(cursor.rowcount) > 0:
        row = cursor.fetchone()
        if row is None:
            break

        (prodId,newHard,newTag,newType) = row
        list.append((prodId,newHard,newTag,newType))

    cursor.close()

    return list

###############################################################################

db = DOMProdTestDB()

showIds = False

for a in range(1,len(sys.argv)):
    arg = sys.argv[a]
    if arg == '-i':
        showIds = True
    elif DOMProdTestUtil.isDOMSerial(arg):
        dumpDOM(db, None, arg, showIds)
    elif DOMProdTestUtil.isMainBoardSerial(arg):
        dumpMB(db, arg, None, showIds)
    elif DOMProdTestUtil.isMainBoardTag(arg):
        dumpMB(db, None, arg, showIds)
    else:
        domTag = fetchDOMTagByName(db, arg)
        if domTag:
            dumpDOM(db, None, domTag, showIds)
        else:
            print 'Unknown string "' + arg + '"'

db.close()
