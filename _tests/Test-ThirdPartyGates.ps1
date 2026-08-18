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
$ErrorActionPreference = "Stop"
$proj = Split-Path $PSScriptRoot -Parent
$plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$src = Join-Path $proj "src\ScaleTier.cpp"

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

# The DLL skips its own folder so a package cannot satisfy its own dependency.
$all = Get-ChildItem -LiteralPath $plugins -Recurse -File -ErrorAction SilentlyContinue |
       Where-Object { $_.FullName -notmatch '\\zzz-SC4UIScale\\' -and $_.FullName -notmatch '\\_dllstash\\' }

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
    $tiers = @("15x", "2x", "3x")
    $liveAt = @()
    $anyPresent = $false
    foreach ($t in $tiers) {
        $p = Join-Path $plugins ("{0}-{1}.dat" -f $d.Package, $t)
        if (Test-Path $p) { $liveAt += $t; $anyPresent = $true }
        elseif (Test-Path "$p.x1-disabled") { $anyPresent = $true }
    }
    $isLive = $liveAt.Count -gt 0
    if ($isLive) {
        Write-Output ("  {0}: live at tier {1}" -f $d.Package, ($liveAt -join ","))
    }
    if (-not $anyPresent) {
        $failures += ("{0}: no tier of this package is present at all - package missing entirely." -f $d.Package)
    } elseif ($liveAt.Count -gt 1) {
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
Write-Output ("ALL PASS ({0} gates: deps resolve, fingerprints match, live/gated state agrees)" -f $deps.Count)
exit 0
