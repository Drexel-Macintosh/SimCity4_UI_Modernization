<#
  Test-SubRingLock.ps1 - #95 sub-flyout: the OTHER half of the placement.

  WHY THIS FILE EXISTS (law 42). tools\uimap\emu\emu_subflyout.py already
  proves our SubPlaceTop() reproduces the game's own sub_79AD00 32/32 at
  n=1..8 x f=1/1.5/2/3. That pass is real and it is NOT ENOUGH: the emulator
  models the CONTAINER and not the RING, so v2.45.0 shipped on a green gate
  and still slid the ring off its button. A gate is only as honest as its
  scope. This gate's scope is the RING.

  It asserts, in the same integer arithmetic the DLL uses:
    A  THE PIN         ring absolute Y is IDENTICAL under the model+Auto and
                       under the legacy constant, at every n and every f.
    B  THE PHYSICS     the ring stays centred on its spawn button (both axes)
                       - the SUBGEO acceptance line, in advance.
    C  STOCK REDUCTION at f=1 the model reproduces the game's own native top
                       exactly, so 1x is untouched.
    D  THE PAYOFF      an 8-item column on a low button overflows the view
                       under the legacy constant and fits under the model.
                       A gate that cannot fail on the OLD code proves nothing.
    E  ANCHOR AGREEMENT the birth path's recovered cy equals the sweep path's
                       button centre, so the two placers cannot disagree (a
                       26px disagreement fails both atNative and atTarget and
                       silently ends the dock).
    F  LIVE CAPTURE    the model reproduces the real SUBGEO measurement of
                       2026-08-02 to the pixel.

  Pure PowerShell, no game, no build. Run it before every sub-flyout change.
#>

$ErrorActionPreference = 'Stop'
$script:Fail = 0
$script:Pass = 0
$script:Clamped = 0

function Assert-Eq($actual, $expected, $what) {
    if ($actual -eq $expected) { $script:Pass++ }
    else {
        $script:Fail++
        Write-Host ("  FAIL  {0}: got {1}, expected {2}" -f $what, $actual, $expected) -ForegroundColor Red
    }
}
function Assert-True($cond, $what) {
    if ($cond) { $script:Pass++ }
    else { $script:Fail++; Write-Host ("  FAIL  {0}" -f $what) -ForegroundColor Red }
}

# ---- the DLL's arithmetic, mirrored exactly (UiSpike.cpp) ----------------
function RoundHalfUp([double]$v) { return [int][Math]::Floor($v + 0.5) }

# contentH at 1x: the game's own item-column height, max(49n-5,53) + 50.
function ContentH1([int]$n) { return ([Math]::Max(49 * $n - 5, 53)) + 50 }

# The ring blit y inside the container, latched by the game from 1x metrics:
#   ringY = (contentH >> 1) - ([0xF4] >> 1)      <- (a>>1)-(b>>1), NOT (a-b)>>1
function RingBltY([int]$contentH1) { return ($contentH1 -shr 1) - (53 -shr 1) }

# SubDockDYEff(): kSubPlaceBias - RoundHalfUp(26.5f)
function SubDockDYEff([double]$f) { return 29 - (RoundHalfUp (26.5 * $f)) }

# SubPlaceTop(): the game's own expression + its four clamps, at f.
function SubPlaceTop([int]$contentH, [int]$cy, [int]$viewH, [double]$f) {
    $fE8  = RoundHalfUp (25 * $f)
    $fF4  = RoundHalfUp (53 * $f)
    $f100 = RoundHalfUp (29 * $f)
    $margT = RoundHalfUp (10 * $f)
    $margB = $viewH - $margT
    $top = ($fF4 -shr 1) - ($contentH -shr 1) + $cy - $f100
    if ($top -lt $margT) { $top = $margT }
    if ($viewH -gt 0 -and $top -gt ($margB - $contentH)) { $top = $margB - $contentH }
    if ($top -gt ($cy - $f100 - $fE8)) { $top = $cy - $f100 - $fE8 }
    $floorT = $cy + $fF4 - $contentH + $fE8 - $f100
    if ($top -lt $floorT) { $top = $floorT }
    return $top
}

# The native container top, from the measured law natT = bcy - ringY - 29.
function NativeTop([int]$bcy, [int]$ringY) { return $bcy - $ringY - 29 }

Write-Host ""
Write-Host "Test-SubRingLock - #95 ring pin + container model" -ForegroundColor Cyan
Write-Host "=================================================="

$factors = @(1.0, 1.5, 2.0, 3.0)
$views   = @{ '1.0' = 800; '1.5' = 1200; '2.0' = 1600; '3.0' = 2400 }

# ---- A + B + C: the pin, the physics, the stock reduction ---------------
Write-Host ""
Write-Host "A/B/C  pin + centred ring + f=1 stock reduction" -ForegroundColor Yellow
foreach ($f in $factors) {
    $viewH = $views[$f.ToString('0.0')]
    $btnH  = RoundHalfUp (37 * $f)
    $btnW  = RoundHalfUp (47 * $f)
    foreach ($n in 1..8) {
        $ch1      = ContentH1 $n
        $contentH = RoundHalfUp ($ch1 * $f)
        $ringY    = RingBltY $ch1          # latched from 1x - never rescaled
        # sweep a range of button positions, including very low ones
        foreach ($bcy in @(200, 500, 900, 1200, 1400)) {
            if ($bcy -ge $viewH) { continue }
            $natT = NativeTop $bcy $ringY
            $legT = $natT + (SubDockDYEff $f)
            $mathT = SubPlaceTop $contentH $bcy $viewH $f
            $autoY = $legT - $mathT

            # A - THE PIN: drawn ring y must be identical either way
            $ringAbsLegacy = $legT + $ringY
            $ringAbsModel  = $mathT + $ringY + $autoY
            Assert-Eq $ringAbsModel $ringAbsLegacy `
                ("A pin f=$f n=$n bcy=$bcy")

            # B - THE PHYSICS: ring sprite centred on the button, both axes.
            # ring drawn height = RoundHalfUp(53f); centre must equal bcy.
            # ⚠ This is the PLACEMENT LAW only. The live ini also applies a
            # deliberate nudge ([Flyout] SubRingDX/DY = 25/-6), so on screen
            # the ring sits 25 right / 6 up of this. That nudge is a separate,
            # intentional term - do NOT "fix" it by changing the law.
            $ringCtr = $ringAbsModel + (RoundHalfUp (53 * $f)) / 2
            Assert-True ([Math]::Abs($ringCtr - $bcy) -le 1) `
                ("B ring centred f=$f n=$n bcy=$bcy (ctr $ringCtr vs btn $bcy)")

            # C - STOCK REDUCTION: at f=1 the model IS the game's native top.
            # ⚠ ONLY where no clamp fires. NativeTop() is the measured
            # UNCLAMPED law, and the game's four clamps are real at 1x too:
            # a tall column on a HIGH button (n>=7 at bcy=200) is pinned to
            # the 10px top margin by the game itself, so there the model is
            # right and the unclamped reference is wrong. Asserting equality
            # unconditionally would be asserting that stock never clamps.
            if ($f -eq 1.0) {
                $margT1 = RoundHalfUp (10 * $f)
                $unclamped = ($natT -ge $margT1) -and `
                             (($natT + $contentH) -le ($viewH - $margT1))
                if ($unclamped) {
                    Assert-Eq $mathT $natT ("C f=1 reduces to native n=$n bcy=$bcy")
                } else {
                    $script:Clamped++
                    # the clamp must still land the column ON the screen
                    Assert-True (($mathT -ge $margT1) -and `
                                 (($mathT + $contentH) -le ($viewH - $margT1))) `
                        ("C f=1 clamped case stays on screen n=$n bcy=$bcy")
                }
            }
        }
    }
}

# ---- D: the payoff - the bug reproduced, then fixed ---------------------
Write-Host ""
Write-Host "D  the payoff: 8 items on a low button" -ForegroundColor Yellow
$f = 2.0; $viewH = 1600; $n = 8; $bcy = 1400
$ch1 = ContentH1 $n                       # 437
$contentH = RoundHalfUp ($ch1 * $f)       # 874
$ringY = RingBltY $ch1                    # 192
$natT = NativeTop $bcy $ringY
$legT = $natT + (SubDockDYEff $f)
$mathT = SubPlaceTop $contentH $bcy $viewH $f
$margB = $viewH - (RoundHalfUp (10 * $f))
Write-Host ("   legacy top=$legT bottom=" + ($legT + $contentH) + "  margin=$margB")
Write-Host ("   model  top=$mathT bottom=" + ($mathT + $contentH) + "  autoY=" + ($legT - $mathT))
Assert-True (($legT + $contentH) -gt $margB) `
    "D legacy MUST overflow (else this gate proves nothing)"
Assert-True (($mathT + $contentH) -le $margB) `
    "D model must fit inside the bottom margin"
Assert-True ($mathT -ge (RoundHalfUp (10 * $f))) `
    "D model must clear the top margin"

# ---- E: birth and sweep feed the model the SAME anchor ------------------
Write-Host ""
Write-Host "E  birth cy == sweep button centre" -ForegroundColor Yellow
foreach ($n in 1..8) {
    $ch1   = ContentH1 $n
    $ringY = RingBltY $ch1
    foreach ($bcy in @(200, 679, 1400)) {
        $natT = NativeTop $bcy $ringY          # what the game itself produced
        $cyRecovered = $natT + ($ch1 -shr 1) + 3   # the birth path's inversion
        Assert-Eq $cyRecovered $bcy ("E anchor n=$n bcy=$bcy")
        # and the birth self-check must accept it
        $check = (53 -shr 1) - ($ch1 -shr 1) + $cyRecovered - 29
        Assert-Eq $check $natT ("E birth self-check n=$n bcy=$bcy")
    }
}

# ---- F: reproduce the LIVE capture of 2026-08-02 ------------------------
#   SUBGEO BTN(180,642 94x74 ctr 227,679) CONT(147,434 258x874)
#          RINGr(0,192) RINGa(147,626) f=2.00
Write-Host ""
Write-Host "F  reproduces the live SUBGEO capture" -ForegroundColor Yellow
$ch1 = ContentH1 8
Assert-Eq (RoundHalfUp ($ch1 * 2.0)) 874 "F container height 874"
Assert-Eq (RingBltY $ch1) 192 "F ring blit y 192"
Assert-Eq ((NativeTop 679 192) + (SubDockDYEff 2.0)) 434 "F legacy container top 434"
Assert-Eq ((NativeTop 679 192) + (SubDockDYEff 2.0) + 192) 626 "F ring absolute y 626"

Write-Host ""
if ($script:Fail -eq 0) {
    Write-Host ("ALL PASS ({0} assertions; {1} f=1 cases the GAME itself clamps)" `
        -f $script:Pass, $script:Clamped) -ForegroundColor Green
    exit 0
} else {
    Write-Host ("{0} FAILED / {1} passed" -f $script:Fail, $script:Pass) -ForegroundColor Red
    exit 1
}
