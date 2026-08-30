# Check-ChannelYaml.ps1 - the ONE pre-flight over a channel yaml.
#
# Dot-sourced by BOTH _packaging\sc4pac\upstream-pr\Submit-PR.ps1 and
# _tests\Test-Sc4pacInstall.ps1. Through v4.5.1 the two carried verbatim
# copies of these checks (same regexes, same thresholds, same prose); two
# copies to update is one copy forgotten, and the 2026-08-30 audit found them
# already starting to drift. One function, two callers.
#
# Returns an ARRAY of failure strings; empty means clear. The caller decides
# whether a failure is fatal.

function Test-ChannelYaml {
    param(
        [Parameter(Mandatory)][string]$YamlPath,
        [string]$Owner = 'Drexel-Macintosh',
        # Repo root; when given, the yaml's version is checked against the
        # DLL's UISCALE_VERSION_STR - a channel entry for a version the code
        # does not carry poisons every user's install.
        [string]$Repo,
        # HEAD-request the asset url (network).
        [switch]$CheckAssetUrl,
        # Extra checks for a file that is about to go UPSTREAM: refuse the
        # annotated internal record (PR #199 shipped it verbatim, engineering
        # commentary, TODOs and a "Do not publish" line included).
        [switch]$ForUpstream
    )
    $yaml = Get-Content $YamlPath -Raw
    $fail = @()

    $hashes = ([regex]'sha256: "').Matches($yaml).Count
    $zeros  = ([regex]'sha256: "0{64}"').Matches($yaml).Count
    if ($hashes -lt 50) { $fail += "only $hashes sha256 entries - expected ~85" }
    if ($zeros -gt 0)   { $fail += "$zeros placeholder sha256 entries still present" }

    if ([regex]::IsMatch($yaml, '(?m)^lastModified:\s*"1970|(?m)^lastModified:\s*""')) {
        $fail += 'lastModified is still a placeholder'
    }

    $m = [regex]::Match($yaml, '(?m)^url:\s*"([^"]+)"')
    if (-not $m.Success) { $fail += 'no asset url in the yaml' }
    else {
        $url = $m.Groups[1].Value
        # The owner segment of THIS url is the string lint compares against
        # the group-to-github mapping - lint.py:581, gh_owner = m.group(1) of
        # the regex at :266. Not info.author, not the git remote.
        $urlOwner = [regex]::Match($url, '^https://github\.com/([^/]+)/').Groups[1].Value
        if ($urlOwner -ne $Owner) {
            $fail += "asset url owner '$urlOwner' != mapping owner '$Owner' - lint compares the URL segment, so the mapping would not match"
        }
        if ($CheckAssetUrl) {
            try {
                $head = Invoke-WebRequest -Uri $url -Method Head -MaximumRedirection 5 -UseBasicParsing -TimeoutSec 30
                Write-Output ("  asset reachable: HTTP {0}, {1:N0} bytes" -f $head.StatusCode, $head.Headers['Content-Length'])
            } catch {
                $fail += "asset URL is not reachable: $url"
            }
        }
    }

    if ($Repo) {
        $dirSrc = Join-Path $Repo 'src\SC4UIScaleDllDirector.cpp'
        $verSrc = Get-Content $dirSrc -Raw
        if ($verSrc -match '#define\s+UISCALE_VERSION_STR\s+"([0-9.]+)') {
            $dllVer = $Matches[1]
            if ($yaml -notmatch ('version:\s*"' + [regex]::Escape($dllVer) + '"')) {
                $fail += "yaml has no version: `"$dllVer`" entry - the DLL's UISCALE_VERSION_STR is $dllVer, and a channel entry for a different version poisons every install"
            }
        } else {
            $fail += "could not read UISCALE_VERSION_STR from $dirSrc"
        }
    }

    if ($ForUpstream) {
        if ($yaml -match 'Do not publish|STILL OUTSTANDING|ANNOTATED INTERNAL') {
            $fail += 'this is the annotated INTERNAL yaml - submit the file gen_channel.py --publish emits, never the internal record'
        }
        $comments = ([regex]'(?m)^\s*#').Matches($yaml).Count
        if ($comments -gt 60) {
            $fail += "the yaml carries $comments comment lines - the corpus norm is under 45, so this looks like the internal file"
        }
    }

    return ,$fail
}
