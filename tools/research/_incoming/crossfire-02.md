{
 "summary": "ANGLE 3 RESULT \u2014 it is a family, but not the family expected: the suspects are not scattered across the region screen, they are the ENTIRE city-select bubble and nothing else.\n\n**The stated premise is refuted.** \"NO child is the rating bar => it is painted INTO a GZWinBMP buffer\" is a blind-instrument null. The RGKID dump prints exactly four nesting levels (UiSpike.cpp:8910/8925/8945/8956, loops i/j/q/z). The bubble prints at level 2 (`RGKID 11.0`), so only two levels below the bubble root are ever reachable. The bar sits three levels below it. It IS a window: `id=0x4a553000 clsid=0xaa5d16a9 iid=IGZWinCustom area=(11,92,113,103)` = 102x11, in `tools\\uiscripts\\extracted\\T-00000000_G-96a006b0_I-ca539340.ui`.\nPOSITIVE CONTROL: the dump's last printed line `RGKID 11.0.11.0 (24,20 470x284)` is the inner BMP (2x of design 235x142). That window has NINE scripted children \u2014 the city name, mayor name and the three population figures, all of which visibly render in the bubble. None appear in the log. The level-5 silence is depth, not emptiness.\n\n**Root cause, one line:** `tools\\selective-safe\\build_selective_safe.py:113-114` lists all 9 region panels the runtime scales; `0x0A551C50` is absent. So the runtime doubles the bubble's windows (measured 516x500) while the builder classified every art it references as UNSCALED/untouched. 10 of 10 bubble arts ship 1x.\n\nThe Mayor Rating bar is simply the most VISIBLE member: its painter fills the window with a 102px-wide source run, so 1x-in-2x shows as a repeat instead of empty space.\n\nRANKED SUSPECT TABLE (all sizes measured; live = the 11:08:14.181 dump, design = I-ca539340.ui, art = tools\\dbpf\\extracted\\SimCity_1\\)\n\n| # | Element | Window id | design\u2192live | Art TGI {46a006b0,\u2026} | stock art | staged? | mismatch | player visibility |\n|---|---|---|---|---|---|---|---|---|\n| 1 | **Mayor Rating bar** | 0x4a553000 (clsid 0xaa5d16a9) | 102x11 \u2192 204x22 | 14416327 (code-loaded @0x007B5183) | 102x26 | **NO \u2014 absent from refmap AND package-list** | 102-wide run in a 204-wide window | REPORTED; dead centre |\n| 2 | Bubble frame/body | \u2013 (11.0.11) | 258x196 \u2192 **516x392** | 14416322 ir=(0,0,258,239) | 258x239 | NO (UNSCALED/untouched) | 1x source, 2x window | largest area on screen |\n| 3 | Bubble inner panel | \u2013 (11.0.11.0) | 235x142 \u2192 **470x284** | 14416322 ir=(12,10,258,239) | 258x239 | NO | same sheet, same crop | holds all bubble text |\n| 4 | Bubble bottom band | \u2013 (11.0.10) | 258x43 \u2192 **516x86** | 14416322 ir=(0,196,258,239) | 258x239 | NO | same | high |\n| 5 | **Play This City** btn | 0x4a560000 | 55x46 \u2192 **110x92** | 14416326 | 220x46 (4-state \u2192 55x46) | NO | cell 55x46 in a 110x92 btn | primary action |\n| 6 | Delete City btn | 0x4a560003 | 36x29 \u2192 **72x58** | 14416324 | 144x29 (4-state \u2192 36x29) | NO | same shape | high |\n| 7 | Import City btn | 0x4a560002 | 22x32 \u2192 **44x64** | 14416325 | 88x32 (4-state \u2192 22x32) | NO | same shape | high |\n| 8 | Rank icons (1/2/3) | 0x6c06f4a0 / 0xac06f4c4 / 0xcc06f4cf | 40x20 \u2192 **80x40** | cbfb3730/31/32 | 11x11 / 22x11 / 33x11 | NO | 11\u201333px crop in an 80x40 window | medium |\n| 9 | Close btn | 0x4a560001 | 13x13 \u2192 **26x26** | 14416323 | 52x13 (4-state \u2192 13x13) | NO | cell 13x13 in 26x26 | low (vis=0 in dump) |\n| 10 | Tooltip hit strips \u00d73 | \u2013 | 94x16/93x16/92x16 \u2192 **188x32/186x32/184x32** | 14015586 | 84x21 | clone 0x47425587 ships, but bubble is in the UNSCALED column \u2192 keeps 1x original | n/a | none (invisible hit targets) |\n\nRows 5\u20137 and 9 are the easy win: all four are exact 4-state strips (220/4=55, 144/4=36, 88/4=22, 52/4=13, heights match the design cell), which per `SC4-UI-ENGINE.md` \u00a74.3 is the \"safest case\" \u2014 state selection is imageWidth/4 with no imagerect, so doubling the art alone self-scales them with no code hook and no imagerect edit.\n\nNEW suspects only \u2014 cross-check done: the region screen proper is CLEAN. `I-aa920991.ui` uses 22 distinct arts; 21 are staged 2x-in-place and the 22nd (`144161E4`, SHARED, 94 refs/49 files) is covered by shipped clone `{46a006b0,470261E5}`. I nearly reported it as a suspect on a package-list grep; the clone check killed it. All 9 runtime-scaled region panels (0x0BB0F5E7, 0x09EBE9EE, 0x6A91DC15, 0x6A91DC16, 0x09EBEE45, 0x09EBEE60, 0xEA8CAD19, 0x6A91DC14, 0x6BB92BCA) are in SCALED_WINDOW_IDS.\n\nONE LOOSE END, stated honestly: I have not measured what the bubble looks like on screen. Rows 2\u20139 are derived from art-vs-window arithmetic, and the user has reported only the bar. Either the frame is also wrong and went unmentioned, or something covers it that I did not find \u2014 but it is NOT the BMPX stretch hook: BMPX is invoked with only `kBmpxCityRoots` (UiSpike.cpp:5874) and `kBmpxDialogRoots` (:8702), no region list, and `0x0A551C50` appears in UiSpike.cpp only inside a comment (:8943). One eyes-on look at the bubble settles rows 2\u20139 before any build.",
 "findings": [
  {
   "claim": "The defect's stated premise is wrong: the Mayor Rating bar is NOT painted into a GZWinBMP buffer \u2014 it is an addressable child window that the dump could never reach.",
   "evidence": "UiSpike.cpp:8910-8960 has exactly four print levels (loops i, j, q, z). The bubble prints as 'RGKID 11.0' = level 2, so only two levels below the bubble root are ever printed. The bar is three levels below it (root -> body BMP -> inner BMP -> bar) per T-00000000_G-96a006b0_I-ca539340.ui. POSITIVE CONTROL: the deepest printed line, 'RGKID 11.0.11.0 id=0x00000000 vt=00ADF6A0 (24,20 470x284) vis=1' (SC4UIScale.log 11:08:14.181), is the inner BMP whose script gives it NINE children \u2014 city name 0x4a552000, mayor name 0x4a552001, funds 0x4a552002/6, population 0x4a552003/4/5, the 'Mayor Rating:' label, and the bar 0x4a553000. All of those visibly render in the bubble; none appear in the log. The silence is the depth cap, not an empty subtree.",
   "status": "MEASURED"
  },
  {
   "claim": "The bar is window 0x4a553000, clsid 0xaa5d16a9 (IGZWinCustom), 102x11 at 1x \u2014 the only use of that class in the entire 331-script corpus.",
   "evidence": "tools\\uiscripts\\extracted\\T-00000000_G-96a006b0_I-ca539340.ui: 'clsid=0xaa5d16a9 iid=IGZWinCustom id=0x4a553000 area=(11,92,113,103)' = 102x11. grep -l 0xaa5d16a9 over all 331 .ui files returns that file alone. Its GetGZCLSID is at VA 0x00797BB0: b8 a9 16 5d aa c3 (mov eax,0xaa5d16a9; ret).",
   "status": "MEASURED"
  },
  {
   "claim": "The game binds the bar by id and feeds it a rating value from the bubble's populate routine at 0x007B4B80.",
   "evidence": "VA 0x007B5157: 68 00 30 55 4a (push 0x4A553000) then ff 92 94 00 00 00 (call [edx+0x94] = GetChildWindowFromID) on the bubble; at 0x007B5172-0x007B5178 it pushes a double (fld qword [esp+0x18] / fstp qword [esp]) into the returned window's vtbl slot +0x10. Enclosing function entry 0x007B4B80.",
   "status": "MEASURED"
  },
  {
   "claim": "The bar's art is {46a006b0,0x14416327}, the region bubble's own copy of the mayor-rating multi-state sheet \u2014 102x26, byte-for-byte the same dimensions as the city HUD's 14015549.",
   "evidence": "VA 0x007B5183: 53 (push 0) / 6a 09 (push 9) / 68 27 63 41 14 (push 0x14416327) / 68 b0 06 a0 46 (push 0x46A006B0) / 53 / lea ecx,[esp+0x9c] / e8 db d9 e4 ff (call 0x602B70) \u2014 the same loader helper 0x602B70 that both 0x14015549 sites use. tools\\dbpf\\extracted\\SimCity_1\\T-856ddbac_G-46a006b0_I-14416327.png = 102x26; T-856ddbac_G-46a006b0_I-14015549.png = 102x26.",
   "status": "MEASURED"
  },
  {
   "claim": "That art ships STOCK 1x while the city HUD's equivalent ships 2x \u2014 which is exactly why the HUD bar is correct and the region bar is not.",
   "evidence": "0x14416327 is absent from tools\\selective-safe\\refmap.csv entirely (no .UI file references it, so the script-derived classifier never saw it) and absent from package-list.txt and stage/. By contrast 14015549 is EXCLUSIVE/2x-in-place: stage\\T-0x856ddbac_G-0x46a006b0_I-0x14015549.png measures 204x52 (stock 102x26) and package-list.txt carries '0x856DDBAC 0x46A006B0 0x14015549 0x002B9BBB 1269'.",
   "status": "MEASURED"
  },
  {
   "claim": "The RatingArrowPatch=0 A/B was a structural null: that patch cannot reach the region bar because the two bars are separate code paths.",
   "evidence": "The city HUD groove window id 0x8A517556 appears as a constant at VA 0x007E86E5, inside the function entered at 0x007E8510 \u2014 the same function containing the three imul-by-7 sites the live log patches (0x007E87B1, 0x007E89D7, 0x007E8A02, log lines 8-10). The region bar's class body spans ~0x00797430-0x00797BB5 and contains none of those sites. Disjoint address ranges.",
   "status": "MEASURED"
  },
  {
   "claim": "THE FAMILY: all 10 arts referenced by the city-select bubble ship at 1x, inside windows the runtime doubles to 2x.",
   "evidence": "refmap.csv marks 14416322/23/24/25/26 and cbfb3730/31/32 as UNSCALED action=untouched (unscaled_files = I-ca539340.ui); 14416327 is absent entirely; 14015586 is SHARED with clone 0x47425587 staged but I-ca539340.ui sits in the UNSCALED column so the bubble keeps the 1x original. None of the ten appear in package-list.txt at their original TGI. Stock sizes: 14416322 258x239, 14416323 52x13, 14416324 144x29, 14416325 88x32, 14416326 220x46, 14416327 102x26, cbfb3730/31/32 11x11 / 22x11 / 33x11, 14015586 84x21.",
   "status": "MEASURED"
  },
  {
   "claim": "Meanwhile every bubble WINDOW is scaled to exactly 2x, so the whole subtree is 1x art in 2x frames.",
   "evidence": "Live log 11:08:14.181 vs I-ca539340.ui design: root 0x0A551C50 516x500 = 2x(258x250); body 516x392 = 2x(258x196); inner 470x284 = 2x(235x142); bottom 516x86 = 2x(258x43); buttons 0x4a560000-3 110x92/26x26/44x64/72x58 = 2x(55x46/13x13/22x32/36x29); tooltip strips 188x32/186x32/184x32 = 2x(94x16/93x16/92x16); rank icons 80x40 = 2x(40x20). All 12 direct children map exactly.",
   "status": "MEASURED"
  },
  {
   "claim": "Root cause is a single missing entry: the bubble root is not in the builder's scaled-subtree list, though every other region panel is.",
   "evidence": "build_selective_safe.py:113-114 lists the region roots 0x0BB0F5E7, 0x09EBE9EE, 0x6A91DC15, 0x6A91DC16, 0xEA8CAD19, 0x6A91DC14, 0x09EBEE45, 0x09EBEE60, 0x6BB92BCA \u2014 all 9 panels the runtime scales. 0x0A551C50 appears nowhere in build_selective_safe.py, and in UiSpike.cpp only inside a comment at :8943. Only the narrow stub 0x0A551C53 is listed (kNeverScaleIds, UiSpike.cpp:2379).",
   "status": "MEASURED"
  },
  {
   "claim": "The region screen proper is clean \u2014 no new suspects there. 22 of 22 arts are covered.",
   "evidence": "I-aa920991.ui references 22 distinct arts; 21 are in package-list.txt at their original TGI (1441630f, 14416300-04, 14416307, 1441630d, 13d14ca0, 14416106, 14416312-1b, 13e14fa0). The 22nd, 144161E4 (SHARED, 94 refs across 49 files), is action=clone+retarget with clone {46a006b0,470261E5}, and package-list.txt carries '0x856DDBAC 0x46A006B0 0x470261E5 0x00513D42 1900'. A raw package-list grep for 144161E4 shows 'not staged' and would have produced a false suspect.",
   "status": "MEASURED"
  },
  {
   "claim": "The existing BMPX 1x-stretch hook cannot rescue the bar even if the bubble were added to its scope.",
   "evidence": "HookRuntimeBmpsUnder is called only twice \u2014 with kBmpxCityRoots (UiSpike.cpp:5874) and kBmpxDialogRoots (:8702); neither list contains a region id and the live log shows BMPX lines only for city panels. Its class gate at UiSpike.cpp:5020 is 'if (vt != kBmpClassVt) return false;' where kBmpClassVt is the GZWinBMP vtable 0x00ADF6A0. The bar's class is 0xaa5d16a9, a different vtable, so it would be rejected.",
   "status": "MEASURED"
  },
  {
   "claim": "The 'two runs side by side' geometry is the painter filling its now-204px-wide window with a 102px-wide source run \u2014 the same signature as tasks #49 and #55.",
   "evidence": "Source run 102px (14416327 is 102 wide) into a destination 204px wide (0x4a553000 scaled from 102x11 to 2x) gives exactly two runs. I did NOT disassemble the paint method itself, so the repeat/tile step is inferred from the arithmetic and from the documented precedent, not read from code. Discriminating A/B: stage 14416327 at 2x (204x52) at its original TGI. If the painter keys off source width the bar becomes one correct full-width run; if it keys off a hardcoded 102 stride it becomes two 204-wide runs (4x overflow), which points at a code patch instead.",
   "status": "HYPOTHESIS"
  },
  {
   "claim": "Rows 5-7 and 9 of the table (the four bubble buttons) can be fixed by art alone, with no code hook and no imagerect edit.",
   "evidence": "All four arts are exact 4-state strips whose cell equals the design area: 14416326 220x46 -> 220/4=55 = area 55x46; 14416324 144x29 -> 36 = area 36x29; 14416325 88x32 -> 22 = area 22x32; 14416323 52x13 -> 13 = area 13x13. None carries an imagerect. SC4-UI-ENGINE.md sec 4.3 records that state selection is imageWidth/4 with no imagerect and calls this 'the SAFEST case', so a doubled strip yields doubled cells automatically.",
   "status": "MEASURED"
  },
  {
   "claim": "Rows 2-9 are arithmetic predictions, not observations \u2014 I never looked at the bubble on screen.",
   "evidence": "The user has reported only the bar. My claim that the frame, buttons and rank icons are also wrong rests on art-size-vs-window-size arithmetic plus the confirmed absence of any covering hook (BMPX scope and class gate above). No screenshot, PrintWindow capture or pixel measurement of the bubble was taken in this pass. One eyes-on look settles rows 2-9 before any build is spent on them.",
   "status": "HYPOTHESIS"
  }
 ],
 "verdictOnHypothesis": "SUPPORTS"
}