<#
Test-GameFolderClean.ps1 - assert we leave NOTHING in the game's own folder.

WHY THIS EXISTS
===============
A player reported finding a file of ours in
    C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Plugins
after a normal shutdown, while the shipped README promised "after a clean exit
there is nothing there to delete".

Both were true at once. The mod put its font at <install>\Plugins\FontStyle.ini
while running - it has to, because the game reads a loose font from exactly two
fixed paths and looks inside no mod folder - and on exit it RENAMED that file
to FontStyle.ini.x1-disabled rather than removing it. So every clean shutdown
left a 23 KB file in Program Files, permanently, under a name carrying none of
the z_SC4UIScale_ marking every other file of ours uses. That is the #182
landmine (a stray file a hand-cleanup cannot recognise as ours) reintroduced
with a different suffix, and nothing in the regression net looked at that
folder at all.

⛔ THE GAP WAS NEVER THE BEHAVIOUR - IT WAS THAT NOTHING WATCHED THE FOLDER.
Every existing gate inspects the Documents Plugins tree, which is ours. The
game's own install folder is where the damage lands and where no test looked.

SCOPE, honestly stated: this asserts the RESTING state, so run it with the game
CLOSED. While the game is running a live FontStyle.ini there is correct and
expected - that is the whole mechanism - so a "failure" during a session is the
mod working.

Usage:  .\_tests\Test-GameFolderClean.ps1
Exit 0 when the folder holds nothing of ours.
#>
[CmdletBinding()]
param(
    [string]$GameDir = $(if ($env:SC4_GAME_DIR) { $env:SC4_GAME_DIR }
                         else { "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe" })
)

$ErrorActionPreference = 'Stop'
$fail = @()
$warn = @()

$plug = Join-Path $GameDir 'Plugins'
Write-Output "Game folder: $GameDir"

if (-not (Test-Path $plug)) {
    Write-Output "SKIP - no Plugins folder at $plug (game not installed here)."
    exit 0
}

# Is the game running? Then a live font is CORRECT and this gate cannot judge.
$running = @(Get-Process -Name 'SimCity 4' -ErrorAction SilentlyContinue).Count -gt 0
if ($running) {
    Write-Output "SKIP - SimCity 4 is RUNNING. A live FontStyle.ini in that"
    Write-Output "folder is the mechanism working; this gate judges the state"
    Write-Output "AFTER a clean shutdown. Close the game and re-run."
    exit 0
}

# --- what counts as ours, and why -----------------------------------------
# The tier sources we ship are the ground truth: anything byte-identical to one
# of them is ours no matter what it is called. That is the same "proven ours,
# not assumed ours" test the DLL uses before it deletes anything.
$docPlug = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'SimCity 4\Plugins'
$srcDir  = Join-Path $docPlug '010-SC4UIScale'
$ourHashes = @{}
if (Test-Path $srcDir) {
    Get-ChildItem $srcDir -Filter 'FontStyle-*.ini' -File -ErrorAction SilentlyContinue |
        ForEach-Object { $ourHashes[(Get-FileHash $_.FullName -Algorithm SHA256).Hash] = $_.Name }
}
Write-Output ("tier font sources known: {0}" -f $ourHashes.Count)
if ($ourHashes.Count -eq 0) {
    # A gate that cannot recognise its own subject must say so rather than pass.
    Write-Output ""
    Write-Output "REFUSED - no tier font sources found under $srcDir, so this"
    Write-Output "gate cannot tell our files from a third party's. That is a"
    Write-Output "broken instrument, not a clean folder."
    Write-Output "GAME-FOLDER: REFUSED"
    exit 1
}

# --- 1. nothing of ours may rest in the game's Plugins folder --------------
$suspects = @()
$suspects += Get-ChildItem $plug -Filter 'FontStyle*' -File -ErrorAction SilentlyContinue
$suspects += Get-ChildItem $plug -Filter 'z_SC4UIScale_*' -File -ErrorAction SilentlyContinue
$suspects += Get-ChildItem $plug -Filter 'SC4UIScale*' -File -ErrorAction SilentlyContinue

foreach ($f in $suspects) {
    # A user's OWN font, and our preserved copy of it, are not ours to remove.
    if ($f.Name -eq 'FontStyle.ini.user-original') {
        $warn += "$($f.Name) - the player's preserved original, correctly left alone"
        continue
    }
    # OUR MARKER FIRST. From 2026-08-31 the DLL stamps the font it writes with
    # a ';' header naming the mod, precisely so a copy stranded by a crash says
    # whose it is. That beats byte-identity, which stops recognising anything
    # the moment a tier source is regenerated.
    $head = ''
    try { $head = (Get-Content $f.FullName -TotalCount 3 -ErrorAction Stop) -join "`n" } catch { }
    if ($head -match 'SC4UIScale:') {
        $fail += ("{0} carries OUR OWN generated-file header and is resting in the GAME folder ({1:N0} bytes)" -f `
                  $f.Name, $f.Length)
        continue
    }
    $h = (Get-FileHash $f.FullName -Algorithm SHA256).Hash
    if ($ourHashes.ContainsKey($h)) {
        $fail += ("{0} is byte-identical to our own {1} ({2:N0} bytes) and is resting in the GAME folder" -f `
                  $f.Name, $ourHashes[$h], $f.Length)
    } elseif ($f.Length -eq 0) {
        $fail += ("{0} is an empty file of ours (#182 placeholder shape) resting in the GAME folder" -f $f.Name)
    } elseif ($f.Name -like 'FontStyle.ini*') {
        # Not provably ours - could be a third-party font mod. Report, do not fail.
        $warn += ("{0} is NOT one of ours (not byte-identical to any tier source) - left alone" -f $f.Name)
    } else {
        $fail += ("{0} carries our naming and is resting in the GAME folder" -f $f.Name)
    }
}

# --- 2. the install ROOT is the second probe path; check it too ------------
foreach ($n in @('FontStyle.ini', 'FontStyle.ini.x1-disabled')) {
    $t = Join-Path $GameDir $n
    if (Test-Path $t) {
        $h = (Get-FileHash $t -Algorithm SHA256).Hash
        if ($ourHashes.ContainsKey($h) -or (Get-Item $t).Length -eq 0) {
            $fail += ("$n is ours and is resting at the INSTALL ROOT (the second probe path)")
        } else {
            $warn += "$n at the install root is not ours - left alone"
        }
    }
}

Write-Output ""
foreach ($w in $warn) { Write-Output "  note: $w" }
if ($fail.Count) {
    Write-Output ""
    Write-Output "$($fail.Count) finding(s):"
    foreach ($f in $fail) { Write-Output "  FAIL $f" }
    Write-Output ""
    Write-Output "GAME-FOLDER: FAIL - we are leaving files in the player's game"
    Write-Output "install. Delete them, and fix whatever put them there: the"
    Write-Output "shipped README promises this folder is left clean."
    exit 1
}
Write-Output "GAME-FOLDER: PASS - nothing of ours rests in the game install."
Write-Output "This is a RESTING-STATE result. It says nothing about what the"
Write-Output "mod does while the game is running, which is when the font is"
Write-Output "deliberately present at <install>\Plugins\FontStyle.ini."
exit 0
