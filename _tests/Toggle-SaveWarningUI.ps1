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
$ours  = Join-Path $plugins "zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-2x.dat"
$oursAside = "$ours.uiscale-testoff"

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

function Show-State {
    $modOn  = Test-Path $live
    $oursOn = Test-Path $ours
    if ($modOn -and $oursOn) {
        Write-Output "SAVE-WARNING MOD = ON  : confirms are the MOD's - first button"
        Write-Output "                         'Option Disabled', greyed and inert."
        Write-Output "                         Expect MWKID 540x324 (2x of 270x162)."
        Write-Output "                         Override: zzz-SC4UIScale\z_SC4UIScale_SaveWarningUI-2x.dat"
    } elseif (-not $modOn -and -not $oursOn) {
        Write-Output "SAVE-WARNING MOD = OFF : confirms are STOCK - first button"
        Write-Output "                         'Save and Exit to Region', ENABLED."
        Write-Output "                         Expect MWKID 540x322 (2x of 270x161)."
        Write-Output "                         Override: root z_SC4UIScale_DialogStatic-2x.dat"
    } else {
        Write-Output ("MIXED STATE - mod dat {0}, our zzz package {1}." -f
            $(if ($modOn) {"ON"} else {"off"}), $(if ($oursOn) {"ON"} else {"off"}))
        Write-Output "  mod off + ours ON is the exact failure this fix exists to prevent:"
        Write-Output "  our frozen copy would keep the removed mod's UI on screen."
        Write-Output "  Re-run with -Off or -On to make it coherent."
    }
}

$modeCount = @($Off, $On, $GateOnly | Where-Object { $_ }).Count
if ($modeCount -gt 1) { Write-Output "Pick ONE of -Off / -On / -GateOnly."; exit 1 }

# ScaleTier's own suffix - -On must restore anything the GATE renamed too,
# otherwise a -GateOnly run would leave our package disabled forever.
$oursTierAside = "$ours.x1-disabled"

if ($Off) {
    if (Test-Path $live) { Move-Item -LiteralPath $live -Destination $aside }
    if (Test-Path $ours) { Move-Item -LiteralPath $ours -Destination $oursAside }
    Write-Output "Disabled BOTH the mod's dat and our zzz override (renamed, not deleted)."
    Write-Output "Expect in the log: 'ScaleTier: ...SaveWarningUI dep ABSENT'."
    Write-Output "NOTE: this arrangement does the GATE's job by hand, so it"
    Write-Output "      verifies RENDERING only. Use -GateOnly to test the gate."
} elseif ($GateOnly) {
    if (Test-Path $live) { Move-Item -LiteralPath $live -Destination $aside }
    if (Test-Path $oursAside) { Move-Item -LiteralPath $oursAside -Destination $ours }
    if (Test-Path $oursTierAside) { Move-Item -LiteralPath $oursTierAside -Destination $ours }
    Write-Output "MOD dat disabled; our zzz override left ACTIVE on purpose."
    Write-Output "This is the REAL test of ScaleTier's dependency gate."
    Write-Output "  PASS: stock confirms (540x322 / 660x314) AND the log line"
    Write-Output "        'ScaleTier: ...SaveWarningUI dep ABSENT (...) -> disabled'."
    Write-Output "  FAIL: the removed mod's greyed 'Option Disabled' button is"
    Write-Output "        still on screen -> the gate lands after the dat scan"
    Write-Output "        and is one launch late. Report it; do not 'fix' by"
    Write-Output "        hand-moving files."
    Write-Output "After the launch, check whether ScaleTier renamed it:"
    Write-Output "  $oursTierAside"
} elseif ($On) {
    if (Test-Path $aside) { Move-Item -LiteralPath $aside -Destination $live }
    if (Test-Path $oursAside) { Move-Item -LiteralPath $oursAside -Destination $ours }
    # ALSO undo a rename performed by ScaleTier itself during a -GateOnly run.
    if (Test-Path $oursTierAside) { Move-Item -LiteralPath $oursTierAside -Destination $ours }
    Write-Output "Re-enabled both (including anything ScaleTier had disabled)."
}

Show-State
