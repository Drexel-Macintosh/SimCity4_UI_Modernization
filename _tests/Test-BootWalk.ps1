# The DLL's BOOT WALKS, lifted and run against a synthetic Plugins tree with
# known answers - and TIMED. The "20 GB boot harness".
#
# WHY THIS EXISTS. Every boot the DLL walks the whole Plugins tree several
# times before the game has opened a single dat: the folder discovery
# (ScanForOurDirs, depth 3), the uncovered-icon scan (IconSynth::Walk twice
# per root, ReadIconTgis on every DBPF), and one depth-4 FindPluginFile walk
# per distinct third-party dependency name. On the developer's tree that is a
# few seconds; on a 20 GB, 50,000-file sc4pac tree nothing had ever measured
# it, and three of its blind spots were known only from reading the code:
#   * ReadIconTgis refuses any index with 200,000 entries or more, so the
#     icons in such a file are simply not counted (uncovered = lower bound);
#   * FindPluginFile builds every path in a MAX_PATH buffer, so a dependency
#     past 260 characters cannot be found - and, measured here, the secure
#     CRT's response to that overflow is to TERMINATE THE PROCESS (exit
#     0xC0000409), not to return false;
#   * FindPluginFile's depth-4 budget reaches a file three directories below
#     Plugins and not four.
# Those three are the EXPECTED FAILURES of the current code. They are
# positive controls: the harness must SEE them, and reports them as expected
# rather than hiding them. When the walks are reworked they flip to FIXED.
#
# HOW IT WORKS. Three regions are lifted VERBATIM out of ScaleTier.cpp by
# sentinel (FOLDER-DISCOVERY, DEP-WALK, BOOT-WALK), compiled standalone with
# the DLL-side symbols stubbed (Logger, LogLevel, PerfProbe, PluginsRootQuiet,
# InstallPluginsDir) and FindFirstFileW / FindNextFileW / CreateFileW wrapped
# in counting macros, then run against trees that _tests\New-SyntheticPlugins.py
# builds and describes in manifest.json. Every count the walks produce is
# checked against that answer key; every phase is timed; the table is the
# deliverable. -Source lifts from a file or a git ref so the baseline can be
# taken from the pre-rework commit while the working tree changes underneath.
#
# DANGER: THIS WRITES N FILES (per -Files value) under -ScaleRoot (default
# C:\dev\_scale) through the generator, which refuses OneDrive, Documents\
# SimCity 4 and the game install. Trees are kept between runs (the generator
# reuses them by parameter fingerprint); -Clean removes them at the end.
# Never touches the live game install or the player's Plugins tree.
#
#   .\_tests\Test-BootWalk.ps1                              # N=1000, working-tree source
#   .\_tests\Test-BootWalk.ps1 -Files 1000,10000,50000 -Source 3f2608b -Record
#   .\_tests\Test-BootWalk.ps1 -Mutate                      # prove it can go red
[CmdletBinding()]
param(
    # DBPF counts, one tree each. Accepts 1000,10000,50000 as one string too,
    # which is how `powershell -File` hands an array over.
    [string[]]$Files = @('1000'),
    [int]$IconsPerFile = 8,
    [int]$PngSubset = 200,
    [int]$LongPaths = 20,
    [bool]$BigIndex = $true,
    [ValidateSet(3, 4)][int]$NamDepth = 3,
    [int]$Seed = 1,
    [string]$ScaleRoot = 'C:\dev\_scale',
    [string]$Bundle,
    # A file path, or a git ref resolved as <ref>:src/ScaleTier.cpp. Default:
    # the working tree.
    [string]$Source,
    [switch]$Record,
    [switch]$Mutate,
    [switch]$Junction,
    [switch]$Clean,
    [switch]$EchoLog
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$work = Join-Path $env:TEMP "sc4uiscale-bootwalk-$PID"
$FileSizes = @($Files | ForEach-Object { "$_" -split ',' } | Where-Object { $_ -match '^\s*\d+\s*$' } | ForEach-Object { [int]$_ })
if ($FileSizes.Count -eq 0) { throw "-Files needs one or more integers (got '$Files')" }
$baselinePath = Join-Path $repo '_tests\golden\bootwalk-baseline.json'
$generator = Join-Path $repo '_tests\New-SyntheticPlugins.py'
$STATUS_STACK_BUFFER_OVERRUN = -1073740791   # 0xC0000409, the CRT fast-fail

if (-not $Bundle) {
    $Bundle = Get-ChildItem (Join-Path $repo 'dist') -Directory -Filter 'SC4UIScale-v*' -EA SilentlyContinue |
              Where-Object { $_.Name -notlike '*-dev' } |
              Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $Bundle -or -not (Test-Path (Join-Path $Bundle 'Plugins'))) {
    throw "no built bundle found; pass -Bundle <dist\SC4UIScale-vX.Y.Z>"
}
$bundlePlugins = Join-Path $Bundle 'Plugins'
Write-Output "bundle: $Bundle"

if (Test-Path $work) { Remove-Item -LiteralPath $work -Recurse -Force }
New-Item -ItemType Directory $work -Force | Out-Null
$cwdEmpty = Join-Path $work 'empty-cwd'
New-Item -ItemType Directory $cwdEmpty -Force | Out-Null

# ---- THE SOURCE: a file, or a git ref ---------------------------------------
if (-not $Source) { $Source = Join-Path $repo 'src\ScaleTier.cpp' }
if (Test-Path -LiteralPath $Source -PathType Leaf) {
    $srcFile = (Resolve-Path -LiteralPath $Source).Path
    $srcLabel = "file:$srcFile"
} else {
    $srcFile = Join-Path $work 'ScaleTier.lifted.cpp'
    $txt = & git -C $repo show "${Source}:src/ScaleTier.cpp" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "-Source '$Source' is neither a file nor a git ref that has src/ScaleTier.cpp: $txt" }
    [IO.File]::WriteAllText($srcFile, ($txt -join "`n"), (New-Object Text.UTF8Encoding($false)))
    $srcLabel = "git:$Source"
}
Write-Output "source: $srcLabel"

# ---- LIFT THE CODE -----------------------------------------------------------
$lines = Get-Content -LiteralPath $srcFile
function Lift-Region([string]$name, [string[]]$mustContain) {
    $b = ($lines | Select-String -SimpleMatch "==== BEGIN $name" | Select-Object -First 1).LineNumber
    $e = ($lines | Select-String -SimpleMatch "==== END $name"   | Select-Object -First 1).LineNumber
    if (-not $b -or -not $e -or $e -le $b) {
        throw "$name sentinels not found in $srcLabel - the harness cannot lift the code it is meant to cover"
    }
    $region = $lines[$b..($e - 2)] -join "`r`n"
    foreach ($fn in $mustContain) {
        if ($region -notmatch [regex]::Escape($fn)) { throw "lifted $name region does not contain $fn - extraction is wrong" }
    }
    # Write-Host, not Write-Output: this function RETURNS the region, and
    # anything written to the output stream would ride along in the return.
    Write-Host "lifted $name`: $($e - $b - 1) lines ($b..$e)"
    return $region
}
$regDisc = Lift-Region 'FOLDER-DISCOVERY' @('ClassifyDir', 'ScanForOurDirs', 'ResolveOurDirs')
$regDep  = Lift-Region 'DEP-WALK'         @('FindPluginFile', 'FindFirstFileW')
$regBoot = Lift-Region 'BOOT-WALK'        @('kLongPath', 'void Walk(', 'bool ReadIconTgis(', 'gLongPathsSeen')

# The two generations of the walk API, told apart by the lifted text, so one
# harness serves the pre-rework blob (the baseline) and the working tree.
$walkFd   = [bool]($regBoot -match 'const WIN32_FIND_DATAW&')
$tgiFull  = [bool]($regBoot -match 'onTgi\)\(uint32_t,\s*uint32_t,\s*uint32_t,\s*void\*\)')
$hasIndex = [bool]($lines | Select-String -SimpleMatch '==== BEGIN BOOT-INDEX' | Select-Object -First 1)
$regIndex = ''
if ($hasIndex) { $regIndex = Lift-Region 'BOOT-INDEX' @('namespace BootIndex', 'FindDep', 'AnyNameContains', 'TopLevelFolders') }
Write-Output ("API: Walk callback {0}; ReadIconTgis callback {1}; BOOT-INDEX region: {2}" -f
    $(if ($walkFd) { '(full, WIN32_FIND_DATAW&, ctx)' } else { '(full, name, ctx)' }),
    $(if ($tgiFull) { '(t, g, i, ctx) for every entry' } else { '(i, ctx), icons only' }),
    $(if ($hasIndex) { 'lifted (bootindex phase enabled)' } else { 'none' }))
$defines = "#define BW_WALK_FD $([int]$walkFd)`r`n#define BW_TGI_FULL $([int]$tgiFull)`r`n#define BW_HAS_INDEX $([int]$hasIndex)"

# The BOOT-WALK sentinel opens at kLongPath, so four helpers Walk/ReadIconTgis
# need sit just ABOVE it in the source: kIconType, kIconGroup, IsDbpfName,
# IsOurPackage, and the Fingerprint struct. The harness carries COPIES and
# checks each one against the source text, so a change there fails this
# build instead of silently measuring a different predicate.
$srcText = $lines -join "`n"
$helperChecks = @(
    @{ what = 'kIconType';     rx = 'kIconType\s*=\s*0x856DDBAC' },
    @{ what = 'kIconGroup';    rx = 'kIconGroup\s*=\s*0x6A386D26' },
    @{ what = 'IsDbpfName .dat';      rx = '_wcsicmp\(dot,\s*L"\.dat"\)' },
    @{ what = 'IsDbpfName .sc4lot';   rx = '_wcsicmp\(dot,\s*L"\.sc4lot"\)' },
    @{ what = 'IsDbpfName .sc4desc';  rx = '_wcsicmp\(dot,\s*L"\.sc4desc"\)' },
    @{ what = 'IsDbpfName .sc4model'; rx = '_wcsicmp\(dot,\s*L"\.sc4model"\)' },
    @{ what = 'IsOurPackage prefix';  rx = '_wcsnicmp\(name,\s*L"z_SC4UIScale_",\s*13\)' },
    @{ what = 'Fingerprint struct';   rx = 'struct Fingerprint\s*\{\s*uint32_t files;\s*uint64_t bytes;\s*uint64_t newest;\s*\}' }
)
foreach ($c in $helperChecks) {
    if ($srcText -notmatch $c.rx) { throw "helper copy check failed: the source no longer matches the harness copy of $($c.what) - update the copy in Test-BootWalk.ps1" }
}
Write-Output "helper copies verified against the source ($($helperChecks.Count) checks)"

# ---- kThirdPartyDeps -> distinct needles (as Test-ThirdPartyGates.ps1 parses) ----
$block = [regex]::Match($srcText, 'kThirdPartyDeps\[\]\s*=\s*\{(?<body>.*?)\n\t\};', 'Singleline')
if (-not $block.Success) { throw 'could not parse kThirdPartyDeps out of the source' }
$rx = [regex]'\{\s*L"(?<pkg>[^"]+)",\s*L"(?<f1>(?:[^"\\]|\\.)*)",\s*(?<pre>true|false),\s*(?<s1>\d+),\s*(?:L"(?<f2>(?:[^"\\]|\\.)*)"|nullptr),\s*(?<s2>\d+)\s*\}'
$needles = [ordered]@{}
foreach ($m in $rx.Matches($block.Groups['body'].Value)) {
    $pre = ($m.Groups['pre'].Value -eq 'true')
    $pairs = @()
    $pairs += ,@(($m.Groups['f1'].Value -replace '\\\\', '\'), [int64]$m.Groups['s1'].Value)
    if ($m.Groups['f2'].Success) { $pairs += ,@(($m.Groups['f2'].Value -replace '\\\\', '\'), [int64]$m.Groups['s2'].Value) }
    foreach ($p in $pairs) {
        $key = "$($p[0].ToLowerInvariant())|$([int]$pre)"
        if (-not $needles.Contains($key)) { $needles[$key] = @{ name = $p[0]; prefix = $pre; size = $p[1] } }
        elseif ($needles[$key].size -eq 0 -and $p[1] -ne 0) { $needles[$key].size = $p[1] }
    }
}
if ($needles.Count -lt 5) { throw "kThirdPartyDeps parsed as $($needles.Count) needle(s) - parse is wrong" }
Write-Output "needles: $($needles.Count) distinct (name, prefix) pairs from kThirdPartyDeps"
$needlesFile = Join-Path $work 'needles.tsv'
$tsv = ($needles.Values | ForEach-Object { "$($_.name)`t$([int]$_.prefix)`t$($_.size)" }) -join "`n"
[IO.File]::WriteAllText($needlesFile, $tsv + "`n", (New-Object Text.UTF8Encoding($false)))

# ---- THE HARNESS SOURCE ------------------------------------------------------
$harnessTemplate = @'
// GENERATED by _tests/Test-BootWalk.ps1 - do not edit.
// The three regions marked LIFTED are verbatim from src/ScaleTier.cpp.
#ifndef BOOTWALK_HARNESS
#error "build with /DBOOTWALK_HARNESS"
#endif
// API shape of the lifted BOOT-WALK, detected from its text by the driver:
//   BW_WALK_FD   onFile(full, const WIN32_FIND_DATAW&, ctx)  (else: full, name, ctx)
//   BW_TGI_FULL  onTgi(t, g, i, ctx) for EVERY entry           (else: onTgi(i, ctx), icons only)
//   BW_HAS_INDEX a BOOT-INDEX region was lifted too
//@@DEFINES@@
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <wchar.h>
#include <cwctype>
#include <string>
#include <vector>
#include <algorithm>
#include <iterator>

// ---- COUNTING WRAPPERS. Defined BEFORE the macros so they reach the real
// functions; everything below (the lifted code included) goes through them.
static long long gFinds = 0, gNexts = 0, gOpens = 0, gCrtTrunc = 0;
static HANDLE CountedFindFirstFileW(LPCWSTR p, LPWIN32_FIND_DATAW fd) { gFinds++; return ::FindFirstFileW(p, fd); }
static BOOL CountedFindNextFileW(HANDLE h, LPWIN32_FIND_DATAW fd) { gNexts++; return ::FindNextFileW(h, fd); }
static HANDLE CountedCreateFileW(LPCWSTR a, DWORD b, DWORD c, LPSECURITY_ATTRIBUTES d, DWORD e, DWORD f, HANDLE g)
{ gOpens++; return ::CreateFileW(a, b, c, d, e, f, g); }
#define FindFirstFileW CountedFindFirstFileW
#define FindNextFileW  CountedFindNextFileW
#define CreateFileW    CountedCreateFileW

// ---- STUBS for the DLL-side symbols the lifted regions touch.
enum class LogLevel : int { Error = 0, Info = 1, Debug = 2, Trace = 3 };
namespace PerfProbe
{
    unsigned long long NowUs() { return 0; }
    void Add(const char*, unsigned long long) {}
    class Scope { public: explicit Scope(const char*) {} };
}
class Logger
{
public:
    static Logger& Get() { static Logger l; return l; }
    void WriteLine(LogLevel, const char* fmt, ...)
    {
        lines++;
        if (!echo) { return; }
        va_list ap; va_start(ap, fmt); vfprintf(stderr, fmt, ap); fputc('\n', stderr); va_end(ap);
    }
    int lines = 0;
    bool echo = false;
};

static double NowMs()
{
    static LARGE_INTEGER f = {};
    if (!f.QuadPart) { QueryPerformanceFrequency(&f); }
    LARGE_INTEGER c; QueryPerformanceCounter(&c);
    return c.QuadPart * 1000.0 / f.QuadPart;
}
struct Snap { long long finds, nexts, opens; double t; };
static Snap Take() { Snap s = { gFinds, gNexts, gOpens, NowMs() }; return s; }
static void Row(const char* phase, const Snap& s0, long long count, const char* note = "")
{
    Snap s1 = Take();
    printf("ROW\t%s\t%.1f\t%lld\t%lld\t%lld\t%lld\t%s\n", phase, s1.t - s0.t, count,
        s1.finds - s0.finds, s1.nexts - s0.nexts, s1.opens - s0.opens, note);
    fflush(stdout);
}

namespace
{
    wchar_t gRoot[MAX_PATH];          // Plugins root WITH trailing backslash
    wchar_t gRootNoSlash[MAX_PATH];   // the same without, as ScanUncoveredIcons hands it on
    wchar_t gInstallRoot[MAX_PATH];   // the <install>\Plugins stand-in, or ""
    bool PluginsRootQuiet(wchar_t* out, size_t outLen) { wcscpy_s(out, outLen, gRoot); return true; }
    void PluginsRoot(wchar_t* out, size_t outLen) { PluginsRootQuiet(out, outLen); }
    void InstallPluginsDir(wchar_t* out, size_t outLen) { wcscpy_s(out, outLen, gInstallRoot); }

    // ---- LIFTED: FOLDER-DISCOVERY ----
//@@FOLDER_DISCOVERY@@
    // ---- END LIFTED: FOLDER-DISCOVERY ----

    // ---- LIFTED: DEP-WALK ----
//@@DEP_WALK@@
    // ---- END LIFTED: DEP-WALK ----
}

namespace IconSynth
{
    // COPIES of the helpers that sit above the BOOT-WALK sentinel in the
    // source. Test-BootWalk.ps1 checks each against the source text.
    const uint32_t kIconType  = 0x856DDBAC;
    const uint32_t kIconGroup = 0x6A386D26;
    bool IsDbpfName(const wchar_t* name)
    {
        const wchar_t* dot = wcsrchr(name, L'.');
        if (!dot) { return false; }
        return _wcsicmp(dot, L".dat") == 0
            || _wcsicmp(dot, L".sc4lot") == 0
            || _wcsicmp(dot, L".sc4desc") == 0
            || _wcsicmp(dot, L".sc4model") == 0;
    }
    bool IsOurPackage(const wchar_t* name)
    {
        return _wcsnicmp(name, L"z_SC4UIScale_", 13) == 0;
    }
    struct Fingerprint
    {
        uint32_t files;
        uint64_t bytes;
        uint64_t newest;
    };

    // ---- LIFTED: BOOT-WALK ----
//@@BOOT_WALK@@
    // ---- END LIFTED: BOOT-WALK ----
#if BW_HAS_INDEX
    // ---- LIFTED: BOOT-INDEX ----
//@@BOOT_INDEX@@
    // ---- END LIFTED: BOOT-INDEX ----
#endif
}

// ---- The ScanAndReport driver loop, REPLICATED (it sits outside the
// sentinels and depends on engine types). Same shape: pass 1 collects OURS,
// pass 2 THEIRS, over root 1 then root 2; AddTgi dedupes with the same
// LINEAR scan the DLL uses; the diff is the same O(theirs x ours) loop.
namespace Scan
{
    struct State { std::vector<uint32_t> ours, theirs; bool collectingOurs; };
    static State gScan;
    static double gAddTgiMs = 0;
    static long long gAddTgiCalls = 0;
    static std::vector<std::wstring> gDbpfPaths;

    static void AddTgiInst(uint32_t inst)
    {
        const double t0 = NowMs();
        gAddTgiCalls++;
        std::vector<uint32_t>& list = gScan.collectingOurs ? gScan.ours : gScan.theirs;
        bool dup = false;
        for (size_t i = 0; i < list.size(); i++) { if (list[i] == inst) { dup = true; break; } }
        if (!dup) { list.push_back(inst); }
        gAddTgiMs += NowMs() - t0;
    }
#if BW_TGI_FULL
    static void AddTgi(uint32_t t, uint32_t g, uint32_t inst, void*)
    {
        if (t != IconSynth::kIconType || g != IconSynth::kIconGroup) { return; }
        AddTgiInst(inst);
    }
#else
    static void AddTgi(uint32_t inst, void*) { AddTgiInst(inst); }
#endif
    static void OnDbpf(const wchar_t* full, const wchar_t* name)
    {
        if (!IconSynth::IsDbpfName(name)) { return; }
        if (IconSynth::IsOurPackage(name) != gScan.collectingOurs) { return; }
        gDbpfPaths.push_back(full);
        IconSynth::ReadIconTgis(full, AddTgi, nullptr);
    }
#if BW_WALK_FD
    static void OnFile(const wchar_t* full, const WIN32_FIND_DATAW& fd, void*) { OnDbpf(full, fd.cFileName); }
#else
    static void OnFile(const wchar_t* full, const wchar_t* name, void*) { OnDbpf(full, name); }
#endif
}

static void PrefixRoot(wchar_t* out, size_t cap, const wchar_t* plain)
{
    if (wcsncmp(plain, L"\\\\?\\", 4) == 0) { swprintf_s(out, cap, L"%s", plain); }
    else { swprintf_s(out, cap, L"\\\\?\\%s", plain); }
}

static int RunDiscover()
{
    Snap s = Take();
    ResolveOurDirs();
    char note[256];
    sprintf_s(note, "earlyFound=%d ovrFound=%d earlyCand=%d ovrCand=%d",
        gOurDirs.earlyFound ? 1 : 0, gOurDirs.overrideFound ? 1 : 0, gEarlyCandidates, gOvrCandidates);
    Row("discover", s, gEarlyCandidates + gOvrCandidates, note);
    printf("DISCOVER\t%d\t%d\t%ls\t%ls\n", gOurDirs.earlyFound ? 1 : 0, gOurDirs.overrideFound ? 1 : 0,
        gOurDirs.earlyLeaf, gOurDirs.overrideLeaf);
    fflush(stdout);
    return 0;
}

static int RunWalk(const wchar_t* uncoveredOut)
{
    wchar_t root[IconSynth::kLongPath];
    PrefixRoot(root, IconSynth::kLongPath, gRootNoSlash);
    wchar_t root2[IconSynth::kLongPath] = L"";
    if (gInstallRoot[0])
    {
        wchar_t inst[MAX_PATH];
        wcscpy_s(inst, MAX_PATH, gInstallRoot);
        size_t n = wcslen(inst);
        while (n > 0 && inst[n - 1] == L'\\') { inst[--n] = 0; }
        if (_wcsicmp(inst, gRootNoSlash) != 0) { PrefixRoot(root2, IconSynth::kLongPath, inst); }
    }
    IconSynth::gLongPathsSeen = 0;
    Scan::gScan.ours.clear(); Scan::gScan.theirs.clear(); Scan::gDbpfPaths.clear();
    Scan::gAddTgiMs = 0; Scan::gAddTgiCalls = 0;
    const Snap all = Take();
    char note[512];

    Scan::gScan.collectingOurs = true;
    IconSynth::Fingerprint fp1a = {};
    Snap s = Take();
    IconSynth::Walk(root, fp1a, Scan::OnFile, nullptr);
    sprintf_s(note, "bytes=%llu ours=%zu", fp1a.bytes, Scan::gScan.ours.size());
    Row("walk-ours-root1", s, fp1a.files, note);
    if (root2[0])
    {
        IconSynth::Fingerprint fp1b = {};
        s = Take();
        IconSynth::Walk(root2, fp1b, Scan::OnFile, nullptr);
        Row("walk-ours-root2", s, fp1b.files);
    }
    const size_t nOurs = Scan::gScan.ours.size();

    Scan::gScan.collectingOurs = false;
    IconSynth::Fingerprint fp2a = {};
    s = Take();
    IconSynth::Walk(root, fp2a, Scan::OnFile, nullptr);
    sprintf_s(note, "bytes=%llu theirs=%zu longPathsSeen=%d", fp2a.bytes, Scan::gScan.theirs.size(), IconSynth::gLongPathsSeen);
    Row("walk-theirs-root1", s, fp2a.files, note);
    uint32_t files2 = 0;
    if (root2[0])
    {
        IconSynth::Fingerprint fp2b = {};
        s = Take();
        IconSynth::Walk(root2, fp2b, Scan::OnFile, nullptr);
        Row("walk-theirs-root2", s, fp2b.files);
        files2 = fp2b.files;
    }
    printf("ROW\taddtgi-linear-dedupe\t%.1f\t%lld\t0\t0\t0\tinside the walks above: AddTgi's linear dedupe scan, copied from ScanAndReport\n",
        Scan::gAddTgiMs, Scan::gAddTgiCalls);

    s = Take();
    std::vector<uint32_t> uncovered;
    for (size_t i = 0; i < Scan::gScan.theirs.size(); i++)
    {
        const uint32_t inst = Scan::gScan.theirs[i];
        bool covered = false;
        for (size_t j = 0; j < nOurs; j++) { if (Scan::gScan.ours[j] == inst) { covered = true; break; } }
        if (!covered) { uncovered.push_back(inst); }
    }
    Row("diff-uncovered", s, (long long)uncovered.size(), "O(theirs x ours) loop, copied from ScanAndReport");
    Row("walk-total", all, (long long)Scan::gDbpfPaths.size(), "DBPFs opened across the four walks");

    std::sort(uncovered.begin(), uncovered.end());
    if (uncoveredOut && uncoveredOut[0])
    {
        FILE* f = nullptr;
        if (_wfopen_s(&f, uncoveredOut, L"wb") == 0 && f)
        {
            for (uint32_t v : uncovered) { fprintf(f, "%08X\n", v); }
            fclose(f);
        }
    }
    printf("ICONS\tours=%zu\ttheirs=%zu\tuncovered=%zu\tlongPathsSeen=%d\tfiles1=%u\tbytes1=%llu\tfiles2=%u\tlogLines=%d\n",
        nOurs, Scan::gScan.theirs.size(), uncovered.size(), IconSynth::gLongPathsSeen,
        fp2a.files, fp2a.bytes, files2, Logger::Get().lines);
    fflush(stdout);
    return 0;
}

static long long gTgiSeen = 0;
#if BW_TGI_FULL
static void CountTgi(uint32_t t, uint32_t g, uint32_t, void*) { if (t == IconSynth::kIconType && g == IconSynth::kIconGroup) { gTgiSeen++; } }
#else
static void CountTgi(uint32_t, void*) { gTgiSeen++; }
#endif
static int RunReadIcons()
{
    if (Scan::gDbpfPaths.empty()) { printf("ERR\treadicons needs the walk phase first\n"); return 1; }
    for (int pass = 0; pass < 2; pass++)
    {
        gTgiSeen = 0;
        Snap s = Take();
        long long ok = 0;
        for (const std::wstring& p : Scan::gDbpfPaths)
        {
            if (IconSynth::ReadIconTgis(p.c_str(), CountTgi, nullptr)) { ok++; }
        }
        char note[128];
        sprintf_s(note, "dbpfs=%zu readOk=%lld", Scan::gDbpfPaths.size(), ok);
        Row(pass == 0 ? "readicons-a" : "readicons-b", s, gTgiSeen, note);
    }
    return 0;
}

static std::wstring Utf8ToWide(const std::string& s)
{
    if (s.empty()) { return std::wstring(); }
    int n = MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), nullptr, 0);
    std::wstring w(n, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), &w[0], n);
    return w;
}

static int RunDeps(const wchar_t* needlesPath)
{
    FILE* f = nullptr;
    if (_wfopen_s(&f, needlesPath, L"rb") != 0 || !f) { printf("ERR\tcannot open needles file\n"); return 1; }
    std::string bytes;
    char buf[4096]; size_t n;
    while ((n = fread(buf, 1, sizeof(buf), f)) > 0) { bytes.append(buf, n); }
    fclose(f);
    std::wstring text = Utf8ToWide(bytes);
    const Snap all = Take();
    int count = 0;
    size_t pos = 0;
    while (pos < text.size())
    {
        size_t nl = text.find(L'\n', pos);
        if (nl == std::wstring::npos) { nl = text.size(); }
        std::wstring line = text.substr(pos, nl - pos);
        pos = nl + 1;
        if (!line.empty() && line.back() == L'\r') { line.pop_back(); }
        if (line.empty()) { continue; }
        size_t t1 = line.find(L'\t');
        size_t t2 = (t1 == std::wstring::npos) ? std::wstring::npos : line.find(L'\t', t1 + 1);
        if (t1 == std::wstring::npos || t2 == std::wstring::npos) { continue; }
        std::wstring name = line.substr(0, t1);
        const bool prefix = (line[t1 + 1] == L'1');
        wchar_t hit[MAX_PATH] = {};
        DWORD sz = 0;
        int matches = 0;
        Snap s = Take();
        const bool present = FindPluginFile(gRoot, name.c_str(), prefix, 4, hit, MAX_PATH, &sz, &matches);
        char label[512];
        char narrow[400] = {};
        WideCharToMultiByte(CP_UTF8, 0, name.c_str(), -1, narrow, sizeof(narrow) - 1, nullptr, nullptr);
        sprintf_s(label, "dep:%s", narrow);
        Row(label, s, matches, present ? "present" : "absent");
        printf("DEP\t%ls\t%d\t%d\t%u\t%d\t%ls\n", name.c_str(), prefix ? 1 : 0, present ? 1 : 0, sz, matches, hit);
        fflush(stdout);
        count++;
    }
    Row("deps-total", all, count, "one depth-4 FindPluginFile walk per distinct needle");
    printf("ROW\tcrt-truncations\t0.0\t%lld\t0\t0\t0\tswprintf_s overflows caught by the harness handler (0 = no handler installed or none happened)\n", gCrtTrunc);
    fflush(stdout);
    return 0;
}

#if BW_HAS_INDEX
// ---- The Beta 1 BOOT-INDEX consumers, driven the way the DLL drives them:
// one walk per root, then every consumer reads the index. The icon pass is
// the harness's own loop over the index (each DBPF opened once per pass,
// sort/unique dedupe) because the DLL's consumer sits outside the sentinels.
static std::vector<uint32_t>* gIdxList = nullptr;
#if BW_TGI_FULL
static void IdxAddTgi(uint32_t t, uint32_t g, uint32_t inst, void*)
{
    if (t == IconSynth::kIconType && g == IconSynth::kIconGroup) { gIdxList->push_back(inst); }
}
#else
static void IdxAddTgi(uint32_t inst, void*) { gIdxList->push_back(inst); }
#endif
static int RunBootIndex(const wchar_t* needlesPath, const wchar_t* uncoveredOut)
{
    using namespace IconSynth::BootIndex;
    Release();
    Snap s = Take();
    const Index& ix = Get();
    char note[512];
    sprintf_s(note, "docs=%u install=%u pastMaxPath=%u namesKB=%u walkMs=%u/%u",
        ix.count[0], ix.count[1], ix.pastMaxPath,
        (unsigned)(ix.names.size() * sizeof(wchar_t) / 1024), ix.walkMs[0], ix.walkMs[1]);
    Row("index-build", s, (long long)ix.files.size(), note);

    std::vector<uint32_t> ours, theirs;
    s = Take();
    long long opened = 0;
    for (int pass = 0; pass < 2; pass++)
    {
        gIdxList = (pass == 0) ? &ours : &theirs;
        for (const File& f : ix.files)
        {
            if (!f.dbpf) { continue; }
            const bool isOurs = IconSynth::IsOurPackage(Leaf(f));
            if (isOurs != (pass == 0)) { continue; }
            wchar_t full[IconSynth::kLongPath];
            if (!FullPath(f, full, IconSynth::kLongPath, true)) { continue; }
            IconSynth::ReadIconTgis(full, IdxAddTgi, nullptr);
            opened++;
        }
    }
    std::sort(ours.begin(), ours.end()); ours.erase(std::unique(ours.begin(), ours.end()), ours.end());
    std::sort(theirs.begin(), theirs.end()); theirs.erase(std::unique(theirs.begin(), theirs.end()), theirs.end());
    std::vector<uint32_t> uncovered;
    std::set_difference(theirs.begin(), theirs.end(), ours.begin(), ours.end(), std::back_inserter(uncovered));
    sprintf_s(note, "ours=%zu theirs=%zu dbpfsOpened=%lld (each once per pass; sort/unique dedupe)", ours.size(), theirs.size(), opened);
    Row("index-icons", s, (long long)uncovered.size(), note);
    if (uncoveredOut && uncoveredOut[0])
    {
        FILE* f = nullptr;
        if (_wfopen_s(&f, uncoveredOut, L"wb") == 0 && f)
        {
            for (uint32_t v : uncovered) { fprintf(f, "%08X\n", v); }
            fclose(f);
        }
    }
    printf("IDXICONS\tours=%zu\ttheirs=%zu\tuncovered=%zu\tpastMaxPath=%u\tfiles1=%u\tbytes1=%llu\n",
        ours.size(), theirs.size(), uncovered.size(), ix.pastMaxPath, ix.count[0], ix.bytes[0]);
    fflush(stdout);

    FILE* nf = nullptr;
    if (_wfopen_s(&nf, needlesPath, L"rb") != 0 || !nf) { printf("ERR\tcannot open needles file\n"); return 1; }
    std::string bytes;
    char buf[4096]; size_t n;
    while ((n = fread(buf, 1, sizeof(buf), nf)) > 0) { bytes.append(buf, n); }
    fclose(nf);
    std::wstring text = Utf8ToWide(bytes);
    const Snap all = Take();
    int count = 0;
    size_t pos = 0;
    while (pos < text.size())
    {
        size_t nl = text.find(L'\n', pos);
        if (nl == std::wstring::npos) { nl = text.size(); }
        std::wstring line = text.substr(pos, nl - pos);
        pos = nl + 1;
        if (!line.empty() && line.back() == L'\r') { line.pop_back(); }
        if (line.empty()) { continue; }
        size_t t1 = line.find(L'\t');
        if (t1 == std::wstring::npos) { continue; }
        std::wstring name = line.substr(0, t1);
        const bool prefix = (line[t1 + 1] == L'1');
        DepHit h;
        s = Take();
        FindDep(name.c_str(), prefix, h);
        char label[512];
        char narrow[400] = {};
        WideCharToMultiByte(CP_UTF8, 0, name.c_str(), -1, narrow, sizeof(narrow) - 1, nullptr, nullptr);
        sprintf_s(label, "idx:%s", narrow);
        Row(label, s, h.matches, h.present ? "present" : "absent");
        printf("IDXDEP\t%ls\t%d\t%d\t%u\t%d\t%ls\t%d\t%ls\n", name.c_str(), prefix ? 1 : 0, h.present ? 1 : 0,
            h.size, h.matches, h.path, h.deepestDepth, h.deepPath);
        fflush(stdout);
        count++;
    }
    Row("index-deps-total", all, count, "FindDep over the index, one pass per needle");

    s = Take();
    const bool wb = AnyNameContains(L"web button improvement mod");
    Row("index-webbutton", s, wb ? 1 : 0, "AnyNameContains over the index");
    printf("IDXWEB\t%d\n", wb ? 1 : 0);

    std::vector<TopFolder> tops;
    s = Take();
    TopLevelFolders(tops);
    Row("index-topfolders", s, (long long)tops.size());
    for (const TopFolder& t : tops) { printf("IDXTOP\t%ls\t%u\t%u\n", t.name, t.dbpf, t.conflicts); }
    fflush(stdout);
    return 0;
}
#endif

static void __cdecl OnInvalidParameter(const wchar_t*, const wchar_t*, const wchar_t*, unsigned int, uintptr_t)
{
    gCrtTrunc++;
}

int wmain(int argc, wchar_t** argv)
{
    if (argc < 3)
    {
        wprintf(L"usage: bootwalk <plugins-root> <phases,comma: discover,walk,readicons,deps> [--needles f] [--install-root d] [--uncovered-out f] [--crt-handler] [--work d] [--echo-log]\n");
        return 2;
    }
    wcscpy_s(gRootNoSlash, MAX_PATH, argv[1]);
    { size_t n = wcslen(gRootNoSlash); while (n > 0 && gRootNoSlash[n - 1] == L'\\') { gRootNoSlash[--n] = 0; } }
    swprintf_s(gRoot, L"%s\\", gRootNoSlash);
    gInstallRoot[0] = 0;
    const wchar_t* needles = L"";
    const wchar_t* uncoveredOut = L"";
    const wchar_t* uncoveredIdxOut = L"";
    bool crtHandler = false;
    for (int i = 3; i < argc; i++)
    {
        if (wcscmp(argv[i], L"--needles") == 0 && i + 1 < argc) { needles = argv[++i]; }
        else if (wcscmp(argv[i], L"--install-root") == 0 && i + 1 < argc) { swprintf_s(gInstallRoot, L"%s\\", argv[++i]); }
        else if (wcscmp(argv[i], L"--uncovered-out") == 0 && i + 1 < argc) { uncoveredOut = argv[++i]; }
        else if (wcscmp(argv[i], L"--uncovered-index-out") == 0 && i + 1 < argc) { uncoveredIdxOut = argv[++i]; }
        else if (wcscmp(argv[i], L"--crt-handler") == 0) { crtHandler = true; }
        else if (wcscmp(argv[i], L"--work") == 0 && i + 1 < argc) { SetCurrentDirectoryW(argv[++i]); }
        else if (wcscmp(argv[i], L"--echo-log") == 0) { Logger::Get().echo = true; }
    }
    if (crtHandler)
    {
        // The DLL installs NO such handler: without one the CRT's answer to a
        // too-long swprintf_s is __fastfail (exit 0xC0000409). With this one
        // the call returns -1 with an EMPTY buffer and the walk carries on
        // into "" - which is why --work points the CWD at an empty folder.
        _set_invalid_parameter_handler(OnInvalidParameter);
    }
    printf("HARNESS\troot=%ls\tinstallRoot=%ls\tcrtHandler=%d\n", gRoot, gInstallRoot, crtHandler ? 1 : 0);
    fflush(stdout);

    std::wstring phases = argv[2];
    size_t pos = 0;
    int rc = 0;
    while (pos <= phases.size())
    {
        size_t c = phases.find(L',', pos);
        if (c == std::wstring::npos) { c = phases.size(); }
        std::wstring ph = phases.substr(pos, c - pos);
        pos = c + 1;
        if (ph == L"discover") { rc |= RunDiscover(); }
        else if (ph == L"walk") { rc |= RunWalk(uncoveredOut); }
        else if (ph == L"readicons") { rc |= RunReadIcons(); }
        else if (ph == L"deps") { rc |= RunDeps(needles); }
#if BW_HAS_INDEX
        else if (ph == L"bootindex") { rc |= RunBootIndex(needles, uncoveredIdxOut); }
#else
        else if (ph == L"bootindex") { printf("ERR\tno BOOT-INDEX region in this source\n"); rc = 2; }
#endif
        else if (!ph.empty()) { printf("ERR\tunknown phase %ls\n", ph.c_str()); rc = 2; }
    }
    printf("DONE\t%d\n", rc);
    return rc;
}
'@

function Write-Harness([string]$path, [string]$depRegion) {
    $text = $harnessTemplate.Replace('//@@DEFINES@@', $defines).Replace('//@@FOLDER_DISCOVERY@@', $regDisc).Replace('//@@DEP_WALK@@', $depRegion).Replace('//@@BOOT_WALK@@', $regBoot).Replace('//@@BOOT_INDEX@@', $regIndex)
    [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
}
Write-Harness (Join-Path $work 'bootwalk.cpp') $regDep

# ---- COMPILE (x86, like the DLL) ------------------------------------------------
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw 'vswhere.exe not found - Visual Studio is required to build the harness' }
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvars32.bat'
if (-not (Test-Path $vcvars)) { throw "vcvars32.bat not found under $vs" }

function Build-Exe([string]$cpp, [string]$exe, [string]$log) {
    Push-Location $work
    try {
        $bat = Join-Path $work ("build-" + [IO.Path]::GetFileNameWithoutExtension($exe) + ".bat")
        # CRLF: cmd.exe seeks by BYTE OFFSET on call/goto and lands mid-line in an
        # LF-only batch file. House law, paid for once already.
        $batText = "@echo off`r`ncall `"$vcvars`" >nul 2>&1`r`ncl /nologo /EHsc /W3 /O2 /std:c++20 /DBOOTWALK_HARNESS `"$cpp`" /Fe:`"$exe`" >`"$log`" 2>&1`r`nexit /b %ERRORLEVEL%`r`n"
        [IO.File]::WriteAllText($bat, $batText, (New-Object Text.UTF8Encoding($false)))
        & cmd /c $bat
        if ($LASTEXITCODE -ne 0) {
            Write-Output "HARNESS DID NOT COMPILE ($cpp):"
            Get-Content $log | ForEach-Object { Write-Output "  $_" }
            throw 'the lifted code does not compile standalone'
        }
    } finally { Pop-Location }
}
$exe = Join-Path $work 'bootwalk.exe'
Build-Exe (Join-Path $work 'bootwalk.cpp') $exe (Join-Path $work 'build.log')
Write-Output 'harness compiled (cl /nologo /EHsc /W3 /O2 /std:c++20 /DBOOTWALK_HARNESS, x86)'

$codeSha = @{}
$sha1 = [Security.Cryptography.SHA1]::Create()
foreach ($pair in @(@('FOLDER-DISCOVERY', $regDisc), @('DEP-WALK', $regDep), @('BOOT-WALK', $regBoot))) {
    $codeSha[$pair[0]] = ([BitConverter]::ToString($sha1.ComputeHash([Text.Encoding]::UTF8.GetBytes($pair[1]))) -replace '-', '').ToLowerInvariant()
}

# ---- THE INSTALL-SIDE ROOT STAND-IN -------------------------------------------
# ScanAndReport walks <install>\Plugins too. A small folder stands in for it so
# all four walks run in the same shape; nothing here is a game file.
$installRoot = Join-Path $ScaleRoot 'InstallPlugins-standin'
New-Item -ItemType Directory $installRoot -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $installRoot 'readme.txt'), 'stand-in for <install>\Plugins - not a game file')
[IO.File]::WriteAllBytes((Join-Path $installRoot 'not-a-dbpf.dat'), (New-Object byte[] 96))

# ---- RUN HELPERS ------------------------------------------------------------------
function Invoke-Generator([string]$out, [int]$n, [int]$namDepth, [int]$longPaths, [bool]$bigIndex, [int]$png, [int]$dirs) {
    $args = @($generator, '--files', $n, '--icons-per-file', $IconsPerFile, '--png-subset', $png, '--long-paths', $longPaths,
              '--nam-depth', $namDepth, '--seed', $Seed, '--out', $out, '--bundle', $bundlePlugins)
    if ($bigIndex) { $args += '--big-index' }
    if ($dirs -gt 0) { $args += @('--dirs', $dirs) }
    if ($Junction -and $out -notlike '*-ctl-*') { $args += '--junction' }
    $t = [Diagnostics.Stopwatch]::StartNew()
    $o = & python @args 2>&1
    $code = $LASTEXITCODE
    # Write-Host: this function returns the manifest object (see Lift-Region).
    $o | ForEach-Object { Write-Host "  gen: $_" }
    if ($code -ne 0) { throw "generator failed ($code) for $out" }
    Write-Host ("  generator: {0:N1}s" -f $t.Elapsed.TotalSeconds)
    $mp = Join-Path $out 'manifest.json'
    return (Get-Content -LiteralPath $mp -Raw | ConvertFrom-Json)
}

function Invoke-Harness([string]$exePath, [string]$root, [string]$phases, [string[]]$extra) {
    $a = @($root, $phases, '--install-root', $installRoot, '--needles', $needlesFile) + $extra
    if ($EchoLog) { $a += '--echo-log' }
    $t = [Diagnostics.Stopwatch]::StartNew()
    $out = & $exePath @a 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $rows = @(); $deps = @{}; $icons = $null; $disc = $null
    $idxDeps = @{}; $idxIcons = $null; $idxWeb = $null; $idxTops = @()
    foreach ($line in $out) {
        $c = $line -split "`t"
        switch ($c[0]) {
            'ROW' { $rows += [pscustomobject]@{ phase = $c[1]; ms = [double]$c[2]; count = [int64]$c[3]; finds = [int64]$c[4]; nexts = [int64]$c[5]; opens = [int64]$c[6]; note = $c[7] } }
            'DEP' { $deps[$c[1].ToLowerInvariant() + '|' + $c[2]] = [pscustomobject]@{ name = $c[1]; prefix = ($c[2] -eq '1'); present = ($c[3] -eq '1'); size = [int64]$c[4]; matches = [int]$c[5]; hit = $c[6] } }
            'ICONS' { $icons = @{}; foreach ($kv in $c[1..($c.Count - 1)]) { $p = $kv -split '=', 2; $icons[$p[0]] = $p[1] } }
            'DISCOVER' { $disc = [pscustomobject]@{ earlyFound = [int]$c[1]; ovrFound = [int]$c[2]; earlyLeaf = $c[3]; ovrLeaf = $c[4] } }
            'IDXDEP' { $idxDeps[$c[1].ToLowerInvariant() + '|' + $c[2]] = [pscustomobject]@{ name = $c[1]; prefix = ($c[2] -eq '1'); present = ($c[3] -eq '1'); size = [int64]$c[4]; matches = [int]$c[5]; hit = $c[6]; deepest = [int]$c[7]; deepPath = $c[8] } }
            'IDXICONS' { $idxIcons = @{}; foreach ($kv in $c[1..($c.Count - 1)]) { $p = $kv -split '=', 2; $idxIcons[$p[0]] = $p[1] } }
            'IDXWEB' { $idxWeb = [int]$c[1] }
            'IDXTOP' { $idxTops += [pscustomobject]@{ name = $c[1]; dbpf = [int]$c[2]; conflicts = [int]$c[3] } }
        }
    }
    return [pscustomobject]@{ code = $code; rows = $rows; deps = $deps; icons = $icons; discover = $disc; raw = $out; seconds = $t.Elapsed.TotalSeconds
                              idxDeps = $idxDeps; idxIcons = $idxIcons; idxWeb = $idxWeb; idxTops = $idxTops }
}

# DIFFERENTIAL: FindDep (over the index) must reproduce FindPluginFile (the
# walk) on every needle - present, size, match count and the path of the first
# hit. The one legitimate difference is a needle the MAX_PATH walk cannot
# reach at all: there the index is RIGHT and the walk is blind, and the
# manifest says which needles those are (withinMaxPath = false).
function Compare-IndexDeps($r, $manifest, [string]$label) {
    if (-not $r.idxDeps -or $r.idxDeps.Count -eq 0) { $script:fail += "$label`: bootindex phase produced no FindDep rows"; return }
    $same = 0; $expectedDiff = 0
    foreach ($nd in $needles.Values) {
        $key = "$($nd.name.ToLowerInvariant())|$([int]$nd.prefix)"
        $a = $r.deps[$key]; $b = $r.idxDeps[$key]
        if (-not $a -or -not $b) { $script:fail += "$label`: $($nd.name): missing a DEP or IDXDEP row"; continue }
        $fact = Get-NeedleFact $manifest $nd.name
        $identical = ($a.present -eq $b.present -and $a.size -eq $b.size -and $a.matches -eq $b.matches -and ($a.hit -ieq $b.hit))
        if ($identical) { $same++; continue }
        if ($fact -and $fact.present -and -not $fact.withinMaxPath -and -not $a.present -and $b.present) {
            $expectedDiff++
            Write-Output "  differential: $($nd.name): walk ABSENT, index PRESENT ($($b.hit.Length)-char path) - the index sees what the MAX_PATH walk cannot; expected"
            continue
        }
        $script:fail += "$label`: FindDep differs from FindPluginFile on $($nd.name): walk present=$([int]$a.present) size=$($a.size) matches=$($a.matches) hit=$($a.hit); index present=$([int]$b.present) size=$($b.size) matches=$($b.matches) hit=$($b.hit)"
    }
    Write-Output "  differential FindDep vs FindPluginFile: $same/$($needles.Count) identical (path, size, matches), $expectedDiff expected past-MAX_PATH difference(s)"
}

function Get-NeedleFact($manifest, [string]$name) {
    foreach ($p in $manifest.needles.PSObject.Properties) { if ($p.Name -ieq $name) { return $p.Value } }
    return $null
}

function Expected-Verdict($fact) {
    if (-not $fact.present) { return 'absent' }
    if ($fact.expectedSize -ne 0 -and $fact.size -ne $fact.expectedSize) { return 'changed' }
    return 'ok'
}
function Measured-Verdict($dep, [int64]$expectedSize) {
    if (-not $dep) { return 'unmeasured' }
    if (-not $dep.present) { return 'absent' }
    if ($expectedSize -ne 0 -and $dep.size -ne $expectedSize) { return 'changed' }
    return 'ok'
}

function Print-Table([object[]]$rows) {
    Write-Output ('  {0,-52} {1,10} {2,9} {3,8} {4,9} {5,7}  {6}' -f 'phase', 'ms', 'count', 'finds', 'nexts', 'opens', 'note')
    foreach ($r in $rows) {
        Write-Output ('  {0,-52} {1,10:N1} {2,9} {3,8} {4,9} {5,7}  {6}' -f $r.phase, $r.ms, $r.count, $r.finds, $r.nexts, $r.opens, $r.note)
    }
}

$fail = @()
$expectedFailures = [ordered]@{}
$results = [ordered]@{}

# ---- CONTROL TREES (small, no long paths, nothing that aborts) ------------------
# B: NAM at depth 3 - the CLEAN dependency run; every verdict must match the
#    manifest exactly. Also the tree the mutant must fail on.
# A: NAM at depth 4 - expected failure #3.
Write-Output ''
Write-Output '== control tree B (NAM at depth 3, no long paths): the clean dependency walk =='
$phases2 = 'discover,deps'
if ($hasIndex) { $phases2 += ',bootindex' }
$ctlB = Join-Path $ScaleRoot 'Plugins-ctl-nam3'
$mB = Invoke-Generator $ctlB 60 3 0 $false 8 8
$rB = Invoke-Harness $exe $ctlB $phases2 @()
if ($rB.code -ne 0) { $fail += "control B: harness exit $($rB.code) ($('0x{0:X8}' -f $rB.code))"; $rB.raw | Select-Object -Last 5 | ForEach-Object { Write-Output "  $_" } }
Print-Table $rB.rows
if ($hasIndex) { Compare-IndexDeps $rB $mB 'control B' }
$depMismatch = 0
foreach ($nd in $needles.Values) {
    $fact = Get-NeedleFact $mB $nd.name
    $dep = $rB.deps["$($nd.name.ToLowerInvariant())|$([int]$nd.prefix)"]
    $exp = Expected-Verdict $fact
    $got = Measured-Verdict $dep $nd.size
    $mOk = ($dep -and $dep.matches -eq $fact.matches)
    if ($got -ne $exp -or -not $mOk) {
        $depMismatch++
        $fail += "control B: $($nd.name): expected $exp/matches=$($fact.matches), measured $got/matches=$(if ($dep) { $dep.matches } else { '-' })"
    }
}
Write-Output "  dependency verdicts vs manifest: $($needles.Count - $depMismatch)/$($needles.Count) agree (present/absent/changed AND match counts)"
if ($rB.discover.earlyFound -ne 1 -or $rB.discover.ovrFound -ne 1) { $fail += "control B: discovery early=$($rB.discover.earlyFound) ovr=$($rB.discover.ovrFound) - both must be 1" }

Write-Output ''
Write-Output '== control tree A (NAM at depth 4): EXPECTED FAILURE #3 =='
$ctlA = Join-Path $ScaleRoot 'Plugins-ctl-nam4'
$mA = Invoke-Generator $ctlA 60 4 0 $false 8 8
$rA = Invoke-Harness $exe $ctlA $phases2 @()
if ($rA.code -ne 0) { $fail += "control A: harness exit $($rA.code)" }
$namName = $mA.namNeedle
$namDep = $rA.deps["$($namName.ToLowerInvariant())|0"]
$namFact = Get-NeedleFact $mA $namName
$namRow = $rA.rows | Where-Object { $_.phase -eq "dep:$namName" } | Select-Object -First 1
if ($namFact.present -and $namDep -and -not $namDep.present) {
    $expectedFailures['namDepth4'] = 'PRESENT: NAM controller 4 dirs below Plugins is ABSENT to the depth-4 walk (manifest says present)'
    Write-Output "  EXPECTED FAILURE #3 confirmed: $namName is on disk at depth 4 ($($namFact.firstRel)) and FindPluginFile(depth=4) reports ABSENT ($($namRow.ms) ms)"
} elseif ($namFact.present -and $namDep -and $namDep.present) {
    $expectedFailures['namDepth4'] = 'FIXED: the walk now reaches depth 4'
    Write-Output "  EXPECTED FAILURE #3 DID NOT OCCUR: the walk found NAM at depth 4 - the code has changed; refresh the baseline"
} else {
    $fail += "control A: cannot evaluate the depth-4 control (fact present=$($namFact.present), measured=$($namDep -ne $null))"
}
# Other needles on A must still agree (they sit at depth 2).
foreach ($nd in $needles.Values) {
    if ($nd.name -ieq $namName) { continue }
    $fact = Get-NeedleFact $mA $nd.name
    $dep = $rA.deps["$($nd.name.ToLowerInvariant())|$([int]$nd.prefix)"]
    if ((Measured-Verdict $dep $nd.size) -ne (Expected-Verdict $fact)) { $fail += "control A: $($nd.name): expected $(Expected-Verdict $fact), measured $(Measured-Verdict $dep $nd.size)" }
}
if ($hasIndex) {
    Compare-IndexDeps $rA $mA 'control A'
    $iNam = $rA.idxDeps["$($namName.ToLowerInvariant())|0"]
    if ($iNam) { Write-Output "  index: FindDep also reports the copy beyond the budget: deepestDepth=$($iNam.deepest) ($($iNam.deepPath))" }
}

# ---- MUTATION CONTROL ---------------------------------------------------------
if ($Mutate) {
    Write-Output ''
    Write-Output '== MUTATION CONTROL: FindPluginFile one level shallower (if (depth <= 0) -> if (depth <= 1)) =='
    $mutant = $regDep -replace 'if \(depth <= 0\)', 'if (depth <= 1)'
    if ($mutant -eq $regDep) {
        $fail += 'MUTATION CONTROL COULD NOT BE BUILT: "if (depth <= 0)" was not found in the lifted DEP-WALK region'
    } else {
        Write-Harness (Join-Path $work 'mutant.cpp') $mutant
        Build-Exe (Join-Path $work 'mutant.cpp') (Join-Path $work 'mutant.exe') (Join-Path $work 'buildm.log')
        $rM = Invoke-Harness (Join-Path $work 'mutant.exe') $ctlB 'discover,deps' @()
        $mNam = $rM.deps["$($mB.namNeedle.ToLowerInvariant())|0"]
        Write-Output "  mutant on control B: $($mB.namNeedle) present=$(if ($mNam) { [int]$mNam.present } else { '?' })   (must be 0 - the needle at depth 3 must vanish)"
        if (-not $mNam -or $mNam.present) {
            $fail += 'MUTATION CONTROL FAILED: the shallower walk still finds the depth-3 NAM controller, so this harness cannot show it is sensitive to the depth budget'
        } else {
            Write-Output '  the harness went RED on the mutant, as required'
        }
    }
}

# ---- THE MAIN TREES ------------------------------------------------------------
foreach ($N in $FileSizes) {
    Write-Output ''
    Write-Output "== N=${N}: K=$IconsPerFile icons/file, P=$PngSubset PNG, L=$LongPaths long paths, bigIndex=$BigIndex, namDepth=$NamDepth, seed=$Seed =="
    $root = Join-Path $ScaleRoot "Plugins-$N"
    $m = Invoke-Generator $root $N $NamDepth $LongPaths $BigIndex $PngSubset 0
    $manifestSize = (Get-Item -LiteralPath (Join-Path $root 'manifest.json')).Length
    $uncFile = Join-Path $work "uncovered-$N.txt"

    # Invocation 1: discovery + the four walks + the isolated index reads.
    $r1 = Invoke-Harness $exe $root 'discover,walk,readicons' @('--uncovered-out', $uncFile)
    if ($r1.code -ne 0) { $fail += "N=$N walk: harness exit $($r1.code) ($('0x{0:X8}' -f $r1.code))"; $r1.raw | Select-Object -Last 5 | ForEach-Object { Write-Output "  $_" } }

    # Invocation 2: the dependency walks, bare. If the CRT kills the process on
    # the long-path fixture, say so and rerun with a counting handler to get
    # the verdicts the code WOULD produce if it survived.
    $uncIdxFile = Join-Path $work "uncovered-index-$N.txt"
    $r2 = Invoke-Harness $exe $root $phases2 @('--uncovered-index-out', $uncIdxFile)
    $depsAborted = $false
    if ($r2.code -eq $STATUS_STACK_BUFFER_OVERRUN) {
        $depsAborted = $true
        Write-Output ("  deps (bare): PROCESS TERMINATED, exit 0x{0:X8} - the secure CRT's __fastfail on a too-long swprintf_s into FindPluginFile's MAX_PATH buffer. The DLL installs no invalid-parameter handler, so this is what the game would do." -f $r2.code)
        Write-Output '  rerunning deps with a counting handler (returns -1, empty buffer; CWD parked on an empty folder):'
        $r2 = Invoke-Harness $exe $root $phases2 @('--crt-handler', '--work', $cwdEmpty, '--uncovered-index-out', $uncIdxFile)
        if ($r2.code -ne 0) { $fail += "N=$N deps (handler): harness exit $($r2.code)" }
    } elseif ($r2.code -ne 0) {
        $fail += "N=$N deps: harness exit $($r2.code) ($('0x{0:X8}' -f $r2.code))"
    }

    $rows = @($r1.rows) + @($r2.rows | Where-Object { $_.phase -ne 'discover' })
    Print-Table $rows

    # ---- compare with the answer key ---------------------------------------
    $ic = $r1.icons
    $junctionNote = ''
    if ($m.junction) { $junctionNote = " [junction '$($m.junction)' present - the walk multiplies; exact comparisons skipped]" }
    Write-Output ("  icons: ours={0} theirs={1} uncovered={2} longPathsSeen={3} files={4} bytes={5}{6}" -f $ic['ours'], $ic['theirs'], $ic['uncovered'], $ic['longPathsSeen'], $ic['files1'], $ic['bytes1'], $junctionNote)
    Write-Output ("  key:   ours={0} theirs={1} uncovered={2} longPaths={3} files={4}(+manifest) bytes={5}(+{6})" -f $m.icons.ours, $m.icons.theirs, $m.icons.uncovered, $m.counts.longPaths.prefixed260, $m.counts.totalFiles, $m.counts.totalBytes, $manifestSize)

    if ($r1.discover.earlyFound -ne 1 -or $r1.discover.ovrFound -ne 1) { $fail += "N=$N discovery early=$($r1.discover.earlyFound) ovr=$($r1.discover.ovrFound) - both must be 1 (leafs: $($r1.discover.earlyLeaf) / $($r1.discover.ovrLeaf))" }
    if (-not $m.junction) {
        if ([int64]$ic['ours'] -ne $m.icons.ours) { $fail += "N=$N ours=$($ic['ours']), manifest says $($m.icons.ours)" }
        # gLongPathsSeen is zeroed once per ScanAndReport and Walk runs over the
        # tree TWICE (ours pass, theirs pass), so the number the DLL logs as
        # "past MAX_PATH" is DOUBLE the truth on the current code. Exactly 2x
        # is the current behaviour, exactly 1x is the fixed one; anything else
        # means the deep tree was not fully walked.
        $lps = [int64]$ic['longPathsSeen']; $keyLp = [int64]$m.counts.longPaths.prefixed260
        if ($lps -eq 2 * $keyLp -and $keyLp -gt 0) {
            Write-Output "  longPathsSeen=$lps = 2 x $keyLp`: every long-path entry was reached, and counted once per pass (the DLL's log line reports double)"
        } elseif ($lps -eq $keyLp) {
            Write-Output "  longPathsSeen=$lps matches the key exactly (counted once)"
        } else {
            $fail += "N=$N longPathsSeen=$lps, manifest says $keyLp (2x = $(2 * $keyLp) on the current code) - the deep tree was not fully walked"
        }
        if ([int64]$ic['files1'] -ne ($m.counts.totalFiles + 1)) { $fail += "N=$N walk saw $($ic['files1']) files, manifest says $($m.counts.totalFiles) + manifest.json" }
        if ([int64]$ic['bytes1'] -ne ($m.counts.totalBytes + $manifestSize)) { $fail += "N=$N walk saw $($ic['bytes1']) bytes, manifest says $($m.counts.totalBytes) + $manifestSize" }

        $uncSha = (Get-FileHash -LiteralPath $uncFile -Algorithm SHA1).Hash.ToLowerInvariant()
        $theirs = [int64]$ic['theirs']
        if ($theirs -eq $m.icons.theirs -and $uncSha -eq $m.icons.uncoveredSha1) {
            $expectedFailures['bigIndex'] = 'FIXED: every icon counted, big index included'
            Write-Output "  theirs/uncovered match the key exactly (sha1 $uncSha) - the big-index guard no longer drops icons; EXPECTED FAILURE #1 DID NOT OCCUR"
        } elseif ($m.icons.bigIndex -and $theirs -eq ($m.icons.theirs - $m.icons.bigIndex.icons) -and $uncSha -eq $m.icons.uncoveredExBigIndexSha1) {
            $expectedFailures['bigIndex'] = "PRESENT: $($m.icons.bigIndex.icons) icons in the $($m.icons.bigIndex.entries)-entry index are not counted (ReadIconTgis count<200000 guard)"
            Write-Output "  EXPECTED FAILURE #1 confirmed: theirs is short by exactly the big index's $($m.icons.bigIndex.icons) icons, and the uncovered set equals the key minus those (sha1 $uncSha)"
        } else {
            $fail += "N=$N theirs=$theirs uncovered-sha1=$uncSha; key theirs=$($m.icons.theirs) sha1=$($m.icons.uncoveredSha1) (ex big index: $($m.icons.uncoveredExBigIndexSha1)) - an UNEXPLAINED icon-count difference"
        }
    }

    # dependency verdicts on the main tree
    $webName = $m.webButtonNeedle
    $depMismatch = 0
    foreach ($nd in $needles.Values) {
        $fact = Get-NeedleFact $m $nd.name
        $dep = $r2.deps["$($nd.name.ToLowerInvariant())|$([int]$nd.prefix)"]
        $exp = Expected-Verdict $fact
        $got = Measured-Verdict $dep $nd.size
        if ($nd.name -ieq $webName) {
            if ($fact.present -and $got -eq 'absent') {
                $expectedFailures['webButtonLongPath'] = "PRESENT: the web-button dat at $($fact.firstPathLen) chars is invisible to the MAX_PATH walk" + $(if ($depsAborted) { ' - and without a CRT handler the walk TERMINATES THE PROCESS (0xC0000409)' } else { '' })
                Write-Output "  EXPECTED FAILURE #2 confirmed: $webName is on disk ($($fact.firstPathLen)-char path) and the MAX_PATH walk reports ABSENT$(if ($depsAborted) { ' (bare run: process terminated)' })"
            } elseif ($fact.present -and $got -ne 'absent') {
                $expectedFailures['webButtonLongPath'] = 'FIXED: the dependency walk reaches past MAX_PATH'
                Write-Output "  EXPECTED FAILURE #2 DID NOT OCCUR: the walk found the web-button dat past MAX_PATH - the code has changed; refresh the baseline"
            } else {
                $fail += "N=$N cannot evaluate the long-path control (fact present=$($fact.present))"
            }
            continue
        }
        $mOk = ($dep -and $dep.matches -eq $fact.matches)
        if ($got -ne $exp -or -not $mOk) {
            $depMismatch++
            $fail += "N=$N $($nd.name): expected $exp/matches=$($fact.matches), measured $got/matches=$(if ($dep) { $dep.matches } else { '-' })"
        }
    }
    Write-Output "  dependency verdicts vs manifest (web button excluded): $($needles.Count - 1 - $depMismatch)/$($needles.Count - 1) agree"
    $dupFact = Get-NeedleFact $m $m.duplicateNeedle
    $dupDep = $r2.deps["$($m.duplicateNeedle.ToLowerInvariant())|0"]
    if ($dupDep) { Write-Output "  duplicate dep source: $($m.duplicateNeedle) matches=$($dupDep.matches) (key $($dupFact.matches)); first hit $($dupDep.hit)" }
    $trunc = $r2.rows | Where-Object { $_.phase -eq 'crt-truncations' } | Select-Object -First 1
    if ($trunc) { Write-Output "  crt truncations caught by the handler: $($trunc.count)" }

    # ---- the Beta 1 index, when the source has one ----------------------------
    $indexRec = $null
    if ($hasIndex) {
        Compare-IndexDeps $r2 $m "N=$N"
        $ii = $r2.idxIcons
        if ($ii) {
            Write-Output ("  index icon scan: ours={0} theirs={1} uncovered={2} pastMaxPath={3} files={4} bytes={5}" -f $ii['ours'], $ii['theirs'], $ii['uncovered'], $ii['pastMaxPath'], $ii['files1'], $ii['bytes1'])
            if (-not $m.junction) {
                if ([int64]$ii['ours'] -ne $m.icons.ours) { $fail += "N=$N index ours=$($ii['ours']), manifest says $($m.icons.ours)" }
                $idxSha = (Get-FileHash -LiteralPath $uncIdxFile -Algorithm SHA1).Hash.ToLowerInvariant()
                if ([int64]$ii['theirs'] -eq $m.icons.theirs -and $idxSha -eq $m.icons.uncoveredSha1) {
                    Write-Output "  index icon scan matches the key EXACTLY, big index included (sha1 $idxSha)"
                } elseif ($m.icons.bigIndex -and [int64]$ii['theirs'] -eq ($m.icons.theirs - $m.icons.bigIndex.icons) -and $idxSha -eq $m.icons.uncoveredExBigIndexSha1) {
                    Write-Output "  index icon scan is still short by the big index's $($m.icons.bigIndex.icons) icons"
                } else {
                    $fail += "N=$N index theirs=$($ii['theirs']) uncovered-sha1=$idxSha; key theirs=$($m.icons.theirs) sha1=$($m.icons.uncoveredSha1) - an UNEXPLAINED icon-count difference"
                }
                if ([int64]$ii['pastMaxPath'] -ne [int64]$m.counts.longPaths.prefixed260) { $fail += "N=$N index pastMaxPath=$($ii['pastMaxPath']), manifest says $($m.counts.longPaths.prefixed260)" }
                if ([int64]$ii['files1'] -ne ($m.counts.totalFiles + 1)) { $fail += "N=$N index saw $($ii['files1']) files, manifest says $($m.counts.totalFiles) + manifest.json" }
            }
        } else { $fail += "N=$N bootindex phase produced no IDXICONS line" }
        if ($null -ne $r2.idxWeb) {
            if ([bool]$r2.idxWeb -ne [bool]$m.webButtonPresent) { $fail += "N=$N index AnyNameContains(web button)=$($r2.idxWeb), key says $([int][bool]$m.webButtonPresent)" }
            else { Write-Output "  index web-button check: $($r2.idxWeb) (key $([int][bool]$m.webButtonPresent)) - agrees, past MAX_PATH included" }
        }
        $expectTops = @($m.orderingWarnFolders) + @($m.orderingOkFolders)
        $seenTops = @($r2.idxTops | ForEach-Object { $_.name })
        $missingTops = @($expectTops | Where-Object { $seenTops -notcontains $_ })
        Write-Output "  index top-level folders: $($seenTops.Count) ($(($r2.idxTops | ForEach-Object { "$($_.name)=$($_.dbpf)" }) -join ' '))"
        if ($missingTops.Count) { $fail += "N=$N index TopLevelFolders lacks: $($missingTops -join ', ')" }
        $ib = $r2.rows | Where-Object { $_.phase -eq 'index-build' } | Select-Object -First 1
        $ic2 = $r2.rows | Where-Object { $_.phase -eq 'index-icons' } | Select-Object -First 1
        $id = $r2.rows | Where-Object { $_.phase -eq 'index-deps-total' } | Select-Object -First 1
        $iw = $r2.rows | Where-Object { $_.phase -eq 'index-webbutton' } | Select-Object -First 1
        $it = $r2.rows | Where-Object { $_.phase -eq 'index-topfolders' } | Select-Object -First 1
        $indexRec = [ordered]@{
            buildMs = $ib.ms; iconsMs = $ic2.ms; depsMs = $id.ms; webButtonMs = $iw.ms; topFoldersMs = $it.ms
            bootMs = [math]::Round($ib.ms + $ic2.ms + $id.ms + $iw.ms + $it.ms, 1)
            finds = $ib.finds; opens = $ic2.opens
            ours = [int64]$ii['ours']; theirs = [int64]$ii['theirs']; uncovered = [int64]$ii['uncovered']; pastMaxPath = [int64]$ii['pastMaxPath']
        }
        Write-Output ("  index boot cost: {0:N1} ms = build {1:N1} + icons {2:N1} + deps {3:N1} + web {4:N1} + top {5:N1}" -f $indexRec.bootMs, $ib.ms, $ic2.ms, $id.ms, $iw.ms, $it.ms)
    }

    $walkTotal = ($rows | Where-Object { $_.phase -eq 'walk-total' } | Select-Object -First 1).ms
    $depsTotal = ($rows | Where-Object { $_.phase -eq 'deps-total' } | Select-Object -First 1).ms
    $discMs = ($rows | Where-Object { $_.phase -eq 'discover' } | Select-Object -First 1).ms
    $results["$N"] = [ordered]@{
        tree = [ordered]@{ root = $root; thirdPartyDbpf = $m.counts.thirdPartyDbpf; oursDbpf = $m.counts.oursDbpf; totalFiles = $m.counts.totalFiles; dirs = $m.counts.dirs; longPaths = $m.counts.longPaths.prefixed260; maxPathLen = $m.counts.maxPathLen; junction = $m.junction }
        api = [ordered]@{ walkFd = $walkFd; tgiFull = $tgiFull; hasIndex = $hasIndex }
        phases = @($rows | ForEach-Object { [ordered]@{ phase = $_.phase; ms = $_.ms; count = $_.count; finds = $_.finds; nexts = $_.nexts; opens = $_.opens } })
        totals = [ordered]@{ discoverMs = $discMs; walkMs = $walkTotal; depsMs = $depsTotal; bootMs = [math]::Round($discMs + $walkTotal + $depsTotal, 1) }
        index = $indexRec
        icons = [ordered]@{ ours = [int64]$ic['ours']; theirs = [int64]$ic['theirs']; uncovered = [int64]$ic['uncovered']; longPathsSeen = [int64]$ic['longPathsSeen']; keyTheirs = $m.icons.theirs; keyUncovered = $m.icons.uncovered }
        depsAbortedWithoutHandler = $depsAborted
        crtTruncations = $(if ($trunc) { $trunc.count } else { 0 })
        expectedFailures = [ordered]@{ bigIndex = $expectedFailures['bigIndex']; webButtonLongPath = $expectedFailures['webButtonLongPath']; namDepth4 = $expectedFailures['namDepth4'] }
    }
}

# ---- BASELINE ---------------------------------------------------------------------
if ($Record) {
    $base = $null
    if (Test-Path -LiteralPath $baselinePath) { $base = Get-Content -LiteralPath $baselinePath -Raw | ConvertFrom-Json }
    $runs = [ordered]@{}
    if ($base -and $base.runs) { foreach ($p in $base.runs.PSObject.Properties) { $runs[$p.Name] = $p.Value } }
    foreach ($k in $results.Keys) { $runs[$k] = $results[$k] }
    $doc = [ordered]@{
        what = 'Baseline of the DLL boot walks (Test-BootWalk.ps1) on synthetic Plugins trees. ms are wall-clock on the recording machine and are informational; counts (finds/nexts/opens/icons) are exact and reproducible per seed.'
        recorded = (Get-Date -Format 'yyyy-MM-dd')
        source = $srcLabel
        codeSha1 = $codeSha
        flags = 'cl /nologo /EHsc /W3 /O2 /std:c++20 /DBOOTWALK_HARNESS (x86)'
        params = [ordered]@{ iconsPerFile = $IconsPerFile; pngSubset = $PngSubset; longPaths = $LongPaths; bigIndex = $BigIndex; namDepth = $NamDepth; seed = $Seed; bundle = (Split-Path $Bundle -Leaf) }
        runs = $runs
    }
    New-Item -ItemType Directory (Split-Path $baselinePath -Parent) -Force | Out-Null
    [IO.File]::WriteAllText($baselinePath, ($doc | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
    Write-Output ''
    Write-Output "baseline recorded: $baselinePath ($($results.Keys -join ', '))"
} elseif (Test-Path -LiteralPath $baselinePath) {
    $base = Get-Content -LiteralPath $baselinePath -Raw | ConvertFrom-Json
    Write-Output ''
    Write-Output "baseline ($($base.recorded), $($base.source)) vs this run:"
    foreach ($k in $results.Keys) {
        $b = $base.runs.PSObject.Properties[$k]
        if (-not $b) { Write-Output "  N=$k`: no baseline entry"; continue }
        $bt = $b.Value.totals; $rt = $results[$k].totals
        Write-Output ('  N={0}: boot {1:N1} ms (baseline {2:N1}) = discover {3:N1}/{4:N1} + walks {5:N1}/{6:N1} + deps {7:N1}/{8:N1}' -f $k, $rt.bootMs, $bt.bootMs, $rt.discoverMs, $bt.discoverMs, $rt.walkMs, $bt.walkMs, $rt.depsMs, $bt.depsMs)
        $bw = $b.Value.phases | Where-Object { $_.phase -eq 'walk-total' } | Select-Object -First 1
        $rw = $results[$k].phases | Where-Object { $_.phase -eq 'walk-total' } | Select-Object -First 1
        if ($bw -and $rw -and ($bw.finds -ne $rw.finds -or $bw.opens -ne $rw.opens)) {
            Write-Output "    walk finds/opens changed: $($bw.finds)/$($bw.opens) -> $($rw.finds)/$($rw.opens) (the code or the tree changed; -Record to re-baseline)"
        }
    }
}

# ---- SUMMARY ----------------------------------------------------------------------
Write-Output ''
Write-Output 'boot cost (discover + four walks + index reads inside them + one dep walk per needle):'
foreach ($k in $results.Keys) {
    $t = $results[$k].totals
    Write-Output ('  N={0,-6} boot {1,10:N1} ms   discover {2,8:N1}   walks {3,10:N1}   deps {4,10:N1}' -f $k, $t.bootMs, $t.discoverMs, $t.walkMs, $t.depsMs)
    if ($results[$k].index) {
        $ix = $results[$k].index
        Write-Output ('  N={0,-6} INDEX {1,9:N1} ms   build    {2,8:N1}   icons {3,10:N1}   deps {4,10:N1}   (one walk per root)' -f $k, $ix.bootMs, $ix.buildMs, $ix.iconsMs, $ix.depsMs)
    }
}
Write-Output ''
Write-Output 'expected failures of the current code (positive controls):'
foreach ($k in @('bigIndex', 'webButtonLongPath', 'namDepth4')) {
    Write-Output ("  {0,-20} {1}" -f $k, $(if ($expectedFailures.Contains($k)) { $expectedFailures[$k] } else { 'NOT EVALUATED' }))
}

if ($Clean) {
    # Python, not Remove-Item: the trees hold paths past 260 characters and a
    # junction loop on request; shutil.rmtree with the \\?\ prefix handles both.
    $rm = Join-Path $work 'rmtree.py'
    [IO.File]::WriteAllText($rm, "import shutil, sys`nshutil.rmtree('\\\\?\\' + sys.argv[1])`n", (New-Object Text.UTF8Encoding($false)))
    foreach ($d in @($ctlA, $ctlB, $installRoot) + @($FileSizes | ForEach-Object { Join-Path $ScaleRoot "Plugins-$_" })) {
        if (Test-Path -LiteralPath $d) { & python $rm $d }
    }
    Write-Output 'trees removed (-Clean)'
}

Write-Output ''
if ($fail.Count) {
    Write-Output 'RED:'
    $fail | ForEach-Object { Write-Output "  - $_" }
    exit 1
}
Write-Output 'ALL PASS - every count the walks produced matches the answer key except the three expected failures, which were seen and reported above.'
exit 0
