#pragma once
#include <cstdint>

enum class LogLevel : int
{
	Error = 0,
	Info = 1,
	Debug = 2,
	Trace = 3,
};

// Minimal append-to-file logger, null45-plugin style: one .log file beside the
// DLL, recreated each game launch. Safe to call before Init (calls are dropped).
class Logger
{
public:
	static Logger& Get();

	void Init(const wchar_t* logFilePath, LogLevel level);
	void SetLevel(LogLevel level);
	bool IsEnabled(LogLevel level) const;

	void WriteHeader(const char* headerLine);
	void WriteLine(LogLevel level, const char* format, ...);

private:
	Logger();
	~Logger();

	void* file; // FILE*
	LogLevel logLevel;
	void* lock; // CRITICAL_SECTION*
};
