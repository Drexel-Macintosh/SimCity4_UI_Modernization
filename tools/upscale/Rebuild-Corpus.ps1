<#
.SYNOPSIS
    Regenerate the whole 1x -> tier PNG corpus. THE single source for the
    upscale command. Do not hand-type it; do not copy it into a doc.

.DESCRIPTION
    WHY THIS EXISTS (#170, 2026-08-16). PACKAGES.md documented the corpus
    rebuild as:

        Upscale2x.exe dbpf\extracted\SimCity_1 upscale\preview-15x\SimCity_1 `
                      --factor 1.5 --normalize-names

    - with NONE of the three derived list files. Anyone following the project's
    own documentation would have silently un-shipped three USER-CONFIRMED
    fixes, at exit 0, with every gate still green (each gate measures the new
    tree against itself):

        --cell-strips   #156  per-STATE sampling for N-state strips. Without
                              it a 4-state sheet is resampled as one image and
                              a sliver of the next state bleeds into the cell
                              boundary.
        --nine-slice    #157  CellUnit{3} sizing for `blttype=edge` frames.
        --no-snap       #160  tiled backgrounds must NOT be snapped - a tiled
                              sheet's only contract is to equal its window,
                              and snapping desynchronises the pair.

    `tiled.txt` has no flag of its own: a tiled sheet's requirement IS
    "no snap", so its members are carried in `no-snap.txt`.

    Law 45: if the generator's output is not the shippable file, the
    generator's output will eventually ship. This script IS the command.

.NOTES
    Offline. Reads `dbpf\extracted\SimCity_1`, writes the preview trees only.
    The DAT builders (`build_selective_safe.py`, `build_dialog_static.py`) run
    afterwards and consume those trees - see PACKAGES.md.

    2x is `preview\`, NOT `preview-2x\`. That name is load-bearing: the
    builders default to it when no --factor is passed.
#>
[CmdletBinding()]
param(
    # Which tiers to rebuild. Default is every shipping tier.
    [ValidateSet('1.5', '2', '3')]
    [string[]] $Factor = @('1.5', '2', '3'),

    # Refuse to run unless every derived list file is present AND non-empty.
    [switch] $AllowEmptyLists,

    # Run the preflight and PRINT the exact command line, invoking nothing.
    # This is how you check the flags without spending a corpus rebuild - and
    # it is what makes the "did we pass the lists?" question answerable
    # cheaply, which is the whole reason #170's regression went unnoticed.
    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$tools = Split-Path -Parent $here

$exe = Join-Path $here 'Upscale2x.exe'
if (-not (Test-Path $exe)) {
    throw "Upscale2x.exe not found. Build it first: upscale\Build.ps1"
}

# ALL THREE ARE MANDATORY. An empty or missing list file is a SILENT
# regression - the upscaler prints "0 sheet(s)" and exits 0, so the failure
# only ever shows up on a player's screen at a fractional tier.
$lists = [ordered]@{
    '--cell-strips' = Join-Path $here 'cell-strips.txt'
    '--nine-slice'  = Join-Path $here 'nine-slice.txt'
    '--no-snap'     = Join-Path $here 'no-snap.txt'
    # #175: sheets whose exact pixel EDGES a downstream builder MEASURES (the
    # #152 advisor face-seat scan). Smoothing moves what the scan finds and the
    # seat guard refuses the build. Derived from ADVISOR_FACE_SEATS by
    # make_no_smooth.py; regenerate it if that table changes.
    '--no-smooth'   = Join-Path $here 'no-smooth.txt'
    # #177: the DERIVED height-exact subset - strips with no vertical
    # structure take a plain-rounded height instead of the CellUnit snap.
    # NOT the whole strip list: the blanket form was tried and reverted; the
    # 44 excluded sheets (partial-height crops, rule-(b) 9-sliced cells -
    # including 14416242 in the #162 script c973b411) keep the snap, each
    # with a named reason printed by find_cell_strips.py.
    '--height-exact-strips' = Join-Path $here 'height-exact-strips.txt'
}
foreach ($kv in $lists.GetEnumerator()) {
    # -f binds tighter than +, so the format call must wrap the WHOLE
    # concatenation - the deploy script paid for this exact idiom once
    # already ("pid {0} still running after {1}s" shipped literally).
    if (-not (Test-Path $kv.Value)) {
        throw (("MISSING derived list {0} for {1}. Regenerate it " +
               "(find_cell_strips.py and friends) before rebuilding the " +
               "corpus - shipping without it un-ships a confirmed fix.") `
               -f $kv.Value, $kv.Key)
    }
    $n = @(Get-Content $kv.Value | Where-Object { $_.Trim() -and $_ -notmatch '^\s*#' }).Count
    if ($n -eq 0 -and -not $AllowEmptyLists) {
        throw (("EMPTY derived list {0} ({1}). This exits 0 and ships a " +
               "regression. Pass -AllowEmptyLists only if you have proven " +
               "the list is legitimately empty.") -f $kv.Value, $kv.Key)
    }
    Write-Output ("  {0,-14} {1,4} entries  {2}" -f $kv.Key, $n, (Split-Path $kv.Value -Leaf))
}

# #185: the SECOND --height-exact-strips input - the HAND-AUTHORED code-bound
# slab table (budget band backgrounds, rowPitch = artHeight/2 at
# 0x788209-0x78822E; full doctrine in the file's own header). It cannot ride
# in height-exact-strips.txt because find_cell_strips.py REGENERATES that
# file wholesale, and it cannot ride in $lists because an ordered dictionary
# cannot carry two entries under the same flag key - so it is wired as an
# explicit extra append below, with the same preflight the $lists entries
# get (Upscale2x.cs's parser APPENDS on every occurrence of the flag).
$slabList = Join-Path $here 'height-exact-slabs.txt'
if (-not (Test-Path $slabList)) {
    throw (("MISSING hand-authored list {0} for the second " +
           "--height-exact-strips occurrence (#185). This tree is NOT a git " +
           "repo - rebuild the file from the REGRESSION.md #185 entry (the " +
           "five TGIs + byte evidence are recorded there verbatim); " +
           "shipping without it un-ships the budget slab heights.") `
           -f $slabList)
}
$nSlab = @(Get-Content $slabList | Where-Object { $_.Trim() -and $_ -notmatch '^\s*#' }).Count
if ($nSlab -eq 0 -and -not $AllowEmptyLists) {
    throw (("EMPTY hand-authored list {0} (--height-exact-strips, 2nd " +
           "occurrence). This exits 0 and ships the #185 regression. Pass " +
           "-AllowEmptyLists only if you have proven the list is " +
           "legitimately empty.") -f $slabList)
}
Write-Output ("  {0,-14} {1,4} entries  {2}" -f '--height-exact-strips', $nSlab, (Split-Path $slabList -Leaf))

$src = Join-Path $tools 'dbpf\extracted\SimCity_1'
if (-not (Test-Path $src)) { throw "1x source corpus not found: $src" }

# 2x deliberately lands in `preview\`, not `preview-2x\`.
$outFor = @{ '1.5' = 'preview-15x'; '2' = 'preview'; '3' = 'preview-3x' }

foreach ($f in $Factor) {
    $dst = Join-Path $here (Join-Path $outFor[$f] 'SimCity_1')
    Write-Output ""
    Write-Output ("=== factor {0} -> {1}" -f $f, $dst)

    $argv = @($src, $dst, '--factor', $f, '--normalize-names')
    foreach ($kv in $lists.GetEnumerator()) { $argv += @($kv.Key, $kv.Value) }
    # #185: second --height-exact-strips occurrence (preflighted above). The
    # parser appends, so the run summary's height-exact count is the SUM of
    # both files' entries.
    $argv += @('--height-exact-strips', $slabList)

    # #175: smooth (Catmull-Rom) resample, and it is safe to pass at EVERY
    # factor because the flag refuses itself where it must - integer factors
    # (nearest is already an exact NxN replicate there) and any sheet holding
    # the FF00FF colour key. Passing it unconditionally keeps this script one
    # command instead of a per-tier special case, and the run summary prints
    # all three counts so a refusal can never be mistaken for coverage.
    $argv += '--smooth-unkeyed'
    # #175 second half: also smooth sheets that CONTAIN the FF00FF key, with the
    # key excluded from every average and re-applied by coverage. Safe to pass
    # unconditionally - it refuses itself at integer factors and, critically,
    # refuses any sheet whose key is 1-2px STRUCTURE rather than a region
    # (MEASURED: re-keying collapses a 1px/2px gap distinction that 2x keeps).
    # Of 465 keyed sheets only 48 qualify; the other 417 keep NEAREST.
    # REVERTED 2026-08-16, USER-REPORTED REGRESSION: "I hit options and a pink
    # block appears". That is the #143 signature - the colour key DRAWING.
    # CAUSE (read out of our own code, not guessed): the belt-and-braces line at
    # the end of the resampler nudges an exact FF00FF result off the key
    # (`if (R==0xFF && G==0x00 && B==0xFF) { G = 1; }`). That is CORRECT for an
    # unkeyed sheet, where manufacturing a key would be the bug. In KEYED mode it
    # is exactly backwards: a smoothed pixel that legitimately lands on the key
    # becomes FF01FF, the engine's key test misses it, and it PAINTS PINK.
    # Re-enable only with that line made keyed-aware AND a corpus-wide near-key
    # scan reading zero. The flag and its guard stay in Upscale2x.cs.
    # GH5 2026-08-18: --supersample replaces the Catmull-Rom fill with a
    # LOSSLESS x3 then an area reduction, which is even by construction
    # rather than even-by-blurring. It reuses this dispatch, so it needs
    # --smooth-unkeyed above; and --smooth-keyed is re-enabled WITH it
    # because the #175 pink cause does not exist on this path - the
    # manufacture-guard nudge is !keyed-only, which is the asymmetry #175
    # had backwards. GATED: the corpus-wide near-key scan must read ZERO
    # and 2x/3x must stay byte-identical, both checked after this runs.
    # GH5 2026-08-18, SCOPED TO UNKEYED SHEETS. --supersample replaces the
    # Catmull-Rom fill with a LOSSLESS x3 then an area reduction - even by
    # construction rather than even-by-blurring. It refuses itself at integer
    # factors, so 2x and 3x stay byte-identical.
    #
    # --smooth-keyed stays OFF and that is the whole point of this scoping.
    # With it on, the 48 eligible KEYED sheets also supersampled and
    # gate_key_integrity.py REJECTED the build (exit 1, 7+ sheets, both
    # directions) because the gate predicts NEAREST key placement and the
    # majority-vote moves the key BOUNDARY. Deciding that boundary policy - and
    # whether the gate should predict the resampler in use - is its own piece of
    # work with its own negative control. Amending a gate so your own change
    # passes is not something to do as a side effect of a sharpness fix.
    $argv += '--supersample'

    # #200 (2026-08-29): the even reduce is now OPT-IN. MEASURED - the
    # x3-then-area-average softens one hard edge in three at f=1.5 (edge
    # retention 0.7981 on averaged sheets) while the sheets already taking
    # nearest at the SAME factor measure 0.9979, i.e. as crisp as 2x/3x,
    # which carry ZERO invented pixels across 562M. It was bought for tick
    # EVENNESS, which genuinely conflicts with sharpness at a fractional
    # factor - so it is kept, but only for the sheets that have ticks.
    # even-strips.txt is DERIVED (make_even_strips.py): the 89 measured tick
    # ladders UNION cell-strips.txt. Only 20 of those 89 were in
    # cell-strips.txt, which is why this is its own list and not a reuse.
    # No-op at integer factors: the whole dispatch already refuses itself
    # there, and 2x/3x outputs must stay byte-identical.
    $evenList = Join-Path $PSScriptRoot 'even-strips.txt'
    if (Test-Path $evenList) { $argv += @('--even-strips', $evenList) }
    else { throw "even-strips.txt missing - run tools/research/sharp15/make_even_strips.py" }

    # Computed before the DryRun exit so the dry run can print the post-steps
    # with the real path (F13).
    $ladderDir = Join-Path $PSScriptRoot (Join-Path $outFor[$f] 'SimCity_1')

    if ($DryRun) {
        Write-Output ("  DRYRUN would run: Upscale2x.exe " + ($argv -join ' '))
        # F13 (review 2026-08-16): the dry run must show the WHOLE rebuild -
        # the two post-steps are part of the command this script IS, and a
        # dry run that hides them re-opens the #170 gap ("did we run the
        # redraw and the gate?" must be answerable without spending a
        # rebuild).
        Write-Output ("  DRYRUN would run: redraw_ladder.py {0} --factor {1}" -f $ladderDir, $f)
        Write-Output ("  DRYRUN would run: gate_key_integrity.py --tier {0}" -f $f)
        continue
    }
    & $exe @argv
    if ($LASTEXITCODE -ne 0) {
        throw ("Upscale2x failed for factor {0} (exit {1})" -f $f, $LASTEXITCODE)
    }

    # #180 LADDER REDRAW IS A POST-STEP, NOT AN OVERLAY (wired 2026-08-16).
    # redraw_ladder.py re-lays the Mayor Rating filmstrip {46a006b0,14015549}
    # (+ its 1abe787d twin) at fractional factors and was originally run BY
    # HAND after this script - which meant every corpus rebuild silently
    # reverted it to plain NN and the builder shipped the reversion (#170's
    # failure shape: the fix is not part of the command that makes the
    # artifact). It asserts integer factors are byte-identical to NN itself,
    # so running it unconditionally is safe at 2x/3x. ($ladderDir is computed
    # above the DryRun branch so the dry run prints the same path - F13.)
    & (Get-Command python).Source (Join-Path $PSScriptRoot 'redraw_ladder.py') `
        $ladderDir --factor $f
    if ($LASTEXITCODE -ne 0) {
        throw ("redraw_ladder failed for factor {0} (exit {1})" -f $f, $LASTEXITCODE)
    }

    # #181 COLOUR-KEY INTEGRITY GATE (wired 2026-08-16). Key damage in the tier
    # just written fails the REBUILD instead of a player's screen: near-key
    # pixels (the #143 "pink" class - an averaged key the engine's exact-match
    # test misses) and any drift of a sheet's exact-key pixel set from the
    # upscaler's own nearest-neighbour map (R2). Runs AFTER redraw_ladder
    # because the gate knows the #180 ladders are re-laid at fractional
    # factors and checks the redraw's invariants there instead; at 2x/3x that
    # exemption is dropped (redraw == NN by construction) so the integer tiers
    # get the full equality. It proves its own teeth via --selftest; see
    # _tests\REGRESSION.md #181.
    & (Get-Command python).Source (Join-Path $PSScriptRoot 'gate_key_integrity.py') `
        --tier $f
    if ($LASTEXITCODE -ne 0) {
        # parens around the concatenation are LOAD-BEARING: -f binds tighter
        # than + in PowerShell, so without them only the last fragment is
        # formatted and the {0}/{1} would print literally.
        throw (("gate_key_integrity failed for factor {0} (exit {1}) - the " +
                "tier tree carries colour-key damage; do NOT run the DAT " +
                "builders on it") -f $f, $LASTEXITCODE)
    }
}

if ($DryRun) { Write-Output ""; Write-Output "DRYRUN - nothing was written."; return }

Write-Output ""
Write-Output "corpus rebuilt. NOW re-run the DAT builders (PACKAGES.md), then:"
Write-Output "  python uimap\emu\gate_btn_undercover.py     # 0 BUILDER-WRONG at every tier"
Write-Output "  _tests\Test-DatIntegrity.ps1                # deployed == built"
Write-Output ""
Write-Output "INTEGER-TIER CONTROL: 2x and 3x must come back with ZERO"
Write-Output "  differing ENTRY PAYLOADS vs what ships today. Compare payloads,"
Write-Output "  never the file hash - a DBPF header carries a timestamp at"
Write-Output "  offsets 25/29 and changes on every single build (#170)."
