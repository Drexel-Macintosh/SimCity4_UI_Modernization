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
	fprintf(static_cast<FILE*>(file), "%s\n", headerLine);
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
	fprintf(
		static_cast<FILE*>(file),
		"[%02u:%02u:%02u.%03u] %s\n",
		st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
		message);
	fflush(static_cast<FILE*>(file));
	LeaveCriticalSection(static_cast<CRITICAL_SECTION*>(lock));
}
