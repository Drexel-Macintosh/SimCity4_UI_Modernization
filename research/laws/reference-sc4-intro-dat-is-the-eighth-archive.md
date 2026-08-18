---
name: reference-sc4-intro-dat-is-the-eighth-archive
description: "FIXED 2026-08-05: SC4 ships NINE DBPF archives, not the seven that were hard-coded — tools\\dbpf\\find_tgi.py omits Intro.dat, and the upscale preview set only covers SimCity_1. Art that lives in Intro.dat therefore reports 'DANGLING / no 2x asset' while being perfectly present in the game. The startup splash {856ddbac,46a006b0,ea7f0eae} is the known case."
metadata: 
  node_type: memory
  type: reference
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-06T04:14:50.741Z
---

# `Intro.dat` is the EIGHTH archive, and two of our tools cannot see it

`tools\dbpf\find_tgi.py:23-25` scans **seven** archives:

    SimCity_1..5.dat, EP1.dat, SimCityLocale.DAT

The install root also holds **`Intro.dat`** (~18 MB, 3 index entries). It is not
in that list. Separately, the upscale preview sets are built from
`SimCity_1` only (`tools\upscale\preview*\SimCity_1\`), so anything in another
archive has no 2x asset even when its 1x source is right there in the game.

**MEASURED 2026-08-05.** The startup-splash background:

    DbpfExtract.exe Intro.dat out 0x856DDBAC
    -> T-856ddbac_G-46a006b0_I-ea7f0eae.png   768x600   500,591 B

That TGI had been recorded **DANGLING / "no source anywhere"** in
`sdkgaps-03.md`, `REGRESSION.md:3508` and the builder reports — a null from a
tool that could not have seen it. [[feedback-null-is-not-evidence]] exactly:
state the positive control before believing an absence. `find_tgi.py`'s own
header already warns it had produced false negatives twice; Intro.dat made it
four times on the same TGI.

**WHAT IT COST.** Believing "no stock source exists", I shipped **CAM's** copy
of the splash in our ROOT DialogStatic package to fix the 2x2 tiling. Pixel
diff against the real stock bitmap: **99.72% of pixels differ, max delta 251** —
not a re-encode, a genuinely different image. The user spotted it on screen and
asked why the CAM background was being used. Wrong on provenance, and wrong for
a CC0 project to redistribute a third-party mod's art. Corrected the same
session: extracted from Intro.dat, upscaled with our own `Upscale2x.exe` at
1.5/2/3, rebuilt and redeployed all three tiers.

## ✅ FIXED 2026-08-05 — and the real count is NINE, not eight

`find_tgi.py` no longer carries a list at all: it **enumerates** `*.dat` in the
install root. Run against this machine it reports **nine** archives, and names
the two the hard-coded list was missing — `Intro.dat` **and `Sound.dat`**. So
the original diagnosis ("we forgot one") was itself short by one, which is the
whole argument for deriving the inventory instead of writing it down.

    python tools\dbpf\find_tgi.py ea7f0eae
    -> discovered 9 archive(s) ... 0xEA7F0EAE  Intro.dat  T=0x856DDBAC ...

That line is the standing regression check. If the count drops, the discovery
regressed to a list.

**THE DURABLE LESSON IS NOT "ADD INTRO.DAT".** A hand-maintained inventory of
what exists on disk is a *claim about the filesystem*. It ages silently, and it
is only ever wrong in the case you needed it. The tool even carried a warning
that its negatives were not "dangling" — and the warning pointed at the wrong
axis (it said *Plugins* were unscanned, which was true and irrelevant; nobody
asked whether the GAME side of the scan was complete). A caveat on the wrong
axis reads as diligence and buys nothing.

**HOW TO APPLY**
* Before calling any art ref dangling, say how many archives you scanned and
  where the number came from. `who_owns_tgi.py` covers plugins; `find_tgi.py`
  now covers every archive the install actually has.
* "No 2x asset in the upscale preview set" means *the SimCity_1 preview set* —
  it is NOT evidence the 1x art is missing from the game.
* `DbpfExtract.exe <archive> <outDir> [0xTYPE]` is read-only and is the way to
  get a pristine 1x source. Prefer it over any mod's copy, always.
* A bitmap that "looks like the stock one" is not the stock one. Pixel-diff it
  ([[feedback-sc4-measure-dont-infer]]).

Related: [[feedback-sc4-scaling-laws]] (law 35 tiled blits; LEFT1X law 55/56),
[[feedback-sc4-plugins-scan-is-recursive]] (the other shallow-probe failure from
the same day), [[project-sc4-ui-scaling-northstar]].
