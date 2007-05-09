import math
from numpy import array, zeros, arange
#from pychart  import area, bar_plot

class Histogram:
    def __init__(self, title, bins, x0, x1):
        self.title = title
        self.h     = zeros(bins, 'd')
        self.x0    = x0
        self.x1    = x1
        self.overflow  = 0
        self.underflow = 0
        self.sum       = 0
        self.var       = 0
        self.entries   = 0

    def fill(self, x, w=1.0):
        b = int((x - self.x0) / (self.x1 - self.x0) * len(self.h))
        if b < 0:
            self.underflow += 1
        elif b >= len(self.h):
            self.overflow  += 1
        else:
            self.h[b] += w
            self.entries += 1
            self.sum  += x*w
            self.var  += (x*w)**2

    def x(self):
        """Returns the vector of x bins"""
        return self.x0 + arange(len(self.h), type='d') / len(self.h) * (self.x1-self.x0)

    def binWidth(self):
        return float((self.x1-self.x0)) / float(len(self.h))

    def getMaximum(self):
        imax = 0
        hmax = self.h[0]
        for i in xrange(1, len(self.h)):
            if hmax < self.h[i]:
                imax = i
                hmax = self.h[i]
        return hmax, self.x0 + self.binWidth()*imax
            
    def mean(self):
        return self.sum / self.entries

    def std(self):
        return math.sqrt(self.var / self.entries - self.mean()**2)
    
    def toXML(self, f):
        print >>f, "<histogram>"
        print >>f, "<title>%s</title>" % (self.title)
        print >>f, "<stat>"
        print >>f, "<entries>%d</entries>" % (self.entries)
        print >>f, "<sum>%d</sum>" % (self.sum)
        print >>f, "<var>%d</var>" % (self.var)
        print >>f, "</stat>"
        print >>f, "<axis bins='%d' x0='%f' x1='%f'>" % (len(self.h), self.x0, self.x1)
        for ch in range(len(self.h)):
            print >>f, "<bin ch='%d'>%f</bin>" % (ch, self.h[ch])
        print >>f, "<underflow>%f</underflow>" % (self.underflow)
        print >>f, "<overflow>%f</overflow>" % (self.overflow)
        print >>f, "</histogram>"

    
        
        
        
