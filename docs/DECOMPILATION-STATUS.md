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
| **Graphics Options selector** | **PARTIAL** — rewritten after the register's cut-off and not folded back into any reference | register flags it as post-dating itself at `UNKNOWNS-AND-NEXT-TARGETS.md:7` (the root CONTINUITY.md originally cited here was deleted 2026-08-29 as a stale progress recap; its durable content was promoted into that same register, so there is no file to open) |
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
not noted anywhere in the reference — **drift D-6**.

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

**D-4 — The gauge class is measured in one document and symptom-level in
another.** `SC4-UI-ENGINE.md:344` carries `0xCBCBF1E0` with a role
("code-painted gauge dials", 134 uses), a symptom ("a correct 2x black circle
with a small dial face pinned top-left") and a law — but **no class name, no
factory, no ctor, no vtable and no Plot VA**. `SDK-GAPS.md:740-742` has the
outer vtable `0x00AB4900`, the window vtable `0x00AB46A0` at `obj+4`, factory
`0x00466220`, Plot `0x00762830`, ctor `0x007628E0`, iid `0x0BCBF1DF` and the
0x108-byte size. The catalogue row was never updated from the gaps file.

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
hooking-rules section of any reference.

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
where scaling returned an ambiguous "no change".

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
