# Install and uninstall this mod THE WAY A USER WOULD - through sc4pac.
#
# WHY THIS EXISTS. The sc4pac readiness claim was tested once, on 2026-08-29,
# by an agent working ad-hoc in a temp directory. The findings were written into
# _tests/REGRESSION.md and the tooling was thrown away. That is prose, not a
# test: nothing in this repo could re-run it, and the sc4pac CLI was not even
# present on the machine afterwards. Every number in that record was therefore
# unfalsifiable the moment it was written.
#
# WHAT IT DOES NOT DO, AND WHY THAT MATTERS. This script proves WHERE BYTES
# LAND. It does not prove the mod WORKS. SC4 is never started here, so the
# arming pass, the dependency gates and tier switching are all unexercised by
# a green run. Use -LaunchReady to build a user directory you can actually
# start the game against; that is the only thing that closes the gap.
#
#   .\_tests\Test-Sc4pacInstall.ps1                  scratch install + uninstall
#   .\_tests\Test-Sc4pacInstall.ps1 -LaunchReady     leave a launchable UserDir
#   .\_tests\Test-Sc4pacInstall.ps1 -Migrated        canonical sc4pac folder layout
[CmdletBinding()]
param(
    # The CLI ships inside the sc4pac GUI download. Parameterised rather than
    # vendored: it is 74 MB and it is not ours to redistribute.
    [string]$Cli = 'C:\Users\<user>\Downloads\sc4pac-gui-windows-x64 (1)\cli\sc4pac-cli.jar',
    [string]$Root = 'C:\dev\_sc4pac-test\run',
    # The download cache is deliberately OUTSIDE $Root so a re-run does not
    # re-fetch the 118 MB release asset. Deleting it is safe, just slow.
    [string]$Cache = 'C:\dev\_sc4pac-test\cache',
    [string]$Yaml,
    # A channel built by a PREVIOUS elevated run. `sc4pac channel build` creates a
    # `latest -> <version>` SYMLINK, and on this machine symlink creation needs
    # elevation (MEASURED: New-Item -ItemType SymbolicLink returns "Administrator
    # privilege required"; a junction succeeds, so it is the symlink specifically).
    # Build it once elevated, then every later run reuses it unelevated.
    # This constrains the HARNESS only - a real user fetches the published channel
    # over https and never builds one.
    [string]$Channel,
    [ValidateSet('Windows-digital', 'Windows-disc', 'macOS')]
    [string]$Edition = 'Windows-digital',
    # Copy the live tree's letter-named top-level folders (BSC, CSX, ...) in, so
    # the hybrid-install ordering exposure is REPRODUCED rather than assumed
    # away. -Migrated instead builds the canonical layout sc4pac documents.
    [switch]$Migrated,
    [switch]$LaunchReady,
    [switch]$KeepTree
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if (-not $Yaml) { $Yaml = Join-Path $repo '_packaging\sc4pac\drexel-sc4-ui-scale.yaml' }

$fail = @()
$note = @()
function Fail($m) { $script:fail += $m }
function Note($m) { $script:note += $m; Write-Output "  note: $m" }

# ---- PRE-FLIGHT --------------------------------------------------------------
Write-Output 'PRE-FLIGHT'
if (-not (Test-Path $Cli)) {
    Write-Output "REFUSING: no sc4pac CLI at"
    Write-Output "  $Cli"
    Write-Output 'It ships inside the sc4pac GUI download (the cli\ subfolder):'
    Write-Output '  https://github.com/memo33/sc4pac-gui/releases/latest'
    Write-Output 'Pass its path with -Cli.'
    exit 2
}
if (-not (Test-Path $Yaml)) { throw "no package yaml at $Yaml" }

$java = (Get-Command java -ErrorAction SilentlyContinue)
if (-not $java) { Write-Output 'REFUSING: java 17+ is required and is not on PATH.'; exit 2 }

$cliVer = (& java -jar $Cli --version | Select-Object -First 1).Trim()
Write-Output "  sc4pac CLI $cliVer"
# NOTE: `java -version` prints to STDERR. Do NOT redirect it - PowerShell 5.1
# wraps a native command's redirected stderr in an ErrorRecord and, with
# ErrorActionPreference=Stop, that ABORTS THE SCRIPT at exit code 0. Read the
# version out of the jar's own runtime instead, which writes to stdout.
Write-Output "  java       $([Diagnostics.FileVersionInfo]::GetVersionInfo($java.Source).ProductVersion)"

# The yaml is generated; a placeholder hash means someone ran the generator
# without a real bundle and every checksum assertion below would be vacuous.
$yamlText = Get-Content $Yaml -Raw
$hashCount = ([regex]'sha256: "').Matches($yamlText).Count
$zeroCount = ([regex]'sha256: "0{64}"').Matches($yamlText).Count
Write-Output "  package yaml: $hashCount sha256 entries, $zeroCount placeholders"
if ($hashCount -lt 50) { Fail "only $hashCount sha256 entries in the yaml - expected ~85" }
if ($zeroCount -gt 0)  { Fail "$zeroCount placeholder sha256 entries - the checksum test would be vacuous" }
if ($fail.Count) { Write-Output 'REFUSING:'; $fail | ForEach-Object { Write-Output "  - $_" }; exit 1 }

# ---- LAY OUT THE SCRATCH TREE ------------------------------------------------
Write-Output ''
Write-Output 'SETUP'
if (Test-Path $Root) { Remove-Item -LiteralPath $Root -Recurse -Force }
$plugins = Join-Path $Root 'Plugins'
# The yaml staging dir lives BESIDE the cache, not inside $Root: $Root is wiped
# at the top of every run, and the elevated-rebuild command this script prints
# has to still be runnable by the time anyone reads it.
$yamlSrc = Join-Path (Split-Path -Parent $Cache) 'yaml'
$yamlDir = Join-Path $yamlSrc 'a-drexel'
$chanDir = Join-Path $Root 'channel'
if (Test-Path $yamlSrc) { Remove-Item -LiteralPath $yamlSrc -Recurse -Force }
New-Item -ItemType Directory $plugins, $yamlDir, $chanDir, $Cache, (Join-Path $Root 'temp') -Force | Out-Null
Copy-Item $Yaml (Join-Path $yamlDir 'sc4-ui-scale.yaml') -Force

# Reproduce the ORDERING EXPOSURE rather than testing a tree that cannot show
# it. Letters sort after digits, so a letter-named top-level folder out-sorts
# 900-overrides, which is where sc4pac puts our override package. The live tree
# has three such folders; a scratch tree with none would pass for the wrong
# reason.
$live = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins'
if ($Migrated) {
    New-Item -ItemType Directory (Join-Path $plugins '075-my-plugins'), (Join-Path $plugins '895-my-overrides') -Force | Out-Null
    Note 'MIGRATED layout: manual content would live in 075-my-plugins / 895-my-overrides, both of which our packages out-sort correctly.'
} else {
    $letterDirs = @()
    if (Test-Path $live) {
        $letterDirs = @(Get-ChildItem $live -Directory | Where-Object { $_.Name -notmatch '^[0-9]' -and $_.Name -notlike 'zzz-SC4UIScale' })
    }
    foreach ($d in $letterDirs) {
        New-Item -ItemType Directory (Join-Path $plugins $d.Name) -Force | Out-Null
    }
    if ($letterDirs.Count) {
        Note ("HYBRID layout: $($letterDirs.Count) letter-named folder(s) recreated (" +
              (($letterDirs | ForEach-Object Name) -join ', ') +
              ") - each out-sorts 900-overrides and can steal keys from our override package.")
    } else {
        Note 'HYBRID layout requested but the live tree has no letter-named folders to copy - the ordering exposure is NOT reproduced in this run.'
    }
}

# ---- BUILD THE CHANNEL -------------------------------------------------------
Write-Output ''
Write-Output 'CHANNEL BUILD'
$prebuilt = Join-Path (Split-Path -Parent $Cache) 'channel'
$elevated = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if ($Channel) {
    if (-not (Test-Path (Join-Path $Channel 'sc4pac-channel-contents.json'))) {
        throw "-Channel '$Channel' does not look like a built channel (no sc4pac-channel-contents.json)"
    }
    # Reuse means the yaml on disk may be NEWER than the channel that was built
    # from it, which would silently test a stale package. Refuse rather than warn.
    $chanStamp = (Get-Item (Join-Path $Channel 'sc4pac-channel-contents.json')).LastWriteTimeUtc
    $yamlStamp = (Get-Item $Yaml).LastWriteTimeUtc
    if ($yamlStamp -gt $chanStamp) {
        throw ("the package yaml is NEWER than the prebuilt channel " +
               "($($yamlStamp.ToString('s')) vs $($chanStamp.ToString('s'))) - " +
               "rebuild it elevated or this run would test stale metadata")
    }
    $chanDir = $Channel
    Write-Output "  reusing the prebuilt channel at $Channel"
} else {
    if ($elevated) { $chanDir = $prebuilt; if (Test-Path $prebuilt) { Remove-Item -LiteralPath $prebuilt -Recurse -Force } }
    & java -jar $Cli channel build --label 'SC4UIScale local test' -o $chanDir $yamlSrc
    if ($LASTEXITCODE -ne 0) {
        Write-Output ''
        Write-Output 'CHANNEL BUILD FAILED.'
        if (-not $elevated) {
            Write-Output 'This shell is NOT elevated, and channel build creates a symlink'
            Write-Output '("latest" -> the version folder) which needs the privilege. Build it'
            Write-Output 'ONCE from an administrator PowerShell:'
            Write-Output ''
            Write-Output "  java -jar '$Cli' channel build -o '$prebuilt' '$yamlSrc'"
            Write-Output ''
            Write-Output 'then re-run this script unelevated with:'
            Write-Output ''
            Write-Output "  .\_tests\Test-Sc4pacInstall.ps1 -Channel '$prebuilt'"
            Write-Output ''
            Write-Output 'NOTE: this is a limitation of building a channel LOCALLY. Real users'
            Write-Output 'fetch the published channel over https and never hit it.'
        }
        throw "channel build FAILED (exit $LASTEXITCODE)"
    }
}
$json = @(Get-ChildItem $chanDir -Recurse -File -Filter '*.json')
Write-Output "  $($json.Count) json file(s) present"
if ($json.Count -lt 2) { throw "channel has $($json.Count) json file(s) - expected the two packages plus an index" }

# ---- PROFILE -----------------------------------------------------------------
# Schema measured against the 0.10.0 jar, not read from docs: the CLI rejects
# a flat object and names the missing keys one at a time until this shape.
$chanUrl = ([uri](Join-Path $chanDir '')).AbsoluteUri
$profileJson = @{
    config = @{
        pluginsRoot = $plugins
        cacheRoot   = $Cache
        tempRoot    = (Join-Path $Root 'temp')
        # sc4pac asks which SC4 edition you have and REFUSES to proceed in a
        # non-interactive shell without an answer ("Operation aborted as
        # terminal is non-interactive"). -y does not cover variant selection.
        # This machine runs the Steam build, which is the digital edition.
        variant     = @{ 'config:sc4-edition:edition' = $Edition }
        # OUR channel first, then the official one. The official channel is not
        # optional: sc4pac resolves shared config packages such as
        # `config:sc4-edition-windows-digital` from it, and without it the
        # install aborts with "Some packages could not be resolved" before a
        # single file is written. A local-channel-only test would have been
        # testing a situation no user is ever in.
        channels    = @($chanUrl, 'https://memo33.github.io/sc4pac/channel/')
    }
    explicit = @()
} | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText((Join-Path $Root 'sc4pac-plugins.json'), $profileJson, (New-Object Text.UTF8Encoding($false)))

# ---- INSTALL -----------------------------------------------------------------
Write-Output ''
Write-Output 'INSTALL'
Push-Location $Root
try {
    & java -jar $Cli add a-drexel:sc4-ui-scale a-drexel:sc4-ui-scale-mod-overrides
    if ($LASTEXITCODE -ne 0) { throw "sc4pac add FAILED (exit $LASTEXITCODE)" }

    & java -jar $Cli update -y
    if ($LASTEXITCODE -ne 0) { throw "sc4pac update FAILED (exit $LASTEXITCODE) - the install did not complete" }
} finally { Pop-Location }

# ---- ASSERTIONS --------------------------------------------------------------
Write-Output ''
Write-Output 'INSTALLED LAYOUT'
$installed = @(Get-ChildItem $plugins -Recurse -File)
Write-Output "  $($installed.Count) file(s) installed"

# POSITIVE CONTROL for every "zero X" below: the install must have produced a
# non-trivial number of files. A zero-orphan claim over an empty tree is not a
# result, and this is the check that makes the later zeros mean something.
if ($installed.Count -lt 50) {
    Fail "only $($installed.Count) file(s) installed - every 'zero' assertion below would be vacuous"
}

$rootFiles = @(Get-ChildItem $plugins -File)
Write-Output "  root files: $(if ($rootFiles.Count) { ($rootFiles | ForEach-Object Name) -join ', ' } else { '(none)' })"
$rootDll = @($rootFiles | Where-Object { $_.Extension -eq '.dll' })
if ($rootDll.Count -ne 1) { Fail "expected exactly 1 DLL at the Plugins root, found $($rootDll.Count) - SC4's DLL loader is top-level only" }
elseif ($rootDll[0].Name -ne 'SC4UIScale.dll') { Fail "root DLL is $($rootDll[0].Name), expected SC4UIScale.dll" }
$rootOther = @($rootFiles | Where-Object { $_.Extension -ne '.dll' })
if ($rootOther.Count) { Fail "$($rootOther.Count) non-DLL file(s) at the Plugins root: $(($rootOther | ForEach-Object Name) -join ', ')" }

$newIni = @(Get-ChildItem $plugins -Recurse -File -Filter '*_sc4pacnew.ini')
if ($newIni.Count) { Fail "$($newIni.Count) *_sc4pacnew.ini file(s) - isIni landed an inert ini we would never activate" }

$allPkgDirs = @(Get-ChildItem $plugins -Recurse -Directory | Where-Object { $_.Name -like '*.sc4pac' })
# OURS only. sc4pac pulls in config:sc4-edition and its edition-specific
# sibling as real dependencies, so a bare count of *.sc4pac folders is a count
# of the whole dependency graph, not of us.
$pkgDirs = @($allPkgDirs | Where-Object { $_.Name -like 'a-drexel.*' })
Write-Output "  package folders:"
foreach ($d in $allPkgDirs) {
    $rel = $d.FullName.Substring($plugins.Length).TrimStart('\')
    $n = @(Get-ChildItem $d.FullName -Recurse -File).Count
    $mine = if ($d.Name -like 'a-drexel.*') { 'OURS' } else { 'dependency' }
    Write-Output "    $rel  ($n files, $mine)"
}
if ($pkgDirs.Count -ne 2) { Fail "expected 2 packages of ours, found $($pkgDirs.Count) (of $($allPkgDirs.Count) total)" }

# THE FLATTENING. sc4pac strips the longest common directory prefix, so our two
# packages do NOT land the same shape: the early one keeps 010-SC4UIScale\, the
# override one has zzz-SC4UIScale\ stripped away entirely. The DLL finds its
# folders by CONTENT for exactly this reason - so record what the DLL will
# actually have to classify, and make it visible rather than assumed.
Write-Output ''
Write-Output 'WHAT THE DLL WILL HAVE TO DISCOVER'
foreach ($d in $pkgDirs) {
    $rel = $d.FullName.Substring($plugins.Length).TrimStart('\')
    $sub = @(Get-ChildItem $d.FullName -Directory)
    $dats = @(Get-ChildItem $d.FullName -Recurse -File -Filter 'z_SC4UIScale_*.dat')
    $pays = @(Get-ChildItem $d.FullName -Recurse -File -Filter 'z_SC4UIScale_*.uipay')
    $shape = if ($sub.Count) { "keeps subfolder(s): $(($sub | ForEach-Object Name) -join ', ')" } else { 'FLATTENED - files sit directly in the package folder' }
    Write-Output "    $rel"
    Write-Output "      $shape"
    Write-Output "      $($dats.Count) live .dat, $($pays.Count) payload(s)"
}

$allPay = @(Get-ChildItem $plugins -Recurse -File -Filter '*.uipay')
$allDat = @(Get-ChildItem $plugins -Recurse -File -Filter 'z_SC4UIScale_*.dat')
Write-Output ""
Write-Output "  total: $($allDat.Count) live .dat, $($allPay.Count) payload(s)"
if ($allPay.Count -lt 40) { Fail "only $($allPay.Count) payloads installed - a non-canonical extension installs ONLY via withChecksum; some entries are include-only" }
if ($allDat.Count -lt 10) { Fail "only $($allDat.Count) live .dat installed" }

# Every live dat must be a real DBPF: sc4pac parses them and aborts on a bad
# one, so a survivor here is also evidence the archive itself is well-formed.
$notDbpf = @()
foreach ($f in $allDat) {
    $fs = [IO.File]::OpenRead($f.FullName)
    try {
        $b = New-Object byte[] 4
        $null = $fs.Read($b, 0, 4)
        if ([Text.Encoding]::ASCII.GetString($b) -ne 'DBPF') { $notDbpf += $f.Name }
    } finally { $fs.Dispose() }
}
if ($notDbpf.Count) { Fail "not a DBPF: $($notDbpf -join ', ')" }
else { Write-Output "  all $($allDat.Count) live .dat begin DBPF" }

# ---- ORDERING ----------------------------------------------------------------
Write-Output ''
Write-Output 'LOAD ORDER'
# ORDINAL sort, not Sort-Object's culture-aware default: culture comparison put
# `~Documents` FIRST in this listing while the ordinal check below correctly
# placed it last, so the printed "load order" contradicted the verdict beside
# it. Ordinal is also the closer model of what the game does.
$topNames = [Collections.Generic.List[string]]::new()
Get-ChildItem $plugins -Directory | ForEach-Object { $topNames.Add($_.Name) }
$topNames.Sort([StringComparer]::Ordinal)
Write-Output "  top level, in load order: $($topNames -join ' | ')"
$ovr = @($pkgDirs | Where-Object { $_.FullName -like '*900-overrides*' })
if ($ovr.Count) {
    $after = @($topNames | Where-Object { [string]::CompareOrdinal($_, '900-overrides') -gt 0 })
    if ($after.Count) {
        Note ("$($after.Count) top-level folder(s) load AFTER 900-overrides and can outrank our override package: " +
              ($after -join ', ') +
              ". This is the documented hybrid-install exposure, not a new defect.")
    } else {
        Write-Output '  nothing out-sorts 900-overrides in this tree'
    }
}

if ($KeepTree -or $LaunchReady) {
    Write-Output ''
    Write-Output 'KEEPING THE TREE - uninstall NOT tested this run.'
} else {
    # ---- UNINSTALL -----------------------------------------------------------
    Write-Output ''
    Write-Output 'UNINSTALL'
    Push-Location $Root
    try {
        & java -jar $Cli remove a-drexel:sc4-ui-scale a-drexel:sc4-ui-scale-mod-overrides
        & java -jar $Cli update -y
        if ($LASTEXITCODE -ne 0) { throw "sc4pac update after remove FAILED (exit $LASTEXITCODE)" }
    } finally { Pop-Location }

    $left = @(Get-ChildItem $plugins -Recurse -File |
              Where-Object { $_.Name -like 'SC4UIScale*' -or $_.Name -like 'z_SC4UIScale_*' -or $_.Extension -eq '.uipay' })
    Write-Output "  files of ours left behind: $($left.Count)"
    foreach ($f in $left) { Write-Output "    $($f.FullName.Substring($plugins.Length).TrimStart('\'))" }
    if ($left.Count) { Fail "$($left.Count) file(s) survived the uninstall" }
}

# ---- LAUNCHABLE USER DIRECTORY ----------------------------------------------
if ($LaunchReady) {
    Write-Output ''
    Write-Output 'LAUNCH-READY USER DIRECTORY'
    # SC4 takes -UserDir:"..." so the game can be pointed at this tree WITHOUT
    # touching the real install. The user dir needs more than Plugins: AutoScale
    # reads SC4GraphicsOptions.ini from it, and with no Regions the game opens
    # to an empty region chooser.
    $liveUser = Split-Path -Parent $live
    foreach ($n in 'Regions', 'Albums') {
        $src = Join-Path $liveUser $n
        $dst = Join-Path $Root $n
        if ((Test-Path $src) -and -not (Test-Path $dst)) { New-Item -ItemType Directory $dst -Force | Out-Null }
    }
    foreach ($n in 'SC4GraphicsOptions.ini', 'SimCity 4.cfg') {
        $src = Join-Path $liveUser $n
        if (Test-Path $src) { Copy-Item $src (Join-Path $Root $n) -Force; Write-Output "  copied $n from the live user dir" }
        else { Note "$n not present in the live user dir - the game will pick its own defaults, and AutoScale will guess from the monitor instead of reading the ini." }
    }
    Write-Output ''
    Write-Output 'Launch the game against this tree with:'
    Write-Output ("  -UserDir:`"$Root`"")
    Write-Output 'Then re-run:'
    Write-Output "  .\_tests\Verify-Arming.ps1 -Plugins '$plugins'"
}

# ---- VERDICT -----------------------------------------------------------------
Write-Output ''
if ($note.Count) {
    Write-Output 'NOTES:'
    $note | ForEach-Object { Write-Output "  - $_" }
    Write-Output ''
}
if ($fail.Count) {
    Write-Output 'RED:'
    $fail | ForEach-Object { Write-Output "  - $_" }
    exit 1
}
Write-Output 'FILE-LEVEL PASS.'
Write-Output 'This says WHERE THE BYTES LANDED and nothing else. SC4 was not started,'
Write-Output 'so arming, the dependency gates and tier switching remain unexercised.'
Write-Output 'Run with -LaunchReady and start the game to test those.'
exit 0
