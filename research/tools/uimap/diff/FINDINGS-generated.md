# FINDINGS-generated.md — machine output of tools\uimap\diff\diff.py

Regenerate with `python diff.py --auto --write-findings`. Do not hand-edit:
prose analysis belongs in `FINDINGS.md`, which cites this file.

## Inputs

| log | version | render | f | evidence | records | events | sha256[:12] |
|---|---|---|---|---|---|---|---|
| SC4UIScale.log | v2.35.1-revert | 2400x1600 | 2.0 | AutoScale tier line | 32 | 12 | e74569766589 |
| SC4UIScale.log.bak-stock800 | v2.6.0-split | - | 1.0 | ScaleAll=0 (sweep inert) -> stock geometry | 70 | 0 | 3d1b43360a33 |

- stock scripts: 1314 ids from `tools\uiscripts\extracted`
- stock log oracles: ['SC4UIScale.log.bak-stock800']
- predicted model: **available** — 50 predicted windows from 7 file(s)

## Summary

```
{
 "event_check": {
  "MATCH": 5
 },
 "live_ids": 47,
 "live_vs_stock": {
  "AMBIGUOUS-ID": 6,
  "MATCH": 4,
  "PRE-SWEEP": 4,
  "STOCK-1X": 10
 },
 "logs": 2,
 "missing_from_live": 22,
 "missing_from_model": 47,
 "model_available": true
}
```

## A. SCALE-EVENT self-check (strongest evidence: before+after on one line)

5 transitions checked, **0 MISMATCH**.

## B. LIVE vs STOCK

### STOCK-1X (10) — live size EQUALS stock while f!=1 — the scaler missed it

| id | instr | parent | live | stock | expected | delta | vis | triage |
|---|---|---|---|---|---|---|---|---|
| 0x09EBE9EE | RGKID | @REGION | 415x106 | 415x106 | 830x212 | [-415, -106] | None | - |
| 0x09EBF2BD | RGKID | 0x6A91DC16 | 80x60 | 80x60 | 160x120 | [-80, -60] | 1 | - |
| 0x26C10A3E | RGKID | 0x6A91DC16 | 80x60 | 80x60 | 160x120 | [-80, -60] | 1 | - |
| 0x2BA6BB97 | RGKID | @REGION | 800x600 | 800x600 | 1600x1200 | [-800, -600] | None | - |
| 0x4A779A1A | RGKID | 0x6A91DC16 | 80x60 | 80x60 | 160x120 | [-80, -60] | 1 | - |
| 0x6A0AF41D | RGKID | @REGION | 800x600 | 800x600 | 1600x1200 | [-800, -600] | None | - |
| 0x6A91DC14 | RGKID | @REGION | 1154x51 | 1154x51 | 2308x102 | [-1154, -51] | None | - |
| 0x6A91DC16 | RGKID | @REGION | 454x91 | 454x91 | 908x182 | [-454, -91] | None | - |
| 0xC9E41918 | RGKID | 0x00000000 | 112x18 | 112x18 | 224x36 | [-112, -18] | 1 | - |
| 0xEA5BD179 | RGKID | 0x00000000 | 384x26 | 384x26 | 768x52 | [-384, -26] | 1 | - |

### OVER-SCALED (0) — live size equals round(stock*f*f) — scaled twice

_none_

### MISMATCH (0) — neither law reproduces the live size

_none_

## C. Model join

- MISSING-FROM-MODEL: 47
- MISSING-FROM-LIVE: 22

| id | seen in | triage |
|---|---|---|
| 0x00000000 | SC4UIScale.log, SC4UIScale.log.bak-stock800 | GENERIC-ID |
| 0x0000AAAA | SC4UIScale.log, SC4UIScale.log.bak-stock800 | ALIGNMENT-MARKER |
| 0x098F4F6C | SC4UIScale.log.bak-stock800 | - |
| 0x09EBE9EE | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x09EBEE45 | SC4UIScale.log.bak-stock800 | - |
| 0x09EBEE60 | SC4UIScale.log.bak-stock800 | - |
| 0x09EBF2BD | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x09EBF2C3 | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x0A5510A9 | SC4UIScale.log.bak-stock800 | - |
| 0x0BB0F5E7 | SC4UIScale.log.bak-stock800 | - |
| 0x0BB0F607 | SC4UIScale.log.bak-stock800 | - |
| 0x26C10A3E | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x2A5B0000 | SC4UIScale.log.bak-stock800 | - |
| 0x2A5B0001 | SC4UIScale.log.bak-stock800 | - |
| 0x2A5B0002 | SC4UIScale.log.bak-stock800 | - |
| 0x2AAB8CC1 | SC4UIScale.log.bak-stock800 | - |
| 0x2BA290C1 | SC4UIScale.log.bak-stock800 | - |
| 0x2BA6BB97 | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x2BB0F616 | SC4UIScale.log.bak-stock800 | - |
| 0x4A779A1A | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x4BA290D8 | SC4UIScale.log.bak-stock800 | - |
| 0x4BB0F5F7 | SC4UIScale.log.bak-stock800 | - |
| 0x4BB92C1F | SC4UIScale.log.bak-stock800 | - |
| 0x6104489A | SC4UIScale.log.bak-stock800 | - |
| 0x6A0AF41D | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x6A91DC14 | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x6A91DC15 | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x6A91DC16 | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0x6BB91308 | SC4UIScale.log.bak-stock800 | - |
| 0x6BB92BCA | SC4UIScale.log.bak-stock800 | - |
| 0x8A1DA655 | SC4UIScale.log.bak-stock800 | - |
| 0x8BB0F5FF | SC4UIScale.log.bak-stock800 | - |
| 0x8BB9130F | SC4UIScale.log.bak-stock800 | - |
| 0xA98F4F88 | SC4UIScale.log.bak-stock800 | - |
| 0xABA290E1 | SC4UIScale.log.bak-stock800 | - |
| 0xABB0F60E | SC4UIScale.log.bak-stock800 | - |
| 0xC9E41918 | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0xCA1DA670 | SC4UIScale.log.bak-stock800 | - |
| 0xCA5CFEE2 | SC4UIScale.log.bak-stock800 | - |
| 0xCBA290EC | SC4UIScale.log.bak-stock800 | - |
| 0xEA5A96E6 | SC4UIScale.log.bak-stock800 | - |
| 0xEA5BD179 | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0xEA659793 | SC4UIScale.log.bak-stock800 | - |
| 0xEA8CAD19 | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0xEA8CAD1A | SC4UIScale.log, SC4UIScale.log.bak-stock800 | - |
| 0xEBB912FE | SC4UIScale.log.bak-stock800 | - |
| 0xEBB91356 | SC4UIScale.log.bak-stock800 | - |

## D. Tier generality (offline)

For each tier: how many (id, stock size) pairs the EDGE law and the
DIRECT law disagree on (a one-pixel class of bug that 2x cannot show),
and how many distinct stock sizes COLLAPSE onto the same scaled size
(where a size-based identification stops being unique).

| f | edge-vs-direct divergent pairs | collapsing size groups |
|---|---|---|
| 1x | 0 | 0 |
| 1.5x | 807 | 0 |
| 2x | 0 | 0 |
| 3x | 0 | 0 |

