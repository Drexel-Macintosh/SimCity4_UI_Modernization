===============================================================================
  SC4UIScale v@VERSION@  -  UI scaling for SimCity 4 Deluxe 1.1.641
===============================================================================

SimCity 4's interface was designed for 1024x768. On a modern screen the game
world looks fine but the buttons, panels and text shrink to the point of being
unusable. This mod draws the UI ELEMENTS larger while the game keeps rendering
the world at your monitor's native resolution.

It is not whole-frame upscaling. The world stays sharp.

This is the first public release. Earlier version numbers belong to internal
development builds that were never published.


-------------------------------------------------------------------------------
  INSTALL  (about 30 seconds)
-------------------------------------------------------------------------------

1. CLOSE SIMCITY 4 COMPLETELY. The game holds these files open while it runs.

2. Copy EVERYTHING inside this bundle's  Plugins\  folder into:

       Documents\SimCity 4\Plugins\

   Keep the folder structure. The  zzz-SC4UIScale\  subfolder MUST stay a
   subfolder - SimCity 4 loads root files before subfolders, and those files
   have to win against other mods. Putting them in the root breaks them
   silently.

3. Start the game. That is it.

There is no configuration step. The mod measures the resolution the game
actually renders at and picks a scale factor (1.5x, 2x or 3x) by itself.

   Or run  Install.ps1  from this folder and it does step 2 for you.


-------------------------------------------------------------------------------
  DID IT WORK?
-------------------------------------------------------------------------------

The UI will be visibly larger the moment you reach the main menu.

If nothing changed, open:

    Documents\SimCity 4\Plugins\SC4UIScale.log

The first few lines report the resolution it detected and the tier it chose.
The log is rewritten on every launch, so read it after the run you care about.

The tier is chosen from the resolution the game actually renders at:

    1.5x    from 1320 x 900
    2x      from 1760 x 1200
    3x      from 2640 x 1800

Below 1320 x 900 there is not enough screen to scale into, so the mod
deliberately stays completely inert and the game is exactly stock. That is not
a failure; the log says so explicitly.


-------------------------------------------------------------------------------
  UNINSTALL
-------------------------------------------------------------------------------

Delete these from  Documents\SimCity 4\Plugins\ :

    SC4UIScale.dll
    SC4UIScale.ini
    SC4UIScale.log
    z_SC4UIScale_*.dat            (every file starting z_SC4UIScale_)
    FontStyle-2x.ini, FontStyle-15x.ini, FontStyle-3x.ini
    FontStyle.ini                 (see the note below before deleting)
    zzz-SC4UIScale\               (the whole folder)

AND ONE FILE IN THE GAME'S OWN FOLDER. The game only reads a loose font file
from its install directory, so the mod copies the matching font there on every
launch. Delete it too, or the game keeps using the enlarged font after you
remove everything above:

    <SimCity 4 install>\Plugins\FontStyle.ini

If you had your OWN FontStyle.ini before installing, the mod saved it once as
FontStyle.ini.user-original and never touched it again. Look for that file in
BOTH Plugins folders and rename it back to FontStyle.ini instead of just
deleting it. If it is not there, you had no font file of your own and deleting
is correct - the game falls back to its built-in font.

Nothing else is written anywhere, there are no registry keys, and your cities
and regions are never touched.


-------------------------------------------------------------------------------
  SETTINGS
-------------------------------------------------------------------------------

SC4UIScale.ini sits beside the DLL and is commented throughout. You do not
need to touch it. The two keys worth knowing:

    ScaleAll=1        the in-city UI. Set 0 to disable that half.
    ScaleRegion=1     the region screen, including the region map itself.

DO NOT DELETE THOSE TWO. They are the only keys in the file that do not fall
back to a working default - remove either and that half of the mod silently
does nothing.

Region screen extras: mouse wheel zooms the region map, five steps each way.


-------------------------------------------------------------------------------
  REQUIREMENTS AND COMPATIBILITY
-------------------------------------------------------------------------------

  * SimCity 4 DELUXE / Rush Hour, version 1.1.641. Other builds are rejected
    at load with a log line rather than misbehaving.
  * Windows 8 or later.
  * IF YOUR SCREEN IS WIDER THAN 2048 PIXELS you also need a graphics wrapper
    such as dgVoodoo2. SimCity 4's DirectX 7 renderer cannot make a drawing
    surface larger than 2048x2048, and the game crashes without a wrapper at
    2560-wide and above. That is the 2003 renderer, not this mod - but you
    will meet it here. dgVoodoo2 is separate third-party software, is NOT
    included in this bundle, and you install it yourself.

Plays well with the usual mod set - NAM, CAM, and the null45 / memo33 DLL
families. Where another mod replaces a dialog this mod scales that mod's
version instead of fighting it.

Another UI-SCALING mod will conflict - only one thing can own the layout.

If the game looks stretched or zoomed from the very first frame, that is
Windows DPI virtualisation, not this mod. It looks similar, this mod does not
cause it, and removing this mod will not fix it - check the compatibility
settings on the game's executable.


-------------------------------------------------------------------------------
  KNOWN ISSUES
-------------------------------------------------------------------------------

  * At the 1.5x tier, two problems remain open: the last item in a flyout
    needs a scroll before it appears, and the dashboard city map can render
    incorrectly. The 2x and 3x tiers are more heavily verified and cannot
    show either problem.

  * The intro video does not scale.


-------------------------------------------------------------------------------
  LICENCE  -  short version: do whatever you want
-------------------------------------------------------------------------------

The code written for this project is PUBLIC DOMAIN (CC0 1.0). No copyright is
claimed and no attribution is required.

It does statically link two third-party libraries whose terms you must honour
if you redistribute a build of it:

    gzcom-dll   LGPL-2.1-or-later   (Nelson Gomez)
    MinHook     BSD-2-Clause        (Tsuda Kageyu)

See LICENSE.txt and THIRD-PARTY-NOTICES.md in this folder for the full detail.

SimCity 4 is the property of Electronic Arts. This is an unofficial,
unaffiliated modification and contains no EA code.


-------------------------------------------------------------------------------
  VERIFYING WHAT YOU GOT
-------------------------------------------------------------------------------

SHA256SUMS.txt lists a hash for every file under Plugins\. To check them:

    Get-FileHash .\Plugins\SC4UIScale.dll -Algorithm SHA256

and compare against the matching line.
