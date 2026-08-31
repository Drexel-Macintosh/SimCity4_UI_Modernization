===============================================================================
  SC4UIScale v@VERSION@  -  UI scaling for SimCity 4 Deluxe 1.1.641
===============================================================================

SimCity 4's interface was designed for 1024x768. On a modern screen the game
world looks fine but the buttons, panels and text shrink to the point of being
unusable. This mod draws the UI ELEMENTS larger while the game keeps rendering
the world at your monitor's native resolution.

It is not whole-frame upscaling. The world stays sharp.

Version numbers below 4.0.0 belong to internal development builds that were
never published; the public release history starts at v4.0.0.


-------------------------------------------------------------------------------
  INSTALL  (about 30 seconds)
-------------------------------------------------------------------------------

1. CLOSE SIMCITY 4 COMPLETELY. The game holds these files open while it runs.

2. Copy EVERYTHING inside this bundle's  Plugins\  folder into:

       Documents\SimCity 4\Plugins\

   Keep the folder structure. The mod is TWO subfolders plus one loose
   file:

       Plugins\SC4UIScale.dll     (the game only loads DLLs from the
                                   top level - the DLL cannot move)
       Plugins\010-SC4UIScale\    (all the mod's packages and fonts)
       Plugins\zzz-SC4UIScale\    (overrides that must load after other mods)

   On its first launch the mod writes one more loose file beside the DLL:

       Plugins\SC4UIScale.ini     (your settings - created for you if
                                   missing, never overwritten, and kept at
                                   the root so upgrades cannot delete it)

   Both folder names are load-bearing - SimCity 4 loads plugin folders in
   name order, and each position is chosen so the right files win (and
   deliberately LOSE) against other mods. Do not rename them, and do not
   move their contents to the Plugins root.

3. Start the game. That is it.

There is no configuration step. The mod measures the resolution the game
actually renders at and picks a scale factor (1.5x, 2x or 3x) by itself.

   Or run  Install.ps1  from this folder and it does step 2 for you.


-------------------------------------------------------------------------------
  DID IT WORK?
-------------------------------------------------------------------------------

The UI will be visibly larger the moment you reach the main menu.

If nothing changed, open:

    Documents\SimCity 4\Plugins\010-SC4UIScale\SC4UIScale.log

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

Run  .\Install.ps1 -Uninstall  , or delete four things by hand from
Documents\SimCity 4\Plugins\ :

    010-SC4UIScale\               (the whole folder)
    zzz-SC4UIScale\               (the whole folder)
    SC4UIScale.dll                (loose at the root)
    SC4UIScale.ini                (loose at the root - your settings)

That is everything. The DLL and the ini are the only files this mod keeps at
the Plugins root: the game loads DLLs from the top level and nowhere else, and
the ini sits beside it so a package-manager update (which replaces the whole
package folder) cannot delete your settings. The log and everything else live
inside 010-SC4UIScale\ and go with the folder. (The same shape every
sc4pac-installed DLL mod uses: the .dll at the root, its data in a folder.)

(Upgrading from before v4.4.0? The mod moves your old root files - log, gcap,
csv - into 010-SC4UIScale\ by itself on the first launch. Your SC4UIScale.ini
stays at the root, which is where the mod reads it from v4.5.0 on.)

THE FONT IN THE GAME'S OWN FOLDER. The game reads a loose font file from two
fixed places and nowhere else - it does not look inside mod folders - so the
only way an enlarged font can apply at all is for the mod to put one at
<SimCity 4 install>\Plugins\FontStyle.ini while it runs. It removes that file
again when the game shuts down normally, leaving nothing behind.

  CORRECTED IN THIS RELEASE. Earlier versions RENAMED that file on exit
  instead of removing it, so a clean shutdown left a 23 KB
  FontStyle.ini.x1-disabled sitting in your SimCity 4 install folder
  permanently - which this file used to claim did not happen. If you have
  installed an older version, look in <SimCity 4 install>\Plugins\ and
  delete FontStyle.ini.x1-disabled by hand: it is ours, it is inert, and
  nothing needs it. This version also removes it for you on its next
  normal shutdown.

If the game CRASHED on its last run the mod never got to clean up: check
<SimCity 4 install>\Plugins\ and delete a leftover FontStyle.ini by hand, or
the game keeps using the enlarged font after everything above is gone.

If you had your OWN FontStyle.ini before installing, the mod saved it once as
FontStyle.ini.user-original and never touched it again, and it restores your
file rather than deleting anything of yours. Look for it in BOTH Plugins
folders and rename it back to FontStyle.ini if it is still there. If it is not
there, you had no font file of your own and deleting is correct - the game
falls back to its built-in font.

Nothing else is written anywhere, there are no registry keys, and your cities
and regions are never touched.


-------------------------------------------------------------------------------
  SETTINGS
-------------------------------------------------------------------------------

SC4UIScale.ini sits at the Plugins root, beside the DLL, and is commented
throughout. The mod creates it on its first launch if it is missing, and it is
never overwritten afterwards. You do not need to touch it. The two keys worth
knowing:

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

  ! FULL UI RESKINS (Scoty Carbon Skin and the like) NEED ONE EXTRA STEP.
    A reskin replaces the UI's art and dialog layouts wholesale - around 490
    of the same resources this mod scales - and it is designed to load after
    everything else, so its 1x versions win. The result is 1x art and
    1x-positioned dialogs inside a scaled UI: it looks broken, and it is not
    something this mod can fix by itself, because shipping a scaled copy of
    someone else's skin would mean redistributing their work.
    The build tools in the source repo rebuild the skin's OWN art and
    layouts at your scale factor, on your machine, from your copy of the
    skin (tools\research\carbon - start at CARBON-COMPAT.md). Scoty Carbon
    Skin 1.5 is supported end to end today.
    If you run a reskin without doing this, SC4UIScale.log says so in one
    line at startup - that line is the symptom, not a crash.

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
