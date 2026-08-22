# CHECKPOINT — sub-flyout BUILDER hunt (agent-owned, incremental)

Target: the code that creates/populates the shared sub-flyout container
`0x8A6E61E0` and its item strip `0x8A2CAD8B` on every second-level menu open.
Everything offline; exe opened `rb` only. Deliverable = `tools\uimap\SUBFLYOUT-BUILDER.md`.

## STATUS

| unit | state |
|---|---|
| id scan (both window ids in `.text`) | DONE |
| owning function identified | DONE — `sub_7EAEB0` |
| twin (first-level flyout) identified | DONE — `sub_7E7270` |
| container class + geometry methods decoded | DONE — `0x79AC60` / `0x79AD00` / `0x79B050` |
| strip control class + item metrics decoded | DONE — `0x79A0E0` / `0x79A620` |
| model validated against live dumps | DONE — reproduces 141x339, 258x482, 88x382, and the 53/25/12/94/62/6 field dump |
| constant table + encodings | DONE |
| imm8 ceiling flags | DONE |
| art-vs-code verdict | DONE — **CODE-derived** |
| C++ site table emitted | DONE |

## HARD FACTS (each with a VA)

- `0x8A6E61E0` appears **exactly once** in the whole exe: `push 0x8a6e61e0`
  at `0x007EB11A` (bytes `68 E0 61 6E 8A`), followed by
  `call [edx+0x100]` = `SetID` at `0x007EB121`.
- `0x8A2CAD8B` appears twice: `push` at `0x007EB1F4` (bytes `68 8B AD 2C 8A`)
  feeding `SetID` at `0x007EB1FB`, and at `0x007E5EB9` inside `sub_7E5E90`
  (a lookup helper, creates nothing).
- Both create sites live in **`sub_7EAEB0` (0x007EAEB0 .. 0x007EB320, 1136 bytes)**.
  That function is the sole builder.
- Its twin `sub_7E7270` (0x007E7270 .. 0x007E75B0) builds the FIRST-level
  flyout from the same classes with its own copies of every constant.

## VALIDATION (why the model is trusted)

Predicted from the constants alone, checked against numbers already measured
in this repo before I existed:

| predicted | source of the measurement |
|---|---|
| first-level container **141** wide | `SC4-UI-ENGINE.md` §2.1 `srcBuf [0xDC] = 141x339` |
| first-level container **339** tall at 6 rows | same line |
| first-level fields `53, 25, 12, 94, 62, 6` | same section, live DOBS dump |
| sub-flyout container **129** wide (258 at 2x) | `MAYOR-MODE.md` "EXACT width 258" |
| sub-flyout heights 103/143/192/241/290/339/388/437 (206/286/384/482/580/678/776/874 at 2x) | `MAYOR-MODE.md` "258 x 206/286/384/482/580/678/776/874" |
| strip 44 x 191 for a 4-item menu (88x382 at 2x) | `MAYOR-MODE.md` / `UiSpike.cpp` SUBHOOK log |
| ring sprite exactly **80** wide | `MAYOR-MODE.md` "this sprite is EXACTLY 80 wide" |

| native placement `btn + (20,−86)` for a 4-item menu | `MAYOR-MODE.md` SUBDOCK, `btn(158,560)+(20,-86)=(178,474)` |

Seven independent live numbers, all reproduced. No fitting was done — the
formulas came out of the disassembly first.

## THE FORMULAS (closed form, `sub_79AD00`)

```
stripW   = itemW(44)
stripH   = (itemH(44) + spacing(5)) * n − spacing      = 49n − 5
contentH = max(stripH, [0xF4]=53) + 2*[0xE8]=25        = max(49n−5,53) + 50
contW    = [0xF0]=80 − [0xF8]=4 + [0xE4]=53            = 129
left     = btnAbsCentreX − [0xFC]=27
top      = ([0xF4]>>1) − (contentH>>1) + btnAbsCentreY − [0x100]=29, then 4 clamps
stripLeft= contW − (([0xE4] + stripW) >> 1) − 1        = 80
stripTop = (contentH − stripH) >> 1
```

## VERDICT ON THE ART HYPOTHESIS

**CODE-derived, decisively.** Every number reaching a `SetArea` is a code
immediate. The art contributes exactly one value — `obj[0xEC] =
img.GetHeight() − 2*[0xE8]`, the tileable middle-segment height of the bar,
consumed only by `Plot` (`0x79B1E7`). It sizes nothing. Confirmed twice:
`53 − 50 = 3` for the sub-flyout's 292x53 atlas and `62 − 50 = 12` for the
first-level atlas, the latter matching `ENGINE`'s live `[0xEC]=12` exactly.
(There IS one coupling: doubling `[0xE8]` against a 1x atlas makes `[0xEC]`
negative — the 2x atlas must load. It ships in both candidate groups.)

## IMM8 CEILING

| tier | over | which |
|---|---|---|
| 1.5x | 1 | `0x7E74A5` (twin ringW 94→141) |
| **2x** | **2** | `0x7EB165` ringW 80→**160**, `0x7E74A5` ringW 94→**188** |
| 3x | 10 | both ringW, both `[0xE4]`, both `[0xF4]`, all four item sizes |

At 2x the sub-flyout has exactly ONE unpatchable constant. Recommended cure =
a thunk on vtable `0xAB6D04` slot `+0x10` (`SetLayout`, fixed arity `ret 0x20`),
which also serves every other constant and every tier.

## PROOF LINE

`SUBLAY ret=0x007EB171 e4=53 e8=25 f0=80 f4=53 f8=4 fc=27 100=29`
— `0x007EB171` is the return address of the ONLY sub-flyout `SetLayout` call
(`call [eax+0x10]` @`0x7EB16E`, 3 bytes). The only other caller of that slot in
the exe returns to `0x007E74B1`. One field names the builder.

## OUTPUTS

- `tools\uimap\SUBFLYOUT-BUILDER.md` — the full decode
- `tools\uimap\subflyout_builder.py` — `--resume`, own state file
- `tools\uimap\subflyout-builder.json` — 30 sites, schema-compatible with `constants.json`
- `tools\uimap\generated-subflyout-builder-{1.5,2,3}x.txt` — C++ site tables
- **0 byte-verify failures** at every tier.

## NOT TOUCHED

`SUBFLYOUT-CONSTANTS.md` (sibling agent), `src\**`, `_tests\**`, `dist\**`,
`HANDOFF.md`, `README.md`, the shared `state.json`, the exe, any game file.
