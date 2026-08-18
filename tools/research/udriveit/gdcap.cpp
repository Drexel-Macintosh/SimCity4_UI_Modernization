// gdcap.cpp - #188 LANE A: capture every primitive SC4 submits, one frame at a
// time, and name the drawer by its RETURN ADDRESS.
//
// WHY THIS LANE CANNOT BE DEFEATED BY A NAME
// ------------------------------------------
// SC4 does not talk to Direct3D directly. It talks to cIGZGDriver (GZIID
// 0xA4554849, vendor\gzcom-dll\gzcom-dll\include\cIGZGDriver.h), an
// OpenGL-1.1-shaped abstraction. The live implementation in this install is
// the DirectX-7 driver, GZCLSID 0xBADB6906 (= GZCLSIDDefs.h:291
// kcSGLDriverDX7), whose vtable is at VA 0x00AC4660 and whose
// GetGZCLSID (0x00886E00) is literally `mov eax,0xBADB6906; ret`.
//
// In THAT driver the entire 2D blit family is unimplemented:
//     BitBlt                  0x00882050  mov [ecx+0x110],3 ; ret 0x24
//     StretchBlt              0x00882060  mov [ecx+0x110],3 ; ret 0x2C
//     BitBltAlpha             0x00882070  mov [ecx+0x110],3 ; ret 0x28
//     StretchBltAlpha         0x00882080  mov [ecx+0x110],3 ; ret 0x30
//     BitBltAlphaModulate     0x00882070  (same stub)
//     StretchBltAlphaModulate 0x00882080  (same stub)
// (3 = the GDriver error code parked at this+0x110.) So NOTHING in this build
// reaches the screen as a blit. Every pixel - 3D world, billboards, the whole
// cIGZWin UI - is a primitive, and there are exactly two doors:
//
//     cIGZGDriver::DrawArrays    vt+0x0C  VA 0x008857E0  ret 0xC   (3 args)
//     cIGZGDriver::DrawElements  vt+0x10  VA 0x00885A00  ret 0x10  (4 args)
//
// Hook those two and you have seen every quad the game drew. dgVoodoo2 sits
// BELOW this (DrawArrays funnels into the D3D wrapper object at drv+0x10,
// which calls IDirect3DDevice7::DrawPrimitive / DrawPrimitiveVB /
// DrawIndexedPrimitive at vtable +0x64 / +0x7C / +0x68 - e.g. 0x0088957C,
// 0x00889864). Nothing dgVoodoo does can hide a submission from us.
//
// DRIVER STATE WE READ (all offsets measured, VAs cited)
//   drv+0x010  D3D device-wrapper object   (its +0x14 = IDirect3DDevice7*)
//   drv+0x118  texture stage count         (DrawArrays 0x00885806)
//   drv+0x11C  texture stage array base, stride 0x80; rec+4 = texture id
//                                          (SetTexture 0x00884810: shl eax,7)
//   drv+0x1B0  gdVertexFormat              (InterleavedArrays 0x00881EF5)
//   drv+0x1B4  vertex STRIDE (already resolved if caller passed 0)  0x00881EDF
//   drv+0x1C4  vertex ARRAY BASE POINTER (plain CPU memory)         0x00881F08
//   drv+0x208  current MatrixMode          (MatrixMode 0x00881EA0)
//   drv+0x238  screen height used to flip Y (GetViewport 0x008838D0)
//
//   DrawArrays computes first-vertex = *(char**)(drv+0x1C4) + stride*first
//   (0x0088588E..0x00885895). We reproduce that exactly.
//
//   POSITION IS ALWAYS THE FIRST 3 FLOATS OF A VERTEX. Proof, not guess:
//   cIGZGDriver::VertexFormatElementOffset (vt+0x24, 0x0087C4C0) tail-calls
//   0x008D04A0, which returns size[elem]*k + stride(fmt & mask[elem]) and
//   SKIPS the stride term when elem == 0 (`test ecx,ecx / jle 0x8D04E0`).
//   size[0] = 0x0C at 0x00ACC0AC. Element 0 is 12 bytes at offset 0 = XYZ.
//
//   gdPrimType -> D3DPRIMITIVETYPE table at 0x00AC44CC = {4,5,6,1,2,3,4,4}
//   and the DrawArrays jump table at 0x008859DC proves the enum:
//     0 TRIANGLES (direct, D3D 4)      4 LINES        (direct, D3D 2)
//     1 TRIANGLE_STRIP (3n-6 indices)  5 LINE_STRIP   (direct, D3D 3)
//     2 TRIANGLE_FAN   (3n-6 indices)  6 QUADS        (3*(n/2) indices)
//     3 POINTS         (direct, D3D 1) 7 QUAD_STRIP   (3n-6 indices)
//   >>> A billboard is primType 6 with count 4. That is the balloon's shape. <<<
//
// LOG-ONLY. This module never writes a game byte, never changes a size, never
// suppresses a draw. It calls the original every time.
//
// ARMING (no flooding): nothing is recorded until GpuCap != 0 in the ini. The
// capture then runs for GpuCap Clear() boundaries and stops itself for good.
// Records go to a preallocated array in memory; the file is written once, when
// the window closes. Nothing does I/O inside the hook.

#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include "MinHook.h"

namespace GdCap {

// ---------------------------------------------------------------- addresses
// SimCity 4 Deluxe 1.1.641, image base 0x400000, code unchanged (the 4GB patch
// flips one header bit only). If the module base is ever not 0x400000 these
// must be rebased - the probe refuses to arm if it is not.
static const uintptr_t kDrawArrays   = 0x008857E0;
static const uintptr_t kDrawElements = 0x00885A00;
static const uintptr_t kClear        = 0x00882C80;

// ------------------------------------------------------------------ record
#pragma pack(push, 1)
struct Rec
{
    uint32_t frame;
    uint32_t seq;
    uint32_t caller;     // <<< THE ANSWER: the VA that decided to draw this
    uint16_t prim;       // gdPrimType (6 = QUADS)
    uint16_t verts;      // vertex count actually inspected
    uint32_t fmt;        // drv+0x1B0
    uint32_t stride;     // drv+0x1B4
    uint32_t tex0;       // stage-0 texture id
    uint32_t tex1;       // stage-1 texture id
    float    bb[6];      // minx,miny,minz, maxx,maxy,maxz in VERTEX space
    float    v0[3];      // first vertex verbatim (sanity / degenerate check)
};                       // 64 bytes
#pragma pack(pop)

static Rec*     gRec      = nullptr;
static uint32_t gCap      = 0;     // records allocated
static uint32_t gCount    = 0;     // records used
static uint32_t gFrame    = 0;
static uint32_t gFramesLeft = 0;   // 0 => disarmed
static bool     gArmed    = false;
static bool     gDone     = false;
static char     gOutPath[MAX_PATH];

// Per-frame census so a NULL can never be mistaken for evidence.
static uint32_t gCallsThisFrame = 0;
static uint32_t gCallsTotal     = 0;

// -------------------------------------------------------------- originals
typedef void (__fastcall* DrawArraysFn)(void* self, void* edx,
                                        uint32_t prim, int32_t first, int32_t count);
typedef void (__fastcall* DrawElementsFn)(void* self, void* edx,
                                          uint32_t prim, int32_t count,
                                          uint32_t type, const void* indices);
typedef void (__fastcall* ClearFn)(void* self, void* edx, uint32_t mask);

static DrawArraysFn   oDrawArrays   = nullptr;
static DrawElementsFn oDrawElements = nullptr;
static ClearFn        oClear        = nullptr;

// ------------------------------------------------------------ state reads
static inline uint32_t U32(void* p, uint32_t off)
{ return *reinterpret_cast<uint32_t*>(reinterpret_cast<char*>(p) + off); }

static inline uint32_t StageTex(void* drv, uint32_t stage)
{
    char* base = *reinterpret_cast<char**>(reinterpret_cast<char*>(drv) + 0x11C);
    if (!base) { return 0; }
    if (stage >= U32(drv, 0x118)) { return 0; }
    return *reinterpret_cast<uint32_t*>(base + stage * 0x80 + 4);
}

// Reads at most kMaxScan vertices. A batched draw is NOT skipped - we still
// record its bbox and its caller, because the caller is what we are after.
static const int kMaxScan = 4096;

static void Bbox(const char* v, uint32_t stride, int n, float* bb, float* v0)
{
    bb[0] = bb[1] = bb[2] =  3.4e38f;
    bb[3] = bb[4] = bb[5] = -3.4e38f;
    v0[0] = v0[1] = v0[2] = 0.0f;
    if (!v || stride < 12 || n <= 0) { return; }
    if (n > kMaxScan) { n = kMaxScan; }
    for (int i = 0; i < n; ++i)
    {
        const float* p = reinterpret_cast<const float*>(v + (size_t)stride * i);
        if (i == 0) { v0[0] = p[0]; v0[1] = p[1]; v0[2] = p[2]; }
        for (int a = 0; a < 3; ++a)
        {
            if (p[a] < bb[a])     { bb[a]     = p[a]; }
            if (p[a] > bb[3 + a]) { bb[3 + a] = p[a]; }
        }
    }
}

static void Emit(void* drv, uint32_t caller, uint32_t prim,
                 const char* verts, int n)
{
    if (gCount >= gCap) { return; }
    Rec& r    = gRec[gCount++];
    r.frame   = gFrame;
    r.seq     = gCallsThisFrame;
    r.caller  = caller;
    r.prim    = (uint16_t)prim;
    r.verts   = (uint16_t)(n > kMaxScan ? kMaxScan : n);
    r.fmt     = U32(drv, 0x1B0);
    r.stride  = U32(drv, 0x1B4);
    r.tex0    = StageTex(drv, 0);
    r.tex1    = StageTex(drv, 1);
    Bbox(verts, r.stride, n, r.bb, r.v0);
}

// --------------------------------------------------------------- detours
// __thiscall => __fastcall(self, edx). Arity and callee-cleanup match the
// originals exactly (DrawArrays ret 0xC at 0x008859D7, DrawElements ret 0x10
// at 0x00885DA8, Clear ret 4 at 0x00882D06), so MinHook's trampoline is safe.
void __fastcall DrawArraysDetour(void* self, void* edx,
                                 uint32_t prim, int32_t first, int32_t count)
{
    ++gCallsThisFrame; ++gCallsTotal;
    if (gArmed && gFramesLeft && count > 0)
    {
        uint32_t stride = U32(self, 0x1B4);
        char*    base   = *reinterpret_cast<char**>(
                              reinterpret_cast<char*>(self) + 0x1C4);
        const char* v = base ? base + (size_t)stride * (size_t)first : nullptr;
        Emit(self, (uint32_t)(uintptr_t)_ReturnAddress(), prim, v, count);
    }
    oDrawArrays(self, edx, prim, first, count);
}

void __fastcall DrawElementsDetour(void* self, void* edx,
                                   uint32_t prim, int32_t count,
                                   uint32_t type, const void* indices)
{
    ++gCallsThisFrame; ++gCallsTotal;
    if (gArmed && gFramesLeft && count > 0 && indices)
    {
        // Index element size is carried by gdType. We only need a bbox, so we
        // bracket by min/max index and scan that span - correct for every
        // width, and it can never read outside the array the game just used.
        uint32_t stride = U32(self, 0x1B4);
        char*    base   = *reinterpret_cast<char**>(
                              reinterpret_cast<char*>(self) + 0x1C4);
        int      lo = 0x7FFFFFFF, hi = 0;
        int      n  = count > kMaxScan ? kMaxScan : count;
        // 16-bit indices are what the DX7 backend builds (0x0088A240 allocates
        // a WORD buffer); 32-bit is handled defensively.
        bool wide = (type == 0x1405u /*GL_UNSIGNED_INT-shaped*/);
        for (int i = 0; i < n; ++i)
        {
            int ix = wide ? (int)reinterpret_cast<const uint32_t*>(indices)[i]
                          : (int)reinterpret_cast<const uint16_t*>(indices)[i];
            if (ix < lo) { lo = ix; }
            if (ix > hi) { hi = ix; }
        }
        if (base && hi >= lo && (hi - lo) < kMaxScan)
        {
            Emit(self, (uint32_t)(uintptr_t)_ReturnAddress(), prim,
                 base + (size_t)stride * (size_t)lo, hi - lo + 1);
        }
    }
    oDrawElements(self, edx, prim, count, type, indices);
}

static void Flush();

void __fastcall ClearDetour(void* self, void* edx, uint32_t mask)
{
    // Frame boundary. NOTE: Clear is a frame marker of convenience, not a
    // guarantee of one-per-frame. If the census shows an implausible call
    // count per "frame", move the marker to cIGZGDriver::Flush (vt+0xAC,
    // 0x00884BA0) or cIGZGraphicSystem2::LazyFlush.
    if (gArmed && gFramesLeft)
    {
        ++gFrame;
        gCallsThisFrame = 0;
        if (--gFramesLeft == 0) { Flush(); gArmed = false; gDone = true; }
    }
    oClear(self, edx, mask);
}

// ----------------------------------------------------------------- output
static void Flush()
{
    FILE* f = nullptr;
    if (fopen_s(&f, gOutPath, "wb") != 0 || !f) { return; }
    // header: magic, version, record count, total driver calls seen
    uint32_t hdr[4] = { 0x50414347u /*'GCAP'*/, 1u, gCount, gCallsTotal };
    fwrite(hdr, sizeof(hdr), 1, f);
    fwrite(gRec, sizeof(Rec), gCount, f);
    fclose(f);
}

// ------------------------------------------------------------------ arming
// frames: how many Clear() boundaries to record. 1 or 2 is plenty.
// Returns false and does nothing at all if it cannot verify the ground it
// stands on - a probe that guesses is worse than no probe.
bool Install(uint32_t frames, uint32_t maxRecords, const char* outPath)
{
    if (gDone || gArmed || frames == 0) { return false; }
    if ((uintptr_t)GetModuleHandleW(nullptr) != 0x00400000) { return false; }

    // Positive control on the TARGET, not on ourselves: the byte at
    // DrawArrays must still be `push ecx` (0x51) and DrawElements must still
    // be `sub esp,0xC` (0x83 0xEC 0x0C). If the exe ever moves, we refuse.
    const uint8_t* a = reinterpret_cast<const uint8_t*>(kDrawArrays);
    const uint8_t* e = reinterpret_cast<const uint8_t*>(kDrawElements);
    if (a[0] != 0x51) { return false; }
    if (!(e[0] == 0x83 && e[1] == 0xEC && e[2] == 0x0C)) { return false; }

    gCap = maxRecords ? maxRecords : 200000u;          // 200k * 64B = 12.8 MB
    gRec = static_cast<Rec*>(::calloc(gCap, sizeof(Rec)));
    if (!gRec) { gCap = 0; return false; }
    lstrcpynA(gOutPath, outPath, MAX_PATH);

    if (MH_CreateHook((void*)kDrawArrays,   &DrawArraysDetour,
                      reinterpret_cast<void**>(&oDrawArrays))   != MH_OK) { return false; }
    if (MH_CreateHook((void*)kDrawElements, &DrawElementsDetour,
                      reinterpret_cast<void**>(&oDrawElements)) != MH_OK) { return false; }
    if (MH_CreateHook((void*)kClear,        &ClearDetour,
                      reinterpret_cast<void**>(&oClear))        != MH_OK) { return false; }
    MH_EnableHook((void*)kDrawArrays);
    MH_EnableHook((void*)kDrawElements);
    MH_EnableHook((void*)kClear);

    gFramesLeft = frames;
    gArmed      = true;
    return true;
}

// gCallsTotal is the POSITIVE CONTROL. If a capture returns zero balloon-sized
// quads but gCallsTotal is in the thousands, the null is real and the balloon
// is not drawn through cIGZGDriver at all (see the failure-mode note in the
// lane report). If gCallsTotal is 0, the probe never saw the driver and the
// null means nothing.
uint32_t CallsSeen() { return gCallsTotal; }

} // namespace GdCap
