# Bootstrap-Corpus.ps1 - turn a cold clone into a buildable tree.
#
# WHY THIS EXISTS. On 2026-08-18 a cold-clone test ran all eight package
# builders from a fresh checkout. Three failed on missing INPUTS, not missing
# code: build_selective_safe.py hard-read tools\dbpf\extracted-png-tgi.csv,
# build_dialog_static.py hard-read tools\uiscripts\extracted\ and
# tools\dialog-static\thirdparty-src\. None of the three is committed - all
# three are DERIVED from the player's own game install and mods, and correctly
# so. The defect was that nothing derived them and no error said how.
# Presence verification had passed on all eight builders; only EXECUTION found
# it.
#
# This script is that missing step. It is idempotent: re-running skips work
# already on disk unless -Force.
#
# ART POLICY. Nothing this produces belongs in the repo. Every output here is
# derived from files the player already owns. See RUNBOOK.md section 1.

[CmdletBinding()]
param(
    [string]$GameDir,
    [string]$PluginsDir,
    [switch]$Force,
    [switch]$SkipArchives     # only re-derive the csv, .ui corpus and mod sources
)

$ErrorActionPreference = "Stop"
$TOOLS   = $PSScriptRoot
$DBPF    = Join-Path $TOOLS "dbpf"
$EXTRACT = Join-Path $DBPF "extracted"
$UIOUT   = Join-Path $TOOLS "uiscripts\extracted"
$TPDIR   = Join-Path $TOOLS "dialog-static\thirdparty-src"
$EXE     = Join-Path $DBPF "DbpfExtract.exe"
$BSLASH  = [char]92

# ---- 0. locate the game -------------------------------------------------
if (-not $GameDir) { $GameDir = $env:SC4_GAME_DIR }
if (-not $GameDir) {
    $GameDir = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
}
if (-not (Test-Path $GameDir)) {
    throw "Game directory not found: $GameDir`nPass -GameDir <path> or set SC4_GAME_DIR."
}

if (-not (Test-Path $EXE)) {
    $csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if (-not (Test-Path $csc)) {
        throw "DbpfExtract.exe missing and csc.exe not found. See RUNBOOK.md section 0."
    }
    Write-Output "Building DbpfExtract.exe ..."
    # csc treats a leading / as an OPTION prefix, so a forward-slash source
    # path fails with "file not found". Windows backslash paths only.
    & $csc /nologo /optimize+ /platform:anycpu ("/out:" + $EXE) (Join-Path $DBPF "DbpfExtract.cs")
    if ($LASTEXITCODE -ne 0) { throw "csc failed building DbpfExtract.exe" }
}

# ---- 1. extract every archive the install actually has ------------------
# DISCOVERED, never listed. A written-down inventory of SC4's archives has
# silently missed one before (the intro dat), and it fails only in the case
# you needed it.
$archives = @(Get-ChildItem -Path $GameDir -Recurse -File -Include *.dat, *.DAT -ErrorAction SilentlyContinue |
              Sort-Object FullName)
if ($archives.Count -eq 0) { throw "No .dat archives found under $GameDir" }
Write-Output ("Archives discovered: {0}" -f $archives.Count)

if (-not $SkipArchives) {
    foreach ($a in $archives) {
        # Sku_Data ships the same plugin twice under two locale folders; key the
        # output dir on the RELATIVE path so the second cannot clobber the first.
        $rel  = $a.FullName.Substring($GameDir.TrimEnd($BSLASH).Length + 1)
        $name = ($rel -replace '[\\/]', '_') -replace '\.[Dd][Aa][Tt]$', ''
        $out  = Join-Path $EXTRACT $name
        $manifest = Join-Path $out "extract-manifest.csv"
        if ((Test-Path $manifest) -and -not $Force) {
            Write-Output ("  skip  {0} (already extracted)" -f $name)
            continue
        }
        New-Item -ItemType Directory -Force -Path $out | Out-Null
        & $EXE $a.FullName $out | Out-Null
        if ($LASTEXITCODE -ne 0) { throw ("DbpfExtract failed on " + $a.FullName) }
        if (-not (Test-Path $manifest)) { throw ("No manifest written for " + $name) }
        $n = (@(Get-Content $manifest).Count - 1)
        Write-Output ("  ok    {0}  ({1} entries)" -f $name, $n)
    }
}

# ---- 2. derive extracted-png-tgi.csv ------------------------------------
# It is a straight copy of the manifest of whichever archive carries the PNG
# store. WHICH archive is MEASURED (most PngMagic=yes rows), not assumed -
# today that is SimCity_1, and that is a fact about this build, not a law.
$csvOut = Join-Path $DBPF "extracted-png-tgi.csv"
if ((Test-Path $csvOut) -and -not $Force) {
    Write-Output "extracted-png-tgi.csv: present"
} else {
    $best = $null; $bestN = -1
    foreach ($m in @(Get-ChildItem -Path $EXTRACT -Recurse -Filter extract-manifest.csv -ErrorAction SilentlyContinue)) {
        $n = @(Select-String -Path $m.FullName -Pattern ',yes,[^,]*$' -AllMatches).Count
        if ($n -gt $bestN) { $bestN = $n; $best = $m.FullName }
    }
    if (-not $best) {
        throw "No extract-manifest.csv found under $EXTRACT - run without -SkipArchives first."
    }
    if ($bestN -le 0) {
        # A null is a REFUSAL, not a pass. Copying an extraction with no
        # PNG-magic rows forward hands every collision check an empty set that
        # then passes vacuously.
        throw "No archive manifest carries any PngMagic=yes rows. The extraction is wrong, not the csv."
    }
    Copy-Item $best $csvOut -Force
    Write-Output ("extracted-png-tgi.csv <- {0}  ({1} PNG-magic entries)" -f
                  (Split-Path -Leaf (Split-Path -Parent $best)), $bestN)
}

# ---- 3. derive the .UI layout corpus ------------------------------------
# Type 0x00000000 entries. DbpfExtract names every output .png regardless of
# type (it writes raw decompressed bytes); the layout parsers want .ui.
$have = 0
if (Test-Path $UIOUT) {
    $have = @(Get-ChildItem -Path $UIOUT -Filter *.ui -ErrorAction SilentlyContinue).Count
}
if ($have -gt 0 -and -not $Force) {
    Write-Output ("uiscripts\extracted: {0} .ui files present" -f $have)
} else {
    New-Item -ItemType Directory -Force -Path $UIOUT | Out-Null
    foreach ($a in $archives) {
        & $EXE $a.FullName $UIOUT "0x00000000" | Out-Null
    }
    foreach ($p in @(Get-ChildItem -Path $UIOUT -Filter "T-00000000_*.png" -ErrorAction SilentlyContinue)) {
        Move-Item $p.FullName (Join-Path $UIOUT ([IO.Path]::ChangeExtension($p.Name, ".ui"))) -Force
    }
    $have = @(Get-ChildItem -Path $UIOUT -Filter *.ui).Count
    if ($have -eq 0) {
        throw "No type-0 entries extracted - the .UI corpus is empty and every layout builder will refuse."
    }
    Write-Output ("uiscripts\extracted: {0} .ui files" -f $have)
}

# ---- 4. positive control ------------------------------------------------
# A null here is a REFUSAL, not a pass. The two groups the layout builders
# actually read must be non-empty, or the next step fails 300 lines later with
# a confusing message about entry counts.
foreach ($g in @("96a006b0", "08000600")) {
    $n = @(Get-ChildItem -Path $UIOUT -Filter ("T-00000000_G-" + $g + "_I-*.ui") -ErrorAction SilentlyContinue).Count
    if ($n -eq 0) {
        throw ("UI group " + $g + " extracted 0 files. The layout builders read this group by name; an empty group is a silent no-op downstream, not a clean run.")
    }
    Write-Output ("  group {0}: {1} layouts" -f $g, $n)
}

# ---- 5. third-party .UI override sources --------------------------------
# build_dialog_static.py rebuilds another mod's OWN dialogs, and must read THAT
# MOD's script, never the stock twin - doubling the stock twin silently reverts
# the mod's function. That was the whole of the five-day "the game bypasses
# static doubling" misdiagnosis; see thirdparty-src\README.md, which IS in the
# repo even though the .ui files it describes are not.
#
# ORDER MATTERS: Plugins root loads BEFORE subfolders, so a subfolder dat WINS.
# Extract root-first and let deeper extracts overwrite - last writer wins, and
# that is the load-order winner.
#
# EXCLUDE OUR OWN PACKAGES. Our deployed dats carry .UI scripts too and they
# outrank the mod in the same computation; letting them in makes the build read
# its own previous output as if it were the mod's source. MEASURED 2026-08-18:
# with our packages installed, winning_corpus.py reports "won by a THIRD PARTY:
# 0" and the confounder is completely invisible.
# The plugin dat list is computed ONCE here and used by both section 5 and
# section 6. It used to live inside 5's else-branch, which meant that once the
# .ui files existed the list was empty and section 6 silently did nothing -
# the exact shape of "a gate that only asks about work you started".
# BOTH plugin trees, in load order: the INSTALL-side <game>\Plugins first,
# then the user's Documents tree, which wins. A "stock" or "complete" claim
# that only enumerated one of the two has been wrong here before.
$trees = @()
if ($PluginsDir) {
    $trees += $PluginsDir
} else {
    if ($env:SC4_PLUGINS) { $trees += $env:SC4_PLUGINS }
    $trees += (Join-Path $GameDir "Plugins")
    # Parse sc4paths.py's own report rather than passing python a -c string:
    # Windows PowerShell mangles embedded quotes in a native-exe argument, and
    # that failure is SILENT - it returns nothing, the tree is skipped, and the
    # build refuses 200 lines later for the wrong reason. Measured 2026-08-18.
    try {
        $rep = @(& python (Join-Path $TOOLS "sc4paths.py") 2>$null)
        foreach ($line in $rep) {
            if ($line -match '^plugins_dir\(\)\s+(\S.*)$') { $trees += $Matches[1].Trim() }
        }
    } catch { }
}
$trees = @($trees | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique)

$ordered = @()
foreach ($tree in $trees) {
    Write-Output ("  plugin tree: {0}" -f $tree)
    # The Plugins scan is RECURSIVE: a dat parked in a subfolder is fully live,
    # and a stash INSIDE Plugins\ disables nothing.
    $pdats = @(Get-ChildItem -Path $tree -Recurse -File -Include *.dat, *.DAT -ErrorAction SilentlyContinue |
               Where-Object { $_.Name -notlike "z_SC4UIScale_*" -and $_.FullName -notlike "*zzz-SC4UIScale*" })
    $root = $tree.TrimEnd($BSLASH)
    $ordered += @($pdats | Sort-Object @{Expression = { $_.FullName.Substring($root.Length).Split($BSLASH).Count }}, FullName)
}
Write-Output ("Plugins dats scanned (ours excluded): {0}" -f $ordered.Count)

$needTp = $true
if (Test-Path $TPDIR) {
    $needTp = (@(Get-ChildItem -Path $TPDIR -Filter *.ui -ErrorAction SilentlyContinue).Count -eq 0)
}
if ($Force) { $needTp = $true }

if (-not $needTp) {
    Write-Output ("dialog-static\thirdparty-src: {0} .ui files present" -f
                  @(Get-ChildItem -Path $TPDIR -Filter *.ui).Count)
} else {
    if ($ordered.Count -eq 0) {
        Write-Warning "No Plugins folder found - SKIPPING third-party sources. build_dialog_static.py will refuse until they exist. Pass -PluginsDir, set SC4_PLUGINS, or see dialog-static\thirdparty-src\README.md."
    } else {
        New-Item -ItemType Directory -Force -Path $TPDIR | Out-Null
        foreach ($d in $ordered) {
            & $EXE $d.FullName $TPDIR "0x00000000" | Out-Null
        }
        foreach ($pn in @(Get-ChildItem -Path $TPDIR -Filter "T-00000000_*.png" -ErrorAction SilentlyContinue)) {
            Move-Item $pn.FullName (Join-Path $TPDIR ([IO.Path]::ChangeExtension($pn.Name, ".ui"))) -Force
        }
        Remove-Item (Join-Path $TPDIR "extract-manifest.csv") -Force -ErrorAction SilentlyContinue
        $tpn = @(Get-ChildItem -Path $TPDIR -Filter *.ui -ErrorAction SilentlyContinue).Count
        Write-Output ("dialog-static\thirdparty-src: {0} .ui files" -f $tpn)
        if ($tpn -eq 0) {
            Write-Warning "0 third-party .UI scripts found. If no installed mod overrides a dialog that is correct - but build_dialog_static.py names every target it needs and will refuse by name."
        }
    }
}

# ---- 6. third-party BITMAPS ---------------------------------------------
# CAM ships its own art for its own dialogs, and blttype=normal art is drawn
# at its native size and CLIPPED, never stretched - so a 1x strip in a 1.5x row
# covers two thirds of it and nothing goes red. Those bitmaps are the mod's,
# not ours, so they are derived here rather than committed.
#
# WHICH bitmaps is asked of the builder (--emit-inputs reads its own
# TP_ART_PACKAGE), never written down here. A hand-copied list of thirteen
# names in this file would be exactly the rotting inventory the project has
# been burned by; the builder is the single source and it also refuses any
# staged file it did not ask for.
$TPART = Join-Path $TOOLS "dialog-static\thirdparty-art"
$needArt = $true
if (Test-Path $TPART) {
    $needArt = (@(Get-ChildItem -Path $TPART -Filter *.png -ErrorAction SilentlyContinue).Count -eq 0)
}
if ($Force) { $needArt = $true }

if (-not $needArt) {
    Write-Output ("dialog-static\thirdparty-art: {0} bitmap(s) present" -f
                  @(Get-ChildItem -Path $TPART -Filter *.png).Count)
} elseif ($ordered -and $ordered.Count -gt 0) {
    $wanted = @(& python (Join-Path $TOOLS "dialog-static\build_dialog_static.py") --emit-inputs 2>$null |
                Where-Object { $_ -match '^T-856ddbac_' })
    if ($wanted.Count -eq 0) {
        Write-Warning "build_dialog_static.py --emit-inputs returned nothing - skipping third-party bitmaps. That is a REFUSAL, not a clean pass: check the builder runs at all."
    } else {
        $stage = Join-Path $TOOLS "dialog-static\_tpart-stage"
        if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
        New-Item -ItemType Directory -Force -Path $stage | Out-Null
        foreach ($d in $ordered) {
            & $EXE $d.FullName $stage "0x856DDBAC" | Out-Null
        }
        New-Item -ItemType Directory -Force -Path $TPART | Out-Null
        $got = 0
        foreach ($w in $wanted) {
            $src = Join-Path $stage $w
            if (Test-Path $src) { Copy-Item $src (Join-Path $TPART $w) -Force; $got++ }
        }
        Remove-Item $stage -Recurse -Force
        Write-Output ("dialog-static\thirdparty-art: {0}/{1} bitmap(s) recovered" -f $got, $wanted.Count)
        if ($got -lt $wanted.Count) {
            Write-Warning "Some mod bitmaps were not found in the installed Plugins tree. The builder names each missing TGI and will refuse - install the owning mod, or the dialog it belongs to is not one you can rebuild here."
        }
    }
}

Write-Output ""
Write-Output "BOOTSTRAP OK - now run upscale\Rebuild-Corpus.ps1, then the builders (packages\PACKAGES.md)."
