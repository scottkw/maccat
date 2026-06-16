---
phase: 24-catalog-format-fix-parser-foundation
reviewed: 2026-06-16T20:15:00Z
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
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 24: Code Review Report

**Reviewed:** 2026-06-16 (iteration 3, final pass)
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Iteration 3 (final pass) re-review. Confirmed that the iteration-2 follow-up gaps are
now resolved and locked:

- **Prior WR-01 (trailing-whitespace not round-trippable)** is now documented at
  `parser.py:23-29` (KNOWN-LOSSY bullet) and locked by `ADVERSARIAL_CASES`
  `("App  (1.0)", "App", "1.0", None, False)` at `test_parser_contract.py:62`.
- **Prior WR-02 (embedded-bracket name ambiguity)** is now documented at
  `parser.py:19-22` and locked by `("Foo [Bar]", "Foo", None, "Bar", False)` at
  `test_parser_contract.py:56`.

These are the accepted contract and are **not** re-flagged.

Independent verification performed this pass:

- **Tests:** 45 passed (`tests/reinstall/test_parser_contract.py` + `tests/collectors/test_homebrew.py`).
- **Lint/type:** `ruff check` clean and `mypy --strict` clean on the changed source files.
- **Round-trip fuzz:** exhaustively ran `emit_item -> _parse_item_line -> emit_item`
  over realistic canonical inputs (names with spaces, `@`, `-`, `+`, dots, unicode;
  multi-token versions like `"3.11.1 3.11.2"`; numeric ids) — **zero round-trip
  failures**. The canonical contract holds.
- **Section separation:** the real cli.py layout (content line directly followed by
  the next section's leading-`\n` header) parses into the correct sections; EOF flush
  does not double-emit.
- **mas parser:** 2-field degradation, parenthesized name fields, tab-separated input,
  and 1-field skip all behave per spec.
- **Degradation paths:** mas `OSError`, non-zero exit, and absent-CLI paths warn and
  continue without crashing.

No genuine runtime defect, crash path, silent data loss on a documented/canonical path,
type/lint breakage, or broken round-trip on canonical `emit_item` output was found.
`catalog/format.py::emit_item` confirmed unmodified.

One robustness gap remains on the non-canonical (hand-edited/external) parse path,
recorded below as a WARNING because it is the input class the parser explicitly claims
to handle gracefully and it produces silent data loss.

## Warnings

### WR-01: A title candidate followed by a second non-separator line silently drops the swallowed line and the trailing section

**File:** `src/maccat/reinstall/parser.py:193-196`
**Issue:**
In the `SEEKING_SEPARATOR` state, when the line after a title candidate is neither the
separator nor blank, the code discards the candidate **and consumes that line** as the
discard trigger without re-evaluating it as a new title candidate:

```python
else:
    # something else: discard the title candidate, back to SEEKING_TITLE
    current_title = None
    state = "SEEKING_TITLE"
```

Effect — verified by direct probe. The fragment
`FakeTitle\nRealTitle\n------------------------------------\nitem1\n`
parses to **zero sections**: `RealTitle` is swallowed as the discard trigger; the
following separator is then seen in `SEEKING_TITLE` and ignored; `item1` becomes a
title candidate that never receives a separator and is dropped at EOF.

This is silent data loss on the external/hand-edited catalog path — the exact path the
module docstring (`parser.py:8-29`) and `_parse_item_line` ("Never raises") advertise as
gracefully handled. It does **not** affect canonical output:
`CatalogWriter.write_section` (`writer.py:67-68`) always emits `\n{title}\n{separator}\n`,
so a title is always immediately followed by its separator, and the round-trip fuzz
confirmed the canonical path is unaffected. Severity is WARNING (not BLOCKER) because no
collector or `emit_item` path can produce this layout; the exposure is confined to
externally supplied catalogs.

**Fix:** Re-evaluate the consumed line as a fresh title candidate rather than throwing it
away:

```python
else:
    # current candidate had no separator: the new line is itself a fresh
    # title candidate — stay in SEEKING_SEPARATOR with it instead of
    # consuming it as a throwaway.
    current_title = line
    state = "SEEKING_SEPARATOR"
```

Alternatively, if requiring an immediately-following separator is intentional, add a
test asserting the zero-section outcome so the swallowing behavior is locked by contract
rather than left incidental.

## Info

### IN-01: `parse_catalog` reads the whole file into memory with no size guard

**File:** `src/maccat/reinstall/parser.py:161`
**Issue:**
`text = path.read_text(encoding="utf-8")` loads the entire catalog into memory. For this
tool's per-machine snapshots this is fine and consistent with the rest of the codebase,
so this is informational only — noted should the parser ever be pointed at arbitrary
external files. No action required for current scope.
**Fix:** None required; documented for awareness.

---

_Reviewed: 2026-06-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
