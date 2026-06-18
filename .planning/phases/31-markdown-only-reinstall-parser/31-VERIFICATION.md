---
phase: 31-markdown-only-reinstall-parser
verified: 2026-06-18T00:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
gaps: []
---

# Phase 31: Markdown-Only Reinstall Parser Verification Report

**Phase Goal:** `reinstall/parser.py` reads the new markdown format (frontmatter + per-section tables) back into the typed `ParsedCatalog`, with the parser ↔ markdown-emitter round-trip re-locked by the contract test; `maccat reinstall` consumes markdown only and refuses legacy `.txt` with a clear convert directive.
**Verified:** 2026-06-18
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `reinstall/parser.py` parses a markdown catalog's frontmatter + per-section tables into the typed `ParsedCatalog`, preserving each item's name / version / ID across the 22 sections | VERIFIED | `parse_markdown_catalog` added to `src/maccat/reinstall/parser.py` lines 288-372. Behavioral spot-check confirms round-trip: Homebrew items `('git', '2.44.0', None)`, App Store `('Final Cut Pro', '10.7.1', '424389933')`, empty Setapp section `items==[]`. All 9 `TestMarkdownRoundTrip` tests pass. |
| 2 | A round-trip contract test asserts emitter → parser is lossless against the markdown emitter from Phase 30 (the v2.1.0 plain-text round-trip lock is replaced, not duplicated) | VERIFIED | `TestMarkdownRoundTrip` class (9 tests) in `tests/reinstall/test_parser_contract.py` calls `render_markdown_catalog` then `parse_markdown_catalog` and asserts losslessness. Covers all item shapes: name+version+id, name+version only, name+id only, name only, pipe in name, backslash in name, empty section. All 9 pass. Legacy `TestRoundTrip` and `TestParseCatalog` remain intact (not deleted). |
| 3 | `maccat reinstall` against a `.md` catalog generates the same reviewable `reinstall.sh` as before (deterministic auto-install lines + manual checklist), never auto-executed | VERIFIED | `cli.py` lines 55-71: deferred import of `parse_markdown_catalog`, calls it, writes `reinstall.sh` via `emit_reinstall_script`. `test_reinstall_cli.py` (14 tests pass) and `test_picker_and_reinstall_cli.py` `TestRunReinstall` (5 tests pass) use `.md` fixtures and confirm `reinstall.sh` is written to disk at mode 0o644, never executed. |
| 4 | `maccat reinstall` handed a legacy `.txt` catalog fails with a clear message directing the user to `convert` it first — no silent partial parse and nothing executed | VERIFIED | Extension check in `parse_markdown_catalog` (line 309-313) raises `ValueError` for non-`.md` paths; content-sniff check (line 321-326) raises `ValueError` for `.md` files missing frontmatter. `cli.py` catches both in `except (OSError, ValueError) as exc: sys.exit(f"ERROR: {exc}")`. Behavioral test confirms exit message: `"ERROR: ... is not a markdown catalog (.md extension required). Convert it first with: maccat convert --from ..."`. `TestMarkdownParserRefusal` (4 tests) all pass. |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/maccat/reinstall/parser.py` | `_unescape_cell`, `_parse_markdown_row`, `parse_markdown_catalog` added; `parse_catalog` and all dataclasses untouched | VERIFIED | All three new symbols importable. `parse_catalog` still importable unchanged. `MD_NONE_FOUND = "(none found)"` (no leading spaces); `NONE_FOUND_SENTINEL = "  (none found)"` (two leading spaces) unchanged. File is 373 lines. |
| `tests/reinstall/test_parser_contract.py` | `TestMarkdownRoundTrip` and `TestMarkdownParserRefusal` classes present | VERIFIED | Both classes exist (lines 376-595). 9 round-trip tests, 4 refusal tests. All 43 tests in the file pass. |
| `src/maccat/reinstall/cli.py` | `parse_catalog` replaced by `parse_markdown_catalog`; `except (OSError, ValueError)` present | VERIFIED | `parse_catalog` does not appear anywhere in the file. `parse_markdown_catalog` is deferred-imported (line 56) and called (line 69). `except (OSError, ValueError) as exc` on line 70. |
| `tests/reinstall/test_reinstall_cli.py` | `_MINIMAL_CATALOG` updated to markdown content; fixture path `.md` | VERIFIED | `_MINIMAL_CATALOG` opens with `'---\n'` (frontmatter). Fixture path `mac-software-list-[TestMac]-20260616120000.md`. Glob assertion uses `*.md`. |
| `tests/reinstall/test_picker_and_reinstall_cli.py` | `TestRunReinstall.fixture_catalog` uses markdown content and `.md` path | VERIFIED | `fixture_catalog` at line 174 writes markdown content with YAML frontmatter to `mac-software-list-[TestMac]-20260616120000.md`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/reinstall/test_parser_contract.py` | `src/maccat/catalog/markdown.py` | `render_markdown_catalog` call in `rendered_catalog` fixture | WIRED | Line 397 of test file calls `render_markdown_catalog(sections, computer=..., ...)` |
| `tests/reinstall/test_parser_contract.py` | `src/maccat/reinstall/parser.py` | `parse_markdown_catalog` call in assertions | WIRED | Line 413 calls `parse_markdown_catalog(path)` in round-trip tests; line 559 in refusal tests |
| `src/maccat/reinstall/cli.py` | `src/maccat/reinstall/parser.py` | deferred import of `parse_markdown_catalog` (PKG-03 pattern) | WIRED | Line 56: `from maccat.reinstall.parser import parse_markdown_catalog`. Called at line 69. |

---

### Data-Flow Trace (Level 4)

The reinstall pipeline is not a data-rendering UI component — it reads a file and writes a file. The round-trip spot-check above (run live against `render_markdown_catalog` output) confirms real data flows end-to-end: `render_markdown_catalog` → disk → `parse_markdown_catalog` → `ParsedCatalog` with populated items. The data is not disconnected or hardcoded.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `parse_markdown_catalog` | `catalog.sections` / `current_section.items` | `path.read_text(encoding="utf-8")` → line iteration | Yes — reads actual file content, appends real `ParsedItem` objects | FLOWING |
| `run_reinstall` | `catalog` | `parse_markdown_catalog(catalog_path)` | Yes — catalog populated from disk file, passed to `emit_reinstall_script` | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `.txt` raises `ValueError` with `"maccat convert --from"` in message | `./venv/bin/python -c "parse_markdown_catalog(Path('old.txt'))"` | `ValueError: ... is not a markdown catalog ... Convert it first with: maccat convert --from ...` | PASS |
| `.md` without frontmatter raises `ValueError` with `"maccat convert --from"` | `./venv/bin/python -c "parse_markdown_catalog(Path('bad.md'))"` | `ValueError: ... is missing valid YAML frontmatter ... Convert it first with: maccat convert --from ...` | PASS |
| `run_reinstall` with `.txt` path exits non-zero with "convert" in message | `./venv/bin/python -c "run_reinstall(Namespace(from_path='...txt', ...))"` | `SystemExit: 'ERROR: ... is not a markdown catalog (.md extension required). Convert it first with: maccat convert --from ...'` | PASS |
| Round-trip: `render_markdown_catalog` → `parse_markdown_catalog` preserves items | Live spot-check | Sections, names, versions, IDs all match input; empty Setapp section `items==[]` | PASS |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| RIN-01 | `reinstall/parser.py` parses markdown catalog format into `ParsedCatalog`; round-trip re-locked against emitter | SATISFIED | `parse_markdown_catalog` exists, 9 `TestMarkdownRoundTrip` tests all pass including adversarial cell values (pipe, backslash, empty cells) |
| RIN-02 | `maccat reinstall` consumes markdown only; `.txt` fails with clear convert directive, no silent partial parse | SATISFIED | Extension check + frontmatter sniff both raise `ValueError`; `cli.py` catches and exits with `"ERROR: ..."` containing convert directive; 4 `TestMarkdownParserRefusal` tests all pass |

---

### Anti-Patterns Found

Scanned `src/maccat/reinstall/parser.py`, `src/maccat/reinstall/cli.py`, `tests/reinstall/test_parser_contract.py` for `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, `PLACEHOLDER`, stub patterns, and hardcoded empty returns.

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| — | None found | — | — |

No debt markers, no stub returns, no hardcoded empty data in any modified file.

---

### Human Verification Required

None. All success criteria are verifiable programmatically and confirmed by live test runs.

---

### Gaps Summary

No gaps. All 4 roadmap success criteria are fully met:

1. `parse_markdown_catalog` reads frontmatter + tables into `ParsedCatalog` with full name/version/ID fidelity.
2. Round-trip contract test (`TestMarkdownRoundTrip`, 9 tests) locks emitter ↔ parser losslessness, including adversarial cell values. Legacy `TestRoundTrip`/`TestParseCatalog` are retained.
3. `maccat reinstall` with a valid `.md` catalog writes `reinstall.sh` correctly (14 + 5 integration tests confirm).
4. `maccat reinstall` with a `.txt` path fails non-zero with a self-contained "Convert it first with: maccat convert --from" message; no silent partial parse.

Legacy `parse_catalog` is unchanged and importable — Phase 32 dependency preserved.

Full suite: **690 passed**, ruff clean, mypy --strict clean (41 source files).

---

_Verified: 2026-06-18_
_Verifier: Claude (gsd-verifier)_
