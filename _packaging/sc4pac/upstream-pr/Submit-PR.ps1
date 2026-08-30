# Submit the sc4pac channel PR: package + group-to-github mapping, in one PR.
#
# WHY THIS IS A SCRIPT AND NOT SOMETHING CLAUDE RAN. Opening a public pull
# request against someone else's repository, under your GitHub account, is an
# outward-facing action the permission layer blocks - correctly. Everything up
# to that point is already done; this runs the last steps under your hand.
#
# WHAT IT SUBMITS, and why both files go together: upstream precedent is a
# SINGLE PR carrying the package and the config line (commit bd7c51ac, PR #164,
# did exactly this). All five existing group-to-github entries belong to groups
# that already have packages in the channel, so a mapping-only PR would add a
# mapping the linter never exercises and a maintainer cannot review.
#
# WHAT IT SUBMITS IS THE LEAN FILE. PR #199 shipped the annotated internal
# yaml verbatim - 211 comment lines of engineering record including a "Do not
# publish" line. The submission source is now the file
# `gen_channel.py --publish` emits, and the pre-flight refuses the internal
# record outright.
#
#   .\Submit-PR.ps1 -WhatIf     show every step, change and push nothing
#   .\Submit-PR.ps1             do it
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # A machine-local scratch clone; derived from TEMP, never hard-coded to a
    # user profile (the repo's own Sync-Check.ps1 flags committed user paths).
    [string]$Clone  = (Join-Path $env:TEMP 'sc4pac-pr\sc4pac'),
    [string]$Group  = 'a-drexel',
    [string]$Owner  = 'Drexel-Macintosh',
    [string]$Branch = 'add-a-drexel-sc4-ui-scale',
    [string]$Upstream = 'memo33/sc4pac'
)

$ErrorActionPreference = 'Stop'
# three levels up: upstream-pr -> sc4pac -> _packaging -> repo root
$repo    = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$pkgSrc  = Join-Path $repo '_packaging\sc4pac\publish\sc4-ui-scale.yaml'
$prBody  = Join-Path $PSScriptRoot 'PR-BODY.md'

foreach ($p in @($pkgSrc, $prBody)) {
    if (-not (Test-Path $p)) {
        if ($p -eq $pkgSrc) {
            throw "missing: $p - run gen_channel.py --publish --last-modified <release publish time> first"
        }
        throw "missing: $p"
    }
}

# ---- 0. the clone ------------------------------------------------------------
# Created on demand: the first run of the old script threw "missing: <clone>"
# because nothing ever created it, and Windows temp cleanup deletes it between
# sessions anyway. Cloning the FORK (origin = the account that opens the PR);
# the branch is based on the UPSTREAM main fetched directly by URL, so a stale
# fork default branch cannot poison the base.
if (-not (Test-Path $Clone)) {
    if ($PSCmdlet.ShouldProcess($Clone, "clone $Owner/sc4pac")) {
        New-Item -ItemType Directory (Split-Path $Clone -Parent) -Force | Out-Null
        $ErrorActionPreference = 'Continue'
        gh repo clone "$Owner/sc4pac" $Clone -- --depth=50
        if ($LASTEXITCODE -ne 0) { throw "gh repo clone failed ($LASTEXITCODE) - fork $Owner/sc4pac missing? (gh repo fork $Upstream)" }
        $ErrorActionPreference = 'Stop'
    }
    Write-Output "  cloned $Owner/sc4pac -> $Clone"
}

# ---- PRE-FLIGHT: every claim the PR rests on, checked before it is made ------
# A PR that fails lint after a maintainer looks at it costs them a round trip.
# The checks live in ONE shared file (Check-ChannelYaml.ps1), dot-sourced here
# and by _tests\Test-Sc4pacInstall.ps1 - they used to be verbatim copies.
. (Join-Path $repo '_packaging\sc4pac\Check-ChannelYaml.ps1')
$fail = Test-ChannelYaml -YamlPath $pkgSrc -Owner $Owner -Repo $repo -CheckAssetUrl -ForUpstream
if ($fail.Count) {
    Write-Output 'REFUSING to open the PR:'
    $fail | ForEach-Object { Write-Output "  - $_" }
    exit 1
}
Write-Output '  pre-flight clear: hashes real, asset live, owner matches, lean file confirmed'

Push-Location $Clone
try {
    # ---- 1. the branch, based on UPSTREAM main -------------------------------
    if ($PSCmdlet.ShouldProcess($Clone, "checkout -B $Branch from $Upstream/main")) {
        # PowerShell 5.1 wraps a native command's stderr in an ErrorRecord, and
        # under ErrorActionPreference=Stop that ABORTS THE SCRIPT - even for
        # git's harmless progress chatter at exit code 0. Check $LASTEXITCODE,
        # which is the only thing that means failure here.
        $ErrorActionPreference = 'Continue'
        git fetch "https://github.com/$Upstream.git" main
        if ($LASTEXITCODE -ne 0) { throw "git fetch upstream failed ($LASTEXITCODE)" }
        # -B, not -b: the old script never created the branch at all - on a
        # fresh clone the commit landed on main and the push died with
        # "src refspec does not match any". Re-running is also now safe.
        git checkout -B $Branch FETCH_HEAD
        if ($LASTEXITCODE -ne 0) { throw "git checkout -B failed ($LASTEXITCODE)" }
        $ErrorActionPreference = 'Stop'
    }

    # ---- 2. the package file -------------------------------------------------
    $pkgDst = Join-Path $Clone "src\yaml\$Group\sc4-ui-scale.yaml"
    if ($PSCmdlet.ShouldProcess($pkgDst, 'copy package yaml (lean)')) {
        New-Item -ItemType Directory (Split-Path $pkgDst -Parent) -Force | Out-Null
        Copy-Item $pkgSrc $pkgDst -Force
    }
    Write-Output "  package -> src/yaml/$Group/sc4-ui-scale.yaml"

    # ---- 3. the mapping ------------------------------------------------------
    # group-to-github is a SEQUENCE OF SINGLE-KEY MAPPINGS, not a mapping -
    # proven by lint.py:569-570 iterating the list then each element's items.
    # The list is in append order, not alphabetical, so the new entry goes last.
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

    # ---- 4. commit and push --------------------------------------------------
    if ($PSCmdlet.ShouldProcess($Clone, 'commit and push')) {
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
        git push -q -f -u origin $Branch
        if ($LASTEXITCODE -ne 0) { throw "git push failed ($LASTEXITCODE)" }
        $ErrorActionPreference = 'Stop'
    }
    Write-Output "  pushed $Branch"

    # ---- 5. the PR -----------------------------------------------------------
    if ($PSCmdlet.ShouldProcess($Upstream, 'open pull request')) {
        # --head OWNER:BRANCH is REQUIRED for a cross-fork PR. Without it gh
        # looks for the branch on the upstream repo itself and aborts with "you
        # must first push the current branch to a remote" - which is
        # misleading, because the push had already succeeded to the fork.
        gh pr create --repo $Upstream `
            --head "${Owner}:${Branch}" --base main `
            --title "Add ${Group}:sc4-ui-scale (SimCity 4 UI Modernization)" `
            --body-file $prBody
    }
} finally { Pop-Location }

Write-Output ''
Write-Output 'A PR showing no checks is EXPECTED, not broken: the validation'
Write-Output 'workflow has to be triggered by a maintainer for a first-time'
Write-Output 'contributor.'
