# FINAL-3-PERCENT — closing report on the unmapped UI

**Date:** 2026-08-03. **Exe:** `SimCity 4.exe` 1.1.641.0 Steam, ImageBase `0x400000`,
sha256[:16] `1189720d5e15b0e1`, 7876608 bytes. **Source tree:** v2.55.0.

Nothing in `src\`, the game install, `Documents\SimCity 4\Plugins`, or any package was
touched. Every number below was either re-derived this session from a checked-in artifact
(`tools\uimap\_work\edges.json`, `funcs.json`, `wincensus.json`, the 330-file `.UI`
corpus, the 5 retained `.log` files) or read out of the exe with the existing
`tools\uimap` harness. Where I quote another agent's measurement without reproducing it,
it is labelled **[not reproduced]**.

---

## ⚠ READ FIRST — every line number quoted in the four input reports is stale

The parallel effort landed task #57 (Graphs legend, v2.55.0) in `src\UiSpike.cpp` **today,
after** those reports were written. Verified drift:

| report says | actually (v2.55.0) | what it is |
|---|---|---|
| `UiSpike.cpp:7609` | **`:7630`** | the ≥90%-of-screen sweep guard |
| `UiSpike.cpp:12549` | **`:12587`** | same guard in `ScaleMenuFlyouts` |
| `UiSpike.cpp:12144` / `:12160` | **`:12182`** | `kBmpxDialogRoots[]` |
| `UiSpike.cpp:3184` / `:3178` | **`:3117`** | `kNeverScaleIds[]` opening brace |
| `UiSpike.cpp:3165` | **`:3186`** | the `0x4A35B0F2` tutorial-page entry |
| `UiSpike.cpp:7010` | **`:7015`** | the single-find in `HookRuntimeBmpsUnder` |
| `UiSpike.cpp:11150` | **`:11172`** | the `0xAA921F4F` `kCityDialogIds` row |

**Do not apply any of the input reports' edits by line number.** Match on text. This is
its own small law: *a file:line citation is an instrument, and it decays the moment
someone else edits the file.*

---

## 1. THE HONEST NUMBER

### The headline falls, by 1.7 points

> ### **94.9% — 299 of 315 named shipping windows carry a scaling mechanism.**
> (was 96.6% = 288/298, which counted only the *scriptable* UI)

The denominator grew by the 17 code-created windows we can now name. The numerator grew
by 11 of them. Both movements are itemised below and both are auditable.

### Three denominators, kept separate — do not merge them

The census's own recommendation #3 was to keep a second denominator distinct from the
first. That is right, and this report holds to it.

```
D1  script-declared shipping ROOTS         298     covered 288    96.6%
D2  code-created NAMED shipping windows     17     covered  11    64.7%
    -------------------------------------------------------------------
    D1 + D2   (the honest headline)        315     covered 299    94.9%

D3  windows we can SEE but cannot NAME     — not a percentage, see §1.4 —
```

**D1 is unchanged and still correct for its scope.** 288/298. The ladder
(330 depth-0 `<LEGACY>` roots − 8 third-party plugin − 24 caption-verified dev-editor)
was independently recounted 2026-08-03 and stands. Corpus recount today: **330 `.ui`
files parsed, 1408 distinct `id=` values** (the input report said 1409 over a 331+9 file
set — a ±1 file-set difference, not a disagreement of substance).

### 1.1 D2 in full — the 17, with this session's corrections applied

Band-derived from `wincensus.json` (`setIds` owner in `0x760000–0x7FFFFF`, plus
`0x6104489A` and `0x4C30E4FA` which sit in the "other" band but are unambiguously
shipping, minus the two dev profiler panels `0x6ACB1AF1` / `0x6ACB1C40`). I reproduced
the band split exactly: GZ 20 ids, SC4-liveUI 17, dev-editor 20, other 7 — 64 distinct
ids over 73 literal-`SetID` sites.

| id | what | verdict | mechanism / why not |
|---|---|---|---|
| `0x9A47B417` | `cSC4View3DWin` | COVERED | sweep root; must stay full-screen |
| `0x6104489A` | SC4 App window | COVERED | sweep root; must stay full-screen |
| `0x6A5E44B6` | **`cSC4WinAlertBorder`** | COVERED | art (3 sheets, v2.37.2, user-confirmed #59) + ≥90% skip at `UiSpike.cpp:7630` |
| `0x2AAB8CC1` | tooltip layer | COVERED | wrap patch + art, #41 |
| `0x8A6E61E0` | sub-flyout container | COVERED | born-scale, #76/#95 user-confirmed |
| `0x8A2CAD8B` | sub-flyout container | COVERED | born-scale, #76/#95 user-confirmed |
| `0x2BA6BB97` | `cSC4WinRegionView` | **COVERED — was "UNREACHABLE"** | dialog-static on the two bubble scripts; #72 user-confirmed. **See §5.1 — this was refuted with a counterexample in our own log.** |
| `0x0423278D` | ordinance/deal shared text popup | **COVERED — was "UNCOVERED (no mechanism)"** | `CodePatches.cpp:201/246/256/464` byte patches **+** the sweep pin at `UiSpike.cpp:12008–12060`, **+** `UiSpike.cpp:11769` |
| `0x0423278E` | ordinance content pane | **COVERED — was "UNCOVERED"** | `UiSpike.cpp:11900` `GetChildWindowFromID(0x0423278E)` |
| `0x0423278F` | ordinance/budget content root | **COVERED — was "UNCOVERED"** | per-instance runtime pass `UiSpike.cpp:11816–11945`, popup pin `:12041–12043` |
| `0x4C30E4FA` | ×6 pooled callout | COVERED **but AT-RISK** | in `kCityDialogIds` (`UiSpike.cpp:11207`) — mechanism present, so covered by our own Q1 definition, **but the label is wrong and two levers fight** (§3.2) |
| `0x00000043` | Restore-Toolbars button | **UNCOVERED, quantified defect** | 10 px clip at birth, 20 px after our own sweep (§3.3) |
| `0xEA659793` | region screen | UNCOVERED | region pass is whitelist-only; `kRegionPanelIds` does not contain it |
| `0x6A0AF41D` | region cloud emitter | UNCOVERED — **and correctly so** | cosmetic; sprite size is a code constant (§3.1). Recommend leaving alone. |
| `0x85202C0E` | ? (vt `0xAB9980`, `sub_7BC350`) | ROLE UNKNOWN | never in any retained log |
| `0xA802B4EB` | ? (vt `0xAB6010`, `sub_7F0840`) | ROLE UNKNOWN | never in any retained log |
| `0x9AEDEF7C` | image file browser | ROLE UNKNOWN | never in any retained log |

**11 covered / 3 uncovered / 3 role-unknown.** The census's "295/314 = 93.9%" is
superseded: it counted `0x2BA6BB97` out of the denominator as unreachable (wrong) and
counted the three Ordinances ids as having no mechanism (also wrong — we ship one).

### 1.2 The bound, stated as a bound

> **At least 315 named shipping windows exist. There is no offline upper bound.**

Three named, quantified channels put windows outside the census by construction. I
reproduced all three from checked-in data this session:

1. **A third creation route the census does not model.** Creation through the runtime COM
   singleton `0xC2C2EB0F` (getter `sub_913C72` @ `0x00913C72`): no literal clsid at the
   create site, no `call 0x005E55E0`, so it is invisible to Route A *and* Route B.
   **Reproduced:** `edges.json` holds **220 `call` edges to `0x00913C72`, spread over 129
   functions; 106 of those 129 the census classifies as no kind of creator; 27 of the 106
   are in the live-UI band `0x760000–0x7FFFFF`.** This is a measured hole, not a worry.
2. **`sub_779660` — a generic window factory whose id is a register.** 86 call sites in
   exactly 6 functions (`sub_77BEC0`, `sub_77C660`, `sub_77E600`, `sub_786690`,
   `sub_7876B0`, `sub_78B120` — three of them the Ordinances builders). It does
   `call 0x913c72` → `call [edx+0x34]` (create) → `push edi; call [edx+0x100]`
   (`SetID` with the id **in a register**). I scanned the 86 sites for the literal pushed
   into that register within 14 instructions: **21 distinct large literals**, of which at
   least five — `0x0ABCE000`, `0x0ABCE001`, `0x0ABCDE00`, `0x0ABCDE01`, `0x0ABCDE02` —
   are confirmed window ids (`CodePatches.cpp:201/246`, and `0x0ABCE000/1` are live in
   the retained log). **None of the 21 is in the census's 64-id table.** The rest of the
   21 are probably LTEXT keys; I did not separate them, so treat 21 as an upper bound on
   that site set and 5 as the confirmed floor.
3. **Anonymous windows.** The census itself counts **109 creation sites that assign no id
   at all** (24 in the live-UI band). No id-keyed rule can ever address them.

### 1.3 D3 — and the best news in this report

The refutation pass flagged, correctly, that **36 window ids appear in retained logs and
are in neither the `.UI` corpus nor the census's 64 literal-`SetID` ids**, and used that
to argue the denominator is ≥350 and coverage ≤85%.

**I reproduced the 36 exactly** (independent script, this session: 171 distinct live ids
across the 5 retained logs; 122 in the corpus; 12 in the census setIds; **36 in neither**,
plus `0x00000000` for the id-less). Positive control: the same scan finds `0x6BB92BCB` in
`I-abb0120f` and `0x27DF05BE` in exactly `I-2a41436c` + `I-6a9455c9`, so an empty result
would have been a MEASURED null.

**Then I did the step nobody had done: I resolved each of the 36 to its dump parent.**

```
0x0000012C..0x00000137  (12)  ── children of 0x0423278F   (MWKID)
0x000002F4..0x000002FF  (12)  ── children of 0x0423278F   (MWKID)
0x00000551..0x00000554  ( 4)  ── children of 0x0423278F   (MWKID)
0x0000016D, 0x000001CD  ( 2)  ── children of 0x0423278F   (MWKID)
0x0ABCE000, 0x0ABCE001  ( 2)  ── children of 0x0423278F   (POPKID)
0x00000168, 0x00000068  ( 2)  ── the ordinance popup dump (POPKID roots 0/0.0)
0x00000484, 0x00000384  ( 2)  ── the ordinance popup dump (POPKID roots 1/1.0)
                        ----
                          36
```

**All 36 are descendants of one family: Ordinances.** Not 36 independent coverage gaps —
**one**, and it is the family already named in `D2` and already covered by a shipped
mechanism. Method: linear walk of each log tracking the most recent `PREFIX N` root line
before each `PREFIX N.M` child line. (My first attempt used a label→id dict and silently
mis-attributed the parent, because labels repeat across dumps; the sequential version is
the one reported.)

**Therefore the refutation's "≥350 / ≤85%" figure is itself a category error** — it adds
*child* windows to a denominator built from *roots*. The refutation's underlying
measurement (36 ids, in neither inventory) is correct and valuable; the coverage arithmetic
built on it is not. Corrected: the 36 add **zero** roots, and their coverage is inherited
from `0x0423278F`, which is covered.

### 1.4 What the remaining unmapped surface actually is, and why most of it is fine

This is the load-bearing honest finding of this report, and it is good news:

> **The sweep is structural, not id-keyed. `ScaleSubtree` recurses on the child list.
> A window does not need an id, a script, or a list entry to be scaled — it needs a
> covered ancestor.**

Two anonymous classes I identified this session prove it, and they also close two
"UNIDENTIFIED" entries in `coverage-matrix.md §8`:

- **`0xAA5C2F86`** ("TrendBar, buffer unverified") — appears in the corpus **only as a
  `clsid=`**, on nodes carrying **no `id=` at all**, `145x9` bars. It is scaled today
  purely because its parent root is swept.
- **`0xC7A0E17E`** ("in status panel, UNIDENTIFIED") — same: `clsid=` only, id-less nodes
  of `71x4` and `8x71`. Thin meter bars.
- **`0x28C5A41F`** ("in Data Views, UNIDENTIFIED") — **not a window id at all.** It is the
  `clsid` of the Data Views **Map-View page**, and in all three declaring scripts
  (`I-0b72f276`, `I-2bc9060f`, `I-ea287193`) it carries `iid=IGZWinCustom id=0x00004200`.
  That is the page that hosts the scrollbar of §3.4. Three "unidentified code-painted
  classes" were two anonymous bar widgets and one mis-read clsid.

So the honest characterisation of the residual, in three sentences:

1. **The named residual is 16 windows** (3 uncovered + 3 role-unknown in D2, 10 uncovered
   roots in D1) — small, enumerated, and every one has a next step in §3 or §4.
2. **The unnamed residual is large in count and low in risk**, because it is overwhelmingly
   *anonymous children inside covered parents*, which the recursive sweep reaches without
   ever knowing their ids.
3. **The residual we cannot bound is the one that matters**: windows created by the
   `0xC2C2EB0F` singleton in functions the census sees as non-creators, at 27 sites inside
   the live-UI band. That is where the next genuinely-unknown defect will come from.

### 1.5 Sentences that must not be written again

- ~~"96.6% of the UI is covered."~~ → "96.6% of the *scriptable* UI; 94.9% once the
  code-created windows we can name are counted; unbounded above."
- ~~"295/314 = 93.9%, a floor not a correction."~~ → It was neither. Two of its inputs
  were wrong (§5.1, §5.2) and nothing in this repo bounds the three channels in §1.2.
- ~~"Covered" as a synonym for "works."~~ → `0x6BB92BCB` is covered by no mechanism and is
  a live defect; `0x00000043` has 2x art shipping and a 10 px clip; `0x4C30E4FA` has *two*
  mechanisms and a wrong label. Mechanism-present is the weakest useful claim.

---

## 2. IDENTITY RESOLVED — `0x6A5E44B6`

**`0x6A5E44B6` is `cSC4WinAlertBorder`.** The premise "IDENTITY UNKNOWN" in
`coverage-matrix.md §5` was three days stale when this batch started: it was named, fixed
and user-confirmed on **2026-07-31 as task #59, shipped in v2.37.2**.

Confirmed in-repo this session at `_tests\REGRESSION.md:3487-3489`,
`VERSION-HISTORY.txt:2573-2574` and `tools\selective-safe\build_selective_safe.py:356-357`.

| fact | address | source |
|---|---|---|
| clsid | `0xCA5D3294` | GZCOM table `.data 0x00B08F70` → name string `"cSC4WinAlertBorder"` at `0x00A895FC` (one reference image-wide); cross-checked `vendor\gzcom-dll\...\GZCLSIDDefs.h:282` `kcSC4WinAlertBorder` |
| vtable | `0x00AB5B48` | 5 slots overridden vs base `cGZWin` `0x00ADC8D8`: QI/AddRef/Release, **Plot `+0x160`→`0x00794100`**, dtor `0x007940E0` |
| ctor / size | `0x00794060`, `0xEC` bytes | `push 0xEC` @ `0x007941C0` → `operator new 0x005E55E0`; image ptr at `+0xE4`; render-props singleton at `+0xE8` |
| created | `0x007EF029` in `sub_7EDEB0` | `push 0xca5d3290 (iid); push 0xca5d3294 (clsid); call [eax+0x0C]` |
| id set | `0x007EF072` | `push 0x6a5e44b6; call [eax+0x100]` (SetID) — **the only two `0x6A5E44B6` immediates in the image are here and the one lookup at `0x007E8AA6`** |
| sized | `0x007EF069` | `SetArea(0, 0, viewW, viewH)` — computed from the live view rect, **no baked constant** |
| flags | `0x007EF088/99/A7` | PrivateBuffer **off**, IgnoreMouse **on**, AlphaBlend **on** |
| drawn | `Plot = 0x00794100` | one nine-slice of one image: `cell = (imgW/3, imgH/3)`, `NineSlice(ctx, img, &cell, &this->area, 0)` at `call 0x008D9550` (**one caller image-wide**), corners blitted **unstretched** |
| image set | `sub_00793FF0` | secondary vtable `0x00AB5B20` slot 4; writes `obj+0xE4` |
| state | `UpdateAlertBorder 0x007E8A90` | disaster → RED `0x14315E60`; else situation → GREEN `0x14315E62`; else paused → GOLD `0x14315E61`; else `SetImage(NULL)` |
| gate | `[renderProps+0x0C]+0x45C` | bool property `kDisplayAlertBorders`, id `0x22`, stride `0x20`: `0x1C + 0x22*0x20 = 0x45C` — matches `cISC4RenderProperties.h:47` |

**Why it is covered without being in any list.** Corners blit unstretched ⇒ stroke
thickness *is* the art pixel count ⇒ the fix is the art, and all three sheets ship at all
three tiers (2x 240×240 → cell 80; 1.5x 180×180 → 60; 3x 360×360 → 120; `/3` exact in
every case). The window itself is skipped by the generic sweep on **geometry**, at
`UiSpike.cpp:7630` — `if (p.w >= screenW*9/10 && p.h >= screenH*9/10) continue;` — and the
same guard exists at `:12587` and `:5122`. At exactly 100%×100% it is unconditionally
skipped. That is a structural reason, not a gap.

**One correction to a sibling note.** `tools\research\_incoming\sdkgaps-04.md §2.6/§8.6`
says the class has a "three-image setter at `0x007942F0`" filling `+0xE0/+0xE4/+0xE8`.
**Wrong.** `sub_7942F0` is in no vtable and is no immediate anywhere in the image; its only
caller is `0x0079710A` inside `sub_796C68` — a different class. It cannot be an AlertBorder
method: `+0xE0` holds a *vptr* and `+0xE8` the render-props singleton, both of which that
function would clobber. There is **one** image field, at `+0xE4`, set by `sub_00793FF0`.

**Residual risk, one line.** The protection is a size heuristic, not an id rule. Any future
change that lowers the 90% guard resizes this window to 4800×3200 and drags the frame
off-screen. `0x6A5E44B6` is a legitimate `kNeverScaleIds` candidate as belt-and-braces —
but it is currently *covered*, not *uncovered*.

**UNKNOWN and unimportant:** the sub-object vtable `0x00AB5B34` at `+0xD8` (ctor calls
`0x0090D957` on it); never touched by Plot.

---

## 3. THE ADJUDICATED FOUR

Ranked by what a player actually hits.

### 3.1 `0x6A0AF41D` — region cloud emitter. **VERDICT: UNCOVERED, COSMETIC, LEAVE ALONE.** (rank 4)

**Do not generalise from `0x2BA6BB97` to reach this verdict — that sibling premise is
itself refuted (§5.1). This one stands on its own evidence.**

`Plot = sub_7A9D60` (`0x007A9D60..0x007AA110`, whole function read) is a **particle
emitter drawn through the 3D device**, not a `cIGZWin` blit:

- ctor `sub_7A9AE0` → vt `0x00AB88C0`; zeroes scroll offsets `+0xF0/+0xF4`; empty list head
  `+0x114`; four null texture slots `+0x118..0x124`.
- init `sub_7A99C0` loads `0x4A624656..0x4A624659` (iids `{0x1AC0E11A, 0xFAC0E219}`), then
  **latches the emitter bounds once**: `view->GetW() → float [+0x100]`,
  `view->GetH() → float [+0x104]` at `0x7A9A95–0x7A9AC5`.
- spawner `sub_7A98E0`: `x = 0 − K`, `y = rand·H`. Plot: `x += vx·dt`; despawn at
  `x ≥ [+0x100]`. Quad corners at `±K` where **`K = float @ 0xAB7E10 = 128.0`**, hardcoded.
- art: `T=0x7AB50E44 G=0x1ABE787D I=0x4A624656..59`, four **DXT3 FSH at 128×128**;
  one was decoded — a white wispy **cloud**. Blitted 1:1 at native 128 px. **[not
  reproduced this session — decode was done by the adjudicating agent; the TGIs and the
  `0xAB7E10` constant are the checkable part.]**

Resizing the window is a **no-op**: bounds are read once at init and the window is already
`(0,0 2400x1600)` in every retained log. The only "1x" thing is the **sprite size**, a code
constant. Two levers exist and are named: the float `0xAB7E10 = 128.0`, and the four-TGI
art set. Player impact: 128 px clouds over a 2400×1600 map instead of ~384 px. Purely
decorative and arguably better small.

**Doc correction:** `SC4-UI-ENGINE.md §2.4`'s "resource-driven, not rect-driven" row should
read *sprite-size-driven by `0xAB7E10`*.

### 3.2 `0x4C30E4FA` ×6 — **VERDICT: mechanism present (so COVERED by our definition) but the LABEL IS WRONG and TWO LEVERS FIGHT.** (rank 3)

- Created by `sub_430680`; `SetArea(0,0,100,100)` @ `0x00430721`; **`HideWindow()` @
  `0x00430741`** — it is born hidden **by construction**. Every `vis=0` in every dump is
  therefore explained by the constructor, and was never evidence of deadness.
- **The show path exists.** `sub_430F70` (`0x00430F70..0x004311B0`) is a per-tick message
  handler (QI iid `0x65297976`, `GetType() == 0xCB7CB509`) that reads W/H, **projects a
  world point to screen** via `[this+0x14] vt+0xDC`, computes `x = projX − W/2`,
  `y = projY − H − 8`, calls `GZWinMoveTo` @ `0x0043105A`, then runs a 4-state timed
  machine calling **`ShowWindow()` @ `0x00431130`** and `HideWindow()` @ `0x004310EB`.
- **Owner subsystem is My Sims**: the `0x18C`-byte owner is allocated in `sub_42C0E0`
  (`push 0x18C` @ `0x42C54E`, then `call sub_430680` @ `0x42C5E3`), which handles
  `0x0B6F3E27 = kSC4MessageMySim_DebugPrintMySimsInfo` and the `0x?B6F3Exx` family.

**Two corrections this forces:**

1. `UiSpike.cpp:11201/11207` labels it "Business Deals empty-state box", `designW 272`,
   base `272x200`. The creator is in the My Sims subsystem and the builder sets `100x100`.
   **The label is unsupported. Re-derive before anything keys off it.**
2. It names **six simultaneous windows**. Any single `GetChildWindowFromIDRecursive` grabs
   an arbitrary pool member — the documented hazard that `IdCollectCtx`
   (`UiSpike.cpp:11816` onward) was written to fix, and which `kCityDialogIds` still
   exposes here.

**Why at risk:** hidden ⇒ the sweep skips it; shown ⇒ next tick it is `Fresh` and
`ScalePanelRoot` both **moves and resizes** it, while the game re-positions it from its own
world projection every message. Size change persists; our move is fought. Plus
`kCityDialogIds` is a second lever on the same id. That is the v2.39.13 4x shape.

**Positive control for the null:** the three dumps reporting `vis=0` were taken at
region-up, city-init and a dialog test — never during an active callout — and the same
dumps report `vis=1` on other windows. MEASURED null about *those moments*, not a claim
about the game.

### 3.3 `0x00000043` Restore-Toolbars button — **VERDICT: UNCOVERED AND AT RISK. Clip quantified: 10 px at birth, 20 px after our own sweep.** (rank 1)

Built by `sub_7EDEB0` (`0x007EDEB0..0x007EF200`, the 3D-view HUD constructor — the same
function that builds `cSC4WinAlertBorder` at `0x7EF029`), from script `I-c973b411`
(`mov [esp+0x6c], 0xc973b411` @ `0x007EDECC`):

```
0x007EDFF6  CreateInstance(clsid 0x22ECFC47 GZWinBtn, iid 0x22BA0121) -> [esi+0x194]
0x007EE02F  image TGI {0x856DDBAC, 0x46A006B0, 0x53244588}
0x007EE13E  push 0x43
0x007EE140  call [edx+0x100]          ; SetID(0x43)
0x007EE146  view->GetH() ... sub eax,0x1C ... GZWinMoveTo(0xC, viewH-0x1C)
0x007EE175  call [edx+0x118]          ; HideWindow() -- born hidden
```

**The builder never sets a size.** `+0xE0` is `GZWinMoveTo` (2 args), not `SetArea`.

**Size, three independent instruments agreeing:**
1. Live (2 logs, 2026-07-22, pre-scale): `id=0x00000043 pos(12,1572) size(21x19) children=0 vis=0`, direct child of the 3D view.
2. Stock art `T-856ddbac_G-46a006b0_I-53244588.png` = **84×19** → 4-frame strip, cell **21×19**. Exact match.
3. `1572 = 1600 − 28`; `28 − 19 = 9` px bottom clear. Self-consistent.

**The defect is ours.** `0x53244588` is `EXCLUSIVE / 2x-in-place` in `refmap.csv` and in
`tools\selective-safe\package-list.txt:432`; the built 3x package carries it at 252×57
(= 84×19 × 3), so the 2x build is 168×38 → cell **42×38**.

- **Birth:** 42×38 at the code-fixed `(12,1572)` → bottom `1610 > 1600` = **10 px clipped**.
- **Second order, worse:** the button is skipped by the sweep only *while hidden*. The
  moment the player hides the toolbars it goes `vis=1` → `Fresh` → `ScalePanelRoot`.
  Working the math: `newW=84, newH=76`; `gapB = 1600 − 1610 = −10`, so the per-edge clamp
  is skipped as an "intentional overhang"; `newY = 1600 − (−20) − 76 = 1544`. Result
  **(24,1544) 84×76 → 20 px clipped**, 2x art in a 4x box. **v2.39.13 class.**
- **Control:** with 1x art the same math is clean — `gapB = +9`, bottom 1582. **The clip
  exists only because we ship 2x art for this TGI.**

**The "safe because no plugin uses id 0x43" reasoning is one integer wide.** The null is
real (no `.UI` declares `0x43`; positive control: the same scan finds `0x40`, `0x41`,
`0x42`, `0x44`). But `0x43` is **not** an arbitrary tiny integer — in the very script this
builder loads, `T-00000000_G-96a006b0_I-c973b411.ui` declares
`id=0x00000044 GZWinBtn 24x22 image={46a006b0,13d14c10} tiptext="Hide Toolbars|…"`.
**`0x43` and `0x44` are the two halves of one feature, one builder, one in code and one in
data.** The neighbourhood is a dense semantically-allocated command-id run (`0x29/0x31`
Transportation, `0x33` Emergency, `0x34/0x37/0x38/0x42`, `0x35/0x39/0x40` Utilities,
`0x41` Budget — all `GZWinBtn 47x37` tool buttons whose roots are in `SCALED_WINDOW_IDS`).
And SC4 demonstrably reuses tiny ids: `wincensus.json` shows `0x000000FF` stamped at three
unrelated sites (`0x435406`, `0x4360BB`, `0x5068C6`). **Small-id collision risk is
present-tense and proven in-image, not a future-plugin hypothetical.** The cure still works
today because only one direct view child carries `0x43` — but pairing it with a parent/size
check is **mandatory, not optional**.

**Cure shape (coupled pair — both halves or neither; do not apply from this document):**
(1) tier-generalise the code constant `0x1C` at `0x007EE15A` to `round(28·f)` in
`CodePatches.cpp`; **and** (2) add `0x00000043` to `kNeverScaleIds` (`UiSpike.cpp:3117`)
with a parent check, so the sweep cannot re-double it. Leaving the art at 1x is the wrong
trade — 46 shipped scripts use `image={46a006b0,53244588}` with explicit areas.

**Offline gate before build:** the `0x43` clip is fully predicted above; the gate is
`Test-DatIntegrity.ps1` unchanged (no dat change) + a `crosscheck.py` re-run after the
`CodePatches` edit (the constant must appear in the model, not as an EXTRA).

### 3.4 `0x42B7C351/53/54/55` Data Views scrollbar — **VERDICT: COVERED (mechanism present, pixel-unverified). It IS the solved family — and the ids are NOT Data-Views-specific.** (rank 2)

**Family match, proven.** These ids are stamped by **generic GZ-framework code**:

- `sub_99A96E` (`0x0099A96E..0x0099AC7E`) allocates a `0x11C`-byte object (ctor
  `sub_99A67E`, vt `0x00ADC398`) into `[owner+0xF0]` and calls `SetID(0x42B7C351)` at
  `0x0099A9F6`. Callers `sub_99AFA8` (8 sites: `0x47A809`, `0x489321`, `0x499D99`,
  `0x79E43F`, `0x8AEE92`, `0x8AF1D2`, `0x8AFB40`, `0x9946CA`) and `sub_99B5BF`.
- The three children are stamped **inside a helper, `sub_99A70F`**, from `sub_99AC7E` at
  `0x0099ADBD` / `0x0099AE3D` / `0x0099AEBA` — `push 0x42b7c353/55/54` as an **argument**,
  not as `call [reg+0x100]`. **That is exactly why the census's literal-SetID scan finds
  only the parent** (verified: `0x42B7C353/54/55` are in zero of the 73 `setIds` entries).

⇒ **Every scrollable GZWin control in the game — including the news/advice scrollbar of
#82/#88 — carries these same four ids.** That answers "does it match the family": it *is*
the family. It also means **any id-keyed rule on `0x42B7C35x` hits every scrollbar in the
game.**

**Structure, from the corpus (verified this session with a depth-tracked parse):**

```
I-2bc9060f   depth 0   0xaa32bce6  area=(460,253,1006,681)   546x428   <- Data Views panel
             depth 1   0x00004200  area=(246,-320,519,-143)  273x177   <- Map View page
                                    clsid=0x28c5a41f iid=IGZWinCustom
                                      \_ 0x42B7C351 (4,4) 265x27, children=3
                                           \_ 0x42B7C353/54/55  24x25
```

**Coverage proof.** `0xAA32BCE6` is in `kAlwaysScaleCityIds`, so `ScalePanelsUnder` scales
it even while hidden. `ScalePanelRoot` then recurses with `ScaleSubtree(child, f, 1, &count)`
— **default `centerLeaves = false`** — and `ScaleSubtree` has **no visibility gate**.
`0x00004200` is not in `kDataScaledSubtreeIds`; depth 3 vs `kMaxDepth 8`. So bar and buttons
are both reached: 265×27→530×54, 24×25→48×50.

**The one real hazard, and it explains the historical symptom.** `0xAA32BCE6` is *also*
`kGZWin_MenuContainer`, and `ScaleMenuFlyouts` walks its children with
`ScaleSubtree(child, f, 0, &n, /*centerLeaves=*/true)`. With `centerLeaves=true`, a 24×25
childless leaf trips `centerThisLeaf` (`≤ spikeCenterLeafMaxPx = 48`) and is **re-centred at
its 1x size and recorded `scaledW == origW`, permanently**. That is precisely "frame swept,
its 24×25 buttons stay 1x". Today the panel loop runs before `ScaleMenuFlyouts` in the same
tick, so `ScalePanelRoot` wins — but **two mechanisms are live on one subtree with an
order-dependent outcome**, the same shape as the `DockDialogs=1` region trap.

**Honesty note.** `codecreated-noncity.md`'s "frame swept to 1076x94" appears in **no
retained log** and is not reproducible from the code path (265×27 → 530×54). Independent
check: I grepped all five retained `.log` files for `42B7C35` — **zero hits**. The
adjudicating agent's quoted "live geometry" for this family therefore has no log behind it
either. **The structure above comes from the `.UI` corpus and the disassembly, which I did
reproduce; the "live" rects should be treated as UNSOURCED until the eyes-on session.**

---

## 4. THE CURE LIST

Build order. Every item states its offline gate. **Nothing here has been applied.**

### 4.0 Two prerequisites that gate everything below

**(a) The collision discriminator — the rule, and the one place the input brief broke it.**

> **Apply a cure to the pair *(builder, script-instance TGI)*. Never to
> *(any builder, window id)* — unless the list you are adding to is provably inert for
> every window that answers that id.**

This is not a convention; it is how the mechanism already works, and the precedent is in
`build_dialog_static.py` in the file's own words for `0x8A8DFCF5`: static doubling is
per-script TGI, the two scripts are doubled independently, and neither shadows the other.

**Collisions are the mode, not an accident** (new instrument `tools\uimap\idcollide.py`,
report `tools\uimap\_work\idcollide-report.txt`, 1048 lines, present in the repo):
**596 of 1409 distinct corpus ids (42%) are declared by ≥2 different script instances**,
and **64 of our own 174 id-keyed entries (37%) are multi-declared** —
`kDataScaledSubtreeIds` 9/10, `kAlwaysScaleCityIds` 16/33, `SCALED_WINDOW_IDS` 20/51.
Every id-keyed rule we ship is already a multi-window rule. **[not reproduced — I verified
the artifact exists and spot-checked the `0x27DF05BE` and `0xAA921F4F` rows; I did not
re-run the 1048-line audit.]**

Per-script-TGI static doubling of a colliding root is **already shipping four times with no
known breakage**: `0x8A8DFCF5` (2 scripts), `0xAA921F4F` (3), `0xCBF32603` (2),
`0x2A5CFB2C` (2). And the cross-builder audit came back **clean**: zero ids where one
declaring script is dialog-static-staged and another is not. The "forbidden move"
(`0x27DF05BE` into `SCALED_WINDOW_IDS`, which would drag `I-2a41436c` into set S and ship
2x imagerects with 1x `area=` from a dat that loads *after* DialogStatic) has genuinely
never been made. **Do not make it.**

> **🚫 THE INPUT BRIEF'S OWN PROPOSAL VIOLATES ITS OWN RULE. Do not add `0x27DF05BE` /
> `0x27DF05BF` to `kBmpxDialogRoots` (`UiSpike.cpp:12182`).**
>
> That list is id-keyed and resolved by a **single first-match walk** at
> `UiSpike.cpp:7015` — `pSearchRoot->GetChildWindowFromIDRecursive(ids[k])` returns **one**
> `cIGZWin*`, no enumeration, no visibility test. Three failures:
> 1. **Wrong window.** `I-2a41436c` contains 2 `GZWinBMP` nodes, so the Obliterate confirm
>    is a *valid* hook target. Which of the two `0x27DF05BE` windows is returned is
>    enumeration order — undecidable from our side.
> 2. **The codebase already learned this and only fixed it elsewhere.**
>    `UiSpike.cpp:11816` onward replaced exactly this single-find with `IdCollectCtx`
>    because "the single-find returned the hidden TEMPLATE for the budget masters." The
>    BMPX path never got that fix.
> 3. **The instrument self-poisons.** `gBmpxRootTrack` slots are keyed by id. One slot, two
>    windows: any flip satisfies `slot->ptr != root`, logging a phantom OPEN, bumping
>    `gBmpOpenSeq` and resetting the draw-log budget. The brief then elevates
>    `BMPX draw-skip … win WxH` to "adjudicates Mode A vs Mode C without a single pixel of
>    guesswork" — on a colliding id it prints the wrong window's frame. **One blind
>    instrument as arbiter.**
>
> **The `kNeverScaleIds` half survives and is fine.** `IsNeverScaleId` is consulted at
> exactly two sites — `ScaleOnShow` (dormant at the shipped `ShowHook=1` log-only default)
> and the direct-view-children loop. Both windows are main-window children, so the entry is
> **inert insurance for both**. Take it.

**(b) The tutorial-page discrepancy — RESOLVED, with one important correction to the rule
it exported.**

`0x0a2dd355` and `0x4A35B0F2` are the same object at two layers, both in one instruction
window:

```
0x00443E70  mov dword ptr [esp+0x14], 0x96a006b0   ; TGI group
0x00443E78  mov dword ptr [esp+0x18], 0x0a2dd355   ; TGI instance  <- the SCRIPT RESOURCE
0x00443EA0  iid 0x5386d516
0x00443EA5  push 0x4a35b0f2                        ; <- the WINDOW ID looked up inside it
0x00443EB5  call 0x5f9480                          ; loader(TGI*, parent, winId, iid, out)
```

`sub_5F9480` is a 5-arg thunk forwarding to service `{0x5a356e15, 0xfa3562fa}` vt+0x0C.
`T-00000000_G-96a006b0_I-0a2dd355.ui` has exactly one depth-0 root, `id=0x4a35b0f2`
`area=(334,6,807,314)` = 473×308. So `UiSpike.cpp:3186` — `0x4A35B0F2, // tutorial page
(I-0a2dd355)` — is exactly right and the census phrasing "loads tutorial page 0x0a2dd355"
was naming the resource. Nothing to reconcile.

**But the general rule the report exported — "window id selects the ROOT inside it" — is
FALSE, and I reproduced the counterexample.** Depth-tracked corpus parse, this session:

```
I-2bc9060f :  depth 0  0xaa32bce6
              depth 1  0x00004200  area=(246,-320,519,-143)   <- and the code asks for THIS
```
Call site `0x007EEB05` inside `sub_7EDEB0`: script instance `0x2bc9060f` (stored
`0x007EEAFD`), iid `0x22ba0121` (`0x007EEAE1`), **winId `0x00004200` (`0x007EEAE6`)**.
`0x00004200` is a **depth-1 child**. Positive control: the same scan returns depth 0 for
`0a2dd355→4a35b0f2`, `0a41be3e→0a41c7b2`, `0a41be3f→0a41c7b3`, `4bc906b5→6a64e3c0`,
`6a9455c9→27df05be`, `6bc9065a→0a4a8176` — it can and does report ROOT, so the single
depth-1 hit is a measured result.

**Corrected rule:** *the script instance selects the resource; the window id selects **any
node** in the deserialized tree, and the loader instantiates and parents **every** depth-0
root of the script regardless of which pointer it returns.*

Two consequences that matter here:
- `I-6a9455c9` has **TWO depth-0 roots** — `0x27df05bf` and `0x27df05be`, both
  `area=(109,151,155,248)` = 46×97 (verified). "The root" is undefined for that script. All
  three creation sites (`0x00438465`, `0x00438935`, `0x0043A812`) request `0x27df05be`;
  `0x27df05bf` is only ever a `GetChildWindowFromID` lookup on the parent afterwards
  (`0x004384CB`, `0x0043899B`, `0x0043A878`). Same pattern in `I-6bc9065a` (3 depth-0 roots;
  code takes the third).
- **A denominator gap independent of the code-created one:** the ladder counts depth-0
  roots, so `0x00004200`-class nodes — which the code addresses directly as top-level
  handles — are structurally excluded. At least one such node exists; the count is
  unmeasured. `0x00004200` is declared in **three** scripts (`I-0b72f276`, `I-2bc9060f`,
  `I-ea287193`) — the same low-integer collision class as `0x43`, now proven to be a live
  loader argument.

---

### R1 (build first) — `0x0A41C7B2` / `0x0A41C7B3` tutorial pointer overlays, 62×49

**Identity settled and final.** `sub_443E60` is ONE function (`0x443E60..0x444160`, single
`ret` at `0x444152` — reproduced with `fn.py`) that loads the tutorial page **and** both
overlays (`0x444057` `push 0xa41c7b2` / `0x44405c` `push 0xa41be3e`; `0x44407e` /
`0x444083`). The overlay's only child is a `GZWinBtn` carrying `tiptext="Disaster Tools"`.
**They are tutorial pointers highlighting that button, inheriting its tooltip.** The old
`coverage-matrix.md` entry ("Establish/Obliterate neighborhood") is dead.

**Mechanism: dialog-static, beside their own page.** Add to `build_dialog_static.py`,
next to `("0a2dd355", "Tutorial page …")`:
```
("0a41be3e", "Tutorial pointer overlay A (Disaster Tools highlight)"),
("0a41be3f", "Tutorial pointer overlay B"),
```
Their art `{46a006b0,14416230}` / `14416232` is single-referenced with `twox_available=yes`
→ EXCLUSIVE 2x-in-place, no clones, zero collateral.

**Plus free insurance:** one `kNeverScaleIds` line each. `kNeverScaleIds` never *enlarges*
anything — it is consulted only at `ScaleOnShow` (dormant) and the direct-view-children
loop — so for a main-window child it changes nothing on screen and costs nothing. It cannot
disable BMPX, dialog-static, `kDataScaledSubtreeIds` or `ScaleSubtree`.

**Open question, stated not papered over:** these two are created through helper
`sub_441B50` which passes **parent = 0** (`push 0` at `0x441B6B`), unlike the page's
explicit `GetMainWindow()`. The loader's NULL-parent default is unmeasured. If it defaults
to the main window, static doubling is exactly right. If it means "unparented, positioned by
the caller", the doubled **size** is still right and only the doubled **origin** is
meaningless. Either way the size is the load-bearing half.

**Offline gate:** builder VERIFY pass (areas exactly 2x node-for-node); refmap re-run must
keep `14416230`/`14416232` EXCLUSIVE with no clone rows; `Test-DatIntegrity.ps1` EXPECTED
count bumped in the same commit. **Eyes-on required for placement** — batch with R4.
**Risk: LOW.** Worst case is a 2x highlight box at a 1x-derived position: visible and
revertible. There is no double-scale path (the sweep cannot reach a main-window child) and
the `kNeverScaleIds` line covers the case where that assumption is wrong.

### R2 — `0x00000043` Restore-Toolbars button

Full brief in **§3.3**. Coupled pair: `CodePatches` tier-generalisation of `0x1C` at
`0x007EE15A` **plus** `kNeverScaleIds` + parent check. **Both halves or neither.**
Offline gate: `crosscheck.py` must show the new constant in the model (not as an EXTRA),
exit 0; no dat change so `Test-DatIntegrity.ps1` is unchanged. **Risk: MEDIUM** — it is a
byte patch in a HUD builder shared with `cSC4WinAlertBorder`. Eyes-on confirms the button
sits clear of the bottom edge and still hit-tests.

### R3 — `0x27DF05BE` + `0x27DF05BF` Sim occupant chip (`I-6a9455c9`, 46×97)

**The premise correction that reshapes this cure: the chip is Mode A, not Mode C.**
`sub_438390` @ `0x43844C`: `mov ecx,[edi+0x1c]` → `call [eax+0x0c]`, and the result is the
**parent** argument to the script loader `sub_5F9480`. `[edi+0x1c]` is
`cSC4BaseViewInputControl::windowManager` (field order from
`vendor\gzcom-dll\...\cSC4BaseViewInputControl.h:243-249`), and `cIGZWinMgr` vt+0x0C is
`GetMainWindow` (`cIGZWinMgr.h:39`). Service identity nailed independently: `sub_4177C0`
does `GetClass(0xA417445E, iid 0x5A4)` = `cIGZWinMgrPtr` in `GZServPtrs.h:50`. Positive
control: the same expression builds the tutorial page, which is already known
main-window-parented.

⇒ **parent = main window ⇒ the frame is never doubled ⇒ shipping selective-safe 2x art for
it would manufacture exactly defect #98 (2x art in a 1x box).**

**Mechanism: dialog-static static-double, the query/confirm family cure.** Add to
`build_dialog_static.py` `TARGETS`, next to the Obliterate entry:
```
("6a9455c9", "Sim occupant chip (SAME root id 0x27df05be as 2a41436c above)"),
```

**The one genuinely new builder feature, justified.** The chip's 36×41 portrait is
**runtime-supplied**, exactly like #47: `0x4385F4-0x43861C`
`GetChildWindowFromIDAs(0xEA9457BA, iid 0xC12CEA13 = GZWinBMP, &out)` then
`out->vt[0x10](image)` — a SetImage (three sites each for `0xEA9457BA`/`0xEA9457BB`).
The builder doubles `imagerect` on any control whose art went 2x, and
`{1abe787d, ea32f100}` has `twox_available=yes` — so it *would* double the rect to
`(0,0,72,82)` over a **36×41 runtime bitmap**. GZWinBMP's plain path is dst-follows-src, so
that is an over-read: the imagerect-invariant violation of task #95.

`RUNTIME_BOUND_2X` expresses "*placeholder whose runtime pixels ARE 2x*". There is no way
to express "*placeholder whose runtime pixels STAY 1x*", because until now every such case
had a **DANGLING** TGI that fell out of the plan automatically. The chip is the first case
where the placeholder TGI is real, in the PNG store, and 2x-generated, yet the pixels that
arrive are 1x. Add the third class — **REAL-BUT-OVERWRITTEN** — as
`RUNTIME_BOUND_1X = {"6a9455c9": {(0x1ABE787D, 0xEA32F100)}}`, ~4 lines mirroring the
existing `RUNTIME_BOUND_2X` handling: force `action=left1x` and do **not** set
`control_art_doubled`.

**Also add:** `kNeverScaleIds += 0x27DF05BE, 0x27DF05BF` (inert insurance covering both
colliding scripts, per §4.0a). **Do NOT add them to `kBmpxDialogRoots`.** **Do NOT add
`0x27DF05BE` to `SCALED_WINDOW_IDS`.**

**Offline gate — one assertion adjudicates the whole design:** the builder's node-for-node
VERIFY must report portrait `imagerect == (0,0,36,41)` and every other rect and every
`area=` exactly 2x. Console SUMMARY must show `left1x=1` and the classifier must print the
portrait ref as REAL-BUT-OVERWRITTEN, **not** MISSING-2X. `Test-DatIntegrity.ps1` EXPECTED
bumped. `Test-BornCorrectCoverage.ps1` unchanged (we deliberately do not touch
`SCALED_WINDOW_IDS`).

**Risk: LOW-MEDIUM.** (a) Font GUID conversion enlarges text — the chip has none. (b) The
chip's code reads `GetW/GetH` and computes `(w-x)>>1` at `0x438494-0x4384A1` for centring;
doubling the frame changes that half-width, correct only if the anchor it centres against is
also 2x. **Unmeasurable offline → eyes-on.** (c) `{46a006b0,13f15214}` becomes SHARED once
only this script is doubled → clone+retarget, standard and safe.

### R4 — `0x6BFAC122` / `0x8BFAC13E` (`I-0bfac164`) and `0xCBFACAE1` / `0x8BFAC13E` (`I-abfac197`), 46×108

**Do not build a cure. Build a sighting.** Whole-image 4-byte immediate scan:

| root | root id in exe | its script TGI in exe |
|---|---|---|
| `0x6BFAC122`, `0x8BFAC13E` (`I-0bfac164`) | **0** | **0** |
| `0xCBFACAE1` (`I-abfac197`) | **0** | **0** |
| `0x27DF05BF` / `0x27DF05BE` (`I-6a9455c9`) | 3 / 5 | 3 |
| `0x0A41C7B2` / `B3` | 1 / 1 | 1 / 1 |
| `0xEACA96DD` (`I-6aca9687`) | **0** | **0** |

Positive control passing (the same scan finds `0x4A35B0F2`, `0x0a2dd355`, `2a41436c`,
`0a41be3e/3f`). **MEASURED null, not structural**, and the corroboration is between two
independent failure modes (static reference vs live tree) because the third member of the
identical family is named at three sites. Escape hatches I cannot close offline: a plugin
creating them, or an id arriving from a *compressed* `.dat` resource (a raw
`SimCity_1.dat` byte scan is a weak instrument — its null is not evidence).

**Burden shifts: the first work on these is a SIGHTING, not a cure.** The instrument is the
`MWKID` change-only dump plus a full `DumpTree`, **not** `kBmpxDialogRoots` (§4.0a).
**Offline gate: none possible — this is the instrument.** Flag: **eyes-on, batched.**

### R5 (do last, and only if sighted) — `0xEACA96DD` grid popup, 94×185 — **RECLASSIFY, DO NOT SHIP**

**It is a code-created window, not a scriptable root.** `sub_79C800` @ `0x79C822` pushes
`{0x856DDBAC, 0x46A006B0, 0x144161C0}` into image loader `0x602B70` and stores into the
image holder at `[esi+0xDC]` (the same holder layout the BMPX hook documents), then
configures a grid object at `[esi+0x14C]`. Zero direct callers ⇒ virtual ⇒ a class Init.
**The `.UI` script `I-6aca9687` is a design-time template the shipping code never loads.
Editing the script changes nothing.**

- The only reachable lever is the art `{46a006b0,144161c0}`, and it is **code-bound**, so it
  could only ship as 2x-in-place via `build_selective_safe.py` `CODE_BOUND_FORCE`.
- **Blast radius is the reason to stop:** the draw follows the source, so doubling
  `144161c0` enlarges it in *whatever window `sub_79C800` builds*, whose geometry constants
  have not been read. Doubling art without the matching geometry patch is the upside-down
  trade. Additionally the `.UI` declares it `blttype=edge`, and the BMPX hook deliberately
  skips 9-slice — so there is no runtime fallback either.
- Cosmetic in any case: `144161c0` is a 120×120 `blttype=edge` rounded frame; it degrades to
  thin borders, not a break.

**Offline gate before any code:** run the `tools\uimap` builder census on
`sub_79C7E0`/`sub_79C800` to recover the window's `SetArea`/`SetID` constants, exactly as
the Graphs legend was pinned to `sub_76D3D0`. **Until then: no code, no art.**

### R6 — `0x6BB92BCB` Trip Types legend (#98), 181×296 — the one genuine live defect, and ours

Not in the "Mode C family" but it outranks everything above on reach × severity, so it is
listed here for ordering. All 12 art refs are EXCLUSIVE 2x-in-place in `refmap.csv` so 2x
art **ships**, while `selective-safe\stage` (and `-15x`, `-3x`) still carry the 1x root
`area=(139,81,320,377)`, and the id is in **no** runtime list (positive control printed for
each — MEASURED null). **2x art in a 1x box.** Reached by Route Query on any road or rail in
a founded city.

**One observation flips the fix entirely** and it is the first item of the eyes-on session:
if the city sweep doubles the window, the 2x art we already ship becomes correct and nothing
else is needed; if it does not, the panel is quarter-art today and needs its root staged 2x.
**Do not build until that rect is read.**

> ### ⛔ CORRECTED 2026-08-03 — R6 ABOVE IS SUPERSEDED IN THREE PLACES. IT IS A BUILD.
>
> The paragraph above is left standing as the record of what the census
> supported. **Three of its statements are now known wrong, and the question it
> calls decisive was settled from the exe, not from a live rect.**
>
> | R6 says | measured / disassembled | how |
> |---|---|---|
> | "All **12** art refs" | **14** distinct art refs — 13 EXCLUSIVE/2x-in-place + one SHARED (`0x14416245` → clone `0x47026244`, used 9×) | `grep -oE 'image=\{46a006b0,[0-9a-f]+\}' <the staged .ui> \| sort -u \| wc -l` → 14 |
> | the 1x root `area=(139,81,320,377)` is the box the art draws into | **that root is a PHANTOM.** `0x6BB92BCB` is a **construction-only container**: its id occurs once image-wide (`0x004C594F`, created `0x004C595C` from `{0,0x96a006b0,0xabb0120f}`) and 0x218 bytes later the same function calls `mainWindow->ChildDelete(container)` at `0x004C5B64` (`cIGZWin` vt+0x40). It never lives in the window tree, so its `area=` is **dead data** | read forward from the creation site |
> | "if the city sweep doubles the window…" — treated as an open coin-flip | **no sweep root can ever reach it.** The two REAL windows are its children, PROMOTED to direct children of the MAIN WINDOW (`GetChildAs(0x0BB0F5E7)`→`ChildRemove`→`ChildAdd`, `0x004C5A04..16`; same for `0x6BB92BCA`, `0x004C5AB5..C8`). City sweep root = `SC4View3DWin`, region = `0xEA659793`, and neither id is in `kCityDialogIds` | ditto |
>
> **So R6 is a BUILD, and it always was.** The decisive fact was reachable
> offline in the disassembler the whole time; waiting on a live rect would have
> answered a question whose premise (that the root is a live window) was false.
> ⚠ **This is law 51:** *a root id in a census is a CLAIM about where a window
> lives, and a construction-only container looks exactly like a live root in
> static data.*
>
> **STATUS: the cure was built and deployed 12:39:39, then MEASURED ABSENT from
> the generator and all three staged tiers at 12:44–13:00.** Nothing on disk
> carries it. See `_tests\REGRESSION.md` → *IN-GENERATOR ADJUDICATOR (#98)* and
> `tools\uimap\coverage-matrix.md` §0.10b. **Re-establish it before quoting any
> of it as shipped.**
>
> ⛔ **DO NOT** add `0x0BB0F5E7` or `0x6BB92BCA` to any CITY runtime list. Both
> are already in `kRegionPanelIds` (`src\UiSpike.cpp:3084-3085`) and the REGION
> legend is a **different** script (`I-abc0ed33`). A city-side entry on top
> would be **4x**.

### R7 — the two data gaps found in passing (cheap, do with whichever batch ships first)

**(a) `kCityDialogIds` `0xAA921F4F` is missing a fourth measured base — CONFIRMED this
session.** `UiSpike.cpp:11172` holds `{ 0xAA921F4F, 330, { 330, 270, 270 }, { 157, 161, 162 } }`,
and the struct at `:11165` has only `bw[3] / bh[3]`. **Three** stock scripts declare that id,
not two — I read all three:

```
I-0a55161d  area=(332,232,662,389) = 330x157   in the table
I-6a553aa4  area=(332,232,602,393) = 270x161   in the table
I-4a551b4c  area=(332,170,662,279) = 330x109   *** NOT IN THE TABLE ***
```
`I-4a551b4c` is the region-screen Quit confirm, named as a collision in
`build_dialog_static.py` and **staged at all three tiers** — verified:
`stage (664,340,1324,558) = 660x218`, `stage-15x = 495x164`, `stage-3x = 990x327`. None
matches any product of the three listed bases (2x products: 660×314, 540×322, 540×324). So
the exact-product guard would set `dataBorn=false`, fall through to `SetW/SetH` and
re-scale 660×218 → **1320×436** — the identical shape of the v2.39.14 failure quoted in
that very code block.
**Reachability, stated honestly: LATENT, not live.** `Disarm()` on
`kSC4MessagePreCityShutdown` clears `continuous`, and `IncrementalPass` only runs while
continuous, so the region-screen variant is not reached with no city loaded. **It is a
one-line data gap in a guard whose own comment says "the data must be complete".** Widen
the struct to `bw[4]/bh[4]` and add `330x109`.

**(b) `0x4C30E4FA`'s label.** Re-derive from `sub_42C0E0`/`sub_430680`/`sub_430F70` before
anything keys off "Business Deals empty-state box" / `designW 272` (§3.2).

---

## 5. WHAT SURVIVED REFUTATION AND WHAT DID NOT

### 5.1 ✗ BROKEN — "`0x2BA6BB97` is structurally unreachable, content code-painted"

**This was the batch's most load-bearing claim and it is refuted by measurement, inside a
single retained log, with the positive control the reports never stated.**

`tools\research\_checkpoints\pds-cache\SC4UIScale-snapshot.log` — I read the lines myself:

```
:52   [17:39:47.281] RGKID 11 id=0x2BA6BB97 vt=00AB9658 (0,0 2400x1600)   <- 0 child lines
:78   [17:39:47.309] identical                                            <- 0 child lines
:124  [17:39:47.339] identical                                            <- 0 child lines
:151  [17:40:02.909] identical, THEN 13 descendants:
:152    11.0     0x0A551C50 (1049,456 516x500) vis=1     <- the city-select bubble
:153-5  11.0.0/1/2   0xCC06F4CF / 0xAC06F4C4 / 0x6C06F4A0   80x40
:156-9  11.0.3-6     0x4A560003 72x58, 0x4A560002 44x64, 0x4A560001 26x26, 0x4A560000 110x92
:160-2  11.0.7-9     anonymous stat rows 184x32 / 186x32 / 188x32
:163-4  11.0.10/11   backdrops (0,392 516x86) and (0,0 516x392)
:165    11.0.11.0    inner (24,20 470x284)
```

**Twelve direct children the moment a city tile is clicked.** `children=0` is a
**state-dependent measured null** meaning "no bubble open" — precisely the standing order's
PRE-FOUNDING failure mode.

The cited evidence is disqualified twice: `crossfire-04.md:56` identifies the 800×600 source
as a one-shot BOOT dump with no city hovered, taken with the DLL inert at tier 1; and the
2400×1600 `children=0` lines are from the same no-bubble state.

**And the killer: we already shipped a user-confirmed fix into this "unreachable" subtree.**
`_tests\REGRESSION.md:3531` — REGION BUBBLE MAYOR RATING BAR, v2.37.1, **task #72,
user-confirmed**. Both bubble scripts are dialog-static targets (`0a8cd184`, `ca539340`).
Every live rect under `0x2BA6BB97` is exactly 2x its staged script: 516×500=2×258×250,
516×392=2×258×196, 470×284=2×235×142, 110×92=2×55×46, 72×58=2×36×29, 44×64=2×22×32,
26×26=2×13×13, 80×40=2×40×20. **The subtree is not merely reachable — it is already fully
scaled by a shipped data mechanism.**

**And our own docs already recorded this refutation and it was not read**
(`sdkgaps-02.md:13`; `REGRESSION.md:3568-3577` "two blind instruments agreeing is worth
exactly as much as one").

**Corrections applied:** the code-created report's "UNREACHABLE CONTENT (1)" bucket is
**empty**; `0x2BA6BB97` is **COVERED**; `coverage-matrix.md §5`'s PROVEN row for it is
struck (§ below). The unknown-child report used it as its load-bearing contrast case — that
support collapses, though its independent vtable evidence for `0x6A5E44B6` stands alone.

**What honestly survives, narrowed:** nobody has proven that the region **map tile
labels/icons drawn on the map itself** (as distinct from the bubble) are windows. That
narrower sub-claim is **untested either way**. The reports did not make the narrow claim;
they filed the window categorically under "content code-painted / structurally unreachable",
and 13 enumerated descendants refute that categorically.

**Also refuted by the same instrument analysis:** `RGKID`'s print depth is hard-capped at
4 levels and it skips invisible children. `crossfire-04.md:11` gives the control — across
4721 log lines the label-depth histogram is {0 dots:53, 1:91, 2:30, 3:1} with **zero 4-dot
labels**, so the printer works at depth 4 and simply has no depth-5 branch. Consequence:
`cSC4WinAuraBar 0x4A553000` — a plain **visible** window at level 5, declared 102×11 in
`I-ca539340` — was ruled "NOT A WINDOW / code-painted" by `task55-47-runtimeimg.md:1455`.
**A saturated enumerator manufactured an unreachability verdict.** Any future
"code-painted" verdict must state the enumerator's depth cap and visibility gate.

### 5.2 ✗ BROKEN — "194 sites and 64 ids bound the code-created set; 93.9% is a FLOOR"

The routes are tight *inside their stated encodings* — five attacks on them failed and are
worth recording so the survivor is credible: the vtable detector has no fragile threshold
(vote histogram {8 marks: 91, 7 marks: 20}, zero at 2); the alternate call encoding
`mov reg,[x+0xc]; call reg` has 0 sites; of 2104 `call 0x5E55E0` sites the 1922 rejected
store no window vtable within 40 instructions; window-vtable stores in `.text` are 211 at
`[reg+0]` and only 9 at nonzero offsets; the `0x8000` per-function scan cap truncates
exactly one non-UI function. **[not reproduced — quoted from the refutation pass.]**

**What breaks it is a third route the census never models**, and I reproduced its size:
**220 `call` edges to the `0xC2C2EB0F` singleton getter `0x00913C72`, in 129 functions, 106
of which the census sees as no kind of creator, 27 of those in the live-UI band.**
`sub_779660` is the concrete generic factory: 86 call sites in 6 functions, `SetID` with the
id **in a register**, and I recovered ≥5 confirmed window ids from those sites
(`0x0ABCE000/1`, `0x0ABCDE00/01/02`) of which **none is in the 64-id table** — while our own
`CodePatches.cpp:246` names `sub_779660` as their creator and the retained log shows
`POPKID 2.0 id=0x0ABCE001 (30,50 750x25) vis=1`. **On screen, actively patched by us, in
neither denominator.**

Second break, in the census's own §5: `0x42B7C353/54/55` are stamped inside `sub_99A70F`
from literal pushes at `0x99ADBD/0x99AE3D/0x99AEBA` passed as an **argument**, and appear in
**zero** of the 73 `setIds` entries. Same widget, same function, 3 of 4 ids invisible.

Third: **the denominator is a band filter, not a shipping test.** `0x42B7C351` was binned
"GZ framework internals" purely because its stamping address is ≥ `0x940000` — while that
exact widget is on screen in Data Views and in every scrollable control in the game.
**Windows were excluded by ADDRESS, not by visibility.**

**Verdict: "floor, not a correction" is the specific sentence that is false.** A floor
requires that everything unmeasured can only add to the denominator in a *bounded* way, and
nothing in this repo bounds those three channels. **93.9% was an inference dressed as a
measurement.** Replaced by §1: 94.9% over 315 named windows, with the bound stated as a
bound.

### 5.3 ✗ BROKEN (as justification) — "the census's biggest new causal finding: Ordinances has no mechanism"

The *causal* half is right and valuable: `0x0423278D/E/F` are code-created `cGZWinGen`s
built through `sub_779660`, they appear in **zero** `.UI` scripts, and there is no
static-dat lever. That explains three historical facts recorded in `UiSpike.cpp` as
unexplained.

The *coverage* half is wrong. We ship a mechanism, and it is extensive:
`CodePatches.cpp:201/246/256/464` (byte patches on the popup's own constants) plus
`UiSpike.cpp:11769` (`0x0423278D`), `:11816-11945` (per-instance `0x0423278F`), `:11900`
(`0x0423278E`), `:12008-12060` (the height/clamp pin, idempotent, size+position only). All
three move from UNCOVERED to COVERED in §1.1.

### 5.4 ✗ BROKEN — "script instance selects the resource, window id selects the ROOT inside it"

Refuted with a reproduced counterexample (`0x00004200` is a depth-1 node passed as the
loader's winId at `0x007EEAE6`). Corrected rule and its two consequences are in §4.0b. The
narrow tutorial-page resolution survives intact.

### 5.5 ✗ BROKEN (as arithmetic) — "36 unexplained live ids ⇒ denominator ≥350, coverage ≤85%"

The **measurement** survives and I reproduced it exactly (36). The **arithmetic** does not:
it adds child windows to a root denominator. And the follow-through nobody did shows all 36
are descendants of one already-known, already-covered family. See §1.3. **This is the single
biggest de-escalation in the batch: a 21%-of-live "hole" collapses to one item.**

### 5.6 ✗ BROKEN — "the `0x27DF05BE` collision is a rare accidental find" and "an id-keyed rule on `0x43` is safe"

Collisions are the **mode**: 42% of corpus ids are multi-declared, and 37% of our own
id-keyed entries already are. `0x43` sits in a dense semantically-allocated command-id run
whose sibling `0x44` is the other half of the same feature, and SC4 already reuses
`0x000000FF` at three unrelated sites. See §3.3 and §4.0a. **The `0x43` cure still works
today; its justification does not, and the parent/size check becomes mandatory.**

### 5.7 ✓ SURVIVED — the load-bearing positives

- **`0x6A5E44B6` = `cSC4WinAlertBorder`**, every address in §2. Independent of the refuted
  `0x2BA6BB97` contrast case.
- **`0x00000043`'s 10 px / 20 px clip**, three instruments agreeing (live log, shipped art
  dimensions, arithmetic self-consistency).
- **`0x42B7C35x` is the generic scrollbar family**, with the `centerLeaves` order hazard
  named. Its "live geometry" citation is **unsourced** (zero hits in all five logs) — flagged.
- **`0x4C30E4FA` is world-anchored and does get shown** — `ShowWindow` at `0x00431130`.
- **`0x6A0AF41D` is a 128 px sprite emitter**; two levers named; leave alone.
- **The chip is parented to the main window** (`GetMainWindow` chain, positive control =
  the tutorial page). This is what saves us from manufacturing a second #98.
- **The per-script-TGI discriminator**, with four shipping precedents and a clean
  cross-builder audit.
- **The Ordinances causal finding** (code-created, no `.UI`) — right, and it is why the
  cure is a builder patch and not a script edit.
- **Route A and Route B are tight inside their encodings** (five failed attacks, §5.2).

### 5.8 ⚠ DOWNGRADED to hypothesis, with its open measurement

| claim | now | the one measurement that settles it |
|---|---|---|
| Region map **tile labels/icons** are code-painted and unreachable | **HYPOTHESIS** (the *container* claim is refuted; the *label* claim was never tested) | `DumpTree=1` on the region screen with **no** bubble open, full depth: do label-shaped rects appear as windows? |
| `0x6BFAC122` / `0x8BFAC13E` / `0xCBFACAE1` exist in the shipping game at all | **HYPOTHESIS** (measured null on two independent instruments; compressed-dat escape hatch open) | one `MWKID`/`DumpTree` sighting run (§6 step 6) |
| `0x42B7C351` live geometry `265x27` / `24x25` | **UNSOURCED** — zero hits in all five retained logs | §6 step 4 |
| Ordinance rows measured `2640x36` inside a `900x754` dialog (v2.27.3 log, `MWKID 0.6`) | **STALE OBSERVATION**, 28 versions old, predates the reverts and the pin | §6 step 5 |
| `0x4C30E4FA` = "Business Deals empty-state box", `designW 272` | **UNSUPPORTED LABEL** | §6 step 10 |
| `sub_441B50`'s NULL-parent default | **UNMEASURED** | §6 step 7 |
| The 21 literals at `sub_779660` sites are all window ids | **UPPER BOUND** — 5 confirmed, rest probably LTEXT keys | separate the two by checking each against the LTEXT store |

---

## 6. THE BATCHED EYES-ON SESSION

The user's game time is the bottleneck. **ONE session.** Everything settleable offline has
been settled above; nothing below is a question the disassembler could have answered.

### Arm the instruments first (offline, no game time)

1. `DumpTree=1` — `UI id=` lines are **0 in all five modern logs** because `spikeDumpTree`
   ships `0`. Without this the session yields a fraction of its value.
2. **Un-gate the `[Probe]` ini read.** It sits behind `static int s_poll … >= 20`, so the
   ini band never takes effect and DPROBE runs at compiled defaults: ~14.7% of the screen,
   silently capped at 30 lines. Widen the band to the full frame, `Max=2000`.
3. **Do NOT** add `0x27DF05BE/BF` to `kBmpxDialogRoots` (§4.0a) — it would poison the very
   line the session relies on.
4. **ARCHIVE THE LOG.** `Logger` recreates the `.log` each launch and
   `Deploy-OnGameClose.ps1` archives none. Fourteen logs survive; the busiest versions left
   nothing. `0x4BCB938A` — the U-Drive-It console, *known live*, closed task #93 — has never
   appeared in a retained log. **That is the positive control that fails, and it is why 28
   "never observed" ids mean nothing about the game and everything about our retention.**

### The click path, in order

| # | do this | grep the log for | what it DECIDES |
|---|---|---|---|
| 1 | Load a founded city with roads. Let the HUD settle. | `VWKID`, `MWKID` baseline | baseline; confirms `DumpTree` armed |
| 2 | **Route Query → click any road or rail.** | `0BB0F5E7`, `6BB92BCA` (⚠ **not** `6BB92BCB`) | **#98.** ⚠ **REWRITTEN 2026-08-03 — the old cell said "this single rect decides whether R6 is a build or a close" and grepped for `6BB92BCB`. Both are wrong.** `6BB92BCB` is a construction-only container that is `ChildDelete`d at `0x004C5B64` and will never appear in a tree dump — grepping it is a **structural null**, not evidence. The live windows are `0x0BB0F5E7` and `0x6BB92BCA`, promoted to MAIN-WINDOW children. It is a **build**, settled in the disassembler (see the correction box under R6). What this click now decides is only **eyes-on**: are the 9 icon rows correct after the cure is re-established? |
| 3 | **Click the Hide-Toolbars button, then the Restore-Toolbars button.** | `0x00000043` | **R2.** Confirms 42×38 at (12,1572) → 10 px clip at birth, and whether the next sweep tick re-doubles it to 84×76 at (24,1544) → 20 px. Also confirms the button still hit-tests. |
| 4 | **Open Data Views. Switch to the Map View page. Scroll it.** | `00004200`, `42B7C35` | **§3.4 + §5.7.** Supplies the *first real* live geometry for the scrollbar family and shows whether `centerLeaves` ever wins the order race (buttons stuck at 24×25 = it did). |
| 5 | **Budget → Ordinances. Click an ordinance NAME to open its description popup.** | `0423278`, `ABCE00`, `MWKID  0\.` | **§5.3 + §5.8.** Re-measures the 32 child rects at v2.55.0 and settles whether the `2640x36` rows from the v2.27.3 log still exist. Also confirms the popup pin holds at `round(125·f)`. |
| 6 | **Query a residential building that has occupants; open the occupant chip. Then repeat on a commercial and an industrial building.** | `27DF05B`, `6BFAC122`, `8BFAC13E`, `CBFACAE1`, `EA9457B` | **R3 + R4.** The chip's live rect settles Mode A vs Mode C on the spot (46×97 = Mode A as predicted; 92×194 = the premise is wrong and R3 must not ship). The three building types are the only way `0x6BFAC122`/`0xCBFACAE1` can be sighted; **if they never appear across all three, they stay uncured with a measured null on two independent instruments.** |
| 7 | **Start a tutorial and advance until a pointer overlay appears.** | `0A41C7B2`, `0A41C7B3`, `4A35B0F2` | **R1.** Live rect + whether the overlay is parented to the main window (settles `sub_441B50`'s NULL-parent default) + whether the tutorial re-positions it against the 2x toolbar. |
| 8 | **Trigger the advisor grid popup.** | `EACA96DD`, `144161C0` | **R5.** First sighting of whatever `sub_79C800` builds. If it never appears, R5 stays blocked — which is the correct outcome. |
| 9 | **Exit to the region screen. Click a city tile so the bubble opens. Then move the mouse off it.** | `RGKID 11`, `0A551C50`, `4A553000` | **§5.1 regression guard.** Confirms the 12 children are still there and still 2x at v2.55.0, and — with `DumpTree` at full depth — answers the one narrow question §5.8 leaves open: **are the map tile labels windows?** |
| 10 | **Open Budget → Business Deals with no deals; separately, follow a My Sim until a callout pops.** | `4C30E4FA` | **§3.2 + R7b.** Which of the two it actually is, whether six instances are alive at once, and whether our resize fights the game's per-message reposition. |

### Ordering rationale

Steps 2–3 first because they are the two quantified defects and the two cheapest to read.
Steps 4–5 next because they are already-covered mechanisms whose *pixel* verification has
never happened (Q1). Steps 6–8 are sightings, which are worth nothing if the log is
truncated, so they sit after the instrument has proven itself on known-good targets.
Steps 9–10 close two refutations.

**One grep line covers the whole session:**
```
6BB92BCB|00000043|00004200|42B7C35|0423278|ABCE00|27DF05B|6BFAC122|8BFAC13E|CBFACAE1|
0A41C7B[23]|EACA96DD|RGKID 11|4A553000|4C30E4FA
```

---

## 7. WHAT REMAINS STRUCTURALLY UNKNOWABLE — named, with the limit that makes it so

Each entry names the *limit*, not just the gap. If the limit can be lifted, the entry moves.

| # | what | the limit that makes it unknowable offline |
|---|---|---|
| 1 | **The `0xC2C2EB0F` singleton factory's output.** 220 call sites, 129 functions, 106 of them invisible to the census, 27 of those in the live-UI band. | The class is chosen from a **runtime-registered dispatch table**, not from a literal clsid in the instruction stream. Static analysis has nothing to read. The project already recorded this as unresolvable (`uimap-stage3-emu.md:317`). **Lift only by emulation or a live hook.** |
| 2 | **Computed window ids.** 162 `call [reg+0x100]` sites exist; the literal scan matches 73. **89 (55%) pass a non-literal argument.** The consecutive runs seen live (12 ids at `0x12C`, 12 at `0x2F4`, 4 at `0x551`) are the signature of `SetID(base+i)` in a loop. | **The value does not exist in the image.** Positive control: the same scan finds `0x43`, `0xFF`, `0x6A5E44B6` — so this is measured, not structural blindness. **Lift only by running the loop.** |
| 3 | **109 anonymous creation sites** (24 in the live-UI band) — windows that are never given an id at all. | **Identity does not exist.** No id-keyed rule can ever address them. They are reachable *only* through parent-subtree recursion, which is why §1.4 calls this low-risk rather than dangerous. Unknowable and mostly harmless. |
| 4 | **Instance counts at runtime.** `0x4C30E4FA` is 6 windows; `0x0423278F` is a template plus N open instances; the chip has 3 creator sites. | A creation site inside a loop or a pool is one site and many windows. **Offline analysis counts sites, never instances.** This is exactly why `IdCollectCtx` exists and why every remaining single-find is a latent bug. |
| 5 | **Which subtree an instance joins.** Nothing in the census proves parenting. | The `ChildAdd` argument is a register whose value comes from the object's own fields. **Needs a live `VWKID`/`MWKID` dump.** Every coverage verdict above that depends on parenting is flagged with its live evidence or marked unknown. |
| 6 | **Depth-1+ nodes the code addresses as top-level handles** (`0x00004200` class). | The denominator ladder counts **depth-0 roots by construction**, so these are excluded by definition. At least one exists; the count is unmeasured. **Lift by re-running the ladder over all depths — cheap, and worth doing.** |
| 7 | **Third-party plugin DLLs.** This repo even carries `tools\research\submenus-dll-src`. | They create their own windows in their own binaries. **Entirely outside every denominator we have.** |
| 8 | **The City LOADING / SAVING screen.** | **No `.UI` exists anywhere in the 339-file corpus and it never appears in the tree.** 100% code-painted. This one is genuinely settled. |
| 9 | **Region map tile labels/icons** (as distinct from the bubble). | Untested either way — see §5.8. **Settleable**: step 9 of the eyes-on session, with `DumpTree` at full depth and no bubble open. Not structurally unknowable; just never measured. |
| 10 | **Rich-text sizing.** All news/story/tutorial/popup text renders through the built-in HTML engine whose size tables live in `.rdata`. | **Outside the `cIGZWin` model entirely.** `FontStyle.ini` can never reach them, and `constants.json` holds only `x/y/w/h/l/t/r/b/gap`. The `kTipWrapSites` and `kPopupStyleRetargets` crosscheck skips are correct, not lazy. |

**The honest closing sentence.** We can name 315 shipping windows and we have a mechanism
for 299 of them. The 16 named exceptions are enumerated in §1.1 and §4 with a next step
each. Beyond the named set there is a large, uncountable population of anonymous child
windows, and the architecture is on our side there: the sweep recurses on the child list,
so they are scaled by having a covered ancestor, not by being known. **The part that should
worry us is neither the 16 nor the anonymous mass — it is item 1 in the table above: 27
call sites in the live-UI band, inside a factory whose output no offline tool in this repo
can enumerate.**

---

## How to reproduce everything new in this report

```
python tools\uimap\crosscheck.py                      # exit 0 - but quote the WHOLE line:
                                                      # 268 entries = 251 adjudicated
                                                      # (251 passed, 0 MISSED) + 8 DEFERRED
                                                      # + 9 SKIPPED. Neither a skip nor a
                                                      # deferral is a pass. (Corrected
                                                      # 2026-08-03: this read "251/251,
                                                      # 9 skipped" and hid the 8 deferred
                                                      # #57 sites.)
python tools\sdk\lookup.py <id|tgi|script>            # step 0 for any id
python tools\uimap\fn.py 0x443E60                     # tutorial builder, one function
python tools\uimap\fn.py --callers 0x779660           # the 6 Ordinances/news builders
```

Derived counts in §1 came from short scripts over checked-in artifacts
(`tools\uimap\_work\edges.json`, `funcs.json`, `wincensus.json`, `tools\uiscripts\extracted\`,
and the five retained `.log` files). The recipes, in one line each:

- **171 live ids** — `id=0x[0-9A-F]{8}` over the 5 logs.
- **1408 corpus ids** — `\bid=(0x…|\d+)` over 330 `.ui` files (`\b` excludes `clsid=`/`iid=`;
  **watch this — an earlier pass without it silently reported clsids as window ids**).
- **36 in neither** — `live − corpus − wincensus.setIds.value`.
- **Parent resolution of the 36** — linear walk per log tracking the most recent
  `PREFIX N id=` root line before each `PREFIX N.M` child line. **A label→id dict does NOT
  work; labels repeat across dumps and the last one wins.**
- **220 / 129 / 106 / 27** — `edges.json` calls to `0x00913C72`, owners via `funcs.json`
  `starts` + `bisect`.
- **86 sites / 21 literals** — `edges.json` calls to `0x779660`, then Capstone over the last
  14 instructions before each call.
- **Band split 20/17/20/7** — `wincensus.json` `setIds` bucketed by `owner` address.

**The scratchpad is volatile.** Re-derive from the recipes above rather than expecting those
scripts to exist.
