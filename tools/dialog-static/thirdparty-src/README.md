# thirdparty-src\ — .UI scripts owned by OTHER plugins (task #79c)

These are **verbatim extracts of another mod's data**, kept here only as
builder inputs. Nothing in this folder is ours and nothing here is edited: the
builder reads them, applies the SAME area/gutters/font transform it applies to
the stock dialogs, and emits the doubled copies into a **separate** package
that ships from `Plugins\zzz-SC4UIScale\`.

## Why this folder exists (the LOAD-ORDER LAW)

Files in the `Plugins` **root** load BEFORE files in **subfolders**, so a root
dat can never override a subfolder dat (`README.md`, `SCENARIOS.md`,
`REGRESSION.md`). Our root `z_SC4UIScale_DialogStatic-2x.dat` therefore lost to
this mod, and the two in-city quit/exit confirms rendered at stock 1x — which
is the whole of the "static doubling is bypassed by the game" misdiagnosis that
stood from 2026-07-26 to 2026-07-31. The game never bypassed anything.

## Contents

| file | owning mod | package | what the mod changed |
|---|---|---|---|
| `I-6a553aa4.ui` | cyclone-boom save-warning | `SaveWarningUI` | Exit-to-Region confirm, 270x**162** vs stock 161 |
| `I-0a55161d.ui` | cyclone-boom save-warning | `SaveWarningUI` | Quit confirm, re-laid to 270x162 (stock 330x157) |
| `I-ca8cbf0f.ui` | CAM | `CamUI` | generic 1-button popup, **500x175** vs stock 300x166 |
| `I-8aa9aa14.ui` | CAM | `CamUI` | startup splash, 6 nodes vs 4 (two extra text lines) |
| `I-2a554f6d.ui` | CAM | `CamUI` | query panel, 292x284 → **300x480**, 21 → 45 nodes |
| `I-aa8b999e.ui` | CAM | `CamUI` | query panel, 292x134 → **404x346**, 8 → 21 nodes |
| `I-ca8b8564.ui` | CAM | `CamUI` | query panel, moved (246,202)→(570,200), 14 → 20 |
| `I-ea565970.ui` | CAM | `CamUI` | query panel, 292x275 → **304x297**, 22 → 24 nodes |
| `I-9b868f68.ui` | CAM | `CamUI` | **city info screen — CAM-ONLY, overrides nothing**, 600x525, 116 nodes |
| `I-12121201.ui` | CAM | `CamUI` | **civic query panel — CAM-ONLY**, 292x260, 15 nodes |
| `I-12121205.ui` | CAM | `CamUI` | **school query panel — CAM-ONLY**, 292x287, 23 nodes |

## ⚠ The CAM-ONLY entries are a different animal (task #154, 2026-08-13)

Every row above `9b868f68` is an OVERRIDE: the mod replaces a stock script, we
rebuild the mod's version, and if the mod goes away the stock twin in the root
`DialogStatic` package takes over. The last three are CAM's **own** dialogs —
the Village Hall / Town Hall info screen captioned "MZ v1", and the civic and
school query panels — and no stock twin exists for any of them, so the
builder's State-B assert cannot apply. They are listed in `TP_MOD_ONLY`, and
that exemption is **proven at build time** (the id must be absent from the
331-script stock corpus) rather than declared, so it can never hide a twin that
really is missing.

`12121205` also references `{46a006b0,b5cfffff}`, which **exists nowhere** —
not in the nine game archives, not anywhere in Plugins. It is a dangling ref in
CAM's own data, the second one found here after the `0xFF5D2E9F` graph-label
typo. It is listed in `TP_ART_DANGLING` with that evidence; the bar for that
list is a null from an instrument that reads Plugins too, plus a positive
control from the same run, because a stock-only null already cost one shipped
defect (v2.38.3's 2x2-tiled splash).

**It also brought its own art:** nine CAM bitmaps, all `blttype=normal`, listed
in `TP_ART_PACKAGE`. Normal-blit art is drawn at its own size and CLIPPED by
the window, never stretched, so a 1x strip in a 1.5x row covers two thirds of
it. `tools\uimap\emu\gate_tp_bmp_fit.py` guards the result.

### ⛔ AND SO DOES THE CROP — this shipped wrong once (v2.97.0 → v2.97.1)

A `blttype=normal` blit has **three** numbers and the first build scaled two:

```
window     285 -> 428   scaled
bitmap     285 -> 429   scaled
imagerect  285 -> 285   NOT SCALED   -> 143px of every row painted nothing
```

`imagerect` is scaled only for a control whose art the build scaled, and that
test reads `art_plan` — computed from the **stock** upscale store alone. Art
from `thirdparty-art\` is therefore *always* `left1x` there, however thoroughly
we scale it. The rule now routes mod art through `RUNTIME_BOUND_2X` ("the ref
is unchanged but its pixels are scaled"), **scoped to the owning package**: a
rect may only scale when the scaled bitmap ships in the same mod-gated dat, or
removing that mod leaves a doubled crop over 1x art.

The same repair fixed `2a554f6d` and `aa8b999e`, which had been drawing 280px
strips inside 420px windows at every tier since v2.38.3.

**Why it hid for the whole life of the project:** every check in this builder
asks "has a mod taken over one of OUR targets?" Nothing ever asked "is a mod's
OWN dialog scaled at all?" It rendered at 1x under 1.5x fonts — labels clipped
mid-word, values overlapping them — and no gate went red.

Extracted with `tools\dbpf\DbpfExtract.exe` from:

    150-mods\cyclone-boom.save-warning.1.0.sc4pac\SaveWarning_Disable_Exit_Quit.dat   2408 bytes
    050-load-first\cam...4.0.1.sc4pac\1 CAM Core\CAM_Extended_Essentials.dat       2817430 bytes
    050-load-first\cam...4.0.1.sc4pac\1 CAM Core\CAM_Intro.dat                     1001294 bytes

Those sizes are the fingerprints `ScaleTier::kThirdPartyDeps` gates on.

**One package per owning mod, and that is not cosmetic:** a copy of mod A's
script must not ride in a package gated on mod B, or uninstalling A leaves our
copy of A's UI alive.

**No mod's own file is ever written to, renamed or deleted by the build.**

## How the CAM set was found — and why it was invisible for so long

`tools\uiscripts\winning_corpus.py` resolves the true load-order winner per TGI
across all 147 archives. It found **12** third-party `.UI` scripts, **nine of
them CAM's** — and six of those are dialog-static TARGETS, i.e. we were shipping
doubled copies of scripts the game never loads.

Four of the six are **auto-enrolled** by `discover_query_family()` rather than
listed literally, which is why a static scan of the builder's source
under-counted them (it said 2; the builder's own assert said 6). The builder now
ASSERTS that a target's winning script is the one it read.

## The identifying difference (keep this - it is how the mod was caught)

| | root `area=` | w x h |
|---|---|---|
| stock `6a553aa4` | `(332,232,602,393)` | 270x**161** |
| **mod** `6a553aa4` | `(332,232,602,394)` | 270x**162** |

The live dialog logged 270x**162**. One pixel identified the winner.

The mod also rewrites `0a55161d` to the same 270x162 body (stock is 330x157),
recaptions the first button to "Option Disabled" and sets `winflag_enable=no`.
Our doubled copy preserves ALL of that verbatim - only pixel geometry and the
font-name -> GUID substitution change. Shipping a doubled copy of the STOCK
script here would silently REVERT the mod's function, which is why the builder
reads this folder and not `tools\uiscripts\extracted\`.

## Re-sync

If the mod is updated, re-extract into this folder, update the fingerprint in
`ScaleTier.cpp` (`kThirdPartyDeps`) and rebuild all three tiers. Until that
happens the size check fails, our override auto-disables, and the dialog falls
back to runtime scaling - correct, with the open flash back.
