# TARGET: tools\research\SC4-UI-ENGINE.md — replace §2.2 wholesale with the section below (it currently runs 12 lines; the replacement is the generalised SDK chapter the brief asked for). Three small edits elsewhere in the same file: the §1.4 "Window flags" row gains the SDK's real flag names and a pointer to §2.2; §8.1 gains/corrects four VA rows; §9 gains the four contradiction entries listed separately. `tools\research\GOD-MODE-FLYOUTS.md` §"REUSABLE PLAYBOOK" and `HANDOFF-god-mode-flyouts.md` §12a should carry a one-line back-reference to the corrected slot numbering rather than being rewritten (they are history, this file is the SDK).

## SUMMARY
Generalised the flyout hit-test playbook into a full SDK section on input routing, measured entirely offline from SimCity 4.exe 1.1.641.0 (capstone, ImageBase 0x400000), the vendor headers and existing logs — no game launch, nothing written.

What is genuinely NEW (not in any doc today):
1. The whole stage upstream of the router. `cRZWin::DoMessage` = 0x0099CCF0, vtable slot 3, is the single per-window funnel. It runs the cIGZWinMessageFilter chain at [this+0x88] FIRST — any filter returning true swallows the message before any handler — then dispatches through a 20-entry jump table at 0x0099CEF9 (message ids 1..0x14; 2, 9, 12, 15 are unhandled). Full id-to-slot map recovered, plus the cGZMessage field layout used by the mouse path (x = int16 at +4, y = int16 at +8, wheel = int16 at +0xC, key/button flags = uint16 at +0xE) and the re-entrancy byte at [this+0x90].
2. Router order == EnumChildren order, PROVEN rather than assumed. Both 0x0099DFA9 and EnumChildren 0x0099D708 walk the identical circular list at [this+0x44] head-forward from the same sentinel with the same AddRef ([esi+4]) and the same release (0x0099D3D2). §1.3 already says enumeration is reverse of add order; that now upgrades to "the first window in any tree dump that covers the point is the one that gets the click". Also: the router AddRefs the list for the duration of the walk, and it does NOT test WinFlag_Enabled (0x2) — a disabled window still claims.
3. THE cause of draw-vs-hit divergence, measured end to end. There are TWO rects. [this+0xA8..0xB4] is the parent-relative rect — that is what .UI `area=`, SetArea (slot 55, 0x0099C837), GZWinMoveTo (slot 56, 0x0099C8C5, literally SetArea(l+dx,t+dy,r+dx,b+dy)), GetW/GetH/GetL and every scaling write touch. [this+0x14..0x20] is a separate ABSOLUTE cache, and it is the ONLY rect the hit test reads (base IsPointInMe 0x0099C97C -> cRZRect::Contains 0x00664C60 on [this+0x14]). Neither SetArea nor GZWinMoveTo updates it. It is rebuilt only by the recursive zero-arg slot 90 (0x0099DCE4), which copies GetArea(), adds every ancestor's GetL/GetT walking GetParentWin, stores into [this+0x14..0x20] and recurses into all children. So a window that has been moved or resized paints at its new place and hit-tests at its old one until slot 90 runs on it or an ancestor.
4. The refined-mask stage is fully decoded and bounded: the mask branch runs ONLY if the coarse rect already passed, so a mask can subtract from the rect but never add; the coordinate handed to it is window-LOCAL, and slot 149 has exactly two call sites in the whole exe (0x0099C94A and 0x0099C9C9), so forcing it is a total override of refined hit-testing. cRZRect::Contains is half-open — right and bottom edges are EXCLUSIVE.
5. A slot-numbering law with a cheap check. gzcom-dll's cIGZWin.h index is NOT the game's vtable slot in the input band (header 62 = GetID; the game's GetID is slot 63 and slot 62 is a virtual the header does not list at all). Measured slot map given, plus the ret-immediate rule (__thiscall callee-cleanup, so a 3-arg mouse handler must be `ret 0xC`) that would have prevented the recorded slot-133 crash in one disassembly line.

Corrections to shipped docs are listed in the contradictions field — the most consequential is that the "CalcAbsoluteArea returns 0x06752001, experiment DEAD" dead end in HANDOFF §12a was aimed one slot short.

## CONTRADICTIONS
- SC4-UI-ENGINE.md §8.1 says `0x0099BE4C` is "base GZPaint (slot 87)". MEASURED: `0x0099BE4C` is `mov eax,[ecx+0x4C]; ret` — a zero-arg getter — and `0x0099BE42` is its paired setter `mov eax,[esp+4]; mov [ecx+0x4C],eax; ret 4`. Slots 86/87 are Set/GetNotificationTarget, not GZPaint. The row is used as the "vtable diffing baseline", so it mislabels the very table readers index from. Correct the row; the *range* 87..97 is still safe to thunk wholesale because every slot in it is zero-argument, which is the property that actually matters.
- SC4-UI-ENGINE.md §2.1 draw-group table (also GOD-MODE-FLYOUTS.md L185 and HANDOFF-god-mode-flyouts.md L729) lists "89 CalcAbsoluteArea". MEASURED: slot 89 `[vt+0x164]` is `0x0099BA07`, which calls `[vt+0x1EC]` then `[vt+0x1F0]` and returns a bool in `al`. The function that actually computes the absolute area is slot **90** `[vt+0x168]` = `0x0099DCE4`: it copies `GetArea()` (`[vt+0xC0]`), walks the parent chain via `GetParentWin` (`[vt+0x2C]`) adding each ancestor's `GetL` (`[vt+0xAC]`) and `GetT` (`[vt+0xB0]`), writes `[this+0x14..0x20]` with four `movsd` at `0x0099DD35`, and recurses into every child at `0x0099DD55`. Only the *name* on slot 89 is wrong; the 87..97 hooking range is unaffected.
- HANDOFF-god-mode-flyouts.md §12a ("CalcAbsoluteArea returns 0x06752001 — NOT a rect pointer … the experiment is DEAD", echoed at GOD-MODE-FLYOUTS.md L411 and UiSpike.cpp L1841/L7760) is EXPLAINED and OVERTURNED. The hook was on slot 89 = `0x0099BA07`, which ends `mov al,bl; ret` — it writes only the low byte of `eax` and leaves the upper 24 bits stale, so `0x06752001` is caller garbage with `al = 0x01` = `true`. That is also why the container and the strip returned the *identical* value: it was never per-window data. The real recompute is slot 90 `0x0099DCE4`; it returns nothing and writes the rect in place at `[this+0x14..0x20]`. The lever the session was looking for exists — it is one slot further on.
- SC4-UI-ENGINE.md §2.2 and HANDOFF-god-mode-flyouts.md both name slot 59 `[vt+0xEC]` `WindowToScreenCoordinates`. MEASURED: `0x0099BD73` calls slot 60 `[vt+0xF0]` with two zeroed locals to obtain the window's absolute origin, then **subtracts** it from the caller's in/out pair — it is `ScreenToWindowCoordinates`. Slot 60 `0x0099BD5E` is the one that ADDS (`*px += [ecx+0x14]; *py += [ecx+0x18]`), i.e. local→screen, and slot 61 `0x0099B8F5` chains the two as `WindowToWindowCoordinates(other,…)`. HANDOFF's own DXF measurement already recorded "in(267,869)->out(77,137), constant dx=-190 dy=-732 … CORRECT screen->local conv" — the log said one thing and the label said the opposite for three sessions.
- SC4-UI-ENGINE.md §2.2 point 2 and §1.4 both refer to the coarse test rect as `[this+0x14]` while §1.4 separately states "Window rect lives at this+0xA8..0xB4", with nothing tying the two together. MEASURED: these are two DIFFERENT rects with different owners — `[0xA8..0xB4]` is parent-relative and is what `SetArea`/`GZWinMoveTo`/`GetW`/`GetH` and every scaling write touch; `[0x14..0x20]` is an absolute cache written only by slot 90, and it is the ONLY rect the hit test reads. Left as-is the docs read as if there were one rect, which is exactly the confusion that produced the v2.11.17 "no 44px rect exists" field dump.
- vendor/gzcom-dll `cIGZWin.h` vs the game, in the input band: the header's index 62 is `GetID`, but the game's `GetID` is slot 63 (`mov eax,[ecx+0x10]; ret`) and slot 62 `[vt+0xF8]` holds a virtual the header does not list at all — the one this project calls `IsPointInMe`. Likewise the header's `GetFlag` is index 66 while the game's is slot 67 `[vt+0x10C]` (shipped code already uses `vt[67]`, UiSpike.cpp L7703), and the header names six `GZOnMouse*` handlers where the game has five 3-arg slots (134..138). The header is right for the router (40), the transforms (59/60/61) and `Plot` (88). Treat header indices as a hint, never as an address.

## OPEN
- Which of `cIGZWin.h`'s six `GZOnMouse*` names has no vtable slot of its own? The game exposes exactly five 3-arg handlers (slots 134..138, `ret 0xC`) reached from message ids 7, 8, 10, 11, 13. Resolve by logging `msg->type` inside a `DoMessage` (`[vt+0x0C]`) hook on a button while clicking left, right and wheeling — one launch, no risk. Do NOT resolve it by counting the header.
- Where is `cRZWinMgr::ProcessMouseMessage` / `GZSetCapture` / `SetCurrentMouseWin`? Not located this session (the `call [reg+0xA0]` census returns 113 sites and slot 0xA0 is shared with unrelated interfaces). Until it is disassembled, the claim "capture bypasses the router" stays HYPOTHESIS, and so does the exact ordering of capture vs modal vs tree walk at stage 2.
- What schedules the absolute-rect recompute (slot 90, `0x0099DCE4`)? Slot 91 `0x0099BECC` sets `[this+0x70]`, slot 89 tests `[this+0x71]` — two dirty bytes, and which one gates the recompute (and whether it lands the same frame or the next) is unmeasured. This decides whether a window is clickable at its new position immediately after `GZWinMoveTo` + `InvalidateSelfAndParents`, or one frame later — i.e. whether there is a one-frame *click* gap analogous to the known one-frame paint flash (§7.2).
- Two window flags are read by the engine but absent from `cIGZWin.h`'s `tWinFlag` enum: `0x1000` (tested in real slot 131, `0x00999004`) and `0x4000000` (tested in real slot 124, `0x0099C4BF`/`0x0099C4F9`). Identify them before any future flag-based lever — `WinFlag_IgnoreMouse` was found the same way and turned out to be the cheapest input lever in the engine.
- Is `[this+0x64]` (the refined hit mask) ever non-null on a stock mayor-mode menu? `DS149` counted 0 in the disaster case, and §2.2.3 now proves the mask can only subtract from the coarse rect. If it is null everywhere outside the flyout pair, the whole gate-2 branch is dead weight in mayor mode and the `SelForce` lever can be retired from that scope. This needs a positive control — probe a window known to carry `WinFlag_MouseTrans` first, or the null means nothing.
- Are `cIGZWinMgr::DebugSetCaptureGadgetVisible`, `DebugSetFocusGadgetVisible` and `DebugDumpWindowList` live in the retail 1.1.641 build? If they are, they answer 'who holds capture/focus right now' and 'what is the full window list' with no hooks at all — the cheapest instrument in the whole input subsystem, and untried.
- The Win32 message coalescer at `0x0098CE30` drops redundant `WM_MOUSEMOVE` runs and appears to zero matched down/up pairs before the UI sees them. It was read in passing, not decoded. Worth finishing only if a lost-click or lost-drag symptom ever appears — it is upstream of everything in this section and would look exactly like a routing bug.

---

### 2.2 Input routing and hit-testing — how a click reaches a widget

This is the second of the two paths through the window tree (the first is the
paint path, §2.1/§7). It is entirely separate machinery: a window can be
painted perfectly and still be unreachable, and a window can be invisible and
still eat every click. Everything below is measured on `SimCity 4.exe`
**1.1.641.0 Steam**, ImageBase `0x400000`, offline (capstone 5.x); the vendor
header `vendor\gzcom-dll\gzcom-dll\include\cIGZWin.h` / `cIGZWinMgr.h` supplies
the *names*, the binary supplies the *slots*, and where the two disagree **the
binary wins** (§2.2.7).

---

#### 2.2.1 The five stages

| # | Stage | Where |
|---|---|---|
| 1 | Win32 message arrives at the canvas HWND; the framework drains and **coalesces** the queue | `cIGZCanvas::FlushInputMessageQueue`, `cIGZCanvasW32::AddWinProcFilter`; the coalescer at `0x0098CE30` peeks a batch into a 0x1C-byte-per-entry array and zeroes redundant `WM_MOUSEMOVE` runs before the UI sees them |
| 2 | The window manager picks a **target window** — capture, else modal, else the tree walk | `cIGZWinMgr::ProcessMouseMessage` / `GZGetCapture` / `DoModalWin` (§2.2.6) |
| 3 | The tree walk resolves cursor → deepest claiming window | **router** `0x0099DFA9` (§2.2.2) + **IsPointInMe** `0x0099C97C` (§2.2.3) |
| 4 | A `cGZMessage` is delivered to that window's `DoMessage` | **`0x0099CCF0`**, slot 3 `[vt+0x0C]` (§2.2.4) |
| 5 | `DoMessage` runs the filter chain, then dispatches to the `GZOn*` handler; the handler notifies its controller | §2.2.4, `SetNotificationTarget` (slot 86) → `GZOnCommand` (slot 142) |

⛔ **Stages 3 and 4 are independent.** Stage 3 decides *which* window; stage 4
decides *what happens*. Almost every input bug in this project has been a
stage-3 bug misdiagnosed as stage 4 — see the failure table in §2.2.8.

---

#### 2.2.2 The router — `GetChildWindowFromCursorPoint` `0x0099DFA9`

Inherited by ~90 classes; slot **40** `[vt+0xA0]`; `ret 8` (2 args, x and y).

```
esi = [this+0x44]                 ; the child-list object
inc [esi+4]                       ; AddRef the LIST for the whole walk
edi = [esi]                       ; sentinel node
ebx = [edi]                       ; first node        ] circular doubly-linked
  child = [ebx+8]                                     ] list, walked HEAD-FORWARD
  if (!child->GetFlag(1))            continue         ; slot 67 [vt+0x10C]
  if ( child->GetFlag(0x200000))     continue         ; IgnoreMouse
  hit = child->[vt+0xA0](x,y)                         ; RECURSE, same virtual
  if (hit) { result = hit; break }                    ; FIRST CLAIM WINS
  ebx = [ebx]                       ; next
call 0x0099D3D2(esi)              ; release the list
if (!result && this->[vt+0xF8](x,y)) result = this    ; fall back to self
return result                     ; a cIGZWin*, not a bool
```

Facts that follow, each of which has cost or saved a session:

| Fact | Evidence |
|---|---|
| **First-claim-wins ⇒ a closed upstream gate STARVES every downstream hook.** Silence in a downstream hook is not evidence the hook is wrong | already law (`HANDOFF-god-mode-flyouts.md` "RESOLVED GATE"); the router disassembly above is the mechanism |
| **Router order == `EnumChildren` order, element for element.** `EnumChildren` `0x0099D708` walks the *same* `[this+0x44]` list from the same sentinel in the same direction with the same AddRef/release pair (`inc [edi+4]` @`0x0099D725`, `call 0x0099D3D2`) | NEW. Combined with §1.3 (enumeration is **reverse of `.UI` sibling order**, and `.UI` order is paint order, first-painted-behind) this closes the loop: **the router walks topmost-first, and the first window in any tree dump that covers the point is the one that gets the click**. `UiSpike.cpp` L7696 already labels its `DCKIDS` dump "router order, first claim wins" — that labelling is now proven, not assumed |
| The router **recurses through the same virtual** (`[vt+0xA0]`), so one class override anywhere in a subtree hijacks routing for everything under it | NEW; `0x0099DFF8` |
| The router **AddRefs the child list** across the walk, so a hook that adds or removes children mid-walk will not free the list under the iterator | NEW; `inc [esi+4]` @`0x0099DFB8` / `call 0x0099D3D2` @`0x0099E00F` |
| ⛔ **The router does NOT test `WinFlag_Enabled` (0x2).** A disabled window claims the point exactly like an enabled one; only its handler declines. "Greyed out but still eats the click" is therefore normal engine behaviour, not a bug to hunt | NEW (the only two `GetFlag` calls in the walk are `1` and `0x200000`) |
| The point is **absolute screen pixels at every level** — the router passes `(x,y)` to children unchanged, and the coarse test is against the window's *absolute* rect cache (§2.2.5). There is no per-level re-basing | NEW; resolves the "is this parent-local?" question that cost the v2.11.17 field-dump session |

---

#### 2.2.3 The two-gate hit model — `IsPointInMe` `0x0099C97C`, slot 62 `[vt+0xF8]`

```
bl = cRZRect::Contains(&this[0x14], x, y)        ; 0x00664C60 - GATE 1 (coarse)
if (this->GetFlag(0x80000) && bl) {              ; MouseTrans AND gate 1 passed
    this->[vt+0xEC](&x,&y)                       ; slot 59: screen -> window-LOCAL
    bl = !this->[vt+0x254](x,y)                  ; GATE 2 (refined mask), INVERTED
}
return bl                                        ; ret 8
```

| Fact | Evidence |
|---|---|
| ⛔ **Gate 2 can only SUBTRACT from gate 1, never add.** The `test bl,bl; je` at `0x0099C9A9` means the mask runs only when the coarse rect already contained the point. Widening a hit region by touching the mask is impossible; widen the rect | NEW |
| The coordinate handed to the mask is **window-local**, produced by slot 59 subtracting the window's absolute origin | NEW (§2.2.7 — and note slot 59 is `ScreenToWindowCoordinates`, *not* what our docs call it) |
| `cRZRect::Contains` `0x00664C60` is **half-open**: `L <= x < R && T <= y < B` (`jge` fails on R and B). A window of width W claims `[L, L+W)` | NEW. Two siblings sharing an edge never overlap — and a 1-px rounding divergence at 1.5x opens a 1-px dead column rather than a double-claim (relevant to open task #75) |
| Gate 2 dispatcher `0x0099BBBE` (slot 149 `[vt+0x254]`): `if (!this[0x64]) fail; if (!mask->[+0x60]) fail; mask->[+0x18](0x800) /*lock*/; r = mask->[+0x64](x,y); mask->[+0x1C](0x800) /*unlock*/; return r`. Result inverted by `neg bl; sbb bl,bl; inc bl` ⇒ **0 = opaque = clickable** | extends the existing §2.2 line with the lock flag `0x800` and the null-guard order |
| **Slot 149 has exactly two call sites in the whole `.text`** — `0x0099C94A` and `0x0099C9C9` (the second is inside `IsPointInMe` itself). Nothing else in the game consumes the mask, so forcing slot 149 (`SelForce`) is a *complete* override of refined hit-testing, not a partial one | NEW. **Positive control for this null:** the same scanner found 91 `.rdata` vtable slots holding `0x0099C97C`, 36 call sites for `[vt+0x168]` and 71 for `[vt+0x16C]`, so it demonstrably finds both vtable entries and `call [reg+disp32]` sites. **Caveat:** it covers six of the eight ModRM register forms (all but the `esp`/SIB and `ebp` encodings); a call through those two forms would be missed |
| Classes MAY override slot 62. The flyout container's `0x0079A180` tail-calls its slot 121 `0x0079AE30`, which claims only `local_x >= width − [this+0xE0]` | already documented (§2.1); repeated here only as the canonical example of "read the vtable first" |

---

#### 2.2.4 The message funnel — `cRZWin::DoMessage` `0x0099CCF0`, slot 3 `[vt+0x0C]`

Once a target window is chosen, **everything** — mouse, keyboard, focus,
capture, commands — arrives through this one function. NEW; not previously
documented anywhere in this project.

```
[this+0x88] = message-filter list      ; walked first, head-forward
    for each filter: swallowed |= filter->DoMessage(this, msg)   ; [filter_vt+0x0C]
    if (swallowed) return true                                   ; NO handler runs
saved = [this+0x90]; [this+0x90] = 1   ; re-entrancy / "in message" guard
switch (msg->type - 1)                 ; bounds cmp 0x13, jump table @ 0x0099CEF9
```

⛔ **`cIGZWinMessageFilter` is the highest-priority input hook in the engine.**
It is registered per-window with `AddMessageFilter` (slot 115) and it runs
*before* the window's own handler, so a filter that returns `true` makes the
window look dead while the router still routes to it. If a stock window stops
responding after a mod loads, this is the first thing to check —
`vendor\gzcom-dll\...\cIGZWinMessageFilter.h`, and the walk at `0x0099CD18`.

**The message table** (jump table `0x0099CEF9`, 20 entries; ids **2, 9, 12, 15
are unhandled** and return false):

| msg id | → slot | arity | Meaning |
|---|---|---|---|
| 1 | 16 `[vt+0x40]` | 1 | child-delete notification |
| 3 | 143 `[vt+0x23C]` | 2 | — |
| 4 | 129 `[vt+0x204]` | 1 (int8) | `GZOnCharacter` |
| 5 | 130 `[vt+0x208]` | 2 | `GZOnKeyDown` — first consults the key accelerator `[this+0x78]` |
| 6 | 131 `[vt+0x20C]` | 2 | `GZOnKeyUp` — on decline, falls back to `AccelerateKeyboardMsg` slot 77 `[vt+0x134]` |
| **7, 8, 10, 11, 13** | **134..138** `[vt+0x218..0x228]` | **3 each** | **the five mouse position handlers** (x, y, flags) |
| 14 | 139 `[vt+0x22C]` | 4 | `GZOnCaptureChanged` |
| 16 | 133 `[vt+0x214]` | 1 | focus handler |
| 17 | 132 `[vt+0x210]` | 1 | focus handler |
| 18 | 140 `[vt+0x230]` | 2 | `GZOnMouseEnter` |
| 19 | 141 `[vt+0x234]` | 1 | `GZOnMouseExit` |
| 20 | 142 `[vt+0x238]` | 1 | `GZOnCommand` |

**`cGZMessage` field layout on the mouse path** (NEW, read off the dispatcher
at `0x0099CD57`, `0x0099CDE9`, `0x0099CE61`):

| offset | read as | meaning |
|---|---|---|
| `+0x00` | `dword` | message type |
| `+0x04` | **`movsx word`** | cursor **x** (signed 16-bit) |
| `+0x08` | **`movsx word`** | cursor **y** (signed 16-bit) |
| `+0x0C` | `movsx word` | wheel delta |
| `+0x0E` | `movzx word` | key / button flags |

The same `+0x04`/`+0x08` dwords carry **pointers** for the non-mouse ids
(`push [edi+4]` at `0x0099CE8F`, `0x0099CE9C`, `0x0099CEBC`) — the fields are
overloaded by message type. ⛔ A hook that reads `+0x04` as a dword on a mouse
message gets `y<<16 | x`, which looks like a plausible pointer and is not.

⚠ The engine exposes only **five** 3-arg mouse handlers (slots 134..138) where
`cIGZWin.h` names **six** (`GZOnMouseDownL/DownR/UpL/UpR/Move/Wheel`). Which
name has no slot of its own is **an open question** — resolve it by logging
`msg->type` inside a `DoMessage` hook on a button while clicking, not by
counting the header.

---

#### 2.2.5 ⛔ THE TWO RECTS — why a scaled window's hit region disagrees with its drawn region

This is the single most useful thing in this section. Every "draws right, eats
clicks" symptom we have ever seen reduces to it.

| rect | offsets | who writes it | who reads it |
|---|---|---|---|
| **parent-relative rect** | `[this+0xA8..0xB4]` = (L,T,R,B) | `.UI area=`, `SetArea` (slot 55 `0x0099C837`), `SetW`/`SetH`, `GZWinMoveTo` (slot 56 `0x0099C8C5`) — **and every scaling write this project makes** | `GetL 0x0099BC53` (`[0xA8]`), `GetW 0x0099C81B` (`[0xB0]−[0xA8]`), `GetH 0x0099C82A` (`[0xB4]−[0xAC]`), the layout/draw path |
| **absolute rect CACHE** | `[this+0x14..0x20]` | **only** the recursive zero-arg **slot 90 `[vt+0x168]` = `0x0099DCE4`** | **the hit test** — `IsPointInMe`'s `cRZRect::Contains(&this[0x14],…)`; also slot 60 `[vt+0xF0]` (local→screen) and slot 59 `[vt+0xEC]` (screen→local), which add/subtract `[0x14]`,`[0x18]` |

`0x0099DCE4` in full: copy `GetArea()` (`[vt+0xC0]`, the `[0xA8]` rect) into
locals → walk the parent chain via `GetParentWin` (`[vt+0x2C]`) adding each
ancestor's `GetL` (`[vt+0xAC]`) to L,R and `GetT` (`[vt+0xB0]`) to T,B →
`movsd`×4 into `[this+0x14]` (`0x0099DD35`) → AddRef `[this+0x44]` and
**recurse into every child** through the same slot (`0x0099DD55`).

`GZWinMoveTo` is literally `SetArea(l+dx, t+dy, r+dx, b+dy)` — it tail-calls
slot 55 through `[vt+0xDC]` at `0x0099C8EB`. `SetArea` writes the four dwords
at `[0xA8..0xB4]` and **nothing else** (`0x0099C881`–`0x0099C893`).

> ⛔ **LAW — MOVE THE WINDOW, THEN MAKE THE ENGINE RECOMPUTE.** `SetArea`,
> `SetW`/`SetH` and `GZWinMoveTo` update only the parent-relative rect. Until
> slot 90 runs on that window *or on any ancestor*, the window **paints at its
> new place and hit-tests at its old one**. This is the mechanism behind
> §1.4's "`InvalidateSelfAndParents()` is the ONLY safe repaint primitive after
> a geometry change" — the rule is not merely cosmetic, it is what keeps the
> click region attached to the pixels.

**Trigger — HYPOTHESIS, do not promote without measuring.** Slot 91
`[vt+0x16C]` = `0x0099BECC` is one instruction, `mov byte [ecx+0x70],1; ret`,
and slot 89 tests a second byte `[this+0x71]`. Which of the two dirty bytes
schedules slot 90, and whether it happens the same frame or the next, is
**unmeasured**. What *is* measured is that slot 90 has 36 call sites in
`.text` and is recursive, so a recompute on a root fixes an entire subtree.

---

#### 2.2.6 Flags — what the router and the hit test actually read

Names from `vendor\gzcom-dll\...\cIGZWin.h` `tWinFlag`; behaviour measured.

| flag | SDK name | read by | effect on input |
|---|---|---|---|
| `0x1` | `WinFlag_Visible` | router `0x0099DFCF` | not visible ⇒ **skipped**, subtree unreachable |
| `0x2` | `WinFlag_Enabled` | *not read by the router* | **no effect on routing** — a disabled window still claims |
| `0x80000` | `WinFlag_MouseTrans` | `IsPointInMe` `0x0099C99F` | selects the refined-mask branch (§2.2.3) |
| `0x200000` | `WinFlag_IgnoreMouse` | router `0x0099DFE3` | ⛔ router **skips the window entirely, subtree and all** — the cheapest "get out of the way" lever, still unused in shipped code |
| `0x800` | `WinFlag_Sortable` | `SortChildren` (slot 33) | ordering ⇒ z-order ⇒ claim priority (§2.2.2) |
| `0x8000` | `WinFlag_AcceptFocus` | focus path | keyboard target eligibility |
| `0x1000` | **not in the SDK enum** | real slot 131 (`GZOnKeyUp` path) `0x00999004` | unknown — flagged for the next reader |
| `0x4000000` | **not in the SDK enum** | real slot 124 `0x0099C4BF`, `0x0099C4F9` | unknown |

Our §1.4 row calls `0x200000` "input-transparent". Keep the description, add
the real name — a reader grepping the vendor headers for "input-transparent"
finds nothing, and `WinFlag_IgnoreMouse` is what is actually there.

---

#### 2.2.7 ⛔ NEVER DERIVE A SLOT INDEX BY COUNTING `cIGZWin.h`

`vendor\gzcom-dll` is a community reconstruction. Counting its virtuals gives
the **right** answer for the router (40), the coordinate transforms (59, 60,
61), `GetFlag`-adjacent geometry (§1.4's confirmed list) and `Plot` (88) — and
the **wrong** answer through the whole hit-test and input band.

Measured anchors (all from the base window vtable, cross-checked against three
class vtables `0x00AB7358` cSC4WinGenTransparent, `0x00ADF6A0` GZWinBMP,
`0x00AB6AA8` flyout container):

| real slot | `[vt+…]` | function | how identified |
|---|---|---|---|
| 62 | `0xF8` | **`IsPointInMe`** `0x0099C97C` | the router's own fallback call; **the header has no such method at all** — its index 62 is `GetID` |
| 63 | `0xFC` | `GetID` | `mov eax,[ecx+0x10]; ret` |
| 67 | `0x10C` | `GetFlag` | `eax = [ecx+0xC8] & arg` — and `UiSpike.cpp` L7703 already uses `vt[67]`, i.e. the shipped code is right and the header is not |
| 71 / 72 | `0x11C` / `0x120` | `IsVisible` / `IsEnabled` | `GetFlag(1)` / `GetFlag(2)` |
| 86 / 87 | `0x158` / `0x15C` | `SetNotificationTarget` / `GetNotificationTarget` | paired setter/getter on `[this+0x4C]` (`0x0099BE42` / `0x0099BE4C`) |
| 88 | `0x160` | **`Plot`** | five independently documented class overrides all land here: `0x0079B0E0`, `0x0079AA70`, `0x009BC325`, `0x00949ADE`, `0x007A9500`, `0x007BF0A0` |
| 90 | `0x168` | **absolute-rect recompute** `0x0099DCE4` | writes `[this+0x14..0x20]`, recurses (§2.2.5) |
| 121 | `0x1E4` | container claim helper | `0x0079AE30` |
| 134..138 | `0x218..0x228` | the five 3-arg mouse handlers | `DoMessage` dispatch (§2.2.4) |
| 139 | `0x22C` | `GZOnCaptureChanged` | 4 args, `ret 0x10` |
| 149 | `0x254` | refined-mask dispatcher `0x0099BBBE` | **past the end of `cIGZWin`** (the header's last index is 146 `[vt+0x248]`) — it is a derived-class vtable extension |

> ⛔ **THE CHEAP CHECK: read the `ret` immediate.** `__thiscall` is
> callee-cleanup, so `ret N` states the argument count exactly: a 3-arg mouse
> handler must be `ret 0xC`, a 2-arg point test `ret 8`, `GZOnCaptureChanged`
> `ret 0x10`. Real slot 133 is `xor al,al; ret 4` — **one** argument — which is
> precisely why hooking "slot 133 = `GZOnMouseDownL`" from the header corrupted
> the stack and crashed the game (`UiSpike.cpp` L160). One `disasm` line would
> have caught it. Do this before every vtable hook, without exception.

**vtable scan technique** (unchanged, still the right tool): search the exe
image for a function's little-endian address; each hit inside `.rdata` is a
vtable slot, and `VA − slot*4` is the vtable base.

---

#### 2.2.8 Failure signatures we have actually seen, and the ONE measurement that separates them

| Symptom | Cause | The diagnostic that proves it |
|---|---|---|
| **Draws right, eats clicks in part of its area** (disaster flyout: only the rightmost ~36px of an 88px picture column clicked) | a **custom claim override** whose width field is still 1x. Container `[0xE0]` held 49 while the draw was 2x: `288 − 49 = 239` = exactly the user-measured threshold | Read the class vtable slot 62. If it is **not** `0x0099C97C`, disassemble the override — six instructions beat six hours (`GOD-MODE-FLYOUTS.md` playbook). `DCLAIM` logs the fix |
| **Draws right, eats clicks everywhere; no override in sight** | the **stale absolute rect** (§2.2.5) — geometry was written to `[0xA8]`, `[0x14]` was never recomputed | Log `GetL/GetT/GetW/GetH` (the `[0xA8]` rect) **and** dump `[this+0x14..0x20]` in the same line. Equal ⇒ not this; different by exactly the move delta ⇒ this |
| **Downstream hook is completely silent** | an **upstream gate**, not a broken hook. First-claim-wins starves everything below | Hook the *parent's* slot 62 as well. `DS149 count = 0` while `DS62` fires means the gate is above, not at the mask (the v2.11.16–18 sequence) |
| **Click lands on the wrong sibling / the right window never sees it** | a sibling **earlier in router order** (= later in add order = drawn on top) covers the point | The `DGPKID` / `DCKID` dumps with the `**OVER-DEAD-BAND**` marker (`UiSpike.cpp` L7678/L7718). A live example is in the shipped log: `DGPKID 4 id=6A5E44B6 L=0 T=0 W=2400 H=1600 vis=1 **OVER-DEAD-BAND**` — a full-screen visible sibling. Because `EnumChildren` order **is** router order (§2.2.2), the dump index *is* the priority |
| **Window looks dead, routing is provably correct** | a **message filter** swallowing at stage 5 (§2.2.4) | Hook `DoMessage` `[vt+0x0C]` on the window and log `msg->type`. Messages arriving but no handler firing ⇒ the filter chain at `[this+0x88]` |
| **Crash on installing a click hook** | wrong argument count on the thunk | `ret` immediate (§2.2.7) |
| **Right class, wrong window → native death** | class identity is necessary, not sufficient | the known-menu gate; `SUBSKIP` logs the decline (§2.1) |

**The decision procedure, in order** — each step is cheap and rules out a whole
family:

1. Is the window in the tree dump *at all*, and where in the sibling order?
   (`EnumChildren` = router order.) Anything earlier that covers the point wins.
2. Do the `[0xA8]` rect and the `[0x14]` rect agree? If not, stop — it is
   §2.2.5, and no amount of hooking will fix it.
3. Is slot 62 the base `0x0099C97C`? If not, disassemble the override.
4. Is `WinFlag_MouseTrans` set? If yes the mask is in play; if no, `SelForce`
   and every mask theory are irrelevant.
5. Only now hook a handler — and check the `ret` immediate first.

---

#### 2.2.9 Capture, focus and modal — the parts we have NOT measured

`cIGZWinMgr` (vendor header) exposes `GZSetCapture` / `GZGetCapture` /
`GZReleaseCapture`, `GZSetFocus` / `GZGetFocus`, `SetCurrentMouseWin`,
`DoModalWin` / `IsModal` / `GetModalNestCount`, and `IsWindowValid` /
`AddWindowToValidList`. Measured on our side: capture changes are delivered as
**message id 14 → slot 139 `GZOnCaptureChanged`** with four arguments
(`pWin`, a dword, a `uint16`, an `int16`), and enter/exit as ids **18/19**.

**HYPOTHESIS (not measured — `cRZWinMgr::ProcessMouseMessage` was not located
this session):** while capture is held, the manager delivers to the capture
window *instead of* running the router, which is why a drag that starts on a
scrollbar keeps working once the cursor leaves it. Do not build on this until
someone disassembles the manager.

Three **free instruments** nobody has used yet, already in the shipped exe via
`cIGZWinMgr`: `DebugSetCaptureGadgetVisible`, `DebugSetFocusGadgetVisible` and
`DebugDumpWindowList`. If they are live in the retail build they answer "who
holds capture / focus right now" without a single hook. Worth ten minutes
before the next input session.

---

*(Companion edits: §1.4's flags row gains the real SDK names and a pointer to
§2.2.6; §8.1 gains `0x0099CCF0` `cRZWin::DoMessage`, `0x0099D708`
`EnumChildren`, `0x0099DCE4` absolute-rect recompute, `0x00664C60`
`cRZRect::Contains`, `0x0099C837` `SetArea`, `0x0099C8C5` `GZWinMoveTo`, and
corrects the `0x0099BE4C` row; §9 gains the four contradiction entries.)*
