# UI coverage matrix — digest (full report in agent transcript, 2026-07-29 night)

Transcribed by the main session because the read-only audit agent could not
write files. Basis: 282 layout scripts, 329 top-level roots, 117 distinct ids.

## Bucket counts
A COVERED-RUNTIME 130 roots (48 ids, all log-verified) · B COVERED-STATIC 158
(45 ids; 55 also kNeverScaleIds-insured) · C deliberately-1x **0** (the list
is now purely a double-scale interlock) · D UNTOUCHED-REACHABLE 16 (13 ids) ·
E dev-editor 25 · F stale copies 5 proven. Coverage: 288/304 shipping roots =
**94.7%**.

## Bucket D (untouched, reachable) — ranked
1. ✅FIXED same night (art): 0x8BB27C12 (I-6bb27447) + 0xAB954023 (I-cb95403e)
   tool flyout columns — WERE live-bugged (swept 2x, art all UNSCALED, marker
   ignored). Art shipped, SelectiveArt 494→506. ⚠ PLACEMENT still generic-
   anchored — markers ignored; dock decision needs MCAL/StripDump measure.
2. 0x6BB92BCB (I-abb0120f) Trip-Types legend inset 181x296 — quarter-art +
   2x-text expected. (NOTE: text-sweep called its root wrapper covered via
   child 0x0BB0F5E7 — the two audits disagree; measure before fixing.)
3. 0x8A8DFCF5 (I-6b704690) Label Tool 409x142 — 1x frame/2x text + TextEdit.
4. 0x0A551C53 (I-ca539343) region city-bubble stub 42x159.
5. 0xEC1A5CBF (I-8c1a5c9f) U-Drive-It console VARIANT (not in the 43-script
   family!) — same footprint as 0x4BCB938A; find which vehicle/mode spawns it.
6. Sim occupant chips: 0x6BFAC122/0x8BFAC13E (I-0bfac164), 0xCBFACAE1
   (I-abfac197), 0x27DF05BF/BE (I-6a9455c9) — 36x41 portrait class.
7. 0xEACA96DD (I-6aca9687) grid popup at advisor-toast origin.
8. 0x0A41C7B2/B3 (I-0a41be3e/3f) unidentified buttons (Establish/Obliterate
   neighborhood) — DPROBE while founding/obliterating.
9. 0x000A0000 (I-ebd0d36d) Select-A-Bridge sibling button, text-only.

## Bucket F — stale script copies (live copy first)
0xE9889775: LIVE I-2bc90671, STALE I-898897de · 0x6A64E3C0: LIVE I-4bc906b5,
STALE I-0a5fa5d6 · 0xC991EDA8: LIVE I-69e3d347, STALE I-a991ed83 ·
Graphs 0x8A8B5B71/72+0x0A4A8176: LIVE I-6bc9065a, STALE I-ea2871aa ·
0xAA3AC002: LIVE I-cbc3c2b9, STALE I-aa3acdfe (this root only).
Hazard: builder marks by root id across ALL copies → stale copies consume
clone budget and could win the DBPF load race missing children.
NOT stale: 0xCA35CBED both scripts live (aa356502 + aaa44448) — do not prune.
UNDETERMINED: Data Views live copy (repo asserts 2bc9060f; settle via deep
child diff — 184 vs 181 vs 165 nodes). Advisor briefing 4a160034 vs cbc905cd
differ only in 0x2A84B45A width.

## Inside covered roots — remaining un-leverable-by-art
Runtime-pixel nodes (imagerect, no image=): My Sims portraits 0x22220000-04 +
0x22220055, 0x8A1F1EEF (100x100), 0xABBAA2D3 ir=5,5,695,130, budget
0xAA3AC000/1 ir=0,0,100,100 ×2 each.
Code-painted classes un-levered: 0xAA5C2F86 TrendBar (buffer unverified),
0x28C5A41F (in Data Views, UNIDENTIFIED), 0xC7A0E17E (in status panel,
UNIDENTIFIED — both sit in always-visible HUD roots = highest value probes).
Refmap art gap inside covered roots: ZERO untouched refs remain.

## Bucket E caveats
Soft-E: I-e9263d4c "Text Entry" + I-e9263d4e "Select Foundation" carry
captionres (localization tell-tale fails); reachable only via Lot Editor.
I-cb40cfdc is the DEV twin of the shipping Label Tool — different root ids.
