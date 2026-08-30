# CHECKPOINT — uimap Stage 3: the LAYOUT EMULATOR

Written for a **cold replacement agent**. Last update 2026-07-30 evening.
Scope of this agent: `tools\uimap\emu\` and this file. Nothing else was
touched — `src\`, `dist\`, `tools\flyout-sim\`, the then-current HANDOFF.md
session diary (retired 2026-08-06, superseded by `START-HERE.md`; its diary
content was archived to the gitignored `_archive\`, so it is not openable
from here), `README.md`, `_tests\REGRESSION.md`, `VERSION-HISTORY.txt` are
all unmodified, and
`tools\uimap\` Stages 1–2 belong to a different agent.

---

## STATUS: DONE, GREEN, AND IT PRODUCED A RESULT THAT CHANGES THE FIX

`python tools\uimap\emu\emu_layout.py --selftest --fresh -v` → **5 pass, 0 fail.**

---

## DONE

1. **`tools\uimap\emu\emu_layout.py`** — Stage 3 per `METHOD.md` §6. Runs the
   REAL `sub_779660` (`0x00779660`) plus the REAL `cGZWin::SetArea`
   (`0x0099C837`), `GZWinMoveTo`, `GetW`, `GetH`, `GetArea`, `SetW`, `SetSize`
   under Unicorn, with the window-text factory / font / graphics services
   stubbed in python. Records every create, `SetArea`, `GZWinMoveTo`,
   `ChildAdd`, `SetID`, `SetAlignment`. Parameterised by scale factor `f` and
   by a **font-metric callback** (`FontModel.measure`). Also decodes a
   builder's `sub_779660` call sites straight from the immediates
   (`--builder=VA --len=N`) and caches the decode.
2. **Acceptance test PASSED.** The model reproduces **795x75 and 750x25
   exactly**, plus the title's 697x37, plus two predictions (1x stock
   345x75; fixed-2x 690x150). See `tools\uimap\emu\POPUP-VERDICT.md` §2.
3. **`POPUP-VERDICT.md`** — the wrap-width answer with VAs, the acceptance
   result, the fix as `round(stock × f)` math with the imm8-ceiling analysis,
   and the leads for anything still open.
4. **`README.md`** (how to point it at any other builder, plus the vtable-offset
   gotchas) and **`RESUME.md`** (one command).
5. **Resumability**: `state.json` flushed after **every** case; `--resume`
   skips completed ones; `--fresh` restarts safely; call-site disassembly
   cached under `cache\`. Verified by an interrupted-then-resumed run.

---

## THE HEADLINE — READ THIS BEFORE TOUCHING THE POPUP AGAIN

**The `push 0x3e8` (1000) at `0x0077971A` is NOT the wrap width and cannot
be.** §POPUP P4 question 2 is answered **NO**, and the prime hypothesis of the
whole deep dive is refuted — on ordering, which is stronger than a value
argument:

* The ordinance BODY `0x0ABCE001` is created with **`align 0x63` = FILL**
  (`push 0x63` at `0x0078BA69`). The fill branch (`0x00779793`–`0x007797D2`)
  does `SetArea(x, y, parentW − 2x, parentH − y)` — **it overwrites all four
  edges**, so the `1000` SetArea two instructions earlier is dead, and so is
  the text extent. Emulator trace shows the 1000 land and then die.
* The only layout call, `FitWindowToText(false,false)` at `0x007796D8`, runs
  **before** both SetAreas. Whatever width the text was laid out against, it
  was the window's width *at creation* — never 1000, never 750, never 840.

**So the two "decisive observation" numbers were never about text.**
`795x75` is the body at x/y `(15,25)`; `750x25` is the same body after the
v2.27.0 patch moved it to `(30,50)`. Same formula, any string, any font:

```
W = parentW − 3x      H = parentH − 2y
```

**The real defect is geometric and it is ours.** Three popup constants were
never scaled:

| VA (imm8) | stock | what | patched today? |
|---|---|---|---|
| `0x0078B9A0` | 125 | popup **height** | ❌ |
| `0x0078B9C3+2` | 125 | the y clamp | ❌ |
| `0x0078B9A3` | 60 | popup right margin (`dialogW − 60`) | ❌ |
| `0x0078B9D8` | 30 | popup x | ❌ |

Result at 2x: popup `840x125` where 2×stock is `780x250`; body `750x25` where
2×stock is `690x150`. `BdgtPopupBody` is Arta **28** at 2x — **25 px cannot
hold one line.** That is the "crushed box".

Fix = add those to the `round(stock × f)` table; it reduces to stock at f=1 and
lands on exactly 2x/3x (emulator-verified sweep in `POPUP-VERDICT.md` §4).
⚠ 125 does **not** fit an imm8 at any shipping tier → use a **runtime pin on
the sweep** for the height (idempotent, size-only, **no scale record** — law
14; `0x0423278F` stays banned from `kCityDialogIds`).

---

## FOLLOW-UP ANSWER (coordinator, same session) — THE LINE BREAKER, DECODED

Question was: at `FitWindowToText` (`0x007796D8`) what width is in effect, is it
a constant, and is the break computed at layout or at paint? Full write-up in
`POPUP-VERDICT.md` §5. Short form:

**Text class field map** (code region `0x009BC000–0x009C1000`):

| Field | Meaning |
|---|---|
| `[this+0x128]` | **WinText FLAGS** — what `cIGZWinText::SetWinTextFlag(long,bool)` (vt `+0x1C`) writes. **ctor default 0** (`0x009C026C`). bit `0x0002` = **WORD WRAP**; bit `0x0200` = force single line. |
| `[this+0x158]` | gutter, ctor default **5** (`0x009BFFCC`) |
| `[this+0x160]` | the **wrap width** |
| `[this+0x1D4]` | optional scrollbar, its width is subtracted |

**`sub_9BCBC5`** — `wrapWidth = GetW() − 2×gutter − scrollbarW`, clamped to 0.
So **`GetW() − 10`**. **Not a constant anywhere — there is no CodePatches site.**

**`sub_9BF3E0`**, switch at **`0x009BF486`**:

```
w = [this+0x160]
w == 0 || flags & 0x0200 -> ONE line, no breaks at all      (0x009BF4D7)
flags & 0x0002           -> WORD WRAP at w                  (0x009BF4B3)
else                     -> break at '\n' ONLY, then clip   (0x009BF4BB)
```

**`0x009BFCA5`** = the class's **`SetArea` override**: base `SetArea` →
`sub_9BCBC5` → store `[+0x160]` → `sub_9BF98B` **re-breaks every line**.

**Therefore (answers, in order):**
1. The width at `FitWindowToText` is `createdWidth − 10` — and it is
   **irrelevant**, because the break is not frozen there.
2. **Not a constant.** Derived from the window's own width. Nothing to patch.
3. **The break is recomputed against the CURRENT rect on every `SetArea`.**
   `sub_779660` issues two after the autosize, so the *last* wins: the
   effective wrap width today is **740** (`750 − 10`). ⚠ This **narrows law
   21** — text does not re-wrap from a re-applied caption, but it **does**
   re-wrap from a `SetArea`.

**Why it still doesn't wrap:** flag `0x0002` is clear (ctor 0; `sub_779660`
never calls `SetWinTextFlag`, only `cIGZWin::SetFlag` for `0x800`/`0x8000`), so
the `'\n'`-only regime applies. That single mechanism explains BOTH live
observations: an early break with space left = a **hard newline in the LTEXT**;
a mid-word cut at the box edge = a newline-delimited segment **longer than the
box**, clipped. A 740-px word wrap could produce neither.

**CURE — one call, no constants, no string work:**
`cIGZWinText::SetWinTextFlag(0x0002, true)` on the body `0x0ABCE001`
(`GetChildAs(0x0ABCE001, 0x212CDC1F, &pText)`), then any `SetArea` (the §4
geometry pin already does one) to trigger the recompute + re-break. Engine then
wraps at `GetW() − 10` at every tier: 335 @1x, 680 @2x-after-fix, 1025 @3x.
Idempotent; survives later resizes by design. **Apply the §4 height fix FIRST**
or the wrapped lines have no room. The manual `CalculateWordsToFitInWidth` +
newline-injection block in the in-flight v2.28.0 `UiSpike.cpp` can be
**deleted**.

**Before shipping, one free confirmation:** the field map belongs to the class
in `0x009BC000–0x009C1000`; that the factory's runtime COM service
(`sub_7B2480`, id `0xC2C2EB0F`) creates *this* class is HYPOTHESIS. Log
`GetWinTextFlag(0x0002)` (vt `+0x18`) on `0x0ABCE001` from the sweep — **false
confirms the whole diagnosis**, true means a different class and §5.4 is wrong.

The emulator now models all of this: `--selftest` prints a `WRAP REGIME` table
and every `-v` `SetArea` line carries `[wrap width becomes N]`
(`wrap_width_model()` / `line_break_regime()` in `emu_layout.py`).

---

## SECOND FOLLOW-UP — TASK #50, THE SHOW PATH (full write-up: `tools\uimap\emu\SHOW-PATH.md`)

Coordinator wanted the visibility-setter slot for a scale-at-show hook.
**Lore was wrong and one constructor fact changes the design.**

**Slots (all `header + 4`):**

| Real | Slot | Impl |
|---|---|---|
| `+0x10C` | `GetFlag(uint32)` — **a READER** | `0x0099BDBB` (`[this+0xC8] & flag`) |
| **`+0x110`** | **`SetFlag(flag, value)` — THE SETTER** | **`0x0099DB6B`** |
| `+0x114` | `ShowWindow()` (already transition-gated) | `0x0099D1AA` |
| `+0x118` | `HideWindow()` | `0x0099D1EA` |
| `+0x11C` | `IsVisible()` = `GetFlag(1)` | `0x0099BDCE` |
| `+0x120` | `IsEnabled()` = `GetFlag(2)` | `0x0099BDD9` |

**Mechanism.** `SetFlag(1,·)` sets/clears bit 1 of **`[this+0xC8]`**, then
`PrivateBuffer(value)` or `sub_99D645` (walks children **only** for private
buffers — never touches their flags), focus fix-up on hide, then
`[this+0x48]->InvalidateSelfAndParents()`. **No Plot, no paint, no re-layout,
no propagation of the visible bit.** First paint happens later in
`cIGZWinMgr::Plot()`, so a hook here is provably pre-paint.

**⚠ WINDOWS ARE BORN VISIBLE.** Both ctors (`0x0099DA15`, `0x0099DB3C`) do
`mov [esi+0xC8], 0x8903` = Visible|Enabled|Sortable|AcceptFocus. So a freshly
built tree produces **no false→true transition** — it lights up via `ChildAdd`
(`vt+0x38`, single shared impl `0x0099EA66` → `sub_99E207`). A show hook cures
**mode switches**, not construction. HYPOTHESIS, well supported.

**⚠ `IsVisible()` is the window's OWN bit only.** The ancestor-walking
"effectively visible" test is **`0x0099EA70`** (`GetParentWin` `+0x2C` +
`IsVisible` `+0x11C` up the chain). The sweep's gate at `UiSpike.cpp` ~4095 is
testing own-bit semantics.

**Parent or child?** Because the bit is not propagated, a mode switch flips
**one parent's** bit and the whole already-flagged subtree appears — **one hook
call covers the subtree.** Individual `SetFlag(1,·)` on children also occurs
(ordinance builder `0x0078BBB0` hide / `0x0078BBCD` show).

**RECOMMENDATION — one 5-byte trampoline on `0x0099DB6B`, no vtable patching.**
`+0x110` holds that same pointer in all 10 window vtables sampled; the only two
overrides (Button `0x009B112D`, text `0x009C9379`) **both call it**, and
`ShowWindow` routes through the virtual `+0x110`. Filter
`flag==1 && value && !([this+0xC8]&1)` (transition-only, 2 compares),
re-entrancy guard, **`ScaleSubtree` BEFORE the original** — because
`PrivateBuffer(true)`/`sub_99D645` size back-buffers from the CURRENT rect, and
because sizing while still flagged hidden is the proven recipe. Gate only the
dock MOVE on visibility, after. Not covered: MenuItem vtable `0x00AB6FE4`
(different hierarchy, `+0x110` = `0x0099E594`).

**Ranking vs `REGRESSION.md` SYSTEMIC #1:** target 1 (.UI deserializer
completion) **cannot be the general cure** — it runs once per tree while the
flash recurs on every re-show, and it is per-class (6 VAs). Target 2
(mode-switch instantiation) is N routines; `SetFlag` is their common downstream
funnel. **Target 3 is right but its VA is wrong** — `vt+0x10C` is the reader;
use `vt+0x110` / `0x0099DB6B`.

**Two zero-risk confirmations before trusting it:** log
`SetFlag(1,false→true)` transitions per mode switch with the window id (one per
panel root ⇒ subtree coverage confirmed), and log `[this+0xC8]` for a fresh
dialog root before its first show (`0x8903` ⇒ born-visible confirmed).

---

## THIRD FOLLOW-UP — NESTED PLOP SUB-FLYOUTS (full write-up: `tools\uimap\SUBFLYOUT-CONSTANTS.md`)

Coordinator retargeted from the paint/show hook (dropped — see that file) to
the on-demand nested plop menus: container `0x8A6E61E0` (always 258 wide),
item strip `0x8A2CAD8B`. He wanted a budget-style constant census + patch table.

**ANSWER: the container is ART-BOUND, not code-sized. No patch table.**

* **Builder = `sub_7EAC70`**, extent `0x007EAC70–0x007EB84C`, `__thiscall`,
  `ret 0x18` (6 args + this). It is the **only** site in the image that pushes
  `0x8A6E61E0` (whole-image imm32 scan: 1 hit, `0x007EB11A`).
* Right before creating the container it loads a bitmap by TGI —
  `0x007EB0C0` `[esp+0x3c]=0x856DDBAC`, `0x007EB0C8` `[esp+0x40]=0x46A006B0`,
  `[esp+0x44]=instance` (from arg `[esp+0x98]`, varies per menu), then
  `call 0x00602B00`. **That is the same art key pair as the budget band
  factory `sub_77A390`** ("GZWinBMP sized FROM THE ART").
* Then `operator new(0x150)` → ctor `sub_79AFF0` → `SetID(0x8A6E61E0)`
  @`0x007EB11A`. Item strip gets `SetArea(cRZRect&)` from a **helper-filled
  rect** (`0x007EB1D2` fills, `0x007EB1E5` applies) then `SetID(0x8A2CAD8B)`
  @`0x007EB1F4`.
* **The literal 258 (`0x102`) does not occur anywhere in the builder's
  extent** (154 imm32 hits image-wide, none in range; 258 cannot be imm8).
* Family confirmed: `0x0079Axxx–0x0079Bxxx` = the same block as the already
  cracked container `Plot 0x0079B0E0`, strip `Plot 0x0079AA70`,
  `IsPointInMe 0x0079A180` → claim `0x0079AE30` (`emu_hittest.py`).

⇒ **HYPOTHESIS (high confidence): cure = ship that art family at `f`**, same as
the budget bands — not `CodePatches`. Told the coordinator BEFORE he wrote a
table, which is what he asked for.

**Deliberately produced NO C++/constants.json table.** The 19 immediates
`sub_7EAC70` feeds to helper methods are listed in the doc with encodings and
bytes but marked `role: UNVERIFIED` — the helper classes
(`[esi vt+0x30/0x34/0x38]`, `[ebx vt+0x10/0x14/0x18]`; ctors `sub_79AFF0`
and `sub_799DD0`) are not decoded, and scaling an unknown-role value is the
exact shape of the three failed popup builds. Flagged anyway: **124
(`0x007EAD4B`) and 80 (`0x007EB165`) can never fit imm8 at any shipping tier**
(overflow at f>1.02 and f>1.58) — they would need pins, like the popup height.
Also noted: a **strip-id TWIN at `0x007E5EB9`** outside this builder (law 15/16).

**ONE log line to settle it** — on first sight of `0x8A6E61E0`, log its rect
AND its first `GZWinBMP` child's rect. Art-derived ⇒ both read 258 wide (and
heights differ per menu because the art instance differs). If the container
reads 258 but the BMP child does not, the art answer is WRONG and the
UNVERIFIED immediates become live candidates, starting with 80 and 124.

**Also dropped at the coordinator's instruction:** the `SHOW-PATH.md` SetFlag
hook (shipped log-only; the ids that fired were disjoint from the ids that
flash — consistent with my own born-visible `0x8903` finding) and the
paint-pass hook. `SHOW-PATH.md` stands as decoded reference; its §6
recommendation is superseded. Confirmed en route: **Plot is real vtable
`+0x160` (slot 88)** — per-class overrides in every vtable sampled — so the
project's `PatchFlashGuardClass` slot number was right. ⚠ The `header + 4`
shift is **not uniform**: it holds at `+0x10C…+0x120` (verified by each impl)
but is back to zero by `+0x160`. Verify every slot by its implementation;
never extrapolate the shift.

---

## IN FLIGHT / NOT MINE

* `src\UiSpike.cpp` carries an **in-progress v2.28.0** self-wrap block
  (`settings.spikePopupWrap`, uses `cIGZFont::CalculateWordsToFitInWidth`).
  I did **not** edit it. Its comment block asserts two things this pass
  refutes: that the body window "already self-scales — 750 wide inside the 840
  box, which is right" (it is 60 too wide and 125 too short), and that the wrap
  happens against the unscaled 1000 (it happens before the 1000 is applied).
  The self-wrap itself is still worth having — but it must wrap against the
  **corrected** box, or it wraps to the wrong width and a box that cannot show
  the lines.
* `tools\uimap\` Stages 1–2 (`census.py`, `argscan.py`, `builders.json`,
  their own `state.json`) belong to another agent. `emu\` is self-contained
  and does not import from them.

---

## SURPRISES (things that cost time — do not re-derive)

1. **`cRZRect` is `{x,y,w,h}` in the SDK header, but a window's area field at
   `[this+0xA8..0xB4]` is `{L,T,R,B}`.** Proven by `GetW = [+0xB0] − [+0xA8]`
   (`0x0099C81B`) and by `SetArea` (`0x0099C837`) storing its four args
   verbatim. Reading the header name first sent me down a wrong branch.
2. **The game's `cIGZWin` vtable is `header + 4` from ~`+0xE4` onward** (one
   extra virtual the SDK header omits). Real `+0x100 = SetID`,
   `+0x110 = SetFlag(flag,value)`. Below `+0xE0` the header is exact.
   `cIGZFont`'s header **is** exact (`+0x8C = GetLineHeight` confirms it).
3. **§POPUP P4 question 3's flag sites are a false lead.** `0x00777299`,
   `0x00777424`, `0x00777479` call `[vt+0x18](f)` / `[vt+0x1C](f)` with **one**
   argument; `cIGZWinText::SetWinTextFlag` takes **two** — a genuine two-arg
   call is `push 0; push 2; call [eax+0x1C]` at `0x009C7DA9`. Those `0x8001` /
   `0x8010` values belong to another class. `0x0077899B` likewise.
4. **There is more than one `cIGZWinText` implementation.** The vtable at
   `0x00AE1678` (SetCaption `0x009C93D7`) is *not* the one the label factory
   creates: its `+0x14` is `ret 4`, and `sub_779660` provably passes two args
   to `+0x14` (proven by whole-function stack balance). Do not assume a single
   text class.
5. The factory itself (`sub_913C72` → service id `0xC2C2EB0F`, built by
   `sub_7B2480`) is a **runtime COM singleton** — its `[vt+0x34]` create cannot
   be resolved statically. That is the one thing blocking a fully-real
   FitWindowToText emulation.
6. The backward push-walk for call-site args must **not** be reversed: args are
   pushed right-to-left, so walking back from the `call` yields arg1 first.
   Reversing it produced convincing garbage (`id=0x55`, `y=0xEA85D307`) that
   looked plausible for a minute.

---

## NEXT ACTION (in order)

1. **Ship the geometry fix** (`POPUP-VERDICT.md` §4): margin 60 and x 30 into
   the imm8 table; height 125 (and its `-125` clamp) as a sweep pin — imm8
   cannot hold 250. Verify by re-running `--selftest`, then by a POPKID dump:
   body must read `690x150` at 2x.
2. **In the same build, add `SetWinTextFlag(2, true)` on `0x0ABCE001`**
   (`POPUP-VERDICT.md` §5.5) and **log `GetWinTextFlag(2)` before setting it**
   — that one log line confirms or kills the §5 diagnosis for free. Order
   matters: geometry first, or the wrapped lines have nowhere to go.
3. **Capture the popup at 1x** anyway (`BUDGET-DETAIL-ANATOMY.md` §POPUP P5,
   ~3 min). §5 predicts stock shows the same `\n`-only breaks + clipping at
   345 px. It is the only thing that distinguishes "we match stock" from "we
   broke it".
3. **Fold the corrections back into the docs** — `BUDGET-DETAIL-ANATOMY.md`
   §POPUP (P2's "decisive observation" needs replacing; add the fill-branch
   formula and the three unscaled constants) and `SC4-UI-ENGINE.md` (the
   `cRZRect` L,T,R,B trap and the `cIGZWin` +4 vtable shift). `METHOD.md` §5
   write-back contract applies — this pass produced novel mechanism.
4. **Extend the emulator to the band stacker** `sub_77A6F0` / band factory
   `sub_77A390` so Stage 3 covers whole budget dialogs, not just labels. The
   stub table and the recorder need no changes; only new vtable slots with
   their argument counts (README, "Extending it to a new builder").
