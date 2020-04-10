"""
Python module to parse DAQ MBean logfiles
"""

from builtins import object
from future.utils import raise_
import re
from datetime import datetime, timedelta

class BeanParserException(Exception):
    def __init__(self, txt):
        self.txt = txt
    def __str__(self):
        return self.txt

h1 = re.compile(
    "(\w+): (\d+)-(\d+)-(\d+)" +
    " (\d+):(\d+):(\d+)\.(\d+)")
h2 = re.compile("\s+(\w+):\s*(.+)")
# A simple scalar value
v0 = re.compile("[0-9]+$")
# An array value
v1 = re.compile("\[\s*(.+)\s*\]")
v2 = re.compile("\'(.+)\'")

class BeanInfo(object):
    def __init__(self, name, time):
        self.name = name
        self.time = time
        
class BeanParser(object):

    
    def __init__(self, f):
        self.f = f
        self.state = 0
        self.beanList = [ ]
        self.activeBean = None
        
    def parse(self):
        for line in self.f:
            self.s = line
            if len(self.s) != 0: self.lineCallback()
            
    def lineCallback(self):
        if self.state == 0:
            m = h1.match(self.s)
            if m is None: return
            beanName = m.group(1)
            year = int(m.group(2))
            month = int(m.group(3))
            day = int(m.group(4))
            hour = int(m.group(5))
            minute = int(m.group(6))
            second = int(m.group(7))
            micro = int(m.group(8))
            beanTime = datetime(year, month, day, hour, minute, second, micro)
            self.activeBean = BeanInfo(beanName, beanTime)
            self.state = 1
            
        elif self.state == 1:
            if self.s == '\n':
                self.state = 0
                if self.activeBean is not None:
                    self.beanList.append(self.activeBean)
                    self.activeBean = None
                return
            m = h2.match(self.s)
            if m is None:raise_(BeanParserException, self.s)
            attrName = m.group(1)
            valText  = m.group(2)
            if v0.match(valText): self.activeBean.__dict__[attrName] = int(valText)
	    lm = v1.match(valText)
	    if lm is not None:
		vlist = [ ]
		for x in lm.group(1).split(", "):
		    if v0.match(x): 
			vlist.append(int(x))
                    elif v2.match(x):
                        vlist.append(x[1:-1])
		    else:
			vlist.append(x)
	        self.activeBean.__dict__[attrName] = vlist

		
