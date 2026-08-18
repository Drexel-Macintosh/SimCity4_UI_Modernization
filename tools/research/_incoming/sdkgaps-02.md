# TARGET: PRIMARY: <PROJECT-ROOT> 1 Project\1 Completed Projects\SC4TouchControls\tools\research\REGION-SWITCH.md — new "## 0. THE REGION SCREEN — architecture" inserted ahead of the existing "## Evidence base" (§0.1 host chain and the 13 children, §0.2 where the panels come from, §0.3 born-hidden split, §0.4 anchoring law, §0.5 the city-select bubble, §0.6 lifecycle, §0.7 what the region pass does not do, §0.8 instrument limits, §0.9 region laws R1-R8), plus a retitle of the file's H1. SECONDARY: tools\research\SC4-UI-ENGINE.md §0 (retraction), §1.1 (host table note), §1.4 (slot correction), §2 (cSC4WinAuraBar row), §8.5 (VA index). TERTIARY: tools\research\DYNAMIC-CONTROLS.md Q1 table + Q3 scoping note + Method notes slot correction.

## SUMMARY
Produced the region screen as a full SDK section from measurement, not restatement. NEW: the complete 13-child host map at stock 800x600 (9 panels + 4 full-screen layers, 68 windows total) with the four born-hidden panels identified and cross-confirmed by two independent instruments; the region anchoring law measured at two resolutions (gaps identical to the pixel — the game holds gaps constant, we double them; two negative design gaps and one 1154px over-wide centred bar); the city-select bubble fully decoded — it hangs under the map layer 0x2BA6BB97 so the runtime sweep can never reach it, and ONE window id 0x0A551C50 carries TWO different scripts chosen in code at 0x007ACC34/0x007ACC40, observed live at 516x500 and at 432x330 in consecutive sessions, with both child maps matching their scripts at exactly 2x. CORRECTED, with disassembly: the Mayor Rating bar IS a window (0x4A553000, cSC4WinAuraBar, fetched at 0x007B5157, fed a double at 0x007B5178, art {46A006B0,14416327} at 0x007B517E) — SC4-UI-ENGINE.md §0 files it as outside the SDK boundary on the strength of a null that came from RGKID recursing only four levels while the bar sits at level five. That art is 102x26 and is in NO tier's package list while our static dat doubles the bar's window to 204x22, so task #72 is a data fix, not an exe hunt. Also corrected: GetID is +0xFC and SetID is +0x100 (docs say SetID +0xFC); the region UI does NOT persist across a city visit (contradicting UiSpike.cpp:8971-8972) — measured full rebuild with boot-equal counts, which is the first proof of PURGE-ON-FRESH-ROOT on the return path; the sweep is 16ms not 250ms; 0x0BB0F5E7 and 0x6BB92BCA are NOT region-exclusive ids; and FLASHSET reports each id once per process, so it is structurally blind to the region flash recurring on every return.

## CONTRADICTIONS
- SC4-UI-ENGINE.md §0 (line 59) lists the region bubble's Mayor Rating bar as OUTSIDE the SDK boundary, on the grounds that “RGKID shows no window where it renders”. WRONG — it is window id 0x4A553000, clsid 0xAA5D16A9 (cSC4WinAuraBar), declared in I-ca539340 at area=(11,92,113,103), and the exe fetches it by id at 0x007B5157 (`push 0x4A5D1208; push 0x4A553000; call [edx+0x94]`) then feeds it a double via slot +0x10. The null came from RGKID recursing only four levels (UiSpike.cpp:8910/8920/8936/8951); the bar sits at level five. Textbook NULL IS NOT EVIDENCE. Row must move out of §0 and task #72 must be reclassified from ‘exe hunt’ to ‘data fix’.
- tools/research/_checkpoints/task55-47-runtimeimg.md heading “REGION BUBBLE — FULLY MEASURED, and the rating bar is NOT A WINDOW” (line 1452) and its body “NOTHING sits where the Mayor Rating bar renders … so the bar is CODE-PAINTED by the bubble's own draw routine” (1459-1460) are refuted by the same evidence. The A/B result at 1472-1477 stays valid (our rating-arrow patch is genuinely not the cause — that patch drives the CITY HUD's four GZWinBMPs via controller 0x7E86C0-0x7E8A80, a different implementation entirely) but the conclusion drawn from it does not.
- SC4-UI-ENGINE.md §1.4 confirmed-slots row states `SetID +0xFC`; DYNAMIC-CONTROLS.md “Method notes” repeats it. MEASURED: +0xFC is GetID — 0x004CB919 `call [eax+0xFC]` with no pushed argument, result compared `cmp eax, 0x0BB0F5E7`. SetID is +0x100 — 0x007A99DF `push 0x6A0AF41D; mov ecx,esi; call [eax+0x100]`. Header order (vendor/gzcom-dll/include/cIGZWin.h lines 145-146: GetID then SetID, not an overload pair so no MSVC reversal) agrees. Positive control for the reading: the same method reproduces the documented `GetChildAsRecursive +0x94` exactly at 0x007B515E (id, iid, &out).
- UiSpike.cpp:8970-8972 comment — “scaleMap keeps its records, so persistent region UI is NOT re-scaled on return” — is false. Nothing in the region host subtree persists. Measured 2026-07-31 11:11:01.441: all nine panels re-scaled from DESIGN geometry at boot-equal counts (10/2/9/3/5/18/10/3/3) on a city→region return. The return is safe because PURGE-ON-FRESH-ROOT (UiSpike.cpp:7817-7830) runs, not because records survive.
- UiSpike.cpp:2279-2280 — “These IDs only exist under the region host - the city pass never matches them” — is false for two of the nine. 0x0BB0F5E7 and 0x6BB92BCA are also direct children of the 3D view: log 11:10:06.636 `panel 0x0BB0F5E7 (2199,2 199x291)` / `panel 0x6BB92BCA (2358,2 40x36)` on the incremental (city) pass, vs (2243,1392 152x203) / (2356,1558 34x32) on the region pass. Two distinct scripts confirm it: I-abc0ed33 root 0x0bb0f5e7 area=(144,86,296,289)=152x203 (region), I-abb0120f root 0x0bb0f5e7 area=(1,-1,200,290)=199x291 (city). Consequence: the visibility gate at UiSpike.cpp:5302-5305 consults IsRegionPanelId on the CITY pass too, so those two city windows are pre-scaled while hidden — currently benign, but by accident, not design.
- REGION-SWITCH.md is written throughout against a 250ms sweep (“within one 250ms tick”, “the continuous 250ms pass never healed it”, “~500ms”). The tick is now 16ms: live log line 26 `Tick subclass installed (16ms)` (v2.37.0) vs `(250ms)` in SC4UIScale.log.bak-stock800 (v2.6.0). UiSpike.cpp:8981-8984's “~500ms” stability-gate comment is stale by ~15x — the gate is two ticks ≈ 32ms, and the measured region-up latency on a return was 12ms (RGKID 11:11:01.429 → `region screen up` 11:11:01.441).
- tools/research/_checkpoints/codecreated-noncity.md:6 — “0x2BA6BB97 cSC4WinRegionView = THE REGION MAP, full-screen, 0 children”. It has 0 children only until a city tile is clicked; the city-select bubble 0x0A551C50 is its child (RGKID 11.0, measured twice). The “0 children” observation was taken with no bubble open.

## OPEN
- Does the region host 0xEA659793 itself survive a city visit, or is it destroyed and recreated? The log cannot tell — it is re-found by id every tick (UiSpike.cpp:8886) and RGKID prints vt=%p but not the window pointer. ONE-LINE INSTRUMENT: add self=%p to the RGKID top-level line; one region→city→region round trip then settles it. Until then this is a structural null, not a fact.
- Does the region flash actually recur on every city→region return? MEASURED: the nine panels are rebuilt at design geometry and re-scaled every return. NOT MEASURED: whether they were on screen when we resized them — NoteFlashCandidate's static seen[96] (UiSpike.cpp:1552) spends each id once per process, so the instrument is structurally blind to a repeat. Fix: key the dedupe on (id, arrivalSerial) or reset seen when regionActive goes false.
- 'Drawn twice' mechanism for the aura bar: is it source tiling (204-wide window over 102-wide art) or does cSC4WinAuraBar compute its own fill extent? ONE build settles it — add {46A006B0,14416327} to selective-safe at 2x; if the bar is still doubled, LEFT1X-exempt id=0x4a553000 in build_dialog_static.py instead. Do NOT touch ApplyRatingArrowScale; the A/B already cleared it.
- What is the CITY-side 0x0BB0F5E7 (script I-abb0120f, root 199x291, 37 nodes, top-right, vt 00ADC678, 34 windows scaled, children 0xABB0F65F/0xEBB0F666 shown-hidden by the handler at 0x004CB926-0x004CB93A)? It is NOT the Data Views legend (that is 0x8A909Exx under 0xAA32BCE6). Naming it matters because it is currently pre-scaled-while-hidden by accident, via IsRegionPanelId leaking into the city visibility gate at UiSpike.cpp:5302-5305.
- Our anchor model scales edge gaps (×2) but leaves the centre bias unscaled (0x6A91DC16 stays −3, 0x09EBEE45 stays +7 at 2x, where proportional consistency wants −6 and +14). 3px and 7px at 2x; 4.5 and 10.5 at 3x. Intentional or an oversight in the centre branch of ScalePanelRoot? Worth deciding before the 3x tier is validated.
- The four full-screen region layers: 0x6A0AF41D (vt 0x00AB88C0, code-created, id stamped at 0x007A99DF, ZERO other exe references) and the two anonymous ones (vt 0x00AB8CD0, 0x00AB8F50) are still unnamed. 0x00AB8CD0's Plot 0x7AB130 is already recorded as an animating list (REGRESSION.md:1812). Naming them would close the last gap in the region host map.
- Both bubble variants' level-5 nodes (city name, mayor name, funds ×2, three population fields, the 'Mayor Rating:' caption) have never been observed live — RGKID cannot reach depth 5. Their 2x geometry is asserted from the staged script only. Raising RGKID one level (or scoping a depth-6 dump to 0x2BA6BB97) would confirm the static dat lands on all of them, including the two co-located funds fields at identical rects (0x4a552002 black / 0x4a552006 red).

---

## BLOCK A — `tools\research\REGION-SWITCH.md`, insert as a NEW `## 0.` ahead of the existing `## Evidence base`

Also retitle the file: it is no longer only "why the population number lands outside the bar" — that investigation becomes §1 onward. Suggested H1: `# REGION-SWITCH — the region screen: architecture, anchoring, lifecycle, and the switch bug`.

---

## 0. THE REGION SCREEN — architecture

### 0.1 The host chain, and the 13 children

The region screen is not a mode of the city screen; it is the **alternative occupant of the same slot**. `WinSC4App 0x6104489A` has exactly one child, and on the region screen that child is `0xEA659793` (clsid `cSC4WinRegionScreen`, registry `.data` 0x00B08FC0) — where in a city it is `0x9A47B417` `cSC4View3DWin`. The tooltip layer `0x2AAB8CC1` is a **sibling of WinSC4App under the MAIN window**, not a region-host child, and on the region screen it is empty and hidden.

> EVIDENCE — `SC4UIScale.log.bak-stock800` (v2.6.0-split, `ScaleAll=0` ⇒ DLL inert, so every number is the GAME's): `UI id=0x00000000 … children=2` → `0x6104489A children=1` → `0xEA659793 (0,0) 800x600 children=13`; and `UI id=0x2AAB8CC1 pos(0,0) size(800x600) children=0 vis=0` at main-window depth. Whole tree = 71 windows, of which **exactly 68 are the region host and its descendants**.

The 13 children, in `EnumChildren` order (= reverse `.UI` add order), at stock 800x600:

| # | id | design rect | vis | kids | role |
|---|---|---|---|---|---|
| 0 | `0x0BB0F5E7` | (643,392) 152x203 | **0** | 9 | region legend / key (`I-abc0ed33`) |
| 1 | `0x6BB92BCA` | (756,558) 34x32 | **0** | 1 | legend toggle button |
| 2 | `0x09EBE9EE` | (5,496) 415x106 | 1 | 5 | region info bar (name / pop / city count) |
| 3 | `0x6A91DC15` | (670,0) 115x76 | 1 | 2 | top-right button cluster |
| 4 | `0x6A91DC16` | (170,0) 454x91 | 1 | 4 | top-centre 3-button cluster |
| 5 | `0x09EBEE45` | (18,4) 778x204 | **0** | 7 | top flyout (New/Load/Delete Region) |
| 6 | `0x09EBEE60` | (472,-1) 306x166 | **0** | 4 | options flyout (5 buttons) |
| 7 | `0xEA8CAD19` | (28,32) 73x42 | 1 | 2 | compass / mode badge |
| 8 | `0x6A91DC14` | (-177,0) 1154x51 | 1 | 2 | top bar (over-wide, see §0.4) |
| 9 | `0x6A0AF41D` | (0,0) 800x600 | 1 | 0 | full-screen layer, vt `0x00AB88C0` |
| 10 | `0x00000000` | (0,0) 800x600 | 1 | 0 | full-screen layer, vt `0x00AB8CD0` |
| 11 | `0x2BA6BB97` | (0,0) 800x600 | 1 | 0* | **`cSC4WinRegionView` — the region map itself**, vt `0x00AB9658` |
| 12 | `0x00000000` | (0,0) 800x600 | 1 | 0 | full-screen layer, vt `0x00AB8F50` |

\* 0 children *until a tile is clicked* — see §0.5.

> EVIDENCE — `SC4UIScale.log.bak-stock800` lines 8-75 (the whole table); vtables from `RGKID` in the live log (`SC4UIScale.log`, v2.37.0-dvorigin, 11:16:11.734 onwards). Class names from the exe's registry (`.data` stride-8 `[clsid][char*]`, dumped 2026-07-31): `0x00B08FC0 EA659793 cSC4WinRegionScreen`, `0x00B08FC8 2BA6BB97 cSC4WinRegionView`.

`0x6A0AF41D` is code-created, not script-declared: it occurs **once** in the whole exe, at `0x007A99DF` (`push 0x6A0AF41D; mov ecx,esi; call [eax+0x100]` = `SetID`). Its class is still unnamed.

**Rows 0-8 are the nine whitelisted panels; rows 9-12 are the four full-screen layers, skipped by design.** `kRegionPanelIds` (`UiSpike.cpp:2281-2284`) is therefore exactly "every non-full-screen child of the region host" — a complete cover, not a sample.

### 0.2 Where the panels come from

Seven of the nine are top-level roots of ONE marker-composed script, `I-aa920991` (51 `<LEGACY>` nodes): `0x6A91DC14`, `0xEA8CAD19`, `0x09EBE9EE`, `0x09EBEE60`, `0x09EBEE45`, `0x6A91DC16`, `0x6A91DC15`. The legend `0x0BB0F5E7` comes from its own script `I-abc0ed33`, the toggle `0x6BB92BCA` from another. Two of the nine (`0x6A91DC14`, `0xEA8CAD19`) have **zero** `.text` immediate references — purely data-declared; the rest are re-found in code by id at the region-screen init around `0x007B0100-0x007B0B00` (`push <id>; call [reg+0x8C]` = `GetChildWindowFromID`).

> EVIDENCE — `tools\uiscripts\extracted\T-00000000_G-96a006b0_I-aa920991.ui` top-level `<LEGACY>` nodes; exe dword scan for each id (0 hits for `0x6A91DC14` / `0xEA8CAD19`; `0x6A91DC16` at `0x007B058D`, `0x6A91DC15` at `0x007B05B5`, `0x09EBEE60` at `0x007B05F1`, `0x09EBEE45` at `0x007B0605`).

### 0.3 Four of the nine are BORN HIDDEN — and that is why only five flash

`0x0BB0F5E7`, `0x6BB92BCA`, `0x09EBEE45`, `0x09EBEE60` all report `vis=0` at region boot; the other five are on screen. The sweep scales all nine anyway (the `IsRegionPanelId` exception at `UiSpike.cpp:5302-5305`), which is the PRE-SCALE-WHILE-HIDDEN cure in its original home.

> EVIDENCE — stock dump `vis=0` on exactly those four rows; and the live log's `FLASHSET region …` lines fire for exactly the five visible ones (`0x09EBE9EE`, `0x6A91DC15`, `0x6A91DC16`, `0xEA8CAD19`, `0x6A91DC14`, candidates #1-#5 at 11:16:11.722) and for none of the four hidden ones. Two instruments, same split. Positive control for the null: `RGKID`'s top-level filter is `if (!w->IsVisible()) continue;` (`UiSpike.cpp:8913`), so the same four are the ones missing from every `RGKID` dump — an independent confirmation, not a second guess.

**The five visible panels flash on EVERY arrival at the region screen, not just at boot** — see §0.6. There is currently no instrument that reports the recurrence (§0.8).

### 0.4 The anchoring law, measured at two resolutions

The game re-anchors every region panel to the live frame. Stock 800x600 vs the game's own pre-scale placement at 2400x1600 gives **identical gaps to the pixel**:

| panel | rule | 800x600 | 2400x1600 |
|---|---|---|---|
| `0x0BB0F5E7` | right+bottom | R 5, B 5 | R 5, B 5 |
| `0x6BB92BCA` | right+bottom | R 10, B 10 | R 10, B 10 |
| `0x09EBE9EE` | left+bottom | L 5, B **−2** | L 5, B **−2** |
| `0x6A91DC15` | right+top | R 15, T 0 | R 15, T 0 |
| `0x6A91DC16` | centred+top | centre −3 | centre −3 |
| `0x09EBEE45` | centred+top | centre +7 | centre +7 |
| `0x09EBEE60` | right+top | R 22, T **−1** | R 22, T **−1** |
| `0xEA8CAD19` | left+top | L 28, T 32 | L 28, T 32 |
| `0x6A91DC14` | centred+top | centre 0 (1154 wide in an 800 frame) | centre 0 |

> EVIDENCE — stock dump vs live log 11:16:11.721-.722 pre-scale rects: (2243,1392)/(2356,1558)/(5,1496)/(2270,0)/(970,0)/(818,4)/(2072,-1)/(28,32)/(623,0).

Three engine facts fall out:

1. **The region screen is a second, independent proof of §1.5's anchor model** (fixed corner gaps + centred top elements), and the first place both **negative design gaps** appear outside the city dock: `0x09EBE9EE` hangs 2px off the bottom and `0x09EBEE60` 1px off the top **at every resolution, by design**. The per-edge conditional clamp is what preserves them (our output keeps −4 and −2 at 2x).
2. **The top bar `0x6A91DC14` is deliberately WIDER than the stock screen** (1154 in an 800 frame, x = −177) so its decorative ends always run off both edges. Anything that clamps a region panel on-screen destroys it.
3. **The game holds edge gaps CONSTANT across resolutions; we DOUBLE them.** Both are correct for their purpose — a resolution-independent chrome vs. a resolution-proportional one — and the difference is the whole point of the mod. Our post-scale gaps are exactly 2× the design gap on all seven edge-anchored edges (5→10, 10→20, 15→30, 22→44, 28/32→56/64, −2→−4, −1→−2).

> EVIDENCE — live log 11:16:11.721-.722 `->` targets: (2086,1184 304x406), (2312,1516 68x64), (10,1392 830x212), (2140,0 230x152), (743,0 908x182), (429,8 1556x408), (1744,-2 612x332), (56,64 146x84), (46,0 2308x102).

**Divergence worth naming: edge gaps scale, the centre bias does not.** `0x6A91DC16` is 3px left of centre at both stock resolutions and stays 3px left after our scale (743+454 = 1197 vs 1200); `0x09EBEE45` is +7 and stays +7 (429+778 = 1207). For proportional consistency they should become −6 and +14. Magnitude 3px and 7px at 2x, 4.5/10.5 at 3x — below the reporting threshold so far, but it is an asymmetry in our own anchor model, not in the game's.

### 0.5 The city-select bubble `0x0A551C50` — created per click, under the map layer

**Parentage.** The bubble is **not** a child of the region host. It hangs under the full-screen map layer `0x2BA6BB97` (`cSC4WinRegionView`). Since `ScalePanelsUnder` enumerates only the *direct* children of `pRoot` and the region pass whitelists nine ids that do not include `0x2BA6BB97`, **the entire bubble subtree is structurally unreachable by the runtime sweep.** It is served by the static dat (`z_SC4UIScale_DialogStatic-2x.dat`) and by that alone. This is the region-screen instance of the PARENTAGE RULE (§1.2).

> EVIDENCE — `RGKID 11 id=0x2BA6BB97` → `RGKID 11.0 id=0x0A551C50 vt=00AB7358`, live log 11:16:14.245; `UiSpike.cpp:5221` (`pRoot->EnumChildren`) + `5262` (region whitelist).

**One window id, three scripts, chosen in code at click time.** The variant is selected by a predicate on the clicked tile and the pair `{scriptIID, windowID}` is recorded on the bubble controller:

```
007ACC2A  call [edx+0xAC]          ; predicate: is this tile a founded city?
007ACC32  je   0x7ACC40
007ACC34  push 0x0A551C50          ; window id
007ACC39  push 0xCA539340          ;   -> I-ca539340  EXISTING CITY   (258x250)
007ACC3E  jmp  0x7ACC4A
007ACC40  push 0x0A551C50          ; SAME window id
007ACC45  push 0x0A8CD184          ;   -> I-0a8cd184  START NEW CITY  (216x165)
007ACC4A  mov  ecx,[esi+0xE0]
007ACC50  call 0x7B5E20            ; stores iid->[obj+0xF0], id->[obj+0xF4], notifies listeners
...
007B5AFD  mov  ebp, 0x0A551C53     ; third variant, DIFFERENT id
007B5B02  mov  dword [esp+0x30], 0xCA539343   ; -> I-ca539343  narrow stub (42x159)
```

> EVIDENCE — offline capstone disassembly of `SimCity 4.exe` 1.1.641.0 at the VAs shown; script roots `I-ca539340 area=(146,71,404,321)`=258x250, `I-0a8cd184 area=(146,71,362,236)`=216x165, `I-ca539343 area=(146,71,188,230)`=42x159.

**This collision is live, not theoretical.** Two consecutive sessions, same id, different size and different child count:

| session | live rect | = 2× | variant | top-level children |
|---|---|---|---|---|
| 11:08:14.181 | (1049,456) **516x500** | 258x250 | `I-ca539340` existing city | 12 |
| 11:16:14.245 | (804,462) **432x330** | 216x165 | `I-0a8cd184` start new city | 5 |

Note also that the script's `area=` **L,T is discarded**: both variants declare (146,71) and both land somewhere else. **Size comes from the script, position from the game** (tail-anchored to the clicked tile).

**Full child map — existing-city variant `I-ca539340`, root `0x0A551C50`.** Enumeration is reverse add order; every live rect is exactly 2× the staged script, so the static dat reaches all of it:

| RGKID | id | class / vt | script `area=` (1x) | live (2x) |
|---|---|---|---|---|
| 11.0.0 | `0xCC06F4CF` | GZWinBMP `00ADF6A0` | (113,49) 40x20, `imagerect=(0,0,33,11)` | (226,98) 80x40 vis=1 |
| 11.0.1 | `0xAC06F4C4` | GZWinBMP | (110,47) 40x20, `imagerect=(0,0,22,11)` | (220,94) 80x40 vis=0 |
| 11.0.2 | `0x6C06F4A0` | GZWinBMP | (110,47) 40x20, `imagerect=(0,0,11,11)` | (220,94) 80x40 vis=1 |
| 11.0.3 | `0x4A560003` | GZWinBtn `00ADDAF0` | (79,159) 36x29 "Delete City" | (158,318) 72x58 |
| 11.0.4 | `0x4A560002` | GZWinBtn | (41,158) 22x32 "Import City" | (82,316) 44x64 |
| 11.0.5 | `0x4A560001` | GZWinBtn | (175,26) 13x13 "Close", `winflag_visible=no` | (350,52) 26x26 vis=0 |
| 11.0.6 | `0x4A560000` | GZWinBtn | (183,158) 55x46 "Play This City" | (366,316) 110x92 |
| 11.0.7 | anon | GZWinBtn | (147,128) 92x16 "Industrial Jobs" | (294,256) 184x32 |
| 11.0.8 | anon | GZWinBtn | (147,112) 93x16 "Commercial Jobs" | (294,224) 186x32 |
| 11.0.9 | anon | GZWinBtn | (147,97) 94x16 "Resident Population" | (294,194) 188x32 |
| 11.0.10 | anon | GZWinBMP | (0,196) 258x43 — tail strip | (0,392) 516x86 |
| 11.0.11 | anon | GZWinBMP | (0,0) 258x196 — main backdrop | (0,0) 516x392 |
| 11.0.11.0 | anon | GZWinBMP | (12,10) 235x142 — inner plate | (24,20) 470x284 |
| ↳ **level 5 — never printed by RGKID** | | | | |
| — | `0x4A552000` | `0xAA7CECFD` / vt `00ABA190` | (8,4) 218x26 city name, `font=RegionLauncherCityName` | — |
| — | `0x4A552001` | `0xAA7CECFD` | (2,22) 230x26 mayor name | — |
| — | **`0x4A553000`** | **`0xAA5D16A9` cSC4WinAuraBar** | **(11,92) 102x11 — THE MAYOR RATING BAR** | — |
| — | `0x4A552002` / `0x4A552006` | GZWinText | (11,114) 123x20 funds (black / red variants) | — |
| — | `0x4A552003/4/5` | GZWinText | (158,87/102/118) ~68x18 res/com/ind pop | — |
| — | anon | GZWinText | (6,68) 227x18 "Mayor Rating:" caption | — |

**Start-new-city variant `I-0a8cd184`** — same id, 5 top-level children, all 2× again: `0x4A560003` (68,75) 36x29 → (136,150) 72x58; `0x4A560002` (31,75) 22x32 → (62,150) 44x64; `0x4A560000` (146,74) 55x46 → (292,148) 110x92; tail strip (0,112) 216x43 → (0,224) 432x86; backdrop (0,0) 216x112 → (0,0) 432x224 with inner plate (13,11) 191x57 → (26,22) 382x114. It has **no aura bar** — an unfounded tile has no rating.

> EVIDENCE — live log `RGKID 11.0.*` at 11:08:14.181 and 11:16:14.245; scripts `tools\uiscripts\extracted\T-00000000_G-96a006b0_I-{ca539340,0a8cd184}.ui`; staged 2x `tools\dialog-static\stage\T-0x00000000_G-0x96a006b0_I-0xca539340.ui` (`id=0x4a553000 area=(22,184,226,206)`).

**THE MAYOR RATING BAR IS A WINDOW.** It is fetched by id and driven every update:

```
007B514C  push 0x4A5D1208        ; iid (cISC4WinAuraBar)
007B5157  push 0x4A553000        ; window id
007B515E  call [edx+0x94]        ; GetChildAsRecursive(id, iid, &out)
007B5178  call [edx+0x10]        ; SetValue(double)  <- the rating, fld from [esp+0x18]
007B517E  push 0x14416327 ; push 0x46A006B0 ; call 0x602B70   ; its art, code-bound
```

Everything the "drawn twice" report needs is now measured: the bar's window **is doubled by our static dat** (102x11 → 204x22) while its art `{46A006B0,14416327}` — **102x26, exactly the shape of the HUD groove `14015549`, which we DO ship at 2x** — is **not in any tier's package list and is not staged**, so it stays 1x. 204 is exactly 2×102.

> EVIDENCE — `grep -c 14416327 tools\selective-safe\package-list{,-15x,-3x}.txt` → 0/0/0, and nothing staged; PNG `tools\dbpf\extracted\SimCity_1\T-856ddbac_G-46a006b0_I-14416327.png` = 102x26. `14015549` IS packaged (`package-list.txt:160`).

HYPOTHESIS (one build to settle): a 204-wide `cSC4WinAuraBar` over a 102-wide source repeats the source — the LEFT1X / tiled-art signature. Fix candidates, in order: (a) add `{46A006B0,14416327}` to `selective-safe` at 2x (consistent with `14015549`); (b) if the painter is not source-driven, LEFT1X-exempt `id=0x4a553000` in `build_dialog_static.py` so its `area=` stays 102x11. **Task #72 is a data fix, not an exe hunt.**

### 0.6 Lifecycle: region → city → region

**Nothing in the region host subtree survives a city visit.** On return, all nine panels are found at DESIGN geometry and re-scaled at boot-equal counts:

```
[11:11:01.429] RGKID  2 id=0x09EBE9EE … (5,1496 415x106)      <- design, i.e. rebuilt
[11:11:01.441] region screen up (2400x1600) - scaling.
[11:11:01.441] region panel 0x0BB0F5E7 - 10 windows scaled.   <- boot value
                   … 2 / 9 / 3 / 5 / 18 / 10 / 3 / 3          <- all boot values
```

and the bubble is gone from under `0x2BA6BB97` (RGKID 11 prints with no children). So a city entry destroys the region UI exactly as a live Load-Region switch does (§1), and the same recycled-address hazard applies — **the return is clean only because PURGE-ON-FRESH-ROOT is now shipping** (`UiSpike.cpp:7817-7830`). This is that fix's first measured proof on the *return* path, as opposed to the switch path.

> EVIDENCE — live log 11:11:01.429 / .441-.442 (session 2026-07-31 11:07:55, v2.37.0-dvorigin). NOTE: `SC4UIScale.log` is truncated on every launch — this session was overwritten by the 11:15:55 launch during the same hour. Copy any region evidence into `_tests\` before it rotates.

**What is reset, and by whom:**

| state | where | cleared on city entry? |
|---|---|---|
| `regionActive`, `regionChildCountSeen`, `regionStableTicks` | `UiSpike.cpp:8969-8977` (`!present` branch) | **yes** — the only region latches that reset |
| `scaleMap` records of the 68 destroyed region windows | `ResetTracking` (`4118-4126`) is **app-shutdown only**; `Disarm` (`4080-4116`) does not touch it | **no** — they persist as records keyed on freed pointers; the purge is what neutralises them |
| `Disarm`'s latch clears (`4105-4115`: minimap/DVMAP/UDMAP surfaces, `gReadyCount`, `healPhase`, `gFgWaitRoot`) | `4080-4116` | yes, but all are **city** latches — none is region |
| `rgkidSig` (`8895`, function-local `static`) | nowhere | **no** — a return whose signature hashes equal suppresses the dump |
| `NoteFlashCandidate::seen[96]` (`1552`) | nowhere | **no** — see §0.8 |
| `dialogDocked[]` | self-heals per dialog in `DialogDockTick` (`8772`); `DockDialogs=0` by default | n/a |

`RegionWatchTick` is additionally suppressed while `armed` (`4179`) so the region tree is never walked mid-teardown.

**Not measured: whether the host `0xEA659793` object itself is destroyed.** It is re-found by id every tick (`GetChildWindowFromIDRecursive`, `8886`), so the log cannot distinguish survival from same-tick recreation. `RGKID` prints `vt=%p` but not the window pointer — adding `self=%p` to the `RGKID` top-level line settles it in one region visit and costs nothing.

**Timing.** The sweep is a **16ms** tick, not 250ms (`Tick subclass installed (16ms)`, live log line 26; the 250ms figure comes from v2.6.0). The stability gate is two consecutive equal child counts ≈ 32ms, not the "~500ms" the comment at `8981-8984` claims. Measured latency from first `RGKID` to `region screen up` on a return: **12ms**.

### 0.7 What the region pass does NOT do

The region pass is a **whitelist-first** pass: `if (isRegionPass && !IsRegionPanelId(id)) continue;` is the first filter (`UiSpike.cpp:5261-5265`). Everything downstream is therefore reachable only by the nine, and none of the nine is in any of these lists — so on the region screen the following are **inert**:

- `kNeverScaleIds` / `IsNeverScaleId` (`5266`). Note `0x0A551C53` (region city-bubble stub) is listed there and is doubly inert: it is not a direct region child, and the whitelist already excludes it. Keep it as insurance, but it is not what protects the region screen.
- `IsGodToolFlyoutId` (`5274`), `IsMayorOnlyFlyoutId` (`5284`), `IsSubFlyoutId` (`5291`), `IsGodPanelId` / `IsAlwaysScaleCityId` (`5304-5305`) — all city-scoped.
- `ScaleGodFlyouts` + the MINIMAP / DVMAP / UDMAP surface-recreate blocks: explicitly gated `if (rootTag[0] != 'r')` (`5372`).
- The full-screen-overlay skip (`5329`) and the degenerate-size skip (`5334`) — the four layers are already excluded by the whitelist.

One thing is **not** rootTag-gated and does run on the region pass: the Data-Views lookup `pRoot->GetChildWindowFromID(0xAA32BCE6)` (`5360-5367`). It finds nothing — a STRUCTURAL null with a clean positive control: the identical call on the city pass does find it (`city panel 0xAA32BCE6 - 152 windows scaled`), and the region host's 13 children contain no `0xAA32BCE6`. Harmless; document it rather than "fix" it.

`DialogDockTick` is the mirror image: region-only, called from `RegionWatchTick` (`9029-9032`), and off by default (`DockDialogs=0`). Leave it off — `codecreated-noncity.md` records that enabling it would 4x the six region dialogs, which the static dat now also serves.

### 0.8 Instrument limits on this screen (read before believing a null)

1. **`RGKID` bottoms out four levels below the region host.** Its loops are `i` / `j` / `q` / `z` (`UiSpike.cpp:8910 / 8920 / 8936 / 8951`), deepest print at `8955`. The bubble is at `i.j` = level 2, so only levels 3 and 4 inside it print. **Every text node, the funds fields and the Mayor Rating bar sit at level 5 and CANNOT appear** — that blind spot is what produced the "the rating bar is not a window" conclusion. Positive control: the level-4 inner plate `11.0.11.0 (24,20 470x284)` does print, and the script says it has nine children; none appears.
2. **`RGKID` prints visible top-level children only** (`8913`), which is why the four born-hidden panels never appear in a dump.
3. **`FLASHSET` reports each window id AT MOST ONCE PER PROCESS** — `static uint32_t seen[96]` in `NoteFlashCandidate` (`1552-1556`), never reset by `Disarm` or `ResetTracking`. So the absence of `FLASHSET` lines at 11:11:01 is **not** evidence that the return did not flash; those five ids were already spent at 11:08:12. The instrument is structurally incapable of seeing a recurring flash. Given §0.6 (full rebuild at design geometry every return), **the region flash almost certainly recurs on every city→region transition and is currently un-instrumented.**
4. **`rgkidSig` is never reset**, so a region return with a byte-identical signature produces no dump at all.

### 0.9 Region laws

- **R1 — The region screen replaces the 3D view, it does not overlay it.** `0xEA659793` and `0x9A47B417` are alternative single children of `WinSC4App`. A window is reachable by the region sweep iff it is one of the nine direct children of `0xEA659793`.
- **R2 — Only nine of the thirteen are panels; four are full-screen layers and must never be scaled.** `kRegionPanelIds` is a complete cover of the panel set, not a sample.
- **R3 — Four of the nine are born hidden. Scale them anyway.** Pre-scale-while-hidden originated here; five visible panels flash, four hidden ones do not.
- **R4 — The game re-anchors region panels with CONSTANT pixel gaps; we re-anchor with SCALED gaps.** Two negative design gaps (`0x09EBE9EE` bottom −2, `0x09EBEE60` top −1) and one over-wide centred bar (`0x6A91DC14`, 1154px) mean any unconditional on-screen clamp is wrong here.
- **R5 — Anything under a full-screen layer is out of the sweep's reach and must be fixed in DATA.** The city-select bubble hangs under `0x2BA6BB97`; the static dat is its only lever.
- **R6 — `0x0A551C50` is ONE id for TWO scripts of different size and child count**, picked in code at `0x007ACC34`/`0x007ACC40`. Never key a record, a skip-list, or a geometry expectation on that id alone. (The narrow stub uses a third id, `0x0A551C53`, from `I-ca539343`.)
- **R7 — Region ids are not region-exclusive.** `0x0BB0F5E7` and `0x6BB92BCA` also exist under the 3D view at different design sizes, from different scripts. Any id-keyed rule written "for the region" must state which pass it is on.
- **R8 — Region UI does not persist. Every arrival is a fresh build**, whether by boot, by live switch, or by returning from a city — so PURGE-ON-FRESH-ROOT is load-bearing on all three paths, and so is the flash.

---

## BLOCK B — `tools\research\SC4-UI-ENGINE.md`

**B1 — §0 "THE BOUNDARY OF THIS SDK", delete the Mayor-Rating-bar row from the table and replace with this note under it:**

> **Retracted 2026-07-31 — the region bubble's Mayor Rating bar was never outside the boundary.** It is window `0x4A553000`, clsid `0xAA5D16A9` = **`cSC4WinAuraBar`**, declared in `I-ca539340` at `area=(11,92,113,103)` and fetched by the exe at `0x007B5157` (`push 0x4A5D1208; push 0x4A553000; call [edx+0x94]`) before `SetValue(double)` at `[vt+0x10]`. The "no window renders there" finding came from `RGKID` recursing only four levels below the region host while the bar sits at level five — a blind spot, not a measurement. **The three §0 triage tests must all be run against an instrument whose reach is stated**: criterion (a) "never appears as a window in a full-depth dump" is only usable if the dump really is full-depth.

**B2 — §1.1 "One tree, four hosts", add to the `0xEA659793` row / note:**

> `0xEA659793` is both a **clsid** (`cSC4WinRegionScreen`, registry `.data 0x00B08FC0`) and the host window's **id** — as is `0x9A47B417` (`cSC4View3DWin`) and `0x2BA6BB97` (`cSC4WinRegionView`). **Code-created top-level screens carry their clsid as their window id**; three for three. Its 13 children split 9 panels + 4 full-screen layers (`REGION-SWITCH.md` §0.1). The tooltip layer `0x2AAB8CC1` is a **sibling of `WinSC4App` under the main window** on the region screen; in a city there are **two** instances of that id as direct children of the 3D view (`VWKID 44` and `45`, both vt `0x00AB6770`, both full-screen) — another case for §1.3's "a global recursive id search returns the LAST-ADDED match".

**B3 — §1.4 geometry table, correct the confirmed-slots row:**

> Confirmed slots: `GetW +0xA4`, `GetH +0xA8`, `GetArea* +0xC0`, `SetW +0xCC`, `SetSize +0xD4`, `SetArea4 +0xDC`, `GZWinMoveTo +0xE0`, `GetChildWindowFromID +0x8C`, `GetChildAs +0x90`, `GetChildAsRecursive +0x94`, **`GetID +0xFC`, `SetID +0x100`**, `Show +0x110` / `Hide +0x114`.
> EVIDENCE — `GetID`: `0x004CB919 call [eax+0xFC]` with no pushed arg, `0x004CB91F cmp eax, 0x0BB0F5E7`. `SetID`: `0x007A99DF push 0x6A0AF41D; call [eax+0x100]`. `GetChildAs`: `0x004C59B7 push &out; push 0x22BA0121; push 0x0BB0F5E7; call [edx+0x90]`. `GetChildAsRecursive`: `0x007B515E`. Header order (`vendor\gzcom-dll\...\cIGZWin.h` 145-146) agrees; `GetID`/`SetID` are not an overload pair so the MSVC reversal rule does not apply. **The previously documented `SetID +0xFC` was off by one slot.**

**B4 — §2 widget catalogue, new row:**

| Class (clsid / vtable) | Size determined by | Art binding | SCALING RULE |
|---|---|---|---|
| **`0xAA5D16A9` = `cSC4WinAuraBar`** (iid `0x4A5D1208`; setter `[vt+0x10]` takes a `double`) | Its own `area=` | **code-bound TGI (Path 2)** — `{46A006B0,14416327}`, fetched at `0x007B517E` right after the window lookup | ⛔ Its window doubles with the script, its art does not. Ship the art 2x in `selective-safe` or the fill draws at source size in a doubled window. Sole known instance: the region bubble's Mayor Rating bar `0x4A553000`. The CITY HUD's rating bar is a **different implementation** (4× `GZWinBMP` + controller `0x7E86C0-0x7E8A80`) and shares nothing with it. |

**B5 — §8.5 "Flyouts, menus, minimaps, dialogs", append:**

| VA | what |
|---|---|
| `0x007A99C0` / `0x007A99DF` | region full-screen layer init; stamps id `0x6A0AF41D` via `SetID [vt+0x100]` |
| `0x007B0100–0x007B0B00` | region-screen init — re-finds the nine panels by id (`push <id>; call [reg+0x8C]`) |
| **`0x007ACC34` / `0x007ACC40`** | **city-select bubble VARIANT SELECT** — `{0xCA539340, 0x0A551C50}` (existing city) vs `{0x0A8CD184, 0x0A551C50}` (start new city), on the predicate at `0x007ACC2A` |
| `0x007B5AFD` / `0x007B5B02` | narrow-stub variant `{0xCA539343, 0x0A551C53}` |
| `0x007B5E20` | bubble controller setter — stores `scriptIID → [obj+0xF0]`, `windowID → [obj+0xF4]`, then walks its listener vector `[obj+0x100..0x104]` calling `0x007B59B0` |
| `0x007B4CE4` | bubble caption path — `GetChildWindowFromID(0x4A552000)` (city name) then `[vt+0x128]` |
| **`0x007B5157` / `0x007B5178` / `0x007B517E`** | **aura-bar drive** — `GetChildAsRecursive(0x4A553000, iid 0x4A5D1208)`, `SetValue(double)`, then art `{46A006B0,14416327}` via `0x00602B70` |
| `0x00B08F60–0x00B09010` | the window-class name registry rows quoted throughout §8 (`.data`, stride 8, `[clsid][char* name]`) |

---

## BLOCK C — `tools\research\DYNAMIC-CONTROLS.md`

**C1 — Q1 table, add a row (the "other custom clsids named while mapping" line already lists `0xaa5d16a9 cSC4WinAuraBar`; it now has a control):**

| Control (visual) | .UI clsid | Engine class | Window id(s) | Key code (VA) |
|---|---|---|---|---|
| Region city-bubble **Mayor Rating bar** | `0xaa5d16a9` | **cSC4WinAuraBar** | `0x4a553000` in `I-ca539340` (102x11) | fetch `0x7B5157` (iid `0x4a5d1208`, slot `+0x94`), `SetValue(double)` `[vt+0x10]` @ `0x7B5178`, art `{46a006b0,14416327}` @ `0x7B517E` |

**C2 — the "Mayor Rating bar + change arrows" row and §Q3, add the scoping note:**

> **These two rating bars are unrelated implementations.** The CITY HUD bar is four `GZWinBMP`s (groove `0x8a517556` art `14015549`, hidden `0x00008a50`, arrows `0x6a5a4156`/`0xca5a415e`) driven by controller `0x7E86C0–0x7E8A80` with the three `imul …,7` sites. The REGION BUBBLE bar is a single `cSC4WinAuraBar` (`0x4a553000`) fed a double at `0x7B5178`. `ApplyRatingArrowScale` therefore cannot affect the bubble — which is exactly what the 2026-07-30 `RatingArrowPatch=0` A/B measured. Keep the patch city-scoped; fix the bubble in art.

**C3 — "Method notes / reproducibility", correct the slot list:** replace `SetID +0xFC` with `GetID +0xFC, SetID +0x100` (see Block B3 for the two disassembly sites and the positive control).
