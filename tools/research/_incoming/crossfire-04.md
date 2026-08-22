{
 "summary": "ANGLE 4 VERDICT: (a) the doubling is INTRODUCED BY OUR 2x SCALING. It cannot occur at stock, and I settled it without a stock screenshot \u2014 because I found the actual widget and its actual draw law.\n\nTwo premises in the brief turned out to be wrong, and correcting them cracked the defect:\n\n1. \"NO child is the rating bar => it is painted INTO a GZWinBMP buffer\" is a BLIND-INSTRUMENT NULL. The RGKID dumper (src/UiSpike.cpp:8956) hard-stops at 4 levels; the rating bar is a level-5 node. It IS a real child window: `clsid=0xaa5d16a9` = **cSC4WinAuraBar**, `id=0x4a553000`, `area=(11,92,113,103)` = **102x11**, declared at line 10 of T-00000000_G-96a006b0_I-ca539340.ui \u2014 sitting directly under the \"Mayor Rating:\" label (line 16).\n\n2. It has nothing to do with the HUD's 14015549 art. Its bitmap is CODE-BOUND: `{46A006B0, 0x14416327}`, pushed at exactly one site in the exe (VA 0x7B517F), measured **102x26** \u2014 the same 12-red / centre / 12-green 3px-segment sheet as the HUD groove. It is referenced by NO .UI script, so it never entered refmap.csv, so it is **NOT in our 2x SelectiveArt package** \u2014 it stays 102 px wide while our sweep doubles its window to 204.\n\nThe AuraBar's own Draw (VA 0x797CC0) computes its source rect as `src.L = (imgW - winW)/2`, `src.R = src.L + winW`, `src.T = round(fraction*(imgH-1))`, `src.B = src.T+1`, and blits that 1-pixel-tall slice into the FULL window rect. At stock winW == imgW == 102 \u2192 src = (0..102) \u2192 exactly ONE run of segments. At 2x with a 1x art, src = (-51..153) \u2192 a 204-px span across a 102-px image = exactly TWO periods, offset by half a period. That is the reported symptom, arithmetically.\n\nNo stock capture of the region bubble exists anywhere in the repo (I enumerated all 71 images and eyes-on read the 6 region candidates) \u2014 but none is needed. If the user still wants one screenshot for the record, it is a very specific one, given below.",
 "findings": [
  {
   "claim": "The region bubble's Mayor Rating bar is a REAL child window, not something painted into a GZWinBMP buffer \u2014 it is cSC4WinAuraBar id=0x4a553000, 102x11 at (11,92).",
   "evidence": "<PROJECT-ROOT> 1 Project\\1 Completed Projects\\SC4TouchControls\\tools\\uiscripts\\extracted\\T-00000000_G-96a006b0_I-ca539340.ui line 10: `<LEGACY clsid=0xaa5d16a9 iid=IGZWinCustom id=0x4a553000 area=(11,92,113,103) ...>` \u2192 113-11=102 wide, 103-92=11 tall. Line 16 of the same file is the `caption=\"Mayor Rating:\"` GZWinText at area=(6,68,233,86), i.e. the label directly above it. clsid 0xaa5d16a9 = cSC4WinAuraBar per tools/research/DYNAMIC-CONTROLS.md:41 AND vendor/gzcom-dll/gzcom-dll/include/GZCLSIDDefs.h:283 (kcSC4WinAuraBar = 0x0AA5D16A9). This clsid occurs in exactly ONE .UI script in the whole extracted set (grep -l aa5d16a9 *.ui \u2192 1 file), so there is no id ambiguity or dat load-order collision risk.",
   "status": "MEASURED"
  },
  {
   "claim": "The brief's premise 'the dump descends 3 levels, NO child is the rating bar' is a STRUCTURAL NULL from a blind instrument \u2014 the dumper physically cannot reach the AuraBar.",
   "evidence": "src/UiSpike.cpp:8956 is the innermost print (`\"UiSpike: RGKID %2d.%d.%d.%-2d ...\"`) and it does NOT recurse further \u2014 4 levels is the hard cap. POSITIVE CONTROL: across all 4721 lines of the live log, label-depth histogram is {0 dots:53, 1:91, 2:30, 3:1} and there are ZERO 4-dot (5-level) labels; the single 3-dot line IS `RGKID 11.0.11.0 id=0x00000000 vt=00ADF6A0 (24,20 470x284)`. So the printer demonstrably works at depth 4 and simply has no depth-5 branch. The AuraBar is depth 5: region 0xEA659793 \u2192 0x2BA6BB97 \u2192 bubble 0x0A551C50 \u2192 BMP(0,0,258,196)=(0,0 516x392) \u2192 BMP(12,10,247,152)=(24,20 470x284) \u2192 0x4a553000. Its child position is confirmed by the .UI nesting in I-ca539340.ui. Corroboration: `grep -c 4A553000 SC4UIScale.log` = 0.",
   "status": "MEASURED"
  },
  {
   "claim": "The AuraBar draw law (VA 0x797CC0): src.L = (imgW - winW)/2, src.R = src.L + winW, src.T = round(fraction*(imgH-1)), src.B = src.T+1; that 1-px-tall slice is blitted into the FULL window rect. The source WIDTH is taken from the WINDOW, its POSITION from the ART \u2014 that mismatch is the whole bug.",
   "evidence": "Disassembly of SimCity 4.exe (7,876,608 bytes, ImageBase 0x400000), file offset = VA-0x400000. Chain: registration at 0x4662E9 `push 0x797f20` / `call 0x797bb0` (=`mov eax,0xaa5d16a9; ret`) / `call 0x90e133`; factory 0x797F20 `push 0xf8; call 0x5e55e0; call 0x797e60` (ctor); ctor 0x797E60 writes vptr 0xAB64B8 to [this+0], 0xAB64A0 to [this+0xD8], 0xAB6488 to [this+0xE0]; vtable 0xAB6488 slot3=0x797E10 SetImage (stores to this+0xF0), slot4=0x797C20 SetFraction (stores double to this+0xE8). Draw 0x797CC0 key bytes: `8b 7808` mov edi,[eax+8] (img.R); `8b 4b08` mov ecx,[ebx+8] (win.R); `2b f9` sub edi,ecx; `8b 0b` mov ecx,[ebx]; `2b fa` sub edi,edx (img.L); `03 f9` add edi,ecx (win.L); `d1 ff` sar edi,1 \u2192 edi = (imgW-winW)>>1 stored as src.L; then `8b 13`/`8b 4b08`/`2b ca`/`03 cf` \u2192 src.R = winW + (imgW-winW)/2; row via `db 44240c` fild (imgH-1) / `dc 8ee8000000` fmul [this+0xE8] / `dc 05 282da900` fadd / `e8 b8712500` call 0x9eef04 (ftol); `push ebx` pushes the WINDOW rect [this+0x24] as the destination; `e8 420e1400` call 0x8d8bc0 does the blit.",
   "status": "MEASURED"
  },
  {
   "claim": "The bar's bitmap is code-bound {46A006B0, 0x14416327}, measured 102x26, referenced by NO .UI script, absent from refmap.csv, and therefore ABSENT from every one of our 2x/1.5x/3x SelectiveArt packages \u2014 it is still 102 px wide at runtime.",
   "evidence": "Controller at VA 0x7B514C-0x7B51A7: `push 0x4a5d1208` (AuraBar iid) / `push 0x4a553000` (win id) / `call [edx+0x94]` (get child as), then `call [edx+0x10]` = vtable-0xAB6488 slot4 = SetFraction, then `push 0; push 9; push 0x14416327; push 0x46a006b0; push 0; call 0x602b70` and `call [edx+0xc]` = slot3 = SetImage. Byte-scan of the whole exe: instance 0x14416327 occurs at exactly 1 site (VA 0x7B517F); iid 0x4A5D1208 at exactly 1 site (VA 0x7B514D). PNG IHDR of tools/dbpf/extracted/SimCity_1/T-856ddbac_G-46a006b0_I-14416327.png = 102x26 (twin T-856ddbac_G-1abe787d_I-14416327.png also 102x26; tools/uimap/_subflyout-art/art-dims.csv rows for both). `grep -i 14416327 tools/selective-safe/package-list.txt` \u2192 no match; `grep -i 14416327 tools/selective-safe/refmap.csv` \u2192 no match; `grep -rl 14416327 tools/uiscripts/extracted/` \u2192 no match.",
   "status": "MEASURED"
  },
  {
   "claim": "AT STOCK (f=1) the doubling is ARITHMETICALLY IMPOSSIBLE: winW = imgW = 102, so src.L = (102-102)/2 = 0 and src.R = 102 \u2014 the source rect covers the art exactly once, producing exactly ONE run of segments.",
   "evidence": "Window width 102 measured from I-ca539340.ui:10 area=(11,92,113,103). Art width 102 measured from the PNG IHDR of T-856ddbac_G-46a006b0_I-14416327.png. Substituted into the measured formula at 0x797D16-0x797D28. Intended stock appearance, measured by pixel-dumping the art: 26 slots of pitch 4 px (3 px lit + 1 px magenta FF00FF key), 12 red slots left of a 6-px grey centre marker, 12 green slots right; row index selects the state (row 0 = 12 red, rows 12-13 = empty, row 25 = 12 green). 12*4 + 6 + 12*4 = 102. That segmented run IS the user's 'green-fill-plus-groove pattern'.",
   "status": "MEASURED"
  },
  {
   "claim": "AT f=2 the same formula yields src = x -51..153 over a 102-px-wide image \u2014 a 204-px span across a 102-px period = exactly TWO copies, offset by half a period. This reproduces 'two runs side by side' to the pixel.",
   "evidence": "src.L = (imgW-winW)/2 = (102-204)>>1 = -51 (sar of -102 by 1); src.R = -51+204 = 153; span = 204 px = 2 x 102. The half-period offset is a falsifiable prediction: the left-hand run should START mid-pattern (51 px into the art), i.e. the seam between the two runs falls at the centre marker's position, not at a segment boundary the user would read as symmetric.",
   "status": "MEASURED"
  },
  {
   "claim": "That the blitter WRAPS (rather than clamps or no-ops) the out-of-range source coordinates is inferred from the symptom, not disassembled.",
   "evidence": "0x8d8bc0 (the blit helper called at VA 0x797D79) was not disassembled. A clamping blitter would edge-smear instead of repeating. The user's 2026-07-30 report of two full runs is what selects 'wrap'. Note the bubble root carries blttype=tiled (I-ca539340.ui line 2), which is consistent but is a property of the root's own fill, not proof about this blit.",
   "status": "HYPOTHESIS"
  },
  {
   "claim": "That the AuraBar window is actually 204 px wide at runtime has never been directly logged \u2014 it is the one link still inferred. It is implied (imgW is fixed at 102, so two runs require winW=204), and the bubble is not exempted from scaling.",
   "evidence": "src/UiSpike.cpp:2379 lists 0x0A551C53 (the NARROW empty-tile stub) in kNeverScaleIds; 0x0A551C50 (the existing-city bubble) is NOT in it, and the live log line 157 shows the bubble itself scaled: `RGKID 11.0 id=0x0A551C50 vt=00AB7358 (1049,456 516x500)` = 258x250 x2. To measure the AuraBar directly, raise the RGKID recursion one level (UiSpike.cpp:8956) or log any descendant whose vtable is 0x00AB64B8 \u2014 that is the AuraBar's cIGZWin vptr, since its QI at 0x797BC0 returns this+0 for iid 0x22BA0121 (GZIID_cIGZWin, vendor/gzcom-dll/gzcom-dll/include/cIGZWin.h:38) and the ctor at 0x797E7C-0x797E92 writes 0xAB64B8 to [this+0].",
   "status": "HYPOTHESIS"
  },
  {
   "claim": "NO stock/1x capture of the region city bubble exists anywhere in the repo. This is a real 'not captured', not a blind instrument.",
   "evidence": "Enumerated every image: 54 in tools/capture/out, 4 in _tests/golden, 1 in _vanilla-reference/captures, 12 in _tests/captures/stock-budget. Eyes-on read of the 6 region candidates \u2014 _tests/golden/stock-1600-NODLL.png (1600x1200), tools/capture/out/pure-stock-1600.png, tools/capture/out/stock-region-1600x1200.png, tools/capture/out/verify-w-1024-stock.png (1032x810), _vanilla-reference/captures/01-region-screen.png (1288x1066, actually CITY/god mode not region), _tests/golden/region-v252.png (2400x1600, 2x) \u2014 none contains the bubble. The two stock shots that DO have a tile selected (stock-1600-NODLL.png, stock-region-1600x1200.png) select an EMPTY tile (yellow outline), which raises the narrow stub 0x0A551C53, not the existing-city bubble. POSITIVE CONTROL: the same harness DID capture other transient region UI at stock \u2014 verify-w-1024-stock.png shows the Audio Options dialog and the top-right options flyout fully rendered, stock-region-1600x1200.png shows the region-view checkbox flyout \u2014 so a bubble would have been captured had one been open.",
   "status": "MEASURED"
  },
  {
   "claim": "tools/capture/out/verify-windowed-citybubble.png and its -crop are MISNAMED: neither contains a city bubble. Do not cite them as bubble evidence.",
   "evidence": "Read both (1608x1242 and 950x650). Both show the London region terrain with the Kensington/Bob and Fulham/Robert city labels, the top button row and the bottom Region/7,633/London panels \u2014 and no bubble anywhere in frame. The 2026-07-22 22:33 capture evidently fired before or after the bubble was up.",
   "status": "MEASURED"
  },
  {
   "claim": "The archived 1x boot dump SC4UIScale.log.bak-stock800 cannot settle this either \u2014 structurally.",
   "evidence": "Full file read (6497 bytes, 2026-07-21 12:32, v2.6.0-split, ScaleAll=0 scaling=0, 800x600). It is a one-shot BOOT tree dump of 71 windows taken with no city hovered; 0x0A551C50 does not appear because the bubble had not been created. The dump also stops at the region screen's children, so it never had reach.",
   "status": "MEASURED"
  },
  {
   "claim": "This also explains cleanly why the CITY HUD bar is correct and why RatingArrowPatch=0 changed nothing \u2014 they are a different widget on a different mechanism.",
   "evidence": "The HUD bar is a plain GZWinBMP 0x8a517556, `image={46a006b0,14015549} imagerect=(0,0,102,11)` (T-00000000_G-96a006b0_I-2bc90671.ui), and 14015549 IS in our package: reading the shipped tools/selective-safe/z_SC4UIScale_SelectiveArt.dat (11,703,241 bytes, identical size to the deployed z_SC4UIScale_SelectiveArt-2x.dat) at the package-list.txt:160 offset 0x002B9BBB gives a PNG IHDR of 204x52 (its siblings likewise: 14015547 296x42, 14015548 384x76, 1401554A 210x26, 1401554B 84x18). Byte-scan: instance 0x14015549 appears at only 2 VAs, 0x7E851D and 0x7ED224 \u2014 both in the CITY HUD controller region \u2014 so it never reaches the region bubble. The imul-by-7 arrow patch lives in that same HUD controller (0x7E86C0-0x7E8A80) and touches nothing in the AuraBar path, which is exactly what the user's A/B showed.",
   "status": "MEASURED"
  },
  {
   "claim": "SYSTEMIC BLIND SPOT worth recording: refmap.csv is built only from .UI-script art references, so every CODE-BOUND art TGI is invisible to it. 14416327 is a concrete instance that slipped through all three tier packages.",
   "evidence": "`grep -i 14416327 tools/selective-safe/refmap.csv` \u2192 no match, while the TGI demonstrably exists in the game archives (tools/dbpf/extracted-png-tgi.csv rows for both 0x46A006B0 and 0x1ABE787D at 265 bytes each) and is loaded at VA 0x7B517F. Same class of gap already noted for the TrendBar images in tools/research/DYNAMIC-CONTROLS.md.",
   "status": "MEASURED"
  },
  {
   "claim": "If a stock screenshot is still wanted for the record, exactly ONE shot settles it \u2014 and it must be a very specific one.",
   "evidence": "Required: region view of a region that HAS a founded city (London: Kensington or Fulham), with the scaler DLL and all z_SC4UIScale_*.dat plus both FontStyle.ini copies parked (the Set-StockCompare/stock-budget procedure in _tests/captures/stock-budget/STOCK-REFERENCE.md), hovering or left-clicking that EXISTING city tile so the wide bubble (0x0A551C50, 258x250 at 1x) opens, cropped to the bubble. It must be an existing city, NOT an empty tile \u2014 an empty tile raises the narrow 42x159 stub 0x0A551C53, which has no AuraBar at all, which is precisely why all five existing stock region captures are useless here. Expected stock result, predicted from the measurements above: a single 102x11 run of 3-px segments under the 'Mayor Rating:' label.",
   "status": "MEASURED"
  },
  {
   "claim": "Derived fix direction (for the parent to weigh, not measured in-game): add {0x856DDBAC, 0x46A006B0, 0x14416327} \u2014 and its 0x1ABE787D twin \u2014 to the SelectiveArt package at tier size (204x52 for 2x), which makes imgW == winW again and restores src.L = 0.",
   "evidence": "Follows directly from src.L = (imgW-winW)/2 at VA 0x797D26 plus the measured 102x26 art. It is the same 2x-in-place action already applied to the HUD's 14015549 (package-list.txt:160 \u2192 204x52 in the dat), and it needs no code patch. Blast radius is minimal: the TGI is bound at exactly one code site and referenced by zero .UI scripts, so nothing else can consume it. Caveat: the AuraBar's row selection uses round(fraction*(imgH-1)), so a 2x art must preserve the 26-state row structure proportionally (52 rows = each state doubled) or the selected state will drift.",
   "status": "HYPOTHESIS"
  }
 ],
 "verdictOnHypothesis": "SUPPORTS"
}