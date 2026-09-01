#!/usr/bin/env python3
"""
Stage the 266 Item Icon PNGs for packing, at any package factor.

For each distinct Item Icon instance (from item_icons_distinct.txt), the override TGI is
{type 0x856DDBAC, group 0x6A386D26, instance}. The upscaled art already exists in
tools/upscale/preview[-<tag>]/SimCity_1/ named T-0x856ddbac_G-0x6a386d26_I-0x<inst8>.png
(lowercase).

Steps:
  - verify the preview PNG exists for every instance (report missing)
  - collision guard: exclude any instance that collides with the selective-safe refmap
    (group 0x6A386D26) or is present in the SelectiveArt / DialogStatic dats OF THE SAME
    FACTOR (tagged factors check the tools\packages\<tag>\ dats + refmap-<tag>.csv)
  - copy survivors into the stage dir with the canonical name
  - tagged factors additionally PACK tools\packages\<tag>\z_SC4UIScale_ItemIcons-<tag>.dat

Factor conventions follow tools\selective-safe\build_selective_safe.py exactly
(tier-generality fix A2, 2026-07-29): --factor 2 (default) keeps the ORIGINAL behaviour
bit-identically (untagged paths, stage/ only, manual pack step unchanged); 1.5 / 3 emit
factor-tagged artifacts into tools\packages\<tag>\ without touching the 2x ones.

Prints a full summary. Creates files only in the stage dir (+ the tagged package dat).
"""
import argparse, math, os, sys, shutil, struct, subprocess

TYPE = 0x856DDBAC
GROUP = 0x6A386D26

_ap = argparse.ArgumentParser(description="Item Icons override stager (factor-parametric).")
_ap.add_argument("--factor", type=float, default=2.0,
                 help="scale factor: 2 (default, bit-identical legacy behaviour), 1.5, or 3")
_args, _ = _ap.parse_known_args()
FACTOR = _args.factor


def _factor_tag(f):
    if abs(f - 2.0) < 1e-9:
        return ""      # default 2x path keeps the original untagged filenames
    if abs(f - 1.5) < 1e-9:
        return "15x"
    if abs(f - 3.0) < 1e-9:
        return "3x"
    if abs(f - round(f)) < 1e-9:
        return "%dx" % int(round(f))
    return ("%gx" % f).replace(".", "_")


TAG = _factor_tag(FACTOR)


def load_distinct(path):
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith(";"):   # ; = comment (v2.25.5)
                out.append(int(line, 16))
    return out

def refmap_group_instances(refmap_csv, group):
    """Return set of instances in refmap.csv whose GroupID == group (collision set)."""
    hits = set()
    with open(refmap_csv) as fh:
        header = fh.readline()
        for line in fh:
            parts = line.split(',')
            if len(parts) < 3:
                continue
            g = int(parts[1], 16)
            i = int(parts[2], 16)
            if g == group:
                hits.add(i)
    return hits

def dat_tgis(dat_path):
    """Parse a DBPF 1.0 / index 7.0 archive index; return set of (type,group,instance)."""
    tgis = set()
    with open(dat_path, 'rb') as fh:
        data = fh.read()
    if data[0:4] != b'DBPF':
        raise ValueError("not DBPF: %s" % dat_path)
    count = struct.unpack_from('<I', data, 0x24)[0]
    idx_off = struct.unpack_from('<I', data, 0x28)[0]
    for k in range(count):
        base = idx_off + k * 20
        t, g, i = struct.unpack_from('<III', data, base)
        tgis.add((t, g, i))
    return tgis

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(base, '..', '..'))
    distinct = load_distinct(os.path.join(base, '_work', 'item_icons_distinct.txt'))
    if TAG:
        preview_dir = os.path.join(root, 'tools', 'upscale', 'preview-%s' % TAG, 'SimCity_1')
        if os.environ.get('SC4UI_UPSCALE_DIR'):
            # lab A/B override (tools/research/sharp15/build_variant_tree.py)
            preview_dir = os.environ['SC4UI_UPSCALE_DIR']
            print('*** preview_dir OVERRIDE (SC4UI_UPSCALE_DIR): %s' % preview_dir)
        stage_dir = os.path.join(base, 'stage-%s' % TAG)
        refmap = os.path.join(root, 'tools', 'selective-safe', 'refmap-%s.csv' % TAG)
        pkg_dir = os.path.join(root, 'tools', 'packages', TAG)
        sel_dat = os.path.join(pkg_dir, 'z_SC4UIScale_SelectiveArt-%s.dat' % TAG)
        dlg_dat = os.path.join(pkg_dir, 'z_SC4UIScale_DialogStatic-%s.dat' % TAG)
        out_dat = os.path.join(pkg_dir, 'z_SC4UIScale_ItemIcons-%s.dat' % TAG)
    else:
        preview_dir = os.path.join(root, 'tools', 'upscale', 'preview', 'SimCity_1')
        stage_dir = os.path.join(base, 'stage')
        refmap = os.path.join(root, 'tools', 'selective-safe', 'refmap.csv')
        sel_dat = os.path.join(root, 'tools', 'selective-safe', 'z_SC4UIScale_SelectiveArt.dat')
        dlg_dat = os.path.join(root, 'tools', 'dialog-static', 'z_SC4UIScale_DialogStatic.dat')
        out_dat = None   # legacy behaviour: stage only; pack step stays manual
    packer = os.path.join(root, 'tools', 'dbpf', 'DbpfPack.exe')

    print("Scale factor: %g  (tag %r)" % (FACTOR, TAG or "(none, 2x default)"))
    print("Preview art dir: %s" % preview_dir)
    if not os.path.isdir(preview_dir):
        sys.exit("FATAL: preview art dir not found for factor %g: %s" % (FACTOR, preview_dir))

    os.makedirs(stage_dir, exist_ok=True)
    # empty in place (never rmdir - OneDrive holds folder handles)
    for fn in os.listdir(stage_dir):
        os.remove(os.path.join(stage_dir, fn))

    # collision sets
    refmap_hits = refmap_group_instances(refmap, GROUP)
    sel_tgis = dat_tgis(sel_dat)
    dlg_tgis = dat_tgis(dlg_dat)

    print("distinct icon instances     : %d" % len(distinct))
    print("refmap group-0x6A386D26 hits : %d" % len(refmap_hits))
    print("SelectiveArt total TGIs      : %d" % len(sel_tgis))
    print("DialogStatic total TGIs      : %d" % len(dlg_tgis))

    missing_preview = []
    excluded = []   # (instance, reason)
    staged = []
    for inst in distinct:
        tgi = (TYPE, GROUP, inst)
        name = "T-0x%08x_G-0x%08x_I-0x%08x.png" % (TYPE, GROUP, inst)
        src = os.path.join(preview_dir, name)
        # collision checks
        if inst in refmap_hits:
            excluded.append((inst, "refmap collision (group 0x6A386D26 referenced by .UI)"))
            continue
        if tgi in sel_tgis:
            excluded.append((inst, "present in SelectiveArt dat"))
            continue
        if tgi in dlg_tgis:
            excluded.append((inst, "present in DialogStatic dat"))
            continue
        if not os.path.exists(src):
            missing_preview.append(inst)
            excluded.append((inst, "no %s preview PNG" % (TAG or "2x")))
            continue
        shutil.copyfile(src, os.path.join(stage_dir, name))
        staged.append((inst, os.path.getsize(src)))

    print("staged                       : %d" % len(staged))
    print("excluded                     : %d" % len(excluded))
    print("missing preview PNG          : %d" % len(missing_preview))
    if excluded:
        print("--- exclusions ---")
        for inst, why in excluded:
            print("   0x%08x : %s" % (inst, why))
    # also cross-check: any staged TGI already in SelectiveArt/DialogStatic (should be 0)
    overlap_sel = [i for (i, _) in staged if (TYPE, GROUP, i) in sel_tgis]
    overlap_dlg = [i for (i, _) in staged if (TYPE, GROUP, i) in dlg_tgis]
    print("staged overlap w/ SelectiveArt : %d" % len(overlap_sel))
    print("staged overlap w/ DialogStatic : %d" % len(overlap_dlg))

    if TAG:
        if len(staged) != len(distinct):
            sys.exit("FATAL: tagged build staged %d != %d distinct - fix inputs first"
                     % (len(staged), len(distinct)))
        os.makedirs(os.path.dirname(out_dat), exist_ok=True)
        r = subprocess.run([packer, stage_dir, out_dat], capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode != 0:
            sys.exit("PACK FAILED:\n" + r.stderr)
        r = subprocess.run([packer, "--list", out_dat], capture_output=True, text=True)
        n_listed = sum(1 for line in r.stdout.splitlines()
                       if line.startswith("0x"))
        print("Packed %s: %d entries listed (staged %d), %d bytes"
              % (os.path.basename(out_dat), n_listed, len(staged),
                 os.path.getsize(out_dat)))
        if n_listed != len(staged):
            sys.exit("FATAL: packed entry count mismatch")
    else:
        print("(2x default: stage only, pack manually with "
              "../dbpf/DbpfPack.exe stage z_SC4UIScale_ItemIcons.dat - unchanged)")

if __name__ == '__main__':
    main()
