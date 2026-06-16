---
phase: 24-catalog-format-fix-parser-foundation
verified: 2026-06-16T20:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
gaps: []
deferred: []
human_verification: []
---

# Phase 24: Catalog Format Fix + Parser Foundation Verification Report

**Phase Goal:** The App Store ID is preserved in the catalog and the catalog can be parsed back into typed structured items
**Verified:** 2026-06-16T20:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A catalog generated after this phase includes the App Store numeric ID in every mas entry: `AppName (version) [id]` — no double-parenthesized version, no missing bracket | VERIFIED | `_parse_mas_output` in `mas.py` calls `emit_item(name, version, id_)` with id extracted from `parts[0]`; version strips one layer of parens with `last[1:-1]`; test `test_mas_collect_parses_output` asserts `["Safari (15.0) [1234567890]", "Xcode (14.0) [9876543210]"]` |
| 2 | The existing mas collector tests pass with updated assertions reflecting the new format | VERIFIED | `./venv/bin/pytest tests/collectors/test_homebrew.py::TestMasCollector -v` — 6/6 passed; `test_mas_two_field_line_degrades_to_name_id` exists; `test_mas_two_field_line_emits_trailing_space` is gone; `grep trailing_space` returns nothing |
| 3 | `parse_catalog(path)` returns a `ParsedCatalog` whose items correctly reflect name, version, and id for all four `emit_item` line shapes, including graceful handling of the `(none found)` sentinel and collector degradation messages | VERIFIED | `TestItemLineParser::test_parses_all_four_shapes` covers all four shapes (30/30 contract tests pass); `TestParseCatalog::test_none_found_sentinel_yields_empty_items` confirms items=[], degraded=False; `test_degradation_line_marks_section_degraded` confirms items=[], degraded=True |
| 4 | The round-trip contract test in `tests/reinstall/test_parser_contract.py` passes for all six `emit_item` degradation variants, including adversarial fixtures with embedded parentheses in names | VERIFIED | `TestRoundTrip` parametrized over 6 cases: all pass; `TestAdversarialFixtures` covers 7 adversarial cases (including nested-paren and embedded-bracket variants); all KNOWN LOSSY cases annotated with comments (7 `# KNOWN LOSSY` markers); `test_last_section_without_trailing_blank_is_not_dropped` passes |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/collectors/mas.py` | Rewritten `_parse_mas_output` calling `emit_item` | VERIFIED | Deferred import `from maccat.catalog.format import emit_item` present inside method body; three-column extraction algorithm implemented; no `parts[1] parts[2]` pattern remains |
| `tests/collectors/test_homebrew.py` | Updated TestMasCollector assertions; replacement two-field test | VERIFIED | Asserts `["Safari (15.0) [1234567890]", "Xcode (14.0) [9876543210]"]`; contains `test_mas_two_field_line_degrades_to_name_id`; `trailing_space` not present |
| `src/maccat/reinstall/__init__.py` | Subpackage init with one-line docstring | VERIFIED | File exists; content: `"""Reinstall script generation — catalog parser and emitter."""` |
| `src/maccat/reinstall/parser.py` | ParsedItem, ParsedSection, ParsedCatalog dataclasses + ITEM_RE + parse_catalog() + _parse_item_line() | VERIFIED | All dataclasses present; ITEM_RE three-branch right-anchored regex with distinct named groups; three-state machine with EOF flush; `parse_catalog` public function |
| `tests/reinstall/__init__.py` | Empty test package init file | VERIFIED | File exists (0 bytes) |
| `tests/reinstall/test_parser_contract.py` | Round-trip contract + adversarial + integration tests | VERIFIED | Four test classes; 30 tests; all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `mas.py::_parse_mas_output` | `catalog/format.py::emit_item` | Deferred import inside method body | VERIFIED | `from maccat.catalog.format import emit_item` on line 37 of `mas.py`, inside `_parse_mas_output` |
| `test_parser_contract.py` | `catalog/format.py::emit_item` | Direct import in contract test | VERIFIED | `from maccat.catalog.format import emit_item` on line 11 of `test_parser_contract.py`; called in `TestRoundTrip.test_round_trip` and `TestAdversarialFixtures` |
| `test_parser_contract.py` | `reinstall/parser.py::_parse_item_line` | Direct import in contract test | VERIFIED | `from maccat.reinstall.parser import (_parse_item_line, parse_catalog,)` on lines 12-15; used in all four test classes |
| `reinstall/parser.py::parse_catalog` | `catalog/writer.py` byte protocol | Inverts 36-dash separator + section-title + blank-line boundary | VERIFIED | `SEPARATOR = "-" * 36`; state machine transitions match `CatalogWriter.write_section` protocol; `_CATALOG_TWO_SECTIONS` fixture in tests encodes the exact byte protocol |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces parsing utilities and test infrastructure, not UI components or data pipelines rendering dynamic state.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `mas list` line produces correct `AppName (version) [id]` format | `./venv/bin/pytest tests/collectors/test_homebrew.py::TestMasCollector::test_mas_collect_parses_output -q` | 1 passed | PASS |
| Round-trip: all 6 emit_item shapes parse and re-emit identically | `./venv/bin/pytest tests/reinstall/test_parser_contract.py::TestRoundTrip -q` | 6 passed | PASS |
| EOF flush: last section without trailing blank is not dropped | `./venv/bin/pytest tests/reinstall/test_parser_contract.py::TestParseCatalog::test_last_section_without_trailing_blank_is_not_dropped -q` | 1 passed | PASS |
| Full suite remains green after changes | `./venv/bin/pytest tests/ -x -q` | 456 passed | PASS |

---

### Probe Execution

No probes declared or conventionally located for this phase. Step 7c: SKIPPED (no probe scripts).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MAS-01 | 24-01-PLAN.md | App Store section preserves numeric App Store ID — emits `AppName (version) [id]` | SATISFIED | `_parse_mas_output` routes through `emit_item(name, version, id_)` with id extracted from `parts[0]`; test assertions match `[id]` bracket format |
| PARSE-01 | 24-02-PLAN.md | Parser reads catalog back into structured per-source items honoring all four emit_item line shapes; round-trip contract test locks format.py coupling | SATISFIED | `parse_catalog()` and `_parse_item_line()` implemented in `reinstall/parser.py`; 30-test contract suite in `test_parser_contract.py` passes; all 6 emit_item shapes round-trip correctly |

**Orphaned requirements:** None — REQUIREMENTS.md maps MAS-01 and PARSE-01 to Phase 24 only; no additional Phase 24 requirements exist.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

Scan notes:
- No `TBD`, `FIXME`, or `XXX` markers in any modified file
- No stub patterns (`return null`, `return []`, `return {}`) in implementation code
- No hardcoded empty data flowing to rendering
- `# KNOWN LOSSY` comments in test file are intentional documentation of design decisions, not debt markers

The SUMMARY.md documents one non-blocking WARNING about state-machine robustness on MALFORMED/hand-edited input. This was reviewed against the code: the parser degrades gracefully on all malformed input paths (unknown title candidates are discarded, unparseable lines fall back to name-only `ParsedItem`, `_parse_item_line` never raises). The warning is a design note about adversarial inputs that `emit_item` never generates — not a gap in the canonical round-trip contract.

---

### Human Verification Required

None. All success criteria are mechanically verifiable via the test suite, linter, and type checker. No visual, real-time, or external-service behavior to confirm.

---

### Gaps Summary

No gaps. All four roadmap success criteria are verified against the actual codebase:

1. Every mas entry format test asserts `AppName (version) [id]` — confirmed by code inspection of `_parse_mas_output` and passing test assertions.
2. All MasCollector tests pass with updated assertions — 6/6 green; old `trailing_space` test eliminated.
3. `parse_catalog()` correctly handles all four `emit_item` line shapes, the `(none found)` sentinel, and degradation messages — 30/30 contract tests green.
4. Round-trip contract holds for all six `emit_item` variants; adversarial fixtures cover embedded parens in names; KNOWN LOSSY cases annotated; EOF flush test present and passing.

Full suite: **456 passed** (up from 421 pre-phase 01, then 442 post-plan 02, settling at 456 with the additional adversarial fixture variants added in the review-fix iterations). Ruff and mypy both exit clean.

---

_Verified: 2026-06-16T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
