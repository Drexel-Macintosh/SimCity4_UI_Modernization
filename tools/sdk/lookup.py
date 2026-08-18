"""
lookup.py - THE SDK QUERY. "What is this thing, and what do we already know?"

    python tools\\sdk\\lookup.py 0xAA8DEF97      window id
    python tools\\sdk\\lookup.py 46a006a6        art instance (any group)
    python tools\\sdk\\lookup.py ca8cbf0f        .UI script instance
    python tools\\sdk\\lookup.py 0x0079AD00      code VA
    python tools\\sdk\\lookup.py disaster        free text

WHY THIS EXISTS
---------------
Our findings live in prose - REGRESSION.md, the research MDs, source comments.
Prose ROTS: on 2026-07-31 four separate wrong theories were shipped because a
note was older than the code it described (laws 20/22/25), and the standing
order "check our previous work first" was slow to execute because the answer
was scattered across six files.

This tool answers the lookup in ONE call, and every fact it prints is either
GENERATED from a live source (source lists, the .UI corpus, staged corpora,
shipped dats) or quoted with its file:line so it can be re-checked. It states
what it did NOT find as explicitly as what it did - a null here is a null with
a stated positive control (law: NULL IS NOT EVIDENCE).

WHAT IT READS (all live, nothing cached, nothing hand-maintained)
  src\\UiSpike.cpp        every k*Ids list + kCityDialogIds bases + comments
  src\\ScaleTier.cpp      third-party dependency gates
  tools\\uiscripts\\extracted\\        the 330 stock .UI scripts
  tools\\dialog-static\\stage*\\       staged .UI + art per tier
  tools\\selective-safe\\stage*\\      staged art per tier
  tools\\dbpf\\extracted\\             stock art (for sizes)
  _tests\\REGRESSION.md, VERSION-HISTORY.txt, tools\\research\\*.md
  the live Plugins folder (who ships it, who WINS the load order)

DESIGN RULE: this file must never contain a FACT. Only how to find facts.
A hardcoded finding here would rot exactly like the prose it replaces.
"""
import os
import re
import sys

# A LOOKUP TOOL THAT CRASHES ON ITS OWN OUTPUT IS WORSE THAN NO TOOL: the
# Windows console is cp1252 here and killed the first run on a single "warning"
# glyph AFTER printing the findings. Reconfigure defensively, and keep the
# body ASCII-only anyway (belt and braces - stdout may be a pipe or a file).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # ...\SC4TouchControls
SRC = os.path.join(ROOT, "src")
TOOLS = os.path.join(ROOT, "tools")
TESTS = os.path.join(ROOT, "_tests")
RESEARCH = os.path.join(TOOLS, "research")
CORPUS = os.path.join(TOOLS, "uiscripts", "extracted")
import sys as _sys
_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS not in _sys.path:
    _sys.path.insert(0, _TOOLS)
from sc4paths import plugins_dir     # noqa: E402
# Resolved, not hard-coded: $SC4_PLUGINS, else the shell's Documents,
# else the OneDrive-redirected or plain %USERPROFILE% variant. See
# tools/sc4paths.py for why a literal path here was a bug, not a shortcut.
PLUGINS = plugins_dir(require=True)

DOCS = [
    os.path.join(TESTS, "REGRESSION.md"),
    os.path.join(ROOT, "VERSION-HISTORY.txt"),
    os.path.join(ROOT, "HANDOFF.md"),
    # THE BUILDERS ARE DOCS TOO. KNOWN_BUILDER_DISAGREEMENTS and the
    # CODE_BOUND_* comments carry decisions that exist nowhere else - the a6
    # scrollbar truth ("SetImage derives cellW = artW/12 and RESIZES the
    # window") lives only here. Omitting them made this tool's first run miss
    # the newest finding about the very id being queried.
    os.path.join(TOOLS, "dialog-static", "build_dialog_static.py"),
    os.path.join(TOOLS, "selective-safe", "build_selective_safe.py"),
]


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# TREES THAT MUST NEVER BE QUOTED AS CURRENT KNOWLEDGE.
# A lookup tool that reads stale prose just launders it. _HANDOFF-* bundles
# carry FROZEN 2026-07-21..24 copies of live docs (verified: the bundled
# GOD-MODE-FLYOUTS.md still calls Create Disaster "UNSOLVED" weeks after it
# was solved). dist/ and _working-backup/ are shipped/frozen snapshots too.
# _incoming/ is RAW agent output - useful as leads, never as evidence - so it
# is searched but LABELLED rather than excluded.
EXCLUDE_DIRS = ("_HANDOFF-SimCity4-Complete", "dist", "_working-backup",
                "superseded", "_archive", "__pycache__", ".git")
UNTRUSTED_DIRS = ("_incoming", "_checkpoints")


def _excluded(path):
    parts = os.path.normpath(path).split(os.sep)
    return any(d in parts for d in EXCLUDE_DIRS)


def _trust(path):
    parts = os.path.normpath(path).split(os.sep)
    if any(d in parts for d in UNTRUSTED_DIRS):
        return "  [RAW AGENT OUTPUT - lead, not evidence; verify before citing]"
    return ""


def _iter_docs():
    for p in DOCS:
        if os.path.isfile(p) and not _excluded(p):
            yield p
    for base in (RESEARCH,):
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            if _excluded(root):
                continue
            for name in sorted(files):
                if name.lower().endswith((".md", ".txt")):
                    yield os.path.join(root, name)


def _hits(text, needles):
    """Line hits for any needle, case-insensitive."""
    out = []
    low = [n.lower() for n in needles]
    for i, line in enumerate(text.split("\n"), 1):
        ll = line.lower()
        if any(n in ll for n in low):
            out.append((i, line.strip()))
    return out


def _forms(q):
    """Every spelling a 32-bit id might appear as."""
    forms = {q, q.lower(), q.upper()}
    m = re.fullmatch(r"(?:0x)?([0-9a-fA-F]{1,8})", q)
    if m:
        v = int(m.group(1), 16)
        for f in ("%08x", "%08X", "0x%08x", "0x%08X", "%x", "%X"):
            forms.add(f % v)
    return sorted(f for f in forms if len(f) >= 4)


def section(title):
    print("\n" + "=" * 74)
    print(title)
    print("=" * 74)


def report_source(forms):
    """Which of OUR lists claim this id, with the surrounding comment."""
    section("1. OUR SOURCE - which lists claim it, and what the comment says")
    found = False
    for fname in ("UiSpike.cpp", "ScaleTier.cpp", "CodePatches.cpp",
                  "Settings.h", "SC4UIScaleDllDirector.cpp"):
        path = os.path.join(SRC, fname)
        text = _read(path)
        if not text:
            continue
        lines = text.split("\n")
        for i, line in enumerate(lines, 1):
            if not any(f in line for f in forms):
                continue
            found = True
            # Walk up for the nearest list/struct/function header - but STOP at
            # the first line that CLOSES a block. Without that stop this
            # happily attributed a standalone `const uintptr_t kFoo = ...;` to
            # whatever array happened to be declared 50 lines above it, which
            # is a false claim of membership - exactly the kind of confident
            # wrong note this tool exists to stop (found 2026-07-31 when
            # 0x0079388F reported "in: kPopupStyleRetargets").
            # 160-line lookback: our tables carry long per-entry comment
            # blocks (kCityDialogIds' last entry sits 76 lines under its
            # header, and the old 60-line window silently reported it as
            # belonging to nothing). Safe to widen only because of the
            # block-close stop below.
            owner = ""
            for k in range(i - 1, max(0, i - 160), -1):
                s = lines[k - 1]
                if re.match(r"^\s*\}", s):
                    break  # a sibling block ended here; nothing above owns us
                m = re.search(r"(k[A-Za-z0-9_]+)\s*\[\]|"
                              r"^\s*(?:const\s+)?[A-Za-z_][\w:<>*&\s]*\b"
                              r"([A-Za-z_]\w*)\s*\(", s)
                if m:
                    owner = (m.group(1) or m.group(2) or "").strip()
                    if owner:
                        break
            print("  %s:%d  %s" % (fname, i, line.strip()[:110]))
            if owner:
                print("        in: %s" % owner)
    if not found:
        print("  (no hit in src\\ - POSITIVE CONTROL: this scan DOES find ids")
        print("   like 0xAA8DEF97; an empty result means our code never names it,")
        print("   so any mechanism touching it is generic, not id-keyed.)")


def report_corpus(forms):
    """Scripts that DECLARE it (root/child id) or REFERENCE it (art)."""
    section("2. .UI CORPUS - who declares it, who draws it")
    if not os.path.isdir(CORPUS):
        print("  (corpus missing)")
        return
    as_id, as_art = [], []
    for name in sorted(os.listdir(CORPUS)):
        if not name.lower().endswith(".ui"):
            continue
        text = _read(os.path.join(CORPUS, name))
        for f in forms:
            if ("id=0x" + f.lower().replace("0x", "")) in text.lower():
                as_id.append(name)
                break
        low = text.lower()
        if any(("{" in low and f.lower().replace("0x", "") in low) for f in forms):
            if re.search(r"image=\{[0-9a-f]+,\s*(?:%s)\}"
                         % "|".join(re.escape(f.lower().replace("0x", ""))
                                    for f in forms), low):
                as_art.append(name)
    declaring = []
    if as_id:
        print("  DECLARED as a window id in %d script(s):" % len(as_id))
        for n in as_id:
            m = re.search(r"I-([0-9a-fA-F]{8})", n)
            if m:
                declaring.append(m.group(1).lower())
        for n in as_id[:12]:
            print("    " + n)
            # print the declaring line's area= so the 1x design size is free
            t = _read(os.path.join(CORPUS, n))
            for ln in t.split("\n"):
                if any(("id=0x" + f.lower().replace("0x", "")) in ln.lower()
                       for f in forms):
                    a = re.search(r"area=\((\d+),(\d+),(\d+),(\d+)\)", ln)
                    c = re.search(r"clsid=([^\s]+)", ln)
                    if a:
                        l, t2, r, b = (int(x) for x in a.groups())
                        print("      1x design %dx%d  %s"
                              % (r - l, b - t2, c.group(1) if c else ""))
                    break
    if as_art:
        print("  REFERENCED as art by %d script(s): %s"
              % (len(as_art), ", ".join(as_art[:8])))
    if not as_id and not as_art:
        print("  (no script declares or references it)")
        print("  POSITIVE CONTROL: this scan finds e.g. 2a2aed99's children and")
        print("  46a006a6's single referrer. An empty result is real evidence")
        print("  that the thing is CODE-bound - look in the exe, not the data.")
    return declaring


def report_staged(forms, extra=None):
    """Do we ship a scaled copy, at which tiers, and at what size?"""
    section("3. WHAT WE SHIP - staged copies per tier (art + scripts)")
    # A WINDOW id and its SCRIPT instance are different numbers, and staged
    # files are named by SCRIPT. Searching only the window id here produced a
    # FALSE "we stage no copy" on the very first smoke test - exactly the kind
    # of null this tool exists to kill. Fold in the declaring script(s).
    forms = list(forms) + [e for e in (extra or []) if e]
    if extra:
        print("  (also matching declaring script instance: %s)" % ", ".join(extra))
    stages = []
    for base, tiers in (
        (os.path.join(TOOLS, "dialog-static"), ("stage", "stage-15x", "stage-3x")),
        (os.path.join(TOOLS, "selective-safe"), ("stage", "stage-15x", "stage-3x")),
    ):
        for t in tiers:
            d = os.path.join(base, t)
            if os.path.isdir(d):
                stages.append((os.path.basename(base) + "/" + t, d))
    any_hit = False
    for label, d in stages:
        for name in os.listdir(d):
            low = name.lower()
            # ⛔ A TGI PAIR IS TWO TOKENS, NOT ONE SUBSTRING (#164).
            # `forms` may contain a pair like "46a006b0:14416315". Staged files
            # are named T-0x<t>_G-0x<g>_I-0x<i>.png, so that pair matches NO
            # filename and this test silently skipped every real hit - then the
            # caller printed "we stage no copy of this at any tier" and offered
            # a diagnosis built on it. Measured: `lookup.py 14416315` found the
            # sheet at all three tiers while `lookup.py 46a006b0:14416315`
            # denied it existed. This project writes TGIs as pairs everywhere,
            # so the pair form is the NATURAL query and the one that lied.
            # A separator now splits the form and EVERY part must appear.
            if not any(all(part in low for part in
                           f.lower().replace("0x", "").replace(",", ":")
                            .replace("{", "").replace("}", "").split(":") if part)
                       for f in forms):
                continue
            any_hit = True
            path = os.path.join(d, name)
            if low.endswith(".png"):
                try:
                    from PIL import Image
                    print("  %-26s %s  %s" % (label, name[-28:], Image.open(path).size))
                except Exception:
                    print("  %-26s %s" % (label, name[-28:]))
            elif low.endswith(".ui"):
                a = re.search(r"area=\((\d+),(\d+),(\d+),(\d+)\)", _read(path))
                if a:
                    l, t2, r, b = (int(x) for x in a.groups())
                    print("  %-26s %s  root %dx%d" % (label, name[-28:], r - l, b - t2))
    if not any_hit:
        print("  (we stage no copy of this at any tier)")
        print("  => if it renders 1x inside a 2x window, THAT is why. If it")
        print("     renders correctly anyway, the game sizes it from something")
        print("     other than this art (law 25).")


def report_owner(forms):
    """Who WINS the load order on the live machine."""
    section("4. LOAD ORDER - who ships this TGI, who WINS")
    tool = os.path.join(TOOLS, "dbpf", "who_owns_tgi.py")
    if not os.path.isfile(tool):
        print("  (who_owns_tgi.py missing)")
        return
    inst = None
    for f in forms:
        m = re.fullmatch(r"(?:0x)?([0-9a-fA-F]{8})", f)
        if m:
            inst = "0x" + m.group(1)
            break
    if not inst:
        print("  (not an 8-hex instance - skipped)")
        return
    print("  run:  python tools\\dbpf\\who_owns_tgi.py %s" % inst)
    print("        (add --group 0x46a006b0 for art; it prints every holder in")
    print("         load order and names the winner - the ONLY way to see a")
    print("         third-party owner, which a stock-vs-ours diff cannot)")


def report_docs(forms, raw):
    """Everything we have already written, newest sources first."""
    section("5. WHAT WE ALREADY WROTE (read before theorising - standing order)")
    needles = list(forms) + ([raw] if len(raw) >= 4 else [])
    total = 0
    for path in _iter_docs():
        hits = _hits(_read(path), needles)
        if not hits:
            continue
        rel = os.path.relpath(path, ROOT)
        print("\n  --- %s (%d hit%s)" % (rel, len(hits), "" if len(hits) == 1 else "s"))
        for ln, txt in hits[:6]:
            print("    :%-5d %s" % (ln, txt[:104]))
        if len(hits) > 6:
            print("    ... %d more" % (len(hits) - 6))
        total += len(hits)
    if not total:
        print("  (nothing written yet - you are first. Write it down when done:")
        print("   REGRESSION.md for the runbook, the research MD for mechanism.)")
    else:
        print("\n  !! LAW 20/22: the older the note, the more confidently wrong it")
        print("    may be. Anything predating the last mechanism change on this")
        print("    family must be re-verified before you reason from it.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    raw = sys.argv[1]
    forms = _forms(raw)
    print("SDK LOOKUP: %s" % raw)
    print("matching forms: %s" % ", ".join(forms))
    report_source(forms)
    declaring = report_corpus(forms) or []
    report_staged(forms, declaring)
    report_owner(forms)
    report_docs(forms, raw)
    section("NEXT")
    print("  TRIAGE.md matches the SYMPTOM to a solved family.")
    print("  MECHANISM-GENERATIONS.md says which generation the family is on.")
    print("  SC4-UI-ENGINE.md 4.7 picks the cure from HOW THE WINDOW IS BORN.")
    print("  Then measure. Every MEASURED value in this project landed first")
    print("  try; every inferred one cost 2-3 builds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
