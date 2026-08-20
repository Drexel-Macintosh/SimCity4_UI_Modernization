# SC4 UI Art Binding — Is Blanket 2x Art Replacement Safe?

Research date: 2026-07-21. Question: the runtime scaling layer doubles CITY-view HUD
windows; native-size-drawn art needs 2x bitmaps. Can we blanket-override all UI PNGs
at 2x, or does shared art break the screens we do NOT scale (region view, loading,
dialogs, menus)?

## Verdict

**Blanket 2x is NOT safe. Use a selective override: same-TGI 2x replacement for
images used exclusively by scaled windows, cloned-instance retargeting for images
shared with unscaled screens, and doubled `imagerect` values wherever art is 2x.**

> ### ADDENDUM 2026-07-29 — TWO LIMITS OF "SELECTIVE IS ENOUGH"
>
> The selective mechanism is still right, but it assumes (a) the stock scripts
> are what the game loads and (b) our package is what wins. Both can be false:
>
> **1. THE LOAD-ORDER LAW.** Files in the `Plugins` **root** load BEFORE files
> in **subfolders**, so a root `z_*.dat` can NEVER override a dat inside a
> subfolder. Another mod in `150-mods\` therefore beats our root package for
> any TGI it also ships. Overrides of another mod must live in a folder sorting
> after it (`zzz-SC4UIScale\`). This cost two failed deploys (submenu icons,
> then the Building Style panel).
>
> **2. A PLUGIN CAN REPLACE A STOCK `.UI` SCRIPT AND/OR ITS ART WHOLESALE.**
> Then the ref-map built from stock scripts describes a layout the game is not
> using, and our 2x art lands under a 1x `imagerect` (or vice versa). Build the
> override from **the MOD's** script and art — never the stock ones (different
> dimensions; using stock silently reverts the mod's own features). Handled by
> the `thirdparty-ui\` / `thirdparty-art\` inputs in
> `build_selective_safe.py`.
>
> **RECOGNITION RULE (cheap):** if a panel's LIVE window count or root size
> does not match the stock script you are reading, a plugin has replaced that
> script — grep `Plugins\**\*.dat` for the TGI before touching anything.
> Corollary seen in practice: **wrong text COLOUR was a symptom of the wrong
> SCRIPT being loaded**, not a font or colour bug.
>
> Also worth knowing here: `GZWinBMP`-family windows draw **dst = src size**,
> so 2x art scales the draw with no code hook — and a 2x source rect over a 1x
> bitmap draws only the corner that exists, which is exactly what a shadowed
> art override looks like on screen.

> ### NOTE ON THIS SNAPSHOT — settled corrections
>
> The binding model in this file was re-derived from the exe after it was
> written; `SC4-UI-ENGINE.md` §4/§4A and `SDK-GAPS.md` are the current
> reference. Four statements below are settled as follows:
>
> 1. **"PNG, TypeID 0x856DDBAC"** (§2) — `0x856DDBAC` is a generic image
>    type. 74 of the 2,280 entries are JFIF (41, all of group `CA133ECB`),
>    SHPI/FSH (26, inside `46A006B0`) and BMP (7, inside `6A1EED2C`). None is
>    `.UI`-referenced, so the selective mechanism is unaffected — but an art
>    tool that assumes PNG will trip over them.
> 2. **"a ref's GID is honored"** (§2) — true for 5 of the 6 ref GIDs.
>    `{82b9b75b,e2b66db8}` in `I-cb40cfdc` names a group that exists in no
>    archive while its instance is a real strip under `46A006B0`; whether the
>    engine falls back to instance lookup or the buttons simply draw
>    unskinned is reference gap G11 in `SDK-GAPS.md` §13.
> 3. **the `edgeimage` mechanism** (§3) — `imagerect` is a SOURCE RECT, never
>    an inset: `GZPaint` divides only `r` and `b` by 3 and leaves `l`/`t`
>    alone, so the 9-slice cell is `(r/3 − l, b/3 − t)` sampled from `(l,t)`
>    (`SC4-UI-ENGINE.md` §4A.7). The practical rule is unchanged and now has
>    a derivation: 2x art requires doubling all four `imagerect` numbers.
> 4. **the 2,280-vs-431 gap** (§2 reason 4) — quantified: 266 exemplar
>    ItemIcons, 61 `sc4://` HTML refs, 76 code image-request sites across 7
>    groups, plus three code-only groups (`6A1EED2C`, `AB7E5421`,
>    `A9179251`) that are largely not UI at all (`SDK-GAPS.md` §9).

Four independent reasons, each fatal to blanket replacement, evidence below:

1. **One image pool serves every screen.** UI images are not partitioned per screen.
   Of 431 distinct image references in the game's .UI scripts, 213 are used by more
   than one UI file, and at least 13 are used by BOTH city-HUD-side windows AND the
   region/loading/neighbor screens — including the universal 180x180 dialog-chrome
   9-slice and the standard button strips that appear on virtually every dialog.
2. **Much art is drawn at bitmap-native size or pixel-registered.** 419 GZWinBMP
   controls have `area` exactly equal to the PNG dimensions (1:1 blit). The region
   screen background (`{46a006b0,13d14ca0}`, 235x222) is drawn as a pixel-registered
   collage: multiple controls each paint a slice via `imagerect` values that are
   absolute bitmap pixel coordinates. 2x art shows the wrong quarter of the bitmap.
3. **9-slice geometry lives in the .UI script in pixels.** `edgeimage=yes` controls
   define the stretchable center as `imagerect=(l,t,r,b)` in bitmap pixel coords
   (e.g. `imagerect=(12,22,180,180)` on the 180x180 chrome PNG). 2x art with a stock
   imagerect slices in the wrong places on every unscaled dialog that uses it.
4. **Most PNGs are not bound through .UI at all.** SimCity_1.dat holds 2,280 PNG
   resources (type 0x856DDBAC); only 431 are referenced from .UI text. The rest are
   bound by exemplars (menu ItemIcons) and by engine code (loading screens, etc.)
   that draw at stock size. A blanket override touches consumers we cannot audit
   from .UI files.

## 1. The .UI format (primary source: extracted from the game)

Verified directly against `C:\Program Files (x86)\Steam\steamapps\common\SimCity 4
Deluxe\SimCity_1.dat` using `tools\dbpf\DbpfExtract.cs` (330 type-0 entries
extracted, QFS-decompressed; commands in the appendix).

- **TGI**: UI layout scripts are **TypeID 0x00000000** inside SimCity_1.dat.
  They are plain text ("`# Generated by UI editor`" headers), XML-ish **LEGACY
  markup**: unquoted attributes, tags closed by a bare `>`, `<CHILDREN>` blocks for
  nesting, `#` line comments. Not valid XML; needs a lenient parser.
- **Group IDs found (330 files)**:
  - `0x96A006B0` — 271 files: the default UI layouts (all screens).
  - `0x08000600` — 10 files: **800x600-resolution variants**. Per the SC4D wiki, a
    resolution-specific UI file uses the literal screen resolution as its GID ("not
    converted to hex": 800x600 -> 0x08000600). The engine picks the variant by
    current resolution — a built-in per-resolution UI selection mechanism, and
    NAM's Jonathan confirms modders can ship per-resolution UIs "without the user
    having to swap plugins in and out".
  - `0x4A87BFE8` — 1 file: the font-style config (style name -> face/size/GUID
    table), not a window layout.
  - `0x8A5971C5` — 48 files: binary payloads (not LEGACY text, no image refs) —
    not window layouts; ignore for art work.
- **Location**: ALL type-0 UI files and ALL UI PNGs live in SimCity_1.dat only.
  SimCity_2.dat through SimCity_5.dat contain zero entries of either type.
- **Coordinates**: `area=(l,t,r,b)` — left/top/right/bottom, **not** (x,y,w,h) as
  the wiki table claims. Proven by button rows: consecutive buttons at
  `(68,28,115,65)`, `(68,78,115,115)`, `(68,128,115,165)`... = 47x37 buttons
  stacked at 50px pitch, and 47 matches the image state-cell math below. The same
  LTRB convention applies to `imagerect`.

## 2. How controls bind images

- Exactly **one attribute** carries image bindings in the shipped files:
  `image={gid,iid}` (2,962 occurrences; the census found no in-use `thumbimage`/
  `containerimage`/`backimage` etc., though the format defines them for
  Scrollbar2/OptGrp/TextEdit). Type is implied: **PNG, TypeID 0x856DDBAC**, looked
  up by the group+instance given in the ref (refs to `46a006b0`, `1abe787d`,
  `22dec92d`, `4c06f888` groups all resolve to PNGs stored under those exact
  groups — so a ref's GID is honored, which selective retargeting can exploit).
- **Reference pool**: 431 distinct `{gid,iid}` pairs referenced across all .UI
  files. GID distribution of refs: `46a006b0` 396, `1abe787d` 19, `22dec92d` 12,
  `4c06f888` 2, others 3. The PNG store itself: 2,280 PNGs across 10 groups
  (`46a006b0` 810, `1abe787d` 743, `6a386d26` 356, `4c06f888` 112, `ab7e5421` 93,
  `00000001` 62, `ca133ecb` 41, `22dec92d` 39, `6a1eed2c` 20, `a9179251` 4).
  Some chrome images are stored twice (same IID under both `46a006b0` and
  `1abe787d`, identical dimensions).
- The gap between 2,280 stored and 431 .UI-referenced PNGs is the exemplar/code
  bound majority (menu ItemIcons, loading art, cursors, etc.) — reason 4 above.

## 3. Stretch vs native-size drawing

Three attributes control it (SC4D wiki property table + empirical checks):

- `blttype = tiled | normal | edge` — tally across all 330 files:
  edge 277, tiled 254, normal 9. `edge` stretches, `tiled` repeats the bitmap at
  native pixel size, `normal` is a plain blit.
- `edgeimage = yes | no` (GZWinBMP) — yes 56, no 788. With `yes`, the bitmap is a
  9-slice: `imagerect=(l,t,r,b)` gives the stretchable center rect **in bitmap
  pixel coordinates**. Verified: chrome PNG `{1abe787d,14416240}` is 180x180 and is
  drawn with `imagerect=(12,22,180,180)` into areas 270x70, 266x74, 320x91 — fixed
  12/22px borders, stretched middle. **The insets are in the .UI text, in pixels:
  2x art requires doubling the imagerect (and the runtime layer must double
  imagerect whenever it doubles area).**
- `imagerect` with `edgeimage=no` is a source crop, and Maxis uses it for
  pixel-registered collages: in the region screen file (I-c973b411, present in both
  G-96a006b0 and G-08000600), the 235x222 background `{46a006b0,13d14ca0}` is
  painted by several GZWinBMPs whose `imagerect` l,t equals their own area l,t —
  bitmap pixels map 1:1 onto window pixels. Strictly native-size; breaks with 2x
  art unless every consuming control is scaled too.
- **GZWinBMP native-draw frequency**: of the BMP controls whose PNG exists in
  SimCity_1.dat, 419 have area exactly equal to PNG dimensions (1:1) and 340
  differ (tiling/edge/crop cases). Native drawing is the norm, not the exception.
- **GZWinBtn state strips**: a button's `image` is a horizontal strip of states.
  875 buttons satisfy pngWidth = 4 x buttonWidth with pngHeight = buttonHeight
  (4 states, cell drawn 1:1); a smaller population shows 8x (toggle variants).
  However, the standard dialog-button strip `{46a006b0,144161eb}` (120x30; 30px
  cell) is referenced by buttons 130-370px wide (height always 30), and
  `{46a006b0,53244588}` (84x19; 21x19 cells) sits on 18x16 buttons — so for
   standard styles the engine fits/stretches the state cell to the button area at
   least horizontally. **Reference gap (G27, `SDK-GAPS.md` §13)**: whether the
   vertical dimension also stretches. Until it is settled, treat shared button
   strips as unsafe for in-place 2x.

## 4. Sharing across screens (the blanket-2x killer)

Cross-referencing every `image=` ref against every .UI file:

- 213 of 431 refs are used by more than one .UI file.
- Splitting files by screen keywords (region/neighbor/loading/etc. in captions and
  tooltips) gives ~23 region-/loading-/neighbor-side layout files vs the rest;
  **13 image refs cross that boundary**, including:
  - `{46a006b0|1abe787d,14416240}` and `{...,144161ee}` — 180x180 window-chrome
    9-slices used by dialogs everywhere;
  - `{46a006b0,144161eb}`, `{46a006b0,14416316}`, `{46a006b0|1abe787d,14416246}`,
    `{46a006b0,14416245}`, `{...,144161e4}` — the standard button strips (used by
    100+ windows on every screen);
  - `{46a006b0,13d14ca0}` — the region-screen background collage, ALSO referenced
    by city-side custom controls;
  - `{46a006b0,14015586}`, `{46a006b0,53244588}` — list/nav buttons used across
    city query windows AND region-side panels.
- The keyword split is heuristic; the definitive boundary is "windows the runtime
  layer scales" vs everything else, computable exactly with the same extraction +
  ref-map method (appendix) once the scaled-window instance list is fixed.
- Remember the 0x08000600 twins: any window that exists in both groups references
  the same art from both variants; an audit keyed only on G-96A006B0 misses them.

## 5. Community prior art

- **SC4D Encyclopaedia "UI" page** (mirrored on SimsWiki): the LEGACY format, the
  full attribute table (`image`, `imagerect`, `blttype`, `edgeimage`, winflags,
  style enums), and the resolution-as-GID rule quoted in section 1.
  https://wiki.sc4devotion.com/index.php?title=UI /
  https://simswiki.info/wiki.php?title=UI and ...title=00000000
- **SC4Devotion: "has anyone modded the UI?"** (2010, archived) —
  https://www.sc4devotion.com/forums/index.php?topic=10582.0
  - SimMars re-skinned the whole UI; GTM moved God-mode tools into Mayor mode; a
    Japanese all-black UI mod existed. All were done as plugin overrides of the
    SimCity_1.dat resources.
  - Jonathan (NAM; author of "Raise the UI Mod"): per-resolution UIs work without
    plugin swapping; hard limits exist (can't add menus; menus stay on the left).
  - jigsaw's smoked-glass recolor: strictly 1:1 pixel replacement; resizing
    buttons was deferred because "it affects other things around it" — the
    community's practical experience that geometry changes ripple.
- **Raise the UI Mod** (Simtropolis file 23771) — ships edited .UI files as a
  plugin to move HUD windows: precedent that same-TGI .UI overrides from the
  Plugins folder are honored and stable. (Page body behind a bot checkpoint;
  identified via the SC4D thread signature and the file listing.)
- **Steam discussions ("UI scale change?", "…microscopic")**: as of the thread
  dates nobody has shipped hi-res UI art for SC4; workarounds are lower
  resolution or external magnifiers. Our 2x art effort is first-of-its-kind —
  there is no existing 2x package whose sharing decisions we can copy.
- Query-modding tutorials (Simtropolis omnibus r187) establish custom .UI +
  custom image plugins as routine; not fetchable in full (bot checkpoint), noted
  for completeness.

## 6. Recommended mechanism (selective 2x)

1. **Fix the scaled set S**: the exact .UI TGIs (G-96A006B0 AND their G-08000600
   twins) whose windows the runtime layer doubles.
2. **Compute the partition** with the extraction + ref-map scripts (appendix):
   - `EXCLUSIVE = refs(S) - refs(all others)` — safe to 2x **in place**: ship a
     plugin DBPF overriding the same PNG TGIs (Plugins load after SimCity_1.dat;
     same-TGI wins, standard modding practice).
   - `SHARED = refs(S) ∩ refs(others)` — **never touch the original TGI**. Clone
     each PNG at 2x under new instance IDs (a dedicated group, e.g. a private
     "HD" GID, keeps them auditable), and retarget only S's `image={gid,iid}`
     refs at the clones. Retargeting can be done either by shipping edited .UI
     overrides for S, or — since the runtime layer already rewrites these windows
     — by rewriting the refs at window-creation time. The .UI files are plain
     text; the edit is a string substitution.
3. **Double `imagerect` alongside any 2x art** (both 9-slice rects and collage
   crops are bitmap-pixel LTRB in the .UI). Rule of thumb: whatever doubles
   `area` must double `imagerect` on the same control.
4. **Leave the other 1,849 non-.UI-referenced PNGs alone** until each consumer
   (exemplar ItemIcons, loading screens) is individually understood.
5. **O1 is filed as reference gap G27** (`SDK-GAPS.md` §13) — if buttons
   stretch both axes, the shared standard strips can move from SHARED to
   "2x in place is harmless", shrinking the clone set substantially.
6. Research lead (not required): the resolution-as-GID mechanism (0x08000600
   pattern) might let a "big UI" variant ship keyed to the table's exact
   resolution with zero runtime .UI rewriting; untested for arbitrary
   resolutions, and it would still need the same art partition — evaluate later.

## Appendix: reproduction

Tool: `tools\dbpf\DbpfExtract.cs` (compile with .NET Framework csc; no deps).

```
DbpfExtract.exe "...\SimCity 4 Deluxe\SimCity_1.dat" out\ui  0x00000000   # 330 UI files
DbpfExtract.exe "...\SimCity 4 Deluxe\SimCity_1.dat" out\png 0x856DDBAC   # 2280 PNGs
```

- UI files are text despite the tool's .png naming; grep for `image=\{gid,iid\}`,
  `blttype=`, `edgeimage=`, `imagerect=`, `area=`.
- Ref map: for each UI file, collect distinct `image={g,i}`; invert to
  image -> [files]; intersect file partitions to find shared art.
- PNG dimensions: bytes 16-23 of the file (IHDR width/height, big-endian) — no
  image library needed.
- Key measured examples: `{46a006b0,14215e30}` 188x37 on 47x37 buttons (4-state
  strip); `{1abe787d,14416240}` 180x180 chrome with `imagerect=(12,22,180,180)`;
  `{46a006b0,13d14ca0}` 235x222 region collage; `{46a006b0,144161eb}` 120x30
  standard button strip on 130-370px buttons.
