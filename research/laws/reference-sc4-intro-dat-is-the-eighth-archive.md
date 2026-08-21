# Enumerate the DBPF Archives, Do Not List Them

The game's install root holds nine DBPF archives, not the seven that a
hand-written list is likely to name. Any tool that searches for a TGI by walking
a hard-coded archive list is capable of reporting a false negative — and it will
only ever be wrong about the archive that was left out, which is exactly the
case the search was run for.

## The archive set

A hard-coded list covering

    SimCity_1.dat .. SimCity_5.dat, EP1.dat, SimCityLocale.DAT

misses at least `Intro.dat` (~18 MB, 3 index entries) and `Sound.dat`. Both sit
in the install root alongside the others. Enumerating `*.dat` in the install
root at run time reports nine archives on a stock install.

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

Under the seven-archive list, that TGI `{856ddbac, 46a006b0, ea7f0eae}` was
reported as dangling — "no stock source anywhere" — across several reports, a
null produced by a scanner that could not have seen the archive it lived in.
Acting on that null meant substituting a third-party mod's copy of the splash in
a shipped package. A pixel diff against the genuine stock bitmap showed 99.72%
of pixels differing with a maximum channel delta of 251: a different image, not
a re-encode. The cure was to extract the pristine 1x source from `Intro.dat` and
upscale it with the project's own `Upscale2x.exe` for the 1.5x, 2x and 3x tiers.

A caveat on the wrong axis does not help here. The list-based tool already
warned that its negatives were unreliable, but the warning named unscanned
*Plugins* as the reason — true, and irrelevant to the actual gap, which was on
the game side of the scan. A disclaimer aimed at the wrong axis reads as
diligence and buys nothing.

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
exists on disk is a claim about the filesystem; it ages silently. The first
correction to the seven-archive list ("one was forgotten") was itself short by
one, which is the whole argument for deriving the inventory rather than writing
it down.
