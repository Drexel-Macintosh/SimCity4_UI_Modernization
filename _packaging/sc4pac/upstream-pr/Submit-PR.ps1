# Submit the sc4pac channel PR: package + group-to-github mapping, in one PR.
#
# WHY THIS IS A SCRIPT AND NOT SOMETHING CLAUDE RAN. Opening a public pull
# request against someone else's repository, under your GitHub account, is an
# outward-facing action the permission layer blocks - correctly. Everything up
# to that point is already done; this runs the last four steps under your hand.
#
# WHAT IT SUBMITS, and why both files go together: upstream precedent is a
# SINGLE PR carrying the package and the config line (commit bd7c51ac, PR #164,
# did exactly this). All five existing group-to-github entries belong to groups
# that already have packages in the channel, so a mapping-only PR would add a
# mapping the linter never exercises and a maintainer cannot review.
#
#   .\Submit-PR.ps1 -WhatIf     show every step, change and push nothing
#   .\Submit-PR.ps1             do it
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Clone  = 'C:\Users\<user>\AppData\Local\Temp\sc4pac-pr\sc4pac',
    [string]$Group  = 'a-drexel',
    [string]$Owner  = 'Drexel-Macintosh',
    [string]$Branch = 'add-a-drexel-sc4-ui-scale'
)

$ErrorActionPreference = 'Stop'
# three levels up: upstream-pr -> sc4pac -> _packaging -> repo root
$repo    = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$pkgSrc  = Join-Path $repo '_packaging\sc4pac\drexel-sc4-ui-scale.yaml'
$prBody  = Join-Path $PSScriptRoot 'PR-BODY.md'

foreach ($p in @($Clone, $pkgSrc, $prBody)) {
    if (-not (Test-Path $p)) { throw "missing: $p" }
}

# ---- PRE-FLIGHT: every claim the PR rests on, checked before it is made ------
# A PR that fails lint after a maintainer looks at it costs them a round trip.
$yaml = Get-Content $pkgSrc -Raw
$fail = @()

$hashes  = ([regex]'sha256: "').Matches($yaml).Count
$zeros   = ([regex]'sha256: "0{64}"').Matches($yaml).Count
if ($hashes -lt 50) { $fail += "only $hashes sha256 entries - expected ~85" }
if ($zeros -gt 0)   { $fail += "$zeros placeholder sha256 entries still present" }

$m = [regex]::Match($yaml, '(?m)^url:\s*"([^"]+)"')
if (-not $m.Success) { $fail += 'no asset url in the package yaml' }
else {
    $url = $m.Groups[1].Value
    # The owner segment of THIS url is the string lint compares against the
    # mapping - lint.py:581, gh_owner = m.group(1) of the regex at :266. Not
    # info.author, not the git remote. Getting it wrong makes the PR useless.
    $urlOwner = [regex]::Match($url, '^https://github\.com/([^/]+)/').Groups[1].Value
    if ($urlOwner -ne $Owner) {
        $fail += "asset url owner '$urlOwner' != mapping owner '$Owner' - lint compares the URL segment, so the mapping would not match"
    }
    try {
        $head = Invoke-WebRequest -Uri $url -Method Head -MaximumRedirection 5 -UseBasicParsing -TimeoutSec 30
        Write-Output ("  asset reachable: HTTP {0}, {1:N0} bytes" -f $head.StatusCode, $head.Headers['Content-Length'])
    } catch {
        $fail += "asset URL is not reachable: $url"
    }
}

if ([regex]::IsMatch($yaml, '(?m)^lastModified:\s*"1970|(?m)^lastModified:\s*""')) {
    $fail += 'lastModified is still a placeholder'
}

if ($fail.Count) {
    Write-Output 'REFUSING to open the PR:'
    $fail | ForEach-Object { Write-Output "  - $_" }
    exit 1
}
Write-Output "  pre-flight clear: $hashes real checksums, 0 placeholders, asset live, owner matches"

# ---- 1. the package file -----------------------------------------------------
$pkgDst = Join-Path $Clone "src\yaml\$Group\sc4-ui-scale.yaml"
if ($PSCmdlet.ShouldProcess($pkgDst, 'copy package yaml')) {
    New-Item -ItemType Directory (Split-Path $pkgDst -Parent) -Force | Out-Null
    Copy-Item $pkgSrc $pkgDst -Force
}
Write-Output "  package -> src/yaml/$Group/sc4-ui-scale.yaml"

# ---- 2. the mapping ----------------------------------------------------------
# group-to-github is a SEQUENCE OF SINGLE-KEY MAPPINGS, not a mapping - proven
# by lint.py:569-570 iterating the list then each element's items. The list is
# in append order, not alphabetical, so the new entry goes last.
$cfgPath = Join-Path $Clone 'lint-config.yaml'
$cfg = Get-Content $cfgPath -Raw
$entry = "- ${Group}: $Owner"
if ($cfg -match [regex]::Escape($entry)) {
    Write-Output '  mapping already present - leaving lint-config.yaml alone'
} else {
    $anchor = [regex]::Match($cfg, '(?m)^group-to-github:\r?\n(?:- .*\r?\n)+')
    if (-not $anchor.Success) { throw 'could not find the group-to-github list in lint-config.yaml' }
    if ($PSCmdlet.ShouldProcess($cfgPath, "append '$entry'")) {
        $block = $anchor.Value.TrimEnd("`r","`n")
        $cfg = $cfg.Remove($anchor.Index, $anchor.Length).Insert($anchor.Index, "$block`n$entry`n")
        [System.IO.File]::WriteAllText($cfgPath, $cfg, (New-Object System.Text.UTF8Encoding($false)))
    }
    Write-Output "  mapping -> lint-config.yaml  ($entry)"
}

# ---- 3. commit and push ------------------------------------------------------
Push-Location $Clone
try {
    if ($PSCmdlet.ShouldProcess($Clone, 'commit and push')) {
        # PowerShell 5.1 wraps a native command's stderr in an ErrorRecord, and
        # under ErrorActionPreference=Stop that ABORTS THE SCRIPT - even for
        # git's harmless "LF will be replaced by CRLF" notice, at exit code 0.
        # Check $LASTEXITCODE instead, which is the only thing that means
        # failure here.
        $ErrorActionPreference = 'Continue'
        # This machine sets user.name/user.email PER REPO, not globally, so a
        # fresh clone under %TEMP% has no identity and `git commit` dies with
        # exit 128. Carry the identity across from the project repo rather than
        # hard-coding it here or writing a global config on the user's behalf.
        if (-not (git config user.email)) {
            git config user.name  (git -C $repo config user.name)
            git config user.email (git -C $repo config user.email)
            Write-Output "  set the clone's git identity from $repo"
        }
        git add lint-config.yaml "src/yaml/$Group/sc4-ui-scale.yaml"
        if ($LASTEXITCODE -ne 0) { throw "git add failed ($LASTEXITCODE)" }
        git commit -q -m "Add ${Group}:sc4-ui-scale and its group-to-github mapping"
        if ($LASTEXITCODE -ne 0) { throw "git commit failed ($LASTEXITCODE)" }
        git push -q -u origin $Branch
        if ($LASTEXITCODE -ne 0) { throw "git push failed ($LASTEXITCODE)" }
        $ErrorActionPreference = 'Stop'
    }
    Write-Output "  pushed $Branch"

    # ---- 4. the PR -----------------------------------------------------------
    if ($PSCmdlet.ShouldProcess('memo33/sc4pac', 'open pull request')) {
        # --head OWNER:BRANCH is REQUIRED for a cross-fork PR. Without it gh
        # looks for the branch on memo33/sc4pac itself and aborts with "you
        # must first push the current branch to a remote" - which is
        # misleading, because the push had already succeeded to the fork.
        gh pr create --repo memo33/sc4pac `
            --head "${Owner}:${Branch}" --base main `
            --title "Add ${Group}:sc4-ui-scale (SimCity 4 UI Modernization)" `
            --body-file $prBody
    }
} finally { Pop-Location }

Write-Output ''
Write-Output 'A PR showing no checks is EXPECTED, not broken: the validation'
Write-Output 'workflow has to be triggered by a maintainer for a first-time'
Write-Output 'contributor.'
