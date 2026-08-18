# Generates synthetic test PNGs (with alpha, indexed palette, odd sizes) into test\in\.
# Deterministic pixel formulas so Verify-Upscale.ps1 can predict every value.
Add-Type -AssemblyName System.Drawing

$here  = Split-Path -Parent $MyInvocation.MyCommand.Path
$inDir = Join-Path $here 'test\in'
$sub   = Join-Path $inDir 'sub'
New-Item -ItemType Directory -Force $inDir | Out-Null
New-Item -ItemType Directory -Force $sub   | Out-Null

function Save-Png([System.Drawing.Bitmap]$bmp, [string]$path) {
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host "wrote $path"
}

# --- 1. rgba_gradient 64x48, 32bppArgb, known corner values, varied alpha -----
# pixel(x,y): A=(x*4+y)%256  R=(x*4)%256  G=(y*5)%256  B=(x -bxor y)%256
# corner overrides:
#   (0,0)   = A255 R255 G0   B0    (opaque red)
#   (63,0)  = A128 R0   G255 B0    (half-alpha green - premultiply canary)
#   (0,47)  = A0   R0   G0   B255  (fully transparent, non-zero blue)
#   (63,47) = A255 R255 G255 B255  (opaque white)
$w=64; $h=48
$bmp = New-Object System.Drawing.Bitmap($w,$h,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
for ($y=0; $y -lt $h; $y++) {
    for ($x=0; $x -lt $w; $x++) {
        $a=($x*4+$y)%256; $r=($x*4)%256; $g=($y*5)%256; $b=($x -bxor $y)%256
        $bmp.SetPixel($x,$y,[System.Drawing.Color]::FromArgb($a,$r,$g,$b))
    }
}
$bmp.SetPixel(0,0,    [System.Drawing.Color]::FromArgb(255,255,0,0))
$bmp.SetPixel(63,0,   [System.Drawing.Color]::FromArgb(128,0,255,0))
$bmp.SetPixel(0,47,   [System.Drawing.Color]::FromArgb(0,0,0,255))
$bmp.SetPixel(63,47,  [System.Drawing.Color]::FromArgb(255,255,255,255))
Save-Png $bmp (Join-Path $inDir 'rgba_gradient_64x48.png')

# --- 2. indexed 8bpp palette 64x48, entry 0 fully transparent ----------------
# GDI+'s PNG encoder does NOT reliably write color-type-3 files, so this one is
# hand-crafted byte-by-byte: IHDR(bitdepth 8, colortype 3) + PLTE + tRNS + IDAT.
# palette entry i (0..15): i=0 -> ARGB(0,0,0,0); else ARGB(255, i*16, 255-i*16, i*7)
# pixel index = ([x/4] + [y/4]) % 16 => (0,0) idx 0 (transparent), (63,47) idx 10 = FFA05F46
$crcTab = New-Object uint32[] 256
for ($n=0; $n -lt 256; $n++) {
    $c = [uint32]$n
    for ($k=0; $k -lt 8; $k++) {
        if ($c -band 1) { $c = 0xEDB88320L -bxor ($c -shr 1) } else { $c = $c -shr 1 }
        $c = [uint32]($c -band 0xFFFFFFFFL)
    }
    $crcTab[$n] = $c
}
function Get-Crc32([byte[]]$data) {
    $c = [uint32]0xFFFFFFFFL
    foreach ($b in $data) { $c = $crcTab[($c -bxor $b) -band 0xFF] -bxor ($c -shr 8) }
    [uint32](($c -bxor 0xFFFFFFFFL) -band 0xFFFFFFFFL)
}
function New-Chunk([string]$type, [byte[]]$payload) {
    $typeBytes = [Text.Encoding]::ASCII.GetBytes($type)
    $lenBytes  = [BitConverter]::GetBytes([UInt32]$payload.Length); [Array]::Reverse($lenBytes)
    $crcInput  = New-Object byte[] ($typeBytes.Length + $payload.Length)
    [Array]::Copy($typeBytes,0,$crcInput,0,4); [Array]::Copy($payload,0,$crcInput,4,$payload.Length)
    $crcBytes = [BitConverter]::GetBytes((Get-Crc32 $crcInput)); [Array]::Reverse($crcBytes)
    $lenBytes + $typeBytes + $payload + $crcBytes
}
$w=64; $h=48
# IHDR: width, height, bitdepth 8, colortype 3 (palette), compression 0, filter 0, interlace 0
$ihdr = New-Object byte[] 13
$wb=[BitConverter]::GetBytes([UInt32]$w); [Array]::Reverse($wb); [Array]::Copy($wb,0,$ihdr,0,4)
$hb=[BitConverter]::GetBytes([UInt32]$h); [Array]::Reverse($hb); [Array]::Copy($hb,0,$ihdr,4,4)
$ihdr[8]=8; $ihdr[9]=3; $ihdr[10]=0; $ihdr[11]=0; $ihdr[12]=0
# PLTE (16 RGB entries) + tRNS (alpha per entry)
$plte = New-Object byte[] 48
$trns = New-Object byte[] 16
for ($i=0; $i -lt 16; $i++) {
    if ($i -eq 0) { $plte[0]=0; $plte[1]=0; $plte[2]=0; $trns[0]=0 }
    else {
        $plte[$i*3]   = ($i*16)%256
        $plte[$i*3+1] = (255-$i*16)%256
        $plte[$i*3+2] = ($i*7)%256
        $trns[$i] = 255
    }
}
# raw scanlines: filter byte 0 + 64 palette indices per row
$raw = New-Object byte[] (($w+1)*$h)
for ($y=0; $y -lt $h; $y++) {
    $rowOfs = $y*($w+1); $raw[$rowOfs] = 0
    for ($x=0; $x -lt $w; $x++) {
        $raw[$rowOfs+1+$x] = ([math]::Floor($x/4) + [math]::Floor($y/4)) % 16
    }
}
# zlib-wrap: 0x78 0x01 header + raw deflate + Adler32(raw)
$defMs = New-Object IO.MemoryStream
$def = New-Object IO.Compression.DeflateStream($defMs,[IO.Compression.CompressionMode]::Compress,$true)
$def.Write($raw,0,$raw.Length); $def.Close()
$a1=[uint32]1; $a2=[uint32]0
foreach ($b in $raw) { $a1 = ($a1 + $b) % 65521; $a2 = ($a2 + $a1) % 65521 }
$adler = [BitConverter]::GetBytes([UInt32](($a2 * 65536) + $a1)); [Array]::Reverse($adler)
$idat = [byte[]](0x78,0x01) + $defMs.ToArray() + $adler
$png = [byte[]](0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A) +
       (New-Chunk 'IHDR' $ihdr) + (New-Chunk 'PLTE' $plte) +
       (New-Chunk 'tRNS' $trns) + (New-Chunk 'IDAT' $idat) +
       (New-Chunk 'IEND' (New-Object byte[] 0))
[IO.File]::WriteAllBytes((Join-Path $inDir 'indexed_pal_64x48.png'), $png)
Write-Host "wrote $(Join-Path $inDir 'indexed_pal_64x48.png') (hand-crafted colortype-3 palette PNG + tRNS)"

# --- 2b. same palette PNG WITHOUT tRNS (all entries opaque) ------------------
# GDI+ decodes pal+tRNS as 32bppArgb but keeps a plain palette PNG as
# Format8bppIndexed, so this variant exercises the tool's manual
# ExpandIndexed (palette lookup) code path. Entry 0 = opaque black here.
$png2 = [byte[]](0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A) +
        (New-Chunk 'IHDR' $ihdr) + (New-Chunk 'PLTE' $plte) +
        (New-Chunk 'IDAT' $idat) + (New-Chunk 'IEND' (New-Object byte[] 0))
[IO.File]::WriteAllBytes((Join-Path $inDir 'indexed_opaque_64x48.png'), $png2)
Write-Host "wrote $(Join-Path $inDir 'indexed_opaque_64x48.png') (colortype-3, no tRNS -> stays 8bppIndexed on load)"

# --- 3. flat opaque 32x32 (HQ no-color-shift check) --------------------------
$bmp = New-Object System.Drawing.Bitmap(32,32,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$c = [System.Drawing.Color]::FromArgb(255,77,144,201)
for ($y=0; $y -lt 32; $y++) { for ($x=0; $x -lt 32; $x++) { $bmp.SetPixel($x,$y,$c) } }
Save-Png $bmp (Join-Path $inDir 'flat_opaque_32x32.png')

# --- 4. flat semi-transparent 32x32 (HQ premultiplication canary) ------------
$bmp = New-Object System.Drawing.Bitmap(32,32,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$c = [System.Drawing.Color]::FromArgb(128,40,200,90)
for ($y=0; $y -lt 32; $y++) { for ($x=0; $x -lt 32; $x++) { $bmp.SetPixel($x,$y,$c) } }
Save-Png $bmp (Join-Path $inDir 'flat_semi_32x32.png')

# --- 5. odd-size 5x7 in a SUBFOLDER with an SC4-resource-ID-style name -------
# pixel(x,y): A=255 unless (x+y)%3==0 then A=64; R=x*40; G=y*30; B=200
$bmp = New-Object System.Drawing.Bitmap(5,7,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
for ($y=0; $y -lt 7; $y++) {
    for ($x=0; $x -lt 5; $x++) {
        $a = if (($x+$y)%3 -eq 0) { 64 } else { 255 }
        $bmp.SetPixel($x,$y,[System.Drawing.Color]::FromArgb($a,($x*40)%256,($y*30)%256,200))
    }
}
Save-Png $bmp (Join-Path $sub '0x856ddbac_0x46a006b0_0x02968802.png')

# --- 6. decoys: non-PNG extension + fake .png (bad magic) --------------------
Set-Content -Path (Join-Path $inDir 'notes.txt') -Value 'not an image' -Encoding ascii
[IO.File]::WriteAllBytes((Join-Path $inDir 'fake_webp.png'), [byte[]](0x52,0x49,0x46,0x46,1,2,3,4,0x57,0x45,0x42,0x50))
Write-Host 'wrote decoys (notes.txt, fake_webp.png)'
Write-Host 'DONE'
