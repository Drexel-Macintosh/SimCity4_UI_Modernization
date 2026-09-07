#include "Logger.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <share.h>

// ---- PerfProbe ------------------------------------------------------------
// Flat table, linear strcmp scan: with ~20 call sites the scan is nanoseconds,
// and a flat table cannot allocate, lock against the logger, or reenter
// anything. The game's UI is single-threaded; a torn diagnostic counter in
// the worst case is acceptable for an instrument, a lock on the hot path is
// not.
namespace PerfProbe
{
	namespace
	{
		const int kMax = 32;
		Row gRows[kMax];
		int gRowN = 0;

		unsigned long long QpcFreq()
		{
			static unsigned long long f = 0;
			if (f == 0)
			{
				LARGE_INTEGER li;
				QueryPerformanceFrequency(&li);
				f = static_cast<unsigned long long>(li.QuadPart);
				if (f == 0) { f = 1; }
			}
			return f;
		}
	}

	unsigned long long NowUs()
	{
		LARGE_INTEGER li;
		QueryPerformanceCounter(&li);
		return static_cast<unsigned long long>(li.QuadPart) * 1000000ull
			/ QpcFreq();
	}

	void Add(const char* name, unsigned long long us)
	{
		for (int i = 0; i < gRowN; i++)
		{
			// Pointer compare first: every caller passes a literal, so the
			// common case never strcmps at all.
			if (gRows[i].name == name
				|| strcmp(gRows[i].name, name) == 0)
			{
				gRows[i].count++;
				gRows[i].totalUs += us;
				if (us > gRows[i].maxUs) { gRows[i].maxUs = us; }
				return;
			}
		}
		if (gRowN < kMax)
		{
			gRows[gRowN].name = name;
			gRows[gRowN].count = 1;
			gRows[gRowN].totalUs = us;
			gRows[gRowN].maxUs = us;
			gRowN++;
		}
	}

	int Snapshot(Row* out, int cap)
	{
		const int n = (gRowN < cap) ? gRowN : cap;
		for (int i = 0; i < n; i++) { out[i] = gRows[i]; }
		return n;
	}
}

Logger& Logger::Get()
{
	static Logger instance;
	return instance;
}

Logger::Logger()
	: file(nullptr), logLevel(LogLevel::Info), lock(nullptr)
{
	CRITICAL_SECTION* cs = new CRITICAL_SECTION();
	InitializeCriticalSection(cs);
	lock = cs;
}

Logger::~Logger()
{
	if (file)
	{
		fclose(static_cast<FILE*>(file));
		file = nullptr;
	}
}

void Logger::Init(const wchar_t* logFilePath, LogLevel level)
{
	logLevel = level;

	// _SH_DENYWR: the log stays readable (tail-able) while the game runs.
	FILE* f = _wfsopen(logFilePath, L"w", _SH_DENYWR);
	if (f)
	{
		file = f;
	}
}

void Logger::SetLevel(LogLevel level)
{
	logLevel = level;
}

bool Logger::IsEnabled(LogLevel level) const
{
	return file != nullptr && static_cast<int>(level) <= static_cast<int>(logLevel);
}

void Logger::WriteHeader(const char* headerLine)
{
	if (!file)
	{
		return;
	}

	EnterCriticalSection(static_cast<CRITICAL_SECTION*>(lock));
	int n = fprintf(static_cast<FILE*>(file), "%s\n", headerLine);
	if (n > 0) { bytesWritten += static_cast<unsigned long long>(n); }
	// v4.10.0: the per-line stamps carry no date, so a session that
	// crosses midnight could not be matched against the game's own exception
	// reports (which are dated). The date goes here once, and an hour marker
	// is printed whenever the hour changes (see WriteLine).
	SYSTEMTIME st;
	GetLocalTime(&st);
	n = fprintf(static_cast<FILE*>(file),
		"[%02u:%02u:%02u.%03u] Log opened %04u-%02u-%02u local. Stamps below carry "
		"no date; a '---- hour' marker line is printed when the hour changes.\n",
		st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
		st.wYear, st.wMonth, st.wDay);
	if (n > 0) { bytesWritten += static_cast<unsigned long long>(n); }
	lastHour = st.wHour;
	fflush(static_cast<FILE*>(file));
	LeaveCriticalSection(static_cast<CRITICAL_SECTION*>(lock));
}

void Logger::WriteLine(LogLevel level, const char* format, ...)
{
	if (!IsEnabled(level))
	{
		return;
	}

	char message[1024];
	va_list args;
	va_start(args, format);
	vsnprintf(message, sizeof(message), format, args);
	va_end(args);

	SYSTEMTIME st;
	GetLocalTime(&st);

	// Bracketed as a freeze suspect: this fflush pushes every line through
	// whatever filter driver sits on the log's folder, synchronously, on the
	// UI thread. The bucket says whether that ever actually stalls.
	PerfProbe::Scope perf_("log.WriteLine");
	EnterCriticalSection(static_cast<CRITICAL_SECTION*>(lock));
	if (static_cast<int>(st.wHour) != lastHour)
	{
		if (lastHour >= 0)
		{
			int m = fprintf(static_cast<FILE*>(file),
				"---- %04u-%02u-%02u %02u:00 local - hour rollover (stamps carry no date) ----\n",
				st.wYear, st.wMonth, st.wDay, st.wHour);
			if (m > 0) { bytesWritten += static_cast<unsigned long long>(m); }
		}
		lastHour = st.wHour;
	}
	int n = fprintf(
		static_cast<FILE*>(file),
		"[%02u:%02u:%02u.%03u] %s\n",
		st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
		message);
	if (n > 0) { bytesWritten += static_cast<unsigned long long>(n); }
	// v4.10.0 SOFT CAP. One Info line inside a 16 ms path once produced
	// "5211 lines and a 1 MB log in one session" (MDOCK); at LogLevel=3 the
	// live log grows ~9 MB/h. Past 64 MB the level drops to Info, once, and
	// says so - a runaway Debug/Trace path cannot fill a disk, and the line
	// names the cure. Info lines are all budgeted; they are never dropped.
	const unsigned long long kSoftCapBytes = 64ull * 1024ull * 1024ull;
	if (!softCapNoted && bytesWritten > kSoftCapBytes)
	{
		softCapNoted = true;
		int m = fprintf(static_cast<FILE*>(file),
			"[%02u:%02u:%02u.%03u] LOG SOFT CAP: %llu bytes written this session - "
			"LogLevel dropped to 1 (Info) from here on so a hot Debug/Trace line "
			"cannot fill the disk. Lower LogLevel in SC4UIScale.ini, or find the "
			"repeating line above and budget it.\n",
			st.wHour, st.wMinute, st.wSecond, st.wMilliseconds, bytesWritten);
		if (m > 0) { bytesWritten += static_cast<unsigned long long>(m); }
		if (static_cast<int>(logLevel) > static_cast<int>(LogLevel::Info))
		{
			logLevel = LogLevel::Info;
		}
	}
	fflush(static_cast<FILE*>(file));
	LeaveCriticalSection(static_cast<CRITICAL_SECTION*>(lock));
}
