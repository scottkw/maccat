---
phase: "30-markdown-emitter-md-plumbing"
plan: 3
subsystem: cli/integration
tags: [cli, markdown, integration, generate-loop, test-fix]
dependency_graph:
  requires:
    - "render_markdown_catalog (30-01)"
    - "CatalogWriter.write_raw (30-01)"
    - "make_catalog_filename returns .md (30-02)"
  provides:
    - "maccat generate writes .md catalog with YAML frontmatter + markdown tables"
    - "test_cli.py all five glob assertions use *.md"
  affects:
    - "src/maccat/cli.py"
    - "tests/test_cli.py"
tech_stack:
  added: []
  patterns:
    - "Deferred import of socket inside run() body"
    - "Single datetime.now() call producing both timestamp and generated_iso"
    - "render_markdown_catalog + write_raw replaces write_section/write_lines loop"
key_files:
  created: []
  modified:
    - path: "src/maccat/cli.py"
      role: "generate loop replaced with render_markdown_catalog + write_raw; socket/Section/__version__ added as deferred imports; flush_section removed"
    - path: "tests/test_cli.py"
      role: "five glob assertions updated from *.txt to *.md; txt_files renamed to md_files"
decisions:
  - "socket.gethostname() called inline in render_markdown_catalog argument; single evaluation per run"
  - "flush_section removed from cli.py deferred imports — now handled entirely inside render_markdown_catalog"
  - "all_sections built with list + extend pattern (explicit type annotation list[Section]) to satisfy mypy --strict"
metrics:
  duration: "5 minutes"
  completed: "2026-06-18"
  tasks_completed: 2
  files_created: 0
  files_modified: 2
---

# Phase 30 Plan 3: CLI Integration Summary

**One-liner:** generate loop wired to render_markdown_catalog + write_raw; socket/Section/__version__ deferred imports added; five test_cli.py *.txt glob assertions replaced with *.md, making all 667 tests pass.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Replace generate loop with render_markdown_catalog + write_raw | 477b246 | src/maccat/cli.py |
| 2 | Fix test_cli.py five glob assertions from *.txt to *.md | 7545b62 | tests/test_cli.py |

## What Was Built

### `src/maccat/cli.py` (modified — generate loop)

The generate loop in `run()` (steps 9–10) was replaced:

**Before:**
- `timestamp = datetime.now().strftime(...)` — single call
- `CatalogWriter` with `write_section("Installed Mac Software List")` + per-collector `write_section(section.title)` + `flush_section` / `write_lines`

**After:**
- `now = datetime.now()` captures once; `timestamp` and `generated_iso` both derived from `now`
- `all_sections: list[Section]` built by iterating `get_registry()` and extending `result.sections`
- `render_markdown_catalog(all_sections, computer=computer, hostname=socket.gethostname(), generated=generated_iso, maccat_version=__version__)` returns the full catalog string
- `CatalogWriter(output_file) as w: w.write_raw(content)` — single write

New deferred imports added inside `run()`:
- `import socket`
- `from maccat import __version__, gitops` (merged from prior `from maccat import gitops`)
- `from maccat.catalog.markdown import render_markdown_catalog`
- `from maccat.collectors.base import Section`
- Removed: `from maccat.catalog.format import flush_section`

### `tests/test_cli.py` (modified — five glob assertions)

| Line | Class | Change |
|------|-------|--------|
| 241 | TestNoCommit::test_no_commit_catalog_file_written | `txt_files` → `md_files`, glob `*.txt` → `*.md`; docstring updated |
| 290 | TestGenerateThenSweep::test_just_written_catalog_not_archived | `txt_files` → `md_files`, glob `*.txt` → `*.md` |
| 295 | TestGenerateThenSweep::test_just_written_catalog_not_archived | `archived` glob `*.txt` → `*.md` |
| 334 | TestGenerateThenSweep::test_timestamp_captured_after_git_pull | `txt_files` → `md_files`, glob `*.txt` → `*.md` |
| 469 | TestInteractiveQuit::test_quit_writes_no_file | `txt_files` → `md_files`, glob `*.txt` → `*.md` |

## Smoke Test Result

`maccat --no-commit --computer Test` writes `mac-software-list-[Test]-YYYYMMDDHHMMSS.md` containing:

```
---
computer: Test
hostname: Kens-Personal-MacBook-Air.local
generated: "2026-06-18T14:46:54"
maccat_version: 2.1.0
---
# Installed Mac Software List

## Homebrew Packages
| Name | Version | ID |
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — full end-to-end integration complete. YAML frontmatter, per-section `##` headings, and 3-column `Name | Version | ID` tables all rendered correctly.

## Threat Flags

None. T-30-08 (atomic write), T-30-09 (hostname in frontmatter), T-30-10 (git add -A extension-agnostic), T-30-11 (single datetime.now() call) — all mitigations verified in implementation.

## Self-Check: PASSED

Files exist:
- src/maccat/cli.py: FOUND (modified)
- tests/test_cli.py: FOUND (modified)

Commits exist:
- 477b246: FOUND (feat — cli.py generate loop)
- 7545b62: FOUND (fix — test_cli.py globs)

Test results:
- 667 passed, 5 skipped — full test suite green
- ruff: All checks passed on src/maccat/cli.py
- mypy --strict: Success on src/maccat/cli.py
- No *.txt glob assertions remaining in tests/test_cli.py
