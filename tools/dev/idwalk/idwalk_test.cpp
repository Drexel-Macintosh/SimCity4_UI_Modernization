// Offline test of UiSpike.cpp's BATCHED ID LOOKUPS block (audit A1,
// 2026-09-25). run_idwalk_test.py copies that block, verbatim, into
// idwalk_block.inc and builds this file against a mock window tree.
//
// The reference is a model of the engine's GetChildWindowFromIDRecursive
// (decompiled 0x0099DEC4): post-order, children in EnumChildren order, self
// last, first match wins. It is a MODEL - the in-game IDWALK line (the first
// 2048 walks re-asked of the real engine) is what checks it against the game.
#include <cstdint>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

enum class LogLevel { Error, Info, Debug };
struct Logger
{
	static Logger& Get() { static Logger l; return l; }
	int lines = 0;
	void WriteLine(LogLevel, const char* fmt, ...)
	{
		lines++;
		if (!getenv("IDWALK_SHOWLOG")) { return; }
		va_list ap;
		va_start(ap, fmt);
		vprintf(fmt, ap);
		printf("\n");
		va_end(ap);
	}
};
const uint32_t GZIID_cIGZWin = 0x22BA0121u;

struct cIGZWin
{
	uint32_t id = 0;
	std::vector<cIGZWin*> kids;
	static long long visits;
	static bool skipLast;   // a deliberately broken EnumChildren, for the checker test

	uint32_t GetID() { return id; }
	bool EnumChildren(uint32_t, bool (*cb)(cIGZWin*, uint32_t, void*, void*), void* ctx)
	{
		std::vector<cIGZWin*> snap = kids;
		if (skipLast && !snap.empty()) { snap.pop_back(); }
		for (cIGZWin* k : snap)
		{
			visits++;
			if (!cb(this, k->id, k, ctx)) { return false; }
		}
		return true;
	}
	cIGZWin* GetChildWindowFromIDRecursive(uint32_t wid)
	{
		for (cIGZWin* k : kids)
		{
			visits++;
			cIGZWin* r = k->GetChildWindowFromIDRecursive(wid);
			if (r) { return r; }
		}
		return id == wid ? this : nullptr;
	}
};
long long cIGZWin::visits = 0;
bool cIGZWin::skipLast = false;

namespace
{
#include "idwalk_block.inc"
}

static std::mt19937 rng(12345);
static std::vector<cIGZWin*> all;

static cIGZWin* Make(int depth, int maxDepth, int pool)
{
	cIGZWin* w = new cIGZWin();
	w->id = 1 + rng() % pool;
	all.push_back(w);
	if (depth < maxDepth)
	{
		const int n = rng() % (depth < 2 ? 6 : 4);
		for (int i = 0; i < n; i++) { w->kids.push_back(Make(depth + 1, maxDepth, pool)); }
	}
	return w;
}

int main()
{
	int fails = 0;
	gIdWalkChecked = kIdWalkChecks;   // checker off: test the walks themselves
	for (int trial = 0; trial < 3000; trial++)
	{
		all.clear();
		const int pool = 3 + rng() % 40;   // small pools force duplicate ids
		cIGZWin* root = Make(0, 2 + rng() % 11, pool);
		uint32_t ids[16];
		const int n = 1 + rng() % 16;
		for (int k = 0; k < n; k++) { ids[k] = 1 + rng() % (pool + 5); }

		// 1. FindIdsRecursive == the engine's per-id lookup
		cIGZWin* out[16];
		FindIdsRecursive(root, ids, n, out);
		for (int k = 0; k < n; k++)
		{
			if (out[k] != root->GetChildWindowFromIDRecursive(ids[k]))
			{
				fails++;
				printf("FIND differs: trial %d id %u\n", trial, ids[k]);
			}
		}

		// 2. CollectIdsUnder == one IdCollectCtx walk per id
		cIGZWin* many[16][4];
		int counts[16];
		CollectIdsUnder(root, ids, n, many, counts);
		for (int k = 0; k < n; k++)
		{
			cIGZWin* single[4] = {};
			int ns = 0;
			IdCollectCtx one = { ids[k], single, 4, &ns, 0 };
			root->EnumChildren(GZIID_cIGZWin, IdCollectCtx::Callback, &one);
			bool same = (ns == counts[k]);
			for (int i = 0; same && i < ns; i++) { same = (single[i] == many[k][i]); }
			if (!same)
			{
				fails++;
				printf("COLLECT differs: trial %d id %u\n", trial, ids[k]);
			}
		}

		// 3. IdBatch: a found window may be followed by a tree change (after
		//    Touched()); every answer must equal the engine's at that moment.
		IdBatch b;
		b.root = root;
		for (int k = 0; k < n; k++) { b.Add(ids[k]); }
		for (int k = 0; k < b.n; k++)
		{
			cIGZWin* got = b.Next(ids[k]);
			if (got != root->GetChildWindowFromIDRecursive(ids[k]))
			{
				fails++;
				printf("BATCH differs: trial %d k %d\n", trial, k);
			}
			if (got && rng() % 2)
			{
				b.Touched();
				cIGZWin* v = all[rng() % all.size()];
				cIGZWin* nw = new cIGZWin();
				nw->id = 1 + rng() % (pool + 5);
				all.push_back(nw);
				v->kids.insert(v->kids.begin() + (v->kids.empty() ? 0 : rng() % v->kids.size()), nw);
				if (rng() % 3 == 0) { v->kids.erase(v->kids.begin() + rng() % v->kids.size()); }
			}
		}

		// 4. asked out of sequence, IdBatch falls back to the engine
		IdBatch c;
		c.root = root;
		c.Add(ids[0]);
		if (c.Next(ids[0] + 1000) != root->GetChildWindowFromIDRecursive(ids[0] + 1000)) { fails++; }
	}

	// 5. the checker: agreeing walks count, a broken walk is corrected
	{
		gIdWalkChecked = 0;
		all.clear();
		cIGZWin* root = Make(0, 6, 5);
		uint32_t ids[3] = { 1, 2, 3 };
		cIGZWin* out[3];
		FindIdsRecursive(root, ids, 3, out);
		if (gIdWalkBad != 0 || gIdWalkChecked != 1) { fails++; }
		cIGZWin::skipLast = true;
		for (int t = 0; t < 20; t++)
		{
			uint32_t one[1] = { static_cast<uint32_t>(1 + t % 5) };
			cIGZWin* o[1];
			FindIdsRecursive(root, one, 1, o);
			if (o[0] != root->GetChildWindowFromIDRecursive(one[0])) { fails++; }
		}
		cIGZWin::skipLast = false;
		printf("checker: a broken walk was corrected %u time(s), %d log line(s)\n",
			gIdWalkBad, Logger::Get().lines);
		if (gIdWalkBad == 0) { fails++; }
	}

	// 6. what it saves: 14 lookups, mostly misses, on a city-sized tree
	{
		gIdWalkChecked = kIdWalkChecks;
		rng.seed(7);
		cIGZWin* root = nullptr;
		do { all.clear(); root = Make(0, 7, 5000); } while (all.size() < 700 || all.size() > 1100);
		uint32_t ids[14];
		for (int k = 0; k < 14; k++) { ids[k] = (k < 9) ? all[rng() % all.size()]->id : 900000u + k; }
		cIGZWin::visits = 0;
		for (int k = 0; k < 14; k++) { root->GetChildWindowFromIDRecursive(ids[k]); }
		const long long per = cIGZWin::visits;
		cIGZWin::visits = 0;
		cIGZWin* out[14];
		FindIdsRecursive(root, ids, 14, out);
		printf("%zu-window tree: 14 per-id lookups visit %lld windows, one batched walk %lld\n",
			all.size(), per, cIGZWin::visits);
	}

	printf("%s (%d failure(s))\n", fails ? "FAIL" : "PASS", fails);
	return fails ? 1 : 0;
}
