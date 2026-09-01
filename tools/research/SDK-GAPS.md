# SDK-GAPS — what the gzcom-dll SDK does not document

`vendor\gzcom-dll` is a community reconstruction of the GZCOM/`cIGZWin`
interface set. It is incomplete and, in places, wrong: whole interfaces are
missing, one virtual is missing from `cIGZWin.h`, and the slot names it does
give drift by one through the entire input and paint band. Everything the
mod relies on beyond those headers was recovered from the binary —
`SimCity 4.exe` **1.1.641.0** Steam, 7,876,608 bytes, ImageBase `0x400000`,
file offset = VA − `0x400000` — and is documented here, per subsystem, as:
what the SDK omits, the known addresses and ids, and how the gap is worked
around. The full derivations live in `SC4-UI-ENGINE.md`; this file is the gap
index.

EXACTLY the audit row whose replacement opens `**Standing rule.** Where the headers and the binary disagree, the binary wins.` and adds `**⛔ STANDING RULE 2 — `vendor\gzcom-dll\` IS READ-ONLY. Added 2026-09-01.**`, applied UNMODIFIED. Anchor verified unique (line 14).

---

## 1. The `cIGZWin` vtable layout

**Gap.** `cIGZWin.h` omits one virtual — a relative-move sibling of
`GZWinMoveTo` at real slot 57 — *and* lists one virtual the game does not
have. Several names in the band are also misattributed.

**⛔ THE SHIFT IS A BAND, NOT A TAIL. Corrected 2026-08-30.** This paragraph
used to end "so every header-implied index from 57 upward is one too low".
That is wrong at both ends, and the model was load-bearing for derived names.
Re-derived here from the headers themselves: `cIGZUnknown.h` declares exactly
**three** virtuals (`QueryInterface`/`AddRef`/`Release`), so
*header-implied slot = declaration index + 3*; `cIGZWin.h` declares 144
virtuals, indices 0–143.

| real slot | shift vs (decl. index + 3) | anchors |
|---|---|---|
| ≤ 56 | **0** | idx 52 `SetArea(l,t,r,b)` → 55; idx 53 `GZWinMoveTo` → 56 |
| 57–133 | **+1** — the undeclared virtual at real 57 pushes everything above it down one | idx 55 → 59, idx 58 → 62, idx 63 `GetFlag` → 67, idx 84 `GZPaint` → 88, idx 96 `PrivateBuffer` → 100, idx 117/118 → 121/122, idx 119/120 → 123/124 |
| 134–138 | **undefined — no shift exists here** | the header names **six** `GZOnMouse*` (idx 130–135) against the game's **five** 3-arg slots |
| ≥ 139 | **0 again** — the six-for-five collapse cancels the +1 | idx 136 `GZOnCaptureChanged` → 139, idx 137/138 → 140/141, idx 139 `GZOnCommand` → 142, idx 141 5-arg `SendMsg` → 144 |

Every anchor in that table is one of the independently measured rows below, so
the model is checked against the binary at both ends and in the middle rather
than assumed along its length.

**What this invalidates.** A header name is usable below 57 and above 138, is
one slot low in between, and is *unusable* across 134–138 — no counting scheme
can map six names onto five slots. Two names that were previously read off the
old tail model are therefore not carried here: real 136/138 are left unnamed
(bind them by message id, below), and real 133 is named only as "a focus
handler" — its arity agrees with the header's 1-argument `GZOnKillFocus`
(§1.4 measures `ret 4`), but real 132 also measures 1 argument where the
header's `GZOnSetFocus` takes 2, so the pair is not settled by counting.
Two names in the table below owe the header nothing: real slot 57
`GZWinMoveRelative` is a description of its disassembled body, and real
149/150 sit past the header's last index (146) altogether.

**Known.** Real slot 57 = `GZWinMoveRelative(dx,dy)` = `0x0099BD27`
(`mov edx,[ecx+0xB4]; add edx,[esp+8]` ×4, then `call [eax+0xDC]` = `SetArea`;
`ret 8`). Measured anchors, all read from function bodies:

| real slot | `[vt+…]` | virtual | base impl |
|---|---|---|---|
| 55 | `0xDC` | `SetArea(l,t,r,b)` | `0x0099C837` |
| 56 | `0xE0` | `GZWinMoveTo` (absolute) | `0x0099C8C5` |
| 57 | `0xE4` | `GZWinMoveRelative` — **absent from the header** | `0x0099BD27` |
| 59 | `0xEC` | `ScreenToWindowCoordinates` (subtracts the absolute origin) | `0x0099BD73` |
| 60 | `0xF0` | `WindowToScreenCoordinates` (adds `[+0x14]`,`[+0x18]`) | `0x0099BD5E` |
| 61 | `0xF4` | `WindowToWindowCoordinates` | `0x0099B8F5` |
| 62 | `0xF8` | `IsPointInWindowScreenCoordinates` — the header **does** declare it (`cIGZWin.h`, immediately before `GetID`); this project's notes call it `IsPointInMe`. Corrected 2026-08-30: the row previously said "the header has no such method", which came from counting declaration indices without the three `cIGZUnknown` slots. It is the screen-coordinate member of the trio completed by `IsPointInWindowWindowCoordinates` and `…ParentCoordinates` (slots 121/122), and `0x0099C97C` tests the ABSOLUTE rect `[this+0x14]`, which is what "screen coordinates" means here | `0x0099C97C` |
| 63 | `0xFC` | `GetID` (`mov eax,[ecx+0x10]; ret`) | `0x0099BE66` |
| 64 | `0x100` | `SetID` | — |
| 67 | `0x10C` | `GetFlag` (`[ecx+0xC8] & arg`) | — |
| 71 / 72 | `0x11C` / `0x120` | `IsVisible` / `IsEnabled` | `GetFlag(1)` / `GetFlag(2)` |
| 86 / 87 | `0x158` / `0x15C` | `SetNotificationTarget` / `GetNotificationTarget` | `0x0099BE42` / `0x0099BE4C` |
| 88 | `0x160` | **`GZPaint`** — the per-class draw; the slot the BMPX/DOBS hooks sit on | per class |
| 89 | `0x164` | **`Plot`** = `PlotComposite() && PlotPresent()`, then (if `byte[this+0x71]==0`) `ExecutePlotStrategy` | `0x0099BA07` |
| 90 | `0x168` | `CalcAbsoluteArea` — the absolute-rect recompute | `0x0099DCE4` |
| 91 / 92 | `0x16C` / `0x170` | `InvalidateSelf` / `InvalidateSelfAndParents` | `0x0099BECC` / `0x0099BED1` |
| 93 / 94 | `0x174` / `0x178` | `GetDrawContext` (`[ecx+0x6C]`) / `GetBufferToDrawTo` (`[ecx+0x68]`) | `0x0099BEF9` / `0x0099BEFD` |
| 95–98 | `0x17C`–`0x188` | `SetBufferToDrawTo` / `…Recursive` / `SetAreaToDrawTo` / `…Recursive` | `0x0099C6F8` / `0x0099D57E` / `0x0099CF6A` / `0x0099D5B7` |
| 99 | `0x18C` | `GetAreaToDrawTo` (`lea eax,[ecx+0x24]; ret`, zero-arg) | `0x00477810` |
| 100 | `0x190` | `PrivateBuffer(bool)` — **1 arg, `ret 4`** | `0x0099EA70` |
| 101 | `0x194` | `GetPrivateBuffer` (`mov eax,[ecx+0x64]`) | `0x009D419D` |
| 121 / 122 | `0x1E4` / `0x1E8` | `IsPointInWindowWindowCoordinates` / `…ParentCoordinates` | `0x0099C8F5` / `0x0099C960` |
| 123 / 124 | `0x1EC` / `0x1F0` | `PlotComposite` / `PlotPresent` | `0x0099E62D` / `0x0099C498` |
| 130 / 131 | `0x208` / `0x20C` | `GZOnKeyDown` / `GZOnKeyUp` | — |
| 134–138 | `0x218`–`0x228` | the **five** 3-arg mouse handlers (`ret 0xC`), reached from message ids 7, 8, 10, 11, 13 | — |
| 139 | `0x22C` | `GZOnCaptureChanged` (4 args, `ret 0x10`) | — |
| 142 | `0x238` | `GZOnCommand` | — |
| 144 | `0x240` | 5-arg `SendMsg(pWin, type, d1, d2, d3)` | — |
| 149 / 150 | `0x254` / `0x258` | refined per-pixel hit test / create-private-buffer — **past the end of `cIGZWin`** (header's last index is 146); `cGZWin`-derived extras | `0x0099BBBE` / `0x0099D0ED` |

Two further names to read from the binary rather than from the header:

- `0x0099BE4C` is **`GetNotificationTarget`** — a zero-arg getter,
  `mov eax,[ecx+0x4C]; ret`, paired with setter `0x0099BE42`. It is also the
  vtable-diffing baseline (re-measured 2026-08-30): **116** `.rdata`
  addresses carry it at slot 87 — the single-marker fingerprint that an
  address is a window vtable at all. **111** of them also pass the ≥3-of-8
  base-implementation census (`wincensus.py` →
  `tools/uimap/_work/wincensus.json` `windowVtables`), which is the
  window-class population every count in this file should use; the 5
  single-marker extras (`0xAC54B8`, `0xACCD5C`, `0xAD47F0`, `0xAD805C`,
  `0xAD825C`) fail the class test.
- The header names six `GZOnMouse*` handlers; the game exposes five 3-arg
  slots (134–138), reached from message ids 7, 8, 10, 11 and 13. Bind mouse
  handlers by slot number and message id, never by header name.

**Slots 95–97 override census (2026-08-23).** Diffed `[vt+0x17C]`/`[vt+0x180]`/
`[vt+0x184]` across all 111 window-class vtables in
`tools/uimap/_work/wincensus.json` (`windowVtables` — the exe's whole measured
population, a superset of the 29 named classes plus the anonymous flyout pair
`0xAB6AA8`/`0xAB6D88`, the tooltip layer `0xAB6770`, the gauge class
`0xAB46A0`, and every other detected window vtable). **Zero overrides**: every
one resolves to the same three base addresses (`0x0099C6F8`/`0x0099D57E`/
`0x0099CF6A`). These three virtuals are non-polymorphic in this build — no
class, named or anonymous, customises them — so their semantics ARE the base
`cGZWin` bodies below, with no per-class variation to reconcile.

**What the base bodies do (disassembled 2026-08-23; confirms the community
header's names for this band and extends them with the actual logic):**

- **slot 95 `SetBufferToDrawTo()`** (`0x0099C6F8`, zero-arg). Resolves
  `[this+0x68]` (bufferDrawnInto) to this window's own `GetPrivateBuffer()`
  (slot 101, `[this+0x64]`) when non-null; otherwise walks `GetParentWin()`
  (`vt+0x2C`) ancestor-by-ancestor until one either owns a private buffer or
  itself carries `WinFlag_DelayedPlot` (`0x8000000`, tested via `GetFlag`
  `vt+0x10C`) and inherits that ancestor's buffer. If the walk exhausts with
  neither (the tree root's case) it falls back to the `cIGZGraphicSystem`
  service (`kGZGraphicSystem_SystemServiceID 0xC416025C`, `REGION-SCREEN.md`
  §"`[0x00B43C9C]`") via helper `0x00449560`. Also resolves `[this+0x6C]`
  (draw context) by `QueryInterface(0xAB300B2B)` on whichever buffer was
  found — a new iid, not otherwise documented in this repo. **Ends by calling
  its own slot 98** (`SetAreaToDrawToRecursive`, `vt+0x188`): rebinding the
  buffer always cascades into rederiving areaToDrawTo down the whole subtree.
- **slot 96 `SetBufferToDrawToRecursive()`** (`0x0099D57E`). Calls slot 95 on
  itself, then walks the child list at `[this+0x44]` calling slot 96 (itself,
  `vt+0x180`) on every child — a literal recursive descent; the header's
  `…Recursive` suffix is mechanically correct, not just nominal.
- **slot 97 `SetAreaToDrawTo()`** (`0x0099CF6A`) — already independently
  anchored via the `GZWinBMP` `areaToDrawTo` field write (§2 above).
  Disassembly confirms both branches: private buffer non-null →
  `[this+0x24..0x30] = (0,0, r−l, b−t)` (own w/h only); private buffer null →
  the own rect walked up through `GetParentWin()`, accumulating each
  ancestor's L/T, stopping at the **same** condition as slot 95's buffer
  search (ancestor owns a private buffer, or ancestor carries
  `WinFlag_DelayedPlot`) — so a window's buffer and its areaToDrawTo always
  agree on which ancestor is "the" drawing surface. Slot 98
  `SetAreaToDrawToRecursive` (`0x0099D5B7`) is the slot-96 recursion pattern
  applied to slot 97 (self, then children).

**Workaround.** Index by number from the table above. **116, 115 and 111 are
three different tests, not three answers to one question** — do not
"reconcile" them:

| test | count |
|---|---|
| `[vt+87*4] == 0x0099BE4C` anywhere in `.rdata` — the bare marker | **116** |
| + `[vt]` and `[vt+88*4]` both inside `.text` (first `0xA8D000`, last `0xAE4398`) | **115** |
| + the ≥3-of-8 base-implementation census (`wincensus.py` → `windowVtables`) | **111** |

The 111 are the window-class population every count in this file should use.
The 5 the class test drops (`0xAC54B8`, `0xACCD5C`, `0xAD47F0`, `0xAD805C`,
`0xAD825C`) carry the marker without passing it. *Corrected 2026-08-30 (later
same day): this paragraph had been re-measured to "116 hits" while still
describing the three-condition scan, which is the 115 test — the 2026-08-30
re-measure had run the bare-marker test and written its answer against the
other test's description. Both numbers were right; the sentence joining them
was not. Re-verified against the shipped exe (`ImageBase 0x400000`, `.text`
`0x407000`+`0x678A2D`, `.rdata` `0xA80000`+`0x86A2A`): bare marker 116;
marker + both endpoints in `.text` 115, `0xA8D000`…`0xAE4398`.*
A vtable address outside `0x00A80000`–`0x00B20000` is a relocated DLL
vtable — one of the mod's own shadow copies (`gVtCopy`, `gVtCopy2`,
`gGaugeVtCopy`, `gStripVtCopy`), which move between sessions; exe vtables are
constant across restarts.

### 1.1 The two rects — why draw and hit-test can disagree

The SDK gives no hint that a window carries two different rects:

| rect | offsets | writers | readers |
|---|---|---|---|
| parent-relative | `[this+0xA8..0xB4]` | `.UI area=`, `SetArea`, `SetW/H`, `GZWinMoveTo` — every scaling write | `GetL/GetT/GetW/GetH`, layout and draw |
| absolute cache | `[this+0x14..0x20]` | **only** slot 90 `CalcAbsoluteArea` (`0x0099DCE4`), which copies `GetArea()`, adds every ancestor's `GetL/GetT`, stores, and recurses into all children | the hit test (`cRZRect::Contains` on `[this+0x14]`), slots 59/60 |

**⛔ THE LAW THAT USED TO SIT HERE WAS FALSE. Corrected 2026-08-30 by
disassembly.** It read: *"move the window, then make the engine recompute —
until slot 90 runs on the window or an ancestor, it paints at its new place and
hit-tests at its old one."* `SetArea` (`0x0099C837`) does the recompute itself,
on every call:

```
0x0099C881..0x0099C893   the four stores into [+0xA8..+0xB4]
0x0099C899  je 0x99C8AB  ; skips ONLY the private-buffer call below
0x0099C8A5  call [eax+0x190]   slot 100 PrivateBuffer(1)  - conditional
0x0099C8AF  call [eax+0x168]   slot  90 CalcAbsoluteArea  - UNCONDITIONAL
0x0099C8B9  call [eax+0x188]   slot  98 SetAreaToDrawTo…  - UNCONDITIONAL
0x0099C8C2  ret 0x10
```

Both recompute calls sit past the branch target, so no path through the
function skips them, and `CalcAbsoluteArea` recurses into every child — the
whole subtree is refreshed synchronously before `SetArea` returns.
`GZWinMoveTo` (`0x0099C8C5`) tail-calls `SetArea`, so it inherits this too.

**The corrected law: the absolute cache goes stale only if geometry is written
by something OTHER than `SetArea` / `GZWinMoveTo` / `SetW` / `SetH`** — a raw
poke at `[+0xA8..+0xB4]`, for instance. Through the normal setters the hit rect
is never behind the paint rect, and `InvalidateSelfAndParents()` is about
*repainting*, not about the absolute cache.

*Provenance, because this one matters:* the false version came from an
unverified draft in the incoming folder, and §3 of this same file has carried
the correct sequence the whole time — the file contradicted itself, with the
wrong half stated as a law and the right half buried in a walkthrough. Both
halves were re-derived from the image before this edit.

### 1.2 Hit-testing

- Router `0x0099DFA9` (slot 40, `ret 8`): walks the same `[this+0x44]`
  circular list as `EnumChildren` (`0x0099D708`), same sentinel, same
  direction — so **router order == `EnumChildren` order, and the first window
  in a tree dump that covers the point is the one that gets the click**.
  First claim wins; recursion is through the same virtual; the list is
  AddRef'd for the walk. The router tests `GetFlag(1)` (visible) and
  `GetFlag(0x200000)` (`WinFlag_IgnoreMouse`, skips the subtree) — it does
  **not** test `WinFlag_Enabled` (0x2): a disabled window still claims.
- `IsPointInMe` `0x0099C97C` (slot 62): gate 1 = `cRZRect::Contains`
  (`0x00664C60`, **half-open**: `L <= x < R && T <= y < B`); gate 2, only if
  `WinFlag_MouseTrans` (0x80000) and gate 1 passed = the refined mask, slot
  149 `0x0099BBBE`, which Locks the **private buffer** `[this+0x64]` with
  `0x800` and reads it per pixel; the result is inverted (0 = opaque =
  clickable). Gate 2 can only subtract from gate 1, never add. Slot 149 has
  exactly two call sites in the image (`0x0099C94A`, `0x0099C9C9`).
  **Positive control for that null** (re-measured 2026-08-30, same scanner):
  the `.rdata` search for `0x0099C97C` returns **91** hits and every one of
  them sits at slot 62 of a marker-identified window vtable, against 116 for
  the slot-87 marker itself — so the scan demonstrably finds both vtable
  entries and `call [reg+disp32]` sites, and "exactly two" is a measured
  count, not a scan that saw nothing.
- On a `MouseTrans` window a stale or wrongly-sized private buffer therefore
  mis-routes clicks, not just pixels.

### 1.3 The message funnel and winproc message ids

Everything — mouse, keyboard, focus, capture, commands — arrives through one
function, `cRZWin::DoMessage` = `0x0099CCF0`, slot 3 `[vt+0x0C]`:

1. The `cIGZWinMessageFilter` chain at `[this+0x88]` runs **first**; any
   filter returning true swallows the message before any handler. This is the
   highest-priority input hook in the engine.
2. Re-entrancy byte `[this+0x90]` is set.
3. Dispatch through the 20-entry jump table at `0x0099CEF9` on
   `msg->type − 1`; ids **2, 9, 12, 15 are unhandled**.

| msg id | → slot | arity | meaning |
|---|---|---|---|
| 1 | 16 | 1 | child-delete notification |
| 3 | 143 | 2 | — |
| 4 | 129 | 1 | `GZOnCharacter` |
| 5 | 130 | 2 | `GZOnKeyDown` (consults the accelerator `[this+0x78]` first) |
| 6 | 131 | 2 | `GZOnKeyUp` (falls back to `AccelerateKeyboardMsg`, slot 77) |
| 7, 8, 10, 11, 13 | 134–138 | 3 each | the five mouse position handlers |
| 14 | 139 | 4 | `GZOnCaptureChanged` |
| 16 / 17 | 133 / 132 | 1 | focus handlers |
| 18 / 19 | 140 / 141 | 2 / 1 | `GZOnMouseEnter` / `GZOnMouseExit` |
| 20 | 142 | 1 | `GZOnCommand` |

`cGZMessage` layout on the mouse path: `+0x00` type; `+0x04` cursor **x**
(`movsx word`); `+0x08` cursor **y**; `+0x0C` wheel delta; `+0x0E` key/button
flags. For non-mouse ids the same `+0x04`/`+0x08` dwords carry pointers —
reading `+0x04` as a dword on a mouse message yields `y<<16 | x`, a
plausible-looking pointer that is not one.

`GZWinBMP`'s own overrides forward three mouse events as
`SendMsg([this+0x4C], id, x, y, GetID())` with ids **`0x68915615`** (slot
134), **`0x28916985`** (slot 136), **`0xC89155E3`** (slot 138), and keyboard
types **5** (slot 130) and **6** (slot 131).

Upstream of the funnel, the Win32 message coalescer `0x0098CE30` drops
redundant `WM_MOUSEMOVE` runs before the UI sees them; it is upstream of all
routing, so its effects read exactly like routing effects.

### 1.4 The arity check

`__thiscall` is callee-cleanup, so a function's `ret N` states its argument
count exactly: a 3-arg mouse handler is `ret 0xC`, a 2-arg point test
`ret 8`, `GZOnCaptureChanged` `ret 0x10`. Real slot 133 is
`xor al,al; ret 4` — one argument — so hooking it as the header's 3-arg
`GZOnMouseDownL` corrupts the stack and crashes the game. Read the `ret`
immediate before every vtable hook, without exception.

### 1.5 Window flags the SDK enum does not list

| flag | read by | effect |
|---|---|---|
| `0x1000` | **18 `GetFlag(0x1000)` sites in `.text`** (`0x4F24C2`, `0x66DE95`, `0x685796`, `0x76A007`, `0x76A46A`, `0x76AAE0`, `0x777BF7`, `0x779863`, `0x78C2DC`, `0x78C81F`, `0x78FF70`, `0x7B6524`, `0x7E8CC9`, `0x7F5903`, `0x999009`, `0x9993FD`, `0x999865`, `0x99FCB3`) | **⚠ MEASURED BEHAVIOUR ONLY — the meaning is OPEN, and the two disassembled sites disagree on polarity.** At `0x00999004` (a slot-131 body, carried at slot 131 by 13 window vtables; `ret 8`): flag **set** ⇒ `xor al,al` return, nothing forwarded; **clear** ⇒ `SendMsg([this+0x4C], 6, a1, a2, 0)` through slot 144. At `0x00779850`: flag **set** ⇒ `GZWinMsgPost(0xF, win, …)` through the window manager (`winmgr vt+0x24`); **clear** ⇒ a *different* post (`[win vt+0x2C]`'s result handed to `winmgr vt+0x38`), not a no-op. So the flag is not a single "do not forward" latch, and no purpose should be written down until more of the 18 sites are read. Absent from `cIGZWin.h`'s `tWinFlag` (15 entries) |
| `0x4000` | `Init` short-circuit `0x0099BC31` | "already initialised" latch: `Init` returns early while it is set |
| `0x400000` | set at `0x0099E859` after a successful `GZPaint` into a private buffer | "this private buffer holds content" |
| `0x4000000` | set at `0x0099E8C8/93C/9D5`, cleared in `PlotPresent` `0x0099C501` | queued into the winmgr plot strategy |
| `0x8000000` `WinFlag_DelayedPlot` | the invalidation walk and `PlotComposite` | a wall in both directions (§3) |

---

## 2. `GZWinBMP` — the complete class

**Gap.** gzcom-dll ships no header for the `cIGZWinBMP` interface at all.
The entire interface, object layout and draw law were recovered offline;
**this section and §2.1/§2.2 are the full reference.** *(Corrected
2026-08-30: this line, `UI-ART-BINDING.md` §0 and `UI-ART-BINDING.md` §3 all
pointed at "`SC4-UI-ENGINE.md` §4A". No `§4A` exists in that file — §4 is
"Art binding" and §4.1 follows it; the decode landed here.)*

**Known.**

- Identity: class `GZWinBMP` clsid `0x82FE68C4`, iid `0xC12CEA13`, class
  vtable `0x00ADF6A0` (151 slots), interface vtable **`0x00ADF66C`** (12
  slots) over base `0x00ADF63C` (24; first 12 = purecall stub `0x5D4A10`),
  ctor `0x9BC4BA`, registration `0x953056`. The interface is an embedded
  sub-object at `this+0xD8`; `QueryInterface` returns `this+0xD8` and every
  interface method converts back with `−0xD8`.
- Interface slots: `+0x0C GetWindow` (`lea eax,[ecx−0xD8]`), `+0x10
  SetImage(cIGZBuffer*)` `0x9BC57E`, `+0x14 GetImage`, `+0x18/1C Set/GetAlpha`,
  `+0x20 SetImageRect` `0x9BC103`, `+0x24 GetImageRect`, `+0x28 GetFlag`,
  `+0x2C SetFlag`.
- Object map (load-bearing entries): `+0x10` id; `+0x14..0x20` absolute area;
  **`+0x24..0x30` areaToDrawTo** — the draw's dst origin, written by slot 97
  as the window's rect in the nearest buffer-owning ancestor's space, or
  `(0,0,w,h)` when the window owns a private buffer; `+0x48` winproc target;
  `+0x4C` notification target; `+0x64` private buffer; `+0x68` buffer drawn
  into; **`+0x6C` draw context**; `+0x70` dirty byte; `+0xA8..0xB4` own area;
  `+0xC8` winflags; `+0xDC` bound image; `+0xE0/+0xE4` alpha enable/value
  (0.5f); **`+0xE8..0xF4` imagerect**; **`+0xF8` flag word** (ctor default
  `0x12`).
- Flag word bits and the `.UI` attribute that sets each: `0x01` ← `notify=`
  (token `0xF003`); `0x02` ← `transparentbkg=` (`0xB01`, skips the background
  fill); `0x04` — click-through, set by nothing; `0x08` ← `edgeimage=`
  (`0xB02`, selects the 9-slice path); `0x10` ← `imagerect=` present
  (`0xF018`; explicitly cleared when absent); `0x20` — same source selection
  as `0x10` plus dst shifted by `(src.l, src.t)`, **set by nothing in the
  image**. `alpha=` (`0xB00`) and `imagetype=` (`0xF017`) parse but
  are dead in practice: nothing in the draw path reads them, and the corpus
  uses each zero times.
- Draw (`GZPaint` `0x9BC325`, slot 88): background fill unless `0x02`; no
  image → nothing; source = `+0xE8` when flag `0x10`/`0x20`, else the image's
  natural rect. **Plain path:** `dst = {A.l, A.t, A.l+srcW, A.t+srcH}` — the
  window's width and height are never read; the blit size is 100% a function
  of the source rect, so a GZWinBMP cannot letterbox, centre or fit. **Edge
  path:** `src.r /= 3; src.b /= 3` (`l`,`t` untouched) then the 9-slice helper
  `0x8D8800` (§2.1).
- The imagerect lifecycle — the complete list of things that change what a
  GZWinBMP draws: `Init` (slot 4, `0x9BC52D`: `imagerect = (0,0,GetW(),GetH())`
  clamped to the image, no-op while flag `0x4000` is set); `SetImage`
  (**destroys** the current rect: resets it to `(0,0,min(winW,imgW),
  min(winH,imgH))` via `0x9BC447`); `SetImageRect` (clamps `l,t ≥ 0`,
  `r,b ≤ image dims` — but only when an image is already bound); and a direct
  field write to `+0xE8`. `SetArea`/`SetSize`/`SetW`/`SetH` never touch it
  (slot 55 is a bare `jmp` to base).
- **The runtime-supplied-image law.** A GZWinBMP whose pixels arrive at
  runtime via `SetImage` draws `min(winW,imgW) × min(winH,imgH)` source
  pixels from the art's top-left corner, at the window's top-left, with no
  scaling: art smaller than the window ⇒ 1x content pinned top-left; art
  larger ⇒ cropped, never downscaled; 2x art ⇒ a 2x draw with no code hook.
- **No state-strip machinery exists in the class** — no `/4`, no index, no
  state field; the only division in the whole class is the edge path's `/3`.
  Multi-state sheets are controller-driven (the controller rewrites the crop
  through interface slot 8, swaps the image through slot 4, or calls
  `cIGZWin::SetW` — the mayor rating bar's `imul …,7` at `0x7E87B1`).
  `imageWidth/4` state selection belongs to `GZWinBtn`, a different class.
- **`image={g,i}` resizes the window to the art.** The deserializer's pass 1
  handler (`0x95002C`) loads the PNG, calls `SetImage`, then
  `SetSize(imgW,imgH)` (`0x95017F`, slot 53). This is the mechanism behind
  "419 controls have `area` exactly == PNG dims" and "style-PNG widgets are
  born at the art's size": it is engine behaviour, not an authoring
  convention. It is a default — an explicit `area=` in the same element wins.
- Creation from a script is two-pass with `Init()` between
  (`0x957BE7`–`0x957C77`): pass 1 = `alpha/notify/transparentbkg/edgeimage/
  image`; `Init()`; parent attach + `PullToFront`; pass 2 = `imagerect` (+ the
  `0x10` flag set or cleared), then the generic attributes.

**Workaround.** Born-correct is the only architecture for this widget: ship
the window at its final size and the art at the matching tier, because a
post-hoc sweep that resizes the window never re-derives the source rect, and
`SetImage` at runtime resets it to the window's size *at that moment* (the
bind-time latch, `SC4-UI-ENGINE.md` §2.6). The mod's BMPRECT pass writes
`+0xE8` directly and therefore bypasses `SetImageRect`'s clamp — safe only
while the paired art really is 2x.

### 2.1 The 9-slice helper `0x8D8800`

Signature (cdecl, caller cleans `0x14`): `helper(ctx, img, srcCell, dst,
fillCentre)`. The source walks a 3×3 grid of `cellW×cellH` starting at
`(srcCell.l, srcCell.t)`; the dst is re-derived per band, never walked
cumulatively. The four corners go through draw-context slot 38 (`+0x98`)
unconditionally, called at `0x8D8928` with 3 arguments; the four edges and
centre go through slot 39 (`+0x9C`, called at `0x8D896A` with 5 — two extra
zeroed args), each guarded by a room test; the centre also requires
`fillCentre`. A window narrower/shorter than two cells does not clip — its
corners overlap. Colour keying arrives via `img->QueryInterface(0x86D72B57)`.
`imagerect` is never an inset, an edge width or a centre rect; there is no
inset concept in the engine. 2x art requires doubling all four `imagerect`
numbers: `(2r/3 − 2l, 2b/3 − 2t) = 2 × (r/3 − l, b/3 − t)` exactly.

Related single-caller tiler: `0x008D9550` wraps `0x008D8BC0` and has exactly
one caller in the image — `cSC4WinAlertBorder::Plot` (§8.2). The tiling blit
`0x8D8BC0` reduces out-of-range coordinates modulo srcW/srcH — it **tiles**,
never clamps.

⛔ **OPEN — does a DECLARED `imagerect` actually reach the draw for
`edgeimage=yes` controls?** The operand question is **closed**: the edge
branch divides `r` and `b` only, re-verified against the shipped exe
2026-08-30 — `0x009BC39D lea edi,[ebp-0x10]` + four `movsd`, and the plain
path at `0x009BC3C2 sub eax,[ebp-0x10]` / `0x009BC3C8 sub ecx,[ebp-0xC]` /
`add eax,[ebp-8]` / `add ecx,[ebp-4]` pins those four locals to `(l,t,r,b)`;
the edge path at `0x009BC411` (`mov eax,[ebp-8]; cdq; push 3; pop ecx; idiv
ecx; mov [ebp-8],eax`) and `0x009BC41F` (the same on `[ebp-4]`, reusing
`ecx`) touches nothing else, then `push 1` / dst `[ebx+0x24]` / cell
`[ebp-0x10]` / img `[ebx+0xDC]` / ctx `[ebx+0x6C]` / `call 0x8D8800` /
`add esp,0x14`. What is still open is one link further down the chain:
whether the rect the script DECLARES is the rect sitting in `+0xE8` at draw
time. An offline PIL recomposition of the real chrome PNGs under the decoded
algorithm disagrees with what the game visibly renders —
`{1abe787d,144161e4}` 78x78 with `imagerect=(12,12,78,78)` gives a 14x14 cell
sampled from the flat interior and composes to a corner-less box, while the
image's natural rect (26x26 cell at `(0,0)`) composes to the correct
decorated chrome; same for `{46a006b0,14416240}` 180x180.

**That mismatch is NOT evidence against the `r`/`b`-only reading** — it tests
a different link, and the two most attractive alternative explanations are
already eliminated offline: the deserializer `0x95002C` branches on arg3
(`0x00950053 cmp byte [ebp+0x10], bl` → `0x0095005A je 0x9501EA`), so
`imagerect=` is applied in **pass 2**, while the factory calls `Init` between
the passes at `0x00957C25` (`call [eax+0x10]`, slot 4) — so `Init` cannot be
overwriting the declared rect; and pass 2 does arm the flag
(`0x00950204 call [eax+0x20]` = `SetImageRect`, then `0x0095020C push 1;
0x0095020E push 0x10; 0x00950210 call [eax+0x2C]` = `SetFlag(0x10,1)`; the
absent-`imagerect` else at `0x00950215` pushes `ebx`=0 into the same
`SetFlag`). Two candidates
survive: flag `0x10` is not actually set live on those 56 controls, or the
decorated chrome the player sees is a **different window in the stack**.
**The probe that settles it:** extend the BMPRECT walker to log
`[win+0xF8] & 0x18`, `[win+0xE8..0xF4]` and the live W/H for one edge BMP
(Save-dialog body `{1abe787d,144161ee}`, `imagerect=(22,35,180,180)`) and
compare the composed corners against a stock screenshot.

### 2.2 The draw context (`[win+0x6C]`)

**Gap.** gzcom-dll has `cIGZBuffer.h` and `cIGZGraphicSystem.h` but no
draw-context header; the class is undisassembled. Known slots: `+0x28`/`+0x2C`
push/pop draw state, `+0x54` `SetColor`, `+0x8C` `FillRect`, **`+0x98`
`DrawImage(img, src, dst)`** — proven to scale (live: `img 64x64 win 128x128
-> dst 128x128`), **`+0x9C` `DrawImage(img, src, dst, 0, 0)`** — the
edge-band blit. `cIGZBuffer::Blt` (`0x826AD0`) clips, never stretches.

---

## 3. The paint pipeline: invalidate → composite → present

**Gap.** None of this is in the SDK: the dirty model, the composite gates,
the buffer allocator's hidden destroy path, and the class-private caches that
make resize paths structurally unreachable.

**Known.** All fields measured in the `cGZWin` constructor
`0x0099DA5A`–`0x0099DB33`. Dirt is a single boolean byte `[win+0x70]` —
**every window is born dirty**; there is no dirty rectangle anywhere in
`cGZWin`, so every repaint is a whole-window repaint. `[win+0x71]` is the
suppress-`ExecutePlotStrategy` latch, written only inside
`SetBufferToDrawTo`. The flag dword at `[win+0xC8]` is born `0x8903`.

- `InvalidateSelf` (slot 91) is `mov byte [ecx+0x70],1; ret` — the entire
  function. It is not a repaint request.
- `InvalidateSelfAndParents` (slot 92, `0x0099BED1`) calls `InvalidateSelf`,
  then walks `GetParentWin` marking every ancestor (`0x0099B7BD`), **stopping
  at the first ancestor with `WinFlag_DelayedPlot` (0x8000000)** — a wall in
  both directions: it halts the dirty walk and reroutes the subtree into
  `cIGZWinMgr::AppendToPlotStrategy` (winmgr slot 7), drained by
  `ExecutePlotStrategy` (slot 8). 337 call sites use slot 92; it is the
  engine's own universal "I changed" primitive.
- `PlotComposite` (slot 123, `0x0099E62D`), in order: visibility gate
  (invisible ⇒ the entire subtree is skipped); message filters; **the dirty
  gate** — a clean window takes the harvest path (`EnumChildren` callback
  `0x0099B9AC`), which paints **nothing**; dirty path — clear the dirty byte
  *only if the window owns a private buffer and has a parent*, optionally
  erase the private buffer (`0x20000 PrivateBufferTrans` + `0x40000
  PrivateBufferErase`), push context state, call slot 88 `GZPaint`, set
  `0x400000`; then children, walked via the `[node+4]` link — the opposite
  link from the hit-test router, which is why paint order is back-to-front
  and hit order front-to-back.
- **A dirty child under a clean parent is never painted.** That is why the
  dirty flag must be pushed to the root and why sweeps call
  `InvalidateSelfAndParents`, never `InvalidateSelf`. The hover "fix" for a
  stale paint works because hovering dirties an ancestor.
- **Two classes of window.** The dirty byte is cleared only for
  private-buffer windows with a parent; everything else — nearly the whole
  HUD — stays dirty forever and runs `GZPaint` every frame. Flash is not a
  missed repaint; it is 60 correct repaints per second of state corrected one
  frame late. Cure the birth, never the paint.
- `PlotPresent` (slot 124, `0x0099C498`): no private buffer ⇒ return;
  deferred (`0x4000000`) ⇒ present `[0x14..0x20]` and clear the flag; else
  blit into the parent's `[0x68]`, or — parentless — into the canvas surface
  via the lazily cached global `0x00BAC058`. A fourth rect
  `[win+0xB8..0xC4]`, zeroed in the constructor at `0x0099DB28`, is read here
  for the non-deferred present.
- **Buffer allocation.** `SetArea` (`0x0099C837`) always stores the rect,
  then, if `WinFlag_PrivateBuffer (0x10000)` is set and W/H changed, calls
  `PrivateBuffer(true)` (slot 100, `0x0099EA70`), then slots 90 and 98.
  `PrivateBuffer(true)` first walks the ancestor chain: **if any ancestor is
  hidden it takes the DESTROY path** — resizing a window while any ancestor
  is hidden throws the buffer away; it is re-made at whatever size the window
  has when next shown.
- **Class-private caches are unreachable by all of this.** The widgets that
  produced the "born at first-paint size" defects keep their cache in a
  class-private field allocated inside their own `GZPaint`: flyout container
  `0x00AB6AA8` `[this+0xDC]`, `cSC4WinMiniMap` `[this+0xF0]` (one-shot at
  city load), gauge dials `0xCBCBF1E0`. `SetArea` cannot see those fields; no
  engine path resizes them. Born-at-the-right-size (ship 2x data) and
  force-recreate (corrupt the cached width so the class's validity check
  fails) are the only two doors.
- **There is no same-tick path.** A resize cannot be made visible in the
  frame it is made: `SetArea` never paints; the composite for the frame has
  already happened or will read half-written state. The reliable lever is to
  make the window correct before it becomes visible — `PlotComposite` skips
  invisible subtrees outright, so a window scaled while hidden has no wrong
  frame to show (the pre-scale-while-hidden and born-correct laws).

---

## 4. Window creation, dialogs and modality

**Gap.** The SDK declares the manager interface names but not the creation
protocol, the placement formula, the two transient lifecycles, or the
liveness contract the game itself follows.

**Known.**

- **Win manager access:** lazy singleton accessor `0x913C46` caching into
  `[0xB628C0]` (`GetService` form `push 0xA417445E; push 0x5A4` =
  `cIGZWinMgrPtr`, the `cRZSysServPtr` typedef in `GZServPtrs.h`); also
  `cIGZWin::GetWindowManager()` (vt `+0x18`) from any held window.
  `cIGZWinMgr` slot map (declaration order, confirmed at four binary
  anchors): `+0x0C` `GetMainWindow`,
  `+0x50/54/58` valid-list add/remove/cleanup, `+0x5C` `DestroyWindow`,
  `+0x60` `IsWindowValid`, `+0x90/94` `GZGetFocus`/`GZSetFocus`, `+0xA4`
  `DoModalWin` (blocks, returns int32), `+0xA8` `IsModal`, `+0xAC`
  `GetModalNestCount` — modals nest.
- **The seven-step code-driven dialog protocol** (generic message-box builder
  `0x78DFF0`; identical at `0x4F2653`, `0x791439`, `0x455240`): get the
  manager → parent = `GetMainWindow()` (code-driven boxes are
  main-window-parented by construction) → save the focus → instantiate the
  `.UI` through the factory **`0x5F9390`** (`cIGZUIScriptService` clsid
  `0x5A356E15` / iid `0xFA3562FA`, vt `+0x10`, `(key, parentWin,
  rootWinId)`; `0x778245` is one caller, not the factory) → `PullToFront()`
  (`0x78E0A2`, every code-built dialog raises itself at birth) → place and
  show → run modally, then tear down.
- **Placement, and only for the boxes this builder builds:**
  `x = (parentW − w)/2`, `y = (parentH − h)/3` (signed), then `GZWinMoveTo`.
  Confirmed to the pixel (270x162 box in a 2400x1600 frame → (1065,479); the
  corpus declares that id three times — `(332,232,602,393)`,
  `(332,232,662,389)`, `(332,170,662,279)` — and it arrives at none of them
  and at no multiple of them, so the builder really does move that one).
- **⛔ "A TALL DIALOG HANGS LOW BY DESIGN" WAS FALSE. Struck 2026-08-30.**
  This bullet used to continue: *"Placement happens once, at creation, from
  the size the window has then; a later content-fit resize does not re-place —
  a tall dialog hangs low by design."* Its sole evidence was query transient
  `0x10000005` opening twice at the same (492,404) at two different heights
  (584x386, then 584x668), read as a sticky y. **The two opens are two
  different scripts that share the root id, and (492,404) is what both of them
  declare.** Measured in the staged 2x corpus: `I-cc313f17` declares that root
  `area=(492,404,1076,790)` = 584x386 and `I-ca56783a` declares it
  `area=(492,404,1076,1072)` = 584x668 — the two live sizes exactly, at one
  common declared origin. (Stock: `(246,202,538,395)` and `(246,202,538,536)`.)
  No content-fit and no placement stickiness is involved, and the formula
  would not have produced the taller one anyway ((1600−668)/3 = 310, not 404).
  Nothing survives of the law; the id's *size* instability is a separate,
  still-true fact and is kept in the "an id promises nothing" bullet below.
- **A `.UI` root's own absolute `area=` is honoured verbatim; the centre/third
  formula is not applied on that path.** This closes the open question about
  `0x6A243D9E`. Stock `I-0a243d80` (Select A My Sim) declares it
  `area=(200,100,634,481)` = (200,100) 434x381; the staged 2x copy writes
  `area=(400,200,1268,962)`; and the live captures land on the script's own
  numbers at two different tiers — `(400,200 868x762)` = exactly 2x and
  `(600,300 1302x1143)` = exactly 3x. Two tiers landing on the declared origin
  rules out any centring formula on the loader path. *Inference, not
  disassembly:* the mechanism ("a script root loaded outside the `0x78DFF0`
  builder keeps its own absolute `area=`") follows from the data; the loader
  path for that id was not disassembled.
- **Teardown:** `DestroyWindow` → `IsWindowValid(prevFocus)` → `GZSetFocus` →
  `Release` → null the cached pointer. The engine maintains a global valid
  list and the game does not trust a saved `cIGZWin*` across a modal without
  asking (`DoModalWin → IsWindowValid → act` at `0x4F2668/81`,
  `0x791433/4C`, `0x78E24D/8E`).
- **The valid list is a hash set at `mgr+0x44`, and it can be EMPTY.**
  `IsWindowValid` (`0x009DC087`, `ret 4`) is a null check plus
  `ecx += 0x44` and a tail into the bucket lookup `0x009DB9B1`:
  `buckets = ([ecx+8] − [ecx+4]) / 4`, `idx = (key >> 2) % buckets`, then a
  chain walk comparing `[node+4]` against the window pointer — the pointer
  *is* the key. `DoDestroyWindow` (`0x009DB0FD`) opens with exactly that call
  (`call [eax+0x60]` into `bl`), then `CleanUpWindowReferences`
  (`[eax+0x58]`), and only then tests `bl` — so **a window that has left the
  valid set is unremovable**, and `ChildDeleteAll` discards the resulting
  `false` and retries the same child forever (the #104 shutdown spin;
  `src\SpinProbe.cpp` replicates the lookup byte-for-byte and carries the
  full call-graph derivation).
  **⚠ Qualifier on using it as a liveness gate:** the set is not always
  populated. The replication has measured it holding **zero entries across
  its whole bucket array**, in which state `IsWindowValid` correctly answers
  FALSE for *every* window — so a gate built on it would then reject
  everything, and a FALSE from it is only meaningful once the same table has
  been shown to contain at least one key (`SPINPROBE #104FIELDS SELFTEST`
  exists to make exactly that distinction: `PASS` vs
  `INCONCLUSIVE-BY-EMPTY`).
- **Two transient lifecycles.** Main-window transients are **unparented on
  close** — they leave the child list entirely, so any cached pointer, index
  or latch is dead the moment the box closes. View-parented transients
  **persist hidden and accumulate** (six live copies of `0x4C30E4FA` measured
  under the 3D view). Never single-find a transient id; iterate every match.
- **An id promises nothing:** not unique across the tree (`0x2AAB8CC1` is the
  tooltip layer *class* — one to three live instances measured), not unique
  within a parent (the six `0x4C30E4FA`), not unique across scripts, not
  stable across a size change (`0x10000005` is 386 tall on one open and 668
  on the next — and the reason is the sharpest form of this bullet: **that id
  is declared as a depth-0 root by 75 different scripts, and appears in 117 of
  the 281**, so "the same id" is not the same window design twice), and `id=0x00000000` is normal (1,749 of 5,964 corpus elements
  carry no `id=` at all).
- **Z-order is mutable at runtime.** Add order fixes only the initial order:
  dialogs `PullToFront` at birth; the tip layer migrates to index 0 on its
  first show and stays. `winflag_sortable=yes` on only 27 of 5,964 corpus
  nodes, so elsewhere the order is add-order plus explicit raises.
- **The pointer rule.** A `cIGZWin*` is safe as a map key within the tick
  that enumerated it; never as a stored handle. The failure mode is
  mis-attribution, not use-after-free: a recycled address hands a live window
  a dead window's record, and an id check cannot see it when the ids match
  (template+instance and pool cases). Identity, in ascending strength: id
  alone (insufficient) → id + parent + original size → `IsWindowValid`
  (answers liveness, not sameness). Engine-provided alternatives to a side
  map:
  `SetParam/GetParam/EnumParams` (a per-window property bag that dies with
  the window) and `Set/GetNotificationTarget` for the owner link.
- **The modal pump still drives a Win32 timer tick** (`DoModalWin`'s pump
  keeps dispatching to the game HWND), so runtime fixes work inside a modal;
  and because modals nest, `GetModalNestCount()` is the correct re-entrancy
  gate. A modal-veil sub-service — cached at `0x602336` from
  `[0xB43C94]->vt[0xAC]()` into `[0xB43CE0]` — brackets every `DoModalWin`
  with `+0x28(win,bool)` and `+0x18(win)`.
- **The loader instantiates every depth-0 root** of a script regardless of
  which node the `rootWinId` selects — the id may name **any** node, not just
  a root (measured: `0x00004200` is a depth-1 child passed as the winId at
  `0x007EEAE6`). The corpus-wide candidate pool for this pattern is measured
  (`tools\uimap\depth_ladder.py`, 2026-08-23): **1,296 distinct ids sit at
  depth ≥1** across the 339-file corpus. Which of those the compiled code
  actually passes as a winId is unmeasured beyond the 7 documented pairs in
  `coverage-matrix.md` §0.6 (1 of 7 is `0x00004200`) — needs a disassembler
  sweep of the winId-loader thunk's callers, not the `.UI` corpus.
- A fourth transient host: the app frame `0x6104489A` itself takes children
  (the missing-plugin-packs warning `0x2A5CFB2C`, added after the 3D view and
  therefore painting over it).

**Creation routes a static census cannot see:**

1. The runtime COM singleton **`0xC2C2EB0F`** (getter `sub_913C72` @
   `0x00913C72`): the class is chosen from a runtime-registered dispatch
   table, no literal clsid in the instruction stream. 220 call edges in 129
   functions; 27 inside the live-UI band `0x760000`–`0x7FFFFF`. Only a live
   hook names the classes it produces.
2. **`sub_779660`** — the generic window factory whose id is a register: 86
   call sites in six functions (the Ordinances/news builders); it does
   `call 0x913c72` → create → `SetID` from a register. Confirmed ids from
   those sites include `0x0ABCE000/1` and `0x0ABCDE00/01/02` — none of them
   in any literal-`SetID` census.
3. **109 anonymous creation sites** (24 in the live-UI band) assign no id at
   all. No id-keyed rule can ever address them; they are reachable only
   through parent-subtree recursion — which the sweep does, so the risk is
   low.
4. **Computed ids.** 162 `call [reg+0x100]` (`SetID`) sites exist; the
   literal scan matches 73. The other 89 pass a non-literal argument — the
   consecutive runs seen live (12 at `0x12C`, 12 at `0x2F4`, 4 at `0x551`)
   are `SetID(base+i)` in a loop. The **per-instance** value does not exist
   in the image — **the BASE does.** A push-only literal scan cannot see it
   because the base is a `mov`-immediate to a stack slot, set once before
   either loop: the Ordinances builder `sub_77C660` writes both of its bases
   two instructions after the prologue —
   `0x0077C670 C7 44 24 3C 2C 01 00 00` = `mov dword [esp+0x3C], 0x12C`
   (checkbox) and `0x0077C678 C7 44 24 24 F4 01 00 00` =
   `mov dword [esp+0x24], 0x1F4` (row strip). The live tree closes on those
   two numbers: 12 checkboxes `0x12C`…`0x137` = base+k, and 12 strips
   `0x2F4`…`0x2FF` = `0x1F4 + 0x100 + k` — the base plus the §4.1
   outer/inner offset. **So these runs are derivable offline**; look for a
   `mov`-immediate into a stack slot before the loop, not for a `push`.
   *(Added 2026-08-30; verified against the shipped exe.)*

### 4.1 The `+0x100` outer/inner pair

Every window created through the button factory `sub_77B960` appears in the
live tree **twice**: an outer window with `id + 0x100`, and its child with
the raw id. The tree carries the outer; code that wants the caption/image
surface fetches the raw id. Proven inside the exe itself at two unrelated
sites (`0x77D330` vs `0x77D350`; `0x78BAC1` vs `0x78BADD`) and live. The
check-strip factory `sub_77B7B0` does not do this. Mechanism: the factories
differ only in the create type passed to the window manager (`push 2` button
vs `push 4` check strip); the offset is applied inside the type-2 create.
Consequence: a builder census keyed on the pushed ids lists `0x451`, `0x6D`,
`0x384`, `0x1F4` while the live tree shows `0x551`, `0x16D`, `0x484`,
`0x2F4` — a join on raw id misses 100% of them. Class fingerprint: outer
`vt=00AE20A0`, inner `vt=00ADDAF0` — **name those two and the pair stops
looking like a quirk: the outer is `GZWinFlatRect`** (registry entry 0, clsid
`0xC2AFA76E` / iid `0xC2AFA76F`; settled twice — its slot-0 `QueryInterface`
`0x009CD1D2` opens `cmp [esp+4], 0xC2AFA76F`, and its ctor `0x009CD842`
stores the vtable at `0x009CD882 C7 06 A0 20 AE 00`; `GZPaint` `0x009CD1FF`)
**wrapping a `GZWinBtn` inner** (`GZPaint` `0x009B167D`, the class vtable
sitting at `obj+4` — its slot 0 is a `sub ecx,4; jmp` thunk). A flat
rectangle holding a button is exactly what a `+0x100` outer/inner pair is.

---

## 5. The `.UI` script format

**Gap.** The SDK gives no grammar. The loader was disassembled instead;
`SC4-UI-ENGINE.md` §3 carries the full reference — §3.0a and the
attribute sections §3.2–§3.6. (This line used to cite §3.7–§3.12, which
have never existed: that chapter ends at §3.6.)

**Known.**

- **The lexical contract.** `.UI` is not line-oriented: 107 of 5,964 elements
  span multiple physical lines (quoted values contain raw newlines); 84
  quoted values in 19 files (16 script instances) contain a literal `>` — so
  any `<LEGACY[^>]*>` regex is wrong, and **five such regexes are live in the
  builders right now**: `build_selective_safe.py` lines 921, 1017, 1078 and
  1274, and `build_dialog_static.py` line 1497. They survive only on the
  prefix invariant below, which is a property of the stock corpus, not of the
  regex. One file (`I-ca551016`, the Credits) carries a UTF-8 BOM.
  **⛔ Corrected 2026-08-30: there are no backslash escapes at all.** This
  bullet used to read "backslash escapes exist for `'` but not for `"` (zero
  `\"` in the corpus)", citing `station\'s` in `I-c9930681` as the positive
  control. That string does not exist — `I-c9930681` contains **zero**
  backslash bytes, and the value it was read from is
  `tiptext="Build Police Stations & Jails|…"`. Re-measured: the 281 layout
  scripts hold **7 backslash bytes in total**, all seven inside one quoted
  `tiptext` in `I-ca53f06e` (the Audio Options custom-tunes tip) as literal
  Windows path separators — `…\maxis\simcity 4\radio\stations\mayor\music` —
  and **zero** `\"` and **zero** `\'` anywhere. The remaining 29,773
  backslashes in the extract are all in non-layout groups (`G-8a5971c5`, 45
  files; `G-4a87bfe8`, 1). *The null keeps its control:* the same scan does
  find backslashes, in a layout file and outside one, so "no escapes" is
  measured rather than blind — which is why a naive quote-toggle scanner
  works.
  The one invariant: every element begins `clsid`, then `iid` (if
  present), then `id=` (if present), then `area=`, and `caption=` never
  precedes any of them (re-verified 2026-08-30 over all 5,964 elements:
  first-three-attribute signature 4,209 `(clsid,iid,id)` / 1,749
  `(clsid,iid,area)` / 6 `(clsid,id,area)`, with **zero** elements where
  `caption=` precedes any of `clsid`/`iid`/`id`/`area`).
- **The keyword dictionary.** The loader does not strcmp attribute names.
  Six registration functions intern 391 keywords — attribute names and enum
  values in one namespace — into the dictionary singleton `[0x00B63588]`
  (registrar `0x00408480`; tables at `0x0094D641`–`0x0094E33A` base 64 pairs,
  `0x0095127E`–`0x0095404D` per-class 177, `0x009552D3`–`0x009560B0`
  FileBrowser 68, `0x00957C9D`–`0x009580EE` OptGrp 21, `0x009599E7`–
  `0x00959E04` TreeView 20, `0x0095B036`–`0x0095B897` Grid 41). The parse
  result is an array of 8-byte `[tokenId][value*]` pairs; the value object's
  `[vt+0x0C]` returns a type code where **type 6 = interned token**.
  Booleans: `yes`/`true`/`on` = 1, `no`/`false`/`off` = 0.
- **Base attribute ids:** `clsid` −1, `iid` −2, `id` `0x0100`, `area`
  `0x0101`, **`pos` `0x0102`**, **`size` `0x0103`**, `fillcolor` `0x0104`,
  `caption` `0x0105`, `captionres` `0x0106`, `transparent` `0x0107`,
  `comments…` `0x0108–0x010F`, `font` `0xF000`, `bkgcolor/forecolor/notify/
  gutters/style` `0xF001–0xF005`, alignment/bevel enum words `0xF006–0xF00E`,
  `colorfont*` `0xF00F–0xF014`, `align` `0xF015`, `image/imagetype/imagerect`
  `0xF016–0xF018`, `outline` `0xF019`, `winflag_visible…winflag_alphablend`
  `0xF01A–0xF026`.
- **`pos=(x,y)` + `size=(w,h)` is a legal alternative to `area=`** —
  registered, parse-side `(%d,%d)` support, zero corpus uses. Every geometry
  regex the mod owns keys on `area=` and would silently scale nothing on a
  script using `pos`/`size`.
- **The tag grammar has 14 entries** (`0x0094B740`–`0x0094BA20`, registered
  through `[vt+0x24]`): `LEGACY` `0xFA450242`, `children`/`_children` 1,
  `/children` 2, **`define` 3, `name` 4, `val` 5 — a real, unexercised
  sub-language no shipped script uses**, `none`/`_null` 0, and legacy font
  faces `comic9`/`comic10`. `0x0094B995` is the `LEGACY` registration, not a
  handler.
- **There are 13 `winflag_*` names, not 14** — 11 universal (5,964/5,964)
  plus `winflag_acceptfocus` (5,852) and `winflag_alphablend` (5,845). The
  exe registers exactly 13.
- **The 13 names' runtime BITS are now pinned** (`SC4-UI-ENGINE.md` §3.1a) —
  the `0xF01A..0xF026` ids above are parse-time tokens only, not the flag.
  Measured via disassembled `GetFlag`/`SetFlag` call sites (real slots
  `vt+0x10C`/`vt+0x110`, not the vendor header's `+0x108`/`+0x10C`):
  `visible`=`0x1` (`IsVisible`=`GetFlag(1)`), `enabled`=`0x2`
  (`IsEnabled`=`GetFlag(2)`), `alphablend`=`0x4`, `moveable`=`0x100`,
  `sortable`=`0x800`, `pbuff`=`0x10000`, `pbufftrans`=`0x20000`,
  `pbufferase`=`0x40000`, `mousetrans`=`0x80000`, `ignoremouse`=`0x200000`,
  `acceptfocus`=`0x8000` — 11 of 13 with a disassembled test site.
  `sizeable`=`0x200` and `pbuffvid`=`0x100000` are header-only (not
  independently disassembled here) but consistent with a header that is
  otherwise 13/13 correct including two non-`.UI` bits (`UseFade`=`0x20`,
  `DelayedPlot`=`0x8000000`).
- **`font=4888` is `font=default`.** The two numeric spellings in the stock
  corpus (`font=4888` ×45, `font=0x00001318` ×14) are one token, `0x1318`,
  which is the loader's own id for the keyword `default` (registration
  `push 0x1318; push 0xAD63FC` at `0x00955823`). No FontStyle GUID `0x1318`
  exists in either font table, so both spellings land on the
  `GetStyleByGUID` fallback `0x68963C4C` "Default". Builders must anchor
  `font=` name matching on a leading letter, never `\w+`.
- **The value grammar** is enumerated by the serializer's own printf
  templates (`0x00AD6E2C`–`0x00AD6EC4`): `%d`, `0x%08x`, bare token, quoted
  string, `(%d,%d)`, `(%d,%d,%d,%d)`, `(%u,%u,%u)` RGB, double-RGB,
  `{%08x,%08x}`, and the OptGrp `option` forms. Parse side: `image=` is
  scanf'd with `%x`, so `0x`-prefixing and case are both tolerated. Four
  tuple-valued attributes are **not pixels** and must never be scaled:
  `minmax`, `minmaxvalue`, `linepagecount`, `insertpos` (plus the counts
  `maxtext`, `maxundo`, `caretperiod`, `charlimit`).
- **Corpus census:** 281 layout scripts, 5,964 `<LEGACY>` elements, 884
  `<CHILDREN>` pairs, 329 top-level roots, 192 distinct attributes, 36 clsid
  values, 4,215 `id=` attributes over 1,408 distinct ids; 21 multi-root
  scripts (My Sims `I-aa1f1f57` has nine roots; the ninth is `0xABB26B0E`);
  **maximum `<CHILDREN>` nesting depth 4**, the files distributing 98 / 116 /
  63 / 4 by their deepest level — so a recursive walker needs no depth guard
  beyond four, and anything reporting depth 5 is reading its own output.
  Four classes appear **exactly once in the whole corpus**, each pinned to one
  file, which makes a per-class change testable against a single script:
  `GZWinOptGrp` and `GZWinOutline` (both `I-49d55c68`), `GZWinTreeView`
  (`I-8a5ab1cd`, City Import), `GZWinScrollbar` (`I-ebd0d36c`, Select A
  Bridge); `GZWinSpinner` is 31 instances confined to five files
  (`I-49d55c68`, `I-6bc61f19`, `I-aa3acdfe`, `I-cbc3c2b9`, `I-e9263d4d`).
  Attribute omission is per-FILE, never per-element — an editor-version
  signature. Every custom (hex-clsid) class writes only base-window
  attributes; the exception `0xAA7CECFD` carries the GZWinText set and
  declares `iid=IGZWinText` (§8.1).
- **Nothing in the shipped corpus is a dead attribute** — all 192 names
  appear in the dictionary. The converse is false: 199 of the 391 keywords
  are never used by the corpus (among them `pos`/`size`, `imagetype`,
  `alpha`, `blttype=divider|bluebar`, six button styles, the whole
  `GZWinLineInput`/`GZWinFileBrowser`/`GZWinTextTicker` classes, and
  `dbgdrawarea`/`autofit` on GZWinText). A string scan of the exe
  under-reports this vocabulary (the literals are pooled and shared — `align`
  sits in the particle-effect keyword table), so the registration tables are
  the only existence authority.

**Workaround.** Both builders parse quote-aware and anchor on attribute
names; the two partition the corpus with zero overlap. **Counts re-measured
2026-08-30 (this line read "selective-safe 88 scripts, dialog-static 163;
together 251 of 281" and has drifted):** `tools\dialog-static\stage\` holds
**164** `.ui` files over 164 distinct script instances,
`tools\selective-safe\stage\` holds **89** files over **79** distinct
instances, the two instance sets do not intersect, and their union is **243**
of the 281. Re-derive these from the stage directories rather than quoting
them — they move with every builder change.

---

## 6. Fonts and text sizing

**Gap.** Two entirely separate text systems exist, and the SDK documents
neither; the second is outside the `cIGZWin` model entirely.

**Known.**

- **System A — FontStyle** (`GZWinText`, button captions): styles are looked
  up by GUID. The `GZWinText` deserializer (`0x94e516`) honours only a
  token-resolved (GUID-valued) `font=`; a raw string value dead-ends in
  property `0xFAA4AE85`, which has zero consumers in the image. The round-
  trip serializer writes `font=0x%08x`, so hex-GUID form is accepted — the
  shipped fix converts every `font=NAME` to its GUID. `cSC4WinText`
  (`0xAA7CECFD`) resolves through the same path (§8.1).
- **System B — the built-in HTML engine** (all rich text: news, advisors,
  My Sims stories, ordinance descriptions): its size tables live in
  `.rdata`; each rich window **copies** the tables at creation (setter
  `0x8FEEB8`). FontStyle can never reach this path; the only levers are the
  exe's tables (byte patches) and the box geometry.
- **Point size to pixels.** Measured line heights: 15 px @ 13 pt, 28 px @
  24–26 pt. Ink does not scale linearly with point size: measured ×2.13 per
  doubling (n=17), so `round(stockBox·f)` is ~6% too narrow and wraps more
  than stock — size boxes from the font, not from `f`. The reference case for
  a vertical check at a fractional tier is the Graphs "Population by Age"
  chart, whose nine labels `1-10`…`81-90` cannot wrap at any tier.
- **The wrap contract:** SC4's wrap call `sub_896957` (font `vt+0xB8`)
  reads `r->left`/`r->right` and never writes them; the only output is
  `bottom = top + nLines*lineHeight`. The box is an input, not an output.
- **Style names never resolve through the token path.** The tokenizer
  dictionary contains zero FontStyle style names, so a `font=NAME` value has
  no token to resolve to. The operational rule follows: ship `font=0x…`
  GUIDs.

---

## 7. `GZWinCombo`, `GZWinListBox` and scrollbar internals

**Gap.** The SDK declares the classes but none of their internal geometry:
drop-list painting, gutter arithmetic, or the scrollbar widget family.

**Known.**

- Class identities (from the exe's own registries, §8): `GZWinListBox` clsid
  `0x00000598`, iid `0x4132242B`, vtable `0x00AE1780`, Plot `0x009CA19A`,
  ctor `0x009CA883`; `GZWinCombo` clsid `0x0000059B`, iid `0x412CE496`,
  vtable `0x00AE2970`, Plot `0x009CF241`, ctor `0x009CF772`.
- **A combo's drop list paints the engine's standard list colour
  (222,232,227) regardless of the `.UI` flags** — the closed field and the
  open list are one colour; an all-white open list is unreachable from
  `.UI` (measured across three builds while styling the in-game scale
  selector). Chrome matching is therefore done by painting the field to the
  standard colour, not by fighting the drop list.
- **The generic scrollbar family.** Every scrollable GZWin control in the
  game carries the same four ids, stamped by GZ-framework code, not by any
  `.UI`: `sub_99A96E` (`0x0099A96E`–`0x0099AC7E`) allocates a `0x11C`-byte
  object (ctor `sub_99A67E`, vt `0x00ADC398`) into `[owner+0xF0]` and calls
  `SetID(0x42B7C351)` at `0x0099A9F6`; the three children `0x42B7C353/55/54`
  are stamped inside helper `sub_99A70F` (from `0x0099ADBD/0x0099AE3D/
  0x0099AEBA`) with the ids passed as **arguments** — which is why a
  literal-`SetID` census sees only the parent. Any id-keyed rule on
  `0x42B7C35x` hits every scrollbar in the game. In Data Views the bar sits
  under the Map-View page `0x00004200` (265x27 frame, three 24x25 buttons).
- **Pixel-valued attributes outside the builders' scaled set:**
  `scrollbargutters` (3 occurrences in dialog-static, 4 in selective-safe),
  `buttongutter` (3), `combodownarrowrect` (3), `icongutter` (1),
  `minmaxboxsize` (1). `combodownarrowrect=(0,0,64,15)` is the drop-arrow
  rect inside a combo (`I-0a243d80`, `I-e9263de5`, `I-e9a56248`).
- **Client padding never scales at runtime.** The DLL contains no
  `SetGutters`/`SetTextOffsets`/`SetTipPlacementOffsets` call site, so every
  runtime-swept window keeps 1x padding; only the statically doubled scripts
  carry scaled padding.
- **The gutter width ceiling is OPEN, and the stock corpus does not test it.**
  ⛔ **Corrected 2026-08-30:** this bullet used to assert "gutter values are
  not 8-bit in practice", offering the two large stock values as the proof.
  They prove nothing — **247 and 232 both fit in a byte.** What is true: the
  SDK declares the setters 8-bit (`cIGZWinGen::SetGutters(uint8_t,uint8_t)`,
  `cIGZWinText::SetGutters(int8_t,int8_t)`,
  `cIGZWinCombo::SetBtnGutter(int8_t)`); the stock corpus reaches
  `gutters=(247,201)` (`I-8a7e052f`, Graphic Options, `0x2A57CB84`) and
  `(232,232)` (`I-aa5e60d1`, `0xCA5E6261`); and **the shipped 2x package
  writes `(494,402)` and `(464,464)` into those two scripts** — verified in
  `tools\dialog-static\stage\` — which nothing has ever read back. Both
  at-risk windows are `GZWinGen`, the one class whose gutter field width is
  *not* pinned by `SC4-UI-ENGINE.md` §3.0a (which does pin `GZWinText`
  `+0xE4`/`+0xE5` as a signed byte pair, `GZWinBtn` `+0x102..+0x105` as four
  unsigned bytes, and `GZWinTextEdit` `+0x158`/`+0x15C` as dwords) — so for
  `GZWinText` a value over 127 already truncates and for `GZWinBtn` one over
  255 does. **The one measurement that settles it:** call `GetGutters` on
  `0x2A57CB84` in the deployed 2x build — `(494,402)` means no ceiling,
  `(238,146)` means truncation and every tier above 1x needs a clamp at
  127/255 by class signedness.

---

## 8. The class registries and SC4-specific window classes

**Gap.** The exe carries two name tables that together name every window
class in the game without a guess; the SDK ships neither.

**Known.**

- **(a) The `.UI` class registry — `0x00B16FA8`…`0x00B170A3`, 21 entries of
  12 bytes `{clsid, iid, char* name}`.** The authority for the `GZWin*`
  family; exactly 21 scriptable widget classes exist. `0xAD5CE0` and
  `0xAD5CAC` are the class-name strings the `GZWinBMP` and `GZWinBtn` rows
  point at; there is no per-class descriptor record.
- **(b) The GZCOM clsid→name table, `~0x00B05000`…`0x00B0B000`, 8-byte
  `{id, char*}` pairs, 906 resolvable entries** — the authority for the
  `cSC4Win*` classes, simulators and command ids.
- **(c) The SC4 window-class registration function `sub_004662B0`** — 17
  `{factory, clsid}` pairs via `AddClass 0x0090E133`. Each factory is
  `new(size) → ctor → return obj+N`, where **N is the byte offset of the
  cIGZWin sub-object** — the fact that tells you which of a class's several
  vtables the window tree will show.

### 8.1 Reading the catalogue rows

- **`0xAA7CECFD` is `cSC4WinText`** (named `kcSC4WinText` in
  `GZCLSIDDefs.h`, absent from the exe table). Its factory `0x007BE740`
  allocates `0x114` bytes, runs `cGZWinText`'s own constructor `0x009C19C8`,
  then swaps the vtable to
  `0x00ABA190` — which differs from `GZWinText`'s in exactly two slots: 88
  (Plot → `0x007BE7A0`) and 148 (dtor). Same object layout, same font code;
  only the painter differs. It is reached by GZCOM clsid instead of by the
  `.UI` class name, which is why it sits outside the `GZWinText` name path
  and scales off FontStyle with no help.
- **`cSC4WinGenTransparent` (`0x89E1567C`, vt `0x00AB7358`)** differs from
  `GZWinGen` in exactly two slots of 151: 121 (the hit-claim `0x0079C5C0`)
  and 148. It is an ordinary container, provably.
- **`0x00ADCB38`** is a `cGZWin` subclass whose only override is slot 89
  (`0x0099C291` against base `0x0099BA07`). Slot 89 is **`Plot`** (§1), and
  the override is **a gated `Plot` wrapper with a self-destruct branch** —
  nothing in it touches a rect. Body: `call 0x0099C20D; test al,al;
  je 0x0099C2B6` → **true** path `call 0x0099BA07` (the BASE `Plot`), stash
  `al` in `bl`, `call [vt+0x170]` (slot 92 `InvalidateSelfAndParents`), return
  the base's result; **false** path `mov ecx,[esi+4]; push esi;
  call [eax+0x5C]` — the window manager's `DestroyWindow` (§4) — then return
  `true`. The predicate `0x0099C20D` tests winflags `0x20` and `0x10000`
  (`test dl,0x20` / `test edx,0x10000` at `0x0099C219`/`0x0099C21E`), then
  `QueryInterface(0xE6E998FD)` through `vt+0x1C4` and reads a byte via
  `vt+0x12C`. **⚠ Corrected 2026-08-30.** This row previously read "slot 89
  `CalcAbsoluteArea` — a coordinate-remapping clip viewport that paints
  nothing; scaling it moves every descendant's absolute rect." Two errors:
  the slot NAME (`CalcAbsoluteArea` is slot **90**, base `0x0099DCE4`), and
  the MECHANISM — the disassembly contains no rect arithmetic at all, so the
  "scaling it moves every descendant's absolute rect" rule was unsupported
  and is **withdrawn**. The slot COUNT was right: a full 151-slot diff
  against `GZWin` `0x00ADC8D8` gives exactly `{89}`.
- **`0x00AB8150` is not a window vtable.** It fails the slot-87 fingerprint
  (its "slots" read `0x800B`/`0x800A`/`0x6005`/`0x5007`); it is the secondary
  COM-interface vtable of `cSC4WinMapView` (clsid `0x28C5A41F`, factory
  `0x00466080` returning `obj+0xE0`).
- **The gauge class `0xCBCBF1E0`:** outer vtable `0x00AB4900`, window vtable
  **`0x00AB46A0` at `obj+4`** (factory `0x00466220` returns base+4), Plot
  `0x00762830`, ctor `0x007628E0`, custom iid `0x0BCBF1DF`, 0x108 bytes.

### 8.2 `cSC4WinAlertBorder` — the full-screen frame painter

clsid `0xCA5D3294` (name string `0x00A895FC`, registry `.data 0x00B08F70`),
iid `0xCA5D3290`, vtable `0x00AB5B48`, ctor `0x00794060` (0xEC bytes; image
ptr `+0xE4`, render-props singleton `+0xE8`). Created by the 3D view at
`0x007EF029` (inside `sub_7EDEB0`), sized to the whole view at `0x007EF069`
(no baked constant), id stamped at `0x007EF072` (`SetID 0x6A5E44B6`); flags:
PrivateBuffer off, IgnoreMouse on, AlphaBlend on. Its Plot `0x00794100` is a
tiling nine-slice frame blit — cell `(imgW/3, imgH/3)`, corners unstretched —
through `0x008D9550` (one caller image-wide), gated on the image at `+0xE4`
and `[renderProps+0x0C]+0x45C` (= `kDisplayAlertBorders`, property id `0x22`,
stride `0x20`). The single image field `+0xE4` is set by `sub_00793FF0`
(secondary vtable `0x00AB5B20` slot 4); `sub_7942F0` is **not** a method of
this class. State selection — `UpdateAlertBorder 0x007E8A90`: disaster → RED
`0x14315E60`; situation → GREEN `0x14315E62`; paused → GOLD `0x14315E61`;
else `SetImage(NULL)`. The window is skipped by the sweep's ≥90%-of-screen
geometry guard, and the frame thickness is the art's pixel count, so the
scaling lever is the art alone (three sheets shipped at all tiers; `/3` exact
in every case).

### 8.3 `cSC4WinAuraBar` — the region bubble's Mayor Rating bar

clsid `0xAA5D16A9` (name string `0x00A89594`, registry `.data 0x00B08FA0` —
neighbours `0x00B08F98` `cSC4WinAdviceList` and `0x00B08FA8`
`cSC4WinGenTransparent`, which is the bubble root's own class), iid
`0x4A5D1208`, vtable `0x00AB64B8`, Plot
**`0x00797CC0`**, ctor `0x00797E60`, factory `0x00797F20` (0xF8 bytes,
returns `obj+0xE0`); sub-vtables `0x00AB64A0` at `+0xD8` and `0x00AB6488` at
`+0xE0` (slot 3 `SetImage` → `+0xF0`, slot 4 `SetFraction` → double at
`+0xE8`, clamped by `[0xA80990]=0.0`/`[0xA80AB0]=1.0` at `0x797C20`). The
class is registered and shipped; its only corpus appearance is the region
city-select bubble `I-ca539340` (window `0x4A553000`, 102x11 at (11,92)).

**Hook handles**, if a code route is ever needed: the primary-vtable slot to
repoint is `.rdata` **`0x00AB6618`** (= `0x00AB64B8 + 0x160`), reading
`0x00797CC0`; the detour prologue at `0x00797CC0` is
`83 EC 14 56 8B F1 8B 86 F0 00 00 00`. `[+0x24]` (dst) and `[+0x68]`
(destination buffer) are **base-class** fields, not AuraBar ones — §1 slots
99 and 94; the draw context is `+0x6C`, not `+0x68`. The class's own fields
are `+0xE8` fraction and `+0xF0` image.

**Vtable diff, as the §8.4 step-5 worked example.** `0x00AB64B8` against
`GZWinBMP` `0x00ADF6A0` over slots 0…119 differs at exactly
**`{0, 1, 2, 3, 4, 5, 55, 62, 88}`** — the COM/lifetime head, slot 55
`SetArea`, slot 62 `IsPointInWindowScreenCoordinates`, and slot 88 `GZPaint`
(`0x00797CC0` aura / `0x009BC325` bmp / `0x009B167D` btn). **Pick the base
deliberately**: against `GZWinBtn` `0x00ADDAF0` the same walk gives
`{0…5, 55, 63, 64, 68, 73, 74, 79, 88}` — six extra slots and no 62 — so the
clean three-slots-past-the-head signature is AuraBar-vs-`GZWinBMP` alone. A
diff against the wrong sibling reads as a richer class than the one you have.

**Draw law** (byte-for-byte at `0x00797CC0`):
`src.L = (imgW − winW) >> 1`; `src.R = src.L + winW`;
`src.T = ftol(fraction × (imgH − 1) + 0.5)` (rounding constant `[0xA92D28]
= 0.5`); `src.B = src.T + 1`. That 1-px-tall slice is blitted into the full
window rect through the **tiling** helper `0x8D8BC0`, whose period is the
source W×H. The source width comes from the window; the art supplies the
period and the row divisor. At f=2 with 1x art, `winW/imgW = 2.00` exactly —
two side-by-side runs, offset half a period; the number of visible copies is
the scale ratio.

The art is code-bound: the region-bubble controller does
`GetChildAsRecursive(0x4A553000, iid 0x4A5D1208)` at `0x007B5157`,
`SetFraction` at `0x007B5178` (value = `rating/200 + 0.5`, computed at
`0x007B4FB5`–`0x007B4FDE` with `[0xAB98B8] = 0.005`), then binds
`{0x856DDBAC, 0x46A006B0, 0x14416327}` at `0x007B517E` — the sole `0x14416327`
immediate in `.text`. The bitmap is referenced by zero `.UI` scripts and is
therefore invisible to the ref-driven art builders.

**The sheet is a 102x26 BIDIRECTIONAL meter, not a fill ladder.** ⚠
*Corrected 2026-08-30 — this paragraph previously read "26-row state stack
(pitch 4: 3 px colour + 1 px `FF00FF` key; row 0 = zero cells filled … row 25
= all filled)". Both halves are wrong, and `build_selective_safe.py:464`
("102x26, 24 cells") and `REGRESSION.md`'s "24-cell segment ladder" were the
correct record all along.* Decoded pixel by pixel: **24** cells, every one
exactly 3 px, separated by `FF00FF` key — but the gaps are `[1 ×11, 8, 1 ×11]`,
not a uniform pitch 4, because an **8 px key block at x=47…54 is the centre
divider**. Geometry closes exactly: `24×3 + 22×1 + 8 = 102`, lead 0, trail 0.
The bar is anchored at that centre and its arm length carries the rating:
row 0 = cells 0…11 RED (`FF0000`) reaching the left edge (worst); the red arm
shrinks toward the centre one cell per row to row 11 (cell 11 alone);
**rows 12 AND 13 are all grey (`BBBBBB`) — neutral is two rows, not one**;
then GREEN (`00FF00`) grows rightward from cell 12 at row 14 to cells 12…23
at row 25 (best). Triage value: the "two runs side by side" symptom means
**two centre gaps**, which is the discriminator against a stretch/clamp model.

**Fix shipped** (`z_SC4UIScale_SelectiveArt*.dat` — **not** DialogStatic,
which carries the bubble's other nine arts but not this one): a **uniform**
upscale, **204x52 / 153x39 / 306x78**, matched to clone windows of
**204x22 / 153x17 / 306x33** (`I-ca539340`'s `area=(22,184,226,206)` /
`(17,138,170,155)` / `(33,276,339,309)` — name the window when quoting
"153x17", since the unrelated HUD groove `0x8A517556` is also 102x11 at 1x
and produces the same string). `imgW == winW` at every tier, so `src.L = 0`
and the doubling symptom is gone. ⚠ *Corrected 2026-08-30: this line
previously read "the art at 204x26 (width ×2, height unchanged — `imgH` sets
the state divisor), 153x26 at 1.5x, 306x26 at 3x". That was a PROPOSAL that
never shipped, absorbed here as history. Verified by reading the PNG IHDRs at
the `package-list*.txt` offsets and off `tools/selective-safe/stage*`.*

**Residual on the shipped fix — one ladder cell, cosmetic.** The width-only
204x26 sheet would have been byte-identical to stock; the uniform 204x52 is
an exact 2× block replicate (verified: 0 mismatching pixels of 10,608), which
makes the row divisor 51 instead of 25. Comparing `ftol(f×25 + 0.5)` against
`ftol(f×51 + 0.5) // 2` over the real domain (`f = clamp(rating/200 + 0.5,
0, 1)`, rating a signed byte) diverges on exactly **23 of the 201 integer
ratings**, always by one cell — 6 px at 2x — first at rating −96. Do **not**
carry the claim that 23 holds "under both plausible row maps": `floor(j/2)`
is the MEASURED map and gives 23; a `round` map gives 57.

The CITY HUD's rating bar is a different implementation entirely (four
`GZWinBMP`s, groove `0x8A517556` art `14015549`); the two share no code and
no art. Its controller is **the function entered at `0x007E8510`
(size 1408 → ends `0x007E8A90`, the next start, `UpdateAlertBorder` §8.2)** —
the `imul …,7` arrow block at `0x7E86C0`–`0x7E8A80` sits INSIDE it and is not
a function boundary. *(Corrected 2026-08-30 against `tools/uimap/funcs.json`:
`0x7E8510` is a start, `0x7E86C0` is not; `0x7E851D`, `0x7E86C0`, `0x7E86E5`,
`0x7E87B1`, `0x7E89D7` and `0x7E8A02` all bisect to `0x7E8510`.)

### 8.4 The identification procedure

Given only a `vt=XXXXXXXX` in a log line: (1) range-check — game classes live
in `0x00A80000`–`0x00B20000` and are fixed for the build; anything else is a
relocated module — the mod's own shadow copies. Restart the game and re-read:
exe vtables print identically, DLL vtables move. (2) Confirm it is
a window vtable: `[vt+87*4] == 0x0099BE4C`; if not, it is a secondary COM
interface and the real window vtable is at another object offset. (3) Read
slot 0 `QueryInterface` and collect its `cmp` immediates — the iids — and
look them up in the two registries. (4) If `QueryInterface == 0x0099B774`
the class overrides nothing (re-measured 2026-08-30: 13 of the 111 census
classes carry the base slot 0, including all three region layers); only its
Plot can identify it. (5) Diff the vtable against
its base over slots 0…150 — the differing slots ARE the class. **Choose the
base deliberately and say which one you used**: §8.3 works the AuraBar
through both, and against the wrong sibling it reads as six slots richer than
it is. (6) Find the
ctor by searching `.text` for the vtable VA (two hits: ctor and deleting
dtor); the ctor's `mov [reg+N], <vt>` must equal the factory's `add eax, N`.
EXACTLY the audit row whose replacement opens `(7) Cross-check the name against **the exe's own class registry** — a table`, applied UNMODIFIED. Anchor verified unique (line 1144).

---

## 9. Art binding beyond the ref map

**Gap.** Four distinct paths feed pixels to the screen; only path 1 (`.UI`
`image=` refs) is visible to script-derived tooling. Full reference:
`SC4-UI-ENGINE.md` §4; `UI-ART-BINDING.md`; §2 above for `GZWinBMP` itself.
*(Repointed 2026-08-30 — there is no `SC4-UI-ENGINE.md` §4A.)*

**Known.**

- **The store type is generic.** `0x856DDBAC` is an image type, not PNG: of
  2,280 entries, 2,206 are PNG, 41 are JFIF (all of group `0xCA133ECB`), 26
  are SHPI/FSH (inside `0x46A006B0`), 7 are Windows BMP (inside
  `0x6A1EED2C`). None of the 74 non-PNG entries is `.UI`-referenced.
- **The twin structure is exact, and there are three twins.** `0x1ABE787D` is
  a strict subset of `0x46A006B0` (743/743 of its instances; the larger group
  has 810). Group `0x00000001` is a third twin: all 62/62 of its members
  exist under both. Covering a shared instance can mean covering three TGIs.
- **Path 1b — the dangling ref.** A well-formed `image={g,i}` whose TGI is in
  no shipped archive; the pixels arrive at runtime from a binder. Every
  offline instrument reports it as ordinary path 1. Shipped instances:
  `0a243d80` Select-A-Sim (22 cells `0x12340000..15`, stand-in TGI
  `{46a006b0,ea32f104}`, runtime pixels generated — rect must NOT double),
  `4bf325e8`/`abfaef15` U-Drive-It (28/14 cells `0x23450000+i`, runtime
  pixels from group `0x4C06F888` via exemplar property `0xEBFC5E5E` — rect
  doubles). The binder stanza: `push <inst>; push <group>; push <type>;
  call 0x602B70` then `call [vt+0x10]` (worked example `0x770154`–`0x7701BD`).
  Recognise from a build log: `WARNING LEFT1X … DANGLING`.
- **Path 2 census (code-bound art).** All code-bound art goes through one of
  two image-request constructors: `0x602B70` (TGI by value; writes vtables
  `0x00A856CC`/`0x00A80810`, triple at `[obj+0x08..0x10]`) and `0x602B00`
  (TGI by pointer); release `0x602BE0`. 76 sites total (50 + 26); 67 carry a
  literal group; 9 take the group from a property/table (`0x5DDE3C`,
  `0x5DDE4E`, `0x5F4881`, `0x6464EE`, `0x675E0D`, `0x6824B9`, `0x6859C9`,
  `0x7EEE20`, `0x7F053C`). **`type = 0` is a legal argument** ("resolve by
  group+instance") — both `0x4C06F888` thumbnail sites push 0. A push-only
  scan under-reports (the TrendBar loads its group into registers at
  `0x7ED4B4`); scan for the constant, not the instruction.
- **Three groups are code-only** (zero `.UI` refs, in no builder's list):
  `0x6A1EED2C` (4096x4096-class BMPs — splash/loading/world, not UI; leave
  alone), `0xAB7E5421` (93 images, one site `0x5F12FB`; cursor/overlay
  class, unidentified), `0xA9179251` (4 images, site `0x7DB4E7`,
  unidentified). Do not stage blind.
- **Wrong-group refs exist.** `{82b9b75b,e2b66db8}` (`I-cb40cfdc`, the
  Apply/Remove Label buttons): group `0x82B9B75B` has zero index entries in
  all seven archives while instance `e2b66db8` is a real strip under
  `0x46A006B0` referenced by 29 other scripts. The classifier tests
  ⛔ **REQUIRED, NOT DONE.** *Corrected 2026-08-30: this line previously read
  "The classifier tests instance-level presence before declaring a ref
  DANGLING." **It does not.** `build_selective_safe.py:3538-3541` builds
  `store_tgis` as a set of `(group, instance)` PAIRS, and both classifier
  sites test only that pair — `:2876 if key not in store_tgis:` →
  `DANGLING .UI ref - runtime-supplied pixels (task #47 family)`, and
  `:3776-3778 kind = ('DANGLING …' if (gid, iid) not in store_tgis else
  'MISSING-2X …')`. The file carries no instance-only index at all (searched
  for `store_iids` / `instance_index` / `iid_index` / `by_instance` /
  `store_instances`; the only hit is an unrelated `script_iids` at `:3216`).*
  So `{82b9b75b,e2b66db8}` would still be labelled DANGLING and would send a
  reader to a draw hook instead of a one-line retarget. **Latent, not live** —
  `I-cb40cfdc` is in neither stage set — but a doc claiming a fix the code
  lacks is worse than no doc, because `TRIAGE.md` routes people here as the
  authority. The fix is a third class at those two sites: group missing but
  instance present ⇒ **wrong-group ref**, not runtime pixels.
- **ItemIcon group `0x6A386D26` is two families.** 320 × 176x44 (the
  exemplar-referenced 4-cell strips; 266 carry an exemplar reference) and
  **36 × 356x58** with sequential structured instances `0xMM0000NN` — bound
  to the one-widget 89x58 template script `I-ebd0d36d` (no `image=` at all),
  referenced by no exemplar and no `.UI`. The 89 px template width is the
  sidebar strip width; the group constant sits at `0x78EE15`, `0x7ECB50` and
  `0x7F038F`.
- **Full residual census (register #9).** Manifest: `tools/dbpf/extracted-png-tgi.csv`
  (2,280 rows, type `0x856DDBAC` only — byte-identical to
  `tools/dbpf/extracted/SimCity_1/extract-manifest.csv`). Union of the four
  known-bound sets — `.UI` refs (`refmap.csv`, 431 distinct `{gid,iid}`),
  ItemIcons (`tools/itemicons/_work/item_icons.csv`, 266 distinct instances
  in `6a386d26`), HTML `sc4://` refs (`html-image-refs.txt`, 59 pairs), and
  the **shipped** `CODE_BOUND_TGIS` in `build_selective_safe.py` (341
  distinct pairs, evaluated in-process — not the illustrative table in
  `SC4-UI-ENGINE.md` §4.2) — is 1,009 pairs, of which **983 resolve to a
  real manifest row and 26 do not**. The 26 are all already-named
  dangling/wrong-group refs: 21 unused instance numbers inside the
  `140155B4..F7` span plus `ec1392ac` (22 total — matches
  `predictive-defect-sweep.md`'s independently-logged "missing 2x asset,
  skipped: 22" exactly), the two Select-A-Sim/U-Drive-It stand-ins
  `ea32f104`/`6b998f30`, one third-party (CAM_Intro.dat) dangling ref
  `ea7f0eae`, and the wrong-group `{82b9b75b,e2b66db8}` above. **2,280 − 983
  = 1,297 real PNGs with no currently-known binding path** — not the ~1,850
  figure elsewhere in this doc, which only subtracts `.UI` refs and does not
  net out paths 2/2b/3/4; of the 1,853 PNGs with no `.UI` ref, only 556 are
  actually covered by a known non-`.UI` path, leaving 1,297 (70%) genuinely
  unaccounted. By group: `1abe787d` 704, `46a006b0` 257, `ab7e5421` 93
  (100%, already named above), `6a386d26` 90 (36 = the `0xMM0000NN` family
  above, 54 unaccounted), `00000001` 61 (98% — a twin-coverage gap, not new
  art: only `14416315` is `.UI`-referenced in this group), `ca133ecb` 41
  (100%, the JFIF tutorial screenshots — no binder found for any of them),
  `22dec92d` 27 (69%, entirely `0x00xxxxxx`-structured, unaccounted),
  `6a1eed2c` 20 (100%, already named above), `a9179251` 4 (100%, already
  named above).
- **Inside the twin groups the residual clusters into named 2-byte
  sub-families** (leading 4 hex digits, summed across `46A006B0` +
  `1ABE787D` + `00000001`): **`1441xx` 288** — largest single bucket,
  mechanism not identified; **`1401xx` 98** — same numeric family as the
  shipped `140155B4..F7` span but with different mid-bytes, not yet staged;
  **`1421xx` 85** — this is the **Mayor Mode mood/rating band already
  decoded instance-by-instance in `MAYOR-MODE.md`** (`14215e20..2c`,
  `30..35`, `40..46`, `50..55`, `60..64`, `70..76`, `80..86`, `d0..d5`,
  `dd`) but **absent from `CODE_BOUND_TGIS`** — check whether Mayor Mode
  art ships through a separate package script before assuming this is
  unstaged; **`1431xx` 10** — extends the 3-member alert-border family
  (`14315E60/61/62`) already in `CODE_BOUND_TGIS`. A second cluster is
  **`ecxxxxxx`, 130 residual** (74 `1abe787d` + 56 `46a006b0`), in two
  dense runs: `ec1392[98-ad]` (~22, already covered by
  `html-image-refs.txt` for the `46A006B0` copy only — the `1ABE787D`
  twin copy is the true residual, same twin-coverage gap as `00000001`
  above) and `ec212d[80-9f]`/`ec212e[01-21]` (106, plus lone `ec238e71`)
  — **no existing doc names this run; it is the next `.text` imm32 scan
  target.** A third pattern recurs across `1abe787d`/`46a006b0`/
  `ab7e5421`/`ca133ecb`/`6a1eed2c`: instance IDs sharing a low nibble on
  the top byte across the even/odd top-nibble cycle (e.g.
  `0b/2b/4b/6b/8b/ab/cb/eb`, or the `a`/`c` equivalents), hundreds of
  instances total, cause not identified.
- **Path 4 (runtime-generated pixels) has two sub-shapes:** 4a — no `image=`
  at all (invisible to every ref scan); 4b — dangling `image=` (counted,
  warned, and its `imagerect` is editable — right for the U-Drive-It pickers,
  wrong for Select-A-Sim). **The power-of-two buffer law:** runtime pixels
  are composed into a power-of-two `cIGZBuffer` (class vt `0x00AC1400`) and
  occupy only a top-left sub-rect (measured: 36x41 into 64x64 at ~6 Hz per
  portrait cell; 152x38 and 91x77 into 256x256). Doubling a path-4
  `imagerect` samples past the live data into the POT padding.
- **The BMPX draw log has a global cap of 40 lines that RE-ARMS PER CITY**
  (`src\UiSpike.cpp`, grep `gBmpDrawLog`), shared by every hooked window;
  one busy window exhausts it. A missing `BMPX draw` line means, in order:
  the budget was already spent *for this city*; the window is under no hooked
  root; only then, the class is not `GZWinBMP`.
  *Corrected 2026-08-30: this bullet said "session-lifetime cap of 12 lines".
  Both halves were wrong — the test is `gBmpDrawLog < 40` and the counter is
  reset in `Disarm()` and again on a fresh open. Both numbers are load-bearing
  for the triage order above, so a reader was being told to expect the wrong
  budget and the wrong reset behaviour.*

**Workaround.** The decision procedure for a wrong-art widget
(`SC4-UI-ENGINE.md` §4.1–§4.6 — the four art-binding paths and the
classification the builder actually uses; §4.7 is the separate flash-cure
question): confirm the live script is the one loaded → anchor the grep on `image=`
→ does the TGI exist (and under which group) → is it staged under all its
twin TGIs → is `imagerect` consistent with the art it got → for path 1b find
the binder, not the art → separate paths 2/2b/4 by where the constant lives →
only then reach for a hook, with the class positively confirmed.

---

## 10. The region screen

**Gap.** The region screen is not a mode of the city screen but the
alternative occupant of the same slot, and none of its architecture is in
the SDK. Full reference: `REGION-SWITCH.md` (its opening summary, above
§1) and `REGION-SCREEN.md`.

**Known.** `WinSC4App 0x6104489A` has exactly one child: in a city
`0x9A47B417` (`cSC4View3DWin`), on the region screen `0xEA659793`
(`cSC4WinRegionScreen`, registry `.data 0x00B08FC0`). The host has 13
children: nine panels + four full-screen layers (68 windows total at stock
800x600). Code-created top-level screens carry their clsid as their window
id (three for three). The tooltip layer `0x2AAB8CC1` is a sibling of
`WinSC4App` under the main window, empty and hidden on the region screen.

- The nine panels are the complete whitelist `kRegionPanelIds`; four are
  born hidden (`0x0BB0F5E7`, `0x6BB92BCA`, `0x09EBEE45`, `0x09EBEE60`) and
  are scaled anyway (pre-scale-while-hidden originated here).
- **Anchoring:** the game re-anchors with constant pixel gaps at every
  resolution (measured identical to the pixel at 800x600 and 2400x1600); the
  project re-anchors with scaled gaps. Two negative design gaps
  (`0x09EBE9EE` bottom −2, `0x09EBEE60` top −1) and one deliberately
  over-wide centred bar (`0x6A91DC14`, 1154 px in an 800 frame) mean any
  unconditional on-screen clamp is wrong here.
- **The city-select bubble `0x0A551C50`** hangs under the full-screen map
  layer `0x2BA6BB97` (`cSC4WinRegionView`), so the runtime sweep can never
  reach it; the static dat is its only lever. One window id serves three
  scripts chosen in code at click time: `I-ca539340` (existing city, 258x250)
  vs `I-0a8cd184` (start new city, 216x165) selected at
  `0x007ACC34`/`0x007ACC40` on the predicate at `0x007ACC2A`; the narrow
  stub uses a third id, `0x0A551C53`, from `I-ca539343`. The bubble
  controller (`0x7B5E20`) stores `scriptIID → [obj+0xF0]`, `windowID →
  [obj+0xF4]`. Never key a record or a geometry expectation on `0x0A551C50`
  alone. The script's `area=` L/T is discarded — size comes from the script,
  position from the game.
- **Lifecycle:** nothing in the region host subtree survives a city visit —
  every arrival is a fresh build at design geometry (boot, live switch, and
  return from a city alike), so purge-on-fresh-root is load-bearing on all
  three paths. The sweep tick is 16 ms; the stability gate is two equal child
  counts (~32 ms); measured region-up latency on a return: 12 ms.
- Region ids are not region-exclusive: `0x0BB0F5E7` and `0x6BB92BCA` also
  exist under the 3D view at different design sizes from different scripts.
- The four full-screen layers: the map layer `0x2BA6BB97`
  (`cSC4WinRegionView`); the cloud emitter `0x6A0AF41D` (vt `0x00AB88C0`,
  code-created, id stamped at `0x007A99DF`, §10.1); and two anonymous ones,
  vt `0x00AB8CD0` (an animating list) and vt `0x00AB8F50`.

### 10.1 The region cloud emitter (`0x6A0AF41D`)

`Plot = 0x007A9D60` is a particle emitter drawn through the 3D device, not a
`cIGZWin` blit: init `0x7A99C0` loads the four texture ids
`0x4A624656..0x4A624659` (iids `{0x1AC0E11A, 0xFAC0E219}`) and latches the
emitter bounds once (`view->GetW/H → float [+0x100]/[+0x104]`); the spawner
`0x7A98E0` starts each sprite at `x = 0 − K`, `y = rand·H`, advances
`x += vx·dt`, despawns at `x ≥ [+0x100]`; quad corners at `±K` where **`K =
[0xAB7E10] = 128.0f`, hardcoded**. Art: `T=0x7AB50E44 G=0x1ABE787D
I=0x4A624656..59`, four DXT3 FSH at 128x128 (white wispy clouds), blitted
1:1. Resizing the window is a no-op; the only "1x" thing is the sprite size,
a code constant. Cosmetic; leave alone. The two levers, if ever wanted: the
float at `0xAB7E10` and the four-TGI art set.

---

## 11. The geometry call sites in `.text`

The game sizes every code-built window through one of four `cIGZWin` slots,
so the whole population of code-driven geometry is enumerable from the image.

- **Population:** `.text` spans `0x407000..0xA7FA2D`. A 6-byte scan for the
  cIGZWin geometry slots (`FF /2 disp32`, disp ∈ {`0xD4 SetSize`, `0xD8
  SetArea(Rect*)`, `0xDC SetArea(l,t,r,b)`, `0xE0 SetPosition`}) across all
  eight ModRM base forms — including ModRM `0x95` (ebp base) and `0x94`
  (SIB) — finds **1026 geometry call sites in 552 functions**, of which 147
  are `0xD8`. 69 functions have `0xD8` as their only geometry call, among
  them the Data Views re-lay `sub_007A04F0` (sites `0x7A082C`, `0x7A0955`).
  On linear disassembly the scan has 0 false positives; it needs the
  high-byte anchor, because a 3-byte substring test matches
  `call [eax+0x1D4]` as `[eax+0xD4]`.
- **Slot `0xD8` carries no coordinates.** It takes a pointer — the pushed
  `lea [esp+disp]` — so constants come from following that `lea` to the four
  member stores, never from immediates at the call site. `sub_007A04F0`
  computes its rect members at runtime, which is why the shipped fix scales
  the origin inside the re-lay instead.
- **Geometry-call count finds builders; caller count finds shared helpers.**
  8 of the 12 named builders have exactly one caller — a top-level dialog
  builder always does. Of the 552 geometry-driving functions, 420 have fewer
  than two callers, and 147 of those make two or more geometry calls.
- **The edge law and the direct law agree at integer factors.**
  `edge_law(pos,len,f) = R(pos+len,f) − R(pos,f)`, which for integer `f` is
  exactly `R(len,f)`; only 1.5x can diverge, and 807 pairs do.
- **Art-rect windows take their size from the art.** For windows built by the
  button factories the exe supplies only x and y; w and h are the art's PNG
  IHDR. The cell rule comes from the create type: type 2 (`sub_77B960`)
  window = the whole strip; type 4 (`sub_77B7B0`) window = one cell.

### 11.1 The row windows (the budget/ordinances dialog contents)

Under dialog `0x0423278F` (stock 450x377): 12 checkbox cells
(ids `0x12C+k`, 16x16, art cell of `{46A006B0,144161EA}` 128x16/8
states), 12 row strips (ids `0x1F4+k` → live `0x2F4+k` by the +0x100 law,
1320x18, art `{46A006B0,140155B7}` 4-state 2640x36), 4 scroll arrows
(`0x551..554`, 64x10), Accept/Cancel (`0x1CD`/`0x16D`, 180x30 by `SetSize`
at `0x77D33F/5F`), the content pane `0x0423278E` and the shared popup
`0x0423278D`. The two id bases are literals: `mov [esp+0x3c],0x12C` @
`0x77C670`, `mov [esp+0x24],0x1F4` @ `0x77C678`, incremented per row
(`0x77CAE2`/`0x77CB1D`) — ids run continuously across the income/expense
boundary. Dialog height closes exactly: `H = 29+23+36·floor(n1/2)+41+23+
36·floor(n2/2)+41+40` (band set `0x140155F0–F7` = 450 × {29,23,36,41,23,36,
41,40}); row counts clamp to 9 at `0x77C829`; slabs = floor(rows/2). The
ordinance name texts live on the content pane (depth 3) and are invisible to
one-level dumps by construction. The Accept/Cancel plate `0x144161EB` is
SHARED (clone+retarget to `0x470261EA`) and bound by six hardcoded pushes: a
code-sized 360x60 button whose art is named by address in `.text`, so a
retarget of the clone leaves those six sites pointing at the original.

---

## 12. Code-created windows and id hazards

A window the game builds in code has no `.UI` script behind it, so nothing
about it appears in a corpus census. The measured detail for the ones that
matter to scaling follows.

- **`0x00000043` Restore-Toolbars:** built by `sub_7EDEB0` from `I-c973b411`
  (`mov [esp+0x6c],0xc973b411` @ `0x007EDECC`): CreateInstance GZWinBtn @
  `0x007EDFF6`, image `{856DDBAC,46A006B0,53244588}` @ `0x007EE02F` (84x19
  4-frame strip, cell 21x19), `SetID(0x43)` @ `0x007EE140`,
  `GZWinMoveTo(0xC, viewH−0x1C)` @ `0x007EE146`, born hidden @ `0x007EE175`.
  The builder never sets a size, so the art's cell decides the extent while
  the origin stays a code constant: art moves the size and never the origin.
  `0x43` and the script-declared `0x44` are the two halves of one feature
  (one in code, one in data), in a dense semantically-allocated command-id
  run; SC4 reuses tiny ids in-image (`0x000000FF` at three unrelated sites),
  so a rule for either keys the pair (builder, script-instance TGI) plus a
  parent check, never the bare id.
- **Id collisions are the mode, not the accident:** 596 of 1409 distinct
  corpus ids (42%) are declared by ≥2 script instances, and 37% of the
  mod's own id-keyed entries are multi-declared. Per-script-TGI static
  doubling of a colliding root ships in four places with no known breakage
  (`0x8A8DFCF5`, `0xAA921F4F`, `0xCBF32603`, `0x2A5CFB2C`).
- **`0x6BB92BCB` (Trip-Types legend) is a construction-only container**: its
  id occurs once image-wide (`0x004C594F`, created from `{0,0x96a006b0,
  0xabb0120f}` at `0x004C595C`), and the same function calls
  `mainWindow->ChildDelete(container)` at `0x004C5B64` — it never lives in
  the window tree, so its `area=` is dead data and it can never appear in a
  dump. The live windows are its children `0x0BB0F5E7`/`0x6BB92BCA`,
  promoted to direct children of the main window (`0x004C5A04..16`,
  `0x004C5AB5..C8`). A root id in a census is a claim about where a window
  lives; a construction-only container looks exactly like a live root in
  static data. Both ids are already in `kRegionPanelIds` — a city-side entry
  on top would be 4x.
- **`0x4C30E4FA` ×6:** created by `sub_430680`, `SetArea(0,0,100,100)` @
  `0x00430721`, `HideWindow()` @ `0x00430741` — born hidden by construction.
  The show path `sub_430F70` projects a world point to screen
  (`[this+0x14] vt+0xDC`), computes `x = projX − W/2`, `y = projY − H − 8`,
  `GZWinMoveTo` @ `0x0043105A`, then a 4-state timed machine calls
  `ShowWindow()` @ `0x00431130`. Owner subsystem is My Sims (`sub_42C0E0`,
  handles `0x0B6F3E27 = kSC4MessageMySim_DebugPrintMySimsInfo`). It is a
  world-anchored callout, not a dialog; the single-find hazard applies (any
  `GetChildWindowFromIDRecursive` grabs an arbitrary pool member).
- **The Sim occupant chip (`0x27DF05BE`/`0x27DF05BF`, `I-6a9455c9`, 46x97)**
  is parented to the main window (`sub_438390` @ `0x43844C` fetches
  `GetMainWindow` through the view-input control's `windowManager` field) —
  so its frame is never doubled by the city sweep and the lever is
  dialog-static. Its 36x41 portrait is runtime-supplied through `SetImage`
  on the GZWinBMP iface (`0x4385F4`–`0x43861C`, ids `0xEA9457BA/B`) — the
  REAL-BUT-OVERWRITTEN class: the stand-in TGI `{1ABE787D,EA32F100}` is
  real and 2x-generated, yet the pixels that arrive are 1x, so its
  `imagerect` must stay `(0,0,36,41)`.
- **`0xEACA96DD` grid popup:** code-created (`sub_79C800` @ `0x79C822`
  pushes `{856DDBAC,46A006B0,144161C0}` into `0x602B70`; zero direct
  callers ⇒ virtual ⇒ a class Init). The `.UI` `I-6aca9687` is a design-time
  template the shipping code never loads — editing the script changes
  nothing; the only lever is the code-bound art, and doubling it without the
  matching geometry patch is the upside-down trade.
- **Tutorial pointer overlays `0x0A41C7B2`/`0x0A41C7B3`** (`I-0a41be3e/3f`,
  62x49): one function `sub_443E60` loads the tutorial page and both
  overlays; they highlight the Disaster Tools button and inherit its
  tooltip. Created through helper `sub_441B50` with parent = 0 (`push 0` @
  `0x441B6B`), so the loader's NULL-parent default decides where they land;
  the size is the load-bearing half.
EXACTLY the audit row whose replacement adds `## 13. `cISC4ViewObject3D` — the interface with no header`, applied UNMODIFIED (it already numbers itself 13 and its subsections 13.1-13.6, which is correct: §12 is currently the last section and this bullet is the last line of the file). ⚠ FOUR audit rows share this anchor and all four wanted to be §13. This is the only one that keeps its number; the other three are re-anchored and renumbered as edits 21, 22 and 23.

---

## Identifiers the vendored SDK does not carry (2026-09-01)

⛔ **NONE OF THESE MAY BE ADDED TO `vendor/gzcom-dll`.** That tree is a pinned
git **submodule** — `.gitmodules` points it at `nsgomez/gzcom-dll`, the parent
repository commits only a gitlink (`160000 commit 08c529bc…`), and
`git status --porcelain` inside it is empty, i.e. all 288 headers are
byte-pristine upstream. Two independent consequences, either one decisive:

1. a header edit is **never captured by a parent commit** — only the SHA is;
2. the cold-clone test re-fetches `08c529bc` from upstream and the edit
   **silently vanishes** — this project's own *presence is not execution*
   failure, in its purest form.

So every identifier below lives here, in our tree, and is marked as **ours** —
reconstructed from the executable's own registry strings. They are **not SDK
symbols**, and grepping `GZMSGIDDefs.h` or `GZCLSIDDefs.h` for them will
correctly find nothing.

### Command ids — the SDK has no command-id table at all

Only five headers mention command ids and all five are *parameter names*
(`cIGZCommandDispatcher.h:34`, `cISC4View3DWin.h:57`, and three others), never a
table. The `kMiscCommand_*` / `kToolCommand_*` block inside `GZMSGIDDefs.h` is a
message-id class doing double duty and contains neither of these.

| name (ours) | value | evidence |
|---|---|---|
| `kCommandID_TrafficQueryTool` | `0x6A935CF4` | factory branch `0x007F26B5`; ctor `0x004C4590` takes route mode as arg 1; primary vtable `0x00A90A88`, 30 slots, **no draw-shaped slot**; `Init` `0x004C57A0` gates `[this+0x8C]==1`; pick handler is vtable `+0x40` = `0x004D4D70` |
| `kCommandID_OpenSnapshotDialog` | `0x6A935E4B` | named in the game's own registry at `.data 0xB09308`; also reached by the city-dock camera button `0x8A1DA655` on two byte-verified routes |

### Message id

`kMsgTrafficMapChanged` = **`0x69247DC7`**. MEASURED from the executable's own
id→name table at `.data 0x00B08018` / `0x00B0801C`. Subscribed by the route
query tool's `Init` (`0x004C57A0`) with target `this+0x28`; it is the decisive
one of the six ids that Init registers.

⚠ **A SEARCH TRAP worth recording.** `GZMSGIDDefs.h` stores its ids as **signed
decimals** in a `uint32_t` table (e.g. `-1414770972`), so a text search of that
header for a hex id will *always* miss — a null there says nothing about whether
the id is present. Convert before concluding absence.

### Class ids

| clsid | class | note |
|---|---|---|
| `0xC9B84E10` | `cSTETerrainView3D` | IS in `GZCLSIDDefs.h:294`, written `0x0C9B84E10` with a cosmetic leading zero. Owns the `{1,2,4,8,16}` ladder at `.rdata 0xAB4330` |
| `0x89e1567c` | generic legacy `IGZWinGen` container | **ABSENT** from `GZCLSIDDefs.h`. Declared by `<LEGACY clsid=0x89e1567c iid=IGZWinGen>` at the root of the query panels, the region bubbles and the Move In My Sim marker; our dialog tooling keys on it (`UiSpike.cpp:5410`, `build_dialog_static.py:1073`). Positive control that the search was sound: the same grep DID find `0xCA5D3294` and `0xAB72FBB3` in that file |

### `cISC4ViewObject3D` — forward-declared only, shape now measured

The interface is **forward-declared and never defined** anywhere in the 288-file
SDK (`cISC43DRender.h:32`, `cISC4DispatchManager.h:30`). Measured shape:

```
5 slots  { QueryInterface, AddRef, Release, Draw @ +0x0C, Pick @ +0x10 }
```

with `bool Draw(void* device)` measured on the route-trace drawable
(`0x007DD9B0`, vtable `0x00ABB648`), registered through
`cISC43DRender::AddViewObject(obj, layer, key)` at `0x004CA54D` with
**layer = 5, key = `0x3E8`**.

⚠ **`Draw` and `Pick` are OUR names, inferred from behaviour** — the slots carry
no symbols. The *arity and order* are measured; the *names* are not. If C++ code
needs the type, add a project-local header under `src/` and say in its comment
that it is a reconstruction. Upstreaming to `nsgomez/gzcom-dll` is the only
route by which it could ever legitimately appear under `vendor/`.
