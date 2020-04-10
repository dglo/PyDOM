
This is the PyDOM project.  It is distributed by standard
distutils means.  To install from source type
    % python setup.py install

Required:
--------
numarray-0.9 or later
PyChart plotting package for some modules
MySQL-python for FAT database connectivity

Kael Hanson : 2005-05-27
	Code branched at pydom-3-16 to support old / new DB interfaces.
	PyDOM-3.x will continue to support old DB interface.  New DB
	code should go to PyDOM-4.x.


*** CHANGES ***

Changed in Version 4.3
----------------------
*) Added Python3 compatibility

Changed in Version 3.9
----------------------
*) Added the icecube.domtest.testdaq module

Changed in Version 3.8
----------------------
*) In 3.8-2 fix DB bug - too many connections open,
   added thread locking and only one connection.
*) Fix bug in multimon and lux - needed a scan prior to DOM discovery.
*) Added RAPCal decode / function support.

Changed in Version 3.7
----------------------
Release 3.7 is the frozen version used for UW-PSL FAT#2
*) Added multimon and lux monitoring
*) Added support to generate ATWD 0/1 steering files

New in Version 3.6
------------------
*) Connect to MySQL FAT database
*) DOR driver made remotable via XMLRPC
*) migrate important scripts from dom-testing module into bin

New in Version 3.5
------------------
*) added support in ibidaq.py to deal with configboot (R5 migration)
*) changed domcal.py to use ATWD-B for amp calibration
*) added features in dor.py to enable DOM autodiscovery dumps

New in Version 3.4
------------------
*) mono.py module to interface to the Digikrom monochromator

New in Version 3.3
------------------
*) util.py module added that contains many high-level utility
   functions, including:
   - gain calibration
   - time resolution
*) PyBook.py module - very minimal histogramming package

New in Version 3.2
------------------
*) Added the icecube.domtest.domcal module to support DOM
   calibration.
*) ibidaq.readPressure() now available - returns pressure in kPa

New in Version 3.1
------------------
*) icecube.domtest.pulser module to support communication with
   Chris Wendt's pulser.
*) ibidaq.setSPEDeadtime() on new FPGA images to support the
   programmable deadtime.

New in Version 3.0
------------------
*) ibidaq.acqX() method now supports (only) zdumps.  If you
   don't have an IceBoot /w/ zdump capability you *must*
   use PyDOM version 2.2!

New in Version 2.2
------------------
*) 'zdump' facility - allows fast, compressed dump of DOM memory. 
   This will be the last version that supports IceBoots that do
   not have zdump.  Unfortunately, the zdump is not integrated
   with acqX so if you want fast acqs then you should probably
   upgrade to the yet-to-be-released version 3.x of PyDOM.

New in Version 2
----------------
ibidaq now can connect directly to the driver file /wo/
having to go through a network server layer.  This option
is selected in the object creation by giving a filename
and *no* port or a 0 portnum - that is:

    >>> q = daq.ibx('/dev/dhc0w0dX')

instead of

    >>> q = daq.ibx('host', port)

    

