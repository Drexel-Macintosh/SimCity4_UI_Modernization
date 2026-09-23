# Build an index of every 4-byte window in .text whose value falls in .rdata
# (candidate references to vtables), plus a classifier for the instruction
# that holds it. Independent of the finder's sweep.
import numpy as np, pickle, os, sys
from v_pe import PE

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'v_refs.pkl')

def build(p):
    text = [s for s in p.secs if s[0] == '.text'][0]
    rdata = [s for s in p.secs if s[0] == '.rdata'][0]
    base = text[1]; raw = p.data[text[3]:text[3]+text[4]]
    lo, hi = rdata[1], rdata[1] + rdata[2]
    refs = {}
    arr = np.frombuffer(raw, dtype=np.uint8)
    n = len(arr) - 3
    vals = (arr[0:n].astype(np.uint32) | (arr[1:n+1].astype(np.uint32) << 8) |
            (arr[2:n+2].astype(np.uint32) << 16) | (arr[3:n+3].astype(np.uint32) << 24))
    idx = np.nonzero((vals >= lo) & (vals < hi))[0]
    for i in idx:
        v = int(vals[i]); refs.setdefault(v, []).append(base + int(i))
    return refs

def load():
    p = PE()
    if os.path.exists(CACHE):
        return p, pickle.load(open(CACHE, 'rb'))
    r = build(p)
    pickle.dump(r, open(CACHE, 'wb'))
    return p, r

if __name__ == '__main__':
    p, r = load()
    print('distinct rdata values referenced from .text:', len(r))
    for v in (0xAB5B48, 0xADC8D8, 0xADFEB8, 0xADF6A0, 0xADDAF0, 0xADDD50, 0xAB8628, 0xAB889C, 0xAB8884,
              0xADD7B0, 0xADD348, 0xADFBD0, 0xAE0FB0, 0xAE20A0, 0xAB83B8, 0xAD6AA0, 0xAE04D8, 0xAE0810, 0xAE1780, 0xADC678, 0xAE46E8, 0xAE4910):
        print('%08X' % v, ['%08X' % a for a in r.get(v, [])])
