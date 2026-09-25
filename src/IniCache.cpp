#include "IniCache.h"
#include "IniParse.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <string>
#include <vector>

// See IniCache.h. One parse per file version, answered under the profile
// API's rules (IniParse.h), guarded by one lock because the API it replaces
// is thread-safe.
namespace
{
	// How the API sees a path: a file, no such file (reads as empty), or
	// nothing it can open at all (the default comes back verbatim).
	enum class State { File, NotFound, Unopenable };

	struct Entry
	{
		std::wstring path;
		State state = State::NotFound;
		FILETIME written = {};
		ULONGLONG size = 0;
		IniParse::File file;
	};

	SRWLOCK gLock = SRWLOCK_INIT;

	// Never freed, so a read during process teardown cannot meet a destroyed
	// container.
	std::vector<Entry>& Entries()
	{
		static std::vector<Entry>* s = new std::vector<Entry>();
		return *s;
	}

	// The profile API resolves a bare file name against the Windows
	// directory; only a full path is cached, anything else goes to the API.
	bool IsFullPath(const wchar_t* p)
	{
		return p && ((p[0] && p[1] == L':' && (p[2] == L'\\' || p[2] == L'/'))
			|| (p[0] == L'\\' && p[1] == L'\\'));
	}

	State StateFromError(DWORD err)
	{
		return (err == ERROR_FILE_NOT_FOUND) ? State::NotFound : State::Unopenable;
	}

	State Stat(const wchar_t* path, FILETIME* written, ULONGLONG* size)
	{
		WIN32_FILE_ATTRIBUTE_DATA a = {};
		if (!GetFileAttributesExW(path, GetFileExInfoStandard, &a))
		{
			return StateFromError(GetLastError());
		}
		if (a.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) { return State::Unopenable; }
		*written = a.ftLastWriteTime;
		*size = (static_cast<ULONGLONG>(a.nFileSizeHigh) << 32) | a.nFileSizeLow;
		return State::File;
	}

	// The API's own caution, kept: a write time within 2.1 s of now may not
	// move on the next write (FAT keeps 2 s), so such a file is re-read.
	bool OldEnoughToTrust(const FILETIME& ft)
	{
		FILETIME now = {};
		GetSystemTimeAsFileTime(&now);
		const ULONGLONG t = (static_cast<ULONGLONG>(ft.dwHighDateTime) << 32) | ft.dwLowDateTime;
		const ULONGLONG n = (static_cast<ULONGLONG>(now.dwHighDateTime) << 32) | now.dwLowDateTime;
		return t + 21000000ull < n;
	}

	// The profile API's decoding: UTF-16 with its byte-order mark, anything
	// else in the ANSI code page. A UTF-8 BOM is not recognised - its three
	// bytes become the first characters of line one, which hides a section
	// header written on that line (the project's no-BOM rule).
	std::wstring Decode(const std::vector<char>& bytes)
	{
		const size_t n = bytes.size();
		const unsigned char* b = reinterpret_cast<const unsigned char*>(bytes.data());
		if (n >= 2 && b[0] == 0xFF && b[1] == 0xFE)
		{
			std::wstring w((n - 2) / 2, L'\0');
			for (size_t i = 0; i < w.size(); ++i)
			{
				w[i] = static_cast<wchar_t>(b[2 + 2 * i] | (b[3 + 2 * i] << 8));
			}
			return w;
		}
		if (n >= 2 && b[0] == 0xFE && b[1] == 0xFF)
		{
			std::wstring w((n - 2) / 2, L'\0');
			for (size_t i = 0; i < w.size(); ++i)
			{
				w[i] = static_cast<wchar_t>((b[2 + 2 * i] << 8) | b[3 + 2 * i]);
			}
			return w;
		}
		if (n == 0) { return std::wstring(); }
		const int len = MultiByteToWideChar(CP_ACP, 0, bytes.data(),
			static_cast<int>(n), nullptr, 0);
		std::wstring w(len > 0 ? static_cast<size_t>(len) : 0, L'\0');
		if (len > 0)
		{
			MultiByteToWideChar(CP_ACP, 0, bytes.data(), static_cast<int>(n), &w[0], len);
		}
		return w;
	}

	// Read and parse `path` into `e`. A file that cannot be opened reads as
	// empty, as it does through the API.
	void Load(const wchar_t* path, Entry& e)
	{
		e.state = State::NotFound;
		e.written = FILETIME{};
		e.size = 0;
		std::vector<char> bytes;
		const HANDLE h = CreateFileW(path, GENERIC_READ,
			FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr,
			OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
		if (h == INVALID_HANDLE_VALUE)
		{
			e.state = StateFromError(GetLastError());
		}
		else
		{
			BY_HANDLE_FILE_INFORMATION info = {};
			if (GetFileInformationByHandle(h, &info))
			{
				e.state = State::File;
				e.written = info.ftLastWriteTime;
				e.size = (static_cast<ULONGLONG>(info.nFileSizeHigh) << 32)
					| info.nFileSizeLow;
				bytes.resize(static_cast<size_t>(e.size));
				DWORD got = 0;
				if (!bytes.empty()
					&& !ReadFile(h, bytes.data(), static_cast<DWORD>(bytes.size()), &got, nullptr))
				{
					got = 0;
				}
				bytes.resize(got);
			}
			CloseHandle(h);
		}
		e.file = IniParse::Parse(Decode(bytes));
	}

	// The entry for `path` as the file stands now. Caller holds gLock.
	const Entry& Current(const wchar_t* path)
	{
		FILETIME w = {};
		ULONGLONG sz = 0;
		const State st = Stat(path, &w, &sz);
		std::vector<Entry>& es = Entries();
		Entry* e = nullptr;
		for (Entry& x : es)
		{
			if (_wcsicmp(x.path.c_str(), path) == 0) { e = &x; break; }
		}
		if (e && e->state == st
			&& (st != State::File || (CompareFileTime(&e->written, &w) == 0
				&& e->size == sz && OldEnoughToTrust(w))))
		{
			return *e;
		}
		if (!e)
		{
			es.emplace_back();
			e = &es.back();
			e->path = path;
		}
		Load(path, *e);
		return *e;
	}

	std::wstring Widen(const char* s)
	{
		const int n = MultiByteToWideChar(CP_ACP, 0, s, -1, nullptr, 0);
		if (n <= 1) { return std::wstring(); }
		std::wstring w(static_cast<size_t>(n), L'\0');
		MultiByteToWideChar(CP_ACP, 0, s, -1, &w[0], n);
		w.resize(static_cast<size_t>(n - 1));
		return w;
	}
}

namespace IniCache
{
	uint32_t ReadIntW(const wchar_t* section, const wchar_t* key, int def,
		const wchar_t* path)
	{
		if (!section || !key || !IsFullPath(path))
		{
			return GetPrivateProfileIntW(section, key, def, path);
		}
		AcquireSRWLockExclusive(&gLock);
		const Entry& e = Current(path);
		const uint32_t v = (e.state == State::Unopenable) ? static_cast<uint32_t>(def)
			: IniParse::GetInt(e.file, section, key, def);
		ReleaseSRWLockExclusive(&gLock);
		return v;
	}

	unsigned long ReadStringW(const wchar_t* section, const wchar_t* key,
		const wchar_t* def, wchar_t* out, unsigned long size, const wchar_t* path)
	{
		if (!section || !key || !IsFullPath(path))
		{
			return GetPrivateProfileStringW(section, key, def, out, size, path);
		}
		AcquireSRWLockExclusive(&gLock);
		const Entry& e = Current(path);
		const unsigned long n = (e.state == State::Unopenable)
			? IniParse::GetStringUnopened(def, out, size)
			: IniParse::GetString(e.file, section, key, def, out, size);
		ReleaseSRWLockExclusive(&gLock);
		return n;
	}

	unsigned long ReadStringA(const char* section, const char* key,
		const char* def, char* out, unsigned long size, const char* path)
	{
		if (!section || !key || !path)
		{
			return GetPrivateProfileStringA(section, key, def, out, size, path);
		}
		const std::wstring s = Widen(section), k = Widen(key), p = Widen(path);
		const std::wstring d = def ? Widen(def) : std::wstring();
		std::vector<wchar_t> wide(size ? size : 1);
		const unsigned long got = ReadStringW(s.c_str(), k.c_str(),
			def ? d.c_str() : nullptr, wide.data(), size, p.c_str());
		if (!out || size == 0) { return 0; }
		// As the API: convert what was read, keep one byte for the NUL.
		int n = 0;
		if (got)
		{
			n = WideCharToMultiByte(CP_ACP, 0, wide.data(), static_cast<int>(got),
				out, static_cast<int>(size - 1), nullptr, nullptr);
			if (!n) { n = static_cast<int>(size - 1); }
		}
		out[n] = '\0';
		return static_cast<unsigned long>(n);
	}

	int WriteStringW(const wchar_t* section, const wchar_t* key,
		const wchar_t* value, const wchar_t* path)
	{
		const BOOL ok = WritePrivateProfileStringW(section, key, value, path);
		if (path) { Invalidate(path); }
		return ok;
	}

	void Invalidate(const wchar_t* path)
	{
		AcquireSRWLockExclusive(&gLock);
		std::vector<Entry>& es = Entries();
		for (size_t i = 0; i < es.size(); ++i)
		{
			if (_wcsicmp(es[i].path.c_str(), path) == 0)
			{
				es.erase(es.begin() + static_cast<std::ptrdiff_t>(i));
				break;
			}
		}
		ReleaseSRWLockExclusive(&gLock);
	}
}
