#include "Logger.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <cstdarg>
#include <cstdio>
#include <ctime>
#include <share.h>

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

	EnterCriticalSection(static_cast<CRITICAL_SECTION*>(lock));
	fprintf(
		static_cast<FILE*>(file),
		"[%02u:%02u:%02u.%03u] %s\n",
		st.wHour, st.wMinute, st.wSecond, st.wMilliseconds,
		message);
	fflush(static_cast<FILE*>(file));
	LeaveCriticalSection(static_cast<CRITICAL_SECTION*>(lock));
}
