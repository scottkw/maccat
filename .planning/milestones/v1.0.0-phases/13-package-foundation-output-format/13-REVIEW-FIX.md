---
phase: 13-package-foundation-output-format
fixed_at: 2026-06-14T00:00:00Z
review_path: .planning/phases/13-package-foundation-output-format/13-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-06-14
**Source review:** .planning/phases/13-package-foundation-output-format/13-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (2 Critical + 3 Warning)
- Fixed: 5
- Skipped: 0

All fixes were verified against the project venv (`./venv`): `mypy --strict`
clean on every modified source file, `ruff check` introduced zero new errors,
and the full suite grew from 54 to 56 passing tests (two WR-02 regression tests
added). Two regression scenarios for the CR-01/CR-02 non-dict-JSON degradation
path were verified manually (array-root locale files now degrade to `ext_id`
instead of raising `AttributeError`).

Note on pre-existing checks unchanged by this work:
- `src/maccat/__main__.py:20` mypy/ruff errors are the known IN-02 Phase-16 stub
  (out of scope, intentionally broken until Phase 16).
- The `ruff` errors remaining in the test files and the `writer.py` quoted
  return annotation (`UP037`) existed in the pre-fix baseline and are unrelated
  to these findings.

## Fixed Issues

### CR-01: `chrome_ext_name` crashes on non-dict `messages.json`

**Files modified:** `src/maccat/helpers/chrome_name.py`
**Commit:** 72ef136
**Applied fix:** Added `UnicodeDecodeError` to the `json.loads` except tuple and
inserted an `if not isinstance(messages, dict): return ext_id` guard before
`messages.items()`. A locale file that is valid JSON but not an object (array,
string, number) now degrades to `ext_id` exactly as the zsh `jq ... 2>/dev/null`
path does, instead of raising `AttributeError` and aborting the catalog run.
Also wrapped the resolved value in `str(...)` to satisfy `mypy --strict`
(`no-any-return`) without changing the happy-path byte output. Verified: an
array-root `messages.json` returns the extension ID.

### CR-02: `resolve_vsc_ext_name` crashes on non-dict `package.nls.json`

**Files modified:** `src/maccat/helpers/vsc_name.py`
**Commit:** 6bef94a
**Applied fix:** Same defect class as CR-01. Added `UnicodeDecodeError` to the
except tuple and inserted an `if not isinstance(nls, dict): return ext_id` guard
before `nls.get(nls_key, "")`. A non-object `package.nls.json` now degrades to
`ext_id` (matching the zsh `jq '.[$k] // ""' 2>/dev/null` path) rather than
raising `AttributeError`. Wrapped the resolved value in `str(...)` for
`mypy --strict`. Verified: an array-root `package.nls.json` returns the
extension ID.

### WR-01: `CatalogWriter` fails `mypy --strict`

**Files modified:** `src/maccat/catalog/writer.py`
**Commit:** 366b394
**Applied fix:** Imported `IO` from `typing` and annotated the attribute as
`self._fh: IO[str] | None = None`. The `os.fdopen(...)` assignment in
`__enter__` and the `self._fh.write(...)` / `.close()` calls now type-check
under `mypy --strict`. Runtime behavior is unchanged. Verified: `mypy --strict
src/maccat/catalog/writer.py` reports no issues.

### WR-02: `version_sort_tail` docstring overclaims parity (missing `^[0-9]` pre-filter)

**Files modified:** `src/maccat/catalog/format.py`, `tests/test_format.py`
**Commit:** 83c6c47
**Applied fix:** Chose the review's preferred option — applied the filter inside
the function so it is faithful to the documented zsh pipe
(`ls -1 | grep -E '^[0-9]' | sort -V | tail -1`). Candidates whose first
character is not an ASCII digit (e.g. `_metadata`, `_crx_invalidation_map`) are
now dropped before `sort -V`, so they cannot "steal the slot." Used
`c[:1].isascii() and c[:1].isdigit()` to match grep's POSIX `^[0-9]` exactly
(plain `str.isdigit()` would also match Unicode digits). Updated the docstring
to describe the filter. Added two regression tests
(`test_filters_chrome_internal_entries`, `test_all_non_version_returns_none`).
Verified: existing version-selection behavior is preserved and the two new tests
pass.

### WR-03: subprocess `sort` failures silently absorbed into output

**Files modified:** `src/maccat/catalog/format.py`
**Commit:** 4357a21
**Applied fix:** After both `subprocess.run(["sort", ...])` calls
(`flush_section` and `version_sort_tail`), added a `result.returncode != 0`
check that raises `RuntimeError` with the captured stderr. Because the result is
materialized in memory before write, a non-zero `sort` exit now aborts and lets
the atomic `CatalogWriter` discard the tmp file rather than committing a
truncated/empty section to the catalog. Verified: clean mypy/ruff and all tests
pass.

---

_Fixed: 2026-06-14_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
