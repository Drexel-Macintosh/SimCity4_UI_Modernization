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
//
// 2026-08-24, wired into the DLL for register row #4 (Build 1). Four review
// findings fixed IN THIS FILE, because the header's own claims were not true
// of the code:
//   1. The file write used to happen INSIDE ClearDetour at self-disarm -
//      exactly the I/O-in-hook this header forbids. It now lives in
//      WriteCloseout(), called from PreAppShutdown by the wrapper.
//   2. MH_Initialize() was never called - armed alone, every MH_CreateHook
//      returned MH_ERROR_NOT_INITIALIZED and Install() silently no-opped.
//   3. Clear 0x882C80 was hooked with NO byte gate while the two draw doors
//      had one. It is now gated on its measured prologue (56 8B F1 8B 4E 10).
//   4. The out-path was ANSI; the Plugins dir can be non-ANSI. Now wide.
// Plus the CITY LATCH: hooks install early (before device creation), but
// recording begins only when Begin(skip) fires at PostCityInit and `skip`
// further Clear boundaries pass - otherwise the capture spends its N frames
// on the intro/region screen and the launch answers the wrong question.

#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <intrin.h>
#include "MinHook.h"
#include "../../../src/GdCap.h"

#pragma intrinsic(_ReturnAddress)

namespace GdCap {

// ---------------------------------------------------------------- addresses
// SimCity 4 Deluxe 1.1.641, image base 0x400000, code unchanged (the 4GB patch
// flips one header bit only). If the module base is ever not 0x400000 these
// must be rebased - the probe refuses to arm if it is not.
static const uintptr_t kDrawArrays   = 0x008857E0;
static const uintptr_t kDrawElements = 0x00885A00;
static const uintptr_t kClear        = 0x00882C80;
// The submitter wrapper (47 bytes, straight-line, zero branches: one call =
// exactly one DrawArrays). The FIRST census proved why this hook is needed:
// every recorded `caller` landed inside 0x007D29xx/0x007D4Bxx - the driver's
// own wrappers - which names the plumbing, not the system. Hooking here and
// recording ITS return address names the drawer. Prologue byte-gated with
// the same bytes the shipped DISPATCHQUAD probe verifies.
static const uintptr_t kSubmitPrimitive = 0x007D2990;
// The frame marker is NOT settled: a capture on 2026-08-24 recorded 2 frames
// off Clear, and the very next launch saw ZERO Clear boundaries in 37 s with
// 3.89M driver calls - a dead marker, not a static view. This file's own
// header always said Clear is "a frame marker of convenience, not a
// guarantee", and named Flush (vt+0xAC) as the fallback. So hook BOTH, count
// BOTH unconditionally (each is the other's positive control), and let the
// FIRST one that fires own the boundary for the session - measured, not
// guessed. The closeout logs which one won and what both counted.
static const uintptr_t kFlush = 0x00884BA0;

// ------------------------------------------------------------------ record
#pragma pack(push, 1)
struct Rec
{
    uint32_t frame;
    uint32_t seq;
    uint32_t caller;     // immediate caller of DrawArrays/DrawElements -
                         // usually inside the driver's own submit wrappers
    uint32_t outer;      // <<< THE ANSWER: the caller of SubmitPrimitive
                         // 0x7D2990, i.e. the SYSTEM that decided to draw.
                         // 0 when the draw did not come through it.
    uint16_t prim;       // gdPrimType (6 = QUADS)
    uint16_t verts;      // vertex count actually inspected
    uint32_t fmt;        // drv+0x1B0
    uint32_t stride;     // drv+0x1B4
    uint32_t tex0;       // stage-0 texture id
    uint32_t tex1;       // stage-1 texture id
    float    bb[6];      // minx,miny,minz, maxx,maxy,maxz in VERTEX space
    float    v0[3];      // first vertex verbatim (sanity / degenerate check)
};                       // 68 bytes (12 + 4 + 16 + 24 + 12; pack(1))
#pragma pack(pop)

static Rec*     gRec      = nullptr;
static uint32_t gCap      = 0;     // records allocated
static uint32_t gCount    = 0;     // records used
static uint32_t gFrame    = 0;
static uint32_t gFramesLeft = 0;   // boundaries still to record once armed
static uint32_t gSkipLeft = 0;     // boundaries to skip after Begin()
static bool     gInstalled = false;
static bool     gBegun    = false; // Begin() latched (PostCityInit)
static bool     gArmed    = false; // actively recording
static bool     gDone     = false;
static bool     gFlushed  = false;
static wchar_t  gOutPath[MAX_PATH];

// Per-frame census so a NULL can never be mistaken for evidence.
static uint32_t gCallsThisFrame = 0;
static uint32_t gCallsTotal     = 0;

// Clear boundaries seen since Begin() latched. SC4 only issues a Clear when
// it actually redraws, and a still/paused city redraws rarely - so this is
// the number that tells us whether the skip could ever have elapsed. Logged
// at CityExit and WriteCloseout: a low count is not a bug, it is the measured
// redraw rate, and it says "keep the view moving".
static uint32_t gClearsSinceBegin = 0;

// Unconditional marker censuses - each is the other's positive control, and
// both together separate "the game did not redraw" from "the hook is dead".
static uint32_t gClearsTotal  = 0;
static uint32_t gFlushesTotal = 0;
// 0 = undecided, 1 = Clear owns the boundary, 2 = Flush owns it.
static int      gMarker = 0;

// -------------------------------------------------------------- originals
typedef void (__fastcall* DrawArraysFn)(void* self, void* edx,
                                        uint32_t prim, int32_t first, int32_t count);
typedef void (__fastcall* DrawElementsFn)(void* self, void* edx,
                                          uint32_t prim, int32_t count,
                                          uint32_t type, const void* indices);
typedef void (__fastcall* ClearFn)(void* self, void* edx, uint32_t mask);
typedef void (__fastcall* SubmitFn)(void* self, void* edx, uint32_t prim,
                                    uint32_t fmt, uint32_t count,
                                    const float* verts);
typedef void (__fastcall* FlushFn)(void* self, void* edx);

static DrawArraysFn   oDrawArrays   = nullptr;
static DrawElementsFn oDrawElements = nullptr;
static ClearFn        oClear        = nullptr;
static SubmitFn       oSubmit       = nullptr;
static FlushFn        oFlush        = nullptr;

// Set by SubmitPrimitiveDetour for the duration of one submission, read by
// Emit. Single render thread; a stray interleave costs one mis-attributed
// record, never a crash (the value is only ever printed).
static uint32_t gPendingOuter = 0;

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
    r.outer   = gPendingOuter;
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
        // A negative `first` would sign-extend into a huge size_t and hand
        // Bbox a wild pointer (review 2026-08-24, finding 10a). Record the
        // call with no vertex scan instead - the caller is the answer.
        const char* v = (base && first >= 0)
            ? base + (size_t)stride * (size_t)first : nullptr;
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
        // a WORD buffer); 32-bit is handled defensively. The gdType enum is
        // GL-shaped: 0x1401 UNSIGNED_BYTE, 0x1403 UNSIGNED_SHORT, 0x1405
        // UNSIGNED_INT. An UNKNOWN width must NOT default to 16-bit - that
        // reads past an 8-bit buffer and lets a garbage `hi` drive Emit into
        // vertices the game never touched (review 2026-08-24, finding 10b).
        // Unknown width => record the call with no vertex scan.
        const bool wide   = (type == 0x1405u);
        const bool narrow = (type == 0x1401u);
        const bool known  = wide || narrow || (type == 0x1403u);
        for (int i = 0; known && i < n; ++i)
        {
            int ix = wide   ? (int)reinterpret_cast<const uint32_t*>(indices)[i]
                   : narrow ? (int)reinterpret_cast<const uint8_t*>(indices)[i]
                            : (int)reinterpret_cast<const uint16_t*>(indices)[i];
            if (ix < lo) { lo = ix; }
            if (ix > hi) { hi = ix; }
        }
        if (known && base && hi >= lo && (hi - lo) < kMaxScan)
        {
            Emit(self, (uint32_t)(uintptr_t)_ReturnAddress(), prim,
                 base + (size_t)stride * (size_t)lo, hi - lo + 1);
        }
        else if (!known)
        {
            Emit(self, (uint32_t)(uintptr_t)_ReturnAddress(), prim,
                 nullptr, count);
        }
    }
    oDrawElements(self, edx, prim, count, type, indices);
}

// One call = exactly one DrawArrays, so the pairing with Emit is exact.
void __fastcall SubmitPrimitiveDetour(void* self, void* edx, uint32_t prim,
                                      uint32_t fmt, uint32_t count,
                                      const float* verts)
{
    const uint32_t prev = gPendingOuter;
    gPendingOuter = (uint32_t)(uintptr_t)_ReturnAddress();
    oSubmit(self, edx, prim, fmt, count, verts);
    gPendingOuter = prev;
}

// The shared boundary machine, driven by whichever marker owns the session.
// NO I/O here, ever - the file write lives in WriteCloseout(), called at
// PreAppShutdown (review finding 1).
static void Boundary()
{
    if (gBegun && !gDone)
    {
        ++gClearsSinceBegin;
        if (!gArmed)
        {
            // City latch pending: burn the skip boundaries so the loading
            // screen and the first camera settle are not the capture.
            if (gSkipLeft > 0) { --gSkipLeft; }
            if (gSkipLeft == 0)
            {
                gArmed = true;
                gFrame = 0;
                gCallsThisFrame = 0;
            }
        }
        else
        {
            ++gFrame;
            gCallsThisFrame = 0;
            if (--gFramesLeft == 0) { gArmed = false; gDone = true; }
        }
    }
}

void __fastcall ClearDetour(void* self, void* edx, uint32_t mask)
{
    ++gClearsTotal;
    if (gMarker == 0) { gMarker = 1; }
    if (gMarker == 1) { Boundary(); }
    oClear(self, edx, mask);
}

// cIGZGDriver::Flush (vt+0xAC) - zero-arg __thiscall, the offline notes'
// "preferred frame marker".
void __fastcall FlushDetour(void* self, void* edx)
{
    ++gFlushesTotal;
    if (gMarker == 0) { gMarker = 2; }
    if (gMarker == 2) { Boundary(); }
    oFlush(self, edx);
}

// ----------------------------------------------------------------- output
// Idempotent; called OUTSIDE any hook (PreAppShutdown). A partial capture
// (game closed mid-recording) is still written - partial data beats none.
bool WriteCloseout()
{
    if (gFlushed) { return true; }
    if (!gRec || gCount == 0) { return false; }
    FILE* f = nullptr;
    if (_wfopen_s(&f, gOutPath, L"wb") != 0 || !f) { return false; }
    // header: magic, version, record count, total driver calls seen
    // v2 = the Rec carries `outer` (the SubmitPrimitive caller). v1 files
    // have no such field; the decoder branches on this number.
    uint32_t hdr[4] = { 0x50414347u /*'GCAP'*/, 2u, gCount, gCallsTotal };
    fwrite(hdr, sizeof(hdr), 1, f);
    fwrite(gRec, sizeof(Rec), gCount, f);
    fclose(f);
    gFlushed = true;
    return true;
}

// ------------------------------------------------------------------ arming
// frames: how many Clear() boundaries to record. 1 or 2 is plenty.
// Returns nullptr when the hooks are armed (capture still waits for Begin());
// otherwise a static reason string, so the wrapper's refusal log names the
// cause - a probe that guesses is worse than no probe.
const char* Install(uint32_t frames, uint32_t maxRecords, const wchar_t* outPath)
{
    if (gDone || gInstalled) { return "already installed"; }
    if (frames == 0)         { return "zero frames requested"; }
    if ((uintptr_t)GetModuleHandleW(nullptr) != 0x00400000)
    {
        return "module base relocated";
    }

    // Positive control on the TARGET, not on ourselves: the byte at
    // DrawArrays must still be `push ecx` (0x51), DrawElements must still
    // be `sub esp,0xC` (0x83 0xEC 0x0C), and Clear must still open with its
    // measured prologue (56 8B F1 8B 4E 10, dumped from the exe 2026-08-24).
    // If the exe ever moves, we refuse.
    const uint8_t* a = reinterpret_cast<const uint8_t*>(kDrawArrays);
    const uint8_t* e = reinterpret_cast<const uint8_t*>(kDrawElements);
    const uint8_t* c = reinterpret_cast<const uint8_t*>(kClear);
    static const uint8_t kClearProlog[6] = { 0x56, 0x8B, 0xF1, 0x8B, 0x4E, 0x10 };
    static const uint8_t kSubmitProlog[6] = { 0x8B, 0x54, 0x24, 0x10, 0x56, 0x52 };
    static const uint8_t kFlushProlog[6] = { 0x83, 0xEC, 0x08, 0x53, 0x55, 0x56 };
    if (memcmp(reinterpret_cast<const void*>(kFlush),
            kFlushProlog, sizeof(kFlushProlog)) != 0)
    {
        return "Flush prologue mismatch";
    }
    if (memcmp(reinterpret_cast<const void*>(kSubmitPrimitive),
            kSubmitProlog, sizeof(kSubmitProlog)) != 0)
    {
        return "SubmitPrimitive prologue mismatch";
    }
    if (a[0] != 0x51) { return "DrawArrays prologue mismatch"; }
    if (!(e[0] == 0x83 && e[1] == 0xEC && e[2] == 0x0C))
    {
        return "DrawElements prologue mismatch";
    }
    if (memcmp(c, kClearProlog, sizeof(kClearProlog)) != 0)
    {
        return "Clear prologue mismatch";
    }

    gCap = maxRecords ? maxRecords : 200000u;          // 200k * 68B = 13.6 MB
    gRec = static_cast<Rec*>(::calloc(gCap, sizeof(Rec)));
    if (!gRec) { gCap = 0; return "record buffer alloc failed"; }
    lstrcpynW(gOutPath, outPath, MAX_PATH);

    // Any failure past the alloc frees the buffer, so a refusal leaves no
    // 13.6 MB leak behind (review 2026-08-24, finding 8).
    struct Bail
    {
        bool armed = false;
        ~Bail() { if (!armed) { ::free(gRec); gRec = nullptr; gCap = 0; } }
    } bail;

    // Review finding 2: without this, GpuCap armed ALONE silently no-ops -
    // every MH_CreateHook returns MH_ERROR_NOT_INITIALIZED.
    const MH_STATUS init = MH_Initialize();
    if (init != MH_OK && init != MH_ERROR_ALREADY_INITIALIZED)
    {
        return "MinHook init failed";
    }

    if (MH_CreateHook((void*)kDrawArrays,   &DrawArraysDetour,
                      reinterpret_cast<void**>(&oDrawArrays))   != MH_OK) { return "hook DrawArrays"; }
    if (MH_CreateHook((void*)kDrawElements, &DrawElementsDetour,
                      reinterpret_cast<void**>(&oDrawElements)) != MH_OK) { return "hook DrawElements"; }
    if (MH_CreateHook((void*)kClear,        &ClearDetour,
                      reinterpret_cast<void**>(&oClear))        != MH_OK) { return "hook Clear"; }
    if (MH_CreateHook((void*)kSubmitPrimitive, &SubmitPrimitiveDetour,
                      reinterpret_cast<void**>(&oSubmit))       != MH_OK) { return "hook SubmitPrimitive"; }
    if (MH_CreateHook((void*)kFlush,        &FlushDetour,
                      reinterpret_cast<void**>(&oFlush))        != MH_OK) { return "hook Flush"; }
    // Enable results MUST be checked (review finding 1): a half-enabled set
    // - draw doors live, Clear dead - would count CallsSeen into the
    // hundreds of thousands while never arming, and the closeout's positive
    // control would then adjudicate a pure arming failure as a substantive
    // negative result.
    if (MH_EnableHook((void*)kDrawArrays)   != MH_OK) { return "enable DrawArrays"; }
    if (MH_EnableHook((void*)kDrawElements) != MH_OK) { return "enable DrawElements"; }
    if (MH_EnableHook((void*)kClear)        != MH_OK) { return "enable Clear"; }
    if (MH_EnableHook((void*)kSubmitPrimitive) != MH_OK) { return "enable SubmitPrimitive"; }
    if (MH_EnableHook((void*)kFlush)        != MH_OK) { return "enable Flush"; }

    gFramesLeft  = frames;
    gInstalled   = true;
    bail.armed   = true;
    return nullptr;
}

// The city latch: called at PostCityInit. Recording starts after `skip` more
// Clear boundaries pass, so the captured frames are the live city view, not
// the loading screen. Idempotent - only the first call latches.
bool Begin(uint32_t skip)
{
    if (!gInstalled || gBegun || gDone) { return false; }
    gSkipLeft = skip ? skip : 1;
    gBegun    = true;
    gClearsSinceBegin = 0;
    // THE MARKER IS CHOSEN AFTER THE LATCH, NOT AT FIRST-EVER FIRE.
    // Measured 2026-08-24: Clear fires freely during boot/menus/region but
    // goes nearly silent inside the city view, while Flush runs every frame
    // (609 vs 2316 in one session, most Clears pre-city). Picking the marker
    // at the first fire anywhere therefore latched onto the one that stops
    // firing exactly when the capture begins - 31 s in-city produced zero
    // counted boundaries. Resetting here makes the session's own in-city
    // behaviour choose the marker.
    gMarker = 0;
    return true;
}

// City EXIT (PreCityShutdown) - review 2026-08-24 finding 3: without this,
// a player leaving the city mid-skip lets the countdown finish on the REGION
// screen and the capture records region frames while every log line claims
// "the live city view". Two cases:
//   still skipping  -> un-latch; the next PostCityInit re-latches fresh.
//   mid-recording   -> finalize with what was captured; every recorded frame
//                      so far IS a city frame, so the partial data is honest.
// Returns: 0 = nothing to do, 1 = re-latched (was skipping), 2 = finalized.
int CityExit()
{
    if (!gInstalled || gDone || !gBegun) { return 0; }
    if (gArmed)
    {
        gArmed = false;
        gDone  = true;
        return 2;
    }
    gBegun    = false;
    gSkipLeft = 0;
    // gClearsSinceBegin is deliberately NOT reset here: the wrapper logs it
    // immediately after this call, and zeroing it made every exit report
    // "0 boundaries" regardless of what actually happened - a reporting
    // artifact that reads exactly like a dead hook (2026-08-24). Begin()
    // owns the reset.
    return 1;
}

uint32_t ClearsSinceBegin() { return gClearsSinceBegin; }
uint32_t ClearsTotal()      { return gClearsTotal; }
uint32_t FlushesTotal()     { return gFlushesTotal; }
int      MarkerUsed()       { return gMarker; }

bool Installed() { return gInstalled; }

// gCallsTotal is the POSITIVE CONTROL. If a capture returns zero balloon-sized
// quads but gCallsTotal is in the thousands, the null is real and the balloon
// is not drawn through cIGZGDriver at all (see the failure-mode note in the
// lane report). If gCallsTotal is 0, the probe never saw the driver and the
// null means nothing.
uint32_t CallsSeen()      { return gCallsTotal; }
uint32_t RecordsUsed()    { return gCount; }
uint32_t FramesCaptured() { return gFrame; }

} // namespace GdCap
