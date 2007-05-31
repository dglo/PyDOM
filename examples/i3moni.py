#!/usr/bin/env python

"""
Parse the i3-moni XMLs
"""

import sys
from xml.dom.minidom import parse

def jdtog(jd):
    """
    Converts a Julian Date in to a Gregorian date
    Returns (year, month, day) tuple
    """
    ij = jd + 32044
    g  = ij / 146097
    dg = ij % 146097
    c  = (dg / 36524 + 1) * 3 / 4
    dc = dg - c * 36524
    b  = dc / 1461
    db = dc % 1461
    a  = (db / 365 + 1) * 3 / 4
    da = db - a * 365
    y  = g * 400 + c * 100 + b * 4 + a
    m  = (da * 5 + 308) / 153 - 2
    d  = da - (m + 4) * 153 / 5 + 122
    return (y - 4800 + (m + 2) / 12, (m + 2) % 12 + 1, d + 1)

def mjdtodate(mjd):
    jd = int(mjd + 2400000.5)
    fd = mjd - int(mjd) + 0.5
    if fd > 1.0: fd -= 1.0
    s  = 86400.0 * fd
    h  = int(s) / 3600
    m  = int((s - 3600 * h) / 60)
    sk = int((s - 3600 * h - 60 * m))
    fs = s - 3600 * h - 60 * m - sk
    return jdtog(jd) + (h, m, sk, fs)
    
class UptimeStats:
    
    def __init__(self):
        self.stat = dict()
        
    def exposure(self, date, dt):
        if date not in self.stat: self.stat[date] = 0
        self.stat[date] += dt
        
    def printStats(self):
        epochs = self.stat.keys()
        epochs.sort()
        for x in epochs:
            print "%4.4d-%2.2d-%2.2d %4.2f" % (jdtog(x+2400001) + (self.stat[x],))

if __name__ == "__main__":
    
    doc = parse(sys.argv.pop(1))
    
    start_times = [ float(x.attributes['v'].value) for x in doc.getElementsByTagName('StartTime') ]
    end_times   = [ float(x.attributes['v'].value) for x in doc.getElementsByTagName('EndTime') ]
    events      = [ float(x.attributes['v'].value) for x in doc.getElementsByTagName('Events') ]
    runnumbers  = [ float(x.attributes['v'].value) for x in doc.getElementsByTagName('Run') ]
    run_info    = zip(runnumbers, start_times, end_times, events)
    
    up = UptimeStats()
    
    for run, start, end, event in run_info:
        fs = int(start)
        ex = min(fs + 1, end)
        up.exposure(fs, ex - start)
        if ex != end: up.exposure(fs+1, end - ex)
        
    up.printStats()

