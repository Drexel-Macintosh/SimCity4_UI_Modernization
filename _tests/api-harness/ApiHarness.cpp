// ApiHarness - the cIUIScaleInfo contract, checked from OUTSIDE the DLL.
//
// Built against nothing of ours but the PUBLIC header (api/cIUIScaleInfo.h) and
// the gzcom-dll interfaces, exactly as another plugin author would build. Loads
// SC4UIScale.dll from a throwaway tree, takes its director the way the game
// does (GZDllGetGZCOMDirector), and asks it what the game's COM would ask:
// which class IDs it registers, and for the object behind ours.
//
// The host is not SimCity 4, so the DLL's version gate refuses to scale - which
// makes this the "unsupported build" row of the contract: the class must still
// be registered and must answer 1.0 / manual / region 1.0.
//
// Usage: ApiHarness.exe <path to SC4UIScale.dll> <expected version, hex>
// Exit 0 = every check passed; 1 = a check failed; 2 = could not run.
// Run by _tests/Test-UIScaleInfoApi.ps1, which also runs the mutation control.

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <cstdio>
#include <cstdlib>

#include "cIGZCOMDirector.h"
#include "cIUIScaleInfo.h"

namespace
{
	int gFailures = 0;

	void Check(bool ok, const char* what)
	{
		std::printf("  %s  %s\n", ok ? "PASS" : "FAIL", what);
		if (!ok) { gFailures++; }
	}

	struct EnumCtx
	{
		int ours = 0;
		int total = 0;
	};

	void OnClass(uint32_t clsid, uint32_t, void* ctx)
	{
		EnumCtx* c = static_cast<EnumCtx*>(ctx);
		c->total++;
		if (clsid == GZCLSID_cIUIScaleInfo) { c->ours++; }
	}
}

int main(int argc, char** argv)
{
	if (argc < 3)
	{
		std::printf("usage: ApiHarness <SC4UIScale.dll> <expected version hex>\n");
		return 2;
	}
	const uint32_t wantVersion = static_cast<uint32_t>(std::strtoul(argv[2], nullptr, 16));

	HMODULE dll = LoadLibraryA(argv[1]);
	if (!dll)
	{
		std::printf("could not load %s (error %lu)\n", argv[1], GetLastError());
		return 2;
	}
	using GetDirFn = cIGZCOMDirector* (*)();
	GetDirFn getDir = reinterpret_cast<GetDirFn>(GetProcAddress(dll, "GZDllGetGZCOMDirector"));
	if (!getDir)
	{
		std::printf("GZDllGetGZCOMDirector is not exported\n");
		return 2;
	}
	cIGZCOMDirector* dir = getDir();   // runs the director's constructor
	if (!dir)
	{
		std::printf("the DLL returned no director\n");
		return 2;
	}

	std::printf("cIUIScaleInfo contract (CLSID 0x%08X, IID 0x%08X):\n",
		GZCLSID_cIUIScaleInfo, GZIID_cIUIScaleInfo);

	// What the game does right after loading a plugin: enumerate its classes.
	EnumCtx ec;
	dir->EnumClassObjects(OnClass, &ec);
	Check(ec.ours == 1, "the director registers the CLSID exactly once");

	// What another DLL's GetClassObject reaches through the game's registry.
	cIUIScaleInfo* p = nullptr;
	const bool got = dir->GetClassObject(GZCLSID_cIUIScaleInfo, GZIID_cIUIScaleInfo,
		reinterpret_cast<void**>(&p));
	Check(got && p != nullptr, "GetClassObject(CLSID, IID) hands out the object");
	if (!got || !p)
	{
		std::printf("%d check(s) failed\n", gFailures);
		return 1;
	}

	const uint32_t v = p->GetModVersion();
	std::printf("  ....  GetModVersion = 0x%06X (want 0x%06X)\n", v, wantVersion);
	Check(v == wantVersion, "GetModVersion matches the DLL's version string");
	const float f = p->GetUIScaleFactor();
	std::printf("  ....  GetUIScaleFactor = %.3f\n", f);
	Check(f == 1.0f, "an unsupported host answers UI factor 1.0");
	Check(!p->IsAutoScale(), "an unsupported host answers IsAutoScale false");
	const float r = p->GetRegionMapScale();
	std::printf("  ....  GetRegionMapScale = %.3f\n", r);
	Check(r == 1.0f, "an unpatched region map answers 1.0");

	// COM identity rules.
	cIGZUnknown* unk = nullptr;
	Check(p->QueryInterface(GZIID_cIGZUnknown, reinterpret_cast<void**>(&unk))
		&& unk == static_cast<cIGZUnknown*>(p), "QueryInterface(cIGZUnknown) is the same object");
	if (unk) { unk->Release(); }
	void* wrong = reinterpret_cast<void*>(1);
	Check(!p->QueryInterface(GZIID_cIUIScaleInfo ^ 1u, &wrong) && wrong == nullptr,
		"QueryInterface(unknown IID) is refused and nulls the out pointer");
	void* wrong2 = nullptr;
	Check(!dir->GetClassObject(GZCLSID_cIUIScaleInfo, GZIID_cIUIScaleInfo ^ 1u, &wrong2)
		&& wrong2 == nullptr, "GetClassObject(CLSID, unknown IID) is refused");
	void* wrong3 = nullptr;
	Check(!dir->GetClassObject(GZCLSID_cIUIScaleInfo ^ 1u, GZIID_cIUIScaleInfo, &wrong3)
		&& wrong3 == nullptr, "GetClassObject(unknown CLSID) is refused");

	// Reference counting, and the static-lifetime promise: releasing more than
	// was ever added must neither crash nor free the object other DLLs hold.
	const uint32_t a = p->AddRef();
	const uint32_t b = p->Release();
	Check(a == b + 1, "AddRef/Release count");
	for (int i = 0; i < 8; i++) { p->Release(); }
	Check(p->GetModVersion() == v, "the object survives over-release");

	// A second lookup is the same object (one static instance).
	cIUIScaleInfo* p2 = nullptr;
	dir->GetClassObject(GZCLSID_cIUIScaleInfo, GZIID_cIUIScaleInfo, reinterpret_cast<void**>(&p2));
	Check(p2 == p, "every lookup returns the one static object");
	if (p2) { p2->Release(); }

	std::printf("%s: %d check(s) failed\n", gFailures ? "FAIL" : "PASS", gFailures);
	// No FreeLibrary: the game never unloads a plugin either.
	return gFailures ? 1 : 0;
}
