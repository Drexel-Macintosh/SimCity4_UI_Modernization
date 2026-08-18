---
name: project-sc4-thirdparty-patches
description: "SC4: we now PATCH OTHER MODS' DATA at runtime (CAM buildings' broken submenu parents via exemplar-patch cohorts + 2x overrides of CAM/submenus/Maxis-landmark icons). STANDING ORDER: every such override gets documented in UPSTREAM-CAM-REPORT.md and called out to the upstream developer. + the long-term plan."
metadata: 
  node_type: memory
  type: project
  originSessionId: f1160943-a698-434b-a6bf-d3c3e2971cea
  modified: 2026-08-14T15:58:53.819Z
---

**STANDING ORDER (user, 2026-07-29): whenever we change or patch ANOTHER
mod's DLLs or data, record it in memory and call it out to the developer.**
The developer-facing write-up lives at
`tools\research\UPSTREAM-CAM-REPORT.md` (SC4TouchControls repo).

Current third-party overrides (all in `Plugins\zzz-SC4UIScale\`, all
delete-when-fixed-upstream):

1. **z_SC4UIScale_MenuFix.dat** — six exemplar-patch cohorts
   (sc4-resource-loading-hooks format: Cohort 0x05342861, group 0xB03697D1,
   targets prop 0x0062E78A) that inject corrected Item Submenu Parent
   (0xAA1DD399) into TEN of CAM 4.0.1's exemplars: 9 police/fire buildings
   shipped with parent={0x00000000} (Police Kiosk, precincts, Jail, Prison,
   3 fire stations - unreachable in game) + the Lifeguard Tower pointing at
   undefined submenu 0x1C3780E4. Built by
   `tools\itemicons\build_menu_patches.py`; found by
   `tools\itemicons\scan_unreachable_items.py` (rerun after ANY plugin
   change; parses BOTH binary and text exemplars).
2. **z_SC4UIScale_ItemIconsSub-2x.dat** (125 entries) — 2x icons owned by
   OTHER mods: 55 submenus-mod + 69 CAM/Maxis-landmark + the submenus DLL's
   Missing Thumb 0x144161EC (never exemplar-bound, so the stock-pool scan
   missed it; 5 CAM items have NO icon art anywhere and wear it).
3. **z_SC4UIScale_ThirdPartyUI-2x.dat** (1 entry, added 2026-07-29) — a
   plugin can REPLACE a stock .UI script wholesale, which our root package
   can never override (load-order law). CoriBoom's 36 Slot Building Styles
   UI (in the allow-more-building-styles-dll sc4pac) replaces the Building
   Style Control script {0,0x96A006B0,0x6BC61F19} from 150-mods\, so that
   panel was NEVER scaled and rendered corrupted. We now build from THE
   MOD'S script (never the stock one — that reverts its 36 slots), scaling
   imagerects + retargeting shared art to our clones, `area=` untouched.
   Source lives in `tools\selective-safe\thirdparty-ui\` — **re-extract it
   after any update to that mod or we ship a stale layout.** Callout:
   `tools\research\UPSTREAM-BUILDINGSTYLES-REPORT.md`.
   ⚠ **STALE-DEPLOY LESSON (2026-08-02, #58 CLOSED user-confirmed):** this
   package sat OUT of `Deploy-OnGameClose.ps1` for four days; the deployed
   dat froze at the 2026-07-29 clone-ref epoch and its radio rows drew as
   bare grey bars once the classification moved to 2x-in-place — AND the
   panel's GenHeader title bands went empty (cured by the same fix though
   nothing was wrong with the band elements; suppression mechanism is an
   unmeasured hypothesis). Stale vs fresh sizes were IDENTICAL — only the
   `Test-DatIntegrity` DEPLOYED==BUILT hash section (added then) catches
   this class. Law 40 in [[feedback-sc4-scaling-laws]].
   **RECOGNITION RULE (cheap, worth reusing): if a panel's LIVE window count
   or root size doesn't match the stock script you're editing, a plugin has
   replaced that script — grep Plugins\**\*.dat for the TGI first.**
   A plugin that replaces a script often replaces its ART too (CoriBoom ships
   its own taller 516x654 background): both need the zzz- treatment, and the
   art must be upscaled from THE MOD'S bitmap, never the stock one.
   `_tests\Toggle-BuildingStylesUI.ps1` flips this panel between the mod's
   36-slot layout and the STOCK 4-style-with-previews panel (renames only,
   never edits; it MUST move our zzz package too or our copy of the mod's
   script keeps the mod layout alive). Both states user-verified good at 2x
   on 2026-07-29 — the stock panel is a genuine early vanilla-pass data point.
   The mod's layout has NO style previews at all (the stock one has four
   160x77 pictures); that is the mod's design, not a scaling bug.

4. **z_SC4UIScale_SaveWarningUI-<tier>.dat** (2 entries, added 2026-07-31,
   task #79c) — same class again: the **cyclone-boom save-warning mod**
   replaces BOTH in-city quit/exit confirm scripts ({0,96A006B0,6A553AA4} and
   {..,0A55161D}) from `150-mods\`, so our root DialogStatic copies never won
   and those two dialogs opened at stock 1x. **For five days that was recorded
   as "the game bypasses the DBPF override" — an OBSERVATION with an INVENTED
   CONCLUSION.** Nobody checked whether a third file existed. Built from the
   MOD's scripts, `area=` doubled; source in `tools\dialog-static\thirdparty-src\`.
   Callout: `UPSTREAM-SAVEWARNING-REPORT.md`.

5. **z_SC4UIScale_WarriorUI-<tier>.dat** (4 entries, added 2026-08-02,
   task #94) — **the load-order law, THIRD occurrence.** warrior's *God
   Terraforming in Mayor Mode* 1.0 replaces TWO stock flyout scripts from
   `150-mods\` (mayor LANDSCAPE {0,96A006B0,09923283} window 0x49923239;
   SIGNS & LABELS {0,96A006B0,CB95403E} window 0xAB954023) **and ships its
   own 1x copies of two art TGIs we already ship 2x** ({46A006B0,14215E27},
   {..,EB7C4D3B}). Its 1x data beat our root 2x → terraform ring UNDOCKED +
   green strips unscaled. THE MOD IS CORRECTLY AUTHORED (both scripts carry
   the 0x0000AAAA marker) — the breakage was entirely ours. Built from ITS
   scripts + ITS bitmaps into `zzz-SC4UIScale\`; gated on both dats by exact
   name+size (8702/5766; filenames verified unique tree-wide, so no other
   mod can satisfy the gate). Callout: `UPSTREAM-WARRIOR-REPORT.md`.
   **BUILDER IS NOW MULTI-GROUP:** `thirdparty-ui\<Name>\` +
   `thirdparty-art\<Name>\` → `z_SC4UIScale_<Name>.dat`, because ONE shared
   package would gate CoriBoom's copy on warrior's mod and vice versa.
   Adding a mod = new subfolder + its kThirdPartyDeps row + 3 deploy lines +
   DatIntegrity count/hash rows, ALL IN THE SAME CHANGE (law 40).
   ⚠ **Generalisable smell: a mod that replaces a stock .UI usually ALSO
   ships the ART that script references.** Check BOTH — fixing the script
   alone leaves 1x art winning, which reads as a half-fix.

**⛔ THE LAW THIS ADDED — GATE EVERY SUCH OVERRIDE ON ITS OWNING MOD.**
A copy of another mod's data is only correct while that mod is in play. Left
active after the user removes the mod, OUR copy sits in `zzz-` (which outranks
everything) and **keeps the removed mod's UI alive.** Measured 2026-07-31: with
CoriBoom's mod deleted our copy (532x640) still beat the stock script
(531x406). `ScaleTier::kThirdPartyDeps` now enables each such package only
while its mod is installed — found by NAME recursively (sc4pac folder names
carry a version), plus a file-size fingerprint where our copy hard-codes the
mod's exact rects, so a mod UPDATE disables our stale copy too. Note the trap
had been written down at `MAYOR-MODE.md:126` and only ever applied inside a
manual test script. **Adding a package built from someone else's data means
adding its dependency row in the same change.**

**THE DIAGNOSTIC (cheap, general): if a live rect matches NEITHER the stock
script NOR our staged copy, a THIRD FILE owns that TGI.** A stock-vs-ours diff
is blind to it. `python tools\dbpf\who_owns_tgi.py <instance...>` prints every
holder in load order and names the winner. On #79c the winner differed from
stock by ONE PIXEL (270x162 vs 270x161).

**⭐ PUBLIC-RELEASE DECISION (user, 2026-08-14).** v3.0.0 goes to a public
GitHub repo + a Simtropolis download. The user's ruling on the five
third-party-derived packages: **regenerated-from-layout is entirely fine to
redistribute and needs only an ATTRIBUTION FIX** — not removal, not permission
chasing. Ship them, credit them properly.

The line that still has to be checked per package, because the user decided the
POLICY and not the FACT: *our own bytes derived from their layout* is cleared;
*their original bytes copied through* is a separate call that comes back to the
user. Anything that cannot be established goes in the second bucket — the safe
default is the one that asks, never the one that ships.

⚠ Note the two are not identical for ART. Our third-party packages are built
from the MODS' OWN BITMAPS, upscaled (WarriorUI: "ITS scripts + ITS bitmaps";
CoriBoom ships its own 516x654 background we upscale). An upscaled bitmap is
derivative of their image in a way a regenerated .UI script is not. Same
attribution answer most likely, but state it accurately rather than filing it
under "regenerated".

Separately, `SelectiveArt` / `ItemIcons` / `DialogStatic` derive from
**Maxis/EA** art out of the game's own archives — a third category again, and
not covered by the third-party ruling above.

**Why:** these are DATA DEFECTS in CAM 4.0.1 / gaps in the icon pools, not
scaling bugs; but the user wants everything working, so we ship surgical
runtime patches rather than editing the mods' files. We never modify another
mod's dat/DLL on disk.

**LONG-TERM PLAN (user, 2026-07-29, not yet started):** finish getting the
modded 2x install fully working → then go back to a VANILLA game and verify
the whole scaling stack there → then tackle the other resolutions
(1.5x / 3x tiers).

**STATE END OF 2026-07-29 (v2.19.0-newshtml DEPLOYED, awaiting eyes-on):**
v2.18.6 fixed everything flyout/submenu/tooltip (user-confirmed). Then the
NEWS BOX (task #42) was cracked: ALL news text (ticker/reader/stories/
popups/tutorials/Credits) is the game's own HTML renderer — SIZE=1..7
resolves through two .rdata point tables the FontStyle system NEVER touches
(why the community's "font size does not work for news"). v2.19.0 scales
both tables + retargets the popup style GUIDs at stock-size clone styles
(MessageHeaderHtml/BodyHtml, added to all six FontStyle files) + AdviceList
never-recurse geometry + SelectiveArt 271→328 (news page art) + Credits
LTEXT maps re-calibrated (would compound otherwise). THREE COUPLED PARTS —
read _tests\REGRESSION.md "NEWS BOX + NEWS TEXT = THE HTML ENGINE" before
touching any of: HtmlSizePatch, the FontStyle Html clone styles, or
build_dialog_static credits_maps. Eyes-on checklist in MAYOR-MODE.md top
block (incl. the never-yet-measured news pop-up TOAST + airports
first-open).

Related: [[reference-sc4-flyout-alignment-marker-rule]],
[[project-sc4-ui-scaling-northstar]], [[feedback-sc4-regression-net]]
