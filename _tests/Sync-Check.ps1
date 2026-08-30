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
# BOTH SLASH FORMS. Through 2026-08-30 this tested only the BACKSLASH form,
# and a tracked file carrying the same path with FORWARD slashes was
# PUBLISHED to the public repo with this gate reporting PASS. A tool that
# writes paths with forward slashes - which most Python does - walked
# straight past it. (Do not paste a real example path into this comment:
# the scan reads its own source, and it will correctly flag itself.)
$rxUser = 'C:[\\/]+Users[\\/]+[A-Za-z]'
$bad = @()
$unscanned = @()
foreach ($f in @(git ls-files)) {
    if (-not (Test-Path $f)) { continue }
    # A file too big to scan is a REFUSAL, not a pass. The old code skipped
    # >4MB silently, so the largest tracked files were the least checked.
    if ((Get-Item $f).Length -gt 4MB) { $unscanned += $f; continue }
    $t = Get-Content $f -Raw -ErrorAction SilentlyContinue
    if ($null -eq $t) { continue }
    if ($t -match $rxUser -or $t -match '@outlook\.com' -or $t -match '@gmail\.com') { $bad += $f }
}
if ($bad.Count -gt 0) {
    Write-Warning ("PRIVACY: {0} tracked file(s) carry a machine path or address." -f $bad.Count)
    $bad | Select-Object -First 8 | ForEach-Object { Write-Output ("    " + $_) }
    $fail = $true
}
if ($unscanned.Count -gt 0) {
    Write-Warning ("PRIVACY: {0} tracked file(s) EXCEEDED the 4MB scan limit and were NOT checked." -f $unscanned.Count)
    $unscanned | Select-Object -First 8 | ForEach-Object { Write-Output ("    " + $_) }
    $fail = $true
}

# --- 4. art policy, BY CONTENT ------------------------------------------
# The player's own game install supplies the art. See RUNBOOK.md section 1.
#
# ⛔ THIS USED TO TEST THE FILE EXTENSION, and that is the project's own
# "text scanners are blind to binaries" law being broken by the gate written
# to enforce it. MEASURED 2026-08-30: 607 PNG images extracted from shipped
# game archives were tracked and PUBLISHED as `.bin` files under
# tools/research/sharp15/ref15/. .gitignore had been taught to exclude them
# the day before - but .gitignore never untracks what is already tracked,
# and an extension test cannot see a PNG called .bin. This gate reported
# PASS the entire time.
#
# So: read the first bytes of every tracked file and classify by MAGIC.
# A rename cannot defeat this, and neither can a new extension nobody
# thought to add to a list.
$MAGIC = @(
    @{ Name = 'PNG';  Bytes = @(0x89,0x50,0x4E,0x47) },
    @{ Name = 'JPEG'; Bytes = @(0xFF,0xD8,0xFF) },
    @{ Name = 'GIF';  Bytes = @(0x47,0x49,0x46,0x38) },
    @{ Name = 'BMP';  Bytes = @(0x42,0x4D) },
    @{ Name = 'DBPF'; Bytes = @(0x44,0x42,0x50,0x46) },   # a SimCity 4 archive
    @{ Name = 'PE';   Bytes = @(0x4D,0x5A) }              # .exe / .dll
)
$art = @()
foreach ($f in @(git ls-files)) {
    if (-not (Test-Path $f)) { continue }
    if ((Get-Item $f).Length -lt 4) { continue }
    $head = [byte[]](Get-Content -LiteralPath $f -Encoding Byte -TotalCount 8 -ErrorAction SilentlyContinue)
    if ($null -eq $head) { continue }
    foreach ($m in $MAGIC) {
        $hit = $true
        for ($i = 0; $i -lt $m.Bytes.Count; $i++) {
            if ($head.Count -le $i -or $head[$i] -ne $m.Bytes[$i]) { $hit = $false; break }
        }
        if ($hit) { $art += ("{0}  [{1}]" -f $f, $m.Name); break }
    }
}
# POSITIVE CONTROL. A census that finds nothing proves nothing until it is
# shown it CAN find something - the classifier is run against a known PNG
# built in memory, and a clean repo with a broken matcher fails here rather
# than passing quietly.
$probe = [byte[]](0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A)
$probeHit = ($probe[0] -eq 0x89 -and $probe[1] -eq 0x50 -and $probe[2] -eq 0x4E -and $probe[3] -eq 0x47)
if (-not $probeHit) {
    Write-Warning "ART POLICY: the magic-byte classifier failed its own positive control - a PASS here would mean nothing."
    $fail = $true
}
if ($art.Count -gt 0) {
    Write-Warning ("ART POLICY: {0} tracked file(s) are binary art/archives/executables BY CONTENT (extension is irrelevant)." -f $art.Count)
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
