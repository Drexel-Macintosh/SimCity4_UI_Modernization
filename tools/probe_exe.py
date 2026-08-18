import os, struct

path = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe"
print("exists:", os.path.exists(path))
print("size:", os.path.getsize(path))

data = open(path, "rb").read()
print("read:", len(data))

# Search for known class names
for name in [b"cSC4WinRCI", b"MiniMap", b"minimap", b"cSC4WinMiniMap"]:
    idx = data.find(name)
    if idx >= 0:
        va = idx + 0x400000
        print("%s found @ VA 0x%08X (off 0x%06X)" % (name.decode(), va, idx))
    else:
        print("%s NOT found" % name.decode())

# Search for clsid 0xCA318388 in little-endian
target = struct.pack("<I", 0xCA318388)
print("\nSearching for clsid bytes:", target.hex())
pos = 0
count = 0
while True:
    idx = data.find(target, pos)
    if idx < 0:
        break
    va = idx + 0x400000
    ctx = data[max(0, idx-8):idx+12]
    print("  clsid @ VA 0x%08X (off 0x%06X): %s" % (va, idx, ctx.hex()))
    count += 1
    pos = idx + 1
print("Total clsid hits:", count)

# Also check the class registry area from the docs (VA 0xB08F78)
print("\nClass registry area (VA 0xB08F78):")
reg_off = 0xB08F78 - 0x400000
for i in range(10):
    off = reg_off + i * 8
    if off + 8 <= len(data):
        clsid, name_ptr = struct.unpack_from("<II", data, off)
        print("  [%d] clsid=0x%08X name_ptr=0x%08X" % (i, clsid, name_ptr))
        # Try to read the name
        name_off = name_ptr - 0x400000
        if 0 <= name_off < len(data):
            end = data.find(b"\x00", name_off, name_off + 64)
            if end > name_off:
                print("       name: %s" % data[name_off:end].decode("ascii", errors="replace"))
