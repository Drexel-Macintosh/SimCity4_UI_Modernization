import struct
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
d = open(EXE,'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
assert d[pe:pe+4] == b'PE\0\0'
mach, nsec = struct.unpack_from('<HH', d, pe+4)
optsz = struct.unpack_from('<H', d, pe+20)[0]
base = struct.unpack_from('<I', d, pe+24+28)[0]
print("machine %04x nsec %d optsz %d imagebase %08x" % (mach,nsec,optsz,base))
so = pe+24+optsz
for i in range(nsec):
    o = so+i*40
    name = d[o:o+8].rstrip(b'\0').decode()
    vsz, va, rsz, ro = struct.unpack_from('<IIII', d, o+8)
    ch = struct.unpack_from('<I', d, o+36)[0]
    print("%-8s VA %08X vsz %08X raw %08X rsz %08X chr %08X  (VA-file=%X)" % (
        name, base+va, vsz, ro, rsz, ch, base+va-ro))
