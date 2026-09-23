// W-FlatRect: does MSVC, fed the Mac DECLARATION order of cIGZWinFlatRect,
// emit the vtable order the shipped exe has at 0x00AE2050?
// Build: msvc_order.cmd  -> msvc_order.asm ; read ??_7cFR@@6B@ (the vftable).
// Methods are declared exactly in Mac slot order (SimCity4.gdt.json
// vftable_cIGZWinFlatRect, slots 0..19).
#include <stdint.h>
struct cRZRect { int32_t l, t, r, b; };
struct cIGZWin;

struct cIGZWinFlatRect {
    virtual bool QueryInterface(uint32_t, void**) = 0;                    // 0
    virtual uint32_t AddRef() = 0;                                         // 1
    virtual uint32_t Release() = 0;                                        // 2
    virtual cIGZWin* AsIGZWin() = 0;                                       // 3
    virtual void SetFillColor(uint8_t, uint8_t, uint8_t) = 0;              // 4  Mac
    virtual void GetFillColor(uint8_t&, uint8_t&, uint8_t&) const = 0;     // 5  Mac
    virtual void SetOutlineColor(long, uint8_t, uint8_t, uint8_t) = 0;     // 6  Mac
    virtual void GetOutlineColor(long, uint8_t&, uint8_t&, uint8_t&) const = 0; // 7 Mac
    virtual void SetOutlineColor(uint8_t, uint8_t, uint8_t) = 0;           // 8  Mac
    virtual bool SetOutlineFlags(long) = 0;                                // 9  Mac
    virtual long GetOutlineFlags() = 0;                                    // 10 Mac
    virtual bool GetOutlineFlag(long) = 0;                                 // 11 Mac
    virtual void SetFillColor(unsigned long) = 0;                          // 12 Mac
    virtual unsigned long GetFillColor() const = 0;                        // 13 Mac
    virtual void SetOutlineColor(unsigned long) = 0;                       // 14 Mac
    virtual void SetOutlineColors(unsigned long, unsigned long, unsigned long, unsigned long) = 0; // 15
    virtual void GetOutlineColors(unsigned long&, unsigned long&, unsigned long&, unsigned long&) const = 0; // 16
    virtual bool AutoSize(const cRZRect&) = 0;                             // 17
    virtual bool SetSizeMode(long) = 0;                                    // 18
    virtual long GetSizeMode() = 0;                                        // 19
};

// Each body is distinct so /OPT:ICF cannot fold them (we only read the .asm anyway).
struct cFR : cIGZWinFlatRect {
    int v;
    bool QueryInterface(uint32_t, void**) { return v == 0; }
    uint32_t AddRef() { return 1u + v; }
    uint32_t Release() { return 2u + v; }
    cIGZWin* AsIGZWin() { return (cIGZWin*)(intptr_t)(3 + v); }
    void SetFillColor(uint8_t, uint8_t, uint8_t) { v = 4; }
    void GetFillColor(uint8_t& a, uint8_t&, uint8_t&) const { a = 5; }
    void SetOutlineColor(long, uint8_t, uint8_t, uint8_t) { v = 6; }
    void GetOutlineColor(long, uint8_t& a, uint8_t&, uint8_t&) const { a = 7; }
    void SetOutlineColor(uint8_t, uint8_t, uint8_t) { v = 8; }
    bool SetOutlineFlags(long) { v = 9; return true; }
    long GetOutlineFlags() { return 10 + v; }
    bool GetOutlineFlag(long) { return v == 11; }
    void SetFillColor(unsigned long) { v = 12; }
    unsigned long GetFillColor() const { return 13ul + v; }
    void SetOutlineColor(unsigned long) { v = 14; }
    void SetOutlineColors(unsigned long, unsigned long, unsigned long, unsigned long) { v = 15; }
    void GetOutlineColors(unsigned long& a, unsigned long&, unsigned long&, unsigned long&) const { a = 16; }
    bool AutoSize(const cRZRect&) { v = 17; return true; }
    bool SetSizeMode(long) { v = 18; return true; }
    long GetSizeMode() { return 19 + v; }
};

cIGZWinFlatRect* make() { return new cFR(); }
