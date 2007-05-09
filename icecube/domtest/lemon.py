
from numarray import *

def linearregression(x, y):
    xm = sum(x)/len(x)
    ym = sum(y)/len(y)
    x0 = x - xm
    y0 = y - ym
    xx = sum(x0*x0)
    yy = sum(y0*y0)
    xy = sum(x0*y0)
    slope = xy / xx
    yint  = ym - slope * xm
    r     = xy / sqrt(xx*yy)
    return slope, yint, r
