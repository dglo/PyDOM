#!/usr/bin/env python
#
# Mock database interface

class Warning(StandardError):
    """
    Exception raised for important warnings like data
    truncations while inserting, etc. It must be a subclass of
    the Python StandardError (defined in the module
    exceptions).
    """

class Error(StandardError):
    """
    Exception that is the base class of all other error
    exceptions. You can use this to catch all errors with one
    single 'except' statement. Warnings are not considered
    errors and thus should not use this class as base. It must
    be a subclass of the Python StandardError (defined in the
    module exceptions).
    """

class InterfaceError(Error):
    """
    Exception raised for errors that are related to the
    database interface rather than the database itself.  It
    must be a subclass of Error.
    """

class DatabaseError(Error):
    """
    Exception raised for errors that are related to the
    database.  It must be a subclass of Error.
    """

class DataError(Error):
    """
    Exception raised for errors that are due to problems with
    the processed data like division by zero, numeric value
    out of range, etc. It must be a subclass of DatabaseError.
    """

class OperationalError(DatabaseError):
    """
    Exception raised for errors that are related to the
    database's operation and not necessarily under the control
    of the programmer, e.g. an unexpected disconnect occurs,
    the data source name is not found, a transaction could not
    be processed, a memory allocation error occurred during
    processing, etc.  It must be a subclass of DatabaseError.
    """

class IntegrityError(DatabaseError):
    """
    Exception raised when the relational integrity of the
    database is affected, e.g. a foreign key check fails.  It
    must be a subclass of DatabaseError.
    """

class InternalError(DatabaseError):
    """
    Exception raised when the database encounters an internal
    error, e.g. the cursor is not valid anymore, the
    transaction is out of sync, etc.  It must be a subclass of
    DatabaseError.
    """

class ProgrammingError(DatabaseError):
    """
    Exception raised for programming errors, e.g. table not
    found or already exists, syntax error in the SQL
    statement, wrong number of parameters specified, etc.  It
    must be a subclass of DatabaseError.
    """

class NotSupportedError(DatabaseError):
    """
    Exception raised in case a method or database API was used
    which is not supported by the database, e.g. requesting a
    .rollback() on a connection that does not support
    transaction or has transactions turned off.  It must be a
    subclass of DatabaseError.
    """

class MockCursor:
    """
    These objects represent a database cursor, which is used to
    manage the context of a fetch operation. Cursors created from 
    the same connection are not isolated, i.e., any changes
    done to the database by a cursor are immediately visible by the
    other cursors. Cursors created from different connections can
    or can not be isolated, depending on how the transaction support
    is implemented (see also the connection's rollback() and commit() 
    methods.)
    """

    def __init__(self, name="Anonymous"):
        # description:
        #   This read-only attribute is a sequence of 7-item
        #   sequences.  Each of these sequences contains information
        #   describing one result column: (name, type_code,
        #   display_size, internal_size, precision, scale,
        #   null_ok). The first two items (name and type_code) are
        #   mandatory, the other five are optional and must be set to
        #   None if meaningful values are not provided.
        #
        #   This attribute will be None for operations that
        #   do not return rows or if the cursor has not had an
        #   operation invoked via the executeXXX() method yet.
        #   
        #   The type_code can be interpreted by comparing it to the
        #   Type Objects specified in the section below.
        self.description = None

        # rowcount:
        #   This read-only attribute specifies the number of rows that
        #   the last executeXXX() produced (for DQL statements like
        #   'select') or affected (for DML statements like 'update' or
        #   'insert').
        #
        #   The attribute is -1 in case no executeXXX() has been
        #   performed on the cursor or the rowcount of the last
        #   operation is not determinable by the interface.
        #
        #   Note: Future versions of the DB API specification could
        #   redefine the latter case to have the object return None
        #   instead of -1.
        self.rowCountInternal = -1

        # arraysize:
        #   This read/write attribute specifies the number of rows to
        #   fetch at a time with fetchmany(). It defaults to 1 meaning
        #   to fetch a single row at a time.
        #
        #   Implementations must observe this value with respect to
        #   the fetchmany() method, but are free to interact with the
        #   database a single row at a time. It may also be used in
        #   the implementation of executemany().
        self.arraysize=1

        self.name = name
        self.closed = False
        self.queries = {}

        self.rowcount = None
        self.activeResult = None

        self.debug = None

    rowcount = property(lambda self: self.rowCountInternal)

    def __del__(self):
        if not self.closed:
            self.close()

    def __repr__(self):
        return 'MockCursor:' + str(self.name) + '[' + str(self.rowcount) + \
            ' rows (' + str(self.activeResult) + '), ' + str(self.queries) + \
            ']'

    def addExpectedExecute(self, qStr, *results):
        resultList = None
        for i in range(len(results)):
            r = results[i]
            if r is None:
                if i > 0:
                    if resultList is None:
                        resultList = [None]
                    resultList.append(None)
            else:
                if i == 0:
                    resultList = []
                elif i == 1 and resultList is None:
                    resultList = [None]

                if isinstance(r, (list, tuple)):
                    resultList.append(r)
                else:
                    if self.debug:
                        print "Fixing result type " + \
                            str(type(r)) + " for result " + str(r)
                    resultList.append((r, ))

        if not self.queries.has_key(qStr):
            if resultList is None:
                self.queries[qStr] = None
            else:
                self.queries[qStr] = [resultList, ]
        else:
            obj = self.queries[qStr]
            if isinstance(obj, list):
                tmpList = obj
            else:
                tmpList = []
                tmpList.append(obj)
                self.queries[qStr] = tmpList

            tmpList.append(resultList)

        if self.debug:
            print self.name + ' QUERIES: ' + str(self.queries)

    def verify(self):
        if len(self.queries) != 0:
            if len(self.queries) == 1:
                plural = "y"
            else:
                plural = "ies"
            raise ProgrammingError, str(len(self.queries)) + \
                " quer" + plural + " not used in MockCursor " + self.name

        if not self.closed:
            raise ProgrammingError, "MockCursor " + self.name + \
                " was not closed"

    def callproc(self, procname, *params):
        """
        (This method is optional since not all databases provide
        stored procedures.)
        
        Call a stored database procedure with the given name. The
        sequence of parameters must contain one entry for each
        argument that the procedure expects. The result of the
        call is returned as modified copy of the input
        sequence. Input parameters are left untouched, output and
        input/output parameters replaced with possibly new values.
        
        The procedure may also provide a result set as
        output. This must then be made available through the
        standard fetchXXX() methods.        
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + " is closed"

        raise Error, "Unimplemented"

    def close(self):
        """
        Close the cursor now (rather than whenever __del__ is
        called).  The cursor will be unusable from this point
        forward; an Error (or subclass) exception will be raised
        if any operation is attempted with the cursor.
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + \
                " has already been closed"

        self.closed = True

    def execute(self, operation, *param):
        """
        Prepare and execute a database operation (query or
        command).  Parameters may be provided as sequence or
        mapping and will be bound to variables in the operation.
        Variables are specified in a database-specific notation
        (see the module's paramstyle attribute for details).
        
        A reference to the operation will be retained by the
        cursor.  If the same operation object is passed in again,
        then the cursor can optimize its behavior.  This is most
        effective for algorithms where the same operation is used,
        but different parameters are bound to it (many times).
        
        For maximum efficiency when reusing an operation, it is
        best to use the setinputsizes() method to specify the
        parameter types and sizes ahead of time.  It is legal for
        a parameter to not match the predefined information; the
        implementation should compensate, possibly with a loss of
        efficiency.
        
        The parameters may also be specified as list of tuples to
        e.g. insert multiple rows in a single operation, but this
        kind of usage is depreciated: executemany() should be used
        instead.
        
        Return values are not defined.
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + " is closed"

        if len(param) > 0:
            raise ProgrammingError, "Too many parameters to execute()"

        if not self.queries.has_key(operation):
            raise ProgrammingError, "Bad query '" + str(operation) + \
                "' for MockCursor " + self.name

        obj = self.queries[operation]
        if self.debug:
            print "Q[" + operation + "] => " + str(obj)
        if not isinstance(obj, list):
            self.activeResult = obj
            del self.queries[operation]
            if self.debug:
                print "DEL Q[" + operation + "]"
        else:
            self.activeResult = obj[0]
            del obj[0]
            if self.debug:
                print "GOT Q[" + operation + "][0]"

            if len(obj) == 0:
                del self.queries[operation]
                #print "DEL Q[" + operation + "]"
            elif len(obj) == 1:
                self.queries[operation] = obj
                if self.debug:
                    print "NOW Q[" + operation + "] => " + \
                        str(self.queries[operation])

        if self.activeResult is None:
            self.rowcount = 0
        else:
            if self.debug:
                print "AR " + str(self.activeResult)
            self.rowcount = len(self.activeResult)
            if self.debug:
                print "RC " + str(self.rowcount)

    def executemany(self, operation, *param):
        """
        Prepare a database operation (query or command) and then
        execute it against all parameter sequences or mappings
        found in the sequence seq_of_parameters.
        
        Modules are free to implement this method using multiple
        calls to the execute() method or by using array operations
        to have the database process the sequence as a whole in
        one call.
        
        Use of this method for an operation which produces one or
        more result sets constitutes undefined behavior, and the
        implementation is permitted (but not required) to raise 
        an exception when it detects that a result set has been
        created by an invocation of the operation.
        
        The same comments as for execute() also apply accordingly
        to this method.
        
        Return values are not defined.
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + " is closed"

        raise Error, "Unimplemented"

    def fetchone(self):
        """
        Fetch the next row of a query result set, returning a
        single sequence, or None when no more data is
        available.
        
        An Error (or subclass) exception is raised if the previous
        call to executeXXX() did not produce any result set or no
        call was issued yet.
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + " is closed"

        if self.activeResult is None:
            return None

        if self.rowcount == 0:
            return None

        result = self.activeResult[0]
        self.rowcount = len(self.activeResult) - 1
        if self.rowcount == 0:
            self.activeResult = None
        else:
            del self.activeResult[0]

        if self.debug:
            print 'FETCHONE => ' + str(result) + '(' + str(type(result)) + \
                ') [' + str(self.rowcount) + ' rows remain] ' + \
                str(self.activeResult)
        return result

    def fetchmany(self, size=None):
        """
        Fetch the next set of rows of a query result, returning a
        sequence of sequences (e.g. a list of tuples). An empty
        sequence is returned when no more rows are available.
        
        The number of rows to fetch per call is specified by the
        parameter.  If it is not given, the cursor's arraysize
        determines the number of rows to be fetched. The method
        should try to fetch as many rows as indicated by the size
        parameter. If this is not possible due to the specified
        number of rows not being available, fewer rows may be
        returned.
        
        An Error (or subclass) exception is raised if the previous
        call to executeXXX() did not produce any result set or no
        call was issued yet.
        
        Note there are performance considerations involved with
        the size parameter.  For optimal performance, it is
        usually best to use the arraysize attribute.  If the size
        parameter is used, then it is best for it to retain the
        same value from one fetchmany() call to the next.
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + " is closed"

        if arraysize == None:
            arraysize = self.arraysize

        raise Error, "Unimplemented"

    def fetchall(self):
        """
        Fetch all (remaining) rows of a query result, returning
        them as a sequence of sequences (e.g. a list of tuples).
        Note that the cursor's arraysize attribute can affect the
        performance of this operation.
        
        An Error (or subclass) exception is raised if the previous
        call to executeXXX() did not produce any result set or no
        call was issued yet.
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + " is closed"

        if self.activeResult is None:
            raise DataError, "No data found"

        if self.rowcount == 0:
            return None

        result = self.activeResult
        self.rowcount = 0
        self.activeResult = None

        if self.debug:
            print 'FETCHALL => ' + str(result) + '(' + str(type(result)) + \
                ') [' + str(self.rowcount) + ' rows remain] ' + \
                str(self.activeResult)
        return result

    def nextset(self):
        """
        (This method is optional since not all databases support
        multiple result sets.)
        
        This method will make the cursor skip to the next
        available set, discarding any remaining rows from the
        current set.
        
        If there are no more sets, the method returns
        None. Otherwise, it returns a true value and subsequent
        calls to the fetch methods will return rows from the next
        result set.
        
        An Error (or subclass) exception is raised if the previous
        call to executeXXX() did not produce any result set or no
        call was issued yet.
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + " is closed"

        raise Error, "Unimplemented"

    def setinputsizes(self, sizes):
        """
        This can be used before a call to executeXXX() to
        predefine memory areas for the operation's parameters.
        
        sizes is specified as a sequence -- one item for each
        input parameter.  The item should be a Type Object that
        corresponds to the input that will be used, or it should
        be an integer specifying the maximum length of a string
        parameter.  If the item is None, then no predefined memory
        area will be reserved for that column (this is useful to
        avoid predefined areas for large inputs).
        
        This method would be used before the executeXXX() method
        is invoked.
        
        Implementations are free to have this method do nothing
        and users are free to not use it.
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + " is closed"

        raise Error, "Unimplemented"

    def setoutputsizes(self, size, column=None):
        """
        Set a column buffer size for fetches of large columns
        (e.g. LONGs, BLOBs, etc.).  The column is specified as an
        index into the result sequence.  Not specifying the column
        will set the default size for all large columns in the
        cursor.
        
        This method would be used before the executeXXX() method
        is invoked.
        
        Implementations are free to have this method do nothing
        and users are free to not use it.
        """

        if self.closed:
            raise ProgrammingError, "Cursor " + self.name + " is closed"

        raise Error, "Unimplemented"

class MockConnection:
    def __init__(self):
        self.cursorList = []
        self.usedList = []
        self.expectedClose = 0
        self.actualClose = 0
        self.debug = None

    def __del__(self):
        self.close()

    def addCursor(self, cursor):
        if self.debug:
            print "ADD CURSOR " + str(cursor)
        self.cursorList.append(cursor)

    def verify(self):
        if len(self.cursorList) != 0:
            unused = []
            if len(self.cursorList) == 1:
                verb = " was"
            else:
                verb = "s were"
            raise ProgrammingError, str(len(self.cursorList)) + \
                " statement" + verb + " not used (" + str(self.cursorList) + \
                ')'

        for c in self.usedList:
            c.verify()

        if self.expectedClose != self.actualClose:
            raise ProgrammingError, "Expected " + str(self.expectedClose) + \
                " close(), got " + str(self.actualClose)

    def close(self):
        """
        Close the connection now (rather than whenever __del__ is
        called).  The connection will be unusable from this point
        forward; an Error (or subclass) exception will be raised
        if any operation is attempted with the connection. The
        same applies to all cursor objects trying to use the
        connection.  Note that closing a connection without
        committing the changes first will cause an implicit
        rollback to be performed.
        """
        self.actualClose = self.actualClose + 1

    def commit(self):
        """
        Commit any pending transaction to the database. Note that
        if the database supports an auto-commit feature, this must
        be initially off. An interface method may be provided to
        turn it back on.
        
        Database modules that do not support transactions should
        implement this method with void functionality.
        """
        raise Error, "Unimplemented"

    def rollback(self):
        """
        This method is optional since not all databases provide
        transaction support.
        
        In case a database does provide transactions this method
        causes the the database to roll back to the start of any
        pending transaction.  Closing a connection without
        committing the changes first will cause an implicit
        rollback to be performed.
        """
        raise Error, "Unimplemented"

    def cursor(self):
        """
        Return a new Cursor Object using the connection.  If the
        database does not provide a direct cursor concept, the
        module will have to emulate cursors using other means to
        the extent needed by this specification.
        """
        if len(self.cursorList) == 0:
            raise ProgrammingError, "No cursors remaining"

        cursor = self.cursorList[0]
        del self.cursorList[0]
        if self.debug:
            print "USE CURSOR " + str(cursor)
        self.usedList.append(cursor)

        return cursor

class MockDB:
    def __init__(self):
        # apilevel:
        #   String constant stating the supported DB API level.
        #   Currently only the strings '1.0' and '2.0' are allowed.
        self.apilevel = '2.0'

        # threadsafety:
        #   Integer constant stating the level of thread safety the
        #   interface supports. Possible values are:
        #
        #       0     Threads may not share the module.
        #       1     Threads may share the module, but not connections.
        #       2     Threads may share the module and connections.
        #       3     Threads may share the module, connections and
        #             cursors.
        #
        #   Sharing in the above context means that two threads may
        #   use a resource without wrapping it using a mutex semaphore
        #   to implement resource locking. Note that you cannot always
        #   make external resources thread safe by managing access
        #   using a mutex: the resource may rely on global variables
        #   or other external sources that are beyond your control.
        self.threadsafety = 0

        # threadsafety:
        #   String constant stating the type of parameter marker
        #   formatting expected by the interface. Possible values are:
        #
        #       'qmark'         Question mark style, 
        #                       e.g. '...WHERE name=?'
        #       'numeric'       Numeric, positional style, 
        #                       e.g. '...WHERE name=:1'
        #       'named'         Named style, 
        #                       e.g. '...WHERE name=:name'
        #       'format'        ANSI C printf format codes, 
        #                       e.g. '...WHERE name=%s'
        #       'pyformat'      Python extended format codes, 
        #                       e.g. '...WHERE name=%(name)s'
        self.paramstyle = 'format'

    def connect(*arg):
        """
        Constructor for creating a connection to the database.
        Returns a Connection Object. It takes a number of
        parameters which are database dependent.
        """
        raise Error, "Unimplemented"

if __name__ == '__main__':
    sys.exit(1)
