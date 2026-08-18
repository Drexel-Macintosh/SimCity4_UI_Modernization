# TARGET: PRIMARY: tools\research\SC4-UI-ENGINE.md — insert the block below as a new "### 2.4 The paint pipeline: invalidate -> composite -> present" immediately after "### 2.3 The buffer class 0x00AC1400 (cIGZBuffer)" and before "## 3. The `.UI` script format". Three surgical corrections also belong in that file: (a) the slot table under §2.1 "The zero-argument draw group, slots 87..97" (currently at SC4-UI-ENGINE.md lines 323-327), (b) §2.2 item 2 ("the `[this+0x64]` mask sub-object's 2-arg HitTest"), (c) §8.1 registry row "`0x0099BE4C` | base `GZPaint` (slot 87)". SECONDARY: _tests\REGRESSION.md — the LAW block at the end extends numbered law 8 ("PBUFFS ARE BORN AT FIRST-PAINT SIZE", REGRESSION.md line 1705) and adds two new laws.

## SUMMARY
Fully reverse-engineered the SC4 paint/invalidate/buffer pipeline from the shipped exe. Five headline results, all measured. (1) The vendor header cIGZWin.h is MISSING one virtual — a relative-move sibling of GZWinMoveTo at real slot 57 (0x0099BD27, ret 8) — so every project slot NAME from 57 up is one too low: what the docs call "Plot (slot 88)" is really GZPaint, real Plot is slot 89 = PlotComposite() && PlotPresent(). Confirmed four independent ways, including real 100 = PrivateBuffer(bool) with `ret 4` and real 123/124 landing exactly on PlotComposite/PlotPresent. (2) Dirty state is a single BOOLEAN BYTE [win+0x70], never a rect; InvalidateSelfAndParents (0x0099BED1) sets it on self then walks GetParentWin marking every ancestor, and STOPS at the first ancestor carrying WinFlag_DelayedPlot 0x8000000 (0x0099B7BD). (3) PlotComposite (real slot 123, 0x0099E62D) skips the whole subtree if the window is invisible, and if the window itself is NOT dirty it descends only through a harvest callback (0x0099B9AC) that paints nothing — so a child cannot repaint unless its parent is dirty too. That is the mechanism behind the long-standing "InvalidateSelfAndParents is the ONLY safe repaint primitive" rule. (4) The dirty byte is cleared ONLY for windows that own a private buffer AND have a parent — every other window re-paints every single frame. (5) The engine DOES resize a window's private buffer inside SetArea, but only when WinFlag_PrivateBuffer is already set and W/H actually changed, and PrivateBuffer(true) (0x0099EA70) silently degrades to DESTROY when any ancestor is hidden. The widgets that show the project's "born at first-paint size" defect keep their cache in a class-private field ([0xDC] flyout, [0xF0] minimap), which SetArea cannot see at all — so no resize path exists for them by construction. Also corrected: [win+0x64] is the private cIGZBuffer (not a "mask sub-object") and the refined hit test slot 149 Locks and reads it per pixel, which ties stale buffers directly to mis-landing clicks; and the project's empirically-found mouse slots 136/138 are GZOnMouseUpL and GZOnMouseMove. One sub-question is left explicitly open with its positive control: where in the frame the UI composites relative to the 3D view.

## CONTRADICTIONS
- SC4-UI-ENGINE.md §2.1 slot table (lines 323-327) and UiSpike.cpp:104-106 name the draw group one slot low. The vendor header cIGZWin.h omits one virtual — GZWinMoveRelative(dx,dy) at real slot 57, 0x0099BD27, `mov edx,[ecx+0xB4]; add edx,[esp+8]` x4 then `call [eax+0xDC]` (SetArea), `ret 8` — so every header-implied index from 57 up is +1. Real 88 = GZPaint (the per-class draw we call 'Plot'), real 89 = Plot = PlotComposite() && PlotPresent(), real 91 = InvalidateSelf, real 92 = InvalidateSelfAndParents, real 123/124 = PlotComposite/PlotPresent. Four independent confirmations, the decisive one being that real 99 is zero-arg (`lea eax,[ecx+0x24]; ret` = GetAreaToDrawTo, header 98) while real 100 ends `ret 4` (PrivateBuffer(bool), header 99). The hooked indices are correct and must not be changed; only the names are wrong.
- SC4-UI-ENGINE.md §2.2 item 2 calls `[this+0x64]` 'the mask sub-object'. It is the window's own private cIGZBuffer: PrivateBuffer(bool) at 0x0099EAD7 calls buffer slot 12 GetBufferArea (0x8268C0, from this file's own §2.3 table) on it, and slot 150 (0x0099D0ED) creates and destroys it. The refined hit test 0x0099BBBE Locks it (buffer slot 6 with 0x800) and reads it per pixel. Consequence: a stale private buffer mis-routes clicks on any MouseTrans window, not just mis-draws.
- tools\uimap\emu\SHOW-PATH.md §3 trap 1, §7, and _checkpoints\uimap-stage3-emu.md line 187 identify 0x0099EA70 as the engine's 'effectively visible' ancestor-walk test. It is real slot 100, PrivateBuffer(bool) — the private-buffer (re)allocator. The ancestor walk is only its entry gate, and its failure action is DESTRUCTIVE: a hidden ancestor makes it take the destroy path instead of resizing. The derived claim (IsVisible() is the window's own bit only) stands; the function's identity does not.
- _tests\REGRESSION.md law 8 and _checkpoints\task55-47-runtimeimg.md (lines 448-456, 485) state the window's own pixel buffer is `[win+0x6c]`. Measured: `[win+0x6c]` is the refcounted DRAW CONTEXT (base slot 93 `mov eax,[ecx+0x6C]`; PlotComposite AddRefs it at 0x0099E772 via 0x004F20C0 and then calls ~11 context virtuals on it). `[win+0x68]` is the destination buffer (base slot 94; the flyout's `dst68`) and `[win+0x64]` is the private buffer. The law's conclusion — pbuffs are sized at first paint and born-2x data is the cure — is unaffected and is now explained: the gauge cache is class-private, so SetArea's resize path (0x0099C837 -> 0x0099EA70) cannot reach it at all.
- SC4-UI-ENGINE.md §2.1 describes the flyout container's `test byte[0x114],1` as 'Plot only REDRAWS when the dirty bit is set… Normally dirty=0, so Plot early-exits to the blit path.' That is the CLASS's own bit and is correct, but it should not be generalised to the engine: the base dirty byte `[win+0x70]` is cleared only when the window owns a private buffer AND has a parent (0x0099E747..0x0099E753). Windows without a private buffer — most of the HUD — stay dirty from construction and run GZPaint every frame. There is no engine-level caching for them.
- REGRESSION.md 2026-07-30 'THE FLASH: DECODED' reasons about sweep cadence vs. a 20-36ms window. The measurement above adds the harder constraint: no cadence can win, because a resize cannot be composited in the tick it is made, and because a dirty child under a clean parent is not painted at all. The 'smaller idea' recorded there (move the gForceRecreate earlier) is the right shape — but the earliest useful point is before the window becomes VISIBLE, since PlotComposite step 1 skips invisible subtrees outright (0x0099E636..0x0099E64E).

## OPEN
- UNRESOLVED, with positive control: where in the frame the UI composites relative to the 3D view. Enumerated by opcode scan every call site of slot 123 PlotComposite (4: 0x005502C2, 0x00916395, 0x00976C6E, 0x0099BA0D) and slot 89 Plot (44). 0x0099BA0D is cIGZWin::Plot itself; 0x00916395 and 0x00976C6E sit inside script/command binding jump tables that also expose GZPaint and InvalidateSelf; 0x0099E9B3 is the child recursion. So the scan COULD have seen a direct driver and did not — the driver must be cIGZWinMgr::Plot (winmgr vtable slot 6), whose vtable is only known at runtime (singleton at 0x00B628C0, filled by 0x00913C46). NEXT STEP: read *(void**)0x00B628C0 live, dump slot 6, log it once per frame against QPC and compare with the 3D view's tick. Claim no ordering before that.
- What are the two undocumented window flags the paint path uses? 0x400000 is set on a window after a successful GZPaint into its private buffer (0x0099E859) and 0x4000000 marks a window queued into the plot strategy (set at 0x0099E8C8/0x0099E93C/0x0099E9D5, consumed and cleared in PlotPresent at 0x0099C501). Neither is in cIGZWin.h's tWinFlag enum. Worth confirming whether 0x400000 gates anything we could use as a cheap 'this buffer is valid' probe.
- Which of our scaled windows actually carry WinFlag_PrivateBuffer (0x10000)? The whole §2.4.4 resize path only runs for those, and the split determines which fixes are even possible per window. This is a one-line addition to the existing tree dump (GetFlag(0x10000) plus GetPrivateBuffer's [win+0x64]) and would turn a lot of per-widget guesswork into a lookup. Cheap, and it should be measured before task #47 is reopened.
- Does any window in our scaled set sit under a WinFlag_DelayedPlot (0x8000000) ancestor? If so, its InvalidateSelfAndParents is silently truncated and it is drawn by ExecutePlotStrategy on a different pass — a completely untested axis against _tests\SCENARIOS.md. Same one-line probe as above.
- 0x0099BD27 (real slot 57, GZWinMoveRelative) is a delta move that goes through SetArea and therefore through the whole invalidate + buffer-resize tail. Nothing in our code uses it. Worth checking whether the game uses it for the dock/flyout MOVE, because a mod that moves a window with it gets the buffer-resize gate for free, whereas our SetArea-with-recomputed-absolute-rect path does the same thing only when W/H changed.
- PlotPresent reads a 4th rect at [win+0xB8..0xC4], distinct from absolute [0x14], area-to-draw-to [0x24] and relative [0xA8]. It is zeroed in the ctor at 0x0099DB28 and used for the non-deferred present. Its writer was not traced; if it is a cached present rect it is another candidate for staleness after a resize.

---

================================================================
PATCH A — tools\research\SC4-UI-ENGINE.md, §2.1, replace the slot
table under "The zero-argument draw group, slots 87..97"
================================================================

⛔ **CORRECTION (supersedes the earlier 87..97 table).** The vendor header
`vendor\gzcom-dll\...\cIGZWin.h` is **missing one virtual**, so every index it
implies from 57 upward is one too low. The exe has, between `GZWinMoveTo`
and `FitRectToWindow`, an undeclared **relative** move: real slot 57
`0x0099BD27` = `SetArea(L+dx, T+dy, R+dx, B+dy)`, `ret 8`. The hooks we ship
were always installed at the RIGHT indices — only the names were wrong.

> **EVIDENCE (naming shift).** `0x0099BD27`: `mov edx,[ecx+0xB4]; add
> edx,[esp+8]` … four adds, then `call [eax+0xDC]` (= slot 55 `SetArea`),
> `ret 8` — a delta move with no header counterpart, while real 56
> `0x0099C8C5` is the absolute `GZWinMoveTo`. Four independent confirmations
> that everything above 56 shifts by +1: real 61 `0x0099B8F5` is
> `this->slot60(x,y)` then `other->slot59(x,y)`, `ret 0xC` = the 3-arg
> `WindowToWindowCoordinates` (header idx 60); real 99 is
> `lea eax,[ecx+0x24]; ret` = zero-arg `GetAreaToDrawTo` (header idx 98) and
> real 100 `0x0099EA70` ends `ret 4` = the 1-arg `PrivateBuffer(bool)`
> (header idx 99); real 123/124 are exactly `PlotComposite`/`PlotPresent`
> (header idx 122/123); real 134 is the first `ret 0xC` mouse handler =
> `GZOnMouseDownL` (header idx 133).

| real idx | virtual (corrected) | base impl | shape |
|---|---|---|---|
| 87 | `GetNotificationTarget` | `0x0099BE4C` | `mov eax,[ecx+0x4C]; ret` |
| **88** | **`GZPaint`** — *this is the per-class "draw myself"* | per class | 0x949ADE (no-op, 18 classes), 0x9995E7 (GZWinGen, 15), 0x79B0E0 (flyout container), 0x7A9500 (RCI), 0x7BF0A0 (TrendBar) |
| **89** | **`Plot`** | `0x0099BA07` | `PlotComposite() && PlotPresent()`; then if `byte[this+0x71]==0`, `winmgr->ExecutePlotStrategy()` |
| 90 | `CalcAbsoluteArea` | `0x0099DCE4` | |
| **91** | **`InvalidateSelf`** | `0x0099BECC` | `mov byte [ecx+0x70],1; ret` — the whole thing |
| **92** | **`InvalidateSelfAndParents`** | `0x0099BED1` | see §2.4.1 |
| 93 | `GetDrawContext` | `0x0099BEF9` | `mov eax,[ecx+0x6C]` |
| 94 | `GetBufferToDrawTo` | `0x0099BEFD` | `mov eax,[ecx+0x68]` |
| 95 | `SetBufferToDrawTo` | `0x0099C6F8` | |
| 96 | `SetBufferToDrawToRecursive` | `0x0099D57E` | |
| 97 | `SetAreaToDrawTo` | `0x0099CF6A` | |
| 98 | `SetAreaToDrawToRecursive` | `0x0099D5B7` | called by `SetArea` |
| 99 | `GetAreaToDrawTo` | `0x00477810` | `lea eax,[ecx+0x24]` — the rect the flyout Blt uses |
| 100 | `PrivateBuffer(bool)` | `0x0099EA70` | **1 arg**, `ret 4` — see §2.4.4 |
| 101 | `GetPrivateBuffer` | `0x009D419D` | `mov eax,[ecx+0x64]` |
| 121 / 122 | `IsPointInWindowWindowCoordinates` / `…ParentCoordinates` | `0x0099C8F5` / `0x0099C960` | 121 rejects negative x/y (window coords); 122 tests against `[0xA8]` (parent coords) |
| 123 | **`PlotComposite`** | `0x0099E62D` | §2.4.2 |
| 124 | **`PlotPresent`** | `0x0099C498` | §2.4.3 |
| 134 | `GZOnMouseDownL` | first `ret 0xC` handler | |
| 136 / 138 | `GZOnMouseUpL` / `GZOnMouseMove` | | |
| 149 / 150 | *cGZWin's own* extras, past the end of `cIGZWin` | `0x0099BBBE` / `0x0099D0ED` | refined per-pixel hit test / create private buffer |

⛔ **Hooking 87..97 remains SAFE** — under the corrected names the range is
still entirely zero-argument (verified: 95/96/97/98 all end in a bare `ret`).
But note what it now means: **slot 88 is `GZPaint`, not `Plot`.** Our
`DOBS`/`SUBHOOK` instruments have always been sitting on `GZPaint`. And
⛔ **do not "fix" this by moving to slot 89** — real `Plot` is the composite
driver; hooking it puts a thunk in front of the whole subtree walk.

⛔ **`0x0099BBBE` is not a "mask sub-object" dispatcher** (§2.2 item 2 is
wrong). It reads **`[this+0x64]`, the window's own private `cIGZBuffer`**:
buffer slot 24, then `Lock(0x800)` (slot 6), then the 2-arg per-pixel test
(slot 25), then `Unlock` (slot 7). The consequence is load-bearing for this
project: **on a `MouseTrans` window the pixel-accurate hit test reads the
private buffer, so a stale or wrongly-sized buffer makes clicks land wrong
even when the DRAW looks right.** Any "the art is 2x but the clicks are 1x"
symptom on such a window is a buffer symptom, not a rect symptom.

> **EVIDENCE.** `0x0099BBBE`: `cmp dword [esi+0x64],0; je fail` →
> `call [buf_vt+0x60]` → `push 0x800; call [buf_vt+0x18]` →
> `call [buf_vt+0x64]` (2 pushed args) → `call [buf_vt+0x1C]`; `ret 8`.
> `[this+0x64]` is proven to be a `cIGZBuffer` by `0x0099EAD7`:
> `call [buf_vt+0x30]` = `GetBufferArea 0x8268C0` from the §2.3 table.

================================================================
PATCH B — tools\research\SC4-UI-ENGINE.md, §8.1 registry table
================================================================

Replace the row `0x0099BE4C | base GZPaint (slot 87)` with:

| `0x0099BE4C` | base **`GetNotificationTarget`** (slot 87) — the vtable-diffing baseline, *not* GZPaint | vtable diffing |
| `0x0099E62D` | **`PlotComposite`** (slot 123) — the recursive paint walker | §2.4.2 |
| `0x0099C498` | **`PlotPresent`** (slot 124) | §2.4.3 |
| `0x0099BA07` | **`Plot`** (slot 89) = composite + present + `ExecutePlotStrategy` | §2.4 |
| `0x0099BECC` / `0x0099BED1` | `InvalidateSelf` / `InvalidateSelfAndParents` (slots 91/92) | §2.4.1 |
| `0x0099B7BD` | the ancestor dirty-marking walk (tail of slot 92) | §2.4.1 |
| `0x0099EA70` | **`PrivateBuffer(bool)`** (slot 100) — the private-buffer (re)allocator, **not** a visibility test | §2.4.4 |
| `0x0099D0ED` | create/destroy the private buffer at `(W,H)` (cGZWin extra slot 150) | §2.4.4 |
| `0x0099BD27` | `GZWinMove**Relative**(dx,dy)` — real slot 57, absent from the vendor header | the +1 index shift |

================================================================
PATCH C — tools\research\SC4-UI-ENGINE.md, NEW §2.4
================================================================

### 2.4 The paint pipeline: invalidate → composite → present

Nearly every hard defect on this project has been a paint-timing problem. This
is the pipeline, disassembled end to end. Read §2.4.6 first if you only want
the rule.

**The nine fields that matter.** All measured in the cGZWin constructor
`0x0099DA5A`–`0x0099DB33` and in the functions below.

| Field | Meaning | Born as |
|---|---|---|
| `[win+0x04]` | the `cIGZWinMgr` | fetched at construction (`0x00913C46`) |
| `[win+0x14..0x20]` | **absolute** rect | 0 |
| `[win+0x24..0x30]` | **area-to-draw-to** (the clipped destination rect; this is the rect in the flyout's `Blt`) | 0 |
| `[win+0x44]` | child list | — |
| `[win+0x48]` | parent | 0 |
| **`[win+0x64]`** | **private `cIGZBuffer`** (only if `WinFlag_PrivateBuffer`) | **0** |
| `[win+0x68]` | the `cIGZBuffer` this window draws INTO | 0 |
| `[win+0x6C]` | the draw context (refcounted) | 0 |
| **`[win+0x70]`** | **the dirty byte** | **1 — every window is born dirty** |
| `[win+0x71]` | suppress-`ExecutePlotStrategy` latch (held only inside `SetBufferToDrawTo`) | 0 |
| `[win+0xA8..0xB4]` | **relative** rect (L,T,R,B) | 0 |
| `[win+0xC8]` | the flag dword | `0x8903` |

> **EVIDENCE.** `0x0099DAB2`: `mov [esi+0x64],ebx; mov [esi+0x68],ebx;
> mov [esi+0x6C],ebx;` then `0x0099DABB  c6 46 70 01` = `mov byte
> [esi+0x70],1` and `88 5E 71` = `mov byte [esi+0x71],bl(0)`. The only writers
> of `[win+0x71]` in the whole image are `0x0099C70C` (set 1) and
> `0x0099C76A` (set 0), both inside `SetBufferToDrawTo` `0x0099C6F8`.

⛔ **There is no dirty RECTANGLE anywhere in cGZWin.** Dirt is one boolean
byte per window. Every repaint is a whole-window repaint. Stop looking for a
region-accumulation stage — there isn't one.

#### 2.4.1 Invalidation and how it propagates

```
InvalidateSelf            (slot 91, 0x0099BECC)   c6 41 70 01 c3
    byte[this+0x70] = 1                      ; that is the ENTIRE function

InvalidateSelfAndParents  (slot 92, 0x0099BED1)
    this->InvalidateSelf()                   ; call [vt+0x16C]
    if (this->GetFlag(0x8000000))  return;   ; WinFlag_DelayedPlot -> stop
    goto 0x0099B7BD:                         ; tail jump
        for (w = this->GetParentWin(); w; w = w->GetParentWin()) {
            w->InvalidateSelf();             ; byte[w+0x70] = 1
            if (w->GetFlag(0x8000000)) break;  ; DelayedPlot is a WALL
        }
```

> **EVIDENCE.** `0x0099BED1`: `56 8B F1 8B 06 FF 90 6C 01 00 00` then
> `push 0x8000000; call [eax+0x10C]; test al,al; jne ret; jmp 0x99B7BD`.
> `0x0099B7BD`: `8B 01 56 EB 21` into the loop `call [vt+0x16C]` →
> `push 0x8000000; call [vt+0x10C]` → `call [vt+0x2C]` (`GetParentWin`).
> `[vt+0x10C]` is `GetFlag`, a reader — already corrected in
> `tools\uimap\emu\SHOW-PATH.md` §7.

Two consequences, both new:

1. **`InvalidateSelf` alone is almost always useless**, because of the parent
   gate in §2.4.2. This finally gives the *mechanism* for the rule recorded in
   `GOD-MODE-FLYOUTS.md` "Other hard-won rules" and repeated in the §1.4 table
   of this file — *"`InvalidateSelfAndParents()` is the ONLY safe repaint
   primitive after a geometry change… otherwise the game keeps the stale paint
   until a mouse hover invalidates."* The hover "fixes" it because the hover
   dirties an **ancestor**, not because it touches the window.
2. **`WinFlag_DelayedPlot (0x8000000)` is a wall in BOTH directions**: it stops
   the upward dirty walk, and (see §2.4.2) it diverts the subtree into the
   window manager's plot strategy. A hook that calls
   `InvalidateSelfAndParents` under a DelayedPlot ancestor has not scheduled
   anything on the normal path. **337 call sites** in the exe use slot 92; it
   is the engine's own universal "I changed" primitive, so matching it is
   always the safe imitation.

#### 2.4.2 `PlotComposite` (slot 123, `0x0099E62D`) — the walker

In order, on `this`:

1. **Visibility gate.** `flags = [this+0xC8]`; if `!(flags & 0x20 UseFade)`
   then continue only if `flags & 1 Visible`, else **return immediately** —
   the entire subtree is skipped. (With `UseFade` set, an invisible window
   still runs one fade step, `0x0099C20D` / `0x0099C026`.)
2. Message filters over `[this+0x88]`; a filter that returns true aborts.
3. **THE DIRTY GATE.** `if (byte[this+0x70] == 0) goto harvest;`
4. **Dirty path.** If `[this+0x64] != 0` **and** `[this+0x48] != 0`, clear
   `byte[this+0x70] = 0`; then, if `flags & 0x20000 PrivateBufferTrans` **and**
   `flags & 0x40000 PrivateBufferErase`, erase the private buffer
   (`0x0099BA3E`: Lock(0x8001) → fill `[this+0x24]` rect → Unlock).
   Acquire the draw context `[this+0x6C]`, push clip/alpha/shade state onto
   it (ctx slots 3, 8, 6, 4, 15, 10, 19, 22, 23, 21, 43 — driven by
   `GetFlag(4 AlphaBlend)`, `GetFlag(0x10000 PrivateBuffer)`, `[this+0xD0]`
   shade), then **`call [vt+0x160]` = slot 88 `GZPaint`** — the class's own
   drawing. If the window has a private buffer, set `flags |= 0x400000`
   ("this private buffer now holds content"; undocumented in the header).
   Pop the context.
5. **Children.** Walk `[this+0x44]` following the `[node+4]` link (the
   **opposite** link from the hit-test router `0x0099DFA9`, which is why paint
   order is back-to-front and hit order is front-to-back — see §1.2). For each
   child: skip unless `IsVisible()`; if the child has `DelayedPlot`, instead
   `child->SetFlag(0x4000000, true)` and `winmgr->AppendToPlotStrategy(child)`
   and remember the child's absolute rect; if a previously deferred sibling's
   rect **overlaps** this child, defer this child too (`0x0099C1E1` rect test);
   otherwise **`child->Plot()`** (slot 89) — the full composite+present,
   recursively.
6. **Harvest path (window NOT dirty).** `EnumChildren(GZIID_cIGZWin,
   0x0099B9AC, winmgr)`. That callback paints **nothing**: for each visible
   child it either hands it to `AppendToPlotStrategy` (DelayedPlot) or recurses
   the same enumeration deeper.

> **EVIDENCE.** Prologue `0x0099E62D`; visibility gate `0x0099E636..0x0099E64E`;
> dirty gate `0x0099E73D  80 7B 70 00  0F 84 CB 02 00 00` then
> `83 7B 64 00 74 25  83 7B 48 00 74 04` and `0x0099E753 mov byte[ebx+0x70],0`;
> `GZPaint` call `0x0099E84D  call [eax+0x160]`; `|= 0x400000` at
> `0x0099E859`; child list `0x0099E883 mov esi,[ebx+0x44]`; recursion
> `0x0099E9B3 call [eax+0x164]`; `AppendToPlotStrategy` at `0x0099E8D4`,
> `0x0099E948`, `0x0099E9E1` via `[ebx+4]` slot 7; harvest at `0x0099EA12
> push [ebx+4]; push 0x0099B9AC; push 0x22BA0121; call [eax+0x80]`
> (`EnumChildren`). `cIGZWinMgr` slot 7 = `AppendToPlotStrategy` and slot 8 =
> `ExecutePlotStrategy` are exact against `vendor\gzcom-dll\...\cIGZWinMgr.h`
> (no shift in that header — proven by the cGZWin ctor calling winmgr slot 20
> `AddWindowToValidList(this)` at `0x0099DA43`).

⛔ **The single most important line in the engine is step 3.** *A dirty child
under a clean parent is never reached.* The parent's `PlotComposite` returns
through the harvest path, which draws nothing. **That is why the dirty flag
must be pushed all the way to the root, and why our sweeps must call
`InvalidateSelfAndParents`, never `InvalidateSelf`.**

⛔ **Two classes of window, two very different lives.** The dirty byte is
cleared *only* for a window that owns a private buffer **and** has a parent.
Everything else — which is nearly the whole HUD — stays `dirty = 1` from
construction forever and therefore **runs its `GZPaint` on every single
frame**. There is no "cached, skip" for them. This is the measured basis of
the flash law in `feedback-sc4-reactive-sweep-flashes`: panels are not
flashing because a repaint was missed, they are flashing because they are
repainted 60x/second from state we corrected one frame too late.

#### 2.4.3 `PlotPresent` (slot 124, `0x0099C498`) — the blit up

```
if ([this+0x64] == 0) return;                 ; nothing of its own to present
rect = [this+0xB8..0xC4]
if (GetFlag(0x4000000)) { ...deferred path, rect = [this+0x14..0x20],
                          SetFlag(0x4000000,false) }
else if (parent && parent->GetBufferToDrawTo())  dst = parent->[0x68]
else                                              dst = canvas->slot8()
```
The parentless case reads a lazily-cached global at **`0x00BAC058`**, filled
from `0x00449560` (a smart-pointer get) and then queried with slot 8 for its
buffer — i.e. **a root window presents into the canvas's own surface**, which
is the 2400x1600 32bpp GPU-only buffer already documented in §2.3 as the
flyout's `dst68`.

> **EVIDENCE.** `0x0099C4A1 cmp [ebx+0x64],0; je ret`; `0x0099C51C`
> `parent->call [eax+0x178]` (slot 94 `GetBufferToDrawTo`); `0x0099C535
> mov ecx,[0xBAC058]` with the fill at `0x0099C54D` and `call [eax+0x20]`
> at `0x0099C563`. Only three references to `0x00BAC058` exist in `.text`,
> all three inside this function.

#### 2.4.4 When a buffer is allocated, and from what size

`SetArea(l,t,r,b)` — base **`0x0099C837`**, real slot 55, already known to the
offline model (`tools\uimap\emu\README.md`, `emu_layout.py`) as "stores L,T,R,B
at `[this+0xA8..0xB4]`". What the model does not yet carry is the **tail**:

```
sizeChanged = (r-l != oldW) || (b-t != oldH)
store L,T,R,B into [this+0xA8..0xB4]                 ; ALWAYS, immediately
if ((flags & 0x10000 WinFlag_PrivateBuffer) && sizeChanged)
        this->PrivateBuffer(true)                    ; slot 100
this->CalcAbsoluteArea()                             ; slot 90
this->SetAreaToDrawToRecursive()                     ; slot 98
```

`PrivateBuffer(true)` — **`0x0099EA70`**, real slot 100:

```
for (w = this->GetParentWin(); w; w = w->GetParentWin())
        if (!w->IsVisible()) { arg = false; break; }   ; <-- the gate
if (!arg) goto DESTROY;
flags |= 0x10000
if ([this+0x64] && buffer size == window size) return;   ; nothing to do
CreatePrivateBuffer(W, H)                                 ; slot 150, 0x0099D0ED
if (flags & 0x20000) 0x0099BA92(1)
this->SetArea(L,T,R,B)                                    ; re-run geometry
```

> **EVIDENCE.** `0x0099C87A  F6 86 CA 00 00 00 01` = `test byte
> [esi+0xCA],1` — byte `0xCA` is bits 16..23 of the flag dword at `0xC8`, so
> bit 0 of it is `0x10000 = WinFlag_PrivateBuffer`; the matching setter is
> `0x0099EAB8 or byte [esi+0xCA],1`. Buffer-vs-window size compare
> `0x0099EAC3..0x0099EAFE` (window W/H from `[0xA8]`, buffer W/H from
> `GetBufferArea`, compared by `0x00798070`). Creation
> `0x0099EB22 call [eax+0x258]` = slot 150. The ancestor gate is
> `0x0099EA8A  8B 07 8B CF FF 90 1C 01 00 00 84 C0 74 0F` →
> `0x0099EAA7 mov byte [ebp+8],0`.

⛔ **`0x0099EA70` is NOT an "effectively visible" test.** `SHOW-PATH.md`
§3 trap 1 and §7, and `_checkpoints\uimap-stage3-emu.md` line 187, describe it
that way. The ancestor walk is real, but it is the **entry gate of the
private-buffer allocator**, and its failure action is destructive: **resizing a
window while any ancestor is hidden does not give you a correctly-sized buffer
— it throws the buffer away.** Do not call it, or provoke it, as a probe.
(The note in `SHOW-PATH.md` that a hidden ancestor makes `IsVisible()` lie is
still correct; only the function's identity is wrong.)

#### 2.4.5 Why the class-cached widgets are unreachable by any of this

The three widgets that produced our "born at first-paint size" bugs do **not**
use `[win+0x64]`. They keep a cache in a **class-private field**, allocated
inside their own `GZPaint`:

| Widget | Cache field | Allocated in |
|---|---|---|
| flyout container `0x00AB6AA8` | `[this+0xDC]` | its `GZPaint` `0x0079B0E0`, realloc check `0x0079B117`, gated on its own dirty bit `byte[0x114]` |
| `cSC4WinMiniMap` `0xCA318388` | `[this+0xF0]` | one-shot at city load (§2 table) |
| gauge dials `0xCBCBF1E0` | class-private | its own draw |

`SetArea` cannot see those fields. **There is no engine path that resizes
them.** That is not an oversight to work around — it is the reason the only
two levers that have ever worked are *born at the right size* (ship the data
2x) and *force-recreate* (corrupt the cached width so the class's own validity
check fails). Both are already law; this is the mechanism.

#### 2.4.6 THE ANSWER: why a window resized this tick still paints small

Nothing about `SetArea` is deferred — the rect is correct within microseconds,
which is exactly what we measured ("the window rect is corrected within ~1ms",
`REGRESSION.md` 2026-07-30). What is deferred is **the pixels**, for four
separate and independent reasons:

1. **`SetArea` never paints.** It calls slots 90 and 98 (recompute absolute
   area and clip rects) and never slot 88 or 123. No drawing happens until the
   frame's own `Plot()`.
2. **If the window keeps its own class cache** (§2.4.5), the new size reaches
   nothing. The next `GZPaint` fills a 141x339 buffer into a 282x678 window and
   the composite is a 1:1 clipped copy (§2.3 — `Blt` clips, never stretches).
   Symptom: correct frame, small content pinned to a corner.
3. **If the window has a real `WinFlag_PrivateBuffer`**, the buffer *is*
   re-created — unless an ancestor is hidden at that instant, in which case it
   is destroyed instead (§2.4.4) and re-made later at whatever size the window
   has when it is next shown.
4. **Even with everything correct, the repaint needs a dirty ancestor chain.**
   If the parent is clean, `PlotComposite` takes the harvest path and paints
   nothing (§2.4.2).

**The earliest point at which a size change is guaranteed visible is the first
`PlotComposite` pass after the change — i.e. the next frame — and only if all
four of these hold at that moment:**

* the window and **every** ancestor up to the root is `Visible`;
* `byte[win+0x70] == 1` **and** every ancestor's is too (so: call
  `InvalidateSelfAndParents`, slot 92, and nothing less);
* no ancestor between the window and the root carries
  `WinFlag_DelayedPlot 0x8000000` (which both stops the dirty walk and reroutes
  the subtree into `ExecutePlotStrategy`);
* the pixels actually live somewhere `SetArea` can reach — i.e. **not** a
  class-private cache.

⛔ **There is no same-tick path.** A hook cannot make a resize visible in the
frame in which it runs; the composite for that frame has either already
happened or will read state the hook has not finished writing. The only
reliable lever is the one we already ship: **make the window correct before it
becomes visible**, because step 1 of `PlotComposite` skips invisible subtrees
outright, so a window scaled while hidden has no wrong frame to show. That is
the measured justification for the pre-scale-while-hidden law
(`feedback-sc4-prescale-while-hidden`) and for born-correct
(`REGRESSION.md` law 8 / task #76 / task #78).

#### 2.4.7 OPEN — where the UI composites relative to the 3D view

**Not resolved, and stated as a null WITH its positive control** (per
`feedback-null-is-not-evidence`). What is measured: the only engine-internal
caller of `PlotComposite` is `cIGZWin::Plot` at `0x0099BA0D`; the other two
call sites (`0x00916395`, `0x00976C6E`) are script/command binding
dispatchers — big jump-table switches that expose `GZPaint`/`Plot`/
`PlotComposite` to Lua — and `0x005502C2` is app code. All **4** call sites of
slot 123 and all **44** of slot 89 were enumerated by opcode scan, so the
search could have seen the driver if it called either virtual directly.

The unexplored branch is the one the header names: **`cIGZWinMgr::Plot`
(winmgr vtable slot 6)**. The winmgr singleton is `0x00B628C0`, populated
lazily by `0x00913C46`, so its concrete vtable is a runtime value and the
static scan cannot reach slot 6. **Next step:** read `*(void**)0x00B628C0`
in a live session, dump slot 6, and set a one-shot log on it — or simply log
the first `GZPaint` of the frame against a `QueryPerformanceCounter` stamp and
compare with the 3D view's own tick. Do not assume an ordering until then.

================================================================
PATCH D — _tests\REGRESSION.md, LAWS section
================================================================

**LAW 8 EXTENDED (was: "PBUFFS ARE BORN AT FIRST-PAINT SIZE").** The law is
right and the field is right, but the *reason* is now measured, and it splits
in two. The engine owns a private buffer at **`[win+0x64]`** (not `[0x6c]` —
`[0x6c]` is the refcounted draw context, `[0x68]` is the destination buffer),
and it **does** resize it: `SetArea` (`0x0099C837`) calls
`PrivateBuffer(true)` (slot 100, `0x0099EA70`) whenever
`WinFlag_PrivateBuffer 0x10000` is set and W/H changed. ⛔ **But
`PrivateBuffer(true)` walks the ancestor chain first and, if any ancestor is
hidden, flips to the DESTROY path** (`0x0099EA8A` → `0x0099EAA7`). And the
widgets that actually bit us — the flyout container `[0xDC]`, the minimap
`[0xF0]`, the gauge dials — keep their cache in a **class-private** field that
`SetArea` cannot see at all, so for them **no resize path exists by
construction**. Born-2x and force-recreate are not workarounds; they are the
only two doors.

**NEW LAW — A DIRTY CHILD UNDER A CLEAN PARENT IS NEVER PAINTED.**
`PlotComposite` (`0x0099E62D`) gates on `byte[this+0x70]` at `0x0099E73D`; if
the window is clean it takes `EnumChildren(0x0099B9AC)`, which paints nothing
and only harvests `DelayedPlot` windows into the plot strategy. Therefore
`InvalidateSelf` (slot 91 — literally `byte[this+0x70]=1; ret`) is not a
repaint request. **Only `InvalidateSelfAndParents` (slot 92, `0x0099BED1`) is**,
because it walks `GetParentWin` marking every ancestor (`0x0099B7BD`). This is
the mechanism behind the long-standing "only scales after I move the mouse over
it" symptom: the hover dirties an ancestor, not the window.

**NEW LAW — `WinFlag_DelayedPlot (0x8000000)` IS A WALL, AND `[win+0x70]` IS
CLEARED ONLY FOR PRIVATE-BUFFER WINDOWS.** The upward dirty walk stops at the
first ancestor with `DelayedPlot`, and the composite reroutes such subtrees to
`cIGZWinMgr::AppendToPlotStrategy` (winmgr slot 7) under flag `0x4000000`,
drained later by `ExecutePlotStrategy` (slot 8). Separately, the dirty byte is
cleared only when `[win+0x64] != 0` **and** `[win+0x48] != 0`
(`0x0099E747..0x0099E753`) — so every window without a private buffer, which is
most of the HUD, runs its `GZPaint` **every frame**. Consequence for any future
flash work: the flash is not a missed repaint, it is 60 correct repaints of
state we fixed one frame late. Cure the birth, never the paint. (This also
re-confirms the permanent ban on `FlashGuard`.)

**NEW LAW — A STALE PRIVATE BUFFER BREAKS CLICKS, NOT JUST PIXELS.** The
refined hit test (cGZWin extra slot 149, `0x0099BBBE`) Locks `[win+0x64]` and
reads it **per pixel** to decide whether a `MouseTrans` window claims a point.
`SC4-UI-ENGINE.md` §2.2 item 2 calls `[this+0x64]` a "mask sub-object"; it is
the window's own private `cIGZBuffer`. So on any `MouseTrans` window, "art
looks 2x but clicks behave 1x" is a **buffer** diagnosis, and the buffer must
be fixed before the rect is even worth checking.

**NEW LAW — THE VENDOR HEADER IS ONE SHORT; NAMES ABOVE SLOT 56 ARE ONE LOW.**
`cIGZWin.h` omits `GZWinMoveRelative(dx,dy)` (real slot 57, `0x0099BD27`,
`ret 8`). Every index it implies from 57 up is one too low. Our hooks are at
the right numbers and stay; **our names were wrong**: slot 88 is `GZPaint`
(not `Plot`), slot 89 is `Plot` = `PlotComposite && PlotPresent`, slot 91 is
`InvalidateSelf`, slot 92 is `InvalidateSelfAndParents`, slot 121/122 are
`IsPointInWindow{Window,Parent}Coordinates`, slot 123/124 are
`PlotComposite`/`PlotPresent`. This also explains, retroactively, two
empirical results in `UiSpike.cpp`: slot 133 crashed because it is
`GZOnKillFocus` (1 arg, `ret 4`) and not `GZOnMouseDownL` (real 134); and the
"VERIFIED list-specific 3-arg handlers" 136 and 138 are `GZOnMouseUpL` and
`GZOnMouseMove` — which is why 136 "commits the selection" (selection fires on
mouse-UP) and 138 "computes item-from-Y" (hover tracking). Update the comment
block at `UiSpike.cpp` ~line 104 and the slot names only; **change no
indices**.

