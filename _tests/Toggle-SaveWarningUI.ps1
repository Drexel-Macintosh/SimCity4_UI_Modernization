# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
# Toggle cyclone-boom's save-warning mod on/off, so the in-city quit /
# exit-to-region confirms can be tested BOTH WAYS at 2x (task #79c, the
# SCENARIOS.md AXIS 2 "mod state" axis - the axis that has hurt most).
#
#   MOD ON  (default) - the mod's script renders (270x162 stock, first button
#                       captioned "Option Disabled" and winflag_enable=no), and
#                       our zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI package
#                       supplies its 2x copy -> born 540x324, no open flash.
#   MOD OFF           - the STOCK script renders (270x161, first button
#                       "Save and Exit to Region", ENABLED), and our ROOT
#                       z_SC4UIScale_DialogStatic-2x.dat copy supplies its 2x
#                       -> born 540x322, also no open flash.
#
# The 2px height difference (324 vs 322) is the tell for which state you are
# actually looking at - MWKID prints it.
#
# UNLIKE Toggle-BuildingStylesUI.ps1, moving our override by hand is only
# needed for a SAME-LAUNCH test: ScaleTier now gates this package on the mod
# automatically (kThirdPartyDeps), so on the next launch it would disable it
# anyway. This script moves it too, which is what makes state B testable on
# the very first launch and therefore what MEASURES whether the automatic gate
# lands before the game's dat scan.
#
# The mod's own file is only ever RENAMED (never edited or deleted), and this
# script renames it back. Nothing else in the mod is touched - its LTEXT
# caption overrides keep loading either way.
#
# Usage:  .\Toggle-SaveWarningUI.ps1            # report current state
#         .\Toggle-SaveWarningUI.ps1 -Off       # stock confirms
#         .\Toggle-SaveWarningUI.ps1 -On        # back to the mod's confirms
#
# The game must be CLOSED (it holds the dats open while running).
# -GateOnly (added 2026-07-31, task #83): moves ONLY the MOD's dat aside and
# LEAVES our zzz override in place. This is the one arrangement that actually
# TESTS ScaleTier's automatic dependency gate, because -Off does the gate's job
# by hand and so can never fail. Measured ordering that makes it meaningful:
# ScaleTier::SyncStaticLayers runs from PreAppInit (SC4UIScaleDllDirector.cpp
# :214), i.e. BEFORE the game's plugin scan, so the rename should take effect
# on THIS launch rather than the next one.
#   PASS  -> stock confirms + "ScaleTier: ...SaveWarningUI dep ABSENT ... disabled"
#   FAIL  -> the removed mod's greyed "Option Disabled" button still on screen,
#            which means the gate lands AFTER the dat scan and is one launch
#            late (a real defect, and exactly the trap MAYOR-MODE.md:126 records)
# Either way -On restores everything, including anything ScaleTier renamed.
[CmdletBinding()]
param(
    [switch]$Off,
    [switch]$On,
    [switch]$GateOnly
)
$ErrorActionPreference = "Stop"

$plugins = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$modDir = Join-Path $plugins "150-mods\cyclone-boom.save-warning.1.0.sc4pac"
$leaf   = "SaveWarning_Disable_Exit_Quit.dat"
$live   = Join-Path $modDir $leaf
$aside  = "$live.uiscale-disabled"

# Our zzz package must move with it: it carries a 2x copy of the MOD's script
# at the SAME TGI, and zzz- outranks both the root package and the game
# archive, so leaving it active would keep the mod's greyed "Option Disabled"
# button on screen after the mod itself is gone. That is exactly the trap
# MAYOR-MODE.md:126 recorded.
# The suffix deliberately differs from ScaleTier's ".x1-disabled" so the tier
# loader does not helpfully re-enable it on the next launch.
#
# ============================================================================
# ⛔ v4.5.0: OUR OVERRIDE'S FILENAME NO LONGER SAYS WHETHER IT IS LIVE
# ============================================================================
# Through v4.4.0 our copy sat at `z_SC4UIScale_SaveWarningUI-2x.dat` when armed
# and `...-2x.dat.x1-disabled` once the dependency gate turned it off, so a
# bare `Test-Path` answered "is our override live?" and `-GateOnly`'s whole
# pass condition was the APPEARANCE of that `.x1-disabled` twin. From v4.5.0
# arming is a CONTENT SWAP at a stable filename (src\ScaleTier.cpp: ArmOne):
# the live file is `z_SC4UIScale_SaveWarningUI.dat` at every tier AND when
# gated off - gated off means that same file holding the inert `.off`
# payload's bytes. `Test-Path` is therefore permanently TRUE, no `.x1-disabled`
# twin ever appears, and Show-State would report "MOD ON" forever - including
# in the one arrangement this script exists to measure.
#
# TWO INDEPENDENT INSTRUMENTS replace the filename, chosen for independent
# failure modes (a shared one would be one instrument wearing two hats):
#   1. `z_SC4UIScale_STATE.txt` - the DLL's OWN record, rewritten by
#      WriteArmState every boot: base <TAB> tag <TAB> reason <TAB> paySize
#      <TAB> payTime <TAB> liveSize <TAB> liveTime. `tag` is the armed payload
#      tag or `off`, and `reason` is the gate verdict in the DLL's own words.
#      Fails when the game has not booted since the tree changed.
#   2. THE LIVE FILE'S SIZE, matched against the `.<tag>.uipay` payloads beside
#      it. The `.off` payload is a one-entry DBPF that contests nothing; a tier
#      payload is the whole package. Bytes on disk, no bookkeeping involved.
#      Fails when two payloads happen to share a length.
# When they disagree, or when neither can answer, this script REFUSES. It must
# not print a confident state: the failure it was built to catch (our frozen
# copy still winning after the mod is gone) looks exactly like success.
$oursDir   = Join-Path $plugins "zzz-SC4UIScale"
$oursBase  = "z_SC4UIScale_SaveWarningUI"
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
# TGI it owns and filename order would pick the winner.
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
    Write-Output "       (ScaleTier finds the dat by NAME, so it survives a folder"
    Write-Output "        rename even when this test script does not.)"
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
        # Moved aside by this script. Worth saying plainly: under the payload
        # layout that is a WEAK off - the DLL recreates the stable name on the
        # next boot from the `.off` payload, so the package stays inert but the
        # file comes back. See the -Off branch.
        return [pscustomobject]@{ State = 'OFF'; How = 'the live .dat is moved aside (this script did it)' }
    }
    $bySize = Get-ArmedTagBySize $ours $oursPayloads
    $row    = Read-ArmRow $oursDir $oursBase
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
    $modOn = Test-Path $live
    $o     = Get-OursState
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
        Write-Output "SAVE-WARNING MOD = ON  : confirms are the MOD's - first button"
        Write-Output "                         'Option Disabled', greyed and inert."
        Write-Output "                         Expect MWKID 540x324 (2x of 270x162)."
        Write-Output ("                         Override: zzz-SC4UIScale\{0}" -f (Split-Path $ours -Leaf))
    } elseif (-not $modOn -and -not $oursOn) {
        Write-Output "SAVE-WARNING MOD = OFF : confirms are STOCK - first button"
        Write-Output "                         'Save and Exit to Region', ENABLED."
        Write-Output "                         Expect MWKID 540x322 (2x of 270x161)."
        Write-Output "                         Override: the DialogStatic package's copy"
    } else {
        Write-Output ("MIXED STATE - mod dat {0}, our zzz package {1}." -f
            $(if ($modOn) {"ON"} else {"off"}), $(if ($oursOn) {"ON"} else {"off"}))
        Write-Output "  mod off + ours ON is the exact failure this fix exists to prevent:"
        Write-Output "  our frozen copy would keep the removed mod's UI on screen."
        Write-Output "  Re-run with -Off or -On to make it coherent."
    }
    Write-Output ("  our override decided by: {0}" -f $o.How)
}

$modeCount = @($Off, $On, $GateOnly | Where-Object { $_ }).Count
if ($modeCount -gt 1) { Write-Output "Pick ONE of -Off / -On / -GateOnly."; exit 1 }

# ScaleTier's own PRE-4.5.0 suffix - -On must restore anything the GATE renamed
# too, otherwise a -GateOnly run would leave our package disabled forever.
# Under the payload layout no such file can ever appear (the gate swaps CONTENT
# now, it renames nothing); the checks are kept because the developer's tree is
# still on the rename layout and a half-migrated tree must still restore.
$oursTierAside = "$ours.x1-disabled"

if ($Off) {
    if (Test-Path $live) { Move-Item -LiteralPath $live -Destination $aside }
    if (Test-Path $ours) { Move-Item -LiteralPath $ours -Destination $oursAside -Force }
    Write-Output "Disabled BOTH the mod's dat and our zzz override (renamed, not deleted)."
    Write-Output "Expect in the log: 'ScaleTier: ...SaveWarningUI dep ABSENT'."
    Write-Output "NOTE: this arrangement does the GATE's job by hand, so it"
    Write-Output "      verifies RENDERING only. Use -GateOnly to test the gate."
    if ($layout -eq 'PAYLOAD') {
        Write-Output ""
        # ASCII ONLY INSIDE STRINGS. These .ps1 files carry no BOM, so
        # PowerShell 5.1 decodes them as ANSI: a UTF-8 "no entry" glyph
        # (E2 9B 94) becomes 'a >' plus U+201D, and PowerShell accepts U+201D
        # AS A DOUBLE QUOTE - the string silently ends mid-line and the parser
        # then reads prose as code. Harmless in a comment (which runs to EOL),
        # fatal in a string. Keep the glyphs in comments, never in output.
        Write-Output "  !! UNDER THE PAYLOAD LAYOUT THIS IS A *WEAK* OFF, and saying so is"
        Write-Output "     the point: ArmOne recreates $oursBase.dat on the next boot"
        Write-Output "     because the live file is missing. It will hold the .off"
        Write-Output "     payload (the mod is gone, so the gate says off), so the package"
        Write-Output "     stays INERT and the test is still valid - but the FILE comes"
        Write-Output "     back, and a listing that shows it is not evidence of anything."
        Write-Output "     Read z_SC4UIScale_STATE.txt, or re-run this script, instead."
    }
} elseif ($GateOnly) {
    if (Test-Path $live) { Move-Item -LiteralPath $live -Destination $aside }
    if (Test-Path $oursAside) { Move-Item -LiteralPath $oursAside -Destination $ours -Force }
    if (Test-Path $oursTierAside) { Move-Item -LiteralPath $oursTierAside -Destination $ours -Force }
    Write-Output "MOD dat disabled; our zzz override left ACTIVE on purpose."
    Write-Output "This is the REAL test of ScaleTier's dependency gate."
    Write-Output "  PASS: stock confirms (540x322 / 660x314) AND the log line"
    Write-Output "        'ScaleTier: ...SaveWarningUI dep ABSENT (...) -> disabled'."
    Write-Output "  FAIL: the removed mod's greyed 'Option Disabled' button is"
    Write-Output "        still on screen -> the gate lands after the dat scan"
    Write-Output "        and is one launch late. Report it; do not 'fix' by"
    Write-Output "        hand-moving files."
    Write-Output ""
    if ($layout -eq 'PAYLOAD') {
        # ⛔ THE OLD PASS CONDITION IS GONE. It was "an .x1-disabled twin
        # appeared", and under the content swap no twin ever appears at any
        # tier under any verdict - so a -GateOnly run would have looked like a
        # FAIL on a working gate. The gate's signature is now a STATE row.
        Write-Output "After the launch, the gate's signature is in the STATE FILE, not in"
        Write-Output "a filename - the content swap renames nothing:"
        Write-Output ("  {0}\z_SC4UIScale_STATE.txt" -f $oursDir)
        Write-Output ("  the {0} row must read  tag=off  with a reason naming the absent dep." -f $oursBase)
        Write-Output "Or just re-run this script with no switch - it reads that file and"
        Write-Output "cross-checks it against the live file's bytes."
    } else {
        Write-Output "After the launch, check whether ScaleTier renamed it:"
        Write-Output "  $oursTierAside"
    }
} elseif ($On) {
    if (Test-Path $aside) { Move-Item -LiteralPath $aside -Destination $live -Force }
    # -Force: under the payload layout the DLL may have recreated the stable
    # name (holding `.off`) since -Off ran, so a plain Move-Item would throw
    # and leave the tier bytes stranded in the .uiscale-testoff file.
    if (Test-Path $oursAside) { Move-Item -LiteralPath $oursAside -Destination $ours -Force }
    # ALSO undo a rename performed by ScaleTier itself during a -GateOnly run.
    if (Test-Path $oursTierAside) { Move-Item -LiteralPath $oursTierAside -Destination $ours -Force }
    Write-Output "Re-enabled both (including anything ScaleTier had disabled)."
    if ($layout -eq 'PAYLOAD') {
        Write-Output "z_SC4UIScale_STATE.txt now describes the PREVIOUS boot, so its stamp"
        Write-Output "will miss and ArmOne re-arms this package on the next launch. That is"
        Write-Output "the designed self-heal, not a fault."
    }
}

Show-State
