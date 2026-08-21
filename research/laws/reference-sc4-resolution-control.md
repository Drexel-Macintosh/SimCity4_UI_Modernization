# Controlling Resolution and Renderer

SimCity 4's render size, renderer backend and window mode are all controlled from
a single file. Read this before making any resolution or display change: the
number the game is asked for and the number it actually renders at are not always
the same, and mistaking one for the other produces a UI that looks catastrophically
mis-scaled while every configuration file reads correct.

## The one knob: SC4GraphicsOptions.ini

`<Documents>\SimCity 4\Plugins\SC4GraphicsOptions.ini` is read by the community
mod **SC4GraphicsOptions.dll**, not by the scaling DLL. It forces:

```ini
Driver=Software        ; or DirectX. Software = CPU render, no GPU, no wrapper, no 2048-wide cap.
WindowWidth=1024       ; stock modes: 800x600, 1024x768, 1280x1024, 1600x1200
WindowHeight=768
WindowMode=FullScreen
ForceDrawOnScroll=true ; leave true; fixes partial-redraw garble
```

Changing resolution means editing `WindowWidth` / `WindowHeight` here and
relaunching. Nothing else is involved.

Write this file without a BOM. The parser does not tolerate one.

## DirectX renders at the monitor's native mode, not the requested size

With `Driver=DirectX` behind a DirectDraw/Direct3D wrapper on a display wider than
2048 px, requesting `WindowWidth`/`WindowHeight=1600x1200` does **not** make the
game render 1600x1200. The wrapper renders at the monitor's native mode and
reports that size back to the game, so the `cIGZWin` tree is built at native size.
Only `Driver=Software` renders at the requested size.

The consequence is that any "sub-native resolution in production" test on such a
panel is really a native-resolution render. An auto-scale tier chosen by reading
the requested resolution out of the ini will disagree with the tier the render
actually needs — a 1600x1200 read picks 1.5x while the frame is really 2x — and
the result is a grossly oversized, blurry UI that looks like a scaling bug rather
than a resolution mismatch.

**The rule:** key auto-scale off the *actual* render resolution, not the requested
one.

- `Driver=DirectX` → render size = the monitor size from `GetSystemMetrics`.
- `Driver=Software` → render size = the requested `WindowWidth`/`WindowHeight`.

Set per-monitor-v2 DPI awareness **before** reading the monitor, so the values
come back in physical pixels. With that in place, DirectX on a large panel always
lands on the tier matching its native render, and a machine whose monitor genuinely
is 1600x1200 lands on 1.5x. The logic is then correct on any device.

## FontStyle.ini is probed by install path, not Documents

Disassembly of the probe order shows the game looks for `FontStyle.ini` at:

1. `<install>\Plugins\FontStyle.ini`
2. `<install>\FontStyle.ini`
3. inside DBPF archives

`<Documents>\SimCity 4\Plugins\` is **not** in that list. Loose `FontStyle.ini`
therefore has to live under the install directory; DAT files continue to load
normally from the Documents plugins folder, so it is easy to assume the loose ini
does too.

Symptom of getting this wrong: every frame and widget renders at the scaled size
while all text renders at 1x. Any test that appears to show a Documents-path
`FontStyle.ini` working is a timing confound — an earlier copy still resident, or
a DBPF fallback supplying the same values.

## The simple, correct stock setup

Software renderer plus a stock resolution plus the DirectDraw wrapper removed
gives a perfectly clean stock render with no GPU, wrapper or DPI complexity in the
picture. This is the configuration to use for stock comparisons and for any
sub-native testing.

1. `Driver=Software` in `SC4GraphicsOptions.ini`.
2. A stock `WindowWidth`/`WindowHeight` at or below 1600x1200.
3. Move the wrapper aside: rename `<install>\Apps\DDraw.dll` and
   `<install>\Apps\D3DImm.dll` to `.off`.
4. The UI scaler layers on top unchanged; at stock resolution its auto-scale tier
   goes inert unless a scaled package actually fits the render size.

## The wrapper is only for big-display DirectX play

The dgVoodoo wrapper (`DDraw.dll` + `D3DImm.dll` in `<install>\Apps\`, configured
by `dgVoodoo.conf`) exists solely because `Driver=DirectX` above 2048 px wide needs
a wrapper and a capable GPU. It is not required for correctness and not required
for testing scaling.

Do not route stock or sub-native resolutions through the wrapper. Doing so
reintroduces exactly the render-size mismatch described above. Restore the wrapper
only when deliberately running DirectX on a large display; when restored,
`ScalingMode=unspecified` in `dgVoodoo.conf` is the known-good value.

## ScaleRemap stays off

`[Scaling] UseScaleRemap=0` is the ini default and `false` is the code default.
ScaleRemap is the rejected whole-frame-upscaling approach. Its internal-versus-
presented size metrics are misleading under a present-scaling wrapper, because the
two transforms compose: the frame is scaled twice. It is never the right lever for
a resolution problem.

It remains present in the DLL only because its `AttachWindow` window-cover is
load-bearing for the large-display DirectX window. In software mode it is
irrelevant.

## Restoring after experiments

After any renderer or resolution experiment, put the machine back to the validated
production state before drawing conclusions from a later run:

- Wrapper DLLs restored under `<install>\Apps\`, `ScalingMode=unspecified`.
- All scaling plugin files present in the plugins folder.
- `SC4UIScale.ini` `Enabled=1`.
- Display back at native resolution.

Boot and confirm the log reports the expected tier and the expected count of
scaled panels. A configuration that merely *looks* restored on disk is not
restored until a launch says so.
