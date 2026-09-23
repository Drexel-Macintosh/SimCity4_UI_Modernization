"""Step 7: emit the deliverable table (slot_table.tsv) = per-class VAs (from s2) + this unit's
exe-derived decode + verdict vs the Mac name. Semantics below were derived from the disassembly
read in s3/s5 and the window-manager routers (see the unit's final report for the evidence)."""
import sys, json
sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from pe import *
from s1_vtables import CLASSES

here = __file__.rsplit("\\", 1)[0]
rows = json.load(open(here + "\\slot_table.json"))
MAC = {}
d = json.load(open(r"C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json"))
for t in d["types"]:
    if t["name"] == "vftable_cIGZWin":
        for f in t["fields"]:
            MAC[f["off"] // 4] = f["name"]

SEM = {
 50: ("&[this+0x14] (absolute rect ptr)", "agree GetAreaAbsolute()", "H"),
 51: ("SetArea(l,t,l+w,b)", "agree SetW", "H"),
 52: ("SetArea(l,t,r,t+h)", "agree SetH", "H"),
 53: ("SetSize(w,h): SetArea(l,t,l+w,t+h)", "agree", "H"),
 54: ("SetArea(const rect&) -> slot 55", "agree", "H"),
 55: ("SetArea(l,t,r,b): store [A8..B4]; realloc private buf (100) if size changed; CalcAbsoluteArea(90); SetAreaToDrawToRecursive(98)", "agree", "H"),
 56: ("MoveTo(x,y) absolute: SetArea(x,y,x+W,y+H)", "agree GZWinMoveTo", "H"),
 57: ("Offset(dx,dy): all 4 edges += d", "agree GZWinOffset", "H"),
 58: ("FitRectToWindow(rect*,margin): clamp rect into (0,0,W,H) inset margin; ret fits", "agree", "H"),
 59: ("ScreenToWindow(int&x,int&y): subtract origin from slot 60", "agree", "H"),
 60: ("WindowToScreen(int&x,int&y): add [0x14],[0x18]", "agree", "H"),
 63: ("GetID [0x10]", "agree", "H"), 64: ("SetID [0x10]", "agree", "H"),
 65: ("GetInstanceID [0xCC]", "agree", "H"), 66: ("SetInstanceID [0xCC]", "agree", "H"),
 67: ("GetFlag: [0xC8]&mask", "agree", "H"), 68: ("SetFlag(mask,on)", "agree", "H"),
 69: ("Show: SetFlag(1,1) if hidden", "agree", "H"), 70: ("Hide: SetFlag(1,0) if visible", "agree", "H"),
 86: ("store [0x4C]", "agree", "H"), 87: ("load [0x4C]", "agree", "H"),
 88: ("per-class paint (base no-op)", "agree GZPaint", "H"),
 89: ("123 && 124, then winmgr+0x20 unless [0x71]", "agree Plot", "H"),
 115: ("iterate param map [0x7C]: fn(this,key,val,ctx)", "agree EnumParams", "H"),
 116: ("insert filter into [0x88] list (DoMessage consults it first)", "agree AddMessageFilter", "H"),
 117: ("remove filter from [0x88] (deferred to [0x8C] mid-dispatch)", "agree RemoveMessageFilter", "H"),
 118: ("SetSize(const pt&): -> slot 53(pt.x,pt.y)", "AGREE", "H"),
 119: ("center in rect, arg deref'd unconditionally (ref)", "AGREE", "H"),
 120: ("center in rect, arg null-tested (ptr)", "AGREE", "H"),
 121: ("0<=x<W && 0<=y<H (+per-pixel 149 if flag 0x80000)", "AGREE", "H"),
 122: ("rect [A8..B4] (parent-relative) contains (x,y)", "AGREE", "H"),
 123: ("composite body: flags, filters msg 0x16, private buffer, draw ctx; called first by Plot", "AGREE", "M"),
 124: ("present private buffer via graphics system; called second by Plot", "AGREE", "H"),
 125: ("store uint32 -> [0xD4] (packed-RGB field)", "AGREE", "H"),
 126: ("return [0xD4]", "AGREE", "H"),
 127: ("split r=p>>16,g=p>>8,b=p -> buffer MakeColor(r,g,b)", "AGREE", "H"),
 128: ("buffer SplitColor(native,&r,&g,&b) -> 0xFF<<24|r<<16|g<<8|b", "AGREE", "H"),
 129: ("msg type 4, byte arg; LineInput inserts chars >=0x20 (deletes selection via own slot 130(VK_BACK=8,0) first); no Win32 map for type 4 found", "AGREE", "H"),
 130: ("msg type 5 = WM_KEYDOWN (exe table 0x9DA71A); arg1=VK (Btn tests 0x0D,0x20)", "AGREE", "H"),
 131: ("msg type 6 = WM_KEYUP", "AGREE", "H"),
 132: ("msg type 0x11: winmgr SetFocus sends to window GAINING focus", "AGREE", "H"),
 133: ("msg type 0x10: winmgr SetFocus sends to window LOSING focus", "AGREE", "H"),
 134: ("msg type 7 = WM_LBUTTONDOWN (x,y,mods)", "AGREE", "H"),
 135: ("msg type 8 = WM_RBUTTONDOWN", "AGREE", "H"),
 136: ("msg type 10 = WM_LBUTTONUP", "AGREE", "H"),
 137: ("msg type 11 = WM_RBUTTONUP", "AGREE", "H"),
 138: ("msg type 13 = WM_MOUSEMOVE (x,y,mods)", "AGREE", "H"),
 139: ("msg type 14 = WM_MOUSEWHEEL; 4 args, arg4 = signed short delta; TextEdit scrolls delta/100", "AGREE", "H"),
 140: ("msg type 0x12: winmgr SetCapture sends (old,new) to both", "AGREE", "H"),
 141: ("msg type 0x13: hover tracker sends to window ENTERED; Btn sets hover bit", "AGREE", "H"),
 142: ("msg type 0x14: hover tracker sends to window LEFT; Btn clears hover bit", "AGREE", "H"),
 143: ("msg type 3 (code,value): controls SendMsg(target,3,code,val,0)", "AGREE", "H"),
 144: ("build msg{t,d1,d2,d3} -> slot 145", "AGREE SendMsg(5 args)", "H"),
 145: ("winmgr IsValid(win) then win->DoMessage(msg) synchronously", "AGREE SendMsg(win,msg&)", "H"),
 146: ("build msg -> slot 147", "AGREE PostMsg(5 args)", "H"),
 147: ("winmgr+0x3C: lock, enqueue {win,msg}, unlock; no dispatch", "AGREE PostMsg(win,msg&)", "H"),
 148: ("scalar deleting dtor (Release slot 2 calls it)", "past Mac end (cGZWin-own)", "H"),
 149: ("per-pixel hit test on private buffer [0x64]", "past Mac end (cGZWin-own)", "H"),
 150: ("(re)create private buffer (w,h)", "past Mac end (cGZWin-own)", "H"),
}

names = [n for n, _ in CLASSES]
with open(here + "\\slot_table.tsv", "w") as f:
    f.write("slot\toff\tmac\t" + "\t".join(names) + "\tshared_in_15\tcensus_overrides_of_111\texe_semantics\tverdict\tconf\n")
    for s in sorted(int(k) for k in rows):
        r = rows[str(s)]
        base = r["base"]
        cells = [r[n] or "" for n in names]
        shared = sum(1 for c in cells[1:] if c == base)
        sem, ver, conf = SEM.get(s, ("", "", ""))
        f.write(f"{s}\t{s*4:#x}\t{MAC.get(s,'-')}\t" + "\t".join(cells) + f"\t{shared}/15\t{r['census_overrides']}\t{sem}\t{ver}\t{conf}\n")
print("wrote slot_table.tsv")
