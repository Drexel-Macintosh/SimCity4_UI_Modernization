# Enumerate the DBPF Archives, Do Not List Them

The game's install root holds nine DBPF archives, not the seven a hand-written
list names. Any tool that searches for a TGI by walking a hard-coded archive
list can report a false negative — and it is only ever wrong about the archive
that was left out, which is exactly the case the search was run for.

## The archive set

A hard-coded list covering

    SimCity_1.dat .. SimCity_5.dat, EP1.dat, SimCityLocale.DAT

misses `Intro.dat` (~18 MB, 3 index entries) and `Sound.dat`. Both sit in the
install root alongside the others. Enumerating `*.dat` in the install root at
run time reports nine archives on a stock install.

`tools\dbpf\find_tgi.py` therefore carries no list: it discovers the archive set
and prints the count it found.

    python tools\dbpf\find_tgi.py ea7f0eae
    -> discovered 9 archive(s) ... 0xEA7F0EAE  Intro.dat  T=0x856DDBAC ...

That line doubles as a regression check. If the reported count drops, discovery
has regressed to a list.

## The failure mode it prevents

The startup-splash background lives in `Intro.dat`:

    DbpfExtract.exe Intro.dat out 0x856DDBAC
    -> T-856ddbac_G-46a006b0_I-ea7f0eae.png   768x600   500,591 B

A seven-archive list reports the TGI `{856ddbac, 46a006b0, ea7f0eae}` as
dangling — "no stock source anywhere" — a null produced by a scanner that could
not have seen the archive the asset lives in. Acting on that null substitutes a
third-party mod's copy of the splash into a shipped package, and a pixel diff
against the genuine stock bitmap separates the two: 99.72% of pixels differ,
maximum channel delta 251. That is a different image, not a re-encode. The cure
is to extract the pristine 1x source from `Intro.dat` and upscale it with the
project's own `Upscale2x.exe` for the 1.5x, 2x and 3x tiers.

A caveat on the wrong axis does not help. A list-based tool that warns its
negatives are unreliable because the *Plugins* tree went unscanned names a real
limitation and the wrong one: the gap here is on the game side of the scan. A
disclaimer aimed at the wrong axis reads as diligence and buys nothing.

## Rules

* Before calling an art reference dangling, state how many archives were scanned
  and where that number came from. A probe finding nothing is not a fact until
  the probe is shown capable of seeing the thing.
* Plugins coverage and game-archive coverage are separate questions answered by
  separate tools: `who_owns_tgi.py` covers the Plugins tree, `find_tgi.py`
  covers every archive the install actually has.
* "No 2x asset in the upscale preview set" means the preview set built from
  `SimCity_1` only (`tools\upscale\preview*\SimCity_1\`). It is not evidence
  that the 1x source is missing from the game.
* `DbpfExtract.exe <archive> <outDir> [0xTYPE]` is read-only and is the way to
  obtain a pristine 1x source. Prefer it over any mod's copy, always — for
  provenance, and because a permissively licensed project must not redistribute
  third-party mod art.
* A bitmap that looks like the stock one is not the stock one. Pixel-diff it.

The durable lesson is not "add `Intro.dat`". A hand-maintained inventory of what
exists on disk is a claim about the filesystem, and it ages silently: every
patch to such a list is itself a list, short by whatever the next install adds.
Deriving the count at run time is the only form of the inventory that cannot be
short by one.
