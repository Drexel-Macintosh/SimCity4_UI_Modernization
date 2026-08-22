<#
  Apply-4GBPatch.ps1 - set (or clear) LARGE_ADDRESS_AWARE on SimCity 4.exe.

  WHY. SimCity 4 is a 32-bit exe from 2003. Without the LARGE_ADDRESS_AWARE
  bit it gets 2 GB of user address space no matter how much RAM the machine
  has. At high resolutions - 2400x1600 is 3.84 Mpx, 5.9x the pixels of
  1024x768 - the DirectDraw/D3D7 surfaces plus our 2x art packages can walk
  into that ceiling. The failure mode is NOT a clean "out of memory": an
  allocation returns null, nothing checks it, and the game dies on a null
  dereference. That is exactly the crash recorded 2026-08-05:

      Exception code: 0xC0000005 ACCESS_VIOLATION
      Exception address: 0x00884fe1  (SimCity 4.exe, 0x01:0x0047dfe1)
      EAX: 00000000   ECX: 00000000        <- the null that was used

  WHAT IT CHANGES. Exactly ONE BIT: 0x0020 in the COFF Characteristics word
  of the PE header. No code is modified, nothing is injected, the file grows
  by zero bytes. This is what every "SC4 4GB patch" does.

  ⚠ THIS MODIFIES A GAME FILE. That is normally forbidden in this project.
  It is done here only because the user asked for it explicitly, and it is
  reversible three ways: -Undo below, the .pre4gb-backup copy this makes, or
  Steam -> SimCity 4 -> Properties -> Installed Files -> Verify.

  ⚠ MUST RUN ELEVATED - the exe lives under Program Files (x86).

    .\Apply-4GBPatch.ps1            apply
    .\Apply-4GBPatch.ps1 -Status    report only, change nothing
    .\Apply-4GBPatch.ps1 -Undo      clear the bit again
#>
[CmdletBinding()]
param(
    [string] $Exe = "C:\Program Files (x86)\Steam\steamapps\common\SimCity 4 Deluxe\Apps\SimCity 4.exe",
    [switch] $Status,
    [switch] $Undo
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Exe)) {
    Write-Output "NOT FOUND: $Exe"
    Write-Output "Pass -Exe <path> if the game is installed somewhere else."
    exit 1
}

if (Get-Process "SimCity 4" -ErrorAction SilentlyContinue) {
    Write-Output "SimCity 4 is RUNNING. Close it from the game's own menu first."
    Write-Output "Do NOT force-kill it - it runs elevated and holds files open."
    exit 1
}

# --- locate the Characteristics word -----------------------------------------
# PE layout: 0x3C holds e_lfanew -> "PE\0\0" (4) + COFF header, whose
# Characteristics is the last 2 bytes of that 20-byte header, i.e. +18.
function Get-CharPos([System.IO.Stream]$s) {
    $r = New-Object System.IO.BinaryReader($s)
    $s.Position = 0x3C
    $peOff = $r.ReadInt32()
    $s.Position = $peOff
    if ($r.ReadUInt32() -ne 0x00004550) { throw "not a PE file (bad signature)" }
    return $peOff + 4 + 18
}

if ($Status) {
    $s = [System.IO.File]::OpenRead($Exe)
    try {
        $pos = Get-CharPos $s
        $s.Position = $pos
        $c = (New-Object System.IO.BinaryReader($s)).ReadUInt16()
    } finally { $s.Close() }
    Write-Output ("Characteristics: 0x{0:X4}" -f $c)
    Write-Output ("LARGE_ADDRESS_AWARE: {0}" -f $(if (($c -band 0x20) -ne 0) { "SET (patched)" } else { "clear (stock 2 GB)" }))
    exit 0
}

# --- back up once, before the first modification -----------------------------
$bak = "$Exe.pre4gb-backup"
if (-not (Test-Path $bak)) {
    Copy-Item $Exe $bak -Force
    Write-Output "backup written: $bak"
} else {
    Write-Output "backup already present (not overwritten): $bak"
}

$s = [System.IO.File]::Open($Exe, 'Open', 'ReadWrite')
try {
    $pos = Get-CharPos $s
    $r = New-Object System.IO.BinaryReader($s)
    $w = New-Object System.IO.BinaryWriter($s)
    $s.Position = $pos
    $old = $r.ReadUInt16()
    $new = if ($Undo) { $old -band (-bnot 0x0020) } else { $old -bor 0x0020 }
    if ($new -eq $old) {
        Write-Output ("already in the requested state: 0x{0:X4}" -f $old)
        exit 0
    }
    $s.Position = $pos
    $w.Write([UInt16]$new)
    $s.Flush()
} finally { $s.Close() }

# --- verify by re-reading from disk, never from the variable we just wrote ----
$v = [System.IO.File]::OpenRead($Exe)
try {
    $pos = Get-CharPos $v
    $v.Position = $pos
    $chk = (New-Object System.IO.BinaryReader($v)).ReadUInt16()
} finally { $v.Close() }

Write-Output ("Characteristics: 0x{0:X4} -> 0x{1:X4}  (re-read from disk: 0x{2:X4})" -f $old, $new, $chk)
Write-Output ("LARGE_ADDRESS_AWARE: {0}" -f $(if (($chk -band 0x20) -ne 0) { "SET" } else { "clear" }))
if ((($chk -band 0x20) -ne 0) -ne (-not $Undo)) { Write-Output "MISMATCH - the write did not stick."; exit 1 }
Write-Output "done."
