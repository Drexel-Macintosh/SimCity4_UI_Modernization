# INDEPENDENT recomputation from the PATCHED MACHINE SEMANTICS (not the model's Consts).
# Register-level replay of sub_76D3D0's legend loop with the candidate's 9 byte patches
# + the AddChildWindow detour. Nothing imported from emu_chart_legend except the two
# MEASURED font inputs, which I re-derive below from the brief's measured pixels.
def R(v): return int(round(v))

def replay(winW, winH, rows, f, detour=True, T1=True,T2=True,T3=True,
           A1=True,A2=True,A3=True,A4=True,A5=True,ROW0=True, rogue_multiplier=False):
    D_plain = R(106*f)-106 if T1 else 0
    D_cbox  = R(108*f)-108 if T2 else 0
    D_swc   = R(90*f)-90  if T3 else 0
    dy      = R(3*f) if A1 else 3            # 0x76E233 lea ecx,[eax+disp8]
    dyh     = (R(3*f)+R(6*f)) if A2 else 9   # 0x76E239 add eax,imm8
    sw      = R(10*f) if A3 else 10          # 0x76E23C add ebx,imm8
    gap     = R(4*f) if A4 else 4            # 0x76E2AF add ecx,imm8
    rmarg   = R(4*f) if A5 else 4            # 0x76E2C8 sub edx,imm8
    row0    = R(20*f) if ROW0 else 20        # 0x76DE79 imm32
    cbox    = len(rows) > 2                  # 0x76E0F8 cmp eax,2 / jbe

    # --- 0x76E0F0..0x76E0F5 : ebx = winW - D_plain - 0x6a
    ebx = winW - D_plain - 0x6a
    if cbox:
        # --- 0x76E155 : edx = winW - D_cbox ; 0x76E159 ecx = edx-0x5c ; 0x76E162 edx += -0x6c
        edx = winW - D_cbox
        cboxR_game = edx - 0x5c
        cboxL      = edx - 0x6c
        cboxH_game = 0x10                                    # 0x76E151 add ecx,0x10
        cboxW_game = cboxR_game - cboxL
        # our AddChildWindow detour @ chart vt+0x38 : size only, guard "exactly 16x16"
        if detour and cboxW_game == 16 and cboxH_game == 16:
            cboxW = cboxH = R(16*f)
        else:
            cboxW = cboxW_game; cboxH = cboxH_game
        if rogue_multiplier:                                  # sweep ran anyway, size-only
            cboxW = R(cboxW*f); cboxH = R(cboxH*f)
        cboxR = cboxL + cboxW
        # --- 0x76E1EF : ebx = winW - D_swc ; 0x76E1F8 : ebx -= 0x5a
        ebx = winW - D_swc - 0x5a
    else:
        cboxL = cboxR = cboxH = None
    swL = ebx; swR = swL + sw                                 # 0x76E236 / 0x76E23C / 0x76E23F
    txL = swR + gap                                           # 0x76E2A8 / 0x76E2AF
    txR = winW - rmarg                                        # 0x76E2C0 / 0x76E2C8
    boxW = txR - txL
    return dict(cboxL=cboxL,cboxR=cboxR,cboxH=cboxH,swL=swL,swR=swR,swH=dyh-dy,swDY=dy,
                txL=txL,txR=txR,boxW=boxW,row0=row0,winW=winW,winH=winH)

# MEASURED font inputs, re-derived from the brief, NOT imported:
#  1x: stock pitch of a 1-line row = 19, ROW_PAD=4 -> LH=15. 2x: measured 28.
#  ink ratio: "Income" 33px@1x -> 70px@2x  = 2.1212
LH={1.0:15,2.0:28}
W1={"Capacity":43,"Total":22,"Garbage":43,"Imported":41,"Exported":41,"Landfill":35,
    "Recycled":42,"Incinerated":53,"Waste":28,"to":10,"Energy":33,"Pollution":41,
    "Expenses":42,"Income":33}
SP=4
GAR=[("Capacity",0),("Total Garbage",1),("Imported",0),("Exported",1),("Landfill",0),
     ("Recycled",0),("Incinerated",0),("Waste to Energy",0),("Garbage Pollution",0)]
PLN=[("Expenses",0),("Income",0)]
def lines(lbl,box,r):
    n,cur=1,0.0
    for w in lbl.split(" "):
        x=W1[w]*r
        if cur>0 and cur+SP*r+x<=box: cur+=SP*r+x; continue
        if cur>0: n+=1; cur=0.0
        while x>box: n+=1; x-=box
        cur=x
    return n
def vert(g,rows,f,r):
    lh=LH[f]; y=g["row0"]; tops=[];ls=[]
    for lbl,extra in rows:
        n=lines(lbl,g["boxW"],r)+extra; tops.append(y); ls.append(n)
        y+=lh*n+4                                             # 0x76E34B lea edx,[ecx+eax+4]
    return tops,ls,y

def show(tag,g,rows,f,r):
    tops,ls,bot=vert(g,rows,f,r)
    print(" %-34s cbox=%s sw=%s(%dx%d dy%d) tx=%s boxW=%d"%(
        tag,"%s..%s"%(g["cboxL"],g["cboxR"]) if g["cboxL"] else "-",
        "%d..%d"%(g["swL"],g["swR"]),g["swR"]-g["swL"],g["swH"],g["swDY"],
        "%d..%d"%(g["txL"],g["txR"]),g["boxW"]))
    prob=[]
    if g["cboxL"] is not None:
        if g["swL"]<g["cboxR"]: prob.append("SWATCH INSIDE CHECKBOX (%d<%d)"%(g["swL"],g["cboxR"]))
        else: prob.append("ok cbox->swatch gap %d"%(g["swL"]-g["cboxR"]))
    if g["swR"]>g["txL"]: prob.append("SWATCH OVER TEXT")
    else: prob.append("ok swatch->text gap %d"%(g["txL"]-g["swR"]))
    if g["txR"]>g["winW"]: prob.append("TEXT PAST WINDOW")
    off=[i for i,(t,n) in enumerate(zip(tops,ls)) if t+LH[f]*n>g["winH"]]
    prob.append("rows offscreen=%d bottom=%d/%d"%(len(off),bot,g["winH"]))
    print("      tops=%s lines=%s"%(tops,ls))
    print("      %s"%(" | ".join(prob)))
    return bot,len(off)

print("=== f=1.0 SELF-CHECK vs MEASURED STOCK (window 488x256, origin abs 513) ===")
g=replay(488,256,GAR,1.0); show("cbox f=1",g,GAR,1.0,1.0)
print("      ABS: cbox %d..%d (meas 893..908+1) sw %d..%d (meas 911..920+1) txL %d (ink meas 926)"%(
    513+g["cboxL"],513+g["cboxR"]-1,513+g["swL"],513+g["swR"]-1,513+g["txL"]+1))
p=replay(488,256,PLN,1.0); show("plain f=1",p,PLN,1.0,1.0)
print("      ABS: sw %d..%d (meas 895..904) txL %d (ink meas 910)"%(513+p["swL"],513+p["swR"]-1,513+p["txL"]+1))

r2=70.0/33.0
print()
print("=== f=2.0 CANDIDATE (window 976x512) ===")
g=replay(976,512,GAR,2.0); b,o=show("BORNLEGEND cbox",g,GAR,2.0,r2)
p=replay(976,512,PLN,2.0); show("BORNLEGEND plain",p,PLN,2.0,r2)
print()
print("=== f=2.0 FAILURE MODES ===")
show("detour DECLINES (cbox stays 16)",replay(976,512,GAR,2.0,detour=False),GAR,2.0,r2)
show("rogue sweep ALSO doubles (->64)",replay(976,512,GAR,2.0,rogue_multiplier=True),GAR,2.0,r2)
show("T3 declines (swatch unbiased)",replay(976,512,GAR,2.0,T3=False),GAR,2.0,r2)
show("T2 declines (cbox unbiased)",replay(976,512,GAR,2.0,T2=False),GAR,2.0,r2)
show("A5 declines (text right margin 4)",replay(976,512,GAR,2.0,A5=False),GAR,2.0,r2)
print()
print("=== INK-RATIO ROBUSTNESS of the 9-row fit at f=2 (box 144) ===")
for rr in (2.00,2.1212,2.30,2.50,2.72,3.00):
    gg=replay(976,512,GAR,2.0); t,l,bt=vert(gg,GAR,2.0,rr)
    off=[i for i,(a,n) in enumerate(zip(t,l)) if a+28*n>512]
    print("   ratio %.4f -> lines %s bottom %d/512 offscreen %d"%(rr,l,bt,len(off)))
