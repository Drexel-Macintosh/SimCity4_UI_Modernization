# Runs Upscale2x.exe over the synthetic test set in both modes and validates:
#   - directory mirroring, filename preservation, non-PNG + bad-magic skipping
#   - dimensions exactly doubled
#   - NN mode: EVERY source pixel equals its 2x2 output block byte-for-byte
#              (proves exact alpha + no premultiplication), alpha histogram = 4x source
#   - HQ mode: flat opaque image has zero color shift / no edge bleed,
#              flat semi-transparent image round-trips (premultiply canary),
#              gradient alpha histogram roughly preserved (mean-alpha delta + L1)
# Prerequisites: Build.ps1 then Make-TestPngs.ps1 have been run.
Add-Type -AssemblyName System.Drawing

$here  = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe   = Join-Path $here 'Upscale2x.exe'
$inDir = Join-Path $here 'test\in'
$nnDir = Join-Path $here 'test\out-nn'
$hqDir = Join-Path $here 'test\out-hq'

$script:fails = 0
function Check([bool]$ok, [string]$msg) {
    if ($ok) { Write-Host ("  PASS  " + $msg) }
    else     { Write-Host ("  FAIL  " + $msg); $script:fails++ }
}

# Load a PNG into an int[] of ARGB values (via Bitmap.Clone to 32bppArgb -
# independent of the tool's own conversion code path). Also returns the
# on-disk pixel format so we can prove the indexed source really was indexed.
function Get-Px([string]$path) {
    $ms  = New-Object IO.MemoryStream (,[IO.File]::ReadAllBytes($path))
    $bmp = [System.Drawing.Bitmap]::FromStream($ms)
    $w = $bmp.Width; $h = $bmp.Height; $fmt = $bmp.PixelFormat.ToString()
    $rect = New-Object System.Drawing.Rectangle(0,0,$w,$h)
    $b32 = $bmp.Clone($rect,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $bd = $b32.LockBits($rect,[System.Drawing.Imaging.ImageLockMode]::ReadOnly,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $px = New-Object int[] ($w*$h)
    if ($bd.Stride -eq $w*4) {
        [System.Runtime.InteropServices.Marshal]::Copy($bd.Scan0,$px,0,$w*$h)
    } else {
        for ($y=0; $y -lt $h; $y++) {
            $ptr = [IntPtr]($bd.Scan0.ToInt64() + $y*$bd.Stride)
            [System.Runtime.InteropServices.Marshal]::Copy($ptr,$px,$y*$w,$w)
        }
    }
    $b32.UnlockBits($bd); $b32.Dispose(); $bmp.Dispose(); $ms.Dispose()
    @{ W=$w; H=$h; P=$px; Fmt=$fmt }
}
function Hex([int]$argb) { '{0:X8}' -f ($argb -band 0xFFFFFFFF) }
function AlphaHist($img) {
    $hist = New-Object int[] 256
    foreach ($p in $img.P) { $hist[($p -shr 24) -band 0xFF]++ }
    ,$hist
}

# ---------------------------------------------------------------- run the tool
Write-Host '=== RUN: nearest-neighbor (default) ==='
& $exe $inDir $nnDir 2>&1 | ForEach-Object { Write-Host "  | $_" }
Check ($LASTEXITCODE -eq 0) "NN run exit code 0 (got $LASTEXITCODE)"
Write-Host '=== RUN: --hq ==='
& $exe $inDir $hqDir --hq 2>&1 | ForEach-Object { Write-Host "  | $_" }
Check ($LASTEXITCODE -eq 0) "HQ run exit code 0 (got $LASTEXITCODE)"

# ------------------------------------------------- structure / name mirroring
Write-Host '=== STRUCTURE ==='
$names = @('rgba_gradient_64x48.png','indexed_pal_64x48.png','indexed_opaque_64x48.png',
           'flat_opaque_32x32.png','flat_semi_32x32.png','sub\0x856ddbac_0x46a006b0_0x02968802.png')
foreach ($n in $names) {
    Check (Test-Path (Join-Path $nnDir $n)) "NN output exists + name preserved: $n"
    Check (Test-Path (Join-Path $hqDir $n)) "HQ output exists + name preserved: $n"
}
Check (-not (Test-Path (Join-Path $nnDir 'notes.txt')))     'non-PNG (notes.txt) not copied'
Check (-not (Test-Path (Join-Path $nnDir 'fake_webp.png'))) 'bad-magic fake_webp.png not processed'

# ------------------------------------------------------------- NN exactness
Write-Host '=== NN MODE: dimensions + full byte-for-byte 2x2 check ==='
foreach ($n in $names) {
    $s = Get-Px (Join-Path $inDir $n)
    $d = Get-Px (Join-Path $nnDir $n)
    Check ($d.W -eq 2*$s.W -and $d.H -eq 2*$s.H) "$n dims $($s.W)x$($s.H) -> $($d.W)x$($d.H) (exactly 2x)"
    $bad = 0
    for ($y=0; $y -lt $s.H; $y++) {
        for ($x=0; $x -lt $s.W; $x++) {
            $v = $s.P[$y*$s.W+$x]
            $r0 = (2*$y)*$d.W + 2*$x; $r1 = (2*$y+1)*$d.W + 2*$x
            if ($d.P[$r0] -ne $v -or $d.P[$r0+1] -ne $v -or $d.P[$r1] -ne $v -or $d.P[$r1+1] -ne $v) { $bad++ }
        }
    }
    Check ($bad -eq 0) "$n every source pixel == its 2x2 block exactly ($($s.W*$s.H) pixels, $bad mismatches)"
    if ($n -eq 'indexed_pal_64x48.png') {
        $ct = ([IO.File]::ReadAllBytes((Join-Path $inDir $n)))[25]
        Check ($ct -eq 3) "indexed_pal on-disk IHDR colortype = $ct (3 = palette; GDI+ auto-expands pal+tRNS on load, decoded as $($s.Fmt))"
    }
    if ($n -eq 'indexed_opaque_64x48.png') {
        Check ($s.Fmt -eq 'Format8bppIndexed') "indexed_opaque loads as $($s.Fmt) (exercises the tool's manual palette-expansion path)"
    }
}

Write-Host '=== NN MODE: indexed-PNG corner spot checks ==='
$s = Get-Px (Join-Path $inDir 'indexed_pal_64x48.png')
$d = Get-Px (Join-Path $nnDir 'indexed_pal_64x48.png')
$sv = Hex $s.P[0];        $dv = Hex $d.P[0]
Check ($sv -eq '00000000' -and $dv -eq '00000000') "palette entry 0 (transparent) at (0,0): src=$sv out=$dv expected=00000000"
$sv = Hex $s.P[47*64+63]; $dv = Hex $d.P[95*128+127]
Check ($sv -eq 'FFA05F46' -and $dv -eq 'FFA05F46') "palette entry 10 at (63,47): src=$sv out=$dv expected=FFA05F46"
$s = Get-Px (Join-Path $inDir 'indexed_opaque_64x48.png')
$d = Get-Px (Join-Path $nnDir 'indexed_opaque_64x48.png')
$sv = Hex $s.P[0];        $dv = Hex $d.P[0]
Check ($sv -eq 'FF000000' -and $dv -eq 'FF000000') "no-tRNS variant entry 0 at (0,0): src=$sv out=$dv expected=FF000000"
$sv = Hex $s.P[47*64+63]; $dv = Hex $d.P[95*128+127]
Check ($sv -eq 'FFA05F46' -and $dv -eq 'FFA05F46') "no-tRNS variant entry 10 at (63,47): src=$sv out=$dv expected=FFA05F46"

Write-Host '=== NN MODE: corner spot checks (src -> out corners) ==='
$s = Get-Px (Join-Path $inDir 'rgba_gradient_64x48.png')
$d = Get-Px (Join-Path $nnDir 'rgba_gradient_64x48.png')
$corners = @(
    @{sx=0;  sy=0;  exp='FFFF0000'; what='opaque red (0,0)'},
    @{sx=63; sy=0;  exp='8000FF00'; what='HALF-ALPHA green (63,0) - premultiply canary'},
    @{sx=0;  sy=47; exp='000000FF'; what='transparent-with-blue (0,47)'},
    @{sx=63; sy=47; exp='FFFFFFFF'; what='opaque white (63,47)'}
)
foreach ($c in $corners) {
    $sv = Hex $s.P[$c.sy*64+$c.sx]
    $dv = Hex $d.P[(2*$c.sy)*128+2*$c.sx]
    Check ($sv -eq $c.exp -and $dv -eq $c.exp) "$($c.what): src=$sv out=$dv expected=$($c.exp)"
}

Write-Host '=== NN MODE: alpha histogram exactly 4x source (gradient) ==='
$hs = AlphaHist $s; $hd = AlphaHist $d
$mismatch = 0
for ($i=0; $i -lt 256; $i++) { if ($hd[$i] -ne 4*$hs[$i]) { $mismatch++ } }
Check ($mismatch -eq 0) "all 256 alpha bins: out == 4 x src ($mismatch bins wrong)"
Write-Host ("        sample bins  a=0: {0}->{1}  a=128: {2}->{3}  a=255: {4}->{5}" -f $hs[0],$hd[0],$hs[128],$hd[128],$hs[255],$hd[255])

# ------------------------------------------------------------------ HQ checks
Write-Host '=== HQ MODE: dimensions ==='
foreach ($n in $names) {
    $s = Get-Px (Join-Path $inDir $n)
    $d = Get-Px (Join-Path $hqDir $n)
    Check ($d.W -eq 2*$s.W -and $d.H -eq 2*$s.H) "$n dims $($s.W)x$($s.H) -> $($d.W)x$($d.H) (exactly 2x)"
}

Write-Host '=== HQ MODE: flat opaque = zero color shift, zero edge bleed ==='
$d = Get-Px (Join-Path $hqDir 'flat_opaque_32x32.png')
$bad = 0; $expect = [System.Drawing.Color]::FromArgb(255,77,144,201).ToArgb()
foreach ($p in $d.P) { if ($p -ne $expect) { $bad++ } }
Check ($bad -eq 0) "all $($d.P.Count) pixels exactly FF4D90C9 ($bad deviations - includes all edges/corners)"

Write-Host '=== HQ MODE: flat semi-transparent premultiply canary ==='
$d = Get-Px (Join-Path $hqDir 'flat_semi_32x32.png')
$expect = [System.Drawing.Color]::FromArgb(128,40,200,90).ToArgb()
$maxDev = 0
foreach ($p in $d.P) {
    foreach ($sh in 24,16,8,0) {
        $dev = [math]::Abs((($p -shr $sh) -band 0xFF) - (($expect -shr $sh) -band 0xFF))
        if ($dev -gt $maxDev) { $maxDev = $dev }
    }
}
Check ($maxDev -le 1) "80(A) 28,C8,5A(RGB) round-trip, max per-channel deviation = $maxDev (<=1)"

Write-Host '=== HQ MODE: gradient alpha histogram roughly preserved ==='
$s = Get-Px (Join-Path $inDir 'rgba_gradient_64x48.png')
$d = Get-Px (Join-Path $hqDir 'rgba_gradient_64x48.png')
$sumS = 0.0; foreach ($p in $s.P) { $sumS += ($p -shr 24) -band 0xFF }
$sumD = 0.0; foreach ($p in $d.P) { $sumD += ($p -shr 24) -band 0xFF }
$meanS = $sumS/$s.P.Count; $meanD = $sumD/$d.P.Count
Check ([math]::Abs($meanS-$meanD) -le 1.0) ("mean alpha src={0:N3} out={1:N3} delta={2:N3} (<=1.0)" -f $meanS,$meanD,($meanS-$meanD))
$hs = AlphaHist $s; $hd = AlphaHist $d
$l1 = 0.0
for ($i=0; $i -lt 256; $i++) { $l1 += [math]::Abs($hd[$i]/4.0 - $hs[$i]) }
$ratio = $l1 / $s.P.Count
Check ($ratio -le 0.60) ("alpha-histogram L1 distance (out/4 vs src) = {0:N1} = {1:P1} of pixels (bicubic redistributes neighbours; <=60% tolerance)" -f $l1,$ratio)

# --------------------------------------------------------------------- result
Write-Host ''
if ($script:fails -eq 0) { Write-Host 'ALL CHECKS PASSED'; exit 0 }
else { Write-Host "$($script:fails) CHECK(S) FAILED"; exit 1 }
