# SDK-GAPS — what the gzcom-dll SDK does not document

`vendor\gzcom-dll` is a community reconstruction of the GZCOM/`cIGZWin`
interface set. It is incomplete and, in places, wrong: whole interfaces are
missing, one virtual is missing from `cIGZWin.h`, and the slot names it does
give drift by one through the entire input and paint band. Everything the
project relies on beyond those headers was recovered from the binary —
`SimCity 4.exe` **1.1.641.0** Steam, 7,876,608 bytes, ImageBase `0x400000`,
file offset = VA − `0x400000` — and is documented here, per subsystem, as:
what the SDK omits, the known addresses and ids, and how the gap is worked
around. The full derivations live in `SC4-UI-ENGINE.md`; this file is the gap
index.

**Standing rule.** Where the headers and the binary disagree, the binary wins.
Index vtable slots by number, never by header name (§1), and check a hook's
argument count from its `ret` immediate before installing it (§1.4).

---

## 1. The `cIGZWin` vtable layout

**Gap.** `cIGZWin.h` omits one virtual — a relative-move sibling of
`GZWinMoveTo` at real slot 57 — so every header-implied index from 57 upward
is one too low. Several names in the band are also misattributed.

**Known.** Real slot 57 = `GZWinMoveRelative(dx,dy)` = `0x0099BD27`
(`mov edx,[ecx+0xB4]; add edx,[esp+8]` ×4, then `call [eax+0xDC]` = `SetArea`;
`ret 8`). Corrected anchors, all measured from function bodies:

| real slot | `[vt+…]` | virtual | base impl |
|---|---|---|---|
| 55 | `0xDC` | `SetArea(l,t,r,b)` | `0x0099C837` |
| 56 | `0xE0` | `GZWinMoveTo` (absolute) | `0x0099C8C5` |
| 57 | `0xE4` | `GZWinMoveRelative` — **absent from the header** | `0x0099BD27` |
| 59 | `0xEC` | `ScreenToWindowCoordinates` (subtracts the absolute origin) | `0x0099BD73` |
| 60 | `0xF0` | `WindowToScreenCoordinates` (adds `[+0x14]`,`[+0x18]`) | `0x0099BD5E` |
| 61 | `0xF4` | `WindowToWindowCoordinates` | `0x0099B8F5` |
| 62 | `0xF8` | `IsPointInMe` — **the header has no such method; its index 62 is `GetID`** | `0x0099C97C` |
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

Two further naming corrections:

- `0x0099BE4C` is **`GetNotificationTarget`** (a zero-arg getter,
  `mov eax,[ecx+0x4C]; ret`; paired setter `0x0099BE42`), not "base GZPaint".
  It is still the vtable-diffing baseline: every one of the exe's 115 window
  vtables carries it at slot 87, which is the fingerprint that a `.rdata`
  address is a window vtable at all.
- The header names six `GZOnMouse*` handlers; the game exposes five 3-arg
  slots (134–138). Which header name has no slot of its own is settled by
  logging `msg->type` in a `DoMessage` hook, not by counting the header
  (§13, gap G9).

**Workaround.** Index by number from the table above. The window-vtable
population scan is: whole-`.rdata` search for `[vt+87*4] == 0x0099BE4C` with
`[vt]` and `[vt+88*4]` inside `.text` → 115 hits, the complete population.
A vtable address outside `0x00A80000`–`0x00B20000` in our own logs is a
relocated DLL vtable — one of the project's shadow copies (`gVtCopy`,
`gVtCopy2`, `gGaugeVtCopy`, `gStripVtCopy`), which move between sessions;
exe vtables are constant across restarts.

### 1.1 The two rects — why draw and hit-test can disagree

The SDK gives no hint that a window carries two different rects:

| rect | offsets | writers | readers |
|---|---|---|---|
| parent-relative | `[this+0xA8..0xB4]` | `.UI area=`, `SetArea`, `SetW/H`, `GZWinMoveTo` — every scaling write | `GetL/GetT/GetW/GetH`, layout and draw |
| absolute cache | `[this+0x14..0x20]` | **only** slot 90 `CalcAbsoluteArea` (`0x0099DCE4`), which copies `GetArea()`, adds every ancestor's `GetL/GetT`, stores, and recurses into all children | the hit test (`cRZRect::Contains` on `[this+0x14]`), slots 59/60 |

**Law: move the window, then make the engine recompute.** Until slot 90 runs
on the window or an ancestor, it paints at its new place and hit-tests at its
old one. This is why `InvalidateSelfAndParents()` is the only safe repaint
primitive after a geometry change.

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
types **5** (slot 130) and **6** (slot 131). Which of the three mouse ids is
down/up/move is a reference gap (§13, G4).

### 1.4 The arity check

`__thiscall` is callee-cleanup, so a function's `ret N` states its argument
count exactly: a 3-arg mouse handler is `ret 0xC`, a 2-arg point test
`ret 8`, `GZOnCaptureChanged` `ret 0x10`. Real slot 133 is
`xor al,al; ret 4` — one argument — which is why hooking "slot 133 =
`GZOnMouseDownL`" from the header corrupted the stack and crashed the game.
Read the `ret` immediate before every vtable hook, without exception.

### 1.5 Window flags the SDK enum does not list

| flag | read by | effect |
|---|---|---|
| `0x1000` | real slot 131 path, `0x00999004` | unidentified (§13, G12) |
| `0x4000` | `Init` short-circuit `0x0099BC31` | "already initialised" latch; decides whether a re-created window re-derives its state (§13, G3) |
| `0x400000` | set at `0x0099E859` after a successful `GZPaint` into a private buffer | "this private buffer holds content" |
| `0x4000000` | set at `0x0099E8C8/93C/9D5`, cleared in `PlotPresent` `0x0099C501` | queued into the winmgr plot strategy |
| `0x8000000` `WinFlag_DelayedPlot` | the invalidation walk and `PlotComposite` | a wall in both directions (§3) |

---

## 2. `GZWinBMP` — the complete class (no `cIGZWinBMP.h` exists)

**Gap.** gzcom-dll ships no header for the `cIGZWinBMP` interface at all.
The entire interface, object layout and draw law were recovered offline;
`SC4-UI-ENGINE.md` §4A is the full reference.

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
  image** (§13, G2). `alpha=` (`0xB00`) and `imagetype=` (`0xF017`) parse but
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
bind-time latch, `SC4-UI-ENGINE.md` §2.6). The project's BMPRECT pass writes
`+0xE8` directly and therefore bypasses `SetImageRect`'s clamp — safe only
while the paired art really is 2x.

### 2.1 The 9-slice helper `0x8D8800`

Signature (cdecl, caller cleans `0x14`): `helper(ctx, img, srcCell, dst,
fillCentre)`. The source walks a 3×3 grid of `cellW×cellH` starting at
`(srcCell.l, srcCell.t)`; the dst is re-derived per band, never walked
cumulatively. The four corners go through draw-context slot 38 (`+0x98`)
unconditionally; the four edges and centre go through slot 39 (`+0x9C`, two
extra zeroed args), each guarded by a room test; the centre also requires
`fillCentre`. A window narrower/shorter than two cells does not clip — its
corners overlap. Colour keying arrives via `img->QueryInterface(0x86D72B57)`.
`imagerect` is never an inset, an edge width or a centre rect; there is no
inset concept in the engine. 2x art requires doubling all four `imagerect`
numbers: `(2r/3 − 2l, 2b/3 − 2t) = 2 × (r/3 − l, b/3 − t)` exactly.

Related single-caller tiler: `0x008D9550` wraps `0x008D8BC0` and has exactly
one caller in the image — `cSC4WinAlertBorder::Plot` (§8.2). The tiling blit
`0x8D8BC0` reduces out-of-range coordinates modulo srcW/srcH — it **tiles**,
never clamps.

### 2.2 The draw context (`[win+0x6C]`)

**Gap.** gzcom-dll has `cIGZBuffer.h` and `cIGZGraphicSystem.h` but no
draw-context header; the class is undisassembled. Known slots: `+0x28`/`+0x2C`
push/pop draw state, `+0x54` `SetColor`, `+0x8C` `FillRect`, **`+0x98`
`DrawImage(img, src, dst)`** — proven to scale (live: `img 64x64 win 128x128
-> dst 128x128`), **`+0x9C` `DrawImage(img, src, dst, 0, 0)`** — the edge
band blit; whether it stretches or tiles is a reference gap (§13, G1).
`cIGZBuffer::Blt` (`0x826AD0`) clips, never stretches.

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
  via the lazily cached global `0x00BAC058`. A fourth rect `[win+0xB8..0xC4]`
  is read here; its writer is untraced (§13, G13).
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
  `cIGZWinMgrPtr`, `GZServPtrs.h:50`); also `cIGZWin::GetWindowManager()`
  (vt `+0x18`) from any held window. `cIGZWinMgr` slot map (declaration
  order, confirmed at four binary anchors): `+0x0C` `GetMainWindow`,
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
- **Placement:** `x = (parentW − w)/2`, `y = (parentH − h)/3` (signed), then
  `GZWinMoveTo`. Confirmed to the pixel (270x162 box in a 2400x1600 frame →
  (1065,479)). Placement happens **once, at creation, from the size the
  window has then**; a later content-fit resize does not re-place — a tall
  dialog hangs low by design.
- **Teardown:** `DestroyWindow` → `IsWindowValid(prevFocus)` → `GZSetFocus` →
  `Release` → null the cached pointer. The engine maintains a global valid
  list and the game does not trust a saved `cIGZWin*` across a modal without
  asking (`DoModalWin → IsWindowValid → act` at `0x4F2668/81`,
  `0x791433/4C`, `0x78E24D/8E`).
- **Two transient lifecycles.** Main-window transients are **unparented on
  close** — they leave the child list entirely, so any cached pointer, index
  or latch is dead the moment the box closes. View-parented transients
  **persist hidden and accumulate** (six live copies of `0x4C30E4FA` measured
  under the 3D view). Never single-find a transient id; iterate every match.
- **An id promises nothing:** not unique across the tree (`0x2AAB8CC1` is the
  tooltip layer *class* — one to three live instances measured), not unique
  within a parent (the six `0x4C30E4FA`), not unique across scripts, not
  stable across a size change (`0x10000005` is 386 tall on one open and 668
  on the next), and `id=0x00000000` is normal (1,749 of 5,964 corpus elements
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
  (answers liveness, not sameness) → `GetInstanceID()` if it proves
  populated (§13, G5). Engine-provided alternatives to a side map:
  `SetParam/GetParam/EnumParams` (a per-window property bag that dies with
  the window) and `Set/GetNotificationTarget` for the owner link.
- **The modal pump still drives a Win32 timer tick** (`DoModalWin`'s pump
  keeps dispatching to the game HWND), so runtime fixes work inside a modal;
  and because modals nest, `GetModalNestCount()` is the correct re-entrancy
  gate.
- **The loader instantiates every depth-0 root** of a script regardless of
  which node the `rootWinId` selects — the id may name **any** node, not just
  a root (measured: `0x00004200` is a depth-1 child passed as the winId at
  `0x007EEAE6`).
- A fourth transient host: the app frame `0x6104489A` itself takes children
  (the missing-plugin-packs warning `0x2A5CFB2C`, added after the 3D view and
  therefore painting over it).

**Creation routes a static census cannot see** (the denominator is unbounded
above; `FINAL-3-PERCENT` §1.2):

1. The runtime COM singleton **`0xC2C2EB0F`** (getter `sub_913C72` @
   `0x00913C72`): the class is chosen from a runtime-registered dispatch
   table, no literal clsid in the instruction stream. 220 call edges in 129
   functions; 27 inside the live-UI band `0x760000`–`0x7FFFFF`. Static
   analysis has nothing to read; only emulation or a live hook lifts it.
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
   are `SetID(base+i)` in a loop. The value does not exist in the image.

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
`vt=00AE20A0`, inner `vt=00ADDAF0`.

---

## 5. The `.UI` script format

**Gap.** The SDK gives no grammar. The loader was disassembled instead;
`SC4-UI-ENGINE.md` §3.0a/§3.7–§3.12 carry the full reference.

**Known.**

- **The lexical contract.** `.UI` is not line-oriented: 107 of 5,964 elements
  span multiple physical lines (quoted values contain raw newlines); 84
  quoted values in 19 files contain a literal `>` (so any `<LEGACY[^>]*>`
  regex is wrong — the project's survive only because `id=`/`area=` always
  precede `caption=`); one file (`I-ca551016`, the Credits) carries a UTF-8
  BOM; backslash escapes exist for `'` but not for `"` (zero `\"` in the
  corpus). The one invariant: every element begins `clsid`, then `iid` (if
  present), then `id=` (if present), then `area=`, and `caption=` never
  precedes any of them.
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
  regex the project owns keys on `area=` and would silently scale nothing on
  a script using `pos`/`size`.
- **The tag grammar has 14 entries** (`0x0094B740`–`0x0094BA20`, registered
  through `[vt+0x24]`): `LEGACY` `0xFA450242`, `children`/`_children` 1,
  `/children` 2, **`define` 3, `name` 4, `val` 5 — a real, unexercised
  sub-language no shipped script uses**, `none`/`_null` 0, and legacy font
  faces `comic9`/`comic10`. `0x0094B995` is the `LEGACY` registration, not a
  handler.
- **There are 13 `winflag_*` names, not 14** — 11 universal (5,964/5,964)
  plus `winflag_acceptfocus` (5,852) and `winflag_alphablend` (5,845). The
  exe registers exactly 13.
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
  scripts (My Sims `I-aa1f1f57` has nine roots; the ninth is `0xABB26B0E`).
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
names; the two partition the corpus with zero overlap (selective-safe 88
scripts, dialog-static 163; together 251 of 281).

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
- **The pt→px rule is only partially known.** Measured line heights: 15 px @
  13 pt and 28 px @ 24–26 pt — two points do not determine the rule, so
  vertical text checks at the 1.5x and 3x tiers are decided by capture
  (procedure: `tools\uimap\emu\measure_lineh_tier.py` against the Graphs
  "Population by Age" chart, whose nine labels `1-10`…`81-90` cannot wrap at
  any tier). Ink does not scale linearly with point size: measured ×2.13 per
  doubling (n=17), so `round(stockBox·f)` is ~6% too narrow and wraps more
  than stock — size boxes from the font, not from `f`.
- **The wrap contract:** SC4's wrap call `sub_896957` (font `vt+0xB8`)
  reads `r->left`/`r->right` and never writes them; the only output is
  `bottom = top + nLines*lineHeight`. The box is an input, not an output.
- **`font=NAME` resolution paradox.** The tokenizer dictionary contains zero
  FontStyle style names, so no style name can resolve through the token
  path — yet `DataInsetHeader` renders correctly while `RegionLabel` does
  not, both on plain `GZWinText`. The `<LEGACY>` tag handler was ruled out
  (it is a registration site). Unresolved (§13, G10); the operational rule —
  always ship `font=0x…` GUIDs — is unaffected.

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
- **Pixel-valued attributes the builders do not scale** (the residual gap in
  the statically scaled set): `scrollbargutters` (3 in dialog-static, 4 in
  selective-safe), `buttongutter` (3), `combodownarrowrect` (3),
  `icongutter` (1), `minmaxboxsize` (1). The one with visible consequence is
  `combodownarrowrect=(0,0,64,15)` — a 1x drop-arrow rect inside a doubled
  combo (`I-0a243d80`, `I-e9263de5`, `I-e9a56248`).
- **Client padding never scales at runtime.** The DLL contains no
  `SetGutters`/`SetTextOffsets`/`SetTipPlacementOffsets` call site, so every
  runtime-swept window keeps 1x padding; only the statically doubled scripts
  carry scaled padding.
- **Gutter byte-range ceiling.** The SDK declares the gutter setters as
  8-bit (`cIGZWinGen::SetGutters(uint8_t,uint8_t)`, `cIGZWinText::
  SetGutters(int8_t,int8_t)`, `cIGZWinCombo::SetBtnGutter(int8_t)`), while
  the stock corpus reaches `gutters=(247,201)` (`I-8a7e052f`, Graphic
  Options, `0x2A57CB84`) and `(232,232)` (`I-aa5e60d1`, `0xCA5E6261`) — both
  in the scaled set, where 2x writes (494,402)/(464,464). Whether the setter
  truncates is a reference gap (§13, G6); the verification is to dump
  `GetGutters` on `0x2A57CB84` in a deployed 2x build.

---

## 8. The class registries and SC4-specific window classes

**Gap.** The exe carries two name tables that together name every window
class in the game without a guess; the SDK ships neither.

**Known.**

- **(a) The `.UI` class registry — `0x00B16FA8`…`0x00B170A3`, 21 entries of
  12 bytes `{clsid, iid, char* name}`.** The authority for the `GZWin*`
  family; exactly 21 scriptable widget classes exist. The "descriptor"
  addresses older notes quote for `GZWinBMP`/`GZWinBtn` (`0xAD5CE0`/
  `0xAD5CAC`) are simply the class-name strings these rows point at; there is
  no per-class descriptor record.
- **(b) The GZCOM clsid→name table, `~0x00B05000`…`0x00B0B000`, 8-byte
  `{id, char*}` pairs, 906 resolvable entries** — the authority for the
  `cSC4Win*` classes, simulators and command ids.
- **(c) The SC4 window-class registration function `sub_004662B0`** — 17
  `{factory, clsid}` pairs via `AddClass 0x0090E133`. Each factory is
  `new(size) → ctor → return obj+N`, where **N is the byte offset of the
  cIGZWin sub-object** — the fact that tells you which of a class's several
  vtables the window tree will show.

### 8.1 Corrections to the catalogue rows

- **`0xAA7CECFD` is `cSC4WinText`** (named in `GZCLSIDDefs.h:285`, absent
  from the exe table). Its factory `0x007BE740` allocates `0x114` bytes,
  runs `cGZWinText`'s own constructor `0x009C19C8`, then swaps the vtable to
  `0x00ABA190` — which differs from `GZWinText`'s in exactly two slots: 88
  (Plot → `0x007BE7A0`) and 148 (dtor). Same object layout, same font code;
  only the painter differs. It is reached by GZCOM clsid instead of by the
  `.UI` class name, which is why it sits outside the `GZWinText` name path
  and scales off FontStyle with no help.
- **`cSC4WinGenTransparent` (`0x89E1567C`, vt `0x00AB7358`)** differs from
  `GZWinGen` in exactly two slots of 151: 121 (the hit-claim `0x0079C5C0`)
  and 148. It is an ordinary container, provably.
- **`0x00ADCB38`** is a `cGZWin` subclass whose only override is slot 89
  `CalcAbsoluteArea` (`0x0099C291` vs base `0x0099BA07`) — a
  coordinate-remapping/clip viewport that paints nothing; scaling it moves
  every descendant's absolute rect.
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

clsid `0xAA5D16A9`, iid `0x4A5D1208`, vtable `0x00AB64B8`, Plot
**`0x00797CC0`**, ctor `0x00797E60`, factory `0x00797F20` (0xF8 bytes,
returns `obj+0xE0`); sub-vtables `0x00AB64A0` at `+0xD8` and `0x00AB6488` at
`+0xE0` (slot 3 `SetImage` → `+0xF0`, slot 4 `SetFraction` → double at
`+0xE8`, clamped by `[0xA80990]=0.0`/`[0xA80AB0]=1.0` at `0x797C20`). The
class is registered and shipped; its only corpus appearance is the region
city-select bubble `I-ca539340` (window `0x4A553000`, 102x11 at (11,92)).

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
immediate in `.text`. The bitmap is a 102x26 **26-row state stack** (pitch 4:
3 px colour + 1 px `FF00FF` key; row 0 = zero cells filled … row 25 = all
filled), referenced by zero `.UI` scripts and therefore invisible to the
ref-driven art builders. Fix shipped: the art at 204x26 (width ×2, height
unchanged — `imgH` sets the state divisor), 153x26 at 1.5x, 306x26 at 3x.
The CITY HUD's rating bar is a different implementation entirely (four
`GZWinBMP`s, groove `0x8A517556` art `14015549`, controller
`0x7E86C0`–`0x7E8A80`); the two share no code and no art.

### 8.4 The identification procedure

Given only a `vt=XXXXXXXX` in a log line: (1) range-check — game classes live
in `0x00A80000`–`0x00B20000` and are fixed for the build; anything else is a
relocated module (in our logs, our own shadow copies — restart the game and
re-read; exe vtables print identically, DLL vtables move). (2) Confirm it is
a window vtable: `[vt+87*4] == 0x0099BE4C`; if not, it is a secondary COM
interface and the real window vtable is at another object offset. (3) Read
slot 0 `QueryInterface` and collect its `cmp` immediates — the iids — and
look them up in the two registries. (4) If `QueryInterface == 0x0099B774`
the class overrides nothing (12 of the 115 classes, including all three
region layers); only its Plot can identify it. (5) Diff the vtable against
its base over slots 0…150 — the differing slots ARE the class. (6) Find the
ctor by searching `.text` for the vtable VA (two hits: ctor and deleting
dtor); the ctor's `mov [reg+N], <vt>` must equal the factory's `add eax, N`.
(7) Cross-check the name against `GZCLSIDDefs.h`, which carries names the
exe table does not (`kcSC4WinText`, `kcSC4WinAlertBorder`, `kcSC4WinAuraBar`).
The standing warning governs: the right class is not the right window.

---

## 9. Art binding beyond the ref map

**Gap.** Four distinct paths feed pixels to the screen; only path 1 (`.UI`
`image=` refs) is visible to script-derived tooling. Full reference:
`SC4-UI-ENGINE.md` §4/§4A; `UI-ART-BINDING.md`.

**Known.**

- **The store type is generic.** `0x856DDBAC` is an image type, not PNG: of
  2,280 entries, 2,206 are PNG, 41 are JFIF (all of group `0xCA133ECB`), 26
  are SHPI/FSH (inside `0x46A006B0`), 7 are Windows BMP (inside
  `0x6A1EED2C`). None of the 74 non-PNG entries is `.UI`-referenced.
- **The twin structure is exact, and there are three twins.** `0x1ABE787D` is
  a strict subset of `0x46A006B0` (743/743 of its instances; the larger group
  has 810). Group `0x00000001` is a third twin: all 62/62 of its members
  exist under both. Covering a shared instance can mean covering three TGIs.
- **Path 1b — the dangling placeholder.** A well-formed `image={g,i}` whose
  TGI is in no shipped archive; the pixels arrive at runtime from a binder.
  Every offline instrument reports it as ordinary path 1. Shipped instances:
  `0a243d80` Select-A-Sim (22 cells `0x12340000..15`, placeholder
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
  `0x46A006B0` referenced by 29 other scripts. Either the engine falls back
  to instance-level lookup or Maxis shipped a dead ref — unresolved (§13,
  G11), and it is the premise clone-retargeting rests on. The classifier
  must test instance-level presence before declaring DANGLING.
- **ItemIcon group `0x6A386D26` is two families.** 320 × 176x44 (the
  exemplar-referenced 4-cell strips; 266 carry an exemplar reference) and
  **36 × 356x58** with sequential structured instances `0xMM0000NN` — bound
  to the one-widget 89x58 template script `I-ebd0d36d` (no `image=` at all),
  referenced by no exemplar and no `.UI`, staged by nothing. Their absence
  from live dumps is a structural null — no deployed instrument walks the
  top-level toolbar (§13, G14).
- **Path 4 (runtime-generated pixels) has two sub-shapes:** 4a — no `image=`
  at all (invisible to every ref scan); 4b — dangling `image=` (counted,
  warned, and its `imagerect` is editable — right for the U-Drive-It pickers,
  wrong for Select-A-Sim). **The power-of-two buffer law:** runtime pixels
  are composed into a power-of-two `cIGZBuffer` (class vt `0x00AC1400`) and
  occupy only a top-left sub-rect (measured: 36x41 into 64x64 at ~6 Hz per
  portrait cell; 152x38 and 91x77 into 256x256). Doubling a path-4
  `imagerect` samples past the live data into the POT padding.
- **The BMPX draw log has a global, session-lifetime cap of 12 lines**
  (`src\UiSpike.cpp:4922`), shared by every hooked window; one busy window
  exhausts it. A missing `BMPX draw` line means, in order: the budget was
  already spent; the window is under no hooked root; only then, the class is
  not `GZWinBMP`.

**Workaround.** The decision procedure for a wrong-art widget (`SC4-UI-ENGINE.md`
§4.7): confirm the live script is the one loaded → anchor the grep on `image=`
→ does the TGI exist (and under which group) → is it staged under all its
twin TGIs → is `imagerect` consistent with the art it got → for path 1b find
the binder, not the art → separate paths 2/2b/4 by where the constant lives →
only then reach for a hook, with the class positively confirmed.

---

## 10. The region screen

**Gap.** The region screen is not a mode of the city screen but the
alternative occupant of the same slot, and none of its architecture is in
the SDK. Full reference: `REGION-SWITCH.md` §0, `REGION-SCREEN.md`.

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
- The four full-screen layers: `0x6A0AF41D` (vt `0x00AB88C0`, code-created,
  id stamped at `0x007A99DF` — the cloud emitter, §10.1), and two anonymous
  ones (vt `0x00AB8CD0` — an animating list, `0x00AB8F50`).

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

## 11. The layout model's own coverage (`tools\uimap`)

The offline model (builder census + constant map + layout emulator + diff
harness) has measured limits; they are stated here so a null from the model
is never read as a fact about the game.

- **Population:** `.text` spans `0x407000..0xA7FA2D`. A 6-byte scan for the
  cIGZWin geometry slots (`FF /2 disp32`, disp ∈ {`0xD4 SetSize`, `0xD8
  SetArea(Rect*)`, `0xDC SetArea(l,t,r,b)`, `0xE0 SetPosition`}) across all
  eight ModRM base forms finds **1026 geometry call sites in 552 functions**.
- **The `--discover` scan's pattern list is incomplete:** it carries no
  `0xD8` pattern and omits ModRM `0x95` (ebp base) and `0x94` (SIB) — 182 of
  1026 sites (17.7%) unscanned; 147 confirmed `0xD8` sites; 69 functions
  have `0xD8` as their only geometry call (among them the Data Views re-lay
  `sub_007A04F0`, sites `0x7A082C`/`0x7A0955`). Including the missing
  patterns takes the candidate list from 96 to 116. The scan technique
  itself is sound (0 false positives on linear disassembly).
- **`0xD8` sites cannot yield constants through the current recorder:** the
  census names slot `0xD8` "SetAreaRect" but the constants pass keys roles on
  "SetSize"/"SetArea"/"SetPosition" only, so every `0xD8` record is dropped.
  The naive fix would fabricate constants — `0xD8` takes a pointer (the
  pushed `lea [esp+disp]`), not four coordinates. The correct treatment is
  "builder found, constants not recoverable" until a rect-store resolver
  exists (follow the `lea` to the four member stores; for `sub_007A04F0`
  even that fails — its rect members are computed at runtime, consistent
  with the shipped fix scaling the origin inside the re-lay).
- **The `callers ≥ 2` discovery filter is a lid, not a filter:** 8 of the 12
  builders the census already holds fail it (including every named dialog
  builder — a top-level dialog builder is called from exactly one place);
  over the 552 geometry-driving functions it removes 420 (76%), of which 147
  make ≥2 geometry calls. A discovery filter must re-find the things already
  found; caller-count finds shared helpers, geometry-call-count finds
  builders.
- **The discovery pass skips the double-proof:** a 3-byte substring test with
  no high-byte anchor means `call [eax+0x1D4]` matches `[eax+0xD4]` — 5 of
  101 listed candidates carry no geometry call at all (`0x4827D0`,
  `0x482DC0`, `0x4832E0`, `0x915EC0`, `0x685AE0`).
- **Coverage:** 10 of 552 geometry-driving functions (1.8%), 43 of 1026
  sites (4.2%), all budget-family; the emulator implements 1 of 13
  primitives (`LABEL_FACTORY 0x00779660`); the predicted-vs-live join is 0
  of 47 live ids (the 50 predicted windows are budget-family; the available
  logs are region-screen dumps). Structural nulls, quoted as such:
  `builders.json` holds zero `SetArea`/`SetAreaRect` rows because the 10
  census owners contain only `0xD4`/`0xE0` calls; and edge-vs-direct
  divergence at integer factors is identically zero (`edge_law(pos,len,f) =
  R(pos+len,f) − R(pos,f)`; for integer f the edge law equals the direct
  law). Only 1.5x can diverge: 807 pairs.
- **The art-rect oracle** that retires the UNKNOWN-STOCK class is a generated
  `art-rects.json` (art TGI → stock/shipped IHDR + create-type cell
  divisor): for these windows the exe supplies only x and y — w and h are
  the art's PNG IHDR, which no layout emulator can produce. Cell rule from
  the create type: type 2 (`sub_77B960`) window = the whole strip; type 4
  (`sub_77B7B0`) window = one cell.

### 11.1 The row windows (the budget/ordinances dialog contents)

The 45 "unjudgeable" windows of the diff harness are identified; 32 have
exact stock rects. Under dialog `0x0423278F` (stock 450x377): 12 checkbox
cells (ids `0x12C+k`, 16x16, art cell of `{46A006B0,144161EA}` 128x16/8
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
SHARED (clone+retarget to `0x470261EA`) and bound by six hardcoded pushes no
retarget touches — a code-sized 360x60 button drawn from a 1x plate until
retargeted.

---

## 12. Coverage of the shipping UI

**Named shipping windows: 315; carrying a scaling mechanism: 299 (94.9%).**
Kept as separate denominators: D1 script-declared roots 288/298 (96.6%); D2
code-created named windows 11/17 (64.7%). There is **no offline upper
bound** — the three channels of §4 (the `0xC2C2EB0F` singleton, the
register-id factory, anonymous creates) are unbounded by construction.

The D2 ledger: covered — `0x9A47B417`, `0x6104489A` (sweep roots),
`0x6A5E44B6` (art + ≥90% skip), `0x2AAB8CC1` (wrap patch + art),
`0x8A6E61E0`/`0x8A2CAD8B` (born-scale), `0x2BA6BB97` (dialog-static on both
bubble scripts), `0x0423278D/E/F` (byte patches + per-instance runtime pass
+ popup pin). Uncovered — `0xEA659793` (whitelist-only region pass),
`0x6A0AF41D` (cosmetic, correctly left alone, §10.1), `0x00000043` (the
Restore-Toolbars button, below). Role-unknown — `0x85202C0E`, `0xA802B4EB`,
`0x9AEDEF7C` (never in any retained log).

- **`0x00000043` Restore-Toolbars:** built by `sub_7EDEB0` from `I-c973b411`
  (`mov [esp+0x6c],0xc973b411` @ `0x007EDECC`): CreateInstance GZWinBtn @
  `0x007EDFF6`, image `{856DDBAC,46A006B0,53244588}` @ `0x007EE02F` (84x19
  4-frame strip, cell 21x19), `SetID(0x43)` @ `0x007EE140`,
  `GZWinMoveTo(0xC, viewH−0x1C)` @ `0x007EE146`, born hidden @ `0x007EE175`.
  The builder never sets a size. With 2x art shipped (cell 42x38) the
  code-fixed position clips 10 px at birth, and the sweep then re-doubles it
  to 84x76 at (24,1544) → 20 px clipped. `0x43` and the script-declared
  `0x44` are the two halves of one feature (one in code, one in data), in a
  dense semantically-allocated command-id run; SC4 reuses tiny ids in-image
  (`0x000000FF` at three unrelated sites), so any cure keys the pair
  (builder, script-instance TGI) plus a parent check, never the bare id.
- **Id collisions are the mode, not the accident:** 596 of 1409 distinct
  corpus ids (42%) are declared by ≥2 script instances, and 37% of the
  project's own id-keyed entries are multi-declared. Per-script-TGI static
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
  REAL-BUT-OVERWRITTEN class: the placeholder TGI `{1ABE787D,EA32F100}` is
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
  `0x441B6B`) — the loader's NULL-parent default is unmeasured (§13, G15);
  the size is the load-bearing half either way.
- **The 36 live ids once unexplained in logs** resolve to one family: all
  are descendants of the Ordinances dialog (12 `0x12C+k`, 12 `0x2F4+k`, 4
  `0x551+k`, Accept/Cancel, `0x0ABCE000/1`, the popup's four outer/inner
  ids) — a child-window population, not 36 roots.

---

## 13. Reference gaps

Unresolved items, each with what is known and the observation that settles
it. Nothing here blocks a shipped mechanism; every entry states its limit.

| # | gap | known | settles it |
|---|---|---|---|
| G1 | draw-context slot 39 (`+0x9C`): stretch or tile | both blit slots located; argument counts read at the call sites (`0x8D8928` 3-arg, `0x8D896A` 5-arg); only the implementation is unread; `blttype=tiled` is the second-most common corpus value (254/540) | hook ctx slot 39 the way BMPX hooks 38; log src/dst for one `edgeimage=yes` window |
| G2 | GZWinBMP flag `0x20` | consumer at `0x9BC37E`/`0x9BC3D9` (source from `+0xE8` plus dst offset by `(src.l, src.t)`); a whole-`.text` `push imm8`-near-`SetFlag` scan finds the three known setters and zero `push 0x20` (a register-computed mask would evade it) | treat as unreachable from data; if a setter is ever found, re-examine the "pixel-registered collage" pattern |
| G3 | `cIGZWin` flag `0x4000` semantics on recreate | `Init` short-circuits on it (`0x0099BC31`); absent from `tWinFlag` | decide whether a re-created GZWinBMP re-derives its imagerect from its (already-scaled) window size — load-bearing for born-correct |
| G4 | GZWinBMP mouse message ids → down/up/move | the three ids and their slots (§1.3); neighbouring stubs bracket the group (135/137 = shared 3-arg stub, 139 = 4-arg) | one live log of the id order on a click |
| G5 | `cIGZWin::GetInstanceID()` (vt `+0x100`) populated for ordinary windows? | the `.UI iid=` hypothesis is disproved (`iid` is token −2 holding an interface name; the only `SetInstanceID`-shaped deserializer call `0x954C2E` is fed by token `0x1336 = rowheight` on a QI'd file-list interface) | add `iid=%08X` to the MWKID/VWKID/DGPKID format strings; if non-zero and distinct, the non-unique-id problem and the rect-matching tie-breaker both retire |
| G6 | gutter setter byte truncation | SDK declares 8-bit setters; corpus reaches (247,201); 2x writes (494,402) | dump `GetGutters` on `0x2A57CB84` in a deployed 2x build: (494,402) = no ceiling; (238,146) = clamp needed |
| G7 | `imagetype=` (token `0xF017`), `pos=`/`size=` (`0x0102/3`), `blttype=divider|bluebar` semantics | registered, zero corpus uses; `size` is parse-only (the serializer never writes it) | one-script generator experiments |
| G8 | which of the header's six `GZOnMouse*` names has no slot | five 3-arg slots (134–138) reached from ids 7/8/10/11/13 | log `msg->type` in a `DoMessage` hook on a button while clicking — never by counting the header |
| G9 | `cRZWinMgr::ProcessMouseMessage` / capture ordering | capture changes arrive as message 14 → slot 139; enter/exit as 18/19; the manager's mouse path was not located (slot `0xA0` is shared with unrelated interfaces) | disassemble the manager; until then "capture bypasses the router" stays hypothesis |
| G10 | `font=NAME` resolution paradox | the dictionary holds zero style names, yet `DataInsetHeader` (×5) resolves and `RegionLabel` (×1) does not, both on plain GZWinText; the tag-handler suspect is ruled out (registration site, not handler) | the GUID rule ships regardless; the mechanism remains open |
| G11 | does the engine honour a `.UI` ref's GROUP? | `{82b9b75b,e2b66db8}` names a nonexistent group while the instance lives under `0x46A006B0` (§9) | open Signs & Labels at stock; compare the two buttons against a sibling binding `{46a006b0,e2b66db8}` — identical art ⇒ group not honoured ⇒ every clone-retarget needs re-examining |
| G12 | window flags `0x1000` and `0x4000000` identities | read sites (`0x00999004`; `0x0099C4BF/99`) | identify before any future flag-based lever |
| G13 | the fourth rect `[win+0xB8..0xC4]` | zeroed in the ctor (`0x0099DB28`), read by `PlotPresent` for the non-deferred present; writer untraced | trace the writer; if it is a cached present rect it is another staleness candidate after resize |
| G14 | the 36 356x58 ItemIcon strips (`0x6A386D26`, `0xMM0000NN`) | bound to template `I-ebd0d36d` (89x58, no `image=`); group constant at `0x78EE15`/`0x7ECB50`/`0x7F038F`; 89 px = the sidebar strip width | build a toolbar walk first — no deployed instrument enumerates the top-level toolbar, so their absence from dumps is a structural null |
| G15 | the `.UI` loader's NULL-parent default | `sub_441B50` passes parent = 0 for the tutorial overlays | a boot-time tree dump locating the overlays' parent |
| G16 | slot-90 recompute scheduling | slot 91 sets `[this+0x70]`; slot 89 tests `[this+0x71]`; slot 90 has 36 call sites and is recursive | which dirty byte gates the recompute, and same-frame vs next — decides whether a moved window is clickable at its new position immediately |
| G17 | where the UI composites relative to the 3D view | all 4 call sites of slot 123 and 44 of slot 89 enumerated; the driver must be `cIGZWinMgr::Plot` (winmgr slot 6), whose vtable is runtime-only (singleton `0x00B628C0`) | read `*(void**)0x00B628C0` live; no ordering claim before that |
| G18 | the Photo Album code-bound image | `{856DDBAC,1ABE787D,2558A4CB}` 296x222 at site `0x7BC624`, panel `I-4a8cc5ea` root `0x0A8CD3EE` 683x582; neither twin staged, in no `CODE_BOUND_TGIS` | one `refmap`/`SCALED_WINDOW_IDS` lookup: if the album is scaled this is a 1x backing |
| G19 | region map tile labels/icons (distinct from the bubble) | the container claim ("nothing under `0x2BA6BB97`") is refuted — 13 descendants print the moment a tile is clicked; the label sub-claim was never tested | `DumpTree` full depth on the region screen with no bubble open |
| G20 | `0x85202C0E` / `0xA802B4EB` / `0x9AEDEF7C` roles | vtables `0xAB9980`/`0xAB6010`/—; never in any retained log | one sighting run |
| G21 | the Win32 message coalescer `0x0098CE30` | drops redundant `WM_MOUSEMOVE` runs; appears to zero matched down/up pairs before the UI sees them; read in passing | finish the decode only if a lost-click/lost-drag symptom appears — it is upstream of all routing and would look exactly like a routing bug |
| G22 | the `[0xB43CE0]` modal-veil sub-service | cached at `0x602336` from `[0xB43C94]->vt[0xAC]()`; `+0x28(win,bool)`/`+0x18(win)` bracket every `DoModalWin` | disassemble the master at `[0xB43C94]` or find the vtable's QI iid |
| G23 | does a declared `imagerect` reach the draw for `edgeimage=yes`? | the code says yes (pass 2 sets flag `0x10` whenever `imagerect=` is present; `GZPaint` selects `+0xE8` on it), and the BMPRECT fix only acts when the flag is live — but an offline recomposition of the real art under the decoded algorithm produces a flat interior where the game shows decorated chrome | extend the BMPRECT walker to log `[win+0xF8] & 0x18`, `[win+0xE8..0xF4]` and live W/H for one edge BMP; third answer: the decorated frame the player sees is a different window in the stack |
| G24 | `sub_441B50`-class NULL parents, `0x6BFAC122`/`0x8BFAC13E`/`0xCBFACAE1` chips | measured null on two independent instruments (static reference and live tree); compressed-dat escape hatch open | one sighting run across the three building query types |
| G25 | budget gray header band | engine + art say it must paint pink through the same plain-blit path as the slabs; the v2.25.33/34 hooks (since removed) are the prime suspect for the contrary observations | judge live; if still gray, the next step is a draw trace — never geometry |
| G26 | Taxes dialog under the family patches | shares builders/helpers with the patched departments (`BUDGET-DETAIL-ANATOMY.md` §1) | eyes-on; patch residual sites the same way if flagged |
| G27 | GZWinBtn standard-style state strips: does the vertical dimension stretch? | horizontal fit/stretch is measured (120x30 strip on 130–370px buttons; 84x19 strip on 18x16 buttons); 875 buttons are exact 4-state, a smaller population 8-state | 2x one shared strip, open an unscaled dialog (e.g. the budget window), see if buttons render correctly; until then treat shared button strips as unsafe for in-place 2x |
| G28 | the flyout `0x09DE8798` (script `0x09DE3002`) | untracked — in no list in `UiSpike.cpp`; reached from the funnel twin's second call site (`0x7E718A`, dispatcher `sub_7E7130` on `[esi+8]==1`); the script exists in no extracted corpus (structural null) | log `GetChildWindowFromIDRecursive(0x09DE8798)` per mode to identify what UI it is before hooking the twin |
| G29 | the `mission_selection_red` spawn site | recorded both as `0x528BC7` (`REGRESSION.md` `[R:11613]`) and `0x528BC9` (`src\CodePatches.cpp:4065`) — 2 bytes apart, unadjudicated | re-read the bytes before patching at either |
| G30 | what draws through marker-strip builder `0x5F5FB0` / zoom table `0xAA523C` | the builder and table are byte-proven (table `{0.5,0.75,1.0,1.5,2.0}` at `.rdata 0xAA523C`, sole consumer `0x5F6067`); the offer-balloon attribution was refuted on screen (the balloon is the CSI); the route-dot fn's reference at `0x5F74AD` is a texture-loop end-bound compare, not a size read; the signpost quad builder is the dormant twin | one `SPTEX`/`SPSTRIP` capture in a scene with dispatched units; both builders ended the #188 hunt with no confirmed on-screen consumer |
| G31 | the signpost kinds table (`[this+0x70]`) | kind 4 = mission balloon per the static trace; the full table lived in volatile session notes and is gone | one `SPTEX` capture in a scene with dispatched units names every live kind; do not guess kind numbers |
| G32 | the pick whitelist's five automata families (`0x4B8880`) | the Accept fn accepts 5 automata families (byte-verified count) plus the signpost occupant at `0x4B8947`; the family ids lived in volatile session notes | read `0x4B8880`'s compare chain; turns "can the player click it?" into a table lookup for every in-world visual |
| G33 | Graphs chart: are the `32f` band rect (`chart+0x108`/`+0x10C`) and the legend column the same object? | the legend row geometry is a six-constant right-margin budget owned by panel builder `sub_76D3D0` (`ApplyGraphLegendBudgetScale`); the chart renders `ChartLabel` (`0xE9C86B5E`), not `Legend`; the band write still ships (`SCALING-AXES.md` M6) | dump `chart+0x108` and the legend child rects in one `CHARTGEO` line at the same instant, or disassemble what reads `chart+0x108` inside draw path `sub_9B5ADE` |
| G34 | gauge dials (`0xCBCBF1E0`): the cached-buffer scaling lever | the class keeps a class-private cached buffer at 1x while the window doubles; the My Sims portrait cure (law 41: one leaf invalidate per open) closed the analogous #47 half; the `[win+0x6c]`-buffer claim behind force-recreate is contested (REGRESSION REFUTED 4/5) | a per-open census of draw calls scoped to root `0x4BCB938A` BEFORE the buffer route; never hook on class identity alone |
| G35 | Graphs legend: what turns the game's 16x16 checkbox into the measured 32x32 | the builder's own `SetArea` writes 16x16 at every tier (`0x0076E151/59`, `0x0076E168`), yet the live window is 32 wide at 2x; every named hypothesis was refuted by disassembly; two survive — nothing resizes it, or something writes `round(16*f)` (numerically identical to the art cell `stripW/8`) | the v2.55.0 fix is correct under both hypotheses; identifying the resizer is open |

**Structurally unknowable offline** (the limit is named, so the entry moves
when the limit lifts): the `0xC2C2EB0F` factory's output (runtime dispatch
table — lift by emulation or live hook); computed window ids (the value does
not exist in the image — lift by running the loop); anonymous creation
sites (identity does not exist — reachable only through subtree recursion);
runtime instance counts (offline analysis counts sites, never instances);
parenting of an instance (the `ChildAdd` argument is a register — needs a
live dump); depth-1+ nodes the code addresses as top-level handles (the
denominator ladder counts depth-0 roots by construction); third-party plugin
DLLs (outside every denominator); the city loading/saving screen (no `.UI`
exists anywhere; 100% code-painted — settled); and rich-text sizing (outside
the `cIGZWin` model; FontStyle can never reach it).
