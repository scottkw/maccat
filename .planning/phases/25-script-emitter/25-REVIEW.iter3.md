---
phase: 25-script-emitter
reviewed: 2026-06-16T20:23:09Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/maccat/reinstall/emitter.py
  - tests/reinstall/test_emitter.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 25: Code Review Report (Iteration 2)

**Reviewed:** 2026-06-16T20:23:09Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Re-review of the script emitter after iteration-1 fixes (CR-01, WR-01, WR-02, WR-03).
Focus was verifying the `set -Eeuo pipefail` guard-logic fixes are actually correct, that
the new runtime-execution tests genuinely exercise abort-resistance, and that no new
shell-injection was introduced.

**Verdict on the iteration-1 fixes: correct.** All three install blocks (brew, mas, editor)
now neutralize a non-zero install exit so the run continues:

- **brew** — `... || brew install <n> || echo <warn>`. The trailing `|| echo` consumes a
  failed install. Verified at runtime: a failing `brew install git` prints the WARN line and
  the script reaches the Manual Checklist sentinel (exit 0). (`test_brew_install_nonzero_does_not_abort`.)
- **mas** — `command -v mas ... && ! mas list | grep -q <pat> && { mas install <id> || echo <warn>; }`.
  The brace group makes the final statement-level command exit 0 on install failure. Empirically
  confirmed this does NOT abort even when `mas list` itself fails under `pipefail` (the `!`
  negation flips the failed pipeline to true, and the brace-group fallback absorbs the install
  failure). Covered by `test_mas_install_nonzero_does_not_abort`.
- **editor** — same brace-group pattern: `... && { <editor> --install-extension <id> || echo <warn>; }`.
  I independently executed the install-FAILURE path (editor present, extension absent, install
  exits 1) and confirmed the script prints the WARN and continues to exit 0. The set -e subtlety
  is handled correctly: a short-circuit in a middle `&&` element is exempt from set -e, and the
  only command that could trigger abort (the final brace group) always exits 0 via `|| echo`.

**Shell-injection safety: intact, no regression.** Every catalog-derived value in command
position (including the NEW `<warn>` strings, which embed `item.name` / lowercased id) routes
through `quote_for_script` (shlex.quote); comment-context values route through
`safe_comment_value` (newline/CR stripping). I executed the install-failure path with a hostile
name `evil $(touch /tmp/PWNED) ` + backtick-`id`-backtick and confirmed the command substitution
did NOT fire — the WARN echo printed the literal text and no file was created. `editor` in the
warn/guard is the trusted literal `code`/`cursor` from the routing map, not catalog-derived.

**Tooling:** `ruff check` clean, `mypy --strict` clean, all 65 tests pass. Zero subprocess
calls in the emitter (only tests shell out) — constraint upheld. Empty catalog renders a valid
header-only script (no crash).

The one finding below is a test-coverage gap, not a correctness defect in the emitted script.

## Warnings

### WR-01: Runtime abort-resistance for the editor install path is not exercised by any test

**File:** `tests/reinstall/test_emitter.py:714-852` (`TestRuntimeExecution`)
**Issue:** The iteration-1 fix added the brace-group guard to the editor block specifically so a
failing `--install-extension` does not abort the run under `set -Eeuo pipefail` (emitter.py
lines 193-204). However, every runtime test stubs the editors with `_EDITOR_PRESENT`
(lines 731-735), whose `--list-extensions` always reports the extension already installed. That
forces the `! ... grep -qi` idempotency check to short-circuit the `&&` chain, so the
`--install-extension` command (and its `|| echo WARN` fallback) NEVER RUNS in any test. The
runtime suite therefore proves abort-resistance for brew and mas, but the editor brace-group
guard is only validated by `bash -n` (syntax) and by manual review — not by execution. A future
regression that drops the editor brace group (reverting to a bare
`&& <editor> --install-extension <id>`) would pass all 65 tests yet abort a real restore the
moment an extension install fails. I confirmed the fix itself is correct by executing the path by
hand; the gap is purely in the guarding tests.

**Fix:** Add a runtime test mirroring `test_brew_install_nonzero_does_not_abort` for the editor
block — stub `code` (and/or `cursor`) so the extension is reported ABSENT and the install fails,
then assert exit 0 and that the WARN line plus the Manual Checklist sentinel both print:
```python
def test_editor_install_nonzero_does_not_abort(self) -> None:
    editor_install_fails = (
        "#!/usr/bin/env bash\n"
        # report the extension as NOT installed so the guard proceeds to install
        'if [ "$1" = "--list-extensions" ]; then echo "other.ext"; exit 0; fi\n'
        'if [ "$1" = "--install-extension" ]; then echo "ext: failed" >&2; exit 1; fi\n'
        "exit 0\n"
    )
    stubs = {
        "brew": "#!/usr/bin/env bash\nexit 0\n",
        "mas": "#!/usr/bin/env bash\nexit 1\n",
        "code": editor_install_fails,
        "cursor": editor_install_fails,
    }
    script = emit_reinstall_script(
        self._catalog_with_all_sources(), source_name="t.txt", generated="2026-06-16"
    )
    result = run_script_with_stubs(script, stubs)
    assert result.returncode == 0, result.stderr
    assert "WARN: code --install-extension failed" in result.stdout
    assert self._SENTINEL in result.stdout
```

## Info

### IN-01: brew abort-safety depends on `echo <warn>` staying the final chain element (currently benign)

**File:** `src/maccat/reinstall/emitter.py:103-106`
**Issue:** The brew guard is
`brew list <n> &>/dev/null || brew list --cask <n> &>/dev/null || brew install <n> || echo <warn>`.
Every non-final element is part of an `||` list and is exempt from set -e; the final element
(`echo <warn>`) always exits 0, so the line is abort-safe today (confirmed at runtime). Noted
only for awareness: the abort-safety depends on `echo <warn>` remaining the last element. If a
future edit appends another command after the warn echo without an `|| echo`/brace guard, the same
set -e trap that CR-01 fixed could reappear.
**Fix:** None required. If the chain is extended, keep a 0-exit command (or brace-group fallback)
as the final element.

### IN-02: `_should_skip` collapses "degraded" and "empty" into one silent skip (intentional, documented)

**File:** `src/maccat/reinstall/emitter.py:55-62`
**Issue:** `_should_skip` returns True for both degraded sections and legitimately-empty sections
(including the WR-05 "Installed Mac Software List" header). A degraded source therefore emits
nothing at all — not even a note that the source degraded — making it indistinguishable from an
empty section in the output. The docstring documents this as intentional and tests
(`test_degraded_section_skipped_entirely`, `test_empty_section_skipped_entirely`,
`test_installed_mac_software_list_header_skipped`) lock the behavior. Accepted as designed;
flagged only so the silent-skip-of-degraded-sources decision stays visible.
**Fix:** None required. If surfacing degraded sources is later desired, emit a
`# NOTE: <title> source was degraded; nothing rendered` comment for `section.degraded` before the
empty-skip check.

---

_Reviewed: 2026-06-16T20:23:09Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
