#!/usr/bin/env python3
r"""WHICH FILE WINS? - a load-order winner table for any Plugins layout.

WHY THIS EXISTS. Every load-order claim in a package redesign ("move this dat
into that folder and it will still win") is a claim about the DBPF merge, and
until now nothing in this repo could measure it for an ARBITRARY layout.
`tools\itemicons\coverage_by_loadorder.py` gets the rule right but is welded to
one resource type (ItemIcons) and one tree; `tools\dbpf\who_owns_tgi.py` gets
the rule right for one TGI but resolves `plugins_dir(require=True)` at import,
so it can only ever answer for the tree that happens to be installed. Neither
can answer "if I move these files, what changes?" - which is the only question
a release gate actually asks.

THE RULE (SC4's DBPF resolution, README.md:272, docs/BUILDING.md:82):

    game archives  ->  <install>\Plugins  ->  <Documents>\SimCity 4\Plugins

  and inside each Plugins tree, at every directory level, FILES load before
  SUBFOLDERS, each group alphabetically. For a duplicate TGI the LAST loaded
  WINS. A root dat can therefore never override a subfolder dat - which is why
  overrides of another mod's data ship from `zzz-SC4UIScale\`.

USAGE

    python winner_table.py                      # live tree, readable table
    python winner_table.py --tree D:\stage\Plugins
    python winner_table.py --diff A\Plugins B\Plugins     # the RELEASE GATE
    python winner_table.py --json
    python winner_table.py --selfcheck          # controls only; exit != 0 = red

`--diff` prints one line per TGI whose WINNING FILE CHANGES between the two
layouts, stable-sorted, `TGI  A-winner  ->  B-winner`. Empty output means the
layouts resolve identically - which is what a safe move looks like.

HOW `.x1-disabled` IS HANDLED, AND WHY IT IS NOT A SPECIAL CASE. `ScaleTier`
stashes an inactive tier by renaming `foo.dat` -> `foo.dat.x1-disabled`. The
game does not have a list of stash suffixes: it loads a file if the file's
extension is a DBPF extension, and `.x1-disabled` is not one. This tool models
exactly that - `loaded()` looks at the FINAL extension - so `.compare-off`,
`.double-load-disabled` and any future stash suffix are excluded for free, and
`FontStyle.ini.x1-disabled` (an ini, not a dat) is correctly ignored either way.
Stashed files of OURS are still opened, but only to build the key universe: the
release gate has to answer for the tiers that are on disk, not just the one
that happens to be staged tonight.

POSITIVE CONTROLS (`--selfcheck`, and run before EVERY report). A winner table
that reports zero contested keys is indistinguishable from a table whose parser
silently returned nothing, and this project has already paid for that twice
(#140's confident "not in any archive", #139's Rail icon). So the tool refuses
to print a table until three things it MUST be able to see have been seen:

  a) `z_SC4UIScale_ZCarbonUI-*` and `z_SC4UIScale_DialogStatic-*` really do
     contest keys, and the comparator puts ZCarbonUI last (`zzz-SC4UIScale\`
     sorts after `010-SC4UIScale\`).  Measured: 197 keys per tier.
  b) at least one CAM-owned `.UI` script outranks our DialogStatic package -
     proves the tool sees type-0 (.UI) entries AND orders `050-load-first\`
     after `010-SC4UIScale\`. (Our own `zzz-` packages then win those keys
     back; that is the point of shipping them from `zzz-`, and it is why this
     control is a PAIRWISE check and not a "third party wins" count.)
  c) the game's own archives are reachable and actually resolve keys - at
     least one TGI in the merged keyspace must be won by a stock archive.
     Without this the tool would happily report a Documents-only view and call
     it complete.

Each control prints the numbers it measured. A control that cannot find its
subject FAILS - it never passes by absence.

Read-only. Never writes to the game or Plugins directories. Never launches the
game.
"""

import argparse
import glob
import json
import os
import struct
import sys
from collections import defaultdict

_TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
from sc4paths import game_dir, plugins_dir            # noqa: E402

# Extensions the DBPF loader actually opens. A file whose FINAL extension is
# not one of these is not loaded - that is the whole `.x1-disabled` mechanism.
DBPF_EXTS = (".dat", ".sc4lot", ".sc4desc", ".sc4model", ".sc4")
OURS_PREFIX = "z_sc4uiscale_"

# The stock archives, in the order who_owns_tgi.py has always used. Anything
# else found in the install root (Intro.dat, Sound.dat, an expansion) is
# appended alphabetically rather than being left out - a hand-written archive
# list is what made #140's splash bug invisible. This ordering only decides
# WHICH stock archive gets named when two of them carry the same TGI; it can
# never change whether a Plugins file wins, because every Plugins file outranks
# every archive.
_ARCHIVE_ORDER = ["simcity_1.dat", "simcity_2.dat", "simcity_3.dat",
                  "simcity_4.dat", "simcity_5.dat", "ep1.dat",
                  "simcitylocale.dat"]

UI_TYPE = 0x00000000          # .UI / LUA script entries
LAYER_ARCHIVE, LAYER_GAME_PLUGINS, LAYER_TREE = 0, 1, 2

# MEASURED 2026-08-29 on the live tree, all three tiers (15x/2x/3x), by
# intersecting the two packages' DBPF indices: 197 keys, of which 88 are
# 0x856DDBAC (PNG) and 109 are 0x00000000 (.UI). ZCarbonUI is a strict subset
# of DialogStatic's 265. If this number moves, the PACKAGES changed - re-pin it
# only after reading the bytes and understanding which entries appeared or
# vanished, never to make the control go green.
EXPECT_ZCARBON_DIALOG = 197


# --------------------------------------------------------------------------
# DBPF
# --------------------------------------------------------------------------

def lp(path):
    r"""Windows long-path form. NAM nests dats past MAX_PATH (298 chars); a
    bare open() throws FileNotFoundError on files that plainly exist, and a
    swallowed error reads as "no resources here"."""
    if os.name == "nt" and len(path) > 240 and not path.startswith("\\\\?\\"):
        return "\\\\?\\" + os.path.abspath(path)
    return path


def dbpf_keys(path):
    """Yield (type, group, instance) for every entry in a DBPF index.

    Header layout is the one find_tgi.py pinned: 0x24 index entry count,
    0x28 index offset, 0x2C index size; the stride follows from size/count
    (20 bytes for the DBPF 1.0 / index 7.0 files SC4 ships).
    """
    try:
        with open(lp(path), "rb") as f:
            hdr = f.read(96)
            if len(hdr) < 96 or hdr[:4] != b"DBPF":
                return
            count, idx_off, idx_size = struct.unpack_from("<III", hdr, 0x24)
            if not count or count > 4_000_000:
                return
            stride = idx_size // count
            if stride < 20:
                return
            f.seek(idx_off)
            blob = f.read(idx_size)
        if len(blob) < count * stride:
            count = len(blob) // stride
        for k in range(count):
            t, g, i, _off, _sz = struct.unpack_from("<IIIII", blob, k * stride)
            yield (t, g, i)
    except (OSError, struct.error):
        # A corrupt or locked dat must not abort the sweep, but it must not
        # pass for an empty one either - callers count what came back.
        return


# --------------------------------------------------------------------------
# load order
# --------------------------------------------------------------------------

def loaded(fn):
    """True if SC4 would open this filename. The ONLY test is the final
    extension, which is exactly why renaming to `.x1-disabled` disables."""
    return os.path.splitext(fn)[1].lower() in DBPF_EXTS


def stashed_dbpf(fn):
    """True if stripping ONE trailing extension leaves a DBPF name -
    i.e. `foo.dat.x1-disabled`, `foo.dat.compare-off`, or any future suffix.
    Deliberately suffix-agnostic: a hard-coded stash list ages badly."""
    if loaded(fn):
        return False
    return loaded(os.path.splitext(fn)[0])


def is_ours(fn):
    return os.path.basename(fn).lower().startswith(OURS_PREFIX)


def tree_rank(rel):
    r"""Load order WITHIN one Plugins tree.

    At each directory level FILES (0) come before SUBFOLDERS (1), each
    alphabetically; later compares greater and therefore WINS. `a.dat` at the
    root gives ((0,'a.dat'),); `b\c.dat` gives ((1,'b'),(0,'c.dat')) - and
    (0,...) < (1,...), so the root file loses to the subfolder file. That one
    comparison is the Rail-icon defect in a single line.
    """
    parts = rel.split(os.sep)
    return tuple((0 if i == len(parts) - 1 else 1, p.lower())
                 for i, p in enumerate(parts))


def discover_archives(game):
    """Every DBPF archive in the install root, de-duplicated case-insensitively
    (the install mixes `.dat` and `.DAT`) and ordered per _ARCHIVE_ORDER."""
    if not game or not os.path.isdir(game):
        return []
    seen = {}
    for pat in ("*.dat", "*.DAT"):
        for p in glob.glob(os.path.join(game, pat)):
            seen[os.path.basename(p).lower()] = os.path.basename(p)
    return [seen[k] for k in sorted(
        seen, key=lambda n: (_ARCHIVE_ORDER.index(n)
                             if n in _ARCHIVE_ORDER else 99, n))]


class Layout(object):
    """One resolved layout: providers per TGI, in load order."""

    def __init__(self, tree, game, use_game=True):
        self.tree = os.path.abspath(tree) if tree else None
        self.game = game if (game and use_game) else None
        self.providers = defaultdict(list)   # key -> [(rank, label, ours)]
        self.our_keys_loaded = set()
        self.our_keys_stashed = set()
        self.our_files = {}                  # label -> (rank, keys, stashed)
        self.archives = []
        self.archive_entries = 0
        self.files_loaded = 0
        self.files_stashed = 0
        self.game_plugins_files = 0
        self.notes = []
        self._build(use_game)

    # -- construction ------------------------------------------------------
    def _add(self, rank, label, path, ours, stash):
        keys = set(dbpf_keys(path))
        if ours:
            self.our_files[label] = (rank, keys, stash)
            (self.our_keys_stashed if stash else self.our_keys_loaded).update(keys)
        if stash:
            return
        for k in keys:
            self.providers[k].append((rank, label, ours))

    def _scan_tree(self, root, layer, prefix):
        if not root or not os.path.isdir(root):
            return 0
        n = 0
        for dirpath, _dirs, files in os.walk(root):
            for fn in files:
                lo, st = loaded(fn), stashed_dbpf(fn)
                if not lo and not st:
                    continue
                p = os.path.join(dirpath, fn)
                rel = os.path.relpath(p, root)
                label = prefix + rel
                ours = is_ours(fn)
                # Stashed third-party files are neither loaded nor part of our
                # key universe; count them and move on.
                if st and not ours:
                    self.files_stashed += 1
                    continue
                if st:
                    self.files_stashed += 1
                else:
                    self.files_loaded += 1
                    n += 1
                self._add((layer, tree_rank(rel)), label, p, ours, st)
        return n

    def _build(self, use_game):
        if self.game:
            self.archives = discover_archives(self.game)
            for n, name in enumerate(self.archives):
                p = os.path.join(self.game, name)
                keys = set(dbpf_keys(p))
                self.archive_entries += len(keys)
                rank = (LAYER_ARCHIVE, ((0, "%04d" % n),))
                for k in keys:
                    self.providers[k].append((rank, "<archives>/" + name, False))
            if not self.archives:
                self.notes.append(
                    "NO archives found in %s - the stock layer is MISSING "
                    "from this report." % self.game)
            self.game_plugins_files = self._scan_tree(
                os.path.join(self.game, "Plugins"),
                LAYER_GAME_PLUGINS, "<gamePlugins>/")
        elif use_game:
            self.notes.append(
                "GAME INSTALL NOT FOUND - no stock archives and no "
                "<install>\\Plugins in this report. Set SC4_GAME_DIR.")
        else:
            self.notes.append(
                "--no-game given - stock archives and <install>\\Plugins were "
                "NOT scanned. This report covers the Plugins tree ONLY.")
        self._scan_tree(self.tree, LAYER_TREE, "")

    # -- queries -----------------------------------------------------------
    def key_universe(self, mode):
        if mode == "all":
            return set(self.providers)
        if mode == "ours-loaded":
            return set(self.our_keys_loaded)
        return set(self.our_keys_loaded) | set(self.our_keys_stashed)

    def winner(self, key):
        """(label, ours) of the file that loads LAST for this TGI, or None."""
        v = self.providers.get(key)
        if not v:
            return None
        rank, label, ours = max(v, key=lambda x: x[0])
        return (label, ours)

    def n_providers(self, key):
        return len(self.providers.get(key, ()))


def tgi(key):
    return "%08X-%08X-%08X" % key


def klass(win):
    if win is None:
        return "none"
    if win[1]:
        return "ours"
    return "stock" if win[0].startswith("<archives>/") else "third"


# --------------------------------------------------------------------------
# positive controls
# --------------------------------------------------------------------------

class Control(object):
    def __init__(self, cid, title):
        self.id, self.title, self.ok, self.lines = cid, title, False, []

    def say(self, msg):
        self.lines.append(msg)

    def report(self):
        head = "[%s] %-46s %s" % (self.id, self.title,
                                  "FIRED" if self.ok else "*** FAILED ***")
        return "\n".join([head] + ["      " + l for l in self.lines])


def _match_our(layout, needle):
    """Our package files whose basename contains `needle`, stash or not."""
    out = []
    for label, (rank, keys, stash) in layout.our_files.items():
        if needle.lower() in os.path.basename(label).lower():
            out.append((label, rank, keys, stash))
    return sorted(out)


def control_a(layout):
    r"""ZCarbonUI and DialogStatic really contest keys, and ZCarbonUI wins.

    This is a control on the COMPARATOR, not on tonight's staging: on this
    machine every ZCarbonUI tier is `.x1-disabled` (Carbon skin off), so a
    check written against the loaded set would silently measure nothing and
    call it a pass. Pairing by tier tag and comparing the files' NOMINAL ranks
    keeps the control alive at every tier.
    """
    c = Control("a", "ZCarbonUI outranks DialogStatic")
    carb = _match_our(layout, "ZCarbonUI")
    dial = _match_our(layout, "DialogStatic")
    if not carb or not dial:
        c.say("could not find both packages (ZCarbonUI=%d DialogStatic=%d). "
              "A control that cannot find its subject FAILS." % (len(carb), len(dial)))
        return c

    def tier(label):
        base = os.path.basename(label).lower()
        for t in ("-15x", "-2x", "-3x", "-1x"):
            if t in base:
                return t
        return ""

    # Deploy-OnGameClose lays down BOTH `X-<tag>.dat` and a refreshed
    # `X-<tag>.dat.x1-disabled` twin, so a tier can legitimately appear twice.
    # De-duplicate on the OUTCOME, or the same tier reports as two pairs and a
    # mismatch prints twice (TRIAGE.md, the duplicated-slot trap).
    npairs, outcomes = 0, set()
    for cl, crank, ckeys, cst in carb:
        for dl, drank, dkeys, dst in dial:
            if tier(cl) != tier(dl):
                continue
            npairs += 1
            outcomes.add((tier(cl) or "(untagged)", len(ckeys & dkeys),
                          crank > drank))
    if not outcomes:
        c.say("no tier-matched pair found among %d/%d files - control is a null."
              % (len(carb), len(dial)))
        return c
    bad = [o for o in outcomes
           if o[1] != EXPECT_ZCARBON_DIALOG or not o[2]]
    for t, inter, later in sorted(outcomes):
        c.say("%-10s intersection=%d  ZCarbonUI sorts later=%s%s"
              % (t, inter, later,
                 "   <-- MISMATCH, expected %d" % EXPECT_ZCARBON_DIALOG
                 if (t, inter, later) in bad else ""))
    if bad:
        c.say("%d tier(s) disagree with the pinned %d. The PACKAGES changed - "
              "read the bytes before re-pinning." % (len(bad),
                                                     EXPECT_ZCARBON_DIALOG))
        return c
    c.say("%d distinct tier(s) over %d file pair(s) (stashed twins included), "
          "every one at %d keys with zzz-SC4UIScale\\ last"
          % (len(outcomes), npairs, EXPECT_ZCARBON_DIALOG))
    c.ok = True
    return c


def _is_cam(label):
    """CAM ships as `cam.<pkg>.sc4pac\\...\\CAM_*.dat` (sc4pac) or a `CAM`
    folder. Match on any path part, so a re-layout does not blind the control."""
    for part in label.replace("/", os.sep).split(os.sep):
        p = part.lower()
        if p.startswith("cam.") or p.startswith("cam_") or p == "cam":
            return True
    return False


def control_b(layout):
    """At least one CAM-owned .UI script outranks our DialogStatic package."""
    c = Control("b", "a CAM .UI script outranks DialogStatic")
    dial = [x for x in _match_our(layout, "DialogStatic") if not x[3]] \
        or _match_our(layout, "DialogStatic")
    if not dial:
        c.say("no DialogStatic package on disk - control is a null.")
        return c
    label, rank, keys, stash = dial[0]
    c.say("subject: %s%s" % (label, "  (STASHED)" if stash else ""))
    beat = defaultdict(list)
    for k in keys:
        for prank, plabel, pours in layout.providers.get(k, ()):
            if not pours and prank > rank and _is_cam(plabel):
                beat[plabel].append(k)
    if not beat:
        c.say("NO CAM file outranks it on any of its %d keys. Either CAM is "
              "not installed or the tool cannot see type-0 (.UI) entries - "
              "both are failures of this control, not passes." % len(keys))
        return c
    ui_total = 0
    for plabel, ks in sorted(beat.items(), key=lambda x: (-len(x[1]), x[0])):
        ui = [k for k in ks if k[0] == UI_TYPE]
        ui_total += len(ui)
        c.say("%-64s %3d keys (%d are .UI)" % (plabel[-64:], len(ks), len(ui)))
        if ui:
            c.say("   e.g. %s beaten by the line above" % tgi(sorted(ui)[0]))
    if not ui_total:
        c.say("CAM outranks it, but on ZERO type-0 entries - the .UI layer is "
              "invisible to this run.")
        return c
    c.say("%d CAM file(s), %d contested keys, %d of them .UI scripts"
          % (len(beat), sum(len(v) for v in beat.values()), ui_total))
    c.ok = True
    return c


def control_c(layout):
    """The stock layer is reachable AND actually resolves keys."""
    c = Control("c", "stock archives reachable and winning keys")
    if not layout.game:
        c.say("no game install in this run - the stock layer was never read.")
        return c
    if not layout.archives:
        c.say("game dir %s holds NO archives." % layout.game)
        return c
    c.say("%d archive(s) in %s, %d index entries"
          % (len(layout.archives), layout.game, layout.archive_entries))
    by_archive = defaultdict(int)
    example = None
    for k in layout.providers:
        w = layout.winner(k)
        if w and w[0].startswith("<archives>/"):
            by_archive[w[0]] += 1
            if example is None:
                example = (k, w[0])
    total = sum(by_archive.values())
    if not total:
        c.say("ZERO keys in the merged keyspace resolve to a stock archive - "
              "the archives parsed but never won anything, which means this "
              "report is effectively Documents-only.")
        return c
    c.say("%d of %d merged keys are won by a stock archive"
          % (total, len(layout.providers)))
    for name in sorted(by_archive, key=lambda n: -by_archive[n])[:4]:
        c.say("   %-30s %6d" % (name, by_archive[name]))
    c.say("example: %s -> %s" % (tgi(example[0]), example[1]))
    ours = layout.key_universe("ours")
    withstock = sum(1 for k in ours
                    if any(l.startswith("<archives>/")
                           for _r, l, _o in layout.providers.get(k, ())))
    c.say("of OUR %d keys, %d are also supplied by a stock archive "
          "(i.e. genuine overrides, not invented TGIs)" % (len(ours), withstock))
    c.ok = True
    return c


def run_controls(live_tree, game, verbose=True):
    """Build the LIVE layout and run all three controls. Returns (ok, layout)."""
    if not live_tree or not os.path.isdir(live_tree):
        print("SELFCHECK CANNOT RUN: live Plugins tree not found (%s).\n"
              "Set SC4_PLUGINS, or pass --skip-selfcheck and accept that "
              "NOTHING has verified this run." % live_tree, file=sys.stderr)
        return False, None
    lay = Layout(live_tree, game, use_game=True)
    cs = [control_a(lay), control_b(lay), control_c(lay)]
    if verbose:
        print("=== POSITIVE CONTROLS on the LIVE tree ===")
        print("    %s" % live_tree)
        for n in lay.notes:
            print("    !! %s" % n)
        for c in cs:
            print(c.report())
        print("    %d/%d controls fired" % (sum(1 for c in cs if c.ok), len(cs)))
        print()
    return all(c.ok for c in cs), lay


# --------------------------------------------------------------------------
# reports
# --------------------------------------------------------------------------

def build_rows(lay, mode):
    rows = []
    for k in sorted(lay.key_universe(mode)):
        w = lay.winner(k)
        rows.append({
            "tgi": tgi(k),
            "type": "%08X" % k[0], "group": "%08X" % k[1],
            "instance": "%08X" % k[2],
            "providers": lay.n_providers(k),
            "winner": w[0] if w else "(none - no loaded file supplies it)",
            "winner_class": klass(w),
        })
    return rows


def summarise(rows):
    c = {"examined": len(rows), "contested": 0, "winner_ours": 0,
         "winner_third_party": 0, "winner_stock_archive": 0, "no_winner": 0}
    for r in rows:
        if r["providers"] > 1:
            c["contested"] += 1
        k = r["winner_class"]
        if k == "ours":
            c["winner_ours"] += 1
        elif k == "stock":
            c["winner_stock_archive"] += 1
            c["winner_third_party"] += 1
        elif k == "third":
            c["winner_third_party"] += 1
        else:
            c["no_winner"] += 1
    return c


def print_table(lay, rows, args):
    print("=== WINNER TABLE ===")
    print("tree      : %s" % lay.tree)
    print("game      : %s" % (lay.game or "(not scanned)"))
    for n in lay.notes:
        print("!! %s" % n)
    print("files     : %d loaded, %d stashed; %d archive(s)/%d entries; "
          "%d in <install>\\Plugins"
          % (lay.files_loaded, lay.files_stashed, len(lay.archives),
             lay.archive_entries, lay.game_plugins_files))
    print("keys      : %s" % args.keys)
    print()
    shown = [r for r in rows
             if args.only == "all"
             or (args.only == "contested" and r["providers"] > 1)
             or args.only == r["winner_class"]]
    if args.limit and len(shown) > args.limit:
        tail = len(shown) - args.limit
        shown = shown[:args.limit]
    else:
        tail = 0
    print("%-26s %-5s %-6s %s" % ("TGI (type-group-inst)", "prov", "class",
                                  "WINNER"))
    for r in shown:
        print("%-26s %5d %-6s %s"
              % (r["tgi"], r["providers"], r["winner_class"], r["winner"]))
    if tail:
        print("... %d more (raise --limit, narrow with --only, or use --json)"
              % tail)
    print()
    c = summarise(rows)
    print("TGIs examined                  : %d" % c["examined"])
    print("contested (more than 1 provider): %d" % c["contested"])
    print("winners that are OURS           : %d" % c["winner_ours"])
    print("winners that are THIRD-PARTY    : %d (of which stock archives: %d)"
          % (c["winner_third_party"], c["winner_stock_archive"]))
    print("no loaded file supplies it      : %d" % c["no_winner"])


def do_diff(a_tree, b_tree, game, args):
    """Only the TGIs whose winning FILE changes between two layouts.

    THE SUMMARY IS THE POINT, NOT THE LINES. Relocating one package rewrites
    the winner PATH of every key it owns, so a move of DialogStatic from
    `010-SC4UIScale\\` to `zzz-SC4UIScale\\` prints 265 lines that all say the
    same thing - and buries the six keys whose OWNER actually changed hands
    from CAM. The per-key lines stay (they are the diffable artefact), but the
    transition summary that follows collapses them, and `--ignore-moves`
    suppresses the pure relocations entirely so only changes of owner survive.
    """
    a = Layout(a_tree, game, use_game=not args.no_game)
    b = Layout(b_tree, game, use_game=not args.no_game)
    keys = a.key_universe(args.keys) | b.key_universe(args.keys)
    changes, moves = [], 0
    for k in sorted(keys):
        wa, wb = a.winner(k), b.winner(k)
        la = wa[0] if wa else "(none)"
        lb = wb[0] if wb else "(none)"
        if la == lb:
            continue
        same_file = os.path.basename(la) == os.path.basename(lb)
        if same_file:
            moves += 1
            if args.ignore_moves:
                continue
        changes.append({"tgi": tgi(k), "a": la, "b": lb,
                        "a_class": klass(wa), "b_class": klass(wb),
                        "relocation_only": same_file})
    trans = defaultdict(int)
    for ch in changes:
        trans[(ch["a"], ch["b"])] += 1
    if args.json:
        print(json.dumps({"a": a.tree, "b": b.tree, "keys": args.keys,
                          "ignore_moves": bool(args.ignore_moves),
                          "a_examined": len(a.key_universe(args.keys)),
                          "b_examined": len(b.key_universe(args.keys)),
                          "examined": len(keys),
                          "relocations": moves,
                          "changed": len(changes), "changes": changes,
                          "transitions": [{"a": x, "b": y, "keys": n}
                                          for (x, y), n in sorted(
                                              trans.items(),
                                              key=lambda z: (-z[1], z[0]))]},
                         indent=2))
        return 0
    print("=== WINNER DIFF ===")
    print("A: %s" % a.tree)
    print("B: %s" % b.tree)
    for n in a.notes + b.notes:
        print("!! %s" % n)
    print("keys examined (union, %s): %d%s"
          % (args.keys, len(keys),
             "   [--ignore-moves: relocations of the same filename hidden]"
             if args.ignore_moves else ""))
    print()
    for ch in changes:
        print("%s  %s  ->  %s" % (ch["tgi"], ch["a"], ch["b"]))
    print()
    print("--- transitions ---")
    for (x, y), n in sorted(trans.items(), key=lambda z: (-z[1], z[0])):
        print("%6d  %s  ->  %s" % (n, x, y))
    print()
    print("TGIs examined                  : %d" % len(keys))
    print("WINNER CHANGED                 : %d" % len(changes))
    print("  of which same file, moved    : %d"
          % sum(1 for c in changes if c["relocation_only"]))
    print("  hidden by --ignore-moves     : %d"
          % (moves if args.ignore_moves else 0))
    if not changes:
        print("(the two layouts resolve identically for every key examined - "
              "the controls above prove the instrument was live)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", help="Plugins tree to resolve "
                    "(default: the live user tree)")
    ap.add_argument("--diff", nargs=2, metavar=("TREE_A", "TREE_B"),
                    help="emit only TGIs whose winning file differs")
    ap.add_argument("--game", help="SimCity 4 install root "
                    "(default: resolved by sc4paths)")
    ap.add_argument("--no-game", action="store_true",
                    help="skip stock archives and <install>\\Plugins "
                         "(report is then Plugins-tree-only, and says so)")
    ap.add_argument("--keys", choices=("ours", "ours-loaded", "all"),
                    default="ours",
                    help="key universe: ours = every TGI our packages carry "
                         "including stashed tiers (default); ours-loaded = "
                         "only the staged tier; all = every TGI on disk")
    ap.add_argument("--only", choices=("all", "contested", "ours", "third",
                                       "stock", "none"), default="all",
                    help="filter the printed table (counts always cover all)")
    ap.add_argument("--limit", type=int, default=60,
                    help="max table rows to print (0 = no limit)")
    ap.add_argument("--ignore-moves", action="store_true",
                    help="--diff only: hide keys whose winner is the SAME "
                         "FILENAME in a new folder, leaving only real changes "
                         "of owner")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    ap.add_argument("--selfcheck", action="store_true",
                    help="run the positive controls and exit")
    ap.add_argument("--skip-selfcheck", action="store_true",
                    help="report WITHOUT verifying the instrument (loud)")
    args = ap.parse_args(argv)

    game = args.game or game_dir()
    live = plugins_dir()

    if args.selfcheck:
        ok, _ = run_controls(live, game)
        print("SELFCHECK: %s" % ("GREEN" if ok else "RED"))
        return 0 if ok else 1

    if args.skip_selfcheck:
        print("!!! --skip-selfcheck: NOTHING has verified that this tool can "
              "see contested keys, .UI entries or the stock archives. A zero "
              "in any count below is not evidence.\n", file=sys.stderr)
    else:
        ok, live_lay = run_controls(live, game, verbose=not args.json)
        if not ok:
            print("REFUSING TO REPORT: a positive control failed (see above). "
                  "A winner table from an instrument that cannot see its own "
                  "known-good cases is not a measurement.", file=sys.stderr)
            return 1

    if args.diff:
        return do_diff(args.diff[0], args.diff[1], game, args)

    tree = args.tree or live
    if not tree or not os.path.isdir(tree):
        print("no such Plugins tree: %s" % tree, file=sys.stderr)
        return 2
    lay = Layout(tree, game, use_game=not args.no_game)
    rows = build_rows(lay, args.keys)
    if args.json:
        print(json.dumps({"tree": lay.tree, "game": lay.game,
                          "keys": args.keys, "notes": lay.notes,
                          "files_loaded": lay.files_loaded,
                          "files_stashed": lay.files_stashed,
                          "archives": lay.archives,
                          "archive_entries": lay.archive_entries,
                          "counts": summarise(rows), "rows": rows}, indent=2))
    else:
        print_table(lay, rows, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
