---
phase: 17-parity-safety-tests
reviewed: 2026-06-14T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - tests/golden/normalize.py
  - tests/golden/generate.py
  - tests/test_golden_parity.py
  - tests/test_safety_invariants.py
  - tests/test_update_list_integrity.py
  - tests/conftest.py
  - .github/workflows/ci.yml
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: clean
---

# Phase 17: Code Review Report

**Reviewed:** 2026-06-14
**Depth:** standard
**Files Reviewed:** 7
**Status:** clean

## Summary

This is a milestone acceptance-gate review of the parity/safety test suite for the
zsh→Python (`maccat`) port. All blocker/critical and warning findings from iteration 1
and the orchestrator's follow-up (CR-02) have been resolved across iterations 1 and 2.

**Harness safety: PASS.** `tests/golden/generate.py` can never trigger the destructive
main flow. The source-guard `[[ "$ZSH_EVAL_CONTEXT" =~ :file ]] && return 0` at
`update-list.sh:2433` fires before the main block, and all destructive functions are only
called from the main block after that guard. The harness sets `HOME` inside the zsh script
body before `source`, and every collector resolves `$HOME` at call time, so the real
`$HOME` is never read. Path interpolation uses `!r` (shell-quoted), no `set -e` issues
exist. `update-list.sh` is byte-unmodified (TEST-04 — `git diff --quiet HEAD --
update-list.sh` is clean).

**Acceptance gate now genuinely verifies Python==zsh (CR-02 resolved).** Previously the
committed goldens were written from Python collector output, so the parity suite asserted
Python==Python — TEST-01 ("Python section bodies byte-identical to the ZSH reference") was
tautological. This is fixed:

1. `tests/golden/generate.py` now defines `ZSH_CAPTURABLE` (13 HOME-driven sections →
   their zsh collector functions) and `regenerate_zsh_goldens()`/`main()`, which source
   `update-list.sh` in real zsh against the synthetic fixture and write the captured
   **body** (header stripped via `capture_zsh_section_body`) as the AUTHORITATIVE golden.
   Re-generating produced byte-identical goldens — the proof that Python==zsh holds today.
2. `tests/test_golden_parity.py::test_live_zsh_parity` captures zsh **live** for each of
   the 13 zsh-capturable sections on every macOS CI run, normalizes both sides, and asserts
   the Python collector output equals the zsh body. A wrong/absent `[id]` now FAILS the
   gate (demonstrated via a temporary mutation — see 17-REVIEW-FIX.md). It skips cleanly
   when `zsh` is off PATH (non-macOS dev) and runs on macos-latest. The `zsh_parity` marker
   is registered in `pyproject.toml`.
3. The 4 non-zsh-capturable sections (`homebrew`/`mas` — CLI-driven; `setapp`/`webapps` —
   hardcoded `/Applications`) are documented honestly as Python-format goldens via
   `NON_ZSH_CAPTURABLE` — no silent overclaim of zsh parity.

**Iteration-1 findings (all resolved):**
- CR-01 (normalizer destroyed the `[id]` field): fixed — `normalize_catalog_body` now only
  strips the 14-digit timestamp; the `[id]` field is asserted byte-exact.
- WR-01 (vacuous `(none found)` cases): fixed — fixture populated so skills/agents and
  opencode plugins/agents yield real items.
- WR-02 (webapps baked-in `fake_applications`): fixed — fixture dir renamed `Applications`.
- WR-03 (prune-unparseable never exercised): fixed in `tests/test_safety_invariants.py`.
- WR-04 (unreachable missing-golden branch): fixed — parametrize driven by `EXPECTED_STEMS`.
- WR-05 (re-normalizing golden masks volatile content): fixed — golden compared verbatim.
- WR-06 (SCRIPT_DIR docstring): fixed — pre-set dropped, docstring corrected.

The 3 Info items below are non-blocking observations retained for the record.

## Critical Issues

None. (CR-01 resolved in iteration 1; CR-02 resolved in iteration 2.)

## Warnings

None. (WR-01 through WR-06 resolved in iteration 1.)

## Info

### IN-01: Tied-newest invariant only covers two distinct hosts, not the same-host tie

**File:** `tests/test_safety_invariants.py:57-75`
**Issue:** The genuinely tricky retain case is two files for the SAME host with identical
max timestamps (both must be kept). The test uses two DIFFERENT hosts, which exercises
per-host independence but not the same-host equality keep at `retention.py:81`. The
docstring references the harder case in `test_retention.py`; confirm that source case
still exists.
**Fix:** Add a same-host tied-newest assertion here, or note in the docstring that the
same-host tie is covered in `test_retention.py`.

### IN-02: Redundant zsh -n execution between CI step and pytest

**File:** `.github/workflows/ci.yml:39-40`, `tests/test_update_list_integrity.py:15-22`
**Issue:** `zsh -n update-list.sh` runs both as a dedicated CI step and inside
`test_update_list_integrity.py`. The duplication is harmless but the dedicated step is
redundant given the pytest run.
**Fix:** Keep one. The dedicated step is a fine fast-fail tripwire; if kept, note in the
test that CI also runs it standalone.

### IN-03: 30s subprocess timeout in harness

**File:** `tests/golden/generate.py`
**Issue:** Addressed — the timeout is now the named constant `_ZSH_TIMEOUT_SECONDS = 30`
with an explanatory comment. Retained as Info only to record the rationale.
**Fix:** None required.

---

_Reviewed: 2026-06-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
