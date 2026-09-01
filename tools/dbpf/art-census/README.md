# FSH art census (group 0x1ABE787D)

Two scripts that enumerate the game's FSH art records **with QFS decompression**,
and recover the artist name each record carries.

## Why this exists

An earlier census over this group byte-scanned the records for plaintext names.
It found 835 of 36,388 and was recorded in the overlay plan as a **structural
null**: 89.9% of the records are QFS-compressed, so a byte scan cannot see them,
and its silence proved nothing at all. This project has a standing law about
exactly that failure — *text scanners are blind to binaries; zero items scanned
is a REFUSAL, not a null.*

`fsh_census.py` decompresses all 36,388 and reads the name out of the FSH
attachment block with code `0x70`, formatted `<instanceid-hex>_<name>` or
occasionally bare. That channel was invisible to the old census.

## Positive control — why a null from this tool is worth something

The signpost art family (`0x8B4A6560`..`0x8B4A6567`) is a closed set of eight
8×8 tiles, and **four of them are QFS-compressed**, so their names are
recoverable only through decompression. Any run that reports them is
demonstrably able to see compressed art. The sweep plants ten such controls —
`pothole` (bare name, uncompressed), `8b4a6566_signpole`, `07f942a1_demolish`,
`28fe0004_dropshadow`, `0b8b0cc9_circlemap`, `4bb0ecf3_driving_bubble`,
`8bb90000_MySimPlumbBob_whitenorm`, `2bb12d1f_CSI_button_background`,
`14315e30_fire_dispatch_enroute`, `8b4a6567_signfoundation` — and prints
`ALL CONTROLS PASS` before reporting any result. **A run that does not print
that line is a refusal and its output must be discarded.** Two earlier versions
of the sweep were thrown away on exactly that basis: the first tokenized the
space-joined CSV column as one run, the second required a token to start with a
letter. Neither was a null; both were broken instruments.

## What it established (2026-08-31)

* The ten 8×8 tiles that init `0x005F73A0` preloads from table `0x00AA5214` are
  **not** route-dot art. They are the query signpost's nine-slice frame plus its
  pole and foundation. That refutes a claim carried in the row-16 write-up.
* **No route-named art exists.** Across all 36,388 decompressed records,
  `route|trip|commut|traffic|trace|destinat|origin|congest|path|dot` yields
  exactly one genuine name, `14315E30_fire_dispatch_enroute` (a CSI dispatch
  icon). Everything else matching is DXT pixel garbage from 256×256 building
  textures. This agrees with row 16's finding that the route trace is a
  triangle strip built from geometry, not a sprite.

## Running it

    python tools/dbpf/art-census/fsh_census.py

Takes roughly 13 minutes and writes a named-art CSV (filename "named-art"
plus the group id) beside the
script. That file is NOT in the repository and there is deliberately no link
to it here - a reference a cloner cannot open is a dead link, and this gate
(`_packaging/Test-NoDeadLinks.py --repo`) caught exactly that. The output is
**gitignored on purpose**: it is bulk EA-derived data, it is regenerable by
anyone who owns the game, and this repository vendors its own tools rather than
extracted game content. The scripts are ours; the data is EA's.
