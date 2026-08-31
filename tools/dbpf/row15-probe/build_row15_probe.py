#!/usr/bin/env python3
r"""BUILD the overlay-census row-15 probe DAT  (v2 -- rebuilt after v1 was refused).

Row 15 of the overlay census is the neighbour-connection arrow that stands at a
city's edge where a road / rail / highway / avenue crosses into the next tile.
The row's channel claim -- "a prop occupant drawn from an S3D model" -- is graded
STRONG_INFERENCE, not proven: every byte behind it is CREATION-side (exemplar
fetch, position, orient, attribute stamp, grid insert) and not one is DRAW-side.
This DAT is the instrument that turns that inference into a measurement.

Data only.  One file into a Plugins subfolder; reverted by deleting it.  The
game install and the live Plugins tree are opened READ-ONLY and every byte we
ship is derived from them.

===========================================================================
WHY v2 EXISTS -- the three defects that got v1 refused
===========================================================================

  1. v1's geometry override covered ONE model.  The arrow is a FAMILY OF TWENTY
     (0x29F10000..0x29F10430, five zooms x four rotations, each self-naming
     "..._Z1S".."..._Z5E").  Nineteen camera positions out of twenty would have
     shown nothing and the run would have produced a confident fake null.
     => v2 covers all twenty, each decoded and rewritten on its own terms
        (vertex counts differ: 4 / 4 / 7 / 7 / 14-15).

  2. v1's identity override (role A, the LTEXT "Neighbor Connection") had no
     positive control and is probably never rendered: zero .UI captionres refs
     across all 271 UI records, zero dword hits in the exe, reachable only via
     the exemplar's generic 0x8A416A99 UserVisibleNameKey.
     => DROPPED.  Its job -- "did the load reach row 15's OWN TGIs?" -- is now
        done at BUILD time by the load-order pre-flight (check L), which is a
        measurement instead of an unreadable in-game observation.

  3. v1's load-order canary targeted a control carrying BOTH an inline caption
     and a captionres, so it silently depended on captionres beating the inline
     caption -- unproven.
     => Replaced by two IMAGE canaries.  An `image={g,i}` has no inline
        alternative (a .UI script cannot embed a bitmap), so the resource is the
        only possible source and there is no precedence rule to beat.

  AND a fourth defect this file found on its own, which is the reason the
  OccupantSize override is NOT the {24,9,3} the rebuild brief asked for:

  4. B (model vertices x3) and C (OccupantSize x3) BOTH produce the single
     observation "the arrow is three times bigger".  Shipped in one DAT they
     cannot be told apart -- the exact disease the rebuild was called to cure.
     => C is now ANISOTROPIC: {8,3,1} -> {8,24,1}, height only.  B changes SIZE,
        C changes SHAPE.  Four distinct observations instead of two colliding
        ones.  Check X0 REFUSES to build any uniformly-scaled OccupantSize.

===========================================================================
THE FIVE OVERRIDES
===========================================================================

  (B) GEOMETRY -- S3D  T=0x5AD0E817 G=0xBADB57F1 I=0x29F10000..0x29F10430
      All TWENTY ConnectArrow models.  Every position float32 (the first three
      of each vertex's five; the last two are UVs, measured 0.0..0.995) times
      SCALE, default 3.0.  438 float writes across the family.  No chunk
      length, no vertex count, no record length changes anywhere.
      ASKS: is the plate sized by its own model vertices?
      A UNIFORM scale, deliberately: the Z1/Z2 members are camera-tilted plates
      whose coordinates do not mean the same thing as the Z3-Z5 boxes' do, so an
      axis-selective edit would mean something different at different zooms and
      re-introduce the camera dependence blocker 1 is about.

  (C) CREATION-SIDE -- EXEMPLAR  T=0x6534284A G=0xC977C536 I=0x29F10000
      Property 0x27812810 OccupantSize {8.0, 3.0, 1.0} -> {8.0, 24.0, 1.0}.
      A 4-byte in-place splice at record offset [92:96]; the record stays 180
      bytes and every length field is untouched.
      ASKS: is the plate sized creation-side from its occupant footprint?
      Prior expectation is NO -- tools/research/overlays/row-23-zots.md §3 shows
      OccupantSize is simulator-footprint metadata, not render geometry, for the
      zot prop class.  C is cheap and fails differently from B, so it is worth
      carrying; its null is expected and therefore weakly informative.  Said
      here so nobody reads a predicted null as a discovery.

  (E) ART-CHANNEL POSITIVE CONTROL -- S3D  G=0xBADB57F1 I=0x0FD10000..0x0FD10430
      The twenty NoPower zot models, scaled by the IDENTICAL recipe as (B) --
      same type, same group, same uncompressed shipping, same transform.  Not a
      similar test: the same test on a different object.
      ASKS: does an S3D override authored by us, from Plugins, reach the model
      renderer on this machine?
      THIS IS THE ONE POSITIVE CONTROL IN THE PROBE THAT IS ALREADY PROVEN ON
      SCREEN.  row-23-zots.md §3 establishes that zot on-screen size comes
      "entirely from the S3D vertex coordinates, in world metres", and §5
      confirmed it live with its own negative control in the same two frames
      (zots grew with zoom; pixel-fixed dispatch balloons did not).  So an E
      null is not an ambiguous shrug -- it is positive evidence that our S3D
      records are not being accepted or not being used.

  (K1) LOAD CANARY, ZERO PRECEDENCE DEPENDENCE -- PNG  G=0x46A006B0 I=0xE2B66DB8
      The generic 120x30 RGBA button face -> SOLID GREEN.
      Defined EXACTLY ONCE in the nine shipped archives and by ZERO of the
      archives in the live Plugins tree (check L measures this every build, and
      REFUSES if it ever stops being true).  So K1 rests on one law only --
      a Plugins record beats a game-archive record -- which is the law this
      whole product already ships on.  No subfolder-order rule, no captionres
      precedence, no inline alternative.
      Read it on the "Establish City" dialog (enter any unestablished region
      tile) -- both of that dialog's buttons draw this sheet with
      winflag_visible=yes.  27 other scripts also draw it; the README lists them.

  (K2) LOAD CANARY, ZERO CLICKS -- PNG  G=0x46A006B0 I=0x144161F0
      The news-ticker strip across the bottom of the city HUD -> SOLID ORANGE.
      Always on screen, no navigation.  BUT this TGI is also defined by our own
      010-SC4UIScale\z_SC4UIScale_SelectiveArt.dat, so K2 additionally depends on
      the Plugins-subfolder-alphabetical-last-wins rule.
      That dependence is turned into an asset rather than hidden: K1 and K2
      fail differently, so the PAIR measures the precedence rule instead of
      assuming it.  K1 green + K2 stock is not a broken probe -- it is the
      finding "we load, but we lose to 010-SC4UIScale", and it voids nothing,
      because no plugin contests any B/C/E record.
      SHIPPED AT THE LIVE WINNER'S DIMENSIONS, not at stock's.  The winner is
      read out of the Plugins tree at build time (currently 1514x86, the 2x
      tier; stock is 757x43).  Shipping a 757x43 sheet where a 1514x86 one is
      live would change the strip's GEOMETRY as well as its colour and conflate
      "the DAT loaded" with "the HUD broke".

  COLOURS ARE CHOSEN AGAINST A KNOWN COLLISION.  Neither canary is magenta.
  Magenta/black is this engine's own missing-texture and wrong-quadrant
  signature (a 1x imagerect on a 2x sheet reads the wrong quadrant), so a
  magenta canary would be indistinguishable from an art-pack failure.

===========================================================================
SELF-VERIFICATION -- this script refuses rather than emit a bad DAT
===========================================================================
On any failed check the output file is deleted and the exit status is non-zero.

  X0  design gate       the OccupantSize edit must be ANISOTROPIC.  If it is a
                        uniform scale of the stock triple, B and C produce the
                        same observation and the probe cannot distinguish its
                        own outcomes -> refuse.  Also refuses SCALE == 1.0 and
                        a no-op OccupantSize.
  L   load-order        every probe TGI resolved across the nine shipped
      pre-flight        archives AND every DBPF file in the live Plugins tree
                        (discovered by magic bytes, not by extension).  B/C/E
                        must be uncontested by any plugin; K1 must be
                        uncontested by any plugin AND defined exactly once in
                        the archives; K2's live winner is identified by path and
                        sha256 and pinned into the manifest.
  S0  source pins       every source TGI found at the pinned offset/size with
                        the pinned stock CONTENT.  A patched or modded install
                        fails here rather than shipping a probe built from
                        different bytes.
  S1  stock re-decode   every source record decodes cleanly BEFORE it is
                        touched (S3D chunk chain walks exactly to ANIM and the
                        vertex stride divides the VERT payload to its last byte;
                        the exemplar walk lands exactly on the record end; the
                        PNG's IHDR/IDAT/IEND chain walks exactly to the file
                        end).
  S2  edit invariance   the override differs from stock ONLY inside the intended
                        value span; identical length; every chunk tag and
                        declared length, every vertex count, every UV, every
                        other exemplar property byte-identical.
  S3  archive structure header field-for-field against DbpfPack.cs; index offset
                        + size == file size; payloads tile [96, index) with no
                        gap and no overlap; no duplicate TGI; NO compression
                        directory under EITHER spelling of the DIR TGI
                        (0xE86B1EEE and the real 0xE86B1EEF -- see the note
                        below).
  S4  read-back bytes   every record pulled back OUT of the finished DAT and
                        byte-compared with what we meant to write.
  S5  read-back meaning the records pulled out of the DAT are re-decoded FROM
                        SCRATCH and compared against the intended VALUES, not
                        the intended bytes -- every scaled float read back at
                        exactly stock*SCALE, the OccupantSize triple, and every
                        canary pixel via an INDEPENDENT decoder (Pillow).
                        S4 fails by a diff, S5 by a wrong number; a packer that
                        wrote the right bytes to the wrong entry is caught by
                        the two together and by neither alone.
  S6  second reader     DbpfPack.exe (independent C# implementation, older than
                        this file) parses the archive and re-extracts every
                        payload; its index and payload bytes must agree.
  S7  second writer     DbpfPack.exe packs the SAME staging directory; its index
                        rows and payloads must match ours byte-for-byte.
  N1  absent TGI        a TGI we did NOT ship must be absent from the finished
                        index -- proving the read-back can come back empty.
  N2  mutation          a deliberately corrupted copy of every override must
                        FAIL its own S2 check.  Proves S2 can fail, not merely
                        that it passed.  Five mutations, every one must be
                        caught by the named control.

DIR NOTE.  tools/dbpf/NOTES-PACK.md used to claim SimCity_1.dat "contains no DIR
entry".  That is FALSE and the note now carries the correction: the archive does
carry one, at TGI {0xE86B1EEF, 0xE86B1EEF, 0x286B1F03}, 782,080 bytes, stride 16,
48,880 of its 60,440 records QFS-compressed.  What survives is only the packer's
BEHAVIOUR: an archive with no compressed payloads legitimately needs no DIR, and
we write none.  It must not be justified by saying SC4 does the same, because it
does not.  DbpfPack.cs line 44 still guards on 0xE86B1EEE (...EE, not ...EF), so
its DIR refusal would not catch a real DIR record; check S3 therefore tests for
BOTH spellings itself rather than trusting that guard.

Usage:
    python build_row15_probe.py
    python build_row15_probe.py --scale 3.0
    python build_row15_probe.py --check-only      # run every check, emit nothing
    SC4_GAME_DIR=... SC4_PLUGINS=... python build_row15_probe.py
"""

import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS_DBPF = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import dbpfcore as D                                              # noqa: E402
import s3d_family as S                                            # noqa: E402

OUT_NAME = "zzzz_SC4UIScale_ROW15_PROBE.dat"
OUT_PATH = os.path.join(HERE, OUT_NAME)
STAGE_DIR = os.path.join(HERE, "staging")
DBPF_PACK_EXE = os.path.join(TOOLS_DBPF, "DbpfPack.exe")

T_S3D = 0x5AD0E817
T_EXEMPLAR = 0x6534284A
T_PNG = 0x856DDBAC
G_MODELS = 0xBADB57F1
G_UIART = 0x46A006B0

ARROW_BASE = 0x29F10000
ZOT_BASE = 0x0FD10000
EXEMPLAR_TGI = (T_EXEMPLAR, 0xC977C536, 0x29F10000)
PROP_OCCUPANT_SIZE = 0x27812810

# Both spellings of the compression-directory TGI.  We must be absent under
# each; the repo carries two and only one of them is real.
DIR_TGIS = {(0xE86B1EEE, 0xE86B1EEE, 0x286B1F03),
            (0xE86B1EEF, 0xE86B1EEF, 0x286B1F03)}

# ---- pins.  Asserted against the install, never assumed. -------------------
PIN_EXEMPLAR = dict(arc="SimCity_1.dat", off=111117434, size=180,
                    occ=(8.0, 3.0, 1.0), occ_span=(88, 100),
                    name="UI8x1x3_ConnectArrow_29F1")
PIN_K1 = dict(tgi=(T_PNG, G_UIART, 0xE2B66DB8), arc="SimCity_1.dat",
              off=44195428, size=1586, w=120, h=30,
              what="generic 120x30 button face")
PIN_K2 = dict(tgi=(T_PNG, G_UIART, 0x144161F0), arc="SimCity_1.dat",
              off=47083902, size=10967, w=757, h=43,
              what="news-ticker strip, city HUD")

NEW_OCCUPANT_SIZE = (8.0, 24.0, 1.0)          # height x8 -- ANISOTROPIC
K1_RGBA = (0x00, 0xFF, 0x00, 0xFF)            # green
K2_RGBA = (0xFF, 0x80, 0x00, 0xFF)            # orange

# Negative control for the finished index: a TGI we deliberately do not ship.
N1_ABSENT_TGI = (T_S3D, G_MODELS, 0x29F1DEAD)


class Refuse(Exception):
    """Any failed check.  Output deleted, exit non-zero."""


_checks = [0]


def check(label, ok, detail=""):
    _checks[0] += 1
    if not ok:
        raise Refuse("%s FAILED  %s" % (label, detail))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def tgis(t):
    return "%08X/%08X/%08X" % t


# ==========================================================================
# minimal PNG -- our own encoder and our own decoder.  Pillow is used only as
# an INDEPENDENT second decoder in S5, never as the authority.
# ==========================================================================

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def png_chunks(buf):
    """[(tag, length, start_of_data)] walking to the exact end of the buffer."""
    if buf[:8] != PNG_MAGIC:
        raise ValueError("not a PNG: %r" % buf[:8])
    out, p = [], 8
    while p < len(buf):
        if p + 8 > len(buf):
            raise ValueError("truncated chunk header at %d" % p)
        ln = struct.unpack_from(">I", buf, p)[0]
        tag = buf[p + 4:p + 8]
        if p + 12 + ln > len(buf):
            raise ValueError("chunk %r at %d overruns the buffer" % (tag, p))
        want = zlib.crc32(buf[p + 4:p + 8 + ln]) & 0xFFFFFFFF
        got = struct.unpack_from(">I", buf, p + 8 + ln)[0]
        if want != got:
            raise ValueError("chunk %r at %d has a bad CRC" % (tag, p))
        out.append((tag.decode("ascii"), ln, p + 8))
        p += 12 + ln
        if tag == b"IEND":
            break
    if p != len(buf):
        raise ValueError("chunk walk ended at %d, buffer is %d bytes"
                         % (p, len(buf)))
    return out


def png_ihdr(buf):
    ch = png_chunks(buf)
    if not ch or ch[0][0] != "IHDR":
        raise ValueError("first chunk is %r, not IHDR" % (ch[0][0] if ch else None))
    w, h, depth, ctype, comp, filt, inter = struct.unpack_from(
        ">IIBBBBB", buf, ch[0][2])
    return dict(w=w, h=h, depth=depth, ctype=ctype, comp=comp, filt=filt,
                inter=inter, chunks=[c[0] for c in ch])


def png_solid(w, h, rgba):
    """A minimal IHDR/IDAT/IEND 8-bit RGBA PNG of one flat colour."""
    px = bytes(rgba)
    row = b"\x00" + px * w                     # filter 0 (None) per scanline
    raw = row * h
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    return (PNG_MAGIC
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def png_decode_solid(buf):
    """Decode an 8-bit RGBA non-interlaced PNG; return (w, h, set_of_pixels).

    Our own decoder, so S5's pixel check does not depend on Pillow alone.
    Supports every PNG filter type, because we must be able to decode STOCK art
    too (the S0 pins re-read the source images through this same code).
    """
    ih = png_ihdr(buf)
    if ih["depth"] != 8 or ih["ctype"] != 6 or ih["inter"] != 0:
        raise ValueError("decoder handles 8-bit RGBA non-interlaced only, got "
                         "depth=%d ctype=%d interlace=%d"
                         % (ih["depth"], ih["ctype"], ih["inter"]))
    idat = b"".join(buf[o:o + n] for (t, n, o) in png_chunks(buf) if t == "IDAT")
    raw = zlib.decompress(idat)
    w, h, bpp = ih["w"], ih["h"], 4
    stride = w * bpp
    if len(raw) != (stride + 1) * h:
        raise ValueError("inflated %d bytes, expected %d"
                         % (len(raw), (stride + 1) * h))
    prev = bytearray(stride)
    seen = set()
    p = 0
    for _y in range(h):
        ft = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if ft == 0:
                v = line[x]
            elif ft == 1:
                v = line[x] + a
            elif ft == 2:
                v = line[x] + b
            elif ft == 3:
                v = line[x] + ((a + b) >> 1)
            elif ft == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                v = line[x] + pr
            else:
                raise ValueError("unknown PNG filter %d" % ft)
            line[x] = v & 0xFF
        for x in range(0, stride, bpp):
            seen.add(bytes(line[x:x + bpp]))
        prev = line
    return w, h, seen


# ==========================================================================
# archive access
# ==========================================================================

# Extensions SC4 actually loads out of Plugins.  The tree also contains DBPF
# files the game never opens -- this mod stages its tier payloads as `.uipay`
# and swaps the chosen one into the matching `.dat`.  Those payloads DO carry
# real records, so a scan that treats every DBPF on disk as live reports
# contests that cannot happen (measured: 6 holders of the K2 TGI on disk, of
# which 1 is loaded).  The scan therefore stays WIDE -- every file is opened and
# magic-checked -- and the extension only decides which bucket a holder lands
# in, so an unexpected holder is still visible instead of filtered away.
LOADED_EXT = (".dat", ".sc4lot", ".sc4desc", ".sc4model", ".sc4")


class Install(object):
    """The nine shipped archives plus every DBPF in the live Plugins tree."""

    def __init__(self, game=None, plugins=None):
        self.game_dir = game or D.GAME
        self.archives = [D.Archive(p) for p in D.discover_archives(self.game_dir)]
        check("L0 nine archives discovered", len(self.archives) >= 7,
              "found %d in %s" % (len(self.archives), self.game_dir))
        self.plugins_dir = plugins or self._find_plugins()
        self.plugin_archives = []
        self.plugin_skipped = 0
        self.plugin_staging = 0
        if self.plugins_dir:
            for root, _dirs, files in os.walk(self.plugins_dir):
                for fn in files:
                    fp = os.path.join(root, fn)
                    if os.path.abspath(fp) == os.path.abspath(OUT_PATH):
                        continue
                    try:
                        with open(fp, "rb") as f:
                            if f.read(4) != b"DBPF":
                                continue
                    except OSError:
                        self.plugin_skipped += 1
                        continue
                    try:
                        arc = D.Archive(fp)
                    except Exception:
                        self.plugin_skipped += 1
                        continue
                    arc.loaded = fn.lower().endswith(LOADED_EXT)
                    self.plugin_archives.append(arc)
                    if not arc.loaded:
                        self.plugin_staging += 1

    @staticmethod
    def _find_plugins():
        if os.environ.get("SC4_PLUGINS"):
            return os.environ["SC4_PLUGINS"]
        for base in (os.path.expanduser(r"~\OneDrive\Documents\SimCity 4\Plugins"),
                     os.path.expanduser(r"~\Documents\SimCity 4\Plugins")):
            if os.path.isdir(base):
                return base
        return None

    def owners(self, tgi, where="game"):
        """where: 'game' | 'plug' (only what SC4 loads) | 'plug_all' (on disk)."""
        if where == "game":
            pool = self.archives
        elif where == "plug":
            pool = [a for a in self.plugin_archives if a.loaded]
        else:
            pool = self.plugin_archives
        out = []
        for a in pool:
            for e in a.index:
                if (e[0], e[1], e[2]) == tgi:
                    out.append((a, e))
        return out

    def rel(self, arc):
        try:
            return os.path.relpath(arc.path, self.plugins_dir)
        except ValueError:
            return arc.path

    def fetch(self, tgi):
        """(archive, entry, decompressed_bytes, was_qfs, dir_listed) -- exactly
        one shipped definition required."""
        hits = self.owners(tgi, "game")
        check("L1 exactly one shipped definition of %s" % tgis(tgi),
              len(hits) == 1, "found %d" % len(hits))
        a, e = hits[0]
        raw, qfs, listed = a.payload(e)
        return a, e, raw, qfs, listed

    def close(self):
        for a in self.archives + self.plugin_archives:
            a.close()


# ==========================================================================
# roles
# ==========================================================================

def family_ids(base):
    return [base | (z << 8) | (r << 4) for z in range(5) for r in range(4)]


def build_s3d_family(inst, base, label, scale, records, notes):
    """Scale every position float of all twenty members of one S3D family."""
    ids = family_ids(base)
    # The family is ENUMERATED out of the archives, then cross-checked against
    # the computed stride -- a computed id list once produced 14 phantom TGIs.
    found = {}
    for a in inst.archives:
        for e in a.index:
            if e[0] == T_S3D and e[1] == G_MODELS and (e[2] & 0xFFFFF000) == base:
                found.setdefault(e[2], []).append((a, e))
    check("%s.F1 family enumerates to exactly 20" % label, len(found) == 20,
          "enumerated %d ids in [%08X, %08X]" % (len(found), base, base | 0xFFF))
    check("%s.F2 enumeration equals the computed id set" % label,
          sorted(found) == ids,
          "enumerated %s" % ["%08X" % i for i in sorted(found)])

    total_floats = 0
    stock_max = 0.0
    for iid in ids:
        tgi = (T_S3D, G_MODELS, iid)
        check("%s.F3 %08X has one shipped definition" % (label, iid),
              len(found[iid]) == 1, "%d holders" % len(found[iid]))
        check("%s.F4 %08X uncontested by any plugin" % (label, iid),
              not inst.owners(tgi, "plug"),
              "held by %s" % [inst.rel(a) for a, _ in inst.owners(tgi, "plug")])
        a, e = found[iid][0]
        stock, qfs, listed = a.payload(e)

        # ---- S1: decode the STOCK record before touching it -----------------
        v = S.decode(stock)
        check("%s.S1a %08X stride divides the VERT payload" % (label, iid),
              v.stride == 20 and v.floats_per_vertex == 5,
              "stride=%d fpv=%d" % (v.stride, v.floats_per_vertex))
        check("%s.S1b %08X has 3*nverts position floats" % (label, iid),
              len(v.position_offsets) == 3 * v.vertex_count,
              "%d offsets for %d verts" % (len(v.position_offsets),
                                           v.vertex_count))
        uvs = [struct.unpack_from("<f", stock, o)[0] for o in v.uv_offsets]
        check("%s.S1c %08X excluded floats are UVs" % (label, iid),
              all(S.UV_MIN <= u <= S.UV_MAX for u in uvs),
              "range %.5f..%.5f" % (min(uvs), max(uvs)))
        pos = [struct.unpack_from("<f", stock, o)[0] for o in v.position_offsets]
        stock_max = max(stock_max, max(abs(p) for p in pos))

        # ---- the edit -------------------------------------------------------
        new = S.scale_positions(stock, v.position_offsets, scale)

        # ---- S2: invariance -------------------------------------------------
        s2_s3d(label, iid, stock, new, v, scale)
        total_floats += len(v.position_offsets)
        records.append(dict(tgi=tgi, role=label, data=new, stock=stock,
                            kind="s3d", meta=v, scale=scale,
                            desc="%s %s  %d verts  x%.3g"
                                 % (label, S.variant_tag(iid) if base == ARROW_BASE
                                    else "%08X" % iid, v.vertex_count, scale)))
    # The plausibility bound is derived from the family being read, not carried
    # over from a sibling.  s3d_family.POS_ABS_MAX (64.0) was measured off the
    # ARROW family; the zot Z1/Z2 plates are 15.6 x 24.0 m and legitimately
    # exceed it, so applying the arrow's constant here would have refused a
    # correct build.  What the check must actually discriminate is "are these
    # really world-metre positions" (they are: 1 m .. 1 km) versus "did we read
    # UVs or garbage" -- and the UV half of that discrimination is S1c, above.
    check("%s.F5a stock positions are world-metre scale" % label,
          1.0 <= stock_max <= 1000.0,
          "stock max |p| = %.4f, which is not a plausible world coordinate"
          % stock_max)
    scaled_max = struct.unpack("<f", struct.pack("<f", stock_max * scale))[0]
    check("%s.F5b every scaled coordinate is finite in float32" % label,
          scaled_max == scaled_max and abs(scaled_max) != float("inf"),
          "stock max |p| %.4f x%.3g overflowed float32" % (stock_max, scale))
    notes.append("%s: 20 models, %d position float32 rewritten, stock max |p| "
                 "%.4f -> %.4f  (arrow-derived bound %.1f is NOT applied to "
                 "this family)" % (label, total_floats, stock_max,
                                   stock_max * scale, S.POS_ABS_MAX))


def s2_s3d(label, iid, stock, new, v, scale, record=True):
    """S2 for one S3D.  Returns the list of failures instead of raising when
    record=False, so the N2 mutation harness can prove it fires."""
    fails = []

    def ok(sub, cond, detail=""):
        if cond:
            if record:
                _checks[0] += 1
            return True
        fails.append("%s.%s %08X %s" % (label, sub, iid, detail))
        return False

    ok("S2a", len(new) == len(stock),
       "length %d -> %d" % (len(stock), len(new)))
    if len(new) == len(stock):
        moved = {i for i in range(len(stock)) if stock[i] != new[i]}
        allowed = {o + k for o in v.position_offsets for k in range(4)}
        ok("S2b", moved <= allowed,
           "%d bytes moved outside the position spans: %s"
           % (len(moved - allowed), sorted(moved - allowed)[:8]))
        ok("S2c", moved, "the edit changed nothing at all")
        for (name, off, want) in v.length_fields():
            if off is None:
                got = len(new)
            elif isinstance(want, bytes):
                got = new[off:off + len(want)]
            else:
                got = struct.unpack_from("<I" if name != "VERT.vertex_count"
                                         else "<H", new, off)[0]
            ok("S2d", got == want, "%s moved: %r -> %r" % (name, want, got))
        v2 = None
        try:
            v2 = S.decode(new)
        except Exception as ex:
            ok("S2e", False, "rewritten record no longer decodes: %s" % ex)
        if v2 is not None:
            ok("S2e", [c.tag for c in v2.chunks] == [c.tag for c in v.chunks]
               and v2.vertex_count == v.vertex_count and v2.stride == v.stride,
               "chunk chain or vertex geometry changed")
            for o in v.uv_offsets:
                ok("S2f", struct.unpack_from("<f", new, o)[0]
                   == struct.unpack_from("<f", stock, o)[0],
                   "a UV moved at offset %d" % o)
            for o in v.position_offsets:
                a0 = struct.unpack_from("<f", stock, o)[0]
                a1 = struct.unpack_from("<f", new, o)[0]
                ok("S2g", a1 == struct.unpack_from(
                    "<f", struct.pack("<f", a0 * scale), 0)[0],
                   "position at %d is %r, not %r*%g" % (o, a1, a0, scale))
    if record and fails:
        raise Refuse("; ".join(fails[:6]))
    return fails


def build_exemplar(inst, records, notes, occ_new):
    tgi = EXEMPLAR_TGI
    a, e, stock, qfs, listed = inst.fetch(tgi)
    check("C.S0a exemplar at the pinned offset/size",
          (a.name, e[3], e[4]) == (PIN_EXEMPLAR["arc"], PIN_EXEMPLAR["off"],
                                   PIN_EXEMPLAR["size"]),
          "found %s @%d %d bytes" % (a.name, e[3], e[4]))
    check("C.S0b exemplar ships UNCOMPRESSED and is absent from the DIR",
          not qfs and not listed, "qfs=%s dir_listed=%s" % (qfs, listed))
    check("C.F4 exemplar uncontested by any plugin",
          not inst.owners(tgi, "plug"),
          "held by %s" % [inst.rel(x) for x, _ in inst.owners(tgi, "plug")])

    # ---- S1: the walk must land exactly on the record end -------------------
    parent, props = D.decode_exemplar(stock)
    check("C.S1a OccupantSize present", PROP_OCCUPANT_SIZE in props)
    tn, vals = props[PROP_OCCUPANT_SIZE]
    check("C.S0c stock OccupantSize is the pinned triple",
          tn == "Float32" and tuple(vals) == PIN_EXEMPLAR["occ"],
          "read %s %r" % (tn, vals))
    check("C.S0d exemplar self-name is the pinned one",
          props.get(0x00000020, ("", [""]))[1][0] == PIN_EXEMPLAR["name"],
          "read %r" % (props.get(0x00000020),))

    # Locate the value span from the BYTES, then cross-check it against the pin.
    hdr = stock.find(struct.pack("<I", PROP_OCCUPANT_SIZE))
    check("C.S1b OccupantSize id appears exactly once",
          hdr >= 0 and stock.find(struct.pack("<I", PROP_OCCUPANT_SIZE),
                                  hdr + 1) < 0)
    tc, kt = struct.unpack_from("<HH", stock, hdr + 4)
    n = struct.unpack_from("<I", stock, hdr + 9)[0]
    lo = hdr + 13
    check("C.S1c OccupantSize header decodes as Float32[3]",
          (tc, kt, n) == (0x0900, 0x0080, 3),
          "type=0x%04X key=0x%04X count=%d" % (tc, kt, n))
    span = (lo, lo + 12)
    check("C.S1d derived value span equals the pinned span",
          span == PIN_EXEMPLAR["occ_span"], "derived %r" % (span,))

    new = bytearray(stock)
    struct.pack_into("<fff", new, lo, *occ_new)
    new = bytes(new)
    s2_exemplar(stock, new, span, occ_new)
    records.append(dict(tgi=tgi, role="C", data=new, stock=stock,
                        kind="exemplar", meta=span, scale=None,
                        desc="C OccupantSize %r -> %r"
                             % (PIN_EXEMPLAR["occ"], occ_new)))
    notes.append("C: OccupantSize %r -> %r at record offsets %d..%d "
                 "(record stays %d bytes)"
                 % (PIN_EXEMPLAR["occ"], occ_new, span[0], span[1], len(new)))


def s2_exemplar(stock, new, span, occ_new, record=True):
    fails = []

    def ok(sub, cond, detail=""):
        if cond:
            if record:
                _checks[0] += 1
            return True
        fails.append("C.%s %s" % (sub, detail))
        return False

    ok("S2a", len(new) == len(stock), "length %d -> %d" % (len(stock), len(new)))
    if len(new) == len(stock):
        moved = {i for i in range(len(stock)) if stock[i] != new[i]}
        ok("S2b", moved <= set(range(*span)),
           "%d bytes moved outside [%d,%d)" % (len(moved - set(range(*span))),
                                               span[0], span[1]))
        ok("S2c", moved, "the edit changed nothing at all")
        try:
            p0, pr0 = D.decode_exemplar(stock)
            p1, pr1 = D.decode_exemplar(new)
        except Exception as ex:
            ok("S2d", False, "rewritten exemplar no longer decodes: %s" % ex)
            p0 = p1 = pr0 = pr1 = None
        if pr1 is not None:
            ok("S2d", p0 == p1 and set(pr0) == set(pr1),
               "the property set or parent cohort changed")
            for pid in pr0:
                if pid == PROP_OCCUPANT_SIZE:
                    continue
                ok("S2e", pr0[pid] == pr1[pid],
                   "property 0x%08X changed: %r -> %r" % (pid, pr0[pid], pr1[pid]))
            ok("S2f", tuple(pr1[PROP_OCCUPANT_SIZE][1]) == tuple(occ_new),
               "OccupantSize reads back %r" % (pr1[PROP_OCCUPANT_SIZE][1],))
    if record and fails:
        raise Refuse("; ".join(fails[:6]))
    return fails


def build_canary(inst, records, notes, pin, rgba, label, allow_plugin_owner):
    tgi = pin["tgi"]
    a, e, stock, qfs, listed = inst.fetch(tgi)
    check("%s.S0a %s at the pinned offset/size" % (label, pin["what"]),
          (a.name, e[3], e[4]) == (pin["arc"], pin["off"], pin["size"]),
          "found %s @%d %d bytes" % (a.name, e[3], e[4]))
    check("%s.S0b ships uncompressed and is absent from the DIR" % label,
          not qfs and not listed, "qfs=%s dir_listed=%s" % (qfs, listed))
    ih = png_ihdr(stock)
    check("%s.S0c stock is the pinned %dx%d 8-bit RGBA PNG"
          % (label, pin["w"], pin["h"]),
          (ih["w"], ih["h"], ih["depth"], ih["ctype"], ih["inter"])
          == (pin["w"], pin["h"], 8, 6, 0), "read %r" % ih)

    # ---- who actually wins the load order for this TGI -----------------------
    plug = inst.owners(tgi, "plug")             # only what SC4 loads
    ondisk = inst.owners(tgi, "plug_all")       # everything, staging included
    staging_only = [inst.rel(x) for x, _ in ondisk
                    if not x.loaded]
    if not allow_plugin_owner:
        check("%s.L2 uncontested by every archive SC4 loads from Plugins"
              % label, not plug, "held by %s" % [inst.rel(x) for x, _ in plug])
        # The STRONGER claim, asserted rather than assumed: this canary's whole
        # value is that no precedence rule stands between us and the screen, so
        # it must be unheld even by files SC4 does not open -- otherwise a tier
        # switch could quietly turn it into a contested TGI between builds.
        check("%s.L2b uncontested by every DBPF in the tree, loaded or not"
              % label, not ondisk,
              "held on disk by %s" % [inst.rel(x) for x, _ in ondisk])
        # Reported, not asserted: a staging payload is not loaded, but if one
        # ever carries this TGI the human should see it rather than have it
        # filtered away silently.
        winner_arc, winner_bytes = a.name, stock
        winner_path = os.path.join(inst.game_dir, a.name)
    else:
        check("%s.L3 exactly one loaded plugin definition to displace" % label,
              len(plug) <= 1,
              "%d loaded holders: %s -- with more than one the winner depends "
              "on a plugin-ordering rule this build cannot measure, so the "
              "canary would have an unknown baseline"
              % (len(plug), [inst.rel(x) for x, _ in plug]))
        if plug:
            wa, we = plug[0]
            winner_bytes, _wq, _wl = wa.payload(we)
            winner_arc = inst.rel(wa)
            winner_path = wa.path
        else:
            winner_arc, winner_bytes, winner_path = a.name, stock, \
                os.path.join(inst.game_dir, a.name)

    wih = png_ihdr(winner_bytes)
    check("%s.S1a the live winner is an 8-bit RGBA non-interlaced PNG" % label,
          (wih["depth"], wih["ctype"], wih["inter"]) == (8, 6, 0),
          "winner %s is %r" % (winner_arc, wih))
    # decode the winner through OUR decoder -- proves it handles real art, which
    # is what makes the S5 pixel check on our own output meaningful
    ww, wh, _seen = png_decode_solid(winner_bytes)
    check("%s.S1b winner decodes to its declared dimensions" % label,
          (ww, wh) == (wih["w"], wih["h"]),
          "IHDR says %dx%d, decoded %dx%d" % (wih["w"], wih["h"], ww, wh))

    new = png_solid(wih["w"], wih["h"], rgba)
    nih = png_ihdr(new)
    check("%s.S2a the replacement matches the WINNER's dimensions, not stock's"
          % label, (nih["w"], nih["h"]) == (wih["w"], wih["h"]),
          "made %dx%d for a %dx%d winner"
          % (nih["w"], nih["h"], wih["w"], wih["h"]))
    check("%s.S2b the replacement matches the winner's pixel format" % label,
          (nih["depth"], nih["ctype"], nih["inter"])
          == (wih["depth"], wih["ctype"], wih["inter"]))
    check("%s.S2c the replacement differs from the winner" % label,
          new != winner_bytes)
    nw, nh, npx = png_decode_solid(new)
    check("%s.S2d every pixel is the intended colour" % label,
          npx == {bytes(rgba)}, "found %d distinct pixels: %r"
          % (len(npx), sorted(npx)[:4]))
    check("%s.S2e the colour is not the engine's missing-texture magenta" % label,
          not (rgba[0] > 0xC0 and rgba[1] < 0x40 and rgba[2] > 0xC0),
          "rgba=%r" % (rgba,))

    records.append(dict(tgi=tgi, role=label, data=new, stock=stock,
                        kind="png", meta=(wih["w"], wih["h"], rgba), scale=None,
                        desc="%s %dx%d solid RGBA%r (%s)"
                             % (label, wih["w"], wih["h"], rgba, pin["what"])))
    notes.append("%s: winner = %s  sha256=%s  %dx%d -> solid RGBA%r"
                 % (label, winner_arc, sha(winner_bytes)[:16],
                    wih["w"], wih["h"], rgba))
    if staging_only:
        notes.append("%s: %d NOT-LOADED staging payload(s) also define this "
                     "TGI (%s) -- reported, not a contest: SC4 opens %s only"
                     % (label, len(staging_only), ", ".join(staging_only[:3]),
                        "/".join(LOADED_EXT)))
    return dict(winner_arc=winner_arc, winner_path=winner_path,
                winner_sha=sha(winner_bytes), w=wih["w"], h=wih["h"],
                contested=bool(plug), staging=staging_only)


# ==========================================================================
# DBPF writer + structural verification
# ==========================================================================

def dbpf_pack(records, out_path, now=None):
    now = int(time.time()) if now is None else now
    rows = sorted(records, key=lambda r: r["tgi"])
    body, offsets = bytearray(), []
    off = 96
    for r in rows:
        offsets.append((r["tgi"], off, len(r["data"])))
        body += r["data"]
        off += len(r["data"])
    idx_off, idx_size = off, len(rows) * 20
    hdr = bytearray(96)
    hdr[0:4] = b"DBPF"
    struct.pack_into("<II", hdr, 4, 1, 0)                 # 1.0
    struct.pack_into("<II", hdr, 0x18, now, now)
    struct.pack_into("<I", hdr, 0x20, 7)                  # index major
    struct.pack_into("<III", hdr, 0x24, len(rows), idx_off, idx_size)
    struct.pack_into("<III", hdr, 0x30, 0, 0, 0)          # no holes
    struct.pack_into("<I", hdr, 0x3C, 0)                  # index minor -> 7.0
    idx = bytearray()
    for (t, g, i), o, n in offsets:
        idx += struct.pack("<IIIII", t, g, i, o, n)
    with open(out_path, "wb") as f:
        f.write(bytes(hdr) + bytes(body) + bytes(idx))
    return rows, idx_off, idx_size


def verify_archive(out_path, rows, idx_off, idx_size, scale, occ_new):
    blob = open(out_path, "rb").read()

    # ---- S3 structure -------------------------------------------------------
    check("S3a magic + version", blob[:4] == b"DBPF"
          and struct.unpack_from("<II", blob, 4) == (1, 0))
    cnt, io_, is_ = struct.unpack_from("<III", blob, 0x24)
    check("S3b index major 7 / minor 0",
          struct.unpack_from("<I", blob, 0x20)[0] == 7
          and struct.unpack_from("<I", blob, 0x3C)[0] == 0)
    check("S3c index count/offset/size agree with what we wrote",
          (cnt, io_, is_) == (len(rows), idx_off, idx_size),
          "header says %r, we wrote %r" % ((cnt, io_, is_),
                                           (len(rows), idx_off, idx_size)))
    check("S3d index size is count*20", is_ == cnt * 20)
    check("S3e index offset + size == file size", io_ + is_ == len(blob),
          "%d + %d != %d" % (io_, is_, len(blob)))
    check("S3f hole count/offset/size all zero",
          struct.unpack_from("<III", blob, 0x30) == (0, 0, 0))
    check("S3g reserved tail 0x40..0x5F is zero", blob[0x40:0x60] == b"\0" * 32)

    ents = [struct.unpack_from("<IIIII", blob, io_ + k * 20) for k in range(cnt)]
    keys = [(t, g, i) for (t, g, i, _o, _n) in ents]
    check("S3h no duplicate TGI", len(set(keys)) == len(keys))
    check("S3i no compression directory under EITHER DIR spelling",
          not (set(keys) & DIR_TGIS))
    spans = sorted((o, o + n) for (_t, _g, _i, o, n) in ents)
    cur = 96
    for (a, b) in spans:
        check("S3j payloads tile [96, index) with no gap and no overlap",
              a == cur, "next payload starts at %d, expected %d" % (a, cur))
        cur = b
    check("S3k payloads end exactly where the index begins", cur == io_,
          "payloads end at %d, index at %d" % (cur, io_))

    # ---- S4 read-back bytes / S5 read-back meaning --------------------------
    got = {}
    for (t, g, i, o, n) in ents:
        got[(t, g, i)] = blob[o:o + n]
    for r in rows:
        k = r["tgi"]
        check("S4 %s round-trips byte-for-byte" % tgis(k),
              got.get(k) == r["data"],
              "%d bytes out, %d in" % (len(r["data"]), len(got.get(k, b""))))

        out = got[k]
        if r["kind"] == "s3d":
            v0 = r["meta"]
            v1 = S.decode(out)                       # decoded FROM SCRATCH
            check("S5a %s re-decodes to the same geometry" % tgis(k),
                  v1.vertex_count == v0.vertex_count and v1.stride == v0.stride
                  and [c.tag for c in v1.chunks] == [c.tag for c in v0.chunks])
            for o1, o0 in zip(v1.position_offsets, v0.position_offsets):
                want = struct.unpack_from("<f", struct.pack(
                    "<f", struct.unpack_from("<f", r["stock"], o0)[0] * scale),
                    0)[0]
                check("S5b %s position at %d reads back at exactly stock*%g"
                      % (tgis(k), o1, scale),
                      struct.unpack_from("<f", out, o1)[0] == want)
            for o1 in v1.uv_offsets:
                check("S5c %s UV at %d is untouched" % (tgis(k), o1),
                      struct.unpack_from("<f", out, o1)[0]
                      == struct.unpack_from("<f", r["stock"], o1)[0])
        elif r["kind"] == "exemplar":
            _p, pr = D.decode_exemplar(out)
            check("S5d %s OccupantSize reads back as the intended triple"
                  % tgis(k),
                  tuple(pr[PROP_OCCUPANT_SIZE][1]) == tuple(occ_new),
                  "read %r" % (pr[PROP_OCCUPANT_SIZE][1],))
            _p0, pr0 = D.decode_exemplar(r["stock"])
            for pid in pr0:
                if pid != PROP_OCCUPANT_SIZE:
                    check("S5e %s property 0x%08X survived the round trip"
                          % (tgis(k), pid), pr0[pid] == pr[pid])
        elif r["kind"] == "png":
            w, h, rgba = r["meta"]
            gw, gh, seen = png_decode_solid(out)
            check("S5f %s decodes to %dx%d" % (tgis(k), w, h), (gw, gh) == (w, h),
                  "decoded %dx%d" % (gw, gh))
            check("S5g %s is one flat colour, the intended one" % tgis(k),
                  seen == {bytes(rgba)}, "%d distinct pixels" % len(seen))
            # INDEPENDENT decoder -- a shared bug would have to exist in both
            try:
                from PIL import Image
                import io as _io
                im = Image.open(_io.BytesIO(out)).convert("RGBA")
                check("S5h %s Pillow agrees on size" % tgis(k),
                      im.size == (w, h), "Pillow says %r" % (im.size,))
                cols = im.getcolors(maxcolors=16)
                check("S5i %s Pillow agrees on the single colour" % tgis(k),
                      cols is not None and len(cols) == 1
                      and cols[0][1] == tuple(rgba),
                      "Pillow says %r" % (cols,))
            except ImportError:
                print("  ! Pillow absent -- S5h/S5i (second image decoder) SKIPPED")

    # ---- N1 negative control ------------------------------------------------
    check("N1 a TGI we did not ship is absent from the finished index",
          N1_ABSENT_TGI not in set(keys))
    return ents


def second_opinion(out_path, rows, stage_dir):
    """S6 second reader and S7 second writer, both via DbpfPack.exe."""
    if not os.path.isfile(DBPF_PACK_EXE):
        print("  ! DbpfPack.exe absent -- S6/S7 SKIPPED")
        return
    listing = subprocess.run([DBPF_PACK_EXE, "--list", out_path],
                             capture_output=True, text=True)
    check("S6a DbpfPack.exe --list succeeds", listing.returncode == 0,
          listing.stderr.strip())
    txt = listing.stdout
    check("S6b it reports DBPF 1.0 / index 7.0", "DBPF 1.0" in txt
          and "index 7.0" in txt)
    check("S6c it reports the compression directory as absent",
          "compression directory absent" in txt)
    check("S6d it counts the records we wrote", "%d entries" % len(rows) in txt,
          txt.splitlines()[3] if len(txt.splitlines()) > 3 else txt[:200])
    for r in rows:
        check("S6e --list names %s" % tgis(r["tgi"]),
              "0x%08X 0x%08X 0x%08X" % r["tgi"] in txt)

    tmp = tempfile.mkdtemp(prefix="row15-verify-")
    try:
        ex = os.path.join(tmp, "ex")
        os.makedirs(ex)
        rc = subprocess.run([DBPF_PACK_EXE, "--extract", out_path, ex],
                            capture_output=True, text=True)
        check("S6f DbpfPack.exe --extract succeeds", rc.returncode == 0,
              rc.stderr.strip())
        for r in rows:
            cand = [p for p in os.listdir(ex)
                    if p.lower().startswith("t-0x%08x_g-0x%08x_i-0x%08x"
                                            % r["tgi"])]
            check("S6g extractor produced exactly one file for %s"
                  % tgis(r["tgi"]), len(cand) == 1, "got %r" % cand)
            blob = open(os.path.join(ex, cand[0]), "rb").read()
            check("S6h extracted payload for %s is byte-identical"
                  % tgis(r["tgi"]), blob == r["data"])

        # S7 -- second writer over the same staging directory
        alt = os.path.join(tmp, "alt.dat")
        rc = subprocess.run([DBPF_PACK_EXE, stage_dir, alt],
                            capture_output=True, text=True)
        check("S7a DbpfPack.exe packs the staging directory", rc.returncode == 0,
              rc.stderr.strip())
        a = open(out_path, "rb").read()
        b = open(alt, "rb").read()
        check("S7b both writers produce the same file size", len(a) == len(b),
              "%d vs %d" % (len(a), len(b)))
        # everything except the two date dwords must match byte-for-byte
        ma = a[:0x18] + a[0x20:]
        mb = b[:0x18] + b[0x20:]
        check("S7c both writers agree byte-for-byte outside the date fields",
              ma == mb, "first difference at %d"
              % next((i for i in range(min(len(ma), len(mb)))
                      if ma[i] != mb[i]), -1))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ==========================================================================
# N2 -- prove S2 can fail
# ==========================================================================

def mutation_suite(records, scale, occ_new):
    """Break one thing at a time; the named control must catch every one."""
    fired = []
    s3d = [r for r in records if r["kind"] == "s3d"][0]
    exms = [r for r in records if r["kind"] == "exemplar"]
    exm = exms[0] if exms else None

    # M1 -- a byte rewritten outside the position spans
    v = s3d["meta"]
    bad = bytearray(s3d["data"])
    off = v.uv_offsets[0]
    bad[off] ^= 0xFF
    f = s2_s3d("N2", s3d["tgi"][2], s3d["stock"], bytes(bad), v, scale,
               record=False)
    fired.append(("M1 byte outside the position spans",
                  any(".S2b" in x or ".S2f" in x for x in f), f))

    # M2 -- a declared chunk length rewritten too
    bad = bytearray(S.scale_positions(s3d["stock"], v.position_offsets, scale))
    struct.pack_into("<I", bad, v.vert_off + 4,
                     struct.unpack_from("<I", bad, v.vert_off + 4)[0] + 4)
    f = s2_s3d("N2", s3d["tgi"][2], s3d["stock"], bytes(bad), v, scale,
               record=False)
    fired.append(("M2 a chunk length moved", any(".S2d" in x or ".S2b" in x
                                                 for x in f), f))

    # M3 -- the scale is a no-op
    f = s2_s3d("N2", s3d["tgi"][2], s3d["stock"],
               S.scale_positions(s3d["stock"], v.position_offsets, 1.0), v,
               scale, record=False)
    fired.append(("M3 scale is a no-op", any(".S2c" in x or ".S2g" in x
                                             for x in f), f))

    # M4 -- the record grew
    f = s2_s3d("N2", s3d["tgi"][2], s3d["stock"], s3d["data"] + b"\x00", v,
               scale, record=False)
    fired.append(("M4 the record grew", any(".S2a" in x for x in f), f))

    # M5 -- an unrelated exemplar property clobbered as well
    if exm is not None:
        span = exm["meta"]
        bad = bytearray(exm["data"])
        bad[10] ^= 0xFF
        f = s2_exemplar(exm["stock"], bytes(bad), span, occ_new, record=False)
        fired.append(("M5 a byte outside the OccupantSize span",
                      any(".S2b" in x for x in f), f))

    # M6 -- our own PNG decoder must reject a corrupted image
    png = [r for r in records if r["kind"] == "png"][0]
    bad = bytearray(png["data"])
    bad[30] ^= 0xFF
    caught = False
    try:
        png_decode_solid(bytes(bad))
    except Exception:
        caught = True
    fired.append(("M6 a corrupted PNG", caught, []))

    for name, ok, detail in fired:
        check("N2 %s is caught" % name, ok,
              "the control did not fire; failures were %r" % (detail[:3],))
    return len(fired)


# ==========================================================================

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=3.0,
                    help="uniform factor on every S3D position float (default 3)")
    ap.add_argument("--occupant-size", default=",".join(
        "%g" % v for v in NEW_OCCUPANT_SIZE),
        help="replacement OccupantSize triple (default %s); must be ANISOTROPIC"
             % ",".join("%g" % v for v in NEW_OCCUPANT_SIZE))
    ap.add_argument("--roles", default="B,C",
                    help="which SUBJECT roles to ship: B (arrow geometry), "
                         "C (arrow OccupantSize), or both (default). The "
                         "controls K1, K2 and E are always shipped -- a probe "
                         "without its controls is not a probe. Use --roles B "
                         "or --roles C to BISECT the one outcome that is "
                         "ambiguous with both live: the arrow VANISHING.")
    ap.add_argument("--out", default=OUT_PATH)
    ap.add_argument("--game", default=None)
    ap.add_argument("--plugins", default=None)
    ap.add_argument("--check-only", action="store_true",
                    help="run every check, then delete the output")
    args = ap.parse_args(argv)

    occ_new = tuple(float(x) for x in args.occupant_size.split(","))
    out_path = os.path.abspath(args.out)
    # --check-only must never touch the shipping path.  It still packs a real
    # archive and runs every structural check against it -- it just does so
    # beside the real one, so running the checks cannot destroy a good DAT.
    check_dir = None
    if args.check_only:
        check_dir = tempfile.mkdtemp(prefix="row15-checkonly-")
        out_path = os.path.join(check_dir, os.path.basename(out_path))
    t0 = time.time()
    records, notes = [], []
    inst = None
    wrote = [False]
    try:
        # ---- X0 design gate -------------------------------------------------
        stock_occ = PIN_EXEMPLAR["occ"]
        check("X0a the OccupantSize triple has three components",
              len(occ_new) == 3, "got %r" % (occ_new,))
        check("X0b every OccupantSize component is positive and finite",
              all(0 < v < 1e6 for v in occ_new), "got %r" % (occ_new,))
        check("X0c the OccupantSize edit is not a no-op",
              tuple(occ_new) != tuple(stock_occ))
        ratios = [n / s for n, s in zip(occ_new, stock_occ)]
        uniform = max(ratios) - min(ratios) < 1e-6
        check("X0d COLLISION GATE: the OccupantSize edit must be ANISOTROPIC",
              not uniform,
              "%r -> %r is a uniform x%.4g, which produces the SAME observation "
              "as the geometry override (role B, also a uniform scale). Two "
              "distinct causes, one observation -- the probe could not "
              "distinguish its own outcomes. Change the aspect ratio instead, "
              "e.g. %r." % (stock_occ, occ_new, ratios[0], NEW_OCCUPANT_SIZE))
        check("X0e the geometry scale is not a no-op", abs(args.scale - 1.0) > 1e-9,
              "scale=%r would make role B and role E unreadable" % args.scale)
        check("X0f the geometry scale is large enough to read by eye",
              args.scale >= 2.0 or args.scale <= 0.5,
              "scale=%r is too close to 1 to judge against a road tile"
              % args.scale)
        roles = {r.strip().upper() for r in args.roles.split(",") if r.strip()}
        check("X0g --roles names only subject roles", roles <= {"B", "C"},
              "got %r; K1/K2/E are controls and are always shipped"
              % sorted(roles))
        check("X0h at least one subject role is shipped", roles,
              "a DAT with only controls measures nothing about row 15")

        print("SC4 row-15 probe builder (v2)")
        print("  game    : %s" % (args.game or D.GAME))
        inst = Install(args.game, args.plugins)
        print("  plugins : %s" % inst.plugins_dir)
        nloaded = sum(1 for a in inst.plugin_archives if a.loaded)
        print("  archives: %d shipped, %d DBPF found in Plugins of which %d "
              "are loaded by SC4 and %d are tier-staging payloads "
              "(%d unreadable skipped)"
              % (len(inst.archives), len(inst.plugin_archives), nloaded,
                 inst.plugin_staging, inst.plugin_skipped))
        check("L4 the live Plugins tree was actually found and read",
              inst.plugins_dir and nloaded > 0,
              "no plugin archives read -- a load-order pre-flight that scans "
              "nothing is not evidence; set SC4_PLUGINS")

        print("\n-- building --")
        if roles != {"B", "C"}:
            print("  ! BISECT BUILD: subject roles %s only. This DAT answers a "
                  "narrower question than the full probe; read the README's "
                  "bisect row, not its main table." % sorted(roles))
        if "B" in roles:
            build_s3d_family(inst, ARROW_BASE, "B", args.scale, records, notes)
        if "C" in roles:
            build_exemplar(inst, records, notes, occ_new)
        build_s3d_family(inst, ZOT_BASE, "E", args.scale, records, notes)
        k1 = build_canary(inst, records, notes, PIN_K1, K1_RGBA, "K1", False)
        k2 = build_canary(inst, records, notes, PIN_K2, K2_RGBA, "K2", True)
        for n in notes:
            print("  " + n)

        # ---- stage, pack, verify -------------------------------------------
        if os.path.isdir(STAGE_DIR):
            shutil.rmtree(STAGE_DIR)
        os.makedirs(STAGE_DIR)
        for r in records:
            with open(os.path.join(STAGE_DIR, "T-0x%08X_G-0x%08X_I-0x%08X.bin"
                                   % r["tgi"]), "wb") as f:
                f.write(r["data"])

        rows, idx_off, idx_size = dbpf_pack(records, out_path)
        wrote[0] = True
        print("\n-- verifying --")
        ents = verify_archive(out_path, rows, idx_off, idx_size, args.scale,
                              occ_new)
        second_opinion(out_path, rows, STAGE_DIR)
        nmut = mutation_suite(records, args.scale, occ_new)
        print("  %d mutations, every one caught by its named control" % nmut)

        # ---- manifest -------------------------------------------------------
        blob = open(out_path, "rb").read()
        print("\n" + "=" * 74)
        print("MANIFEST  %s" % os.path.basename(out_path))
        print("=" * 74)
        print("  %d records, %d bytes, sha256 %s" % (len(rows), len(blob),
                                                     sha(blob)))
        print("  index %d entries @ 0x%X (%d bytes); DIR: none, under either "
              "spelling" % (len(rows), idx_off, idx_size))
        print("  geometry scale x%g   OccupantSize %r -> %r (ratios %s)"
              % (args.scale, stock_occ, occ_new,
                 ", ".join("%.3g" % r for r in ratios)))
        print()
        byrole = {}
        for r in rows:
            byrole.setdefault(r["role"], []).append(r)
        for role in ("B", "C", "E", "K1", "K2"):
            rs = byrole.get(role, [])
            if not rs:
                print("  role %-3s  NOT SHIPPED in this bisect build" % role)
                continue
            print("  role %-3s %2d record(s)  %s" % (role, len(rs), {
                "B": "ConnectArrow S3D family, ALL TWENTY zoom/rotation "
                     "variants, positions x%g" % args.scale,
                "C": "arrow exemplar OccupantSize, height only (anisotropic)",
                "E": "NoPower zot S3D family, ALL TWENTY, positions x%g "
                     "-- the proven positive control" % args.scale,
                "K1": "generic button face -> GREEN; uncontested by all %d "
                      "DBPF files in the Plugins tree, loaded or not"
                      % len(inst.plugin_archives),
                "K2": "news-ticker strip -> ORANGE; contested by %s"
                      % (k2["winner_arc"] if k2["contested"] else "nothing"),
            }[role]))
            for r in rs[:2]:
                print("        %s  %5d B  %s" % (tgis(r["tgi"]), len(r["data"]),
                                                 r["desc"]))
            if len(rs) > 2:
                print("        ... and %d more, each decoded and rewritten on "
                      "its own terms" % (len(rs) - 2))
        print()
        print("  K1 winner : %s  (%dx%d)  sha256 %s"
              % (k1["winner_arc"], k1["w"], k1["h"], k1["winner_sha"][:16]))
        print("  K2 winner : %s  (%dx%d)  sha256 %s"
              % (k2["winner_arc"], k2["w"], k2["h"], k2["winner_sha"][:16]))
        if k2["contested"]:
            print("              ^ K2 is shipped at the WINNER's size, not "
                  "stock's (%dx%d). Rebuild the probe if the SC4UIScale tier "
                  "changes." % (PIN_K2["w"], PIN_K2["h"]))
        print()
        print("  %d checks passed in %.1fs" % (_checks[0], time.time() - t0))
        print("=" * 74)

        if args.check_only:
            print("--check-only: every check ran against a real archive packed "
                  "in a scratch directory. %s was not touched."
                  % os.path.basename(args.out))
        else:
            print("\nINSTALL: copy %s into a NEW folder\n"
                  "  %s\\zzzz-SC4UIScale-row15-probe\\\n"
                  "REMOVE : delete that folder. Nothing else changes.\n"
                  "READ   : README.md -- do the BASELINE pass FIRST or the run "
                  "is void." % (os.path.basename(out_path), inst.plugins_dir))
        return 0

    except Refuse as ex:
        print("\nREFUSED after %d checks: %s" % (_checks[0], ex), file=sys.stderr)
        # Delete ONLY a file this run created.  A refusal that fires before the
        # pack must not destroy a good DAT an earlier run left behind -- that
        # turns a check run into a demolition, and it bit this file once.
        if wrote[0] and os.path.exists(out_path):
            os.remove(out_path)
            print("the DAT this run wrote has been deleted; nothing shipped.",
                  file=sys.stderr)
        else:
            print("nothing was written; any existing %s is untouched."
                  % os.path.basename(out_path), file=sys.stderr)
        return 1
    finally:
        if inst is not None:
            inst.close()
        if check_dir:
            shutil.rmtree(check_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
