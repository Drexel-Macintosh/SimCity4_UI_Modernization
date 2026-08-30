"""common.py - shared plumbing for the SC4 offline UI model (STAGE 1+2).

Everything here is READ-ONLY with respect to the game: the exe is opened
'rb' and never written. All derived data lands under tools\\uimap\\.

Mapping: SimCity 4.exe 1.1.641.0 Steam, ImageBase 0x400000, and for
.text/.rdata/.data the section header proves file offset == VA - 0x400000
(see pe_probe.py output recorded in BUILDER-CENSUS.md).

RESUMABILITY
------------
`State` is a tiny manifest of work units persisted to tools\\uimap\\state.json.
Every stage marks each unit done IMMEDIATELY after finishing it (atomic
replace), so an interruption loses at most one unit. Re-running without
--resume simply redoes everything; every stage is idempotent.

EXE FINGERPRINT  (audit 2026-08-02)
-----------------------------------
Every persisted unit describes BYTES AT A VA in one particular build of
SimCity 4.exe. Until 2026-08-02 nothing recorded WHICH build, so a Steam
patch - or pointing EXE at a different install - would let a --resume run
report hundreds of units 'done' while the addresses underneath had moved.
That is the same class of silent-stale failure as the #58 ThirdPartyUI dat.
The state file now carries sha256(exe)[:16] + the exe byte size, and a
mismatch (or an unstamped legacy file) makes the manifest STALE: units are
archived, never reused, and --resume refuses to run at all.
"""
import hashlib
import json
import os
import struct
import sys
import time
from bisect import bisect_right

def _resolve_exe():
    """The game binary, resolved rather than hard-coded.

    $SC4_EXE wins; otherwise tools\\sc4paths.py finds the install ($SC4_GAME_DIR
    or the usual locations); the Steam default is the last resort so an
    existing setup keeps working. A hard-coded absolute path here was a
    cold-clone trap: anyone whose install sits elsewhere had to edit source
    before a single tool would run.
    """
    env = os.environ.get("SC4_EXE")
    if env:
        return env
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        from sc4paths import exe_path           # noqa: E402
        p = exe_path()
        if p and os.path.isfile(p):
            return p
    except Exception:
        pass
    return (r"C:\Program Files (x86)\Steam\steamapps\common"
            r"\SimCity 4 Deluxe\Apps\SimCity 4.exe")


EXE = _resolve_exe()
# What the persisted JSONs record as provenance. The FINGERPRINT (sha256[:16]
# + byte size) is the identity every gate actually checks; the full path adds
# nothing to that and differs per machine, so only the file name travels.
EXE_PROVENANCE = os.path.basename(EXE)
IMAGE_BASE = 0x400000

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "_work")
STATE_PATH = os.path.join(HERE, "state.json")

SHARD = 0x10000  # 64 KB of .text per work unit


# --------------------------------------------------------------------------
# exe / PE
# --------------------------------------------------------------------------
_data = None


def exe_bytes():
    global _data
    if _data is None:
        with open(EXE, "rb") as f:
            _data = f.read()
    return _data


_fp = None


def exe_fingerprint():
    """(sha256(exe)[:16], byteSize) of the exe every derived file describes.

    16 hex chars = 64 bits: far past collision risk for 'is this the same
    build?', and short enough to eyeball in a state file. Size is carried
    alongside because it is free and catches a truncated/locked read that
    would otherwise hash to a plausible-looking value.

    ⚠ THE LAA BIT IS MASKED OUT BEFORE HASHING (2026-08-05). Applying the
    "4GB patch" sets IMAGE_FILE_LARGE_ADDRESS_AWARE (0x0020) in the PE COFF
    Characteristics word - ONE BIT, in a header field, that cannot change a
    single instruction. Without the mask it changed the whole-file hash, and
    every exe-pinned gate in this repo went from GREEN to "FAIL: fingerprint
    mismatch" at once, with nothing announcing why. Three of them were
    re-run and refused to speak before the cause was found.

    Masking rather than re-pinning is deliberate: every pin in this repo was
    derived when the bit was 0, so masking keeps ALL existing pins valid and
    makes them immune to the flip in both directions (patch and -Undo). If a
    future patch touches anything else in the header, the hash still moves,
    which is what a fingerprint is for.
    """
    global _fp
    if _fp is None:
        d = bytearray(exe_bytes())
        pe = struct.unpack_from("<I", d, 0x3C)[0]
        cofs = pe + 4 + 18                      # COFF header + Characteristics
        ch = struct.unpack_from("<H", d, cofs)[0]
        struct.pack_into("<H", d, cofs, ch & ~0x0020)
        _fp = (hashlib.sha256(bytes(d)).hexdigest()[:16], len(d))
    return _fp


def sections():
    """[(name, vaLo, vaHi, fileOff, rawSize)] from the PE section table."""
    d = exe_bytes()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    optsz = struct.unpack_from("<H", d, pe + 20)[0]
    base = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    out = []
    so = pe + 24 + optsz
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vsz, va, rsz, ro = struct.unpack_from("<IIII", d, o + 8)
        out.append((name, base + va, base + va + vsz, ro, rsz))
    return out


def _sec(name):
    for s in sections():
        if s[0] == name:
            return s
    raise KeyError(name)


TEXT_NAME, TEXT_LO, TEXT_HI, TEXT_OFF, TEXT_RAW = _sec(".text")
RDATA_NAME, RDATA_LO, RDATA_HI, RDATA_OFF, RDATA_RAW = _sec(".rdata")
DATA_NAME, DATA_LO, DATA_HI, DATA_OFF, DATA_RAW = _sec(".data")

# The 1:1 identity the whole project relies on. Asserted, not assumed.
assert TEXT_LO - TEXT_OFF == IMAGE_BASE, "text mapping is not VA-0x400000"
assert RDATA_LO - RDATA_OFF == IMAGE_BASE
assert DATA_LO - DATA_OFF == IMAGE_BASE


def va_ok(va):
    return TEXT_LO <= va < TEXT_HI


def rd(va, n):
    """n bytes at VA (text/rdata/data share the VA-0x400000 mapping)."""
    off = va - IMAGE_BASE
    return exe_bytes()[off:off + n]


def dw(va):
    b = rd(va, 4)
    if len(b) < 4:
        return None
    return struct.unpack("<I", b)[0]


def text_blob():
    return exe_bytes()[TEXT_OFF:TEXT_OFF + (TEXT_HI - TEXT_LO)]


# --------------------------------------------------------------------------
# capstone
# --------------------------------------------------------------------------
def md():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    m = Cs(CS_ARCH_X86, CS_MODE_32)
    m.detail = True
    return m


# --------------------------------------------------------------------------
# resumable state
# --------------------------------------------------------------------------
class State(object):
    """Work-unit manifest. Keys are '<stage>/<unit>' -> dict(status=..., ...).

    status is one of: pending | done | failed

    The manifest is only meaningful for the exe it was built from, so it is
    stamped with exe_fingerprint(). A file whose stamp is missing (written
    before 2026-08-02) or different is STALE: its units are archived under
    'unitsStale' and the run starts from an empty manifest. We archive rather
    than delete because the manifest doubles as the record of which .text
    shards were ever scanned - evidence worth keeping when diagnosing why the
    fingerprint moved.
    """

    def __init__(self, path=STATE_PATH):
        self.path = path
        sha, size = exe_fingerprint()
        fresh = {"version": 2, "exe": EXE_PROVENANCE, "exeSha256_16": sha,
                 "exeSize": size, "units": {}, "notes": {}}
        self.d = dict(fresh)
        self.stale = False
        self.stale_reason = ""
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.d = json.load(f)
            except Exception:
                pass
            got_sha = self.d.get("exeSha256_16")
            got_size = self.d.get("exeSize")
            if got_sha is None or got_size is None:
                self.stale = True
                self.stale_reason = ("written before the exe fingerprint "
                                     "existed (no exeSha256_16 in the file)")
            elif (got_sha, got_size) != (sha, size):
                self.stale = True
                self.stale_reason = (
                    "built from a DIFFERENT exe: state says %s/%d bytes, "
                    "the exe on disk is %s/%d bytes"
                    % (got_sha, got_size, sha, size))
            if self.stale:
                old = self.d.get("units", {})
                self.d = dict(fresh)
                self.d["unitsStale"] = old
                self.d["staleReason"] = self.stale_reason
                # Every stage builds C.State() BEFORE it consults st.done()
                # (build_funcs.py:100, census.py:186, constants.py:142), so
                # this single check covers all of them without each stage
                # having to remember to ask. Refusing here is the point: a
                # --resume over a stale manifest is the failure mode we are
                # closing, not something to warn about and continue.
                if "--resume" in sys.argv:
                    sys.stderr.write(
                        "\n*** STALE STATE - REFUSING TO --resume ***\n"
                        "  %s\n  %s\n"
                        "  Every 'done' unit in it describes bytes at VAs in "
                        "a build this file cannot vouch for.\n"
                        "  Re-run this command WITHOUT --resume (every stage "
                        "is idempotent).\n\n" % (path, self.stale_reason))
                    sys.exit(2)
                sys.stderr.write(
                    "[state] ignoring stale manifest (%s); starting fresh\n"
                    % self.stale_reason)
        self.d.setdefault("units", {})
        self.d.setdefault("notes", {})
        # Always re-stamp: from here on the file only ever describes THIS exe.
        self.d["exe"] = EXE_PROVENANCE
        self.d["exeSha256_16"] = sha
        self.d["exeSize"] = size

    def status(self, stage, unit):
        return self.d["units"].get("%s/%s" % (stage, unit), {}).get("status", "pending")

    def done(self, stage, unit):
        return self.status(stage, unit) == "done"

    def mark(self, stage, unit, status, **info):
        rec = {"status": status, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        rec.update(info)
        self.d["units"]["%s/%s" % (stage, unit)] = rec
        self.flush()

    def note(self, key, value):
        self.d["notes"][key] = value
        self.flush()

    def reset_stage(self, stage):
        pre = stage + "/"
        for k in [k for k in self.d["units"] if k.startswith(pre)]:
            del self.d["units"][k]
        self.flush()

    def counts(self, stage=None):
        out = {}
        for k, v in self.d["units"].items():
            if stage and not k.startswith(stage + "/"):
                continue
            out[v.get("status", "pending")] = out.get(v.get("status", "pending"), 0) + 1
        return out

    def flush(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.d, f, indent=1)
        os.replace(tmp, self.path)


def ensure_work(*parts):
    p = os.path.join(WORK, *parts) if parts else WORK
    os.makedirs(p, exist_ok=True)
    return p


def jdump(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def jload(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def hexs(v):
    return "0x%X" % v


# --------------------------------------------------------------------------
# function map helpers (produced by build_funcs.py, consumed by later stages)
# --------------------------------------------------------------------------
class FuncMap(object):
    def __init__(self, path=None):
        path = path or os.path.join(HERE, "funcs.json")
        j = jload(path)
        if j is None:
            raise SystemExit("funcs.json missing - run build_funcs.py first")
        self.starts = j["starts"]           # sorted list of ints
        self.meta = {int(k): v for k, v in j["meta"].items()}

    def owner(self, va):
        i = bisect_right(self.starts, va) - 1
        if i < 0:
            return None
        return self.starts[i]

    def end(self, start):
        i = bisect_right(self.starts, start)
        return self.starts[i] if i < len(self.starts) else TEXT_HI
