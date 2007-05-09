#!/bin/env python
"""
Database utility module

Functions need for the handling of the domprodtest database are defined in this module.

$Id: databaseutil.py,v 1.2 2005/08/17 20:31:22 bvoigt Exp $
"""

def getNextId(db, idName, tableName, labId):
      """
      This method returns the next valid id for the given table in the range of the IDs of a given laboratory.

      db has to be a valid database connection object
      idName is the name of the id column
      labId is the id of the laboratory - within the related id scope the next id is taken

      Throws an exception on any error
      """

      # create db cursor
      cursor = db.cursor()
      
      # Find existing keys in the valid range for this lab
      # If not found, return the lowest id, ie. the laboratory offset
      # else get the highest id and add 1 and care for range overflow
      sql = """
            SELECT IF(max(%s.%s) >= Laboratory.offset, 
               IF(max(%s.%s) < Laboratory.offset + Laboratory.range, max(%s.%s)+1, -1),
            NULL )
            FROM %s , Laboratory  
            WHERE Laboratory.lab_id = %s AND 
            %s.%s >= Laboratory.offset AND
            %s.%s <= Laboratory.offset+Laboratory.range;
            """
      cursor.execute(sql % (tableName, idName,
                            tableName, idName,
                            tableName, idName,
                            tableName, labId,
                            tableName, idName,
                            tableName, idName))

      nextId = cursor.fetchone()[0]
      if nextId is None:
            # no id found, we start from the offset value of the lab
            sql = "SELECT Laboratory.offset FROM Laboratory WHERE Laboratory.lab_id = %s"
            cursor.execute(sql % labId)
            return cursor.fetchone()[0]
      else:
            if nextId < 0:
                  message = "Range overflow for %s in the %s table for laboratory %s " % (idName, tableName, labId)
                  raise Exception(message)
            else:
                  return nextId
#end getNextId

