---
phase: 25-script-emitter
reviewed: 2026-06-16T20:12:53Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/maccat/reinstall/emitter.py
  - tests/reinstall/test_emitter.py
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 25: Code Review Report

**Reviewed:** 2026-06-16T20:12:53Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

`emitter.py` renders a `ParsedCatalog` into a `reinstall.sh` string with zero subprocess
calls. The injection-safety design is sound: `quote_for_script()` (wrapping `shlex.quote()`)
is consistently used for every catalog-derived value in command position, and
`safe_comment_value()` strips newlines before any value reaches `# comment` context. I traced
the adversarial inputs (`$(...)`, backticks, `;`, spaces, quotes, embedded newlines) through
all four renderers and could find **no injection vector** — criterion 5 holds. The Homebrew
`||` guard and the VS Code/Cursor `command -v ... && ! ... | grep -qi ... && --install-extension`
guard are both correctly in conditional context and do **not** spuriously abort under
`set -Eeuo pipefail` (verified by executing equivalent shapes).

However, the **mas (App Store) renderer emits a bare, unguarded `mas install <id>` line**.
Unlike the brew and editor renderers, it has no conditional-context wrapper and no idempotency
guard. Under the script's own `set -Eeuo pipefail`, the first `mas install` that returns
non-zero — which happens routinely (app already installed, not signed into the App Store,
transient error) — aborts the entire script, silently skipping every subsequent install
*and the whole Manual Checklist*. This directly violates the stated pipefail-safety criterion.
The 62 passing tests never execute the script (only `bash -n`), so they cannot catch this.

## Critical Issues

### CR-01: Bare `mas install` aborts the entire script under `set -Eeuo pipefail`

**File:** `src/maccat/reinstall/emitter.py:119`
**Issue:**
The script header emits `set -Eeuo pipefail`, but `_mas_block` emits each App Store install as
a bare top-level command:

```
mas install 424389933  # cataloged: 10.7.1 — Final Cut Pro
```

This line has no `||`/`&&` conditional-context exemption and no idempotency guard — unlike
`_brew_block` (`... || ... || brew install`) and `_editor_ext_block`
(`command -v ... && ! ... && --install-extension`). `mas install` returns a non-zero exit
status in entirely expected situations:
- the app is already installed (the common case on a re-run — this tool exists for restorable,
  idempotent re-runs),
- the user is not signed into the App Store,
- any per-app transient/store error.

Under `set -e`, the first such non-zero exit aborts the whole script. Verified empirically:

```
$ cat t.sh
#!/usr/bin/env bash
set -Eeuo pipefail
echo start
false                 # stands in for a failing/already-installed 'mas install'
echo "next line"      # never printed
$ bash t.sh; echo "exit=$?"
start
exit=1
```

Consequence: one already-installed App Store app halts the run, skipping every later
`mas install`, the VS Code/Cursor extension installs, **and the entire Manual Checklist** —
the opposite of the graceful, restore-the-whole-machine behavior the tool promises. This is
also inconsistent with the two sibling auto-install renderers, both of which are pipefail-safe.

**Fix:**
Give the mas line the same idempotency + conditional-context treatment the other renderers
use. A `mas list | grep -q` guard parallels the editor block and is safe under pipefail
(`grep -q` non-zero is consumed by `&&` short-circuit / `!` negation):

```python
qid = quote_for_script(item.id)
grep_pat = quote_for_script(f"^{item.id} ")  # mas list rows start with the numeric id
line = (
    f"command -v mas >/dev/null && "
    f"! mas list | grep -q {grep_pat} && "
    f"mas install {qid}"
)
```

A minimal alternative is appending `|| true` to neutralize the expected non-zero exit:

```python
line = f"mas install {qid} || true"
```

but the `mas list | grep -q` guard is preferred: it mirrors the established editor pattern,
adds a `command -v mas` PATH guard (mas may not be installed on the target machine), and
avoids re-attempting installs for already-present apps. Add a runtime regression test
(execute the script with `set -e` and a stubbed failing `mas`, assert later lines still run)
since `bash -n` cannot catch this class of defect (see WR-01).

## Warnings

### WR-01: Test suite only syntax-checks the script; it never executes it under `set -e`

**File:** `tests/reinstall/test_emitter.py:29-40,485-491`
**Issue:**
`assert_bash_n_clean()` runs only `bash -n` (syntax check), and `test_set_errexit_on_second_line`
merely asserts the literal `set -Eeuo pipefail` string is present. Nothing in the suite
*executes* the emitted script, so the runtime pipefail-abort behavior of the guards is never
validated. This is why CR-01 ships with 62 green tests. Asserting the presence of
`set -Eeuo pipefail` without proving the generated guards survive it gives false confidence —
it locks in the directive while leaving the central safety claim (no spurious abort on
expected non-zero exits) unverified.
**Fix:**
Add execution tests that run the emitted script under `bash` (not `bash -n`) with stubbed
tools on `PATH` (a `brew`/`mas`/`code` shim that returns non-zero for the "already installed"
case) and assert the script reaches the end (exit 0) and runs later sections. Skip gracefully
when `bash` is unavailable, matching the existing `assert_bash_n_clean` skip pattern.

### WR-02: `brew install` failure also aborts the whole script (no partial-failure tolerance)

**File:** `src/maccat/reinstall/emitter.py:96-99`
**Issue:**
The brew guard `brew list X || brew list --cask X || brew install X` is pipefail-safe for the
expected cases (already-installed short-circuits; successful install returns 0), which I
verified. But when `brew install` *itself* fails (network error, renamed/removed formula,
genuine formula-vs-cask ambiguity that the section NOTE warns about), the entire `||` chain
returns non-zero and `set -e` aborts the run — skipping all remaining packages and sections.
Verified empirically that `false || false || false` under `set -Eeuo pipefail` exits 1 and
halts. For a "rebuild the whole environment" tool, one missing/renamed formula should not
abort the rest of the restore.
**Fix:**
Decide explicitly whether install failures should be fatal. If not (recommended for this
tool's graceful-degradation ethos), make each guard non-fatal, e.g. append `|| true` or wrap
install failures with a warning echo:

```python
guard = (
    f"brew list {n} &>/dev/null || brew list --cask {n} &>/dev/null"
    f" || brew install {n} || echo {quote_for_script('  WARN: brew install failed: ' + item.name)}"
)
```

If install failures *should* be fatal, document that decision in the module docstring so it
is not mistaken for the same defect class as CR-01.

### WR-03: VS Code/Cursor section unconditionally emits its `echo "=== ... ==="` header even when no installs apply

**File:** `src/maccat/reinstall/emitter.py:156`
**Issue:**
`_editor_ext_block` always emits `echo "=== {title} ==="`. When the editor is not installed on
the target machine, every guard line short-circuits at `command -v <editor>` (correct), but the
user still sees a "=== VS Code Extensions ===" banner with nothing happening beneath it and no
indication the editor was skipped. This is a minor UX/clarity issue, not a correctness bug, but
it makes the output misleading on machines where the editor is absent. (Same pattern in
`_mas_block` and `_brew_block`, which also emit unconditional headers — acceptable there since
brew/mas are nearly always present, but the editor case is the most likely to be absent.)
**Fix:**
Either gate the banner behind the same `command -v` check (emit it inside a guarded block) or
add a trailing `echo` note such as `echo "(skipped — code not installed)"` in the not-found
path. Lowest-effort acceptable option: leave as-is but document that an empty banner means the
editor was absent.

## Info

### IN-01: `mas list` already-installed semantics are assumed, not asserted

**File:** `src/maccat/reinstall/emitter.py:106-141`
**Issue:**
The fix for CR-01 (and the existing brew/editor guards) depends on the runtime exit-code
semantics of external tools (`mas install` returning non-zero when already installed, `mas list`
row format starting with the numeric id). These are reasonable assumptions but are undocumented
in the module, making future maintenance fragile — a reader cannot tell which exit-code contract
each guard relies on.
**Fix:**
Add a brief comment to each auto-install renderer stating the exit-code contract it relies on
(e.g. "`mas install` returns non-zero when the app is already installed; guarded so re-runs do
not abort"). This makes the pipefail-safety reasoning auditable.

---

_Reviewed: 2026-06-16T20:12:53Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
