---
phase: 25-script-emitter
fixed_at: 2026-06-16T20:40:00Z
review_path: .planning/phases/25-script-emitter/25-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 25: Code Review Fix Report

**Fixed at:** 2026-06-16T20:40:00Z
**Source review:** .planning/phases/25-script-emitter/25-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + Warning): 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Bare `mas install` aborts the entire script under `set -Eeuo pipefail`

**Files modified:** `src/maccat/reinstall/emitter.py`
**Commits:** `d5d6bf8`, `0b9a6b5`
**Status:** fixed: requires human verification (runtime guard logic — covered by new execution tests)

**Applied fix:** Replaced the bare `mas install <id>` line in `_mas_block` with a guarded,
idempotent, pipefail-safe chain mirroring the editor pattern:

```
command -v mas >/dev/null && ! mas list | grep -q '^<id> ' && { mas install <id> || echo '  WARN: ...'; }
```

The `command -v mas` guard skips when mas is absent; `! mas list | grep -q '^<id> '`
(leading-id column of `mas list`, quoted via `quote_for_script`) skips already-installed
apps; and the brace group `{ mas install ... || echo WARN; }` is what makes it genuinely
pipefail-safe.

**Important correction discovered via WR-01 execution tests:** the fix suggested in REVIEW.md
(plain `... && mas install <id>`) is itself NOT safe. Under `set -e`, when the `&&` chain
actually reaches the install and it fails, the install is the LAST command of the list, so
`set -e` still aborts the run (verified empirically: `true && true && false` exits 1 and
halts). The `&&` short-circuit only protects the install if an *earlier* link fails. The
correct fix neutralizes the final non-zero exit with a trailing `|| echo WARN` wrapped in a
brace group so the line's final status is 0. The same latent defect existed in the editor
guard (`_editor_ext_block`) — the review marked it "verified safe" but only the short-circuit
path was exercised, not an actual `--install-extension` failure. Both guards were hardened.

### WR-01: Test suite only syntax-checks the script; it never executes it under `set -e`

**Files modified:** `tests/reinstall/test_emitter.py`
**Commit:** `0b9a6b5`
**Status:** fixed

**Applied fix:** Added a `run_script_with_stubs()` helper (PATH-shims fake `brew`/`mas`/`code`/
`cursor` executables into a tmp `bin/` dir, runs the emitted script under `bash`, skips if bash
absent) and a `TestRuntimeExecution` class with three execution tests:
- `test_mas_install_nonzero_does_not_abort` — stubbed `mas install` exits non-zero; asserts the
  script reaches exit 0 and the Manual Checklist sentinel still prints. This test FAILED against
  the REVIEW.md-suggested fix and is what surfaced the set -e latent bug above.
- `test_brew_install_nonzero_does_not_abort` — stubbed `brew install` fails; asserts the `WARN`
  line prints and the run completes.
- `test_everything_already_installed_runs_clean` — all idempotency guards match; nothing installs;
  run completes cleanly (the common re-run case).

### WR-02: `brew install` failure also aborts the whole script (no partial-failure tolerance)

**Files modified:** `src/maccat/reinstall/emitter.py`
**Commit:** `d5d6bf8`
**Status:** fixed: requires human verification (graceful-degradation policy choice)

**Applied fix:** Chose the graceful-degradation option (consistent with the project's stated
constraint). Appended `|| echo '  WARN: brew install failed: <name>'` (value quoted via
`quote_for_script`) to the brew guard chain so a genuine install failure surfaces a warning
without aborting the rest of the restore. A module comment documents the policy and the exit-code
contract the guard relies on.

### WR-03: VS Code/Cursor section unconditionally emits its `echo "=== ... ==="` header

**Files modified:** `src/maccat/reinstall/emitter.py`
**Commit:** `d5d6bf8`
**Status:** fixed (documented — lowest-effort acceptable option per review)

**Applied fix:** Documented the intentional behavior in the `_editor_ext_block` docstring: the
banner is emitted unconditionally and an empty banner with no install output means the editor was
absent. This keeps the renderer's structure parallel with the brew/mas blocks rather than
duplicating the per-line `command -v` guard at the section level — the review listed documenting
as an acceptable resolution.

## Out-of-scope (noted only)

### IN-01: `mas list` already-installed semantics are assumed, not asserted

Info-severity (outside the `critical_warning` fix scope), so not formally fixed. In practice it is
largely addressed as a side effect of the CR-01/WR-02 work: each hardened guard now carries an
inline comment stating the exit-code contract it relies on (e.g. `mas install` returns non-zero
when already installed / not signed in; `mas list` rows begin with the numeric id).

## Verification

- `ruff check` clean on both modified files.
- `mypy --strict` clean on both modified files (`MYPYPATH=src`).
- Full suite: `516 passed, 5 skipped` (5 skips pre-existing/environment-conditional; the 3 new
  runtime execution tests run and pass — bash present).
- Emitter retains ZERO subprocess calls; only the tests shell out (under `bash`, guarded by a
  `pytest.skip` when bash is unavailable).
- `from __future__ import annotations` retained at line 1; stdlib-only; type hints intact.

---

_Fixed: 2026-06-16T20:40:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
