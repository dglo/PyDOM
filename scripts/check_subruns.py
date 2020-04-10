#!/usr/bin/env python

from __future__ import print_function
from sys import argv, exit
from icecube.daq.payload import read_payloads

data_filename = ''

try:
    data_filename = argv[1]
except IndexError:
    print("Usage %s data" % argv[0])
    exit(-1)

data_file = open(data_filename)
payloads = read_payloads(data_file)
run = payloads[0].run_number
subrun = payloads[0].subrun_number
print("file: %-45s run: %-10d  subrun: %3d  events: %10d" % (data_filename, run, subrun, len(payloads)))
for p in payloads:
    if p.subrun_number != subrun:
        print("  outlying subrun number %5d %5d @ %5d" % (p.run_number, p.subrun_number, p.utime))

