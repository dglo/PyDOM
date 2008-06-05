from icecube.daq.payload import HitDataPayload, TriggerRequestPayload

def getTrigHits(tr):
    hits = []
    for hit in tr.hits:
        if isinstance(hit, HitDataPayload): 
            hits.append(hit)
        elif isinstance(hit, TriggerRequestPayload):
            hits += getTrigHits(hit)
    return hits

def checkMissingReadouts(evt):
    hits = [ x.mbid for x in evt.getHits() ]
    trig_hits = [ "%12.12x" % x.mbid for x in getTrigHits(evt.trigger_request) ]
    for mbid in trig_hits:
        if mbid not in hits: return True
    return False


        
