#pragma once
#include <cstdint>

enum class LogLevel : int
{
	Error = 0,
	Info = 1,
	Debug = 2,
	Trace = 3,
};

// ---- PerfProbe: in-memory timing buckets (freeze localization) -----------
// Named duration accumulators that NEVER touch a file on the hot path - the
// whole point is to measure paths suspected of stalling on file I/O, so the
// instrument must not be made of the thing it measures. The selector dumps
// the table on dialog close and at shutdown, and a per-pass watchdog names
// the top in-gap contributor when a stall is seen.
namespace PerfProbe
{
	struct Row
	{
		const char* name;
		unsigned int count;
		unsigned long long totalUs;
		unsigned long long maxUs;
	};

	unsigned long long NowUs();
	void Add(const char* name, unsigned long long us);
	// Copies up to `cap` buckets into `out`; returns the count copied.
	int Snapshot(Row* out, int cap);

	class Scope
	{
	public:
		explicit Scope(const char* n) : name(n), t0(NowUs()) {}
		~Scope() { Add(name, NowUs() - t0); }
	private:
		const char* name;
		unsigned long long t0;
	};
}

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
