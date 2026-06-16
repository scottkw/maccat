---
phase: 21-cli-cleanup
reviewed: 2026-06-16T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - src/maccat/cli.py
  - src/maccat/identity.py
  - src/maccat/gitops.py
  - src/maccat/naming.py
  - src/maccat/retention.py
  - src/maccat/catalog/writer.py
  - tests/test_cli.py
  - tests/test_identity.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-06-16
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 21 is a well-scoped mechanical refactor. The core surgery — collapsing
`resolve_computer_selection` to a single `computer: str | None` keyword-only
parameter, removing the three argparse flags, updating both CLI guards, and
migrating the test suite — is executed correctly. mypy --strict passes, ruff
passes, all 71 tests pass.

Three issues were found:

- **1 Warning:** Stale module-level docstring entry in `identity.py` still
  describes `resolve_computer_selection` as mirroring the zsh
  `parse_arguments` mutual-exclusion block (lines 199–268). That logic was
  removed. The entry is actively misleading.
- **2 Info:** Duplicate test intent in `TestResolveComputerSelection`
  (two tests that assert `computer=None → None`); and the `--rename ×
  --computer` guard test has weaker assertion coverage than the three
  newly-added removed-flag tests.

---

## Warnings

### WR-01: Stale module-level zsh-analog entry in identity.py

**File:** `src/maccat/identity.py:10`

**Issue:** The module docstring's "Zsh analogs" table still contains:

```
  parse_arguments (subset)       update-list.sh lines 199–268  (flag-alias + mutual-exclusion)
```

After Phase 21, `resolve_computer_selection` no longer performs
flag-aliasing (`--personal` → `"personal"`, etc.) or the mutual-exclusion
guard — both were removed. The entry maps to a dead code surface. Any reader
cross-referencing this file against `update-list.sh:199-268` will be
confused because none of that block's logic exists here anymore.

The plan (21-01-PLAN.md lines 92–96) explicitly called for removing this
reference in the function-level docstring; the module-level table entry was
not updated.

**Fix:** Remove or replace line 10 in the "Zsh analogs" table. Either
drop the row entirely (since the simplified `resolve_computer_selection`
has no direct zsh analog) or replace it with an accurate description:

```python
  resolve_computer_selection     (no direct zsh analog — simplified to --computer only)
```

---

## Info

### IN-01: Duplicate test intent in TestResolveComputerSelection

**File:** `tests/test_identity.py:96` and `tests/test_identity.py:122`

**Issue:** Two tests both assert that `resolve_computer_selection(computer=None)`
returns `None`:

- `test_none_returns_none` (line 96): `computer=None` → `assert result is None`
- `test_none_returns_none_for_interactive_fallback` (line 122): same call,
  same assertion

The plan (21-02-PLAN.md) specified these as two distinct test cases: one
named `test_none_returns_none_for_interactive_fallback` was intended to be
newly added while `test_none_returns_none` was the renamed survivor of the
old `test_no_flag_returns_none_for_interactive`. Both ended up with the
same body. One is redundant.

This is not a bug (both pass and neither is wrong), but it signals that
the planned consolidation was partially doubled-up rather than
replace-and-rename.

**Fix:** Remove one of the two tests. Keep
`test_none_returns_none_for_interactive_fallback` (the more descriptive
name) and delete `test_none_returns_none`.

---

### IN-02: test_rename_with_computer_exits does not assert a nonzero exit code

**File:** `tests/test_cli.py:134-139`

**Issue:** The three newly-added removed-flag regression tests all assert
`exc.value.code == 2` (the specific argparse exit code). The pre-existing
`test_rename_with_computer_exits` — the only remaining `TestRenameFlag`
test after Phase 21's pruning — asserts only `pytest.raises(SystemExit)`
with no exit code check. This means the test would pass even if the guard
were accidentally changed to exit with code 0, which is an exit that
conventionally signals success.

The test predates Phase 21 and was not required to be strengthened by the
plan. It is a pre-existing weakness, not a regression introduced here.
Noted as Info so it can be addressed alongside the new regression tests for
consistency.

**Fix:** Add an exit-code assertion consistent with the three new tests.
The guard calls `sys.exit("ERROR: ...")` which produces a string code (not
integer 0), so `!= 0` is the right check:

```python
def test_rename_with_computer_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["maccat", "--rename", "--computer", "box"])
    from maccat.cli import run

    with pytest.raises(SystemExit) as exc:
        run()
    assert exc.value.code != 0
```

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
