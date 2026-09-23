// Verifier's own MSVC layout probe (independent of the finder's msvc_order.cpp).
// Compiled with /d1reportSingleClassLayout, which makes cl.exe PRINT each
// class's vftable in slot order - no asm reading needed.
// Declarations are the MAC (GCC, declaration-order) vtable of
// vftable_cIGZWinFlatRect from SimCity4.gdt.json, slots 0..19, with the
// Itanium manglings decoded to argument types.
typedef unsigned char uchar;
typedef unsigned long ulong;
struct cRZRect { long l, t, r, b; };
struct cRZColor { uchar r, g, b, a; };
struct cRZPoint { long x, y; };
struct cIGZWin;

struct VerFR {
    virtual bool QueryInterface(ulong riid, void** ppv) = 0;      // 0
    virtual ulong AddRef() = 0;                                  // 1
    virtual ulong Release() = 0;                                 // 2
    virtual cIGZWin* AsIGZWin() = 0;                             // 3
    virtual bool SetFillColor(uchar r, uchar g, uchar b) = 0;    // 4  _ZN..SetFillColorEhhh
    virtual bool GetFillColor(uchar& r, uchar& g, uchar& b) const = 0; // 5 NK..GetFillColorERhS0_S0_
    virtual bool SetOutlineColor(long e, uchar r, uchar g, uchar b) = 0; // 6 SetOutlineColorElhhh
    virtual bool GetOutlineColor(long e, uchar& r, uchar& g, uchar& b) const = 0; // 7
    virtual bool SetOutlineColor(uchar r, uchar g, uchar b) = 0; // 8  SetOutlineColorEhhh
    virtual bool SetOutlineFlags(long f) = 0;                    // 9
    virtual long GetOutlineFlags() = 0;                          // 10
    virtual bool GetOutlineFlag(long f) = 0;                     // 11
    virtual bool SetFillColor(ulong c) = 0;                      // 12 SetFillColorEm
    virtual ulong GetFillColor() const = 0;                      // 13 NK..GetFillColorEv
    virtual bool SetOutlineColor(ulong c) = 0;                   // 14 SetOutlineColorEm
    virtual bool SetOutlineColors(ulong a, ulong b, ulong c, ulong d) = 0; // 15
    virtual bool GetOutlineColors(ulong& a, ulong& b, ulong& c, ulong& d) = 0; // 16
    virtual bool AutoSize(const cRZRect& r) = 0;                 // 17
    virtual bool SetSizeMode(long m) = 0;                        // 18
    virtual long GetSizeMode() = 0;                              // 19
};

// Mac cIGZWin 102..107 carry names only (Get,Set,Get,Set,Get,Set); the three
// overload identities are unknown on Mac.  Test: does MSVC pull interleaved
// Get/Set overloads into two groups (G,G,G,S,S,S)?  Signatures chosen from the
// exe bodies (102 raw copy to ref, 103 native getter, 104 rgb refs; 105 raw
// by-value setter, 106 native setter, 107 rgb setter) in Mac interleaving.
struct VerFill {
    virtual void pad0() = 0;
    virtual bool GetFillColor(cRZColor& c) = 0;              // Mac 102 'GetFillColor'
    virtual bool SetFillColor(cRZColor c) = 0;               // Mac 103 'SetFillColor'
    virtual ulong GetFillColor() = 0;                        // Mac 104 'GetFillColor'
    virtual void SetFillColor(ulong c) = 0;                  // Mac 105 'SetFillColor'
    virtual void GetFillColor(uchar& r, uchar& g, uchar& b) = 0; // Mac 106 'GetFillColor'
    virtual void SetFillColor(uchar r, uchar g, uchar b) = 0;    // Mac 107 'SetFillColor'
    virtual bool MakeFillColor(uchar r, uchar g, uchar b) = 0;   // Mac 108
};

// The vendored gzcom-dll cIGZWin.h band, verbatim order (lines 201-207).
struct GzcomFill {
    virtual void pad0() = 0;
    virtual bool GetFillColor(cRZColor& fillColor) = 0;
    virtual unsigned int GetFillColor() = 0;
    virtual void GetFillColor(uchar& red, uchar& green, uchar& blue) = 0;
    virtual bool SetFillColor(cRZColor const& color) = 0;
    virtual void SetFillColor(unsigned int fillColor) = 0;
    virtual void SetFillColor(uchar red, uchar green, uchar blue) = 0;
    virtual bool MakeFillColor(uchar red, uchar green, uchar blue) = 0;
};

// Far-apart overloads (the cIGZWin 53 vs 118 SetSize question): does MSVC
// still group them?
struct VerFar {
    virtual void a0() = 0;
    virtual void SetSize(long w, long h) = 0;
    virtual void a2() = 0;
    virtual void a3() = 0;
    virtual void SetSize(const cRZPoint& p) = 0;
    virtual void a5() = 0;
};

struct ImplFR : VerFR {
    bool QueryInterface(ulong, void**) { return 0; }
    ulong AddRef() { return 0; }
    ulong Release() { return 0; }
    cIGZWin* AsIGZWin() { return 0; }
    bool SetFillColor(uchar, uchar, uchar) { return 0; }
    bool GetFillColor(uchar&, uchar&, uchar&) const { return 0; }
    bool SetOutlineColor(long, uchar, uchar, uchar) { return 0; }
    bool GetOutlineColor(long, uchar&, uchar&, uchar&) const { return 0; }
    bool SetOutlineColor(uchar, uchar, uchar) { return 0; }
    bool SetOutlineFlags(long) { return 0; }
    long GetOutlineFlags() { return 0; }
    bool GetOutlineFlag(long) { return 0; }
    bool SetFillColor(ulong) { return 0; }
    ulong GetFillColor() const { return 0; }
    bool SetOutlineColor(ulong) { return 0; }
    bool SetOutlineColors(ulong, ulong, ulong, ulong) { return 0; }
    bool GetOutlineColors(ulong&, ulong&, ulong&, ulong&) { return 0; }
    bool AutoSize(const cRZRect&) { return 0; }
    bool SetSizeMode(long) { return 0; }
    long GetSizeMode() { return 0; }
};


struct ImplFill : VerFill {
    void pad0() {}
    bool GetFillColor(cRZColor&) { return 0; }
    bool SetFillColor(cRZColor) { return 0; }
    ulong GetFillColor() { return 0; }
    void SetFillColor(ulong) {}
    void GetFillColor(uchar&, uchar&, uchar&) {}
    void SetFillColor(uchar, uchar, uchar) {}
    bool MakeFillColor(uchar, uchar, uchar) { return 0; }
};
struct ImplGz : GzcomFill {
    void pad0() {}
    bool GetFillColor(cRZColor&) { return 0; }
    unsigned int GetFillColor() { return 0; }
    void GetFillColor(uchar&, uchar&, uchar&) {}
    bool SetFillColor(cRZColor const&) { return 0; }
    void SetFillColor(unsigned int) {}
    void SetFillColor(uchar, uchar, uchar) {}
    bool MakeFillColor(uchar, uchar, uchar) { return 0; }
};
struct ImplFar : VerFar {
    void a0() {}
    void SetSize(long, long) {}
    void a2() {}
    void a3() {}
    void SetSize(const cRZPoint&) {}
    void a5() {}
};
VerFill* mkFill() { return new ImplFill; }
GzcomFill* mkGz() { return new ImplGz; }
VerFar* mkFar() { return new ImplFar; }

int main() {
    ImplFR f;
    VerFR* p = &f;
    return (int)p->GetSizeMode() + sizeof(VerFill*) + sizeof(GzcomFill*) + sizeof(VerFar*);
}
