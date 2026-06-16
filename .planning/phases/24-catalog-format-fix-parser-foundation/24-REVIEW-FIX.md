---
phase: 24-catalog-format-fix-parser-foundation
fixed_at: 2026-06-16T20:00:00Z
review_path: .planning/phases/24-catalog-format-fix-parser-foundation/24-REVIEW.md
iteration: 2
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 24: Code Review Fix Report

**Fixed at:** 2026-06-16T20:00:00Z
**Source review:** .planning/phases/24-catalog-format-fix-parser-foundation/24-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 2 (both Warnings; 2 Info findings explicitly out of scope and require no action per the review)
- Fixed: 2
- Skipped: 0

Both in-scope Warnings were contract/test-coverage gaps, not runtime defects. Per the
fix guidance they were resolved by documenting the behavior as KNOWN LOSSY in the
`parser.py` module docstring and pinning each behavior with an `ADVERSARIAL_CASES`
test row (`round_trip_ok=False`). The right-anchored regex contract was NOT changed
and `src/maccat/catalog/format.py::emit_item` was NOT touched. Full suite stays green
(451 passed, 5 skipped); `mypy --strict` and `ruff check` clean on both touched files.

## Fixed Issues

### WR-01: Trailing-whitespace tolerance silently mutates a name that legitimately ends in a space

**Files modified:** `src/maccat/reinstall/parser.py`, `tests/reinstall/test_parser_contract.py`
**Commit:** f23cc4f
**Applied fix:** Added a KNOWN-LOSSY bullet to the `parser.py` module docstring documenting
that a name legitimately ending in whitespace is not round-trippable (the WR-04 `\s+`/`\s*$`
tolerance consumes the name's trailing space along with the emit separator space), and noting
that emit_item-derived catalogs never produce such names. Locked the behavior with an
`ADVERSARIAL_CASES` row `("App  (1.0)", "App", "1.0", None, False)` — the exact
`emit_item("App ", "1.0", "")` output — marked `round_trip_ok=False`. Verified: parser
contract suite green, full suite green, mypy --strict + ruff clean.

### WR-02: Embedded-bracket name ambiguity is unhandled and untested

**Files modified:** `src/maccat/reinstall/parser.py`, `tests/reinstall/test_parser_contract.py`
**Commit:** 3dc8bfe
**Applied fix:** Added a KNOWN-LOSSY bullet to the `parser.py` module docstring documenting
the symmetric embedded-bracket case (`"Foo [Bar]"` parses to name `"Foo"`, id `"Bar"` under
right-anchored matching, parallel to the documented embedded-paren case). Locked the behavior
with an `ADVERSARIAL_CASES` row `("Foo [Bar]", "Foo", None, "Bar", False)` marked
`round_trip_ok=False`. Verified: parser contract suite 30 passed, full suite green,
mypy --strict + ruff clean.

## Skipped Issues

None. The two Info findings (IN-01 `mas list` subprocess timeout, IN-02 multi-space
name collapse) were out of scope (`fix_scope: critical_warning`) and the review
itself states no action is required for either.

---

_Fixed: 2026-06-16T20:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
