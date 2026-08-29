# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# Toggle CoriBoom's Building Styles UI override on/off, so the Building Style
# Control panel can be tested BOTH WAYS at 2x (user request 2026-07-29):
#
#   MOD ON  (default) - CoriBoom's 36-slot replacement script renders, styles
#                       as a checkbox list, NO preview pictures (the mod's
#                       layout drops them), and our zzz-SC4UIScale\
#                       z_SC4UIScale_ThirdPartyUI package supplies its 2x
#                       script + 2x background art.
#   MOD OFF           - the STOCK 4-style panel renders instead, WITH its four
#                       160x77 style preview pictures (art abc3e0e5..e8), and
#                       our root SelectiveArt copy of the stock script applies.
#                       This is how to verify our scaling against vanilla.
#
# The mod's own file is only ever RENAMED (never edited or deleted), and this
# script renames it back. Nothing else in the mod is touched: its DLL keeps
# running either way.
#
# Usage:  .\Toggle-BuildingStylesUI.ps1            # report current state
#         .\Toggle-BuildingStylesUI.ps1 -Off       # stock panel + previews
#         .\Toggle-BuildingStylesUI.ps1 -On        # back to the 36-slot mod UI
#
# The game must be CLOSED (it holds the dats open while running).
[CmdletBinding()]
param(
    [switch]$Off,
    [switch]$On
)
$ErrorActionPreference = "Stop"

$plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$modDir = Join-Path $plugins ("150-mods\" +
          "null-45.allow-more-building-styles-dll.3.6.1-1.sc4pac")
$leaf   = "CoriBoom's 36 Slot Building Styles UI - v0.46 Beta HA250411.dat"
$live   = Join-Path $modDir $leaf
$aside  = "$live.uiscale-disabled"

# CRITICAL: our own zzz package must move with it. It carries a 2x copy of the
# MOD's 36-slot script at the SAME TGI, and zzz- outranks the root package, so
# leaving it active would keep the mod's layout alive even with the mod's own
# dat disabled - i.e. you would NOT see the stock panel. It also carries the
# 2x of the MOD's taller background art (1032x1308 vs the stock 1032x792),
# which the stock script would sample wrongly.
# The suffix deliberately differs from ScaleTier's ".x1-disabled" so the tier
# loader does not helpfully re-enable it on the next launch.
#
# ============================================================================
# ⛔ v4.5.0: OUR OVERRIDE'S FILENAME NO LONGER SAYS WHETHER IT IS LIVE
# ============================================================================
# Through v4.4.0 our copy sat at `z_SC4UIScale_ThirdPartyUI-2x.dat` when armed
# and `...-2x.dat.x1-disabled` once the dependency gate turned it off, so a
# bare `Test-Path` answered "is our override live?". From v4.5.0 arming is a
# CONTENT SWAP at a stable filename (src\ScaleTier.cpp: ArmOne): the live file
# is `z_SC4UIScale_ThirdPartyUI.dat` at every tier AND when gated off - gated
# off means that same file holding the inert `.off` payload's bytes.
# `Test-Path` is therefore permanently TRUE and Show-State would report
# "MOD UI = ON" forever, including right after a -Off run.
#
# TWO INDEPENDENT INSTRUMENTS replace the filename, chosen for independent
# failure modes:
#   1. `z_SC4UIScale_STATE.txt` - the DLL's OWN record, rewritten by
#      WriteArmState every boot: base <TAB> tag <TAB> reason <TAB> paySize
#      <TAB> payTime <TAB> liveSize <TAB> liveTime. `tag` is the armed payload
#      tag or `off`; `reason` is the gate verdict in the DLL's own words.
#      Blind when the game has not booted since the tree changed.
#   2. THE LIVE FILE'S SIZE, matched against the `.<tag>.uipay` payloads beside
#      it. The `.off` payload is a one-entry DBPF that contests nothing; a tier
#      payload is the whole package. Bytes, not bookkeeping. Blind only when
#      two payloads share a length.
# When they disagree, or when neither can answer, this script REFUSES rather
# than printing a confident state - "mod off + ours ON" is the failure this
# whole arrangement exists to catch, and it looks exactly like success.
$oursDir    = Join-Path $plugins "zzz-SC4UIScale"
$oursBase   = "z_SC4UIScale_ThirdPartyUI"
$oursStable = Join-Path $oursDir "$oursBase.dat"

$oursPayloads = @(Get-ChildItem -LiteralPath $oursDir -File -Filter "$oursBase.*.uipay" -ErrorAction SilentlyContinue)
$oursTierFiles = @(Get-ChildItem -LiteralPath $oursDir -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "$oursBase-*.dat" -or
                   $_.Name -like "$oursBase-*.dat.x1-disabled" -or
                   $_.Name -like "$oursBase-*.dat.uiscale-testoff" })
$oursHasStable = Test-Path -LiteralPath $oursStable

# RENAME LAYOUT ONLY: WHICH TIER'S FILE IS OURS RIGHT NOW?
# ⚠ THIS USED TO HARD-CODE "-2x". That is precisely the tier-blind bug
# Test-ThirdPartyGates.ps1 was fixed for on 2026-08-06: at 1.5x or 3x the 2x
# file IS the .x1-disabled twin, so Show-State reported "our zzz package off"
# on a machine where nothing was wrong, and -Off/-On moved a file that was
# already inert while leaving the armed tier live and winning. Discover the
# tier from disk instead. (Under the PAYLOAD layout there is nothing to
# discover - one constant filename, all tiers.)
function Resolve-RenameTierFile {
    param([string]$Dir, [string]$Base)
    # 1. A file THIS SCRIPT disabled names the tier it disabled; -On has to
    #    target that exact name or the restore silently misses.
    $testoff = @($oursTierFiles | Where-Object { $_.Name -like "$Base-*.dat.uiscale-testoff" })
    if ($testoff.Count -ge 1) {
        return (Join-Path $Dir ($testoff[0].Name -replace '\.uiscale-testoff$', ''))
    }
    # 2. The bare tagged .dat is the armed tier.
    $bare = @($oursTierFiles | Where-Object { $_.Extension -eq '.dat' })
    if ($bare.Count -eq 1) { return $bare[0].FullName }
    if ($bare.Count -gt 1) { return $null }   # two tiers live: caller refuses
    # 3. Every tier gated off. Nothing to move; keep the historical name so the
    #    paths below are still well-formed. INFERRED, not measured.
    return (Join-Path $Dir "$Base-2x.dat")
}

# The developer's own Plugins tree is DELIBERATELY still on the rename layout,
# so both are supported and the script names which one it found. A tree
# carrying BOTH is refused: the package would have two live providers for every
# TGI it owns, and filename order - not intent - would pick the winner.
$layout =
    if ($oursTierFiles.Count -and ($oursPayloads.Count -or $oursHasStable)) { 'MIXED' }
    elseif ($oursPayloads.Count -or $oursHasStable) { 'PAYLOAD' }
    elseif ($oursTierFiles.Count) { 'RENAME' }
    else { 'ABSENT' }

$oursTagged = if ($layout -eq 'RENAME') { Resolve-RenameTierFile $oursDir $oursBase } else { $null }
if ($layout -eq 'RENAME' -and -not $oursTagged) {
    Write-Output "REFUSING: more than one tier of $oursBase is live (bare .dat) in"
    Write-Output "  $oursDir"
    Write-Output ("  {0}" -f ((@($oursTierFiles | Where-Object { $_.Extension -eq '.dat' }) | ForEach-Object { $_.Name }) -join ', '))
    Write-Output "Both supply the same TGIs and filename order picks the winner, so there is"
    Write-Output "no single 'our override' for this script to move or to report on."
    exit 1
}
$ours  = if ($layout -eq 'RENAME') { $oursTagged } else { $oursStable }
$oursAside = "$ours.uiscale-testoff"

# WriteArmState's row for one package, or $null. `base` in that file is the
# LEAF name - SyncDat strips the folder before recording it.
function Read-ArmRow {
    param([string]$Dir, [string]$Base)
    $s = Join-Path $Dir 'z_SC4UIScale_STATE.txt'
    if (-not (Test-Path -LiteralPath $s)) { return $null }
    foreach ($line in (Get-Content -LiteralPath $s)) {
        if (-not $line -or $line -match '^\s*#') { continue }
        $c = $line -split "`t"
        if ($c.Count -lt 7) { continue }
        if ($c[0] -ieq $Base) {
            return [pscustomobject]@{
                Tag = $c[1]; Reason = $c[2]
                LiveSize = [int64]$c[5]; LiveTime = [int64]$c[6]
                StateFile = $s
            }
        }
    }
    return $null
}

# Instrument 2. Returns a tag ('2x', 'off', ...), or a word naming why it could
# not answer - never a guess.
function Get-ArmedTagBySize {
    param([string]$LivePath, $Payloads)
    if (-not (Test-Path -LiteralPath $LivePath)) { return 'ABSENT' }
    if (-not $Payloads -or -not @($Payloads).Count) { return 'NO-PAYLOADS' }
    $len = (Get-Item -LiteralPath $LivePath).Length
    $hit = @(@($Payloads) | Where-Object { $_.Length -eq $len } |
             ForEach-Object { $_.Name -replace '^.*\.([^.]+)\.uipay$', '$1' } |
             Sort-Object -Unique)
    if ($hit.Count -eq 1) { return $hit[0] }
    if ($hit.Count -gt 1) { return ('AMBIGUOUS:' + ($hit -join '/')) }
    return 'NO-MATCH'
}

if (Get-Process "SimCity 4" -ErrorAction SilentlyContinue) {
    Write-Output "SimCity 4 is RUNNING - close it first (it holds the dats open)."
    exit 1
}
if (-not (Test-Path $modDir)) {
    Write-Output "FAIL: mod folder not found - has the sc4pac package moved or updated?"
    Write-Output "       expected: $modDir"
    exit 1
}
if ($layout -eq 'MIXED') {
    Write-Output "REFUSING: $oursBase exists under BOTH layouts in"
    Write-Output "  $oursDir"
    Write-Output ("  tier-tagged/.x1-disabled : {0}" -f (($oursTierFiles | ForEach-Object { $_.Name }) -join ', '))
    Write-Output ("  stable .dat / payloads   : {0}" -f (@(@($oursPayloads | ForEach-Object { $_.Name }) + @(if ($oursHasStable) { "$oursBase.dat" })) -join ', '))
    Write-Output "Two live providers for every TGI this package owns, and filename order"
    Write-Output "picks the winner - so no state this script printed would be meaningful."
    Write-Output "Finish the conversion (_tests\Convert-ToPayloadLayout.ps1) or restore the"
    Write-Output "rename layout, then re-run."
    exit 1
}
Write-Output ("arming layout: {0}" -f $(switch ($layout) {
    'PAYLOAD' { "PAYLOAD (v4.5.0 content swap - our override is $oursBase.dat, $($oursPayloads.Count) payload(s) beside it)" }
    'RENAME'  { "RENAME (pre-4.5.0 - our override is $(Split-Path $ours -Leaf), discovered from disk, gated by an .x1-disabled twin)" }
    default   { "our package is NOT INSTALLED in $oursDir" }
}))

# Is OUR override actually supplying its scaled copy right now?
# RENAME: the filename says so. PAYLOAD: the filename says nothing at all, so
# ask the two instruments described in the header block and refuse on
# disagreement. Returns 'ON' / 'OFF' / 'UNKNOWN', plus how it was decided.
function Get-OursState {
    if ($layout -eq 'RENAME') {
        return [pscustomobject]@{
            State = $(if (Test-Path -LiteralPath $ours) { 'ON' } else { 'OFF' })
            How   = 'filename (rename layout: a bare .dat is armed, an .x1-disabled twin is gated)'
        }
    }
    if ($layout -eq 'ABSENT') {
        return [pscustomobject]@{ State = 'OFF'; How = 'package not installed' }
    }
    if (-not (Test-Path -LiteralPath $ours)) {
        # Moved aside by this script. Under the payload layout that is a WEAK
        # off - ArmOne recreates the stable name on the next boot from the
        # `.off` payload, so the package stays inert but the FILE comes back.
        return [pscustomobject]@{ State = 'OFF'; How = 'the live .dat is moved aside (this script did it)' }
    }
    $bySize  = Get-ArmedTagBySize $ours $oursPayloads
    $row     = Read-ArmRow $oursDir $oursBase
    $byState = if ($row) { $row.Tag } else { $null }

    if ($bySize -match '^(AMBIGUOUS|NO-MATCH|NO-PAYLOADS)') {
        if (-not $byState) {
            return [pscustomobject]@{ State = 'UNKNOWN'
                How = "neither instrument could answer (bytes: $bySize; no z_SC4UIScale_STATE.txt row - the game has not booted since the tree changed)" }
        }
        return [pscustomobject]@{
            State = $(if ($byState -eq 'off') { 'OFF' } else { 'ON' })
            How   = "z_SC4UIScale_STATE.txt only, tag='$byState' ($($row.Reason)) - UNCORROBORATED, the byte instrument returned $bySize" }
    }
    if ($byState -and $byState -ne $bySize) {
        return [pscustomobject]@{ State = 'UNKNOWN'
            How = "the two instruments DISAGREE: the live file's bytes are the '$bySize' payload, z_SC4UIScale_STATE.txt says '$byState' ($($row.Reason)). One of them is describing a different boot." }
    }
    $how = if ($byState) { "bytes = the '$bySize' payload, confirmed by z_SC4UIScale_STATE.txt ($($row.Reason))" }
           else          { "bytes = the '$bySize' payload (no STATE.txt row - uncorroborated)" }
    return [pscustomobject]@{ State = $(if ($bySize -eq 'off') { 'OFF' } else { 'ON' }); How = $how }
}

function Show-State {
    $modOn  = Test-Path $live
    $o      = Get-OursState
    $oursOn = ($o.State -eq 'ON')

    if ($o.State -eq 'UNKNOWN') {
        Write-Output ("REFUSING TO REPORT A STATE - mod dat {0}, our override UNDECIDABLE." -f
            $(if ($modOn) {"ON"} else {"off"}))
        Write-Output ("  {0}" -f $o.How)
        Write-Output "  Under the v4.5.0 content swap the filename carries no verdict, so an"
        Write-Output "  undecidable override is exactly the case where a confident answer"
        Write-Output "  would be wrong in the 'looks fine' direction. Launch the game once"
        Write-Output "  (the DLL rewrites z_SC4UIScale_STATE.txt every boot) and re-run."
        return
    }

    if ($modOn -and $oursOn) {
        Write-Output "MOD UI = ON  : CoriBoom 36-slot panel (4 named styles + 32 hidden"
        Write-Output "               slots), NO style previews - the mod's layout has none."
        Write-Output ("               Active override: zzz-SC4UIScale\{0}" -f (Split-Path $ours -Leaf))
    } elseif (-not $modOn -and -not $oursOn) {
        Write-Output "MOD UI = OFF : STOCK 4-style panel WITH its four 160x77 preview"
        Write-Output "               pictures (art abc3e0e5..e8)."
        Write-Output "               Active override: the SelectiveArt package's copy"
    } else {
        Write-Output ("MIXED STATE - mod dat {0}, our zzz package {1}." -f
            $(if ($modOn) {"ON"} else {"off"}), $(if ($oursOn) {"ON"} else {"off"}))
        Write-Output "  Re-run with -Off or -On to make it coherent."
    }
    Write-Output ("  our override decided by: {0}" -f $o.How)
}

if ($Off -and $On) { Write-Output "Pick one of -Off / -On."; exit 1 }

if ($Off) {
    if (Test-Path $live) { Move-Item -LiteralPath $live -Destination $aside }
    if (Test-Path $ours) { Move-Item -LiteralPath $ours -Destination $oursAside -Force }
    Write-Output "Disabled BOTH the mod's UI dat and our zzz override (renamed, not deleted)."
    if ($layout -eq 'PAYLOAD') {
        # Say it out loud: under the content swap a rename-aside is a WEAK off.
        Write-Output "  !! PAYLOAD LAYOUT: ArmOne recreates $oursBase.dat on the next"
        Write-Output "     boot because the live file is missing. It will hold the .off"
        Write-Output "     payload (the mod is gone, so the gate says off), so the package"
        Write-Output "     stays INERT and the comparison is still valid - but the FILE"
        Write-Output "     comes back, and a listing that shows it proves nothing."
    }
} elseif ($On) {
    if (Test-Path $aside) { Move-Item -LiteralPath $aside -Destination $live -Force }
    # -Force: under the payload layout the DLL may have recreated the stable
    # name (holding .off) since -Off ran, so a plain Move-Item would throw and
    # leave the tier bytes stranded in the .uiscale-testoff file.
    if (Test-Path $oursAside) { Move-Item -LiteralPath $oursAside -Destination $ours -Force }
    Write-Output "Re-enabled both."
    if ($layout -eq 'PAYLOAD') {
        Write-Output "z_SC4UIScale_STATE.txt now describes the PREVIOUS boot, so its stamp"
        Write-Output "will miss and ArmOne re-arms this package on the next launch. That is"
        Write-Output "the designed self-heal, not a fault."
    }
}

Show-State
