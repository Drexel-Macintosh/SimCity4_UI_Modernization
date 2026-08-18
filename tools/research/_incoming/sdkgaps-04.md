# TARGET: PRIMARY: `tools\research\SC4-UI-ENGINE.md`
 - **§2 "Widget catalogue"** — insert new **§2.0** before the table; **replace/extend the table rows** listed below; append new **§2.4** (blind spots) and **§2.5** (identification procedure). Existing §2.1/2.2/2.3 renumber to §2.2/2.3/2.4 or keep and add mine as §2.5–§2.7 — either is fine, the blocks are self-contained.
 - **§8** — new sub-block **§8.6 "Class registries and window-class vtables"**; three corrections inside §8.4/§8.5.
 - **§9 "Where the existing docs contradict each other"** — four new numbered entries (12–15).
SECONDARY:
 - `_tests\REGRESSION.md` — addendum under "# 2026-07-30 — THE PAUSE BORDER: DECODED TO A DEAD END (task #59)".
 - `tools\research\METHOD.md` — one paragraph under "YOUR OWN INSTRUMENTS CAN LIE".

## SUMMARY
The widget catalogue is now derived, not inferred. Two naming tables were found inside the exe — the `.UI` class registry at `0x00B16FA8` (21 entries × 12 bytes: clsid, iid, name string) and the GZCOM clsid→name table spanning ~`0x00B05000`–`0x00B0B000` (906 {id, char*} pairs) — and from them all 21 `.UI` widget classes and every SC4-specific window class seen live were mapped to a concrete cIGZWin vtable, clsid, iid, ctor and Plot. A whole-image census finds 115 cIGZWin vtables in the exe; 22 distinct ones appear in the live logs; the current catalogue names 10 of those, so 12 live vtables were blind spots and are now filled in. Three findings change existing doc text rather than extend it: (1) `vt=` values in the `0x6C……`/`0x6F……` range in our own logs are SC4UIScale's own shadow vtable copies, not game classes — they move between sessions, which is the positive control; (2) clsid `0xAA7CECFD` ("unnamed", 56 uses) is `cSC4WinText` in the vendor header and is measurably a plain `cGZWinText` object whose vtable differs from `GZWinText` in exactly two slots (Plot + deleting dtor), so the "resolved independently of the GZWinText name path" mechanism in the doc is wrong; (3) a live, always-present, full-screen (`0,0 2400x1600`) window `0x6A5E44B6` of class **cSC4WinAlertBorder** hangs off the 3D view, and its Plot is a tiling nine-slice frame painter whose only tiler caller in the whole exe was never audited — which is a concrete, un-eliminated candidate for the task-#59 pause border and explains why VisTrace could not see it.

## CONTRADICTIONS
- SC4-UI-ENGINE.md §2 catalogue, GZWinCustom row: "⛔⛔ POSITIONING DATA. NEVER SCALE IT — not at runtime, not in shipped data." CONTRADICTED at runtime by our own shipped behaviour: the sweep does double 0x0000AAAA markers. Measured: tools\research\_checkpoints\pds-cache\SC4UIScale-snapshot.log:37 `RGKID 3.0 id=0x0000AAAA vt=00AD6AA0 (110,0 20x20)` and :109 the same node at `(220,0 40x40)`. It is harmless only because every consumer we ship (UiSpike.cpp:2505 offX and the marker table 2522–2564) uses a BAKED 1x offset, never the live marker. The data half of the rule is correct (build_dialog_static.py skips the tag).
- SC4-UI-ENGINE.md §2 catalogue, `0xAA7CECFD` row: "unnamed in the registry" and "Its font style, resolved independently of the GZWinText name path". BOTH wrong. It is named `cSC4WinText` in vendor\gzcom-dll\gzcom-dll\include\GZCLSIDDefs.h:285 (kcSC4WinText = 0x0AA7CECFD). And its factory 0x007BE740 runs cGZWinText's OWN constructor 0x009C19C8 on a 0x114-byte object and then swaps the vtable; a slot-by-slot diff of 0x00ABA190 vs GZWinText's 0x00ADFEB8 differs in exactly two slots, 88 (Plot) and 148 (dtor). It is the SAME font code, not an independent path.
- The task brief's own vtable shortlist: "0x00AB8150 (data-view panel)". CONTRADICTED — 0x00AB8150 is not a window vtable at all. It fails the universal window fingerprint [vt+87*4] == 0x0099BE4C (its slots read 0x800B / 0x800A / 0x6005 / 0x5007) and is the secondary COM interface vtable of cSC4WinMapView (clsid 0x28C5A41F, ctor 0x007A0280, factory 0x00466080 returning obj+0xE0). It appears in NO log in Documents\SimCity 4\Plugins. The Data-Views map child is a cSC4WinMiniMap (0x00AB83B8), which §2 already says.
- SC4-UI-ENGINE.md §8.4 and §2, cSC4WinAdviceList: "draw-self is a no-op `mov al,1; ret` @ 0x949ADE" reads as a property of that class. 0x00949ADE is cGZWin::Plot — the BASE no-op — shared by GZWin itself (vt 0x00ADC8D8), cSC4WinAdviceList (0x00AB58B0) and 0x00ADCB38, plus ~14 other classes in the census. Not a correction of fact, but the attribution is misleading and matters for step 4 of the identification procedure.
- _tests\REGRESSION.md "THE PAUSE BORDER: DECODED TO A DEAD END (task #59)" and HANDOFF.md "SKIPPED BY DECISION": "the pause border is NOT reachable from any UI-side lever, and that is now proven, not assumed." NOT YET SAFE. A live full-screen window 0x6A5E44B6 of class cSC4WinAlertBorder (clsid 0xCA5D3294, vt 0x00AB5B48, Plot 0x00794100) is created by the 3D view at 0x007EF029–0x007EF078 and appears in every view dump at (0,0 2400x1600). Its Plot is a tiling nine-slice FRAME blit (source cell = imgW/3 × imgH/3) over its own absolute rect via 0x008D9550 -> 0x008D8BC0. The write-up's offline decode audited helper 0x008D8800 ("6 callers, none a full-screen painter") — the wrong helper; 0x008D9550 has exactly one caller and it is this Plot. And VisTrace could not have seen it: the window never flips visibility and is never created late; only an internal image pointer [+0xE4] and flag [+0xE8]->[0x0C]->[0x45C] change. This is a HYPOTHESIS about the pause border, not a proof — but the existing null is a blind-spot null, not a measured one.
- GOD-MODE-FLYOUTS.md / §2.1 read against a current log: the shared sub-flyout container 0x8A6E61E0 now prints `vt=6F101F70`, not `vt=00AB6AA8`. Not a doc error — that is OUR shadow vtable (gVtCopy) installed by SUBBORNHOOK — but any reader diffing logs against the doc will think the class changed. Needs an explicit note; the same id printed 6C461F70 in the previous session and 6F101F70 in this one.

## OPEN
- Does cSC4WinAlertBorder actually paint the pause frame? THE TEST: hook slot 88 of vt 0x00AB5B48 (PatchFlashGuardClass already patches exactly this vtable — see `[11:08:17.531] DFG patched class vt=00AB5B48 Plot=00794100 (idx 3)`) and log [this+0xE4], [this+0xE8]->[0x0C]->[0x45C] and the computed W/3 x H/3 cell on state change. POSITIVE CONTROL: the hook must emit at least one line before pausing, or the null is another blind spot. If it fires on pause, the source cell is blitted 1:1 (the GZWinBMP law) and the cure is 2x art on its code-bound TGI with no code at all.
- Which TGI feeds cSC4WinAlertBorder? The three-image setter is 0x007942F0 (fills [+0xE0]/[+0xE4]/[+0xE8] via vt+0x1B0 three times). Its caller was not traced this session — that caller holds the code-bound TGI constants, i.e. the art pass target if the test above is positive.
- What are region layers A/B/C for? 0x00AB88C0 (id 0x6A0AF41D, at regionScreen+0xE4), 0x00AB8CD0 (+0x174), 0x00AB8F50 — all full-screen, all bare cGZWin subclasses identifiable only by Plot. Layer A's Plot 0x007A9D60 is gated on four resources fetched with iids 0x1AC0E11A / 0xFAC0E219 and four consecutive ids 0x4A624656..0x4A624659, and drives a sprite object (0x0088FEFB / 0x008905C4 / 0x00890198). None is currently scaled; none is known to need it. Resolve before any region-screen work touches full-screen layers.
- 0x00ADCB38 is a cGZWin subclass whose ONLY override is slot 89 CalcAbsoluteArea (0x0099C291 vs base 0x0099BA07) — a coordinate-remapping/clip viewport that paints nothing. It appeared 7x in the live tree as an anonymous view child. Which panels sit inside one, and does the sweep's rect math stay correct across it? A remapping ancestor is exactly the shape of a silent off-by-a-scale-factor bug.
- Six of the 21 .UI classes resolved cleanly by factory but their QueryInterface was not reached by the iid-xref route (GZWinGrid, GZWinOutline, GZWinTextTicker, GZWinFileBrowser, GZWinTreeView, GZWinFolders) — their QI is presumably a thunk chain. The vtables are firm (factory -> ctor -> single .rdata store, all present in the 115-entry census); only the QI cross-check is missing. Low risk, worth closing if any of them is ever hooked.
- cSC4WinAuraBar (clsid 0xAA5D16A9, vt 0x00AB64B8, Plot 0x00797CC0, ctor 0x00797E60) is registered and shipped but has never appeared in any log. STRUCTURAL NULL, not a measured one — no session has opened whatever hosts it. Worth one targeted look before the next release, since an unexercised painter is an untested scaling path.
- The exe has 115 window classes; one session exercised 22. Closing the catalogue honestly needs a coverage pass driven by the SCENARIO MATRIX (_tests\SCENARIOS.md) rather than by ad-hoc play, so that 'never seen live' becomes a measured statement per class instead of a coverage artefact.

---

# ============================================================================
# BLOCK 1 — insert as `### 2.0 The two registries that name every widget`
# (SC4-UI-ENGINE.md, immediately after the "## 2. Widget catalogue" heading
#  and before the existing table)
# ============================================================================

### 2.0 The two registries that name every widget

Nothing below is inferred from behaviour. The exe carries **two name tables**,
and between them every window class in the game can be named without a single
guess.

**(a) The `.UI` class registry — `0x00B16FA8` … `0x00B170A3`, 21 entries of 12
bytes: `{clsid, iid, char* name}`.** This is what the `.UI` deserializer walks
when it meets a `clsid=` attribute. It is the authority for the `GZWin*`
family and it is complete — there are exactly 21 scriptable widget classes.

> EVIDENCE: `0x00B16FF0 = 0x22ECFC47`, `0x00B16FF4 = 0x00008810`,
> `0x00B16FF8 -> 0x00AD5CAC "GZWinBtn"`; the iid column reproduces the two iids
> this doc already carried (`GZWinBtn 0x00008810`, `GZWinBMP 0xC12CEA13`),
> which is the cross-check that the column order is `{clsid, iid, name}`.

⚠ **Correction to §2's table header text.** What §2 currently calls the
"descriptor" of `GZWinBMP` (`0xAD5CE0`) and `GZWinBtn` (`0xAD5CAC`) is not a
descriptor structure — it is simply the **class-name string** those registry
rows point at. There is no per-class descriptor record.

> EVIDENCE: `0xAD5CE0` is a `char*` target holding `"GZWinBMP\0"`; its only two
> image-wide xrefs are `0x0095306C` (.text) and `0x00B17004` (the registry row).

**(b) The GZCOM clsid→name table, `~0x00B05000` … `0x00B0B000`, 8-byte
`{uint32 id, char* name}` pairs — 906 resolvable entries.** This is the
authority for everything the `.UI` files cannot name: the `cSC4Win*` classes,
the simulators, the command ids.

> EVIDENCE: `0x00B08FA8 = 0x89E1567C`, `0x00B08FAC -> 0x00A8957C
> "cSC4WinGenTransparent"`; `0x00B08FE8 = 0x9A47B417 -> "cSC4View3DWin"`;
> `0x00B08FC8 = 0x2BA6BB97 -> "cSC4WinRegionView"`.

**(c) The SC4 window class registration function, `sub_004662B0`.** It pairs a
factory with a clsid seventeen times (`push <factory>; push/call <clsid>; call
0x0090E133`). Every SC4-specific window class in the game is registered here,
and each factory is a five-line stub `new(size) → ctor → return obj+N`, where
**N is the byte offset of the cIGZWin sub-object** — the single fact you need
to know which of a class's several vtables the window tree will show you.

> EVIDENCE: `0x004663B8 push 0x4661D0 / 0x004663BD push 0x89E1567C`
> (cSC4WinGenTransparent); factory `0x004661D0` = `push 0x128; call malloc;
> jmp 0x0079C560` (N = 0). Contrast `0x00466220` (clsid `0xCBCBF1E0`):
> `push 0x108; call ctor 0x007628E0; add eax, 4` (N = 4).

**One structural fact that makes the whole census possible: every cIGZWin
vtable in this build is 151 slots and its slot 87 (`GZPaint`) is
`0x0099BE4C`.** Scanning `.rdata` for that constant yields **115 window-class
vtables** in the exe — the complete population.

> EVIDENCE: whole-`.rdata` scan for `[vt+87*4] == 0x0099BE4C` with `[vt]` and
> `[vt+88*4]` both inside `.text` → 115 hits, and every class this project has
> ever hooked is among them.
> ⛔ Corollary and trap: **if slot 87 is not `0x0099BE4C`, you are not holding a
> window vtable.** `0x00AB8150` (listed in a prior handoff as "the data-view
> panel") fails this test — it is the secondary COM-interface vtable of
> `cSC4WinMapView`, and its "slots" read `0x800B`, `0x6005`, `0x5007`.


# ============================================================================
# BLOCK 2 — the completed catalogue. Insert as `### 2.0b` (or fold into the
# existing §2 table). SC4-UI-ENGINE.md §2.
# ============================================================================

### 2.0b The complete class table (vtable ⇄ name ⇄ clsid ⇄ Plot)

**The 21 `.UI` widget classes.** `vtable` is the cIGZWin vtable — the value a
`MWKID`/`VWKID`/`RGKID` line prints as `vt=`.

| `.UI` class name | clsid | iid | **vtable** | Plot (slot 88) | ctor |
|---|---|---|---|---|---|
| `GZWin` (the base) | `0xE2BA00EE` | `0x22BA0121` | **`0x00ADC8D8`** | `0x00949ADE` *(no-op)* | `0x0099D938` |
| `GZWinGen` | `0x4386D516` | `0x5386D516` | **`0x00ADC678`** | `0x009995E7` | `0x0099B6A5` |
| `GZWinBMP` | `0x82FE68C4` | `0xC12CEA13` | **`0x00ADF6A0`** | `0x009BC325` | `0x009BC4BA` |
| `GZWinBtn` | `0x22ECFC47` | `0x00008810` | **`0x00ADDAF0`** | `0x009B167D` | `0x009B1C27` |
| `GZWinText` | `0x00000592` | `0x212CDC1F` | **`0x00ADFEB8`** | `0x009C1A9A` | `0x009C19C8` |
| `GZWinTextEdit` | `0x231A1C58` | `0x231A1C57` | **`0x00ADFBD0`** | `0x009BEA28` | `0x009C01AF` |
| `GZWinFlatRect` | `0xC2AFA76E` | `0xC2AFA76F` | **`0x00AE20A0`** | `0x009CD1FF` | `0x009CD842` |
| `GZWinCustom` | `0x478D1E6F` | `0x678D1E84` | **`0x00AD6AA0`** | `0x0095BA43` | `0x0095BAB3` |
| `GZWinListBox` | `0x00000598` | `0x4132242B` | **`0x00AE1780`** | `0x009CA19A` | `0x009CA883` |
| `GZWinCombo` | `0x0000059B` | `0x412CE496` | **`0x00AE2970`** | `0x009CF241` | `0x009CF772` |
| `GZWinLineInput` | `0x21335C5A` | `0x21335C59` | **`0x00AE0FB0`** | `0x009C6B03` | `0x009C68AC` |
| `GZWinScrollbar` | `0x61325A2E` | `0x61325A2D` | **`0x00AE0810`** | `0x009C453D` | `0x009C46AF` |
| `GZWinSlider` | `0x21325208` | `0x21325207` | **`0x00AE04D8`** | `0x009C3623` | `0x009C3836` |
| `GZWinSpinner` | `0x612CE0C4` | `0x612CE0C3` | **`0x00AE0B90`** | `0x009C55F3` | `0x009C5327` |
| `GZWinOptGrp` | `0xA1336CC1` | `0xA1336CC0` | **`0x00AE1300`** | `0x009C7803` | `0x009C7BB8` |
| `GZWinOutline` | `0x4303E5B6` | `0xE303E5AE` | **`0x00AE1AC8`** | `0x009CB57C` | `0x009CBBFF` |
| `GZWinTextTicker` | `0xE32F0B31` | `0x032F0B3C` | **`0x00AE37E8`** | `0x009D69FC` | `0x009D6530` |
| `GZWinGrid` | `0xDAA6B9BF` | `0xDAA6B9BE` | **`0x00ADD7B0`** | `0x009AF168` | `0x009ABC95` |
| `GZWinFileBrowser` | `0x1AA52EA4` | `0x3AA52E64` | **`0x00ADCF30`** | `0x009A0A17` | `0x009A57C4` |
| `GZWinTreeView` | `0x3AE8BAE1` | `0x3AE8BAD2` | **`0x00AE2FE0`** | `0x009D37C6` | `0x009D2BF0` |
| `GZWinFolders` | `0x078E8055` | `0xA13351B8` | **`0x00AE3D88`** | `0x009D7459` | `0x009D77CA` |

> EVIDENCE (method, one row shown): the GZ framework registers each class at
> `0x00998BEA`–`0x00998D60` as `push <factory>; push <clsid>; call AddClass`.
> `GZWinBMP`: `push 0x998AC5 / push 0x82FE68C4` → factory `0x00998AC5` calls
> ctor `0x009BC4BA`, whose only `.rdata` store is `mov dword ptr [esi],
> 0xadf6a0`. Every one of the 21 rows was resolved by that same walk; all 21
> vtables land in the 115-entry census, and the five vtables this doc already
> carried (`0xADF6A0`, `0xADDAF0`, `0xADFEB8`, `0xADC678`, `0xAD6AA0` implied)
> match.

**The SC4-specific window classes** (registered in `sub_004662B0`, or `new`ed
directly by their owner):

| Class | clsid | **vtable** | Plot | ctor / factory | Where it is live |
|---|---|---|---|---|---|
| `cSC4WinGenTransparent` | `0x89E1567C` | **`0x00AB7358`** | `0x009995E7` *(= GZWinGen's)* | `0x0079C560` / `0x004661D0` | every HUD panel root |
| `cSC4WinText` | `0xAA7CECFD` | **`0x00ABA190`** | `0x007BE7A0` | `0x007BE740` (factory-only) | region name `0xEA5BD179`, city name |
| `cSC4WinAdviceList` | `0xCA1492AC` | **`0x00AB58B0`** | `0x00949ADE` *(no-op)* | `0x00793CB0` / `0x00793D20` | news reader, advisors, My Sims |
| `cSC4WinMiniMap` | `0xCA318388` | **`0x00AB83B8`** | `0x007A79B0` | `0x007A8920` / `0x007A8AF0` | dock, Data Views, U-Drive-It |
| `cSC4WinRCI` | `0xC7A0E17E` | **`0x00AB8628`** | `0x007A9500` | `0x007A9770` / `0x00466170` | the demand columns |
| `cSC4WinTrendBar` | `0xAA5C2F86` | **`0x00ABA430`** | `0x007BF0A0` | `0x007BF5E0` / `0x004661A0` | polls |
| `cSC4WinAlertBorder` | `0xCA5D3294` | **`0x00AB5B48`** | **`0x00794100`** | `0x00794060` / `0x007941C0` | **live, full-screen — see §2.6** |
| `cSC4WinAuraBar` | `0xAA5D16A9` | **`0x00AB64B8`** | `0x00797CC0` | `0x00797E60` / `0x00797F20` | not yet seen live |
| `cSC4WinRegionView` | `0x2BA6BB97` | **`0x00AB9658`** | `0x00648F00` | `0x007B4090` | region screen, full-screen |
| `cSC4View3DWin` | `0x9A47B417` | **`0x00ABCBC0`** | `0x007F6200` | `0x007F1167` | the city view host |
| `cSC4WinMapView` | `0x28C5A41F` | *(win vt at obj+0xE0)* | — | `0x007A0D50` / `0x00466080` | — |
| `cSC4WinSplashScreen` | `0xAA38326E` | **`0x00AB9EB8`** | `0x007BE3A0` | — | boot |
| gauge dial class | `0xCBCBF1E0` | **`0x00AB46A0`** | `0x00762830` | `0x007628E0` / `0x00466220` | U-Drive-It dash |
| *(unnamed)* | `0x2AC45173` | **`0x00AB7640`** | `0x009995E7` *(GZWinGen's)* | `0x0079C6A0` / `0x004661F0` | — |
| `WinSC4App` | — | **`0x00A92F28`** | `0x004E0910` | `0x004E0EE0` | id `0x6104489A`, app frame |
| tooltip layer | — | **`0x00AB6770`** | `0x00798710` | `0x00799DD0` | id `0x2AAB8CC1` |
| flyout container | — | **`0x00AB6AA8`** | `0x0079B0E0` | `0x0079AFF0` | see §2.1 |
| flyout strip | — | **`0x00AB6D88`** | `0x0079AA70` | `0x0079B500` | see §2.1 |
| clip/transform container | — | **`0x00ADCB38`** | `0x00949ADE` *(no-op)* | `0x0099EA30` | anonymous, under the view |
| region layer A | — | **`0x00AB88C0`** | `0x007A9D60` | `0x007A9AE0` | id `0x6A0AF41D`, 2400x1600 |
| region layer B | — | **`0x00AB8CD0`** | `0x007AB130` | `0x007AAE10` | id `0`, 2400x1600 |
| region layer C | — | **`0x00AB8F50`** | `0x007AB590` | `0x007AB5E0` | id `0`, 2400x1600 |

> EVIDENCE (naming): `0x00B08F78..0x00B08FCC` gives
> `cSC4WinMiniMap / cSC4WinRCI / cSC4WinTrendBar / cSC4WinAdviceList /
> cSC4WinAuraBar / cSC4WinGenTransparent / cSC4WinMapView / cSC4WinRegionScreen
> / cSC4WinRegionView` against their clsids, and `0x00B08F70 = 0xCA5D3294 ->
> "cSC4WinAlertBorder"`. `cSC4WinText` is not in the exe table; it is named in
> `vendor\gzcom-dll\gzcom-dll\include\GZCLSIDDefs.h:285`
> (`kcSC4WinText = 0x0AA7CECFD`).
> EVIDENCE (vtables): each ctor's `mov dword ptr [reg+N], <vt>` store, with N
> confirmed against the factory's `add eax, N`. e.g. gauge ctor `0x007628E0`:
> `lea edi,[esi+4]; mov [esi],0xab4658; call 0x99d938; mov [esi],0xab4900;
> mov [edi],0xab46a0` and factory `0x00466220` returns `obj+4` ⇒ the window
> vtable is `0x00AB46A0`. That is the constant already hard-coded at
> `src\UiSpike.cpp:4497` (`kGaugeClassVt`) and its draw at
> `UiSpike.cpp:4498` (`kGaugeDrawVA = 0x00762830`) — the code knew, the doc
> did not.


# ============================================================================
# BLOCK 3 — replace / amend three existing §2 table rows. SC4-UI-ENGINE.md §2.
# ============================================================================

### Row amendments (measured, replacing inferred text)

**`cSC4WinGenTransparent` — it is `GZWinGen` plus one hit-claim, nothing else.**
Diffed slot-by-slot over all 151 slots, `0x00AB7358` differs from
`0x00ADC678` in exactly **two**: slot 121 (`0x0079C5C0` vs base `0x0099955D`)
and slot 148 (the deleting destructor). Plot, art binding, geometry, layout and
`IsPointInMe` (`0x00998FD7`) are byte-identical to `GZWinGen`.
⇒ The catalogue's "Ordinary container: scale it and recurse" is correct, and
now it is *provable* rather than observed: there is no draw-path or geometry
code of its own to surprise you.
> EVIDENCE: slot diff `0x00AB7358` vs `0x00ADC678`, slots 0..150 → `{121, 148}`.

**`0xAA7CECFD` — it IS `GZWinText`, with one slot swapped. The doc's mechanism
is wrong.** The current row says its font style is "resolved independently of
the `GZWinText` name path". Measured: its factory `0x007BE740` allocates
`0x114` bytes, runs **`cGZWinText`'s own constructor `0x009C19C8`**, and then
overwrites the vtable pointers (`mov [esi],0xaba190; mov [eax],0xaba118`).
Diffed against `GZWinText`'s vtable, `0x00ABA190` differs in exactly **two**
slots: 88 (`Plot` → `0x007BE7A0`) and 148 (dtor).
⇒ Same object layout, same font resolution code, same text geometry — **only
the painter differs**. Rewrite the row as: *"a `cGZWinText` with a replaced
Plot, reached by GZCOM clsid instead of by the `.UI` class name, which is why
it is outside the `GZWinText` name path and why it scales off FontStyle with no
help."* The co-location observation in `FONTS-AND-DIALOGS.md` Q1 stands; its
explanation changes. The class is `cSC4WinText`.
> EVIDENCE: `0x007BE740` disassembly; slot diff `0x00ABA190` vs `0x00ADFEB8`
> → `{88, 148}`; `GZCLSIDDefs.h:285`. Live:
> `[11:08:12.401] RGKID 2.3.0 id=0xEA5BD179 vt=00ABA190 (0,0 384x26) vis=1`.

**`GZWinCustom` (the `0x0000AAAA` alignment marker) — vtable `0x00AD6AA0`, and
the ⛔ rule as written does not match what we ship.** The doc says
"NEVER SCALE IT — not at runtime, not in shipped data". The data half is true
(`build_dialog_static.py` skips `id=0x0000AAAA`, §6.1). **The runtime half is
not: our sweep does double markers, and always has.**
> EVIDENCE: `tools\research\_checkpoints\pds-cache\SC4UIScale-snapshot.log:37`
> `RGKID 3.0 id=0x0000AAAA vt=00AD6AA0 (110,0 20x20) vis=0` and `:109` the same
> node at `(220,0 40x40)` after the sweep. It is harmless because the god-dock
> placement uses the **baked** `R = −marker(1x)` offsets (`UiSpike.cpp:2505
> offX` and the marker table at 2522–2564), not the live marker window.
> Suggested rewrite: *"⛔ NEVER scale it in shipped `.UI` data. At runtime the
> sweep does double it; that is safe only because every consumer we ship uses
> a baked 1x offset — any new code that reads the LIVE marker must divide by
> the tier."*


# ============================================================================
# BLOCK 4 — new subsection. SC4-UI-ENGINE.md, `### 2.4 Blind spots`
# ============================================================================

### 2.4 The twelve live vtables the catalogue did not cover

A one-session harvest of every `vt=` in `SC4UIScale.log` (2026-07-31,
11:07–11:17, region screen → mayor mode → menus → dialogs) yields **22 distinct
vtables**. The catalogue named ten of them. These twelve were blind spots; each
now has a name, a Plot and a rule.

| vtable | Class | What it is, measured | Scaling rule |
|---|---|---|---|
| `0x00A92F28` | `WinSC4App` (id `0x6104489A`) | the app frame; full-screen; own Plot `0x004E0910` | never scale — it is the frame the tier already sets |
| `0x00ABCBC0` | `cSC4View3DWin` (id `0x9A47B417`) | the city-view host; Plot `0x007F6200` | never scale — §1.2 host |
| `0x00AB9658` | `cSC4WinRegionView` (id `0x2BA6BB97`) | region map, full-screen; Plot `0x00648F00`; **overrides slot 149** (refined hit test) with `0x007B2440` | never scale; it hit-tests cities through its own mask |
| `0x00AB5B48` | **`cSC4WinAlertBorder`** (id `0x6A5E44B6`) | full-screen `0,0 2400x1600` child of the 3D view; Plot `0x00794100` = tiling nine-slice frame | **OPEN — see §2.6** |
| `0x00AB88C0` | region layer A (id `0x6A0AF41D`) | full-screen; Plot `0x007A9D60` gated on four resources loaded via `{0x1AC0E11A, 0xFAC0E219}` and ids `0x4A624656..59`; drives a sprite/animation object (`0x0088FEFB`/`0x008905C4`/`0x00890198`) | leave alone — its draw is resource-driven, not rect-driven |
| `0x00AB8CD0` | region layer B (id `0`) | full-screen; Plot `0x007AB130`, animating list (already decoded in the border hunt) | leave alone |
| `0x00AB8F50` | region layer C (id `0`) | full-screen; Plot `0x007AB590`, 3-line delegate to `[this+0xD8] vt+0x54` | leave alone |
| `0x00ADC678` | **`GZWinGen`** | the generic container; Plot `0x009995E7`; `IsPointInMe 0x00998FD7` | scale and recurse (identical to `cSC4WinGenTransparent`) |
| `0x00ADCB38` | anonymous `cGZWin` subclass | **paints nothing** (Plot = the no-op `0x00949ADE`) and differs from base `GZWin` in exactly **one** slot: 89 `CalcAbsoluteArea` (`0x0099C291` vs `0x0099BA07`) ⇒ it is a **coordinate-remapping / clip viewport** | ⛔ scaling it moves every descendant's absolute rect. Treat like `cSC4WinAdviceList`: scale the container, do not recurse blindly |
| `0x00ADFBD0` | **`GZWinTextEdit`** | matches the existing row; Plot `0x009BEA28` | as the existing row |
| `0x00AE20A0` | **`GZWinFlatRect`** | `fillcolor` panel; Plot `0x009CD1FF` | ordinary; see §6.3 re-imposition |
| `0x00AE2970` | **`GZWinCombo`** | drop-down; Plot `0x009CF241` | ordinary (`area=`) |

> EVIDENCE (harvest): `rg -o "vt=[0-9A-F]+"` over `SC4UIScale.log` — 22 distinct
> values, e.g. `VWKID vt=00AB7358` ×530, `MWKID vt=00ADDAF0` ×149,
> `VWKID vt=00AB5B48` ×72, `MWKID vt=00AE20A0` ×23, `VWKID vt=00ADCB38` ×7.
> Sample lines: `[11:17:42.584] MWKID 0.1 id=0x00000000 vt=00AE20A0
> (110,682 740x60) vis=1`; `[11:17:42.584] MWKID 0.4 id=0xAA243F5E vt=00AE2970
> (352,620 340x40) vis=1`; `[11:17:42.584] MWKID 0.5 id=0x8A243F6E vt=00ADFBD0
> (896,556 200x46) vis=0`; `[11:16:19.364] MWKID 0.0 id=0x9A47B417 vt=00ABCBC0
> (0,0 2400x1600) vis=1`.
> **POSITIVE CONTROL for the nulls in this table.** The exe contains 115 window
> classes; one session exercised 22. A class absent from a log is a statement
> about that session's coverage, not about the game. `cSC4WinAuraBar`,
> `cSC4WinRCI`, `cSC4WinTrendBar`, `cSC4WinAdviceList` and the gauge class are
> all *known to exist and be used*, and none appears in this log — because the
> session never opened polls, the demand box, a news item or U-Drive-It.


# ============================================================================
# BLOCK 5 — new subsection. SC4-UI-ENGINE.md, `### 2.5 …`
# ============================================================================

### 2.5 How to identify an unknown widget — the seven-step procedure

Given nothing but a `vt=XXXXXXXX` in a log line:

1. **Range-check the vtable.** Game classes live in `0x00A80000`–`0x00B20000`
   and are *fixed for the build*. Anything else — `0x1……`, `0x6C……`,
   `0x6F……`, `0x7……` — is a **relocated module**, and in our logs it is
   almost always **our own shadow vtable copy**, not a game class.
   ⛔ The positive control is one line long: *restart the game and re-read the
   log.* An exe vtable prints identically; a DLL vtable moves.
   > EVIDENCE: same window id, two sessions of the same log file —
   > `[11:09:45.210] DFG patched class vt=6C469328 Plot=6C4179A0 (idx 9)` and,
   > after the restart, `[11:16:23.594] VWKID 0 id=0x48E945B4 vt=6F109328`. The
   > shadow arrays are `gVtCopy` / `gVtCopy2` / `gGaugeVtCopy` /
   > `gStripVtCopy` (`src\UiSpike.cpp:141,150,1314,4519`), installed by
   > `*reinterpret_cast<void***>(w) = gVtCopy;` at `UiSpike.cpp:3573, 3620,
   > 6557`.
2. **Confirm it is a window vtable at all:** `[vt + 87*4] == 0x0099BE4C`
   (`GZPaint`). If not, you are holding a secondary COM interface vtable and
   the window's real vtable is at a different object offset.
3. **Read slot 0 (`QueryInterface`) and collect its `cmp` immediates** — those
   are the interface iids. Look each up in the `.UI` registry (`0x00B16FA8`)
   for a `GZWin*` name, then in the GZCOM table (`~0x00B05000`) for a
   `cSC4*` name.
4. **If `QueryInterface == 0x0099B774`, the class overrides nothing.** It is a
   bare `cGZWin` subclass answering only `cIGZWin (0x22BA0121)` and
   `0xE98B2F57`, and **only its Plot can identify it**. Twelve of the 115
   classes are in this state, including all three region layers.
5. **Diff the vtable against its base over slots 0…150. The differing slots
   ARE the class.** Two slots (88 + 148) = a Plot swap and nothing else. One
   slot (89) = a coordinate override. Slot 121/62/149 = a custom hit claim.
   This is faster and far more reliable than reading the constructor.
6. **Find the constructor:** search `.text` for the 4-byte vtable VA. You get
   exactly two hits — the ctor and the deleting destructor. The ctor's
   `mov [reg+N], <vt>` gives the cIGZWin sub-object offset **N**, which must
   equal the `add eax, N` in the GZCOM factory. If they disagree, you have the
   wrong vtable (this is exactly the `0x00AB8150` trap).
7. **Cross-check the name against
   `vendor\gzcom-dll\gzcom-dll\include\GZCLSIDDefs.h`** before writing it down.
   It carries names the exe's own table does not (`kcSC4WinText`,
   `kcSC4WinAlertBorder`, `kcSC4WinAuraBar`).

⛔ **And the standing warning from §2.1 still governs: the right class is not
the right window.** Every step above identifies a *class*. Installing a hook
on class identity alone is what killed the game on U-Drive-It's Earned Cars.


# ============================================================================
# BLOCK 6 — new subsection. SC4-UI-ENGINE.md `### 2.6`, and cross-post the
# addendum verbatim into _tests\REGRESSION.md under the task-#59 heading.
# ============================================================================

### 2.6 `cSC4WinAlertBorder` — a full-screen frame painter in the UI layer

**This reopens task #59, and the reason it was missed is instructive.**

The 3D view creates, as one of its own children, a window of class
`cSC4WinAlertBorder` (clsid `0xCA5D3294`, iid `0xCA5D3290`, vtable
`0x00AB5B48`), id **`0x6A5E44B6`**, sized to the entire view.

> EVIDENCE (creation): `0x007EF029 push 0xca5d3290 / 0x007EF02E push
> 0xca5d3294 / call [eax+0xC]` (GZCOM CreateInstance) inside the
> `cSC4View3DWin` code region; then `SetArea(0, 0, [esi+0xBC]−[esi+0xB4],
> [esi+0xC0]−[esi+0xB8])` via `[eax+0xDC]` at `0x007EF069`, then
> `0x007EF071 push 0x6a5e44b6; call [eax+0x100]` (SetID).
> EVIDENCE (live): `[11:16:19.364] UiSpike: VWKID 3 id=0x6A5E44B6 vt=00AB5B48
> (0,0 2400x1600)` — and again at VWKID 4/5/6/7 across the session as siblings
> come and go. It is present in every view dump.

**Its Plot (`0x00794100`) is a tiling nine-slice frame blit over the window's
own absolute rect.** It early-outs unless `[this+0xE4]` (an image) is non-null
**and** `[this+0xE8]->[0x0C]->[0x45C]` is true; then it takes the source
image's `W/3` and `H/3` (the classic `mul 0xAAAAAAAB; shr 1` divide-by-three)
and calls `0x008D9550(ctx, img, &cell, &this[0x24], 0)` between a
`ctx.vt+0x18(0x8010)` / `ctx.vt+0x1C(0x8010)` push/pop pair. The class has a
three-image setter at `0x007942F0` filling `[+0xE0]/[+0xE4]/[+0xE8]`.

⚠ **`0x008D9550` is a frame tiler, it wraps `0x008D8BC0`, and it has exactly
ONE caller in the whole exe — this Plot.**

> EVIDENCE: callers of `0x008D9550` = `['0x00794198']`; `0x008D9550` calls
> `0x008D8BC0` — the same arc/tiling helper §2.1 documents for the flyout
> container's bar spine.

**Why the six #59 probes could not have seen it — this is a NULL-IS-NOT-EVIDENCE
case, not a wrong conclusion about the pixels.**
- The window **never changes visibility and is never created late**. It is
  born with the view and stays. VisTrace (v2.36.8–10) reported only
  *visibility flips* and *newly created windows*; this window does neither.
  What toggles is an **image pointer and a flag inside the object**, which no
  window-tree probe can observe.
- The offline decode audited **`0x008D8800`** ("6 callers, none a full-screen
  painter"). The tiler this painter actually uses is **`0x008D8BC0` via
  `0x008D9550`** — never audited.
- "No border art exists" was concluded from a PNG scan of the *extracted* set;
  this class's image arrives through its own `SetImages`, i.e. a code-bound
  TGI (Path 2, §4.2), which the extraction sweep does not enumerate by name.

**WHAT THIS DOES AND DOES NOT PROVE.** It proves there is a live, full-screen,
UI-layer, nine-slice **frame** painter named *AlertBorder* whose draw is
gated by internal state, and that no #59 probe was capable of observing it.
It does **not** prove it draws the pause frame. Stated as `HYPOTHESIS`.

**THE ONE TEST, with its positive control.** Hook slot 88 of `0x00AB5B48`
(the existing `PatchFlashGuardClass` machinery already patches this exact
vtable — `[11:08:17.531] UiSpike: DFG patched class vt=00AB5B48
Plot=00794100 (idx 3)`) and log `[this+0xE4]`, `[this+0xE8]->[0x0C]->[0x45C]`
and the computed `W/3 × H/3` cell, once per state change.
- **Positive control:** the hook must print at least one line *before* pausing
  (proving it runs at all). If `[+0xE4]` is null in every state, the class is
  dormant in this build and #59's conclusion survives — as a *measured* null
  this time.
- **If it fires on pause:** the cell is `srcW/3 × srcH/3` blitted 1:1, i.e.
  exactly the `GZWinBMP` law (§2, "the draw follows the SOURCE IMAGE"). The
  cure is then **2x art on that code-bound TGI and no code at all** — which
  also explains the symptom, a frame that stays 2-3 px at every tier.

⛔ Do **not** re-run the six probes in `2026-07-30-BORDER-HUNT-README.md`.
This is a seventh, different instrument aimed at a window none of them could
observe.


# ============================================================================
# BLOCK 7 — SC4-UI-ENGINE.md §8, new sub-block 8.6, plus three corrections
# ============================================================================

### 8.6 Class registries and window-class vtables

| VA | What |
|---|---|
| **`0x00B16FA8` … `0x00B170A3`** | **the `.UI` class registry** — 21 × 12 bytes `{clsid, iid, char* name}`; the complete set of scriptable widget classes |
| **`~0x00B05000` … `0x00B0B000`** | **GZCOM clsid → name table** — 8-byte `{id, char*}` pairs, 906 resolvable; names every `cSC4*` class, simulator and command id |
| **`0x004662B0`** | SC4 window-class registration — 17 `{factory, clsid}` pairs via `AddClass 0x0090E133` |
| `0x00998BEA` … `0x00998D60` | GZ framework registration of the 21 `.UI` classes |
| **`0x0099BE4C`** | `GZPaint`, slot 87 — **identical in all 115 window vtables; the fingerprint that a `.rdata` address IS a window class** |
| **`0x00949ADE`** | `cGZWin::Plot` — the no-op `mov al,1; ret` (bytes `B0 01 C3`). Shared by `GZWin`, `cSC4WinAdviceList` and `0x00ADCB38`: **"children paint"** |
| `0x009995E7` | `GZWinGen::Plot`, shared verbatim by `cSC4WinGenTransparent` and clsid `0x2AC45173` |
| `0x0099D938` | `cGZWin` constructor — the base every window ctor calls first |
| `0x0099B774` | `cGZWin::QueryInterface` — a class using it overrides nothing (iids `0x22BA0121`, `0xE98B2F57`) |
| `0x00794100` / `0x008D9550` → `0x008D8BC0` | **`cSC4WinAlertBorder::Plot`** / its **single-caller** frame tiler → the arc/tile helper |
| `0x007EF029–0x007EF078` | the view creates the AlertBorder: CreateInstance, `SetArea(full view)`, `SetID(0x6A5E44B6)` |
| `0x007628E0` / `0x00762830` / `0x00AB46A0` | gauge class (`0xCBCBF1E0`) ctor / Plot / **window vtable**; outer vtable `0x00AB4900`, cIGZWin at `obj+4` |
| `0x007BE740` | `cSC4WinText` (`0xAA7CECFD`) factory — runs `cGZWinText::ctor 0x009C19C8`, then swaps in `0x00ABA190` / `0x00ABA118` |
| `0x009BC251` | `GZWinBMP::IsPointInMe` (slot 62) override — add to §8.5's GZWinBMP row beside `0x9BC2D0` / `0x9BC27C` |
| `0x0079C5C0` | `cSC4WinGenTransparent` slot-121 hit-claim — its **only** functional override vs `GZWinGen` |

**Corrections inside the existing §8 tables:**
- §8.4, `cSC4WinAdviceList` row: `0x949ADE` is not that class's private no-op —
  it is **`cGZWin::Plot`**, shared by at least three classes. Re-word to
  "inherits the base no-op draw-self `0x949ADE`".
- §8.5, `GZWinBMP` row: add slot 62 = `0x009BC251`.
- §8.5, `0x8D8BC0` row ("arc / tiling helper used by the container"): add
  "and, through the single-caller wrapper `0x8D9550`, by
  `cSC4WinAlertBorder::Plot` — the exe's only full-screen frame painter".


# ============================================================================
# BLOCK 8 — SC4-UI-ENGINE.md §9, entries 12–15
# ============================================================================

12. **`0x00AB8150` is not "the data-view panel".** It is carried in the
    project's live-vtable shortlist with that label. It is the **secondary COM
    interface vtable of `cSC4WinMapView`** (clsid `0x28C5A41F`); its "slots"
    read `0x800B`, `0x800A`, `0x6005`, `0x5007` and it fails the
    `[vt+87*4] == 0x0099BE4C` window test. **Resolution: delete the label.**
    The Data-Views map child `0x00004203` is a `cSC4WinMiniMap`
    (vtable `0x00AB83B8`) exactly as the §2 minimap row already says.
    > EVIDENCE: ctor `0x007A0280` stores `0xab8150` at `[esi]` and `0xab8140`
    > at `[esi+4]`; the `cSC4WinMapView` factory `0x00466080` returns
    > `obj+0xE0`, and `[esi+0xE0]` is where its window vtable is stored.

13. **`0xAA7CECFD` is not "unnamed".** §2 calls it "unnamed in the registry;
    56 uses" — true of the *exe's* name table, false of the SDK.
    `GZCLSIDDefs.h:285` names it `cSC4WinText`. **Resolution: name it, and
    replace the mechanism sentence** (see Block 3).

14. **`0x6C……` / `0x6F……` vtables in our logs are OURS.** `GOD-MODE-FLYOUTS.md`
    and §2.1 state that the shared sub-flyout container `0x8A6E61E0` is class
    `0x00AB6AA8`. That is still true of the *game's* object — but a log read
    after `SUBBORNHOOK` shows `id=0x8A6E61E0 vt=6F101F70`, because we replaced
    that instance's vtable pointer with `gVtCopy`. **Resolution: not a
    contradiction, a reading trap.** Add to §2.5 step 1 and to any
    log-reading guidance: *"a `vt=` outside `0x00A80000–0x00B20000` is a
    relocated DLL; ours."*
    > EVIDENCE: `[11:17:01.482] VWKID 0 id=0x8A6E61E0 vt=6F101F70
    > (125,450 258x482)` vs the earlier session's `6C461F70` for the same id.

15. **Task #59's "not reachable from any UI-side lever" is not yet safe.**
    `cSC4WinAlertBorder` is a live, full-screen, UI-layer nine-slice frame
    painter that no #59 probe was structurally capable of observing (§2.6).
    **Resolution: downgrade #59 from "decoded to a dead end" to "one
    un-eliminated candidate remains, with a named one-line test".** Keep the
    ⛔ on re-running the original six probes — they remain answered.


# ============================================================================
# BLOCK 9 — one paragraph for METHOD.md, under "YOUR OWN INSTRUMENTS CAN LIE"
# ============================================================================

**A vtable address in your own log is not necessarily the game's.** This
project installs per-instance vtable *copies* (`gVtCopy`, `gVtCopy2`,
`gGaugeVtCopy`, `gStripVtCopy`) and points live windows at them. From that
moment the window reports **our** vtable, in our DLL's relocated address range.
Four of the vtables in one session's harvest were ours, and the same window id
printed `vt=6C461F70` in one run and `vt=6F101F70` in the next. **The positive
control is free: exe addresses are constant across restarts, DLL addresses are
not.** More generally — when an instrument reports an address, know which
module the address belongs to before you write it into a doc.
