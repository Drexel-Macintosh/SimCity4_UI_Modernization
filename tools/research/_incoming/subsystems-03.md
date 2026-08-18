# TARGET: tools\research\SC4-UI-ENGINE.md — new §11 "Transients, dialogs and modality" (the file currently ends at §10). Secondary inserts: §1.1 (host table), §1.3 (z-order), §3.1 (token table), §8.5 (VAs); plus _tests\REGRESSION.md "LAWS MINTED" 34-36 and one README LAWS bullet.

## SUMMARY
Decoded the transient/dialog subsystem end to end. NEW: the seven-step code-driven dialog protocol with VAs (WinMgr accessor 0x913C46, .UI factory 0x5F9390 via cIGZUIScriptService, PullToFront-at-birth, the placement formula x=(pw-w)/2 y=(ph-h)/3 confirmed to the pixel against a live log line, DoModalWin at WinMgr vt+0xA4, DestroyWindow at +0x5C, and the engine's own IsWindowValid re-check at +0x60 that the game performs on every saved window pointer after a modal). NEW: two DISTINCT transient lifecycles — main-window transients are unparented on close (measured: they vanish from the child list), view-parented transients persist hidden and ACCUMULATE (measured: six live copies of 0x4C30E4FA at once). NEW: z-order is mutable at runtime (tip layer migrates to index 0 on first tip show and stays). NEW: DLL-provided window classes carry vtables outside the exe image, silently defeating our `vt == 0x00ADF6A0` equality tests. NEW: the .UI token table decoded (id=0x100, area=0x101, plus unused pos=/size=), and `iid=`/`clsid=` are tokens -2/-1. CORRECTED: 0x2AAB8CC1 is not "the" tooltip layer — 1 to 3 live windows share that id. FOUND BUG: the kCityDialogIds block re-reads live L/T instead of rec.origL/origT, so a re-shown dialog drifts by a fixed delta per open. The pointer rule: a cIGZWin* is safe as a MAP KEY within the tick that enumerated it, never as a stored HANDLE; identity by id alone is insufficient and IsWindowValid is the engine's own contract.

## CONTRADICTIONS
- SC4-UI-ENGINE.md §1.1 calls 0x2AAB8CC1 "the tooltip layer" (singular, "on the region screen it exists but is empty and hidden"). CORRECTED: it is a CLASS, not an instance — three live windows shared that id on 2026-07-31 11:08 (one main-window child at vis=0 plus VWKID 41 and 42 under the 3D view, both vt=00AB6770, both visible), and one in the 11:15 session (11:17:11.533 VWKID 8). The count is state-dependent, so no code may hold "the" tip layer.
- SC4-UI-ENGINE.md §1.3 point 1 presents z-order as a static consequence of .UI add order ("the dock paints on top of the composite"). EXTENDED/CORRECTED: add order fixes only the INITIAL order. Every code-built dialog calls PullToFront at birth (0x78E0A2), and the tip layer migrates from index 1 to index 0 on its first show and stays there after hiding (11:16:19.364 vs 11:16:40.241 vs 11:16:40.866, current log). Only 27 of 5,964 corpus nodes are winflag_sortable=yes, so outside those the order is add-order plus explicit raises.
- SC4-UI-ENGINE.md §8.5 lists "0x778245 dialog factory (instantiates the Delete-City confirm script)". CORRECTED: 0x778245 is a CALLER. The factory is 0x5F9390 — it acquires cIGZUIScriptService (clsid 0x5A356E15 / IID 0xFA3562FA, matching GZServPtrs.h:46) and calls its vt+0x10 with (resourceKey, parentWin, rootWinId).
- UiSpike.cpp L8015 asserts the in-city quit/exit boxes "are modal popups" — written as an assumption. NOW MEASURED: the builders call cIGZWinMgr::DoModalWin (vt +0xA4) and test its int32 result (0x4F2668, 0x791433, 0x78E24D). The assumption was correct; it is no longer an assumption.
- SC4-UI-ENGINE.md §1.2's table entry "Under the main window → Static 2x .UI" reads as an absolute. It needs the qualifier the source already carries (UiSpike.cpp L8016-L8020, L8027-L8032): several main-window transients are built through a code path that BYPASSES the DBPF override, so for those the runtime per-instance pass is the only lever that works, and the static entry is inert. 0xAA921F4F is the live proof — it still arrives at 270x162 design size and is scaled at runtime every open (11:17:58.155).
- DEFECT, not a doc contradiction: the kCityDialogIds block writes rec.origL/origT (UiSpike.cpp L8206) and then never reads them. It re-derives the anchor from the LIVE position (L8168, L8191), unlike ScalePanelRoot which restores prev.origL/origT on ResetToOriginal (L7846-L7856). DialogDockTick has the same shape (L8789). Consequence measured 2026-07-31 11:10 (log since rotated): the quit confirm's second open scaled from (930,398) instead of the game's (1065,479) — a fixed -135,-81 drift per reopen.
- HANDOFF-god-mode-flyouts.md L1086-L1103 proposes hooking cIGZWinMgr's GetWindowFromPoint / cursor tracker for the hit-test work but had no cheap way to reach the manager. 0x913C46 / [0xB628C0] is that way, and cIGZWin::GetWindowManager() (vt +0x18) is another — available from any window we already hold.

## OPEN
- Is cIGZWin::GetInstanceID() (vt +0x100) populated for ordinary windows? NOT MEASURED — stated as a null with its positive control, not as a fact. The .UI `iid=` hypothesis is disproved (iid is token -2 and holds an interface NAME; the one SetInstanceID-shaped call in the deserializer, 0x954C2E, is fed by token 0x1336 = 'rowheight' on a QI'd file-list interface, not a cIGZWin*). Cheapest probe: add iid=%08X to the MWKID/VWKID/DGPKID format strings. If distinct and non-zero, the whole non-unique-id problem and §3.6's rect-matching hack both retire.
- What class is [0xB43CE0]? It is cached at 0x602336 from [0xB43C94]->vt[0xAC](), and its +0x28(win,bool) / +0x18(win) bracket every DoModalWin call site (0x78E236/0x78E25E, 0x4F265E/0x4F2677, 0x455245). Functionally a show/hide-plus-modal-veil manager; identity unproven. Resolve by disassembling the master at [0xB43C94] or by finding the vtable's QueryInterface IID.
- Are the registered-but-unused .UI tokens `pos` (0x102) and `size` (0x103) actually consumed by a handler, or registered and dead like the string-valued font= path (§3.4)? A one-script generator experiment settles it. If live, build_dialog_static.py can emit pos/size directly and skip the corner-vs-extent conversion.
- Why exactly six instances of 0x4C30E4FA? Leak-per-open, a fixed pool sized by the empty-state row count, or one-per-department? Instrument: log the count on every DGPKID dump across a session that opens Business Deals N times. This decides whether any per-instance treatment is bounded.
- How many transients are re-shown (position preserved) vs destroyed-and-recreated? Measured: 0xAA921F4F preserves position across opens; 0x6A243D9E opens at an identical (400,200 868x762) eight times running, which is consistent with either a fixed absolute area= or a persistent object. cISLWinLocationSaver.h exists in the SDK headers and is a third possible mechanism. Distinguishing probe: log the window POINTER (not just the vtable) in MWKID — currently only vt=%p is printed, which cannot tell two instances of the same class apart.
- Does the .UI-supplied absolute area= for a main-window root override the (pw-w)/2, (ph-h)/3 placement, or does the code move it afterwards? 0x6A243D9E at (400,200) does not match the formula for 868x762 ((2400-868)/2 = 766), so at least one of the two paths ignores it. Needed before any static-dat position edit on a main-window transient.

---

# §11. Transients, dialogs and modality

> The subsystem that has surprised this project more than any other. Everything
> below is measured on 1.1.641.0 Steam unless marked `HYPOTHESIS`. Where a log
> line is cited, note that `SC4UIScale.log` is **truncated at every launch** —
> the citation names the session that produced it, and the re-test that
> reproduces it.

## 11.1 There are TWO transient lifecycles, and they are opposites

The single most useful question about a window that "appeared from nowhere" is
not what class it is — it is **which list it lives in**.

| | **Main-window transient** | **View-parented transient** |
|---|---|---|
| Parent | main window, or the app frame `0x6104489A` | the 3D view `0x9A47B417` |
| On close | **unparented — it leaves the child list entirely** | **stays in the list, `vis=0`** |
| On reopen | re-added at the FRONT of the list | shown again in place |
| Instances | 1 at a time (observed) | **accumulates — 6 observed** |
| Reachable by the sweep | no (§1.2) | yes |
| Our lever | `kCityDialogIds` / `DialogDockTick`, per instance | the sweep, or `kNeverScaleIds` + static dat |

**EVIDENCE (unparenting).** `MWKID` prints **every** direct child of the main
window regardless of visibility — only the one-level-down sub-dump is gated on
`IsVisible()` (`src\UiSpike.cpp` L8259-L8270). So an id missing from the dump is
missing from the *list*, not merely hidden. Live session 2026-07-31 11:15:55:
steady state is exactly two entries (`0x2AAB8CC1`, `0x6104489A`); when the My
Sims picker opens the list becomes three with the picker at index 0
(`11:17:42.584 MWKID 0 id=0x6A243D9E vt=00ADC678 (400,200 868x762) vis=1`), and
between opens it is two again. Eight open/close cycles, 11:17:42→11:17:54.

**EVIDENCE (accumulation).** Same session, `DGPKID` dump of the 3D view's direct
children at `11:16:31.493`: 42 children, of which **six** are
`id=4C30E4FA L=0 T=0 W=136 H=100 vis=0` (indices 36-41), stable across every
subsequent dump. `0x4C30E4FA` is the Business Deals empty-state box, already in
`kCityDialogIds` with `designW 272` (`UiSpike.cpp` L8072). Six live windows, one
id, all hidden, all at the origin at **1x** size — i.e. `IsVisible()` plus a
single `GetChildWindowFromIDRecursive` finds one arbitrary member of a *pool*.

⛔ **Operational rule.** For a main-window transient, "closed" means *gone*: a
cached pointer, a cached child index, or a `dialogDocked[i]` style latch is stale
the moment the box closes. For a view-parented transient, "closed" means
*hidden and still there*, and the id may name any of N siblings — always iterate
(`IdCollectCtx`, `UiSpike.cpp` L5136-L5141), never single-find.

## 11.2 How a code-driven dialog is built — the seven-step protocol

Disassembled from the generic message-box builder `0x78DFF0` (§8.5 already names
it and its script `I-ea8cc3c6`; what follows is the protocol it runs). The same
idiom appears verbatim in at least three other builders — `0x4F2653`,
`0x791439`, `0x455240` — so it is the engine's house style, not one function's
quirk.

1. **Get the window manager.** `0x913C46` is a lazy singleton accessor caching
   into `[0xB628C0]`; the cold path is a `cRZSysServPtr` acquire. The
   `GetService` form is `push <IID>; push <clsid>` = `push 0xA417445E;
   push 0x5A4` (`0x78E024`-`0x78E02E`), which matches
   `cIGZWinMgrPtr` in `vendor\gzcom-dll\...\GZServPtrs.h:50`
   (`cRZSysServPtr<cIGZWinMgr, 1444ul, 2752988254ul>`).
   **EVIDENCE**: `0x913C46`-`0x913C71`; `0x78E01D`-`0x78E033`.
2. **Parent = `WinMgr->GetMainWindow()`** — vtable `+0x0C`, no arguments,
   result used directly as the parent handed to the factory.
   **EVIDENCE**: `0x78E037 mov edx,[ecx] / 0x78E039 call [edx+0xc]`, result in
   `edi`, pushed to the factory at `0x78E05A`. *This is the mechanism behind
   §1.2's parentage rule: a code-driven box is main-window-parented **by
   construction**, never by accident.*
3. **Save the focus.** `WinMgr->GZGetFocus()` (vt `+0x90`, no args) is stashed
   before the box is built. **EVIDENCE**: `0x78E04B call [eax+0x90]`, stored to
   `[esp+0x2c]`, consumed at step 7.
4. **Instantiate the `.UI`.** `0x5F9390` = the `.UI` script instantiation
   entry point. It acquires **`cIGZUIScriptService`** (`push 0xFA3562FA;
   push 0x5A356E15`, matching `cIGZUIScriptServicePtr`, `GZServPtrs.h:46`) and
   calls its vt `+0x10` with `(key, parentWin, rootWinId)` → `cIGZWin*`.
   The caller fills the key inline: `[esp+0x3c]=0x96A006B0` (group),
   `[esp+0x40]=0xEA8CC3C6` (instance), and pushes `0x8A8DFCF5` as the root id.
   **EVIDENCE**: `0x5F9390`-`0x5F93E1`; caller `0x78E064`-`0x78E079`.
   *This generalises §8.5's "`0x778245` dialog factory": `0x778245` is one
   caller; `0x5F9390` is the factory.*
5. **`pDlg->PullToFront()`** — `cIGZWin` vt `+0x5C`. Every code-built dialog
   raises itself at birth. **EVIDENCE**: `0x78E0A2 call [edx+0x5c]` on the
   just-created window.
6. **Place it, then show it** (§11.3), then `[0xB43CE0]->vt[0x28](pDlg, true)`.
   **EVIDENCE**: `0x78E236`-`0x78E241`; identical at `0x4F265B` and `0x455242`.
   `[0xB43CE0]` is one of a table of sub-services cached at `0x6022E0`-`0x60234E`
   from a master at `[0xB43C94]` (slot `+0xAC`). `HYPOTHESIS`: an SC4-level
   window/veil manager; its `+0x28(win,bool)` shows and its `+0x18(win)` hides.
   Identity `[OPEN]`.
7. **Run it modally, then tear down** (§11.4, §11.7).

## 11.3 Placement: centre horizontally, ONE THIRD vertically — then content-fit

```
x = (parentW - w) / 2          ; signed /2  (cdq; sub; sar 1)
y = (parentH - h) / 3          ; signed /3  (imul 0x55555556; shr 31; add)
pDlg->GZWinMoveTo(x, y)        ; cIGZWin vt +0xE0
```

**EVIDENCE (code)**: `0x78E0A5`-`0x78E0F0`. `GetH` = vt `+0xA8`, `GetW` = vt
`+0xA4`, `GZWinMoveTo` = vt `+0xE0`; the `push eax` at `0x78E0CF` is the *y*
argument pushed early, with two zero-argument getters evaluated between the two
pushes.

**EVIDENCE (live, to the pixel)**: 2026-07-31 `11:17:58.155`
`UiSpike: in-city dialog 0xAA921F4F scaled (1065,479 270x162) -> 540x324`.
Frame 2400x1600: `(2400-270)/2 = 1065` ✓, `(1600-162)/3 = 479.33 → 479` ✓.

Two consequences worth more than the formula:

- **It re-confirms the relative-move law from a second direction.** `GZWinMoveTo`
  moves *by*, not *to* (§1.4); the game's absolute result is only correct because
  the freshly-created window is still at (0,0). Any code that moves a window and
  then lets the game "re-place" it will compound.
- **PLACEMENT-THEN-FIT.** The position is computed once, at creation, from the
  size the window has *then*; a later content-fit resize does **not** re-place
  it. Measured on the query/U-Drive-It transient `0x10000005` (session
  2026-07-31 11:08, log since rotated; re-test = open a query panel on two
  different subjects): two opens at the same `(492,404)`, sizes `584x386` then
  `584x668` — `(1600-386)/3 = 404` ✓ for the first, and the taller instance kept
  the shorter instance's y. **A tall dialog therefore hangs low by design, and
  "it moved" is not evidence that anything re-ran the placement.**

## 11.4 Destruction, and the engine's own liveness contract

```
WinMgr->DestroyWindow(pDlg)          ; vt +0x5C
if (WinMgr->IsWindowValid(prevFocus)) ; vt +0x60
    WinMgr->GZSetFocus(prevFocus)     ; vt +0x94
pDlg->Release()                       ; cIGZWin vt +0x08
owner->cachedPtr = nullptr
```

**EVIDENCE**: teardown tail `0x78E27D`-`0x78E2A8`, all four calls on the same
`edi` that took `DoModalWin` at `0x78E24D`. Independent confirmation of
`DestroyWindow` at `+0x5C` from an unrelated owner destructor at
`0x8AF356`-`0x8AF3A3`: `winMgr->vt[0x5C](this->[0x140]); this->[0x140] = 0;
pWin->Release()`.

**This is the headline.** `cIGZWinMgr` maintains a global **valid list** —
`AddWindowToValidList` (+0x50), `RemoveWindowFromValidList` (+0x54),
`CleanUpWindowReferences` (+0x58), `DestroyWindow` (+0x5C), `IsWindowValid`
(+0x60) — and **the game does not trust a saved `cIGZWin*` across a modal
without asking**. The `DoModalWin → IsWindowValid → act` sequence occurs at
`0x4F2668`/`0x4F2681`, `0x791433`/`0x79144C` and `0x78E24D`/`0x78E28E`.

⛔ **This project has never called any of them.** MEASURED NULL WITH POSITIVE
CONTROL: `grep -rn "IsWindowValid|ValidList|CleanUpWindowReferences|DoModalWin|
IsModal|GetModalNestCount|NotificationTarget|SetParam|GetParam|GetInstanceID"
src\ tools\research\*.md _tests\*.md` returns zero hits, while the same grep set
returns 88 hits for `GetID` in `UiSpike.cpp` alone and finds `GetPrivateBuffer`
in `GOD-MODE-FLYOUTS.md:207` — the instrument can see `cIGZWin` method names in
both the source and the docs, so the null is real. `Classify()`'s id-equality
eviction (`UiSpike.cpp` L4358-L4366) is a hand-rolled, weaker re-implementation
of a contract the engine already publishes.

**Slot map provenance.** `cIGZWinMgr` slot *n* sits at `4n`, counting the three
`cIGZUnknown` slots first, in `vendor\gzcom-dll\...\cIGZWinMgr.h` declaration
order (the two overloaded pairs occupy their slots in place, so they do not
shift the count). Four independent anchors confirm it in the binary:
`+0x0C GetMainWindow` (0-arg, returns the parent, `0x78E039`),
`+0x5C DestroyWindow` (`0x8AF38E`, followed by `Release`),
`+0x60 IsWindowValid` (1 arg, `test al,al`, `0x4F2681`),
`+0x94 GZSetFocus` (1 arg, `0x78E29E`). `DoModalWin` is bracketed by these at
`+0xA4`, `IsModal` at `+0xA8`, `GetModalNestCount` at `+0xAC`.
The `cIGZWin` map is anchored the same way: `+0x5C PullToFront`,
`+0xA4/+0xA8 GetW/GetH`, `+0xE0 GZWinMoveTo`, `+0x110/+0x114 ShowWindow/
HideWindow` (`0x8AF191`/`0x8AF072`), `+0xF8/+0xFC GetID/SetID`,
`+0x100/+0x104 GetInstanceID/SetInstanceID`.

## 11.5 The dialog list, and what an id actually promises

**There is no dialog registry.** "The dialog list" is just the main window's
child list — a stack, LIFO, steady-state depth 2. A dialog is `ChildAdd`ed at
open and unparented at close; `EnumChildren` returns children in reverse add
order (§1.3), so **the newest transient is always index 0**.

An id promises **nothing**:

- **It is not unique across the tree.** `0x2AAB8CC1` — which §1.1 calls "the
  tooltip layer" — was measured as **three** simultaneous live windows on
  2026-07-31 11:08 (one main-window child plus `VWKID 41` and `VWKID 42`, both
  `vt=00AB6770 (0,0 2400x1600)`, both visible), and as **one** in the 11:15
  session (`11:17:11.533 VWKID 8`). The *count is state-dependent*. §1.1 should
  say "the tooltip layer **class**"; there is no singular instance to hold onto.
- **It is not unique within one parent.** Six `0x4C30E4FA` (§11.1).
- **It is not unique across scripts.** Already recorded for `0xAA32BCE6` (§3.6)
  and `0x0BC3B559` (§1.3); the transient case is worse because the duplicates
  are *live at the same time*, so §3.6's rect-matching tie-breaker does not
  apply.
- **It does not survive a size change.** `0x10000005` is 386 tall on one open
  and 668 on the next (§11.3).
- **It does not identify a builder.** Law 16 already: one id, several code paths.
- **`id=0x00000000` is normal, not an error.** In the 330-script corpus,
  5,964 window nodes carry `clsid=`/`area=` but only 245 top-level `id=` tokens
  appear — anonymous children are the default, and the real disaster flyout root
  is one of them (`UiSpike.cpp` L7550-L7553).

There **is** a second identity field the engine exposes and we have never read:
`cIGZWin::GetInstanceID()` / `SetInstanceID()` (vt `+0x100`/`+0x104`).
`[OPEN] — NOT MEASURED`: whether it is populated for ordinary windows.
The obvious candidate — that the `.UI` `iid=` token feeds it — is **disproved**:
`iid` is registered as token **−2** and `clsid` as **−1** at `0x94D651`/
`0x94D689`, and both carry interface *names* (`IGZWinBMP`, `IGZWinBtn`,
`IGZWinCustom`). The only `SetInstanceID`-shaped call inside the deserializer
range, `0x954C2E`, is fed by token `0x1336` = `rowheight` on a QI'd file-list
interface, not a `cIGZWin*` — the same offset means different things on
different interfaces, which is itself a trap worth remembering.
**Cheapest possible probe**: add `iid=%08X` to the `MWKID`/`VWKID`/`DGPKID`
format strings. If it is non-zero and distinct, the whole non-unique-id problem
collapses to one call, and §3.6's rect-matching hack retires.

## 11.6 "Hidden template + open instance", concretely

The phrase means: for several `.UI`-backed panels the game keeps a **permanently
hidden window carrying the design geometry** in the tree, and creates or shows a
**second window with the same id** when the panel opens. The budget masters are
the recorded case — the hidden template measured 500x464 while the deployed
static data was 1000x404, which is how we proved the static override was being
bypassed (`UiSpike.cpp` L8053-L8061).

Three consequences, all paid for:

1. `GetChildWindowFromIDRecursive` returns the **last-added** match (§1.3), which
   in practice is the template — so `find + IsVisible()` skipped the real dialog
   on every pass for four builds. Cure: collect all matches (`IdCollectCtx`).
2. A template is *inside the swept tree* even when its instance is not, so the
   sweep can scale the template and leave the instance at 1x (or vice versa) —
   this is the same failure shape as the marker-composed panels in §3.6.
3. A pool (§11.1's six) is a template set, not a template. Any "the template"
   phrasing in a fix is a bug waiting.

## 11.7 Modality

`WinMgr->DoModalWin(pWin)` (vt `+0xA4`) **blocks and returns an `int32_t`
result**; `IsModal()` (+0xA8) and `GetModalNestCount()` (+0xAC) say that modals
**nest**. The comment at `UiSpike.cpp` L8015 ("These are modal popups") was an
assumption when written; it is now measured.

**The nested pump still drives our tick, and that is why runtime fixes work
inside a modal.** Our sweep is a Win32 `SetTimer(gameWindow, kTimerId, 16ms)`
plus a subclassed `WndProc` (`SC4UIScaleDllDirector.cpp` L376, L443) — a
message-driven tick, not a game-loop callback. `DoModalWin`'s pump keeps
dispatching to the game HWND, so `TickCheck` keeps firing.
**EVIDENCE**: `11:17:58.155` shows `in-city dialog 0xAA921F4F scaled` *and* the
`MWKID` dump of the same open box in the same millisecond — the tick ran with
the modal on screen.

Two corollaries: (a) a modal is not a reason to defer a fix; (b) because modals
nest, `GetModalNestCount()` is the correct gate for "are we inside anything
re-entrant", not a boolean of our own.

## 11.8 Z-order: dialogs vs HUD vs tip layer

§1.3 derives paint order from `.UI` add order. That is true **at birth only**;
the top-level order is mutated at runtime.

- **A code-built dialog raises itself at birth** — `PullToFront` at `0x78E0A2`
  — which is why it always appears at `MWKID` index 0.
- **The tip layer migrates and stays.** 2026-07-31 11:15 session:
  `11:16:19.364` app frame index 0 / tip layer index 1, tip `vis=0`. First tip
  show, `11:16:40.241`, tip layer is index 0 `vis=1`. It is **still** index 0
  at `11:16:40.866` with `vis=0`, and at every later dump. The raise is
  triggered by the show and is **sticky**.
  `HYPOTHESIS` for the call: `ChildToFront`/`PullToFront` on show.
- **Sorting is effectively off.** `winflag_sortable=yes` on **27 of 5,964**
  window nodes (0.45%) in the 330-script corpus — `I-aa1f1f57` (My Sims),
  `I-c973b411` (minimap dock + mode overlay), `I-2bc9060f`/`I-0b72f276` (Data
  Views), `I-6bc9065a` (Graphs) and six others. Everywhere else, z-order is
  purely add order plus explicit raises, so it is predictable — and where you
  see a `sortable` root, `SortChildren` may re-order under you.

So the standing order, bottom to top: HUD composite < dock < mode overlay
(§1.3, inside the app frame) < tip layer once any tip has shown < newest
transient. A transient opened while a tip is up outranks the tip; the next tip
show takes the crown back.

**A window painted by a mod is not identifiable by vtable equality.** Live
session 2026-07-31 11:16 carries three window classes whose vtables lie
**outside the exe image** (`0x400000`-`0xBC8000`): `vt=6F109328` on
`0x48E945B4` (128x128), plus `6F104E18` and `6F101F70` on two anonymous strips.
Our `DFG` path already adapts (`11:16:23.608 DFG patched class vt=6F109328
Plot=6F0B79A0 (idx 8)`), but every hard-coded comparison —
`kBmpClassVt = 0x00ADF6A0` (`UiSpike.cpp` L4868, used at L5098),
`0x00AB6AA8`/`0x00AB6D88` (L3546-L3548) — silently *no-ops* on a mod window.
That is a structural null, not a measurement: those paths cannot report what
they cannot see.

## 11.9 Lifecycle across city load, teardown and region↔city

`REGION-SWITCH.md` §1 already establishes that a live switch rebuilds the whole
view subtree, that every root comes back at a new address, and that the window
objects are recycled LIFO so a new window frequently lands on a dead one's
address. Three things it does **not** cover, all transient-specific:

- **Main-window transients are outside that rebuild.** They hang off the main
  window, not the view, so a city teardown neither destroys nor purges them —
  and `PurgeSubtreeRecords`, which only ever walks down from a Fresh *panel
  root*, can never reach their records. The dialog paths compensate with their
  own `PurgeSubtreeRecords(pDlg, 0)` on Fresh (`UiSpike.cpp` L8165, L8779).
- **A re-shown main-window transient keeps our geometry.** On the second open of
  `0xAA921F4F` the game restored the **design size** (270x162) but the window
  was at the position *we* had left it, not the formula's — so our own
  centre-clamp compounded. Measured 2026-07-31 11:10 (log since rotated;
  re-test: open the quit confirm twice in one sitting and read the two
  `in-city dialog … scaled (l,t …)` lines — the second `l,t` should equal the
  first, and does not).
  **The mechanism is in our source and is permanent**: the `kCityDialogIds`
  block reads `const int32_t l = pDlg->GetL();` (L8168) and then anchors on that
  live value (L8191), while `ScalePanelRoot` correctly restores `prev.origL/
  origT` on `ResetToOriginal` (L7846-L7856). The record even *stores* the
  original position (`rec.hasOrigPos = true`, L8206) and never reads it.
  `DialogDockTick` has the same shape at L8789. **This is a live defect, not a
  historical one.**
- **A transient can be parented to the APP FRAME, not the main window.** The
  missing-plugin-packs warning `0x2A5CFB2C` was measured as
  `MWKID 0.0 id=0x2A5CFB2C vt=00ADC678 (90,98 710x476) vis=1` — a child of
  `0x6104489A`, added *after* the 3D view, therefore painting over it
  (2026-07-31 11:08:17; log since rotated; re-test: launch with a plugin pack
  absent). §1.1's host table should list the app frame as a third transient
  host, alongside the main window and the view.

## 11.10 THE POINTER RULE — when `scaleMap` keyed on `void*` is safe

**A `cIGZWin*` is safe as a MAP KEY within the tick that enumerated it. It is
never safe as a stored HANDLE.**

That distinction is the whole answer, and the shipped code is on the right side
of it almost everywhere:

- **Safe, and why the sweep works.** Every pointer the sweep uses comes from an
  `EnumChildren` executed in the same tick, is looked up, mutated and dropped.
  A dangling key in the map is inert: `std::map` never dereferences it.
  `DrainBornScaleRecords` (L3858-L3873) is the model — it writes
  `scaleMap[b.win] = rec` from **cached** id and sizes and never touches
  `b.win`, so a window destroyed between birth and drain costs a stale map
  entry and nothing else.
- **The real hazard is MIS-ATTRIBUTION, not use-after-free.** A recycled address
  hands a *live* window a *dead* window's record. `Classify()` rejects that only
  when the ids differ (L4358-L4366) — so a recycled address holding a **same-id**
  window (the transient-pool case, the six `0x4C30E4FA`, and every id that
  exists as template + instance) passes the check and inherits geometry that was
  never its own. `PurgeSubtreeRecords` patches the subtree case; the top-level
  transient case is unpatched.
- **Therefore: never key state on a transient's pointer across ticks.** Not a
  hook slot, not a `lastSeen`, not a docked latch. If you must, the record needs
  identity the address cannot forge. In ascending strength:
  1. `id` — necessary, nowhere near sufficient.
  2. `id + GetParentWin()` (vt `+0x2C`) `+ origW/origH` — rejects the
     template/instance collision and the pool.
  3. `WinMgr->IsWindowValid(p)` (vt `+0x60`) — the engine's own answer to
     "is this pointer a live window". It does **not** answer "is this the *same*
     window", so it complements (2), it does not replace it.
  4. `GetInstanceID()` if the probe in §11.5 comes back non-zero — then it
     replaces all of the above.
- **Two engine-provided alternatives to a side map, both unused here.**
  `cIGZWin::SetParam/GetParam/EnumParams` is a per-window `uint32 → cIGZVariant`
  property bag: state stored *on* the window dies exactly when the window does,
  which is the property a pointer-keyed side map cannot have.
  `SetNotificationTarget/GetNotificationTarget` gives a dialog's owner link.
  `HYPOTHESIS` — neither has been exercised against SC4; `GetParam` on a stock
  window may well be empty, and a write may collide with a key the game uses.
  Test on a throwaway window before relying on either.

---

# Inserts into existing sections

**§1.1 (host table)** — after the `0xAA32BCE6` cautionary note, add: *"A fourth
transient host: the app frame `0x6104489A` itself takes children (the
missing-plugin-packs warning `0x2A5CFB2C`, added after the 3D view and therefore
painting over it). And `0x2AAB8CC1` is the tooltip layer **class**, not an
instance — one to three live windows have been measured sharing that id at
once. See §11.1/§11.5."*

**§1.3 (child enumeration order)** — after point 1, add: *"Add order fixes the
**initial** order only. Every code-built dialog calls `PullToFront` at birth
(`0x78E0A2`), and the tip layer migrates to the front of the main window's list
on its first show and stays there (measured 2026-07-31 11:16:19 → 11:16:40).
`winflag_sortable=yes` on only 27 of 5,964 nodes, so outside those 27 the order
is add-order plus explicit raises. See §11.8."*

**§3.1 (`.UI` format)** — new sub-table, the token dictionary, extracted from the
registration block at `0x94D641`+ (registrar `0x408480` → `[svc+0x0C]`, table
global `[0xB63588]`): `clsid` = −1, `iid` = −2, the truth words `yes`/`true`/`on`
= 1, then `id` = 0x100, `area` = 0x101, **`pos` = 0x102**, **`size` = 0x103**,
`fillcolor` = 0x104, `caption` = 0x105, `captionres` = 0x106,
`transparent` = 0x107, `comments*` = 0x108-0x10F, `font` = 0xF000,
`bkgcolor`/`forecolor`/`notify`/`gutters`/`style` = 0xF001-0xF005, the alignment
and bevel words 0xF006-0xF00E, `colorfont*` 0xF00F-0xF014, `align` = 0xF015,
`image`/`imagetype`/`imagerect` = 0xF016-0xF018, `outline` = 0xF019,
`winflag_*` = 0xF01A-0xF026, plus per-class blocks at 0x1000 (spinner/number),
0x1100, 0x1200 and 0x1300 (the file dialog, 60+ tokens). *Note `pos=` and
`size=` are registered but appear in **zero** shipped scripts — `HYPOTHESIS`
that they are accepted alternatives to `area=`; a generator experiment would
settle it, and if true it removes the corner-vs-extent conversion in
`build_dialog_static.py`.*

**§8.5 (VA table)** — add:

| VA | What |
|---|---|
| `0x913C46` / `[0xB628C0]` | **cached `cIGZWinMgr` accessor** and its singleton slot — the cheap way for a DLL to reach the manager (relevant to the hit-test note in `HANDOFF-god-mode-flyouts.md` L1086-L1103, which proposed hooking `GetWindowFromPoint` without having this) |
| `0x5F9390` | **the `.UI` instantiation factory** — `cIGZUIScriptService` (clsid `0x5A356E15`, IID `0xFA3562FA`) vt `+0x10` `(key, parent, rootWinId) → cIGZWin*`. `0x778245` is a caller, not the factory |
| `0x78DFF0` | generic message-box builder, protocol decoded (§11.2) |
| `0x4F2653`, `0x791439`, `0x455240` | three more builders running the identical show → `DoModalWin` → hide → `IsWindowValid` → `GZSetFocus` sequence |
| `0x8AF356`-`0x8AF3A3` | owner destructor: `WinMgr->DestroyWindow(w); field=0; w->Release()` — the canonical teardown |
| `[0xB43CE0]`, set at `0x602336` from `[0xB43C94]->vt[0xAC]()` | the sub-service whose `+0x28(win,bool)` / `+0x18(win)` bracket every `DoModalWin`. Identity `[OPEN]` |
| `0x94D641`+ | `.UI` token-name registration table (§3.1) |
| `cIGZWinMgr` vt | `+0x0C` GetMainWindow, `+0x50/54/58` valid-list add/remove/cleanup, `+0x5C` DestroyWindow, `+0x60` IsWindowValid, `+0x90/94` GZGetFocus/GZSetFocus, `+0xA4` DoModalWin, `+0xA8` IsModal, `+0xAC` GetModalNestCount |
| `cIGZWin` vt | `+0x2C` GetParentWin, `+0x5C` PullToFront, `+0xA4/A8` GetW/GetH, `+0xE0` GZWinMoveTo, `+0xF8/FC` GetID/SetID, `+0x100/104` GetInstanceID/SetInstanceID, `+0x110/114` Show/HideWindow |

---

# For `_tests\REGRESSION.md` → LAWS MINTED (continuing from 33)

34. **"Closed" means two different things, and you must know which.** A
    main-window transient is **unparented** on close — it leaves the child list,
    so any cached pointer, index or latch is dead. A view-parented transient
    stays in the list hidden and **accumulates**: six live copies of
    `0x4C30E4FA` were measured under the 3D view at once. Never single-find a
    transient id; iterate every match, and never treat "not visible" as "not
    there". *(`SC4-UI-ENGINE.md` §11.1.)*

35. **A pointer is a key, never a handle — and a key needs identity the address
    cannot forge.** `scaleMap` is safe because every pointer is enumerated and
    used inside one tick and no key is ever dereferenced
    (`DrainBornScaleRecords` is the pattern to copy). The failure mode is not a
    crash, it is **mis-attribution**: a recycled address hands a live window a
    dead window's record, and `Classify`'s id check cannot see it when the ids
    match — exactly the template+instance and pool cases. The engine publishes
    the contract we re-implemented: `cIGZWinMgr::IsWindowValid` at vt `+0x60`,
    which the game itself calls on every saved window pointer after a modal.
    *(§11.4, §11.10.)*

36. **Placement happens once, at creation, from the size the window had then.**
    Code-driven boxes land at `x=(parentW−w)/2, y=(parentH−h)/3` and are
    content-fitted afterwards without re-placing — so a tall instance hangs low
    by design, and a fix that mutates position must restore the *recorded*
    origin on every re-show or it compounds. `kCityDialogIds` currently does not
    (`UiSpike.cpp` L8168/L8191 read live `L/T` while `rec.origL/origT` sit
    unread at L8206; `ScalePanelRoot` gets it right at L7846-L7856), and the
    quit confirm drifts a fixed delta per reopen. *(§11.3, §11.9.)*

# For `README.md` → LAWS (short form)

**A WINDOW POINTER IS A KEY, NOT A HANDLE.** Look it up only in the tick you
enumerated it; never store one across ticks; never assume an id identifies one
window. Main-window dialogs are unparented on close, view-parented ones persist
hidden and pile up. The engine's own liveness test is
`cIGZWinMgr::IsWindowValid` (vt `+0x60`) — the game calls it on every saved
pointer after a modal, and we never have.
`tools\research\SC4-UI-ENGINE.md` §11.
