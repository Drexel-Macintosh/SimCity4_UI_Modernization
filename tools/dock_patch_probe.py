#!/usr/bin/env python3
r"""dock_patch_probe.py - THROWAWAY. Applies the proposed build_selective_safe.py
patch to a SCRATCHPAD COPY of the builder, byte-verifies each oldText anchor,
compiles the result, and exercises neutralize_dock_recess() at f=1.5 / 2.0 / 3.0
against real staged sheets copied into a scratch STAGE.

Touches nothing under src/, _tests/, or the real selective-safe/stage* dirs.
"""
import os
import py_compile
import shutil
import subprocess
import sys

TOOLS = r"<HOME>\OneDrive\Projects\Surface 1 Project\1 Completed Projects\SC4TouchControls\tools"
BUILDER = os.path.join(TOOLS, "selective-safe", "build_selective_safe.py")
SCRATCH = (r"<HOME>\AppData\Local\Temp\claude"
           r"\<SESSION-DIR>"
           r"\f1160943-a698-434b-a6bf-d3c3e2971cea\scratchpad")
WORK = os.path.join(SCRATCH, "dockpatch")

# ---------------------------------------------------------------------------
# THE PATCH. Each entry is (label, oldText, newText) - oldText must appear
# EXACTLY ONCE in the shipped builder.
# ---------------------------------------------------------------------------
OLD_IMPORTS = """import shutil
import subprocess
import sys
from collections import defaultdict
"""

NEW_IMPORTS = """import shutil
import struct
import subprocess
import sys
import zlib
from collections import defaultdict
"""

OLD_HELPERS = """FONT_GUIDS = load_font_guids()


def main():
"""

NEW_HELPERS = '''FONT_GUIDS = load_font_guids()


# ---------------------------------------------------------------------------
# DOCK MINIMAP RECESS - neutralize the baked FAKE MAP (3x tier and up).
#
# The dock artwork sheet {46a006b0,13d14ca0} (1x = 235x222) carries a
# DECORATIVE terrain thumbnail baked into the minimap recess. MEASURED on the
# shipped 1x extract
#     tools\\dbpf\\extracted\\SimCity_1\\T-856ddbac_G-46a006b0_I-13d14ca0.png
# by saturation bbox (max(r,g,b)-min(r,g,b) > 60, magenta colour-key excluded):
# it occupies EXACTLY x[18,81] y[71,134] = 64x64, contiguous in both axes, and
# it is the ONLY saturated block on the entire sheet (0 saturated pixels
# anywhere else).
#
# The real minimap the game blits into that recess can only ever be a
# power-of-two multiple of the city tile:
#     f=2.00 -> recess 128x128, real map 128 -> EXACT fit, fake map invisible
#     f=3.00 -> recess 192x192, real map 128 -> a 32px ring of fake terrain
# That ring is the artefact the user has reported four times.
#
# FIX: repaint the block with the recess plate that surrounds it. MEASURED:
# the plate is a PURE VERTICAL GRADIENT - the pixels immediately LEFT of the
# block and immediately RIGHT of it agree to within 1-2/255 on every one of
# the 64 rows, so there is no horizontal component to reproduce. A per-row
# median of the flanking pixels therefore reconstructs the plate exactly;
# worst measured seam delta against the immediate neighbour pixel is 2/255.
# (A flat single-colour fill would be WRONG here - the recess is a gradient
# running #a2b5bc at the top to #c7d4d8 at the bottom.)
#
# The rect is DERIVED, not baked: scale_len() over the measured 1x rect
# reproduces the independently-measured block at ALL THREE shipped tiers -
#     1.5x  measured (27,107) 96x96    scale_len -> (27,107) 96x96
#     2.0x  measured (36,142) 128x128  scale_len -> (36,142) 128x128
#     3.0x  measured (54,213) 192x192  scale_len -> (54,213) 192x192
# so the derivation is confirmed at a THIRD tier, not only at the 2x blind
# spot where competing laws agree (scaling law 53).
#
# GATE: FACTOR >= 2.5. That gate is the ONLY thing keeping this code out of
# the 2x and 1.5x packages, and it is a BYTE-level guarantee, not a visual
# one: at f=2 the fill would still rewrite 128x128 pixels (invisibly, since
# the real 128 map covers them exactly), so 2x parity rests entirely on
# returning before a single byte is read. 2.00 and 1.50 both fail the gate.
#
# Idempotency: the staging step re-copies the pristine upscaled sheet from
# UPSCALE_DIR before this runs, so a repeat build always starts from unfixed
# art. Running this twice WITHOUT that re-copy trips the pre-fill assertion
# and aborts - loudly, which is the intended failure mode.
# ---------------------------------------------------------------------------
DOCK_SHEET = (0x46A006B0, 0x13D14CA0)
DOCK_FAKEMAP_1X = (18, 71, 64, 64)   # left, top, w, h - MEASURED, see above
DOCK_NEUTRALIZE_MIN_FACTOR = 2.5     # f=2.00 and f=1.50 must stay byte-identical
_PNG_SIG = bytes([137, 80, 78, 71, 13, 10, 26, 10])


def _png_chunks(blob):
    """[(type, data)] in file order. Stdlib only - same no-PIL contract as png_wh."""
    if blob[:8] != _PNG_SIG:
        raise ValueError("not a PNG")
    out, off = [], 8
    while off < len(blob):
        (ln,) = struct.unpack(">I", blob[off:off + 4])
        out.append((blob[off + 4:off + 8], blob[off + 8:off + 8 + ln]))
        off += 12 + ln
    return out


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _png_read_rgba(path):
    """(w, h, bytearray of RGBA rows, chunks). 8-bit RGBA, non-interlaced only."""
    with open(path, "rb") as f:
        blob = f.read()
    chunks = _png_chunks(blob)
    ihdr = next(d for (t, d) in chunks if t == b"IHDR")
    w, h, depth, ctype, comp, filt, ilace = struct.unpack(">IIBBBBB", ihdr)
    if (depth, ctype, comp, filt, ilace) != (8, 6, 0, 0, 0):
        raise ValueError("%s: need 8-bit RGBA non-interlaced, got %r"
                         % (os.path.basename(path),
                            (depth, ctype, comp, filt, ilace)))
    raw = zlib.decompress(b"".join(d for (t, d) in chunks if t == b"IDAT"))
    stride, bpp = w * 4, 4
    px, pos = bytearray(stride * h), 0
    for y in range(h):
        ft = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        ro, po = y * stride, y * stride - stride
        if ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + px[po + i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + px[po + i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                c = px[po + i - bpp] if i >= bpp else 0
                line[i] = (line[i] + _paeth(a, px[po + i], c)) & 0xFF
        elif ft != 0:
            raise ValueError("%s: bad PNG filter %d on row %d"
                             % (os.path.basename(path), ft, y))
        px[ro:ro + stride] = line
    return w, h, px, chunks


def _png_write_rgba(path, w, h, px, chunks):
    """Rewrite with filter 0 rows, PRESERVING every ancillary chunk. Dropping
    gAMA/sRGB would change how the game renders the colours (see
    tools/dbpf/optimize_png.py), so they are copied through untouched."""
    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]
    new_idat, wrote = zlib.compress(bytes(raw), 9), False
    out = bytearray(_PNG_SIG)
    for (typ, data) in chunks:
        if typ == b"IDAT":
            if wrote:
                continue
            data, wrote = new_idat, True
        out += struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(bytes(out))


def _dock_sat(px, stride, x, y):
    """Saturation of one pixel; 0 for the magenta colour key. Terrain is
    saturated, the grey recess plate is not."""
    o = y * stride + x * 4
    r, g, b = px[o], px[o + 1], px[o + 2]
    if (r, g, b) == (255, 0, 255):
        return 0
    return max(r, g, b) - min(r, g, b)


def neutralize_dock_recess():
    """Repaint the baked fake map in the STAGED dock sheet with the recess
    plate. Hard no-op (nothing read, nothing written) below 2.5x."""
    if FACTOR < DOCK_NEUTRALIZE_MIN_FACTOR:
        print("Dock recess: SKIPPED at factor %g (< %g) - 2x/1.5x sheet bytes "
              "untouched" % (FACTOR, DOCK_NEUTRALIZE_MIN_FACTOR))
        return
    gid, iid = DOCK_SHEET
    names = [tgi_png_name(gid, iid), tgi_png_name(gid, iid ^ CLONE_XOR)]
    hits = [n for n in names if os.path.isfile(os.path.join(STAGE, n))]
    if not hits:
        sys.exit("FATAL: dock sheet %08x/%08x is not staged, so the recess fix "
                 "would ship silently unapplied. Looked for %s in %s"
                 % (gid, iid, " / ".join(names), STAGE))
    l0, t0, w0, h0 = DOCK_FAKEMAP_1X
    left, top = scale_len(l0), scale_len(t0)
    bw, bh = scale_len(w0), scale_len(h0)
    flank = max(1, scale_len(3))          # 3 source px each side, in output px
    for name in hits:
        path = os.path.join(STAGE, name)
        w, h, px, chunks = _png_read_rgba(path)
        stride = w * 4
        if left - flank < 0 or left + bw + flank > w or top < 0 or top + bh > h:
            sys.exit("FATAL: dock recess rect (%d,%d) %dx%d +/-%d flank does "
                     "not fit the staged sheet %dx%d (%s)"
                     % (left, top, bw, bh, flank, w, h, name))
        # VERIFY BEFORE WRITE: the rect must actually BE the fake map. If the
        # art is ever re-extracted and the block moves, abort rather than paint
        # grey over the wrong pixels.
        probe = [(x, y) for y in range(top, top + bh, 4)
                 for x in range(left, left + bw, 4)]
        n_sat = sum(1 for (x, y) in probe if _dock_sat(px, stride, x, y) > 60)
        if n_sat < len(probe) * 0.6:
            sys.exit("FATAL: dock recess rect (%d,%d) %dx%d holds only %d/%d "
                     "saturated probe px - that is not the baked fake map. "
                     "Re-measure DOCK_FAKEMAP_1X against the 1x extract."
                     % (left, top, bw, bh, n_sat, len(probe)))
        fills = []
        for y in range(top, top + bh):
            s = []
            for dx in range(1, flank + 1):
                for x in (left - dx, left + bw - 1 + dx):
                    o = y * stride + x * 4
                    s.append((px[o], px[o + 1], px[o + 2], px[o + 3]))
            med = bytes(sorted(v[c] for v in s)[len(s) // 2] for c in range(4))
            fills.append(med)
            o = y * stride + left * 4
            px[o:o + bw * 4] = med * bw
        _png_write_rgba(path, w, h, px, chunks)
        # POSITIVE CONTROL: the same detector that just found a full block of
        # saturated pixels must now find none inside the rect.
        w2, h2, px2, _ = _png_read_rgba(path)
        s2 = w2 * 4
        rem = sum(1 for y in range(top, top + bh) for x in range(left, left + bw)
                  if _dock_sat(px2, s2, x, y) > 60)
        if rem:
            sys.exit("FATAL: dock recess still holds %d saturated px after the "
                     "fill (%s)" % (rem, name))
        print("Dock recess NEUTRALIZED in %s: rect (%d,%d) %dx%d, %d rows "
              "filled from the plate gradient #%02x%02x%02x (top) .. "
              "#%02x%02x%02x (bottom); %d saturated px found before, 0 after"
              % (name, left, top, bw, bh, bh,
                 fills[0][0], fills[0][1], fills[0][2],
                 fills[-1][0], fills[-1][1], fills[-1][2], n_sat))


def main():
'''

OLD_CALL = """    print("Staged: %d exclusive in-place PNGs (%d no-2x skipped), %d shared clones (%d no-2x skipped)"
          % (n_excl_staged, n_excl_missing, n_shared_staged, n_shared_missing))
"""

NEW_CALL = """    print("Staged: %d exclusive in-place PNGs (%d no-2x skipped), %d shared clones (%d no-2x skipped)"
          % (n_excl_staged, n_excl_missing, n_shared_staged, n_shared_missing))

    # Post-upscale art repair: erase the decorative fake map baked into the
    # dock's minimap recess. 3x tier and up only - see the block comment above.
    neutralize_dock_recess()
"""

PATCH = [("imports", OLD_IMPORTS, NEW_IMPORTS),
         ("helpers", OLD_HELPERS, NEW_HELPERS),
         ("call site", OLD_CALL, NEW_CALL)]


def main():
    src = open(BUILDER, "r", encoding="utf-8", newline="").read()
    print("Builder: %s (%d bytes, %d LF, %d CR)"
          % (BUILDER, len(src), src.count("\n"), src.count("\r")))

    out = src
    for label, old, new in PATCH:
        n = out.count(old)
        print("  anchor %-10s occurrences=%d  (must be 1)  old=%dch new=%dch"
              % (label, n, len(old), len(new)))
        if n != 1:
            sys.exit("ANCHOR NOT UNIQUE: %s" % label)
        out = out.replace(old, new)
    if "\r" in out:
        sys.exit("patched text gained a CR - builder is LF-only")

    os.makedirs(WORK, exist_ok=True)
    # The builder reads sibling data files relative to __file__, so the patched
    # copy has to live in selective-safe/ to import at all. Named *_probe.py per
    # the task rules; deleted by exact name at the end of this run.
    patched = os.path.join(TOOLS, "selective-safe", "_dockpatched_probe.py")
    with open(patched, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print("  wrote %s (%d bytes)" % (patched, len(out)))
    py_compile.compile(patched, doraise=True)
    print("  py_compile: OK")

    # ---- exercise the function at each tier against a scratch STAGE -------
    up = {1.5: os.path.join(TOOLS, "upscale", "preview-15x", "SimCity_1"),
          2.0: os.path.join(TOOLS, "upscale", "preview", "SimCity_1"),
          3.0: os.path.join(TOOLS, "upscale", "preview-3x", "SimCity_1")}
    name = "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png"
    driver = os.path.join(WORK, "driver.py")
    with open(driver, "w", encoding="utf-8", newline="") as f:
        f.write(
            "import importlib.util, os, sys, hashlib\n"
            "fac = float(sys.argv[1]); stage = sys.argv[2]\n"
            "sys.argv = [sys.argv[0], '--factor', repr(fac)]\n"
            "spec = importlib.util.spec_from_file_location('b', %r)\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(m)\n"
            "m.STAGE = stage\n"
            "print('   FACTOR seen by module: %%g' %% m.FACTOR)\n"
            "p = os.path.join(stage, %r)\n"
            "before = hashlib.sha256(open(p,'rb').read()).hexdigest()\n"
            "m.neutralize_dock_recess()\n"
            "after = hashlib.sha256(open(p,'rb').read()).hexdigest()\n"
            "print('   sha256 before == after: %%s' %% (before == after))\n"
            % (patched, name))

    for fac in (1.5, 2.0, 3.0):
        stage = os.path.join(WORK, "stage-%g" % fac)
        os.makedirs(stage, exist_ok=True)
        shutil.copy2(os.path.join(up[fac], name), os.path.join(stage, name))
        print("\n--- FACTOR %g ---" % fac)
        r = subprocess.run([sys.executable, driver, str(fac), stage],
                           capture_output=True, text=True)
        print(r.stdout.rstrip() or "(no stdout)")
        if r.stderr.strip():
            print("   STDERR:", r.stderr.strip()[:400])
        print("   exit=%d" % r.returncode)

    # ---- FATAL-path control: does the pre-fill assertion actually fire? ----
    print("\n--- NEGATIVE CONTROL: rerun 3x on the ALREADY-FIXED file ---")
    stage3 = os.path.join(WORK, "stage-3")
    r = subprocess.run([sys.executable, driver, "3.0", stage3],
                       capture_output=True, text=True)
    print((r.stdout + r.stderr).strip()[:400])
    print("   exit=%d (nonzero = the guard fires, as designed)" % r.returncode)

    # ---- MISSING-SHEET control: does the silent-skip guard fire? ----
    print("\n--- NEGATIVE CONTROL: 3x with the sheet absent from STAGE ---")
    empty = os.path.join(WORK, "stage-empty")
    os.makedirs(empty, exist_ok=True)
    with open(driver, "a", encoding="utf-8", newline="") as f:
        pass
    r = subprocess.run(
        [sys.executable, "-c",
         "import importlib.util,sys\n"
         "sys.argv=['x','--factor','3.0']\n"
         "spec=importlib.util.spec_from_file_location('b',%r)\n"
         "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
         "m.STAGE=%r\n"
         "m.neutralize_dock_recess()\n" % (patched, empty)],
        capture_output=True, text=True)
    print((r.stdout + r.stderr).strip()[:300])
    print("   exit=%d (nonzero = silent-skip guard fires)" % r.returncode)

    os.remove(patched)
    print("\ncleaned up %s" % patched)


if __name__ == "__main__":
    sys.exit(main())
