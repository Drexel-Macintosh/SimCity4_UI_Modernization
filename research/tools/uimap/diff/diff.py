#!/usr/bin/env python3
r"""
diff.py - join PREDICTED vs LIVE vs STOCK and report per-window verdicts.

STAGE 4 of the offline UI model (tools\research\METHOD.md section 6):
"predicted tree vs the live dump vs the stock capture, as a _tests\ suite.
Kills silent regressions; makes tier generality (1.5x/3x) provable offline."

------------------------------------------------------------------------------
THE LAW BEING TESTED
------------------------------------------------------------------------------
_tests\captures\stock-budget\STOCK-REFERENCE.md, the standing directive:

    "Our 2x output SHOULD BE these dialogs, scaled - and every fix must be
     decided from GEOMETRY / MATH against this reference, never from pixel
     counting or screenshot eyeballing."

As math:  live == round(stock * f).  This file never opens a PNG.

There are TWO rounding laws in the codebase and they are BOTH transcribed
from source, not assumed:

  EDGE-DERIVED - the runtime sweep, src\UiSpike.cpp:6478
      newW = ScaleRound(l + w, f) - ScaleRound(l, f)
      ScaleRound(v,f) = llround(v*f)                    (UiSpike.cpp:2806)
  DIRECT - the data generators, tools\selective-safe\build_selective_safe.py:74
      newW = scale_len(w) = floor(w*f + 0.5)            (identical in
      tools\dialog-static\build_dialog_static.py:124)

They agree for every INTEGER f (2x and 3x: k*(l+w) - k*l == k*w exactly) and
can differ by one pixel at 1.5x. 2x therefore HIDES a whole bug class, which
is exactly what SCENARIOS.md AXIS 1 warns about. --tier-sweep enumerates the
divergences offline, with no game and no 1.5x session.

------------------------------------------------------------------------------
THE THREE SOURCES
------------------------------------------------------------------------------
1. LIVE (authority). Censuses from parse_log.py. The project's standing rule
   (METHOD.md section 6): "the model is never the authority - the live dump
   is." Every verdict here is anchored on a measured rect.

2. STOCK. Three oracles, in descending strength:
   a) SCALE EVENTS inside the live log itself. `panel 0xID (l,t wxh) -> (...)`
      carries the pre-scale rect the GAME laid down and the post-scale rect
      we made of it, on the SAME line, at the SAME resolution. No second
      source, no cross-resolution caveat. Strongest evidence available.
   b) An INERT log (ScaleAll=0 / tier 1.0) - measured stock rects. Only SIZES
      and CHILD positions are comparable across resolutions; a top-level
      window's position is anchored to the screen, so it is not.
   c) The 330 extracted .UI scripts, `area=(l,t,r,b)` -> stock w,h. Declarative
      f=1 by construction. Caveat inherited from _tests\Audit-UnscaledWindows.py:
      generic ids <= 0xFF are reused across unrelated scripts, and one id can
      have several script copies (REGRESSION.md law: non-unique dialog ids).

3. PREDICTED. tools\uimap\ (builders.json / constants.json / emu\). Written by
   other agents and MAY NOT EXIST YET. This file never writes there and
   degrades to "model source absent" rather than failing.

------------------------------------------------------------------------------
VERDICTS
------------------------------------------------------------------------------
  MATCH               live == round(stock*f) under one of the laws
  STOCK-1X            live == stock while f != 1     <- the scaler MISSED it
  OVER-SCALED         live == round(stock*f*f)       <- scaled twice
  MISMATCH            neither; the delta is reported
  UNKNOWN-STOCK       live id in no stock oracle - cannot judge
  MISSING-FROM-MODEL  observed live, absent from the predicted model
  MISSING-FROM-LIVE   in the predicted model, never observed in these logs

Every verdict carries a TRIAGE tag when the id sits on one of the DLL's own
never-scale lists (parsed live out of src\UiSpike.cpp, read-only). A window
that is 1x BY DESIGN is not a defect, and a harness that cannot tell the
difference just produces noise.

------------------------------------------------------------------------------
RESUMABILITY (hard requirement)
------------------------------------------------------------------------------
Work is split into UNITS; state.json is rewritten after EVERY unit, not at the
end. --resume skips units whose input fingerprint is unchanged. Running from
scratch is always safe and produces byte-identical artifacts: no wall-clock,
no dict-order, no PRNG anywhere in the output path. See RESUME.md.

USAGE
    python diff.py --auto                      # discover logs, do everything
    python diff.py --live L.census.json --factor 2.0
    python diff.py --tier-sweep
    python diff.py --auto --resume
    python diff.py --auto --write-findings     # emit FINDINGS-generated.md
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UIMAP = os.path.dirname(HERE)                      # tools\uimap
TOOLS = os.path.dirname(UIMAP)                     # tools
PROJ = os.path.dirname(TOOLS)                      # project root
SCHEMA = "sc4-uimap-diff/report/1"
TIERS = (1.0, 1.5, 2.0, 3.0)

sys.path.insert(0, HERE)
import parse_log  # noqa: E402  (same directory, deliberate)


# ============================================================ rounding laws

def scale_round(v: int, f: float) -> int:
    """UiSpike.cpp:2806 ScaleRound - llround (half away from zero)."""
    return int(math.floor(v * f + 0.5)) if v >= 0 else -int(math.floor(-v * f + 0.5))


def scale_len(v: int, f: float) -> int:
    """build_selective_safe.py:74 scale_len - floor(v*f + 0.5), half up."""
    return int(math.floor(v * f + 0.5))


def edge_law(pos: int, length: int, f: float) -> int:
    """UiSpike.cpp:6478 - the runtime sweep's size law."""
    return scale_round(pos + length, f) - scale_round(pos, f)


# ============================================================ id triage lists

ARRAY_RE = re.compile(r"const\s+uint32_t\s+(k\w+)\s*\[\]\s*=\s*\{", re.S)


def strip_c_comments(text: str) -> str:
    """
    Comments in UiSpike.cpp are DENSE and full of window ids ("0x698894D3 My
    Sims strip - REMOVED from this list"). Extracting hex without stripping
    them first would enrol every id ever DISCUSSED into every list.
    """
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def load_id_lists(src_path: str) -> dict[str, list[str]]:
    """Parse every `const uint32_t kXxx[] = {...}` out of UiSpike.cpp."""
    if not os.path.isfile(src_path):
        return {}
    with open(src_path, "r", encoding="utf-8", errors="replace") as fh:
        text = strip_c_comments(fh.read())
    out: dict[str, list[str]] = {}
    for m in ARRAY_RE.finditer(text):
        name = m.group(1)
        i = m.end()
        depth = 1
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[m.end():i]
        ids = ["0x" + v.upper().rjust(8, "0")
               for v in re.findall(r"0x([0-9A-Fa-f]{1,8})", body)]
        out[name] = sorted(set(ids))
    return out


# Ids that are 1x ON PURPOSE. Sources: SCENARIOS.md "Some things must NEVER be
# scaled" + the arrays themselves.
EXPECTED_1X_LISTS = (
    "kNeverScaleIds",            # served by the static .UI dat instead
    "kFontSizedIds",             # already correct once fonts are scaled
    "kAdviceListNeverTouchIds",  # game re-imposes cached geometry every tick
    "kDataScaledSubtreeIds",     # children already carry scaled .UI geometry
    "kGodToolFlyoutIds",         # sweep skips outright
)
MARKER_ID = "0x0000AAAA"         # alignment marker - POSITIONING DATA, never scaled


def triage(wid: str, lists: dict[str, list[str]]) -> list[str]:
    tags = []
    if wid == MARKER_ID:
        tags.append("ALIGNMENT-MARKER")
    for name in EXPECTED_1X_LISTS:
        if wid in lists.get(name, ()):
            tags.append(name)
    if int(wid, 16) <= 0xFF:
        tags.append("GENERIC-ID")
    return tags


# ============================================================ stock oracles

SCRIPT_RE = re.compile(
    r"id=0x([0-9A-Fa-f]{1,8})(.*?)area=\((-?\d+),(-?\d+),(-?\d+),(-?\d+)\)")


def load_stock_scripts(scripts_dir: str) -> dict[str, list[list[int]]]:
    """id -> sorted list of [w,h] seen in any .UI script (f=1 by construction)."""
    stock: dict[str, set] = {}
    if not os.path.isdir(scripts_dir):
        return {}
    for name in sorted(os.listdir(scripts_dir)):
        if not name.lower().endswith(".ui"):
            continue
        # 0x08000600 is the native 800x600 layout DIALECT - a different design,
        # not a stock reference for the 96a006b0 tree (Audit-UnscaledWindows.py).
        if "08000600" in name:
            continue
        try:
            with open(os.path.join(scripts_dir, name), "r",
                      encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        for m in SCRIPT_RE.finditer(text):
            wid = "0x" + m.group(1).upper().rjust(8, "0")
            l, t, r, b = (int(m.group(i)) for i in (3, 4, 5, 6))
            w, h = r - l, b - t
            if w > 0 and h > 0:
                stock.setdefault(wid, set()).add((w, h))
    return {k: sorted([list(x) for x in v]) for k, v in sorted(stock.items())}


def load_stock_from_census(census: dict) -> dict[str, list[list[int]]]:
    """id -> [w,h] from an INERT (factor 1.0) census. MEASURED stock."""
    out: dict[str, set] = {}
    for r in census["records"]:
        if r["w"] > 0 and r["h"] > 0:
            out.setdefault(r["id"], set()).add((r["w"], r["h"]))
    return {k: sorted([list(x) for x in v]) for k, v in sorted(out.items())}


def screen_size(census: dict) -> list[int] | None:
    """
    The RENDER resolution this census was taken at.

    Needed because a screen-sized window (the main window, the tip layer, the
    full-screen region view layers) is sized by the RESOLUTION, not by f. It
    is 800x600 in an 800x600 run and 2400x1600 in a 2400x1600 run, and
    comparing the two as if `live == round(stock*f)` invents four defects that
    are not there. AXIS 5 in SCENARIOS.md is the same distinction.

    Authority: the DLL's own AutoScale line; else the root of a full-tree
    dump (depth 0 IS the screen).
    """
    rr = (census.get("meta") or {}).get("render_res")
    if rr:
        return list(rr)
    roots = [(r["w"], r["h"]) for r in census["records"]
             if r["instr"] == "TREE" and r.get("depth") == 0]
    return list(roots[0]) if roots else None


# ============================================================ predicted model

def load_model(uimap_dir: str) -> dict:
    """
    Load the PREDICTED tree from tools\\uimap\\ - tolerantly.

    Written by other agents and not guaranteed to exist yet, so this accepts
    every reasonable shape rather than one contract:
      * a bare list of window dicts
      * {"windows": [...]} / {"predicted": [...]} / {"tree": [...]} / {"rects": [...]}
      * {"<id>": {...}} keyed by id
    and a rect as any of {l,t,w,h} / {x,y,w,h} / {"area":[l,t,r,b]} / [l,t,r,b].

    Returns {"available": bool, "reason": str, "sources": [...], "windows": {id: [ {..} ]}}
    """
    result = {"available": False, "reason": "", "sources": [], "windows": {}}
    if not os.path.isdir(uimap_dir):
        result["reason"] = f"model dir does not exist: {uimap_dir}"
        return result

    candidates = []
    for pat in ("builders.json", "constants.json", "*.json"):
        candidates += sorted(glob.glob(os.path.join(uimap_dir, pat)))
    candidates += sorted(glob.glob(os.path.join(uimap_dir, "emu", "*.json")))
    candidates += sorted(glob.glob(os.path.join(uimap_dir, "emu", "out", "*.json")))
    # Never read our own artifacts back in as if they were a model.
    candidates = [c for c in dict.fromkeys(candidates)
                  if os.path.abspath(os.path.dirname(c)) != os.path.abspath(HERE)
                  and os.sep + "diff" + os.sep not in c]
    if not candidates:
        result["reason"] = (f"no *.json under {uimap_dir} (stages 1-3 have not "
                            f"emitted yet)")
        return result

    total = 0
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            result["sources"].append({"path": path, "windows": 0,
                                      "note": f"unreadable: {exc.__class__.__name__}"})
            continue
        wins = _extract_windows(doc)
        if wins:
            total += len(wins)
            for w in wins:
                result["windows"].setdefault(w["id"], []).append(w)
        result["sources"].append({"path": os.path.relpath(path, PROJ),
                                  "windows": len(wins)})
    if total:
        result["available"] = True
        result["reason"] = f"{total} predicted windows from {len(result['sources'])} file(s)"
    else:
        result["reason"] = ("model files exist but none contained recognisable "
                            "window rects (see SCHEMA in RESUME.md)")
    return result


def load_emu_cases(uimap_dir: str) -> list[dict]:
    """
    Stage 3's acceptance cases (tools\\uimap\\emu\\state.json).

    Each case records a PREDICTED size (`got`) produced by emulating a builder
    with stubbed window/font APIs. The cases are keyed by prose, not by window
    id, so they cannot be joined on id - but a predicted size that turns up as
    a real live rect is still a genuine predicted-vs-live confirmation, and
    that is exactly what stage 4 exists to state. Read only; never written.
    """
    path = os.path.join(uimap_dir, "emu", "state.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return []
    out = []
    for name, case in sorted((doc.get("cases") or {}).items()):
        got = case.get("got")
        if isinstance(got, list) and len(got) == 2 and all(
                isinstance(v, int) for v in got):
            out.append({"case": name, "predicted": got,
                        "expect": case.get("expect"),
                        "pass": bool(case.get("pass")),
                        "inputs": case.get("inputs")})
    return out


def _rect_of(d) -> dict | None:
    if isinstance(d, (list, tuple)) and len(d) == 4 and all(
            isinstance(v, int) for v in d):
        l, t, r, b = d
        return {"l": l, "t": t, "w": r - l, "h": b - t}
    if not isinstance(d, dict):
        return None
    if "area" in d:
        return _rect_of(d["area"])
    keys = set(d)
    if {"l", "t", "w", "h"} <= keys:
        return {k: int(d[k]) for k in ("l", "t", "w", "h")}
    if {"x", "y", "w", "h"} <= keys:
        return {"l": int(d["x"]), "t": int(d["y"]),
                "w": int(d["w"]), "h": int(d["h"])}
    if {"w", "h"} <= keys:
        return {"l": int(d.get("l", 0)), "t": int(d.get("t", 0)),
                "w": int(d["w"]), "h": int(d["h"])}
    return None


def _norm_id(v) -> str | None:
    if isinstance(v, int):
        return "0x%08X" % (v & 0xFFFFFFFF)
    if isinstance(v, str):
        s = v.strip()
        try:
            return "0x%08X" % (int(s, 16) & 0xFFFFFFFF)
        except ValueError:
            return None
    return None


def _extract_windows(doc) -> list[dict]:
    """Pull every {id + rect} out of an arbitrarily-shaped model document."""
    # STAGE 1/2 SHAPE (the one tools\uimap\builders.json actually emits):
    #   {"builders": {"<va>": {"identification": {"childIds": [int, ...]}, ...}}}
    # These carry NO rect - stage 1 is a builder census, not a layout. The id
    # set is still the joinable surface that matters: it answers "is this live
    # window attributable to a known builder?", which is what
    # MISSING-FROM-MODEL means at this stage.
    if isinstance(doc, dict) and isinstance(doc.get("builders"), dict):
        out = []
        for va, b in doc["builders"].items():
            if not isinstance(b, dict):
                continue
            ident = b.get("identification") or {}
            for cid in (ident.get("childIds") or []):
                wid = _norm_id(cid)
                if wid:
                    out.append({"id": wid, "parent_id": None, "factor": None,
                                "builder": va})
        if out:
            return out

    rows = None
    if isinstance(doc, list):
        rows = doc
    elif isinstance(doc, dict):
        for key in ("windows", "predicted", "tree", "rects", "nodes"):
            if isinstance(doc.get(key), list):
                rows = doc[key]
                break
        if rows is None:
            # id-keyed map?
            keyed = [(k, v) for k, v in doc.items()
                     if _norm_id(k) and isinstance(v, dict)]
            if keyed:
                rows = [dict(v, id=k) for k, v in keyed]
    if not rows:
        return []
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        wid = None
        for k in ("id", "win_id", "window_id", "wid"):
            if k in r:
                wid = _norm_id(r[k])
                if wid:
                    break
        if not wid:
            continue
        rect = _rect_of(r)
        row = {"id": wid, "parent_id": _norm_id(r.get("parent") or r.get("parent_id")),
               "factor": r.get("factor"),
               "builder": r.get("builder") or r.get("builder_va") or r.get("va")}
        if rect:
            row.update(rect)
        out.append(row)
    return out


# ============================================================ classification

def classify(live_w: int, live_h: int, stock_sizes: list, f: float,
             live_l: int | None = None, live_t: int | None = None,
             tol: int = 0) -> dict:
    """
    Judge one live size against every known stock size for that id.

    Both laws are tried. At integer f they are the same number, so this costs
    nothing at 2x/3x and is the whole point at 1.5x.
    """
    if not stock_sizes:
        return {"verdict": "UNKNOWN-STOCK"}

    best = None
    for sw, sh in stock_sizes:
        cands = {
            "direct": (scale_len(sw, f), scale_len(sh, f)),
        }
        if live_l is not None and live_t is not None:
            cands["edge"] = (edge_law(live_l, sw, f), edge_law(live_t, sh, f))
        for law, (ew, eh) in cands.items():
            dw, dh = live_w - ew, live_h - eh
            if abs(dw) <= tol and abs(dh) <= tol:
                return {"verdict": "MATCH", "law": law,
                        "stock": [sw, sh], "expected": [ew, eh],
                        "delta": [dw, dh]}
            score = abs(dw) + abs(dh)
            if best is None or score < best["score"]:
                best = {"score": score, "law": law, "stock": [sw, sh],
                        "expected": [ew, eh], "delta": [dw, dh]}

    # STOCK-1X: the strongest defect signal in the project's history - a window
    # the sweep never touched, sitting at half size inside 2x siblings.
    if f != 1.0:
        for sw, sh in stock_sizes:
            if abs(live_w - sw) <= tol and abs(live_h - sh) <= tol:
                return {"verdict": "STOCK-1X", "stock": [sw, sh],
                        "expected": [scale_len(sw, f), scale_len(sh, f)],
                        "delta": [live_w - scale_len(sw, f),
                                  live_h - scale_len(sh, f)]}
        for sw, sh in stock_sizes:
            dw = live_w - scale_len(scale_len(sw, f), f)
            dh = live_h - scale_len(scale_len(sh, f), f)
            if abs(dw) <= tol and abs(dh) <= tol:
                return {"verdict": "OVER-SCALED", "stock": [sw, sh],
                        "expected": [scale_len(sw, f), scale_len(sh, f)],
                        "delta": [live_w - scale_len(sw, f),
                                  live_h - scale_len(sh, f)]}
    # ONE AXIS EXACT. If width satisfies the law to the pixel and height does
    # not (or vice versa), the failing axis is almost always CONTENT-driven -
    # a window sized by its wrapped text or its art, which no `stock * f` can
    # predict (REGRESSION.md law 17 "a style-PNG widget is born at the ART's
    # size", law 21 "text laid out once at creation does not re-wrap", and the
    # kFontSizedIds family). A uniform scaling defect moves BOTH axes; it
    # essentially never moves exactly one and leaves the other pixel-perfect.
    # Reported as its own verdict so it is neither ignored nor mistaken for a
    # scaling bug.
    if best and (best["delta"][0] == 0) != (best["delta"][1] == 0):
        out = {"verdict": "ONE-AXIS-EXACT",
               "axis_ok": "w" if best["delta"][0] == 0 else "h",
               "note": ("one axis satisfies the law exactly, the other does "
                        "not - the failing axis is content/art-sized, not "
                        "uniformly scaled")}
        out.update({k: v for k, v in best.items() if k != "score"})
        return out

    out = {"verdict": "MISMATCH"}
    out.update({k: v for k, v in best.items() if k != "score"})
    return out


# ============================================================ state / resume

STATE_VERSION = 3


def load_state(path: str) -> dict:
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                st = json.load(fh)
            if st.get("state_version") == STATE_VERSION:
                return st
        except (OSError, ValueError):
            pass
    return {"state_version": STATE_VERSION, "units": {}}


def write_json(path: str, doc) -> None:
    """
    Write JSON atomically where the filesystem allows it.

    ONEDRIVE GOTCHA (SCENARIOS.md "Environment gotchas"): OneDrive keeps
    handles on files in a synced folder and os.replace intermittently fails
    with WinError 5 - the whole project tree is inside OneDrive, so this is
    the normal case, not an edge case. Retry, then fall back to a direct
    write. A direct write is less atomic but a lost temp file is worse: the
    caller is relying on this to survive an interruption.
    """
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    for _ in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            pass
    try:
        os.remove(tmp)
    except OSError:
        pass
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")


def save_state(path: str, state: dict) -> None:
    """Rewritten after EVERY unit (user order: assume interruption)."""
    write_json(path, state)


def fingerprint(path: str) -> str:
    st = os.stat(path)
    return hashlib.sha256(
        f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}".encode()
    ).hexdigest()[:16]


# ============================================================ the run

def plugins_dir() -> str:
    """
    READ ONLY. The Plugins folder is the game's; nothing here ever writes to
    it. Documents is OneDrive-redirected on this machine, so it is RESOLVED
    rather than hardcoded to C:\\Users\\<u>\\Documents (which does not exist).
    """
    docs = os.path.join(os.path.expanduser("~"), "OneDrive", "Documents")
    if not os.path.isdir(docs):
        docs = os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(docs, "SimCity 4", "Plugins")


def discover_logs(history: bool) -> list[str]:
    """
    Default: the CURRENT log plus every f=1 (inert) log, which are the stock
    oracle. The .bak-* archive is up to twenty versions old - every fix since
    is in it as a "defect", so it is archaeology, not a defect list. --history
    opts in, and it is genuinely useful for one thing: confirming the detector
    lights up on builds we KNOW were broken.
    """
    plug = plugins_dir()
    out = sorted(glob.glob(os.path.join(plug, "SC4UIScale.log")))
    # An inert log is a stock oracle at any age - geometry the game itself laid
    # down does not go stale.
    out += sorted(glob.glob(os.path.join(plug, "SC4UIScale.log.bak-stock*")))
    if history:
        out += sorted(glob.glob(os.path.join(plug, "SC4UIScale.log.bak-*")))
        out += sorted(glob.glob(os.path.join(plug, "SC4UIScale.log.prev")))
        out += sorted(glob.glob(os.path.join(PROJ, "_tests", "*.log")))
    return [p for p in dict.fromkeys(out) if os.path.isfile(p)]


def run(args) -> dict:
    censdir = os.path.join(HERE, "census")
    os.makedirs(censdir, exist_ok=True)
    statepath = os.path.join(HERE, "state.json")
    state = load_state(statepath) if args.resume else {
        "state_version": STATE_VERSION, "units": {}}

    # ---- unit 1..N: parse each log -------------------------------------
    logs = args.live_logs or (discover_logs(args.history) if args.auto else [])
    censuses = []
    for p in logs:
        unit = "parse:" + os.path.basename(p)
        fp = fingerprint(p)
        dest = os.path.join(censdir, os.path.basename(p).replace(".", "_")
                            + ".census.json")
        done = state["units"].get(unit)
        if args.resume and done and done.get("fp") == fp and os.path.isfile(dest):
            with open(dest, "r", encoding="utf-8") as fh:
                censuses.append(json.load(fh))
            print(f"  [resume] {os.path.basename(p)}")
            continue
        c = parse_log.aggregate(parse_log.parse_log(p))
        with open(dest, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(c, fh, indent=1, sort_keys=True)
            fh.write("\n")
        censuses.append(c)
        state["units"][unit] = {"fp": fp, "artifact": os.path.relpath(dest, HERE),
                                "records": len(c["records"]),
                                "events": len(c["events"]),
                                "factor": c["effective_factor"]}
        save_state(statepath, state)          # <-- after EVERY unit
        print(f"  parsed {os.path.basename(p)}: {len(c['records'])} records, "
              f"{len(c['events'])} events, f={c['effective_factor']}")

    for p in args.census or []:
        with open(p, "r", encoding="utf-8") as fh:
            censuses.append(json.load(fh))

    # ---- unit: stock oracles -------------------------------------------
    scripts_dir = args.scripts or os.path.join(TOOLS, "uiscripts", "extracted")
    stock_scripts = load_stock_scripts(scripts_dir)
    state["units"]["stock:scripts"] = {"dir": os.path.relpath(scripts_dir, PROJ),
                                       "ids": len(stock_scripts)}
    save_state(statepath, state)

    # THIRD-PARTY SCRIPT REPLACEMENTS. A plugin can replace a stock .UI script
    # outright (SCENARIOS.md AXIS 2 + the LOAD-ORDER LAW), and when it does,
    # "stock" for that TGI is the MOD's script, not Maxis's. Judging the live
    # window against the Maxis copy manufactures a delta that is really just
    # the mod's different design. These are extracted copies of the mod's own
    # scripts, kept for exactly this reason.
    tp_dir = os.path.join(TOOLS, "selective-safe", "thirdparty-ui")
    thirdparty_scripts = load_stock_scripts(tp_dir)
    state["units"]["stock:thirdparty"] = {
        "dir": os.path.relpath(tp_dir, PROJ) if os.path.isdir(tp_dir) else None,
        "ids": len(thirdparty_scripts)}
    save_state(statepath, state)

    stock_logs = {}
    stock_screens = []
    for c in censuses:
        if c.get("effective_factor") == 1.0:
            stock_logs[c["source"]["name"]] = load_stock_from_census(c)
            sc = screen_size(c)
            if sc:
                stock_screens.append(tuple(sc))
            state["units"]["stock:" + c["source"]["name"]] = {
                "ids": len(stock_logs[c["source"]["name"]]),
                "screen": sc,
                "evidence": c["factor_evidence"]}
            save_state(statepath, state)

    merged_stock: dict[str, dict[str, list]] = {}
    for wid, sizes in stock_scripts.items():
        merged_stock.setdefault(wid, {})["scripts"] = sizes
    # The mod's copy REPLACES the Maxis one for that id - it does not add to
    # it. Keeping both would let a live window match the wrong design and hide
    # the very defect this oracle exists to expose.
    for wid, sizes in thirdparty_scripts.items():
        merged_stock.setdefault(wid, {}).pop("scripts", None)
        merged_stock[wid]["thirdparty-scripts"] = sizes
    for name, table in sorted(stock_logs.items()):
        for wid, sizes in table.items():
            merged_stock.setdefault(wid, {})[name] = sizes

    # STRONGEST STOCK ORACLE: the pre-scale rect on a scale-event line. That is
    # the geometry the GAME laid down, in this run, at this resolution - it
    # beats a .UI script, which is one of possibly several declared copies and
    # may not be the copy that is live (SCENARIOS.md: "identify the LIVE one by
    # rect-matching against a runtime dump"). Registered per source log so the
    # provenance of every verdict stays visible in `oracles`.
    ev_from: dict[str, dict[str, set]] = {}
    ev_to: dict[str, dict[str, set]] = {}
    for c in censuses:
        nm = c["source"]["name"]
        for e in c.get("events", []):
            if e["kind"] not in ("panel", "dialog", "in-city dialog"):
                continue
            src, dst = e.get("from"), e.get("to")
            if src and src.get("w"):
                merged_stock.setdefault(e["id"], {}).setdefault(
                    "events:" + nm, [])
                sizes = merged_stock[e["id"]]["events:" + nm]
                if [src["w"], src["h"]] not in sizes:
                    sizes.append([src["w"], src["h"]])
                    sizes.sort()
                ev_from.setdefault(nm, {}).setdefault(e["id"], set()).add(
                    (src["w"], src["h"]))
            if dst and dst.get("w"):
                ev_to.setdefault(nm, {}).setdefault(e["id"], set()).add(
                    (dst["w"], dst["h"]))

    # ---- unit: id triage lists -----------------------------------------
    lists = load_id_lists(os.path.join(PROJ, "src", "UiSpike.cpp"))
    state["units"]["triage:UiSpike.cpp"] = {k: len(v) for k, v in sorted(lists.items())}
    save_state(statepath, state)

    # ---- unit: predicted model -----------------------------------------
    model = load_model(UIMAP)
    state["units"]["model"] = {"available": model["available"],
                               "reason": model["reason"],
                               "sources": model["sources"]}
    save_state(statepath, state)

    report = {
        "schema": SCHEMA,
        "inputs": {
            "logs": [{"name": c["source"]["name"], "sha256": c["source"]["sha256"],
                      "size": c["source"]["size"],
                      "factor": c["effective_factor"],
                      "factor_evidence": c["factor_evidence"],
                      "version": c["meta"].get("version"),
                      "render_res": c["meta"].get("render_res"),
                      "records": len(c["records"]), "events": len(c["events"])}
                     for c in censuses],
            "stock_scripts_dir": os.path.relpath(scripts_dir, PROJ),
            "stock_script_ids": len(stock_scripts),
            "thirdparty_script_ids": len(thirdparty_scripts),
            "stock_log_oracles": sorted(stock_logs),
            "model": {"available": model["available"], "reason": model["reason"],
                      "sources": model["sources"]},
            "id_lists": {k: len(v) for k, v in sorted(lists.items())},
        },
        "event_check": [],
        "live_vs_stock": [],
        "model_join": {"missing_from_model": [], "missing_from_live": [],
                       "model_vs_stock": []},
        "tier_sweep": {},
        "summary": {},
    }

    # ---- unit: SCALE-EVENT self check (strongest evidence) --------------
    for c in censuses:
        f = args.factor or c.get("effective_factor")
        if not f:
            continue
        for e in c.get("events", []):
            if e["kind"] not in ("panel", "dialog", "in-city dialog"):
                continue
            src, dst = e.get("from"), e.get("to")
            if not src or not dst or dst.get("w") is None:
                continue
            ew = edge_law(src["l"], src["w"], f)
            eh = edge_law(src["t"], src["h"], f)
            dw = scale_len(src["w"], f)
            dh = scale_len(src["h"], f)
            ok_edge = (dst["w"] == ew and dst["h"] == eh)
            ok_dir = (dst["w"] == dw and dst["h"] == dh)
            row = {
                "log": c["source"]["name"], "kind": e["kind"], "id": e["id"],
                "factor": f, "stock_rect": src, "live_rect": dst,
                "expect_edge": [ew, eh], "expect_direct": [dw, dh],
                "verdict": "MATCH" if (ok_edge or ok_dir) else "MISMATCH",
                "law": "edge" if ok_edge else ("direct" if ok_dir else None),
                "delta_vs_edge": [dst["w"] - ew, dst["h"] - eh],
                "laws_agree": [ew, eh] == [dw, dh],
                "triage": triage(e["id"], lists),
                "n": e.get("n", 1),
            }
            report["event_check"].append(row)
    report["event_check"].sort(key=lambda r: (r["verdict"] != "MISMATCH",
                                              r["id"], r["log"]))
    state["units"]["diff:event_check"] = {
        "rows": len(report["event_check"]),
        "mismatch": sum(1 for r in report["event_check"]
                        if r["verdict"] == "MISMATCH")}
    save_state(statepath, state)

    # ---- unit: LIVE vs STOCK per census ---------------------------------
    for c in censuses:
        f = args.factor or c.get("effective_factor")
        if f is None:
            print(f"  SKIP {c['source']['name']}: no factor derivable "
                  f"({c['factor_evidence']}) - pass --factor")
            continue
        if f == 1.0 and not args.include_stock_logs:
            continue                      # an inert log IS the stock oracle
        unit = f"diff:{c['source']['name']}:f={f}"
        nm = c["source"]["name"]
        live_screen = screen_size(c)
        efrom = ev_from.get(nm, {})
        eto = ev_to.get(nm, {})
        seen = set()
        rows = []
        for r in c["records"]:
            if r["w"] <= 0 or r["h"] <= 0:
                continue
            # ON-SCREEN GATE. A full-tree dump contains every window in every
            # CLOSED dialog, and those are stock-sized simply because they were
            # never opened. Reporting them buries the real misses - the exact
            # failure _tests\Audit-UnscaledWindows.py hit on its first run.
            # Tolerate ONE hidden ancestor: several god/region roots report
            # vis=0 while their children genuinely draw, and those are the
            # windows this project keeps getting burned by.
            if not args.include_hidden:
                if r.get("eff_vis") is not None:
                    if not r["eff_vis"] and r.get("hidden_ancestors", 9) > 1:
                        continue
                elif r.get("vis") == 0:
                    continue
            key = (r["id"], r["w"], r["h"])
            if key in seen:
                continue
            seen.add(key)
            oracles = merged_stock.get(r["id"])
            sizes = []
            if oracles:
                for v in oracles.values():
                    sizes.extend(tuple(x) for x in v)
                sizes = sorted(set(sizes))
            # Position is only comparable when the record is PARENT-relative
            # AND has a real parent window; a top-level window is anchored to
            # the screen, so its l/t depends on the render resolution.
            usable_pos = (r["coord"] == "rel" and r.get("parent_id")
                          and not str(r["parent_id"]).startswith("@"))
            v = classify(r["w"], r["h"], sizes, f,
                         r["l"] if usable_pos else None,
                         r["t"] if usable_pos else None,
                         tol=args.tol)
            # SCREEN-SIZED: sized by the RESOLUTION, not by f. Recognised
            # POSITIVELY (live == this run's render res AND stock == the stock
            # run's render res), never by a size heuristic - SCENARIOS.md
            # "Size heuristics cannot identify content-sized windows".
            if (v["verdict"] != "MATCH" and live_screen
                    and [r["w"], r["h"]] == live_screen
                    and any(tuple(s) in stock_screens for s in sizes)):
                v = {"verdict": "SCREEN-SIZED", "stock": v.get("stock"),
                     "note": f"live == render res {live_screen[0]}x{live_screen[1]}; "
                             f"stock == the stock run's render res"}
            v.update({
                "log": c["source"]["name"], "instr": r["instr"], "id": r["id"],
                "parent_id": r.get("parent_id"), "vis": r.get("vis"),
                "live": [r["w"], r["h"]], "live_pos": [r["l"], r["t"]],
                "coord": r["coord"], "factor": f,
                "oracles": sorted(oracles) if oracles else [],
                "triage": triage(r["id"], lists),
                "n": r.get("n", 1),
                "eff_vis": r.get("eff_vis", r.get("vis")),
                "first_ts": r.get("first_ts"), "last_ts": r.get("last_ts"),
            })
            rows.append(v)

        # EVER-CORRECT EXCLUSION. The sweep runs ~250 ms after a panel is born,
        # so a window caught at stock EARLY and correct LATER is not a miss.
        # Only ids that were NEVER once seen correct in the whole session are
        # real (Audit-UnscaledWindows.py's `ever_scaled` rule).
        # ---- relabel by EVIDENCE, in strength order ------------------------
        # 1. PRE-SWEEP: this exact rect is the `from` side of a scale event in
        #    this same log, so the instrument simply sampled the window before
        #    the sweep reached it (the sweep runs ~250 ms after a panel is
        #    born). Benign, and provable from one line - not a guess.
        # 2. TRANSIENT-*: the id was seen CORRECT at some point in the session
        #    but this sighting was not. Weaker evidence than 1, same meaning
        #    (Audit-UnscaledWindows.py's `ever_scaled` rule).
        ever_ok = {x["id"] for x in rows if x["verdict"] == "MATCH"}
        for x in rows:
            if x["verdict"] not in ("STOCK-1X", "OVER-SCALED", "MISMATCH",
                                    "ONE-AXIS-EXACT"):
                continue
            live = tuple(x["live"])
            if live in efrom.get(x["id"], ()):
                x["verdict"] = "PRE-SWEEP"
                x["evidence"] = ("this rect is the pre-scale side of a scale "
                                 "event in this same log")
            elif live in eto.get(x["id"], ()):
                x["verdict"] = "MATCH"
                x["law"] = "event"
                x["evidence"] = ("this rect is the post-scale side of a scale "
                                 "event in this same log")
            elif x["id"] in ever_ok:
                # 3. TEMPORAL SPLIT. "Seen correct at some point" is not one
                #    thing. If every wrong sighting PRECEDES the first correct
                #    one, the instrument merely sampled ahead of the sweep -
                #    benign. If a wrong sighting comes AFTER a correct one, the
                #    window REVERTED, which is REGRESSION.md law 14 exactly
                #    (a scale record outliving the state that matched it - the
                #    id that tore Ordinances twice). Those are not the same
                #    finding and must not share a bucket.
                first_ok = min((y.get("first_ts") or "" for y in rows
                                if y["id"] == x["id"] and y["verdict"] == "MATCH"),
                               default="")
                if x.get("last_ts") and first_ok and x["last_ts"] <= first_ok:
                    x["verdict"] = "PRE-SWEEP"
                    x["evidence"] = (f"last seen wrong at {x['last_ts']}, first "
                                     f"seen correct at {first_ok}")
                else:
                    x["verdict"] = "RECURRING-" + x["verdict"]
                    x["evidence"] = (f"seen WRONG at {x.get('last_ts')} which is "
                                     f"NOT before the first correct sighting "
                                     f"{first_ok or '(none)'} - candidate for the "
                                     f"law-14 revert class")

        # AMBIGUOUS IDS. Generic placeholder ids (0x00000000..0x000000FF) are
        # reused across hundreds of unrelated scripts and windows, so joining
        # on id alone produces pure noise (the caveat _tests\Audit-Unscaled-
        # Windows.py already carries). Keep them, but never in a defect bucket.
        for x in rows:
            if "GENERIC-ID" in x["triage"] and x["verdict"] not in (
                    "MATCH", "UNKNOWN-STOCK", "SCREEN-SIZED"):
                x["ambiguous_reason"] = ("generic placeholder id - identity "
                                         "cannot be established by id alone")
                x["verdict"] = "AMBIGUOUS-ID"

        order = {"STOCK-1X": 0, "OVER-SCALED": 1, "MISMATCH": 2,
                 "RECURRING-STOCK-1X": 3, "RECURRING-OVER-SCALED": 4,
                 "RECURRING-MISMATCH": 5, "RECURRING-ONE-AXIS-EXACT": 6,
                 "ONE-AXIS-EXACT": 7, "MATCH": 8, "PRE-SWEEP": 9,
                 "SCREEN-SIZED": 10, "AMBIGUOUS-ID": 11, "UNKNOWN-STOCK": 12}
        rows.sort(key=lambda x: (order.get(x["verdict"], 9), x["id"], x["instr"]))
        report["live_vs_stock"].extend(rows)
        state["units"][unit] = {
            "rows": len(rows),
            "by_verdict": {k: sum(1 for x in rows if x["verdict"] == k)
                           for k in sorted(order)},
        }
        save_state(statepath, state)

    # ---- unit: MODEL join ------------------------------------------------
    live_ids = sorted({r["id"] for c in censuses for r in c["records"]}
                      | {e["id"] for c in censuses for e in c.get("events", [])})
    if model["available"]:
        mids = set(model["windows"])
        report["model_join"]["missing_from_model"] = [
            {"id": i, "triage": triage(i, lists),
             "seen_in": sorted({c["source"]["name"] for c in censuses
                                for r in c["records"] if r["id"] == i})}
            for i in live_ids if i not in mids]
        report["model_join"]["missing_from_live"] = [
            {"id": i, "triage": triage(i, lists)}
            for i in sorted(mids) if i not in set(live_ids)]
        # MODEL vs STOCK: the model claims a rect at some factor; that claim
        # must itself equal round(stock*f), or the model is wrong before any
        # live data is even involved.
        for wid in sorted(mids):
            oracles = merged_stock.get(wid)
            if not oracles:
                continue
            sizes = sorted({tuple(x) for v in oracles.values() for x in v})
            for w in model["windows"][wid]:
                if "w" not in w:
                    continue
                mf = float(w.get("factor") or args.factor or 1.0)
                v = classify(w["w"], w["h"], sizes, mf,
                             w.get("l"), w.get("t"), tol=args.tol)
                v.update({"id": wid, "model": [w["w"], w["h"]], "factor": mf,
                          "builder": w.get("builder")})
                report["model_join"]["model_vs_stock"].append(v)
    else:
        report["model_join"]["note"] = model["reason"]

    # STAGE-3 CROSS-CHECK: a size the emulator PREDICTED, found in a live rect.
    # This is the acceptance test METHOD.md section 6 names ("if the model
    # reproduces the measured 795x75 / 750x25 bodies, it is trustworthy").
    emu = load_emu_cases(UIMAP)
    live_by_size: dict[tuple, set] = {}
    for c in censuses:
        for r in c["records"]:
            live_by_size.setdefault((r["w"], r["h"]), set()).add(
                (r["id"], r["instr"], c["source"]["name"]))
    for case in emu:
        hits = sorted(live_by_size.get(tuple(case["predicted"]), ()))
        case["live_matches"] = [{"id": h[0], "instr": h[1], "log": h[2]}
                                for h in hits]
        case["confirmed_live"] = bool(hits)
    report["model_join"]["emu_cases"] = emu
    state["units"]["diff:emu_cases"] = {
        "cases": len(emu),
        "confirmed_live": sum(1 for c in emu if c["confirmed_live"])}

    state["units"]["diff:model_join"] = {
        "available": model["available"],
        "missing_from_model": len(report["model_join"]["missing_from_model"]),
        "missing_from_live": len(report["model_join"]["missing_from_live"]),
    }
    save_state(statepath, state)

    # ---- unit: TIER SWEEP (offline tier-generality proof) ----------------
    if args.tier_sweep or args.auto:
        sweep = {}
        for f in TIERS:
            diverge, collapse = [], {}
            for wid, sizes in sorted(merged_stock.items()):
                allsz = sorted({tuple(x) for v in sizes.values() for x in v})
                for (sw, sh) in allsz:
                    # Divergence is position-dependent, so probe the worst
                    # case: an odd origin. l=1 is the minimal witness.
                    d = (scale_len(sw, f), scale_len(sh, f))
                    e = (edge_law(1, sw, f), edge_law(1, sh, f))
                    if d != e:
                        diverge.append({"id": wid, "stock": [sw, sh],
                                        "direct": list(d), "edge_at_l1": list(e)})
                    collapse.setdefault(d, set()).add((sw, sh))
            collided = [{"scaled": list(k), "stock_sizes": sorted(list(x) for x in v)}
                        for k, v in sorted(collapse.items()) if len(v) > 1]
            sweep["%g" % f] = {
                "divergent_pairs": len(diverge),
                "divergent_sample": diverge[:40],
                "collapsing_sizes": len(collided),
                "collapsing_sample": collided[:20],
            }
            state["units"][f"tiersweep:f={f}"] = {
                "divergent_pairs": len(diverge), "collapsing": len(collided)}
            save_state(statepath, state)
        report["tier_sweep"] = sweep

    # ---- summary ---------------------------------------------------------
    def tally(rows, key="verdict"):
        out = {}
        for r in rows:
            out[r[key]] = out.get(r[key], 0) + 1
        return dict(sorted(out.items()))

    report["summary"] = {
        "logs": len(censuses),
        "live_ids": len(live_ids),
        "event_check": tally(report["event_check"]),
        "live_vs_stock": tally(report["live_vs_stock"]),
        "model_available": model["available"],
        "missing_from_model": len(report["model_join"]["missing_from_model"]),
        "missing_from_live": len(report["model_join"]["missing_from_live"]),
    }

    dest = os.path.join(HERE, "report.json")
    with open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    state["units"]["report"] = {"artifact": "report.json",
                                "summary": report["summary"]}
    save_state(statepath, state)
    return report


# ============================================================ findings writer

def write_findings(report: dict, path: str) -> None:
    """
    Deterministic markdown digest. NO wall-clock anywhere: the same inputs
    must produce the same bytes, or the file is useless as a regression
    artifact. Provenance comes from the input SHA256s instead of a date.
    """
    L = []
    A = L.append
    A("# FINDINGS-generated.md — machine output of tools\\uimap\\diff\\diff.py")
    A("")
    A("Regenerate with `python diff.py --auto --write-findings`. Do not hand-edit:")
    A("prose analysis belongs in `FINDINGS.md`, which cites this file.")
    A("")
    A("## Inputs")
    A("")
    A("| log | version | render | f | evidence | records | events | sha256[:12] |")
    A("|---|---|---|---|---|---|---|---|")
    for i in report["inputs"]["logs"]:
        rr = "x".join(str(v) for v in (i["render_res"] or []))or "-"
        A(f"| {i['name']} | {i['version'] or '-'} | {rr} | {i['factor']} | "
          f"{i['factor_evidence']} | {i['records']} | {i['events']} | "
          f"{i['sha256'][:12]} |")
    A("")
    A(f"- stock scripts: {report['inputs']['stock_script_ids']} ids from "
      f"`{report['inputs']['stock_scripts_dir']}`")
    A(f"- stock log oracles: {report['inputs']['stock_log_oracles'] or 'none'}")
    A(f"- predicted model: **{'available' if report['inputs']['model']['available'] else 'ABSENT'}** "
      f"— {report['inputs']['model']['reason']}")
    A("")
    A("## Summary")
    A("")
    A("```")
    A(json.dumps(report["summary"], indent=1, sort_keys=True))
    A("```")
    A("")

    A("## A. SCALE-EVENT self-check (strongest evidence: before+after on one line)")
    A("")
    bad = [r for r in report["event_check"] if r["verdict"] == "MISMATCH"]
    A(f"{len(report['event_check'])} transitions checked, **{len(bad)} MISMATCH**.")
    A("")
    if bad:
        A("| id | log | kind | stock rect | live | expect(edge) | delta | triage |")
        A("|---|---|---|---|---|---|---|---|")
        for r in bad:
            s = r["stock_rect"]
            A(f"| {r['id']} | {r['log']} | {r['kind']} | "
              f"({s['l']},{s['t']} {s['w']}x{s['h']}) | "
              f"{r['live_rect']['w']}x{r['live_rect']['h']} | "
              f"{r['expect_edge'][0]}x{r['expect_edge'][1]} | "
              f"{r['delta_vs_edge']} | {','.join(r['triage']) or '-'} |")
        A("")

    A("## B. LIVE vs STOCK")
    A("")
    for verdict, note in (
            ("STOCK-1X", "live size EQUALS stock while f!=1 — the scaler missed it"),
            ("OVER-SCALED", "live size equals round(stock*f*f) — scaled twice"),
            ("MISMATCH", "neither law reproduces the live size")):
        rows = [r for r in report["live_vs_stock"] if r["verdict"] == verdict]
        A(f"### {verdict} ({len(rows)}) — {note}")
        A("")
        if not rows:
            A("_none_")
            A("")
            continue
        A("| id | instr | parent | live | stock | expected | delta | vis | triage |")
        A("|---|---|---|---|---|---|---|---|---|")
        for r in rows[:120]:
            A(f"| {r['id']} | {r['instr']} | {r.get('parent_id') or '-'} | "
              f"{r['live'][0]}x{r['live'][1]} | "
              f"{r.get('stock', ['-', '-'])[0]}x{r.get('stock', ['-', '-'])[1]} | "
              f"{r.get('expected', ['-', '-'])[0]}x{r.get('expected', ['-', '-'])[1]} | "
              f"{r.get('delta', '-')} | {r.get('vis')} | "
              f"{','.join(r['triage']) or '-'} |")
        if len(rows) > 120:
            A(f"| … | _{len(rows) - 120} more in report.json_ | | | | | | | |")
        A("")

    A("## C. Model join")
    A("")
    if not report["summary"]["model_available"]:
        A(f"SKIPPED — {report['model_join'].get('note', 'model absent')}")
        A("")
        A("Live ids observed and therefore available to check a model against: "
          f"**{report['summary']['live_ids']}**.")
    else:
        mm = report["model_join"]["missing_from_model"]
        ml = report["model_join"]["missing_from_live"]
        A(f"- MISSING-FROM-MODEL: {len(mm)}")
        A(f"- MISSING-FROM-LIVE: {len(ml)}")
        A("")
        if mm:
            A("| id | seen in | triage |")
            A("|---|---|---|")
            for r in mm[:120]:
                A(f"| {r['id']} | {', '.join(r['seen_in'])} | "
                  f"{','.join(r['triage']) or '-'} |")
    A("")

    A("## D. Tier generality (offline)")
    A("")
    A("For each tier: how many (id, stock size) pairs the EDGE law and the")
    A("DIRECT law disagree on (a one-pixel class of bug that 2x cannot show),")
    A("and how many distinct stock sizes COLLAPSE onto the same scaled size")
    A("(where a size-based identification stops being unique).")
    A("")
    A("| f | edge-vs-direct divergent pairs | collapsing size groups |")
    A("|---|---|---|")
    for f in ("1", "1.5", "2", "3"):
        s = report["tier_sweep"].get(f)
        if s:
            A(f"| {f}x | {s['divergent_pairs']} | {s['collapsing_sizes']} |")
    A("")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="join predicted / live / stock geometry",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auto", action="store_true",
                    help="discover the current SC4UIScale log + the inert (f=1) "
                         "stock oracles")
    ap.add_argument("--history", action="store_true",
                    help="also include the .bak-*/.prev archive (older builds - "
                         "every fix since reads as a defect; use to validate the "
                         "detector, not to triage today)")
    ap.add_argument("--live-logs", nargs="*", default=None, metavar="LOG",
                    help="explicit log paths instead of --auto")
    ap.add_argument("--census", nargs="*", default=None,
                    help="pre-parsed *.census.json to include")
    ap.add_argument("--factor", type=float, default=None,
                    help="force the factor instead of reading it from the log")
    ap.add_argument("--scripts", default=None, help="stock .UI script dir")
    ap.add_argument("--tol", type=int, default=0,
                    help="pixel tolerance for MATCH (default 0 = exact)")
    ap.add_argument("--tier-sweep", action="store_true")
    ap.add_argument("--include-stock-logs", action="store_true",
                    help="also diff f=1 logs against stock (self-check)")
    ap.add_argument("--include-hidden", action="store_true",
                    help="do not apply the on-screen gate (floods with windows "
                         "inside closed dialogs - debugging only)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--write-findings", action="store_true")
    ap.add_argument("--fail-on", default="none",
                    choices=("none", "event-mismatch", "any"),
                    help="exit non-zero when the named class is non-empty")
    args = ap.parse_args(argv)

    if not (args.auto or args.live_logs or args.census or args.tier_sweep):
        ap.error("nothing to do: pass --auto, --live-logs, --census or --tier-sweep")

    report = run(args)

    print("\n=== SUMMARY ===")
    print(json.dumps(report["summary"], indent=1, sort_keys=True))
    if args.write_findings:
        dest = os.path.join(HERE, "FINDINGS-generated.md")
        write_findings(report, dest)
        print(f"wrote {dest}")

    if args.fail_on == "event-mismatch":
        n = report["summary"]["event_check"].get("MISMATCH", 0)
        return 1 if n else 0
    if args.fail_on == "any":
        s = report["summary"]["live_vs_stock"]
        n = (s.get("STOCK-1X", 0) + s.get("OVER-SCALED", 0) + s.get("MISMATCH", 0)
             + sum(v for k, v in s.items() if k.startswith("RECURRING-"))
             + report["summary"]["event_check"].get("MISMATCH", 0))
        return 1 if n else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
