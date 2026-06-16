---
phase: 24-catalog-format-fix-parser-foundation
fixed_at: 2026-06-16T19:16:51Z
review_path: .planning/phases/24-catalog-format-fix-parser-foundation/24-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 24: Code Review Fix Report

**Fixed at:** 2026-06-16
**Source review:** .planning/phases/24-catalog-format-fix-parser-foundation/24-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (Warnings WR-01..WR-05; 0 Critical)
- Fixed: 5
- Skipped: 0

All in-scope warnings fixed. The 4 Info findings (IN-01..IN-04) were out of
scope (fix_scope=critical_warning) and were not attempted. Full project gates
stayed green after every fix: `ruff check src tests` clean, `mypy --strict src`
clean (32 files), `pytest` 449 passed / 5 skipped (up from 442 / 5 — seven new
test rows/methods added). `format.py::emit_item` was not modified, per the
phase constraint.

## Fixed Issues

### WR-01: `mas list` subprocess can raise an unhandled exception and crash the CLI

**Files modified:** `src/maccat/collectors/mas.py`
**Commit:** 18324ce
**Applied fix:** Wrapped the `subprocess.run(["mas", "list"], ...)` call in
`try/except OSError`. On `OSError` (TOCTOU after `available()`, broken symlink,
exec/permission failure) the collector now prints
`  WARNING: could not run mas: {exc}` to stderr and returns the existing
"Could not retrieve App Store list." raw section instead of propagating the
exception through the orchestrator and aborting the whole catalog run. This
restores the mandatory warn-and-continue / graceful-degradation guarantee.

### WR-02: mas non-zero exit returns an error section silently (no stderr warning)

**Files modified:** `src/maccat/collectors/mas.py`
**Commit:** e9f0722
**Applied fix:** Added `print(f"  WARNING: mas list failed (exit {result.returncode}).", file=sys.stderr)`
before returning the error section on non-zero exit, matching the project's
"Output Conventions" and the sibling `homebrew.py` degradation paths. The
non-zero-exit path is no longer silent.

### WR-03: Parser silently drops version on names containing nested parentheses

**Files modified:** `src/maccat/reinstall/parser.py`, `tests/reinstall/test_parser_contract.py`
**Commit:** bc43d77
**Applied fix:** Chose review option (a) — documented the behavior as an explicit
KNOWN LOSSY contract rather than changing the regex (lower risk; matches the
existing "documented lossy" pattern and the phase's "prefer guard + test"
guidance). Added a KNOWN LOSSY section to the module docstring describing the
nested-paren case, and added two `ADVERSARIAL_CASES` rows pinning current
behavior: `"Foo (Bar (Baz)) [9]"` -> name kept verbatim, version=None, id="9";
and `"Foo (Bar (Baz))"` -> name-only. `emit_item` never emits nested parens, so
self-produced catalogs are unaffected.

### WR-04: Trailing whitespace on an item line silently degrades it to name-only

**Files modified:** `src/maccat/reinstall/parser.py`, `tests/reinstall/test_parser_contract.py`
**Commit:** 191e0aa
**Applied fix:** Inserted `\s*` before the final `$` in `ITEM_RE` so optional
trailing whitespace is tolerated. Version/id are now recovered from lines like
`"Safari (15.0) "` or `"Safari (15.0) [123] "`, and a name-only line with a
trailing space resolves to a trimmed name while `raw_line` is preserved verbatim.
This does not touch `emit_item` (which never emits trailing whitespace), so
canonical round-trip cases are unchanged. Added a parametrized
`test_trailing_whitespace_is_tolerated` covering version-only, version+id,
id-only, and name-only trailing-space inputs.

### WR-05: Header section is parsed as a spurious empty `ParsedSection` (no test coverage)

**Files modified:** `src/maccat/reinstall/parser.py`, `tests/reinstall/test_parser_contract.py`
**Commit:** d105beb
**Applied fix:** Decided and locked the contract per the review. Chose to keep
the current behavior (parser does NOT filter the content-less
"Installed Mac Software List" header) rather than filtering in `parse_catalog`,
because an empty header is indistinguishable from a section that legitimately
produced no item lines, and there are no `parse_catalog` consumers yet (Phase 25
is future) to validate a filtering change against. Documented the header-section
contract in the `parse_catalog` docstring (downstream consumers must skip empty,
non-degraded sections) and added an integration test
`test_real_header_layout_yields_leading_empty_header_section` that feeds the
exact `cli.py` header+sections layout and asserts the leading empty header plus
correct parsing of the trailing real sections.

---

_Fixed: 2026-06-16_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
