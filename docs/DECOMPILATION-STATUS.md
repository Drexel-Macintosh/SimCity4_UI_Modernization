# SC4 UI decompilation — status

**What this file is.** One page that answers "how much of SimCity 4's UI have
we actually reversed, what does the shipping DLL touch today, and where do the
notes disagree with the code." It is a **status and inventory** document — the
front door to the engine documentation, not the documentation itself.

## Reading order

New to this corpus, read in this order:

1. **[../tools/research/](../tools/research/)** — the engine reference. Its
   index names the one file to read first and what each family document owns.
2. **[../research/laws/](../research/laws/)** — the rules, each one derived
   from a defect that reached the screen. Transferable past this game.
3. **This page** — per-screen status, then §4's inventory of every hook and
   byte patch the shipping DLL installs.
4. **[../research/UNKNOWNS-AND-NEXT-TARGETS.md](../research/UNKNOWNS-AND-NEXT-TARGETS.md)**
   — what is still open, ranked, with the refutation record behind each.

Routed by question:

| Question | Read instead |
|---|---|
| How does the UI engine work? | [../tools/research/SC4-UI-ENGINE.md](../tools/research/SC4-UI-ENGINE.md) |
| A user reported a symptom — where do I start? | [../tools/research/TRIAGE.md](../tools/research/TRIAGE.md) |
| Which side of the SDK boundary is this element on? | [../research/laws/reference-sc4-ui-sdk-boundary.md](../research/laws/reference-sc4-ui-sdk-boundary.md) |
| How was any of this established? | [../tools/research/METHOD.md](../tools/research/METHOD.md) |
| Can I check a layout claim without the game? | [../tools/uimap/](../tools/uimap/) |

**Version.** Prose rots, so this page pins nothing: the running version is
`UISCALE_VERSION_STR` in `src\SC4UIScaleDllDirector.cpp`, and the newest ledger
entry is `VERSION-HISTORY.txt:1`. Section 4's inventory was re-derived from
`src\` on 2026-08-30; §2 and §3 were last re-derived 2026-08-29. Nothing on
this page was built and the game was not launched for it.

**Provenance marks, used throughout.**

- **MEASURED** — re-derived from the tree this session, method stated inline.
- **CARRIED** — inherited from the repo's own notes, cited but *not*
  re-verified against the executable. Every VA on this page is CARRIED; the
  exe was not opened.
- **INFERRED** — a reading of measured facts, not itself a measurement.

**The grading bar this page uses, stated rather than assumed.** An element is
**DOCUMENTED** only when a measurement matched a *prediction* — the mechanism
was named, it predicted a behaviour, and the behaviour was then observed. A
mechanism named from static disassembly and never seen running is **PARTIAL**,
however confident the reasoning. This is the strict bar.

**UPDATED 2026-08-31 — the in-world overlay census is COMPLETE.** An earlier
version of this paragraph said a looser bar "would promote roughly eight of the
in-world census rows, and those rows are deliberately left PARTIAL here". Those
eight have since been closed on the *strict* bar, by measurement rather than by
relaxing the standard — see the census status below.

**The null rule applies here too.** Where a search came back empty, the
positive control that proves the search could have seen a hit is stated beside
it. A count with no control is not a finding.

---

## 1. Corpus status — who owns what

MEASURED (`ls` + heading scan, 2026-08-29). Sizes are the file's own.

| Document | Size | Owns | Last touched |
|---|---|---|---|
| `tools\research\SC4-UI-ENGINE.md` | 206 KB, 9 top sections | The GZWin engine, SDK-grade | 2026-08-24 |
| `tools\research\SDK-GAPS.md` | 70 KB, 12 sections | What the vendor SDK omits | 2026-08-23 |
| `tools\research\SC4-WORLD-OVERLAYS.md` | 42 KB, 23 census rows | Renderer-side visuals | 2026-08-24 |
| `tools\research\REGION-SCREEN.md` | 54 KB | The region screen, 197 fns | 2026-08-20 |
| `tools\research\TRIAGE.md` | 45 KB, 49 symptom rows | Symptom → cause → lever | 2026-08-20 |
| `tools\research\CITY-SITUATION-INDICATORS.md` | 16 KB | The 7-way dispatch indicators | 2026-08-24 |
| `research\UNKNOWNS-AND-NEXT-TARGETS.md` | 127 KB, §A–§H | The unknowns register | 2026-08-24 |
| `tools\uimap\coverage-matrix.md` | 86 KB | The coverage census (generated) | 2026-08-23 |
| `tools\research\FINAL-3-PERCENT.md` | 71 KB | The honest denominator (D1/D2/D3), the three unbounded creation channels, the §7 structurally-unknowable table | 2026-08-22 |
| `tools\research\overlays\row-NN-*.md` | 10 files | Per-overlay deep dives | 2026-08-23/24 |

**There was no per-screen status document before this one.** MEASURED:
`grep -rln "decompil"` over `*.md`/`*.txt`, excluding `_archive\`,
`_working-backup\` and `.claude\worktrees\`, returns 13 files, none of which is
a status table — they are the register, the laws, the ledger and two
generated slices. *Positive control:* the same grep does return
`research\laws\reference-sc4-region-screen.md`, whose first line is "The region
screen is fully decompiled", so the pattern can find a status claim where one
exists. Hence this file is **new**, not a rewrite. The register
(`research\UNKNOWNS-AND-NEXT-TARGETS.md`) remains the owner of the *backlog*;
it is organised documented-vs-unknown and carries no hook inventory.

---

## 2. Per-screen / per-subsystem status

Grading bar, taken from the register's own ("Grading bar used", head of
`UNKNOWNS-AND-NEXT-TARGETS.md`):
**DOCUMENTED** = a concrete mechanism that predicts behaviour (a VA, a struct
offset, a vtable slot, a resource type/group, or a rule with a stated control).
**PARTIAL** = mechanism named but a load-bearing piece missing, or named but
never seen running. **UNKNOWN** = exists on screen, nothing says what draws or
sizes it.

### 2.1 Screens and panels

| Screen / subsystem | Status | Evidence |
|---|---|---|
| **Region screen** | **DOCUMENTED — the most complete area in the project.** 197 functions of reconstructed code, field maps for six objects, three call-graph walkthroughs, a 17-row lever table. | `research\laws\reference-sc4-region-screen.md:3-6`; `tools\research\REGION-SCREEN.md`; tree/anchoring/lifecycle in `SDK-GAPS.md:946-1004` |
| — region cloud emitter | DOCUMENTED, fully decompiled | `SDK-GAPS.md:992-1004` — Plot `0x007A9D60`, init `0x7A99C0`, spawner `0x7A98E0`, `K=128.0f` at `0x00AB7E10` |
| — region rotation | **CLOSED AS IMPOSSIBLE** | 0 refs to rotate/angle/yaw across all 197 fns, against a stated positive control — `reference-sc4-region-screen.md`, "Measured dead ends" |
| **Budget + the eight department detail panels** | **DOCUMENTED**, and the most heavily patched family in the DLL — 4 site tables, 168 sites (see §3.2) | `SDK-GAPS.md:1040-1058` (dialog `0x0423278F`, `SetSize 0x77D33F/0x77D35F`, id bases `0x77C670/0x77C678`, row clamp `0x77C829`); `src\CodePatches.cpp:449-459, 598, 695, 798, 819` |
| **Ordinances** | DOCUMENTED | `src\CodePatches.cpp:478` (6 inset sites), `:512` (2 name-column sites) |
| **Nested plop sub-flyout** | **DOCUMENTED — "fully decoded", the most-decoded panel after the budget family** | `SC4-UI-ENGINE.md:1621-1623`; closed form `stripH = 49n−5`, `contW = 129` invariant |
| **Tool flyouts (container + strip pair)** | Container **DOCUMENTED** ("fully reverse-engineered", 279 instructions); strip **PARTIAL** — decoded field-by-field, never claimed complete | `SC4-UI-ENGINE.md:361` (container Plot `0x0079B0E0`); `:392-397` (strip Plot `0x0079AA70`, fields `[0xD8]/[0xE4]/[0xE8]/[0xF4]/[0xF8]/[0xFC]`) |
| **Data Views (fold-out + legend + map)** | DOCUMENTED. Legend origins byte-decoded; map surface snap decoded. | `SC4-UI-ENGINE.md` §2.4; `SDK-GAPS.md:1019` (`sub_007A04F0`, sites `0x7A082C`/`0x7A0955`); `src\CodePatches.cpp:904, 910` |
| **Minimap terrain bake** | DOCUMENTED, with one named hole: **zoom −3 skips every tile silently** (the bound test `cmp ecx,4 ; ja` at `0x7A8563` is unsigned) | `SC4-UI-ENGINE.md:767, :2995`; `reference-sc4-minimap-bake.md` |
| **Graphs panel / chart / legend** | Panel + legend **DOCUMENTED** (the densest VA block in the reference, 60 distinct VAs in §8.6); the **chart itself is code-painted and art-unreachable** | `SC4-UI-ENGINE.md` §8.6 (`:3006`); `:1539-1543` |
| **HUD + mayor-rating controller** | DOCUMENTED — 22 distinct VAs in §8.4 | `SC4-UI-ENGINE.md:2948`; `src\CodePatches.cpp:28` (3 `imul ,7` sites at `0x7E87B1/0x7E89D7/0x7E8A02`) |
| **News / ticker / rich text (HTML engine)** | DOCUMENTED — sizes live in `.rdata` tables and can never be reached from `FontStyle.ini` | `SC4-UI-ENGINE.md` §8.3 (`:2934`); `reference-sc4-html-text-engine.md`; `src\CodePatches.cpp:321, 323` |
| **Tooltips** | DOCUMENTED as a mechanism, and **structurally geometry-only**: the tip layer code-paints the whole tooltip, no child windows exist | `SC4-UI-ENGINE.md:1544-1545`; 250px wrap at `0x79880A`/`0x7988A9`, `src\CodePatches.cpp:41` |
| **Static dialogs** | DOCUMENTED via the `.UI` corpus + the staged-art path | `tools\research\FONTS-AND-DIALOGS.md`; `tools\dialog-static\` |
| **Graphics Options selector** | **PARTIAL** — rewritten after the register's cut-off and not folded back into any reference | ⚠ **CORRECTED 2026-08-31 — the second half of this row's grade cell ("not folded back into any reference") is SUPERSEDED and wrong; the PARTIAL grade itself is right, for a different reason.** The method half IS in a reference — three laws, all three carried in `research\laws\README.md`'s index — and two gates pin it: `research\laws\feedback-state-machine-derive-diff-commit.md` (the state struct, the pure derive, diff-apply, commit-at-close, and the request-vs-effective split), `research\laws\feedback-selector-freeze-named-by-instrument.md` (the ~3.3 s first `EnumDisplaySettingsW` through dgVoodoo and the warm-at-DLL-load cure; `SELPERF` stays in the shipping build so the cure is re-measurable), `research\laws\feedback-liveness-guard-stored-window-pointers.md` (locate-in-this-pass, branch on null). Our rewrite is **v3.14.0**, commit `895efe6`, 2026-08-20. Source: `src\UiSpike.cpp`, banner `// ============ IN-GAME SCALE SELECTOR (v3.14 STATE MACHINE)` through `void UiSpike::ServiceScaleSelector()`, naming `struct SelState`, `SelDerive`, `SelApply`, `SelOnClose`; tick entered from `src\SC4UIScaleDllDirector.cpp` (grep `uiSpike.ServiceScaleSelector()`). Gates, both run green 2026-08-31: `_tests\Test-SelectorDerive.py` (the rule, written FIRST) `ALL PASS (23 checks)`; `_tests\Test-SelectorContract.py` (source shape) `ALL PASS`, carrying three negative controls. **What stays PARTIAL is the GAME's dialog, not our rewrite:** its `.UI` script and window roots are decoded — script `I-8a7e052f`, root `GZWinGen 0x2A57CB82` at `(3,0,725,558)`, 81 controls all handled (`tools\dialog-static\REPORT-15x.md`), inner `0x2A57CB84` gutters `(247,201)` (`SDK-GAPS.md` §7), `kTallestDesignPx = 558` (`SC4-UI-ENGINE.md`), and the widget class `GZWinCombo` Plot `0x009CF241` / ctor `0x009CF772` / factory `sub_7798C0` — but **no VA is recorded anywhere for its builder, its combo-population routine, or its Accept/Cancel handler**, and the hide-from-menu / destroy-in-city lifetime is known **behaviourally** (it faulted a process) rather than from decoded code. ***Positive control for that null:*** the same corpus does return dialog-**code** VAs when it has them — the budget dialog `0x0423278F` and Data Views `sub_007A04F0`, both cited in rows above — so the search is demonstrably capable of hitting; it returns none. Provenance: MEASURED 2026-08-31 (greps + both gates executed); every VA quoted is **CARRIED** (the exe was not opened). The register still correctly flags the rewrite as post-dating itself at `UNKNOWNS-AND-NEXT-TARGETS.md:7` (the root CONTINUITY.md originally cited here was deleted 2026-08-29 as a stale progress recap; its durable content was promoted into that same register, so there is no file to open) |
| **City LOADING / SAVING screen** | **CLOSED AS UNREACHABLE** — no `.UI` in the 339-file corpus and never appears in a window dump | `UNKNOWNS-AND-NEXT-TARGETS.md` §C row 1 |

### 2.2 Widget classes

MEASURED (heading scan of `SC4-UI-ENGINE.md:328-352`): the catalogue table has
**17 data rows covering 18 classes** (one row bundles two vtables), plus **6
more classes/objects documented in §2 outside the table** (both buffer classes,
base `cGZWin`, the router, `cSC4WinAlertBorder`, `cSC4WinAuraBar`).

| Bucket | n | Classes |
|---|---|---|
| **DOCUMENTED** (clsid/vtable/ctor/Draw all present, doc claims byte-verification) | **9** | `GZWinBMP`, `GZWinText`, `GZWinBtn`, `cSC4WinGenTransparent`, `cSC4WinText`, `cSC4WinRCI`, `cSC4WinTrendBar`, `cSC4WinAlertBorder`, `cSC4WinAuraBar` |
| **PARTIAL** (mechanism known, a named piece missing) | **5** | `cSC4WinAdviceList` (guard is id-keyed — "STRUCTURAL WEAKNESS, noted not fixed", `:342`), `cSC4WinMiniMap` (the zoom −3 hole), flyout strip, the second buffer class `0x00ADB418` ("can take a renderer path under dgVoodoo", `SC4-UI-ENGINE.md:526`), `cSC4WinMapView` (`0x00AB8150` disambiguated as *not* its window vtable, `SDK-GAPS.md:736-739`) |
| **THIN / STUB** (attribute-level only, no ctor or Draw decoded) | **4** | `GZWinTextEdit`, `GZWinSpinner`, `GZWinGrid`, `GZWinFlatRect` |
| **UNNAMED but measured** | **2** | the gauge class `0xCBCBF1E0` — **now fully identified in BOTH files (MEASURED 2026-08-31)**: `SDK-GAPS.md` §8.1 *and* `SC4-UI-ENGINE.md` §2's own `0xCBCBF1E0` catalogue row each carry outer vt `0x00AB4900`, window vt `0x00AB46A0` at `obj+4`, factory `0x00466220` (returns base+4), the slot-88 painter `0x00762830`, ctor `0x007628E0`, custom iid `0x0BCBF1DF` and the `0x108`-byte size. ⚠ *Superseded 2026-08-31, kept: this cell read "(`SDK-GAPS.md:740-742` has factory `0x00466220`, Plot `0x00762830`, ctor `0x007628E0`, iid `0x0BCBF1DF` — but the reference's own catalogue row `:344` still carries no factory, ctor, vtable or Plot VA and is symptom-level)". The row WAS updated, and both line numbers had drifted (`SC4-UI-ENGINE.md:344`→`:373`, `SDK-GAPS.md:740-742`→`:1003-1005`) — which is why the anchors above are sections and row ids, not line numbers.* — **see drift D-4 (CLOSED)**. Still open: both files name `0x00762830` **`Plot`**, but it sits at **slot 88 = `GZPaint`** — **see drift D-4a**. And the clip-viewport subclass at vt `0x00ADCB38` (`SDK-GAPS.md` §8.1) |

⚠ **The class population is printed two ways.** `SDK-GAPS.md:808-809` said "12 of
the **115** classes"; `SDK-GAPS.md:73-76` says "all **111** window-class
vtables … a superset of the **29** named classes". Was unreconciled — drift
D-5, **CLOSED 2026-08-30**: `SDK-GAPS.md` now splits the counts by instrument
(**116** slot-87 single-marker / **111** ≥3-of-8 census / 5 named extras) and
the `:808` count re-measures to **13** of the 111 census classes.

### 2.3 Renderer-side / in-world overlays

MEASURED (row scan of `SC4-WORLD-OVERLAYS.md:442-464`): **23 census rows,
tally line at `:466-470` reads "23 rows, every owning system identified."**

The census has **no reachability column** — its column is `tier scaling`. That
maps as follows (INFERRED mapping, the file does not draw it):

| `tier scaling` verdict | n | Rows |
|---|---|---|
| `scaled by <named lever>` — pixel-fixed, lever found and shipped | **4** | 1 (UDI offer balloon), 3 (mission bubble), 5 (dispatch markers), 16 (route overlay) |
| `correct` — already right at every tier, no lever wanted | **4** | 2, 9, 20, 21 |
| `n-a` — world-anchored or zoom-ramped, a lever would be a defect | **15** | 4, 6, 7, 8, 10–15, 17–19, 22, 23 |

**Depth is uneven and the row files say so.** MEASURED
(`ls tools\research\overlays\` + grade scan of the `CURRENT GRADE` line each row file now carries under its title): 10 of 23 rows have
a dedicated file. **The census is now COMPLETE — every row that was PARTIAL
or UNKNOWN has been closed on the strict bar.** The eight this page used to
list as "static disassembly, never screen-proven" (8, 10, 11, 12, 13, 14, 15,
16) are done, and three of them killed a standing attribution rather than
confirming one:

| row | outcome |
|---|---|
| 4, 8 | CLOSED — confirmed on screen; row 4 is not a separate visual, row 8 needs no patch |
| 10, 11, 12 | MEASURED, confirmed live |
| 13 | MEASURED + DECODED |
| 14 | **TRUE NULL** — the attribution was REFUTED, and the negative is written down |
| 15 | **DOCUMENTED** — the connection arrow is sized by its own S3D model vertices. The exemplar `OccupantSize` route was **refuted** (×8 on one axis left a 0.4% aspect change), correcting this repo’s own claim that "the size is exemplar data for this family" |
| 16 | **DOCUMENTED** — the route trace is a dedicated `cISC4ViewObject3D` (drawer `0x007DD9B0`, vtable `0x00ABB648`, layer 5 key `0x3E8`). **Three** attributions died here: named effect, the signpost-occupant module, and a per-tile occupant highlight flag |

Rows 15 and 16 were each closed against a prediction written down *before* the
run — row 16’s into `SC4UIScale.ini` itself, so it could not be reinterpreted
afterwards. Row 23 (zots) remains DOCUMENTED from 2026-08-24.
Rows 1 and 5 are covered by `CITY-SITUATION-INDICATORS.md` instead.

**A caution earned closing these rows.** Three separate measuring instruments
failed *clean* during row 15 — each returned a confident, plausible number while
measuring the wrong thing: a detector whose "arrows" were the pause button and a
permission toast; SC4’s own full-frame paused border reported as the widest
arrow; and a normaliser that had locked onto the very object it was correcting
for, returning a perfectly circular 1.854. None announced itself. Any number on
this page that came from a detector deserves the question *what would this
instrument have reported if it were broken?*

**The last genuinely unowned overlays item is now OWNED (2026-08-31).**
`.rdata 0xAB4330` = `{1.0,2.0,4.0,8.0,16.0}`, consumer `0x751CB5` in
function `0x751C80`, belongs to **`cSTETerrainView3D`** (GZCLSID
`0xC9B84E10`) — the terrain/water mesh texture-coordinate regenerator. It
**touches nothing this mod scales**: zero `.text` references into the
terrain `.rdata` window from anywhere in the UI band, against a control of
5,175 UI-band `.rdata` references found by the same scanner in the same
pass. Superseded reading kept for the record: "module/subsystem
unidentified — shape suggests an LOD/mip scale-by-zoom helper". See
`SC4-WORLD-OVERLAYS.md` for the three independent identification lines.

---

## 3. The three-way boundary classification — current tally

The project's triage (`research\laws\reference-sc4-ui-sdk-boundary.md:21-35`)
scores three questions — (a) ever a window in a full-depth dump? (b) art in any
dat? (c) spans or overlays the 3D view? — into three buckets.

| Bucket | Members today | Evidence |
|---|---|---|
| **ART REACHABLE + GEOMETRY REACHABLE** (a real window: the sweep, the `.UI` pass and art overrides all apply) | **Everything in the shipped UI that has been tested** | `SC4-UI-ENGINE.md:68-69`: "**No element of the shipped UI is known to sit outside the boundary**, and two elements once believed to be outside it are on the inside." |
| **ART REACHABLE + GEOMETRY NOT** (never a window, drawn over the 3D view, art *is* a stageable dat resource) | **0 confirmed — see D-1. The law file still names one; that element was cured as a window ten days before the law file was last edited.** | Contradiction between `reference-sc4-ui-sdk-boundary.md:51-70` and `UNKNOWNS-AND-NEXT-TARGETS.md:384-403` (§H.5), settled against the source in §4 below |
| **RENDERER-DRAWN / WHOLLY UNREACHABLE** | **0 named members. The bucket is defined structurally, never populated.** | `SC4-UI-ENGINE.md:107-110` — anything spanning the screen without owning a window "is being drawn in the render / present path, which **this project has never decoded** and for which none of its instruments are scoped" |

**The two historical mis-classifications, both now inside the boundary**
(CARRIED, `SC4-UI-ENGINE.md:72-99`):

| Element | Was called | Is | Why the null was false |
|---|---|---|---|
| Paused / sim-speed screen-edge border | outside | `cSC4WinAlertBorder`, id `0x6A5E44B6`, vt `0x00AB5B48`, clsid `0xCA5D3294` (`SDK-GAPS.md:744-762`) | Born full-screen and **never flips visibility** — every probe was a visibility/render-side check |
| Region bubble Mayor Rating bar | outside | `cSC4WinAuraBar`, clsid `0xAA5D16A9`, id `0x4A553000` | An `RGKID` dump that stopped one level short, plus an A/B against a different class entirely |

`TRIAGE.md:68-69` already carries the standing warning: *"If the symptom
matches a row but the current diagnosis says 'unreachable', suspect the
DIAGNOSIS (law 34). That exact combination has been wrong twice."*

**It is about to be wrong a third time, and §4's D-1 is that finding.**

### 3.1 A separate, genuine "art unreachable" class

Not the same thing as the boundary buckets, and easy to conflate. CARRIED,
`SC4-UI-ENGINE.md:1518-1553` — **Path 4, runtime-generated with no TGI**: the
window is ordinary and geometry-reachable, but "**the PIXELS are unreachable by
any art pass — they are not in any dat**" (`:1520`).

| Element | Art | Geometry |
|---|---|---|
| My Sims portraits (HUD `I-aa1f1f57`; picker `I-0a243d80`) | unreachable | reachable — but the picker's rect must **not** double (`:1527-1533`) |
| Advisor faces (live 3D head renders, binder `0x41DE20`) | unreachable | reachable |
| Gauge dials `0xCBCBF1E0` | unreachable — TGIs staged 2x and they **still draw small** (`:1550-1553`) | window yes, cached buffer no |
| Graphs chart | unreachable — **but its LEGEND is reachable by a byte patch and by nothing else** | legend yes |
| Tooltips | unreachable — code-paints the entire tooltip | no child geometry at all |

Unifying symptom (`:1547-1548`): **a correctly 2x window with its content
pinned in the top-left quadrant.**

---

## 4. Hook and patch inventory — what the DLL actually touches today

All of §4 is **MEASURED 2026-08-29** against `src\`. Methods are stated so the
counts can be re-derived.

### 4.1 Detours (MinHook)

**Method:** `grep -c "MH_CreateHook("` per file. This counts *static call
sites*, not hooks installed at runtime — every one is behind a gate.

| File | Sites | Targets |
|---|---|---|
| `src\CodePatches.cpp` | **22** | Game-exe functions. 19 resolve a fixed VA; **3 resolve through a live vtable** (`vt[0x80/4]` at `:8083`, `vt[0x54/4]` at `:8100`, and `:8164`) and are bounds-checked to `0x401000..0xA80000` before use |
| `src\UiSpike.cpp` | **7** | Game-exe functions, all fixed VAs |
| `src\ScaleRemap.cpp` | **1** | A loop over a **9-row** `HookSpecEx` table (`:430-439`) of `user32`/`gdi32` exports — `GetCursorPos`, `SetCursorPos`, `ClipCursor`, `GetSystemMetrics`, `GetDeviceCaps`, `GetClientRect`, `GetWindowRect`, `SetWindowPos`, `MoveWindow`. **9 hooks from 1 site** |
| `src\WebRedirect.cpp` | **2** | `shell32!ShellExecuteA` / `ShellExecuteW` |
| `src\ScaleTier.cpp` | **0** | *Positive control:* the same grep returns 22 for `CodePatches.cpp` in the same invocation, so a zero here is a real zero. `ScaleTier.cpp` is the tier/data layer and installs no detours |
| **Total static sites** | **32** | of which **29 target game-engine functions** and **11 target OS exports** (9 + 2) |

**The 29 engine detour targets** (CARRIED VAs, MEASURED presence in source):

| VA | Role | Site |
|---|---|---|
| `0x7AE3D0` | region per-buffer builder | `CodePatches.cpp:1605` |
| `0x7AE510` | region item build | `:2007` |
| `0x7E8510` | mayor-rating update | `:4158` |
| `0x0046D990` | `cSC4DispatchVehicleView::Draw` (CSI) | `:4418` |
| `0x007D2990`, `0x0046F240` | GL dispatch quad / add | `:5151`, `:5154` |
| `0x602B70` | art fetch | `:6618` |
| `0x004FBFE0` | TagKind balloon builder | `:6902` |
| `0x00505370` | sprite factory | `:6930` |
| `0x5F20A0`, `0x5F1610` | signpost quad / texture | `:6967`, `:6970` |
| `0x5FD2D0` | draw (vt4 +0x18) | `:6986` |
| `0x496950`, `0x528580`, `0x4D7950`, `0x5F7C80` | sprite bind / target / hover / attach | `:7002`–`:7051` |
| `0x5F5FB0` | marker strip builder | `:7067` |
| `0x9C16FD` | `SetFontStyleByGuid` | `:7549` |
| `0x5939B0` | `CreateEffectByName` | `:7716` |
| `vt+0x80 → 0x007C5D90` | `cISC43DRender::AddViewObject` | `:8083` |
| `vt+0x54` | renderer draw | `:8100` |
| `vt+0x104` | renderer pick | `:8164` |
| `0x0099C498` | `PlotPresent` | `UiSpike.cpp:3445` |
| `0x0079AC60` | sub-flyout vf10 | `:6621` |
| `0x007E5C10`, `0x007E5D80` | flyout open (two entry points) | `:7788`, `:7807` |
| `0x0079A0E0`, `0x0079AD00` | sub-flyout `SetItemMetrics` / `Place` | `:8215`, `:8223` |
| `0x0099DB6B` | `cGZWin::SetFlag` — the born-correct hook | `:8668` |

⚠ **§4.1 SUPERSEDED 2026-08-31 — THE COUNTS AND 20 OF THE 27 LINE NUMBERS ABOVE ARE WRONG. Re-run the method before quoting any number here.** The counts and citations above were correct against `5df8663` (2026-08-30) and were overtaken by the next day's eight commits; this page was itself edited on 2026-08-31 without re-running its own stated method. **Kept, not deleted — they are the evidence for the law below.**

**MEASURED 2026-08-31 by `grep -c "MH_CreateHook("`:** `CodePatches.cpp` **26** (was 22), `UiSpike.cpp` **7**, `ScaleRemap.cpp` **1** (still a 9-row `HookSpecEx` table), `WebRedirect.cpp` **2**, `ScaleTier.cpp` **0** (positive control: the same invocation returns 26 for `CodePatches.cpp`, so the zero is real). **Total static sites 36** (was 32), of which **33 target game-engine functions** (was 29) and 11 target OS exports.

**The four detours the old count of 29 was missing**, VA constants read from source, roles taken from each installer's own miss-log string: `0x5E90E0` occupant highlight (`kHighlightVa` / `HighlightDetour`); `0x6CC970` zone display-quad builder (`kZoneQuadVa` / `ZoneQuadDetour`, same VA as census row 13 of `SC4-WORLD-OVERLAYS.md`); `0x5F7810` UDI route-dot size (`kDotSizeVa` / `DotSizeDetour`); `0x6D4860` neighbour-connection arrows (`kNborArrowVa` / `NborArrowDetour`). ⚠ These are MEASURED **present in `src`** and have **never been observed running** — under §0's own bar they are PARTIAL, not DOCUMENTED. The tree is also not the shipped v4.7.0 DLL: `CHANGELOG.md` carries an **Unreleased** section.

⭐ **WHY THIS SECTION NOW CITES BY SYMBOL.** Of the 27 `file:line` rows above, **6 resolved** to the hook they name within ±12 lines. The split is the whole finding and it is clean: all **7** `UiSpike.cpp` rows resolved (that file is byte-identical to `5df8663`); **0 of 20** `CodePatches.cpp` rows resolved (that file took **+1,632 / −58** lines over eight commits dated 2026-08-31). *Positive control:* the same checker found all seven `UiSpike.cpp` rows, so the zero on the other side is a real zero. Both halves were written the same day, by the same author, by the same method, into the same table — the split tracks **which file was edited**, nothing else. Largest drift: `AddViewObjDetour`, cited `:8083`, now `:9777` — **1,694 lines short**. **A line number in this corpus had a shelf life of one day.** Cite the hook by its symbol (`AddViewObjDetour`, `RenderDrawDetour`, `PickDetour`, `kCsiDrawVa`, `PlotPresentDetour`, `SetFlagDetour`, …); a symbol survives 1,632 inserted lines above it and a line number does not.

**Scope of this audit, so it is not over-read:** §4.1's 27 rows were audited exhaustively. The page carries **128** `file:line` citations in all (60 fully qualified, 68 bare `` `:N` `` continuations); a hand audit of the 60 put roughly **23** on text that supports the claim they anchor. **The rest of the page is NOT converted and stays open.** Named misses, each with the grep that resolves it: §2.2 `SC4-UI-ENGINE.md:328-352` → grep `Size determined by`; §2.2 / §5.1 D-4 `SDK-GAPS.md:740-742` → grep `The gauge class`; §2.2 / D-5 `SDK-GAPS.md:808-809` → grep `116, 115 and 111 are`; D-4 `SC4-UI-ENGINE.md:344` → grep `0xCBCBF1E0`; §4 `SC4-UI-ENGINE.md:68-69` → grep `No element of the shipped UI`; §4 `SC4-UI-ENGINE.md:107-110` → grep `render / present path`. **The last two are the worst shape this defect takes: a sentence in quotation marks attributed to lines that do not contain it reads as verified and is not.**

⚠ **Two substantive claims elsewhere on this page went stale in the same pass and are left OPEN, not fixed here.** §5.1 **D-7** says the shipping macro "is **4.4.0**" — right anchor (grep `UISCALE_VERSION_STR`), but it now reads **4.7.0**. §5.1 **D-3** says `research/START-HERE.md:38` carries the "~30 byte-patched layout constants" figure; that file now says "18 feature families across 36 site tables, **295** individual patch sites", which also disagrees with D-3's own "36 named families, 274 sites". Three numbers for one quantity; both need a re-derivation, not a citation fix.

### 4.2 Vtable-slot hooks (not MinHook, counted separately)

**Method:** `grep -n "VirtualProtect.*vt\|vtCopy"` plus reading each hit.

| Mechanism | Slot | Site |
|---|---|---|
| `PatchFlashGuardClass` — patches **class** vtable slot 88 (Plot) for up to `kFgMax` classes | 88 | `UiSpike.cpp:4573-4591`, 5 call sites |
| `EnsureBufferClassBltHook` — patches buffer-class vtable **slot 29** (`Blt`) | 29 | `UiSpike.cpp:6777-6797`, 7 call sites |
| `InstallVtCap` — copies a vtable to a private instance copy | n/a | `CodePatches.cpp:6225, 6263-6296` |

⚠ The house rule (`SC4-UI-ENGINE.md` §A.5 / `reference-sc4-thiscall-hook-rule.md`)
is **swap the vtable on the instance, never the class**. `PatchFlashGuardClass`
and `EnsureBufferClassBltHook` are *class*-level by name and construction. Both
are probe/guard machinery rather than geometry surgery, but the divergence is
not noted anywhere in the reference — **drift D-6**. **Corrected 2026-08-31:** that clause is superseded and kept for the record. **The divergence IS documented** — `SC4-UI-ENGINE.md` **§2.5** (heading `### 2.5 HOOKING RULES`) names both as the two deliberate, permanent exceptions and gives the reason for each. See **§5.1 D-6**, now mostly closed; the only surviving gap is the memory note `reference-sc4-thiscall-hook-rule.md`, which still carries the law with no exceptions attached. ⚠ **The citation "§A.5" above is a DEAD ANCHOR** — MEASURED 2026-08-31, `SC4-UI-ENGINE.md` has no §A section at all; its top-level headings run `## 0.` through `## 9.`, and the string `A.5` returns zero hits. *Positive control:* the same pass listed all ten `## N.` headings, so it can see headings. The correct anchor is **§2.5**, addressed by its heading text.

### 4.3 Byte-patch sites

**Method:** a script over `CodePatches.cpp` and `UiSpike.cpp` matching
declarations `k<Name>Site` / `k<Name>Sites`, following the initialiser across
lines to its `;`, stripping `//` comments, and keeping hex literals in
`0x400000..0xC00000`.

> **Result: 30 named site tables, 263 site slots, 263 distinct VAs.**

*Positive control for the scan:* the same pass separately resolved **21
single-VA hook-target constants** (`k…Va`) with only 1 address overlapping the
site set, and its per-table counts match the arrays read by hand — 20 for
`kBudgetBtnSizeSites` (`CodePatches.cpp:449`) and 10 for `kBudgetBtnYSites`
(`:459`). The scan can see both shapes and tells them apart.

**263 is a floor, and the exclusions are named.** MEASURED by diffing the scan
against the `WIDTHS` registry in
`tools\uimap\emu\gate_patch_families_combined.py:57`: **6 real patch families
are registered in the gate but invisible to a `k…Site` regex** because they are
named otherwise — `kGraphLegendBlocks` (3 entries, `CodePatches.cpp:1001`),
`kPopupStyleRetargets` (4, `:336`), `kBizBoxCloseX`/`kBizBoxCloseY` (1 each,
`:863`/`:864`), `kHtmlFontSizeTable`/`kHtmlHeadingSizeTable` (`.rdata` bases at
`:321`/`:323`, 7 dwords each).

> **Honest total: 36 named patch families, 274 site slots.**

**RE-MEASURED 2026-08-30 at v4.5.9, and the counting is now the gate's, not a
regex's.** The 40 symbols that were unregistered on 2026-08-29 (the six named
above plus 34 more that had accumulated across five feature arcs) were each
classified by reading the applier — a `Site` suffix does not make a site, and
three of them turned out to be `.rdata` data tables rather than instruction
streams. With every symbol registered, the gate itself now reports the
population, so a scan and a registry can no longer disagree:
>
> **18 feature families, 36 site tables, 295 site spans**
> (`python tools\uimap\emu\gate_patch_families_combined.py --verbose`).
>
> The three groupings are not interchangeable and were previously conflated:
> a **family** is one ini-gated applier (what a user turns on), a **table** is
> one `k…` array or scalar in the source, a **span** is one contiguous byte
> range verified and written. The v4.5.9 additions since the 274 figure are
> the cheat dialog (`kCheatRectSite` 32 bytes, `kCheatClearSite` 39) and the
> restore-toolbars origin (`kRestoreToolbarsOriginSite`, one 6-byte block
> holding both placement constants deliberately, so a half-applied state is
> unreachable).
>
> The gate had been failing this whole time, and long enough that the
> composition of its redness drifted unnoticed — the failure its own header
> warns about, where a standing red makes every later red look pre-excused. It
> is green as of 2026-08-30, verified with a mutation control (unregister one
> table in a scratch copy → the gate fails on exactly that table).

| Family | Sites | Family | Sites |
|---|---|---|---|
| `kDeptImm32Sites` | 62 | `kOrdinanceInsetSites` | 6 |
| `kBudgetSubImm8Sites` | 53 | `kRegionIso2Sites` | 6 |
| `kDeptImm8Sites` | 36 | `kBizBoxSizeSites` | 5 |
| `kBudgetBtnSizeSites` | 20 | `kBudgetBtnXSites` | 5 |
| `kBudgetLeaDisp8Sites` | 17 | `kGraphLegendImmSites` | 5 |
| `kBudgetBtnYSites` | 10 | `kIntroVidSites` | 4 |
| `kRegionIsoSites` | 4 | `kDataViewLegendLeaSites` | 4 |
| `kDataViewLegendImm32Sites` | 4 | `kPopupStyleRetargets` | 4 |
| `kRatingImulSites` | 3 | `kSubFlyoutProviderSites` | 3 |
| `kGraphLegendBlocks` | 3 | `kTipWrapSites` | 2 |
| `kOrdinanceNameXImm8Sites` | 2 | `kMasterNotchSites` | 2 |
| 14 single-site families | 14 | | |

**The budget/department family alone is 168 of 274 sites (61%)** — INFERRED
from the table above (62+53+36+17 = 168). That is where the byte-patch risk is
concentrated, and it is why the combined-family gate exists.

### 4.4 Exe addresses referenced by the DLL

**Method:** distinct hex literals in `0x400000..0xC00000` after stripping `/* */`
and `//` comments.

| File | Distinct exe VAs |
|---|---|
| `src\CodePatches.cpp` | **380** (`0x7xxxxx` 296, `0xAxxxxx` 25, `0x4xxxxx` 22, `0x5xxxxx` 19, `0xBxxxxx` 13, other 5) |
| `src\UiSpike.cpp` | **40** |
| `src\SpinProbe.cpp` | **5** |
| `src\ScaleTier.cpp`, `WebRedirect.cpp`, `ScaleRemap.cpp` | **0** each |

For scale: `SC4-UI-ENGINE.md` tabulates **272 distinct VAs in §8** and **490
across the whole document** (CARRIED from a §8-range scan of
`0x[0-9A-Fa-f]{6,8}` plus `sub_NNNNNN`, filtered to the image range). So the
DLL touches a set of comparable size to the reference's own catalogue — but
**they are not the same set**, which is drift D-3.

### 4.5 Runtime id lists (which screens the sweep names)

**Method:** array-declaration scan of `UiSpike.cpp`, counting distinct
`0x........` literals per list.

| List | ids | Line |
|---|---|---|
| `kAlwaysScaleCityIds` | 34 | `UiSpike.cpp:5833` |
| `kNeverScaleIds` | 21 | `:5375` |
| `kBmpxCityRoots` | 14 | `:12790` |
| `kDataScaledSubtreeIds` | 10 | `:5987` |
| `kRegionPanelIds` | 9 | `:5341` |

`kRegionPanelIds` = 9 matches `SDK-GAPS.md:960-962`'s "nine panels = the
complete whitelist" exactly — MEASURED agreement between doc and source, the
only one of the five lists the reference states a number for.

---

## 5. Drift

### 5.1 The doc says something the source contradicts

**D-1 — ⛔ THE SDK-BOUNDARY LAW STILL NAMES A CURED ELEMENT AS ITS ONE
"GEOMETRY UNREACHABLE" INSTANCE. Highest-value item on this page.**

`research\laws\reference-sc4-ui-sdk-boundary.md:51-70` heads a section "The
third category: art reachable, geometry unreachable" and states: *"The confirmed
instance is the 'move in a sim' marker over the city view: its portrait art is
reachable, its geometry is not."* It goes on to prescribe the only cure as "a
size constant in the renderer's own path".

That element was **closed as an ordinary window pair ten days before the law
file was last edited.** `UNKNOWNS-AND-NEXT-TARGETS.md` §H.5, the heading
"CORRECTION — #191's real cause was a GZWin pair, not S3D/renderer-side",
records that the 37-dump window-layer null was itself false — the marker's
windows first appear in dump #5 and the baseline was the first 5, so a
persistent show/hide pair could never register as "new". The marker is
`0x27DF05BE` / `0x27DF05BF`, parented to the 3D-view root, each with a
`GZWinBMP` plate child. **CLOSED 2026-08-19, user-confirmed.**

MEASURED IN SOURCE 2026-08-29 — the cure is live and shipping:

- `src\UiSpike.cpp:12841` — both ids are entries in `kBmpxCityRoots`
- `src\UiSpike.cpp:16800-16801` — `const bool worldAnchored = (win->GetID() == 0x27DF05BE || win->GetID() == 0x27DF05BF);` gates the `GZWinMoveTo` skip
- `src\UiSpike.cpp:5470-5474`, `:12810-12815`, `:16610`, `:16780-16786` — five more live references naming the pair by role

**Consequence: the "art reachable, geometry not" bucket has zero confirmed
members today.** The register's §H.2, which minted the category, derives it
entirely from the §H.1 row "Is the marker a window? SOLVED — NO" — and §H.5
marks that exact row ⛔ WRONG. The law file inherited §H.2 without §H.5.

This is the third instance of the failure mode the law file itself documents.
The category may still be real as a *shape* — the reasoning about art loading
while the renderer computes its own size is sound — but it currently has **no
confirmed member**, and the file must say so rather than name a cured window.

✅ **D-1 ALREADY RESOLVED IN THE LAW FILE, TWO DAYS BEFORE THIS PAGE WAS WRITTEN. Re-adjudicated 2026-08-31; nothing is owed in `reference-sc4-ui-sdk-boundary.md`.** MEASURED against the law file itself, not a summary: its section `## The third category: art reachable, geometry unreachable` now opens with **"⛔ THIS CATEGORY HAS ZERO CONFIRMED MEMBERS. Corrected 2026-08-29."** (grep `ZERO CONFIRMED MEMBERS`, 1 hit, line 64 — *inside* the `:51-70` range D-1 cited as contradicting it). The banner names the pair `0x27DF05BE`/`0x27DF05BF`, records the 2026-08-19 user-confirmed close, and hands over the two cure sites by symbol (grep `kBmpxCityRoots`, grep `worldAnchored`). The sentence D-1 quoted — *"The confirmed instance is the 'move in a sim' marker…"* — is **gone**: `grep -n "The confirmed instance is"` returns nothing, and the positive control for that null is the hit in (1) over the same path. Chronology: the law file's last commit is `7f25298` (2026-08-30); this page's is `d15e30a` (2026-08-31). **The claim above was CARRIED, never MEASURED** — its source is the register's header bullet, which still reads "…`reference-sc4-ui-sdk-boundary.md:51-70` still names it and needs the same correction" (grep `still names it and needs the same correction`). **That bullet is now the last stale copy, and striking it is the only edit D-1 still owes anywhere.** The classification verdict is unchanged and both files state it: the "ART REACHABLE + GEOMETRY NOT" bucket has **zero confirmed members**.

**D-1a — D-1's own line citations had drifted.** Four of six no longer point at what they name: `:12841` (ids are one entry line at 12864), `:16800-16801` (`worldAnchored` is 16823-16824), `:16610` (`kOwnsBackgroundSheet` is 16632-16633), `:16780-16786` (unrelated `StoreScaleRecord`). Two still land. "Five more live references" was an undercount stated as a count: `grep -c 0x27DF05BE` = **9**. This page walked into its own "the symbol is the anchor" law inside the item that enforces it.

**D-1b — OPEN, documentary only, no behavioural claim.** Inside `kNeverScaleIds`, `0x27DF05BE` is a live entry while the comment four lines below states *"ONLY the ...BF twin. `0x27DF05BE` is NOT here on purpose"* and argues that listing BE would reach the Obliterate City confirm (`I-2a41436c`). Both arrived in the same squashed publish commit, so `git blame` cannot date them. Per this repo's law a static contradiction is a **hypothesis**, so nothing is asserted about behaviour and no code changes.

**Residual, deliberately NOT filed as drift:** the law file's tail still uses the marker as a worked example that "the module owning a resource is often not the module drawing it" (grep `the portrait preload sits at`, line 86). That sits *below* the banner and does not re-assert membership. Leave it.

**D-2 — Coverage is quoted at a superseded denominator.**
`UNKNOWNS-AND-NEXT-TARGETS.md` §A.5 states "D1 = 298 script-declared roots, 288
covered (96.6%); D2 = 17 code-created named windows, 11 covered (64.7%);
combined 299/315 = 94.9%". MEASURED: `tools\uimap\coverage-matrix.md:16` makes
the canonical headline **86/117 distinct root ids = 73.5%**, re-measured
2026-08-16, and `:50-56` explicitly lists 94.9% among the looser views that were
being "quoted interchangeably, which is exactly how #99 hid for weeks". The
same file states `coverage_rederive.py` "is now the ONLY tool allowed to state a
coverage figure". The register's §A.5 numbers are not wrong for their scope but
are **not the canonical headline**, and §A.5 does not say so.

**D-3 — `~30 byte-patched layout constants` under-states the site count by
roughly 9x.** `research\START-HERE.md:38`, `START-HERE.md:26` and
`docs\HOW-IT-WORKS.md` ("About thirty layout values are compiled into the
executable") all carry the same figure. MEASURED today: **36 named families,
274 sites**. The prose is defensible if "constants" is read as *families* (30 →
36, a real but modest drift); it is badly wrong if read as *sites*, which is how
a reader will read it. **Fix the noun, not just the number.**

> **ADJUDICATED 2026-08-31 — the prose targets are CLOSED; the counting is REOPENED, and this item's own figure was wrong the day it was written.** The only triple that reproduces today is **23 families, 45 tables, 320 spans**. Every other number in this section — 30, 36, 274, 295 — is superseded and kept only to show what was believed. Do not quote them.
>
> **Why the original figure was itself the defect it was raised against.** "36 named families, 274 sites" is the same conflation one layer down: **36 is the TABLE count, not the family count.** §4.3 had already stated the corrected split 120 lines above, so the register contradicted its own body inside one document. `VERSION-HISTORY.txt` names the failure in terms — "FAMILIES, TABLES AND SITES ARE THREE DIFFERENT NUMBERS … The first attempt at this fix repeated the error - it corrected the number and kept the wrong noun."
>
> **The prose targets are CLEAN — MEASURED 2026-08-31**, clean tree at `d15e30a`: `about thirty` / `thirty` / `~30 byte` / `30 byte` return **zero hits** in `research\START-HERE.md`, `START-HERE.md`, `docs\HOW-IT-WORKS.md` and `README.md`. *Positive control:* `byte` over the same four files hits in each, so the files are readable and the phrase is what is absent. `START-HERE.md` was fixed by deleting the number outright; the other two adopted the gate's three nouns.
>
> **ALREADY DEAD — do not re-open D-3 on these.** `about thirty` still appears in `_packaging\public-repo\README.md` and `_packaging\public-repo\docs\HOW-IT-WORKS.md`. Both are **untracked build output, not sources**: `git ls-files` returns nothing for either, and `Build-PublicRepo.ps1` says so — "ROOT and DOCS come from the REPOSITORY, not from a staged copy." Their mtimes predate the source fixes, so the next export regenerates them clean. The `_archive\`, `_working-backup\` and `REGRESSION.md` hits are history by design.
>
> ⚠ **STILL OPEN — the 2026-08-30 fix has the right nouns and stale numbers.** Running the exact command §4.3 names, `python tools\uimap\emu\gate_patch_families_combined.py --verbose`, CHECK A prints **`320 site spans across 45 tables, 23 families`**, `overlaps: 0`, gate PASS, identical on three consecutive runs. That supersedes §4.3's `18 feature families, 36 site tables, 295 site spans`, which had itself superseded `36 named patch families, 274 site slots`. The population grew because work landed after that measurement (`kMarkerZoomTableVa` is in today's ownership block and appears **zero** times in this file; `CHANGELOG.md`'s `## Unreleased` records its fix). Three sites now carry the superseded triple with the right nouns: §4.3 → `18 feature families, 36 site tables, 295 site spans`; `research\START-HERE.md` → `18 feature families`; `docs\HOW-IT-WORKS.md` → `Eighteen families`. Each needs the gate re-run and **its own output line pasted, never a hand-edit** — the gate is the only thing allowed to state these counts.

**D-4 — The gauge class is measured in one document and symptom-level in
another.** `SC4-UI-ENGINE.md:344` carries `0xCBCBF1E0` with a role
("code-painted gauge dials", 134 uses), a symptom ("a correct 2x black circle
with a small dial face pinned top-left") and a law — but **no class name, no
factory, no ctor, no vtable and no Plot VA**. `SDK-GAPS.md:740-742` has the
outer vtable `0x00AB4900`, the window vtable `0x00AB46A0` at `obj+4`, factory
`0x00466220`, Plot `0x00762830`, ctor `0x007628E0`, iid `0x0BCBF1DF` and the
0x108-byte size. ~~The catalogue row was never updated from the gaps file.~~ ✅ **CLOSED 2026-08-31 — the row HAS been updated; this item's own two `file:line` citations were the stale things.** The `0xCBCBF1E0` row in `SC4-UI-ENGINE.md` §2 (Widget catalogue) now carries the whole identity inline — outer vt `0x00AB4900`, window vt `0x00AB46A0` at `obj+4`, factory `0x00466220` "returns base+4", `0x00762830`, ctor `0x007628E0`, iid `0x0BCBF1DF`, `0x108` bytes — and cross-references `SDK-GAPS.md` §8.1 by section, while keeping its role, symptom and law. Both cited numbers had drifted: `SC4-UI-ENGINE.md:344` is now the `CITY-DOCK-OVERLAP` clamp snippet (row is `:373`); `SDK-GAPS.md:740-742` is now the `.UI` backslash-escape correction (bullet is §8.1, `:1003-1005`). **MEASURED 2026-08-31 against the pinned exe** (`…\SimCity 4 Deluxe\Apps\SimCity 4.exe`, ImageBase `0x00400000`): the `{factory, clsid}` table in `sub_004662B0` pairs `0x00466220` with `0xCBCBF1E0` (positive control — the same scan reproduces `0x00466170`↔`0xC7A0E17E` and `0x004661A0`↔`0xAA5C2F86`); factory body is `push 0x108` → `operator new` → `mov ecx,eax` → `call 0x007628E0` → `add eax,4; ret`; ctor writes `0x00AB4900` at `obj+0` and `0x00AB46A0` at `obj+4`; iid literal sits at `0x00762495` inside slot-0 QueryInterface `0x00762490`. ⛔ **D-4a — OPEN, raised 2026-08-31: `0x00762830` is this class's slot-88 `GZPaint`, NOT its `Plot`, and two corpus files call it `Plot`.** A full 151-slot diff of window vt `0x00AB46A0` against `cGZWin 0x00ADC8D8` differs in exactly `{0,1,2,4,5,88,148}`; slot **88** = `0x00762830`, slot **89** = `0x0099BA07` — the class does not override `Plot` at all. `SDK-GAPS.md` §1's slot table is the authority: slot 88 (`vt+0x160`) = `GZPaint`, slot 89 (`vt+0x164`) = `Plot`. Positive control: `GZWinBMP`'s vt `0x00ADF6A0` reads slot 88 = `0x009BC325`, slot 89 = `0x0099BA07` — identical shape, and that row was renamed on 2026-08-30. **The rename was never propagated to the gauge.** Not cosmetic: a reader trusting the word `Plot` would hook `0x00762830` expecting the composite/present slot when it is the per-class draw. Fix in `SC4-UI-ENGINE.md` §2's `0xCBCBF1E0` row and `SDK-GAPS.md` §8.1's last bullet — outside this page, which reports drift and does not edit the corpus. *CARRIED, not re-measured: the "134 uses" count and the on-screen symptom.*

**D-5 — The window-class population is printed as both 111 and 115.**
`SDK-GAPS.md:73-76` says "all **111** window-class vtables … a superset of the
**29** named classes"; `:808-809` says "12 of the **115** classes". One file,
two numbers, no reconciliation.
**CLOSED 2026-08-30, re-measured.** `python tools/uimap/wincensus.py` re-run
against the pinned exe reproduces **111** exactly
(`tools/uimap/_work/wincensus.json` `windowVtables`, ≥3-of-8 markers); the
slot-87 single-marker fingerprint (`0x0099BE4C` at `vt+0x15C`) matches
**116** `.rdata` addresses — so the printed 115 reproduced under *neither*
filter. The 5 single-marker extras are `0xAC54B8`, `0xACCD5C`, `0xAD47F0`,
`0xAD805C`, `0xAD825C` (all fail the class test). `SDK-GAPS.md` now
reconciles both counts by instrument at the `GetNotificationTarget` bullet,
names the census as the population every count in that file should use, and
the identification-procedure count re-measures to **13** of the 111 census
classes (base `QueryInterface` at slot 0; all three region layers included).

**D-6 — Two class-level vtable patches exist in a project whose stated law is
"swap the vtable on the instance, never the class".** See §4.2. Neither
`PatchFlashGuardClass` nor `EnsureBufferClassBltHook` is mentioned in the
hooking-rules section of any reference. **MOSTLY CLOSED 2026-08-31 — the engine reference DOES document both exceptions; only the one-line memory note is still silent.** The sentence above **was TRUE when written and is FALSE now**, and the corpus says exactly why: by `git blame`, D-6 was filed 2026-08-29 (`9d328f36`) and the paragraph that answers it landed 2026-08-30 in `3225a92` ("Engine documentation: honest disclosure, reconciled corpus, working gates"). The fix shipped; the drift row was never updated. **The documentation that closes it:** `tools/research/SC4-UI-ENGINE.md` **§2.5, heading `### 2.5 HOOKING RULES — NEVER GUESS A CALLING CONVENTION`** states the instance-swap law and names **both** symbols as the two deliberate, permanent exceptions — "`EnsureBufferClassBltHook()` (slot 29 `Blt`) is the buffer-class case above. The other permanent exception is the FLASH GUARD, `PatchFlashGuardClass()`" — with the reason for each: the buffer is *shared*, so a per-instance swap cannot reach repaint paths that run outside the hooked Plot (gated instead on `destIsContainer`/`destIsSubContainer`); and the flash guard must be in place for a window's **first-ever** Plot, which an instance swap cannot be, because it cannot exist before the instance does. **Anchor by symbol:** grep `EnsureBufferClassBltHook`. **Each §2.5 claim re-checked against `src\UiSpike.cpp` (MEASURED 2026-08-31):** `PatchFlashGuardClass(void** vt)` `VirtualProtect`s `&vt[88]` then writes `vt[88]`; `const int kFgMax = 12;` enforced by `if (gFgCount >= kFgMax) return;`; seeds `0x00AB6AA8` (container) and `0x00AB6D88` (strip); two further sites pass `*(void***)win` from a live window; `EnsureBufferClassBltHook()` `VirtualProtect`s `&kBufClassVt[0]` for `64 * sizeof(void*)` then writes `kBufClassVt[29]`, with `void** const kBufClassVt = reinterpret_cast<void**>(0x00AC1400);`. ⚠ **STILL OPEN, the narrow half:** the memory reference `reference-sc4-thiscall-hook-rule.md` contains **zero** occurrences of either symbol and zero of "never the class". *Positive control:* the identical grep over `SC4-UI-ENGINE.md` returned both symbols, so the scan can see these strings and the null is real. A reader who reaches the rule through the memory note still gets the law with no exceptions attached. **COSMETIC / PURE_DOCS** — the code is correct and the engine reference is correct; one memory one-liner is silent.

**D-7 — The register's own self-date is stale.**
the header line of `UNKNOWNS-AND-NEXT-TARGETS.md` read "This register's newest content is dated
**2026-08-19** (written against **v3.0.2**)". MEASURED: the file's mtime is
2026-08-24 and it contains rows marked "CLOSED 2026-08-24"; the shipping macro
is **4.4.0** (`SC4UIScaleDllDirector.cpp:55`) and `VERSION-HISTORY.txt:1` is
`2026-08-29 v4.4.0`. The register is **~19 releases behind the version it names
itself against.**

**D-8 — The register's §H has two headings numbered H.5** — "CORRECTION —
#191's real cause…" and "#191 — the contradiction that is now the sharpest
lead". Cosmetic, but a cross-reference to "§H.5" is ambiguous.

**D-9 — The ranking table is short two rows.** MEASURED: `§B.1` contains rows
1–21 and 24–29; **rows 22 and 23 do not exist anywhere in the file** in either
struck or open form. *Positive control:* the identical regex
`^\| ~*(21|24)~* \|` returns both neighbours, so the scan
can see rows in both spellings. The prose at the head of §B says "35 raw unknowns …
collapse to **28** distinct items"; the table carries **27**.

**D-10 — "gap census" is a stale name.** `research\START-HERE.md:93` points at
`SC4-WORLD-OVERLAYS.md` for "the gap census of undocumented systems". MEASURED:
§3 of that file is titled "THE CENSUS" (`:433`) and has **dropped the
DOCUMENTED/PARTIAL/UNKNOWN column entirely** because every owner is now
identified. The old 22-row version with the column survives only in the
worktree copy.

> **D-7 / D-8 / D-9 / D-10 — ALL FOUR CLOSED AT THE TARGET, verified 2026-08-31. Three of them also had stale numbers of their own; one was WRONG THE DAY IT WAS WRITTEN.**
>
> **D-7 — CLOSED, and its own figures are superseded.** `UNKNOWNS-AND-NEXT-TARGETS.md:7` (grep `This register's newest content is dated`) now reads **2026-08-24** and carries the old claim inline; the version pin at `:9` was removed the same way. ⚠ **Do not quote "4.4.0", "2026-08-29 v4.4.0" or "~19 releases behind":** re-measured, `src\SC4UIScaleDllDirector.cpp:55` is `#define UISCALE_VERSION_STR "4.7.0"` and `VERSION-HISTORY.txt:1` is `SC4UIScale 4.7.0 (2026-08-31)`. *Positive control:* `grep -n UISCALE_VERSION_STR` returns three hits — the definition and both consumers. **No replacement number is pinned here on purpose:** a version written into prose rots inside one release cycle — the 2026-08-30 correction was one release stale the next day, and this item's own MEASURED line went stale in two. **Cite the macro and the changelog head, never a transcribed number.**
>
> **D-8 — CLOSED 2026-08-30.** `:392` is now the sole `### H.5` (the CORRECTION), so an unqualified "§H.5" resolves to the adjudicated verdict; the superseded mid-investigation lead became `### H.5a` at `:412`, carrying its annotation inline. *Positive control:* `grep -nE '^### H\.5'` returns exactly two lines and would have shown a surviving duplicate.
>
> **D-9 — ⛔ REFUTED. This item was WRONG THE DAY IT WAS WRITTEN, and its own positive control is the reason.** The rows exist, and existed then, as **one merged struck row**: `| ~~22~~ · ~~23~~ | ~~In-world Data View tint / underground-pipe views~~ **✅ CLOSED 2026-08-24 …`. Chronology by git, not inference: `git log -S 'In-world Data View tint / underground-pipe views'` → **bbfb418, 2026-08-24**; `git log -S 'The ranking table is short two rows'` → **9d328f3, 2026-08-29**; `git merge-base --is-ancestor bbfb418 9d328f3` succeeds; `git show 9d328f3:…| grep -c '~~22~~ · ~~23~~'` = **1**. The row was in the tree, in that exact spelling, five days before the claim of its absence was committed. ⭐ **THE LAW THIS PAID FOR: A CONTROL THAT ONLY EXERCISES THE SHAPE YOU EXPECTED IS NOT A CONTROL FOR THE SHAPE YOU DID NOT.** The quoted control `^\| ~*(21|24)~* \|` **cannot match a merged cell** — `| ~~22~~ · ~~23~~ |` carries a second number and a separator inside one cell. Matching rows 21 and 24 proved only that *single-numbered* rows were visible. That is an un-evidenced null **wearing a positive control as cover** — exactly what NULL IS NOT EVIDENCE forbids. A row-presence control must vary the row's *formatting*, not just its number.
>
> **D-10 — CLOSED, and this item's own `:433` and "22-row" are stale.** `research\START-HERE.md` no longer contains "gap census" (`grep -c` = 0 against a control of `census` = 2); the row now reads "the 23-row in-world census (every owning system identified)" and sits at `:98`, not `:93`. In `tools\research\SC4-WORLD-OVERLAYS.md` the heading is at `:436` (not `:433`), the grade column is indeed gone (`grep -c PARTIAL` in range = 0), and the table carries **23** rows, not 22. Note the file lives under `tools\research\`, not `research\`.

### 5.2 The source has something no document covers — the more important gap

**G-1 — There is no per-screen decompilation status anywhere but this file.**
That is why it exists. Before it, answering "how much of the Budget panel do we
have" meant reading four documents.

**G-2 — Six shipping patch families are outside the only gate that can see two
byte patches colliding.** MEASURED by diffing the `k…Site` scan against
`gate_patch_families_combined.py`'s `WIDTHS` map:

| Unregistered family | Feature |
|---|---|
| `kCostBoxHeightSite` | #159 placement cost readout |
| `kCostBoxWidthSite` | #159 |
| `kCostOriginSite` | #159 |
| `kX8DispatchSite` | minimap x8 bake dispatch |
| `kSignpostSizeSite` | signpost 44.0f quad |
| `kSignpostRaiseSite` | signpost 150.0f pole raise |

The register (`§D.2`) reported this as **five** unregistered tables, all
cost-box. MEASURED today it is **six**, and the composition changed: the
cost-box family accounts for 3 (the other 2 the register named,
`kCostOriginBack` and `kCostOriginStock`, are stock-byte arrays, not site
tables), and **two signpost sites plus the x8 dispatch site have joined since**.
The gate's own header (`:34`) says "A new table nobody registered FAILS the gate
rather than …" — so this gate is red, and has been red long enough that the
composition of its redness drifted without anyone reading it.

**G-3 — The 29 engine detour targets are not tabulated in any reference.**
`SC4-UI-ENGINE.md` §8 catalogues 272 VAs, but there is no "what we hook"
list anywhere; §4.1 above is the first. Four of the DLL's detour targets —
`0x5FD2D0`, `0x496950`, `0x528580`, `0x4D7950` — do not appear in §8 at all.
*Positive control:* §8 does carry `0x0046D990`, `0x5F5FB0` and `0x5939B0`,
three other detour targets, so the reference does list hookable VAs when it
knows them.

**G-4 — `tools\uimap\constants.json` is 25 days behind `CodePatches.cpp`.**
MEASURED: `constants.json` mtime **2026-08-04 07:46**, `CodePatches.cpp`
**2026-08-29 08:44**. The register flagged this at a 14-day gap and warned "no
reasoning about the region-screen, intro-video or cost-box patch families
[should be trusted] until it is regenerated". The gap has since **doubled**.

**G-5 — `dist\` has caught up; that register entry is stale in the good
direction.** MEASURED: `dist\SC4UIScale-v4.4.0\` exists (2026-08-29 08:58) and
matches the version macro. The register's "`dist/` is ~24 DLL versions behind"
(§D.3) no longer holds.

**G-6 — `src\UiSpike.cpp.before-iconprobe-2026-08-14` is gone.** MEASURED:
absent from `src\`. *Positive control:* the same `ls` lists all 23 current
`src\` files including `UiSpike.cpp` itself. Publication blocker §E-8 is
correctly marked resolved.

---

## 6. What to attack next

Ranked by **how much UI a closure unblocks**, not by tractability. Reasoning
stated for each.

### 1. Re-audit the SDK-boundary law against the source (D-1)

**Unblocks:** every future triage. **Cost:** one editing pass, no launch.

The boundary triage is step 0 of the project's own method — it decides whether
the whole toolkit applies before any address is chosen. It has now been wrong
three times in the same way, and the third instance is **live in the law file
today**, telling the next reader that a window we already scale is reachable
only through the renderer. A modder following it would go looking for a size
constant in a render path that does not own the element.

The edit is small: strike the "move in a sim marker" as the confirmed instance,
record that the bucket currently has **no confirmed member**, and cite
`UiSpike.cpp:16800` as the proof of cure. Keep the category — the reasoning is
sound and the trap is real — but stop naming a cured window as its example.

This is first because it is cheap, because it corrupts a *method* rather than a
fact, and because the file itself predicts exactly this failure and asks for a
periodic re-audit that has not happened.

### 2. Register the six unregistered patch families and regenerate `constants.json` (G-2, G-4)

**Unblocks:** all 274 byte-patch sites, and the budget family's 168 in
particular. **Cost:** one gate edit plus one generator run, no launch.

`gate_patch_families_combined.py` is the **only** instrument that can see two
byte patches colliding, and it is currently blind to six families and red for
reasons whose composition has drifted. A standing red is worse than no gate:
the register already recorded the exact hazard — "a standing red makes every
later red look pre-excused". Meanwhile `constants.json`, the model the
crosscheck reasons over, is 25 days stale, so nothing it says about the region,
intro-video or cost-box families is currently load-bearing.

Second, not first, because it is mechanical: the sites are enumerated in §4.3
and the gate's `WIDTHS` map takes an encoding width and a shape string per
family.

### 3. The `.UI` deserializer's completion path (register row 29)

**Unblocks:** the largest single surface — the `.UI` pass reaches 271 default
layouts plus the 800×600 override set, and the deserializer is the choke point
every one of them passes through. The register scores it **V=5, T=1** and calls
it "open-ended; highest ceiling".

It is third rather than first precisely because of that T=1. Do it after the two
cheap correctness items above, and do it with an instrument rather than a
disassembler — the register's own §G law is that suppression identifies while
scaling does not.

### 4. Screen-prove the eight PARTIAL overlay rows

**Unblocks:** 8 of 23 census rows, and closes the honesty gap the register's §F
already flags — that several rows graded DOCUMENTED "would be **PARTIAL** under
the repo's own stricter law: mechanism named, never seen running".

Rows 8, 10, 11, 12, 13, 14, 15, 16 all carry addresses derived from static
disassembly with no screen evidence. The project's own law is that a static
defect is a hypothesis until something on screen disagrees; the same rule makes
a static *attribution* a hypothesis too. One suppression launch per row is the
cheap test, and suppression has repeatedly named a drawer in a single launch
where scaling returned an ambiguous "no change". ⛔ **SUPERSEDED 2026-08-31 — THIS IS NO LONGER A NEXT ACTION. The ranked list has four live items (1, 2, 3, 5), not five. Do not spend eight launches on it.** Kept because three of these rows closed by *killing* a standing attribution, and those refutations are worth more than the closure. **Why it went stale:** the per-row suppression launches ran (2026-08-30 and 2026-08-31), and separately the instrument that would have made them unnecessary — the register's row 4 DX7 `DrawArrays` caller census, whose stated purpose was to convert rows 8 and 10–16 from "mechanism named, never seen running" to attributed — **also ran and closed** (`research/UNKNOWNS-AND-NEXT-TARGETS.md`, grep `the live census RAN`; probe ships as `[Probe] GpuCap=N` in `src/CodePatches.cpp`). Both routes are spent. MEASURED 2026-08-31 from the `CURRENT GRADE` line each row file now carries: row 4 CLOSED; row 8 CLOSED; row 10 ATTRIBUTED; rows 11, 12 MEASURED; row 13 MEASURED+DECODED; row 14 TRUE NULL (attribution REFUTED); row 15 DOCUMENTED (S3D vertices; the `OccupantSize` route REFUTED); row 16 DOCUMENTED (`0x007DD9B0`; three attributions died on it); row 23 DOCUMENTED. **No row is graded PARTIAL any more**, and that null has a control: `PARTIAL` and `UNKNOWN` return zero hits in `SC4-WORLD-OVERLAYS.md` while `row` returns 29 and the tally reads `Census tally: 23 rows, every owning system identified`. ⚠ **One caveat, stated rather than smoothed over:** row 10 is closed at **ATTRIBUTED**, not on this page's strict bar — its chain is byte-verified and the decoded tint quads match what a player sees, but **no detour was ever run for it**, and §2.3 above groups it with 11/12 as "confirmed live", which row 10's own file does not support. The settling gesture is one naked log-only detour on `SetHighlight` at `0x80D580` (stock prologue `51 55 56 8B 74 24 10 57 8B E9` — verify bytes first), then a QUERY-tool hover: expect `dwHighlight=7` on enter and a restore on leave, `5`/restore with DEMOLISH. **The actionable remainder is in another file:** `research/UNKNOWNS-AND-NEXT-TARGETS.md` still reads `Next up:** #4, the DrawArrays caller census`, still calls rows 8 and 10–16 "mechanism named, never seen running", and its §F item 5 still flags them as PARTIAL-under-the-stricter-law. All three predate these closures.

### 5. Reconcile the class population and fold `SDK-GAPS` §8 into the catalogue (D-4, D-5)

**Unblocks:** the widget catalogue, which is the first thing a new reader opens.
Two of its 17 rows are strictly worse than what another file in the same folder
already knows, and the class count is printed two ways. Low value per unit
effort compared to 1–4, but it is the difference between a reference and a set
of notes.

**Deliberately not ranked:** #162 (the register's one open defect with no known
mechanism, 8 hypotheses refuted) and #104 (the teardown spin, no loop ever
named). Both are real and both are open, but neither unblocks other UI — they
are single defects, not levers, and the register already holds the full
refutation record for each.

---

## Next action

Start with §6 item 1: open `research\laws\reference-sc4-ui-sdk-boundary.md`, and
correct the "third category" section against `src\UiSpike.cpp:16800-16801` and
`research\UNKNOWNS-AND-NEXT-TARGETS.md` §H.5 ("CORRECTION — #191's real
cause…"). It is a documentation
edit, needs no launch and no build, and it is the one drift on this page that
can mislead the next investigation before it starts.
