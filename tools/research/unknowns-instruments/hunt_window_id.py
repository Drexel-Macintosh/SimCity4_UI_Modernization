#!/usr/bin/env python3
"""Is a window id declared by any SHIPPED SCRIPT, or is it code-created?

Answers, for one or more window ids, across FOUR channels with stated controls:
  A. the CONTENTS of every type-0x00000000 .UI script (decompressed)
  B. every archive index, any type (game + BOTH Plugins trees, recursive)
  C. the exe .text/.rdata/.data as an imm32
  D. control ids that MUST be found, or the instrument is blind

Written 2026-08-24 closing register #27 (flyout 0x09DE8798 = a dead branch).
Reach: 279 archives / 1,303 scripts on this machine.

TWO TRAPS THIS FILE EXISTS TO DOCUMENT:

 1. A SCRIPT-CONTENT MISS IS NOT ABSENCE. A window id lives INSIDE a script's
    text, so it never appears as a TGI instance in an index. find_tgi.py's
    "not in the 9 archives" is therefore the WRONG instrument for a window id -
    it answers a different question. Channel A is the one that matters, and
    channel C decides "code-created" vs "missing data".

 2. ~/Documents IS NOT THE PLUGINS PARENT ON THIS MACHINE. Documents is
    OneDrive-redirected, so os.path.expanduser("~/Documents/SimCity 4/Plugins")
    returns a path that DOES NOT EXIST and the scan silently reports zero
    plugin archives - a structural null that looks exactly like "no plugin
    declares it". The first run of this script did precisely that.
    USE tools/sc4paths.py (it resolves OneDrive), or join OneDrive explicitly.
    Shipped tooling already does the right thing; this scratch script did not.

    python hunt_window_id.py            (edit TARGET/CONTROLS below)
Read-only. Never writes to the game directory or the Plugins tree.
"""

import glob, os, struct, sys, io, zlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:\dev\SC4UIScale\tools\dbpf")
from find_tgi import discover_archives, read_index   # reuse the discovery law

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
DOCS_PLUG = os.path.join(os.environ["USERPROFILE"], "OneDrive", "Documents", "SimCity 4", "Plugins")  # Documents is OneDrive-redirected on this machine; expanduser(~Documents) is WRONG and yields a nonexistent path
ROOT_PLUG = os.path.join(GAME, "Plugins")
EXE = os.path.join(GAME, "Apps", "SimCity 4.exe")

TARGET = 0x09DE8798
# D: controls. Known-present window ids that our corpus DOES declare.
CONTROLS = [0xAB954023,   # Signs & Labels flyout (hooked v2.39.6)
            0x8A6E61E0,   # sub-flyout container
            0x4A35B0F2]   # tutorial page root

def qfs_maybe(buf):
    """Decompress if QFS/RefPack: 4-byte LE size, then 0x10FB magic."""
    if len(buf) > 9 and buf[4] == 0x10 and buf[5] == 0xFB:
        try:
            out_len = (buf[6] << 16) | (buf[7] << 8) | buf[8]
            src, dst = 9, bytearray()
            while src < len(buf):
                c = buf[src]; src += 1
                if c < 0x80:
                    b = buf[src]; src += 1
                    n = c & 3
                    dst += buf[src:src+n]; src += n
                    off = ((c & 0x60) << 3) | b; cnt = ((c >> 2) & 7) + 3
                    p = len(dst) - off - 1
                    for _ in range(cnt): dst.append(dst[p]); p += 1
                elif c < 0xC0:
                    b0, b1 = buf[src], buf[src+1]; src += 2
                    n = (b0 >> 6) & 3
                    dst += buf[src:src+n]; src += n
                    off = ((b0 & 0x3F) << 8) | b1; cnt = (c & 0x3F) + 4
                    p = len(dst) - off - 1
                    for _ in range(cnt): dst.append(dst[p]); p += 1
                elif c < 0xE0:
                    b0, b1, b2 = buf[src], buf[src+1], buf[src+2]; src += 3
                    n = c & 3
                    dst += buf[src:src+n]; src += n
                    off = ((c & 0x10) << 12) | (b0 << 8) | b1
                    cnt = ((c & 0x0C) << 6) + b2 + 5
                    p = len(dst) - off - 1
                    for _ in range(cnt): dst.append(dst[p]); p += 1
                elif c < 0xFC:
                    n = ((c & 0x1F) << 2) + 4
                    dst += buf[src:src+n]; src += n
                else:
                    n = c & 3
                    dst += buf[src:src+n]; src += n
                    break
            return bytes(dst)
        except Exception:
            return buf
    return buf

def all_archives():
    out = []
    for n in discover_archives(GAME):
        out.append(os.path.join(GAME, n))
    for tree in (DOCS_PLUG, ROOT_PLUG):
        if os.path.isdir(tree):
            for pat in ("**/*.dat", "**/*.DAT", "**/*.sc4lot", "**/*.SC4Lot",
                        "**/*.sc4desc", "**/*.sc4model"):
                out += glob.glob(os.path.join(tree, pat), recursive=True)
    seen, uniq = set(), []
    for p in out:
        k = os.path.normcase(os.path.abspath(p))
        if k not in seen:
            seen.add(k); uniq.append(p)
    return uniq

def needles(v):
    """Every textual + binary form a window id can appear as."""
    h = f"{v:08x}"
    forms = {h, h.upper(), "0x"+h, "0x"+h.upper(), f"{v:X}", f"{v:x}"}
    return [f.encode('latin1') for f in forms] + [struct.pack('<I', v), struct.pack('>I', v)]

def main():
    archives = all_archives()
    print(f"ARCHIVES DISCOVERED: {len(archives)}")
    print(f"  game root : {sum(1 for p in archives if os.path.dirname(p)==GAME)}")
    print(f"  docs plug : {sum(1 for p in archives if DOCS_PLUG.lower() in p.lower())}")
    print(f"  root plug : {sum(1 for p in archives if ROOT_PLUG.lower() in p.lower())}")

    want = {TARGET: 'TARGET'}
    for c in CONTROLS: want[c] = 'control'
    pats = {v: needles(v) for v in want}

    idx_hits = {v: [] for v in want}
    script_hits = {v: [] for v in want}
    scripts_scanned = 0
    bad = 0

    for p in archives:
        try:
            entries = list(read_index(p))
        except Exception:
            bad += 1
            continue
        for (t, g, i, off, size) in entries:
            for v in want:
                if i == v:
                    idx_hits[v].append((os.path.basename(p), t, g))
            if t != 0x00000000:      # .UI scripts only
                continue
            try:
                with open(p, 'rb') as f:
                    f.seek(off); raw = f.read(size)
                data = qfs_maybe(raw)
            except Exception:
                continue
            scripts_scanned += 1
            for v, ns in pats.items():
                if any(n in data for n in ns):
                    script_hits[v].append((os.path.basename(p), f"{g:08X}", f"{i:08X}"))

    print(f"\nUI SCRIPTS SCANNED (type 0x00000000, decompressed): {scripts_scanned}")
    if bad: print(f"  (skipped {bad} non-DBPF / unreadable files)")

    print("\n--- D. POSITIVE CONTROLS (must be non-empty or the scan is blind) ---")
    for c in CONTROLS:
        print(f"  0x{c:08X}: script-content hits={len(script_hits[c])}  index hits={len(idx_hits[c])}"
              + (f"  e.g. {script_hits[c][0]}" if script_hits[c] else ""))

    print("\n--- A/B. THE TARGET ---")
    print(f"  0x{TARGET:08X}: script-content hits={len(script_hits[TARGET])}  index hits={len(idx_hits[TARGET])}")
    for h in script_hits[TARGET][:12]: print("     script:", h)
    for h in idx_hits[TARGET][:12]:    print("     index :", h)

    print("\n--- C. EXE imm32 SWEEP ---")
    d = open(EXE,'rb').read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe+6)[0]
    optsz = struct.unpack_from("<H", d, pe+20)[0]
    base = struct.unpack_from("<I", d, pe+24+28)[0]
    secs=[]
    for k in range(nsec):
        o = pe+24+optsz+k*40
        name = d[o:o+8].rstrip(b"\0").decode('latin1')
        vs,va,rs,ra = struct.unpack_from("<IIII", d, o+8)
        secs.append((name,va,vs,ra,rs))
    for v in want:
        needle = struct.pack('<I', v); found=[]
        for name,va,vs,ra,rs in secs:
            seg = d[ra:ra+max(vs,rs)]; st=0
            while True:
                kk = seg.find(needle, st)
                if kk < 0: break
                found.append((name, base+va+kk)); st=kk+1
        lbl = 'TARGET ' if v==TARGET else 'control'
        print(f"  {lbl} 0x{v:08X}: {len(found)} hit(s)" +
              (f"  {[(n,hex(a)) for n,a in found[:6]]}" if found else ""))

main()
