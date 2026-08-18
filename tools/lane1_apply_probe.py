"""Adversarial probe #3: actually APPLY the three patches to a scratch copy of
build_selective_safe.py, compile it, and exercise neutralize_dock_recess() at
every tier.  Also cross-checks the stdlib PNG decoder against PIL (independent
instrument -> the positive control for the decoder).
Throwaway.  Writes ONLY under the scratchpad.
"""
import hashlib
import importlib.util
import os
import py_compile
import shutil
import subprocess
import sys

PROJ = r"<HOME>\OneDrive\Projects\Surface 1 Project\1 Completed Projects\SC4TouchControls"
SRC = os.path.join(PROJ, "tools", "selective-safe", "build_selective_safe.py")
SCR = r"<HOME>\AppData\Local\Temp\claude\<SESSION-DIR>\f1160943-a698-434b-a6bf-d3c3e2971cea\scratchpad\lane1"
os.makedirs(SCR, exist_ok=True)

OLD1 = "import shutil\nimport subprocess\nimport sys\nfrom collections import defaultdict"
NEW1 = "import shutil\nimport struct\nimport subprocess\nimport sys\nimport zlib\nfrom collections import defaultdict"
OLD2 = "FONT_GUIDS = load_font_guids()\n\n\ndef main():"
OLD3 = ('    print("Staged: %d exclusive in-place PNGs (%d no-2x skipped), '
        '%d shared clones (%d no-2x skipped)"\n'
        '          % (n_excl_staged, n_excl_missing, n_shared_staged, n_shared_missing))')
NEW3 = OLD3 + ("\n\n    # Post-upscale art repair: erase the decorative fake map baked into the\n"
               "    # dock's minimap recess. 3x tier and up only - see the block comment above.\n"
               "    neutralize_dock_recess()")

# NEW2 is long; read it from the spec file the lead will apply.  Reconstructed
# here verbatim from the spec text.
NEW2 = open(os.path.join(SCR, "new2.txt"), "r", encoding="utf-8").read()

with open(SRC, "r", encoding="utf-8", newline="") as f:
    text = f.read()
for i, o in ((1, OLD1), (2, OLD2), (3, OLD3)):
    print("anchor %d occurrences: %d" % (i, text.count(o)))
    assert text.count(o) == 1, "anchor %d not unique/absent" % i

patched = text.replace(OLD1, NEW1).replace(OLD2, NEW2).replace(OLD3, NEW3)
OUT = os.path.join(PROJ, "tools", "selective-safe", "build_patched_probe.py")
with open(OUT, "w", encoding="utf-8", newline="") as f:
    f.write(patched)
print("patched file written: %d bytes (orig %d)" % (len(patched), len(text)))

py_compile.compile(OUT, doraise=True)
print("py_compile: OK")

# ---- flake-ish sanity: any NameError at import time? -----------------------
DOCK = "T-0x856ddbac_G-0x46a006b0_I-0x13d14ca0.png"
SRC3 = os.path.join(PROJ, "tools", "selective-safe", "stage-3x", DOCK)
SRC2 = os.path.join(PROJ, "tools", "selective-safe", "stage", DOCK)
SRC15 = os.path.join(PROJ, "tools", "selective-safe", "stage-15x", DOCK)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run_tier(factor, src_png, expect_change, absent=False):
    tag = ("%g" % factor).replace(".", "_")
    stage = os.path.join(SCR, "stage_%s%s" % (tag, "_absent" if absent else ""))
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)
    if not absent:
        shutil.copy2(src_png, os.path.join(stage, DOCK))
    script = os.path.join(SCR, "run_%s%s.py" % (tag, "_absent" if absent else ""))
    with open(script, "w", encoding="utf-8") as f:
        f.write(
            "import sys, hashlib, os\n"
            "sys.argv = ['x', '--factor', %r]\n"
            "import importlib.util\n"
            "spec = importlib.util.spec_from_file_location('bp', %r)\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "m.STAGE = %r\n"
            "p = os.path.join(m.STAGE, %r)\n"
            "before = hashlib.sha256(open(p,'rb').read()).hexdigest() if os.path.isfile(p) else None\n"
            "m.neutralize_dock_recess()\n"
            "after = hashlib.sha256(open(p,'rb').read()).hexdigest() if os.path.isfile(p) else None\n"
            "print('FACTOR', m.FACTOR, 'sha_equal', before == after)\n"
            % (str(factor), OUT, stage, DOCK))
    r = subprocess.run([sys.executable, script], capture_output=True, text=True)
    print("\n--- tier f=%s%s (rc=%d) ---" % (factor, " SHEET ABSENT" if absent else "", r.returncode))
    tail = [ln for ln in (r.stdout + r.stderr).splitlines()
            if ("Dock recess" in ln or "FACTOR" in ln or "FATAL" in ln
                or "Error" in ln or "Traceback" in ln)]
    for ln in tail:
        print("   " + ln)
    if not absent:
        changed = sha(os.path.join(stage, DOCK)) != sha(src_png)
        print("   bytes changed: %s  (expected change: %s)  -> %s"
              % (changed, expect_change, "PASS" if changed == expect_change else "*** FAIL ***"))
        return os.path.join(stage, DOCK)
    return None


run_tier(1.5, SRC15, False)
run_tier(2.0, SRC2, False)
out3 = run_tier(3.0, SRC3, True)
run_tier(3.0, SRC3, True, absent=True)

# ---- PIL cross-check: independent decoder = positive control ---------------
print("\n### PIL cross-check (independent decoder)")
from PIL import Image
a = Image.open(SRC3).convert("RGBA")
b = Image.open(out3).convert("RGBA")
print("  dims", a.size, b.size)
pa, pb = a.load(), b.load()
inside_diff = outside_diff = 0
sat_in = 0
for y in range(a.size[1]):
    for x in range(a.size[0]):
        va, vb = pa[x, y], pb[x, y]
        insid = 54 <= x < 246 and 213 <= y < 405
        if va != vb:
            if insid:
                inside_diff += 1
            else:
                outside_diff += 1
        if insid:
            r, g, bl, _ = vb
            if (r, g, bl) != (255, 0, 255) and max(r, g, bl) - min(r, g, bl) > 60:
                sat_in += 1
print("  pixels changed INSIDE  rect (54,213)192x192 :", inside_diff, "of 36864")
print("  pixels changed OUTSIDE rect                 :", outside_diff, "  <-- MUST be 0")
print("  saturated px remaining inside rect (PIL)    :", sat_in)
# seam check with PIL
worst = 0
for y in range(213, 405):
    for x in (53, 54, 245, 246):
        pass
    l_out, l_in = pb[53, y], pb[54, y]
    r_in, r_out = pb[245, y], pb[246, y]
    worst = max(worst, max(abs(l_out[c] - l_in[c]) for c in range(4)),
                max(abs(r_in[c] - r_out[c]) for c in range(4)))
print("  worst seam delta at the rect border (PIL)   :", worst, "/255")
