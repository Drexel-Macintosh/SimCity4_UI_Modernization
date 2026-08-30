# SHOW-PATH — the visibility setter, decoded (task #50, the systemic 1x flash)

Offline only: exe read-only, game never launched, no shipping code touched.
Sibling of `POPUP-VERDICT.md`. Everything here is read from
`SimCity 4.exe 1.1.641.0`; **inference is labelled HYPOTHESIS and the live
dump remains the authority.**

---

## 0. ANSWER FIRST

**The lore is wrong.** `vt+0x10C` is **`GetFlag` — a READER**, not the setter.
The setter is **`vt+0x110 = SetFlag(uint32 flag, bool value)`**, base impl
**`0x0099DB6B`**, and it is **the same pointer in every window vtable**. So the
hook is **one 5-byte trampoline on one function**, not a vtable-patch campaign.

**And one thing that changes the design:** the cGZWin constructors set
`[this+0xC8] = 0x8903` — **every window is BORN VISIBLE**
(`Visible|Enabled|Sortable|AcceptFocus`). A freshly built subtree therefore
produces **no false→true transition**; it lights up by being `ChildAdd`ed into
an attached parent. A transition hook is the right cure for **mode switches**
(hidden variant stacks → shown), which is where the systemic flash lives —
but it is **not** a cure for born-then-attached trees, and any claim that it
is would be wrong.

Recommendation in §6.

---

## 1. THE SLOTS (all confirmed, all `header + 4` — see `README.md` gotchas)

| Real offset | Slot | Impl | What it does |
|---|---|---|---|
| `+0x10C` | `GetFlag(uint32)` | `0x0099BDBB` | `return ([this+0xC8] & flag) != 0` — **reader** |
| **`+0x110`** | **`SetFlag(uint32 flag, bool value)`** | **`0x0099DB6B`** | **the setter — THE HOOK POINT** |
| `+0x114` | `ShowWindow()` | `0x0099D1AA` | transition-gated wrapper, see below |
| `+0x118` | `HideWindow()` | `0x0099D1EA` | mirror of the above |
| `+0x11C` | `IsVisible()` | `0x0099BDCE` | literally `this->GetFlag(1)` |
| `+0x120` | `IsEnabled()` | `0x0099BDD9` | `this->GetFlag(2)` |

`ShowWindow` (`0x0099D1AA`), transcribed:

```
if (this->GetFlag(1)) return;              // ALREADY VISIBLE -> no-op
this->SetFlag(1, true);                    // virtual, through vt+0x110
if (this->GetFlag(0x20 /*UseFade*/))
    sub_99CAAD(this, 0, [this+0x94]);      // start the fade
```

`HideWindow` is the mirror (`if (!GetFlag(1)) return; SetFlag(1,false); …
sub_99CAAD(this, 0xFF, 0)`). **Both funnel through the virtual `+0x110`**, so a
trampoline on `0x0099DB6B` catches them as well as every direct
`SetFlag(1,·)` call site.

---

## 2. `SetFlag` ITSELF — mechanism (`0x0099DB6B`)

```
value = [esp+8]; flag = [esp+4]
if (value) [this+0xC8] |=  flag;
else       [this+0xC8] &= ~flag;

switch (flag) {                            // a dec/sub chain, 0x0099DB8D+
  case 0x00000001:  -> 0x0099DC81          // Visible      <-- ours
  case 0x00000002:  -> 0x0099DC4C          // Enabled
  case 0x00000020:  -> 0x0099DC2B          // UseFade
  case 0x00010000:  -> 0x0099DC04          // PrivateBuffer
  case 0x00020000:  -> 0x0099DBDA          // PrivateBufferTrans
  case 0x08000000:  -> 0x0099DBC1          // DelayedPlot
  default:          -> 0x0099DCD9          // fall straight out
}
return [this+0xC8];                        // the NEW flag word
```

The Visible case (`0x0099DC81`):

```
if (this->GetFlag(0x10000))  this->[vt+0x190] PrivateBuffer(value);
else                         sub_99D645(this, value);
if (!value && winMgr->GZGetFocus() == this) sub_99C9DF(this, [this+0x4C]);
if ([this+0x48]) [this+0x48]->[vt+0x170] InvalidateSelfAndParents();
[this+0xCA] &= 0xBF;
```

**Three things it does NOT do**, and all three matter:

* **No `Plot`, no paint, no draw of any kind.** Only an *invalidate*.
* **No recursion of the visible bit into children.** `sub_99D645`
  (`0x0099D645`) walks the child list `[this+0x44]` but only to test
  `GetFlag(0x10000)` and manage private buffers — it never touches a child's
  `[+0xC8]`.
* **No re-layout, no resize.** Geometry is untouched by showing.

---

## 3. WHERE THE FLAG LIVES, AND THE TRANSITION TEST

**`[this+0xC8]`, bit `0x1`.** `IsVisible()` reads exactly that field, through
the virtual `GetFlag`, so a hook that tests `[this+0xC8] & 1` **before**
calling the original fires on the **false→true transition only** — no
redundant sets. That is the cheap gate.

Two traps in this field:

1. **`IsVisible()` is the window's OWN bit, not "on screen".** The engine's
   real "effectively visible" test is **`0x0099EA70`**, which walks
   `GetParentWin()` (`+0x2C`) calling `IsVisible()` (`+0x11C`) at every level
   and fails if any ancestor is hidden. Worth knowing for the sweep's gate at
   `UiSpike.cpp` ~4095: it is testing the panel's own bit, so a panel whose
   *ancestor* is hidden still reads visible.
2. **Windows are BORN VISIBLE.** Both cGZWin constructors —
   **`0x0099DA15`** and **`0x0099DB3C`** — do
   `mov dword ptr [esi+0xC8], 0x8903`
   = `Visible(1) | Enabled(2) | Sortable(0x800) | AcceptFocus(0x8000)`.
   **HYPOTHESIS**, but a strongly supported one: it means a newly constructed
   tree never transitions, and §6 is built around it.

---

## 4. PARENT OR CHILD? — both, and they are different events

**Event A — the mode switch (the flash).** Because the visible bit is *not*
propagated (§2), every child of a hidden panel already carries its own
`Visible` bit; only the parent's bit is off. Flipping the parent's bit
therefore lights the entire subtree in **one** `SetFlag(1,true)` call.
**One hook call catches the whole subtree** — the cheap case — and it is
consistent with the observation that `panels[]` is full of "hidden variant
stacks and menu layers".

**Event B — fresh construction.** Born visible (§3.2), then attached. The
attach is `ChildAdd`, `vt+0x38`, also a **single shared impl**: every sampled
vtable holds `0x0099EA66`, a `jmp` thunk to **`sub_99E207`**. Evidence in hand:
`sub_779660` sizes a label completely and calls
`parent->ChildAdd(win)` **last**, at `0x00779835`.

**Both routes are used, sometimes in the same builder.** The ordinance popup
builder shows and hides individual children by id —
`0x0078BBB0` `SetFlag(1,false)` on `0x454`, `0x0078BBCD` `SetFlag(1,true)` on
`0x453` — while its labels arrive by `ChildAdd`.

---

## 5. ORDERING — no paint in the call stack, but scale BEFORE the original

There is **no `Plot` anywhere in the show path** (§2); `SetFlag` only
invalidates, and the first paint happens later in the frame when
`cIGZWinMgr::Plot()` (`cIGZWinMgr` `+0x18`) walks the tree. So a hook on
`0x0099DB6B` is **guaranteed to run before the first paint of that window** —
scaling there cannot be beaten by a paint, and no paint suppression is needed
or wanted.

**Scale before calling the original anyway**, for a concrete reason:
for a window carrying `WinFlag_PrivateBuffer (0x10000)`, the Visible case calls
`PrivateBuffer(true)` (`vt+0x190`) / `sub_99D645`, which **sizes back-buffers
from the window's CURRENT rect**. Scale afterwards and a private-buffered
window gets a 1x buffer behind a 2x rect. Scaling first also means our
`SetArea`s land while the window is still flagged hidden — which is precisely
the **pre-scale-while-hidden** recipe already proven on region panels, the god
flyouts and `kAlwaysScaleCityIds`. Keep the existing discipline: **size while
hidden, gate only the reposition/dock MOVE on visibility** and do that after,
or leave it to the next sweep tick.

---

## 6. THE ONE RECOMMENDATION

**Trampoline the base function `0x0099DB6B`, not any vtable.**

```
hook SetFlag(this, flag, value):
    if (flag != 1 || !value)            -> tail to original          // 2 compares
    if ([this+0xC8] & 1)                -> tail to original          // already visible
    if (reentrancyGuard)                -> tail to original
    reentrancyGuard = 1;
    ScaleSubtree(this);                 // size only, window still flagged hidden
    reentrancyGuard = 0;
    -> original(this, flag, value)      // its buffers now size from the 2x rect
```

Why this and not the alternatives:

| | |
|---|---|
| **One patch, total coverage** | `+0x110` holds `0x0099DB6B` in **every** window vtable sampled — GZWinBMP `0x00ADF6A0`, Button `0x00ADDAF0`, flyout container `0x00AB6AA8`, strip `0x00AB6D88`, text `0x00AE1780`, RCI `0x00AB8628`, TrendBar `0x00ABA430`, GenTransparent `0x00AB7358`, AdviceList `0x00AB58B0`, tooltip `0x00AB6770`. Only **two** overrides exist among them — Button `0x009B112D`, text `0x009C9379` — and **both call `0x0099DB6B`**. A code trampoline covers overrides and any class we have not enumerated; a vtable campaign would not. |
| **Reuses your machinery** | `PatchFlashGuardClass` already does VirtualProtect + thunk + no-double-patch registry. This is the same tooling minus the vtable indirection. |
| **Transition-only for free** | the `[this+0xC8] & 1` pre-test (§3). |
| **Provably before first paint** | §5. |
| **Not covered** | MenuItem vtable `0x00AB6FE4` is a different hierarchy — its `+0x110` is `0x0099E594`. Menu items are outside this hook; decide separately whether they flash. |
| **Hot path** | fires for every flag on every window. The two-compare filter is mandatory; do no allocation and no logging on the fast path. |
| **Re-entrancy** | `ScaleSubtree` calls `SetArea`, which for text windows re-derives the wrap width and re-breaks lines (`POPUP-VERDICT.md` §5). Guard it, and keep `scaleMap` idempotent — the sweep *will* revisit a birth-scaled window (the 4x lesson). |

**Event B (born-visible, attached without a later show)** is deliberately
**not** hooked in this proposal. `ChildAdd` (`0x0099EA66` → `sub_99E207`) is a
single shared impl and hookable, but it fires **mid-construction**, when the
subtree is incomplete and its geometry not yet final — scaling there is the
kind of half-built-tree hazard that has cost this project before. Prefer: most
dialogs are built hidden-or-detached and then shown, which Event A catches;
for any case proven otherwise by the live dump, keep using
`kAlwaysScaleCityIds` as today.

### Ranking against the SYSTEMIC #1 candidates

1. **`.UI` deserializer completion path — cannot be the general cure.** The
   deserializer runs **once per tree**, but the flash recurs on **every**
   mode switch, i.e. on re-shows of trees already built. It is also **per
   class** (`0x94E516`, `0x94CF0A`, `0x94F9E4`, `0x950657`, `0x950C94`,
   `0x959491`) — N patches, not one. Useful only for the born-1x-once case.
2. **Mode-switch instantiation routine** — N routines, one per mode, each
   needing its own VA and its own verification across the scenario matrix.
   `SetFlag` is the **common downstream funnel** all of them pass through.
3. **The visibility setter — the winner**, with the VA corrected from
   `vt+0x10C` (the reader) to `vt+0x110`, base `0x0099DB6B`.

### Verify before you trust any of it

Two log lines, no risk, from the existing sweep or the first hooked build:

* count `SetFlag(1, false→true)` transitions per mode switch, with the window
  id — if a mode switch produces **one** transition on a panel root, §4 Event A
  is confirmed and the whole subtree is covered by one call;
* log `[this+0xC8]` for a freshly built dialog root before its first show — if
  it reads `0x8903`, §3.2 is confirmed.

---

## 7. WHAT WAS CORRECTED HERE

* `vt+0x10C` is **`GetFlag`**, a reader. The setter is `vt+0x110`. Project lore
  (and `REGRESSION.md` SYSTEMIC #1 target 3) names the wrong slot.
* `IsVisible()` is the window's **own** bit only; the ancestor-walking test is
  `0x0099EA70`.
* Windows are **born visible** (`[this+0xC8] = 0x8903`,
  `0x0099DA15` / `0x0099DB3C`) — so "hook the show" does not, by itself, cover
  construction.
* The show path performs **no paint**, so nothing needs to be suppressed —
  consistent with the permanent rejection of FlashGuard.
