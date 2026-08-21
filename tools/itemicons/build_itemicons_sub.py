#!/usr/bin/env python3
"""
Build z_SC4UIScale_ItemIconsSub-<tag>.dat at any package factor (tier fix A1/A2).

The shipped 2x Sub package (_work/z_SC4UIScale_ItemIconsSub-2x.dat, 130 entries,
packed from _work/pack-sub/) was assembled by hand across three passes (REPORT.md
2026-07-29: submenus 55 -> +69 landmarks -> +missing-thumb +5 lots = 130). This
script replicates that packing path per tier, from the SAME 1x sources:

    _work/submenus-1x/   (55)  submenus-mod icons, canonical names
    _work/plugins-1x/    (69)  CAM + Maxis landmark plugin icons, canonical names
    _work/lots-icons-1x/ ( 5)  Maxis Buildings .SC4Lot icons, un-normalized names
  + the submenus DLL Missing Thumb 0x144161EC, which is a STOCK-POOL image and is
    taken pre-upscaled from tools/upscale/preview[-<tag>]/SimCity_1/ (never from a
    1x source - it ships in SimCity_1.dat, exactly like the root 266).

All 129 1x sources are upscaled with the project upscaler (Upscale2x.exe --factor
<f> --normalize-names, the preview-set method), staged to _work/pack-sub-<tag>/,
verified name-for-name against the shipped _work/pack-sub/ set (so tier packages
can never silently diverge from the user-confirmed 2x contents), then packed to
tools/packages/<tag>/z_SC4UIScale_ItemIconsSub-<tag>.dat.

--factor 2 (default) is VERIFY-ONLY: it stages to _work/pack-sub-2x-verify/ and
compares against _work/pack-sub/, but never overwrites the shipped 2x dat.

Factor/tag conventions follow tools/selective-safe/build_selective_safe.py.
"""
import argparse, os, shutil, subprocess, sys

_ap = argparse.ArgumentParser(description="ItemIconsSub package builder (factor-parametric).")
_ap.add_argument("--factor", type=float, default=2.0,
                 help="scale factor: 2 (default, verify-only), 1.5, or 3")
_args, _ = _ap.parse_known_args()
FACTOR = _args.factor


def _factor_tag(f):
    if abs(f - 2.0) < 1e-9:
        return ""
    if abs(f - 1.5) < 1e-9:
        return "15x"
    if abs(f - 3.0) < 1e-9:
        return "3x"
    if abs(f - round(f)) < 1e-9:
        return "%dx" % int(round(f))
    return ("%gx" % f).replace(".", "_")


TAG = _factor_tag(FACTOR)
MISSING_THUMB = "T-0x856ddbac_G-0x6a386d26_I-0x144161ec.png"

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, '..', '..'))
WORK = os.path.join(BASE, '_work')
UPSCALER = os.path.join(ROOT, 'tools', 'upscale', 'Upscale2x.exe')
PACKER = os.path.join(ROOT, 'tools', 'dbpf', 'DbpfPack.exe')
SRC_1X = [os.path.join(WORK, d) for d in ('submenus-1x', 'plugins-1x', 'lots-icons-1x')]
REFERENCE = os.path.join(WORK, 'pack-sub')   # the shipped, user-confirmed 2x set
# ...but only its NAME SET is ever read, and a directory of 130 upscaled mod
# bitmaps cannot live in the repo. The manifest is that name set as text - our
# derivation, not anyone's art - so a cold clone still gets the divergence
# check. Regenerate with:  ls _work/pack-sub > _work/pack-sub-manifest.txt
REFERENCE_MANIFEST = os.path.join(WORK, 'pack-sub-manifest.txt')


def reference_names():
    """The shipped 2x name set: the directory if present, else the manifest.

    Either source is fine because the check is on NAMES. Refusing when both are
    missing is deliberate - without a reference this build cannot tell a
    correct tier package from one silently missing an icon, and shipping that
    unnoticed is exactly the failure this check was added for.
    """
    if os.path.isdir(REFERENCE):
        return sorted(fn.lower() for fn in os.listdir(REFERENCE)
                      if fn.lower().endswith('.png'))
    if os.path.isfile(REFERENCE_MANIFEST):
        with open(REFERENCE_MANIFEST, 'r', encoding='utf-8') as f:
            return sorted(ln.strip().lower() for ln in f
                          if ln.strip().lower().endswith('.png'))
    sys.exit("FATAL: no shipped-2x reference. Need either %s\n"
             "  or %s\n"
             "  Run tools\\itemicons\\recover_sub_sources.py, or see REPORT.md."
             % (REFERENCE, REFERENCE_MANIFEST))


def fresh_dir(path):
    """Empty a directory in place (OneDrive holds folder handles; never rmdir)."""
    if not os.path.isdir(path):
        os.makedirs(path)
        return
    for entry in os.listdir(path):
        p = os.path.join(path, entry)
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            os.remove(p)


def main():
    print("Scale factor: %g  (tag %r)" % (FACTOR, TAG or "(none, 2x verify-only)"))
    if TAG:
        preview_dir = os.path.join(ROOT, 'tools', 'upscale', 'preview-%s' % TAG, 'SimCity_1')
        stage = os.path.join(WORK, 'pack-sub-%s' % TAG)
        pkg_dir = os.path.join(ROOT, 'tools', 'packages', TAG)
        out_dat = os.path.join(pkg_dir, 'z_SC4UIScale_ItemIconsSub-%s.dat' % TAG)
    else:
        preview_dir = os.path.join(ROOT, 'tools', 'upscale', 'preview', 'SimCity_1')
        stage = os.path.join(WORK, 'pack-sub-2x-verify')
        out_dat = None

    ref = reference_names()      # resolves dir-or-manifest, or exits saying so

    for d in SRC_1X + [preview_dir]:
        if not os.path.isdir(d):
            sys.exit("FATAL: missing input dir: %s\n"
                     "  The 1x sources are another mod's icons and are not in the\n"
                     "  repo. Run tools\\itemicons\\recover_sub_sources.py to\n"
                     "  re-extract them from your own Plugins tree." % d)

    # gather + upscale the 1x sources (three dirs -> one temp input set)
    merged_1x = os.path.join(WORK, 'pack-sub-src-merged')
    fresh_dir(merged_1x)
    n_src = 0
    for d in SRC_1X:
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith('.png'):
                continue
            dst = os.path.join(merged_1x, fn)
            if os.path.exists(dst):
                sys.exit("FATAL: duplicate 1x source name across dirs: %s" % fn)
            shutil.copy2(os.path.join(d, fn), dst)
            n_src += 1
    print("1x sources merged: %d (expect 129)" % n_src)

    fresh_dir(stage)
    r = subprocess.run([UPSCALER, merged_1x, stage,
                        '--factor', '%g' % FACTOR, '--normalize-names'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("UPSCALE FAILED:\n" + r.stderr + r.stdout)
    # the missing thumb is stock-pool art: take it pre-upscaled from the preview set
    mt_src = os.path.join(preview_dir, MISSING_THUMB)
    if not os.path.isfile(mt_src):
        sys.exit("FATAL: missing-thumb preview absent: %s" % mt_src)
    shutil.copy2(mt_src, os.path.join(stage, MISSING_THUMB))

    got = sorted(fn.lower() for fn in os.listdir(stage) if fn.lower().endswith('.png'))
    only_new = [f for f in got if f not in ref]
    only_ref = [f for f in ref if f not in got]
    print("staged: %d   shipped-2x reference: %d" % (len(got), len(ref)))
    if only_new or only_ref:
        for f in only_new:
            print("   EXTRA (not in shipped 2x): %s" % f)
        for f in only_ref:
            print("   MISSING (in shipped 2x):   %s" % f)
        sys.exit("FATAL: tier Sub set diverges from the shipped 2x set - fix inputs")
    print("name set == shipped 2x set: OK")

    if not TAG:
        print("(2x verify-only: shipped _work/z_SC4UIScale_ItemIconsSub-2x.dat untouched)")
        return

    os.makedirs(pkg_dir, exist_ok=True)
    r = subprocess.run([PACKER, stage, out_dat], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit("PACK FAILED:\n" + r.stderr)
    r = subprocess.run([PACKER, '--list', out_dat], capture_output=True, text=True)
    n_listed = sum(1 for line in r.stdout.splitlines() if line.startswith("0x"))
    print("Packed %s: %d entries (staged %d), %d bytes"
          % (os.path.basename(out_dat), n_listed, len(got), os.path.getsize(out_dat)))
    if n_listed != len(got):
        sys.exit("FATAL: packed entry count mismatch")


if __name__ == '__main__':
    main()
