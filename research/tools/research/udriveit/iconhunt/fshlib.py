#!/usr/bin/env python3
r"""fshlib.py - reusable FSH -> PIL decode, lifted from extract_fsh.py's proven
codec table and generalised: works on a payload buffer, returns EVERY entry as
an RGBA image plus its tag, and resolves 8-bit indexed entries against the
palette entry that follows them (SC4 packs pal-after-pixels).
Read-only helpers; no game writes.
"""
import struct
from PIL import Image

FSH_TYPE = 0x7AB50E44
PNG_TYPE = 0x856DDBAC


def _pal_from(data, off, code, n):
    p = off + 16
    cols = []
    if code == 0x22:      # 24-bit DOS
        for k in range(n):
            b, g, r = data[p+k*3:p+k*3+3]
            cols.append((r*4, g*4, b*4, 255))
    elif code == 0x24:    # 24-bit
        for k in range(n):
            b, g, r = data[p+k*3:p+k*3+3]
            cols.append((r, g, b, 255))
    elif code == 0x2D:    # 16-bit A1R5G5B5
        for k in range(n):
            v = struct.unpack_from("<H", data, p+k*2)[0]
            r = (v >> 10) & 31; g = (v >> 5) & 31; b = v & 31
            cols.append((r*8, g*8, b*8, 255 if (v & 0x8000) else 0))
    elif code == 0x2A:    # 32-bit
        for k in range(n):
            b, g, r, a = data[p+k*4:p+k*4+4]
            cols.append((r, g, b, a))
    return cols


def decode_fsh(data, max_px=4096*4096):
    """-> list of (tag, PIL RGBA image). Raises on non-SHPI."""
    if data[:4] != b"SHPI":
        raise ValueError("not SHPI: %r" % data[:4])
    nent = struct.unpack_from("<I", data, 8)[0]
    if nent > 4096:
        raise ValueError("absurd entry count %d" % nent)
    ents = []
    for e in range(nent):
        tag = data[16 + 8*e:20 + 8*e]
        off = struct.unpack_from("<I", data, 20 + 8*e)[0]
        ents.append((tag, off))
    out = []
    pending = None   # (tag, idx_image, w, h)
    for k, (tag, off) in enumerate(ents):
        if off + 16 > len(data):
            continue
        code = data[off] & 0x7F
        w, h = struct.unpack_from("<2H", data, off + 4)
        if w == 0 or h == 0 or w*h > max_px:
            if code in (0x22, 0x24, 0x2A, 0x2D) and pending:
                pass
            else:
                continue
        p = off + 16
        img = None
        try:
            if code == 0x7D:
                need = w*h*4
                if p+need > len(data): continue
                img = Image.frombytes("RGBA", (w, h), data[p:p+need], "raw", "BGRA")
            elif code == 0x7F:
                need = w*h*3
                if p+need > len(data): continue
                img = Image.frombytes("RGB", (w, h), data[p:p+need], "raw", "BGR").convert("RGBA")
            elif code == 0x7E:   # A1R5G5B5
                need = w*h*2
                if p+need > len(data): continue
                img = Image.frombytes("RGBA", (w, h), data[p:p+need], "raw", "BGR;15")
            elif code == 0x78:   # R5G6B5
                need = w*h*2
                if p+need > len(data): continue
                img = Image.frombytes("RGB", (w, h), data[p:p+need], "raw", "BGR;16").convert("RGBA")
            elif code == 0x6D:   # A4R4G4B4
                need = w*h*2
                if p+need > len(data): continue
                raw = data[p:p+need]
                px = bytearray(w*h*4)
                for i in range(w*h):
                    v = raw[i*2] | (raw[i*2+1] << 8)
                    px[i*4+0] = ((v >> 8) & 15) * 17
                    px[i*4+1] = ((v >> 4) & 15) * 17
                    px[i*4+2] = (v & 15) * 17
                    px[i*4+3] = ((v >> 12) & 15) * 17
                img = Image.frombytes("RGBA", (w, h), bytes(px))
            elif code == 0x60:   # DXT1
                need = max(1, w//4)*max(1, h//4)*8
                if p+need > len(data): continue
                img = Image.frombytes("RGBA", (w, h), data[p:p+need], "bcn", 1)
            elif code == 0x61:   # DXT3
                need = max(1, w//4)*max(1, h//4)*16
                if p+need > len(data): continue
                img = Image.frombytes("RGBA", (w, h), data[p:p+need], "bcn", 2)
            elif code == 0x62:   # DXT5 (rare)
                need = max(1, w//4)*max(1, h//4)*16
                if p+need > len(data): continue
                img = Image.frombytes("RGBA", (w, h), data[p:p+need], "bcn", 3)
            elif code == 0x7B:   # 8-bit indexed, palette follows
                need = w*h
                if p+need > len(data): continue
                pal = None
                for (t2, o2) in ents[k+1:k+3]:
                    if o2 + 16 <= len(data):
                        c2 = data[o2] & 0x7F
                        if c2 in (0x22, 0x24, 0x2A, 0x2D):
                            n2 = struct.unpack_from("<H", data, o2+4)[0]
                            pal = _pal_from(data, o2, c2, min(n2, 256))
                            break
                idx = data[p:p+need]
                if pal:
                    lut = pal + [(0, 0, 0, 0)]*(256-len(pal))
                    px = bytearray(w*h*4)
                    for i, v in enumerate(idx):
                        r, g, b, a = lut[v]
                        px[i*4:i*4+4] = bytes((r, g, b, a))
                    img = Image.frombytes("RGBA", (w, h), bytes(px))
                else:
                    img = Image.frombytes("L", (w, h), idx).convert("RGBA")
            elif code in (0x22, 0x24, 0x2A, 0x2D):
                continue   # palette
            else:
                continue
        except Exception:
            continue
        if img is not None:
            out.append((tag.decode("ascii", "replace"), img))
    return out
