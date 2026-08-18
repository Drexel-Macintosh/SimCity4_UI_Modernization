#!/usr/bin/env python3
r"""corpus_inputs.py - resolve the two derived inputs every layout builder reads.

WHY THIS EXISTS. A cold-clone test on 2026-08-18 ran all eight package
builders from a fresh checkout. Three died on a bare FileNotFoundError
naming a path the reader had never heard of:

    tools\dbpf\extracted-png-tgi.csv       (build_selective_safe.py)
    tools\uiscripts\extracted\             (build_dialog_static.py)

Neither is committed - both are derived from the player's own game install,
and correctly so. The defect was that nothing derived them and no error said
how. Presence verification had passed on all eight builders; only EXECUTION
found it.

extracted-png-tgi.csv is a straight COPY of the extract-manifest.csv of
whichever archive carries the PNG store, so it is derived here automatically
rather than demanded. The .UI corpus needs the extractor, so that one raises
an error that names the exact command instead.
"""
import os
import shutil

TOOLS = os.path.dirname(os.path.abspath(__file__))
EXTRACT_ROOT = os.path.join(TOOLS, "dbpf", "extracted")
PNG_TGI_CSV = os.path.join(TOOLS, "dbpf", "extracted-png-tgi.csv")
UI_DIR = os.path.join(TOOLS, "uiscripts", "extracted")

_BOOTSTRAP = (
    "Run the corpus bootstrap first:\n"
    "    powershell -NoProfile -ExecutionPolicy Bypass -File tools\\Bootstrap-Corpus.ps1\n"
    "It extracts the game archives and derives both inputs. See RUNBOOK.md section 1."
)


def _png_magic_rows(path):
    """Count PngMagic=yes rows. Column 8 of the manifest, 0-based index 7."""
    n = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            next(f, None)
            for line in f:
                parts = line.rstrip("\n").split(",")
                if len(parts) > 7 and parts[7] == "yes":
                    n += 1
    except OSError:
        return 0
    return n


def ensure_png_tgi_csv():
    """Return the path to extracted-png-tgi.csv, deriving it if absent.

    WHICH archive carries the PNG store is MEASURED, not assumed. Today that
    is SimCity_1 - that is a fact about this build, not a law, and a hard-coded
    name would rot silently against a different edition.
    """
    if os.path.isfile(PNG_TGI_CSV):
        return PNG_TGI_CSV

    best, best_n = None, 0
    if os.path.isdir(EXTRACT_ROOT):
        for dirpath, _dirnames, filenames in os.walk(EXTRACT_ROOT):
            if "extract-manifest.csv" not in filenames:
                continue
            cand = os.path.join(dirpath, "extract-manifest.csv")
            n = _png_magic_rows(cand)
            if n > best_n:
                best, best_n = cand, n

    if not best:
        raise SystemExit(
            "MISSING INPUT: %s\n"
            "No extract-manifest.csv found under %s to derive it from.\n%s"
            % (PNG_TGI_CSV, EXTRACT_ROOT, _BOOTSTRAP))
    if best_n == 0:
        # A null is a REFUSAL, not a pass: an extraction that produced no
        # PNG-magic rows is a broken extraction, and copying it forward would
        # hand every collision check an empty set that passes vacuously.
        raise SystemExit(
            "REFUSING: the best manifest (%s) carries 0 PngMagic=yes rows.\n"
            "The extraction is wrong, not the csv. %s" % (best, _BOOTSTRAP))

    shutil.copyfile(best, PNG_TGI_CSV)
    print("derived %s from %s (%d PNG-magic entries)"
          % (os.path.basename(PNG_TGI_CSV),
             os.path.basename(os.path.dirname(best)), best_n))
    return PNG_TGI_CSV


def require_ui_corpus(groups=("96a006b0", "08000600")):
    """Fail with an actionable message if the .UI layout corpus is absent.

    Also refuses an EMPTY group: the builders select layouts by group name, so
    a present-but-empty group is a silent no-op that surfaces 300 lines later
    as a wrong entry count rather than as a missing input.
    """
    if not os.path.isdir(UI_DIR):
        raise SystemExit("MISSING INPUT: %s\n%s" % (UI_DIR, _BOOTSTRAP))
    names = os.listdir(UI_DIR)
    for g in groups:
        pre = "T-00000000_G-%s_I-" % g
        if not any(n.startswith(pre) and n.endswith(".ui") for n in names):
            raise SystemExit(
                "EMPTY UI GROUP %s in %s\n"
                "The layout builders read this group by name; 0 files here is a\n"
                "silent no-op downstream, not a clean run.\n%s"
                % (g, UI_DIR, _BOOTSTRAP))
    return UI_DIR


if __name__ == "__main__":
    ensure_png_tgi_csv()
    require_ui_corpus()
    print("corpus inputs OK")
