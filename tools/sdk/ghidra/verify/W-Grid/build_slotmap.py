#!/usr/bin/env python3
"""Emit grid_slot_map.json: every cIGZWinGrid slot (Mac name) -> Windows VA (read from the exe's
cGZWinGrid interface vtable 0xADD578), stack-arg bytes (ret N), and the verdict + evidence decided
by hand in the W-Grid unit (2026-09-23). VA and ret N are re-measured on every run; verdicts are data.

    python build_slotmap.py            (writes grid_slot_map.json next to this script)
"""
import json
import os

import pe

VT_IFACE = 0xADD578      # cGZWinGrid's cIGZWinGrid vtable (object +0)
VT_ABSTRACT = 0xADD348   # cIGZWinGrid pure vtable: 140 x _purecall (0x5D4A10)
VT_WIN = 0xADD7B0        # cGZWinGrid's cIGZWin vtable (object +4)
GDT = r"C:\dev\SC4UIScale\tools\sdk\ghidra\out\SimCity4.gdt.json"

# functions whose first linear 'ret' is not their own (tail-jmp / shared tails) - measured by hand
RET_OVERRIDE = {4: "tail-jmp 0x99D2FE (0 args)", 45: 8, 117: 16, 133: 36}

V, C = "VERIFIED", "CONSISTENT"
VERDICT = {
    0: (V, "cmp riid,0xDAA6B9BE -> *ppv=this(+0),AddRef; else ecx+=4, jmp cGZWin QI 0x99B774"),
    1: (V, "inc [ecx+0x10] (shared AddRef)"), 2: (V, "dec [ecx+0x10]; destroy at 1"),
    3: (V, "cIGZWin slot4 thunk target; chains base Init 0x99C2C3 on this+4"),
    4: (V, "cIGZWin slot5 thunk target; releases +0x164/+0x168/+0x208/+0x2C0/+0x26C/+0x270/+0x274/+0x278, tail-jmp base 0x99D2FE"),
    5: (V, "returns this+4 (null-safe); deserializer calls it before cIGZWin calls"),
    6: (C, "runs layout 0x9AEE63, sets dirty byte +0xE4"),
    7: (V, "ret 0x10; forwards to cGZWin SetArea 0x99C837 then recomputes +0x118..+0x124; cIGZWin slot55 thunks here"),
    8: (V, "rect {+0xF0, +0xF4, W-+0xF8, H-+0xFC} (gutters)"),
    9: (V, "grid area + colhdr(+0x110 if flag 8) + rowhdr(+0x114 if flag 0x10) - scrollbar W/H"),
    10: (V, "if !(flags&f) -> slot11(flags|f); deserializer f* keywords"), 11: (V, "stores +0xDC; scrollbar rebuild on bits 6"),
    12: (V, "slot11(flags&~f)"), 13: (V, "flags&f"), 14: (V, "mov eax,[ecx+0xDC]"),
    15: (V, "+0x208 AddRef/Release; deserializer font="), 16: (V, "mov eax,[ecx+0x208]"),
    17: (V, "(color,idx<6) -> +0x20C+4*idx; deserializer fontcolor idx 0"), 18: (V, "(color*,idx) reads +0x20C+4*idx"),
    19: (V, "(color,idx,start,count) -> column-format map +0x19C key (c,0)"), 20: (V, "same on row map +0x1C0 key (0,r)"),
    21: (V, "flag 0x800 (fcellwrap) via slots 13/10/12; deserializer textwrapping"), 22: (V, "IsFlagSet(0x800)"),
    23: (V, "4 out-ptrs <- +0xF0..+0xFC"), 24: (V, "4 args -> +0xF0..+0xFC; deserializer gutters= (0,0,0,0 when absent)"),
    25: (V, "4 out-ptrs <- +0x100..+0x10C"), 26: (V, "4 args -> +0x100..+0x10C"),
    27: (V, "(bool,color): flag 0x200 fdoutline + +0x148; deserializer fdoutline/olinecolor"), 28: (V, "mov eax,[ecx+0x148]"),
    29: (V, "counter +0xE8 inc/dec; layout skips while >0"),
    30: (C, "(cols->+0x138, maxSel->+0x190, bool allowNoSel->flag 0x1000); flags=(f&0xFFFC2BA6)|0x2BA6, rule=1"),
    31: (V, "first visible row +0x12C += n, clamped"), 32: (V, "first visible col +0x128 += n, clamped"),
    33: (V, "slot31(n<<2)"), 34: (V, "slot32(n<<2)"), 35: (V, "sets +0x128 clamped"), 36: (V, "sets +0x12C clamped"),
    37: (V, "slot35(col); slot36(row)"), 38: (V, "out <- +0x18C,+0x190"), 39: (V, "+0x18C,+0x190 then ClearSelection; deserializer selrule/maxselcount"),
    40: (V, "counts selection list +0x194"), 41: (C, "copies up to *count (col,row) pairs from +0x194"),
    42: (C, "first selected (col*,row*), false if none"), 43: (V, "ClearSelection + AddCellToSelection(c,r,1)"),
    44: (V, "(c,r,bool) honours +0x190 max and +0x18C rule"), 45: (V, "(c,r) rule-dependent list match; ret 8"),
    46: (V, "empties +0x194, invalidate"), 47: (V, "flags 0x2000 ffixcolcnt / 0x4000 ffixrowcnt; limits reset -1"),
    48: (V, "+0x138,+0x13C"), 49: (V, "out <- +0x138,+0x13C"), 50: (C, "cell map +0x1E4 min/max -> rect"),
    51: (V, "{+0x128,+0x12C, +0x128+(int)+0x130, +0x12C+(int)+0x134}"), 52: (V, "limit +0x138"), 53: (V, "limit +0x13C"),
    54: (V, "slot52 && slot53"), 55: (V, "out <- +0x15C,+0x160; false if -1"), 56: (V, "cIGZWin slot106 fill colour on this+4"),
    57: (V, "+0x164 AddRef/Release; GZPaint draws it under flag 0x100"), 58: (V, "2 colours -> +0x14C,+0x150; deserializer colgridclr/rowgridclr"),
    59: (V, "out <- +0x14C,+0x150"), 60: (V, "+0x198; deserializer textalign"), 61: (V, "(start,count,byte) -> col format +0x1D"),
    62: (V, "(start,count,byte) -> row format +0x1D"), 63: (V, "mov eax,[ecx+0x198]"),
    64: (V, "+0x140 (px); deserializer dcolwidth (default 100)"), 65: (V, "(start,count,w) -> int16 col-format +0x24 (clamped >=0); wingridcol"),
    66: (V, "+0x144 (px); deserializer drowheight (default 20)"), 67: (V, "(start,count,h) -> int16 row-format +0x24; wingridrow"),
    68: (V, "mov eax,[ecx+0x140]"), 69: (V, "mov eax,[ecx+0x144]"), 70: (V, "(start,count) sum of resolver 0x9AD684"),
    71: (V, "(start,count) sum of resolver 0x9AE387"), 72: (V, "flag 8, height +0x110"), 73: (V, "flag 0x10, width +0x114"),
    74: (V, "(bool col->flag 8, bool row->flag 0x10); deserializer enablehdr"), 75: (V, "out <- +0x110,+0x114"),
    76: (V, "+0x110,+0x114 (px); deserializer colhdrsz,rowhdrsz"), 77: (V, "9-dword format -> +0x2C0 (GZPaint heading font)"),
    78: (V, "map +0x2A8 lookup (GZPaint col headings)"), 79: (V, "map +0x2A8 store; game code SetColumnHeading(c,'Class'...) 0x8B0ECC"),
    80: (V, "map +0x2B4 lookup"), 81: (V, "map +0x2B4 store"), 82: (V, "clears +0x2B4"), 83: (V, "clears +0x2A8"),
    84: (V, "(c,r,fmt*) default +0x208 merged with col/row/cell; row auto-height calls it (vt+0x150)"),
    85: (V, "(c,r,fmt*), (-1,-1)=default; deserializer wingridcell, FileBrowser 0x9A2111"), 86: (C, "removes cell format"),
    87: (V, "col map +0x19C key (c,0)"), 88: (V, "row map +0x1C0 key (0,r)"), 89: (V, "slot87 else slot88"),
    90: (C, "(c,r,font*) bounds-checked via slot54"), 91: (C, "(c,r,a,b) colours"), 92: (C, "(c,r,b) -> fmt +0x1C"),
    93: (C, "(c,r,h,v) -> fmt +0x1D/+0x1E"), 94: (C, "(c,r,a,b) -> fmt +0x1F/+0x20"), 95: (V, "cell record type (1 win, 2 text, 4 bitmap)"),
    96: (C, "deselect (slot44 c,r,0) + remove"), 97: (V, "loops slot96 over (c,r,w,h)"), 98: (V, "slot50 -> slot97 -> slot46"),
    99: (C, "shared stub 'xor al,al; ret 0x10' - unimplemented on Windows"), 100: (C, "(start,count,mode default 2)"),
    101: (C, "(start,count,mode default 3); game 0x684EC3"), 102: (C, "(src,dst,count,flags)"), 103: (C, "(src,dst,count,flags)"),
    104: (V, "first-visible + float visible counts"), 105: (V, "slot104 then slot31/slot32 scroll"),
    106: (V, "(c,r,rect*) via GetColumnWidth; cell-window placement insets it by cell gutters"),
    107: (V, "out <- +0x128,+0x12C"), 108: (V, "+0x128,+0x12C + invalidate"), 109: (V, "float* x2 <- +0x130,+0x134"),
    110: (C, "(x,y,out*,out*) uses slot8 + header sizes"), 111: (V, "type 2 -> string copy"),
    112: (V, "6 args; deserializer wingridcell text; Custom Tunes 0x4F4D78"), 113: (V, "type 4"),
    114: (V, "(c,r,bmp,1); deserializer + FileBrowser 0x9A49B0"), 115: (V, "type 1"),
    116: (V, "6 args; Custom Tunes checkbox windows 0x4F4D9B; calls slot117"),
    117: (V, "(win*,id,col*,row*) walks +0x22C, compares ptr or GetID (cIGZWin vt+0xFC); ret 0x10"),
    118: (C, "(col,flag) sizes col from cell windows' GetW"), 119: (V, "cell record +0x14 (mode +0x188=1)"),
    120: (V, "cell record +0x14; game 0x669854 after GetSelection2"), 121: (V, "map +0x25C"), 122: (V, "map +0x25C"),
    123: (V, "map +0x250"), 124: (V, "map +0x250"), 125: (V, "+0x268, mode 1"), 126: (V, "mov eax,[ecx+0x268]"),
    127: (C, "mode 2: slot120 then object vt+0"), 128: (C, "(c,r,obj*) AddRef + slot120 path"),
    129: (V, "+0x268 -> tail-jmp object vt+0"), 130: (V, "+0x268 AddRef/Release, mode 2"),
    131: (C, "4 args; game 0x47AD20/0x66ACC9"), 132: (C, "4 args"), 133: (C, "9 args (ret 0x24); strlen when len==-1"),
    134: (V, "+0x168 AddRef/Release; GZPaint notifies 0xFA785CB0/B1 to it"), 135: (C, "out <- cGZWin buffer obj+0x6C, rect obj+0x28"),
    136: (V, "+0x274 -> applied to v-scrollbar +0x26C"), 137: (V, "+0x278 -> h-scrollbar +0x270"),
    138: (V, "(idx<3, id) -> +0x29C+4*idx (played by extra slot 141)"), 139: (V, "SetFlag(0x40000) = fdrpdnmenu"),
}


def main():
    names = {}
    for t in json.load(open(GDT))["types"]:
        if t["name"] == "vftable_cIGZWinGrid":
            for f in t["fields"]:
                names[f["off"] // 4] = f["name"]
    abstract = [pe.u32(VT_ABSTRACT + 4 * k) for k in range(141)]
    n_pure = next(k for k, v in enumerate(abstract) if v != 0x5D4A10)
    rows = []
    for k in range(142):
        va = pe.u32(VT_IFACE + 4 * k)
        ret = RET_OVERRIDE.get(k, pe.ret_n(va, 0x1800))
        st, ev = VERDICT.get(k, ("UNCHECKED", "class-added virtual (beyond Mac list)"))
        rows.append({"slot": k, "vt_off": "0x%03X" % (4 * k), "mac_name": names.get(k, "(beyond Mac)"),
                     "windows_va": "0x%08X" % va, "ret_bytes": ret, "status": st, "evidence": ev})
    out = {"exe": pe.GAME_EXE, "iid": "0xDAA6B9BE", "clsid": "0xDAA6B9BF",
           "interface_vtable": "0x%08X" % VT_IFACE, "abstract_vtable": "0x%08X" % VT_ABSTRACT,
           "abstract_purecall_slots": n_pure, "win_vtable_at_plus4": "0x%08X" % VT_WIN, "slots": rows}
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grid_slot_map.json")
    json.dump(out, open(p, "w"), indent=1)
    print("wrote", p, "| purecall slots in abstract vtable:", n_pure,
          "| statuses:", {s: sum(1 for r in rows if r["status"] == s) for s in (V, C, "UNCHECKED")})


if __name__ == "__main__":
    main()
