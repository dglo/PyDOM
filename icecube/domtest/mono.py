"""
The Digikrom monochromator Python interface library.
This module encapsulates the RS-232 controlled monochromator
into a Python class with member functions that do the obvious
thing.  Usage typically proceeds as such:

        (1) Create an object and point to the terminal server:
        >>> from icecube.domtest.ibidaq import Digikrom
        >>> m = Digikrom('host', port-number)
        Note that the package uses socket I/O so you CANNOT
        connect directly to a serial device.

        (2) Operate on that object, e.g.:
        >>> m.goto(5320)
"""

import socket
import struct

# Monochromator units
MICRONS    = 0
NANOMETERS = 1
ANGSTROMS  = 2

class Digikrom:
    
    def __init__(self, host, port):
        """Open a connection to the monochromator over TCP sockets."""
        self.host = host
        self.port = port
        self.s    = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((host, port))
        self.setUnits(ANGSTROMS)
        
    def getSerial(self):
        """Return the 16-bit serial # of the monochromator unit."""
        self.s.send(struct.pack('BB', 56, 19))
        t = struct.unpack('>HBB', self.s.recv(4))
        self.status = t[1]
        return t[0]

    def setUnits(self, units):
        """Set the units for the goto command.  Possible units are
        mono.MICRONS
        mono.NANOMETERS 
        mono.ANGSTROM   (default)
        """
        self.s.send(struct.pack('BB', 50, units))
        t = struct.unpack('BB', self.s.recv(2))
        self.status = t[0]

    def goto(self, pos):
        """Set the monochromator to the wavelength specified.
        Note that the previous .setUnits() call dictates how
        the pos argument is interpreted.
        """
        self.s.send(struct.pack('>BH', 16, pos))
        t = struct.unpack('BB', self.s.recv(2))
        self.status = t[0]

    def getPosition(self):
        self.s.send(struct.pack('BB', 56, 0))
        t = struct.unpack('>HBB', self.s.recv(4))
        self.status = t[1]
        return t[0]

    def reset(self):
        self.s.send(struct.pack('BBB', 255, 255, 255))

