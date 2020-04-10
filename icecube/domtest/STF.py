####
#
# (C) 2005 Kael Hanson
#
####

"""
STF database inspection utility module. The main class is 
STFResult which encapsulates the high-level information returned
by an STF test and is the entry point for further information such
as the detailed list of the parameters.

SYNOPSIS
First - the caller must obtain a db instance, e.g.
    >>> import MySQLdb
    >>> db = MySQLdb.connect(user='...',passwd='...',db='...')
Then you will need to get the stf_result_id for the test
you are looking for.  Currently - this must be done using raw SQL:
    >>> c = db.cursor()
    >>> c.execute('''SELECT stf_result_id FROM
    ...     Product JOIN STFResult USING(prod_id)
    ...     WHERE tag_serial='UP5P0500' AND passed=0''')
    187L
    >>> stf_result_ids = [ x[0] for x in c.fetchall() ]
will, for example, retrieve all records for DOM UP5P0500 that failed.
Then you transform the STF result IDs into STFResult objects using
the constructor function:
    >>> rvec = [ STFResult(db, x) for x in stf_result_ids ]
"""
from __future__ import print_function

from builtins import str
from builtins import object
from future.utils import raise_
from array import array


class STFResult(object):
    """
    STF result base class - has info from the STFResult table
    Get the information contained in the <code>STFResult</code>
    and STFParameter tables:
        .prod_id : product ID pointer into the Product table
        .test_name : plain English name of the test
        .test_version : version string of the test
        .date_tested  : date of the test
        .passed       : true = PASS, false = FAIL
        .temp         : MB temperature during test
        .domid        : returns tag_serial from JOIN with Product Table
        .<param_name> : returns STFParameter <param_name> - this name
                       depends on the STF test (and version)
    Thus, one can say for an object s of type STFResult:
    >>> if s.test_name == 'atwd_pulser_spe' and test_version == '1.0':
    ...     print s.atwd_waveform_width, s.atwd_waveform_position
    &c.
    """
    def __init__(self, db, stf_result_id):
        """
        Dual argument constructor - takes db connection object and
        a result_id that points to a valid entry in STFResult
        """
        self.stf_result_id = stf_result_id
        self.db = db
        c = self.db.cursor()
        c.execute(
            "SELECT prod_id,stf_test_id,date_tested,passed,temp " +
            "FROM STFResult WHERE stf_result_id=%s", (stf_result_id)
        )
        prod_id, stf_test_id, date_tested, passed, temp = c.fetchone()
        self.prod_id = prod_id
        c.execute(
            """
            SELECT name,version
            FROM STFTest LEFT JOIN STFTestType USING(stf_testtype_id)
            WHERE stf_test_id=%s
            """,
            stf_test_id
        )
        name, version = c.fetchone()
        self.test_name = name
        self.test_version = version
        self.date_tested = date_tested
        if passed == 0:
            self.passed = False
        else:
            self.passed = True
        self.temp = temp
        
    def __getattr__(self, name):
        if name == 'domid':
            c = self.db.cursor()
            n = c.execute("SELECT tag_serial FROM Product WHERE prod_id=%s",
                self.prod_id
            )
            if n == 1:
                return c.fetchone()[0]
            else:
                return None
        else:
            try:
                return self.getParameter(name)
            except LookupError:
                raise_(AttributeError, "attribute " + str(name) + " does not exist.")
        
    def getParameters(self):
        """
        Return a list of (name,value_index,value,is_output)
        """
        c = self.db.cursor()
        # Now grab the parameters
        c.execute(
            """
            SELECT
                name,value_index,value,is_output
            FROM
                STFResultParameter LEFT JOIN STFParameter USING(stf_param_id)
            WHERE
                stf_result_id=%s
            ORDER BY
                STFParameter.stf_param_id,value_index
            """,
            self.stf_result_id
        )
        return c.fetchall()

    def getParameter(self, param_name):
        """
        Return a particular parameter.  Note for vector parameters
        (value_index>1) the parameter is automatically converted and
        returned as a Python sequence.
        """
        c = self.db.cursor()
        c.execute(
            """
            SELECT
                value_index,value
            FROM
                STFResultParameter LEFT JOIN STFParameter USING(stf_param_id)
            WHERE
                stf_result_id=%s AND name=%s
            ORDER BY
                value_index
            """,
            (self.stf_result_id, param_name)
        )
        a = c.fetchall()
        if len(a) == 0:
            raise_(LookupError, "Parameter " + param_name + " not found.")
        elif len(a) == 1:
            return a[0][1]
        else:
            return [ x[1] for x in a ]
            
def stf_test_summary(db, domid, min_date, max_date):
    """
    This function will obtain a tree of information about STF
    tests run on a particular DOM from min_date to max_date dates.
    """
    c = db.cursor()
    c.execute(
        """
        SELECT stf_result_id
        FROM Product LEFT JOIN STFResult USING(prod_id)
        WHERE tag_serial=%s and date_tested BETWEEN %s AND %s
        ORDER BY date_tested
        """,
        (domid, min_date, max_date)
    )
    results = dict()
    for stf_result_id in c.fetchall():
        stf_result = STFResult(db, stf_result_id)
        if stf_result.test_name not in results:
            results[stf_result.test_name] = list()
        results[stf_result.test_name].append(stf_result)
        
    return results
    
def waive_failure(s, verbose=False):
    """
    Examine an STF test and attempt to waive based on known FAT looser
    parameters. If verbose is true, the conditional check is printed to stdout.
    Pass in a generic STFResult, e.g.
        >>> s = STFResult(db, 100777116)
        >>> if waive_failure(s): print "OK"
    """
    if s.test_name == 'fadc_fe_pulser':
        if s.test_version == '1.0':
            pos = int(s.fadc_fe_pulser_position)
            amp = int(s.fadc_fe_pulser_amplitude)
            pex = int(s.pulser_amplitude_uvolt) * 8 / 5000
            # Expand the window a bit - use +/- 60% inv. +/- 50%
            if verbose:
                print('Checking whether amplitude %i > %i and %i < %s' % (amp, 0.4*pex, amp, 1.6 * pex))
                
            return amp > 0.4 * pex and amp < 1.6 * pex
        
    elif s.test_name == 'flasher_brightness':
        if s.test_version == '1.4':
            err = int(s.max_current_err_pct)
            min_peak_brite = int(s.min_peak_brightness_atwd)
            slope = 0.01 * int(s.min_slope_x_100)
            print(verbose)
            if verbose:
                print('Checking whether slope %i > 1.0 and peak brightness %i > 300 and error %i < 10' % (slope, min_peak_brite, err))
            return slope > 1.0 and min_peak_brite > 300 and err < 10
        
    elif s.test_name == 'flasher_width':
        if s.test_version == '1.3':
            if verbose:
                print('Checking whether missing width %i < 15' % s.missing_width)
                
            return int(s.missing_width) <= 15
        
    elif s.test_name == 'pmt_hv_ramp':
        if s.test_version == '1.1':
            set  = 0.001 * int(s.hv_worst_set_mvolt)
            read = 0.001 * int(s.hv_worst_read_mvolt)
            f = set / read
            if verbose:
                print('Checking whether ratio set/read %f > 0.985 and %f < 1.015' % (f, f))
                
            return f > 0.985 and f < 1.015
        
    elif s.test_name == 'atwd_pulser_spe':
        pos = int(s.atwd_waveform_position)
        wid = int(s.atwd_waveform_width)
        amp = int(s.atwd_waveform_amplitude)
        ampex = int(s.atwd_expected_amplitude)
        if verbose:
            print('Checking whether pos %i > 2 and %i < 10 and width %i < 6 and amp %i > %i and %i < %i' % (pos, wid, amp, 0.5*ampex, amp, 1.5*ampex))  
        return pos > 2 and pos < 10 and wid < 6 and \
            amp > 0.5*ampex and amp < 1.5 * ampex
    else:
        return s.passed
