#include "SpinProbe.h"
#include "Logger.h"

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <tlhelp32.h>

#include <cstdint>
#include <cstdio>
#include <cstring>

namespace
{
	const int    kSampleIntervalMs = 50;    // 20 Hz
	const int    kMaxDistinctEips  = 512;
	const int    kMaxThreads       = 64;
	const int    kReportTop        = 24;   // v2: 12 hid most of the hot
		// thread's addresses behind ntdll wait stubs from 46 parked threads.
	const int    kPartialEverySec  = 1;
	const int    kStackScanBytes   = 8192; // v2: caller-chain scan depth
	const uintptr_t kPreferredImageBase = 0x400000; // the VA space our
		// disassembly and every address in CodePatches.cpp is written in.

	// The game image's live range, resolved once. Everything interesting is
	// code INSIDE it - the 2026-08-03 capture found 46 of 47 threads parked at
	// fixed ntdll/win32u wait addresses and exactly one executing game code,
	// so "is this EIP in the game image" is the signal that separates the
	// spinning thread from the sleeping crowd.
	uintptr_t gImgLo = 0;
	uintptr_t gImgHi = 0;

	// v3: the loop's `this`, captured across ALL sweeps.
	//
	// v2 gated the field dump on the EIP being inside the loop head AT THE
	// SINGLE INSTANT of the stack scan, and it never fired - the thread was
	// down in a callee (0x009DB8A4). The loop head is only ~4% of samples, so
	// that gate was a coincidence detector. Capture it whenever we happen to
	// land there instead; over ~600 sweeps that is near-certain.
	uintptr_t gLoopThis = 0;
	uint32_t  gLoopTid  = 0;
	uint32_t  gLoopHits = 0;

	// COPY-ON-WRITE CHURN (#104). sub_99E08F clones the child list and swaps
	// [this+0x44] to the clone whenever the iteration guard [list+4] is held.
	// If that fires mid-teardown, ChildDelete erases from one list object while
	// ChildDeleteAll keeps re-reading [esi+0x44] and getting another - enumerate
	// and erase diverge for good. A CHANGING list pointer is that signature; a
	// stable one refutes it. Recorded across sweeps, not at one instant.
	uint32_t  gListPtrFirst = 0;
	uint32_t  gListPtrLast  = 0;
	uint32_t  gListPtrChanges = 0;

	void InitImageRange()
	{
		HMODULE h = GetModuleHandleW(nullptr);
		if (h == nullptr) { return; }
		const uintptr_t b = reinterpret_cast<uintptr_t>(h);
		const IMAGE_DOS_HEADER* dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(b);
		if (dos->e_magic != IMAGE_DOS_SIGNATURE) { return; }
		const IMAGE_NT_HEADERS* nt =
			reinterpret_cast<const IMAGE_NT_HEADERS*>(b + dos->e_lfanew);
		if (nt->Signature != IMAGE_NT_SIGNATURE) { return; }
		gImgLo = b;
		gImgHi = b + nt->OptionalHeader.SizeOfImage;
	}

	inline bool InGameImage(uintptr_t a)
	{
		return gImgLo != 0 && a >= gImgLo && a < gImgHi;
	}

	// ================= LOOP SIGNATURE GATE (v2.67.0, #114) =================
	// THE PROBLEM THIS CLOSES. The #104 fix is the ONLY write in this product
	// that was not verify-before-write. Everything in CodePatches.cpp compares
	// the live bytes against a stock expectation and skips on mismatch; this
	// one trusted a HARD-CODED VA (0x0099DD6F..0x0099DDB2) relocated by image
	// base alone. On any exe that is not 1.1.641 that range points at
	// unrelated code, the EIP guard can match a DIFFERENT loop, and we would
	// then WriteProcessMemory through a pointer taken from a suspended
	// thread's esi. That is how you corrupt somebody else's game.
	//
	// THE GATE. Verify the actual bytes at the relocated address against the
	// first 16 of cGZWin::ChildDeleteAll as shipped in 1.1.641:
	//   53 56 57         push ebx/esi/edi
	//   8B F1            mov esi, ecx
	//   32 DB            xor bl, bl
	//   8B 46 44         mov eax, [esi+0x44]     <- the child list
	//   8B 08            mov ecx, [eax]          <- the sentinel
	//   33 FF            xor edi, edi
	//   FF 40 ..         inc dword [eax+4]       <- the iteration guard
	// A mismatch DISABLES THE FIX ENTIRELY for the session and says so. It is
	// deliberately fail-closed: a hang we do not fix is a nuisance, a write
	// into the wrong address is somebody's save game.
	const uint8_t kLoopSig[] = {
		0x53, 0x56, 0x57, 0x8B, 0xF1, 0x32, 0xDB, 0x8B,
		0x46, 0x44, 0x8B, 0x08, 0x33, 0xFF, 0xFF, 0x40,
	};
	const uintptr_t kLoopVa = 0x0099DD6F;
	int gLoopVerified = -1;   // -1 = not yet checked, 0 = REFUSED, 1 = ok

	bool LoopBytesVerified()
	{
		if (gLoopVerified >= 0) { return gLoopVerified == 1; }
		gLoopVerified = 0;
		if (gImgLo == 0) { return false; }
		const uintptr_t at = gImgLo + (kLoopVa - kPreferredImageBase);
		if (!InGameImage(at) || !InGameImage(at + sizeof(kLoopSig))) { return false; }
		// The range is inside the mapped image, so a read cannot fault; compare
		// directly rather than through Peek (which is for FOREIGN pointers).
		if (memcmp(reinterpret_cast<const void*>(at), kLoopSig, sizeof(kLoopSig)) == 0)
		{
			gLoopVerified = 1;
		}
		return gLoopVerified == 1;
	}

	// ---------------- outcome recorder state (task #107) ----------------
	SpinProbe::LaunchInfo gLaunch = {};
	bool     gLaunchValid  = false;
	bool     gBudgetSeen   = false;
	bool     gSpunWritten  = false;   // one spun row per launch, not per sweep
	char     gLaunchId[32] = {};
	wchar_t  gCsvPath[MAX_PATH] = {};

	// Budget-family roots. Opening Budget is what puts these on screen, and
	// #104 does not reproduce unless Budget was opened at least once.
	const uint32_t kBudgetRootIds[] = {
		0xAA3AC000, // balance bar / compact
		0xAA3AC001, // expanded / detail-dialog frame
		// #102 COMMENT-ONLY CORRECTION (2026-08-03): "income section" was
		// wrong. LIVE 500x464 at (158,40) = script I-cbc3c2b9, whose subtree
		// is captioned "Taxes" with per-RCI rate editors + Accept/Cancel.
		// The id list and the probe's behaviour are unchanged.
		0xAA3AC002, // Taxes editor popup
		0xCA4C332D, // "Take Out A Loan" popup (name NOT adjudicated by #102 -
		            // no caption in either script; see UiSpike.cpp
		            // kDataScaledSubtreeIds NOTE)
	};

	// The CSV lives beside OUR DLL, resolved from our own module - not from
	// the game's directory and not from a hardcoded path.
	bool ResolveCsvPath()
	{
		if (gCsvPath[0] != L'\0') { return true; }
		HMODULE self = nullptr;
		if (!GetModuleHandleExW(
				GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
				GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
				reinterpret_cast<LPCWSTR>(&ResolveCsvPath), &self) || self == nullptr)
		{
			return false;
		}
		wchar_t path[MAX_PATH] = {};
		if (GetModuleFileNameW(self, path, MAX_PATH) == 0) { return false; }
		wchar_t* lastSlash = nullptr;
		for (wchar_t* p = path; *p; p++)
		{
			if (*p == L'\\' || *p == L'/') { lastSlash = p; }
		}
		if (lastSlash == nullptr) { return false; }
		*(lastSlash + 1) = L'\0';
		if (wcslen(path) + wcslen(L"SC4UIScale-104.csv") >= MAX_PATH) { return false; }
		wcscpy_s(gCsvPath, MAX_PATH, path);
		wcscat_s(gCsvPath, MAX_PATH, L"SC4UIScale-104.csv");
		return true;
	}

	// APPEND ONLY. This file is the one artefact that must survive across
	// launches; opening it "w" anywhere would destroy the whole point.
	void CsvAppend(const char* line)
	{
		if (!ResolveCsvPath()) { return; }
		FILE* f = nullptr;
		if (_wfopen_s(&f, gCsvPath, L"ab") != 0 || f == nullptr) { return; }
		// MUST seek to end before asking for the size: in "ab" mode the CRT
		// leaves the position indicator at 0 until the first write, so a bare
		// _ftelli64 reports 0 for a file that already has content - which
		// re-emitted the header before EVERY row and broke Show-104Rates.ps1
		// (it parsed the repeated header as data). Writes still always append.
		fseek(f, 0, SEEK_END);
		if (_ftelli64(f) == 0)
		{
			fputs("launchId,localTime,version,factor,scaleAll,ordinanceInset,"
				  "budgetDept,budgetButton,budgetSeen,probeSec,verdict,detail\r\n", f);
		}
		fputs(line, f);
		fflush(f);
		fclose(f);
	}

	void MakeLaunchId()
	{
		if (gLaunchId[0] != '\0') { return; }
		SYSTEMTIME st = {};
		GetLocalTime(&st);
		sprintf_s(gLaunchId, sizeof(gLaunchId), "%04u%02u%02u-%02u%02u%02u-%lu",
			st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond,
			GetCurrentProcessId());
	}

	void WriteCsvRow(const char* verdict, const char* detail)
	{
		if (!gLaunchValid) { return; }
		MakeLaunchId();
		SYSTEMTIME st = {};
		GetLocalTime(&st);
		char line[512];
		sprintf_s(line, sizeof(line),
			"%s,%04u-%02u-%02u %02u:%02u:%02u,%s,%.2f,%d,%d,%d,%d,%d,%d,%s,%s\r\n",
			gLaunchId,
			st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond,
			gLaunch.version ? gLaunch.version : "?",
			static_cast<double>(gLaunch.factor),
			gLaunch.scaleAll ? 1 : 0,
			gLaunch.ordinanceInset ? 1 : 0,
			gLaunch.budgetDept ? 1 : 0,
			gLaunch.budgetButton ? 1 : 0,
			gBudgetSeen ? 1 : 0,
			gLaunch.probeSeconds,
			verdict,
			detail ? detail : "");
		CsvAppend(line);
	}

	struct EipBucket
	{
		uintptr_t eip;
		uint32_t  count;
		uint32_t  tid;   // a representative sampler-side tid
	};

	struct ThreadBucket
	{
		uint32_t tid;
		uint32_t samples;
		uint32_t failures;
		uint32_t gameSamples; // v2: samples whose EIP was in the game image
	};

	struct Tally
	{
		EipBucket    eips[kMaxDistinctEips];
		int          eipCount;
		ThreadBucket threads[kMaxThreads];
		int          threadCount;

		uint32_t     sweeps;
		uint32_t     threadsSeen;      // enumeration hits (summed over sweeps)
		uint32_t     opensOk;
		uint32_t     opensFailed;
		uint32_t     ctxFailed;
		uint32_t     samples;
		bool         eipOverflow;
		bool         threadOverflow;
	};

	void TallyInit(Tally& t)
	{
		memset(&t, 0, sizeof(t));
	}

	void TallyEip(Tally& t, uintptr_t eip, uint32_t tid)
	{
		for (int i = 0; i < t.eipCount; i++)
		{
			if (t.eips[i].eip == eip) { t.eips[i].count++; return; }
		}
		if (t.eipCount >= kMaxDistinctEips) { t.eipOverflow = true; return; }
		t.eips[t.eipCount].eip = eip;
		t.eips[t.eipCount].count = 1;
		t.eips[t.eipCount].tid = tid;
		t.eipCount++;
	}

	ThreadBucket* TallyThread(Tally& t, uint32_t tid)
	{
		for (int i = 0; i < t.threadCount; i++)
		{
			if (t.threads[i].tid == tid) { return &t.threads[i]; }
		}
		if (t.threadCount >= kMaxThreads) { t.threadOverflow = true; return nullptr; }
		ThreadBucket* b = &t.threads[t.threadCount++];
		b->tid = tid;
		b->samples = 0;
		b->failures = 0;
		b->gameSamples = 0;
		return b;
	}

	// v2: the thread that matters is the one running GAME code, not the one
	// with the most samples - every parked thread is sampled every sweep.
	const ThreadBucket* HottestGameThread(const Tally& t)
	{
		const ThreadBucket* best = nullptr;
		for (int i = 0; i < t.threadCount; i++)
		{
			if (t.threads[i].gameSamples == 0) { continue; }
			if (best == nullptr || t.threads[i].gameSamples > best->gameSamples)
			{
				best = &t.threads[i];
			}
		}
		return best;
	}

	// Name the module an address belongs to, and translate the address into
	// the VA space our disassembly uses. For the game exe at its preferred
	// base that is the identity, which is exactly what makes the number in
	// the log paste-able straight into the site tables.
	void DescribeAddress(uintptr_t addr, char* modOut, size_t modCap, uintptr_t* vaOut)
	{
		modOut[0] = '?';
		modOut[1] = '\0';
		*vaOut = addr;

		HMODULE hm = nullptr;
		if (!GetModuleHandleExA(
				GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
				GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
				reinterpret_cast<LPCSTR>(addr), &hm) || hm == nullptr)
		{
			return; // not in any module: JIT/heap/stack - itself a finding
		}

		char path[MAX_PATH] = {};
		if (GetModuleFileNameA(hm, path, MAX_PATH))
		{
			const char* base = path;
			for (const char* p = path; *p; p++)
			{
				if (*p == '\\' || *p == '/') { base = p + 1; }
			}
			strncpy_s(modOut, modCap, base, _TRUNCATE);
		}
		*vaOut = addr - reinterpret_cast<uintptr_t>(hm) + kPreferredImageBase;
	}

	void ReportTally(const Tally& t, const char* tag)
	{
		Logger& log = Logger::Get();

		// POSITIVE CONTROL FIRST. A probe that captured nothing is not the
		// finding "nothing was spinning" - it is a probe that could not see.
		// Say which, every time, before any histogram.
		if (t.samples == 0)
		{
			log.WriteLine(
				LogLevel::Info,
				"SPINPROBE %s STRUCTURAL NULL - 0 samples from %u sweeps "
				"(threads seen %u, opened %u, open-failed %u, ctx-failed %u). "
				"This says the PROBE could not see, NOT that nothing spun.",
				tag, t.sweeps, t.threadsSeen, t.opensOk, t.opensFailed, t.ctxFailed);
			return;
		}

		log.WriteLine(
			LogLevel::Info,
			"SPINPROBE %s %u samples over %u sweeps; threads seen %u, opened %u, "
			"open-failed %u, ctx-failed %u; %d distinct EIPs%s across %d threads%s.",
			tag, t.samples, t.sweeps, t.threadsSeen, t.opensOk, t.opensFailed,
			t.ctxFailed, t.eipCount, t.eipOverflow ? " (OVERFLOWED)" : "",
			t.threadCount, t.threadOverflow ? " (OVERFLOWED)" : "");

		// v2: lead with the ONE number that separates signal from crowd. The
		// 2026-08-03 capture had 46 threads parked at fixed ntdll wait stubs,
		// which swamped the ranked list; game-code samples are the signal.
		const ThreadBucket* hot = HottestGameThread(t);
		if (hot)
		{
			log.WriteLine(
				LogLevel::Info,
				"SPINPROBE %s >>> HOT THREAD tid %u: %u of its %u samples were in the "
				"GAME IMAGE. Every other thread is parked in a wait stub. This is the "
				"thread to explain.",
				tag, hot->tid, hot->gameSamples, hot->samples);
		}
		else
		{
			log.WriteLine(
				LogLevel::Info,
				"SPINPROBE %s >>> NO thread sampled inside the game image. If the "
				"process is nonetheless burning CPU, the spin is in a LIBRARY, not in "
				"the game's own code - which would refute #104's framing.",
				tag);
		}

		// Per-thread totals: which thread is burning the core.
		for (int i = 0; i < t.threadCount; i++)
		{
			const ThreadBucket& b = t.threads[i];
			if (b.samples == 0 && b.failures == 0) { continue; }
			log.WriteLine(
				LogLevel::Info,
				"SPINPROBE %s   tid %5u: %u samples (%u%% of all), %u in game image, %u failures.",
				tag, b.tid, b.samples,
				t.samples ? (b.samples * 100u / t.samples) : 0u,
				b.gameSamples, b.failures);
		}

		// v2: EVERY game-image EIP, not just whatever survives the global
		// top-N. In the first capture the top-12 cut showed only 3 of the hot
		// thread's addresses and hid the rest behind parked-thread wait stubs -
		// a report cap that silently drops the only interesting rows is an
		// instrument that lies by omission.
		if (hot)
		{
			int shown = 0;
			for (int i = 0; i < t.eipCount; i++)
			{
				if (!InGameImage(t.eips[i].eip)) { continue; }
				char mod[64];
				uintptr_t va = 0;
				DescribeAddress(t.eips[i].eip, mod, sizeof(mod), &va);
				log.WriteLine(
					LogLevel::Info,
					"SPINPROBE %s   GAME-EIP %4u hits  eip=0x%08X  va@%06X=0x%08X  tid %u",
					tag, t.eips[i].count, static_cast<uint32_t>(t.eips[i].eip),
					static_cast<uint32_t>(kPreferredImageBase),
					static_cast<uint32_t>(va), t.eips[i].tid);
				shown++;
			}
			if (shown == 0)
			{
				log.WriteLine(LogLevel::Info,
					"SPINPROBE %s   (hot thread found but no distinct game EIP retained - "
					"the distinct-EIP table overflowed)", tag);
			}
		}

		// Hot addresses, descending. Selection sort over a copy of the index
		// set - kReportTop passes over <= 512 entries, trivial, and it avoids
		// mutating the tally so the caller can keep sampling.
		bool taken[kMaxDistinctEips] = {};
		const int top = (t.eipCount < kReportTop) ? t.eipCount : kReportTop;
		for (int rank = 0; rank < top; rank++)
		{
			int best = -1;
			for (int i = 0; i < t.eipCount; i++)
			{
				if (taken[i]) { continue; }
				if (best < 0 || t.eips[i].count > t.eips[best].count) { best = i; }
			}
			if (best < 0) { break; }
			taken[best] = true;

			char mod[64];
			uintptr_t va = 0;
			DescribeAddress(t.eips[best].eip, mod, sizeof(mod), &va);
			log.WriteLine(
				LogLevel::Info,
				"SPINPROBE %s   #%-2d %5u hits (%2u%%) eip=0x%08X  va@%06X=0x%08X  %s  tid %u",
				tag, rank + 1, t.eips[best].count,
				t.samples ? (t.eips[best].count * 100u / t.samples) : 0u,
				static_cast<uint32_t>(t.eips[best].eip),
				static_cast<uint32_t>(kPreferredImageBase),
				static_cast<uint32_t>(va), mod, t.eips[best].tid);
		}
	}

	// v3: read a 4-byte field out of our own process, safely.
	bool Peek(uintptr_t addr, uint32_t* out)
	{
		SIZE_T got = 0;
		*out = 0;
		return addr != 0 &&
			ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<LPCVOID>(addr),
				out, 4, &got) && got == 4;
	}

	// Count a circular intrusive list, bounded so a corrupt or cyclic list
	// cannot hang the probe itself. head is the sentinel node.
	int CountList(uint32_t head)
	{
		if (head == 0) { return -1; }
		uint32_t first = 0;
		if (!Peek(head, &first)) { return -2; }
		int n = 0;
		uint32_t node = first;
		while (node && node != head && n < 4096)
		{
			uint32_t next = 0;
			if (!Peek(node, &next)) { return -2; }
			n++;
			node = next;
		}
		return n;
	}

	// Replicate cIGZWinMgr::IsWindowValid (0x009DC087 -> hash find 0x009DB9B1)
	// EXACTLY as the bytes do it, so we can ask the question the game asks:
	//     ecx = mgr + 0x44
	//     begin = [ecx+4] = [mgr+0x48], end = [ecx+8] = [mgr+0x4C]
	//     buckets = (end - begin) / 4
	//     idx = (key >> 2) % buckets
	//     node = [begin + idx*4]; while (node) { if ([node+4]==key) FOUND;
	//                                            node = [node] }
	// Returns 1 found, 0 not found, -1 could not evaluate. The -1 case matters:
	// an unreadable table is a STRUCTURAL null and must not read as "absent".
	int ReplicateIsWindowValid(uint32_t mgr, uint32_t key, uint32_t* bucketsOut)
	{
		*bucketsOut = 0;
		if (mgr == 0 || key == 0) { return -1; }
		uint32_t begin = 0, end = 0;
		if (!Peek(mgr + 0x48, &begin) || !Peek(mgr + 0x4C, &end)) { return -1; }
		if (begin == 0 || end <= begin) { return -1; }
		const uint32_t buckets = (end - begin) / 4;
		*bucketsOut = buckets;
		if (buckets == 0) { return -1; }   // the game would #DE here, not return
		const uint32_t idx = (key >> 2) % buckets;
		uint32_t node = 0;
		if (!Peek(begin + idx * 4, &node)) { return -1; }
		for (int i = 0; i < 4096 && node; i++)
		{
			uint32_t nkey = 0;
			if (!Peek(node + 4, &nkey)) { return -1; }
			if (nkey == key) { return 1; }
			if (!Peek(node, &node)) { return -1; }
		}
		return 0;
	}

	// v3 THE DECIDING MEASUREMENT for #104.
	//
	// Established by the 2026-08-03 captures (stack + EIP histogram, run 17):
	//   sub_99DD6F  (loop)      enumerates  [esi+0x44]
	//     -> vt+0x5C sub_9DC4AC (remove)
	//       -> vt+0xE0 sub_9DB0FD (REAL removal)  <- reached, so the DEFERRAL
	//          path is REFUTED: sub_9DC4AC only calls vt+0xE0 when
	//          [this+0x18C] <= 0.
	// sub_9DB0FD does Contains(child) FIRST and returns FALSE if absent; the
	// loop tolerates FALSE and retries the SAME first element forever.
	//
	// But the loop enumerates ESI's collection while removing through the
	// object at [esi+4]. So the hypothesis this dump adjudicates is:
	//   THE TWO COLLECTIONS DISAGREE - a child is in [esi+0x44] but not in
	//   [[esi+4]+0x44], making it enumerable but unremovable.
	// If both counts are equal and nonzero, that is REFUTED and the failure
	// is elsewhere in sub_9DB0FD.
	void DumpLoopFields(uintptr_t self, uint32_t tid, uint32_t hits)
	{
		Logger& log = Logger::Get();
		if (self == 0)
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS not captured - the sampler never caught the "
				"thread inside sub_99DD6F. STRUCTURAL null: says nothing about the "
				"collections, only that the probe did not land there.");
			return;
		}

		uint32_t mapA = 0, guardA = 0, headA = 0, owner = 0, mapB = 0, guardB = 0,
				 headB = 0, defer = 0, ownerVt = 0, selfVt = 0;
		Peek(self, &selfVt);
		Peek(self + 0x44, &mapA);
		Peek(self + 0x04, &owner);
		if (mapA) { Peek(mapA, &headA); Peek(mapA + 4, &guardA); }
		if (owner)
		{
			Peek(owner, &ownerVt);
			Peek(owner + 0x44, &mapB);
			Peek(owner + 0x18C, &defer);
			if (mapB) { Peek(mapB, &headB); Peek(mapB + 4, &guardB); }
		}
		// The SENTINEL is [list+0], not the list object. Passing mapA here made
		// the walk unable to terminate and it just hit the 4096 cap, which then
		// got read as "4096 children". Sentinel semantics, from the loop's own
		// bytes: eax=[esi+0x44] (list), ecx=[eax] (sentinel), edx=[ecx] (first).
		const int countA = CountList(headA);
		const int countB = CountList(headB);

		// THE DECIDING FIELD (identified 2026-08-03 by the cIGZWinMgr RE pass).
		// Names, all CONFIRMED from the bytes:
		//   esi          = the cGZWin running ChildDeleteAll (0x0099DD6F, its
		//                  vtable slot 18); only caller is ~cGZWin at 0x0099E1AC
		//   [esi+0x44]   = that window's CHILD LIST
		//   [esi+0x04]   = m_pWinMgr (cIGZWinMgr, service 0xA417445E, IID 1444)
		//   mgr vt+0x5C  = DestroyWindow, vt+0x60 = IsWindowValid
		//
		// DoDestroyWindow (0x009DB0FD) unlinks the child by calling
		//     parent->vt[0x44](child)   where parent = child->GetParentWin()
		//                                            = [child+0x48]
		// i.e. it asks the child's OWN PARENT POINTER to unlink it - NOT the
		// window whose list actually holds it. cGZWin::ChildDelete's helper
		// (0x0099E2BD) does find(childList, child) and, when not found,
		//     0099E305  xor al,al   ; return false, having unlinked NOTHING
		// ChildDeleteAll records that failure in bl and NEVER TESTS IT, so it
		// re-reads the same first child and retries forever.
		//
		// => THE PREDICTION: [firstChild + 0x48] != esi.
		// A child whose parent pointer disagrees with the list it is in is
		// enumerable but unremovable. This reads exactly that.
		uint32_t firstNode = 0, firstChild = 0, childParent = 0, childId = 0;
		if (headA) { Peek(headA, &firstNode); }
		if (firstNode && firstNode != headA)
		{
			Peek(firstNode + 8, &firstChild);
			if (firstChild)
			{
				Peek(firstChild + 0x48, &childParent);
				Peek(firstChild + 0x0C, &childId); // best-effort id field
			}
		}

		log.WriteLine(LogLevel::Info,
			"SPINPROBE #104FIELDS tid=%u hits=%u this=0x%08X vt=0x%08X "
			"A(this+0x44)=0x%08X countA=%d guardA=%d | owner=[this+4]=0x%08X "
			"vt=0x%08X B(owner+0x44)=0x%08X countB=%d guardB=%d defer(+0x18C)=%d",
			tid, hits, static_cast<uint32_t>(self), selfVt, mapA, countA, guardA,
			owner, ownerVt, mapB, countB, guardB, static_cast<int>(defer));

		log.WriteLine(LogLevel::Info,
			"SPINPROBE #104FIELDS CHILD firstNode=0x%08X firstChild=0x%08X "
			"child+0x48(parent)=0x%08X childId=0x%08X  loopWindow=0x%08X",
			firstNode, firstChild, childParent, childId,
			static_cast<uint32_t>(self));

		// ---- ALL children, with the field that ADJUDICATES the verdict ----
		// The RE pass concluded (CONFIRMED by call-graph elimination) that
		// "absent from the valid set" means ~cGZWin ALREADY RAN for that object:
		// hs_erase has one caller, reachable only via mgr vt+0x54, and of 602
		// `call [reg+0x54]` sites exactly one has a m_pWinMgr receiver with a
		// window argument - 0x0099E1C7, inside cGZWin::~cGZWin (0x0099E1A2).
		//
		// ~cGZWin overwrites the vptr with the BARE cGZWin vtable at 0x0099E1A6.
		// So the child's [+0x00] is the discriminator, and it was written down
		// BEFORE the value was seen:
		//     vptr == 0x00ADC8D8 (bare cGZWin)  -> destructed. VERDICT HOLDS.
		//     vptr == a live DERIVED vtable     -> VERDICT IS WRONG, and the
		//         next suspect is a SECOND cIGZWinMgr instance (which is why
		//         validity is tested against BOTH managers below).
		// Dumping all three children, not just the first: the other two may be
		// healthy, and "1 of 3 rotten" vs "3 of 3 rotten" are different bugs.
		{
			uint32_t node = firstNode;
			for (int i = 0; i < 8 && node && node != headA; i++)
			{
				uint32_t ch = 0;
				if (!Peek(node + 8, &ch) || ch == 0) { break; }
				uint32_t vptr = 0, ownMgr = 0, refc = 0, id = 0, kids = 0, par = 0;
				Peek(ch + 0x00, &vptr);
				Peek(ch + 0x04, &ownMgr);
				Peek(ch + 0x0C, &refc);
				Peek(ch + 0x10, &id);
				Peek(ch + 0x44, &kids);
				Peek(ch + 0x48, &par);
				uint32_t bk1 = 0, bk2 = 0;
				const int vLoop = ReplicateIsWindowValid(owner, ch, &bk1);
				const int vOwn  = ReplicateIsWindowValid(ownMgr, ch, &bk2);
				log.WriteLine(LogLevel::Info,
					"SPINPROBE #104FIELDS CHILD[%d] ptr=0x%08X vptr=0x%08X mgr=0x%08X "
					"ref=%d id=0x%08X childList=0x%08X parent=0x%08X "
					"valid(loopMgr)=%s valid(ownMgr)=%s%s",
					i, ch, vptr, ownMgr, static_cast<int>(refc), id, kids, par,
					vLoop == 1 ? "TRUE" : (vLoop == 0 ? "FALSE" : "?"),
					vOwn  == 1 ? "TRUE" : (vOwn  == 0 ? "FALSE" : "?"),
					(ownMgr != owner && ownMgr != 0) ? "   <== DIFFERENT MANAGER" : "");
				if (!Peek(node, &node)) { break; }
			}
		}

		// Pre-committed reading, written BEFORE any value was known.
		if (firstChild == 0)
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS VERDICT: could not read the first child - "
				"STRUCTURAL null, decides nothing.");
		}
		else if (childParent != static_cast<uint32_t>(self))
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS VERDICT: *** PARENT-POINTER MISMATCH *** "
				"child 0x%08X sits in window 0x%08X's child list but its "
				"m_pParentWin says 0x%08X. DoDestroyWindow unlinks via the CHILD'S "
				"parent pointer, so it asks the wrong window, ChildDelete returns "
				"false without unlinking, and ChildDeleteAll retries forever. "
				"THIS IS THE BUG - and the fix is to stop the reparent that "
				"desynced them, NOT to touch the loop.",
				firstChild, static_cast<uint32_t>(self), childParent);
		}
		else
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS VERDICT: parent pointer AGREES (0x%08X) - the "
				"reparent hypothesis is REFUTED for this child. The unlink fails for "
				"another reason; next suspect is the find inside 0x0099E2BD.",
				childParent);
		}
		log.WriteLine(LogLevel::Info,
			"SPINPROBE #104FIELDS context: countA(childList)=%d countB(mgr valid "
			"set)=%d. countB is the WinMgr's global valid-window set, a different "
			"kind of collection - it is context, not the comparison.",
			countA, countB);

		// THE VALIDITY TEST. DoDestroyWindow (0x009DB0FD) opens with
		//     bl = mgr->IsWindowValid(child)
		// and if bl is FALSE it skips GetParentWin, falls to 0x9DB13D, and
		//     0x9DB15A  xor al,al   ; returns FALSE having unlinked NOTHING
		// ChildDeleteAll discards that FALSE and retries the same child. So an
		// invalid child is enumerable, unremovable, and immortal.
		// ================= POSITIVE CONTROL (added 2026-08-03) ==============
		// ReplicateIsWindowValid has returned FALSE for every window it has
		// ever been pointed at, and I reported "THIS IS THE MECHANISM" off it
		// WITHOUT EVER SHOWING IT CAN RETURN TRUE. That is a structural null
		// dressed as a finding - the exact error this project has a law about.
		//
		// So: enumerate the valid set directly, then feed one of ITS OWN keys
		// back through the replication. If the lookup cannot find a key we
		// literally just read out of the table, the replication is WRONG and
		// every FALSE it has ever produced - including the mechanism verdict -
		// is void.
		{
			uint32_t begin = 0, end = 0;
			Peek(owner + 0x48, &begin);
			Peek(owner + 0x4C, &end);
			const uint32_t nb = (begin && end > begin) ? (end - begin) / 4 : 0;
			uint32_t total = 0, sampleKey = 0, occupied = 0;
			for (uint32_t b = 0; b < nb && b < 8192; b++)
			{
				uint32_t node = 0;
				if (!Peek(begin + b * 4, &node)) { break; }
				if (node) { occupied++; }
				for (int g = 0; g < 512 && node; g++)
				{
					uint32_t k = 0;
					if (!Peek(node + 4, &k)) { break; }
					if (k && sampleKey == 0) { sampleKey = k; }
					total++;
					if (!Peek(node, &node)) { break; }
				}
			}
			uint32_t bk = 0;
			const int self0 = sampleKey ? ReplicateIsWindowValid(owner, sampleKey, &bk) : -1;
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS SELFTEST validset begin=0x%08X end=0x%08X buckets=%u "
				"occupied=%u entries=%u sampleKey=0x%08X lookup(sampleKey)=%s",
				begin, end, nb, occupied, total, sampleKey,
				self0 == 1 ? "TRUE" : (self0 == 0 ? "FALSE" : "N/A"));
			if (self0 == 1)
			{
				log.WriteLine(LogLevel::Info,
					"SPINPROBE #104FIELDS SELFTEST PASS - the replication CAN return TRUE, "
					"so a FALSE for a child is a MEASURED null and the mechanism stands.");
			}
			else if (total == 0)
			{
				// This is what run22 actually hit, and the old wording led with
				// "THE REPLICATION IS WRONG" - which was NOT the finding. An
				// empty table is a real measurement, not a broken instrument.
				log.WriteLine(LogLevel::Info,
					"SPINPROBE #104FIELDS SELFTEST INCONCLUSIVE-BY-EMPTY - the valid set holds "
					"ZERO entries across %u buckets, so there was no key to test the lookup "
					"with. The replication is NOT implicated. The finding is that THE SET IS "
					"EMPTY: IsWindowValid correctly returns FALSE for every window, so every "
					"DoDestroyWindow no-ops. See the #104ORDER lines for WHEN it emptied.", nb);
			}
			else
			{
				log.WriteLine(LogLevel::Info,
					"SPINPROBE #104FIELDS SELFTEST *** FAIL *** - the table holds %u entries but "
					"the lookup cannot find a key read straight out of it. THE REPLICATION IS "
					"WRONG and every FALSE it produced is VOID.", total);
			}
		}

		uint32_t buckets = 0;
		const int valid = ReplicateIsWindowValid(owner, firstChild, &buckets);
		log.WriteLine(LogLevel::Info,
			"SPINPROBE #104FIELDS VALIDSET mgr=0x%08X begin/end-derived buckets=%u "
			"IsWindowValid(firstChild 0x%08X) = %s",
			owner, buckets, firstChild,
			valid == 1 ? "TRUE" : (valid == 0 ? "FALSE" : "UNEVALUABLE"));
		if (valid == 0)
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS VERDICT-VALID: *** THE CHILD IS NOT IN THE "
				"WINDOW MANAGER'S VALID SET *** DoDestroyWindow therefore returns "
				"FALSE without unlinking, and ChildDeleteAll retries it forever. "
				"THIS IS THE MECHANISM. The child was dropped from the valid set "
				"while still linked as a child - find WHO removes it (mgr vt+0x58 "
				"RemoveWindowFromValidList) and why it ran early.");
		}
		else if (valid == 1)
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS VERDICT-VALID: the child IS valid - this "
				"mechanism is REFUTED. DoDestroyWindow should have taken the "
				"GetParentWin path; the failure is then in ChildDelete's find "
				"(0x009D07A0) despite the child being list-resident.");
		}
		else
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS VERDICT-VALID: UNEVALUABLE (buckets=%u) - "
				"STRUCTURAL null. The valid-set table could not be read, which "
				"decides nothing either way.", buckets);
		}

		// Copy-on-write verdict, pre-committed.
		log.WriteLine(LogLevel::Info,
			"SPINPROBE #104FIELDS COW listPtr first=0x%08X last=0x%08X changes=%u "
			"over %u loop samples.",
			gListPtrFirst, gListPtrLast, gListPtrChanges, gLoopHits);
		if (gListPtrChanges > 0)
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS VERDICT-COW: *** THE CHILD LIST OBJECT IS BEING "
				"SWAPPED *** (%u changes). sub_99E08F clones the list and rebinds "
				"[this+0x44] whenever the iteration guard is held, so ChildDelete "
				"erases from one object while ChildDeleteAll re-reads another. "
				"Enumerate and erase have diverged - THIS IS THE BUG.",
				gListPtrChanges);
		}
		else
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS VERDICT-COW: list pointer STABLE (0 changes) - "
				"the copy-on-write swap is REFUTED. The list object never moves, so "
				"the failure is inside the find at 0x009D07A0 or the erase itself.");
		}
		if (defer != 0)
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE #104FIELDS NOTE: defer=%d is NONZERO - the sub_9DC4AC "
				"deferral path is live after all; re-open that candidate.",
				static_cast<int>(defer));
		}
	}

	// ===================== #104 THE FIX ==============================
	// Break cGZWin::ChildDeleteAll's immortal loop by making its child list
	// report EMPTY. Two 4-byte writes, no game code called.
	//
	// WHY THE LOOP CANNOT END ON ITS OWN (all measured, 6 reproductions):
	//   ~cGZWinMgr (0x009DC172) destructs the window manager FIRST - its
	//   hashtable dtor clears every bucket and FREES the bucket array while
	//   leaving [set+4]/[set+8] dangling. Then ~cGZMessageServer (0x0092FE56)
	//   drains its notification map and Releases windows that were still
	//   registered as message targets. Those windows' destructors run
	//   ChildDeleteAll, whose every removal goes through
	//   mgr->IsWindowValid() - which now answers FALSE for EVERY window
	//   because the set is gone. DoDestroyWindow then returns FALSE having
	//   unlinked nothing, ChildDeleteAll records that failure and NEVER TESTS
	//   IT, and re-reads the same first child forever.
	//
	// WHY THIS SHAPE AND NOT A CALL INTO THE GAME:
	//   The obvious repair is parent->ChildDelete(child). It was proposed as
	//   vtable slot +0x3C - but the LIVE vtable says +0x3C is 0x0099EA6B, not
	//   the expected 0x0099E2BD; +0x44 is ChildDelete. Calling the wrong slot
	//   would have executed an unknown function. Worse, ChildDelete's helper
	//   (0x0099E2BD) calls mgr->IsWindowValid, which READS THE FREED BUCKET
	//   ARRAY, and sub_99E08F would clone-and-rebind the list if the iteration
	//   guard were held. All of that risk disappears if we never call in.
	//
	// From the loop's own bytes at 0x0099DD76:
	//     mov eax,[esi+0x44]   ; list object
	//     mov ecx,[eax]        ; sentinel = [list+0]
	//     inc dword [eax+4]    ; iteration guard
	//     mov edx,[ecx]        ; first    = [sentinel]
	//     cmp edx,ecx          ; EMPTY when first == sentinel  <- only exit
	// So pointing the sentinel at itself makes the next test read empty and
	// the loop returns.
	//
	// SAFETY, deliberately conservative:
	//   * only when the spin is MEASURED (a thread running game code inside
	//     the loop range), never speculatively;
	//   * the target thread is SUSPENDED across the writes;
	//   * refuses unless the iteration guard [list+4] == 0, so we never mutate
	//     while the game holds the list open (that is what would make
	//     sub_99E08F clone it);
	//   * every pointer is range-checked before it is written through;
	//   * ONE attempt per launch.
	//   * It leaks the 3 child windows. The process is seconds from exit and
	//     currently never gets there at all - leaking at exit is strictly
	//     better than not exiting.
	bool gSpinFixEnabled = true;   // [UiSpike] SpinFix, default ON
	uint32_t gWaitLogged = 0;      // throttle for the "waiting" line

	// v2.62.0: the fix is REPEATABLE, not one-shot.
	//
	// ~cGZMessageServer drains its whole notification map and releases EVERY
	// window still subscribed. Each one's ~cGZWin runs ChildDeleteAll. If more
	// than one window was orphaned, curing the first loop simply lets the next
	// begin - and v2.61.2 latched after a single success, so it would fix one
	// and then watch the rest hang. Remember which sentinels are already
	// emptied (so we never re-write the same one) and keep going.
	const int kMaxFixes = 64;
	uint32_t gFixedSentinels[kMaxFixes] = {};
	int      gFixCount = 0;

	bool AlreadyFixed(uint32_t sentinel)
	{
		for (int i = 0; i < gFixCount; i++)
		{
			if (gFixedSentinels[i] == sentinel) { return true; }
		}
		return false;
	}

	// POST-CONDITION. "The process vanished" cannot tell an exit from an End
	// Task - that ambiguity produced a false 'it worked' report. This counts
	// game-code samples on the hot thread AFTER a fix lands, which is direct
	// evidence of whether the loop actually returned.
	uint32_t gSamplesAtFix = 0;
	bool     gVerdictLogged = false;
	// Set INSIDE the suspension (where logging is forbidden), printed after
	// the thread resumes. 0 none, 1 guard held, 2 already empty, 3 APPLIED,
	// 4 write failed, 5 fields unreadable.
	volatile int gFixNote = 0;
	uint32_t gFixList = 0, gFixSentinel = 0, gFixFirst = 0, gFixTid = 0, gFixWin = 0;
	// TrySpinFix() was REMOVED in v2.62.0. It attempted the repair from the
	// once-a-second report, which lost two races in a row: v2.61.0 ran before
	// gLoopThis existed and returned mute; v2.61.1 latched "tried" ahead of the
	// EIP guard so the first refusal burned the only attempt. The repair now
	// happens inside SampleOnce, at the instant the sampler already holds the
	// thread suspended inside ChildDeleteAll - the preconditions hold by
	// construction instead of by luck. Deleted rather than left dead, so
	// nobody reads it as live code.


	// v2: STACK SCAN of the spinning thread. The leaf EIP says WHAT is looping;
	// the stack says WHO called it, and that is what names the subsystem.
	//
	// We could not do this from outside: the game runs ELEVATED, and an
	// unelevated OpenProcess for VM_READ fails with ERROR_ACCESS_DENIED (5),
	// measured 2026-08-03. From inside the process there is no such barrier.
	//
	// This is a SCAN, not a true unwind. Optimised frames have no reliable
	// ebp chain, so we read the raw stack and report every dword that points
	// into the game image. Some hits will be stale frames or data that merely
	// looks like a code pointer - the output is CANDIDATES in stack order, and
	// the log says so, because a scan mislabelled as a call stack would be
	// exactly the kind of confident-wrong instrument that has cost runs here.
	void StackScan(uint32_t tid)
	{
		Logger& log = Logger::Get();

		HANDLE h = OpenThread(
			THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION,
			FALSE, tid);
		if (h == nullptr)
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE stack: OpenThread(%u) failed (err %lu) - no scan.",
				tid, GetLastError());
			return;
		}

		static uint8_t buf[kStackScanBytes];
		// esi is the loop's `this` in sub_99DD6F (mov esi,ecx at 0x99DD72),
		// which is why CONTEXT_INTEGER is requested alongside CONTEXT_CONTROL.
		uintptr_t eip = 0, esp = 0, ebp = 0, esi = 0;
		SIZE_T copied = 0;
		bool haveCtx = false;

		// --- suspension window: capture and COPY, never log ---
		if (SuspendThread(h) != static_cast<DWORD>(-1))
		{
			CONTEXT ctx = {};
			ctx.ContextFlags = CONTEXT_CONTROL | CONTEXT_INTEGER;
			if (GetThreadContext(h, &ctx))
			{
#if defined(_M_IX86)
				eip = ctx.Eip; esp = ctx.Esp; ebp = ctx.Ebp; esi = ctx.Esi;
#elif defined(_M_X64)
				eip = ctx.Rip; esp = ctx.Rsp; ebp = ctx.Rbp;
#endif
				haveCtx = (esp != 0);
			}
			if (haveCtx)
			{
				// Clamp to the thread's own stack region so we never read off
				// the end of the committed range.
				MEMORY_BASIC_INFORMATION mbi = {};
				SIZE_T want = kStackScanBytes;
				if (VirtualQuery(reinterpret_cast<LPCVOID>(esp), &mbi, sizeof(mbi)) == sizeof(mbi))
				{
					const uintptr_t regionEnd =
						reinterpret_cast<uintptr_t>(mbi.BaseAddress) + mbi.RegionSize;
					if (regionEnd > esp && (regionEnd - esp) < want)
					{
						want = regionEnd - esp;
					}
				}
				// ReadProcessMemory on ourselves: a bad address returns FALSE
				// instead of raising, which a raw memcpy would not.
				if (!ReadProcessMemory(GetCurrentProcess(),
						reinterpret_cast<LPCVOID>(esp), buf, want, &copied))
				{
					copied = 0;
				}
			}
			ResumeThread(h);
		}
		// --- suspension window closed ---
		CloseHandle(h);

		if (!haveCtx)
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE stack: could not capture context for tid %u - STRUCTURAL "
				"null, not a finding about the stack.", tid);
			return;
		}
		log.WriteLine(LogLevel::Info,
			"SPINPROBE stack tid %u: eip=0x%08X esp=0x%08X ebp=0x%08X, read %u bytes. "
			"Image 0x%08X..0x%08X. Lines below are CANDIDATE return addresses in stack "
			"order (a raw scan, NOT a verified unwind - stale frames can appear).",
			tid, static_cast<uint32_t>(eip), static_cast<uint32_t>(esp),
			static_cast<uint32_t>(ebp), static_cast<uint32_t>(copied),
			static_cast<uint32_t>(gImgLo), static_cast<uint32_t>(gImgHi));

		// v3: the field dump moved OUT of here. Gating it on the EIP being in
		// the loop at this single instant never fired (the thread was in a
		// callee at 0x009DB8A4); it is now captured opportunistically across
		// every sweep via gLoopThis and reported by DumpLoopFields().

		if (copied < 4)
		{
			log.WriteLine(LogLevel::Info,
				"SPINPROBE stack: read %u bytes - nothing to scan.",
				static_cast<uint32_t>(copied));
			return;
		}

		// v4 - MY OWN INSTRUMENT BUG, found 2026-08-03 and worth recording.
		// This loop used to `continue` on !InGameImage(v), i.e. it could ONLY
		// EVER print game frames - and the probe then closed by asking "if the
		// top address is in a DIFFERENT module, #104's framing is wrong", a
		// question the filter made unanswerable. I reported "every frame is the
		// game" as evidence that no mod was involved; that was a STRUCTURAL
		// null, not a measurement. A stack scan that cannot show a foreign
		// frame cannot testify about foreign frames.
		//
		// Now every dword that lands in ANY loaded module is attributed and
		// printed with its module name. That is what makes OURS vs GAME vs
		// THIRD-PARTY answerable.
		int hits = 0, foreign = 0;
		for (SIZE_T off = 0; off + 4 <= copied; off += 4)
		{
			uint32_t v = 0;
			memcpy(&v, buf + off, 4);
			if (v < 0x10000) { continue; }          // not a code pointer
			char mod[64];
			uintptr_t va = 0;
			DescribeAddress(v, mod, sizeof(mod), &va);
			if (mod[0] == '?') { continue; }        // not inside any module
			const bool game = InGameImage(v);
			if (!game) { foreign++; }
			log.WriteLine(LogLevel::Info,
				"SPINPROBE stack   +0x%04X  0x%08X  %-18s va@%06X=0x%08X%s",
				static_cast<uint32_t>(off), v, mod,
				static_cast<uint32_t>(kPreferredImageBase),
				static_cast<uint32_t>(va), game ? "" : "   <== NOT THE GAME");
			if (++hits >= 64)
			{
				log.WriteLine(LogLevel::Info,
					"SPINPROBE stack   (capped at 64 frames - deeper frames not shown)");
				break;
			}
		}
		log.WriteLine(LogLevel::Info,
			"SPINPROBE stack: %d module-resolved frames, %d of them OUTSIDE SimCity 4.exe. "
			"%s", hits, foreign,
			hits == 0
				? "Zero resolvable frames - STRUCTURAL null, decides nothing."
				: (foreign == 0
					? "A MEASURED null for foreign code: the scan CAN name other modules "
					  "(it resolves every module, not just the game) and found none here."
					: "Foreign frames present - identify them before blaming the game."));
	}

	// One sweep over every other thread in this process. Returns the number
	// of samples captured. NOTHING in here logs - a suspension is live for a
	// few instructions at a time and the Logger takes a lock that a suspended
	// thread may be holding.
	int SampleOnce(Tally& t, DWORD selfTid, DWORD selfPid)
	{
		HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
		if (snap == INVALID_HANDLE_VALUE) { return 0; }

		THREADENTRY32 te = {};
		te.dwSize = sizeof(te);
		int got = 0;

		if (Thread32First(snap, &te))
		{
			do
			{
				if (te.dwSize < FIELD_OFFSET(THREADENTRY32, th32OwnerProcessID) +
						sizeof(te.th32OwnerProcessID)) { continue; }
				if (te.th32OwnerProcessID != selfPid) { continue; }
				if (te.th32ThreadID == selfTid) { continue; }

				t.threadsSeen++;
				ThreadBucket* tb = TallyThread(t, te.th32ThreadID);

				HANDLE h = OpenThread(
					THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT,
					FALSE, te.th32ThreadID);
				if (h == nullptr)
				{
					t.opensFailed++;
					if (tb) { tb->failures++; }
					continue;
				}
				t.opensOk++;

				// --- suspension window opens ---
				uintptr_t eip = 0;
				bool ok = false;
				if (SuspendThread(h) != static_cast<DWORD>(-1))
				{
					CONTEXT ctx = {};
					// v3: INTEGER too - esi is the loop's `this` and we must
					// grab it opportunistically (see gLoopThis).
					ctx.ContextFlags = CONTEXT_CONTROL | CONTEXT_INTEGER;
					if (GetThreadContext(h, &ctx))
					{
#if defined(_M_IX86)
						eip = static_cast<uintptr_t>(ctx.Eip);
						if (gImgLo != 0)
						{
							const uintptr_t lo = gImgLo + (0x0099DD6F - kPreferredImageBase);
							const uintptr_t hi = gImgLo + (0x0099DDB2 - kPreferredImageBase);
							if (eip >= lo && eip <= hi && ctx.Esi != 0)
							{
								gLoopThis = static_cast<uintptr_t>(ctx.Esi);
								gLoopTid = te.th32ThreadID;
								gLoopHits++;

								// ===== #104 THE FIX, APPLIED RIGHT HERE =====
								// This is the ONE moment that satisfies every
								// precondition at once: the thread is ALREADY
								// suspended, and its EIP is ALREADY inside
								// ChildDeleteAll. Two previous versions tried to
								// act from the once-a-second report and failed -
								// v2.61.0 ran before gLoopThis existed and
								// returned mute; v2.61.1 latched "tried" BEFORE
								// the EIP guard, so the first refusal consumed
								// the only attempt. Doing it here removes the
								// race instead of retrying against it.
								// NOTHING logs inside the suspension - results
								// are stashed and printed after ResumeThread.
								// v2.67.0 (#114): LoopBytesVerified() is the
								// verify-before-write this site never had. It
								// is checked LAST so the cheap flags
								// short-circuit first, and it memoises, so the
								// byte compare happens once per session.
								if (gSpinFixEnabled && gSpunWritten &&
									gFixCount < kMaxFixes && LoopBytesVerified())
								{
									uint32_t lst = 0, grd = 0, sen = 0, fst = 0;
									if (Peek(ctx.Esi + 0x44, &lst) && lst &&
										Peek(lst + 4, &grd) &&
										Peek(lst, &sen) && sen &&
										Peek(sen, &fst))
									{
										if (fst == sen)
										{
											// already empty - nothing to do, and
											// NOT a reason to stop: a different
											// window may still be stuck.
										}
										else if (AlreadyFixed(sen))
										{
											// we emptied this one and it refilled
											gFixNote = 6;
											gFixSentinel = sen;
										}
										else if (grd != 0)
										{
											gFixNote = 1;   // guard held, retry
										}
										else
										{
											SIZE_T w = 0;
											const BOOL a = WriteProcessMemory(
												GetCurrentProcess(),
												reinterpret_cast<LPVOID>(sen),
												&sen, 4, &w);
											const BOOL b = WriteProcessMemory(
												GetCurrentProcess(),
												reinterpret_cast<LPVOID>(sen + 4),
												&sen, 4, &w);
											gFixNote = (a && b) ? 3 : 4;
											gFixList = lst;
											gFixSentinel = sen;
											gFixFirst = fst;
											gFixTid = te.th32ThreadID;
											gFixWin = static_cast<uint32_t>(ctx.Esi);
											if (a && b)
											{
												gFixedSentinels[gFixCount++] = sen;
												gSamplesAtFix = t.samples;
												gVerdictLogged = false;
											}
										}
									}
									else
									{
										gFixNote = 5;       // unreadable, retry
									}
								}
								// Watch [this+0x44] for the copy-on-write swap.
								uint32_t lp = 0;
								SIZE_T rd = 0;
								if (ReadProcessMemory(GetCurrentProcess(),
										reinterpret_cast<LPCVOID>(ctx.Esi + 0x44),
										&lp, 4, &rd) && rd == 4 && lp != 0)
								{
									if (gListPtrFirst == 0) { gListPtrFirst = lp; }
									else if (lp != gListPtrLast) { gListPtrChanges++; }
									gListPtrLast = lp;
								}
							}
						}
#elif defined(_M_X64)
						eip = static_cast<uintptr_t>(ctx.Rip);
#endif
						ok = (eip != 0);
					}
					ResumeThread(h);
				}
				// --- suspension window closed; safe to touch anything again ---

				CloseHandle(h);

				if (ok)
				{
					TallyEip(t, eip, te.th32ThreadID);
					if (tb)
					{
						tb->samples++;
						if (InGameImage(eip)) { tb->gameSamples++; }
					}
					t.samples++;
					got++;
				}
				else
				{
					t.ctxFailed++;
					if (tb) { tb->failures++; }
				}
			} while (Thread32Next(snap, &te));
		}

		CloseHandle(snap);
		t.sweeps++;
		return got;
	}

	DWORD WINAPI SamplerProc(LPVOID param)
	{
		const int seconds = static_cast<int>(reinterpret_cast<intptr_t>(param));
		const DWORD selfTid = GetCurrentThreadId();
		const DWORD selfPid = GetCurrentProcessId();

		InitImageRange();

		Tally t;
		TallyInit(t);

		// SELF-TEST before the interesting window: one sweep, reported
		// immediately. If this says 0 samples, every later null is the
		// probe's fault and the log will already say so in its own words.
		const int first = SampleOnce(t, selfTid, selfPid);
		Logger::Get().WriteLine(
			LogLevel::Info,
			"SPINPROBE armed for %ds at %dHz - self-test sweep captured %d "
			"sample(s) from %d thread(s). Sampling begins now; the game's own "
			"teardown is what runs from here.",
			seconds, 1000 / kSampleIntervalMs, first, t.threadCount);

		const DWORD started = GetTickCount();
		const DWORD deadline = started + static_cast<DWORD>(seconds) * 1000u;
		DWORD nextPartial = started + kPartialEverySec * 1000u;

		while (GetTickCount() < deadline)
		{
			SampleOnce(t, selfTid, selfPid);
			if (GetTickCount() >= nextPartial)
			{
				// Emit as we go: if the process does manage to exit, the
				// evidence is already on disk.
				ReportTally(t, "partial");
				nextPartial += kPartialEverySec * 1000u;

				// Record the SPIN verdict the moment it is unambiguous, not
				// at the end - a run that gets End-Tasked before the deadline
				// must still count as SPUN, or the rate we are building
				// silently biases toward clean.
				// #104 ORDERING. run22 measured the manager's valid set EMPTY
				// (1543 buckets, 0 entries) while ChildDeleteAll span forever.
				// An empty set may be entirely CORRECT at this point - the
				// manager plausibly clears it during its own shutdown, by which
				// time every window should already be gone. If so the defect is
				// not the empty set, it is that THIS WINDOW OUTLIVED the
				// manager's teardown.
				//
				// The discriminator is WHEN it emptied. Sampling the count each
				// second: already 0 at the first sample => it emptied before the
				// spin began (window outlived the manager). Draining across
				// samples => it is being emptied while we watch, and the race is
				// visible.
				if (gLoopThis != 0)
				{
					uint32_t owner = 0, begin = 0, end = 0;
					if (Peek(gLoopThis + 4, &owner) && owner &&
						Peek(owner + 0x48, &begin) && Peek(owner + 0x4C, &end) &&
						begin && end > begin)
					{
						const uint32_t nb = (end - begin) / 4;
						uint32_t entries = 0, occ = 0;
						for (uint32_t b = 0; b < nb && b < 8192; b++)
						{
							uint32_t node = 0;
							if (!Peek(begin + b * 4, &node)) { break; }
							if (node) { occ++; }
							for (int g = 0; g < 512 && node; g++)
							{
								entries++;
								if (!Peek(node, &node)) { break; }
							}
						}
						Logger::Get().WriteLine(LogLevel::Info,
							"SPINPROBE #104ORDER t+%us validset buckets=%u occupied=%u entries=%u",
							(GetTickCount() - started) / 1000u, nb, occ, entries);
					}
				}

				if (!gSpunWritten)
				{
					const ThreadBucket* hot = HottestGameThread(t);
					if (hot && hot->gameSamples >= 3)
					{
						uintptr_t topEip = 0;
						uint32_t topHits = 0;
						for (int i = 0; i < t.eipCount; i++)
						{
							if (!InGameImage(t.eips[i].eip)) { continue; }
							if (t.eips[i].count > topHits)
							{
								topHits = t.eips[i].count;
								topEip = t.eips[i].eip;
							}
						}
						const uintptr_t va = (topEip && gImgLo)
							? (topEip - gImgLo + kPreferredImageBase) : 0;
						char detail[160];
						sprintf_s(detail, sizeof(detail),
							"tid=%u gameSamples=%u topVa=0x%08X",
							hot->tid, hot->gameSamples, static_cast<uint32_t>(va));
						WriteCsvRow("spun", detail);
						gSpunWritten = true;
						Logger::Get().WriteLine(LogLevel::Info,
							"SPINPROBE recorded verdict=spun to SC4UIScale-104.csv (%s).",
							detail);
					}
				}

				// #104 THE FIX now applies inside SampleOnce, at the instant the
				// sampler catches the thread suspended inside ChildDeleteAll.
				// This block only REPORTS what happened there - logging is
				// forbidden while a thread is suspended, so the outcome is
				// stashed in gFixNote and printed here.
				if (gFixNote != 0)
				{
					const int note = gFixNote;
					gFixNote = 0;
					switch (note)
					{
					case 3:
						Logger::Get().WriteLine(LogLevel::Info,
							"SPINFIX APPLIED #%d win=0x%08X tid=%u list=0x%08X sentinel=0x%08X "
							"(was ->0x%08X, now ->itself). ChildDeleteAll's empty "
							"test should now pass and the loop should return. If "
							"the process exits, #104 is cured AT THE SYMPTOM; the "
							"CAUSE (cGZWinGen orphaned by ChildRemove without "
							"Shutdown, outliving ~cGZWinMgr) is the game's and "
							"is still held.",
							gFixCount, gFixWin, gFixTid, gFixList, gFixSentinel, gFixFirst);
						break;
					case 2:
						Logger::Get().WriteLine(LogLevel::Info,
							"SPINFIX no-op - the child list already reported empty.");
						break;
					case 4:
						Logger::Get().WriteLine(LogLevel::Error,
							"SPINFIX WRITE FAILED tid=%u sentinel=0x%08X (err %lu) - "
							"will retry on the next capture.",
							gFixTid, gFixSentinel, GetLastError());
						break;
					case 6:
						Logger::Get().WriteLine(LogLevel::Info,
							"SPINFIX sentinel 0x%08X REFILLED after we emptied it - "
							"something is re-adding children, so emptying the list "
							"is not sufficient. Leaving it alone.", gFixSentinel);
						break;
					case 1:
						if ((gWaitLogged++ % 10) == 0)
						{
							Logger::Get().WriteLine(LogLevel::Info,
								"SPINFIX deferred - iteration guard HELD at the "
								"moment of capture. Refusing to mutate a list the "
								"game has open; retrying on the next capture.");
						}
						break;
					default:
						if ((gWaitLogged++ % 10) == 0)
						{
							Logger::Get().WriteLine(LogLevel::Info,
								"SPINFIX deferred - list/sentinel unreadable at "
								"capture; retrying.");
						}
						break;
					}
				}

				// POST-CONDITION, ~2s after the latest fix. MEASURED 2026-08-03:
				// one fix APPLIED and tid 3520 kept accruing game samples
				// (218 -> 261 in 5s) - the loop did NOT stop. "The process
				// vanished" cannot tell a clean exit from an End Task, so the
				// only honest evidence is whether game-code samples keep
				// climbing on the hot thread.
				if (gFixCount > 0 && !gVerdictLogged &&
					t.samples >= gSamplesAtFix + 40)
				{
					gVerdictLogged = true;
					const ThreadBucket* hb = HottestGameThread(t);
					Logger::Get().WriteLine(LogLevel::Info,
						"SPINFIX VERDICT after %d fix(es): %s (hot tid=%u "
						"gameSamples=%u). %s",
						gFixCount,
						hb ? "a thread is STILL running game code"
						   : "NO thread is running game code any more",
						hb ? hb->tid : 0, hb ? hb->gameSamples : 0,
						hb ? "Either that loop did not stop, or ANOTHER window's "
							 "ChildDeleteAll took over. The fix now repeats per "
							 "DISTINCT list, so expect further APPLIED lines - "
							 "judge only after they stop coming."
						   : "The loop RETURNED; the process should be in normal "
							 "teardown now.");
				}
			}
			Sleep(kSampleIntervalMs);
		}

		ReportTally(t, "FINAL");

		// v2: the caller chain. Do this AFTER the sampling loop so the scan's
		// own suspend cannot perturb the samples.
		// v3: the deciding measurement. Independent of where the thread happens
		// to be standing right now, because gLoopThis was captured across every
		// sweep rather than at one instant.
		DumpLoopFields(gLoopThis, gLoopTid, gLoopHits);

		const ThreadBucket* hot = HottestGameThread(t);
		if (hot)
		{
			StackScan(hot->tid);
		}
		else
		{
			Logger::Get().WriteLine(LogLevel::Info,
				"SPINPROBE stack: skipped - no thread ran game code, so there is no "
				"game-code caller chain to walk.");
		}

		Logger::Get().WriteLine(
			LogLevel::Info,
			"SPINPROBE done. A hot EIP inside SimCity 4.exe names the loop: "
			"read va@400000 straight against the disassembly / CodePatches "
			"site tables. If the top address is in a DIFFERENT module, the "
			"spin is not in the game's own code and #104's framing is wrong.");
		return 0;
	}
}

namespace SpinProbe
{
	void NoteWindowId(uint32_t id)
	{
		if (gBudgetSeen) { return; }
		for (uint32_t b : kBudgetRootIds)
		{
			if (id == b) { gBudgetSeen = true; return; }
		}
	}

	void RecordShutdown(const LaunchInfo& info)
	{
		gLaunch = info;
		// v2.67.0 (#114): TELEMETRY IS NOW OPT-IN. gLaunchValid is the single
		// gate WriteCsvRow() early-returns on, so tying it to probeSeconds
		// silences the whole CSV in one place. A shipped build wrote
		// SC4UIScale-104.csv into the player's Plugins folder on EVERY launch,
		// forever, recording their config - for an internal bug hunt (#104 /
		// #107) that means nothing to them and that they never opted into.
		// It is OUR instrument; it turns on when OUR probe is on.
		// NOTE the deliberate ordering: gSpinFixEnabled is still set
		// unconditionally below, because the #104 FIX must keep working when
		// the probe is off. The fix and the telemetry are different things and
		// were only ever entangled by implementation.
		gLaunchValid = (info.probeSeconds > 0);
		gSpinFixEnabled = (info.spinFix != 0);
		// probeSeconds == 0 -> nothing can ever detect a spin this launch, so
		// the row must NOT be readable as evidence of a clean exit.
		WriteCsvRow(info.probeSeconds > 0 ? "pending" : "unknown", "");
		Logger::Get().WriteLine(
			LogLevel::Info,
			"SPINPROBE recorded launch to SC4UIScale-104.csv: verdict=%s "
			"budgetSeen=%d ordinance=%d dept=%d button=%d probeSec=%d. "
			"A pending row with NO later 'spun' row means the process exited "
			"on its own = CLEAN.",
			info.probeSeconds > 0 ? "pending" : "unknown",
			gBudgetSeen ? 1 : 0, info.ordinanceInset ? 1 : 0,
			info.budgetDept ? 1 : 0, info.budgetButton ? 1 : 0,
			info.probeSeconds);
	}

	bool Arm(int seconds)
	{
		if (seconds <= 0) { return false; }
		if (seconds > 120) { seconds = 120; } // hard cap: it is a probe

		HANDLE h = CreateThread(
			nullptr, 0, SamplerProc,
			reinterpret_cast<LPVOID>(static_cast<intptr_t>(seconds)),
			0, nullptr);
		if (h == nullptr)
		{
			Logger::Get().WriteLine(
				LogLevel::Error,
				"SPINPROBE could not start its sampler thread (err %lu) - no "
				"samples will be taken this run.",
				GetLastError());
			return false;
		}
		CloseHandle(h); // fire and forget; it must never block process exit
		return true;
	}
}
