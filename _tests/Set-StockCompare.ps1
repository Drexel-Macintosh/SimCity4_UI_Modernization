# Paths are RESOLVED, not hard-coded: Documents may be redirected by
# OneDrive, and the repo may be cloned anywhere (task #108).
<#
  Set-StockCompare.ps1 - flip SC4 between STOCK (vanilla UI) and OURS (2x UI)
  for side-by-side comparison, WITHOUT touching dgVoodoo, the game exe, or
  SC4TouchControls.dll (hard rule: touch DLL is separate + shipped).

  STOCK mode disables ONLY our scaling layer, by renaming to .compare-off:
    Documents\Plugins : SC4UIScale.dll, every ACTIVE z_SC4UIScale_*.dat,
                        FontStyle.ini (the 2x font)
    <install>\Plugins : FontStyle.ini   <- the copy the game actually probes
                        (probe order: <install>\Plugins -> <install> -> DBPF)
  ...and sets a stock resolution in SC4GraphicsOptions.ini (Windowed, so the
  DirectX+dgVoodoo path renders at the REQUESTED size instead of panel-native).

  OURS mode restores every renamed file and the saved graphics settings.

  Usage:
    .\Set-StockCompare.ps1 -Mode Stock              # 1024x768 windowed, vanilla UI
    .\Set-StockCompare.ps1 -Mode Stock -Width 1280 -Height 1024
    .\Set-StockCompare.ps1 -Mode Ours               # back to 2400x1600 fullscreen, 2x UI
    .\Set-StockCompare.ps1 -Status                  # show what is currently active
#>
[CmdletBinding()]
param(
    [ValidateSet("Stock", "Ours")] [string] $Mode,
    [int] $Width  = 1024,
    [int] $Height = 768,
    [switch] $Status
)

$ErrorActionPreference = "Stop"

$DocPlugins  = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins')
$InstallRoot = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe"
$InstPlugins = Join-Path $InstallRoot "Plugins"
$GfxIni      = Join-Path $DocPlugins "SC4GraphicsOptions.ini"
$StateFile   = Join-Path $DocPlugins "SC4UIScale.compare-state.txt"
$OffSuffix   = ".compare-off"

# Our scaling layer. NOTE: SC4TouchControls.dll is deliberately NOT here.
# Only files WITHOUT an existing gating suffix (.x1-disabled) are touched.
function Get-OurLiveFiles {
    $files = @()
    $files += Get-ChildItem -Path $DocPlugins -Filter "SC4UIScale.dll" -ErrorAction SilentlyContinue
    $files += Get-ChildItem -Path $DocPlugins -Filter "z_SC4UIScale_*.dat" -ErrorAction SilentlyContinue
    # zzz-SC4UIScale subfolder: our 2x copies of OTHER MODS' scripts
    # (ThirdPartyUI / CamUI / SaveWarningUI). These MUST come off in stock
    # mode too - found 2026-08-02 when the #58 stock capture would otherwise
    # have kept our 2x Building Styles script live under an otherwise 1x UI
    # (a Franken-capture of exactly the panel being measured). The .dat
    # filter already excludes .x1-disabled files, same as the root scan.
    $files += Get-ChildItem -Path (Join-Path $DocPlugins "zzz-SC4UIScale") -Filter "z_SC4UIScale_*.dat" -ErrorAction SilentlyContinue
    $files += Get-ChildItem -Path $DocPlugins -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    $files += Get-ChildItem -Path $InstPlugins -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    # 2026-08-05: THE THIRD COPY, and it was missing for months. Our own font
    # file's header says it plainly - "Deploy as: <install root>\FontStyle.ini
    # ... Plugins\FontStyle.ini would take priority". The game probes
    #     <install>\Plugins  ->  <install>  ->  the DBPF
    # so disabling only the two Plugins copies left OUR 2x table live as the
    # FALLBACK, and "stock" mode still had doubled fonts. <install> here means
    # where the exe lives = the Apps folder.
    $files += Get-ChildItem -Path $InstallRoot -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    $appsDir = Join-Path $InstallRoot "Apps"
    $files += Get-ChildItem -Path $appsDir -Filter "FontStyle.ini" -ErrorAction SilentlyContinue
    return $files
}

function Assert-GameClosed {
    $p = Get-Process -Name "SimCity 4" -ErrorAction SilentlyContinue
    if ($p) { throw "SimCity 4 is running (pid $($p.Id)). Close it first - files are locked while it runs." }
}

# #105/#107's law, learned AGAIN 2026-08-17: SC4UIScale.log is recreated on
# every launch, and a mode flip is usually followed by a launch - this is the
# last safe moment. The 40-thin THINBLT capture (#162's first real signal) was
# destroyed because the ad-hoc flip scripts lacked this step while the deploy
# script had it. Named by the log's OWN mtime, so it keeps its run's identity.
function Preserve-Log {
    $srcLog = Join-Path $DocPlugins "SC4UIScale.log"
    if (-not (Test-Path $srcLog)) { return }
    $capDir = Join-Path (Split-Path -Parent $PSScriptRoot) "_tests\captures"
    if (-not (Test-Path $capDir)) { New-Item -ItemType Directory $capDir | Out-Null }
    $stamp = (Get-Item $srcLog).LastWriteTime.ToString("yyyy-MM-dd-HHmmss")
    $dest = Join-Path $capDir ("SC4UIScale-{0}.log" -f $stamp)
    if (-not (Test-Path $dest)) {
        Copy-Item $srcLog $dest -Force
        Write-Output ("preserved previous run log -> {0}" -f (Split-Path $dest -Leaf))
    }
}

function Set-IniValue {
    param([string] $Path, [string] $Key, [string] $Value)
    $lines = Get-Content -Path $Path
    $hit = $false
    $out = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=") { $hit = $true; "$Key=$Value" } else { $line }
    }
    if (-not $hit) { throw "Key '$Key' not found in $Path" }
    # NO BOM. PowerShell 5.1's `Set-Content -Encoding utf8` writes a UTF-8 BOM;
    # SC4GraphicsOptions.dll then fails to parse the ini and the game silently
    # falls back to its own SimCity 4.cfg (this stranded the game at the stock
    # 1024x768 after a restore, 2026-07-28). Write UTF8-no-BOM explicitly.
    [System.IO.File]::WriteAllLines($Path, $out, (New-Object System.Text.UTF8Encoding($false)))
}

function Get-IniValue {
    param([string] $Path, [string] $Key)
    foreach ($line in (Get-Content -Path $Path)) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.*)$") { return $Matches[1].Trim() }
    }
    return $null
}

function Show-Status {
    $off = @(Get-ChildItem -Path $DocPlugins -Filter "*$OffSuffix" -ErrorAction SilentlyContinue)
    $off += @(Get-ChildItem -Path $InstPlugins -Filter "*$OffSuffix" -ErrorAction SilentlyContinue)
    $off += @(Get-ChildItem -Path (Join-Path $DocPlugins "zzz-SC4UIScale") -Filter "*$OffSuffix" -ErrorAction SilentlyContinue)
    $mode = if ($off.Count -gt 0) { "STOCK (our scaling disabled)" } else { "OURS (2x scaling active)" }
    Write-Host "Mode      : $mode"
    Write-Host "Resolution: $(Get-IniValue $GfxIni 'WindowWidth')x$(Get-IniValue $GfxIni 'WindowHeight') $(Get-IniValue $GfxIni 'WindowMode') / $(Get-IniValue $GfxIni 'Driver')"
    if ($off.Count -gt 0) {
        Write-Host "Disabled  : $($off.Count) file(s)"
        $off | ForEach-Object { Write-Host "            $($_.Name)" }
    }
}

if ($Status -or -not $Mode) { Show-Status; return }

Assert-GameClosed
Preserve-Log

if ($Mode -eq "Stock") {
    # Save what we are leaving, so -Mode Ours restores it exactly.
    if (-not (Test-Path $StateFile)) {
        @(
            "WindowWidth=$(Get-IniValue $GfxIni 'WindowWidth')"
            "WindowHeight=$(Get-IniValue $GfxIni 'WindowHeight')"
            "WindowMode=$(Get-IniValue $GfxIni 'WindowMode')"
        ) | Set-Content -Path $StateFile -Encoding utf8
    }

    $n = 0
    foreach ($f in Get-OurLiveFiles) {
        Rename-Item -Path $f.FullName -NewName ($f.Name + $OffSuffix) -Force
        $n++
    }
    # Windowed so DirectX renders at the REQUESTED size (fullscreen+dgVoodoo
    # renders panel-native and ignores sub-native requests).
    Set-IniValue $GfxIni "WindowWidth"  $Width
    Set-IniValue $GfxIni "WindowHeight" $Height
    Set-IniValue $GfxIni "WindowMode"   "Windowed"

    Write-Host "STOCK MODE: disabled $n of our files; ${Width}x${Height} Windowed."
    Write-Host "dgVoodoo + SC4TouchControls untouched. Launch and compare."
    Write-Host "Restore with:  .\Set-StockCompare.ps1 -Mode Ours"
}
else {
    $n = 0
    foreach ($dir in @($DocPlugins, $InstPlugins, (Join-Path $DocPlugins "zzz-SC4UIScale"))) {
        Get-ChildItem -Path $dir -Filter "*$OffSuffix" -ErrorAction SilentlyContinue | ForEach-Object {
            $orig = $_.Name.Substring(0, $_.Name.Length - $OffSuffix.Length)
            Move-Item -Path $_.FullName -Destination (Join-Path $dir $orig) -Force
            $n++
        }
    }
    if (Test-Path $StateFile) {
        foreach ($line in (Get-Content $StateFile)) {
            if ($line -match "^(\w+)=(.*)$") { Set-IniValue $GfxIni $Matches[1] $Matches[2] }
        }
        Remove-Item $StateFile -Force
    }
    Write-Host "OURS MODE: restored $n file(s) + saved graphics settings."
    Write-Host "Check the 'AutoScale: ... -> tier' line in SC4UIScale.log on next boot -
the tier follows the RESTORED resolution, so it is 3.00 at 3840x2160.
(This line used to hard-code 'tier 2.00' and was wrong for anyone not
running the 2x tier.)"
}

Write-Host ""
Show-Status
