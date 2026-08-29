#!/usr/bin/env python3
"""Stage the #202 SCAN-PREDICATE probe. One boot answers two engine questions
that gate the whole post-rename arming design.

WHY THIS EXISTS. Arming a tier by renaming files is the single reason sc4pac
cannot uninstall this mod cleanly. The replacement under consideration is a
CONTENT SWAP at a stable filename, with each tier's bytes shipped as an inert
payload file the game never loads. That rests on two engine facts nobody in
this tree has measured:

  Q1  IS THE PLUGIN SCAN GATED ON EXTENSION, OR ON DBPF MAGIC?
      `.dat.x1-disabled` being skipped proves ONE string is skipped. It is not
      proof about a DIFFERENT string. If the scan sniffs magic instead, every
      payload is a live plugin and the design is void on day one - three tiers
      of every package, plus every gated-off set, permanently in the index.

  Q2  DOES A ONE-ENTRY DBPF LOAD CLEANLY AND CONTEST NOTHING?
      A gated-off package needs a live file that declares no contested TGI.
      Build-Dist.ps1 hard-throws on shipping a content-free file at a live name
      (#182: an empty FontStyle.ini got snapshotted as the user's original and
      the game took an ACCESS_VIOLATION), so "empty" is not an option - it has
      to be one entry at a TGI nothing else owns.

RUN THIS, THEN LAUNCH THE GAME ONCE, THEN RUN Read-Probe.  The arming path is
NOT touched: this stages two inert files beside the live ones and reads the
SegmentCensus output the DLL already knows how to write.

    python _tests\\Probe-ScanPredicate.py --stage
    ... launch SimCity 4, reach the region screen, quit ...
    python _tests\\Probe-ScanPredicate.py --read
    python _tests\\Probe-ScanPredicate.py --clean
"""

import argparse
import os
import struct
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_PLUGINS = os.path.join(
    os.environ.get("USERPROFILE", ""), "OneDrive", "Documents", "SimCity 4", "Plugins")
OUR_DIR = os.path.join(DOCS_PLUGINS, "010-SC4UIScale")
DBPF_PACK = os.path.join(REPO, "tools", "dbpf", "DbpfPack.exe")

PROBE_PAYLOAD = "z_SC4UIScale_PROBE.uipay"     # must NOT be scanned
PROBE_OFF = "z_SC4UIScale_PROBEOFF.dat"        # must be scanned, contest nothing
LOG = os.path.join(OUR_DIR, "SC4UIScale.log")

DBPF_EXTS = (".dat", ".sc4desc", ".sc4model", ".sc4lot", ".dll")


def read_index(path):
    """Every TGI in one DBPF v1.x archive. Returns a set, or None if unparsable.

    Header layout verified against retail SimCity_1.dat - see
    tools/dbpf/NOTES-PACK.md.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(96)
            if len(head) < 96 or head[:4] != b"DBPF":
                return None
            count, off, size = struct.unpack_from("<III", head, 0x24)
            if count == 0 or size == 0:
                return set()
            stride = size // count
            if stride < 20:
                return None
            f.seek(off)
            raw = f.read(size)
        out = set()
        for i in range(count):
            t, g, inst = struct.unpack_from("<III", raw, i * stride)
            out.add((t, g, inst))
        return out
    except (OSError, struct.error):
        return None


def merged_index(trees):
    """Every TGI the game can currently see, plus a parse census.

    POSITIVE CONTROL: the caller must assert this is large and that `unparsed`
    is small. A tiny index would make "this TGI is absent" true for the wrong
    reason - the absence has to come from looking, not from failing to look.
    """
    keys = set()
    parsed = unparsed = 0
    for tree in trees:
        if not tree or not os.path.isdir(tree):
            continue
        for root, _dirs, files in os.walk(tree):
            for name in files:
                if not name.lower().endswith(DBPF_EXTS):
                    continue
                idx = read_index(os.path.join(root, name))
                if idx is None:
                    unparsed += 1
                else:
                    parsed += 1
                    keys |= idx
    return keys, parsed, unparsed


def game_trees():
    """The game's own Plugins folder and its archive directory, if findable."""
    for base in (
        r"C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe",
        r"C:\Program Files (x86)\Maxis\SimCity 4 Deluxe",
    ):
        if os.path.isdir(base):
            return [os.path.join(base, "Plugins"), base]
    return []


def pick_absent_tgi(keys):
    """A TGI in our own art type/group space that nothing currently owns.

    Walks upward from a fixed instance so the answer is deterministic rather
    than random - a probe that picks a different key each run cannot be
    compared against its own previous result.
    """
    t, g = 0x856DDBAC, 0x6A386D26
    for inst in range(0x5C4B0000, 0x5C4BFFFF):
        if (t, g, inst) not in keys:
            return t, g, inst
    raise SystemExit("no free instance in the probe range - widen the search")


def stage():
    if not os.path.isdir(OUR_DIR):
        raise SystemExit("our package folder not found: %s" % OUR_DIR)

    trees = [DOCS_PLUGINS] + game_trees()
    keys, parsed, unparsed = merged_index(trees)
    print("merged index: %d TGI(s) from %d archive(s); %d unparsable"
          % (len(keys), parsed, unparsed))
    # POSITIVE CONTROL. Without this an "absent" TGI could just mean the scan
    # read nothing, which is the false-zero this project has shipped twice.
    if parsed < 50 or len(keys) < 50000:
        raise SystemExit(
            "REFUSING: the index census looks too small (%d archives, %d keys). "
            "An 'absent' TGI would be absent because we failed to look, not "
            "because nothing owns it." % (parsed, len(keys)))

    t, g, inst = pick_absent_tgi(keys)
    print("probe TGI chosen (verified ABSENT from all %d): "
          "T=%08X G=%08X I=%08X" % (len(keys), t, g, inst))

    # Q2 subject: a one-entry DBPF at that TGI.
    tmp = tempfile.mkdtemp(prefix="probeoff-")
    entry = os.path.join(tmp, "T-0x%08X_G-0x%08X_I-0x%08X.bin" % (t, g, inst))
    with open(entry, "wb") as f:
        f.write(b"SC4UIScale probe #202 - one inert entry, owns nothing else.")
    out = os.path.join(OUR_DIR, PROBE_OFF)
    r = subprocess.run([DBPF_PACK, tmp, out], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(out):
        raise SystemExit("DbpfPack failed: %s%s" % (r.stdout, r.stderr))
    print("staged %s (%d bytes, 1 entry)" % (PROBE_OFF, os.path.getsize(out)))

    # Q1 subject: a real DBPF under a non-canonical extension.
    src = None
    for name in sorted(os.listdir(OUR_DIR)):
        if name.startswith("z_SC4UIScale_") and name.endswith(".dat") \
                and not name.startswith("z_SC4UIScale_PROBE"):
            src = os.path.join(OUR_DIR, name)
            break
    if not src:
        raise SystemExit("no live package to copy as the payload probe")
    dst = os.path.join(OUR_DIR, PROBE_PAYLOAD)
    with open(src, "rb") as a, open(dst, "wb") as b:
        b.write(a.read())
    print("staged %s (a byte-for-byte copy of %s - REAL DBPF content under a "
          "non-canonical extension)" % (PROBE_PAYLOAD, os.path.basename(src)))

    ini = os.path.join(OUR_DIR, "SC4UIScale.ini")
    with open(ini, "r", encoding="utf-8-sig") as f:
        txt = f.read()
    if "SegmentCensus=1" not in txt:
        txt = txt.replace("SegmentCensus=0", "SegmentCensus=1")
        with open(ini, "w", encoding="utf-8", newline="") as f:
            f.write(txt)
    print("armed [Probe] SegmentCensus=1")
    print()
    print("NOW: launch SimCity 4, reach the REGION screen, quit. Then --read.")


def read():
    if not os.path.exists(LOG):
        raise SystemExit("no log at %s" % LOG)
    with open(LOG, "r", encoding="utf-8", errors="replace") as f:
        lines = [l for l in f if "SEGCENSUS" in l]
    if not lines:
        raise SystemExit("no SEGCENSUS lines - was SegmentCensus=1 armed, and "
                         "did the game reach PostAppInit? Nothing measured.")

    ours = [l for l in lines if "z_SC4UIScale_" in l]
    payload_seen = any(PROBE_PAYLOAD in l for l in lines)
    off_seen = any(PROBE_OFF in l for l in lines)

    print("SEGCENSUS lines: %d, naming our files: %d" % (len(lines), len(ours)))
    # POSITIVE CONTROL FIRST. A census that lists none of ours proves nothing
    # about what it omits.
    if len(ours) < 3:
        raise SystemExit(
            "CONTROL FAILED: the census named %d of our files. It cannot be "
            "used as evidence that it did NOT name the payload." % len(ours))
    print("CONTROL PASSED: the census demonstrably sees our files, so an "
          "absence in it is real evidence.")
    print()
    print("Q1  scan predicate : %s"
          % ("MAGIC-GATED - .uipay WAS scanned. The payload design is VOID."
             if payload_seen else
             "EXTENSION-GATED - .uipay was NOT scanned. Payload extension is safe."))
    print("Q2  one-entry DBPF : %s"
          % ("loaded (appears as a child)" if off_seen else
             "NOT loaded - a one-entry archive did not register; the .off "
             "payload shape needs rethinking."))
    print()
    print("Q2 also needs your eyes: did the game reach the region screen "
          "normally this boot? A one-entry archive that loads but destabilises "
          "the game fails Q2 just as surely as one that never loads.")


def clean():
    n = 0
    for name in (PROBE_PAYLOAD, PROBE_OFF):
        p = os.path.join(OUR_DIR, name)
        if os.path.exists(p):
            os.remove(p)
            n += 1
    ini = os.path.join(OUR_DIR, "SC4UIScale.ini")
    if os.path.exists(ini):
        with open(ini, "r", encoding="utf-8-sig") as f:
            txt = f.read()
        txt = txt.replace("SegmentCensus=1", "SegmentCensus=0")
        with open(ini, "w", encoding="utf-8", newline="") as f:
            f.write(txt)
    print("removed %d probe file(s); SegmentCensus disarmed" % n)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", action="store_true")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--clean", action="store_true")
    a = ap.parse_args()
    if a.stage:
        stage()
    elif a.read:
        read()
    elif a.clean:
        clean()
    else:
        ap.print_help()
        sys.exit(2)
