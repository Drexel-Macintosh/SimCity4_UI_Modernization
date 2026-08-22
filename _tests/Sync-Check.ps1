# Sync-Check - the repo IS the project. Fails if work is not committed+pushed.
#
# WHY THIS EXISTS. On 2026-08-18 an audit found the GitHub repo carried 2.8%
# of files and was missing three of eight package builders. Nobody knew,
# because "is it committed?" was never a gate. It is now.
#
# The privacy scan runs over the TRACKED SET ONLY (git ls-files), never the
# working tree - the tree holds ~2.3 GB of deliberately-ignored archives and
# scanning those is a guaranteed false FAIL. That mistake was made once.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
$fail = $false

# --- 1. uncommitted work -------------------------------------------------
$dirty = @(git status --porcelain)
if ($dirty.Count -gt 0) {
    Write-Warning ("UNCOMMITTED: {0} path(s). A finding that is not committed does not exist." -f $dirty.Count)
    $dirty | Select-Object -First 10 | ForEach-Object { Write-Output ("    " + $_) }
    $fail = $true
}

# --- 2. unpushed commits -------------------------------------------------
git fetch -q origin 2>$null
$ahead = git rev-list --count "@{u}..HEAD" 2>$null
if ($ahead -and ([int]$ahead) -gt 0) {
    Write-Warning ("{0} commit(s) NOT PUSHED." -f $ahead)
    $fail = $true
}

# --- 3. privacy, tracked files only --------------------------------------
$bad = @()
foreach ($f in @(git ls-files)) {
    if (-not (Test-Path $f)) { continue }
    if ((Get-Item $f).Length -gt 4MB) { continue }
    $t = Get-Content $f -Raw -ErrorAction SilentlyContinue
    if ($null -eq $t) { continue }
    if ($t -match 'C:\\Users\\[A-Za-z]' -or $t -match '@outlook\.com' -or $t -match '@gmail\.com') { $bad += $f }
}
if ($bad.Count -gt 0) {
    Write-Warning ("PRIVACY: {0} tracked file(s) carry a machine path or address." -f $bad.Count)
    $bad | Select-Object -First 8 | ForEach-Object { Write-Output ("    " + $_) }
    $fail = $true
}

# --- 4. art policy -------------------------------------------------------
# The player's own game install supplies the art. See RUNBOOK.md section 1.
$art = @(git ls-files | Where-Object { $_ -match '\.(dat|png|jpg|jpeg|bmp|fsh|exe|dll|pdb)$' })
if ($art.Count -gt 0) {
    Write-Warning ("ART POLICY: {0} binary/art file(s) tracked." -f $art.Count)
    $art | Select-Object -First 8 | ForEach-Object { Write-Output ("    " + $_) }
    $fail = $true
}

$n = @(git ls-files).Count
Pop-Location
if ($fail) {
    Write-Output ""
    Write-Output "SYNC-CHECK: FAIL"
    exit 1
}
Write-Output ("SYNC-CHECK: PASS - {0} tracked files, clean, pushed." -f $n)
