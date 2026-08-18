#pragma once

#include <cstdint>   // uint32_t in the NoteWindowId signature - this header
                     // must stand alone, not rely on its .cpp's include order

// SPINPROBE (task #105) - name the loop instead of deducing it.
//
// Task #104: after the game window closes, the process survives and one core
// spins at 84-94% with the message pump still alive. Thirteen in-game runs
// bisected it to a PAIR - OrdinanceInsetPatch + BudgetDeptPatch, with the
// Budget dialog opened at least once - but a bisect names a CONFIG, never a
// MECHANISM. We have never once looked at what the spinning thread is
// actually executing, and every time inference lost to measurement on this
// project the cure was to build the instrument.
//
// Our DLL is already inside the process, so this needs no debugger, no
// elevation dance and no external tool: walk our own threads, sample each
// one's EIP, and log a histogram. ONE address ends the argument.
//
// SAFETY, and why the shape is what it is:
//  * At most ONE thread is suspended at any instant, and it is resumed
//    within a few lines. If we suspended a thread that holds the Logger's
//    CRITICAL_SECTION and then logged, we would deadlock the very shutdown
//    we are trying to observe - so nothing here logs while a suspension is
//    outstanding. Samples are buffered and reported only after the sweep.
//  * Default OFF ([UiSpike] SpinProbe = 0). It is a probe, not a fix.
//  * A partial histogram is emitted every second, so the evidence survives
//    the process actually managing to exit mid-run.
//  * It reports its OWN positive control - threads seen, threads opened,
//    samples taken. A probe that captured nothing must say so as a
//    STRUCTURAL null, never as "nothing was spinning" (law: null is not
//    evidence until you prove the probe could have seen the thing).
namespace SpinProbe
{
	// Spawn the sampler. seconds <= 0 is a no-op. Returns true if the
	// sampler thread started. Call at the very end of PreAppShutdown: the
	// spin is measured to begin only AFTER our cleanup returns.
	bool Arm(int seconds);

	// ---------------------------------------------------------------------
	// OUTCOME RECORDER (task #107)
	//
	// #104 is INTERMITTENT: on 2026-08-03, two runs with byte-identical patch
	// configuration and identical user actions produced opposite outcomes
	// (17:16 SPUN at 97% of a core; 17:27 exited clean ~1s after shutdown).
	//
	// That is fatal to how the bug was bisected. Runs 6-13 gave each config
	// ONE trial, so every "CLEAN" verdict in that truth table is a coin flip
	// rather than evidence, and the "culprit pair" it produced is not
	// established. Deciding this needs RATES, not single trials.
	//
	// Rates are expensive only if a human has to sit through them. This makes
	// ordinary play the experiment: one row per launch into an append-only
	// CSV beside the log - which, unlike SC4UIScale.log, is NEVER recreated.
	// (The log IS recreated per launch, and that is how the run-14 spin
	// capture was lost.)
	//
	// Two-row protocol, because the outcome is only knowable after our code
	// has stopped running:
	//   * RecordShutdown() writes verdict=pending at PreAppShutdown.
	//   * The sampler appends verdict=spun IF it sees a thread running game
	//     code.
	//   * A launch with a pending row and NO spun row means the process
	//     exited on its own = CLEAN.
	// A launch recorded with probeSeconds=0 is written verdict=unknown, never
	// clean - with the probe disarmed nothing could have detected a spin, and
	// a disarmed probe must not manufacture clean results.
	struct LaunchInfo
	{
		const char* version;
		float factor;
		bool  scaleAll;
		bool  ordinanceInset;
		bool  budgetDept;
		bool  budgetButton;
		int   probeSeconds;
		// #104 THE FIX ([UiSpike] SpinFix, default 1). When the sampler has
		// MEASURED the shutdown spin, break it by making the stuck child list
		// report empty - two 4-byte writes, no call into game code. Set 0 to
		// observe the hang without curing it.
		int   spinFix;
	};

	// Call once from PreAppShutdown, BEFORE Arm().
	void RecordShutdown(const LaunchInfo& info);

	// Cheap id filter fed from the sweep. "Was Budget opened?" is a measured
	// precondition of #104 - bisect runs 2-4 were false negatives purely
	// because Budget never got opened - so it must be recorded per launch
	// rather than remembered.
	void NoteWindowId(uint32_t id);
}
