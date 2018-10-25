
import rapcal
import struct

f = file('../../data/rapcal.dat', 'rb')
cals = [ ]
while True:
    buf = f.read(300)
    if len(buf) != 300: break
    domid, = struct.unpack("q", buf[0:8])
    print "Read DOM ID %12.12x" % (domid)
    if domid == 0xA5B57A6DFA0D:
        cals.append(rapcal.RAPCal(buf[12:]))
        if len(cals) == 2:
            print 50e-09*(cals[1].dorTx - cals[0].dorTx)
            print 25e-09*(cals[1].domTx - cals[0].domTx)
            cals[1].doRAPCal(cals[0])
            print cals[1].getDorRxC() - cals[1].getDorTx(), \
                  cals[1].getDomTx() - cals[1].getDomRxC()
            print cals[1].clkratio, cals[1].cablelen
            cals.pop(0)

