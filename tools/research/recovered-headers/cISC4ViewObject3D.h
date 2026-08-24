#pragma once
// ============================================================================
// cISC4ViewObject3D - RECOVERED INTERFACE, NOT A VENDOR HEADER
// ============================================================================
// No official or community header for this interface exists. This layout was
// recovered statically from SimCity 4 Deluxe 1.1.641.0 (ImageBase 0x00400000)
// on 2026-08-24, closing register item #12
// (research/UNKNOWNS-AND-NEXT-TARGETS.md).
//
// HOW IT WAS DERIVED (three independent lines of evidence agreeing):
//
//  1. VTABLE INTERSECTION. The five classes captured live through the
//     AddViewObject hook on 2026-08-17 (vtables 0x00AB4480, 0x00AB39D0,
//     0x00AB42F8, 0x00AB4624, 0x00AA8314) were dumped and intersected.
//     THREE OF THE FIVE END AT EXACTLY FIVE SLOTS - the interface cannot be
//     wider than 5, and every slot below 5 is overridden by at least one class.
//
//  2. THE RENDERER'S OWN CALLS. Four per-pass walkers iterate the renderer's
//     sorted object lists and call [vt+0x0C](drawCtx) on every node - that
//     fixes Draw at +0x0C and fixes its single argument.
//
//  3. THE PICK PATH. The renderer's pick calls [vt+0x10](&p0, &p1, drawCtx,
//     outFloat) on the terrain object, which FindViewObject pointer-compares
//     against registered view objects - proving the terrain IS a view object
//     and fixing Pick's four-argument shape. The SOLE Pick override
//     (0x00752700, the terrain view class) forwards its four arguments plus a
//     trailing `push 0` into a member's slot 3, which matches the vendor
//     signature cISTETerrainView::Pick(v, v, SC4DrawContext*, float*, bool)
//     exactly.
//
// BONUS, from the same override: GZIID_cISTETerrainView = 0x6771477D
// (re-verified independently as an imm32 at 0x00752745, inside 0x00752700).
//
// STATUS: static evidence only, no game launch. Names of the two virtuals are
// inferred from behaviour and from the matching vendor terrain signature, NOT
// from a symbol or string. Treat the SHAPE as pinned and the NAMES as good
// guesses.
//
// NOT DETERMINED: this interface's own GZIID. Every capture reached these
// objects through AddViewObject (cISC43DRender vt+0x80 = 0x007C5D90) rather
// than through a QueryInterface, so no iid constant was ever pushed on the
// observed paths.
// ============================================================================

#include <cstdint>

class cIGZUnknown;      // slots 0..2: QueryInterface / AddRef / Release
struct SC4DrawContext;  // opaque here; the renderer threads it through unchanged
class cS3DVector3;

class cISC4ViewObject3D /* : public cIGZUnknown */
{
public:
    // --- slots 0-2: cIGZUnknown (QueryInterface, AddRef, Release) ---

    // slot 3, vtable offset +0x0C.
    // Called by all four of the renderer's per-pass list walkers, once per
    // node, with the frame's draw context. This is the whole drawing contract:
    // an object registered with AddViewObject gets exactly this call.
    virtual void Draw(SC4DrawContext* pDrawContext) = 0;

    // slot 4, vtable offset +0x10.
    // Ray pick. p0/p1 are the ray endpoints in world space; the float* receives
    // the hit distance/parameter. Only ONE class in the image overrides this
    // (the terrain view, 0x00752700); the other view objects inherit a base
    // body, which is why terrain is the only pickable view object on this path.
    virtual bool Pick(cS3DVector3 const& p0,
                      cS3DVector3 const& p1,
                      SC4DrawContext*    pDrawContext,
                      float*             pOutDistance) = 0;
};

// ============================================================================
// RENDERER BOOKKEEPING (decoded alongside, same session)
// ============================================================================
// The renderer keeps FOUR sorted, sentinel-terminated doubly-linked lists, one
// per draw pass, on itself:
//
//      [renderer + 0x188]  ->  pass 3
//      [renderer + 0x18C]  ->  pass 5
//      [renderer + 0x190]  ->  pass 0
//      [renderer + 0x194]  ->  pass 2
//
// Node layout: { next, prev, cISC4ViewObject3D* obj, uint32_t sortKey }.
// Insertion keeps each list ASCENDING BY sortKey, and ascending sortKey IS
// draw order within a pass (lower draws first / behind).
//
// Frame order across passes:   0  ->  2  ->  <scene>  ->  3  ->  5
//
// So an object registered into pass 0 or 2 draws BEFORE the scene, and pass 3
// or 5 draws AFTER it - which is the lever for anything that must composite
// over the city. The list a given object lands in is chosen by the pass
// argument at AddViewObject time, not by the object's class.
// ============================================================================
