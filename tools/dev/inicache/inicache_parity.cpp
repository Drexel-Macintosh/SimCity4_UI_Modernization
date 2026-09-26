// Parity of IniCache (src/IniCache.cpp, src/IniParse.h) with the real
// profile API (audit B8, 2026-09-25). Built and run by run_inicache_parity.py.
//
// ON WINDOWS: every case below is written to a temp file and every lookup
// is asked of BOTH IniCache and GetPrivateProfileStringW / StringA / IntW -
// every section and key name in the file plus case, padding and missing
// variants, several defaults, and buffer sizes from 1 up. Any difference in
// the returned length or in the buffer is a failure. Extra .ini files named
// on the command line (the shipped ini, the starter ini) join the corpus.
//
// UNDER WINE (detected through ntdll!wine_get_version) the same comparison
// runs, but Wine is a model of Windows, not Windows: its known divergences
// (it decodes a UTF-8 BOM, Windows does not) are reported, not failed.
//
// ELSEWHERE: only IniParse.h can be built, so a golden table of the rules it
// states is checked instead. That is a model check, NOT parity; the runner
// says so and exits 2.
#include "IniParse.h"

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include "IniCache.h"
#endif

namespace
{
	struct Case { std::string name; std::string bytes; bool utf8Bom = false; };

	std::string Utf16Le(const char* ascii)
	{
		std::string s = "\xFF\xFE";
		for (const char* p = ascii; *p; ++p) { s += *p; s += '\0'; }
		return s;
	}

	std::vector<Case> BuiltInCases()
	{
		std::vector<Case> c;
		c.push_back({ "basic", "[UiSpike]\r\nScaleAll=1\r\nScaleFactor = 2.5 \r\n; comment=3\r\n[Probe]\r\nEnabled=0\r\n" });
		c.push_back({ "lf-only", "[UiSpike]\nScaleAll=1\nScaleFactor = 2.5 \n[Probe]\nEnabled=0\n" });
		c.push_back({ "cr-only", "[UiSpike]\rScaleAll=1\rScaleFactor = 2.5 \r[Probe]\rEnabled=0\r" });
		c.push_back({ "mixed-cr", "[S]\r\nA=1\rB=2\nC=3" });
		c.push_back({ "no-final-newline", "[S]\r\nk=last" });
		c.push_back({ "spaces", "  [ S ]  \r\n\t K \t=\t v \t\r\n[S2]\r\n K2 = v2 ; tail\r\n[S3]   \r\n  k3=  \r\n" });
		c.push_back({ "quotes", "[Q]\r\nD=\"dq\"\r\nS='sq'\r\nM=\"mixed'\r\nE=\"\"\r\nO=\"\r\nI=\"in\"side\"\r\nL=\"x\r\nT= \"sp\" \r\nX='\r\nY=''\r\n" });
		c.push_back({ "dupes", "[A]\r\nk=1\r\nk=2\r\n[a]\r\nk=3\r\nj=4\r\n[B]\r\n" });
		c.push_back({ "noeq", "[N]\r\nbare\r\nk=v\r\n=nameless\r\n=again\r\n[N2]\r\n=first\r\nk=after\r\n" });
		c.push_back({ "headers", "[H] ; c\r\nk=1\r\n[H2]x]\r\nk=2\r\n[Unclosed\r\nk=3\r\n[]\r\nk=4\r\n[H3]]\r\nk=5\r\n[ Pad ]\r\nk=6\r\n" });
		c.push_back({ "lead", "k=0\r\nj\r\n[L]\r\nk=1\r\n" });
		c.push_back({ "ints", "[I]\r\na=7\r\nb= 7\r\nc=+7\r\nd=-7\r\ne=0x1F\r\nf=0X1F\r\ng=0o17\r\nh=0b101\r\n"
			"i=12abc\r\nj=abc\r\nk=4294967295\r\nl=4294967296\r\nm=-2147483648\r\nn=99999999999\r\n"
			"o= 3 ; comment\r\np=\r\nq=\"5\"\r\nr=0x\r\ns=-\r\nt=0xFFFFFFFF\r\nu=1e3\r\nv=00012\r\n"
			"w=\t9\r\nx=0b\r\ny=0x-1\r\nz=- 4\r\n" });
		c.push_back({ "long", "[Long]\r\nv=" + std::string(300, 'x') + "\r\nq=\"" + std::string(40, 'y') + "\"\r\n" });
		c.push_back({ "utf8bom", "\xEF\xBB\xBF[B]\r\nk=1\r\n[C]\r\nk=2\r\n", true });
		c.push_back({ "utf8bom-blank", "\xEF\xBB\xBF\r\n[B]\r\nk=1\r\n", true });
		c.push_back({ "utf16le", Utf16Le("[U]\r\nk=wide\r\nq=\"w\"\r\n") });
		c.push_back({ "ctrlz", "[Z]\r\nk=1\x1a\r\n\x1a[Z2]\r\nk=2\r\n" });
		c.push_back({ "hash", "[X]\r\n#k=1\r\nk=2\r\n;k=3\r\n" });
		c.push_back({ "eqvalue", "[E]\r\nk=a=b\r\nk2==c\r\nk3 = = d\r\n" });
		c.push_back({ "nbsp", "[S]\r\nk=\xA0v\xA0\r\n\xA0j=2\r\n" });
		c.push_back({ "empty", "" });
		c.push_back({ "only-comments", "; nothing\r\n; here\r\n" });
		c.push_back({ "embedded-nul", std::string("[N]\r\nk=ab\0cd\r\nj=1\r\n", 20) });
		c.push_back({ "tabs-in-names", "[T]\r\nk\tx=1\r\nk x=2\r\n" });
		return c;
	}

#ifdef _WIN32
	std::string ReadAll(const char* path)
	{
		std::string s;
		FILE* f = nullptr;
		if (fopen_s(&f, path, "rb") != 0 || !f) { return s; }
		char buf[4096];
		size_t n;
		while ((n = fread(buf, 1, sizeof(buf), f)) > 0) { s.append(buf, n); }
		fclose(f);
		return s;
	}
#endif

	std::string Escape(const wchar_t* s, size_t n)
	{
		std::string o;
		for (size_t i = 0; i < n; ++i)
		{
			const unsigned c = static_cast<unsigned>(s[i]);
			if (c >= 32 && c < 127 && c != '\\') { o += static_cast<char>(c); }
			else
			{
				char b[12];
				snprintf(b, sizeof(b), "\\x%X", c);
				o += b;
			}
		}
		return o;
	}

	// ---- the golden table (every platform) --------------------------------
	int gFails = 0;

	void ExpectStr(const IniParse::File& f, const wchar_t* s, const wchar_t* k,
		const wchar_t* def, unsigned long size, const wchar_t* want, const char* why)
	{
		wchar_t buf[512];
		for (auto& c : buf) { c = L'#'; }
		const unsigned long n = IniParse::GetString(f, s, k, def, buf, size);
		const bool ok = (wcscmp(buf, want) == 0) && n == wcslen(want);
		if (!ok)
		{
			++gFails;
			printf("MODEL FAIL %s: got \"%s\" (%lu), want \"%s\"\n", why,
				Escape(buf, wcslen(buf)).c_str(), n, Escape(want, wcslen(want)).c_str());
		}
	}

	void ExpectInt(const IniParse::File& f, const wchar_t* s, const wchar_t* k,
		int def, uint32_t want, const char* why)
	{
		const uint32_t got = IniParse::GetInt(f, s, k, def);
		if (got != want)
		{
			++gFails;
			printf("MODEL FAIL %s: got %u, want %u\n", why, got, want);
		}
	}

	std::wstring Latin1(const std::string& b)
	{
		std::wstring w;
		for (unsigned char c : b) { w += static_cast<wchar_t>(c); }
		return w;
	}

	void GoldenChecks()
	{
		using IniParse::Parse;
		const IniParse::File basic = Parse(Latin1(BuiltInCases()[0].bytes));
		ExpectStr(basic, L"UiSpike", L"ScaleFactor", L"", 64, L"2.5", "value trimmed");
		ExpectStr(basic, L"uispike", L"SCALEALL", L"", 64, L"1", "names fold case");
		ExpectStr(basic, L" UiSpike ", L" ScaleAll ", L"", 64, L"1", "query trimmed");
		ExpectStr(basic, L"UiSpike", L"Missing", L"dflt   ", 64, L"dflt", "default loses trailing spaces");
		ExpectStr(basic, L"UiSpike", L"Missing", L"   ", 64, L" ", "all-space default keeps one");
		ExpectStr(basic, L"UiSpike", L"; comment", L"d", 64, L"3", "a ; line is a key");
		ExpectStr(basic, L"UiSpike", L"ScaleFactor", L"", 3, L"2.", "truncated to size-1");
		ExpectStr(basic, L"UiSpike", L"ScaleFactor", L"", 1, L"", "size 1 holds only the NUL");
		const IniParse::File q = Parse(Latin1(BuiltInCases()[6].bytes));
		ExpectStr(q, L"Q", L"D", L"", 64, L"dq", "double quotes removed");
		ExpectStr(q, L"Q", L"S", L"", 64, L"sq", "single quotes removed");
		ExpectStr(q, L"Q", L"M", L"", 64, L"\"mixed'", "unmatched quotes kept");
		ExpectStr(q, L"Q", L"E", L"x", 64, L"", "empty quotes read empty");
		ExpectStr(q, L"Q", L"O", L"", 64, L"\"", "a lone quote is kept");
		ExpectStr(q, L"Q", L"I", L"", 64, L"in\"side", "only the outer pair goes");
		ExpectStr(q, L"Q", L"D", L"", 3, L"dq", "quotes go first, then truncation (real Windows; Wine drops one more)");
		const IniParse::File d = Parse(Latin1(BuiltInCases()[7].bytes));
		ExpectStr(d, L"A", L"k", L"", 64, L"1", "first key wins");
		ExpectStr(d, L"a", L"j", L"none", 64, L"none", "only the first section is searched");
		const IniParse::File ne = Parse(Latin1(BuiltInCases()[8].bytes));
		ExpectStr(ne, L"N", L"bare", L"dflt", 64, L"dflt", "no '=' reads as absent");
		const IniParse::File h = Parse(Latin1(BuiltInCases()[9].bytes));
		ExpectStr(h, L"H", L"k", L"", 64, L"1", "text after ']' ignored");
		ExpectStr(h, L"H2]x", L"k", L"", 64, L"2", "name runs to the last ']'");
		ExpectStr(h, L"H2]x", L"[Unclosed", L"d", 64, L"d", "unclosed header is a bare key");
		ExpectStr(h, L"Unclosed", L"k", L"d", 64, L"d", "unclosed header opens no section");
		ExpectStr(h, L"H3]", L"k", L"", 64, L"5", "a doubled ']' stays in the name");
		ExpectStr(h, L"Pad", L"k", L"d", 64, L"6", "a padded header name is trimmed");
		ExpectStr(h, L"", L"k", L"d", 64, L"d", "'[]' is nameless, but the lead section answers first");
		const IniParse::File l = Parse(Latin1(BuiltInCases()[10].bytes));
		ExpectStr(l, L"", L"k", L"d", 64, L"0", "an empty section name reaches the lead keys");
		ExpectStr(l, L"  ", L"j", L"d", 64, L"d", "a key line with no '=' reads as absent");
		const IniParse::File cr = Parse(Latin1(BuiltInCases()[3].bytes));
		ExpectStr(cr, L"S", L"A", L"", 64, L"1", "a lone CR ends a line");
		ExpectStr(cr, L"S", L"B", L"", 64, L"2", "... so the next key is its own line");
		ExpectStr(cr, L"S", L"C", L"", 64, L"3", "the last line needs no newline");
		const IniParse::File bom = Parse(Latin1(BuiltInCases()[13].bytes));
		ExpectStr(bom, L"B", L"k", L"lost", 64, L"lost", "a UTF-8 BOM hides the first header");
		ExpectStr(bom, L"C", L"k", L"", 64, L"2", "later sections survive the BOM");
		const IniParse::File in = Parse(Latin1(BuiltInCases()[11].bytes));
		ExpectInt(in, L"I", L"a", 5, 7u, "int");
		ExpectInt(in, L"I", L"c", 5, 7u, "plus sign");
		ExpectInt(in, L"I", L"d", 5, static_cast<uint32_t>(-7), "minus sign");
		ExpectInt(in, L"I", L"e", 5, 31u, "0x prefix");
		ExpectInt(in, L"I", L"f", 5, 0u, "0X is not a prefix");
		ExpectInt(in, L"I", L"g", 5, 15u, "0o prefix");
		ExpectInt(in, L"I", L"h", 5, 5u, "0b prefix");
		ExpectInt(in, L"I", L"i", 5, 12u, "stops at the first non-digit");
		ExpectInt(in, L"I", L"j", 5, 0u, "no digits reads 0, not the default");
		ExpectInt(in, L"I", L"l", 5, 0u, "wraps at 32 bits");
		ExpectInt(in, L"I", L"o", 5, 3u, "inline comment ignored by the int read");
		ExpectInt(in, L"I", L"p", 5, 5u, "empty value returns the default");
		ExpectInt(in, L"I", L"q", 5, 5u, "quotes removed before the int read");
		ExpectInt(in, L"I", L"missing", -3, static_cast<uint32_t>(-3), "absent returns the default");
	}

#ifdef _WIN32
	// ---- parity with the real API (Windows, or Wine as a model) -----------
	bool gWine = false;
	long long gCompared = 0;
	int gMismatch = 0;
	int gWineOnly = 0;

	std::wstring TempDir()
	{
		wchar_t t[MAX_PATH] = {};
		GetTempPathW(MAX_PATH, t);
		std::wstring d = std::wstring(t) + L"inicache-parity\\";
		CreateDirectoryW(d.c_str(), nullptr);
		return d;
	}

	void WriteBytes(const std::wstring& path, const std::string& b)
	{
		const HANDLE h = CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr,
			CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
		DWORD w = 0;
		if (!b.empty()) { WriteFile(h, b.data(), static_cast<DWORD>(b.size()), &w, nullptr); }
		CloseHandle(h);
	}

	std::string Narrow(const std::wstring& w)
	{
		const int n = WideCharToMultiByte(CP_ACP, 0, w.c_str(), -1, nullptr, 0, nullptr, nullptr);
		std::string s(n > 0 ? static_cast<size_t>(n) : 1, '\0');
		WideCharToMultiByte(CP_ACP, 0, w.c_str(), -1, &s[0], n, nullptr, nullptr);
		s.resize(strlen(s.c_str()));
		return s;
	}

	int gCaseMismatch = 0;   // reset per case, so every case shows its first few
	long long gWaived = 0;   // mismatches in the waived query classes (see Compare)

	void Mismatch(const Case& c, const std::string& what)
	{
		if (gWine && c.utf8Bom)
		{
			++gWineOnly;   // Wine decodes a UTF-8 BOM; Windows does not
			return;
		}
		// A NUL byte inside a value: Windows' return count runs past it, the
		// cache stops at it; a caller reading the text sees "ab" from both.
		// No ini the DLL reads is written with NULs (waived, 2026-09-25).
		if (c.name == "embedded-nul") { ++gWaived; return; }
		++gMismatch;
		if (++gCaseMismatch <= 6) { printf("MISMATCH [%s] %s\n", c.name.c_str(), what.c_str()); }
	}

	// What a caller can observe: the return value, the string through its
	// terminator, and that nothing was written past `size` or before the
	// buffer (guard cells). The bytes between the terminator and `size` are
	// unspecified - real Windows leaves residue there - so they are not
	// compared. (A full-buffer memcmp passed under Wine and failed on Windows
	// on that residue alone, 2026-09-25.)
	template <typename C>
	bool SameAsCaller(const C* a, unsigned long ra, const C* b, unsigned long rb,
		unsigned long size, C guard)
	{
		if (ra != rb) { return false; }
		if (a[-1] != guard) { return false; }
		for (unsigned long i = size; i < 512; ++i) { if (a[i] != guard) { return false; } }
		if (size == 0) { return true; }
		const unsigned long n = ra < size ? ra : size - 1;
		for (unsigned long i = 0; i <= n; ++i) { if (a[i] != b[i]) { return false; } }
		return true;
	}

	void Compare(const Case& c, const std::wstring& path, const IniParse::File& model)
	{
		std::vector<std::wstring> secs, keys;
		auto add = [](std::vector<std::wstring>& v, const std::wstring& s)
		{
			for (const std::wstring& x : v) { if (x == s) { return; } }
			v.push_back(s);
		};
		for (const IniParse::Section& s : model.sections)
		{
			add(secs, s.name);
			for (const IniParse::Key& k : s.keys) { add(keys, k.name); }
		}
		const size_t ns = secs.size(), nk = keys.size();
		for (size_t i = 0; i < ns; ++i)
		{
			std::wstring up = secs[i], lo = secs[i];
			for (auto& ch : up) { ch = static_cast<wchar_t>(towupper(ch)); }
			for (auto& ch : lo) { ch = static_cast<wchar_t>(towlower(ch)); }
			add(secs, up); add(secs, lo); add(secs, L" " + secs[i] + L"\t");
		}
		for (size_t i = 0; i < nk; ++i)
		{
			std::wstring up = keys[i];
			for (auto& ch : up) { ch = static_cast<wchar_t>(towupper(ch)); }
			add(keys, up); add(keys, L"\t" + keys[i] + L" ");
		}
		add(secs, L"MissingSection");
		add(keys, L"MissingKey");
		// The shipped inis carry ~100 keys: a smaller matrix keeps them fast.
		const bool big = nk > 40;
		const std::vector<const wchar_t*> defs = big
			? std::vector<const wchar_t*>{ L"", L"\"q\"" }
			: std::vector<const wchar_t*>{ L"", L"dflt   ", L"   ", L"\"q\"", L"'q" };
		const std::vector<unsigned long> sizes = big
			? std::vector<unsigned long>{ 1, 3, 30, 512 }
			: std::vector<unsigned long>{ 1, 2, 3, 4, 8, 30, 512 };
		const std::string pathA = Narrow(path);
		for (const std::wstring& s : secs)
		{
			const std::string sA = Narrow(s);
			for (const std::wstring& k : keys)
			{
				const std::string kA = Narrow(k);
				// WAIVED QUERY CLASSES (measured on real Windows, 2026-09-25):
				// IniCache follows Wine, not Windows, for an empty section
				// name, a key beginning with ';', a tab inside a name, and a
				// default with trailing blanks or a leading quote. The DLL
				// never issues such a query - tools/dev/inicache/
				// check_call_sites.py proves it for every call site - so a
				// mismatch there is counted and printed, not failed.
				const bool nameWaived = s.empty() || (!k.empty() && k[0] == L';')
					|| s.find(L'\t') != std::wstring::npos || k.find(L'\t') != std::wstring::npos
					|| s.find(L']') != std::wstring::npos;
				for (const wchar_t* d : defs)
				{
					const std::string dA = Narrow(d);
					const size_t dl = wcslen(d);
					const bool defWaived = dl > 0 && (d[dl - 1] == L' ' || d[dl - 1] == L'\t'
						|| d[0] == L'"' || d[0] == L'\'');
					const bool waived = nameWaived || defWaived;
					for (unsigned long size : sizes)
					{
						// One guard cell each side: Wine writes buffer[-1] for a
						// value of "" read into size 1 (an out-of-bounds write
						// in PROFILE_CopyEntry). Only the buffers are compared.
						wchar_t ga[514], gb[514];
						for (int i = 0; i < 514; ++i) { ga[i] = gb[i] = L'#'; }
						wchar_t* a = ga + 1;
						wchar_t* b = gb + 1;
						const unsigned long ra = IniCache::ReadStringW(s.c_str(), k.c_str(), d, a, size, path.c_str());
						const unsigned long rb = GetPrivateProfileStringW(s.c_str(), k.c_str(), d, b, size, path.c_str());
						++gCompared;
						const bool diffW = !SameAsCaller<wchar_t>(a, ra, b, rb, size, L'#');
						if (diffW && waived) { ++gWaived; }
						else if (diffW)
						{
							Mismatch(c, "StringW [" + Escape(s.c_str(), s.size()) + "] " + Escape(k.c_str(), k.size())
								+ " def \"" + Escape(d, wcslen(d)) + "\" size " + std::to_string(size)
								+ ": cache \"" + Escape(a, ra < size ? ra : 0) + "\" (" + std::to_string(ra)
								+ ") api \"" + Escape(b, rb < size ? rb : 0) + "\" (" + std::to_string(rb) + ")");
						}
						char gx[514], gy[514];
						memset(gx, '#', sizeof(gx));
						memset(gy, '#', sizeof(gy));
						char* x = gx + 1;
						char* y = gy + 1;
						const unsigned long rx = IniCache::ReadStringA(sA.c_str(), kA.c_str(), dA.c_str(), x, size, pathA.c_str());
						const unsigned long ry = GetPrivateProfileStringA(sA.c_str(), kA.c_str(), dA.c_str(), y, size, pathA.c_str());
						++gCompared;
						const bool diffA = !SameAsCaller<char>(x, rx, y, ry, size, '#');
						if (diffA && waived) { ++gWaived; }
						else if (diffA)
						{
							Mismatch(c, "StringA [" + sA + "] " + kA + " size " + std::to_string(size)
								+ ": cache (" + std::to_string(rx) + ") api (" + std::to_string(ry) + ")");
						}
					}
				}
				for (int def : { 0, 7, -3 })
				{
					const uint32_t ia = IniCache::ReadIntW(s.c_str(), k.c_str(), def, path.c_str());
					const uint32_t ib = GetPrivateProfileIntW(s.c_str(), k.c_str(), def, path.c_str());
					++gCompared;
					if (ia != ib && nameWaived) { ++gWaived; }
					else if (ia != ib)
					{
						Mismatch(c, "IntW [" + Escape(s.c_str(), s.size()) + "] " + Escape(k.c_str(), k.size())
							+ " def " + std::to_string(def) + ": cache " + std::to_string(ia)
							+ " api " + std::to_string(ib));
					}
				}
			}
		}
	}

	// The cache must follow the file: a rewrite (different size), a write of
	// our own, and a deleted file.
	void CacheFollowsTheFile(const std::wstring& dir)
	{
		const Case c = { "follow", "" };
		const std::wstring p = dir + L"follow.ini";
		wchar_t a[64], b[64];
		WriteBytes(p, "[F]\r\nk=1\r\n");
		IniCache::ReadStringW(L"F", L"k", L"", a, 64, p.c_str());
		WriteBytes(p, "[F]\r\nk=22\r\n");
		IniCache::ReadStringW(L"F", L"k", L"", a, 64, p.c_str());
		GetPrivateProfileStringW(L"F", L"k", L"", b, 64, p.c_str());
		++gCompared;
		if (wcscmp(a, b) != 0) { Mismatch(c, "an external rewrite was not seen"); }
		IniCache::WriteStringW(L"F", L"k", L"33", p.c_str());
		IniCache::ReadStringW(L"F", L"k", L"", a, 64, p.c_str());
		++gCompared;
		if (wcscmp(a, L"33") != 0) { Mismatch(c, "our own write was not seen"); }
		DeleteFileW(p.c_str());
		IniCache::ReadStringW(L"F", L"k", L"gone", a, 64, p.c_str());
		++gCompared;
		if (wcscmp(a, L"gone") != 0) { Mismatch(c, "a deleted file still answered"); }
	}
#endif
}

int main(int argc, char** argv)
{
	GoldenChecks();
	printf("model: %s (%d failure(s)) - the rules IniParse.h states, checked against themselves\n",
		gFails ? "FAIL" : "ok", gFails);
#ifndef _WIN32
	(void)argc; (void)argv;
	printf("parity: NOT RUN - the real profile API exists only on Windows.\n");
	return gFails ? 1 : 2;
#else
	typedef const char* (*WineVer)();
	const HMODULE nt = GetModuleHandleW(L"ntdll.dll");
	const WineVer wv = nt ? reinterpret_cast<WineVer>(GetProcAddress(nt, "wine_get_version")) : nullptr;
	gWine = (wv != nullptr);
	if (gWine) { printf("running under Wine %s - a MODEL of Windows, not Windows.\n", wv()); }

	std::vector<Case> cases = BuiltInCases();
	for (int i = 1; i < argc; ++i)
	{
		const std::string bytes = ReadAll(argv[i]);
		if (bytes.empty()) { printf("note: %s is empty or unreadable\n", argv[i]); }
		cases.push_back({ argv[i], bytes, bytes.rfind("\xEF\xBB\xBF", 0) == 0 });
	}
	const std::wstring dir = TempDir();
	int idx = 0;
	for (const Case& c : cases)
	{
		const std::wstring p = dir + L"case" + std::to_wstring(idx++) + L".ini";
		WriteBytes(p, c.bytes);
		const int before = gMismatch;
		gCaseMismatch = 0;
		IniCache::Invalidate(p.c_str());
		wchar_t probe[4];
		IniCache::ReadStringW(L"x", L"x", L"", probe, 4, p.c_str());   // loads the cache
		// The model the lookups enumerate is the cache's own decode of the file.
		std::string asRead = c.bytes;
		std::wstring text;
		if (asRead.size() >= 2 && static_cast<unsigned char>(asRead[0]) == 0xFF
			&& static_cast<unsigned char>(asRead[1]) == 0xFE)
		{
			for (size_t i = 2; i + 1 < asRead.size(); i += 2)
			{
				text += static_cast<wchar_t>(static_cast<unsigned char>(asRead[i])
					| (static_cast<unsigned char>(asRead[i + 1]) << 8));
			}
		}
		else if (!asRead.empty())
		{
			const int n = MultiByteToWideChar(CP_ACP, 0, asRead.data(), static_cast<int>(asRead.size()), nullptr, 0);
			text.resize(static_cast<size_t>(n));
			MultiByteToWideChar(CP_ACP, 0, asRead.data(), static_cast<int>(asRead.size()), &text[0], n);
		}
		Compare(c, p, IniParse::Parse(text));
		printf("  %-28s %s\n", c.name.c_str(), gMismatch == before ? "ok" : "MISMATCH");
		DeleteFileW(p.c_str());
	}
	{
		// A file that does not exist, in a folder that does and one that does not.
		const Case m = { "missing", "" };
		const std::wstring p1 = dir + L"absent.ini";
		const std::wstring p2 = dir + L"no-such-dir\\absent.ini";
		for (const std::wstring& p : { p1, p2 })
		{
			for (const wchar_t* d : { L"", L"\"q\"", L"dflt  " })
			{
				wchar_t a[32], b[32];
				for (int i = 0; i < 32; ++i) { a[i] = b[i] = L'#'; }
				const unsigned long ra = IniCache::ReadStringW(L"S", L"k", d, a, 32, p.c_str());
				const unsigned long rb = GetPrivateProfileStringW(L"S", L"k", d, b, 32, p.c_str());
				++gCompared;
				// A quoted default is a waived query class (see Compare).
				if ((ra != rb || memcmp(a, b, sizeof(a)) != 0) && d[0] == L'"') { ++gWaived; }
				else if (ra != rb || memcmp(a, b, sizeof(a)) != 0)
				{
					Mismatch(m, "missing file, default \"" + Escape(d, wcslen(d)) + "\": cache \""
						+ Escape(a, ra) + "\" api \"" + Escape(b, rb) + "\"");
				}
			}
		}
		printf("  %-28s %s\n", "missing file", gMismatch ? "see above" : "ok");
	}
	CacheFollowsTheFile(dir);
	RemoveDirectoryW(dir.c_str());

	printf("parity: %lld comparison(s), %d mismatch(es)%s\n", gCompared, gMismatch,
		gWine ? " (Wine)" : "");
	printf("waived: %lld mismatch(es) in query classes the DLL never issues (empty section,"
		" ';' key, tab in a name, default with trailing blanks or a leading quote);"
		" tools/dev/inicache/check_call_sites.py proves no call site does\n", gWaived);
	if (gWineOnly)
	{
		printf("        %d known Wine-only divergence(s) not counted (Wine decodes a "
			"UTF-8 BOM; Windows does not).\n", gWineOnly);
	}
	if (gFails || gMismatch)
	{
		printf("FAIL\n");
		return 1;
	}
	printf("%s\n", gWine ? "PASS under Wine - still to be run on Windows" : "PASS");
	return 0;
#endif
}
