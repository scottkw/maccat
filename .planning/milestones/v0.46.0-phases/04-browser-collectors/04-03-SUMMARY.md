---
phase: 04-browser-collectors
plan: "03"
subsystem: testing
tags: [zsh, chrome, firefox, browser-extensions, self-test, determinism]

# Dependency graph
requires:
  - phase: 04-01
    provides: collect_chrome_extensions function in update-list.sh
  - phase: 04-02
    provides: collect_firefox_extensions function in update-list.sh
provides:
  - Live-verified automated evidence that CHR-01 and FF-01 are met
  - Determinism confirmation: two runs of each collector produce byte-identical output
  - Component exclusion verified: nmmhkkegccagdldgiimedpiccmgmieda absent from Chrome output
  - Name resolution verified: no raw __MSG_ strings in output
affects: [05-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ephemeral self-test: extract function block via sed lines 254-1380, source in child zsh, run assertions, cleanup /tmp"
    - "Collector isolation: source only function definitions to avoid triggering interactive main block"

key-files:
  created: []
  modified: []

key-decisions:
  - "Extract function definitions via sed (lines 254-1380) rather than sourcing full script — avoids triggering interactive main block (get_target_location prompt)"
  - "Single output file for both collectors per run — Chrome and Firefox sections appended sequentially, allowing unified assertions"
  - "Test script written to /tmp and cleaned up post-run — never committed"

patterns-established:
  - "Self-test pattern: sed-extract functions → child zsh → assert → cleanup (mirrors Phase 2/3 harness approach)"

requirements-completed: [CHR-01, FF-01]

# Metrics
duration: 5min
completed: 2026-06-13
---

# Phase 4 Plan 03: Browser Collector Self-Test Summary

**Live-machine self-test confirms 7 Chrome user extensions and 6 Firefox app-profile addons with component exclusion, __MSG_ resolution, and byte-identical determinism across two consecutive runs.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-13T18:18:00Z
- **Completed:** 2026-06-13T18:23:54Z
- **Tasks:** 1
- **Files modified:** 0 (test is fully ephemeral — no committed files changed)

## Accomplishments

- All 11 self-test assertions pass: 9 correctness checks + 2 prerequisite checks
- Chrome: 7 user-installed extensions emitted; Bitwarden Password Manager (2026.5.1) [nngceckbapebfimnlniiiahkandclblb] present; component nmmhkkegccagdldgiimedpiccmgmieda excluded; zero raw __MSG_ strings
- Firefox: 6 app-profile addons emitted; Vue.js devtools (7.7.7) [{5caff8cc-3d2e-4110-a88a-003cc85b3858}] present; app-builtin and app-builtin-addons (12 entries) correctly excluded
- Determinism confirmed: diff of run1 vs run2 is empty for both collectors
- update-list.sh: zsh -n exits 0; no uncommitted changes after test

## Task Commits

No task commits — self-test is entirely ephemeral (all work in /tmp, cleaned up).

**Plan metadata:** (docs commit — this SUMMARY.md only)

## Files Created/Modified

None — test ran entirely in /tmp, all files cleaned up post-run.

## Decisions Made

- Extracted function definitions (lines 254–1380) via `sed -n '254,1380p'` rather than sourcing the full script. The main block (line 1581+) calls `get_target_location` which is an interactive prompt — sourcing the full script would block. This is the correct isolation approach for a harness that must not trigger catalog generation.
- Used a single output file per run (both Chrome and Firefox sections appended sequentially) rather than separate files per collector. This simplifies assertions and accurately mirrors how the functions will behave when wired into `generate_catalog` in Phase 5.

## Deviations from Plan

None — plan executed exactly as written. The sed-extraction approach was anticipated in the plan's NOTE about main block interaction.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CHR-01 and FF-01 are verified met by the Phase 04 implementations
- Phase 05 (integration) can now wire `collect_chrome_extensions` and `collect_firefox_extensions` into `generate_catalog` with confidence
- No blockers

---
*Phase: 04-browser-collectors*
*Completed: 2026-06-13*
