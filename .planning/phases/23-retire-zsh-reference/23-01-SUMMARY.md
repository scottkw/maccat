---
phase: 23-retire-zsh-reference
plan: "01"
subsystem: testing
tags: [pytest, chrome_name, vsc_name, branch-coverage, isinstance-guard]

requires: []
provides:
  - "isinstance(messages, dict) guard in chrome_name.py exercised by test_msg_non_dict_messages_json_degrades_to_ext_id"
  - "isinstance(nls, dict) guard in vsc_name.py exercised by test_nls_non_dict_top_level_degrades_to_ext_id"
affects: [23-retire-zsh-reference]

tech-stack:
  added: []
  patterns:
    - "Branch-gap test: write JSON array to file normally built by _make_ext locales helper; assert graceful fallback to ext_id"

key-files:
  created: []
  modified:
    - tests/test_helpers.py

key-decisions:
  - "Wrote messages.json as JSON array [1,2,3] by manually creating _locales/en/ inside manifest.parent — avoids touching _make_ext locales kwarg which expects dict-of-dicts"
  - "Third candidate case (vsc_name NLS value = integer scalar) confirmed redundant; omitted per ZSH-03 'do NOT manufacture redundant cases'"

patterns-established: []

requirements-completed: [ZSH-03]

duration: 5min
completed: 2026-06-16
---

# Phase 23 Plan 01: ZSH-03 Backfill — isinstance-dict Branch Tests Summary

**Two branch-gap test methods closing the isinstance(messages/nls, dict) guard coverage in chrome_name.py and vsc_name.py via JSON-array top-level fixtures**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-16T15:38:00Z
- **Completed:** 2026-06-16T15:43:25Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Added `test_msg_non_dict_messages_json_degrades_to_ext_id` to `TestChromeExtName`: writes `_locales/en/messages.json` as a JSON array `[1, 2, 3]`, asserts `chrome_ext_name` returns `ext_id` without raising — exercises the `isinstance(messages, dict)` guard at `chrome_name.py:52-53`
- Added `test_nls_non_dict_top_level_degrades_to_ext_id` to `TestResolveVscExtName`: writes `package.nls.json` as a JSON array `["a", "b"]`, asserts `resolve_vsc_ext_name` returns `ext_id` without raising — exercises the `isinstance(nls, dict)` guard at `vsc_name.py:53-54`
- 31/31 tests pass; ruff and mypy --strict remain clean; no new files created

## Task Commits

1. **Task 1: Add two branch-gap test methods to tests/test_helpers.py** - `29eb0cf` (test)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `tests/test_helpers.py` - Two new test methods appended to existing `TestChromeExtName` and `TestResolveVscExtName` classes (46 lines added)

## Decisions Made

- Used `manifest.parent / "_locales" / "en"` to manually create the locale directory rather than using `_make_ext`'s `locales` kwarg — the locales kwarg writes valid dict-of-dicts; the test needs a JSON array at `messages.json` specifically to exercise the not-a-dict branch
- Omitted the third candidate case (NLS value = integer scalar in vsc_name) per ZSH-03 audit: `test_nls_v2_object_value_degrades_to_ext_id` already exercises the identical `isinstance(resolved, str)` guard path

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Branch coverage gaps closed; `test_helpers.py` is fully green
- Phase 23 Plan 02 (23-02) can proceed to delete `tests/test_golden_parity.py` and the parity scaffold without losing coverage
- No blockers

---
*Phase: 23-retire-zsh-reference*
*Completed: 2026-06-16*
