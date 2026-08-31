#!/usr/bin/env python3
r"""ConnectArrow S3D FAMILY reader -- all twenty zoom/rotation variants.

WHY THIS EXISTS
---------------
The neighbour-connection arrow (overlay census row 15) is NOT one model.  It is
a family of twenty S3D records, instances 0x29F10000 .. 0x29F10430, laid out as

    instance = 0x29F10000 + (zoom-1) * 0x100 + rotation * 0x10
    zoom 1..5      rotation 0..3 = S, W, N, E

and each one self-names accordingly ("29F10430_ConnectArrow_Ui8x1x3_Z5E").  A
geometry override that rewrites ONE of them changes nothing at nineteen of the
twenty camera positions, and the play session that follows cannot tell "the
override does not work" apart from "the camera was not on the variant I
patched".  That is a probe that cannot distinguish its own outcomes.  This
module exists so the override can cover the whole family instead.

The variants DO NOT share a layout.  Vertex counts are 4 / 4 / 7 / 7 / 14 or 15
and decompressed sizes are 336 / 420 / 590 / 622.  Every number reported here is
derived from that variant's own bytes; nothing is copied from a sibling and the
vertex stride is DIVIDED OUT of the chunk, never assumed.

WHAT IT GIVES YOU
-----------------
    family_instances()             -> the twenty ids, in (zoom, rotation) order
    load(instance)                 -> Variant, every offset absolute into .data
    position_offsets(instance)     -> (decompressed_bytes,
                                       [byte offset of every position float32])
    scale_positions(data, offs, f) -> new bytes, guaranteed same length

READ-ONLY.  Opens the game archives for reading and writes nothing, anywhere.

SELF-TEST -- the point of the file.  Run it before trusting any number:

    python s3d_family.py                 # family table + every control
    python s3d_family.py --verbose       # + every vertex of every variant
    SC4_GAME_DIR=... python s3d_family.py

Exit status is 0 only if every control passes for every variant.
"""

import argparse
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dbpfcore
from dbpfcore import GAME, T_S3D, T_EXEMPLAR

S3D_GROUP = 0xBADB57F1
FAMILY_BASE = 0x29F10000
FAMILY_LAST = 0x29F10430

# The exemplar that binds this family, via its RKT property 0x27812821.  Stored
# UNCOMPRESSED, so it must be ABSENT from the compression directory -- that is
# the negative control on the DIR lookup (control D0d).
EXEMPLAR_TGI = (T_EXEMPLAR, 0xC977C536, 0x29F10000)

ZOOM_CHARS = "12345"
ROT_CHARS = "SWNE"

# Chunks that use the "tag + uint32 length INCLUDING this 8-byte header"
# convention.  ANIM does NOT.  The four bytes after the ANIM tag read as a
# constant 9301 in all twenty variants, and the files are only 336..622 bytes
# long, so that value is not a length of anything -- it is the first two
# animation fields.  The chain is therefore walked only as far as ANIM, and the
# tail past it is never touched by anything here.
LENGTH_CHUNKS = ("HEAD", "VERT", "INDX", "PRIM", "MATS")
ANIM_TAG = b"ANIM"

# Plausibility bounds.  MEASURED off the shipped family, not guessed -- the
# self-test prints the measured extremes next to the bound it applied, so a
# future variant that drifts outside them is visible rather than silently
# tolerated.
#   position floats  measured  -6.00042 .. +14.45752
#   excluded floats  measured   0.00000 ..  +0.99498   <- texture coordinates
# The UV bound is the DISCRIMINATING half: if the 5 floats per vertex were split
# 3+2 the wrong way round, a metre-scale coordinate would land in the UV test and
# blow it up.  A loose position bound alone would not catch that.
POS_ABS_MAX = 64.0
UV_MIN, UV_MAX = -0.01, 1.01

# Which of the five float32s per vertex are position and which are texture
# coordinates.  Named rather than inlined so the mutation harness (--mutation)
# can swap them and prove control C5d actually fires when the split is wrong.
POS_SLOTS = (0, 1, 2)
UV_SLOTS = (3, 4)


# ---------------------------------------------------------------------------
# instance id <-> zoom / rotation
# ---------------------------------------------------------------------------

def family_instances():
    """The twenty ids this family occupies, in (zoom, rotation) order."""
    return [FAMILY_BASE + z * 0x100 + r * 0x10
            for z in range(5) for r in range(4)]


def zoom_rot(instance):
    """(zoom 1..5, rotation 0..3) as encoded in the instance id's low 12 bits.

    This mapping is not asserted here -- control C4 checks it against each
    model's OWN embedded name, which is the game's statement of it, not ours.
    """
    delta = instance - FAMILY_BASE
    if not (0 <= delta <= FAMILY_LAST - FAMILY_BASE):
        raise ValueError("0x%08X is outside the ConnectArrow family" % instance)
    if delta & 0x00F:
        raise ValueError("0x%08X is not on a rotation slot" % instance)
    z = (delta >> 8) & 0xF
    r = (delta >> 4) & 0xF
    if z > 4 or r > 3:
        raise ValueError("0x%08X is not a valid zoom/rotation slot" % instance)
    return z + 1, r


def variant_tag(instance):
    z, r = zoom_rot(instance)
    return "Z%s%s" % (ZOOM_CHARS[z - 1], ROT_CHARS[r])


# ---------------------------------------------------------------------------
# S3D structure
# ---------------------------------------------------------------------------

class Chunk(object):
    def __init__(self, tag, off, length):
        self.tag = tag
        self.off = off
        self.length = length        # declared, header-inclusive
        self.end = off + length

    def __repr__(self):
        return "%s@%d:%d" % (self.tag, self.off, self.length)


class Variant(object):
    """One decoded family member.  All offsets are absolute into `data`."""

    def __init__(self):
        self.instance = 0
        self.tag = ""
        self.zoom = 0
        self.rotation = 0
        self.archive = ""
        self.offset = 0             # byte offset within the archive
        self.ondisk_size = 0
        self.dir_size = None        # uncompressed size declared by the DIR
        self.compressed = False
        self.data = b""             # DECOMPRESSED record bytes
        self.header_uint32 = 0      # the uint32 at record offset 4
        self.chunks = []
        self.vert_off = 0
        self.vert_len = 0
        self.group_count = 0
        self.vertex_count = 0
        self.vertex_format = b""
        self.stride = 0             # DERIVED per variant
        self.floats_per_vertex = 0
        self.vertices_off = 0
        self.position_offsets = []  # byte offset of every position float32
        self.uv_offsets = []
        self.self_name = ""

    def positions(self):
        """[(x, y, z), ...] read back through self.position_offsets."""
        out = []
        for k in range(self.vertex_count):
            trio = self.position_offsets[k * 3: k * 3 + 3]
            out.append(tuple(struct.unpack_from("<f", self.data, o)[0]
                             for o in trio))
        return out

    def uvs(self):
        out = []
        for k in range(self.vertex_count):
            duo = self.uv_offsets[k * 2: k * 2 + 2]
            out.append(tuple(struct.unpack_from("<f", self.data, o)[0]
                             for o in duo))
        return out

    def length_fields(self):
        """Every field in this record that encodes a LENGTH or a COUNT, named.

        A value-only rewrite must leave every one of them byte-identical;
        control T3 asserts that field by field rather than trusting the diff.
        """
        f = [("record_length", None, len(self.data)),
             ("header_uint32@4", 4, self.header_uint32),
             ("VERT.group_count", self.vert_off + 8, self.group_count),
             ("VERT.vertex_count", self.vert_off + 14, self.vertex_count),
             ("VERT.vertex_format", self.vert_off + 16, self.vertex_format)]
        for c in self.chunks:
            f.append(("%s.declared_length" % c.tag, c.off + 4, c.length))
        return f


def _walk_chunks(data):
    """Walk tag + uint32(header-inclusive) from offset 8, stopping at ANIM.

    Returns (chunks, anim_off).  Raises on any tag that is not printable ASCII
    or any declared length that does not fit the buffer -- a wrong layout
    almost never lands cleanly, so this fails loudly rather than drifting.
    """
    chunks = []
    pos = 8
    anim_off = None
    while pos + 8 <= len(data):
        tag = data[pos:pos + 4]
        if tag == ANIM_TAG:
            anim_off = pos
            break
        if not all(32 <= b < 127 for b in tag):
            raise ValueError("non-ASCII chunk tag at offset %d: %r" % (pos, tag))
        ln = struct.unpack_from("<I", data, pos + 4)[0]
        if ln < 8 or pos + ln > len(data):
            raise ValueError("chunk %r at %d declares length %d, which does not "
                             "fit the %d-byte record" % (tag, pos, ln, len(data)))
        chunks.append(Chunk(tag.decode("ascii"), pos, ln))
        pos += ln
    return chunks, anim_off


def decode(data, instance=None):
    """Decode one decompressed S3D record.  Everything is derived from `data`."""
    v = Variant()
    v.data = data
    if data[0:4] != b"3DMD":
        raise ValueError("not an S3D: magic=%r" % data[0:4])
    v.header_uint32 = struct.unpack_from("<I", data, 4)[0]

    v.chunks, anim_off = _walk_chunks(data)
    tags = [c.tag for c in v.chunks]
    if tags != list(LENGTH_CHUNKS):
        raise ValueError("unexpected chunk chain %r (expected %r)"
                         % (tags, list(LENGTH_CHUNKS)))
    if v.chunks[0].off != 8:
        raise ValueError("first chunk starts at %d, not 8" % v.chunks[0].off)
    for a, b in zip(v.chunks, v.chunks[1:]):
        if a.end != b.off:
            raise ValueError("gap or overlap between %r and %r" % (a, b))
    if anim_off is None:
        raise ValueError("no ANIM chunk -- chain walked off the end")
    if v.chunks[-1].end != anim_off:
        raise ValueError("MATS ends at %d but ANIM starts at %d"
                         % (v.chunks[-1].end, anim_off))

    vert = v.chunks[tags.index("VERT")]
    v.vert_off, v.vert_len = vert.off, vert.length
    body = vert.off + 8
    v.group_count = struct.unpack_from("<I", data, body)[0]
    if v.group_count != 1:
        raise ValueError("VERT declares %d vertex groups; this decoder handles "
                         "one (all twenty shipped variants declare one)"
                         % v.group_count)
    _unk, v.vertex_count = struct.unpack_from("<HH", data, body + 4)
    v.vertex_format = data[body + 8:body + 12]
    v.vertices_off = body + 12

    payload = vert.end - v.vertices_off
    if v.vertex_count <= 0:
        raise ValueError("VERT declares %d vertices" % v.vertex_count)
    if payload <= 0 or payload % v.vertex_count != 0:
        raise ValueError("VERT payload of %d bytes does not divide evenly by "
                         "%d vertices" % (payload, v.vertex_count))
    v.stride = payload // v.vertex_count          # DERIVED, per variant
    if v.stride % 4 != 0:
        raise ValueError("derived stride %d is not a whole number of float32s"
                         % v.stride)
    v.floats_per_vertex = v.stride // 4
    if v.floats_per_vertex != 5:
        raise ValueError("this variant has %d floats per vertex; the 3-position"
                         " + 2-UV split implemented here is only defined for 5"
                         % v.floats_per_vertex)
    for k in range(v.vertex_count):
        base = v.vertices_off + k * v.stride
        v.position_offsets.extend([base + 4 * s for s in POS_SLOTS])
        v.uv_offsets.extend([base + 4 * s for s in UV_SLOTS])

    mats = v.chunks[tags.index("MATS")]
    blob = data[mats.off:mats.end]
    j = blob.find(b"29F1")
    if j >= 0:
        e = blob.find(b"\x00", j)
        v.self_name = blob[j:e if e >= 0 else len(blob)].decode("latin-1")

    if instance is not None:
        v.instance = instance
        v.zoom, v.rotation = zoom_rot(instance)
        v.tag = variant_tag(instance)
    return v


# ---------------------------------------------------------------------------
# archive access -- the holding archive is DISCOVERED, never listed
# ---------------------------------------------------------------------------

_ARCS = {}


def _archives(game=None):
    root = game or GAME
    if root not in _ARCS:
        _ARCS[root] = [dbpfcore.Archive(p)
                       for p in dbpfcore.discover_archives(root)]
    return _ARCS[root]


def locate(instance, game=None):
    """Every (Archive, index entry) holding this family instance, across every
    archive discovered in the install root."""
    hits = []
    for arc in _archives(game):
        for e in arc.find(t=T_S3D, g=S3D_GROUP, i=instance):
            hits.append((arc, e))
    return hits


def load(instance, game=None):
    """Decode one family member out of the shipped archives.

    Raises KeyError when the instance does not ship.  The module never invents a
    variant -- negative control N1 depends on this failing.
    """
    hits = locate(instance, game=game)
    if not hits:
        raise KeyError("no S3D record T=0x%08X G=0x%08X I=0x%08X in any archive"
                       % (T_S3D, S3D_GROUP, instance))
    if len(hits) > 1:
        raise KeyError("instance 0x%08X is defined %d times (%s) -- ambiguous"
                       % (instance, len(hits),
                          ", ".join(a.name for a, _ in hits)))
    arc, entry = hits[0]
    data, was_qfs, listed = arc.payload(entry)
    v = decode(data, instance=instance)
    v.archive = arc.name
    v.offset = entry[3]
    v.ondisk_size = entry[4]
    v.compressed = was_qfs
    v.dir_size = arc.dir.get((entry[0], entry[1], entry[2]))
    return v


def position_offsets(instance, game=None):
    """THE API.

    Given a family instance id, return

        (decompressed_bytes, [byte offset of every position float32])

    The offsets index straight into the returned bytes.  There are
    3 * vertex_count of them, and vertex_count comes from that variant's own
    VERT chunk -- 4, 7, 14 or 15 depending on which of the twenty you ask for.
    """
    v = load(instance, game=game)
    return v.data, list(v.position_offsets)


def scale_positions(data, offsets, factor):
    """Multiply every named float32 by `factor` in a copy of `data`.

    The result is always the same length as the input: this rewrites values in
    place and cannot, by construction, move a length field.  Control T3 proves
    that on the shipped bytes rather than asserting it from the construction.
    """
    buf = bytearray(data)
    for o in offsets:
        val = struct.unpack_from("<f", buf, o)[0]
        struct.pack_into("<f", buf, o, val * factor)
    return bytes(buf)


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

class Controls(object):
    def __init__(self):
        self.failures = []
        self.checks = 0

    def ok(self, cond, label, detail=""):
        self.checks += 1
        if not cond:
            self.failures.append("%s %s" % (label, detail))
        return bool(cond)


def self_test(game=None, verbose=False, out=sys.stdout):
    c = Controls()
    p = lambda *a: print(*a, file=out)
    arcs = _archives(game)
    p("install root : %s" % (game or GAME))
    p("archives DISCOVERED (%d): %s"
      % (len(arcs), ", ".join(a.name for a in arcs)))

    # ---- D0  the compression directory, and the stride it is walked at ----
    p("\n=== D0  COMPRESSION DIRECTORY ===")
    host = [a for a in arcs if a.dir_tgi is not None]
    p("  archives carrying a DIR record: %s"
      % (", ".join("%s {0x%08X,0x%08X,0x%08X} %d entries"
                   % (a.name, a.dir_tgi[0], a.dir_tgi[1], a.dir_tgi[2], len(a.dir))
                   for a in host) or "NONE"))
    sc1 = [a for a in arcs if a.name.lower() == "simcity_1.dat"]
    c.ok(bool(sc1), "D0a", "SimCity_1.dat not discovered")
    if sc1:
        a = sc1[0]
        c.ok(a.dir_tgi is not None, "D0b",
             "SimCity_1.dat reports NO DIR record -- it has one")
        p("  SimCity_1.dat DIR: %s, %d entries"
          % ("{0x%08X,0x%08X,0x%08X}" % a.dir_tgi if a.dir_tgi else "absent",
             len(a.dir)))
        # POSITIVE CONTROL on the stride: at the right stride every DIR entry
        # names a record that really exists AND declares a size larger than that
        # record's on-disk size.  A wrong stride shreds both properties at once.
        idx = {(t, g, i): (off, size) for (t, g, i, off, size) in a.index}
        missing = sum(1 for k in a.dir if k not in idx)
        not_bigger = sum(1 for k, s in a.dir.items()
                         if k in idx and s <= idx[k][1])
        p("  stride control: %d/%d DIR entries resolve to a real index record; "
          "%d declare a size <= their on-disk size"
          % (len(a.dir) - missing, len(a.dir), not_bigger))
        c.ok(missing == 0, "D0c",
             "%d DIR entries name records that do not exist" % missing)
        c.ok(not_bigger == 0, "D0d",
             "%d DIR entries do not actually shrink" % not_bigger)
        # NEGATIVE CONTROL: the exemplar is stored uncompressed, so it must be
        # ABSENT.  If the lookup "found" everything, finding the S3Ds in it
        # would carry no information at all.
        absent = EXEMPLAR_TGI not in a.dir
        p("  negative control: exemplar {0x%08X,0x%08X,0x%08X} in DIR? %s "
          "(expected: absent)"
          % (EXEMPLAR_TGI[0], EXEMPLAR_TGI[1], EXEMPLAR_TGI[2],
             "PRESENT" if not absent else "absent"))
        c.ok(absent, "D0e", "the uncompressed exemplar is listed in the DIR")

    # ---- the family table ----
    p("\n=== FAMILY TABLE ===")
    p("  %-12s %-4s %-14s %-10s %-7s %-6s %-8s %-6s %-7s %-7s %-8s %s"
      % ("instance", "tag", "archive", "offset", "ondisk", "DIR",
         "hdr@4", "nvert", "stride", "vstart", "#posflt", "self-name"))
    variants = []
    for inst in family_instances():
        v = load(inst, game=game)
        variants.append(v)
        p("  0x%08X  %-4s %-14s %-10d %-7d %-6s %-8d %-6d %-7d %-7d %-8d %s"
          % (v.instance, v.tag, v.archive, v.offset, v.ondisk_size, v.dir_size,
             v.header_uint32, v.vertex_count, v.stride, v.vertices_off,
             len(v.position_offsets), v.self_name))
    c.ok(len(variants) == 20, "F0",
         "loaded %d variants, expected 20" % len(variants))
    c.ok(len({v.self_name for v in variants}) == 20, "F1",
         "the twenty variants do not carry twenty distinct self-names")

    # ---- per-variant controls ----
    p("\n=== PER-VARIANT CONTROLS ===")
    all_pos, all_uv = [], []
    for v in variants:
        lbl = "0x%08X %s" % (v.instance, v.tag)

        # C1  decompression agrees with the DIR's independent declaration
        c.ok(v.compressed, "C1a[%s]" % lbl, "not QFS-compressed")
        c.ok(v.dir_size is not None and len(v.data) == v.dir_size,
             "C1b[%s]" % lbl,
             "decompressed to %d bytes, DIR declares %s"
             % (len(v.data), v.dir_size))

        # C2  chunk-chain exactness: the five length-bearing chunks abut with no
        # gap and no overlap, and MATS ends exactly where ANIM begins
        c.ok(all(a.end == b.off for a, b in zip(v.chunks, v.chunks[1:])),
             "C2[%s]" % lbl, "chunk chain has a gap or overlap")

        # C3  VERT internal exactness: the DERIVED stride must consume the VERT
        # body to its LAST byte.  A wrong group-header layout leaves a remainder
        # or overruns; it does not land exactly.
        consumed = v.vertices_off + v.vertex_count * v.stride
        c.ok(consumed == v.vert_off + v.vert_len, "C3[%s]" % lbl,
             "vertices end at %d, VERT chunk ends at %d"
             % (consumed, v.vert_off + v.vert_len))

        # C4  the instance id's bits agree with the model's OWN embedded name.
        # This is the control that the zoom/rotation mapping is the GAME's
        # convention and not one this module invented.
        c.ok(v.self_name.endswith("_" + v.tag), "C4a[%s]" % lbl,
             "instance id implies %s but the model names itself %r"
             % (v.tag, v.self_name))
        c.ok(v.self_name.startswith("%08X_" % v.instance), "C4b[%s]" % lbl,
             "self-name %r does not lead with its own instance id" % v.self_name)

        # C5  plausibility of the 3-of-5 split.  Positions must be finite and
        # metre-scale; the two floats we EXCLUDED must be texture coordinates in
        # [0,1].  Split the five the wrong way round and a metre-scale
        # coordinate lands in the UV test and blows it up -- that half is the
        # one that actually discriminates.
        pos = [f for t in v.positions() for f in t]
        uv = [f for t in v.uvs() for f in t]
        all_pos += pos
        all_uv += uv
        c.ok(all(math.isfinite(f) for f in pos), "C5a[%s]" % lbl,
             "a position float is not finite")
        c.ok(all(abs(f) <= POS_ABS_MAX for f in pos), "C5b[%s]" % lbl,
             "position outside +/-%g: max |v| = %g"
             % (POS_ABS_MAX, max(map(abs, pos))))
        c.ok(any(f != 0.0 for f in pos), "C5c[%s]" % lbl,
             "every position is zero")
        c.ok(all(UV_MIN <= f <= UV_MAX for f in uv), "C5d[%s]" % lbl,
             "the excluded floats are not texture coordinates: range %g .. %g"
             % (min(uv), max(uv)))

        # C6  the reported offsets are what they claim to be
        c.ok(len(v.position_offsets) == 3 * v.vertex_count, "C6a[%s]" % lbl,
             "%d position offsets for %d vertices"
             % (len(v.position_offsets), v.vertex_count))
        c.ok(len(set(v.position_offsets)) == len(v.position_offsets),
             "C6b[%s]" % lbl, "duplicate position offsets")
        c.ok(not (set(v.position_offsets) & set(v.uv_offsets)), "C6c[%s]" % lbl,
             "a position offset collides with a UV offset")
        c.ok(all(v.vertices_off <= o and o + 4 <= v.vert_off + v.vert_len
                 for o in v.position_offsets), "C6d[%s]" % lbl,
             "a position offset falls outside the VERT chunk")

        # ---- T  the claim the geometry override actually rests on ----

        # T0  identity: factor 1.0 must produce a BYTE-IDENTICAL buffer.  This
        # proves the diff machinery below reports real changes and is not simply
        # echoing back the span it was handed.
        c.ok(scale_positions(v.data, v.position_offsets, 1.0) == v.data,
             "T0[%s]" % lbl, "factor 1.0 changed bytes")

        tripled = scale_positions(v.data, v.position_offsets, 3.0)

        # T1  length invariance
        c.ok(len(tripled) == len(v.data), "T1[%s]" % lbl,
             "length %d -> %d" % (len(v.data), len(tripled)))

        # T2  the diff is EXACTLY the position spans -- nothing outside them
        # moved, and every non-zero position float DID move
        diff = {k for k in range(len(v.data)) if v.data[k] != tripled[k]}
        span = set()
        for o in v.position_offsets:
            span |= set(range(o, o + 4))
        c.ok(diff <= span, "T2a[%s]" % lbl,
             "%d byte(s) changed OUTSIDE the position floats, at %s"
             % (len(diff - span), sorted(diff - span)[:8]))
        # Granularity matters here.  Scaling a float32 by 3 is NOT guaranteed to
        # disturb all four of its bytes -- a mantissa byte can survive the
        # multiply by coincidence -- so the assertion is per FLOAT, not per
        # byte: every non-zero position float must have at least one byte move.
        # A float whose span is entirely untouched would mean the offset points
        # at something inert, which is the failure this is looking for.
        inert = [o for o in v.position_offsets
                 if struct.unpack_from("<f", v.data, o)[0] != 0.0
                 and not (set(range(o, o + 4)) & diff)]
        c.ok(not inert, "T2b[%s]" % lbl,
             "%d non-zero position float(s) did not move at all, at offsets %s"
             % (len(inert), inert[:8]))

        # T3  no length or count field moved -- named field by named field,
        # re-read out of the REWRITTEN buffer rather than assumed
        v2 = decode(tripled, instance=v.instance)
        bad = [(n, a, b)
               for (n, _, a), (_, _, b) in zip(v.length_fields(), v2.length_fields())
               if a != b]
        c.ok(not bad, "T3a[%s]" % lbl, "length/count fields changed: %r" % bad)
        c.ok((v2.vertex_count, v2.stride, v2.vertices_off, v2.self_name,
              [(x.tag, x.off, x.length) for x in v2.chunks])
             == (v.vertex_count, v.stride, v.vertices_off, v.self_name,
                 [(x.tag, x.off, x.length) for x in v.chunks]),
             "T3b[%s]" % lbl, "the rewritten buffer re-decodes to a different shape")

        # T4  the rewrite is real: every position reads back at exactly 3x
        p3 = [f for t in v2.positions() for f in t]
        c.ok(all(abs(b - 3.0 * a) <= 1e-4 * max(1.0, abs(3.0 * a))
                 for a, b in zip(pos, p3)), "T4[%s]" % lbl,
             "a position did not read back as 3x")

        # T5  the documented API returns the same thing the Variant does
        d_api, o_api = position_offsets(v.instance, game=game)
        c.ok(d_api == v.data and o_api == v.position_offsets, "T5[%s]" % lbl,
             "position_offsets() disagrees with load()")

        if verbose:
            p("  %s -- %d vertices (x, y, z | u, v):" % (lbl, v.vertex_count))
            for k, (pp, uu) in enumerate(zip(v.positions(), v.uvs())):
                p("     %2d @%-4d  %10.5f %10.5f %10.5f  |  %8.5f %8.5f"
                  % (k, v.position_offsets[k * 3], pp[0], pp[1], pp[2],
                     uu[0], uu[1]))

    p("  measured extremes across all twenty variants:")
    p("    position floats : %10.5f .. %10.5f    (bound applied: +/- %g)"
      % (min(all_pos), max(all_pos), POS_ABS_MAX))
    p("    excluded floats : %10.5f .. %10.5f    (bound applied: %g .. %g)"
      % (min(all_uv), max(all_uv), UV_MIN, UV_MAX))

    # ---- N1  negative control: the loader must be able to come back empty ----
    p("\n=== N1  NEGATIVE CONTROL ===")
    for gi in (FAMILY_BASE + 0x40, FAMILY_BASE + 0x500, 0x29F1DEAD):
        try:
            load(gi, game=game)
            found = True
        except (KeyError, ValueError):
            found = False
        p("  0x%08X -> %s" % (gi, "FOUND (bad)" if found else "absent (expected)"))
        c.ok(not found, "N1[0x%08X]" % gi, "the loader invented a variant")

    p("\n=== SUMMARY ===")
    p("  assertions run: %d    failures: %d" % (c.checks, len(c.failures)))
    for f in c.failures:
        p("  FAIL %s" % f)
    return c


# ---------------------------------------------------------------------------
# mutation harness -- proves the controls above can FAIL
# ---------------------------------------------------------------------------
# A self-test that passes is worth nothing until you have seen it fail for the
# right reason.  Each mutation below breaks exactly one thing and names the
# control that must catch it; if the control stays green under its own mutation
# it is decoration, not evidence, and this harness fails the run.

def _mutations():

    def m_split():
        """Read positions from the WRONG three of the five floats per vertex."""
        global POS_SLOTS, UV_SLOTS
        old = (POS_SLOTS, UV_SLOTS)
        POS_SLOTS, UV_SLOTS = (2, 3, 4), (0, 1)
        return lambda: _restore_slots(old)

    def _restore_slots(old):
        global POS_SLOTS, UV_SLOTS
        POS_SLOTS, UV_SLOTS = old

    def m_stray_byte():
        """Rewrite one byte OUTSIDE the position floats as well.

        The last byte of the record (padding in the ANIM tail) is chosen on
        purpose: it does not break the decode, so this mutation isolates T2a
        instead of merely crashing the walker somewhere else."""
        return _patch_scale(lambda buf: buf.__setitem__(len(buf) - 1,
                                                        buf[len(buf) - 1] ^ 0xFF))

    def m_length_field():
        """Rewrite the record's length-derived header field as well.

        The uint32 at offset 4 tracks the record length exactly (it is length +
        9240 in all twenty variants) but nothing in decode() validates it, so
        corrupting it isolates T3a cleanly instead of crashing the chunk walker
        the way a mangled vertex_count would."""
        return _patch_scale(lambda buf: buf.__setitem__(4, buf[4] ^ 0x01))

    def m_no_op():
        """Do not actually scale anything."""
        global scale_positions
        old = scale_positions
        scale_positions = lambda data, offsets, factor: bytes(data)
        return lambda: _restore_scale(old)

    def m_dir_stride_12():
        """Walk the compression directory at the old, wrong stride of 12."""
        old = dbpfcore.read_dir

        def bad(path, index=None):
            if index is None:
                index = dbpfcore.read_index(path)
            for (t, g, i, off, size) in index:
                if t == dbpfcore.DIR_TYPE:
                    with open(path, "rb") as f:
                        f.seek(off)
                        blob = f.read(size)
                    m = {}
                    for k in range(size // 12):
                        if k * 12 + 16 > size:
                            break
                        et, eg, ei, esz = struct.unpack_from("<IIII", blob, k * 12)
                        m[(et, eg, ei)] = esz
                    return m, (t, g, i)
            return {}, None

        dbpfcore.read_dir = bad
        _ARCS.clear()
        return lambda: (_restore_read_dir(old), _ARCS.clear())

    def _restore_read_dir(old):
        dbpfcore.read_dir = old

    def _restore_scale(old):
        global scale_positions
        scale_positions = old

    def _patch_scale(corrupt):
        global scale_positions
        old = scale_positions

        def bad(data, offsets, factor):
            buf = bytearray(old(data, offsets, factor))
            corrupt(buf)
            return bytes(buf)

        scale_positions = bad
        return lambda: _restore_scale(old)

    def m_ghost():
        """Make the loader hand back a variant for an instance that does not ship."""
        global load
        old = load

        def bad(instance, game=None):
            try:
                return old(instance, game=game)
            except (KeyError, ValueError):
                return old(FAMILY_BASE, game=game)

        load = bad
        return lambda: _restore_load(old)

    def _restore_load(old):
        global load
        load = old

    return [
        ("M1 wrong 3-of-5 position/UV split", m_split, "C5d"),
        ("M2 a byte rewritten outside the position floats", m_stray_byte, "T2a"),
        ("M3 a length/count field rewritten too", m_length_field, "T3a"),
        ("M4 the scale is a no-op", m_no_op, "T2b"),
        ("M5 compression directory walked at stride 12", m_dir_stride_12, "D0c"),
        ("M6 loader invents a variant that does not ship", m_ghost, "N1"),
    ]


def mutation_test(game=None, out=sys.stdout):
    import io
    p = lambda *a: print(*a, file=out)
    p("=== MUTATION HARNESS ===")
    p("Each row breaks ONE thing and names the control that must notice.")
    p("A control that stays green under its own mutation is decoration.\n")
    p("  %-52s %-8s %s" % ("mutation", "expects", "result"))
    bad = []
    for label, apply_mut, expect in _mutations():
        undo = apply_mut()
        try:
            sink = io.StringIO()
            try:
                c = self_test(game=game, out=sink)
                fired = [f for f in c.failures if f.startswith(expect)]
                got = "CAUGHT by %s (%d)" % (expect, len(fired)) if fired else \
                      "NOT CAUGHT -- %d other failure(s)" % len(c.failures)
                good = bool(fired)
            except Exception as e:
                # a mutation that makes the decode raise is also "caught", but
                # say so explicitly rather than counting it as a clean catch
                got = "raised %s: %s" % (type(e).__name__, str(e)[:60])
                good = True
        finally:
            undo()
            _ARCS.clear()
        p("  %-52s %-8s %s" % (label, expect, got))
        if not good:
            bad.append(label)
    p("\n  mutations that escaped: %d" % len(bad))
    for b in bad:
        p("  ESCAPED %s" % b)
    return not bad


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", default=GAME, help="SimCity 4 install root")
    ap.add_argument("--verbose", action="store_true",
                    help="print every vertex of every variant")
    ap.add_argument("--mutation", action="store_true",
                    help="also prove every control can fail (slow: reruns the "
                         "whole self-test once per mutation)")
    args = ap.parse_args(argv)
    c = self_test(game=args.game, verbose=args.verbose)
    ok = not c.failures
    if args.mutation:
        print("")
        ok = mutation_test(game=args.game) and ok
    print("\nRESULT: %s" % ("ALL CONTROLS PASS" if ok else "CONTROLS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
