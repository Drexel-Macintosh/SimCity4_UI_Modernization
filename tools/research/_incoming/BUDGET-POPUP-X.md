> # ⛔ THIS FILE'S VERDICT IS REFUTED — read this box before anything below it.
> **2026-08-03, task #110, v2.63.0.** §1's "STOCK BEHAVIOUR" verdict is **WRONG**.
> With the whole scaling layer parked (`Set-StockCompare -Mode Stock`, 1024x768)
> the close-X **CLOSES THE BOX**. User-confirmed. So a click on that X does not
> reach `sub_78B120` as command `0xCC` at all — §2's dispatch decoding is correct
> about the bytes and irrelevant to the symptom. The likely real route is the
> notification target the builder wires at `0x77C342`; **not traced**.
>
> **The cause was OURS.** The POPBOX pin applied the *ordinance* twin's stock
> height (125) to the *empty-ledger* twin (stock 100), whose host **is** the
> 600x127 box — so the clamp resolved to `127 − 250 = −123` and put the close-X
> at host-local `y = −101`, above the host rect, where the router's hit walk
> never descends. Confirmed by isolation: `PopupWrap=0` at 2x restored the X and
> simultaneously reintroduced the ordinance twin's text clip.
>
> §3 IS THE PART THAT WAS RIGHT — and its "HYPOTHESIS about a code path never
> observed to execute" caveat was already false when written: **19 logged
> `POPBOX 600x127 -> 600x250 at y=-123` lines** exist from 15:41 that day.
> Fixed in v2.63.0 as a five-window coupled resize (host + popup + content +
> 0x485 + 0x385 → `round(100*f)`), not the four §6.2 assumed.
>
> Other corrections: §2 step 5 — `0x78B287` is **not** a `sub_779850` caller, it
> never posts `0x42B7C353`. §7 — `CodePatches.cpp:310` **does** patch `0x78BAAD`.
> Stock aside: the WinProc closes this popup on **ESC / ENTER / F4** (`0x78BCFE`).

# #103 — Budget department popup: the X draws right and does not close

Written 2026-08-03 against exe `SimCity 4.exe` 1.1.641.0, `sha256[:16] 1189720d5e15b0e1`,
7,876,608 bytes, ImageBase 0x400000. Shipped DLL v2.55.0.
Every address below was re-derived in this session; nothing is inherited on trust.

---

## 1. VERDICT

**STOCK BEHAVIOUR — not ours, not a regression from v2.55.0.**
Confidence: high, offline-gated with a passing positive control (§5). One user action
(§4b, ~10 s, no build, no stock swap) converts "high" into "closed".

The department "no entries in the budget ledger" box is built by `sub_77BEC0`. Its
close-X carries id **0xCC** and its backdrop id **0x385**. The budget dialog's command
handler `sub_78B120` routes **both of those ids to a branch that does not close the
popup**, while routing the *other* twin's ids (0x68 / 0x384 — the ordinance description
popup) to a branch that does. The asymmetry is in the shipped bytes and is untouched by
any patch of ours.

Separately, and **not** the cause of the reported symptom, there is one real
pre-existing defect of ours on the same window (§3, the POPBOX cross-twin pin). It is
worth fixing in the same change because it is cheap, it strictly reduces our footprint,
and it converts a never-measured code path into a logged fact.

Rejected verdicts and why:

| verdict | why not |
|---|---|
| REGRESSION FROM v2.55.0 | v2.55.0 touched `src/UiSpike.cpp` only at the flags block and the chart block; the popup block carries v2.26–v2.28 tags (2026-07-30). No patch table of ours writes inside `sub_78B120` or the dispatch tables at 0x78BC08/0x78BC28. |
| PRE-EXISTING OURS (law 43, hit box left behind the sprite) | Impossible by construction in this engine: `SetW/SetH/SetSize/GZWinMoveTo` all funnel into virtual `SetArea`, which writes the own-rect **and** calls `CalcAbsoluteArea`, which rewrites `[this+0x14]` recursively — and `[this+0x14]` is exactly the rect the router's hit test reads. Sprite and hit box are the same rect. Geometry changes cannot produce "drawn right, click dead". |
| UNDETERMINED | The dispatch table is decodable byte-for-byte and its classifier passes a positive control on a user-confirmed-working twin. This is a measurement, not an inference. |

---

## 2. THE CAUSE, step by step

**Step 1 — identity. #103's popup is `sub_77BEC0`, not the ordinance popup.**
Window id `0x0423278D` is created at exactly **two** sites image-wide (gate §5b):
`0x77BFF1` (`push 0x423278D; call [edx+0x100]` = SetID, inside `sub_77BEC0`) and
`0x78B819` (inside `sub_78B120`). `sub_77BEC0` is called from `0x77C7E6` (Ordinances),
`0x77F51A` (Neighbor Deals), `0x786BA2` (Transportation) and **`0x78826D`, the
slider-department dispatcher — Public Safety / Health & Ed / Utilities / Beautification /
Government**. So it is the generic empty-ledger box; the name "Business Deals empty box"
used throughout `src/CodePatches.cpp` and our notes is a misnomer.

**Step 2 — the two twins have disjoint child ids.** Measured (§5b gate, all PASS):

| | ordinance popup `sub_78B120` | empty-ledger box `sub_77BEC0` (#103) |
|---|---|---|
| stock size | `push 0x7d` H=125, W=dialogW−60 | `push 0x64 / push 0x12c` = **300x100**, five sites |
| backdrop id / outer | 0x384 / 0x484 (`0x78BA95`, `0x78BADD`) | **0x385 / 0x485** (`0x77C2A3`, `0x77C2F4`) |
| close-X id | 0x68 (`0x78BAB3`) | **0xCC** (`0x77C2C1`) |
| close-X x, y | `lea edx,[ebx-0x1f]` @0x78BAAF, `push 0xb` @0x78BAAD | `push 0x10D` @0x77C2BC, `push 0xb` @0x77C2BA |

Neither twin's ids appear anywhere in the other twin's body — gate checks
"`0x484` never referenced inside `sub_77BEC0`" and "`0x485` never referenced inside
`sub_78B120`" both PASS. The discriminator is total.

**Step 3 — both twins notify the SAME window and the SAME handler.**
`sub_77BEC0` sets the notification target (`vt+0x158`) of backdrop 0x385 at **`0x77C325`**
and of close-X 0xCC at **`0x77C342`**, both to the function's `edi`. The ordinance twin
does the identical thing for 0x384/0x68 at `0x78BB09`/`0x78BB22`. The popup itself is
`ChildAdd`ed (`vt+0x38`) to **arg1** at `0x77C008` (`mov edi,[esp+0x50]` at `0x77BFFF`
reloads the first stack argument — correcting a prior note that claimed `edi` came from
the factory; the factory result is overwritten there). One class, one WinProc
(`sub_78BCA0`), one command handler (`sub_78B120`).

**Step 4 — the handler's id→branch table, decoded from the shipped bytes.**
Byte index table `0x78BC28` (0x69 entries, base id 0x67) → jump table `0x78BC08`, plus
the explicit compares at `0x78B128` and `0x78B2CB`. `tools/uimap/emu/gate_103_closepath.py`
prints it:

```
branch 0x0078B15D  CLOSES       ids: 0xCD
branch 0x0078B1E1  CLOSES       ids: 0xCF
branch 0x0078B227  CLOSES       ids: 0xCE
branch 0x0078B287  CLOSES       ids: 0x68, 0x384     <- ordinance twin (POSITIVE CONTROL)
branch 0x0078B406  does NOT     ids: 0xCC, 0x385     <- #103's own X and backdrop
```

"CLOSES" = the branch reads the popup member `[this+0x14]` (the member `sub_77BEC0`
writes at `0x77BF24`) and calls `ChildRemove` (`vt+0x3c`) on it. `0x78B406` is
`sub_779850(win, 0x42B7C353); mov al,1; ret 8` — it **consumes** the click (returns
handled) and removes nothing.

**Step 5 — `sub_779850` is not a hidden closer.** It is
`pWin->GetWindowManager()` (`vt+0x18`) then a message *post* (`vt+0x24`) of
`0xF / sender / 0x42B7C353`. It is also the common tail of the four branches that
*already* did an explicit `ChildRemove`. **INFERENCE, labelled:** if the post closed the
box, those four `ChildRemove` calls would be dead code. I did not trace the posted
command downstream — that is the one residual escape hatch and it is what §4b closes.

**Step 6 — our bytes are excluded.** In `sub_77BEC0` we write exactly three things
(`src/CodePatches.cpp:496-501`, `:1399-1427`): the five 7-byte `SetSize` sites
(`kBizBoxSizeSites`), `kBizBoxCloseX = 0x77C2BC`, `kBizBoxCloseY = 0x77C2BA`. The id push
at **`0x77C2C1` (`68 CC 00 00 00`) is verified stock** by the gate, and nothing of ours is
within 0x50 bytes of the `SetNotificationTarget` wiring at `0x77C325`/`0x77C342`.
`src/UiSpike.cpp` only calls `SetH/SetW/GZWinMoveTo/SetWinTextFlag` here — none of which
can reach an id-keyed dispatch.

**Why nobody noticed in #61–#69:** the box *is* dismissible in stock — the dialog's own
0xCD/0xCE/0xCF buttons tear down `[this+0x14]` as a side effect, and opening another
department's box releases the previous one (`0x77BF13`–`0x77BF30`). #61–#69 were
appearance verifications.

---

## 3. THE ONE DEFECT THAT *IS* OURS ON THIS WINDOW (and the fix)

`src/UiSpike.cpp` POPBOX pin (the `if (settings.spikePopupWrap)` block) applies
`wantH = lround(125.0 * pf)` — the **ordinance** twin's stock height — to **every**
visible `0x0423278D`, because its only test is `pop->GetH() != wantH`. The empty-ledger
twin's stock height is **100**, and `src/CodePatches.cpp:1401-1402` clamps its patched
height to the `push imm8` ceiling:

```cpp
long bh = std::lround(kStockBizBoxH * factor);   // 100 * 2 = 200
if (bh > 127) bh = 127;                          // push imm8 ceiling -> 127
```

This clamp is **live-confirmed**, not inferred: today's v2.55.0 log reads
`bizbox 450x127 (7 sites)` at 1.5x. So the drawn frame — the backdrop pair 0x385/0x485,
sized by two of those same five sites — is 127 tall at every tier ≥ 1.28x, while the pin
would stretch the popup window and its content to 188/250/375. Gate output:

```
DEAD BAND (hit rect minus drawn frame): [25, 61, 123, 248] px at 1x/1.5x/2x/3x
```

At 1x it is worse in kind: `if (bw != kStockBizBoxW)` skips the byte patches entirely, so
the box is stock 300x100 and the pin grows it to 125 — **1x stops reducing to stock.**

⚠ **This is a HYPOTHESIS about a code path never observed to execute.** `POPBOX` appears
**0 times** in every log in the repo (`tools/research/_checkpoints/pds-cache/SC4UIScale-snapshot.log`,
`_tests/last-selective-2x.log`, `_tests/captures/2026-07-30-border-hunt-vistrace.log`,
`_tests/captures/2026-07-31-task89-ours-baseline-SC4UIScale.log`,
`_tests/captures/2026-08-03-TIER15X-dashboard-broken-SC4UIScale.log`) — and that null is
**structural, not measured**: the only log containing a live `0x0423278D` (snapshot.log:409,
`MWKID 0.0 id=0x0423278D (30,376 840x125)`) predates the pin, and no post-pin log contains
the id at all. Nobody opened a description popup in those sessions.
The snapshot's `POPKID` dump (lines 410-416: 0x168/0x68/0x484/0x384, 840x125) is the
**ordinance** twin — a structural null for #103.

The fix below therefore does two things at once: it removes the cross-twin hazard, and it
makes the pin **say out loud** what it sees, so the next single game session settles
reachability instead of another static argument.

### THE PATCH

**File:** `<PROJECT-ROOT> 1 Project\1 Completed Projects\SC4TouchControls\src\UiSpike.cpp`

**Anchor TEXT** (exact, tabs; currently at ~12144 — match on text, not the number):

```cpp
			cIGZWin* content = pop->GetChildWindowFromID(0x0423278F);
			if (!content) { continue; }

			const float pf = settings.spikeScaleFactor;
			const int32_t wantH = static_cast<int32_t>(std::lround(125.0 * pf));
			const int32_t haveH = pop->GetH();
			if (haveH == wantH) { continue; }   // already pinned - idempotent
```

**Replacement:**

```cpp
			cIGZWin* content = pop->GetChildWindowFromID(0x0423278F);
			if (!content) { continue; }

			// TWIN GATE + POPSEEN (task #103, 2026-08-03). Window 0x0423278D
			// is built by TWO functions and only ONE has stock height 125:
			//
			//   sub_78B120  ordinance DESCRIPTION popup - H 125 (push 0x7d
			//               @0x78B99F), backdrop 0x384 / outer 0x484,
			//               close-X 0x68 / outer 0x168.  THIS is what the
			//               pin below was written for (v2.28.2).
			//   sub_77BEC0  the generic "no entries in the budget ledger"
			//               box - H 100 (push 0x64 @0x77C19E + 4 more),
			//               backdrop 0x385 / outer 0x485, close-X 0xCC /
			//               outer 0x1CC. Called from 0x77C7E6 Ordinances,
			//               0x77F51A Neighbor Deals, 0x786BA2 Transportation
			//               and 0x78826D EVERY department page.
			//
			// Both write the same dialog member [this+0x14], so only one is
			// alive at a time and the popup id alone cannot tell them apart.
			// The outer backdrop id can, and the split is TOTAL: 0x484 never
			// appears inside sub_77BEC0 and 0x485 never appears inside
			// sub_78B120 (gate tools\uimap\emu\gate_103_twin_ids.py).
			// Identify the ordinance twin POSITIVELY and act only on it -
			// fail-closed, so an unknown third builder is left alone.
			//
			// WHY: applying wantH = round(125*f) to the sub_77BEC0 box is a
			// law-43 violation of OURS. CodePatches builds that box
			// round(300*f) x min(round(100*f),127) - the height hits the
			// `push imm8` ceiling, so it ships 127 at every tier >= 1.28x
			// (LIVE: v2.55.0 log "bizbox 450x127 (7 sites)" at 1.5x). The
			// backdrop 0x385/0x485 is sized by two of those SAME five sites
			// and we never touch it, so pinning popup+content to 250 leaves
			// the frame drawn 127 and the HIT rect 250 - a 123px dead band
			// below the visible box (25/61/123/248 at 1x/1.5x/2x/3x). At 1x
			// the byte patches are skipped entirely, so the pin grew a stock
			// 100 box to 125 and 1x stopped reducing to stock.
			//
			// POPSEEN is the reachability instrument this pin never had:
			// POPBOX has printed 0 times in every log we hold, and that null
			// is STRUCTURAL (no post-pin log contains a live 0x0423278D at
			// all). One line per popup instance, unconditional, so absence
			// of the line is finally evidence.
			const bool ordinanceTwin =
				(pop->GetChildWindowFromIDRecursive(0x00000484) != nullptr);
			const bool ledgerTwin =
				(pop->GetChildWindowFromIDRecursive(0x00000485) != nullptr);
			{
				// One box exists at a time (both builders own [this+0x14]),
				// so a single pointer latch is enough. It never resets: if
				// the allocator reuses the address for the next popup the
				// line is skipped - acceptable for an instrument, and it is
				// why POPSEEN must never be used to COUNT opens.
				static cIGZWin* gPopSeen = nullptr;
				if (pop != gPopSeen)
				{
					gPopSeen = pop;
					Logger::Get().WriteLine(LogLevel::Info,
						"UiSpike: POPSEEN 0x0423278D host 0x%08X pop (%d,%d %dx%d) "
						"twin=%s action=%s",
						host->GetID(), pop->GetL(), pop->GetT(),
						pop->GetW(), pop->GetH(),
						ordinanceTwin ? "ordinance(0x484)"
							: (ledgerTwin ? "empty-ledger(0x485)" : "UNKNOWN"),
						ordinanceTwin ? "PIN" : "SKIP");
				}
			}
			if (!ordinanceTwin) { continue; }

			const float pf = settings.spikeScaleFactor;
			const int32_t wantH = static_cast<int32_t>(std::lround(125.0 * pf));
			const int32_t haveH = pop->GetH();
			if (haveH == wantH) { continue; }   // already pinned - idempotent
```

Nothing else in the block changes. The pin, the `GZWinMoveTo` clamp, the fill re-apply
and the `POPBOX` line are untouched for the ordinance twin.

**Binding safety (measured, not assumed).** The patch introduces exactly one method our
shipped DLL does not already call on this path: `GetChildWindowFromIDRecursive`. A
displacement histogram of every `FF /2 disp32` virtual call in
`build/Release/SC4UIScale.dll` shows **8 call sites at `+0x8c`** already, and the exe's
`+0x8c` in the base window vtable (0xA8D000) is the recursive lookup — the same slot the
game itself uses at `0x77C2F4` to fetch 0x485 and at `0x78BADD` to fetch 0x484.
`GetID`(+0xFC, 55 sites), `GetL/GetT/GetW/GetH`(+0xAC/+0xB0/+0xA4/+0xA8) are likewise
already in the histogram.

### What it does at each tier

| tier | ledger box today | ledger box after | ordinance popup (unchanged) |
|---|---|---|---|
| **1x** | byte patches skipped (stock 300x100); pin fires 100→125 and rewrites the body — **not stock** | untouched, exactly stock 300x100 → **reduces to stock** | `haveH 125 == wantH 125`, early-out, no-op |
| **1.5x** | built 450x127; pin → 188, 61 px dead band | stays 450x127 (matches the live `bizbox 450x127` line) | pinned to 188 as today |
| **2x** | built 600x127, close-X (538,22); pin → 250, 123 px dead band | stays 600x127, close-X (538,22) — **byte-level identical to what #61–#69 confirmed** | pinned to 250 as today |
| **3x** | built 900x127; pin → 375, 248 px dead band | stays 900x127 | pinned to 375 as today |

Blast radius: the only behaviour that can change is on windows carrying outer id 0x485,
i.e. the four `sub_77BEC0` call sites. The ordinance path is bit-identical. No patch
table, no generator, no .dat is touched.

---

## 4. THE ADJUDICATING PROBE

### 4a. The number that decides whether the fix worked

Open **City → Budget → Government** with an empty ledger, then **Budget → Ordinances →
click any ordinance row** (the in-session control), then grep the log for `POPSEEN` and
`POPBOX`.

**PASS — all three, pre-committed at 2x:**
1. `UiSpike: POPSEEN 0x0423278D host 0x........ pop (x,y 600x127) twin=empty-ledger(0x485) action=SKIP`
   — the width is **600** and the height is **127**, exactly.
2. **No** `POPBOX` line whose reported width is 600 (i.e. the pin did not run on the
   ledger box).
3. The ordinance open still produces `twin=ordinance(0x484) action=PIN` **and** a
   `UiSpike: POPBOX <w>x125 -> <w>x250 at y=...` line — the v2.28.x behaviour survives.

**FAIL — any one of:**
- a `POPSEEN … twin=empty-ledger(0x485)` line whose height is not 127 at 1.5x/2x/3x
  (or not 100 at 1x);
- any `POPBOX … -> 600x250` line;
- `twin=UNKNOWN` (a third builder exists and the discriminator is incomplete);
- the ordinance `POPBOX` line disappears (the fix over-scoped).

At other tiers substitute the gate's tier table: expected `POPSEEN` size is
**450x127 / 600x127 / 900x127** at 1.5x/2x/3x and **300x100** at 1x.

### 4b. The measurement that CLOSES #103 itself — 10 s, no build, no stock swap

The empty-ledger box is one function with one id and one handler, so any of its four
callers reproduces it. Open **Budget → Ordinances** (or **Neighbor Deals**) and click a
row with no active entry so the same box appears. The exe predicts:

- (i) its X is dead too — same box, same 0xCC;
- (ii) in the **same session**, the ordinance *description* popup's X (id 0x68) still
  closes — the in-session positive control;
- (iii) the dialog's own OK/Close makes the box vanish.

All three holding ⇒ close #103 **NOT-A-BUG (stock defect)**, exactly as #91 was closed.
If (i) fails — the X *does* close it elsewhere — the verdict is wrong and the difference
between callers is the next thing to chase. Cheaper still if it can be combined with any
already-planned session: this needs no DLL change at all.

The stronger control (`_tests\Set-StockCompare.ps1`, DLL disarmed, click the same X, with
a real mouse rather than touch) is worth running only if 4b is ambiguous.

---

## 5. THE OFFLINE GATE

Two gates, both run this session, both exit 0, both with their scope stated.

**a. `tools\uimap\emu\gate_103_closepath.py` — the verdict.** Decodes the id→branch table
and classifies each branch by whether it reaches `ChildRemove` on `[this+0x14]`.
**Positive control:** it must classify the ordinance twin's 0x68 and 0x384 as CLOSING
*before* it reports on 0xCC/0x385 — a classifier blind there would make the verdict void.
Both controls PASS; subject `0xCC`/`0x385` → does NOT close.

**b. `tools\uimap\emu\gate_103_twin_ids.py` — the fix's runtime test (new this session).**
27 checks, all PASS, `REAL_EXITCODE=0`: two and only two creation sites for 0x0423278D;
each twin's six ids present in its own builder and **absent** from the other; the five
`kBizBoxSizeSites` still `6A 64 68 2C 01 00 00`; `kBizBoxCloseX`/`kBizBoxCloseY` at their
stock values; and the id push at `0x77C2C1` verified as `68 CC 00 00 00` (we never write
it). It also prints the tier table and the dead-band row quoted in §3.
**SCOPE, stated honestly:** this gate proves the *discriminator is sound*. It does not and
cannot prove the pin ever reaches either popup, nor anything about a live hit rect.

**What cannot be gated offline, plainly:** the hit box. There is no offline model of the
live child tree or of `[this+0x14]`, and the popup is created only by user action. The
eyes-on step is §4a's `POPSEEN` line; the verdict's eyes-on step is §4b.

---

## 6. WHAT THIS DOES NOT FIX

1. **The reported symptom.** The X still will not close the box. That is stock (§2) and
   this change deliberately does not attempt to alter the game's command dispatch.
   Redirecting the `0xCC` table byte to the closing branch is a *possible* one-byte
   stock-behaviour patch, but `0xCC` currently forwards command `0x42B7C353` — an
   unidentified command that some other control in the budget dialog may legitimately
   need. Out of scope for a scaling mod, and not proposed. Blast radius unknown =
   do not ship.
2. **D1, the imm8 clamp.** The empty-ledger box stays **127 px tall at every tier ≥ 1.28x**
   instead of `round(100*f)`. It cannot be a byte fix: `6A xx` cannot encode >127 and the
   two-push site is 7 bytes where `push imm32; push imm32` needs 10. The honest options
   are (a) leave it — the frame is at least self-consistent and the user's screenshot
   shows a readable box, or (b) a runtime pin that resizes popup **+ content + 0x385 +
   0x485 together** to `round(100*f)`. (b) is a *coupled set*: all four or none, or the
   dead band comes straight back. **Separate ticket. Do not bolt it onto this change** —
   it alters the on-screen appearance of a dialog user-confirmed across #61–#69, and
   nothing today says the current 127 looks wrong.
3. **The backdrop.** 0x385/0x485 covers the whole box and is equally inert (same branch
   `0x78B406`), so clicking the box body will not close it either. Stock.
4. **Touch vs mouse.** Not investigated. §4b's control (i)/(ii) discriminates it for free:
   if the ordinance X closes with the same input method in the same session, input is not
   the variable.
5. **The name.** `kBizBox*` / "Business Deals empty box" in `src/CodePatches.cpp` is a
   misnomer for a box used by four dialogs including every department page. Renaming is
   cosmetic and deferred, but the comment at `:495` should at least gain the four caller
   addresses.

---

## 7. CORRECTIONS TO EARLIER LENSES (each re-measured here)

- **"`GZWinMoveTo` is ABSOLUTE and ~15 shipped call sites are wrong" — REFUTED, and the
  open UNKNOWN is now closed.** The base window vtable has *two* movers:
  `+0xE0 = 0x99C8C5` computes `SetArea(x, y, x+W, y+H)` (absolute) and
  `+0xE4 = 0x99BD27` adds both args to all four edges then calls `SetArea` (**relative**).
  A displacement histogram of every virtual call in `build/Release/SC4UIScale.dll` shows
  **12 sites at `+0xE4` and zero at `+0xE0`**, and **55 at `+0xFC`** (= `GetID`, whose exe
  impl at `+0xFC` is `mov eax,[ecx+0x10]; ret`). Our binary therefore calls the
  **relative** mover and the project law holds. Do not "fix" those call sites.
  ⚠ Side effect worth its own ticket: `vendor/gzcom-dll/gzcom-dll/include/cIGZWin.h` as it
  sits on disk computes `GZWinMoveTo = +0xE0` and `GetID = +0xF8`, which **disagrees with
  the shipped binary** — the DLL was built against a header with one more virtual in that
  region. An instrument that disagrees with the artifact it describes is a trap for the
  next reader; reconcile or annotate it.
- **"close-X `y = 11` is unpatched at both sites" — FALSE.** `kBizBoxCloseY = 0x77C2BA`
  exists at `src/CodePatches.cpp:501` and is written at `:1420-1426` as
  `lround(11*factor)` (expect `{0x6A,0x0B}`). Only the *ordinance* site `0x78BAAD` is
  unpatched. There is no coupled-pair violation there.
- **"the X is enum index 0 / H4 refuted / router order measured" — the evidence is the
  WRONG TWIN.** `snapshot.log:410-416` shows ids 0x168/0x68/0x484/0x384 at 840x125: that
  is `sub_78B120`. Every conclusion drawn from it is about a different window. (The
  conclusions may still be true; they are simply not measured for #103.)
- **"`edi` in `sub_77BEC0` comes from the factory, so the parent may not be top-level" —
  half right.** The factory result *is* loaded into `edi` at `0x77BF11`, but `0x77BFFF`
  reloads `edi` from the **first stack argument** before `ChildAdd` at `0x77C008`. The
  popup's parent is the caller-supplied host. Whether that host is a direct child of the
  main window — i.e. whether the POPBOX sweep can reach the ledger twin at all — remains
  **UNKNOWN**, and `POPSEEN` is precisely the line that answers it.

---

## FILES

- brief: `…\tools\research\_incoming\BUDGET-POPUP-X.md` (this file)
- new gate: `…\tools\uimap\emu\gate_103_twin_ids.py` (27 checks, exit 0)
- existing gate: `…\tools\uimap\emu\gate_103_closepath.py` (positive control passes, exit 0)
- patch target: `…\src\UiSpike.cpp` (POPBOX block, anchor in §3)
- referenced, unmodified: `…\src\CodePatches.cpp:496-501`, `:1399-1427`
- ⚠ `…\tools\research\BUDGET-DETAIL-ANATOMY.md` §P1 documents only the 0x168 twin and
  should gain the `sub_77BEC0` variant (ids 0x1CC/0xCC, 0x485/0x385, stock 300x100).
