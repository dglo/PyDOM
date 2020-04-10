from __future__ import print_function
from distutils.core import setup
import sys, string, os

print("*****", os.getcwd(), "*****")
scfiles=[ 'scripts/HubDaemon.py',
          'scripts/add-fat.py',
          'scripts/autogen-steering',
          'scripts/domhub-services',
          'scripts/fatstat2db.py',
          'scripts/genSteering.py',
          'scripts/startRun.py',
          'scripts/stopDomProcs.py',
          'scripts/tdaq-efmt',
          'scripts/tune-optics',
          'scripts/multimon.py',
          'scripts/lux.py',
          'scripts/testLC.py',
          'scripts/testLC2.py',
          'scripts/testLC3.py'
          ]
setup(
    name='PyDOM',
    version='4.3.0',
    description='Python classes to interact with IceCube DOMs',
    long_description="""
        IceCube Project Python interface to DOMs and DOMHubs.
        Includes the libraries icecube.domtest.* and associated
        useful scripts.
    """,
    author='Kael Hanson',
    author_email='kael.hanson@icecube.wisc.edu',
    url='http://icecube.wisc.edu/~kaeld/domtest/python',
    scripts=scfiles,
    packages=['icecube', 'icecube.daq', 'icecube.domtest']
    )
