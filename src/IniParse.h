#pragma once
// THE PROFILE-API RULES, AS DATA (audit B8, 2026-09-25).
//
// IniCache (IniCache.h) answers GetPrivateProfileString/Int from ONE parse of
// the file instead of re-opening and re-parsing it on every call. This header
// holds the rules that parse and those lookups follow. It has no Win32
// dependency, so tools/dev/inicache can build it anywhere; on Windows the
// same tool checks every rule below against the real API
// (run_inicache_parity.py). The rules are the documented ones plus the Wine
// 9.0 implementation (dlls/kernel32/profile.c, read from source), which is
// itself tested against Windows:
//
//   * A line ends at any CR or LF. Leading and trailing white space
//     (TAB..CR, space, ^Z) is dropped; blank lines are skipped.
//   * `[` starts a section header; the name runs to the LAST `]` on the line
//     and is trimmed. A `[` line with no `]` is an ordinary key line.
//   * Keys before the first header belong to a nameless section, which an
//     empty (or all-space) section name reaches.
//   * A key line splits at the FIRST `=`; the name loses trailing white space,
//     the value leading white space. A line with no `=` is a key with no value,
//     which reads as absent.
//   * No comment syntax at all: `;x=1` is a key named ";x", and in `K = 1 ; c`
//     the value is "1 ; c" (GetPrivateProfileInt still reads 1).
//   * Section and key names compare case-insensitively (ASCII folding; every
//     name this project reads is ASCII) after trimming the query. The FIRST
//     matching section is the only one searched, and the first matching key
//     in it wins.
//   * A value wrapped in a matching pair of ' or " comes back without them.
//   * The default loses trailing spaces (all but the first, if it is only
//     spaces). The copy is truncated to size-1 characters; the return value
//     is the length copied. A file that does not exist reads as empty; one
//     that cannot be opened at all (a missing folder, no access) returns the
//     default without the quote rule (GetStringUnopened).
//   * GetPrivateProfileInt reads the string (30-character buffer) and parses
//     it like RtlUnicodeStringToInteger base 0: leading control/space
//     characters skipped, one sign, 0x/0o/0b prefixes (lower case), digits
//     until the first non-digit, 32-bit wraparound. An empty or absent value
//     returns the default.
#include <cstddef>
#include <cstdint>
#include <cwchar>
#include <string>
#include <vector>

namespace IniParse
{
	struct Key
	{
		std::wstring name;
		std::wstring value;
		bool hasValue = false;   // false: the line had no '='
	};

	struct Section
	{
		std::wstring name;       // sections[0] is the nameless lead section
		std::vector<Key> keys;
	};

	struct File
	{
		std::vector<Section> sections;
	};

	inline bool IsSpace(wchar_t c)
	{
		return c == L' ' || (c >= 0x09 && c <= 0x0D) || c == 0x1A;
	}

	inline wchar_t FoldAscii(wchar_t c)
	{
		return (c >= L'A' && c <= L'Z') ? static_cast<wchar_t>(c - L'A' + L'a') : c;
	}

	// Case-insensitive equality of a stored name with the query span [q, q+n).
	inline bool NameEquals(const std::wstring& name, const wchar_t* q, size_t n)
	{
		if (name.size() != n) { return false; }
		for (size_t i = 0; i < n; ++i)
		{
			if (FoldAscii(name[i]) != FoldAscii(q[i])) { return false; }
		}
		return true;
	}

	inline File Parse(const std::wstring& text)
	{
		File f;
		f.sections.emplace_back();
		size_t cur = 0;                  // index of the section being filled
		const size_t n = text.size();
		size_t pos = 0;
		while (pos < n)
		{
			size_t a = pos;
			while (pos < n && text[pos] != L'\n' && text[pos] != L'\r') { ++pos; }
			while (pos < n && (text[pos] == L'\n' || text[pos] == L'\r')) { ++pos; }
			size_t b = pos;
			while (a < b && IsSpace(text[a])) { ++a; }
			while (b > a && IsSpace(text[b - 1])) { --b; }
			if (a >= b) { continue; }

			if (text[a] == L'[')
			{
				size_t close = b;
				while (close > a && text[close - 1] != L']') { --close; }
				if (close > a + 1)
				{
					size_t na = a + 1, nb = close - 1;
					while (na < nb && IsSpace(text[na])) { ++na; }
					while (nb > na && IsSpace(text[nb - 1])) { --nb; }
					Section s;
					s.name.assign(text, na, nb - na);
					f.sections.push_back(std::move(s));
					cur = f.sections.size() - 1;
					continue;
				}
				// no ']' after the '[': an ordinary key line
			}

			Key k;
			size_t eq = a;
			while (eq < b && text[eq] != L'=') { ++eq; }
			if (eq < b)
			{
				size_t nameEnd = eq;
				while (nameEnd > a && IsSpace(text[nameEnd - 1])) { --nameEnd; }
				k.name.assign(text, a, nameEnd - a);
				size_t v = eq + 1;
				while (v < b && IsSpace(text[v])) { ++v; }
				k.value.assign(text, v, b - v);
				k.hasValue = true;
			}
			else
			{
				k.name.assign(text, a, b - a);
			}
			// Wine keeps a nameless key only after a named one (a quirk of
			// its blank-line handling; nameless keys never match a lookup).
			std::vector<Key>& keys = f.sections[cur].keys;
			if (!k.name.empty() || keys.empty() || !keys.back().name.empty())
			{
				keys.push_back(std::move(k));
			}
		}
		return f;
	}

	// The key the profile API would read, or nullptr.
	inline const Key* Find(const File& f, const wchar_t* section, const wchar_t* key)
	{
		const wchar_t* s = section;
		while (*s && IsSpace(*s)) { ++s; }
		size_t sn = wcslen(s);
		while (sn > 0 && IsSpace(s[sn - 1])) { --sn; }
		const wchar_t* k = key;
		while (*k && IsSpace(*k)) { ++k; }
		size_t kn = wcslen(k);
		while (kn > 0 && IsSpace(k[kn - 1])) { --kn; }
		for (const Section& sec : f.sections)
		{
			if (!NameEquals(sec.name, s, sn)) { continue; }
			for (const Key& kk : sec.keys)
			{
				if (NameEquals(kk.name, k, kn)) { return &kk; }
			}
			return nullptr;   // only the first matching section is searched
		}
		return nullptr;
	}

	// lstrcpyn: at most size-1 characters, always terminated.
	inline unsigned long CopyTruncated(const wchar_t* src, wchar_t* out, unsigned long size)
	{
		if (!out || size == 0) { return 0; }
		size_t len = wcslen(src);
		if (len > size - 1) { len = size - 1; }
		for (size_t i = 0; i < len; ++i) { out[i] = src[i]; }
		out[len] = L'\0';
		return static_cast<unsigned long>(len);
	}

	// The copy-out: one pair of matching quotes removed, then truncation.
	// MEASURED ON REAL WINDOWS (2026-09-25): a quoted value "dq" read into
	// size 3 returns "dq". Wine instead drops one more character when the
	// buffer is exactly one short of the value plus its closing quote, and
	// this function used to copy that Wine quirk - the parity harness passed
	// under Wine and failed on Windows. The quote is stripped first, then
	// the copy is truncated, as Windows does.
	inline unsigned long CopyEntry(const wchar_t* value, wchar_t* out, unsigned long size)
	{
		if (!out || size == 0) { return 0; }
		size_t len = wcslen(value);
		if (len >= 2 && (value[0] == L'\'' || value[0] == L'"') && value[len - 1] == value[0])
		{
			std::wstring inner(value + 1, len - 2);
			return CopyTruncated(inner.c_str(), out, size);
		}
		return CopyTruncated(value, out, size);
	}

	// The default as the API uses it: trailing spaces removed.
	inline std::wstring TrimmedDefault(const wchar_t* def)
	{
		std::wstring d = def ? def : L"";
		while (d.size() > 1 && d.back() == L' ') { d.pop_back(); }
		return d;
	}

	// GetPrivateProfileStringW over a parsed file.
	inline unsigned long GetString(const File& f, const wchar_t* section,
		const wchar_t* key, const wchar_t* def, wchar_t* out, unsigned long size)
	{
		if (!out || size == 0) { return 0; }
		const std::wstring d = TrimmedDefault(def);
		const Key* k = Find(f, section, key);
		return CopyEntry((k && k->hasValue) ? k->value.c_str() : d.c_str(), out, size);
	}

	// A file the API could not open at all (not merely absent): the default,
	// trailing spaces removed, copied WITHOUT the quote rule.
	inline unsigned long GetStringUnopened(const wchar_t* def, wchar_t* out,
		unsigned long size)
	{
		if (!out || size == 0) { return 0; }
		return CopyTruncated(TrimmedDefault(def).c_str(), out, size);
	}

	// RtlUnicodeStringToInteger, base 0.
	inline uint32_t ParseInt(const wchar_t* s)
	{
		while (*s && *s <= L' ') { ++s; }
		bool minus = false;
		if (*s == L'+') { ++s; }
		else if (*s == L'-') { minus = true; ++s; }
		uint32_t base = 10;
		if (s[0] == L'0' && s[1] != 0)
		{
			if (s[1] == L'b') { base = 2; s += 2; }
			else if (s[1] == L'o') { base = 8; s += 2; }
			else if (s[1] == L'x') { base = 16; s += 2; }
		}
		uint32_t total = 0;
		for (; *s; ++s)
		{
			int digit = -1;
			if (*s >= L'0' && *s <= L'9') { digit = *s - L'0'; }
			else if (*s >= L'A' && *s <= L'Z') { digit = *s - L'A' + 10; }
			else if (*s >= L'a' && *s <= L'z') { digit = *s - L'a' + 10; }
			if (digit < 0 || static_cast<uint32_t>(digit) >= base) { break; }
			total = total * base + static_cast<uint32_t>(digit);
		}
		return minus ? static_cast<uint32_t>(0u - total) : total;
	}

	// GetPrivateProfileIntW over a parsed file.
	inline uint32_t GetInt(const File& f, const wchar_t* section, const wchar_t* key, int def)
	{
		wchar_t buf[30] = {};
		if (GetString(f, section, key, L"", buf, 30) == 0)
		{
			return static_cast<uint32_t>(def);
		}
		return ParseInt(buf);
	}
}
