# SC4-UI-ENGINE — the GZWin UI engine of SimCity 4 Deluxe 1.1.641

**What this file is.** The *engine model*: how SimCity 4's UI is built, sized,
painted, hit-tested and re-imposed — written as the SDK guide Maxis never
shipped, from measurements taken while scaling that UI to 2x. Read it once and
you can predict how an **unseen** SC4 panel will behave before you open it.

**What this file is not.** It is not a change log and not a test plan. The five
laws that decide a fix are in `README.md`; symptom-to-mechanism triage is in
`tools\research\TRIAGE.md`; the method that produced these facts is in
`METHOD.md`; panel-specific anatomy lives in the family docs beside this one.
Every generalisable engine fact belongs here.

**Evidence rules used throughout.** Every non-obvious claim carries its source
inline: a **log line**, a **disassembly VA**, a **script path + line**, or the
doc that proved it. Binary facts are from `SimCity 4.exe` **1.1.641.0 Steam
(x86, 4GB-patched)**, ImageBase `0x400000`, file offset = VA − 0x400000 for
every section referenced; all disassembly offline (capstone 5.x, Unicorn for
emulation).

**Precision note on ids.** Three different kinds of hex number appear and are
routinely confused:
- **window id** — the `id=0x........` in a `.UI` script, what `GetID()`
  returns and what every skip-list keys on (e.g. `0xAA32BCE6`).
- **clsid** — the class selector in `clsid=` (e.g. `0xCA1492AC`
  cSC4WinAdviceList), resolvable to a name via the exe's registry (§8).
- **class vtable address** — a `.rdata` address (e.g. `0x00AB6AA8`), which is
  how *anonymous* windows (`id==0`) get identified at all.
This document always says which one it means. `0x00AB6AA8` is a **vtable**, not
a clsid; `0xCA318388` is a **clsid**, not a vtable.

---

## 0. THE BOUNDARY OF THIS SDK — what the GZWin engine does NOT draw

Everything in this file describes the **cIGZWin / GZWin** UI: windows,
`.UI` scripts, art binding, the buffer class, hit-testing. Some of what a
player sees on screen is **not drawn by that system at all**, and no lever in
this SDK can reach it. Recognising that early is worth days.

> **Triage first.** `tools\research\TRIAGE.md` maps a reported symptom to its
> mechanism, its lever and its precedent, and lists the five cheap measurements
> to take before opening a disassembler. Read that, then come here for the
> section it names.

**Two facts govern how this document's slot numbers are read.**

1. **The vendor header `cIGZWin.h` is missing one virtual.** Between
   `GZWinMoveTo` (real 56) and `FitRectToWindow` sits an undeclared **relative**
   move at real slot 57, `0x0099BD27` — `mov edx,[ecx+0xB4]; add edx,[esp+8]`
   (a delta, not an absolute). So **every header-derived slot NAME above 56 is
   one too low**, while the *indices* are unaffected.
2. **Slot 88 (`vt+0x160`) is the PER-CLASS "draw myself"**, not the composite
   driver. Measured across four classes, all distinct:
   `cSC4WinAuraBar 0x797CC0` · `GZWinBMP 0x9BC325` (the hooked one) ·
   `GZWinBtn 0x9B167D`. Do **not** move to slot 89 instead — that is the
   composite driver, and hooking it puts a thunk in front of the whole
   subtree walk.

**THREE BLIT BEHAVIOURS EXIST**, and assuming every blit is the first of them
costs a day:
**dst-follows-src** (GZWinBMP plain path — 2x art gives a 2x draw),
**stretch** (the 9-slice EDGE path), and **src-follows-dst**
(`cSC4WinAuraBar 0x00797CC0`: `src.L = (imgW-winW)>>1`, `src.R = winW+src.L`)
— the third is the only one where **under-sized art TILES rather than
shrinking**, so its art must be compared against the **window**, not the source.

**No element of the shipped UI is known to sit outside the boundary**,
and two elements once believed to be outside it are on the inside. Both are
worth recording, because each was put outside on a structural null.

**The paused screen-edge border IS a window** — `cSC4WinAlertBorder`, id
`0x6A5E44B6`, vtable `0x00AB5B48`, born full-screen and *never flipping
visibility*, which is precisely why a visibility probe cannot fire on it. Its
art exists in the shipped dats as three 120x120 sheets, `0x14315E60/61/62`,
and staging all three scales it. Note on the two 9-slice blitters:
`0x008D8800` serves **`GZWinBMP`'s `edgeimage=yes` path and `GZWinBtn`'s** and
is the busy one; the alert border's own path is **`0x008D9550`, which has
exactly one caller**, so an audit of `0x008D8800`'s callers says nothing about
the border. Neither blitter divides: each of the three drawers (`0x00794100`,
`0x009BC325`, `0x009B05E0`) cuts its own cell first. See §4.6c.

**The region city-bubble's Mayor Rating bar IS a window** —
`clsid=0xAA5D16A9` (`cSC4WinAuraBar`), `id=0x4A553000`, declared 102x11 in
`I-ca539340` at depth 3, and cured as a data change. Two nulls had put it
outside, and neither carried a positive control:

1. *"`RGKID` shows no window where it renders."* The dump stops one level
   above the bar.
2. *"A/B with `RatingArrowPatch=0` still doubles it."* True and irrelevant —
   that patch scales the **HUD** controller (`0x7E86C0-0x7E8A80`, the `imul ,7`
   sites). The region bar is a different class with different art, so the A/B
   tested a subsystem that was never involved.

**Two independent nulls, both structural, and their agreement reads as proof.**
It is not: agreement between two blind instruments is exactly as informative as
one. Before any element is called outside the boundary, state the positive
control for every null in its evidence — what the instrument WOULD have
shown, and whether it has ever shown it.

**THE STRUCTURAL FACT THAT DEFINES THE BOUNDARY, and the fastest test for it:**
> **The UI buffer class never composites to the screen.** Measured with the
> class-Blt hook armed: *every* destination is PANEL-sized — 258x482, 383x156,
> 360x156, 340x148, 323x156, 317x148, 280x148 — and **not one is
> screen-sized**.

So anything that spans the whole screen, or that paints over the 3D view
without owning a window, is being drawn in the **render / present path**, which
this project has never decoded and for which none of its instruments are
scoped. Two consequences:

1. **A blit-level hook on the UI buffer class can never see it** — a zero from
   such a detector is structural, not evidence (`METHOD.md`, "a null is not
   evidence until the instrument is proven able to see").
2. **The only foothold would be the graphics API** — everything visible must
   pass through the DirectDraw primary surface. That is a new subsystem, it
   runs through dgVoodoo, and it should be gated off by default and log-only.

**Triage rule, before spending a session:** if an element (a) never appears as
a window in a full-depth dump, (b) has no art in any dat, and (c) spans or
overlays the 3D view — stop. It is outside this SDK. Write down the negatives
and move on.

---

## 1. The window model

### 1.1 One tree, four hosts

The whole UI is a single `cIGZWin` tree rooted at
`cISC4App::GetMainWindow()`. Four interior windows matter because **which one
a window descends from decides how it can be fixed at all**:

| Window id | Role | Class / evidence |
|---|---|---|
| `0x6104489A` | `WinSC4App` — the app frame, first child of the main window | walked at `README.md` → architecture; `kGZWin_WinSC4App` in `UiSpike.cpp` |
| `0x9A47B417` | The 3D city view. **Host of every in-city HUD panel, toolbar, flyout and sub-flyout.** | clsid `0x9A47B417` = `cSC4View3DWin` (registry, `DYNAMIC-CONTROLS.md` Q1); QI'd as `cISC4View3DWin` |
| `0xEA659793` | Region-screen host, 13 children (legend, region panel, button clusters, compass, hidden flyouts) | boot tree dump; `kGZWin_RegionScreen` comment in `UiSpike.cpp` |
| `0xAA32BCE6` | The **Data Views fold-out panel** (compact bar + expanded pages + list flyout + a `0x0000AAAA` marker). The `kGZWin_MenuContainer` name it carries in `UiSpike.cpp` is a misnomer. | 8-child tree dump of the live panel |

> **`0xAA32BCE6` is a cautionary tale, not a menu host.** A label reading
> "hosts the entire plop-menu machinery" is enough to keep it on the sweep's
> skip list for weeks; one tree dump settles what it actually is, and skipping
> it by id is the defect.
>
> **`0x2AAB8CC1` is likewise not the region host.** It is the **tooltip layer**
> (class vtable `0x00AB6770`); on the region screen it
> exists but is empty and hidden (`UiSpike.cpp` `kGZWin_RegionScreen` comment).

### 1.2 THE PARENTAGE RULE — the first question to ask about any panel

> **A window is reachable by the runtime sweep ONLY IF it is a descendant of
> the 3D view `0x9A47B417` (or, on the region screen, of `0xEA659793`).
> Transients parented at MAIN-WINDOW level are invisible to the sweep and must
> be fixed in DATA.**

Descent from the host is **NECESSARY, NOT SUFFICIENT**, and the sufficiency
half fails for two structurally different reasons.

**1. The sweep never recurses to FIND a panel.** `ScalePanelsUnder` takes a
flat `EnumChildren` of the host (`src\UiSpike.cpp:10185`), so `ScalePanelRoot`
is only ever called on a **direct child** of the view, and a direct child is
skipped outright by any of eight gates: region whitelist (`:10233`),
`kNeverScaleIds` (`:10237`), god-tool flyouts (`:10245`), mayor-only flyouts
(`:10255`), the shared sub-flyout container (`:10262`), hidden and not
id-excepted (`:10273`), full-screen overlays (`:10300`), degenerate size
(`:10305`) — plus the 128-panel cap (`:10177-10196`). On the **region screen**
`:10233` makes the pass **whitelist-only**, so "descends from `0xEA659793`" says
almost nothing about reachability.

**2. Whole subtrees are walled off BELOW a swept root.** `ScalePanelRoot`
scales and anchors the root, then **RETURNS** for any id in
`kDataScaledSubtreeIds` — `src\UiSpike.cpp:14568-14573`, which sits **after**
the root move/resize (ends `:14553`) and **before** the child loop (`:14579`,
`ScaleSubtree` at `:14608`). That is the **only** call site of
`IsDataScaledSubtreeId` in `src\`, and `ScaleSubtree` never consults it, so
nothing re-opens those subtrees later. **Every descendant of such a root is a
3D-view descendant the sweep NEVER WALKS.**

**Warning: read the list, never a copy of it.** `kDataScaledSubtreeIds` spans
`src\UiSpike.cpp:5373-5486` and is longer than the advisor/Graphs/U-Drive-It
story suggests — **ten** ids: the advisor strip
(`:5374`), the three Graphs roots (`:5386-5388`), the U-Drive-It dashboard
(`:5397`) and its fifth console variant (`:5429`), and the **four**
Monthly-Budget roots (`:5466-5469`). A hand-list here would rot silently, and
only in the case you needed it. Note: the array CLOSES at `:5486`: `kFontSizedIds`
opens at `:5505` and the ids under it (Building Style Control `:5506`/`:5514`,
the `0xAA3ACB00` and `0x00000200` spinner blocks `:5523-5527`) are a **different
array with a different rule** — they are not walled off from the sweep.

**What is DATA-only is the DESCENDANTS, not the root.** The root is still
runtime-scaled and re-anchored every pass — deliberately, so HUD edge-anchoring
keeps working at any resolution (`src\UiSpike.cpp:5361-5364`; §7.3 cure 1). The
children ship born-scaled from `double_subtree_areas` in
`tools\selective-safe\build_selective_safe.py:646`, and that builder is the ONLY
place their geometry can be changed.

**The advisor strip is the worked example.** Its seven buttons live under
`0x6A15C767` (`src\UiSpike.cpp:5374`), which is in the list, so a fix aimed at
`ScaleSubtree` is aimed at code that does not run there. The log says so in one
line: `city panel 0x6A15C767 - 1 windows scaled`. The cure belongs in the DATA
builder.

**Ask the parentage question in this order:** is it under the host at all → is
it a *direct* child → does any of the eight gates skip it → is any ancestor in
`kDataScaledSubtreeIds`. Only a "no" to the last three means `ScaleSubtree`
governs it.

Consequences, and this is the whole decision tree for a new panel:

| Parentage | Treatment | Why |
|---|---|---|
| Under `0x9A47B417` | **Runtime scale** (`ScalePanelRoot` + `ScaleSubtree`) + 2x art in `SelectiveArt` — **Law: UNLESS the root id is in `kDataScaledSubtreeIds` (`src\UiSpike.cpp:5373`): `ScalePanelRoot` scales and anchors the ROOT, then RETURNS at `src\UiSpike.cpp:14568-14573`, before the child-enumeration loop that opens at `:14579`. `ScaleSubtree` is never entered below it and the children ship pre-scaled in the `.UI` (`double_subtree_areas` in `build_selective_safe.py`; §7.3 cure 1, §6.2)** | the sweep walks this subtree every tick, **except below a `kDataScaledSubtreeIds` root, where it stops AT the root**. Stated no stronger than the evidence: the gate lives only in `ScalePanelRoot` — `ScaleSubtree` does not consult the list (`IsDataScaledSubtreeId` has exactly one call site, `:14570`), so the exception holds because the sweep enters through `ScalePanelRoot` (`:10320`). The one path that could bypass it, `ScaleOnShow` (`:7371`), needs `gShowHookMode >= 2` and the shipped default is `0` (`:7217`) |
| Under the main window | **Static 2x `.UI`** (`build_dialog_static.py`: `area=` included) | "transient dialogs parented at the MAIN-WINDOW level (parent `0x00000000`), OUTSIDE the city runtime sweep... static-doubling them cannot double-scale" — live dump; `build_dialog_static.py` TARGETS comment |
| **Both layers act** | **BUG: ~4x** | the failure mode below |

**The double-scale failure, twice paid for:**
- *Establish City* (`0x6A414973`, script `I-2a41436b`) is served by the static
  dat **and** lives in the swept tree: static-only → sweep doubles it again
  (log `868x468 -> 1736x936`); DLL-only → right size but its `GZWinText` nodes
  render **purple** while `TextEdit`/button captions stay black. It needs BOTH
  the static entry AND its root in `kNeverScaleIds`
  (`UiSpike.cpp` kNeverScaleIds).
- *U-Drive-It status panel* (`0x10000006`):
  `discover_query_family()` adopts any script containing `id=0x10000005` +
  `clsid=0x89e1567c`, which the eleven driving scripts do — but their **root**
  parents at the 3D view (`DPROBE d1 par=0x9A47B417`), unlike the query panels
  the rule was written for. Log: `panel 0x10000006 (1968,8 424x650) ->
  (1536,16 848x1300)` = a 4x frame around 2x content.
  **LESSON: an auto-discovery rule can enrol windows whose PARENTAGE its author
  never checked.** Verify parentage per script before adopting a family.

The purple-text asymmetry is itself an engine fact worth keeping: **runtime
geometry scaling does not carry the text/art resolution path that a doubled
`.UI` does** — `GZWinText` nodes mis-resolve, `GZWinTextEdit` and button
captions do not (`UiSpike.cpp` kNeverScaleIds).

### 1.3 Child enumeration order is REVERSE of add order

`EnumChildren` (and therefore every tree dump) enumerates children in **exact
reverse of `.UI` sibling order**. Proven: the composite HUD's 14 children
appear in the dump precisely backwards from `I-2bc90671`, background last
(`CITY-DOCK-OVERLAP.md` §1.2). `.UI` order = add order = **paint order, first
child painted first (behind)** — only first-behind explains the dock's
full-size background BMP being its first child with buttons painting over it.

Three things depend on this and have each broken once:

1. **Z-order / paint order.** Top-level add order gives, bottom to top:
   `0xE9889775` (composite) < `0x0987B48F` (dock) < `0xEA8CAD14` (mode
   overlay). So the **dock paints on top of the composite**, and the two
   background sheets are shaped to interlock — `4bbe9c7d` has a diagonal notch
   cut into its top-left, `13d14ca0` has the curved right hump that fills it
   (`CITY-DOCK-OVERLAP.md` §1.2–1.3).
2. **Never identify a button by enumeration order — use its y position.**
   `MAYOR-MODE.md` "The mayor toolbar map"; the same rule is restated in
   `kMayorFlyoutDock`'s header comment.
3. **A global `GetChildWindowFromIDRecursive` returns the LAST-ADDED match.**
   Window id `0x0BC3B559` is not unique — the HUD dock minimap and the
   U-Drive-It dashboard minimap share it, the dashboard is added later, so
   while driving a global search reached the *dashboard's* instance. The
   MINIMAP block now **scopes** its search under the dock `0x0987B48F` and
   prints the parent id, because both log lines otherwise read "128x128"
   (`UiSpike.cpp` MINIMAP block, v2.22.3 audit fix).

### 1.4 Geometry primitives and their traps

| Fact | Evidence |
|---|---|
| Window rect lives at `this+0xA8..0xB4` = (L,T,R,B) on the `cIGZWin` subobject | `DYNAMIC-CONTROLS.md` method notes; getters `GetW 0x99C81B`, `GetH 0x99C82A`, `GetL 0x99BC53` |
| `GZWinMoveTo` is **RELATIVE** — moves BY a delta in parent space, never TO an absolute | `README.md` FACTS; `ScalePanelRoot` comment "proven by the cycle-20 diagnostics" |
| **MSVC reverses the vtable order of overloaded virtuals**, so adjacent overloaded pairs like `GetArea`/`SetArea` land in swapped slots vs the header and are unusable via naive vtable indexing | `README.md` FACTS; `GetAreaAbsolute()` is avoided for exactly this reason (`UiSpike.cpp` AbsTopLeft comment) |
| Confirmed slots: `GetW +0xA4`, `GetH +0xA8`, `GetArea* +0xC0`, `SetW +0xCC`, `SetSize +0xD4`, `SetArea4 +0xDC`, `GZWinMoveTo +0xE0`, `GetChildAsRecursive +0x94`, `Show +0x110` / `Hide +0x114`, **`GetID +0xFC` / `SetID +0x100`** | `DYNAMIC-CONTROLS.md` method notes (community `cIGZWin.h` confirmed against game code). ⚠ **CORRECTED 2026-08-24:** this row read "`SetID +0xFC`" for months — wrong, and it is the very overload-reversal trap the row two above warns about. Byte-verified on `cGZWinText`'s vtable `0xADFEB8`: `+0xFC` → `0x99BE66` = `mov eax,[ecx+0x10]; ret` (a zero-arg **getter**, it cannot be a setter), `+0x100` → `0x99BE5C` = `mov eax,[esp+4]; mov [ecx+0x10],eax; ret 4` (the **setter**). Our shipped code is unaffected — it calls the vendor header, never raw slots — but every `SetID +0xFC` in older notes and memories inherits the error |
| `InvalidateSelfAndParents()` is the ONLY safe repaint primitive after a geometry change — without it the game keeps the stale paint until a mouse hover invalidates (the panel then scales only when the pointer passes over it) | `GOD-MODE-FLYOUTS.md` "Other hard-won rules"; **never** call Plot/draw entry points from a hook |
| Window flags: `1` = visible, `0x80000` = MouseTrans (routes to the refined mask), `0x200000` = **input-transparent** (router skips the window entirely — the cheapest "get out of the way" lever) | `GOD-MODE-FLYOUTS.md` reusable playbook |

### 1.5 Anchoring: how a scaled root is placed

`UiSpike::ScalePanelRoot` (`UiSpike.cpp` ~L5365) is the model of how the game
itself lays out at different resolutions, and it was validated against stock:

```
gapL = l              gapR = frameW-(l+w)      gapT = t     gapB = frameH-(t+h)
per axis:  both gaps > frame/4  ->  scale about the panel's own centre
           else                 ->  keep the SCALED gap to the nearer edge
```

This is not an invention. **The game's own convention is fixed pixel corner
gaps plus centred top elements at any resolution** — stock 800x600 and
native-design child coordinates are *identical* line for line, so uniform 2x
reproduces stock composition exactly, including the top cluster's 3px
off-centre bias (`STOCK-PARITY.md`). Edge math on a mid-screen panel teleports
it (the day/night slider at y=832 became y=64), which is why the centre branch
exists (`ScalePanelRoot` comment).

**The design-overhang exemption.** Stock hangs the minimap dock `0x0987B48F`
11px off the bottom and starts the mode overlay `0xEA8CAD14` at y=−16, *by
design*. An unconditional on-screen clamp discarded the correct anchor answer
and lifted the dock 22px relative to the composite — the whole
"Mayor symbol overlaps / elements look missing" report reduced to that one
number (`CITY-DOCK-OVERLAP.md` §2.3: ghost target (204,1250) vs actual
(204,1228), *x exact, y off by exactly 22*). The clamp is now per-edge and
conditional on the **design** gap:

```cpp
if (gapR >= 0 && newX + newW > frameW) newX = frameW - newW;
if (gapL >= 0 && newX < 0)             newX = 0;
if (gapB >= 0 && newY + newH > frameH) newY = frameH - newH;
if (gapT >= 0 && newY < 0)             newY = 0;
```

A negative gap can only reach the clamp via the matching edge-anchor branch
(the centre branch requires both gaps > frame/4, i.e. positive), so
`gap < 0` is *precisely* "the anchor result carries scaled design overhang"
(`CITY-DOCK-OVERLAP.md` §3.1).

---

## 2. Widget catalogue

Each row: what determines the widget's **size**, what its **art binding** is,
and its **scaling rule**. Rules marked **Law** are laws — breaking one has cost a
shipped regression.

| Class (clsid / vtable) | Size determined by | Art binding | SCALING RULE |
|---|---|---|---|
| **`GZWinBMP`** (iid `0xC12CEA13`, descriptor `0xAD5CE0`; class vtable **`0x00ADF6A0`**, Plot override `0x9BC325`) | Its own `area=`; but the **DRAW** is `dst = origin + srcW×srcH` — the draw follows the SOURCE IMAGE, not the window | `image={gid,iid}` + optional `imagerect=` source crop; 419 controls have `area` exactly == PNG dims (1:1 blit) | **2x art scales the draw with NO code hook.** **Law:** `imagerect` must double whenever its art doubles. Corollary: **a 2x source rect over a 1x bitmap draws only the corner that exists** — that is exactly what a shadowed art override looks like on screen. Evidence: `MAYOR-MODE.md` "EMERGENCY = the missed-art-pass case" (Plot `0x9BC325`, 3-state branch divides src by 3, helper `0x8D8800`); `UI-ART-BINDING.md` addendum. **Warning: the LIVE `imagerect` is a bind-time LATCH** — `SetImage` (`0x9BC57E→0x9BC447`) rewrites `[win+0xE8]` from the window's area *at that moment* and `SetArea` never touches it, so content bound before a resize keeps drawing its pre-resize size (§2.6) |
| **`GZWinText`** (cGZWinText, ctor `0x9C19C8`, 0x114 bytes, main vt `0xADFEB8`, iface vt `0xAE0118`, `cIGZWinText` iid `0x212cdc1f` at `+0xD8`) | The **font style**, resolved at creation | `font=` style; no image | Doubled window + doubled FontStyle style = correct. **Law:** only if `font=` is **GUID-valued** (§5.1). Controllers bind the interface and update captions only (`0x7EE64D`/`0x7EE668`) |
| **`GZWinBtn`** (iid `0x00008810`, descriptor `0xAD5CAC`; button class vtable `0x00ADDAF0`) | Its `area=`; the art is a **horizontal 4-state strip** (normal/hover/pressed/disabled), state selected by `imageWidth ÷ 4` — proportional, no pixel constants (875 buttons satisfy `pngW = 4×btnW`) | `image={gid,iid}` strip | **Safest case: a 2x strip still picks the right cell.** Verified in-game on the Audio playlist checkbox (8 states of 16x16, slicing is `imageWidth/8`). The generic strip `{46a006b0,144161eb}` (120x30) serves buttons 130–370px wide but is always 30 tall, so horizontal fit is proportional and the vertical dimension is the widget's own (`SDK-GAPS.md` G27) |
| **`GZWinTextEdit`** | `area=` | `image=` (format also defines `thumbimage`/`containerimage`/`backimage` for Scrollbar2/OptGrp/TextEdit, **none in use** in the shipped corpus) | Scales like a plain window. Data point: under runtime-only scaling its captions render **correctly** where sibling `GZWinText` nodes go purple (§1.2) |
| **`0x89e1567c`** = **cSC4WinGenTransparent** (factory `0x4661D0`, ctor `0x79C560`, vt `0xAB7358`) | `area=` | `image=`/`blttype` like a GZWinGen | Ordinary container: scale it and recurse. It is also the **query-family fingerprint**: root `0x10000005` + `clsid=0x89e1567c` is what `discover_query_family()` matches (`build_dialog_static.py`) |
| **`0xAA7CECFD`** = **`cSC4WinText`** (`GZCLSIDDefs.h:285`; 56 uses) | The **font style** — it IS a `cGZWinText`: factory `0x007BE740` runs `cGZWinText`'s own constructor `0x9C19C8` on a 0x114-byte object and then swaps the vtable to `0x00ABA190`, which differs from `GZWinText`'s in exactly two slots: 88 (Plot → `0x007BE7A0`) and 148 (dtor) | `font=` | **Scales correctly off fonts with no help** — same object layout, same font-resolution code; only the painter differs. It is reached by GZCOM clsid instead of by the `.UI` class name, which is why it sits outside the `GZWinText` name path. Proven by co-location: in `I-aa920991` the region name (`0xEA5BD179`, this class) rendered 2x while sibling plain `GZWinText` nodes in the same file rendered 1x (`FONTS-AND-DIALOGS.md` Q1 table). Same for the city name `0x00000002` in `I-c973b411` |
| **`cSC4WinAdviceList`** clsid **`0xCA1492AC`** (QI `0x793080`, Init `0x793190`, **item-create `0x7931F1`**, vt `0xAB58B0`; draw-self is a **no-op** `mov al,1; ret` @ `0x949ADE` — children paint) | Container from `area=`; **its items are GAME-sized**: item-create does `SetArea(0, 0, GetW(), GetH())` of the already-scaled container (vcalls `[+0xA4]`,`[+0xA8]`,`[+0xDC]` at `0x793210–0x79322E`) | none itself; items are the rich-text class below | **Law: scale the list, NEVER recurse into it.** Recursing double-scales: the news reader's item ballooned to **1648x708 inside its 824x354 list** (v2.18.6). Members: `kAdviceListScaleSelfIds` = `0x6A231531` (news reader), `0x00100100`/`0x00100101` (advisor briefings), `0xAA1F1EB5`/`0x6A1F1F4A` (My Sims stories). **STRUCTURAL WEAKNESS, noted not fixed:** the guard is keyed by ID, so any NEW `0xCA1492AC` window is unprotected by default (`UiSpike.cpp` comment) |
| **`cSC4WinMiniMap`** clsid **`0xCA318388`**, interface iid **`0xCA318385`** | `area=`; `blitSize` at `[this+0xE4]` self-updates via the class `SetArea` override — **but the display surface at `[this+0xF0]` is ONE-SHOT**, inited once at city load | code-painted into its own surface | **Law: every scaled instance needs destroy-and-recreate of the surface** (not a resize: `vtable+0xC` is an `Init`, one-shot; calling it on a live surface corrupts it — replicate the game's own pattern `0x7A8C18–0x7A8C61`, then its recompute `0x7A7840`). **Three known instances:** dock minimap `0x0BC3B559` under `0x0987B48F` (MINIMAP block); Data-Views map child `0x00004203` (DVMAP block); U-Drive-It dashboard minimap, **same window id `0x0BC3B559`** under `0x4BCB938A` (UDMAP block, scoped). Skipping the recreate is **fatal, not cosmetic**: a 512-sized render into a surface still inited at 256 = heap overrun = silent native death, which is precisely the v2.21.0 Data Views expand crash (renderer `sub_7A2F60`, live rect read `vt+0xBC` @ `0x7A301E`, buffer create `0x7A3094` format `{9,32bpp}` clsid `0xC470D325`, 77-case painter table `0x7A4884`). **Law: the SIZE you pick selects a code path — see §2.4 for the terrain bake, the derived `zoom`, and the exact-power-of-two constraint on `blitSize`** |
| **`0xCBCBF1E0`** (unnamed, 134 uses) — code-painted **gauge dials** | its own **cached buffer**, which keeps its 1x size while the window doubles | code-painted (its TGIs *are* staged 2x and it still draws small) | Symptom: a correct 2x black circle with a small dial face pinned top-left (`SDK-GAPS.md` G34). The My Sims portraits are the same shape, and a per-open census of hook calls found the hook installed and never called there; one leaf invalidate per open cured them (law 41). Run that instrument here before reaching for **force-recreate-buffer** (§7.3). **Law:** probe the vtable AND scope the hook to the owning root `0x4BCB938A` first — class identity alone is what crashed the game on Earned Cars (§2.1 note) |
| **`0x00AB6AA8`** (vtable) container + **`0x00AB6D88`** (vtable) strip — the **flyout pair** | on-screen size == the **source buffer's** physical size, NOT the window rect (composite is a 1:1 clipped copy) | immediate-mode blits from an art atlas read out of the draw context | See §2.1 — the most involved widget in the game and the source of most reusable technique |
| **`0xAA12E5F5`** — rich-text pane (`GetClassID 0x8FA317`; creation sites `0x443FC9`, `0x76A182`, `0x78CE11`, `0x7931F0`; created via `CreateInstance(clsid 0xAA12E5F5, iid 0x4A11FD4A)`) | Content-sized from the **HTML engine's** point tables — *not* FontStyle | text is HTML; page art via `sc4://` URLs | Text scales only via the `.rdata` table patch (§5.2). It appears as `id=2` in the five message-box scripts and is the item AdviceList creates |
| **`GZWinCustom`, `id=0x0000AAAA`** — the **alignment marker** | sized like the panel's **anchor** (usually its spawn button) | none; `winflag_visible=no` | **Law: POSITIONING DATA. NEVER SCALE IT — not at runtime, not in shipped data.** See §6.1 |
| **`GZWinSpinner`** | derives its size from its **arrow strip** `{46a006b0,82b99d9d}` | that strip | **Law:** art-sized ⇒ `kFontSizedIds` treatment: **scale position, leave size alone** (§6.2) |
| **`GZWinGrid`** | `drowheight` / `dcolwidth` (**d-prefixed** — a `\browheight` regex silently missed them) and `wingridcol="a,b,width"` where **every 3rd slot is a PIXEL width** | per-row art may be code-bound (`0x14416244`) | Scale the d-attributes and the width slot only; never the two index slots (`build_dialog_static.py`; `DYNAMIC-CONTROLS.md` addendum) |
| **`cSC4WinRCI`** clsid `0xC7A0E17E` (factory `0x466170`, ctor `0x7A9770`, **Draw `0x7A9500`**, vt `0xAB8628`) | **the WINDOW rect** — reads `this+0xA8..0xB4`, `half = extent/2` from the window, log-scales the demand value; **no pixel constants anywhere in the function** | none (FillRect via draw context) | Fully proportional: **follows doubling automatically**. If it looks stock, the three 8x71 column windows (`0x09D27EB0`/`0x29D27EC0`/`0x49D27ED0`) were not actually resized — dump their W/H (expect 16x142) |
| **`cSC4WinTrendBar`** clsid `0xAA5C2F86` (factory `0x4661A0`, ctor `0x7BF5E0`, **Draw `0x7BF0A0`** = vt `0xABA430` slot 88, main vt `0xABA68C`, iface iid `0xCA5C2F84`) | **its ART's pixel size**, drawn *centred* in the window (`x = L+(winW−imgW)/2`); the fill marker is `fraction × (imgdim−1)`; **the FILL sheet is a SIX-cell strip — `bandW = fillW/6`** (`0x7BF0E4` `imul 0xAAAAAAAB` / `0x7BF0F5` `shr 2`, the /6 reciprocal; byte-verified) | **code-bound** `{46A006B0,0x14015580}` groove + `{…,0x14015584}` fill, loaded by the polls controller at `0x7ED4AC` and pushed in via **`SetImages` `0x7BEEB0` (main vt slot 4) — stores POINTERS only** — **zero `.UI` refs**, so `find_cell_strips.py`'s `.UI` derivation is blind BY CONSTRUCTION; the fill's states=6 lives in its `CODE_BOUND` table (byte evidence inline) | Content scale = **art size only**. Note the deceptive symptom: the fill is proportioned relative to its own groove image, so the bar reads "correct" even while the whole unit renders 1x centred in a 2x frame. **Note: IMMUNE to §2.6's SetImage latch** (measured): Draw re-reads EVERY geometric input live per frame — groove/fill dims via `cIGZBuffer` Width/Height virtuals each draw, vertical extent from the draw rect that **vt`+0x184` (base impl `0x99CF6A`) recomputes INSIDE the SetArea chain** — full member census found zero stale-able geometry; bind-before-sweep and bind-after-sweep draw identically, f=2 control pixel-exact. (`+0x184` = slot 97, which for this family is a draw-rect recompute) |
| **`GZWinFlatRect`** | `area=`; the ticker's clip strip is **resized by code** at init to `SetSize(W, min(2×lineHeight, H))` | `fillcolor` | Ordinary — but see §6.3: some are re-imposed |

### 2.1 The flyout pair `0x00AB6AA8` / `0x00AB6D88` in detail

These two anonymous classes (`id==0`, identified only by vtable) implement the
disaster flyout **and every second-level menu** — the shared sub-flyout
container `0x8A6E61E0` and its strip `0x8A2CAD8B` are the *same classes*, so
the disaster fixes apply verbatim (proven by the SVT probe, `MAYOR-MODE.md`).

**Container (`0x00AB6AA8`), Plot `0x0079B0E0`** — fully reverse-engineered
(279 instructions):

1. **Top gate:** `test byte[0x114],1; je end` — Plot only REDRAWS when the
   dirty bit is set, and clears it after. Normally dirty=0, so Plot early-exits
   to the blit path and just re-blits the cached buffer.
2. **Redraw path (dirty=1 only):** reallocates the internal buffer `[0xDC]` to
   the window rect size (realloc check at `0x79B117`), then draws bar/circle
   into it via the draw context `[0xD8]->[0x74]` plus the arc/tile helper
   `0x8D8BC0`, using rects = window W/H minus the `[0xE0..0xF4]` **insets**.
3. **Blit path (always):** `[0x68]->Blt(src=[0xDC], …)` with a rect at
   `[0x24..0x30]`.

Live values that explain everything (DOBS, un-forced): `r24 = (0,0,282,678)`,
`win = (66,682,348,1360)`, `dst68 = 2400x1600 32bpp` (the FULL SCREEN buffer),
**`srcBuf [0xDC] = 141x339`** — created once and reused forever.

The six layout fields at `[0xE0..0xF4]` measured `53, 25, 12, 94, 62, 6`. Under
the offline emulator (the real Plot run under Unicorn) the four container draws
are: bar top cap `dst(229,0,282,25)`, bar spine
`(229,25,282,653)` via the tiling arc helper, bar bottom cap
`(229,653,282,678)`, **ring `dst(0,138,94,200)`**. Note the **opposite
anchoring** — the circle is LEFT-anchored `x[0,0xEC]`, the bar is
RIGHT-anchored `x[W−0xE0,W]`; that is why blind field-doubling looked wrong.

**Strip (`0x00AB6D88`), Plot `0x0079AA70`** — loops items from `[0xD8]`,
reading item size `[0xF4]`, spacing `[0xF8]`, count `[0xFC]`, drawing a visible
RANGE `[0xE4]..[0xE8]` (it is a genuine scrollable control). Each picture blits
`src 44x44` from a **352x88** sheet — which is already 2x of native 176x44, so
reading 44x44 grabbed a QUARTER of the icon (the "zoom") **and the same 44px
fields fed the hit-test**, so clicks missed.

**Custom hit-claim (the hardest bug in the project).** The container
**overrides `IsPointInMe`** with `0x0079A180`, which transforms the point
(`[vt+0xEC]`) and tail-calls its **slot 121 = `0x0079AE30`** — six
instructions: bounds-check the window rect, then

```
claim = local_x >= (width - [this+0xE0])
```

i.e. it claims **only the rightmost `[0xE0]` px**. With `[0xE0]` still holding
the 1x strip width (~49) while the draw went 2x: `288 − 49 = 239` = *exactly*
the measured dead-zone threshold. The strip's own hooks stayed silent
there because they were **downstream of a closed gate** — silence in a
downstream hook is not evidence the hook is wrong.

**Law: `[0xE0]` is DUAL-USE**: hit-claim width (wants 2x) **and** a Plot layout
inset (wants 1x — otherwise the game paints its own bar beside the replayed
one, the "second orange bar"). The rule: **scale it for the hit-test and mask
it back to 1x inside the draw-group hooks** (slots 87..97; hit-tests never run
inside the draw group).

**The draw group, slots 87..97**, is the range hooked wholesale, because
`__thiscall` is callee-cleanup and a thunk with the wrong argument count
corrupts the stack. Both `SlotThunk<N>` and `SlotThunk2<N>` are installed over
`for (int si = 87; si <= 97; si++)` on a 256-entry private copy of the instance
vtable (`src\UiSpike.cpp`, **six** install sites — re-count with
`grep -c "si <= 97"` rather than trusting any line numbers; anchors move as
the file grows, and the symbol is the anchor, not the number).

**The table below is re-derived from the exe** (base `cGZWin` vt
`0x00ADC8D8`; `cSC4WinMiniMap` vt `0x00AB83B8` differs only at `+0xDC` and
`+0x160`) and is carried in `src\UiSpike.cpp`'s header comment. **Slot 89 is
easy to omit, and omitting it shifts every name after it by one** — call
"92" expecting `GetDrawContext` and the answer is NULL, call "93" expecting
`GetBufferToDrawTo` and the answer is `[ecx+0x6c]`, the DRAW CONTEXT. Slot
87's `0x0099BE4C` is
`GetNotificationTarget` (a zero-arg getter), and the per-class draw `GZPaint`
is slot **88** (§0).

| idx | offset | virtual | VA |
|---|---|---|---|
| 87 | `+0x15C` | `GetNotificationTarget` | `0x0099BE4C` |
| 88 | `+0x160` | **`GZPaint`** (per-class draw) | base no-op `0x00949ADE` / minimap `0x007A79B0` |
| 89 | `+0x164` | **`Plot`** (= composite + present) | `0x0099BA07` |
| 90 | `+0x168` | `CalcAbsoluteArea` | `0x0099DCE4` |
| 91 | `+0x16C` | `InvalidateSelf` (`[ecx+0x70] = 1`) | `0x0099BECC` |
| 92 | `+0x170` | `InvalidateSelfAndParents` | `0x0099BED1` |
| 93 | `+0x174` | `GetDrawContext` (`= [ecx+0x6c]`) | `0x0099BEF9` |
| 94 | `+0x178` | `GetBufferToDrawTo` (`= [ecx+0x68]`) | `0x0099BEFD` |
| 95–98 | `+0x17C..+0x188` | `SetBufferToDrawTo` / `…Recursive` / `SetAreaToDrawTo` / `…Recursive` — zero-arg, hooked safely | `0x0099C6F8` / `0x0099D57E` / `0x0099CF6A` / `0x0099D5B7` |
| 100 | `+0x190` | `PrivateBuffer(bool)` — **NOT zero-arg** | `0x0099EA70` |
| 101 | `+0x194` | `GetPrivateBuffer` (`= [ecx+0x64]`) | `0x009D419D` |
| 123/124 | — | `PlotComposite` / `PlotPresent` | `0x0099E62D` / `0x0099C498` |

Slots 95–98 are named from the base implementations and all end in a bare
`ret` (zero-arg), which is why hooking the whole 87..97 range is safe. The
community header's names for this band include argument-taking entries, so do
not hook any of them with a typed thunk on the strength of a name alone
(`SDK-GAPS.md` §1).

**95–97 override census + disassembled semantics (2026-08-23):** diffed
`[vt+0x17C]`/`[vt+0x180]`/`[vt+0x184]` across all 111 window-class vtables in
`tools/uimap/_work/wincensus.json` — **zero overrides**; every class (named
and anonymous) resolves to the same three base bodies, so these three
virtuals are non-polymorphic in this build. Slot 95 `SetBufferToDrawTo`
resolves `[this+0x68]` to its own private buffer (`[this+0x64]`) or, walking
`GetParentWin()`, the nearest ancestor that owns one or carries
`WinFlag_DelayedPlot` (`0x8000000`) — falling back to the `cIGZGraphicSystem`
service for the tree root — then calls its own slot 98. Slot 96 is slot 95
on self, then slot 96 recursively on every `[this+0x44]` child. Slot 97
writes `[this+0x24..0x30]` areaToDrawTo using the identical ancestor-stopping
rule as slot 95, so buffer and area always name the same drawing surface;
slot 98 is the slot-96 recursion pattern applied to slot 97. Full derivation:
`SDK-GAPS.md` §1.

**Slot 89 `Plot` is load-bearing, not trivia:** it calls `[eax+0x1EC]` and only
reaches `[eax+0x1F0]` if that returned true — so **a `[win+0x64]` private
buffer cannot reach the screen without a paint on the same object in the same
call.**

**Built-in positive control for any hook in this range:** a call to
`InvalidateSelfAndParents()` routes through the swapped vtable, so **slot 92
must fire**. If 92 fires and nothing else does, the machinery is
proven and the silence is a finding. If 92 is also silent, the swap did not take
and the index base is wrong.

**Law: the right class is NOT the right window.** The disaster-derived surgery
(buffer force-recreate, `[0xF4]/[0xF8]/[0xFC]` doubling, `[0xE0]` claim
doubling) installed itself on U-Drive-It's *Earned Cars* strip — same class,
different layout — and the game died. The container's vtable check passed;
class identity was **necessary but not sufficient**. The fix is a
**known-menu gate**: hooks install only while one of the five validated parent
menus is visible (`SUBSKIP` logs the decline). Verify the class **and** the
owning context.

**Law: identify these windows positively, never by size.** Height-only gates
missed the 258x206 Freight menu twice (at 300, then 260); the identification
that works is **exact width**: `destIsSubContainer = (selfW==258 && selfH>=100)`.
And a "200–400 wide, >500 tall" bar gate ate **tooltip** buffers (tips are
content-sized: 430x120 / 490x316 observed), tearing their translucent fill in
the x 200..400 band.

### 2.2 The routing / hit-test architecture (applies to ~90 classes)

1. **Router** `GetChildWindowFromCursorPoint` **`0x0099DFA9`**: walks the
   `[this+0x44]` child list **head-forward**, skips children without flag `1`
   or with flag `0x200000`, gives the point to the **FIRST** child whose slot 40
   (`[vt+0xA0]`) claims it, else falls back to `self.IsPointInMe` (slot 62,
   `[vt+0xF8]`). **First-claim-wins ⇒ a closed upstream gate STARVES every
   downstream hook.**
2. **Base `IsPointInMe`** **`0x0099C97C`**: coarse `[this+0x14]` rect test; if
   flag `0x80000` (MouseTrans) then transform (slot 59) and run the **refined**
   test slot 149 (`[vt+0x254]` → `0x0099BBBE` → the `[this+0x64]` mask
   sub-object's 2-arg HitTest, **result inverted: 0 = opaque = clickable**).
3. **Custom overrides exist.** Always read the class vtable before assuming
   base behaviour. Useful slot offsets: slot 40 `[vt+0xA0]`, slot 59
   `[vt+0xEC]`, slot 62 `[vt+0xF8]`, slot 121 `[vt+0x1E4]`, slot 149
   `[vt+0x254]`, GetFlag `[vt+0x10C]`.

**vtable scan technique:** search the exe image for a function's little-endian
address; each hit inside `.rdata` is a vtable slot, and `VA − slot*4` is the
vtable base. That is how base-vs-override was settled without a game launch.

### 2.3 The buffer classes (cIGZBuffer) — there are **TWO**, and **THREE** channels

**Law: THERE IS MORE THAN ONE BUFFER CLASS, AND MORE THAN ONE WAY OUT OF A
BUFFER.** Naming one class and one slot is exactly how five separate
instruments can all report "every blit corrected" while the screen shows
uncorrected art. From `src\UiSpike.cpp:390–480` and `:3925–3955`.

| Class vtable | Where it turns up | Slot 29 (`Blt`) |
|---|---|---|
| **`0x00AC1400`** | the main UI buffer class — flyout container buffers, the shared screen buffer | `0x826AD0` |
| **`0x00ADB418`** | a **second, different** buffer class. Region-screen map items hold these at `[item+0x28]`/`[item+0x2C]` (verified on two independent runs, `src\UiSpike.cpp:16059`) | `0x00991BA0` — and it **can take a renderer path under dgVoodoo** |

**`0x00AC1400` slot / field map**

| Slot / field | Meaning |
|---|---|
| `+0x0C` (idx 3) | `Init` = `0x8269B0` — **one-shot** |
| `+0x24` (idx 9) | `GetW` = `0x808620`, returns `[0x1C]` |
| `+0x28` (idx 10) | `GetH` |
| `+0x30` (idx 12) | `GetBufferArea` = `0x8268C0` (`lea eax,[ecx+0x14]`) |
| **`+0x50` (idx 20)** | **the PRESENT path** — its own 16bpp pixel loop, reached from `0x0099BA3E`. Copies a window's PRIVATE buffer out. **Does not route through slot 29.** |
| `+0x74` (idx 29) | **`Blt` = `0x826AD0`** |
| `[0x14..0x20]` | area rect (L,T,R,B); `[0x1C]`/`[0x20]` = W/H |
| `[0x3C]` / `[0x40]` | **pixel pointer / stride** — 32bpp **BGRA**, magenta `0xFF00FF` = colour key |

**The three channels a pixel can leave a buffer by**, and the rule that
follows:

1. **slot 29 `Blt`** — the one everybody hooks.
2. **slot 20 (`+0x50`)** — the private-buffer present, `0x0099BA3E`.
3. **`PlotPresent` `0x0099C498`** — primary call `[eax+0x98]`, the renderer.

**Law: a window that owns a PRIVATE BUFFER is invisible to a slot-29 hook.** The
menu strip's own slot 192 (`0x0079BDC0`) calls `PrivateBuffer(true)`, so its
item draws write into that buffer, and the buffer then reaches the screen by
channels 2 and 3. *Every* "the instrument says corrected, the screen says not"
report reduces to this. **Before believing a blit census, ask whether
the window has a private buffer** (`GetPrivateBuffer`, slot 101 = `[ecx+0x64]`).

**Note: the `PRESENTWATCH` positive control is the model to copy.** `gS20Any`
counts EVERY slot-20 call for ANY window, not just the interesting one — so a
silent "no present over the cell" can be told apart from "the thunk never ran".
A probe without that counter produces a null that cannot be graded.

**Law: buffer `Blt` CLIPS, it never stretches** (no scaling ops in `0x826AD0` or
its delegate `0x826210`; proven again empirically — a dest rect set to
`2538x6102` changed nothing on screen). Therefore 2x is reached by a **bigger
buffer**, a **code upscale**, or **field doubling** — never by enlarging the
dest rect.

Two consequences that are pure gold and reusable:
- **You can read the game's own art at runtime and re-blit it bigger.** The
  draw source (`[0xD8]`) is itself a readable buffer, so the ring is fixed by a
  nearest-neighbour upscale of the 94x62 sprite into 188x124 — **no dat
  needed**.
- **Law: the alpha guard shape is `0 < a < 128`, never `a < 128`.** Stock
  magenta-keyed art has `a == 0` everywhere and MUST keep drawing; the
  submenus mod's RGBA frame art has semi-transparent edges that painted a dark
  halo.

**The colour key, in the exact form the code tests it**
(`src\UiSpike.cpp:2491`). Pixels are **32bpp BGRA**, so magenta is *not* a `0xFF00FF`
word compare — it is a per-byte test, and writing it as a word is a real way to
get it wrong:

```c
if (sp[0] == 0xFF && sp[1] == 0x00 && sp[2] == 0xFF) continue;  // B,G,R = magenta
if (sp[3] >  0x00 && sp[3] <  0x80)                  continue;  // 0 < a < 128
```

**Law: this is also why no interpolating resampler may ever touch shipped
art.** Interpolation moves a keyed pixel off exactly `0xFF00FF`, the test above
misses it, and **the key colour itself draws** — that is the pink Mayor Rating
bar and the pink news-reader borders, one launch after `--hq` was enabled.
Nearest-neighbour only copies source pixels, so it cannot invent a colour the 1x
art lacks; that single sentence rules the upscaler out of any colour or seam
investigation. See §4.6c.

**DEAD END, do not retry (nine builds):** you cannot read the rendered frame
back in-process. The container has no private buffer; it paints into the shared
2400x1600 screen buffer, which is **GPU-only** — `Lock()` succeeds but every
pixel reads `(0,0,0)` and `GetColorSurfaceBits()`/`Stride()` return 0.
Objective pixel measurement must come from a real screen capture.

### 2.4 `cSC4WinMiniMap` (clsid `0xCA318388`) — the TERRAIN BAKE

The §2 catalogue row covers this class's *geometry* (`blitSize` self-updates,
the display surface is one-shot). This subsection is the other half: **how the
terrain image gets INTO that surface**, decoded from the shipped exe. It is
here so that nobody has to re-disassemble it.

**Read this before changing the SIZE of any minimap instance** — dock minimap
`0x0BC3B559` under `0x0987B48F`, Data-Views map child `0x00004203`, U-Drive-It
dashboard minimap (same window id `0x0BC3B559`) under `0x4BCB938A`. The size
you choose selects a code path, and one of the sizes the tiers produce has no
code path at all.

#### 2.4.1 The field map

The class's map state is a **contiguous sub-struct starting at `+0xD8`**, and
that is not a guess: the message handler `0x7A8640` is a `__thiscall` on
`this + 0xD8` (`0x7A8647  lea ebx,[ebp-0xD8]`), so every field below appears in
its disassembly as `[ebp + (offset − 0xD8)]`. Offsets are from the **window**
pointer, which is what calling code holds.

| Offset | Kind | Meaning | Measured at |
|---|---|---|---|
| `+0xE0` | byte flags | handler tests bit `8` (surface-transfer path) and bit `2` | `0x7A86B0`, `0x7A8726` |
| **`+0xE4`** | int32 | **`blitSize`** — the square edge of the whole map image. Self-updates via the class `SetArea` override; **Law:** `SetW`/`SetH` **bypass** that override (§2 row, and the "split map" below) | `0x7A7879`, `0x7A8596` |
| **`+0xF0`** | ptr | **display surface** — one-shot `Init` (`vt+0x0C`); destroy-and-recreate, never resize | `0x7A8B57` init site; pattern `0x7A8C18–0x7A8C61` |
| `+0xF4` | ptr | the object the handler **locks** (`vt+0x18`/`vt+0x1C`, mode `0x8040`) and reads dimensions from (`vt+0x88`/`vt+0x8C`) on the transfer path | `0x7A86B8`–`0x7A8710` |
| `+0xFC` | byte | one-shot init latch; also gates the message **subscription** at `0x7A714D` | set at `0x7A8B50` |
| **`+0xFD`** | byte | **re-bake gate** — "the terrain image is stale" | tested `0x7A8718`, cleared `0x7A8604` |
| **`+0xFE`** | byte | **whole-body gate** — clear and the handler does nothing at all | tested `0x7A867D` |
| **`+0x104`** | int32 | **`zoom`** (signed; negative = magnify) | `0x7A852C` |
| **`+0x114`** | ptr | **raster pixel block** — the *source* the bake fills | `0x7A8550` |
| `+0x118` / `+0x11C` | int32 | raster **w** / **h** | `0x7A8547`; read by the clip |
| **`+0x120`** | 16 bytes | **dirty-tile bitmask** | `memset(-1)` `0x7A78E2`; tested `0x7A8165`; `memset(0)` `0x7A8614` |

**Law: `+0x114` IS NOT A COM OBJECT.** It is a plain 3-dword struct
`{pixel ptr, w, h}` — `0x7A7570` treats `ecx` as exactly that (early-out
`0x7A757C`, free `0x5E5620`, `malloc(w*h*4)` `0x5E55E0`, store `0x7A75BB`), and
the bake reads it as a raw base. Passing `this+0x114` to a `QueryInterface`
probe loads the **first pixel of the map** as a vtable pointer and calls
through it — a wild indirect call, and every field such a probe reports is
meaningless. Plain reads only.

**Two rasters, not one.** `+0x114` is the *source* (terrain colours, one dword
per screen pixel of the map) and `+0xF0` is the *destination* the panel blits.
The bake fills the source; a separate transfer (`0x7A66F0` / `0x7A67F0`) moves
it to the surface. Clearing one is not clearing the other: pre-clear the
surface and `0x7A7840` will free+malloc the raster underneath it, after which
the transfer copies **uninitialised heap** over the cleared pixels.

#### 2.4.2 Zoom is DERIVED, and the derivation has a hard constraint

Zoom is never chosen; it is computed from the two sizes:

> **`zoom = −log2(blitSize / terrainDim)`** — negative magnifies, positive
> shrinks. `terrainDim` is the city tile's cell count (64 small / 128 medium /
> 256 large).

The computation is a **shift loop**, not a division (`0x7A7892–0x7A78D5`):
`zoom = 0`; while `dim > blitSize` → `dim >>= 1, zoom++`; while
`dim < blitSize` → `dim <<= 1, zoom--`.

**Law — HARD CONSTRAINT: `blitSize` MUST be an exact power-of-two multiple (or
divisor) of `terrainDim`.** The loop has no exactness test — on an inexact
ratio it stops at the first crossing and every downstream address is computed
from a `zoom` that does not describe the real size. The dest math
(`destY = cellY*16 >> (zoom+4)`, tile side `256 >> (zoom+4)`) then walks off the
end of the raster **in stock code, including the data-cells loop** — which is
the 1.5x (384) and 3x (768) data-view crash, and it exists in stock code with
or without any patch. **Any sizing policy must select only exact multiples.**
`gX8Clips` (§2.4.6) is the alarm that says one leaked.

| tier / instance | `terrainDim` | `blitSize` | `zoom` | stock bake |
|---|---|---|---|---|
| any | 256 | 256 | `0` | 1:1 |
| 2x, large tile | 256 | 512 | `-1` | x2 |
| 2x, medium tile | 128 | 512 | `-2` | x4 |
| **2x, small tile** | **64** | **512** | **`-3`** | **none — see §2.4.6** |
| 1.5x / 3x | 64/128/256 | 384 / 768 | *inexact* | overruns |

#### 2.4.3 The recompute `0x7A7840` MARKS; it does not PAINT

This is the single most useful fact in the section: it is what makes a
jump-on-open symptom look like someone else's bug. `0x7A7840` — the
exact call the class's own init makes at `0x7A8B57` — does, in order:

1. read the terrain object from **`[0xB43CEC]`**; **if null, return** (nothing
   at all happens, not even the dirty marking);
2. `w = vt+0x174()`, `h = vt+0x178()`; **if either ≤ 0, return**;
3. resize the raster: `0x7A7570(this+0x114, blitSize, blitSize)` — a
   **free + malloc**, so the raster is uninitialised heap on exit;
4. derive `zoom` into `+0x104` by the shift loop of §2.4.2;
5. `memset(this+0x120, 0xFF, 0x10)` — **mark every tile dirty**;
6. `[+0xFD] = [+0xFE] = 1`.

> **Law: nothing in that list paints.** The recompute is a *request*. The paint
> happens later, when the game's own message handler notices `+0xFD`.

For stock this distinction is invisible: the map is built before the panel is
ever shown. It becomes visible once a rescale and recreate happen **after**
creation, because the bake then lands a tick or more after the panel is on
screen and the player watches it fill in. **The cure is the standing one — do
the work while HIDDEN** (§7.3 cure 2): call the bake synchronously right
after the recompute (`UiSpike::DriveMiniMapBake`). That is safe and idempotent
because the bake clears the dirty mask and `+0xFD` itself, so the later message
finds nothing to do — no double paint, no fight.

#### 2.4.4 The handler `0x7A8640` — the ONLY caller of the bake

`__thiscall` on `this+0xD8`, registered on the **game's own message server**
(`[0xB43CCC]`, ids `0x99EF1142` / `0x99EF1143`) — **not** the Windows queue,
which is why it still runs during the load tail when posted `WM_APP` messages
starve. Its gate chain, in order:

1. validate the raster struct (`0x7A6590`); on failure **free `+0x114` and null
   it**, then, `+0x114 == 0` → return. The whole pass does nothing.
2. `if (![+0xFE]) return;` — the whole-body gate (`0x7A867D`).
3. read terrain dims from `[0xB43CEC]` (`vt+0x174` / `vt+0x178`).
4. if `+0xF4` is non-null **and** flags bit `8` is set → lock, **transfer**
   raster→surface via `0x7A66F0`, unlock, done — **this path never bakes**.
5. otherwise → `if ([+0xFD]) call 0x7A7FF0` (the bake) at **`0x7A8721`**.

Setting `[+0xFD] = [+0xFE] = 1` by hand is therefore a legitimate way to
request a re-bake without calling the recompute — that is exactly what
`EarlyMinimapBake` does with two byte writes inside `PostCityInit`, the only
kind of write that is safe there (§7.3).

#### 2.4.5 The bake `0x7A7FF0` — one pass per 16x16-cell TILE

`__thiscall` on the window; frame `sub esp,0xC68` (it carries a 16x16-dword
scratch tile). Structure:

1. Read the sampler object from **`[0xB43CF4]`** (a *different* global from the
   recompute's `[0xB43CEC]`); **if null, return immediately** — skipping even
   the mask clear in step 5.
2. `tilesX = vt+0x1C() >> 4`, `tilesY = vt+0x20() >> 4` — i.e. **the terrain is
   walked in 16x16-cell tiles**. A 64-cell tile is 4x4 = **16 tiles**; that is
   why a correct small-city bake logs `blits=16`.
3. Doubly-nested loop, rows then columns. Per tile:
   - **dirty test** `test [this + idx*4 + 0x120], 1<<(tileCol & 31)` where
     `idx = (tileCol >> 5) + tileRow` (`0x7A8150–0x7A816C`). Not dirty → skip to
     the next tile, no work done.
   - gather the tile's 16x16 cell colours into the stack scratch;
   - compute the destination (`0x7A8532–0x7A8556`):
     `destY = (cellY*16) >> (zoom+4)`, `destX = (cellX*16) >> (zoom+4)`,
     `dst = [+0x114] + (destY*[+0x118] + destX)*4`, and
     **`side = 256 >> (zoom+4)`** — note this is **fully general in `zoom`**;
   - **dispatch** to a per-scale blitter through the table at `0x7A8628`
     (§2.4.6);
   - `test ecx,ecx; je` — a null table slot is tolerated and simply skips.
4. Blitter call contract, measured at `0x7A8594–0x7A85AA`, `cdecl`, 6 args,
   `add esp,0x18`:
   `f(dst, dstPitchBytes = blitSize*4, src = 16x16 scratch,
   srcPitchBytes = 0x40, destW = side, destH = side)`.
    **Law: `dstPitchBytes` comes from `blitSize` (`+0xE4`) while the dest offset
    was computed with the raster width (`+0x118`)** — the bake assumes those two
    are equal. Any code that changes one must change the other.
5. Tail (`0x7A8602–0x7A8619`): `[+0xFD] = 0` and `memset(this+0x120, 0, 0x10)`
   — **the bake clears its own dirty state whether or not it drew anything.**
   That is what made the stock zoom `-3` failure *silent*: skip every tile,
   then report done.

The mask index arithmetic (`(tileCol>>5) + tileRow`) implies a
1-dword-per-tile-row stride, i.e. up to 32 dwords for a 256-cell tile, while
both memsets cover only `0x10` bytes = 4 dwords. The measured case is a
64-cell tile (4 tile rows), which bakes all 16 tiles: `blits=16`, `clips=0`.

#### 2.4.6 The dispatch table `0x7A8628` — five blitters, and the hole at zoom −3

Five dwords at `0x7A8628`, indexed by **`zoom + 2`**, each pointing at a 5–7
byte stub in the block at `0x7A856F` that does `mov ecx, <blitter>` and falls
through to the shared call tail at `0x7A8590`:

| index | zoom | stub | blitter | dest tile side | scale |
|---|---|---|---|---|---|
| 0 | `-2` | `0x7A858B` | `0x7A6EE0` | 64 | x4 up |
| 1 | `-1` | `0x7A8584` | `0x7A6E60` | 32 | x2 up |
| 2 | `0` | `0x7A857D` | `0x7A6A70` | 16 | 1:1 |
| 3 | `+1` | `0x7A8576` | `0x7A6AD0` | 8 | /2 |
| 4 | `+2` | `0x7A856F` | `0x7A6BD0` | 4 | /4 |

The bound in front of it is the whole defect:

```
0x7A8560  lea ecx,[edx+2]          ; index = zoom+2
0x7A8563  cmp ecx,4                ; 5 entries
0x7A8566  ja  0x7A85B0             ; UNSIGNED -> zoom -3 = 0xFFFFFFFF -> skip
0x7A8568  jmp [ecx*4+0x7A8628]
```

**Law: `ja` is UNSIGNED, so `zoom = -3` wraps to `0xFFFFFFFF` and every tile is
skipped** — and by §2.4.5 step 5 the bake then clears the dirty mask and
reports success. **Only the dispatch stops at −2**; the surrounding dest math
is general. Stock can never reach −3 (its largest blit 256 over its smallest
terrain 64 is −2), so this is a hole only a resized 512 surface falls into.

**What it looks like on screen, and why nothing downstream can repair it.** The
data-CELL loop (`0x7A882A`, `shl`/`shr` by `zoom+4`) has **no table and no
bound**, so cells keep painting at zoom −3 over a terrain base that was never
drawn. The surface is re-cleared to `0xFF000000` and repainted **every sim-day
tick (~1 Hz)**, and the game **alpha-blends** cells onto whatever base exists at
paint time. So the cells are *born* dark and cannot be un-blended:

> **Law: if a base layer is missing, fix the BASE, never the composite.**
> Three composite-side attempts each fail in their own way: a one-shot seed
> works once and goes black at the next re-clear; a black-hole heal never fires
> at all, because the game's black is `0xFF000000` and not numeric `0`; a
> per-sweep heal from cache produces **wrong colours plus a ~1 Hz flash** —
> unfixable in principle, because the blend has already happened.

**The lever, and where it lives.** `CodePatches::ApplyMiniMapX8Bake` rewrites
those 15 bytes to index **`zoom + 3`** against a **6-entry table inside the
DLL**: entry 0 is a replacement x8 tile blitter, entries 1..5 are the game's
five stub VAs **in their original relative order**. Consequences worth
stating exactly:

- zoom `-2..+2` is **bit-identical** to stock (same stubs, same order);
- zoom `≤ -4` and `≥ +3` keep the stock skip (the `ja` rel8 is **unchanged**, so
  it still lands at `0x7A85B0`);
- the **only** behavioural delta anywhere in the reachable space is zoom `-3`:
  skip → draw.
- **In-memory only** — the exe on disk is never written; nothing is written at
  all below factor 1.01.
- **Blast radius, enumerated:** the bake `0x7A7FF0` has exactly **one** caller
  (`0x7A8721`); the table `0x7A8628` is referenced exactly **once** in `.text`
  (at `0x7A856B` — inside the very instruction being replaced); no branch target
  lands inside the 15-byte window; stubs and blitters are untouched.
- **Guards:** 15 (dispatch) + 33 (stub block) + 20 (table) bytes are verified
  before any write, and a mismatch **declines loudly** and leaves stock
  behaviour (see §8.5's verify-before-write rule). The replacement blitter
  clips against `+0x114`/`+0x118`/`+0x11C` and counts every clip in
  `gX8Clips`; `gX8Blits` is an **EXECUTED** counter (law 47 — installed
  ≠ executed).
- **Offline gate:** `_tests\Test-MiniMapX8Bake.py` asserts all of the above
  against the **stock exe on disk**, read-only, with a positive and a negative
  control. The positive control uses a blitter VA the gate has already proven
  is an `imm32`: the bake itself is reached by `call rel32`, so its address
  never appears as an immediate, and a control that searched for it would be
  blind. *(A gate that cannot see the thing it is looking for is a null, not a
  pass — §0.)*
- **The offline layout model does not own these sites**: they are **control
  flow, not geometry**, classified permanently out of its scope with a reason
  and a falsifier (as `kPopupStyleRetargets` is) and adjudicated by their own
  dedicated gate.

**When the patch declines, the fallback is a SIZE clamp, not a repair:** hold
`blitSize` at `terrainDim * 4` (zoom −2, the bake ceiling) and centre the map.
Correct and stable, but it costs map size, so it is the fallback only. Two
traps it taught: `SetW`/`SetH` bypass the `SetArea` override and leave
`blitSize` at 512 against a 256 surface (stride comb — the "split map"), so
write `blitSize` **directly**; and the `DVPIN` table entry re-doubles the map
every sweep unless the clamp is the single source of truth (law 43, coupled
pair).

**Law: THE FALLBACKS MUST STAND DOWN WHEN THE BAKE IS LIVE.** A dock-seed that
keeps firing on open overwrites a correctly baked 512 terrain with a blurry
128→512 bilinear upscale of the dock minimap — good map, then worse map,
then re-bake, which reads on screen as a jump when the panel opens. The
stand-down condition is `!CodePatches::MiniMapX8Active()`. *Standing law: a
comment is an instrument, and a comment describing a stand-down that was never
wired reads exactly like one describing a stand-down that was.*

**The measured end state** (small tile, 2x):
`x8bake=live blits=16 clips=0`, `fd=0`, and `SEEDED 0 / maint probes 0 /
HEALED 0 / CLAMPED 0 / faults 0` — every workaround dormant. Read those
counters together: `zoom=-3` with `blits` climbing means a real base is being
baked at full size; `zoom=-3` with `blits` **stuck at 0** means the write took
but the path never runs; `clips>0` means the sizing policy leaked an inexact
ratio (§2.4.2).

> **The process fact, recorded because it is the expensive part.** This chain
> cost ~13 builds while it was iterated against on-screen appearance;
> **the disassembly answered it in one pass.** Twice a STOCK CONTROL settled
> ownership in about two minutes with no build at all — first that the black
> map came from the mod, then that the jump on open did too. `METHOD.md`:
> measure, don't infer.

### 2.5 HOOKING RULES — NEVER GUESS A CALLING CONVENTION

Everything in this engine is C++ `__thiscall` virtuals, and **`__thiscall` is
CALLEE-CLEANUP**. A thunk that declares the wrong argument count cleans the
wrong number of stack bytes and unwinds into garbage. There is no partial
failure mode: it is a crash, usually far from the hook.

| Situation | The rule | The crash it prevents |
|---|---|---|
| a `__thiscall` virtual with a **known, zero** arity | `uintptr_t __thiscall Fn(void*)` — a typed thunk is fine. Return `uintptr_t` so **EAX is preserved exactly**; void-returning slots simply have their garbage EAX ignored | — |
| a `__thiscall` virtual with **known** args | write it as **`__fastcall(void* self, void* edx, …)`** — `ecx` maps to `self`, `edx` is ignored, and nothing is cleaned that should not be | `PlotPresent` detoured as `__stdcall` looked for `this` on the stack, left ECX as whatever the caller had, and the original ran against garbage: **ACCESS_VIOLATION at `0x0099C4A1`, ECX = 1** |
| **arity UNKNOWN** | **Law: a `__declspec(naked)` TAIL JMP, and nothing else.** It makes no arity assumption at all: it never returns to you, so it never cleans anything, and `ecx`/`edx`/the argument stack pass through byte-identical. Read what you need off `[esp+N]` without disturbing the frame | the first typed thunk on **slot 20** — declared `__fastcall` with two stack args "inferred from two visible pushes" — died **PRIV_INSTRUCTION at a garbage EIP**, EDX still holding `0x00AC1400` |
| you inferred the arity from a disassembly excerpt | **Law: that is guessing.** Two visible pushes at a call site are not proof of two parameters | both of the above |

**Where you patch matters as much as what you patch:**

- **Law: swap the vtable on the INSTANCE, never the class** — copy the class
  vtable into a private 256-entry array (`cIGZWin` declares 144 virtuals / 147
  slots; concrete classes add their own, so the copy is deliberately oversized),
  point the instance at the copy, and leave the game's `.rdata` untouched. No
  other window of that class is affected.
- **The exceptions are deliberate and permanent.** The two *buffer* classes are
  patched class-wide (`VirtualProtect` + write `kBufClassVt[29]` / `[20]`),
  because the buffer is shared and a per-instance swap cannot reach the repaint
  paths that run outside the hooked Plot. Those are gated *inside* the thunk
  instead (`destIsContainer` / `destIsSubContainer`), so other UI on the same
  buffer class is untouched.
- **Law: CLASS IDENTITY IS NECESSARY, NEVER SUFFICIENT.** The disaster-derived
  surgery installed itself on U-Drive-It's *Earned Cars* strip — same class,
  different layout — and the game died. Gate on the class **and** the owning
  context (§2.1).
- **Law: never call Plot or any draw entry point from a hook.**
  `InvalidateSelfAndParents()` (slot 92) is the only safe repaint primitive
  after a geometry change.

**Install timing is a third, separate trap.** *Installed ≠ executed*: the My
Sims portrait hook was installed and never called. And `ArmDeferred` installs four hooks
at `PostCityInit`, **before any sweep has written `gTierF`**, so anything running
from them pre-sweep sees the compiled default `2.0f` — pre-sweep code must read
`settings.spikeScaleFactor` instead (`src\UiSpike.cpp:160-169`). **A hook that
arms lazily produces a guaranteed null, and nothing in the log says so.**

### 2.6 `GZWinBMP` — the SetImage crop LATCH (byte-verified)

The member map that matters (window-pointer relative; class vtable `0x00ADF6A0`):

| offset | member | evidence |
|---|---|---|
| `+0xA8..0xB4` | window rect L,T,R,B on the `cIGZWin` subobject — the "area" | `DYNAMIC-CONTROLS.md` method notes; same fields `GetW/GetH` return |
| `+0xD8` | interface/flag holder — its own vtable, `hvt[10]` is the flag test; **bit `0x10` = has-imagerect, bit 8 = edge/9-slice** (slice geometry lives in the rect) | `src\UiSpike.cpp` RELATCH helper (grep `"RELATCH"`), same access pattern as BMPRECT/BMPX |
| `+0xDC` | the live image, a `cIGZBuffer*` | same |
| `+0xE8..0xF4` | **the `imagerect` LATCH** — four int32, read as `(0,0,W,H)` when latch-following | `0x9BC447` write; RELATCH reads `r[0..3]` |

**The mechanism.** `cIGZWinBMP::SetImage` (`0x9BC57E`) ends in `0x9BC447`,
which rewrites the live `imagerect` `[win+0xE8]` to
`(0, 0, min(areaW,imgW), min(areaH,imgH))` **from the window's area at that
moment** — i.e. at BIND time. `GZWinBMP::SetArea` (`0x99C837`) never touches
`+0xE8`, and the draw (`0x9BC325`, vt slot 88's Plot family) is
**dst-follows-src off that member**. So a window whose bitmap was bound BEFORE
a resize keeps drawing its pre-resize size until the game happens to call
`SetImage` again. All byte-verified.

**Law — THE LATCH LAW. A latch computed from live geometry is a hidden consumer of
that geometry.** Any value derived from a window's size at bind time
(SetImage's crop; the mayor-rating arrow anchors at `[ctl+0x378]`) silently keeps the
pre-resize world — resizing the window does not resize what was derived from
it. When a widget draws at its old size after the sweep, **ask WHEN its content
was BOUND, not what its geometry is now**: a geometry probe reads correct
(`DRAWPROBE` does — `153x17`, exactly proportional) while the latch stays
stale, which is exactly how an attribution goes wrong.

**The measured victim — the city-HUD Mayor Rating groove `0x8A517556`, and its
fill mechanism.** The fill is not a crop of the sheet: the rating handler
`sub_7E8510` **COMPOSES a bitmap per rating tick** — one filmstrip row of
`{46a006b0,14015549}`, `row = artH*(rating+100)/200`, replicated to every row —
and pushes it via `SetImage` on EVERY firing, even delta=0. The handler's first
bind lands **0.3–1.8 s before the city sweep in every one of 61 measured
sessions, at every tier**, so the crop latches at `102x11`; the sweep enlarges
the window, the latch stays; the next sim rating tick (~once per sim month of
running time) re-runs `SetImage` and heals it. Hence *a playing session looks
right and a paused inspection looks broken at every tier* — 1.5x draws
102x11 in 153x17, and 2x's "half bar" is the same latch at 102/204. **There is
no tier split; both "works" and "broken" are true observations of tick
timing.**

**Warning: the three `imul ...,7` sites are ARROWS ONLY** (`0x7E87B1`/`0x7E89D7`/
`0x7E8A02`: the `SetW(delta*7)` reveal and the `GZWinMoveTo(base+(3−delta)*7)`
reposition — §8.4). **No pixel constant exists in the fill chain**, and
the latch is the only wrong number. The 7 is not the art's segment pitch
either: decoding the sheet gives a tick pitch at row 5 of `14015549` of **4px**
(boundary-gap histogram alternates 1,3).

**THE CURE — RELATCH** (`ScaleSubtree`'s resize site; `src\UiSpike.cpp`,
grep `"RELATCH"`). When a resized window is
class-`0x00ADF6A0` with flag `0x10`, not edge/9-slice (bit 8), holds a live
image, and its crop reads EXACTLY `(0,0,oldW,oldH)` — the latch's own
signature — rewrite it to `(0,0,min(newW,imgW),min(newH,imgH))`, mirroring
`0x9BC447`'s clamp verbatim. Keyed on the derived condition, not an id list
(law 94); deliberately tier-general (the latch fires at 2x/3x too); idempotent
under sweep-first ordering (a staged crop ≠ old area → no fire). Log:
`RELATCH id=...`. Measured end state: one controller firing pre-sweep, one
RELATCH line, bar full from first paint with the sim paused.

**Warning: the guard is armed PER PANEL ROOT, never blanket, and the reasons are
load-bearing** (scope note at the helper):
`crop == (0,0,oldW,oldH)` alone is NOT unique to the latch — **577 of 877
authored `.UI` imagerects are full-area-at-origin, and 34 of those are the
top-left cell of a larger sheet**; expanding such a crop drags neighbour art
into the window. The discriminator is the ROOT: under the
`kAlwaysScaleCityIds` roots every staged script pre-scales its crops, so an
authored crop there can never equal the OLD (1x) area — only a SetImage latch
can (`gRelatchArmed`, set around `ScalePanelRoot`). That scoping also keeps it
out of the `kCityDialogIds` pass, where BMPRECT multiplies crops AFTER
`ScaleSubtree` — the two rewrites composing would double-scale. Known-inert:
BMPX-hooked instances carry a swapped vtable and fail the class test (served by
BMPX's dst-stretch). Bounded case: a game-shrunk-then-tombstoned window
overdraws until its next SetImage — no such window lives under the armed
roots.

**Coverage note:** the polls panel's small rating meter (panel-init fn
`0x7ED224`) binds the SAME `14015549` sheet through the GZWinBMP family, so
RELATCH covers it automatically (class+signature keyed); its position latch
(`[ctl+0x378/0x37C]`, re-asserted by `GZWinMoveTo` at `0x7E883B` every refresh)
is RATEANCHOR mode 2. The six City Opinion Polls bars are `cSC4WinTrendBar`
and **IMMUNE** — see the §2 catalogue row. Art-side companion: at
fractional tiers the `14015549` ladder filmstrip is re-laid by
`tools\upscale\redraw_ladder.py`, an unconditional post-step of the corpus
rebuild that self-guards at integer factors, and the colour-key gate imports
that module's ladder list rather than restating it.

### 2.7 `GZWinBtn` — state-cell art is SOURCE-sized, not window-stretched (byte-verified)

Answers register item #1 / OPEN QUESTION O1 (`UI-ART-BINDING.md §3` published the
horizontal rule `imageWidth/N` and left the vertical axis unsettled — the
corpus alone cannot distinguish the two hypotheses because in all 875 measured
buttons `pngHeight == buttonHeight` by construction, so window-derived and
source-derived height predict the identical pixel result).

**Member map** (class vt `0x00ADDAF0`; `[this+4]` is the `cIGZWin` subobject,
so field offsets below are relative to the outer `GZWinBtn`, and the
window's own geometry is reached through `[this+4]`'s vtable):

| offset | field | role |
|---|---|---|
| `+0xf4,+0xf6` | int16 x,y | state-cell's position, LOCAL to the window (`(x,y)` of a `(x,y,w,h)`-form rect) |
| `+0xf8,+0xfa` | int16 w,h | state-cell's **size** — the value this item settles |
| `+0x108` | ptr | the resolved image/state-provider interface (lazy-QI'd, IIDs `0x68963c54`/`0x68963c4c` as fallbacks) |
| `+0xdc` bit `0x04` | flag | "has image" gate on the whole draw |
| `+0xdc` bit `0x40` | flag | selects the alternate (`GetW()`-driven) sizing branch below — **never set** by the constructor (`0x9B1C27`, zeros `+0xdc` then ORs only `0x6a0`) or by any of the class's own `SetFlag(mask,bool)` call sites (`sub_9B13DD`); exhaustive scan of the class's ~5,600-byte code block (`0x9AE000-0x9B2E20`) found no `push`ed mask with bit `0x40` set anywhere |

**Plot** (slot 88, `0x9B167D`) dispatches to the icon draw `0x9B1541`, which
builds the destination rect as:
`destLeft = winAbsX([this+0x28]) + F4 + pressedOffset`,
`destTop = winAbsY([this+0x2c]) + F6 + pressedOffset`,
`destRight = destLeft + F8`, `destBottom = destTop + FA`
(`0x9B15C5-0x9B15EA`) — i.e. **position tracks the window's absolute screen
origin, but size is whatever `F8`/`FA` currently hold.** The window's own
`GetH()` (vt `+0xA8`) is never read on this path.

**`F8`/`FA` are written in exactly one place, `sub_9B09B7`**, called from the
class's `SetArea` override (`0x9B1397 → 0x9B0C08 → 0x9B09B7`) — so they
refresh on every resize, but WHAT they are refreshed FROM is the question.
With flag bit `0x40` clear (the constructor default, and — per the exhaustive
scan above — the only value ever observed), `sub_9B09B7` takes the branch at
`0x9B0B34`:

```
call [image_iface + 0xbc](&rectOut, state_a, state_b)   ; state_a/state_b from
                                                          ; the button's own
                                                          ; state tracker, [this+0x54]
F8 = rectOut.right  - rectOut.left     ; 0x9B0B56-0x9B0B5C
FA = rectOut.bottom - rectOut.top      ; 0x9B0B63-0x9B0B69
```

`rectOut` is the image interface's own per-state rect — the SOURCE cell's
native pixel geometry for the currently-selected button state — with no
window dimension as an input. **The vertical rule mirrors the horizontal
one: both axes of the drawn state cell are sized off the ART, never off the
window rect.** A resize moves the icon (position follows `winAbsX/Y`) but
never stretches or squeezes it; art whose per-state cell height does not
match the button's window height will overflow or leave a gap rather than
scale to fit.

(The bit-`0x40` branch, `0x9B0A49-0x9B0B32`, computes `FA` from `GetW()` of
the window combined with an image-interface state-count call — evidence it
exists for some non-standard button configuration — but no code path in the
class's own attribute handling was found to ever set the bit, so it is not
exercised by any `.UI`-authored button found so far. Flagged, not chased
further: finding its trigger would need either a live `SetFlag(0x40,...)`
capture across a full game session, or a corpus-wide diff of every shipped
`GZWinBtn` node's `+0xdc` at runtime — an instrument beyond a static read.)

**Consequence for #177** (the `CellUnit`-snapped strip height, currently
protected by a 44-entry hand-maintained exception list): the engine performs
no vertical divide for `GZWinBtn` state art at all — height is copied
whole from the source rect, never divided by a state count the way width is.
A snap rule that treats strip height as needing the same `/N` treatment as
width is solving a problem the engine's own draw path does not have for this
class; re-derive `--height-exact-strips` against `cell-strips.txt` per the
corpus test in `research/UNKNOWNS-AND-NEXT-TARGETS.md` B.2 before trusting
the hand list further.

---

## 3. The `.UI` script format

### 3.1 Storage and census

`.UI` layout scripts are **DBPF TypeID `0x00000000`** and live **only in
`SimCity_1.dat`** (SimCity_2..5 and EP1 hold zero of them, and zero UI PNGs).
330 entries, all QFS/RefPack-compressed except 42.

| Group | Count | Content |
|---|---|---|
| `0x96A006B0` | 271 | the default layouts (all screens) |
| `0x08000600` | 10 | **800x600 layout overrides** — the group id literally encodes the resolution (0800 x 0600). Same instance ids, same window ids, different pixel geometry |
| `0x8A5971C5` | 48 | 44 binary animation-bank blobs + 4 INI-style configs — **not layouts** (the community-cited "UI group" is a red herring under type 0) |
| `0x4A87BFE8` | 1 | the font-style config table |

So the layout corpus proper is **281 text files**.

**`0x08000600` is the engine's own per-resolution override mechanism** — proof
that "another size = another copy of the numbers", not runtime layout. Any
audit keyed only on `G-96A006B0` misses the twins, and a window existing in
both groups references the same art from both.

### ⭐ The per-resolution GID is COMPUTED — arbitrary resolutions are first-class

`0x08000600` is not a special case in a table; it is **one value of a formula the
loader evaluates on every script load** (register #11, closed 2026-08-24;
independently byte-verified). The `.UI` loader service — clsid `0x5A356E15`,
iface `0xFA3562FA`, impl vtable `.rdata 0xAD5158`, QI `0x94B120`, ctor
`0x94B400` — centralizes selection in **vt+0x10 = `0x94B210`**, which every one
of the 75 hard-coded-`0x96A006B0` call sites reaches through the two thunk shapes
of the `sub_5F9480` family (vt+0x0C = `0x94B08B` forwards to vt+0x10; the 3-arg
thunk at ~`0x5F9390` calls it directly).

| step | VA | what happens |
|---|---|---|
| copy caller TGI to locals | `0x94B220-33` | the caller's group is preserved for fallback |
| get `cIGZPersistResourceManager` | `0x94B236` | helper `0x4496C0` (iface `0x656B8EFC`, clsid `0x056B906E`). **Absent ⇒ substitution skipped entirely** |
| get `cIGZWinMgr` → `GetMainWindow` | `0x94B244` | `sub_4177C0`, then vt+0x0C |
| read **main-window** W / H | `0x94B25F` / `0x94B26C` | `GetW` vt+0xA4, `GetH` vt+0xA8 — the *window*, not the desktop |
| format | `0x94B279` → `0x94B27F` | `sprintf(buf, "0x%.4u%.4u", W, H)`; format string `.rdata 0xAD50AC`, W pushed second so W is the first field |
| parse | `0x94B288` | `0x90FCEF`, a whitespace-skipping `0x`-aware hex atoi |
| write into the **GROUP** slot | `0x94B296` | the instance and type are untouched |
| probe | `0x94B29C` | `resMan->TestForKey(&localTGI)` (vt+0x38) — **on miss, the caller's group is restored** |

**`%.4u` is decimal with a 4-digit minimum, and the result is then read back as
hex** — so the rule is literally *decimal digits re-interpreted as hex nibbles*:
800×600 → `"0x08000600"` → `0x08000600`, which is exactly the stock override
group. That known data point falling out of the derived formula is the built-in
positive control.

Two consequences worth stating plainly:

1. **Per-resolution `.UI` scripts are shippable with zero runtime rewriting.** A
   dat carrying scripts under `0x24001600` is picked up automatically at
   2400×1600 and ignored everywhere else. This is a genuine architectural
   alternative to tier packages + runtime scaling — *not* a defect, and not
   pursued here; it is recorded so the choice is informed.
2. **The fallback is per-instance and silent.** A resolution-specific script that
   is missing, or misfiled by one digit, degrades to the default layout with no
   log line and no error — so a partial per-resolution set is a debugging trap,
   not a crash.

Format: `# Generated by UI editor` header, then pseudo-XML `<LEGACY …>`
records — usually one per line, but a quoted value may contain raw newlines
(107 of 5,964 elements span multiple physical lines), nested via
`<CHILDREN>…</CHILDREN>`. **Legacy markup, not
XML** — unquoted attributes, tags closed by a bare `>`, `#` comments; needs a
lenient parser, and `.UI` is NOT line-oriented (`SDK-GAPS.md` §5 for the full
lexical contract). Annotated real example (`I-0a55161d`, the quit dialog):

```
<LEGACY clsid=GZWinGen iid=IGZWinGen id=0xaa921f4f      <- window id
        area=(332,232,662,389)                          <- CORNERS, absolute (root)
        image={46a006b0,144161e4}                       <- {group,instance}; type implied
        blttype=edge  gutters=(64,64)  winflag_visible=yes ... >
<CHILDREN>
   <LEGACY clsid=GZWinBtn ... id=0x8a921f5b
           area=(7,4,307,34)                            <- 300x30, PARENT-relative
           caption="Save and Quit" captionres={0a554ae8,ca6cd434}
           image={46a006b0,144161eb}                    <- 120x30 = four 30x30 states
           font=GenButton gutters=(0,0,0,0) >
</CHILDREN>
```

Attribute frequency across the 281 files: every control has `clsid`, `area`,
`fillcolor`, and **13** `winflag_*` (11 universal — `visible`, `enabled`,
`moveable`, `sizeable`, `sortable`, `pbuff`, `pbufftrans`, `pbufferase`,
`pbuffvid`, `mousetrans`, `ignoremouse` — plus near-universal `acceptfocus`
and `alphablend`); then `gutters` 4520, `image` 2962, `edgeimage`
844, `imagerect` 839, `blttype` 540, plus `caption`/`captionres`, `font`,
`tiptext`/`tipres`, `textoffsets`, `tipoffsets`. **There is no
inset/edges/corners/slice attribute anywhere in the corpus.**

#### 3.0a `gutters` / `textoffsets` / `tipoffsets` — consumers PINNED

Traced tokenizer → per-class deserializer → iface slot → setter → field → every
reader (register #13, closed 2026-08-24). **`gutters=` is per-class in both width
and meaning** — the same attribute name is three different field shapes, which is
why one general rule never fit it:

| class | field | shape | consumer, and what it means there |
|---|---|---|---|
| `GZWinText` | `+0xE4`/`+0xE5` | **signed** byte pair | caption re-layout `0x9C1E6D`, as a symmetric inset. **Center-align ignores gutterY.** Ctor default (2,2), but the deserializer **force-writes (0,0) when the attribute is absent** — so "no `gutters=`" is not "ctor default" |
| `GZWinBtn` | `+0x102` L, `+0x103` T, `+0x104` R, `+0x105` B | **four unsigned** bytes, ctor-zeroed ⇒ default (0,0,0,0) | the **recompute routine `0x9B0C08`** (10 rel32 callers; gate `[this+0xDC]&4` @`0x9B0D76`) builds the content box `[gL, gT, W−gR, H−gB]` @`0x9B0D76-0x9B0DC7` and passes it to seat helper `0x9B0B87`. Further readers inside the same routine: `0x9B0D14`, `0x9B0E83/93`, `0x9B0F67/74/7E/87`. Getters: `vt+0x80` = `0x9B008D` (L/T only), `vt+0x7C` = `0x9B0116` (all four). The 2-value form duplicates symmetrically; **other arities are silently dropped** |
| `GZWinTextEdit` | `+0x158`/`+0x15C` | **dword** pair | the text draw origin and visible width. Ctor default (5,0) — `0x9BFFCC` is `mov dword [esi+0x158], 5`, which is the long-cited "gutter default 5" now with a field behind it |

Ten classes consume `gutters=` in total (10 deserializer sites, matching 10
serializer sites — the round-trip is the completeness control).

**`tipoffsets=` is GZWinBtn-only and inert on stock art.** It is an int16 pair at
`+0x178`/`+0x17A` with exactly one consumer: `SubmitTip 0x9B1AC0` uses it as the
tip **anchor point** (converted local→screen via win `vt+0xF0`, posted to the tip
manager as message `0x22C010D0`) — **but only when bit `0x10000` of `+0x174` is
set.** `+0x174` comes from the `tipflag=` attribute (token `0xA18`), whose default
`0x1000000` leaves that bit **clear**. So every stock `tipoffsets=` in the corpus
is dead data unless its control also opts in via `tipflag=`. ⚠ The community
wiki's `tipsoffset` spelling does not exist in the exe.

#### 3.1a `winflag_*` name → runtime BIT, PINNED

The base keyword table (`0x0094D641`–`0x0094E33A`) gives each name a
sequential **parse-time token id**, `0xF01A`..`0xF026` (only `visible`
=`0xF01A` and the two late-registered `acceptfocus`=`0xF025` /
`alphablend`=`0xF026` are individually confirmed; the middle nine follow the
corpus listing order above but were not re-disassembled one by one). **That
token id is not the runtime flag.** The bit each name actually sets/clears in
the live `[this+0xC8]` flags dword — tested through `GetFlag`/`SetFlag`, real
slots `vt+0x10C`/`vt+0x110` (§1.4, §2.2) — is:

| `.UI` name | runtime bit | evidence |
|---|---|---|
| `winflag_visible` | `0x1` | `IsVisible()` (`vt+0x11C`, `0x0099BDCE`) IS `GetFlag(1)`; `PlotComposite`'s visibility gate tests `flags & 1` |
| `winflag_enabled` | `0x2` | `IsEnabled()` (`vt+0x120`, `0x0099BDD9`) IS `GetFlag(2)` |
| `winflag_moveable` | `0x100` | ctors `0x0099DA15`/`0x0099DB3C` write `[this+0xC8]=0x8903` at birth — bit decomposition below |
| `winflag_sizeable` | `0x200` | not independently disassembled — see caveat |
| `winflag_sortable` | `0x800` | same `0x8903` ctor decomposition; qualitatively corroborated — `winflag_sortable=yes` on only 27/5,964 corpus nodes (`SDK-GAPS.md` §4) |
| `winflag_pbuff` | `0x10000` | `PlotComposite`'s dirty path drives its draw-context alpha/buffer state off `GetFlag(0x10000 PrivateBuffer)` |
| `winflag_pbufftrans` | `0x20000` | same dirty path: private-buffer erase is gated on `flags & 0x20000` |
| `winflag_pbufferase` | `0x40000` | same test, paired: `flags & 0x40000` |
| `winflag_pbuffvid` | `0x100000` | not independently disassembled — see caveat |
| `winflag_mousetrans` | `0x80000` | base `IsPointInMe` (`0x0099C97C`) tests `GetFlag(0x80000)` to select the refined hit-test mask (§2.2 item 2) |
| `winflag_ignoremouse` | `0x200000` | hit-test router (`0x0099DFA9`) skips a child on `GetFlag(0x200000)` (§2.2 item 1) |
| `winflag_acceptfocus` | `0x8000` | same `0x8903` ctor decomposition |
| `winflag_alphablend` | `0x4` | same dirty path: `GetFlag(4 AlphaBlend)` drives the draw-context alpha state |

> **EVIDENCE (MEASURED).** `0x8903` = `1000 1001 0000 0011`b = bits
> {0,1,8,11,15} = `0x1 | 0x2 | 0x100 | 0x800 | 0x8000` — Visible, Enabled,
> **Moveable, Sortable, AcceptFocus**, exactly the "every window is BORN
> visible" ctor constant already used in §7.2/§1.4
> (`tools\research\_checkpoints\uimap-stage3-emu.md` "SECOND FOLLOW-UP", and
> independently in `tools\research\_incoming\subsystems-02.md` §2.4's field
> table, both against ctors `0x0099DA15`/`0x0099DB3C`). `GetFlag(1)` /
> `GetFlag(2)` are the disassembled bodies of `IsVisible`/`IsEnabled`
> (`tools\research\regionmap\slice-2.md` §0.1 cGZWin vtable map; also
> `SDK-GAPS.md` line 42). `GetFlag(4 AlphaBlend)`, `GetFlag(0x10000
> PrivateBuffer)`, and the raw `flags & 0x20000` / `flags & 0x40000` tests
> are read directly off `PlotComposite`'s disassembly (`0x0099E62D`,
> `subsystems-02.md` §2.4.2 step 4). `GetFlag(0x80000 MouseTrans)` is in base
> `IsPointInMe` (`0x0099C97C`; `subsystems-01.md` line 100/226, folded into
> §2.2 item 2 above). `GetFlag(0x200000 IgnoreMouse)` is in the hit-test
> router (`0x0099DFA9`, §2.2 item 1; `SDK-GAPS.md` §2 lines 102–103).

**⚠ Two names are not independently confirmed in this repo:
`winflag_sizeable` (`0x200`) and `winflag_pbuffvid` (`0x100000`).** Both come
only from the community `cIGZWin.h` `tWinFlag` enum
(`vendor\gzcom-dll\gzcom-dll\include\cIGZWin.h`), which is otherwise a
**perfect match** against every one of the 11 bits actually measured above —
plus two more of its entries that aren't `.UI` keywords at all,
`WinFlag_UseFade=0x20` (tested in `PlotComposite`'s own visibility gate) and
`WinFlag_DelayedPlot=0x8000000` (the invalidation-walk wall, §2.4.1 lineage).
13 of 15 header bits now have a disassembled test site; that is strong
circumstantial support for the last two, not a measured one. Closing it
outright needs a live `GetFlag(0x200)` / `GetFlag(0x100000)` capture, or the
disassembly of whichever setter creates a `PrivateBufferVid` window.

**Token id ≠ runtime bit — a third `.UI` generator cannot rely on the
former.** The deserializer stores an *interned token id* in each
`[tokenId][value]` record; only the per-class handler (not the tokenizer)
decides which flag bit that record's value actually sets. Reordering the
keyword-registration table would renumber the parse-time ids without moving
a single runtime bit.

### 3.2 `area=` is CORNER form, absolute for roots, parent-relative for children

`area=(x1,y1,x2,y2)` = left,top,right,bottom — **not** (x,y,w,h) as the
community wiki table claims. Proven by button rows: consecutive buttons at
`(68,28,115,65)`, `(68,78,115,115)`, `(68,128,115,165)` = 47x37 buttons on a
50px pitch, and 47 matches the 4-state cell math. Everything geometric is
**absolute pixels**: no percentages, no anchors, no layout managers, and font
sizes never appear in scripts (only named styles).

**Therefore a window the engine (re)creates comes back at script-declared 1x
size.** That single sentence is the root of the timing model in §7.

### 3.3 `imagerect=` is a SOURCE crop, in bitmap pixels, corner form

Corner-format proof: the HUD background `14015545` is 878x182 and a child at
`area=(122,111,254,130)` uses `imagerect=(122,111,878,182)` — as (x,y,w,h)
that would read 878px starting at x=122 of an 878px image, impossible; as
corners it is exactly "the same region of the big sheet, clipped by the
window".

**Law: never double an `imagerect` without doubling its art, and never double art
without doubling the `imagerect`.** 839 crops exist in absolute source pixels;
they are the real blanket-2x breaker (slice insets are not in scripts at all —
§4.4). Four patterns matter:

1. **Big-sheet cropping** — one large PNG per screen (HUD `14015545` 878x182;
   tool column `14015546` 157x489) drawn 1:1 by the root BMP, then child BMPs
   re-crop regions of the *same* image to layer text backgrounds.
2. **Multi-state sheets** — mayor-rating bar `14015549` is 102x26 and
   `imagerect=(0,0,102,11)` picks the first 11px state. Note: on the
   HUD groove `0x8A517556` that **staged crop is DEAD DATA at runtime** — the
   first `SetImage` from the rating handler overwrites `[win+0xE8]` with its
   own window-derived latch (§2.6), so editing this script's `imagerect` moves
   nothing on screen there.
3. **Pixel-registered collages** — in `I-c973b411` the 235x222 region
   background `{46a006b0,13d14ca0}` is painted by several BMPs whose
   `imagerect` l,t **equals their own area l,t**: bitmap pixels map 1:1 onto
   window pixels. Strictly native-size; breaks under 2x art unless every
   consumer scales too.
4. **9-slice / edge-blt** — `edgeimage=yes` (56 of 844) with an `imagerect`
   source rect edge-blitted into arbitrary window sizes.

`blttype=` tally **in the 330-script STOCK corpus**: `edge` 277, `tiled` 254,
`normal` 9. Note: that last number is why this section reads as a curiosity and
should not: across the 11 third-party scripts in
`tools\dialog-static\thirdparty-src\` the tally is `edge` 17, `tiled` 1,
**`normal` 31** — more `normal` blits in 11 mod scripts than in all 330 of
Maxis's. CAM builds its dialogs almost entirely out of them. **A count taken
over the stock corpus describes Maxis's habits, not the game's behaviour**, and
mod data is where the rare paths live.

#### THE RULE IS BROKEN BY A CODE PATH THAT NEVER ASKS THE QUESTION

Scaling a mod dialog's windows and its bitmaps while leaving all 24 of its
`imagerect` crops at 1× makes each row stripe paint 285px of a 428px
window. Knowing the rule is not enough:

`build_dialog_static.py` scales an `imagerect` only when the control's art was
scaled, and it decides that from `art_plan` — which is computed from the
**stock upscale store alone**. Art the MOD supplies is therefore *always*
classified `left1x` there, however thoroughly it is scaled elsewhere. The
builder is not disobeying the rule; it cannot see that the rule applies.

**So the durable form of the rule is about the three numbers, not two:**

> A blit has a SOURCE (bitmap), a CROP (`imagerect`), and a DESTINATION
> (window). Scaling any two of them is not a partial fix, it is a new defect.

And when you check one, check whether your test for "did the art scale?" can
actually see every supplier of art.

### 3.4 The `font=` GUID-vs-name rule

**The `GZWinText` deserializer at VA `0x94E516`** (registered `0x951D29`)
handles `font=` two ways:

- **token value (type 6, i.e. GUID-valued)** → `SetFontStyleByGUID`
  (iface `+0x4C` = `0x9C16FD`, stores at `this+0xE0`, resolves via
  `GetStyleByGUID` = font-system `vt+0x14`, fallback GUID `0x68963C4C`
  "Default") — **works**;
- **raw string (type `0x800E`)** → stored into the generic property map as
  property `0xFAA4AE85` (main `vt+0x1C8` = `0x99D7C8`) with **no font side
  effect and NO CONSUMER ANYWHERE IN THE IMAGE** (zero xrefs to `0xFAA4AE85`
  and to its inverse `0x055C417B`) — **silently dead**.

The font system exposes `+0x98 GetStyleFromName`, and *other* control
deserializers call it (`0x94CF0A`, `0x94F9E4`, `0x950657`, `0x950C94`,
`0x959491`) — **`GZWinText`'s handler does not.** None of the 88 style names
exists as a string in the exe, so name resolution can only go through the
ini-fed dictionary.

**Law — practical rule: in any shipped `.UI`, convert every `font=NAME` to
`font=0x........`.** The round-trip serializer at `0x95BC5F` writes
`font=0x%08x` for styles without a resolvable name, so the parser accepts the
hex form by construction. Both builders do this for every edited script (437
tokens across 23 scripts in the shipped dat).

The exact tokenizer step that makes *some* names resolve
(`DataInsetHeader` works; `RegionLabel`, `RegionPopulation`, `Mayor*`,
`PUckDate` do not) is `SDK-GAPS.md` G10. The tokenizer dictionary is fully
enumerated (391 keywords, six registration tables) and contains **zero**
FontStyle style names, so no style name can resolve through the token path;
the `<LEGACY>` tag handler is not the route either — `0x94B995` is the tag's
*registration* site, not a handler. None of that matters operationally,
because the GUID form bypasses the whole question. Note also
that `font=4888` / `font=0x00001318` are the loader's own token for the
keyword `default` (registration `0x00955823`); no FontStyle GUID `0x1318`
exists, so both spellings land on the fallback `0x68963C4C` "Default".

### 3.5 `winflag_visible`, and why a hidden window still matters

A hidden window is still a real window with real geometry, and four separate
mechanisms depend on that:

- **The sweep's visibility gate skips it** → it stays 1x until something shows
  it → that IS the mode-transition flash (§7.2).
- **`vis=0` does not mean "not drawing".** `0x69E40A1F` reports `vis=0` in god
  mode **while its children still draw**, so the visibility gate skipped it and
  only its twin `0xC991EDA8` scaled — the "duplicate sun / 1x rail" report. The
  disaster flyout's root is `vis=0` *always*, so gating its dock on
  `IsVisible()` silently skipped the dock entirely (0 log lines).
- **`vis=1` inside a hidden parent is not on screen.** Naive counting reported
  369 false hits until an **effective** visibility filter was added.
- **A mod's DLL may use visibility as its own state.** CoriBoom's script marks
  all 36 style rows `winflag_visible=yes` and its DLL **hides** the ones with
  no style assigned — so "only 4 rows show" is correct behaviour, not a bug.

### 3.6 Multiple top-level roots per script, and marker-composed panels

**One script file routinely holds several top-level roots**, and they compose
on screen via `0x0000AAAA` markers rather than parent/child nesting:

- `I-2bc90671` — root 1 = composite HUD `0xE9889775`, root 2 = the left tool
  column `0x69E40A1F`.
- `I-c973b411` — root 1 = the minimap dock `0x0987B48F`, root 2 = the
  mode-transition overlay `0xEA8CAD14`.
- `I-6bc9065a` / `I-ea2871aa` — **three** roots; `0x8A8B5B72` was the one
  nobody listed, so the sweep doubled its frame over wholly 1x art (the broken
  Graphs panel).
- **`I-aa1f1f57` (My Sims) has NINE**: `0x698894D3`, `0xCA1F1D9C`,
  `0xAA1F1EC5`, `0xEA1F1E4D`, `0x6A61E29F`, `0xABBAA2D3`, `0xEA1F1E4E`,
  `0xEA1F1E5E`, `0xABB26B0E` (+ the catalog/detail pairing).

**Law: deferral must cover the whole composition or none of it.** With My Sims'
outer root in `kNeverScaleIds` the sweep still scales sibling `0xCA1F1D9C`
(log `(149,1413 861x134) -> (298,1226 1722x268)`) and the marker-glued pair
tears apart (scattered title, detached slots) — *and* three family arts are
already 2x-in-place because they are shared with swept Sim-mode panels, so
pure-1x is not reachable either. **A deferred window in a scaled ecosystem does not
stay stock: its siblings and its shared art move on without it.**

Operational corollary: **when several scripts share a root id, identify the
LIVE one by rect-matching against a runtime dump.** The Data Views panel exists
as three copies of root `0xAA32BCE6` (`I-2bc9060f`, `I-ea287193`,
`I-0b72f276`); all seven probe rects match only `I-2bc9060f`, the other two are
stale dev copies offset ~34px. (Same trick earlier separated live
`I-2bc90671` from stale `I-898897de` and live `I-4bc906b5` from
`I-0a5fa5d6` — by scanning the exe for the instance id: 1 hit vs 0.) Mark all
copies scaled anyway so shared-art refs stay consistent.

---

## 4. Art binding — the four paths a pixel takes to the screen

The store: **2,280 PNGs** (type `0x856DDBAC`) in `SimCity_1.dat` across 10
groups — `46a006b0` 810, `1abe787d` 743, `6a386d26` 356, `4c06f888` 112,
`ab7e5421` 93, `00000001` 62, `ca133ecb` 41, `22dec92d` 39, `6a1eed2c` 20,
`a9179251` 4. Only **431** distinct `{gid,iid}` pairs are referenced from `.UI`
text. **The other ~1,850 are bound some other way** — that gap is the whole
reason a blanket 2x replacement is unsafe. Reference counts differ by
denominator — distinct `{gid,iid}` pairs against distinct instances, and 330
type-0 entries against 286 text files against the 281-file layout corpus —
so always state which is meant.

**Law: art groups `0x46A006B0` and `0x1ABE787D` are twins — and the twin
structure is exact, with a third twin.** `0x1ABE787D` is a **strict subset**
of `0x46A006B0`: all 743 of its instances also exist under `46A006B0` (which
has 810). **Group `0x00000001` is a third twin**: all 62 of its members exist
under BOTH. Overriding one without the others produces mixed-scale UI —
covering a shared instance can mean covering three TGIs.

### 4.1 Path 1 — `.UI`-referenced TGI

`image={gid,iid}`, 2,962 occurrences, type `0x856DDBAC` implied; a ref's GID is
honoured for five of the six ref GIDs (refs to `46a006b0`, `1abe787d`,
`22dec92d`, `4c06f888` all resolve under those exact groups), **which is what
makes selective retargeting possible**. The one shipped counter-example is
`{82b9b75b,e2b66db8}` (`I-cb40cfdc`, the Apply/Remove Label buttons): group
`0x82B9B75B` exists in no archive while the instance is a real strip under
`0x46A006B0` (`SDK-GAPS.md` G11). No
`thumbimage`/`containerimage`/`backimage` is in use.

**Fixable at:** the art layer (`build_selective_safe.py`) — plus the
`imagerect` on the same control.

### 4.2 Path 2 — code-bound TGI constants in `.text`

The exe assembles a TGI from immediates and loads it (`call 0x602B00` or
`[edx+0x94]`), with **zero `.UI` refs**, so no reference scan can see it.
Confirmed instances:

| Art | Code site | Consumer |
|---|---|---|
| `{46A006B0,14015580}` groove, `{…,14015584}` fill | `0x7ED4AC` | cSC4WinTrendBar via `SetImages` |
| `{46A006B0,14315E60/62}` mayor faces | `0x7E8AF4` / `0x7E8B0A` | mayor-rating widget |
| `{46A006B0,14416244}` playlist checkbox strip (128x16 = 8×16x16) | `0x4F4B78` / `0x4F4E37` (explicit group immediate; the `1ABE787D` twin is *not* loaded by this path) | Audio Options grid |
| `{46A006B0,53244588}` restore-toolbars icon | code-created button, `0x602B00` | dock controller |
| `{46A006B0,094AC89A}` U-Drive-It mission bubble + a 15-entry glyph table | pushed beside the window id at `0x4B8314` / `0x7AC651`; table `0x44DEC7–0x44E268` | in-world bubble `0x48E945B4` |
| `0x140155B4..F7` span (news pages, advisor panels) | `0x77A495–0x77A837`, `0x780952–0x78910C` | news window + advisor panels |
| **ItemIcons** — `{0x856DDBAC, 0x6A386D26, <Item Icon>}` | property `0x8A2602B8` read at `0x78EDC9`; **type and group are exe constants** stamped at `0x78EE09`/`0x78EE11`; two more sites `0x7ECB1E`/`0x7ECB44`/`0x7ECB4C` and `0x7F0359`/`0x7F038F`/`0x7F0597`; alt-icon property `0xABE1AF70` when a `0x144161EC` test holds | exemplar-driven menu items (see 4.3) |

**Fixable at:** the art layer, 2x **in place at the original TGI** (no clone —
code-bound art has no `.UI` rect to retarget), and only after the safety
classifier clears it (§4.5).

### 4.3 Path 2b — exemplar-bound (the ItemIcon system)

Exemplars are type `0x6534284A` (cohorts `0x05342861`), **SimCity_1.dat only**
(8,957 + 388; SimCity_2..5 and EP1 have zero). Three properties matter:
`0x8A2602B8` **Item Icon** (278 exemplars, 266 distinct values),
`0x8A2602B9` **Item Order**, `0x8A2602BB` **Item Button ID**.

- The property holds **only the instance**; type + group are hardcoded (4.2).
- **266/266 values resolve** to a PNG in group `0x6A386D26`, and **all 266
  exemplar-referenced icons are exactly 176x44** = a 4-cell 44x44 state strip
  on a `GZWinBtn` (menu-item template clsid `0x4988BC6A`). The GROUP is
  larger: 356 images — the other **36 are 356x58** with sequential structured
  instances `0xMM0000NN`, bound to the one-widget 89x58 template script
  `I-ebd0d36d` (no `image=` at all), referenced by no exemplar and no `.UI`,
  staged by nothing (`SDK-GAPS.md` G14).
- Because state selection is `imageWidth/4` and **there is no `imagerect`** on
  these buttons, this is the **safest** case: a 352x88 strip yields 88x88 cells
  and picks the right state every time.

**Law: parse BOTH exemplar formats.** Base-game exemplars are all binary
(`EQZB1###`), but **CAM is roughly half TEXT** — a binary-only parse
silently misses 30 icons. Binary layout (decoded from scratch, 8,957/8,957 parse):
signature 8 bytes, parent cohort TGI 3×u32, u32 property count, then per
property `u32 id; u16 valueType; u16 keyType(0x80=array)`; **arrays get 1 pad
byte + u32 count + values, singles get 1 pad byte + one value** — that pad byte
on singles was the parser gotcha.

### 4.4 Path 3 — `sc4://` image URLs inside LTEXTs

The HTML engine resolves `sc4://HTML/<group>/<instance>` and
`sc4://image/...` URLs embedded in **LTEXT** resources (type `0x2026960B` in
`SimCityLocale.DAT`). `{46a006b0,14416264}` (`html_TextBG_General`) alone backs
**188 story pages**. Harvest recipe: extract LTEXTs, grep `sc4://`
(→ `tools/selective-safe/html-image-refs.txt`).

**Fixable at:** the art layer — but this path creates the sharpest sharing
conflicts, because the same TGI backs both scaled panels and unscaled HUD
frames. `{46a006b0,14416264}` is a **DELIBERATE 1x HOLE**: three unscaled HUD
panels 9-slice it with 16px insets and a 2x would corrupt their frames.

### 4.5 Path 4 — runtime-generated, NO TGI at all

**The PIXELS are unreachable by any art pass** — they are not in any dat.
(The *frame* of a widget with a dangling `image=` ref is still editable —
`RUNTIME_BOUND_2X` in `build_dialog_static.py` doubles such `imagerect`s
where the runtime pixels are themselves 2x; see path 4b below.)

- **My Sims portraits** — two sub-shapes. **4a — no `image=` at all:** the
  HUD panel `I-aa1f1f57` lines 19-23 (`0x22220000..04`, plus `0x22220055`;
  `0x8A1F1EEF` carries `imagerect=(0,0,100,100)` with no image). **4b —
  dangling `image=`:** the Select-A-Sim picker `I-0a243d80`'s 22 portrait
  cells (`0x12340000..0x12340015`) each carry `image={46a006b0,ea32f104}` —
  a TGI in no shipped archive — with `imagerect=(0,0,36,41)`. In both the
  game supplies the pixels at runtime (composed into power-of-two
  `cIGZBuffer`s — 36x41 into 64x64 — so a doubled `imagerect` samples past
  the live data into the POT padding; the picker's rect must NOT double).
- **Advisor faces** — the 7 strip faces are **live 3D head renders**, not
  films: their arts `14015570-76` are plain 220x94 4-state strips, and the head
  binder `0x41DE20` creates each head object ONCE per controller slot
  (`cmp [edi],0; jne` = reuse path).
- **Gauge dials** (`0xCBCBF1E0`) and the **Graphs chart** — code-painted into
  their own cached buffers. **Note: the chart's LEGEND is a different story**: its
  swatches and text blocks are real entry objects laid out by the *panel*
  builder from `.text` literals and only *painted* by the chart, so it is
  reachable by a byte patch on the builder and by nothing else (§5.4).
- **Tooltips** — the tip layer `0x2AAB8CC1` (class vt `0x00AB6770`)
  code-paints the ENTIRE tooltip: no child windows exist.

**Fixable at:** code only — buffer force-recreate, surface destroy+recreate, a
slot-pitch hook, or a byte patch (§7.3). The unifying diagnostic: **a correctly
2x window with its content pinned in the top-left quadrant.**

Worked example of "the pixels come from code, so measure the buffer not the
art": the dials' TGIs are ALL already staged 2x-in-place
(`refmap.csv`: `2BEB4BBB`, `CBCB9A73/74`, `2BEC54A3`, `2BEC99B1`, `4BE99DC8`,
`CC39214D`, `AC101989`) and they **still draw small**.

### 4.6 The classification the builder actually uses

`build_selective_safe.py` marks the subtree of every id in
`SCALED_WINDOW_IDS`, then classifies every `image=` ref:

| Class | Definition | Action |
|---|---|---|
| **EXCLUSIVE** | referenced only by scaled subtrees | stage the 2x PNG at the **ORIGINAL TGI** (in-place override; Plugins load after `SimCity_1.dat`, same TGI wins) |
| **SHARED** | referenced by scaled *and* unscaled scripts | **never touch the original.** Stage a 2x **clone at `IID XOR 0x53430001`** and retarget only the scaled subtree's refs (collision-checked; `0x53430002` on collision) |
| **UNSCALED** | referenced only by unscaled scripts | untouched |
| **CODE-BOUND** | absent from every `.UI` ref | 2x in place at the original TGI |
| **CODE-BOUND CONFLICT** | code-bound *and* referenced by unscaled-only scripts | **not staged** — an in-place 2x would corrupt the unscaled context. Escalate by cloning + retargeting the scaled consumer, or accept 1x |
| **CODE_BOUND_FORCE** | code-*created* controls that load the original TGI and cannot be retargeted | forced in-place; unscaled `fill=yes` consumers downscale acceptably |

Plus: `imagerect` doubles **iff** that control's art went 2x; every `font=`
name becomes a GUID. **Three live stages edit `area=`:**

1. `double_subtree_areas` (`build_selective_safe.py:646`; called at `:1963`,
   `:2011`, `:2035`, `:2057`, `:2082`) — pre-scales a whole subtree (§7.3).
2. `seat_faces_on_apertures` (`:864`, rewrite at `:924-926`, called `:1976`) —
   runs immediately AFTER the advisor call at `:1963`, on the same `new_text`.
   Seats the 7 advisor faces (`ADVISOR_FACE_SEATS`, `:802-810` — the same 7 ids
   in both `I-cbc905cd` and `I-4a160034`, so 14 windows) on their frame's
   MEASURED art aperture. The delta is FATAL beyond 1px (G5, `:921-922`) and is
   `(0,0)` — nothing written — at an integer tier, which is ASSERTED, not
   assumed (`:918-919`, `:1985-1987`).
3. the ticker-marquee design-width widen for `I-2a2aed99`, inline at
   `:1936-1946` (`re.subn` on `id=0xaa12f33c`, FATAL unless it matches exactly
   once). The code calls it "the ONE deliberate exception" at `:1934-1935`; see
   also the **Ticker marquee `0xAA12F33C`** row later in this file.

Note: `parity_nudge_btn_areas` (`:1241`, write at `:1273`) and
`double_one_window_area` (`:931`, write at `:957`) also contain `area=` writes
but are **defined and never called** (`:2122-2125`). A grep for `area=` finds
five write sites; only the three above are live.

Outside those three the builder leaves `area=` alone — which is why the panels
it does **not** pre-scale must stay runtime-scaled. (The pre-scaled subtrees are
the opposite case: `0x6A15C767` is in `kDataScaledSubtreeIds`, so
`ScalePanelRoot` returns before the child loop — `src\UiSpike.cpp:14568-14573` —
and the runtime sweep never walks those buttons.)

**Law: ART AND RUNTIME SCALE MUST MOVE TOGETHER — including in reverts.** Art
without the scale, or the scale without the art, produce the *identical*
symptom: **quarter-art with black fill** (budget panels, U-Drive-It dashboard,
Graphs middle root, My Sims detail roots — four independent instances of one
signature). Scale factors are expressed via `FACTOR`/`scale_len` =
`floor(v*N + 0.5)`, never `*2`: **1.5x is where rounding bugs hide, 2x hides
them.**

**Law — THE LOAD-ORDER LAW.** Files in the `Plugins` **root load BEFORE
subfolders**, so a root `z_*.dat` can NEVER override a dat inside a subfolder.
Overrides of another mod must live in a folder sorting after it
(`zzz-SC4UIScale\` beats `150-mods\`). And a plugin may replace a stock
**script**, its **art**, or **both** — CoriBoom replaced the Building Style
script AND shipped its own **taller** background (516x654 vs stock 516x396),
so the art half must be upscaled from **the MOD's** bitmap, never the stock
one.

**RECOGNITION RULE (cheap, and it settled the case in one pass):** *if a
panel's LIVE window count or root size does not match the stock script you are
reading, a plugin has replaced that script* — live `532x640 / 73 windows` vs
stock `531x406` was the tell. Grep `Plugins\**\*.dat` for the TGI before
touching anything. Corollary seen in practice: **wrong text COLOUR was a
symptom of the wrong SCRIPT being loaded**, not a font or colour bug.

### 4.6b THE NESTED PLOP SUB-FLYOUT — fully decoded

It is the most-decoded panel in the project after the budget family, and the
most dangerous to change — see the coupling at the end.

**The assembly is THREE windows, and the items are NOT among them:**
```
container 0x8A6E61E0   (width invariant 129 stock / 258 at 2x)
└── strip 0x8A2CAD8B
    └── tip layer 0x2AAB8CC1   (always 0x0, vis=0 - degenerate)
```
The visible menu items are **blits into the container's paint buffer**, not
child windows. **No window-tree sweep can ever reach a sub-flyout item at any
depth** — which is why pre-scale-while-hidden, the SetFlag show hook and data
pre-scale all failed on it: every one of them operates on windows.

**Builder: `sub_7EAEB0`** (`0x007EAEB0..0x007EB320`), the only code in the
image that pushes either id (`0x007EB11A` / `0x007EB1F4`); runs fresh on every
open (`operator new(0x150)` @ `0x7EB0DD`). **Warning — twin: `sub_7E7270` builds the
FIRST-LEVEL flyout from the same two classes with its own copies of every
constant** — and the first-level one is already scaled after birth. `sub_7F4690`
calls both. **Patch by VA, never by pattern.**

**Closed-form geometry — reproduces 8/8 observed container heights:**
```
stripH   = count*(cellH 44 + gap 5) - 5      = 49n - 5,  n = clamp(count,1,8)
contentH = max(stripH, [+0xF4]=53) + 2*[+0xE8]=50
contW    = [+0xF0]=80 - [+0xF8]=4 + [+0xE4]=53 = 129     (invariant)
```
Freight's `258x206` is the proof: 1 item → 44, *below* the 53 floor → clamps to
`53+50 = 103`, ×2 = 206 — the one height that fits no arithmetic progression,
produced exactly by the constant at `0x007EB163`.

| VA | bytes | stock | field | meaning |
|---|---|---|---|---|
| `0x007EAEF3` | `6a 2c` | 44 | provider | cell W |
| `0x007EAEF1` | `6a 2c` | 44 | provider | cell H |
| `0x007EAEEF` | `6a 05` | 5 | provider | row gap |
| `0x007EB169` | `6a 35` | 53 | `+0xE4` | bar width — **dual-use: also the `IsPointInMe` hit-claim** |
| `0x007EB167` | `6a 19` | 25 | `+0xE8` | end cap (×2 = the +50) |
| `0x007EB165` | `6a 50` | 80 | `+0xF0` | ring-sprite width term — **cannot encode ×2 in imm8** |
| `0x007EB163` | `6a 35` | 53 | `+0xF4` | minimum content extent (the Freight floor) |
| `0x007EB161` | `6a 04` | 4 | `+0xF8` | overlap subtracted from W |
| `0x007EB15F` / `0x007EB15D` | `6a 1b` / `6a 1d` | 27 / 29 | `+0xFC` / `+0x100` | anchor offsets |

Setters: `vf10 = 0x0079AC60` stores the fields; `vf14 = 0x0079AD00` is the only
`SetArea` in the family. **Policy constants that are NOT geometry:** count
clamps 1/8/6, and `cmp eax,0x258` @ `0x007EAF3D` which is **600 decimal**, a
view-height rule — a false friend for anyone grepping "258".

**Law — THE COUPLING THAT BROKE THE UI TWICE.** The bar is a 9-slice whose
middle segment is computed from the art:
```
[+0xEC] = artHeight - 2 x [+0xE8]
  stock            53 - 50  =   3   correct
  constants only   53 - 100 = -47   NEGATIVE -> bar renders as a thin sliver
  art only (2x)   106 - 50  =  56   ~19x too tall
  both            106 - 100 =   6   = 2 x stock
```
The atlas is `{0x856DDBAC, 0x46A006B0, 0x14215ED0..ED5/EDD}`, 292×53, present
in **both** mirror groups, code-bound (no `.UI` refs). **Constants and art are
a matched pair — neither half is shippable alone**, and shipping both
together still breaks the bar, so a third term is in play. The cure that ships
instead is row 4 of §4.7: leave every constant alone and scale the finished
rect.

**The flash on these menus is BIRTH, not the sweep** (measured, 6 opens / 3
menus): the container is born VISIBLE at 1x and the game paints 1-2 genuine
stock-size frames before the sweep's next tick — 20-36ms at 54.5fps —
which is why it reads on screen as the pre-scaled panel for a split second
rather than as garbage. The 1x paint buffer `DOBS` reports at Plot #1 is the
fossil of those frames, not an independent defect: a container born at 258
allocates its buffer at 258. Acceptance criterion: `DOBS`'s `srcBuf` equals the
window rect on **Plot #1**, not Plot #2.

**Cured by row 4 of §4.7** — a detour on `Place` (`0x0079AD00`) scales
the finished rects (container, the strip rect still sitting in `[0x108..0x114]`
where `GetStripRect` will read it, and the strip's item metrics) plus the dock
delta, between the end of the layout and the first pixel. Offline proof:
`tools\uimap\emu\emu_subflyout.py` runs the game's own `sub_79AD00` for n=1..8
at f=1/1.5/2/3 and asserts born == sweep == the six measured live rects (71
checks). **The constants are never touched** — that is what separates it
from patching them directly.

Full detail: `tools\uimap\SUBFLYOUT-{BUILDER,ART-VERDICT,CONSTANTS,LIVE-EVIDENCE}.md`.

### 4.6c THE SHEET'S **ROLE** DECIDES ITS SIZING RULE — three roles, three rules

This is an ENGINE fact, and it decides four separate classes of 1.5x defect.

**The engine cell-divides a sheet with an INTEGER DIVIDE baked into its own
machine code.** It never reads a cell count from data. So the *only* contract a
scaled sheet has is: **after scaling, the divide the engine performs on it must
still come out even.** Which divide that is depends entirely on what the sheet
*is for* — its ROLE — and the role is **not** predictable from its pixels.

| ROLE | What the engine does | Sizing rule for a scaled sheet | Derived from |
|---|---|---|---|
| **N-state strip** (buttons, ItemIcons, checkboxes) | `cell = imageWidth / N`, state selected by index. Cut **HORIZONTALLY ONLY** | **Width:** the snap unit is `CellUnit(v)` = the LCM of whichever of `{3,4}` divide the **1x** dimension (`tools\upscale\Upscale2x.cs:846`, `:798-807`, `:677`). `CellUnit` takes only the dimension and **never sees N**, so it can over-snap and it can miss entirely: a 4-state sheet whose width also divides by 3 snaps on **12** — the Zoom Out 84px sheet goes to 132, cell **33** against a 32px window — and the corpus's two **8**-state strips (`cell-strips.txt:8`, `:154`) are never snapped to a multiple of N at all, since 8 ∉ `{3,4}` (`Upscale2x.cs:684-688` works that case out). **Height:** exact only when `sNoHeightSnap` is set (`:876`), and only `--height-exact-group` / `--height-exact-strips` set it (`:361`, `:417`). The corpus rebuild passes **neither**, so **button and checkbox heights ARE cell-snapped**. Only **ItemIcons** take the exact height, via `--height-exact-group 6A386D26` in the ItemIcon builders. Measured with `gate_btn_undercover.py --tier 15x`: `{(0,1):1, (1,0):1, (0,2):347, (0,6):3}` — **351 of 352 are the cell TALLER than the window; exactly one is width.** **Law: DO NOT "FIX" THE HEIGHT HALF FROM THIS ROW.** Passing `--height-exact-strips` leaves the two known 1.5x hairlines unchanged and breaks the "?" button `{46a006b0,14415860}`; it is a forbidden cure. Those hairline buttons are runtime-swept and their widths already agree under both rules. | `upscale\find_cell_strips.py` — reads **the `.UI` that BINDS each sheet**. 193 of 2206. Note: that derived list reaches the per-state **SAMPLER** (`Upscale2x.cs:317-327` → `:734`) and `--height-exact-strips` **only**. It never reaches `CellUnit`, so N does not drive the width snap — `Upscale2x.cs:403-409` says so outright, and that separation is deliberate |
| **9-slice frame** (`blttype=edge`, `edgeimage=yes`) | `cell = (img->Width()/3, img->Height()/3)`; corners unstretched, edges stretch only *along* the run. **Note on the drawer:** `0x00794100` does not serve this row — it is `cSC4WinAlertBorder`'s own slot-88 draw, a code-created full-screen window that appears in **no `.UI` script at all**, so it can never own a role derived *from* the `.UI` corpus. The drawer for this row is the widget's own slot-88 draw: **`GZWinBMP` → `0x009BC325`** (EDGE branch, entered on flag bit 8 of the holder at `[this+0xD8]` via its `vt[10]`), **`GZWinBtn` → `0x009B05E0`** (its draw's nine-slice branch). **Note: each of the three drawers performs the `/3` ITSELF and hands an already-cut cell to a blitter that contains no divide** — `0x008D9550` for the alert border (one caller image-wide), `0x008D8800` for `GZWinBMP` and `GZWinBtn`. The arithmetic in this row: `0x009BC325` divides the *source rect*, which for a sheet with no `imagerect` **is** the image's natural rect. | snap to a multiple of **3, and 3 alone** | `upscale\find_nine_slice.py` |
| **Tiled background** (`blttype=tiled`) | src-follows-dst: the source is **repeated** across the destination. No divide at all | **Law: snap NOTHING.** Its only contract is with its WINDOW, and the window scales by a plain round | `no-snap.txt` is generated by **`upscale\find_no_snap.py`** (`no-snap.txt:2`, `find_no_snap.py:124`), and its scope is `blttype=tiled` **OR** a sheet a `.UI` binds 1:1 to a window of exactly its 1x size, in either case only if no `.UI` ever draws it as a `GZWinBtn` state or a 9-slice and it is absent from `cell-strips.txt`/`nine-slice.txt` (`find_no_snap.py:22-28`). **121 entries**, and this is the file the corpus rebuild binds to `--no-snap`; the exe parses only `--cell-strips`/`--nine-slice`/`--no-snap` (`Upscale2x.cs:146,182,214`) |

**Law: DERIVED LISTS, NEVER HAND-LISTS.** Every one of those three lists is
generated from the `.UI` corpus. The counter-example is measured: scoping the
cell-aligned sampler by `CellUnit`'s *guess* instead of the derived list moved
**1186 of 2206** sheets and displaced an advisor aperture.

**Law: THE LCM IS A THIRD ANSWER THAT IS WRONG FOR BOTH.** A 9-slice frame whose
width happens to divide by 4 is not a 4-state strip; taking `LCM{3,4}` satisfies
neither consumer:

```
180x180 frame at f=1.5     /3 -> 270     /4 -> 272     LCM 12 -> 276
```

At 276 the NineSlice cell is 92 while every geometry number in the `.UI` was
scaled for 90 — the corner art overshoots and the rounded corner never reaches
the window corner. Measured: **418 uncovered px at 276, 4 px at 270**.

**Warning — THE PROPORTIONALITY GUARD, and why it is not a fudge.** A 16px icon divides
by 16, but it is an ICON, not a 16-cell strip. `ScaleDim` therefore abandons the
snap when the correction would exceed **12.5%** of the dimension: a genuine cell
sheet is far larger than its cell count, so real cases are 2–6 px corrections on
100–5000 px sheets and pass easily.

**Law: EVERY RULE ON THIS PAGE IS A PROVABLE NO-OP AT AN INTEGER FACTOR** —
`ScaleDim` returns before `CellUnit` is ever consulted when `f` is whole, so 2x
and 3x output is **byte-identical** with and without all of it, and the build
asserts that. **This is the house control**: a new sheet-sizing metric that
reads nonzero at 2x or 3x is measuring itself, not a defect. Measured spread of
the underlying breakage: **31% of `/3` sheets and 43% of `/4` sheets break at
1.5x; 0% at both integer tiers.**

**Law: NEVER REACH FOR THE RESAMPLER.** Nearest-neighbour only copies source
pixels, so it **cannot introduce a colour the 1x art lacks** — a white seam
absent from the source can never be an NN artifact, which rules the upscaler out
of any seam investigation in one sentence. And interpolation moves magenta off
`0xFF00FF`, the key test misses, and **the key colour itself draws** (§2.3):
`--hq` turns the Mayor Rating bar and the news-reader borders pink within one
launch.

#### 4.6c.1 THE RULE HAS **TWO** IMPLEMENTATIONS, AND THEY MUST NOT DRIFT

`ScaleDim` / `CellUnit` exist **twice**, deliberately, because two paths both
claim to scale an icon and a disagreement is a visible defect:

| Copy | Scope | Where |
|---|---|---|
| offline art pipeline | the shipped dats | `tools\upscale\Upscale2x.cs` — `ScaleDim`, `CellUnit`, `kCellCounts = {3,4}` |
| **runtime ICONSYNTH** | third-party ItemIcons enlarged live at boot | `src\ScaleTier.cpp` — `RoundHalfUp` `:1270`, `kCellCounts` `:1294`, `CellUnit` `:1298`, `ScaleDim` `:1309`, `ResampleCells` `:1342` |

The runtime copy's header calls itself *"THE OFFLINE UPSCALER'S DIMENSION RULE,
PORTED VERBATIM"* and carries the worked example that forced it:
`h = 44, f = 1.5 -> 66`; `CellUnit(44) = 4`; `66 % 4 = 2`, so `down=64 up=68`, a
**TIE**, and ties go **UP** to 68 — the same 68 the offline build reaches from
its 88-tall stage art via 0.75. *Different starting point, identical answer* —
**for that one worked example only. It is not the general case; see below.**

**MEASURED 2026-08-23 (register #7, `_tests\Test-ScaleDimParity.py`): THE TWO
COPIES HAVE DRIFTED, and it is live, not hypothetical.** The runtime copy has
`kCellCounts = {3,4}` and **no** equivalent of the offline `sNineSliceOnly` /
`sNoSnapThis` / `sNoHeightSnap` role scoping — confirmed by reading
`ScaleDim`'s signature (`int ScaleDim(int v, float factor)`, two arguments,
one overload) and by the absence of any `NoHeightSnap`/`HeightExact` text
anywhere in `ScaleTier.cpp`. That absence is not academic: `rebuild_namicons.py:43`
builds the shipped NamIcons packages with `--height-exact-group 6A386D26` —
`sNoHeightSnap` for exactly the TGI group (`{0x856DDBAC,0x6A386D26}`) the
runtime ICONSYNTH path exists to enlarge (`ScaleTier.cpp:1656`'s
`kIconType`/`kIconGroup` check). Run over the real 392-file 1x corpus in
`tools\itemicons\nam-1x` at f=1.5: **WIDTH agrees on all 392** (the runtime's
direct cell-first formula and the offline pipeline's plain-`ScaleDim`-then-
round-to-4 happen to coincide here), but **122 of 392 sheets — every 176×44
sheet in the corpus, the exact #150 disaster-flyout-thumbnail shape —
disagree on HEIGHT: offline ships 66, the runtime ICONSYNTH path would
enlarge the same TGI to 68.** Any third-party ItemIcon of this group NOT
already covered by our shipped package hits the runtime path and gets the
wrong (68) height at 1.5x. The control that keeps the two from drifting: they
must agree on every sheet the runtime path touches at 1.5x, and both must be
no-ops at 2x/3x — **the no-op control holds (proven, S3); the 1.5x agreement
control does not (measured FAIL, S5).**

The runtime path also carries **its own** per-cell resampler,
`ResampleCells` (`src\ScaleTier.cpp:1040`) — the rule that a 4-state strip
is four independent images sharing a texture, implemented a second time. Same
drift risk, same control.

### 4.7 WHICH FLASH CURE APPLIES — pick by HOW THE WINDOW IS BORN

**Read this before designing any anti-flash fix.** Every cure that has worked
in this project makes the window **born correct**. Not one of them catches the
window later. The mechanism is decided by how the window comes into
existence — get that wrong and the fix cannot work no matter how well built:

| How the window is born | Cure | Precedent |
|---|---|---|
| **Persists hidden** between uses | pre-scale while HIDDEN; gate only the dock MOVE on visibility | region panels, god flyouts (v2.11.29) |
| **Scripted `.UI` subtree**, not runtime-composed | DATA pre-scale (`double_subtree_areas` + root in `kDataScaledSubtreeIds`) | advisor strip, Graphs, U-Drive-It dashboard (v2.20.0) |
| **Code-created fresh on every open** | patch the BUILDER's constants so children are created at scaled coordinates | the whole budget detail family (v2.25-2.29, ~190 sites); the Data Views legend (v2.37.0, 8 sites) |
| **Code-created fresh, and its constants are COUPLED** | detour the builder's own *placement* call and scale the FINISHED rect on its return — never the constants | the nested plop sub-flyout (v2.36.0, §4.6b) |

**Row 4 is row 3's escape hatch.** Both rows make the window born correct; they differ in *what*
they change. Patch the constants when each one feeds exactly one coordinate
(budget: 190 sites, zero surprises). When a constant is *also* read by
something else — `[+0xE4]` is the bar width **and** the hit-claim, and
`[+0xEC]` is computed as `artH − 2×[+0xE8]` — the ripple lands in a different
subsystem and the fix breaks the panel (that is the −47 sliver). Then let the
game compute its own 1x layout undisturbed and scale the *output*: the
arithmetic is identical to the sweep's, so the settled state provably cannot
change, and only the first 1–2 frames differ. The hook point is whichever call
finishes the layout — for this family `Place` (`0x0079AD00`), which is also the
only `SetArea` in it.

**Warning: A BORN-CORRECT WINDOW NEEDS ITS DRAW-HOOK STATE BORN TOO.** Getting
the *geometry* right at birth is only
half the job: for a code-painted control the chrome is drawn by transforms that
read PER-WINDOW state — the promoted `[0xE0]`, the latched `gClaimOrig`, the
instance `SlotThunk` install. Leave that state to the sweep and the window is
born the right SIZE with 1x CHROME, which is a new artifact, not a smaller one.
Measured: 159 ms (9 frames) of 1x bar on the first sub-flyout of a city, while
later opens look perfect **because they inherit the latched state from the
previous open — they are not faster (30-48 ms), they are pre-warmed.** A
defect that only appears on the first use of a session is an uninitialised
latch, not a race.
**Corollary:** install that state in the SAME ORDER the sweep does. `[0xE0]` is
dual-use (hit-claim width AND a Plot layout inset) and `SlotThunk<88>` is what
presents the 1x value to the draw group — promote the field before installing
the thunk and the game paints a SECOND bar (v2.11.24).

**Warning: four things a row-4 fix must not forget:**
1. **Register the window as already-scaled.** `ScaleSubtree` is idempotent via
   `scaleMap`, keyed on the window POINTER. A window you scaled at birth is a
   pointer the sweep has never seen ⇒ `Fresh` ⇒ it scales it a *second* time
   (129 → 258 → 516). `DrainBornScaleRecords()` exists for exactly this.
2. **Prime every latch that reads the 1x value.** `SlotThunk2<88>` re-applies
   `base × f` to the strip's item fields on every Plot and *latches the first
   value it sees*. Born-scale it first and the latch becomes 88, so it writes
   176. The base is now primed from the builder's own argument
   (`gStripBase*`) — the general form of law 30.
3. **The DOCK must be born too, and its inputs must be warmable BEFORE the
   first open.** Caching the dock target but writing the cache only while a
   flyout is OPEN gives a latch that is cold on the first open of every
   session *by construction* (measured: `DISBORN at (63,688)`). Worse, a
   post-birth corrective move is NOT equivalent
   to being born docked when any part of the assembly is a PARENTLESS window:
   the disaster thumbnail strip does not follow a container move — only the
   game's own re-layout places it, and that runs at open (from the
   already-docked container, if you docked at birth) or on a user hover (if
   you did not). Cache rule: **warm from the persistent anchor (the scaled
   toolbar) on every sweep tick, not from the transient window.**
4. **A layout-time DECISION sees birth-state units — born rect therefore
   requires born metrics.** The scroll-arrow flags `[0x118]/[0x119]` are
   computed at OPEN from `visibleRows = (stripWinH+sp)/(itemH+sp)`
   (`0x79AA70`); with a 2x window and 1x metrics that is 11 ≥ 9 items ⇒
   "nothing to scroll" ⇒ no arrow, and **no repaint can restore it —
   the draw only READS the flag** (a forced repaint fires and cures nothing).
   Make every input of every decision taken at open consistent at birth. Safe order: latches primed from stock
   BEFORE Place (the game guarantees it: SetItemMetrics precedes Place in
   the builder), fields written to `base×f` AFTER Place, behind a READ-GUARD
   that refuses unless the fields still hold the exact stock values.
   Offline proof pattern: `emu_subflyout.py --builder=disaster` runs the
   three states (stock / half-born / born) and asserts the decision flips
   only in the half-born one.

**Anti-patterns, each measured and rejected:**
- **Suppressing paints** — a `FlashGuard` blanked HUD windows and did not fix
  the flash. Permanently rejected.
- **A show hook** (`SetFlag` vt+0x110) — cannot work for anything created on
  demand: both constructors set `[this+0xC8]=0x8903`, so a new window is BORN
  visible and never produces a false→true transition. Measured: the ids that
  fired were disjoint from the ids that flashed.
- **DATA pre-scale on a COMPOSED HUD panel** — broke mayor mode outright. The
  city HUD roots are re-laid and re-anchored at runtime and some children are
  game-created, not scripted; freezing scripted children at 2x under a root the
  sweep still moves separates the pieces. Row 2 requires *fully scripted* and
  *not runtime-composed* — a 152-live-window panel with only 146 scripted
  `area=` entries fails that test, and the 4% gap is the tell.
- **Waiting for the sweep** — the first tick after `PostCityInit` is ~290ms
  late (the message loop is busy finishing the load), so no cadence change can
  win the race. Remove the race instead of trying to win it.

**Warning: A RE-LAY IS NOT A BUILD — AND ONLY PART OF IT IS A 1x CONSTANT**
(the Data Views legend). A panel can be built once from its `.UI` and then
**re-laid by code on every user action**. There the row-3 patch applies to the
re-lay routine, and the constant to scale is only the **ORIGIN**: SC4 composes
the running offset from *measured* text (`edi += 18*ceil(h/18)`), which already
self-scales with the font at every tier. Scale the origin, never the step.

The tell that you are looking at one of these is a **mixed** rect: the log
shows a correct 2x pitch sitting on a 1x origin (`24+36k` where design is
`24+18k`). And the payoff is not only the frame: because the step is measured
per row, a wrapped two-line label gets a **taller slot**, so any correction
that writes a uniform table *flattens* it. Patching the origin is the only form
that keeps the game's own per-row deltas — measured: a nine-entry legend
whose real layout is `...168,240,276...` (a 72px gap) has eight windows dragged
up 36px by exactly such a table.

**Diagnostic that picks the row:** count the window's live children vs the
`area=` entries under its root in the staged `.UI`. Equal ⇒ row 2 is safe.
Live > scripted ⇒ the extra children are code-created: row 3 (or row 1 if the
whole window persists hidden). If the children ARE scripted but a *runtime
re-lay* moves them anyway, data pre-scale cannot win — patch the re-lay
(v2.37.0).

---

### 4.8 The three "role unknown" code-created windows (register #17) — Photo Album / recorded-animation export cluster

Static disasm (`tools\research\disasm_at.py`, `SimCity 4.exe` 1.1.641.0 Steam,
ImageBase `0x400000`), byte-verified against the shipped exe. Two of the three
are now fully identified; the third's builder function is identified but its
id↔vtable link is not.

**`0x9AEDEF7C` — CONFIRMED: an image-file Open/Browse dialog's content list.**
Its sole `SetID` site is inside a 656-byte vtable-only method at `0x79D8D0`
(`funcs.json`: 0 direct callers, i.e. virtual-dispatch only). That method:
sets its own window's area to `(20,20)-(424,288)` (`vt+0xDC`, the register's
`SetArea4`), configures a grid via `vt+0x1AC` with args `(0x19,3,0xDC)`
(25 rows, 3 columns, 220px cell), then gets/creates a helper object through
the GZCOM singleton getter `0x90DDF1` using a 2-dword class-id pair
`{0x1AA52EA4, 0x3AA52E64}` (stored at `[this+0xD8]`). Through that helper's
`vt+0xC` it obtains a NEW child window, `SetID`s it `0x9AEDEF7C` (`0x79D95B`,
`push 0x9AEDEF7C; call [eax+0x100]`), sizes it to `(parentW-8, parentH-8)`
(an 8px inset filling the 404×288 parent almost entirely), sets a 4px
margin (`vt+0x124`, args `4,4,4`), and adds it as the parent's child
(`vt+0x38`). The SAME helper object is then fed **six placement-constructed
`cRZString`s, each built from a literal C-string in `.rdata`**, one per
`vt+0x54` call: `0xAB7DDC`=`"*.bmp"`, `0xAB7DD4`=`"*.png"`,
`0xAB7DCC`=`"*.gif"`, `0xAB7DC4`=`"*.jpg"`, `0xAB7DBC`=`"*.jpeg"`,
`0xAB7DB4`=`"*.tga"` (six consecutive 8-byte-apart `.rdata` slots, raw bytes
read directly, not inferred) — a file-type filter list of exactly the six
image formats. **This confirms the register's prior guess.** `0x9AEDEF7C` is
the file-list/content pane of an image-file browser, not the browser's own
outer dialog (which is `this` in `0x79D8D0` and carries no id found anywhere
in `.text`/`.rdata`/`.data` by literal scan — likely a computed/hashed id,
register unknown #10).

**`0xA802B4EB` (vt `0x00AB6010`) — CONFIRMED: the "RecordedAnimations"
folder browser.** `sub_7F0840` is a get-or-create singleton accessor
(`GetChildWindowFromID(0xA802B4EB)` via `vt+0x88`; creates only if the
caller's bool arg is true and none exists). On create it allocates 0x218
bytes, constructs via `sub_796380` — which stamps `mov dword ptr [esi],
0x00AB6010` at `0x796399`, directly confirming the vtable — then builds a
default path as a placement-constructed `cRZString` (vtable `0x00A80810`,
independently already on record as the `cRZString` vtable in
`tools\research\regionmap\slice-3.md`/`slice-5.md`/`slice-7.md`) whose text
is copied from the literal ASCII range `0xABCBA8`..`0xABCBBA` in `.rdata` —
**`"RecordedAnimations"`** (18 chars, `0xABCBBA` is exactly the byte after
the last char, i.e. a `(begin,end)` pointer pair into that literal) — then
appends a trailing `\`. It calls `sub_795100(path, true)` (an Init-style
method) on the new window, `SetID(0xA802B4EB)` (`0x7F094B`), adds it as a
child of the manager (`vt+0x38`), and releases. A third reference site
(`0x7F144D`, not traced further) is presumably the menu/command handler that
opens it. **Conclusion: `0xA802B4EB` is the load/browse dialog for SC4's
recorded camera-path ("movie") feature, defaulting to
`...\RecordedAnimations\`.**

**`0x85202C0E` (register-cited vt `0xAB9980`, `sub_7BC350`) — PARTIAL.**
`sub_7BC350` itself is fully identified: it reads exemplar/property values
`0x6A8CD21F, 0xAA8CD25D, 0xAA8CD14A, 0xAA8CD139, 0x4A8CD356(×2), 0x6A8CD222,
0x8A8CC775(×2), 0xAA8CC64E, 0x8A8CC773, 0x4A8CD34E, 0xA8CD3FF, 0xA8CD401,
0xA8CD400` from a passed-in property holder via `vt+0x8C`, and its own
literal art-load at `0x7BC624` is `{0x856DDBAC, 0x1ABE787D, 0x2558A4CB}` —
already on record in `tools\research\_incoming\sdkgaps-03.md` (the "ONE REAL
GAP FOUND" passage) as the **Photo Album** panel's 296×222 backdrop, sourced
from `I-4a8cc5ea` (captions "Photo Album"/"Albums"/"expand"/"Close", scripted
root `0x0A8CD3EE`). `sub_7BC350`'s single caller (`0x7BCFA1`, `funcs.json`:
1 caller) resolves its target child via property `0xA8CD3FF` (same Photo
Album cluster) from a routine that also centers a 640×480 (`0x280×0x1E0`)
dialog on screen. **`sub_7BC350` is the Photo Album panel's
content/backdrop-populate routine — that half is closed.**

What did NOT close: the literal id `0x85202C0E` occurs exactly twice in the
whole image (`68 0E 2C 20 85`, `.text` only, no `.rdata`/`.data` hits) —
`0x7B753B` and `0x7B7AA7` — and both are `GetChildWindowFromID`-style lookups
belonging to a *different* get-or-create pair (`sub_7B7530`/`sub_7B7480`)
whose constructed object's own vtable is stamped **`0x00AB9BF8`**, not
`0xAB9980`. `0xAB9BF8` and `0xAB9980` are siblings, not the same class: they
share ~85 of the first 90 vtable slots byte-for-byte (both inherit the
documented `cIGZWin` layout — identical GZPaint at slot 87) but diverge at
slots 0–2 (QI/AddRef/Release equivalents), 3, 4, 5, 55, 62, and 88 (Plot —
`0x7C0220` for the `0xAB9980` sibling vs `0x7B6B30` for the `0xAB9BF8`
sibling, matching the register's "Plot is per-class" note). `0xAB9BF8`'s
own `OnCreate` (vtable slot 4, `0x7B7A80`, the function that does
`SetID(0x85202C0E)`) builds a **standard image/video export-resolution
preset list** — `160×120`, `320×240`, then successively larger 4:3-ish
presets gated by comparisons against a live width up to `2048×~1536`,
via repeated calls to `0x4467A0(w,h)` — behaviourally an "export size"
picker, which fits the same Photo-Album/recorded-animation-export feature
family as the other two windows above, but is not itself proven to be
`sub_7BC350`'s object.

**Net:** the id↔vtable pairing `0x85202C0E`↔`0xAB9980` printed in the
original register entry could not be re-derived by static means in this
pass — no code path was found connecting `sub_7BC350`'s caller (`0x7BCFA1`)
to a literal `SetID(0x85202C0E)`, and the two places that literal DOES occur
belong to the sibling vtable `0xAB9BF8` instead. `sub_7BC350`'s role (Photo
Album content populate) is solid regardless of which id its window carries.
**To close the id↔vtable link fully needs a live instrument**: break on the
`SetID` call inside whichever function actually creates `sub_7BC350`'s
target window (or dump `[this]` of the window returned by the property-`
0xA8CD3FF` lookup at `0x7BCF3C` while the Photo Album panel is open
in-game) — a static `.text`/`.rdata`/`.data` sweep cannot see a
non-literal (computed/hashed) id, and register unknown #10 already notes
89 of 162 `SetID` sites are non-literal.

---

## 5. Text rendering — two entirely separate systems

### 5.0 THE LINE-BREAK REGIME — why a `GZWinText` does or does not wrap

**Read this before treating any clipped caption as a geometry bug.** Decoded by
offline emulation of the text class (`0x009BC000-0x009C1000`) and confirmed
live: the wrap flag reads 0 on `0x0ABCE001`.

The class picks ONE of three regimes at `0x009BF486`, from a wrap width
`w = [this+0x160]` and a flags field `[this+0x128]`:

| Condition | Behaviour |
|---|---|
| `w == 0` or `flags & 0x0200` | **ONE line, no breaks at all** |
| `flags & 0x0002` | **WORD WRAP at `w`** |
| otherwise | **break at explicit `\n` ONLY, then clip horizontally** |

**The constructor default for `flags` is 0** (`mov [esi+0x128], edi`, edi = 0,
at `0x009C026C`), so the third regime is what an ordinary code-created text
window gets: it honours hard newlines already in the LTEXT and clips anything
else. `sub_779660` never calls `SetWinTextFlag` — only `cIGZWin::SetFlag` for
`0x800`/`0x8000`, which are unrelated.

**The wrap width is not a constant and has no CodePatches site.** It is
`GetW() - 2*gutter - scrollbarW`, clamped at 0 (`sub_9BCBC5` @ `0x009BCBC5`);
the gutter default is **5** (`0x009BFFCC`), so in practice **`GetW() - 10`**.

> **Warning: `scrollbarW` is read LIVE, not baked** — `[this+0x1d4]` holds the
> scrollbar object and `sub_9BCBC5` calls its `AsIGZWin` (vt+`0x0C`) then
> `GetW` (vt+`0xA4`) on every recompute. So **a pane's usable content width
> shrinks when its scrollbar is scaled**, and any fixed right-hand reserve a
> layout budgets against it can be right at one tier and wrong at another.
> This is the boundary that matters for anything measuring "does my content
> fit" — **not `GetW()`**. It is why an advice row can push a cell out of
> sight while arithmetic against the raw pane width says it is still inside.
> See §5.0a.

> **Warning: the other half of the wrap story, and it is the half that bites.**
> Whichever regime is in force, when the engine *does* wrap, **the box width
> is an INPUT and only the HEIGHT comes back** (`sub_896957`, font `vt+0xB8`,
> read-only on `r->left`/`r->right` at `0x00896979` — §5.4.5). So a layout
> that hands a FIXED box to a scaled font turns the extra ink into extra
> LINES, and the overflow surfaces at the BOTTOM of a panel whose real defect
> is on its RIGHT. §5.4 is the worked case.

### 5.0a THE ADVICE-ROW COLUMN BUDGET — one emitter, one constant, six lists

`cSC4WinAdviceList::Refresh` (**`0x00793810`**, vtable `0xAB5880` slot +`0x14`,
**one dword xref image-wide**) is the *only* row emitter for every advice list
in the process: news reader `0x6A231531`, advisor briefings `0x00100100` /
`0x00100101`, My Sims `0xAA1F1EB5` / `0x6A1F1F4A`, the briefing panels, and the
never-touch ticker marquee `0xAA12F33C`. There is **no twin builder** — unlike
the five budget builders, one change here reaches the whole family (and one
wrong byte breaks all of it).

Each row is one `<TR>` of a three-column table:

| cell | literal | width |
|---|---|---|
| expander arrow | `0x00AB5794` `<TR><TD WIDTH="18">` | hard-coded 18 |
| headline | `0x00AB5868` `</TD><TD WIDTH="%d">` | **`GetW() - 61`** |
| dismiss X | `0x00AB56B0` `</TD><TD WIDTH="18"><A NAME="item%d" HREF="sc4://action/close?item=%d">` | hard-coded 18 |

`61 = 18 + 18 + 25` from **`83 EE 3D` at `0x0079388F`**, so the declared total
is always `GetW() - 25`. The X cell is emitted **unconditionally** — there is
no dismissible flag and no fit test anywhere in `0x00793B1C..0x00793BA5`.

**Two layout rules make the row glyphs load-bearing** (both measured):
- a column's width is the **MEASURED cell rect** (`0x0090A0A3` →
  `0x00909A47`), *not* the declared `WIDTH=`, which reaches only
  `col+0x08`/`col+0x0C` — fields the width-distribution loop never reads;
- a container's rect is the **UNION of its children with no clamp**
  (vt+`0x10` = `0x00909A0C` → `0x009092BE` → `0x009084A0`).

So an `<IMG>` with no declared size (all sixteen row glyphs — §HTML furniture)
**grows its own cell**. 2x arrow art therefore adds 18px to column 1, consumes
the 25px reserve, and carries the last column past the pane's content edge.
Cellpadding/cellspacing absorb none of it: the TABLE ctor's three `2`s at
`0x00908770` are never read in the layout path.

**The lever** is the one constant: `CodePatches::ApplyAdviceRowScale`, which
restores the declared total by taking the arrow's extra width out of the
*headline* column. But **the 25px reserve is not one number — it is the gutter
plus the scrollbar**, and only the scrollbar half scales:

```
25  ≈  2*gutter (10)  +  stock scrollbar cell (16)
S(f) = round(18f) + 18 + 9 + round(16f)      f=1 → 61 EXACTLY
       arrow        X   fixed  scrollbar     1.5 → 78   2 → 95   3 → 129†
```

† clamped to 127 (sign-extended imm8; ~2px of X clipped at 3x, logged).

**That the form reduces to the game's own 61 at f=1 is the check that makes it
trustworthy** — the constant is reproduced from its parts. If an edit ever
stops reducing to 61, the split is wrong.

**Warning: this is why an advice list must be tested EXPANDED as well as collapsed.**
A collapsed list has no scrollbar and 15px to spare, so it passes with a wrong
reserve; expand a row and the scrollbar appears, usable width drops by another
`round(16f)`, and the last column goes over the edge. A flat reserve passes
collapsed and clips the X on expand.

`83 EE ib` **sign-extends**, so S must stay ≤ 127. All sixteen glyphs fit at
1.5x/2x (S = 113); at 3x the formula wants 165 and the wide re-encode carries
it (S = 129, ~2px of X clipped, logged). All sixteen glyphs ship scaled at
every tier.

> **The X glyph scales with the tier like the rest of the row.** The builder
> applies no factor filter, `ApplyAdviceRowScale` sets `xScaled = true`, and
> SelectiveArt ships **655 entries at every tier**. The wide re-encode
> (`lea esi,[eax-imm32]`) carries the >127 values.

**It is recomputed on EVERY `SetArea`.** The class overrides `SetArea` at
`0x009BFCA5`: base `SetArea` (`0x0099C837`) → recompute wrap width → store
`[this+0x160]` → `sub_9BF98B` **re-breaks every line**. This **narrows law
21**: text does not re-wrap from a re-applied caption (that early-outs), but
it *does* re-wrap from a resize.

**Therefore, to make any clipped caption wrap:**
```cpp
cIGZWinText* t = ...;            // QI on the window
t->SetWinTextFlag(0x0002, true); // vtable +0x1C
win->SetW(...); win->SetH(...);  // the resize IS the trigger
```
The engine then wraps at `GetW() - 10` **at every tier by itself** — 335 at
1x, 680 at 2x, 1025 at 3x. No added constant, nothing to re-tune per tier, and
no string manipulation. Prefer this to pre-wrapping a caption yourself.

**Diagnosing which regime you are in, from symptoms alone:** a break at a
sensible word with empty space left in the box = a hard newline in the string
(regime 3). A cut mid-word at the box edge = a newline-delimited segment
wider than the box (also regime 3). *Neither is a word wrap* — a real wrap at
width `w` produces neither. Both together mean `flags & 0x0002` is clear.

> **Measurement worth keeping:** the ordinance descriptions measure
> **4,225-6,166 px** as a single unwrapped line at 2x (logged text extents).
> Any "just make the box wider" instinct dies on that number — the screen is
> 2,400 px. It also shows why an extent inferred from a screenshot — a
> ~920 px estimate, for these strings — can be wrong by 6x.

**Law: do NOT reach for `cIGZFontSys` to measure text.** It declares three
`FontAcquire` overloads and two `AddFont` overloads before
`EnumerateFontInfo`; MSVC reverses overloaded groups in the vtable (§1.4), so
calls through the community header dispatch to the wrong slots — observed as
`FontAcquire` returning null in one build and a silently swallowed fault in
the next. The regime switch above removes any need for it.

### 5.1 System A: FontStyle styles (`GZWinText`, button captions)

- One parse site only: `[Font Styles]`/`[Font Aliases]` section names are
  referenced exactly once each (`0x44DE23` / `0x44DD7F`) inside the font init
  at **`0x44DB60`**. **No second font table load exists** — no locale override
  path in code.
- Registration is **unconditional**: per-line callback `0x44D7F0` → `0x44D4D0`
  parses every line (helper `0x5C11B0`), registers it with the font system
  (singleton getter **`0x913C72`**, `vt+0x18` = RegisterStyle) and adds the
  name→GUID pair to a private dictionary (created `0x44DDEF`, clsid
  `0xBA2E7954`, handed over via `vt+0x34` before the `[Font Styles]` parse).
- Font-system slots: `vt+0x14` `GetStyleByGUID`, `vt+0x18` `RegisterStyle`,
  `vt+0x34` name dictionary, `vt+0x8C` line height, `vt+0x98`
  `GetStyleFromName`.
- The game fetches these styles **by GUID** from code:
  `WindowTitle 0xE2B14587` @`0x7EACA5`, `GenBodyMedium 0x4A809917` @`0x77993D`,
  `GenButton 0x4A809919` @`0x77BA93`,
  `MessageHeader/Body 0x4A809914/15` @`0x52CCE7`/`0x762F7E`,
  **`ChartLabel 0xE9C86B5E`** @**`0x0076DD91`** (the fetch is
  `0x0076DD8A call 0x913C72` → `push GUID` → `call [edx+0x14]`) and
  **`Legend 0xE9C86B5F`** @**`0x007A0747`**, plus `ChartTickText`
  @`0x76D63E`,
  `AdvisorHeadline 0xAA0F4AB4` @`0x7726B4`,
  `LoadScreenTitle 0x4A9C7970` @`0x777931`.
- File probe order (proven by disassembly): the game probes
  `<install>\Plugins\`, then the install root, then falls back to the DBPF
  copy. Deployment is **whole-file replacement, not a merge** — every style
  must be present.

**Law: `ChartLabel` and `Legend` differ in the last nibble and are NOT
interchangeable** (byte-verified). The **Graphs chart
legend** is `ChartLabel`; the **Data Views** legend is `Legend`. The
`make_fontstyle.py` entry `SIZE_SQUEEZE = {"Legend": 0.92}` therefore **does
not apply to the Graphs chart** — it renders at ChartLabel's raw size, and
any calculation that treats the chart as squeezed is ~8 % wrong. §5.4.6.

**Because FontStyle doubles EVERY style, an unscaled frame ALWAYS clips its
text** — including the unresolved-token case, which lands on the doubled
`Default` `0x68963C4C`, so name-vs-GUID does not save it
(`build_dialog_static.py` TEXT-SWEEP BATCH). That is why the static-dialog list
is long: it is not cosmetic polish, it is the necessary other half of 2x
fonts.

### 5.2 System B: the built-in HTML engine (all rich text)

> **Law: FontStyle can NEVER reach this path.** This is exactly why the
> community's DAT font mods report "font size does not work for news".

**Everything rich is HTML**: ticker roll items, news-reader headline rows,
story pages, advisor/message popups, tutorials, and the Credits — all rendered
by one engine whose item class is **`0xAA12E5F5`** (`id=2` in the five
message-box scripts). The exe carries literal templates in `.rdata`:
`'<FONT COLOR="#3f4967" FACE="Arta" SIZE=3><I>'` at `0xA83850` (unread
headline), `'<HTML>…<BODY BACKGROUND="sc4://HTML/46a006b0/%x"><FONT FACE="Arta"
SIZE=3>'` at `0xAB57A8` (story page), plus `0xA83820`, `0xAB5810`, bold headers
`0xA83880`/`0xAB51C0`, popup format string `0xA97F08` (with `sc4://` LINK
support) — and **189 locale LTEXTs embed their own `<font size="N">`**.

`SIZE=1..7` resolves through **two `.rdata` point-size tables**:

| Table | VA | Stock values | Set up by |
|---|---|---|---|
| FONT (`<FONT SIZE=n>`) | **`0xACD4A0`** | `{8,10,12,14,18,24,36}` | `push 7; push 0xacd4a0; call 0x8FEEB8` at `0x905C82` |
| HEADING (`<H1>..<H7>`) | **`0xAB4AD0`** | `{8,10,12,16,19,24,48}` | news builder `push 0xab4ad0; call [vt+0x84]` at `0x76A1FD` |

**Law: each rich window COPIES the tables at creation** — setter **`0x8FEEB8`** →
`this+0x1A8`. That is what makes a **PostAppInit** patch of the `.rdata` source
reach *every* instance the game will ever build, and it is verify-before-write
against the stock values above (a different exe build logs and skips).

**Law — the popup index derivation.** The advisor/message popup builders derive
their HTML size index from a *style's* point size:

```
idx = (4*size + 8) / 18          (sites in the 0x762F30 / 0x52CC70 regions)
```

Since the FontStyle files DOUBLE `MessageHeader`/`MessageBody`, with the tables
also scaled the popups would compound to **4x**. The fix is to retarget four
`push imm32` GUID sites at **stock-size clone styles** that exist solely as
index sources:

| Site | from | to |
|---|---|---|
| `0x52CCEE` | `0x4A809914` MessageHeader | `0x5C4B0914` MessageHeaderHtml |
| `0x52CD01` | `0x4A809915` MessageBody | `0x5C4B0915` MessageBodyHtml |
| `0x762F85` | `0x4A809914` | `0x5C4B0914` |
| `0x762F98` | `0x4A809915` | `0x5C4B0915` |

**Law: the three parts are COUPLED — breaking one regresses the others:**
(1) the table patch, (2) the stock-size `*Html` clone styles present in **all**
FontStyle files at **every** tier, (3) the Credits LTEXT size maps recalibrated
so they do not compound against the scaled tables.

### 5.3 Text geometry is font-derived in places

The ticker init (`0x77258B–0x772735`) caches the marquee rect, fetches
`AdvisorHeadline` (GUID `0xAA0F4AB4`) from the font manager (`0x913C72`,
`vt+0x14`, line height `vt+0x8C`), computes scroll geometry as
**`3 × lineHeight`**, and resizes the clip strip `0xCA2AEEC0` to
`SetSize(W, min(2 × lineHeight, H))`. **No pixel constants** — strip height and
scroll step both scale with the font style automatically.

The tooltip is the opposite case: its Plot (`0x798710`) wraps text at a
**HARDCODED 250px** (`push 0xfa` at `0x79880A` and `0x7988A9`), so with 2x
fonts the text wrapped narrow-and-tall and painted over the frame's rounded
corners. Cured by a byte patch to `250*factor`.

### 5.4 THE GRAPHS CHART AND ITS LEGEND — the PANEL builds it, the chart only draws it

**Read this before treating any chart legend as a chart problem.** Rewriting an
output rect only moves the collision somewhere else, because *the chart lays out
its legend* is false: **the chart never sizes a legend row.** It only paints and
destroys a list somebody else filled in.

This section is the general case, not one panel's anatomy: it is the clearest
worked example in the codebase of a **shared right-margin budget** (§5.0a
is the other) and of the rule that **a wrapped text box's width is an INPUT**.

> **Scope note — two measured objects** (`SDK-GAPS.md` G33). Everything
> below describes the legend as a **per-row right-margin COLUMN**, measured by
> disassembling `sub_76D3D0`. A second object sits beside it: the chart's own
> **full-width TOP BAND** at `chart+0x108`, logged live by `CHARTGEO` as
> **`(4,4,972,36)` with `bandH=32`**, which `src\UiSpike.cpp` writes as a
> coupled set (`+0x108/+0x10C/+0x110/+0x114`, gated on the field `bandH==32`
> rather than a pointer latch, because the chart object is replaced per graph
> switch). **Both writes ship**, and each rests on its own instrument — a
> disassembler for the column, a live `CHARTGEO` dump for the band. Keep both;
> dropping either loses a measurement. The measurement that ties them together
> is a single `CHARTGEO` line carrying `chart+0x108` and the legend child rects
> at the same instant, or a disassembly of what reads `chart+0x108` inside the
> draw path `sub_9B5ADE`.

#### 5.4.1 Ownership — one builder, two allocation sites, a draw-only list

The Graphs **panel** builder **`sub_76D3D0`** (`0x0076D3D0..0x0076E420`)
creates the chart and then lays out the **whole** legend column itself, ONCE
per chart build, from hard-coded literals plus the **chart window's WIDTH**.
The chart class only:

| Role | Where | What it does with `chart+0x228` |
|---|---|---|
| **draw** | `sub_9B5ADE`, main `vt+0x278` | walks the list, calls each node's `[+8]->vt[1]` |
| **destroy** | `sub_9B5990` | frees the nodes |

**`chart+0x228` is a DRAW LIST, never a layout list** — nothing on that path
reads a window width or recomputes a rect. Proven not by absence but by a
**whole-`.text` scan for the two allocation sites**, each of which has exactly
one call site image-wide:

| Entry | Allocator | Entry vtable | ONLY call site |
|---|---|---|---|
| legend **text block** | `sub_9B963D` (iface `+0xC4`) | `0x00ADE540` | **`0x0076E20A`** |
| legend **swatch** | `sub_9B5A84` (iface `+0xCC`) | `0x00ADE0DC` | **`0x0076E220`** |

Both call sites are inside `sub_76D3D0`. There is no second producer, so there
is no runtime re-lay to lose a race against, and **no post-hoc pass left to
jump**: the panel destroys and rebuilds the chart on **every graph switch**
(`0x0076D3DA-0x0076D409`), so a builder patch is born-correct for free at every
switch. This is the same shape as the Data Views legend (§6.2 / v2.37.0):
*scale the origin inside the game's own layout, never the step.*

**Warning: the diagnostic to reach for first.** If a control's rect is
wrong and every attempt to correct it after the fact just relocates the
problem, stop probing the OUTPUT and disassemble the **BUILDER**. A constant
that no instrument ever prints is still a constant — the 110 px gutter below
was invisible to every window-tree probe this project owns.

#### 5.4.2 Chart class dispatch — only ONE of three classes has a legend

**`0x0076D807`** switches on the chart class. The **legend row loop**
(`0x0076DE95..0x0076E373`) runs for **type1 only**:

| Type | Main vtable | Legend |
|---|---|---|
| **type1** | **`0x00AB4D08`** | **runs the row loop** — the shipped Graphs chart (every `CHARTGEO` log line reports `vt=00AB4D08`) |
| type2 | `0x00ADE648` | its own block, **no legend** |
| type3 | `0x00ADEEC0` | skips both |

The matching **iface** vtables matter for the plot-rect detour: `+0x30` holds
`0x9B1F1D` in type1 (`0xAB4C28`) and type2 (`0xADE568`), while type3
(`0xADEDE0`) **overrides** it with `0x9B2F92` and is deliberately left alone
(verify-before-write; `src\UiSpike.cpp` EARLYCHART).

#### 5.4.3 The SIX-CONSTANT right-margin budget (the whole mechanism)

Every legend column position is `winW − <constant>`. **None of the constants
scale.** All immediates below are byte-verified against the shipped exe:

```
plot right reserve 110 | checkbox left 108 | swatch left 90 (cbox) / 106 (plain)
| swatch 10x6 | swatch->text gap 4 | text right 4
```

| Field | VA | Encoding | Result |
|---|---|---|---|
| plot left / top | `0x0076DD5F` / `0x0076DD6A` | `mov …,0x2d` / `mov …,0x14` | 45, 20 |
| plot right | **`0x0076DD4E`** | `83 EA 6E` | `winW − 110` |
| plot bottom | `0x0076DD4B` | `sub eax,0x14` | `winH − 20` |
| checkbox rect | `0x0076E151/59/62/68` | `add ecx,0x10` / `lea ecx,[edx-0x5c]` / `add edx,-0x6c` / `call [ebx+0xDC]` | `SetArea(winW−108, y, winW−92, y+16)` = **16x16 AT EVERY TIER** |
| checkbox id | `0x0076E17B` | `add ecx,0x4000000` | `0x04000000 + seriesIndex` |
| swatch left | `0x0076E0F5` (plain) / `0x0076E1F8` (cbox) | `83 EB 6A` / `83 EB 5A` | `winW − 106` / `winW − 90` |
| swatch rect | `0x0076E233/39/3C` | `lea ecx,[eax+3]` / `add eax,9` / `add ebx,0xa` | `(L, y+3, L+10, y+9)` = 10x6 |
| text left | `0x0076E2AF` | `add ecx,4` | `swatchRight + 4` |
| text right | `0x0076E2C8` | `sub edx,4` | `winW − 4` |
| row 0 top | `0x0076DE79` | `mov [esp+0x18],0x14` | 20 |
| row advance | `0x0076E34B` | `lea edx,[ecx+eax+4]` | `rowY += fittedTextHeight + 4` |

**Only the row ADVANCE self-scales**, because `fittedTextHeight` comes back
from the font (§5.4.5). Every horizontal number is a literal.

#### 5.4.4 The plain-vs-checkbox split is ONE SKIPPED INSTRUCTION

`ebx = winW − 106` is written at **`0x0076E0F5`**; immediately after, at
**`0x0076E0F8`**, `cmp eax,2 / jbe 0x0076E200`. A 1-2 series chart (Income /
Expenses) takes the branch and keeps 106 with **no checkbox at all**;
multi-series charts fall through and **`0x0076E1F8` overwrites `ebx` with
`winW − 90`**, the 16 px difference being the checkbox column.

So "plain" and "checkbox" are not two layouts — they are one layout with one
extra store. Any change to the column must be expressed at **both** anchors or
the two kinds silently diverge.

#### 5.4.5 THE BOX IS AN INPUT, THE HEIGHT IS THE OUTPUT

The builder fetches its style once and reuses it for every row:

```
0x0076DD8A  call 0x913c72          ; font/style manager singleton (§5.1)
0x0076DD91  push 0xe9c86b5e        ; <-- ChartLabel, NOT Legend
0x0076DD98  call [edx+0x14]        ; GetStyleByGUID -> font object
0x0076DDA2  mov [esp+0x34], eax    ; frame slot +0x30 (one pending push)
   ...
0x0076E2DA  mov eax,[esp+0x30]     ; the loop re-reads the SAME slot
0x0076E2FD  call [eax+0xB8]        ; FitRectToText(str, len, &rect, 1, 1)
```

`vt+0xB8` is **`sub_896957`**, called with **multiline=1, wrap=1**. It takes
the branch at **`0x00896979`**, where `r->left` and `r->right` are **READ and
never WRITTEN**. Only `r->bottom` comes back, as `top + nLines*lineHeight`.

> **ENGINE RULE (general, and it explains several families at once).**
> For a wrapped text fit, **the box WIDTH is an INPUT and the HEIGHT is the
> OUTPUT.** You cannot learn the required width by asking the font — you can
> only ask "how tall does *this* width make it". A layout that hands the
> engine a fixed box therefore converts a bigger font into **more lines**, not
> a wider column, and the overflow appears at the BOTTOM of a panel whose real
> defect is on its RIGHT. Recorded as law 48.

This is the same distinction §5.0 draws from the other end (which *regime* a
`GZWinText` is in); here the regime is fixed at the call site — `wrap=1`
always — and the only lever is the box.

#### 5.4.6 `ChartLabel` `0xE9C86B5E` is NOT `Legend` `0xE9C86B5F`

Byte-verified at `0x0076DD91` (above). The two GUIDs differ in the last
nibble and are easily interchanged:

| Style | GUID | Who actually uses it |
|---|---|---|
| **ChartLabel** | `0xE9C86B5E` | **the Graphs chart legend** (`0x0076DD91`) |
| **Legend** | `0xE9C86B5F` | the **Data Views** legend (`0x007A0747`) |

**Consequence.**
`tools\fonts\make_fontstyle.py` carries `SIZE_SQUEEZE = {"Legend": 0.92}`, and
**that squeeze does not reach the Graphs chart at all.** The chart renders at
ChartLabel's **raw** size (13 pt stock, 26 pt at 2x, 20 / 39 at 1.5x / 3x), not
at a squeezed 24 pt. Any arithmetic that mixes the two is wrong by ~8 %.

#### 5.4.7 TEXT INK GROWS ×2.13, NOT ×2.00

17 label strings were measured at **both** 13 pt and 26 pt out of the game's
own rendered pixels. The ratio is **2.13** and never 2.00: Crime 28→59, Garbage 42→88,
Income 33→70, "Population by Age" 87→185. Per-point advance is ~6 % larger at
26 pt than at 13 pt (glyph-advance rounding inside the font).

> **The ×2.13 figure is a population mean, not a single sample.** `2.121` is
> one string's ratio: `Income` 33 → 70 (`emu_text_extent.py:157`). Over the
> full n=17 pair set (`emu_text_extent.py:140-158`) the figures are **mean
> 2.130, sd 0.026**, pooled **2080/975 = 2.133**, spread **2.085 (`Air
> Pollution`) .. 2.188 (`Commute Time`)** — and `emu_text_extent.py:37`
> states **"2.13 \u00b1 0.03"**: the \u00b1 0.03 band belongs to the mean.
> `src\CodePatches.cpp:589` carries 2.121, the single-string figure. The
> load-bearing fact is only that the ratio is not 2.00.

> **Therefore a box of `round(stockBox * f)` WRAPS MORE THAN STOCK.** Boxes
> must be sized from the FONT, not from `f`. That 6 % is also exactly the
> "Expense / s" shortfall the 0.92 `SIZE_SQUEEZE` was invented to hide.

**Warning: why every one of those numbers is a pixel measurement and not a font
query.** The shipped fonts are `<install>\Fonts\*.mxf` — Monotype MicroType
Express, magic `MXFN`. There is **no `.ttf`/`.otf` anywhere in the install**,
so PIL/FreeType cannot be pointed at Arta and no offline tool can ask the real
metrics. Everything in `tools\uimap\emu\emu_text_extent.py` is scanned out of
rendered pixels with a **stated residual of ±3.8 px**. `Arta (Bold).mxf` does
not exist, so a style's bold flag cannot change metrics either. **Advance at any
size other than 13 and 26 pt is MODELLED** — linear interpolation or
extrapolation between those two anchors, and `emu_chart_font.py` prints a `~`
for every such size. The extra line carried by two of the nine Garbage rows is
modelled the same way: the pitch formula at `0x0076E34B` has no
group-separator term, so the extra 15 px (1x) / 28 px (2x) is an extra line.

#### 5.4.8 What the budget does when the font and the checkbox grow

**The stock budget closes exactly**, which is how you know the decomposition
is right and not fitted:

```
108  =  16 (checkbox) + 2 (gap) + 10 (swatch) + 4 (gap) + 72 (text box) + 4 (right margin)
110  =  108 + 2        the plot's own clearance from the checkbox column
```

(72 px is the text box of the **checkbox** kind; the plain kind has no
checkbox and its box is **88**. Both are FIXED — §5.4.5.)

At 2x the checkbox **window** measures **32** wide live (`LEGENDCBOX` reports
`868..900`) and the 2x font wants a wider box, so ~52 px of content was pushed
into the **same 110 px** budget: `checkboxRight (900) == textLeft (900)`, and
the 17 px slot the swatch lives in collapsed to zero.

As arithmetic — **the swatch never moved, its BUDGET was eaten**:

```
swatch buried  <=>  cbox.L + cboxW(f) > swatch.L  <=>  16f > 18  <=>  f > 1.125
```

false at `f=1`, **true at every shipped tier** (1.5, 2, 3); at `f=3` the
checkbox eats the text column as well. That is why each rect-patch inside the
unchanged budget merely relocated the collision.

**The builder writes the checkbox 16x16 and the live window measures 32 wide at
2x** (`SDK-GAPS.md` G35). `SetArea` at `0x0076E168` takes `16x16` at every tier
(`0x0076E151` / `0x0076E159`), and disassembly refutes every candidate writer of
the 32, so the widening happens outside the builder. The fix is therefore built
to be **correct under both readings**:

| Reading | Prediction |
|---|---|
| `H_NONE` | nothing resizes it; it round-trips 16 |
| `H_SCALE` | something writes `round(16*f)` — numerically identical to the art cell `stripW/8` (32 / 24 / 48 at 2x / 1.5x / 3x) |

That requirement is what keeps the checkbox at the game's own 16 in the patched
`SetArea` (see below).

#### 5.4.9 The lever, and why it is a COUPLED PAIR

`CodePatches::ApplyGraphLegendBudgetScale` re-budgets the column **inside
`sub_76D3D0`** so it is BORN at `f`: **5 in-place `imm8` sites** plus **3
EQUAL-LENGTH block re-encodings**, verify-**all**-before-write-**any**.

| Block | VA | len | What it re-encodes |
|---|---|---|---|
| B1 | `0x0076E0E8` | 25 | plain swatch anchor `winW−106` → `winW−round(106f)` (imm32) |
| B2 | `0x0076E145` | 41 | checkbox rect `L = winW−strip`, **`R = L+16`, `H = 16` (UNSCALED, on purpose)** |
| B3 | `0x0076E1D6` | 42 | `AddChildWindow` + cbox swatch anchor `winW−90` → imm32 |

The four `winW` margins overflow `imm8` at `f≥2`, so they need `imm32` forms —
but there is **no trampoline and no code cave**: each replacement is
byte-for-byte the same LENGTH as stock, bought by dropping loads proven dead
across the seam. `B2` writes the checkbox WIDTH exactly once, as `L+16`, so
the left edge and the width can never split (law 15/43).

**Law — COUPLED PAIR (law 43) with EARLYCHART's plot right margin.** The legend
column and the plot's right edge budget the *same* gutter. Both arm together
behind the one `[Flyout] ChartScale` flag, and
`CodePatches::GraphLegendPlotRightMargin()` **returns 0 unless all 8 sites
took**, so EARLYCHART cannot adopt the new margin against an unpatched legend.
Taking one half without the other is the acceptance oracle's `H-EARLYCHART`
candidate, and it paints the plot border **inside** the checkbox column.

**Law: THE STRIP IS TABLED FROM THE ORACLE, NEVER COMPUTED.**
`f=1 → 108` (= stock), `1.5 → 178`, `2 → 240`, `3 → 371`. The oracle derives
it as `strip(f) = sc(16,f)+sc(2,f)+sc(10,f)+sc(4,f)+box(f)+sc(4,f)` with
`box(f)` sized from a provable glyph bound rather than from `f` (§5.4.7).
**A factor with no certified strip DECLINES rather than guessing.**

**Live acceptance:**

```
graph legend budget x2.00 (8 of 8 sites) - strip 240, cboxL winW-240,
  swatch winW-204 (cbox) / winW-236 (plain), gap 8, textR 8
EARLYCHART store (45,20,866,492) -> (90,40,732,472) budgetRM=244
```
matching the oracle's certified targets to the pixel — cbox `736..768`,
swatch `772..792`, text `800..968` (box 168), `plot.R 732`.

#### 5.4.10 The offline model, and the calibration rule it taught

All under `tools\uimap\emu\`, all following `emu_chart_range.py`'s conventions
(counts its checks, prints per-section summaries, ends `OVERALL: PASS`,
non-zero exit on failure):

| File | Role |
|---|---|
| `emu_chart_legend.py` | the layout model — reproduces stock 1x, live 2x **and the bug** |
| `emu_text_extent.py` | glyph metrics scanned from rendered pixels (±3.8 px) |
| `emu_chart_font.py` | what ChartLabel point size the measured stock layout implies |
| `gate_graphlegend_leftanchor.py` | 127 checks: shipped-exe stock bytes, `f=1` reduction, every tier × kind × **both** checkbox-writer hypotheses, plus a **capstone round-trip of the REPLACEMENT bytes** (length, instruction boundary, certified imm32, both branch targets). `--emit` prints the exact hex the C++ must write |

**The acceptance oracle** spans **ten** invariants × 11 candidate layout
engines × 2 font hypotheses × 4 tiers × 2 legend kinds = 10,708 checks, and is
mutation-audited: 22 of 22 mutations turn it red. The split is **6977 PASS /
789 FAIL-as-expected / 2914 SKIP / 28 UNDECIDED** — 10,708 is the CHECK count,
never a pass count.

The oracle reports **PASS / FAIL / SKIP / UNDECIDED** separately — a skip is
never a pass, and `UNDECIDED` is any check that turns on a difference smaller
than the text model's own **±3.8 px** residual. Its **ten** invariants: I1 order +
non-overlap, I2 visibility, I3 fit, I4 containment, I5 `f=1` reduction, I6
monotonicity + northstar, I7 round-half-up consistency, I8 coupled pair,
**I9 ROW PITCH** (consecutive checkbox child windows must not overlap; its
falsifier is the candidate `J-TAPTARGET`) and **I10 FRAME** (the chart-local
coordinate frame, asserted at f=1/2/3).

**Law: CALIBRATION IS MANDATORY, and `f=1` reduction is NOT sufficient.**
Candidate `A-FROZEN` reproduces the broken live layout 11/11 exact and then
**fails six of the ten invariants** — an oracle that cannot flag the known
defect cannot certify a fix. And **every modelled candidate, including each
failed patch, reduces to stock byte-exactly at `f=1`**: the §5.0a self-check
that a form "reduces to the game's own constant" is necessary but worthless on
its own here. Every expectation is therefore measured at `f≥1.5`.

**Warning: two gates certifying different targets is worse than one gate** (law 47).
A byte gate written against `round(108*f)` targets the candidate the oracle
calls `E-STRIPxf` and **rejects**; whichever gate ran last would decide what
ships. Reconcile gates onto ONE number before building, and make the loser's
target unreachable.

**Warning: verify emitted bytes against the gate's** (law 50). Writing B3's
imm32 at offset 26 instead of 25 puts it *inside* the preceding instruction —
a crash, not a layout bug, and visible only by diffing the emitted bytes
against `gate … --emit`. Any hand-encoded instruction block gets a capstone
round-trip **in a durable artifact**, never in a session transcript.

#### 5.4.11 Re-deriving this from scratch

1. Find the builder, not the control: scan `.text` for the **allocation** site
   of the entry object (`iface+0xC4` / `+0xCC` here). One xref = one builder.
2. Read every `winW − imm` in that function and write the budget out as a
   single sum. If the sum of the content exceeds the reserve at your tier, the
   defect is the **budget**, and no output rect can fix it.
3. Find the font fetch (`call 0x913c72`, `push <GUID>`, `call [edx+0x14]`) and
   confirm **which style GUID** — do not assume from the style's name.
4. Check the fit call's flags. `multiline/wrap = 1` ⇒ the box is an input;
   the only free variable is width, and width must be sized from measured ink.
5. Express the fix as a change to the builder's **constants**, prove it
   offline at `f ≥ 1.5` against invariants the current (broken) build fails,
   then encode it equal-length and round-trip the bytes.

---

## 6. Layout and placement laws

### 6.1 THE ALIGNMENT-MARKER RULE

> **Every tool-flyout script carries a hidden child `id=0x0000AAAA` whose size
> equals its SPAWN BUTTON, and the game places the panel at
> `panelPos = anchorAbs − markerOffset`, in NATIVE units.**

Once the subtree is scaled, the correct dock target is therefore
`target = anchorAbs − markerOffset(live)`, equivalently
`target = anchorAbs + f*R` with `R = nativePlacement − anchorAbs = −marker(1x)`
— which is what `kMayorFlyoutDock` stores.

**Why it is trustworthy (four independent confirmations):**
1. It reproduces all three locked, hand-tuned **god** docks to the pixel —
   terraform (22,262), terrain-fx (22,502), day/night (22,742) — which had
   taken ~15 build cycles to find by eye.
2. It predicted the game's native mayor placement exactly: Landscape marker
   (3,27), button abs (28,398) → (25,371) = what `MCAL` measured in game.
3. Two independent derivations agreed on (22,344) for Landscape
   (`button + 2R` and `button − marker2x`).
4. Self-consistency check: flyouts 1 and 2 both land at (22,344) because each
   marker sits lower by exactly the button pitch, cancelling out.

It also explains the special case the god constant table needed: the shared
window `0xCA35CBED` needs two offsets (terrain-fx 40 / day-night 160) because
**swapping the SCRIPT moves its marker**.

**Law: NEVER SCALE A MARKER — not at runtime, and not in shipped data.**
Doubling the advisor strip's marker (229,63) along with the rest of the subtree
births the strip shifted by exactly `−(229,63)`: native (209,1412) →
**(−20,1349)**, proven live. `double_subtree_areas` skips `id=0x0000AAAA`
tags (19 edits per script instead of 20).

**Markers do more than dock flyouts:**
- They encode **designed panel interlock**: `I-2bc90671` carries
  `<LEGACY clsid=GZWinCustom id=0x0000aaaa area=(-37,12,23,56)
  caption="0xc988bc79" winflag_visible=no>` — composite origin (139,1413) +
  (−37,12) = **(102,1425)** = exactly where the dock puts the Mayor Mode button
  (cluster (5,1388) + child (97,37)). The designers encoded the intended
  relative placement of two independent panels as a ghost rect. The 800x600
  twin carries the same ghost at (−37,47) — per-resolution anchoring, same
  mechanism.
- A second ghost `0xAA6767AA` captioned `"<alignment target>"` at (413,140)
  marks the ticker slot.
- They glue **marker-composed sibling roots** (My Sims, advisors) — §3.6.
- **Their presence in a script is weak evidence that a root is view-parented**
  (used as the rationale for pre-emptively listing `0x0C525B9E` Select-A-Bridge
  in `kNeverScaleIds`).

**TRAP: one window id can carry TWO scripts.** `0x49923239` is god/terraform
(125x291 → 250x582, marker (4,90)) **and** mayor/Landscape (125x249 → 250x498,
marker (3,27)). A single fixed offset can never serve both — a **mode gate** is
what separates them, and the only gate verified in all three states
(pre-founding god / founded god / founded mayor) is **"mayor HUD `0xE9889775`
is visible"**. **Warning:** do **not** use the toolbar button's ENABLED flag: it reads
true in pre-founding god mode and flickers between sweep and dump.

**TRAP: founding a city changes what a window IS.** `0x0A78827A` is inert
before founding and **is the god toolbar** (script `I-aa53e3ea`) in a founded
city, where it belongs in both `SCALED_WINDOW_IDS` and `kGodPanelIds`. An
observation taken pre-founding describes a different tree; re-take it in a
founded city before acting on it.

### 6.2 Never scale what the game already computed

Three members of one family, each paid for with a shipped bug:

| Family member | Rule | Evidence |
|---|---|---|
| **Alignment markers** | never scale, anywhere | §6.1 |
| **`kDataScaledSubtreeIds`** (data-pre-scaled subtrees) | scale the ROOT at runtime, **never recurse** | children already ship 2x in the `.UI`; recursing = 4x |
| **`kFontSizedIds`** (font- or art-sized controls) | scale POSITION, **leave SIZE alone** | "Change style every" `0xCBC61559`: three fixed siblings are 238x18 → 476x36 cleanly, but this one measured **526x64** live where 2x of its 101x16 design is 202x32 — the mod's DLL had already sized it to fit its **2x caption** (263x32), so doubling it again gives a 64-tall box that centres its radio glyph ~16px below the 36-tall rows. Year spinner `0xABC61550`: measured **60x72 inside a 98x44 parent**, overflowing by 32px and clipping the DOWN arrow away — it is sized from its own 2x arrow art |

Expected log shapes: `font-sized 0xCBC61559 pos (2,63)->(4,126), size 263x32
kept.` **Trap symmetry:** row misaligned again → the id fell out of the list;
row now too SMALL/clipped → a genuinely fixed-size control was wrongly added.

### 6.3 The game RE-IMPOSES init-cached geometry (so runtime loses)

Some controls have their geometry written by game code **after** the sweep, on
a schedule the mod does not control. Three measured instances:

| Control | Re-imposition | Cure |
|---|---|---|
| **Ticker marquee `0xAA12F33C`** | the game re-imposes its **init-cached** rect every roll tick — one `width 676 -> 1352` apply appears in the log and the next dump reads 676x90 again, so 2x glyphs laid out in a 1x width wrapped mid-word | **DATA**: scale the marquee's design width in the shipped `.UI` (676→1352 in `G-96a006b0`, 484→968 in `G-08000600`) so the init cache STARTS scaled and the game's own resets re-impose the scaled value. The DLL then **never touches it** (`kAdviceListNeverTouchIds`) |
| **RCI columns** | re-imposed after the sweep | a re-log/re-check pass (`rciRecheckCountdown`) |
| **Data Views legend** | the view-select code **re-lays the legend on EVERY selection**, mixing 1x origin constants with 2x font-derived pitches (DPROBE-measured: rows re-set to container-rel x=278, y=24+36k; chips to (371,61+36k)) — label rows end up buried under the 512-wide map | **DVPIN pin-back pass**: pin all 21 laid-out children (rows `0x8A909E00-08`, chips `0x8A909E10-18`, labels `0x8100`/`0x8101`, map `0x4203`) to scaled design geometry every sweep while the page `0x8A2871C3` is visible. The game re-imposes at select time; the sweep snaps it right back |

**Diagnostic rule:** if a value is right in one log line and wrong in the next
dump with no mod code in between, you are fighting a re-imposition — move
the fix to DATA or add a pin-back pass. Do not retune the constant.

### 6.4 THE TIER SYSTEM — one number, and what is derived from it

*The tier decision is an engine-facing fact: it fixes `f` for every rule in
this document.*

**There is exactly ONE scale number in the DLL**: `Settings::spikeScaleFactor`
(`src\Settings.h:44`), written once at boot from `ScaleTier::Decide`
(`src\ScaleTier.cpp:1651`, called `src\SC4UIScaleDllDirector.cpp:218`) and
mirrored into namespace-scope `gTierF` (`src\UiSpike.cpp:169`) for the hooks
that cannot see the settings object. **UI scale and TEXT scale are locked 1:1
by decision of record; there is no text knob.**

`Decide(width, height)` — walk the package table **largest first** and take the
first tier that satisfies all three:

```
kWidestDesignPx  * f <= width      kWidestDesignPx  = 880   (city composite status panel)
kTallestDesignPx * f <= height     kTallestDesignPx = 558   (Graphics Options dialog)
f <= min(width/800, height/600)                             the DENSITY CAP
```

…and whose **art dat is installed** — `PackageInstalled()` looks for
`z_SC4UIScale_SelectiveArt<tag>.dat`, live **or** `.x1-disabled`. No match ⇒
`return 1.0f` = true stock, every scaling subsystem off.

**Law: THE DENSITY CAP IS NOT REDUNDANT WITH THE TWO DESIGN MINIMA.** The two
minima only assert that the widest and tallest *individual* design elements fit.
The cap asserts the whole screen still holds an 800x600-equivalent workspace.
Dropping it admits resolutions with **no slack**: a panel then crosses
`frameW/4`, flips `ScalePanelRoot` to the centre-anchor branch and shears the
polls panel over the RCI meter (measured −256px at 1400x1050, −385px at
1920x1080).

**Warning: `kPackages` declares FOUR tiers, not three** (`src\ScaleTier.cpp:43`):
`4.0f/-4x`, `3.0f/-3x`, `2.0f/-2x`, `1.5f/-15x`. **No `-4x` package is built**,
so `PackageInstalled` always rejects it and 4x is unreachable — but the
table is the thing `Decide` iterates, so anyone who stages a `-4x` art dat turns
4x on with no other change. Docs that say "three tiers" are describing what
ships, not what the code will select.

**One tag gates two layers.** `SyncStaticLayers` (`src\ScaleTier.h:27`) picks a
single tag and uses it for **both** the art dats and `FontStyle<tag>.ini`, and
stashes every other tier's dats as `.x1-disabled`. *"UI 2x + text 3x" is not
expressible at any layer* — not in settings, not at runtime, not in packaging.

**Which constants are tier-DERIVED, and which are not:**

| Kind | Rule | Integer-tier behaviour |
|---|---|---|
| window geometry | `ScaleRound(v, f)` = `RoundHalfUp(v*f)` (`src\UiSpike.cpp:5385`) — **children round inside the PARENT's design frame**, not independently | exact |
| art sheet dimensions | `ScaleDim` + the ROLE rules (§4.6c) | **provable no-op** |
| blit destination extents | **Law: FLOOR, never round up** — `RoundHalfUp(srcExtent*f)` with an odd source at f=1.5 manufactures a destination column that has no source pixel (the stray line down the right edge of the sun/moon rings) | exact |
| byte-patched exe constants | re-encoded per tier by `CodePatches.cpp`; each must **reduce exactly to the stock byte at f=1** | that reduction is the control |
| a few things that are **NOT** tier-derived | the alignment marker `0x0000AAAA` (§6.1); the Graphs checkbox at `16x16` (`0x0076E151`/`0x0076E159`); `CamGraphLabels.dat`; `WebText.dat`; `MenuFix.dat` | n/a |

**Law — THE HOUSE CONTROL, stated once so every new metric inherits it.** An
integer factor is *structurally* immune to the whole fractional-tier defect
family — `v*f` is already whole, so floor, round-half-up and round-half-away all
agree and every snap short-circuits. **Therefore any new metric or gate MUST
read exactly ZERO at 2x and 3x. If it does not, it is measuring itself, not a
defect.** Corollary: **a "known residual" that exists at ONE TIER ONLY is the
defect, not a residual.**

---

## 7. Timing model

### 7.1 Windows are BORN 1x

`.UI` scripts carry stock geometry **by design** as the DEFAULT — so
**every window the game creates or re-creates arrives at script-declared 1x
size** (§3.2), and anything the engine rebuilds mid-session reverts to
script-declared size until something scales it again. **"Born 1x" is the
default, not the rule, and the exceptions are the ones that bite.** TWO
builders write `area=` into the shipped scripts, so a window is born 1x only
if NEITHER of them owns it:

1. `build_selective_safe.py::double_subtree_areas` (`:646`) rewrites `area=` on
   every descendant — never the root, and alignment markers `0x0000AAAA` are
   skipped (`:701-702`) — of **TEN roots across FIVE call sites**: advisor
   strip `0x6A15C767` (`:1963`), the **four** budget roots (`:2010-2011`), the
   three Graphs roots (`:2033-2035`), the U-Drive-It dashboard `0x4BCB938A`
   (`:2057`) and the console variant `0xEC1A5CBF` (`:2082`). This runs at
   **every tier**, not only fractional ones.
   `seat_faces_on_apertures` (`:864`, rewrite at `:924-926`, called `:1976`)
   adds **no new** pre-scaled windows: it re-seats 7 children that
   `double_subtree_areas` already wrote, by at most 1px, in each of the two
   advisor scripts — 14 `area=` sites, the same 7 ids twice (`:798-800`) — and
   **only at a fractional tier** (`:918-919` writes nothing when the delta is
   zero; `:1985-1987` FATALs if it ever moves anything at an integer factor).
2. `build_dialog_static.py` scales the `area=` of **every node it owns, ROOTS
   INCLUDED** — `scaled_area()` (`:783-789`) applied to `walk(roots)`
   (`:1418-1421`) — across its whole `TARGETS` corpus (`:292`).

**Neither is repaired downstream, and that is deliberate on both sides.**
`ScalePanelRoot` **returns before the child loop** for any
`kDataScaledSubtreeIds` member (`src\UiSpike.cpp:14568-14573`; list at
`:5373`), and every static-dialog root sits in `kNeverScaleIds`
(`src\UiSpike.cpp:4778`; e.g. Establish City `0x6A414973` at `:4806`) because
running the sweep on top of the doubled script double-scales it — measured
868x468 -> 1736x936 (`:4803`). See also `build_dialog_static.py:755-757`.

**Warning: so for these windows the answer to "the sweep will fix it" is NO.** A
wrong number a builder writes there ships exactly as written — the advisor
row and the 132 pre-scaled buttons are both that shape. The 1x-birth rule above
holds for every window OUTSIDE those two builders' scope.

### 7.2 The sweep is reactive, and its gate — not its latency — is the flash

`UiSpike::TickCheck` runs `IncrementalPass()` **every tick (~16 ms)**, not a few
times a second (`UiSpike.cpp` TickCheck; `kAlwaysScaleCityIds` comment). It
re-walks the 3D-view subtree idempotently: new panels get the full
treatment, known panels get a descendant sweep, already-scaled windows are
skipped by `Classify()`.

> **Law — MEASURED MECHANISM of the 1x mode-transition flash: it is the VISIBILITY
> GATE in `ScalePanelsUnder`, not sweep latency.** A hidden panel is skipped, so
> a panel that spends city-load hidden is still 1x when a mode switch shows it.
> It paints 1x, and only the NEXT tick scales it.

It follows that the flash count scales with coverage — the more panels are
scaled, the more transitions can flash — which is why it reads as universal.

Safety engineering the sweep depends on, all learned the hard way:

- **Idempotent per-window scale records**, keyed by window pointer, and
  **never cleared between cities** — the game **reuses window objects across
  city loads**.
- **PURGE-ON-FRESH-ROOT**: a `Fresh` root proves the game rebuilt the subtree,
  and new objects land on **recycled heap addresses** that can still carry
  records of destroyed windows; `id=0` children then collide (0==0, size
  matches neither) and stay stuck at 1x forever (the region-switch population
  bug). Erasing every record under a fresh root makes a switch
  bookkeeping-identical to a fresh boot.
- **Tombstones** for game-managed dynamic controls, and for the double-scale
  guard (`target WxH exceeds frame` → touch nothing, record dead, never retry).
- **Liveness re-verification before every mutation**; **deferred execution** —
  the tree is never walked during `PostCityInit`; `inPass` re-entrancy guard so
  a nested message pump cannot start a second walk on the same stack.

### 7.3 The three cures (all make the window BORN 2x) and the one permanent ban

| Cure | Mechanism | When it is the right answer |
|---|---|---|
| **1. DATA pre-scale** | `double_subtree_areas` ships the subtree already 2x in the `.UI`; the root stays runtime-scaled (so HUD edge-anchoring still works at any resolution) and is made **root-only** via `kDataScaledSubtreeIds` | **The game reads the geometry before any sweep can run.** Advisor strip: the briefing portrait always rendered correctly because its head binds when the briefing is first OPENED (after scaling), while the strip's 7 heads bind during **CITY LOAD** — framing is fixed at **BIND TIME** from the then-current geometry. Verified exact: 16/16 children match `2 × design` |
| **2. Pre-scale while HIDDEN** | `kAlwaysScaleCityIds` — scale by id even at `vis=0`, gate only the *dock MOVE* on visibility | The panel exists but is hidden until a mode switch/open. The principled rule that also keeps the layers coupled: **IF WE SHIP 2x ART FOR A PANEL, IT MUST BE PRE-SCALED WHILE HIDDEN.** Proven five times (region flyouts, news reader, budget popups, advisors, and the v2.22.4 batch) |
| **3. Scale at birth** (the general fix) | **The settle-gated `SetFlag` detour**, which solves city-load panels — generation 9. Fire from `cGZWin::SetFlag` (base impl `0x0099DB6B`, hooked once, on the game's own stack, still firing after city init returns) the moment the subtree reports its **full design child count**; scale via `ScalePanelRoot` so scaleMap makes the sweep a no-op; run any one-shot-surface recreate **in the same action**. Measured +109–328ms vs the sweep's +968ms; FLASHSET fell silent for the dock | The three refuted routes, so nobody retries them: the visibility setter as a *transition* hook (windows are BORN visible — the `[+0xC8]=0x8903` fact below); the message queue (never pumps during the load tail); geometry mutation inside `PostCityInit` (crashes at ~25 windows; two byte writes are fine). The `.UI` deserializer completion path is not needed |
| **Law — BANNED: paint suppression** | — | `FlashGuard=1` suppressed Plot for descendants of the god parent — but that parent is an ancestor of far more than the flyouts, so HUD windows went unpainted (black box, bottom-left panel). **Kept permanently at 0. Fix the TIMING, never the PAINTING.** |

**For runtime-painted content the lever is the BUFFER, not the window:**

- **force-recreate-buffer** — corrupt the cached width `[buf+0x1C]` so Plot's
  validity check fails and it rebuilds the buffer at the CURRENT window size.
  Self-stabilising. This is what took the disaster flyout from a stale 141x339
  buffer to a correct 282x678.
- **destroy-and-recreate the display surface** — for any instance holding a
  one-shot surface (MINIMAP / DVMAP / UDMAP). **Law: the recreate is only half of
  it: the recompute that follows MARKS the map dirty and the paint is
  message-driven, so it lands after the panel is visible.** Drive the game's own
  bake synchronously in the same action, while hidden (§2.4.3).
- **code-only atlas upscale** — read the game's own art out of the draw
  context and re-blit it bigger (§2.3).
- **byte patch** — for geometry that exists only as an immediate.

**Law: ONE-SHOT CAPTURES ARE FRAGILE.** The Plot hook captures the strip's
natural field values once; any other writer that runs first poisons it (a
sweep-side write captured 88 as "natural" → forced 176 → 4x pitch everywhere,
most menus broken). **Sweep-side code may INVALIDATE, never write**
(`SUBHEAL`).

**Law: idempotency must survive birth-scaling**: the sweep WILL revisit a
birth-scaled window and `scaleMap` must recognise its own work — that is the 4x
lesson in general form.

---

## 8. Known exe VAs (1.1.641.0 Steam, ImageBase 0x400000)

`file offset = VA − 0x400000` for every section referenced. Registries first,
then subsystems.

### 8.1 Registries and infrastructure

| VA | What | Used for |
|---|---|---|
| `0xB08F78` | **`{clsid → class-name}` registry**, `.data`, 648 entries, 8-byte stride `[clsid][char* name]`; name pool ~`0xA89000` | naming every custom clsid seen in `.UI` |
| `0xB16FA0` | standard clsid/iid/descriptor table, 12-byte stride | GZWinBtn/BMP descriptors |
| `0x4662B0` | window-class registration (`push <factory>; push <clsid>; mov ecx,esi; call 0x90E133`) | finding factories |
| `0x90E133` | the registration callee | — |
| `0x99C81B` / `0x99C82A` / `0x99BC53` / `0x994EE4` / `0x99BCE1` | `GetW` / `GetH` / `GetL` / `GetArea` getters | reading the `this+0xA8..0xB4` rect |
| `0x0099DFA9` | **`GetChildWindowFromCursorPoint`** (router, inherited by ~90 classes) | hit-test path §2.2 |
| `0x0099C97C` | base **`IsPointInMe`** | hit-test path |
| `0x0099BBBE` | refined mask dispatcher (slot 149) | hit-test path |
| `0x0099BE4C` | `GetNotificationTarget` (slot 87; the per-class draw `GZPaint` is slot 88, §2.1) | vtable diffing baseline |
| `0x00AC1400` | **cIGZBuffer class vtable**; `Init 0x8269B0`, `GetW 0x808620`, `GetBufferArea 0x8268C0`, **`Blt 0x826AD0`** (delegate `0x826210`) | §2.3 |
| `0x602B00` | the standard image loader (TGI → image) | every code-bound art path |
| `0x5FD480` | `GetProperty` (exemplars) | ItemIcons |

### 8.2 `.UI` deserialization and fonts

| VA | What |
|---|---|
| `0x94E516` | **`GZWinText` `.UI` deserializer** — honours only GUID-valued `font=` (registered at `0x951D29`) |
| `0x94B995` | `<LEGACY>` tag registration site (not a handler; the tokenizer suspect is ruled out — §3.4) |
| `0x95BC5F` | round-trip serializer — writes `font=0x%08x` |
| `0x99D7C8` | main `vt+0x1C8` generic property store (where a string `font=` dead-ends, property `0xFAA4AE85`, zero consumers) |
| `0x94CF0A`, `0x94F9E4`, `0x950657`, `0x950C94`, `0x959491` | other deserializers that DO call `GetStyleFromName` |
| `0x44DB60` | font init |
| `0x44DE23` / `0x44DD7F` | `[Font Styles]` / `[Font Aliases]` section-name refs (one each) |
| `0x44D7F0` → `0x44D4D0` | per-line parse/registration; helper `0x5C11B0` |
| `0x44DDEF` / `0x44DE1C` | name→GUID dictionary creation (clsid `0xBA2E7954`) / handoff |
| `0x913C72` | font-system singleton getter (`vt+0x14` GetStyleByGUID, `+0x18` RegisterStyle, `+0x34` dictionary, `+0x8C` line height, `+0x98` GetStyleFromName) |
| `0x9C19C8` / `0x9C16FD` | cGZWinText ctor / `SetFontStyleByGUID`; main vt `0xADFEB8`, iface vt `0xAE0118`, iface at `+0xD8`, GUID at `this+0xE0`, Default `0x68963C4C`; creation helper `0x996E90` |

### 8.3 The HTML engine

| VA | What |
|---|---|
| **`0xACD4A0`** | FONT point-size table `{8,10,12,14,18,24,36}` — **patched ×factor** |
| **`0xAB4AD0`** | HEADING point-size table `{8,10,12,16,19,24,48}` — **patched ×factor** |
| `0x905C82` | engine setup: `push 7; push 0xacd4a0; call 0x8FEEB8` |
| **`0x8FEEB8`** | the table setter — **COPIES into each rich window at `this+0x1A8`** |
| `0x76A1FD` | news builder passes the heading table (`push 0xab4ad0; call [vt+0x84]`) |
| `0x762F30` / `0x52CC70` | popup builders' `idx = (4*size+8)/18` derivation |
| `0x52CCEE`, `0x52CD01`, `0x762F85`, `0x762F98` | the four `push <style GUID>` retarget sites |
| `0xA83850`, `0xA83820`, `0xAB57A8`, `0xAB5810`, `0xA83880`, `0xAB51C0`, `0xA97F08` | `.rdata` HTML templates (headline / story page / bold header / popup format) |
| `0x8FA317` | rich-item `GetClassID` (clsid `0xAA12E5F5`); creation sites `0x443FC9`, `0x76A182`, `0x78CE11`, `0x7931F0` |

### 8.4 HUD controls

| VA | What |
|---|---|
| `0x466170` / `0x7A9770` / **`0x7A9500`** | cSC4WinRCI factory / ctor / **Draw** (window-derived, no pixel constants); vt `0xAB8628`, main `0xAB8884` |
| `0x7ED362` | RCI controller xref (binds demand ids + colours only, never sizes) |
| `0x4661A0` / `0x7BF5E0` / **`0x7BF0A0`** | cSC4WinTrendBar factory / ctor / **Draw** (art-size-derived); vt `0xABA430`, main `0xABA68C`; value constants `0xABA3EC/F0/F4`, `0xABA414/418/41C` |
| `0x7ED4AC` | polls controller — loads the two code-bound TrendBar TGIs, `GetChildAsRecursive(id, iid 0xCA5C2F84)` then `[vt+0x10]` SetImages |
| `0x4661D0` / `0x79C560` | cSC4WinGenTransparent (`0x89E1567C`) factory / ctor; vt `0xAB7358` |
| `0x793080` / `0x793190` / **`0x7931F1`** / `0x949ADE` | cSC4WinAdviceList QI / Init / **item-create (`SetArea(0,0,GetW,GetH)`)** / no-op draw-self; vt `0xAB58B0`; iface iid `0xCA1492A2` |
| `0x77258B–0x772735` | ticker init (caches marquee rect, `3 × lineHeight`); `0x7726E2+` clip-strip resize; `0x7726B4` AdvisorHeadline fetch |
| `0x7EE64D` / `0x7EE668` | HUD binds `cIGZWinText` (iid `0x212CDC1F`) for funds/pop |
| `0x7EE69E` | HUD loads its `.UI` by TGI `{0x96A006B0, 0x2A2AED99}` |
| `0x7E86C0–0x7E8A80` | mayor-rating controller |
| **`sub_7E8510`** | the rating-fill composer — builds one buffer per rating tick (`row = artH*(rating+100)/200` of `{46a006b0,14015549}`, replicated to all rows) and pushes it via `cIGZWinBMP::SetImage` on EVERY firing, even delta=0 (§2.6) |
| `0x7E883B` | `GZWinMoveTo` re-assert of the meter position from the `[ctl+0x378/0x37C]` latch, every refresh (RATEANCHOR) |
| `0x7ED224` | polls-panel init — binds the small rating meter to the SAME `14015549` sheet through the GZWinBMP family |
| **`0x7E87B1`, `0x7E89D7`, `0x7E8A02`** | the three `imul r32,r/m32,7` sites — **7 px per rating point, ARROWS ONLY** (reveal `SetW(delta*7)` + reposition; no pixel constant exists in the FILL chain — §2.6), bytes `6B F6 07` / `6B C9 07` / `6B C9 07`, patched imm8 at `+2` |
| `0x7E8AF4` / `0x7E8B0A` | mayor face art swap (code-bound `0x14315E60`/`62`) |
| `0x798710` | tooltip layer Plot (window `0x2AAB8CC1`, class vt `0x00AB6770`) |
| **`0x79880A`, `0x7988A9`** | tooltip `push 0xfa` = the hardcoded 250px wrap width (patched to `250*factor`) |
| `0x41DE20` | advisor 3D-head binder (creates each head ONCE per controller slot) |

### 8.5 Flyouts, menus, minimaps, dialogs

| VA | What |
|---|---|
| **`0x0079B0E0`** | disaster/sub-flyout **container Plot** (vtable `0x00AB6AA8`); realloc check `0x79B117` |
| **`0x0079AA70`** | **strip Plot** (vtable `0x00AB6D88`) |
| `0x0079A180` → **`0x0079AE30`** | container `IsPointInMe` override → its slot-121 claim (`local_x >= width − [this+0xE0]`) |
| `0x8D8BC0` | arc / tiling helper used by the container |
| `0x00ADF6A0` / **`0x9BC325`** | **GZWinBMP class vtable / its Plot override** — `dst = origin + srcW×srcH`; 3-state branch divides src by 3, helper `0x8D8800`; mouse overrides `0x9BC2D0` / `0x9BC27C` |
| **`0x9BC57E` → `0x9BC447`** | `cIGZWinBMP::SetImage` → its tail, which **rewrites the live `imagerect` `[win+0xE8]` to `(0,0,min(areaW,imgW),min(areaH,imgH))` from the window's area AT THAT MOMENT** — the crop latch (§2.6) |
| `0x99C837` | `GZWinBMP::SetArea` — **never touches `+0xE8`**, which is why the latch survives every resize (§2.6) |
| `0x99CF6A` | base draw-rect recompute at vt`+0x184` (slot 97), run inside the SetArea chain — what makes `cSC4WinTrendBar` latch-immune (§2 catalogue row) |
| `0x7BEEB0` | `cSC4WinTrendBar::SetImages` (main vt `0xABA68C` slot 4) — stores POINTERS only, no geometry snapshot |
| `0x00ADDAF0` | button class vtable |
| `0x78EDC9` / `0x78EE09` / `0x78EE11`; `0x7ECB1E` / `0x7ECB44` / `0x7ECB4C`; `0x7F0359` / `0x7F038F` / `0x7F0597` | the three ItemIcon read+stamp sites (`0x8A2602B8`, then `0x856DDBAC` + `0x6A386D26`) |
| `0x79B6B0` / `0xAB6FE4` | menu-item object ctor / vtable |
| `0x7EC41C–0x7EC586`, `0x7F5944–0x7F5C6F`, `0x7E9150`, `0x7E97A0`, `0x7F21B0` | menu / toolbar handlers |
| `0x76E7C7–0x76FD25`, `0x7717EA–0x77157C` | My Sims strip builder (container `0x698894D3` @`0x76E8FB`/`0x76EA11`/`0x76FD02`; inner `0xCA1F1D9C` @`0x76E7C7`+; templates `0x22220000` @`0x76EB67`/`0x76F889`/`0x76FAD8`/`0x76FBBF`; chooser `0x22220055` @`0x7717EA`/`0x7718CA`) — the `containerWidth / slotPitch(≈135)` loop lives here |
| `0x7A5E4B` / `0x7A60CC` / `0x79DF10` / `0x79DFB0` / `sub_9AFCFE` | Data Views **expand** path: switch / jump table / two state-flip helpers / show-hide primitive. **Proven pure show/hide — no moves, no resizes** |
| `0x7A6580` | `GetClassID` returning `0xCA318388` for the DV map child `0x00004203` |
| `sub_7A2F60`; `0x7A301E`; `0x7A3094`; `0x7A4884` | DV renderer; live-rect read `vt+0xBC`; buffer create (`{9,32bpp}`, clsid `0xC470D325`); 77-case per-view painter table |
| **`0x7A7840`**; `0x7A8B57`; `0x7A8C18–0x7A8C61` | minimap recompute (**MARKS dirty, does not paint** — §2.4.3); the game's own init call site; the destroy+recreate pattern to replicate |
| **`0x7A8640`**; `0x7A8721` | minimap **message handler** (`__thiscall` on `this+0xD8`; server `[0xB43CCC]`, ids `0x99EF1142`/`0x99EF1143`) → the bake's **only** call site (§2.4.4) |
| **`0x7A7FF0`**; `0x7A66F0` / `0x7A67F0` | the **terrain bake**, one pass per 16x16-cell tile (§2.4.5); the raster→surface transfer |
| **`0x7A8560`** (15 B) / `0x7A856F` (0x21 B) / **`0x7A8628`** (5 dwords) | the bake's zoom **dispatch** / its five stubs / the jump table — blitters `0x7A6EE0` x4, `0x7A6E60` x2, `0x7A6A70` 1:1, `0x7A6AD0` /2, `0x7A6BD0` /4. **Law:** `cmp ecx,4 / ja` is **UNSIGNED**, so `zoom=-3` skips every tile silently (§2.4.6). Patched in memory by `ApplyMiniMapX8Bake`; gated by `_tests\Test-MiniMapX8Bake.py` |
| `0x7A8590`–`0x7A85AA` | the shared blitter call tail — `cdecl(dst, blitSize*4, src16x16, 0x40, side, side)` |
| `0x7A882A` | the data-**CELL** loop (`shl`/`shr` by `zoom+4`) — **no table, no bound**, which is why cells paint at zoom −3 while the terrain base does not |
| `0x7A7570`; `0x7A6590` | raster `{ptr,w,h}` free+malloc (`0x5E5620` / `0x5E55E0`, store `0x7A75BB`); the handler's raster validity test |
| `0x78DFF0` | **generic message-box builder** — loads `I-ea8cc3c6` for every code-driven confirm |
| `0x778245` | dialog factory (instantiates the Delete-City confirm script) |
| `0xAB9230` / `0x7AFE78` | per-size Import-City title LTEXT table / its use site |
| `0x4F4B78` / `0x4F4E37` | Audio playlist checkbox art loads (`{46A006B0,14416244}`) |
| `0x4B8314` / `0x7AC651`; `0x44DEC7–0x44E268` | U-Drive-It bubble art pushes; the 15-entry per-mission glyph table |
| `0x77A495–0x77A837`, `0x780952–0x78910C` | news-window + advisor-panel code-bound art constants (`0x140155B4..F7`, incl. c8, cb, cc, d0–d7) |

### 8.6 The Graphs panel, its chart and the legend budget (§5.4)

| VA | What |
|---|---|
| **`0x0076D3D0..0x0076E420`** | **`sub_76D3D0`** — the Graphs PANEL builder; it lays out the entire legend, the chart does not |
| `0x0076D3DA-0x0076D409` | chart destroy + rebuild — runs on **every graph switch**, which is what makes a builder patch born-correct |
| **`0x0076D807`** | chart-class dispatch; the legend row loop runs for **type1** (main vt `0x00AB4D08`) only — type2 `0x00ADE648` has a no-legend block, type3 `0x00ADEEC0` skips both |
| `0x0076DE95..0x0076E373` | the legend ROW LOOP |
| `0x0076DD8A` / **`0x0076DD91`** / `0x0076DD98` | style manager `0x913C72` → `push 0xE9C86B5E` (**ChartLabel**) → `call [edx+0x14]`; stored at frame `+0x30`, re-read at `0x0076E2DA` |
| **`0x0076E2FD`** | `call [eax+0xB8]` = **`sub_896957`** `FitRectToText(str,len,&rect,1,1)`; branch `0x00896979` **READS** `r->left`/`r->right`, writes only the bottom |
| `0x0076DD4E` / `0x0076DD4B` | plot right `winW−110` (`83 EA 6E`) / plot bottom `winH−20` |
| `0x0076DD5F` / `0x0076DD6A` | plot left 45 / top 20 |
| `0x0076E0F5` + `0x0076E0F8` | plain swatch anchor `winW−106` (`83 EB 6A`) then `cmp eax,2 / jbe 0x0076E200` — **the one skipped instruction that separates the two legend kinds** |
| `0x0076E1F8` | cbox swatch anchor `winW−90` (`83 EB 5A`), reached only by fall-through |
| `0x0076E151` / `0x0076E159` / `0x0076E162` / `0x0076E168` | checkbox `SetArea(winW−108, y, winW−92, y+16)` — **16x16 at every tier** |
| `0x0076E17B` | checkbox id = `0x04000000 + seriesIndex` |
| **`0x0076E20A`** / **`0x0076E220`** | the ONLY image-wide call sites of the legend **text-block** allocator `sub_9B963D` (iface `+0xC4`, entry vt `0x00ADE540`) and the **swatch** allocator `sub_9B5A84` (iface `+0xCC`, entry vt `0x00ADE0DC`) |
| `0x0076E233` / `0x0076E239` / `0x0076E23C` | swatch `T=y+3`, `B=y+9`, `R=L+10` |
| `0x0076E2AF` / `0x0076E2C5` / `0x0076E2C8` | text left `swatchR+4` / bottom seed `y+10` / right `winW−4` |
| `0x0076E34B` | `lea edx,[ecx+eax+4]` — `rowY += fittedTextHeight + 4` (the only self-scaling term) |
| `0x0076DE79` | first row top = 20 |
| `sub_9B5ADE` (main `vt+0x278`) / `sub_9B5990` | the chart **draws** / **destroys** the list at `chart+0x228`. **Draw-only — never a layout pass** |
| `0x009B1F1D` (iface `vt+0x30`) | the plot-rect store EARLYCHART detours; present in iface vts `0xAB4C28` (type1) and `0xADE568` (type2); type3 `0xADEDE0` overrides with `0x9B2F92` and is not patched |
| `0x009B3647` / `0x009B2431` / `0x009B38A5` | chart layout driver / first-paint caller / the local rect the paint path reads |
| `0x007A0747` | the **Data Views** legend's style fetch — `Legend 0xE9C86B5F`, a **different** style from ChartLabel |
| B1 `0x0076E0E8` (25 B) · B2 `0x0076E145` (41 B) · B3 `0x0076E1D6` (42 B) | the three EQUAL-LENGTH block re-encodings of `ApplyGraphLegendBudgetScale`; branch targets that must survive: `jbe 0x0076E200`, `call 0x00602BE0` |

**Law: every patch is verify-before-write**: an unexpected byte pattern skips that
patch and logs, so a different exe build **degrades instead of corrupting**.
No game file is ever modified — all patches are in-memory. The eight
graph-legend sites go further and are **verify-ALL-before-write-ANY**: a
partial application would split a coupled pair (§5.4.9).

---

## 9. Predicting an unseen panel — the checklist

1. **Parentage.** Under `0x9A47B417` → runtime + art. Under the main window →
   static `.UI`. Both → 4x bug. (§1.2)
2. **Is the live tree what the script says?** Compare live window COUNT and
   root SIZE against the script. Mismatch ⇒ **a plugin replaced the script**
   (and check its art too). Several scripts sharing the root id ⇒ rect-match
   the live one. (§3.6, §4.6)
3. **How does each child get its size?** Own `area=` → scale it. Own art or
   caption → `kFontSizedIds`, position only. Game-managed items (AdviceList) →
   scale the container, never recurse. `0x0000AAAA` → never touch. (§2, §6)
   **And ask WHO sizes it** — the owner is not always the thing on screen. Find
   the entry object's ALLOCATION site; one xref = one builder, and if that
   builder is a *different* panel then the visible control's own class is a
   dead end. (§5.4.1)
3b. **Is any of it a shared BUDGET?** Two or more constants measured off the
   same edge (`winW − a`, `winW − b`, …) that must sum to a reserve. Scaling
   the members individually cannot work; write the sum out and check it closes
   at `f=1` first. Known instances: the advice row (§5.0a) and the chart legend
   (§5.4.3). **A fixed text box inside such a budget is an INPUT** — sizing it
   `round(box*f)` wraps MORE than stock, because ink grows ×2.13, not ×2.
   (§5.4.5, §5.4.7)
4. **Where do its pixels come from?** `.UI` TGI → art pass. Code-bound TGI →
   art pass, in place, after the conflict classifier. `sc4://` → art pass +
   the HTML tables. **No TGI → code lever only.** (§4)
5. **Is its text rich?** Any news/story/tutorial/popup/Credits surface is the
   HTML engine — FontStyle cannot reach it. (§5.2)
6. **Does the game re-impose its geometry?** If a value is right in one log
   line and wrong in the next dump, yes → DATA fix or pin-back pass. (§6.3)
7. **When is it born, and when does the game BIND anything from its
   geometry?** Bound at city load ⇒ runtime is structurally too late ⇒ pre-scale
   in DATA. Hidden until a mode switch ⇒ pre-scale while hidden. (§7)
8. **Does it hold a one-shot surface or a cached buffer?** Then a scaled window
   without a recreate is not a cosmetic bug — it can be a **heap overrun and a
   silent native death**. (§2, §7.3)
9. **Is anything shared?** Shared art → clone + retarget. Shared *container
   class* → gate on class **AND** owning context. Shared window id → scope
   every recursive search. (§4.6, §2.1, §1.3)
10. **Then MEASURE.** Every measured value in this project landed first try;
    every screenshot-inferred one cost 2-3 builds and twice broke something
    that already worked. Build the instrument, read it, then act — and **if two
    symptoms contradict each other you are at the wrong LAYER: move up one.**
