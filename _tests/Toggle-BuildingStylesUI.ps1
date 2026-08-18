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
$ours  = Join-Path $plugins "zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-2x.dat"
$oursAside = "$ours.uiscale-testoff"

if (Get-Process "SimCity 4" -ErrorAction SilentlyContinue) {
    Write-Output "SimCity 4 is RUNNING - close it first (it holds the dats open)."
    exit 1
}
if (-not (Test-Path $modDir)) {
    Write-Output "FAIL: mod folder not found - has the sc4pac package moved or updated?"
    Write-Output "       expected: $modDir"
    exit 1
}

function Show-State {
    $modOn  = Test-Path $live
    $oursOn = Test-Path $ours
    if ($modOn -and $oursOn) {
        Write-Output "MOD UI = ON  : CoriBoom 36-slot panel (4 named styles + 32 hidden"
        Write-Output "               slots), NO style previews - the mod's layout has none."
        Write-Output "               Active override: zzz-SC4UIScale\z_SC4UIScale_ThirdPartyUI-2x.dat"
    } elseif (-not $modOn -and -not $oursOn) {
        Write-Output "MOD UI = OFF : STOCK 4-style panel WITH its four 160x77 preview"
        Write-Output "               pictures (art abc3e0e5..e8)."
        Write-Output "               Active override: root z_SC4UIScale_SelectiveArt-2x.dat"
    } else {
        Write-Output ("MIXED STATE - mod dat {0}, our zzz package {1}." -f
            $(if ($modOn) {"ON"} else {"off"}), $(if ($oursOn) {"ON"} else {"off"}))
        Write-Output "  Re-run with -Off or -On to make it coherent."
    }
}

if ($Off -and $On) { Write-Output "Pick one of -Off / -On."; exit 1 }

if ($Off) {
    if (Test-Path $live) { Move-Item -LiteralPath $live -Destination $aside }
    if (Test-Path $ours) { Move-Item -LiteralPath $ours -Destination $oursAside }
    Write-Output "Disabled BOTH the mod's UI dat and our zzz override (renamed, not deleted)."
} elseif ($On) {
    if (Test-Path $aside) { Move-Item -LiteralPath $aside -Destination $live }
    if (Test-Path $oursAside) { Move-Item -LiteralPath $oursAside -Destination $ours }
    Write-Output "Re-enabled both."
}

Show-State
