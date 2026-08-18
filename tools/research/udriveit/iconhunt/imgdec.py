#!/usr/bin/env python3
r"""iconhunt shared decoder: DBPF entry -> RGBA numpy array.

FSH decode follows tools/research/udriveit/extract_fsh.py (the working decoder)
and extends it: palette entries are now PAIRED with their indexed bitmap
instead of being dropped, and every SC4 FSH pixel code is handled or COUNTED as
a named failure.  A silent skip would turn "we decoded everything" into a lie.
"""
import io
import struct

import numpy as np
from PIL import Image

T_FSH = 0x7AB50E44
T_PNG = 0x856DDBAC

# ---- QFS / RefPack -------------------------------------------------------


def qfs(data):
    p = 0
    if len(data) > 9 and data[4] == 0x10 and data[5] == 0xFB:
        p = 4
    if not (len(data) > 5 and data[p] == 0x10 and data[p + 1] == 0xFB):
        return None
    usize = (data[p + 2] << 16) | (data[p + 3] << 8) | data[p + 4]
    i = p + 5
    out = bytearray(usize)
    o = 0
    n = len(data)
    while i < n:
        b0 = data[i]
        if b0 < 0x80:
            b1 = data[i + 1]
            i += 2
            npl = b0 & 3
            off = ((b0 & 0x60) << 3) + b1 + 1
            cnt = ((b0 >> 2) & 7) + 3
        elif b0 < 0xC0:
            b1 = data[i + 1]
            b2 = data[i + 2]
            i += 3
            npl = (b1 >> 6) & 3
            off = ((b1 & 0x3F) << 8) + b2 + 1
            cnt = (b0 & 0x3F) + 4
        elif b0 < 0xE0:
            b1 = data[i + 1]
            b2 = data[i + 2]
            b3 = data[i + 3]
            i += 4
            npl = b0 & 3
            off = ((b0 & 0x10) << 12) + (b1 << 8) + b2 + 1
            cnt = ((b0 & 0x0C) << 6) + b3 + 5
        elif b0 < 0xFC:
            npl = ((b0 & 0x1F) + 1) * 4
            off = cnt = 0
            i += 1
        else:
            npl = b0 & 3
            off = cnt = 0
            i += 1
        if npl:
            out[o:o + npl] = data[i:i + npl]
            i += npl
            o += npl
        if cnt:
            s = o - off
            if s < 0:
                break
            if off >= cnt:                       # non-overlapping: block copy
                out[o:o + cnt] = out[s:s + cnt]
                o += cnt
            else:
                for k in range(cnt):
                    out[o] = out[s + k]
                    o += 1
        if b0 >= 0xFC:
            break
    return bytes(out[:o])


def payload(raw):
    if len(raw) > 9 and raw[4] == 0x10 and raw[5] == 0xFB:
        d = qfs(raw)
        if d:
            return d
    if len(raw) > 5 and raw[0] == 0x10 and raw[1] == 0xFB:
        d = qfs(raw)
        if d:
            return d
    return raw


# ---- FSH ------------------------------------------------------------------
PALCODES = (0x22, 0x24, 0x29, 0x2A, 0x2D)


def _pal_rgba(code, w, data, p):
    n = w
    out = np.zeros((max(n, 256), 4), np.uint8)
    out[:, 3] = 255
    if code == 0x2A:                              # 32-bit BGRA
        a = np.frombuffer(data[p:p + n * 4], np.uint8)
        if a.size < n * 4:
            return None
        a = a.reshape(n, 4)
        out[:n, 0] = a[:, 2]
        out[:n, 1] = a[:, 1]
        out[:n, 2] = a[:, 0]
        out[:n, 3] = 255
    elif code in (0x22, 0x24):                    # 24-bit BGR (0x22 is 6-bit)
        a = np.frombuffer(data[p:p + n * 3], np.uint8)
        if a.size < n * 3:
            return None
        a = a.reshape(n, 3)
        sc = 4 if code == 0x22 else 1
        out[:n, 0] = np.clip(a[:, 2].astype(np.int32) * sc, 0, 255)
        out[:n, 1] = np.clip(a[:, 1].astype(np.int32) * sc, 0, 255)
        out[:n, 2] = np.clip(a[:, 0].astype(np.int32) * sc, 0, 255)
    elif code in (0x29, 0x2D):                    # 16-bit 1555 / 565
        a = np.frombuffer(data[p:p + n * 2], "<u2")
        if a.size < n:
            return None
        out[:n, 0] = ((a >> 11) & 31) * 255 // 31
        out[:n, 1] = ((a >> 5) & 63) * 255 // 63
        out[:n, 2] = (a & 31) * 255 // 31
    else:
        return None
    return out


def decode_fsh(data):
    """-> (list of RGBA HxWx4 uint8 arrays, list of failure reasons)"""
    if data[:4] != b"SHPI":
        return [], ["not-SHPI:%s" % data[:4].hex()]
    nent = struct.unpack_from("<I", data, 8)[0]
    if nent > 4096:
        return [], ["absurd-entry-count-%d" % nent]
    offs = []
    for e in range(nent):
        try:
            offs.append(struct.unpack_from("<I", data, 20 + 8 * e)[0])
        except Exception:
            return [], ["truncated-directory"]
    imgs = []
    fails = []
    pal = None
    pending = []
    for off in offs:
        if off + 16 > len(data):
            fails.append("entry-offset-past-eof")
            continue
        code = data[off] & 0x7F
        w, h = struct.unpack_from("<2H", data, off + 4)
        p = off + 16
        if code in PALCODES:
            got = _pal_rgba(code, w, data, p)
            if got is not None:
                pal = got
            continue
        if w == 0 or h == 0 or w > 4096 or h > 4096:
            fails.append("bad-dims-%dx%d-code%02x" % (w, h, code))
            continue
        need = {0x7D: w * h * 4, 0x7F: w * h * 3, 0x7E: w * h * 2,
                0x78: w * h * 2, 0x6D: w * h * 2, 0x7B: w * h,
                0x60: max(w // 4, 1) * max(h // 4, 1) * 8,
                0x61: max(w // 4, 1) * max(h // 4, 1) * 16,
                0x62: max(w // 4, 1) * max(h // 4, 1) * 16}.get(code)
        if need is None:
            fails.append("unhandled-code-%02x" % code)
            continue
        blob = data[p:p + need]
        if len(blob) < need:
            fails.append("truncated-pixels-code%02x" % code)
            continue
        try:
            if code == 0x7D:
                a = np.frombuffer(blob, np.uint8).reshape(h, w, 4)
                img = a[:, :, [2, 1, 0, 3]].copy()
            elif code == 0x7F:
                a = np.frombuffer(blob, np.uint8).reshape(h, w, 3)
                img = np.dstack([a[:, :, [2, 1, 0]],
                                 np.full((h, w, 1), 255, np.uint8)])
            elif code == 0x7E:                    # A1R5G5B5
                a = np.frombuffer(blob, "<u2").reshape(h, w).astype(np.uint32)
                img = np.dstack([
                    (((a >> 10) & 31) * 255 // 31).astype(np.uint8),
                    (((a >> 5) & 31) * 255 // 31).astype(np.uint8),
                    ((a & 31) * 255 // 31).astype(np.uint8),
                    np.where(a & 0x8000, 255, 0).astype(np.uint8)])
            elif code == 0x78:                    # R5G6B5
                a = np.frombuffer(blob, "<u2").reshape(h, w).astype(np.uint32)
                img = np.dstack([
                    (((a >> 11) & 31) * 255 // 31).astype(np.uint8),
                    (((a >> 5) & 63) * 255 // 63).astype(np.uint8),
                    ((a & 31) * 255 // 31).astype(np.uint8),
                    np.full((h, w), 255, np.uint8)])
            elif code == 0x6D:                    # A4R4G4B4
                a = np.frombuffer(blob, "<u2").reshape(h, w).astype(np.uint32)
                img = np.dstack([
                    (((a >> 8) & 15) * 17).astype(np.uint8),
                    (((a >> 4) & 15) * 17).astype(np.uint8),
                    ((a & 15) * 17).astype(np.uint8),
                    (((a >> 12) & 15) * 17).astype(np.uint8)])
            elif code == 0x7B:
                idx = np.frombuffer(blob, np.uint8).reshape(h, w)
                if pal is None:
                    pending.append((idx,))
                    continue
                img = pal[idx]
            else:                                 # DXT
                n = {0x60: 1, 0x61: 2, 0x62: 3}[code]
                img = np.asarray(Image.frombytes(
                    "RGBA", (w, h), blob, "bcn", n))
            imgs.append(np.ascontiguousarray(img))
        except Exception as ex:
            fails.append("code%02x-%s" % (code, type(ex).__name__))
    for (idx,) in pending:
        if pal is None:
            # No palette in this container. Render the INDEX as luminance so the
            # shape is still scoreable - dropping it would be a silent null.
            fails.append("indexed-without-palette(rendered-as-grey)")
            h2, w2 = idx.shape
            g = np.dstack([idx, idx, idx, np.full((h2, w2), 255, np.uint8)])
            imgs.append(np.ascontiguousarray(g))
        else:
            imgs.append(np.ascontiguousarray(pal[idx]))
    if not imgs and not fails:
        fails.append("no-bitmap-entries")
    return imgs, fails


def decode_entry(t, raw):
    """-> (list of RGBA arrays, list of failure strings)"""
    try:
        data = payload(raw)
    except Exception as ex:
        return [], ["qfs-%s" % type(ex).__name__]
    # MAGIC FIRST, type second: SimCity_1.dat stores 26 SHPI/FSH payloads under
    # T=0x856DDBAC (the "PNG" type), including four mission-marker balloons.
    # Trusting the type id here produced 26 silent "decode failures".
    if data[:4] == b"SHPI":
        return decode_fsh(data)
    if t == T_PNG or data[:8] == b"\x89PNG\r\n\x1a\n":
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
            return [np.asarray(im.convert("RGBA"))], []
        except Exception as ex:
            return [], ["png-%s" % type(ex).__name__]
    if data[:4] == b"SHPI":
        return decode_fsh(data)
    return [], ["unknown-magic-%s" % data[:4].hex()]
