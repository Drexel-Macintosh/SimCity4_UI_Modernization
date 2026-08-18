#!/usr/bin/env python3
"""
parse_log.py - turn any SC4UIScale.log into a structured WINDOW CENSUS.

STAGE 4 of the offline UI model (tools\\research\\METHOD.md section 6). The
census is the machine-readable form of source 2 of 3 - the LIVE oracle.
diff.py joins it against the PREDICTED model (tools\\uimap\\) and the STOCK
reference.

  METHOD.md rule: "the model is never the authority - the live dump is."
  Everything this file emits is MEASURED. Nothing here is inference.

------------------------------------------------------------------------------
LINE GRAMMAR - transcribed from the printf sites in src\\UiSpike.cpp, NOT
guessed. (src is READ ONLY; the VAs below are line numbers as of v2.27.3.)
------------------------------------------------------------------------------
Every line is prefixed by Logger::WriteLine's stamp "[HH:MM:SS.mmm] "
(Logger.cpp:87). The banner line (file line 1) carries NO stamp.

  UiSpike.cpp:6884  MWKID  %2d      id=0x%08X vt=%p (%d,%d %dx%d) vis=%d
  UiSpike.cpp:6899  MWKID  %2d.%-2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d
  UiSpike.cpp:6916  POPKID %d       id=0x%08X vt=%p (%d,%d %dx%d) vis=%d
  UiSpike.cpp:6930  POPKID %d.%-2d  id=0x%08X vt=%p (%d,%d %dx%d) vis=%d
  UiSpike.cpp:7101  BHDR instance %d dlg (%d,%d %dx%d) pane children=%d
  UiSpike.cpp:7109  BHDR   %2d      id=0x%08X vt=%p (%d,%d %dx%d) vis=%d
  UiSpike.cpp:7124  BHDR   %2d.%-2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d
  UiSpike.cpp:7244  VWKID  %2d      id=0x%08X vt=%p (%d,%d %dx%d)        <-- no vis
  UiSpike.cpp:7476  RGKID  %2d      id=0x%08X vt=%p (%d,%d %dx%d)        <-- no vis
  UiSpike.cpp:7486  RGKID  %2d.%-2d id=0x%08X vt=%p (%d,%d %dx%d) vis=%d
  UiSpike.cpp:7506  RGKID  %2d.%d.%-2d    ... vis=%d
  UiSpike.cpp:7517  RGKID  %2d.%d.%d.%-2d ... vis=%d
  UiSpike.cpp:6297  DGPKID %d id=%08X L=%d T=%d W=%d H=%d vis=%d[ <==CONTAINER][ **OVER-DEAD-BAND**]
                          ^^ NOTE: no 0x prefix on this one instrument.
  UiSpike.cpp:6280  DGP-OPEN godParent has %d children, container=idx %d rect(%d,%d %dx%d)
  UiSpike.cpp:5093  DPROBE ptr%p d%d id=0x%08X par=0x%08X #%d abs(%d,%d) %dx%d vis=%d[ NEW]
  UiSpike.cpp:4988  MPROBE id=0x%08X abs(%d,%d) %dx%d vis=%d vt=%p[ NEW]
  UiSpike.cpp:5013  TPROBE d%d id=0x%08X abs(%d,%d) %dx%d vis=%d vt=%p
  UiSpike.cpp:7725  UI %*sid=0x%08X pos(%d,%d) size(%dx%d) children=%d vis=%d en=%d
                          ^^ the BOOT / LiveDump full tree. %*s width = depth*2.
  UiSpike.cpp:7211  POPFIT body (%d,%d %dx%d) -> popup %dx%d

SCALE EVENTS - the strongest single source in the whole log, and the reason
this parser is worth more than a grep. These lines carry the BEFORE and the
AFTER rect of the same window in the same line, at the same render resolution:

  UiSpike.cpp:6567  panel 0x%08X (%d,%d %dx%d) -> (%d,%d %dx%d)[ note]
  UiSpike.cpp:6846  in-city dialog 0x%08X scaled (%d,%d %dx%d) -> %dx%d, %d descendants, %d imagerects x%.2f
  (dialog form)     dialog 0x%08X scaled (%d,%d %dx%d) -> %dx%d, %d descendants.
  UiSpike.cpp:7811  font-sized 0x%08X pos (%d,%d)->(%d,%d), size %dx%d kept.
  UiSpike.cpp:6489  panel 0x%08X target %dx%d exceeds frame %dx%d - SKIPPED ...
  (window form)     window 0x%08X target %dx%d exceeds frame - skipped and tombstoned.

The BEFORE rect on a `panel` line is the geometry the GAME laid down, i.e.
STOCK at the live resolution, and the AFTER is what we made of it. That
sidesteps the whole cross-resolution problem: a stock capture taken at
1024x768 cannot be compared position-for-position against a 2400x1600 run,
but a `panel` line needs no second source at all.

THE TWO SIZE LAWS (both transcribed from source; the diff models both):
  edge-derived (the runtime SWEEP, UiSpike.cpp:6478):
      newW = ScaleRound(l + w, f) - ScaleRound(l, f),  ScaleRound = llround
  direct (the DATA generators, build_selective_safe.py:74 / build_dialog_static.py:124):
      newW = scale_len(w) = floor(w * f + 0.5)
They are identical for INTEGER f (2x, 3x) and can differ by one pixel at
1.5x. That is exactly the trap SCENARIOS.md AXIS 1 warns about ("1.5x is
where rounding bugs hide, 2x hides them"), and it is provable offline.

TWO COORDINATE SPACES - the single most important thing this parser records.
  * every KID instrument and the UI tree print GetL()/GetT(), which are
    PARENT-RELATIVE.
  * DPROBE prints the accumulated ax/ay, which are ABSOLUTE (screen).
Mixing them silently is how a diff harness invents defects, so every record
carries coord="rel" or coord="abs" and diff.py refuses to cross them.

PARENT DERIVATION (what is derivable, and what is not):
  MWKID i      -> the MAIN WINDOW           (synthetic id "@MAINWIN")
  MWKID i.j    -> the id printed at MWKID i in the same block
  POPKID q     -> 0x0423278D                (the shared text popup; the dump
                  only fires from inside that id's branch, UiSpike.cpp:6907)
  POPKID q.r   -> the id printed at POPKID q
  BHDR i       -> 0x0423278E                (the budget content PANE)
  BHDR i.j     -> the id printed at BHDR i
  VWKID i      -> the 3D VIEW               (synthetic id "@VIEW")
  RGKID i      -> the REGION screen         (synthetic id "@REGION")
  RGKID i.j... -> the id printed at the parent path in the same block
  DGPKID j     -> the god flyout parent     (synthetic id "@GODPARENT")
  DPROBE       -> par=0x........            (printed explicitly - authoritative)
  UI tree      -> indentation stack         (authoritative)

BLOCKS. Every KID instrument is a CHANGE-ONLY dump: one whole enumeration is
written per firing. A block boundary is declared when (a) the instrument's
top-level index fails to strictly increase, or (b) the stamp jumps >= 1000 ms,
or (c) for BHDR, a new "instance" header appears. That rule is deterministic
and needs no lookahead, so a truncated log parses the same as a whole one.

TOLERANCE. Unknown lines are counted, never fatal. A half-written final line
(the game was killed mid-flush) simply fails the regex and lands in
unknown_lines. No line type is required to be present.

USAGE
    python parse_log.py LOG [LOG...] --out DIR [--full] [--json-only]
    python parse_log.py --help

Output: one <stem>.census.json per input, plus a printed summary.
Deterministic: identical input bytes -> identical output bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

SCHEMA = "sc4-uimap-diff/census/1"

# ---------------------------------------------------------------- line grammar

TS_RE = re.compile(r"^\[(\d{2}):(\d{2}):(\d{2})\.(\d{3})\]\s?")

# MWKID / VWKID / BHDR / POPKID / RGKID all share one shape. vis= is absent on
# the top-level VWKID and RGKID lines (see the transcription above), so it is
# optional here rather than in five near-identical patterns.
KID_RE = re.compile(
    r"UiSpike:\s+(MWKID|VWKID|BHDR|POPKID|RGKID)\s+"
    r"(\d+(?:\.\d+)*)\s+"
    r"id=0x([0-9A-Fa-f]{8})\s+"
    r"vt=([0-9A-Fa-f]+)\s+"
    r"\((-?\d+),(-?\d+)\s+(-?\d+)x(-?\d+)\)"
    r"(?:\s+vis=(\d))?"
)

BHDR_HDR_RE = re.compile(
    r"UiSpike:\s+BHDR instance (\d+) dlg "
    r"\((-?\d+),(-?\d+)\s+(-?\d+)x(-?\d+)\) pane children=(\d+)"
)

DGPKID_RE = re.compile(
    r"UiSpike:\s+DGPKID (\d+) id=([0-9A-Fa-f]{8}) "
    r"L=(-?\d+) T=(-?\d+) W=(-?\d+) H=(-?\d+) vis=(\d)(.*)$"
)

DGPOPEN_RE = re.compile(
    r"UiSpike:\s+DGP-OPEN godParent has (\d+) children, container=idx (\d+) "
    r"rect\((-?\d+),(-?\d+)\s+(-?\d+)x(-?\d+)\)"
)

DPROBE_RE = re.compile(
    r"UiSpike:\s+DPROBE ptr([0-9A-Fa-f]+) d(\d+) "
    r"id=0x([0-9A-Fa-f]{8}) par=0x([0-9A-Fa-f]{8}) #(-?\d+) "
    r"abs\((-?\d+),(-?\d+)\)\s+(-?\d+)x(-?\d+) vis=(\d)(\s+NEW)?"
)

# "UI %*sid=..." - width is depth*2, so at depth 0 there is NO padding at all.
TREE_RE = re.compile(
    r"^UI (\s*)id=0x([0-9A-Fa-f]{8}) pos\((-?\d+),(-?\d+)\) "
    r"size\((-?\d+)x(-?\d+)\) children=(\d+) vis=(-?\d+) en=(-?\d+)"
)

POPFIT_RE = re.compile(
    r"UiSpike:\s+POPFIT body \((-?\d+),(-?\d+)\s+(-?\d+)x(-?\d+)\) "
    r"-> popup (-?\d+)x(-?\d+)"
)

MPROBE_RE = re.compile(
    r"UiSpike:\s+MPROBE id=0x([0-9A-Fa-f]{8}) abs\((-?\d+),(-?\d+)\)\s+"
    r"(-?\d+)x(-?\d+) vis=(\d) vt=([0-9A-Fa-f]+)(\s+NEW)?"
)

TPROBE_RE = re.compile(
    r"UiSpike:\s+TPROBE d(\d+) id=0x([0-9A-Fa-f]{8}) abs\((-?\d+),(-?\d+)\)\s+"
    r"(-?\d+)x(-?\d+) vis=(\d) vt=([0-9A-Fa-f]+)"
)

# ---- scale events (before -> after in one line) ------------------------------
PANEL_RE = re.compile(
    r"UiSpike:\s+panel 0x([0-9A-Fa-f]{8}) "
    r"\((-?\d+),(-?\d+)\s+(-?\d+)x(-?\d+)\)\s+->\s+"
    r"\((-?\d+),(-?\d+)\s+(-?\d+)x(-?\d+)\)(.*)$"
)

DLGSCALED_RE = re.compile(
    r"UiSpike:\s+(?:(in-city) )?dialog 0x([0-9A-Fa-f]{8}) scaled "
    r"\((-?\d+),(-?\d+)\s+(-?\d+)x(-?\d+)\)\s+->\s+(-?\d+)x(-?\d+), "
    r"(\d+) descendants"
)

FONTSIZED_RE = re.compile(
    r"UiSpike:\s+font-sized 0x([0-9A-Fa-f]{8}) pos "
    r"\((-?\d+),(-?\d+)\)->\((-?\d+),(-?\d+)\), size (-?\d+)x(-?\d+) kept"
)

TOMBSTONE_RE = re.compile(
    r"UiSpike:\s+(?:panel|window) 0x([0-9A-Fa-f]{8}) target (-?\d+)x(-?\d+) "
    r"exceeds frame(?: (-?\d+)x(-?\d+))? - SKIPPED|"
    r"UiSpike:\s+(?:panel|window) 0x([0-9A-Fa-f]{8}) target (-?\d+)x(-?\d+) "
    r"exceeds frame(?: (-?\d+)x(-?\d+))? - skipped"
)

FLYOUT_RE = re.compile(
    r"UiSpike:\s+(god|mayor) flyout 0x([0-9A-Fa-f]{8}) at\((-?\d+),(-?\d+)\) "
    r"size (-?\d+)x(-?\d+), \+(\d+) win"
)

BANNER_RE = re.compile(r"^SC4UIScale (v\S+)")
SETTINGS_RE = re.compile(
    r"Settings:\s+ScaleAll=(\d)\s+ScaleRegion=(\d)\s+MenuFlyouts=(\d)\s+"
    r"factor=([\d.]+)\s+scaling=(\d)"
)
RENDERRES_RE = re.compile(r"AutoScale:.*render res = \w+ (\d+)x(\d+)")
TIER_RE = re.compile(r"AutoScale:\s+(\d+)x(\d+)\s+->\s+tier ([\d.]+)\s+\((.*?)\)")

# Synthetic parents for the roots each instrument enumerates from. They are
# NOT window ids; the "@" prefix makes that impossible to confuse with one.
ROOT_OF = {
    "MWKID": "@MAINWIN",
    "VWKID": "@VIEW",
    "RGKID": "@REGION",
    "BHDR": "0x0423278E",   # the budget content PANE (UiSpike.cpp:7032)
    "POPKID": "0x0423278D",  # the shared text popup (UiSpike.cpp:6907)
}

BLOCK_GAP_MS = 1000


def _ms(h: int, m: int, s: int, ms: int) -> int:
    return ((h * 60 + m) * 60 + s) * 1000 + ms


def _hexid(v: str) -> str:
    return "0x" + v.upper().rjust(8, "0")


class _Blocker:
    """Deterministic single-pass block splitter (see BLOCKS in the docstring)."""

    def __init__(self) -> None:
        self._last_top: dict[str, int] = {}
        self._last_ms: dict[str, int] = {}
        self._block: dict[str, int] = {}

    def index(self, instr: str, top: int, tms: int | None) -> int:
        prev_top = self._last_top.get(instr)
        prev_ms = self._last_ms.get(instr)
        new = prev_top is None
        if not new and top <= prev_top:
            new = True
        if (not new and tms is not None and prev_ms is not None
                and tms - prev_ms >= BLOCK_GAP_MS):
            new = True
        if new:
            self._block[instr] = self._block.get(instr, -1) + 1
        self._last_top[instr] = top
        if tms is not None:
            self._last_ms[instr] = tms
        return self._block[instr]

    def force_new(self, instr: str) -> int:
        self._block[instr] = self._block.get(instr, -1) + 1
        self._last_top.pop(instr, None)
        self._last_ms.pop(instr, None)
        return self._block[instr]

    def current(self, instr: str) -> int:
        return self._block.get(instr, 0)


def parse_log(path: str) -> dict:
    """Parse one log into a census dict. Streams; never loads the file whole."""
    meta: dict = {
        "version": None, "settings": None, "render_res": None,
        "tier": None, "tier_note": None,
    }
    counts: dict[str, int] = {}
    unknown = 0
    total = 0
    records: list[dict] = []
    events: list[dict] = []
    blocker = _Blocker()

    # Per-instrument, per-block map: path -> id, for parent derivation.
    seen_paths: dict[tuple[str, int], dict[str, str]] = {}
    # BHDR carries a dialog rect per instance header.
    bhdr_instances: list[dict] = []
    tree_stack: list[tuple] = []   # (depth, id, eff_vis, hidden_ancestors)
    dprobe_blk: int | None = None
    dprobe_ms: int | None = None

    h = hashlib.sha256()
    with open(path, "rb") as raw:
        for chunk in iter(lambda: raw.read(1 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            total += 1
            line = line.rstrip("\r\n")
            if not line:
                continue

            tms = None
            ts = None
            m = TS_RE.match(line)
            if m:
                ts = f"{m.group(1)}:{m.group(2)}:{m.group(3)}.{m.group(4)}"
                tms = _ms(*(int(g) for g in m.groups()))
                body = line[m.end():]
            else:
                body = line

            # ---- metadata -------------------------------------------------
            if meta["version"] is None:
                mm = BANNER_RE.match(body)
                if mm:
                    meta["version"] = mm.group(1)
                    continue
            if body.startswith("Settings:"):
                mm = SETTINGS_RE.search(body)
                if mm:
                    meta["settings"] = {
                        "ScaleAll": int(mm.group(1)),
                        "ScaleRegion": int(mm.group(2)),
                        "MenuFlyouts": int(mm.group(3)),
                        "factor": float(mm.group(4)),
                        "scaling": int(mm.group(5)),
                    }
                    continue
            if body.startswith("AutoScale:"):
                mm = RENDERRES_RE.search(body)
                if mm:
                    meta["render_res"] = [int(mm.group(1)), int(mm.group(2))]
                    continue
                mm = TIER_RE.search(body)
                if mm:
                    meta["render_res"] = [int(mm.group(1)), int(mm.group(2))]
                    meta["tier"] = float(mm.group(3))
                    meta["tier_note"] = mm.group(4)
                    continue

            # ---- KID family ----------------------------------------------
            mm = KID_RE.search(body)
            if mm:
                instr = mm.group(1)
                pathtok = mm.group(2)
                parts = pathtok.split(".")
                top = int(parts[0])
                # Only a TOP-LEVEL line can open a block. Child lines share
                # their parent's block or the path->id table they need for
                # parent derivation is thrown away between "0" and "0.0".
                if len(parts) == 1:
                    blk = blocker.index(instr, top, tms)
                else:
                    blk = blocker.current(instr)
                key = (instr, blk)
                table = seen_paths.setdefault(key, {})
                if len(parts) == 1:
                    parent = ROOT_OF.get(instr)
                else:
                    parent = table.get(".".join(parts[:-1]))
                wid = _hexid(mm.group(3))
                table[pathtok] = wid
                vis = mm.group(9)
                rec = {
                    "instr": instr, "block": blk, "ts": ts, "line": lineno,
                    "path": pathtok, "depth": len(parts),
                    "id": wid, "vt": mm.group(4).upper(),
                    "parent_id": parent,
                    "parent_path": ".".join(parts[:-1]) if len(parts) > 1 else None,
                    "l": int(mm.group(5)), "t": int(mm.group(6)),
                    "w": int(mm.group(7)), "h": int(mm.group(8)),
                    "vis": int(vis) if vis is not None else None,
                    "coord": "rel",
                }
                if instr == "BHDR" and bhdr_instances:
                    rec["bhdr_instance"] = bhdr_instances[-1]["instance"]
                records.append(rec)
                counts[instr] = counts.get(instr, 0) + 1
                continue

            mm = BHDR_HDR_RE.search(body)
            if mm:
                blk = blocker.force_new("BHDR")
                seen_paths.pop(("BHDR", blk), None)
                bhdr_instances.append({
                    "instance": int(mm.group(1)), "block": blk, "ts": ts,
                    "dlg_l": int(mm.group(2)), "dlg_t": int(mm.group(3)),
                    "dlg_w": int(mm.group(4)), "dlg_h": int(mm.group(5)),
                    "pane_children": int(mm.group(6)),
                })
                counts["BHDR_instance"] = counts.get("BHDR_instance", 0) + 1
                continue

            mm = DGPKID_RE.search(body)
            if mm:
                top = int(mm.group(1))
                blk = blocker.index("DGPKID", top, tms)
                tail = mm.group(8) or ""
                records.append({
                    "instr": "DGPKID", "block": blk, "ts": ts, "line": lineno,
                    "path": mm.group(1), "depth": 1,
                    "id": _hexid(mm.group(2)), "vt": None,
                    "parent_id": "@GODPARENT", "parent_path": None,
                    "l": int(mm.group(3)), "t": int(mm.group(4)),
                    "w": int(mm.group(5)), "h": int(mm.group(6)),
                    "vis": int(mm.group(7)), "coord": "rel",
                    "container": "<==CONTAINER" in tail,
                    "over_dead_band": "OVER-DEAD-BAND" in tail,
                })
                counts["DGPKID"] = counts.get("DGPKID", 0) + 1
                continue

            mm = DGPOPEN_RE.search(body)
            if mm:
                blocker.force_new("DGPKID")
                counts["DGP_OPEN"] = counts.get("DGP_OPEN", 0) + 1
                continue

            mm = DPROBE_RE.search(body)
            if mm:
                # DPROBE has no index to block on (it walks a subtree, not an
                # indexed child list) and it prints its parent explicitly, so
                # blocks here are only for readability: split on a stamp gap.
                if dprobe_blk is None or (
                        tms is not None and dprobe_ms is not None
                        and tms - dprobe_ms >= BLOCK_GAP_MS):
                    dprobe_blk = 0 if dprobe_blk is None else dprobe_blk + 1
                if tms is not None:
                    dprobe_ms = tms
                blk = dprobe_blk
                records.append({
                    "instr": "DPROBE", "block": blk, "ts": ts, "line": lineno,
                    "path": mm.group(5), "depth": int(mm.group(2)),
                    "id": _hexid(mm.group(3)), "vt": None,
                    "parent_id": _hexid(mm.group(4)), "parent_path": None,
                    "l": int(mm.group(6)), "t": int(mm.group(7)),
                    "w": int(mm.group(8)), "h": int(mm.group(9)),
                    "vis": int(mm.group(10)), "coord": "abs",
                    "ptr": mm.group(1).upper(),
                    "new": bool(mm.group(11)),
                })
                counts["DPROBE"] = counts.get("DPROBE", 0) + 1
                continue

            mm = TREE_RE.match(body)
            if mm:
                depth = len(mm.group(1)) // 2
                if depth == 0:
                    blocker.force_new("TREE")
                    tree_stack = []
                while tree_stack and tree_stack[-1][0] >= depth:
                    tree_stack.pop()
                parent = tree_stack[-1][1] if tree_stack else None
                wid = _hexid(mm.group(2))
                vis_self = int(mm.group(8))
                # EFFECTIVE visibility. A window's own vis=1 means nothing if
                # an ancestor is hidden - a naive pass reports every window in
                # every CLOSED dialog as an on-screen miss (this is the exact
                # trap _tests\Audit-UnscaledWindows.py documents). The tree is
                # in the indentation, so carry it down the stack. Also carry
                # hidden_ancestors: several god/region roots report vis=0 while
                # their children genuinely draw, and those are precisely the
                # windows this project keeps getting burned by.
                p_eff = tree_stack[-1][2] if tree_stack else True
                p_hid = tree_stack[-1][3] if tree_stack else 0
                eff = bool(p_eff and vis_self)
                hid = p_hid + (0 if vis_self else 1)
                tree_stack.append((depth, wid, eff, hid))
                records.append({
                    "instr": "TREE", "block": blocker.current("TREE"),
                    "ts": ts, "line": lineno,
                    "path": None, "depth": depth,
                    "id": wid, "vt": None,
                    "parent_id": parent, "parent_path": None,
                    "l": int(mm.group(3)), "t": int(mm.group(4)),
                    "w": int(mm.group(5)), "h": int(mm.group(6)),
                    "vis": vis_self, "coord": "rel",
                    "children": int(mm.group(7)),
                    "enabled": int(mm.group(9)),
                    "eff_vis": 1 if eff else 0,
                    "hidden_ancestors": hid,
                })
                counts["TREE"] = counts.get("TREE", 0) + 1
                continue

            if "BOOT tree dump begin" in body or "BOOT dump end" in body:
                blocker.force_new("TREE")
                tree_stack = []
                continue

            # MPROBE enumerates the MAIN window's children (parent derivable);
            # TPROBE walks the tip layer 0x2AAB8CC1's subtree and prints no
            # parent, so parentage there is NOT derivable. Both are ABSOLUTE.
            mm = MPROBE_RE.search(body)
            if mm:
                records.append({
                    "instr": "MPROBE", "block": 0, "ts": ts, "line": lineno,
                    "path": None, "depth": 1,
                    "id": _hexid(mm.group(1)), "vt": mm.group(7).upper(),
                    "parent_id": "@MAINWIN", "parent_path": None,
                    "l": int(mm.group(2)), "t": int(mm.group(3)),
                    "w": int(mm.group(4)), "h": int(mm.group(5)),
                    "vis": int(mm.group(6)), "coord": "abs",
                })
                counts["MPROBE"] = counts.get("MPROBE", 0) + 1
                continue

            mm = TPROBE_RE.search(body)
            if mm:
                records.append({
                    "instr": "TPROBE", "block": 0, "ts": ts, "line": lineno,
                    "path": None, "depth": int(mm.group(1)),
                    "id": _hexid(mm.group(2)), "vt": mm.group(8).upper(),
                    "parent_id": None, "parent_path": None,
                    "l": int(mm.group(3)), "t": int(mm.group(4)),
                    "w": int(mm.group(5)), "h": int(mm.group(6)),
                    "vis": int(mm.group(7)), "coord": "abs",
                })
                counts["TPROBE"] = counts.get("TPROBE", 0) + 1
                continue

            # ---- scale events --------------------------------------------
            mm = PANEL_RE.search(body)
            if mm:
                events.append({
                    "kind": "panel", "ts": ts, "line": lineno,
                    "id": _hexid(mm.group(1)),
                    "from": {"l": int(mm.group(2)), "t": int(mm.group(3)),
                             "w": int(mm.group(4)), "h": int(mm.group(5))},
                    "to": {"l": int(mm.group(6)), "t": int(mm.group(7)),
                           "w": int(mm.group(8)), "h": int(mm.group(9))},
                    "note": (mm.group(10) or "").strip() or None,
                })
                counts["EV_panel"] = counts.get("EV_panel", 0) + 1
                continue

            mm = DLGSCALED_RE.search(body)
            if mm:
                events.append({
                    "kind": "in-city dialog" if mm.group(1) else "dialog",
                    "ts": ts, "line": lineno,
                    "id": _hexid(mm.group(2)),
                    "from": {"l": int(mm.group(3)), "t": int(mm.group(4)),
                             "w": int(mm.group(5)), "h": int(mm.group(6))},
                    "to": {"l": None, "t": None,
                           "w": int(mm.group(7)), "h": int(mm.group(8))},
                    "descendants": int(mm.group(9)),
                })
                counts["EV_dialog"] = counts.get("EV_dialog", 0) + 1
                continue

            mm = FONTSIZED_RE.search(body)
            if mm:
                # DECLARED unscaled: kFontSizedIds keeps the size on purpose
                # (SCENARIOS.md "Some things must NEVER be scaled"). A 1x
                # finding on one of these is EXPECTED, not a defect.
                events.append({
                    "kind": "font-sized-kept", "ts": ts, "line": lineno,
                    "id": _hexid(mm.group(1)),
                    "from": {"l": int(mm.group(2)), "t": int(mm.group(3)),
                             "w": int(mm.group(6)), "h": int(mm.group(7))},
                    "to": {"l": int(mm.group(4)), "t": int(mm.group(5)),
                           "w": int(mm.group(6)), "h": int(mm.group(7))},
                })
                counts["EV_fontsized"] = counts.get("EV_fontsized", 0) + 1
                continue

            mm = TOMBSTONE_RE.search(body)
            if mm:
                g = [x for x in mm.groups() if x is not None]
                events.append({
                    "kind": "tombstoned", "ts": ts, "line": lineno,
                    "id": _hexid(g[0]),
                    "from": None,
                    "to": {"l": None, "t": None, "w": int(g[1]), "h": int(g[2])},
                })
                counts["EV_tombstone"] = counts.get("EV_tombstone", 0) + 1
                continue

            mm = FLYOUT_RE.search(body)
            if mm:
                events.append({
                    "kind": mm.group(1) + "-flyout", "ts": ts, "line": lineno,
                    "id": _hexid(mm.group(2)),
                    "from": None,
                    "to": {"l": int(mm.group(3)), "t": int(mm.group(4)),
                           "w": int(mm.group(5)), "h": int(mm.group(6))},
                    "descendants": int(mm.group(7)),
                })
                counts["EV_flyout"] = counts.get("EV_flyout", 0) + 1
                continue

            mm = POPFIT_RE.search(body)
            if mm:
                counts["POPFIT"] = counts.get("POPFIT", 0) + 1
                continue

            unknown += 1

    st = os.stat(path)
    effective, why = _effective_factor(meta)
    return {
        "schema": SCHEMA,
        "source": {
            "path": os.path.abspath(path),
            "name": os.path.basename(path),
            "size": st.st_size,
            "sha256": digest,
        },
        "meta": meta,
        "effective_factor": effective,
        "factor_evidence": why,
        "counts": counts,
        "lines_total": total,
        "unknown_lines": unknown,
        "bhdr_instances": bhdr_instances,
        "records": records,
        "events": events,
    }


def _effective_factor(meta: dict) -> tuple[float | None, str]:
    """
    Which factor was the UI actually laid out at?

    AUTHORITY ORDER (this is the one place the parser makes a judgement, so it
    is spelled out and it is conservative):
      1. the AutoScale tier line - that is the DLL printing its own decision;
      2. otherwise Settings ScaleAll=0 => the sweep never ran => the tree is
         STOCK, factor 1.0 regardless of what "factor=" says (factor= is the
         ini's requested value, not a decision);
      3. otherwise Settings factor= with ScaleAll=1;
      4. otherwise None - and diff.py will require --factor.
    """
    if meta.get("tier") is not None:
        return float(meta["tier"]), "AutoScale tier line"
    s = meta.get("settings")
    if not s:
        return None, "no Settings line found"
    if s.get("ScaleAll") == 0:
        return 1.0, "ScaleAll=0 (sweep inert) -> stock geometry"
    return float(s.get("factor", 0)) or None, "Settings factor= (no AutoScale line)"


def aggregate(census: dict) -> dict:
    """
    Collapse repeated identical sightings.

    A 250 ms sweep over a long session writes the same window hundreds of
    times; .prev holds 278k tree lines. Deduping on the full geometry keeps
    every DISTINCT state (which is what a diff needs) and throws away only
    the repetition. Deterministic: sorted by the key itself.
    """
    buckets: dict[tuple, dict] = {}
    for r in census["records"]:
        key = (r["instr"], r["id"], r.get("parent_id"), r["l"], r["t"],
               r["w"], r["h"], r.get("vis"), r["coord"], r.get("depth"),
               r.get("eff_vis"))
        b = buckets.get(key)
        if b is None:
            b = dict(r)
            b["n"] = 0
            b["first_ts"] = r.get("ts")
            b["first_line"] = r.get("line")
            b.pop("ts", None)
            b.pop("line", None)
            b.pop("ptr", None)
            b.pop("new", None)
            buckets[key] = b
        b["n"] += 1
        b["last_ts"] = r.get("ts")
    out = dict(census)
    out["records"] = [buckets[k] for k in sorted(buckets.keys(),
                                                 key=lambda k: tuple(
                                                     "" if v is None else v for v in k))]

    # Scale events dedupe on the whole (id, from, to) transition: the same
    # panel is re-scaled on every city re-entry and the transition is what
    # matters, not how many times it happened.
    ebuckets: dict[str, dict] = {}
    for e in census.get("events", []):
        key = json.dumps({k: e[k] for k in e if k not in ("ts", "line")},
                         sort_keys=True)
        b = ebuckets.get(key)
        if b is None:
            b = dict(e)
            b["n"] = 0
            b["first_ts"] = e.get("ts")
            b["first_line"] = e.get("line")
            b.pop("ts", None)
            b.pop("line", None)
            ebuckets[key] = b
        b["n"] += 1
    out["events"] = [ebuckets[k] for k in sorted(ebuckets.keys())]

    out["aggregated"] = True
    out["distinct_records"] = len(out["records"])
    out["distinct_events"] = len(out["events"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="+", help="one or more SC4UIScale.log files")
    ap.add_argument("--out", default=None,
                    help="directory for <stem>.census.json (default: alongside this script in census\\)")
    ap.add_argument("--full", action="store_true",
                    help="keep every sighting instead of deduping identical ones")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    outdir = args.out or os.path.join(here, "census")
    os.makedirs(outdir, exist_ok=True)

    rc = 0
    for p in args.logs:
        if not os.path.isfile(p):
            print(f"FAIL: not a file: {p}")
            rc = 1
            continue
        c = parse_log(p)
        if not args.full:
            c = aggregate(c)
        stem = os.path.basename(p).replace(".", "_")
        dest = os.path.join(outdir, stem + ".census.json")
        with open(dest, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(c, fh, indent=1, sort_keys=True)
            fh.write("\n")
        if not args.quiet:
            kinds = ", ".join(f"{k}={v}" for k, v in sorted(c["counts"].items()))
            print(f"{os.path.basename(p)}: {c['lines_total']} lines, "
                  f"{len(c['records'])} records + {len(c['events'])} events "
                  f"({kinds or 'none'}), "
                  f"unknown={c['unknown_lines']}, "
                  f"f={c['effective_factor']} [{c['factor_evidence']}]")
            print(f"  -> {dest}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
