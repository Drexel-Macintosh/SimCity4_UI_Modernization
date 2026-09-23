r"""verify_tooltip.py - W-ToolTip unit: re-derive every claim from the exe bytes.

Offline, read-only. Run:  python tools\sdk\ghidra\verify\W-ToolTip\verify_tooltip.py
Exit code 0 = every check PASS.

Two tooltip systems exist in SimCity 4 Deluxe 1.1.641.0 (Steam):
  (1) GZ framework: cGZWinToolTipMgr (clsid 0x22C010CE, mgr iid 0x22C010CD) +
      cGZWinToolTip window (id 0x82F0121D) implementing cIGZWinToolTip
      (iid 0x22C010CF, 6 slots, iface at +0xD8). DORMANT in shipping SC4.
  (2) SC4: cSC4WinToolTipMgr (vt 0xABCB60, created in cSC4App init) driving
      cSC4WinCalloutBox (window id 0x2AAB8CC1; iface vt 0xAB69D0, iid 0xC9B432CF,
      21 slots at +0; cGZWin at +4 with class vt 0xAB6770). This is what paints.
"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pe import *

FAILS = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (("  -- " + detail) if detail else ""))
    if not cond:
        FAILS.append(name)

def insn(va):
    a, m, o, b = dis(va, 1)[0]
    return m + " " + o, b

# ---- positive control: the scanner finds the known FlatRect IID sites --------
fr = xrefs_imm32(0xC2AFA76F)
check("positive control: FlatRect IID 0xC2AFA76F at 0x47B994 and 0x4861D8",
      0x47B994 in fr and 0x4861D8 in fr, "%d hits" % len(fr))

PURE = 0x5D4A10   # push 0; push 0; call 0x9EF84F  (pure-virtual stub)

# ---- (1) cIGZWinToolTip -------------------------------------------------------
abstract = [u32(0xAE4368 + 4 * i) for i in range(7)]
check("cIGZWinToolTip abstract vt 0xAE4368 = exactly 6 pure slots",
      abstract[:6] == [PURE] * 6 and abstract[6] != PURE)
iface = [u32(0xAE4380 + 4 * i) for i in range(6)]
check("cIGZWinToolTip iface vt 0xAE4380 slots",
      iface == [0x9D9A38, 0x95BA81, 0x95BA8C, 0x95BA6F, 0x9D97B0, 0x9DA05E],
      " ".join(hex(x) for x in iface))
check("ctor 0x9D9C6C: [this+0xD8]=0xAE4368 then 0xAE4380; [this]=0xAE4398 (class vt starts right after the 6)",
      rd(0x9D9C7C, 6) == bytes.fromhex("c7006843ae00") and rd(0x9D9C82, 6) == bytes.fromhex("c7008043ae00")
      and rd(0x9D9C8E, 6) == bytes.fromhex("c7069843ae00") and 0xAE4380 + 6 * 4 == 0xAE4398)
check("slot0 thunk: sub ecx,0xD8; jmp 0x9D9624", rd(0x9D9A38, 11) == bytes.fromhex("81e9d8000000e9e1fbffff"))
check("slot1 AddRef thunk: sub ecx,0xD8; jmp 0x8FB729", rd(0x95BA81, 6) == bytes.fromhex("81e9d8000000"))
check("slot2 Release thunk: sub ecx,0xD8; jmp 0x8FB72E", rd(0x95BA8C, 6) == bytes.fromhex("81e9d8000000"))
check("slot3 AsIGZWin: lea eax,[ecx-0xD8]; ret", rd(0x95BA6F, 7) == bytes.fromhex("8d8128ffffffc3"))
check("class QI 0x9D9624 compares riid 0x22C010CF", rd(0x9D9627, 7) == bytes.fromhex("817d08cf10c022"))
check("class QI returns this+0xD8 for it", rd(0x9D9634, 6) == bytes.fromhex("8d91d8000000"))
check("SetFont 0x9D97B0 ends ret 0xC (3 args)", rd(0x9D980B, 3) == bytes.fromhex("c20c00"))
check("SetFont stores font @iface+4, bytes @+8/+9",
      rd(0x9D97D7, 3) == bytes.fromhex("897e04") and rd(0x9D97EF, 6) == bytes.fromhex("884e08885609"))
check("CopyTipInfo 0x9DA05E ends ret 4 (1 arg)", rd(0x9DA103, 3) == bytes.fromhex("c20400"))
check("GZ mgr gets tip window: GetChildAs(0x82F0121D, 0x22C010CF) via main-win vt+0x90",
      rd(0x9D9955, 10) == bytes.fromhex("68cf10c022681d12f082") and rd(0x9D9961, 6) == bytes.fromhex("ff9290000000"))
check("GZ mgr ShowTip calls tip->vt+0x14 (CopyTipInfo)", rd(0x9D9AF8, 3) == bytes.fromhex("ff5014"))
check("GZ mgr Init calls tip->vt+0x10 (SetFont) with its 3 args", rd(0x9D9E2C, 3) == bytes.fromhex("ff5010"))
check("GZ mgr class registered: clsid 0x22C010CE -> factory 0x9D9F40",
      rd(0x998BD4, 10) == bytes.fromhex("68409f9d0068ce10c022"))
check("clsid 0x22C010CE has no other literal in .text (no CreateInstance by literal)",
      xrefs_imm32(0x22C010CE) == [0x998BDA])
check("GZWinBtn ShowTip builds tipinfo and sends msg 0x22C010D0",
      rd(0x9B1BA6, 7) == bytes.fromhex("c745e8d010c022"))
check("tipinfo ctor 0x9B035D: +0 = 1, +0x20 = 0xFFFFE0",
      rd(0x9B0361, 6) == bytes.fromhex("c70001000000") and rd(0x9B037C, 7) == bytes.fromhex("c74020e0ffff00"))

# ---- (2) cSC4WinCalloutBox ---------------------------------------------------
ab = [u32(0xAB6718 + 4 * i) for i in range(22)]
check("CalloutBox abstract iface vt 0xAB6718 = exactly 21 pure slots", ab[:21] == [PURE] * 21 and ab[21] != PURE)
cv = vtable(0xAB69D0, 40)
check("CalloutBox iface vt 0xAB69D0 = 21 slots, terminated by 0", len(cv) == 21 and u32(0xAB69D0 + 84) == 0)
check("CalloutBox QI compares riid 0xC9B432CF", rd(0x797F54, 5) == bytes.fromhex("3dcf32b4c9"))
check("CalloutBox ctor: [this]=0xAB69D0, [this+4]=0xAB6770",
      rd(0x799DE5, 12) == bytes.fromhex("c706d069ab00c7077067ab00"))
check("CalloutBox Init sets window id 0x2AAB8CC1", rd(0x7980E5, 5) == bytes.fromhex("68c18cab2a"))
check("CalloutBox GZPaint (class vt slot 88) = 0x798710", u32(0xAB6770 + 88 * 4) == 0x798710)
check("SC4 tip mgr vt 0xABCB60 slots QI/AddRef/Release/DoMessage/Init/Shutdown",
      [u32(0xABCB60 + 4 * i) for i in range(6)] == [0x7E6030, 0x5F47F0, 0x7E97F0, 0x7EFBD0, 0x7E7C80, 0x7E7EA0])
check("SC4 tip mgr QI accepts 0x22C010CD (same mgr iid as GZ mgr)", rd(0x7E6037, 5) == bytes.fromhex("2dcc10c022"))
check("SC4 tip mgr Init creates CalloutBox (new 0x1B4; ctor 0x799DD0)",
      rd(0x7E7D09, 5) == bytes.fromhex("68b4010000") and rd(0x7E7D1C, 5) == bytes.fromhex("e8af20fbff"))
check("SC4 tip mgr fonts: slot11 <- ToolTip 0xA85F1A83, slot10 <- ToolTipTitle 0xE9C86C9D",
      rd(0x7E7D4C, 8) == bytes.fromhex("68831a5fa8ff522c") and rd(0x7E7D59, 8) == bytes.fromhex("689d6cc8e9ff5028"))
check("SC4 tip mgr frame art: expanded I=0x14416190, simple I=0x14416192",
      rd(0x7E7D91, 4) == struct.pack("<I", 0x14416190) and rd(0x7E7E0B, 4) == struct.pack("<I", 0x14416192))
check("SC4 tip mgr show handler reads ONLY tipinfo+8 (text)",
      rd(0x7EFC42, 6) == bytes.fromhex("8b41048b4008"))
check("SC4 tip mgr splits title|body on '|' (0xA81388)", rd(0xA81388, 2) == b"|\0")

# ---- pixel-sized levers: exact bytes at each site ------------------------------
LEVERS = [
    # va,        expected bytes,   meaning
    (0x79880A, "68fa000000",       "CalloutBox Plot: title wrap width 250 (push imm32; ALREADY PATCHED by kTipWrapSites)"),
    (0x7988A9, "68fa000000",       "CalloutBox Plot: body wrap width 250 (push imm32; ALREADY PATCHED)"),
    (0x79871C, "bf10000000",       "CalloutBox Plot: frame cell 16 when no background art (fallback only)"),
    (0x798781, "83c004",           "CalloutBox Plot: icon->text gap +4"),
    (0x79885A, "83c104",           "CalloutBox Plot: title width slack +4"),
    (0x79887B, "8d540803",         "CalloutBox Plot: title band = titleH + padY + 3 (disp8 @0x79887E)"),
    (0x79890B, "83c004",           "CalloutBox Plot: title/body gap +4"),
    (0x798994, "83c104",           "CalloutBox Plot: meter band gap +4"),
    (0x798A02, "83c002",           "CalloutBox Plot: +2 content height"),
    (0x798CB2, "83c004",           "CalloutBox Plot: body y offset under title +4"),
    (0x798CE1, "83c004",           "CalloutBox Plot: body y offset under meter +4"),
    (0x79834C, "b808000000",       "SetBackgroundImage default padX 8 (arg<0)"),
    (0x79835F, "b803000000",       "SetBackgroundImage default padY 3 (arg<0)"),
    (0x799E94, "b8e4ffffff",       "ctor default avoidance rect l,t = -28"),
    (0x799EA5, "b81c000000",       "ctor default avoidance rect r,b = +28"),
    (0x7981EA, "83c010",           "Init: constraint rect = main window inset 16 (l)"),
    (0x7981EF, "83c210",           "Init: inset 16 (t)"),
    (0x7981F3, "83e910",           "Init: inset 16 (r)"),
    (0x7981F9, "83ee10",           "Init: inset 16 (b)"),
    (0x7EFCCB, "6a08",             "SC4 mgr expanded tip padY 8"),
    (0x7EFCCD, "6a08",             "SC4 mgr expanded tip padX 8"),
    (0x7EFCD6, "b8e4ffffff",       "SC4 mgr expanded avoidance l,t = -28"),
    (0x7EFCE3, "b81c000000",       "SC4 mgr expanded avoidance r,b = +28"),
    (0x7EFD40, "6a03",             "SC4 mgr simple tip padY 3"),
    (0x7EFD42, "6a05",             "SC4 mgr simple tip padX 5"),
    (0x7EFD4B, "b8fcffffff",       "SC4 mgr simple avoidance l,t = -4"),
    (0x7EFD58, "b814000000",       "SC4 mgr simple avoidance r,b = +20"),
    (0x438000, "6a0a",             "query callout (0x437D10) padY 10"),
    (0x438002, "6a0c",             "query callout (0x437D10) padX 12"),
    (0x43A395, "6a0a",             "query callout (0x43A0B0) padY 10"),
    (0x43A397, "6a0c",             "query callout (0x43A0B0) padX 12"),
    (0x4391FE, "6a0a",             "query callout (0x438EA0) padY 10"),
    (0x439200, "6a0c",             "query callout (0x438EA0) padX 12"),
    (0x438039, "c784249000000018fcffff", "query callout avoidance t = -1000"),
    (0x43804B, "c78424980000001c000000", "query callout avoidance b = +28"),
    (0x4C58BF, "b8d8ffffff",       "traffic-route query callout avoidance l,t = -40"),
    (0x4C58CC, "b828000000",       "traffic-route query callout avoidance r,b = +40"),
    # dormant GZ-framework tooltip (never instantiated in shipping SC4)
    (0x9D9D3D, "6a40",             "[dormant] cGZWinToolTip buffer height 64"),
    (0x9D9D3F, "6800010000",       "[dormant] cGZWinToolTip buffer width 256"),
    (0x9DA07F, "6800010000",       "[dormant] cGZWinToolTip text ellipsis width 256"),
    (0x9DA4B3, "83ff02",           "[dormant] cGZWinToolTip screen margin 2"),
    (0x44CB3C, "6a01",             "[ignored] tip-mgr Init padY 1 (SC4 mgr never reads it)"),
    (0x44CB3E, "6a03",             "[ignored] tip-mgr Init padX 3 (SC4 mgr never reads it)"),
]
for va, hx, what in LEVERS:
    got = rd(va, len(hx) // 2).hex()
    check("lever %08X %s" % (va, what), got == hx, got if got != hx else "")

print("\n%d FAIL" % len(FAILS) if FAILS else "\nALL PASS")
sys.exit(1 if FAILS else 0)
