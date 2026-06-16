---
phase: 25-script-emitter
fixed_at: 2026-06-16T20:40:00Z
review_path: .planning/phases/25-script-emitter/25-REVIEW.md
iteration: 2
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 25: Code Review Fix Report (Iteration 2)

**Fixed at:** 2026-06-16T20:40:00Z
**Source review:** .planning/phases/25-script-emitter/25-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 1 (Warning)
- Fixed: 1
- Skipped: 0
- Out of scope (Info, not fixed): IN-01, IN-02

## Fixed Issues

### WR-01: Runtime abort-resistance for the editor install path is not exercised by any test

**Files modified:** `tests/reinstall/test_emitter.py`
**Commit:** edc7fa9
**Applied fix:** Added `test_editor_install_nonzero_does_not_abort` to the
`TestRuntimeExecution` class, mirroring the existing `test_brew_install_nonzero_does_not_abort`
and `test_mas_install_nonzero_does_not_abort` execution helpers. The new test stubs both
`code` and `cursor` so `--list-extensions` reports the extension ABSENT (the idempotency
`! ... grep -qi` guard then proceeds to install) and `--install-extension` exits non-zero.
It runs the emitted script under `bash` (via the existing `run_script_with_stubs` helper,
which already `pytest.skip`s when bash is unavailable) and asserts:

- the script reaches exit 0 (does NOT abort mid-run under `set -Eeuo pipefail`),
- the editor WARN line (`WARN: code --install-extension failed`) prints, and
- the Manual Checklist sentinel (`REACHED_END_SENTINEL`) still prints.

This locks the editor brace-group guard (`{ <editor> --install-extension <id> || echo <warn>; }`)
at runtime the same way brew and mas are already locked. Previously every runtime test used
`_EDITOR_PRESENT`, whose `--list-extensions` always reported the extension installed, so the
`&&` chain short-circuited and the brace-group fallback never executed.

**Regression-lock verified by mutation:** temporarily reverting the emitter to a bare
`&& <editor> --install-extension <id>` (no brace group) causes the new test to FAIL — the
script aborts at the editor block (exit 1, output truncated at `=== VS Code Extensions ===`).
The emitter was restored unchanged after this check; only the test file was committed.

**Verification:**
- Tier 1: re-read modified region; fix present, surrounding tests intact.
- Tier 2: `python -c ast.parse` clean; new test PASSES; full suite `517 passed, 5 skipped`;
  ruff clean; `mypy --strict` clean (with `MYPYPATH=src`).
- The emitter (`src/maccat/reinstall/emitter.py`) was NOT modified — zero subprocess calls
  preserved; only the test shells out. `catalog/format.py` and `reinstall/parser.py` untouched.

## Skipped Issues

None.

## Out-of-Scope Findings (Info — not addressed)

- **IN-01** (emitter.py:103-106): brew abort-safety depends on `echo <warn>` staying the final
  chain element. Reviewer marked "Fix: None required." Noted only.
- **IN-02** (emitter.py:55-62): `_should_skip` collapses "degraded" and "empty" into one silent
  skip — intentional and test-locked. Reviewer marked "Fix: None required." Noted only.

---

_Fixed: 2026-06-16T20:40:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
