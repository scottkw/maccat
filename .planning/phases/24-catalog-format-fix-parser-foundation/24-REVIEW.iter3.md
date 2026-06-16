---
phase: 24-catalog-format-fix-parser-foundation
reviewed: 2026-06-16T19:30:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/maccat/collectors/mas.py
  - src/maccat/reinstall/parser.py
  - src/maccat/reinstall/__init__.py
  - tests/collectors/test_homebrew.py
  - tests/reinstall/test_parser_contract.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 24: Code Review Report

**Reviewed:** 2026-06-16 (iteration 2)
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Iteration 2 re-review after WR-01..WR-05 were fixed. The five prior Warning fixes were
verified against the source and are **sound**:

- **WR-03** (nested-paren lossy contract + non-zero `sort` exit aborts instead of
  committing a truncated section) is implemented in `catalog/format.py:70-71` and
  `:104-105` and locked by the `Foo (Bar (Baz))` rows in `ADVERSARIAL_CASES`.
- **WR-04** (tolerate trailing whitespace via the `\s*$` tail in `ITEM_RE`) is at
  `parser.py:58` and locked by `test_trailing_whitespace_is_tolerated`.
- **WR-05** (leading content-less "Installed Mac Software List" header emitted as an
  empty, non-degraded `ParsedSection`, filtering deferred to the consumer) is in the
  state machine and locked by `test_real_header_layout_yields_leading_empty_header_section`.

Verification performed this iteration: all 43 tests across the two suites pass;
`mypy --strict` clean on both source files; `ruff check` clean on all five files. The
parser is a faithful right-anchored inverse of `emit_item` (`catalog/format.py:16`,
intentionally unmodified); the EOF-flush rule does not double-emit across trailing blank
lines (verified with single- and double-trailing-blank inputs); and `_parse_mas_output`
correctly degrades versionless rows and empty-paren `()` versions.

No correctness regressions were introduced by the prior fixes. The remaining findings
are pre-existing edge gaps surfaced by adversarial probing — none are blockers.

## Warnings

### WR-01: Trailing-whitespace tolerance silently mutates a name that legitimately ends in a space

**File:** `src/maccat/reinstall/parser.py:48-60`
**Issue:** The WR-04 fix tolerates trailing whitespace, but the same `\s+`/`\s*`
matching also eats a trailing space that is part of the name itself, breaking the
round-trip contract the module advertises. Probed directly:

```
emit_item("App ", "1.0", "")          -> "App  (1.0)"   (name's space + emit's space)
_parse_item_line("App  (1.0)").name   -> "App"          (both spaces consumed)
emit_item("App", "1.0", "")           -> "App (1.0)"    != "App  (1.0)"  -- round-trip fails
```

The same applies to name-only lines: `_parse_item_line("plain name   ").name` returns
`"plain name"` (trailing spaces dropped from `name`, though `raw_line` is preserved). For
real catalogs this is benign — `MasCollector`/`HomebrewCollector` derive names via
`str.split()` and never produce trailing-space names — so this is a hand-edited/external
catalog defect only. But the module docstring claims a clean round-trip contract and the
KNOWN-LOSSY section does not list trailing-space names.
**Fix:** Either (a) add a KNOWN-LOSSY bullet to the parser module docstring documenting
that a trailing-whitespace name is not round-trippable (matches the existing
"document the lossy case" convention used for nested parens), or (b) add an
`ADVERSARIAL_CASES` row with `round_trip_ok=False` for a trailing-space name so the
contract is locked by test rather than left implicit.

### WR-02: Embedded-bracket name ambiguity is unhandled and untested (asymmetry with the documented embedded-paren case)

**File:** `src/maccat/reinstall/parser.py:8-16` (docstring KNOWN-LOSSY list) and
`tests/reinstall/test_parser_contract.py:36-51` (`ADVERSARIAL_CASES`)
**Issue:** The KNOWN-LOSSY contract and adversarial fixtures cover embedded
*parentheses* in names but not the symmetric embedded-*bracket* case, which is equally
ambiguous under right-anchored matching. Probed:

```
_parse_item_line("Foo [Bar]")  -> name="Foo", version=None, id="Bar"
```

An app legitimately named `Foo [Bar]` (no real App Store id) is silently re-interpreted
as name `Foo` with id `Bar` — directly parallel to the documented `App (Beta)` paren
case, but neither documented nor tested. Downstream Phase 25 would then emit a spurious
`[Bar]` id. Real `mas`/`brew` names rarely contain brackets, so this is not a blocker,
but the documentation gives a false impression of exhaustiveness.
**Fix:** Add an `ADVERSARIAL_CASES` row, e.g.
`("Foo [Bar]", "Foo", None, "Bar", False)` with a `round_trip_ok=False` comment, and a
matching bullet to the parser module docstring's KNOWN-LOSSY list, so the
bracket-ambiguity behavior is locked and discoverable alongside the paren case.

## Info

### IN-01: `mas list` subprocess has no timeout (consistent with sibling collector)

**File:** `src/maccat/collectors/mas.py:76-78`
**Issue:** `subprocess.run(["mas", "list"], ...)` has no `timeout=`. A hung `mas`
invocation would block the CLI indefinitely. This is *consistent* with
`HomebrewCollector._run` (`homebrew.py:31`), which also omits a timeout, so it is a
pre-existing project-wide convention, not a regression from this phase. Flagged only so
it is not mistaken for an oversight specific to the parser work.
**Fix:** Optionally add a uniform `timeout=` to both collectors and handle
`subprocess.TimeoutExpired` in the existing warn-and-continue path
(`mas.py:79-91`). Out of scope for this phase; no action required now.

### IN-02: Multi-space app names are collapsed by `_parse_mas_output`

**File:** `src/maccat/collectors/mas.py:48,51`
**Issue:** `name = " ".join(parts[1:-1])` rebuilds the name from `line.split()`,
collapsing internal whitespace runs to a single space. Probed:
`"123   Lots Of   Spaces  (1.0)"` yields name `"Lots Of Spaces"`. App Store names with
internal double spaces are vanishingly rare, and this matches the whitespace-normalizing
approach used elsewhere in the collectors, so it is a minor fidelity note, not a defect.
**Fix:** None required. If exact-name fidelity ever becomes a requirement, parse the id
with `line.split(None, 1)` and strip the trailing `(version)` via regex to preserve
interior spacing.

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
