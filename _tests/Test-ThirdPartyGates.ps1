# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# Regression: every package built from ANOTHER MOD'S data is correctly gated.
#
# WHY THIS EXISTS
# ---------------
# Three of our packages contain 2x copies of other mods' .UI scripts, because
# those mods replace stock scripts and - by the load-order law - our root
# packages can never override them. Such a copy is only correct while that mod
# is installed and unchanged:
#   * mod REMOVED and our copy left active -> our frozen copy keeps the removed
#     mod's UI on screen. Measured 2026-07-31: with CoriBoom's mod deleted our
#     zzz- copy (532x640) still beat the stock script (531x406).
#   * mod UPDATED and our copy left active -> our copy encodes the OLD rects, so
#     the dialog is visibly wrong rather than merely unscaled.
# ScaleTier::kThirdPartyDeps gates each package on its mod. This test proves the
# gate's INPUTS are still true, which is the half that rots silently: a mod
# update changes a file size and nothing else tells us.
#
# It does NOT uninstall anything. It reads the dependency table straight out of
# ScaleTier.cpp so the test cannot drift from the shipped gate, then checks each
# declared mod file the same way the DLL does (search by NAME, because sc4pac
# folder names carry a version).
#
# OFFLINE. Never launches, attaches to or kills SimCity 4. Reads only.
# PASS = exit 0, "ALL PASS".
#
# ⛔ v4.5.0: THE LIVE/GATED VERDICT NO LONGER COMES FROM A FILENAME.
# Through v4.4.0 the armed tier kept `<pkg>-<tag>.dat` while the other tiers
# wore `.dat.x1-disabled`, so a directory listing carried BOTH the tier and the
# gate verdict, and that is what this test read. From v4.5.0 arming is a
# CONTENT SWAP at a stable filename (src\ScaleTier.cpp: ArmOne / CommitArming):
# the live name is `z_SC4UIScale_<Pkg>.dat` at every tier, under every gate
# verdict, forever, and the bytes come from an inert `<Pkg>.<tag>.uipay`
# payload the plugin scan never opens (extension-gated, measured by probe #202
# whose positive control was 13 of our live .dat files appearing in the same
# census that omitted the .uipay). A GATED-OFF package is a live file holding
# `.off` content: byte-different and TGI-empty, but NAME-IDENTICAL to an armed
# one.
#
# Left unchanged, the old check therefore failed CLOSED for every package on a
# healthy install - no `<pkg>-<tag>.dat` exists any more, so `$anyPresent` was
# false everywhere and the suite reported "package missing entirely" for rows
# that were fine. The verdict is now re-sourced from `z_SC4UIScale_STATE.txt`
# (ScaleTier.cpp: WriteArmState), the only surviving record of the armed tag
# and the gate reason.
#
# BOTH LAYOUTS ARE HANDLED, ON PURPOSE, and the script SAYS WHICH ONE IT FOUND:
# the developer's own Plugins tree is deliberately still on the rename layout.
$ErrorActionPreference = "Stop"
$proj = Split-Path $PSScriptRoot -Parent
$plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$src = Join-Path $proj "src\ScaleTier.cpp"

# The only folders this mod ever puts a package in. Scanned directly rather
# than recursively over Plugins\ - the recursive scan below is for OTHER mods'
# files, and it deliberately excludes ours.
$OurDirs = @(
    $plugins                                  # pre-4.2.0 root copies, if any
    (Join-Path $plugins '010-SC4UIScale')
    (Join-Path $plugins 'zzz-SC4UIScale')
)

function Get-OurPackageFiles {
    $f = @()
    foreach ($d in $OurDirs) {
        if (-not (Test-Path -LiteralPath $d)) { continue }
        $f += @(Get-ChildItem -LiteralPath $d -File -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -like 'z_SC4UIScale_*' })
    }
    return $f
}

# Reads every z_SC4UIScale_STATE.txt in our folders. Format is WriteArmState's:
# two `#` header lines, then TSV
#   base <TAB> tag <TAB> reason <TAB> paySize <TAB> payTime <TAB> liveSize <TAB> liveTime
# `tag` is the armed payload tag (15x/2x/3x/1x/on) or `off`. `base` is the LEAF
# name - SyncDat splits the folder off before recording - so a kThirdPartyDeps
# package string must be reduced with Split-Path -Leaf before lookup.
function Read-ArmState {
    $rows = @()
    foreach ($d in $OurDirs) {
        $s = Join-Path $d 'z_SC4UIScale_STATE.txt'
        if (-not (Test-Path -LiteralPath $s)) { continue }
        foreach ($line in (Get-Content -LiteralPath $s)) {
            if (-not $line -or $line -match '^\s*#') { continue }
            $c = $line -split "`t"
            if ($c.Count -lt 7) { continue }
            $rows += [pscustomobject]@{
                Base     = $c[0]
                Tag      = $c[1]
                Reason   = $c[2]
                LiveSize = [int64]$c[5]
                LiveTime = [int64]$c[6]
                Dir      = $d
                StateFile = $s
            }
        }
    }
    return $rows
}

if (-not (Test-Path $src)) { Write-Output "FAIL: ScaleTier.cpp not found"; exit 1 }
$text = Get-Content $src -Raw

# Parse kThirdPartyDeps { package, modFile, prefixMatch, modSize, modFile2, modSize2 }
$block = [regex]::Match($text,
    'kThirdPartyDeps\[\]\s*=\s*\{(?<body>.*?)\n\t\};', 'Singleline')
if (-not $block.Success) { Write-Output "FAIL: could not parse kThirdPartyDeps"; exit 1 }
$rx = [regex]'\{\s*L"(?<pkg>[^"]+)",\s*L"(?<f1>(?:[^"\\]|\\.)*)",\s*(?<pre>true|false),\s*(?<s1>\d+),\s*(?:L"(?<f2>(?:[^"\\]|\\.)*)"|nullptr),\s*(?<s2>\d+)\s*\}'
$deps = @()
foreach ($m in $rx.Matches($block.Groups['body'].Value)) {
    $deps += [pscustomobject]@{
        Package = $m.Groups['pkg'].Value -replace '\\\\', '\'
        File1   = $m.Groups['f1'].Value -replace '\\\\', '\'
        Prefix  = ($m.Groups['pre'].Value -eq 'true')
        Size1   = [int64]$m.Groups['s1'].Value
        File2   = $(if ($m.Groups['f2'].Success) { $m.Groups['f2'].Value -replace '\\\\', '\' } else { $null })
        Size2   = [int64]$m.Groups['s2'].Value
    }
}
if ($deps.Count -eq 0) { Write-Output "FAIL: kThirdPartyDeps parsed as empty"; exit 1 }
Write-Output ("Parsed {0} third-party dependency row(s) from ScaleTier.cpp" -f $deps.Count)

# ---- WHICH ARMING LAYOUT IS ON DISK? ---------------------------------------
# Named out loud because the two answer the "is it live" question by different
# evidence, and a wrong guess here is silent: under the payload layout every
# tier-tagged name is absent, which the rename-era check read as "missing".
$ourFiles = @(Get-OurPackageFiles)
$payFiles = @($ourFiles | Where-Object { $_.Extension -eq '.uipay' })
$renFiles = @($ourFiles | Where-Object {
    $_.Name -like '*.x1-disabled' -or
    (($_.Extension -eq '.dat') -and ($_.BaseName -match '-(15x|2x|3x|4x|1x)$')) })
$armState = @(Read-ArmState)

if ($payFiles.Count -and $renFiles.Count) {
    Write-Output ""
    Write-Output ("REFUSING: MIXED LAYOUT - {0} payload file(s) and {1} rename-layout " -f $payFiles.Count, $renFiles.Count)
    Write-Output "file(s) are present in the same tree, e.g."
    Write-Output ("    {0}" -f $payFiles[0].Name)
    Write-Output ("    {0}" -f $renFiles[0].Name)
    Write-Output "A package present under BOTH a stable name and a tier-tagged name has TWO"
    Write-Output "live providers for every TGI it owns, and which one wins is filename order."
    Write-Output "No live/gated verdict taken here would mean anything. Finish the conversion"
    Write-Output "(_tests\Convert-ToPayloadLayout.ps1) or restore the rename layout, then re-run."
    exit 1
}
$layout = if ($payFiles.Count) { 'PAYLOAD' } elseif ($renFiles.Count) { 'RENAME' } else { 'NONE' }
Write-Output ("Arming layout on disk: {0}" -f $(switch ($layout) {
    'PAYLOAD' { "PAYLOAD (v4.5.0 content swap; $($payFiles.Count) .uipay, verdicts from z_SC4UIScale_STATE.txt)" }
    'RENAME'  { "RENAME (pre-4.5.0; $($renFiles.Count) tier-tagged/.x1-disabled file(s), verdicts from the filename)" }
    default   { "NONE - no package of ours found in $($OurDirs -join ', ')" }
}))

if ($layout -eq 'PAYLOAD') {
    # NULL IS NOT EVIDENCE. Under this layout the filename carries neither the
    # tier nor the gate verdict, so with no state file there is nothing to read
    # and every verdict below would be a guess dressed as a measurement.
    if ($armState.Count -eq 0) {
        Write-Output ""
        Write-Output "REFUSING: the payload layout is on disk but no z_SC4UIScale_STATE.txt"
        Write-Output "was found in any of our folders. That file is written by the DLL on"
        Write-Output "EVERY boot (ScaleTier.cpp: WriteArmState) and is the ONLY place the"
        Write-Output "armed tier and the gate verdict now exist - a directory listing carries"
        Write-Output "neither. The game has not been launched since the conversion, so this"
        Write-Output "test cannot say whether any package is live. Launch once, then re-run."
        exit 1
    }
    # A package recorded in TWO folders' state files is ambiguous by
    # construction - both rows claim the same leaf name.
    $dupe = @($armState | Group-Object Base | Where-Object { $_.Count -gt 1 })
    if ($dupe.Count) {
        Write-Output ""
        Write-Output ("REFUSING: {0} package base(s) appear in more than one z_SC4UIScale_STATE.txt" -f $dupe.Count)
        $dupe | ForEach-Object { Write-Output ("    {0}: {1}" -f $_.Name, (($_.Group | ForEach-Object { $_.Dir }) -join ' + ')) }
        Write-Output "The same leaf name is armed in two folders, so 'which one is live' has"
        Write-Output "two answers and both dats load. Remove the stale folder and re-run."
        exit 1
    }
    # POSITIVE CONTROL on the state file itself: ArmOne stamps the live file's
    # size and FILETIME into the row it writes, so a row can be checked against
    # the file it claims to describe. A mismatch means the state file is STALE
    # (a deploy copied dats after the last boot) or something rewrote the live
    # file behind the DLL - either way the tag in that row is not a fact about
    # what is on disk now, and this suite must not quote it.
    $stale = @()
    foreach ($r in $armState) {
        $liveFile = Join-Path $r.Dir ("{0}.dat" -f $r.Base)
        if (-not (Test-Path -LiteralPath $liveFile)) { $stale += ("{0} (no live .dat at all)" -f $r.Base); continue }
        $fi = Get-Item -LiteralPath $liveFile
        if ($fi.Length -ne $r.LiveSize -or $fi.LastWriteTimeUtc.ToFileTimeUtc() -ne $r.LiveTime) {
            $stale += ("{0} (state says {1} bytes @ {2}, disk has {3} bytes @ {4})" -f
                $r.Base, $r.LiveSize, $r.LiveTime, $fi.Length, $fi.LastWriteTimeUtc.ToFileTimeUtc())
        }
    }
    if ($stale.Count) {
        Write-Output ""
        Write-Output ("REFUSING: {0} of {1} z_SC4UIScale_STATE.txt row(s) do not describe the" -f $stale.Count, $armState.Count)
        Write-Output "live file they name:"
        $stale | Select-Object -First 8 | ForEach-Object { Write-Output "    $_" }
        Write-Output "The state file is stale (files were deployed after the last boot) or"
        Write-Output "something rewrote a live dat behind the DLL. Launch the game once so"
        Write-Output "CommitArming re-arms and rewrites the state, then re-run."
        exit 1
    }
    Write-Output ("z_SC4UIScale_STATE.txt: {0} row(s), every row's stamp matches its live .dat" -f $armState.Count)
}

# The DLL skips its own folder so a package cannot satisfy its own dependency.
$all = Get-ChildItem -LiteralPath $plugins -Recurse -File -ErrorAction SilentlyContinue |
       Where-Object { $_.FullName -notmatch '\\zzz-SC4UIScale\\' -and $_.FullName -notmatch '\\010-SC4UIScale\\' -and $_.FullName -notmatch '\\_dllstash\\' }

$failures = @()
foreach ($d in $deps) {
    $files = @([pscustomobject]@{ Name = $d.File1; Size = $d.Size1 })
    if ($d.File2) { $files += [pscustomobject]@{ Name = $d.File2; Size = $d.Size2 } }

    $allPresent = $true
    foreach ($f in $files) {
        $hit = if ($d.Prefix) { $all | Where-Object { $_.Name.StartsWith($f.Name, 'OrdinalIgnoreCase') } | Select-Object -First 1 }
               else            { $all | Where-Object { $_.Name -ieq $f.Name } | Select-Object -First 1 }
        if (-not $hit) {
            $allPresent = $false
            Write-Output ("  {0}: dep ABSENT ({1}) -> package must be GATED OFF" -f $d.Package, $f.Name)
            continue
        }
        if ($f.Size -ne 0 -and $hit.Length -ne $f.Size) {
            $allPresent = $false
            $failures += ("{0}: {1} is {2} bytes, gate expects {3} - our copy is STALE. Re-extract into thirdparty-src\ and rebuild, or update the fingerprint." -f $d.Package, $f.Name, $hit.Length, $f.Size)
        } else {
            Write-Output ("  {0}: dep ok ({1}{2})" -f $d.Package, $f.Name,
                          $(if ($f.Size -ne 0) { ", $($hit.Length) bytes" } else { ", presence only" }))
        }
    }

    # The package must be LIVE at SOME tier when the deps hold, and gated at
    # EVERY tier when they do not. Either state is correct - the WRONG pairing
    # is the bug.
    #
    # ⚠ THIS USED TO HARD-CODE "-2x.dat" (fixed 2026-08-06). It assumed 2x was
    # always the active tier, so the moment anyone ran 1.5x or 3x it reported
    # "deps hold but the package is GATED OFF" for every third-party override -
    # a false failure, on a machine where nothing was wrong. Caught the first
    # time a tier other than 2x was ever exercised end to end. A tier-blind
    # check in a project whose whole subject is tiers.
    #
    # ⛔ v4.5.0: SPLIT BY LAYOUT. Under RENAME the filename IS the verdict.
    # Under PAYLOAD the filename is a constant and the verdict lives only in
    # z_SC4UIScale_STATE.txt - see the header block. Neither branch may guess:
    # the payload branch has already refused above if the state file is absent
    # or stale.
    $tiers = @("15x", "2x", "3x")
    $liveAt = @()
    $anyPresent = $false
    $gateReason = $null

    if ($layout -eq 'PAYLOAD') {
        # base is the LEAF: SyncDat strips the folder before recording.
        $leaf = Split-Path $d.Package -Leaf
        $row  = $armState | Where-Object { $_.Base -ieq $leaf } | Select-Object -First 1
        # "present at all" = a live file OR any payload for this base. A row in
        # the state file is NOT presence evidence on its own - it survives a
        # boot in which the package was deleted.
        $anyPresent = @($ourFiles | Where-Object {
            $_.Name -ieq "$leaf.dat" -or $_.Name -like "$leaf.*.uipay" }).Count -gt 0
        if ($row) {
            $gateReason = $row.Reason
            if ($row.Tag -ne 'off') { $liveAt += $row.Tag }
        } elseif ($anyPresent) {
            # Files on disk that the DLL never recorded: it did not arm this
            # package this boot, so its live .dat holds whatever the last
            # writer left - unknown, not "off". State that, do not average it.
            $failures += ("{0}: present on disk but ABSENT from z_SC4UIScale_STATE.txt - the DLL did not arm it this boot, so the bytes in its live .dat are whatever the last writer left. Unknown, not inert." -f $d.Package)
        }
    } else {
        foreach ($t in $tiers) {
            $p = Join-Path $plugins ("{0}-{1}.dat" -f $d.Package, $t)
            if (Test-Path $p) { $liveAt += $t; $anyPresent = $true }
            elseif (Test-Path "$p.x1-disabled") { $anyPresent = $true }
        }
    }
    $isLive = $liveAt.Count -gt 0
    if ($isLive) {
        Write-Output ("  {0}: live at tier {1}{2}" -f $d.Package, ($liveAt -join ","),
                      $(if ($gateReason) { " [$gateReason]" } else { "" }))
    } elseif ($layout -eq 'PAYLOAD' -and $gateReason) {
        Write-Output ("  {0}: inert (.off content) [{1}]" -f $d.Package, $gateReason)
    }
    if (-not $anyPresent) {
        # ZCarbon* IS ABSENT BY DESIGN ON A NORMAL INSTALL (2026-08-25). Those
        # packages are built from another author's skin, so the release bundle
        # deliberately ships none of them (Build-Dist throws if one gets in) -
        # a player, and a cold clone, legitimately has zero of these files.
        # Failing here made the SHIPPED state red, which is how a suite teaches
        # people to ignore it. Same presence-gate shape as Test-Builders.ps1
        # and the deploy's own ZCarbon block.
        if ($d.Package -match 'z_SC4UIScale_ZCarbon') {
            Write-Output ("  {0}: not built on this machine - skipped (carbon packages are local-only by design)." -f $d.Package)
        } else {
            $failures += ("{0}: no tier of this package is present at all - package missing entirely." -f $d.Package)
        }
    } elseif ($liveAt.Count -gt 1) {
        # RENAME LAYOUT ONLY - structurally impossible under PAYLOAD, where one
        # package has exactly one live filename. Kept because that layout is
        # still what the developer's own Plugins tree carries.
        # Two tiers of one package loading together is a real defect: they both
        # supply the same TGIs and the winner is filename order, not intent.
        $failures += ("{0}: LIVE AT {1} TIERS AT ONCE ({2}) - both load, and which one wins is decided by filename order rather than by the tier decision." -f $d.Package, $liveAt.Count, ($liveAt -join ","))
    } elseif ($allPresent -and -not $isLive) {
        $failures += ("{0}: deps hold but the package is GATED OFF - the override is not applying." -f $d.Package)
    } elseif (-not $allPresent -and $isLive) {
        $failures += ("{0}: deps DO NOT hold but the package is LIVE - our frozen copy of another mod's UI is still winning. This is the exact failure the gate exists to prevent (it self-heals on the next launch; if it does not, the gate is broken)." -f $d.Package)
    }
}

if ($failures.Count) {
    Write-Output ""
    $failures | ForEach-Object { Write-Output ("FAIL: " + $_) }
    exit 1
}
Write-Output ("ALL PASS ({0} gates: deps resolve, fingerprints match, live/gated state agrees) - layout {1}" -f $deps.Count, $layout)
if ($layout -eq 'PAYLOAD') {
    Write-Output "The live/gated half of that verdict came from z_SC4UIScale_STATE.txt,"
    Write-Output "not from a filename - under the v4.5.0 content swap the filename is a"
    Write-Output "constant and carries no verdict at all."
}
exit 0
