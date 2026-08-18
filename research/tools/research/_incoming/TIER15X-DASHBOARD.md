# TASK #101 - THE 1.5x CITY DASHBOARD IS UNUSABLE

Written 2026-08-03. Every number below is either read out of a preserved log, measured off
the preserved screenshot, read out of a `.ui` in `tools\uiscripts\extracted\`, or produced by
`tools\uimap\emu\emu_panel_anchor.py` (new, this task) which reproduces **39/39 panel
placements in the 2400x1600 f=2.0 capture and 39/39 in the 1400x1050 f=1.5 capture, with
zero mismatches**. Anything that is an inference is labelled INFERENCE.

---

## 0. THREE CORRECTIONS TO THE INSTRUMENTS, BEFORE ANYTHING ELSE

**0a. The preserved log is NOT an A/B. It contains ONE session.**
`_tests\captures\2026-08-03-TIER15X-dashboard-broken-SC4UIScale.log` is 1141 lines, has one
`SC4UIScale v2.55.0` banner on line 1, and every timestamp is 13:10-13:13.
`grep -c "12:5"` returns **0**. The 12:56 2x boot was truncated away when the 1.5x boot
started. The real 2x control is
`_tests\captures\2026-07-31-task89-ours-baseline-SC4UIScale.log` (v2.40.2-bigx, DirectX
FullScreen 2400x1600, tier 2.00, same city). All 2x numbers here come from that file.

**0b. The live composite script is `I-2bc90671`, NOT `I-898897de`.** Four `.ui` scripts
declare `0xE9889775`; two are 880x180. The earlier analyses quoted `I-898897de` (RCI at
design rel 278, buttons at 329..353). That is the wrong file. MEASURED, three children
independently:

| child | design rel in `I-2bc90671` | predicted at f=1.5, composite x=80 | logged |
|---|---|---|---|
| `0xAA9211B3` RCI meter button | (256,16) 42x118 | abs(464,793) 63x177 | `DPROBE ... abs(464,793) 63x177` |
| `0x09D27EB0` RCI column | (263,56) 8x71 | rel 395, abs(475,853) 12x107 | `RCI column ... post-pass (395,84 12x107)` + `DPROBE ... abs(475,853) 12x107` |
| `0x29D27EC0` RCI column | (273,56) 8x71 | abs(490,853) 12x107 | `DPROBE ... abs(490,853) 12x107` |

`I-898897de` predicts 407 / 417 for the first two and is refuted. Every button-cluster
coordinate in this brief therefore comes from `I-2bc90671`:
buttons `0xABC54125 / 0x49EDF9B7 / 0x00000041` at rel x 299..333 and
`0x99887755 / 0x15200002 / 0x15200003` at rel x 326..360.
**Design gap from the button column's right edge (139+360 = 499) to the polls panel
(l=501) is 2 px, not 7.**

**0c. The RCI lead in the task brief is CLOSED NEGATIVE.** Design 8x71 (`lookup.py
0x09D27EB0`); 2x log `16x142`; 1.5x log `12x107` = `round(8*1.5) x round(71*1.5)`. The RCI
columns scale correctly at both tiers, in size *and* in parent-relative position. They were
never unscaled - they were painted over.

---

## 1. THE CAUSE

**ESTABLISHED, for the primary symptom (RCI + button cluster invisible, empty right strip,
"Mayor Rat..."). One number accounts for all four.**

### 1.1 The mechanism

`src\UiSpike.cpp`, inside `ScalePanelRoot`, under the comment `// Scaled-gap anchoring:
uniform scaling about the nearer frame`:

```cpp
const int32_t cMinX = frameW / 4;
...
if (gapL > cMinX && gapR > cMinX)      newX = l + w / 2 - newW / 2;   // CENTER, f-free
else if (gapL <= gapR)                 newX = ScaleRound(gapL, f);    // EDGE-L
else                                   newX = frameW - ScaleRound(gapR, f) - newW;
```

The branch selector `frameW/4` is **frame-relative**. The design gaps it judges are
**frame-independent**: MEASURED, `0xE9889775` reports design `l=139` and `0x6A64E3C0`
reports design `l=501` in the 1400-wide capture *and* in the 2400-wide capture (only `t`
differs, because the game bottom-anchors). So which law a panel gets depends on the
monitor, not on the panel.

| frame | `cMinX` | composite `0xE9889775` gapL=139 | polls `0x6A64E3C0` gapL=501, gapR=W-1039 | same branch? |
|---|---|---|---|---|
| 2400x1600 f=2.0 | 600 | 139 <= 600 -> **EDGE-L** -> 278 | 501 <= 600 -> **EDGE-L** -> 1002 | YES |
| 1400x1050 f=1.5 | 350 | 139 <= 350 -> EDGE-L -> 209, clamped -> **80** | 501 > 350 AND 361 > 350 -> **CENTER** -> **367** | **NO** |

Both rows are log lines, not predictions:
```
[22:07:26.366] UiSpike: panel 0x6A64E3C0 (501,1412 538x135) -> (1002,1224 1076x270)
[22:07:26.368] UiSpike: panel 0xE9889775 (139,1413 880x180) -> (278,1226 1760x360)
[13:11:02.389] UiSpike: panel 0x6A64E3C0 (501,862 538x135)  -> (367,767 807x203)
[13:11:02.389] UiSpike: panel 0xE9889775 (139,863 880x180)  -> (80,769 1320x270)
```
Relative offset at 2x: 1002-278 = **724 = 2 x 362**, exact. At 1.5x: 367-80 = **287**, where
1.5 x 362 = 543. **Shear = -256 px.**

The CENTER branch contains no `f` at all, so `newX = 367` for the polls panel at *every*
frame width in the band. **The band is a WIDTH predicate, not a tier predicate: the two
panels take different branches for any render width `1386 <= W <= 2003`** (solve
`501 > W/4` -> `W < 2004`; `W-1039 > W/4` -> `W > 1385.3`). That contains **1400, 1440,
1536, 1600, 1680 and 1920** - and 1920x1200 too, which selects tier **2.0**.

### 1.2 The proof that this is the whole primary symptom - pixel spans, not adjectives

Screenshot `dashboard-15x-BROKEN-2026-08-03.png` is 1408x1092 = 1400x1050 client with a
+4,+38 chrome offset. I read it directly.

| symptom | arithmetic from log + `I-2bc90671` | in the image |
|---|---|---|
| polls panel position | logged `(367,767 807x203)` -> client x 367..1174 | left edge at image x 371, right edge 1178. **exact** |
| RCI columns invisible | abs 475..517 (DPROBE), inside 367..1174 | no RCI bars anywhere |
| button cluster invisible | abs 80+`SR(299..360,1.5)` = **529..620**, inside 367..1174 | no button column anywhere |
| "Mayor Rat..." | label `0x0A51201D` DPROBE abs(209,811) 248x36 -> 209..457, cut at 367 | text stops dead at image x 371, the polls panel's edge |
| right ~260 px empty | composite ends 1400, polls ends 1174 -> **226 px** of bare backdrop | bare dashboard from image 1178 to 1404 |

Under `--law fam` (the fix, section 3) the same adjudicator returns **PASS at 1400x1050,
1440x900, 1536x864, 1600x900, 1680x1050, 1920x1080, 2400x1600 and 3200x1800**.

### 1.3 A SECOND, INDEPENDENT DEFECT - established as a data fact, NOT yet causally proven

The remaining symptoms (funds/date leading digits, the news ticker's third line) are **not**
explained by the occlusion:
* the news ticker box is logged `(232,1002 757x43) -> (264,977 1136x65)`, client y 977..1042,
  image y 1015..1080 - **fully on screen**. The third line is cut by the **box**, not the
  window and not the polls panel.
* the date box reads `6/30/189` where a SC4 date is `6/30/1893`, and it is clipped at
  image x ~280, i.e. **client 276, which is 91 px LEFT of the polls panel's edge at 367**.
  Nothing is covering it.

MEASURED cause candidate, from the shipped tier tables (I re-derived this, 88-90 tokens each):

| table | tokens not exactly `1x * f` |
|---|---|
| `_working-backup\...\FontStyle-2x.ini` | **0 of 88** |
| `tools\packages\3x\FontStyle-3x.ini` | **1 of 90** (`Legend` 13->36, deliberate, #57) |
| `tools\packages\15x\FontStyle-15x.ini` | **41 of 90** |

Every odd 1x point size is **ceiled**, while the boxes scale by `ScaleRound` on the edges:

| token | 1x | 1.5x shipped | exact | ratio | box it overflows |
|---|---|---|---|---|---|
| `MayorFunds` | 13 | **20** | 19.5 | 1.5385 | funds |
| `MayorPop` | 13 | **20** | 19.5 | 1.5385 | population |
| `PUckDate` | 11 | **17** | 16.5 | **1.5455** | date |
| `PanelLabel` | 13 | **20** | 19.5 | 1.5385 | "Mayor Rating" |
| `Body` / `ListBoxItem` / `NewsBody`(14->21, exact) | 13 | 20 | 19.5 | 1.5385 | ticker |

`MayorRCI` (16->24) and `MayorMRating` (14->21) are exact, which is why the RCI numerals are
not reported clipped. **INFERENCE, clearly labelled:** that the ceil is what truncates the
date and funds. It is consistent (a 2.6-4.6 % overflow in a box that scaled exactly) and
nothing else on the left of x=367 could do it, but I have not measured Arta's rendered
extent at 17pt vs 16pt. Also unmeasured: `linespacing=2` is a **raw pixel** adjustment that
is byte-identical in the 1x and the 1.5x ini, which would explain a third line that no
longer fits a 65 px box. Do not "fix" either until measured.

**THE ONE MEASUREMENT THAT SETTLES IT is free** - it is the same eyes-on as section 5. Once
the anchor fix lands, nothing overlaps the funds/date/ticker. If they still truncate, it is
the font table. If they read in full, occlusion was the whole story and the font audit
becomes cosmetic.

---

## 2. IS IT OURS?

**YES, it is ours. It is NOT a regression - do not raise its priority on that ground, and do
not lower it either: it is P1 because 1.5x is the mainstream tier.**

**Stock is exonerated, and the stock control has ALREADY BEEN RUN - it is inside the log you
have.** Every `UiSpike: panel ...` line prints the rect **before** we touch it, so the
left-hand side of every arrow *is* the stock layout at 1400x1050. Positive control that this
field could have disagreed: it faithfully reports the intentional negative overhang
(`0xEA8CAD14 (0,-16 ...)`) and differs from the post-pass value on every single line.
And our `-15x` package does not pre-scale these roots - `lookup.py 0xE9889775` shows
`selective-safe/stage-15x` root `880x180`, byte-identical to stock.

Stock at 1400x1050: composite 139..1019, polls 501..1039, advisors strip 209..1049, news
195..1016. Widest right edge 1049 in a 1400 client = **351 px of slack**. Button column ends
at 499, polls begins at 501. **Stock cannot hide the RCI or the buttons at this resolution.**
Do not spend in-game time re-proving it.

**v2.55.0 is exonerated on all four symptoms.** Five checks:
1. **Temporal** - the dashboard was placed at 13:11:02.387-.390; the v2.55.0 legend patch
   armed at 13:11:02.393, **3-6 ms later**, and the last VWKID sample 50 s on still reads
   `0x6A64E3C0 (367,767 807x203)`, unchanged.
2. **The patched code never ran** - `grep -c " GKID"` = 0 and `grep -c "EARLYCHART store"`
   = 0 in that session. Zero charts were built (consistent with Graphs being unreachable).
3. **No shared builder** - both panels are `.UI`-declared and built by the generic loader,
   not by `sub_76D3D0`.
4. **The game's own pre-pass rects are bit-identical** between the v2.55.0 1.5x capture and
   the **v2.40.2** 2x capture for every city panel (the only 7 differences are region
   windows offset by exactly 1000 = 2400-1400).
5. **The mechanism is 11 days old, in source** - the branch sits under a comment block
   dated `NOTE (2026-07-23)`; there is no v2.55.0 marker anywhere in `ScalePanelRoot`. The
   font ceil predates it too: `MayorFunds`/`PUckDate`/`PanelLabel` are unchanged from the
   2026-07-23 golden backup.

**Not proven:** the 2x control is v2.40.2, 15 versions from v2.55.0. I proved today's named
changes are inert here; I did not bisect the whole span. A v2.55.0 2x boot would close it,
but the anchor code being 2026-07-23-dated makes that a formality.

---

## 3. THE FIX - EXACT PATCH

**Law:** the city bottom-HUD family co-anchors off ONE leader, so overlapping siblings
transform identically - which is what this file's own comment has promised since v2.12 and
does not deliver. Two constants, **both from one window**, so `python tools\sdk\lookup.py
0xE9889775` verifies the whole table.

**File:** `<HOME>\OneDrive\Projects\Surface 1 Project\1 Completed Projects\SC4TouchControls\src\UiSpike.cpp`
All three anchors verified **unique** (`count == 1`) against the current file. Match on text.

### HUNK 1 of 3

**ANCHOR TEXT**
```cpp
	inline int32_t ScaleRound(int32_t v, float f)
	{
		return static_cast<int32_t>(std::llround(static_cast<double>(v) * static_cast<double>(f)));
	}
```
**REPLACE WITH**
```cpp
	inline int32_t ScaleRound(int32_t v, float f)
	{
		return static_cast<int32_t>(std::llround(static_cast<double>(v) * static_cast<double>(f)));
	}

	// ---- #101 v2.56.0: THE CITY BOTTOM-HUD CO-ANCHOR ---------------------
	// ScalePanelRoot's generic anchor picks its branch by comparing a
	// FRAME-INDEPENDENT design gap against a FRAME-RELATIVE threshold
	// (frameW/4). MEASURED, not assumed: the game leaves this cluster at a
	// fixed design x - 0xE9889775 reports l=139 and 0x6A64E3C0 reports l=501
	// in BOTH the 1400x1050 capture and the 2400x1600 capture; only t moves,
	// because the game bottom-anchors. So the branch a panel gets depends on
	// the MONITOR, not on the panel: at any render width in 1386..2003 the
	// polls panel crossed frameW/4 and flipped to the f-free CENTER law while
	// the composite it RIDES ON stayed EDGE-L. Measured shear -256px at
	// 1400x1050; -385px at 1920x1080, which is the mainstream 1.5x
	// resolution. The polls panel then painted over the RCI meter and the
	// entire button column, and Graphs could not be opened at all.
	//
	// Cure = what this file's own anchor comment already promises: "both must
	// transform identically for their relative layout to survive". The family
	// co-anchors off ONE leader, so relative layout is exactly x f at every
	// frame width and the branch heuristic never gets a vote.
	//
	// TWO CONSTANTS, BOTH FROM ONE WINDOW (so `python tools\sdk\lookup.py
	// 0xE9889775` verifies the whole table): design l = 139, and design right
	// edge = 139 + 880 = 1019 where 880x180 is the .UI root of the LIVE
	// declaring script T-00000000_G-96a006b0_I-2bc90671.ui. That the LIVE
	// script is 2bc90671 and not the other 880-wide variant 898897de is
	// MEASURED from three of its children: at f=1.5 with the composite at
	// x=80 this script predicts 0xAA9211B3 abs(464,793) 63x177 and
	// 0x09D27EB0 abs(475,853) 12x107, and the log's DPROBE prints exactly
	// those. 898897de predicts 407/417 and is refuted.
	const int32_t kCityHudLeaderL = 139;
	const int32_t kCityHudLeaderR = 1019;

	// Every city root the game places at a frame-independent design x on the
	// dashboard row. MEASURED membership: each id below reports the SAME
	// design l in the 1400x1050 capture and in the 2400x1600 capture. The
	// leader is a member of its own family, so its own x is unchanged by
	// definition - nothing that docks against it (the minimap cluster) moves.
	const uint32_t kCityHudFamilyIds[] = {
		0xE9889775, // composite status HUD  <-- LEADER (design l 139)
		0x698894D3, // My Sims outer root                          139
		0xCA1F1D9C, // My Sims content panel                       149
		0xEA1F1E4E, // find-sim overlay                            153
		0xEA1F1E4D, // Sim detail / news strip                     195
		0x6A15C767, // Advisors console strip                      209
		0xAA15EF06, // advisor briefing (compact)                  209
		0xAA3AC000, // budget compact bar                          210
		0xC98F49F1, // city panel variant                          232
		0xCA2AEDC0, // news ticker strip                           232
		0xAA1F1EC5, // My Sims dialog                              263
		0xABBAA2D3, // Sim actions strip                           321
		0x6A61E29F, // Sim profile strip                           321
		0x2A1D96B1, // advisor briefing (expanded)                 482
		0xAA3AC001, // budget expanded                             483
		0xABC619D2, // Building Style Control  489 - 1.5x capture ONLY. Its
		            // 2x placement is a MODEL prediction (978 = the generic
		            // law's own EDGE-L output at 2400), never observed.
		0xAA32BCE6, // Data Views panel                            494
		0x0A4A8176, // graphs/data root C                          494
		0x8A8B5B71, // graphs/data root A                          495
		0x8A8B5B72, // graphs/data MIDDLE root                     495
		0x6A64E3C0, // City Opinion Polls                          501
	};
	inline bool IsCityHudFamilyId(uint32_t id)
	{
		for (uint32_t known : kCityHudFamilyIds)
		{
			if (id == known) { return true; }
		}
		return false;
	}

	// The leader's scaled x, clamped ONCE for the whole family. Members are
	// never clamped individually: individual clamping is exactly what shears
	// them apart today (11 of the 15 bottom panels were pulled back by
	// DIFFERENT amounts at 1400x1050, up to 90px of relative shear between
	// two siblings). Union-rect containers are ALL-OR-NONE.
	inline int32_t CityHudOriginX(int32_t frameW, float f)
	{
		int32_t origin = ScaleRound(kCityHudLeaderL, f);
		const int32_t span =
			ScaleRound(kCityHudLeaderR, f) - ScaleRound(kCityHudLeaderL, f);
		if (origin + span > frameW) { origin = frameW - span; }
		if (origin < 0) { origin = 0; }
		return origin;
	}
```

### HUNK 2 of 3

**ANCHOR TEXT**
```cpp
		int32_t newX;
		if (gapL > cMinX && gapR > cMinX)
			newX = l + w / 2 - newW / 2;
		else if (gapL <= gapR)
			newX = ScaleRound(gapL, f);
		else
			newX = frameW - ScaleRound(gapR, f) - newW;
```
**REPLACE WITH**
```cpp
		// #101: the city bottom-HUD family co-anchors off ONE leader so that
		// overlapping siblings transform identically. Adjudicated offline
		// before this was built, with tools\uimap\emu\emu_panel_anchor.py:
		//   0 of 39 panels move at 2400x1600 f=2.0 (the USER-CONFIRMED tier)
		//   20 of 39 move at 1400x1050 f=1.5, all of them toward the design
		//   layout, and the leader itself does not move at either.
		// Family X is deliberately NOT clamped per-member below (clampX
		// stays false): CityHudOriginX already decided the family's fit, and
		// a per-member clamp is precisely what shears the family apart.
		int32_t newX;
		bool clampX = true;
		if (IsCityHudFamilyId(win->GetID()))
		{
			newX = CityHudOriginX(frameW, f)
			     + ScaleRound(l, f) - ScaleRound(kCityHudLeaderL, f);
			clampX = false;
		}
		else if (gapL > cMinX && gapR > cMinX)
			newX = l + w / 2 - newW / 2;
		else if (gapL <= gapR)
			newX = ScaleRound(gapL, f);
		else
			newX = frameW - ScaleRound(gapR, f) - newW;
```

### HUNK 3 of 3

**ANCHOR TEXT**
```cpp
		if (gapR >= 0 && newX + newW > frameW) newX = frameW - newW;
		if (gapL >= 0 && newX < 0) newX = 0;
```
**REPLACE WITH**
```cpp
		if (clampX && gapR >= 0 && newX + newW > frameW) newX = frameW - newW;
		if (clampX && gapL >= 0 && newX < 0) newX = 0;
```

`cMinX` remains in use by the non-family path; `cMinY` and the whole Y axis are untouched
(the Y branch tally is EDGE-B 28 / EDGE-T 11 at 2x and EDGE-B 29 / EDGE-T 10 at 1.5x, with
CENTER **never** taken in either capture - so Y is measurably not implicated).

### 3.1 THE RESULTING NUMBERS AT 1.5x, 2x AND 3x

`emu_panel_anchor.py --dash <W> <H> <f> --law fam`. "clearance" = polls left edge minus the
button column's right edge; design gap is 2 px, so the target is `round(2*f)`.

| frame | f | composite x | polls x | RCI cols | button column | clearance | verdict |
|---|---|---|---|---|---|---|---|
| 1400x1050 | 1.5 | **80..1400** (unchanged from today) | 623..1430 | 475..517 | 529..620 | **+3** (want +3) | PASS |
| 1440x900 | 1.5 | 120..1440 | 663..1470 | 515..557 | 569..660 | +3 | PASS |
| 1536x864 | 1.5 | 209..1529 | 752..1559 | 604..646 | 658..749 | +3 | PASS |
| 1600x900 | 1.5 | 209..1529 | 752..1559 | 604..646 | 658..749 | +3 | PASS |
| 1680x1050 | 1.5 | 209..1529 | 752..1559 | 604..646 | 658..749 | +3 | PASS |
| **1920x1080** | 1.5 | 209..1529 | 752..1559 | 604..646 | 658..749 | **+3** | PASS |
| **2400x1600** | **2.0** | **278..2038** | **1002..2078** | 804..860 | 876..998 | **+4** (want +4) | PASS |
| 3200x1800 | 3.0 | 417..3057 | 1503..3117 | 1206..1290 | 1314..1497 | **+6** (want +6) | PASS |

Today, for comparison: clearance **-253 px** at 1400x1050 and **-382 px** at 1920x1080.

**2x DOES NOT MOVE. This is the hard requirement and it is met by construction and verified
by replay: `--blast <2x capture> 2400 1600 2.0 --law fam` prints `0 panels move of 39`.**
The composite 278 and polls 1002 in the table are the *logged* values from the 2400x1600
capture, reproduced by the new law. Same for 3x: at every frame that can select 3.0 the
family origin is `ScaleRound(139,3) = 417` with no clamp, so every member is exactly
`ScaleRound(l,3)` - which is what the generic law already produces there. **The patch is a
no-op at 2x and at 3x. It only bites inside the 1386..2003 width band.**

### 3.2 THE PRICE, STATED

At a frame narrower than `ScaleRound(1049, f)` = 1574 px, the family members that are wider
than the leader hang off the right edge: at 1400x1050 the polls panel by **30 px** and the
advisors strip by **45 px**. That is real and it is not hidden by the fix - `1.5 x 1049 =
1574 > 1400`, so the dashboard genuinely does not fit at that width. The alternative
(clamping the origin against the family's right edge 1049 instead of the leader's 1019)
loses nothing but drags the composite 45 px further left to x=35, which un-pins the minimap
dock that sits in the composite's left well. **Leader-pinned is the conservative choice: the
composite's x is unchanged at every frame width, today's value included.** The proper cure
for the residual is the fit gate, section 6.

---

## 4. THE OFFLINE GATE

**The dashboard was NOT modelled offline, and neither was any of our own layout code.**
Everything under `tools\uimap\emu\` models *SimCity 4's* machine code (`emu_layout.py` runs
`sub_779660` under Unicorn, etc.). `grep -rl "cMinX\|ScalePanelRoot"` over `tools\` returns
only `.md` files. That is why #101 shipped blind: no gate existed that could see our own
anchor.

**It exists now.** `tools\uimap\emu\emu_panel_anchor.py` (created this task, 0 external
deps, runs in under a second):

* transcribes the anchor block line for line - edge-derived `newW/newH`, the double-scale
  guard, `cMinX/cMinY`, the three-way per-axis branch and all four per-edge conditional
  clamps - and says in its own header what is REAL and what is NOT covered (EARLYDOCK, the
  `kCityDialogIds` re-centre, the AlreadyScaled bookkeeping).
* **states its positive control:** the emitter it replays
  (`"UiSpike: panel 0x%08X (%d,%d %dx%d) -> (%d,%d %dx%d)"`) has **no counter, no cap and no
  spatial band**, unlike `DPROBE` (which is `gProbeMax = 30` AND band-limited to
  `gProbeL..gProbeR = -150..500`, and is saturated at 30/30 in BOTH logs). So `--check`
  compares against a complete population and a 0-mismatch result is a measured pass.

Three modes, and the exact commands the orchestrator should run:

```
:: 1. REGRESSION - the model must still reproduce every capture we hold
python tools\uimap\emu\emu_panel_anchor.py --check _tests\captures\2026-07-31-task89-ours-baseline-SC4UIScale.log 2400 1600 2.0
python tools\uimap\emu\emu_panel_anchor.py --check _tests\captures\2026-08-03-TIER15X-dashboard-broken-SC4UIScale.log 1400 1050 1.5
::    -> "39 panels, 39 match, 0 MISMATCH"  x2   (verified today)

:: 2. BLAST RADIUS - THE GATE. Must print "0 panels move" or the patch is rejected.
python tools\uimap\emu\emu_panel_anchor.py --blast _tests\captures\2026-07-31-task89-ours-baseline-SC4UIScale.log 2400 1600 2.0 --law fam
::    -> "0 panels move of 39"   (verified today)

:: 3. ACCEPTANCE - the dashboard occlusion adjudicator, at any frame, no game
python tools\uimap\emu\emu_panel_anchor.py --dash 1920 1080 1.5 --law fam   -> PASS (+3)
python tools\uimap\emu\emu_panel_anchor.py --dash 1920 1080 1.5 --law cur   -> FAIL (-382)
```

`--dash` is a real adjudicator, not a sighting: it fails on the *specific* condition the user
reported (polls left edge left of the button column's right edge), so it distinguishes a fix
from a near-miss.

**Standing value beyond this fix, which is the point:** every future change to
`ScalePanelRoot` can be blast-tested against the shipping tier for free, and any new capture
(at any resolution) drops straight into `--check` and permanently widens the population. Add
both `--check` lines and the `--blast`-must-be-0 line to `_tests\REGRESSION.md`.

---

## 5. THE EYES-ON STEP, PRE-COMMITTED

**Test at 1920x1080, NOT at 1400x1050.** Reasons, all measured: 1080p is the mainstream 1.5x
resolution and the one that matters; at 1920 the family needs no clamp at all, so the result
is the *pure* geometry rather than a clamped edge case; `1.5 x 1049 = 1574 <= 1920` so
nothing hangs off; and it still fits windowed inside the user's 2400x1600 monitor
(1928x1122 with chrome). Height 1080 selects 1.5x because `558 x 2 = 1116 > 1080`, confirmed
by the same rule that produced the broken capture.

**Config** - `SC4GraphicsOptions.ini`, written **without a BOM**
(`Set-Content -Encoding utf8` only; a BOM makes the DLL abandon the file and boot windowed
at the wrong size):
```
WindowWidth=1920
WindowHeight=1080
WindowMode=Windowed
```
WINDOWED IS REQUIRED - DirectX FullScreen renders at the monitor's native mode regardless of
the request, which silently yields tier 2.0 and measures the wrong thing. Confirm in the log
before believing anything:
```
AutoScale: DirectX Windowed - render res = window 1920x1080
AutoScale: 1920x1080 -> tier 1.50 (scaling active)
```
Deploy with `_tests\Deploy-OnGameClose.ps1` (the game runs elevated and holds the DLL open -
never kill it).

**WHAT TO CLICK.** Load Centropolis and look at the bottom-left dashboard. **Do not open
Graphs** - it is unreachable at this tier today and the test must not depend on it. Click the
**City Opinion Polls** button (`0x15200003`, bottom of the right-hand button column) to bring
the polls panel up beside the HUD. That is the entire interaction.

**PASS looks like:**
* the three RCI columns and the RCI meter button are **fully visible** (predicted at client
  x 604..646 and 593..656 respectively - both entirely left of the polls panel at 752);
* the **six-button column is fully visible** at client x 658..749, and every button is
  clickable;
* the **City Opinion Polls panel sits to their RIGHT**, starting at client x 752, with a
  ~3 px gutter - it must not cross the button column;
* "Mayor Rating" reads in full;
* the dashboard's right end is at client x 1529, and the strip does **not** end in a wide
  band of empty backdrop;
* **Graphs opens** when its button is clicked (that button being reachable at all is the
  headline result).

**FAIL looks like:** the polls panel starting left of x ~750, or any RCI bar / button hidden
behind it, or a wide empty strip on the right. Capture the log **and** a game-window-only
screenshot either way, and copy them into `_tests\captures\` **under new names** - the 1.5x
log is truncated on every boot and the 2026-08-03 file is the only record of the broken
state.

**Report separately, do not treat as FAIL of this patch:** whether the funds box, the date
box and the news ticker's third line read in full. Nothing overlaps them after this fix, so
that observation is the free measurement that settles section 1.3.

**A second boot at 1400x1050 Windowed is optional and lower value.** If it is run, expect
PASS on the occlusion test (clearance +3) plus a visibly clipped right edge on the polls
panel (30 px) and the advisors strip (45 px). That is the stated price, not a new defect.

---

## 6. WHAT THIS SAYS ABOUT THE OTHER TIERS

**2x - extensive eyes-on, and this patch is a measured no-op there.** `--blast` on the
2400x1600 capture prints `0 panels move of 39`. The 2x font table is `0 of 88` tokens off
exact. Nothing in this task should change 2x, and the gate proves it before a build exists.

**1.5x - one eyes-on, broken; every other 1.5x claim we have ever made is arithmetic.** Two
independent defect classes are now on record at this tier and only at this tier: the anchor
band (a *width* defect that happens to catch every mainstream 1.5x resolution) and the
`41 of 90` ceiled font tokens. Both existed for weeks. The lesson is not about the anchor -
it is that **a tier with no eyes-on is an untested tier no matter how much arithmetic backs
it**, and 1.5x is the tier most users will actually get.

**3x - NEVER OBSERVED, AND CANNOT BE ON THIS HARDWARE. Name it and accept it.**
`ScaleTier::Decide` needs `558 * 3 = 1674` px of height for the Graphics Options dialog; the
user's monitor is 2400x**1600**. There is no windowed or fullscreen configuration on this
machine that selects 3.0. **Consequence, stated plainly: every 3x statement we ship -
including this brief's `--dash 3200 1800 3.0 -> PASS` - is a MODEL RESULT, not an
observation.** The model is credible (it reproduces 39/39 real placements at two other
factors) but it is not eyes-on. If 3x is ever to be shipped as verified, it needs either a
>=1800-tall display or an explicit lowering of `kTallestDesignPx`, and until then 3x should
be described in release notes as *generated and modelled*, never as *tested*. One mild
comfort: the 3x font table is `1 of 90` off exact (the deliberate `Legend`), so the font half
of the 1.5x class does not exist at 3x.

**Two residuals this turned up. Both real, both OUT OF SCOPE for #101 - raise as their own
tasks, do not bundle:**

1. **`kWidestDesignPx = 880` in `src\ScaleTier.cpp:14` is the wrong quantity.** It is the
   composite's *width*, but the anchor places panels at `ScaleRound(l,f)`, so the binding
   quantity is a design *right edge*. Our own guard already proved it at 1400x1050:
   `UiSpike: panel 0x6A91DC14 target 1731x77 exceeds frame 1400x1050 - SKIPPED
   (double-scale guard) and tombstoned` - the region top bar is 1154x51 design and
   `1154 * 1.5 = 1731`. That guard's own comment says the line should NEVER appear in a
   healthy log. Honest thresholds are 1574 (advisors strip) or 1731 (region top bar), which
   would drop 1400x1050 / 1440x900 / 1600x900 / 1680x1050 to stock and 1920x1200 from 2x to
   1.5x. **That is a product decision, not an engineering one, and it does NOT cure #101** -
   1920x1080 passes every candidate gate and is still broken without the section 3 patch.
2. **Region strip `0x09EBEE45` is clamped to x=0 at 1.5x** (`(318,4 778x204) -> (0,6
   1167x306)`) - it is genuinely frame-centred (design l = 318 at 1400, 818 at 2400, delta
   exactly `(2400-1400)/2`) and takes the EDGE-R branch instead. Same family of defect,
   different window set, not touched by this patch.

---

## 7. CONFIDENCE

| claim | basis | confidence |
|---|---|---|
| the anchor branch flip is the cause of the RCI / button / empty-strip / Mayor-Rating symptoms | 4 log lines + 5 matched pixel spans + a replica that reproduces 39/39 at both tiers | **HIGH - established** |
| stock is fine at 1400x1050 | pre-pass rects in the log at that exact resolution, with a stated positive control | **HIGH - measured** |
| v2.55.0 is not implicated | 5 independent checks incl. a 3-6 ms temporal ordering and a zero-execution count | **HIGH** |
| the section 3 patch is a no-op at 2x and 3x | `--blast` replay = 0 of 39 at 2x; identical `ScaleRound(l,f)` output at 3x | **HIGH at 2x (replayed against real data), MEDIUM at 3x (model only, never observed)** |
| the section 3 patch cures the symptom at 1920x1080 | `--dash` adjudicator, model | **MEDIUM-HIGH - model, pending eyes-on** |
| the ceiled 1.5x font table is what truncates the date / funds / ticker | 41 of 90 tokens measured off-exact; the clipped pixels are 91 px clear of any overlap | **INFERENCE - do not fix before section 5 measures it** |
| the button cluster's live rects | design data (`I-2bc90671`) + screenshot, cross-checked; `DPROBE` is band-limited to x<500 and has **never** measured them live | **MEDIUM-HIGH - two instruments agreeing, neither of them the live log** |
| 3x behaviour, anything | model only, unobservable on this display | **LOW as evidence, and named as such** |

**One knob worth turning on the next capture, and it is NOT the one previously suggested:**
`DPROBE`'s missing button-column lines are caused by the **spatial band**
(`gProbeR = 500`, `src\UiSpike.cpp:257-262`), not by the 30-line cap - the DFS had logged
only 18 entries when it left the composite's sibling list. Raising `[Probe] Max` changes
nothing. Raise **`[Probe] BandR` to 1400** (parsed at `src\UiSpike.cpp:8956-8966`) and the
button column adjudicates itself for the first time ever.
