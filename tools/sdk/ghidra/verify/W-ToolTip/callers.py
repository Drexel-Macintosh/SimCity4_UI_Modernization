import struct, sys
from pe import *
n,v,vs,ro,rs=[s for s in SECS if s[0]=='.text'][0]
DATA=IMG[ro:ro+rs]
def callers(t):
    res=[]
    i=DATA.find(b'\xe8')
    while i>=0 and i < len(DATA)-5:
        d=struct.unpack_from('<i',DATA,i+1)[0]
        if v+i+5+d==t: res.append(v+i)
        i=DATA.find(b'\xe8',i+1)
    return res
if __name__=='__main__':
    for a in sys.argv[1:]:
        t=int(a,16); print(hex(t),[hex(x) for x in callers(t)])
