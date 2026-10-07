# cIUIScaleInfo: ask SC4UIScale for the UI scale

From version 4.11.0, SC4UIScale registers a GZCOM class that other plugin DLLs
can query. It answers two questions:

- how much the game's UI is enlarged in this session
- how much the region map is enlarged right now

Copy [`cIUIScaleInfo.h`](cIUIScaleInfo.h) into your project. It needs only the
[gzcom-dll](https://github.com/nsgomez/gzcom-dll) headers. No rights are
reserved on it.

| | |
|---|---|
| Class ID | `GZCLSID_cIUIScaleInfo` = `0xB54643B5` |
| Interface ID | `GZIID_cIUIScaleInfo` = `0xA9885499` |
| First version | SC4UIScale 4.11.0 |

## Getting the object

```cpp
#include "cIUIScaleInfo.h"
#include "cRZAutoRefCount.h"

float QueryUIScale()
{
    cRZAutoRefCount<cIUIScaleInfo> info;
    if (RZGetFramework()->GetCOMObject()->GetClassObject(
            GZCLSID_cIUIScaleInfo, GZIID_cIUIScaleInfo, info.AsPPVoid()))
    {
        return info->GetUIScaleFactor();
    }
    return 1.0f;   // SC4UIScale is not installed, or is older than 4.11.0
}
```

Ask from your director's `PostAppInit` or later. The game loads plugin DLLs
one at a time and registers each DLL's classes when it loads, so a lookup made
from your constructor or `OnStart` can fail only because SC4UIScale has not
been loaded yet.

Look the object up when you need it and release it straight away, as the
sample does; a lookup is cheap. Do not keep the pointer past your director's
`PreAppShutdown`. At exit the game unloads every plugin DLL in path order
without asking them first, so a pointer still held when SC4UIScale's DLL is
unloaded points at code that no longer exists, and releasing it then crashes.

The object is a single static instance inside SC4UIScale. `AddRef` and
`Release` keep a count but never free it, so one `Release` too many cannot
free an object another DLL holds.

## The methods

| Method | Returns |
|---|---|
| `GetModVersion()` | The SC4UIScale version as `(major << 16) \| (minor << 8) \| patch`. For example, `0x040B00` is 4.11.0. |
| `GetUIScaleFactor()` | The factor the game's UI is enlarged by: `1.0` when SC4UIScale is not scaling, otherwise the tier (1.5, 2.0 or 3.0 today; treat it as any float). It is fixed for the session, because a new tier takes effect only after a restart. |
| `IsAutoScale()` | `true` when the factor was picked from the render resolution, `false` when the player set it by hand. |
| `GetRegionMapScale()` | Screen pixels per stock pixel of the region map, including the player's region zoom. A region cell that is 128 px wide in the stock game is `128 * scale` px wide on screen. `1.0` when SC4UIScale does not scale the region view. It is first set during SC4UIScale's own `PostAppInit`, which may run after yours, and it changes when the player zooms the region view. Read it each time you lay something out on the region view, not once at startup. |

SC4UIScale reports `1.0` in these cases:

- the player is on the stock tier
- scaling is turned off in the ini
- the game build is not 1.1.641

In all of them the class is still registered, so a successful lookup that
returns 1.0 means "installed, not scaling".

### Rounding

SC4UIScale draws a length of `L` stock pixels as `floor(L * factor + 0.5)`
pixels. That is the same rule its art and layout builders use. Round the same
way and your windows line up with the game's.

## What SC4UIScale already enlarges

Use this list to avoid enlarging something twice. It is read from the
SC4UIScale source; it has not yet been tested against a window from another
DLL.

- **Fonts.** At a scaled tier the game reads an enlarged font-style table, so
  text drawn with the game's own font styles is already larger. Scale your
  window geometry, not those font sizes.
- **The game's own art and `.UI` layouts.** These are replaced by enlarged
  copies. Art and `.UI` files that your DLL ships are drawn as you made them.
- **Dialogs under the main window.** This is where modal dialogs live. The
  runtime scaler touches only a fixed list of the game's own dialog IDs, so
  yours is left alone.
- **The region view.** The scaler touches only the game's own region panels,
  so yours are left alone.
- **The city view.** The scaler enlarges every visible direct child of the 3D
  city view that it does not explicitly skip. A window you add there is likely
  to be enlarged once by SC4UIScale. Either create it at stock size and let
  SC4UIScale enlarge it, or parent it elsewhere and scale it yourself.

## Checking it from the log

SC4UIScale makes the same lookup through the game's COM at startup. The result
is written to `SC4UIScale.log` in SC4UIScale's folder (by default
`Documents\SimCity 4\Plugins\010-SC4UIScale\SC4UIScale.log`):

```
API: cIUIScaleInfo answered through the game's COM (CLSID 0xB54643B5, IID 0xA9885499): version 4.11.0, UI factor 2.00 (auto), region map 2.00. Unknown IID refused: yes.
```

The line after it checks those answers against what the session actually
applied, and reads `API: the answers MATCH this session` when they agree.

A lookup that asks for an interface ID the class does not implement is
refused. The refusal is logged with that ID (the first eight refusals), so a
mistyped IID is distinguishable from "not installed".

## Stability

The interface is frozen. The IDs, the base class, and the methods and their
order never change, and the test `_tests\Test-UIScaleInfoApi.ps1` fails if
they do. Anything new goes in a new interface with a new IID. A DLL built
against this header keeps working with every later SC4UIScale.
